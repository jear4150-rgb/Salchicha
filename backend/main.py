import base64
import csv
import io
import json
import os
from datetime import date, datetime

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Domicilio, DomicilioBatch, Repartidor, Ticket, Zona, get_db, init_db
from spreadsheet import detect_columns, guess_address_column, parse_spreadsheet

load_dotenv()

app = FastAPI(title="Delivery Receipt Payment App")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

init_db()

client = anthropic.Anthropic()

TIPOS_PAGO = {"efectivo", "tarjeta", "transferencia", "otro"}

VISION_PROMPT = """Analiza este ticket/remito de entrega y extrae la información de pago.

Devuelve SOLO un JSON con esta estructura exacta (sin markdown, sin explicaciones):
{
  "monto": <número decimal con punto como separador>,
  "tipo_pago": "<efectivo|tarjeta|transferencia|otro>",
  "descripcion": "<descripción breve: número de ticket o cliente>"
}

Reglas para tipo_pago:
- "efectivo": si dice cash, efectivo, contado, o no especifica método
- "tarjeta": si dice tarjeta, débito, crédito, visa, mastercard
- "transferencia": si dice transferencia, QR, Yape, Plin, MercadoPago, CBU, CVU, Bizum
- "otro": cualquier otro método no listado

Si no puedes leer el monto, usa 0.
Solo responde con el JSON."""


@app.post("/api/tickets")
async def create_ticket(file: UploadFile = File(...), db: Session = Depends(get_db)):
    image_data = await file.read()
    if not image_data:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    content_type = file.content_type or "image/jpeg"
    if content_type not in ("image/jpeg", "image/png", "image/gif", "image/webp"):
        content_type = "image/jpeg"

    base64_image = base64.standard_b64encode(image_data).decode("utf-8")

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=256,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": content_type,
                                "data": base64_image,
                            },
                        },
                        {"type": "text", "text": VISION_PROMPT},
                    ],
                }
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Error de IA: {str(e)}")

    response_text = message.content[0].text.strip()
    # Strip markdown code blocks if present
    if "```" in response_text:
        parts = response_text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("{"):
                response_text = part
                break

    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        raise HTTPException(status_code=422, detail="No se pudo interpretar la imagen como ticket")

    tipo_pago = data.get("tipo_pago", "efectivo")
    if tipo_pago not in TIPOS_PAGO:
        tipo_pago = "otro"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ext = os.path.splitext(file.filename or "ticket.jpg")[1] or ".jpg"
    image_filename = f"{timestamp}{ext}"
    image_path = os.path.join(UPLOAD_DIR, image_filename)
    with open(image_path, "wb") as f:
        f.write(image_data)

    ticket = Ticket(
        monto=float(data.get("monto", 0)),
        tipo_pago=tipo_pago,
        descripcion=str(data.get("descripcion", ""))[:200],
        imagen_path=image_filename,
        fecha=date.today(),
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)

    return _ticket_to_dict(ticket)


@app.get("/api/tickets")
async def list_tickets(db: Session = Depends(get_db)):
    tickets = (
        db.query(Ticket)
        .filter(Ticket.fecha == date.today())
        .order_by(Ticket.created_at.desc())
        .all()
    )
    return [_ticket_to_dict(t) for t in tickets]


