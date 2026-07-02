import base64
import json
import os
from datetime import date, datetime

import anthropic
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session

import whatsapp as wa
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

TIPO_LABELS = {
    "efectivo": "Efectivo 💵",
    "tarjeta": "Tarjeta 💳",
    "transferencia": "Transferencia 📱",
    "otro": "Otro 💰",
}


class TicketProcessingError(Exception):
    pass


async def _extract_ticket_data(image_data: bytes, content_type: str) -> dict:
    """Envía la imagen a Claude y devuelve los datos del ticket extraídos."""
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
        raise TicketProcessingError(f"Error de IA: {str(e)}")

    response_text = message.content[0].text.strip()
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
        return json.loads(response_text)
    except json.JSONDecodeError:
        raise TicketProcessingError("No se pudo interpretar la imagen como ticket")


def _save_ticket(image_data: bytes, data: dict, original_filename: str, db: Session) -> Ticket:
    """Guarda la imagen y los datos del ticket en la base de datos."""
    tipo_pago = data.get("tipo_pago", "efectivo")
    if tipo_pago not in TIPOS_PAGO:
        tipo_pago = "otro"

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    ext = os.path.splitext(original_filename)[1] or ".jpg"
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
    return ticket


@app.post("/api/tickets")
async def create_ticket(file: UploadFile = File(...), db: Session = Depends(get_db)):
    image_data = await file.read()
    if not image_data:
        raise HTTPException(status_code=400, detail="Archivo vacío")

    content_type = file.content_type or "image/jpeg"

    try:
        data = await _extract_ticket_data(image_data, content_type)
    except TicketProcessingError as e:
        msg = str(e)
        if "IA" in msg:
            raise HTTPException(status_code=503, detail=msg)
        raise HTTPException(status_code=422, detail=msg)

    ticket = _save_ticket(image_data, data, file.filename or "ticket.jpg", db)
    return _ticket_to_dict(ticket)


@app.post("/api/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """Webhook de Twilio: recibe fotos de tickets por WhatsApp y los registra."""
    form = await request.form()
    num_media = int(form.get("NumMedia", "0"))

    if num_media == 0:
        msg = "Para registrar un ticket, enviá una foto del remito/comprobante. 📸"
        return Response(content=wa.twiml_reply(msg), media_type="application/xml")

    media_url = str(form.get("MediaUrl0", ""))
    media_type = str(form.get("MediaContentType0", "image/jpeg"))

    try:
        image_data, content_type = await wa.download_media(media_url)
    except Exception:
        msg = "No pude descargar la imagen. Por favor intentá de nuevo. 🔄"
        return Response(content=wa.twiml_reply(msg), media_type="application/xml")

    try:
        data = await _extract_ticket_data(image_data, content_type or media_type)
    except TicketProcessingError:
        msg = "No pude leer el ticket. Asegurate de que la foto sea clara y el ticket esté completo. 📋"
        return Response(content=wa.twiml_reply(msg), media_type="application/xml")

    ticket = _save_ticket(image_data, data, "whatsapp_ticket.jpg", db)

    tipo_label = TIPO_LABELS.get(ticket.tipo_pago, ticket.tipo_pago)
    reply = (
        f"✅ Ticket registrado\n"
        f"💰 Monto: ${ticket.monto:,.2f}\n"
        f"💳 Pago: {tipo_label}\n"
        f"📝 {ticket.descripcion}"
    )
    return Response(content=wa.twiml_reply(reply), media_type="application/xml")


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
