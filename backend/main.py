import base64
import json
import os
from datetime import date, datetime

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from models import Ticket, get_db, init_db

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
