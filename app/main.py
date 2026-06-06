"""
Backend principal — FastAPI con webhook de Twilio WhatsApp.
"""
from fastapi import FastAPI, Request, Form
from fastapi.responses import PlainTextResponse
from typing import Optional

from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER
from app.bot import generate_response
from app.escalation import should_escalate, get_bridge_message, notify_marcela

import httpx
from base64 import b64encode

app = FastAPI(title="ArriendoFlexible Bot")

conversation_history: dict[str, list[dict]] = {}

TWILIO_MESSAGES_URL = f"https://api.twilio.com/2010-04-01/Accounts/{TWILIO_ACCOUNT_SID}/Messages.json"


@app.post("/webhook")
async def receive_message(
    From: Optional[str] = Form(None),
    Body: Optional[str] = Form(None),
    ProfileName: Optional[str] = Form(None),
):
    if not From or not Body:
        return PlainTextResponse("")

    client_phone = From
    client_text = Body.strip()
    client_name = ProfileName or From

    history = conversation_history.get(client_phone, [])

    if should_escalate(client_text):
        bridge = get_bridge_message(client_name, client_text)
        await send_whatsapp_message(client_phone, bridge)
        context_summary = _build_context_summary(history, client_text)
        await notify_marcela(client_name, client_phone, client_text, context_summary)
        return PlainTextResponse("")

    response_text = generate_response(client_text, client_name, history)

    history.append({"role": "user", "content": client_text})
    history.append({"role": "assistant", "content": response_text})
    conversation_history[client_phone] = history[-20:]

    parts = [p.strip() for p in response_text.split("|") if p.strip()]
    for part in parts:
        await send_whatsapp_message(client_phone, part)

    return PlainTextResponse("")


async def send_whatsapp_message(to: str, text: str):
    credentials = b64encode(f"{TWILIO_ACCOUNT_SID}:{TWILIO_AUTH_TOKEN}".encode()).decode()
    to_number = to if to.startswith("whatsapp:") else f"whatsapp:{to}"
    from_number = TWILIO_WHATSAPP_NUMBER if TWILIO_WHATSAPP_NUMBER.startswith("whatsapp:") else f"whatsapp:{TWILIO_WHATSAPP_NUMBER}"

    async with httpx.AsyncClient() as client:
        await client.post(
            TWILIO_MESSAGES_URL,
            data={"From": from_number, "To": to_number, "Body": text},
            headers={"Authorization": f"Basic {credentials}"}
        )


def _build_context_summary(history: list[dict], latest_message: str) -> str:
    if not history:
        return f"Primer mensaje del cliente: {latest_message}"
    recent = history[-4:]
    lines = []
    for msg in recent:
        role = "Cliente" if msg["role"] == "user" else "Marcela"
        lines.append(f"{role}: {msg['content'][:100]}")
    lines.append(f"Cliente (ahora): {latest_message}")
    return "\n".join(lines)


@app.get("/health")
async def health():
    return {"status": "ok", "service": "ArriendoFlexible Bot"}
