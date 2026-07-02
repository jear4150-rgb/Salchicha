import os

import httpx

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")


async def download_media(media_url: str) -> tuple[bytes, str]:
    """Descarga una imagen del servidor de Twilio y devuelve (bytes, content_type)."""
    async with httpx.AsyncClient() as client:
        r = await client.get(
            media_url,
            auth=(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN),
            follow_redirects=True,
            timeout=30.0,
        )
        r.raise_for_status()
        content_type = r.headers.get("content-type", "image/jpeg").split(";")[0].strip()
        return r.content, content_type


def twiml_reply(body: str) -> str:
    """Genera una respuesta TwiML con un mensaje de WhatsApp."""
    safe = body.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<Response>\n"
        f"  <Message>{safe}</Message>\n"
        "</Response>"
    )