@app.delete("/api/tickets/{ticket_id}")
async def delete_ticket(ticket_id: int, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    # Remove image file
    if ticket.imagen_path:
        path = os.path.join(UPLOAD_DIR, ticket.imagen_path)
        if os.path.exists(path):
            os.remove(path)
    db.delete(ticket)
    db.commit()
    return {"ok": True}


@app.get("/api/summary")
async def get_summary(db: Session = Depends(get_db)):
    tickets = db.query(Ticket).filter(Ticket.fecha == date.today()).all()

    totals = {"efectivo": 0.0, "tarjeta": 0.0, "transferencia": 0.0, "otro": 0.0}
    for ticket in tickets:
        tipo = ticket.tipo_pago if ticket.tipo_pago in totals else "otro"
        totals[tipo] += ticket.monto

    return {
        **totals,
        "total": sum(totals.values()),
        "cantidad_tickets": len(tickets),
    }


@app.get("/api/uploads/{filename}")
async def get_image(filename: str):
    path = os.path.join(UPLOAD_DIR, filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Imagen no encontrada")
    return FileResponse(path)


def _ticket_to_dict(ticket: Ticket) -> dict:
    return {
        "id": ticket.id,
        "monto": ticket.monto,
        "tipo_pago": ticket.tipo_pago,
        "descripcion": ticket.descripcion,
        "imagen_path": ticket.imagen_path,
        "fecha": ticket.fecha.isoformat(),
        "created_at": ticket.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Clasificación de domicilios
# ---------------------------------------------------------------------------

COLORES_VALIDOS = {"orange", "green", "blue", "purple", "pink", "yellow", "red", "teal", "indigo", "slate"}
DOMICILIO_CHUNK_SIZE = 25
MAX_DOMICILIOS = 1000


class RepartidorIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    color: str = "slate"
    zonas: str = ""


class RepartidorUpdate(BaseModel):
    nombre: str | None = None
    color: str | None = None
    zonas: str | None = None


class DomicilioUpdate(BaseModel):
    repartidor_id: int | None = None


class ZonaIn(BaseModel):
    nombre: str = Field(min_length=1, max_length=80)
    valor: float = 0.0


class ZonaUpdate(BaseModel):
    nombre: str | None = None
    valor: float | None = None


def _build_repartidores_block(repartidores: list[Repartidor]) -> str:
    if not repartidores:
        return "(No hay repartidores cargados todavía. Solo indicá la zona detectada y dejá repartidor en null.)"
    lines = [f"- {r.nombre}: cubre {r.zonas.strip() or 'sin zonas definidas'}" for r in repartidores]
    return "\n".join(lines)


def _build_zonas_block(zonas: list[Zona]) -> str:
    if not zonas:
        return "(No hay zonas configuradas todavía. Indicá vos el barrio/zona que detectes, con texto corto.)"
    return "\n".join(f"- {z.nombre}" for z in zonas)


def _classify_chunk(addresses: list[str], repartidores: list[Repartidor], zonas: list[Zona]) -> list[dict]:
    nombres_validos = {r.nombre for r in repartidores}
    addresses_block = "\n".join(f"{i}: {addr}" for i, addr in enumerate(addresses))
    prompt = f"""Sos un clasificador de domicilios de reparto.

Repartidores disponibles y las zonas que cubre cada uno:
{_build_repartidores_block(repartidores)}

Zonas configuradas (usá EXACTAMENTE uno de estos nombres cuando la dirección corresponda a alguna de ellas):
{_build_zonas_block(zonas)}

Para cada domicilio de la lista de abajo, indicá:
1. "zona": si la dirección corresponde a alguna zona configurada, usá ese nombre exacto. Si no hay zonas configuradas o ninguna corresponde, indicá el barrio/zona que detectes (texto corto, ej: "Palermo", "Centro").
2. "repartidor": a qué repartidor le corresponde según las zonas que cubre cada uno. Usá EXACTAMENTE el nombre tal cual está listado arriba, o null si no hay repartidores cargados o ninguno cubre esa zona.
3. "confianza": un número entre 0 y 1.

Domicilios (formato "índice: dirección"):
{addresses_block}

Devolvé SOLO un JSON array (sin markdown, sin explicaciones), un elemento por cada domicilio en el mismo orden:
[{{"idx": <índice>, "zona": "<zona>", "repartidor": "<nombre exacto o null>", "confianza": <0-1>}}]"""

    fallback = [{"idx": i, "zona": "", "repartidor": None, "confianza": 0.0} for i in range(len(addresses))]

    try:
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200 + len(addresses) * 60,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception:
        return fallback

    response_text = message.content[0].text.strip()
    if "```" in response_text:
        parts = response_text.split("```")
        for part in parts:
            part = part.strip()
            if part.startswith("json"):
                part = part[4:].strip()
            if part.startswith("["):
                response_text = part
                break

    try:
        results = json.loads(response_text)
    except json.JSONDecodeError:
        return fallback

    by_idx = {}
    for item in results:
        idx = item.get("idx")
        if not isinstance(idx, int):
            continue
        repartidor_nombre = item.get("repartidor")
        if repartidor_nombre not in nombres_validos:
            repartidor_nombre = None
        by_idx[idx] = {
            "idx": idx,
            "zona": str(item.get("zona", ""))[:100],
            "repartidor": repartidor_nombre,
            "confianza": float(item.get("confianza", 0) or 0),
        }

    return [by_idx.get(i, fallback[i]) for i in range(len(addresses))]


def classify_addresses(addresses: list[str], repartidores: list[Repartidor], zonas: list[Zona]) -> list[dict]:
    results = []
    for start in range(0, len(addresses), DOMICILIO_CHUNK_SIZE):
        chunk = addresses[start : start + DOMICILIO_CHUNK_SIZE]
        results.extend(_classify_chunk(chunk, repartidores, zonas))
    return results


@app.get("/api/repartidores")
async def list_repartidores(db: Session = Depends(get_db)):
    repartidores = db.query(Repartidor).order_by(Repartidor.nombre).all()
    return [_repartidor_to_dict(r) for r in repartidores]


@app.post("/api/repartidores")
async def create_repartidor(payload: RepartidorIn, db: Session = Depends(get_db)):
    color = payload.color if payload.color in COLORES_VALIDOS else "slate"
    repartidor = Repartidor(nombre=payload.nombre.strip(), color=color, zonas=payload.zonas.strip())
    db.add(repartidor)
    db.commit()
    db.refresh(repartidor)
    return _repartidor_to_dict(repartidor)


@app.patch("/api/repartidores/{repartidor_id}")
async def update_repartidor(repartidor_id: int, payload: RepartidorUpdate, db: Session = Depends(get_db)):
    repartidor = db.query(Repartidor).filter(Repartidor.id == repartidor_id).first()
    if not repartidor:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    if payload.nombre is not None:
        repartidor.nombre = payload.nombre.strip()
    if payload.color is not None and payload.color in COLORES_VALIDOS:
        repartidor.color = payload.color
    if payload.zonas is not None:
        repartidor.zonas = payload.zonas.strip()
    db.commit()
    db.refresh(repartidor)
    return _repartidor_to_dict(repartidor)


@app.delete("/api/repartidores/{repartidor_id}")
async def delete_repartidor(repartidor_id: int, db: Session = Depends(get_db)):
    repartidor = db.query(Repartidor).filter(Repartidor.id == repartidor_id).first()
    if not repartidor:
        raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    db.query(Domicilio).filter(Domicilio.repartidor_id == repartidor_id).update({"repartidor_id": None})
    db.delete(repartidor)
    db.commit()
    return {"ok": True}


@app.get("/api/zonas")
async def list_zonas(db: Session = Depends(get_db)):
    zonas = db.query(Zona).order_by(Zona.nombre).all()
    return [_zona_to_dict(z) for z in zonas]


@app.post("/api/zonas")
async def create_zona(payload: ZonaIn, db: Session = Depends(get_db)):
    zona = Zona(nombre=payload.nombre.strip(), valor=payload.valor)
    db.add(zona)
    db.commit()
    db.refresh(zona)
    return _zona_to_dict(zona)


@app.patch("/api/zonas/{zona_id}")
async def update_zona(zona_id: int, payload: ZonaUpdate, db: Session = Depends(get_db)):
    zona = db.query(Zona).filter(Zona.id == zona_id).first()
    if not zona:
        raise HTTPException(status_code=404, detail="Zona no encontrada")
    if payload.nombre is not None:
        zona.nombre = payload.nombre.strip()
    if payload.valor is not None:
        zona.valor = payload.valor
    db.commit()
    db.refresh(zona)
    return _zona_to_dict(zona)


@app.delete("/api/zonas/{zona_id}")
async def delete_zona(zona_id: int, db: Session = Depends(get_db)):
    zona = db.query(Zona).filter(Zona.id == zona_id).first()
    if not zona:
        raise HTTPException(status_code=404, detail="Zona no encontrada")
    db.delete(zona)
    db.commit()
    return {"ok": True}


@app.post("/api/domicilios/importar")
async def importar_domicilios(file: UploadFile = File(...), db: Session = Depends(get_db)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    filename = file.filename or "domicilios.csv"
    try:
        rows = parse_spreadsheet(filename, data)
    except Exception:
        raise HTTPException(status_code=422, detail="No se pudo leer la planilla. Verificá que sea un CSV o XLSX válido")

    if not rows:
        raise HTTPException(status_code=422, detail="La planilla no tiene filas con datos")
    if len(rows) > MAX_DOMICILIOS:
        raise HTTPException(status_code=422, detail=f"La planilla tiene demasiadas filas (máximo {MAX_DOMICILIOS})")

    headers = list(rows[0].keys())
    columns = detect_columns(headers)
    if not columns["direccion"]:
        exclude = {c for c in (columns["cliente"], columns["telefono"]) if c}
        columns["direccion"] = guess_address_column(headers, rows, exclude)
    if not columns["direccion"]:
        raise HTTPException(status_code=422, detail="No se pudo detectar la columna de dirección en la planilla")

    direccion_col = columns["direccion"]
    cliente_col = columns["cliente"]
    telefono_col = columns["telefono"]

    filas_validas = [row for row in rows if row.get(direccion_col, "").strip()]
    if not filas_validas:
        raise HTTPException(status_code=422, detail="No se encontraron direcciones en la columna detectada")

    repartidores = db.query(Repartidor).all()
    zonas = db.query(Zona).all()
    addresses = [row[direccion_col].strip() for row in filas_validas]
    clasificaciones = classify_addresses(addresses, repartidores, zonas)
    repartidores_by_nombre = {r.nombre: r for r in repartidores}
    valor_by_zona = {z.nombre.strip().lower(): z.valor for z in zonas}

    batch = DomicilioBatch(filename=filename, total=len(filas_validas), clasificados=0)
    db.add(batch)
    db.flush()

    clasificados = 0
    total_comision = 0.0
    for row, clasificacion in zip(filas_validas, clasificaciones):
        repartidor = repartidores_by_nombre.get(clasificacion.get("repartidor"))
        if repartidor:
            clasificados += 1
        zona_detectada = clasificacion.get("zona", "")
        valor_comision = valor_by_zona.get(zona_detectada.strip().lower(), 0.0)
        total_comision += valor_comision
        db.add(Domicilio(
            batch_id=batch.id,
            direccion=row[direccion_col].strip(),
            cliente=(row.get(cliente_col, "") if cliente_col else "").strip(),
            telefono=(row.get(telefono_col, "") if telefono_col else "").strip(),
            zona_detectada=zona_detectada,
            repartidor_id=repartidor.id if repartidor else None,
            confianza=clasificacion.get("confianza", 0.0),
            valor_comision=valor_comision,
        ))

    batch.clasificados = clasificados
    batch.total_comision = total_comision
    db.commit()
    db.refresh(batch)

    domicilios = db.query(Domicilio).filter(Domicilio.batch_id == batch.id).order_by(Domicilio.id).all()
    return {"batch": _batch_to_dict(batch), "domicilios": [_domicilio_to_dict(d) for d in domicilios]}


@app.get("/api/domicilios/batches")
async def list_batches(db: Session = Depends(get_db)):
    batches = db.query(DomicilioBatch).order_by(DomicilioBatch.created_at.desc()).all()
    return [_batch_to_dict(b) for b in batches]


@app.get("/api/domicilios/batches/{batch_id}")
async def get_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(DomicilioBatch).filter(DomicilioBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    domicilios = db.query(Domicilio).filter(Domicilio.batch_id == batch_id).order_by(Domicilio.id).all()
    return {"batch": _batch_to_dict(batch), "domicilios": [_domicilio_to_dict(d) for d in domicilios]}


@app.delete("/api/domicilios/batches/{batch_id}")
async def delete_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(DomicilioBatch).filter(DomicilioBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    db.delete(batch)
    db.commit()
    return {"ok": True}


@app.patch("/api/domicilios/{domicilio_id}")
async def update_domicilio(domicilio_id: int, payload: DomicilioUpdate, db: Session = Depends(get_db)):
    domicilio = db.query(Domicilio).filter(Domicilio.id == domicilio_id).first()
    if not domicilio:
        raise HTTPException(status_code=404, detail="Domicilio no encontrado")
    if payload.repartidor_id is not None:
        repartidor = db.query(Repartidor).filter(Repartidor.id == payload.repartidor_id).first()
        if not repartidor:
            raise HTTPException(status_code=404, detail="Repartidor no encontrado")
    domicilio.repartidor_id = payload.repartidor_id
    db.commit()
    db.refresh(domicilio)
    return _domicilio_to_dict(domicilio)


@app.get("/api/domicilios/reporte")
async def get_reporte(db: Session = Depends(get_db)):
    rows = (
        db.query(
            Domicilio.repartidor_id,
            func.count(Domicilio.id),
            func.coalesce(func.sum(Domicilio.valor_comision), 0.0),
        )
        .group_by(Domicilio.repartidor_id)
        .all()
    )
    repartidores_by_id = {r.id: r for r in db.query(Repartidor).all()}

    resultado = []
    for repartidor_id, cantidad, total_comision in rows:
        repartidor = repartidores_by_id.get(repartidor_id) if repartidor_id else None
        resultado.append({
            "repartidor_id": repartidor_id,
            "repartidor_nombre": repartidor.nombre if repartidor else "Sin asignar",
            "repartidor_color": repartidor.color if repartidor else None,
            "cantidad_domicilios": cantidad,
            "total_comision": total_comision,
        })

    resultado.sort(key=lambda r: (r["repartidor_id"] is None, -r["total_comision"]))

    return {
        "por_repartidor": resultado,
        "total_domicilios": sum(r["cantidad_domicilios"] for r in resultado),
        "total_comision": sum(r["total_comision"] for r in resultado),
    }


@app.get("/api/domicilios/batches/{batch_id}/export")
async def export_batch(batch_id: int, db: Session = Depends(get_db)):
    batch = db.query(DomicilioBatch).filter(DomicilioBatch.id == batch_id).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Lote no encontrado")
    domicilios = (
        db.query(Domicilio)
        .filter(Domicilio.batch_id == batch_id)
        .order_by(Domicilio.repartidor_id.is_(None), Domicilio.zona_detectada)
        .all()
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["direccion", "cliente", "telefono", "zona", "repartidor", "confianza", "comision"])
    for d in domicilios:
        writer.writerow([
            d.direccion,
            d.cliente,
            d.telefono,
            d.zona_detectada,
            d.repartidor.nombre if d.repartidor else "Sin asignar",
            f"{d.confianza:.2f}",
            f"{d.valor_comision:.2f}",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="domicilios_{batch_id}.csv"'},
    )


def _repartidor_to_dict(r: Repartidor) -> dict:
    return {"id": r.id, "nombre": r.nombre, "color": r.color, "zonas": r.zonas}


def _zona_to_dict(z: Zona) -> dict:
    return {"id": z.id, "nombre": z.nombre, "valor": z.valor}


def _batch_to_dict(b: DomicilioBatch) -> dict:
    return {
        "id": b.id,
        "filename": b.filename,
        "total": b.total,
        "clasificados": b.clasificados,
        "total_comision": b.total_comision,
        "created_at": b.created_at.isoformat(),
    }


def _domicilio_to_dict(d: Domicilio) -> dict:
    return {
        "id": d.id,
        "batch_id": d.batch_id,
        "direccion": d.direccion,
        "cliente": d.cliente,
        "telefono": d.telefono,
        "zona_detectada": d.zona_detectada,
        "repartidor_id": d.repartidor_id,
        "repartidor_nombre": d.repartidor.nombre if d.repartidor else None,
        "repartidor_color": d.repartidor.color if d.repartidor else None,
        "confianza": d.confianza,
        "valor_comision": d.valor_comision,
        "created_at": d.created_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# Frontend estático (build de producción), servido por este mismo backend
# ---------------------------------------------------------------------------

FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "static")

if os.path.isdir(FRONTEND_DIST):
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        candidate = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(candidate):
            return FileResponse(candidate)
        return FileResponse(os.path.join(FRONTEND_DIST, "index.html"))
