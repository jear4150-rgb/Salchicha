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
from sqlalchemy.orm import Session

from models import Domicilio, DomicilioBatch, Repartidor, Ticket, get_db, init_db
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


def _build_repartidores_block(repartidores: list[Repartidor]) -> str:
    if not repartidores:
        return "(No hay repartidores cargados todavía. Solo indicá la zona detectada y dejá repartidor en null.)"
    lines = [f"- {r.nombre}: cubre {r.zonas.strip() or 'sin zonas definidas'}" for r in repartidores]
    return "\n".join(lines)


def _classify_chunk(addresses: list[str], repartidores: list[Repartidor]) -> list[dict]:
    nombres_validos = {r.nombre for r in repartidores}
    addresses_block = "\n".join(f"{i}: {addr}" for i, addr in enumerate(addresses))
    prompt = f"""Sos un clasificador de domicilios de reparto.

Repartidores disponibles y las zonas que cubre cada uno:
{_build_repartidores_block(repartidores)}

Para cada domicilio de la lista de abajo, indicá:
1. "zona": el barrio/zona detectado en la dirección (texto corto, ej: "Palermo", "Centro").
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


def classify_addresses(addresses: list[str], repartidores: list[Repartidor]) -> list[dict]:
    results = []
    for start in range(0, len(addresses), DOMICILIO_CHUNK_SIZE):
        chunk = addresses[start : start + DOMICILIO_CHUNK_SIZE]
        results.extend(_classify_chunk(chunk, repartidores))
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
    addresses = [row[direccion_col].strip() for row in filas_validas]
    clasificaciones = classify_addresses(addresses, repartidores)
    repartidores_by_nombre = {r.nombre: r for r in repartidores}

    batch = DomicilioBatch(filename=filename, total=len(filas_validas), clasificados=0)
    db.add(batch)
    db.flush()

    clasificados = 0
    for row, clasificacion in zip(filas_validas, clasificaciones):
        repartidor = repartidores_by_nombre.get(clasificacion.get("repartidor"))
        if repartidor:
            clasificados += 1
        db.add(Domicilio(
            batch_id=batch.id,
            direccion=row[direccion_col].strip(),
            cliente=(row.get(cliente_col, "") if cliente_col else "").strip(),
            telefono=(row.get(telefono_col, "") if telefono_col else "").strip(),
            zona_detectada=clasificacion.get("zona", ""),
            repartidor_id=repartidor.id if repartidor else None,
            confianza=clasificacion.get("confianza", 0.0),
        ))

    batch.clasificados = clasificados
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
    writer.writerow(["direccion", "cliente", "telefono", "zona", "repartidor", "confianza"])
    for d in domicilios:
        writer.writerow([
            d.direccion,
            d.cliente,
            d.telefono,
            d.zona_detectada,
            d.repartidor.nombre if d.repartidor else "Sin asignar",
            f"{d.confianza:.2f}",
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="domicilios_{batch_id}.csv"'},
    )


def _repartidor_to_dict(r: Repartidor) -> dict:
    return {"id": r.id, "nombre": r.nombre, "color": r.color, "zonas": r.zonas}


def _batch_to_dict(b: DomicilioBatch) -> dict:
    return {
        "id": b.id,
        "filename": b.filename,
        "total": b.total,
        "clasificados": b.clasificados,
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
        "created_at": d.created_at.isoformat(),
    }
