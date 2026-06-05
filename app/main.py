"""
Backend principal — FastAPI con webhook de Meta WhatsApp Business API.
"""
import httpx
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.responses import PlainTextResponse

from app.config import META_VERIFY_TOKEN, META_ACCESS_TOKEN, META_PHONE_NUMBER_ID
from app.bot import generate_response
from app.escalation import should_escalate, get_bridge_message, notify_marcela

app = FastAPI(title="ArriendoFlexible Bot")

conversation_history: dict[str, list[dict]] = {}

META_MESSAGES_URL = f"https://graph.facebook.com/v20.0/{META_PHONE_NUMBER_ID}/messages"


# ── Webhook verification (Meta lo llama una vez para verificar la URL) ──────
@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == META_VERIFY_TOKEN:
        return PlainTextResponse(hub_challenge)
    raise HTTPException(status_code=403, detail="Token inválido")


# ── Webhook receptor de mensajes ─────────────────────────────────────────────
@app.post("/webhook")
async def receive_message(request: Request):
    body = await request.json()

    try:
        entry = body["entry"][0]
        changes = entry["changes"][0]
        value = changes["value"]

        if "messages" not in value:
            return {"status": "no_message"}

        message = value["messages"][0]
        msg_type = message.get("type")

        if msg_type != "text":
            return {"status": "non_text_ignored"}

        client_phone = message["from"]
        client_text = message["text"]["body"]

        contacts = value.get("contacts", [{}])
        client_name = contacts[0].get("profile", {}).get("name", client_phone)

        history = conversation_history.get(client_phone, [])

        if should_escalate(client_text):
            bridge = get_bridge_message(client_name)
            await send_whatsapp_message(client_phone, bridge)

            context_summary = _build_context_summary(history, client_text)
            await notify_marcela(client_name, client_phone, client_text, context_summary)
            return {"status": "escalated"}

        response_text = generate_response(client_text, client_name, history)

        history.append({"role": "user", "content": client_text})
        history.append({"role": "assistant", "content": response_text})
        conversation_history[client_phone] = history[-20:]

        parts = [p.strip() for p in response_text.split("|") if p.strip()]
        for part in parts:
            await send_whatsapp_message(client_phone, part)

        return {"status": "ok"}

    except (KeyError, IndexError):
        return {"status": "ignored"}


async def send_whatsapp_message(to: str, text: str):
    headers = {
        "Authorization": f"Bearer {META_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text}
    }
    async with httpx.AsyncClient() as client:
        await client.post(META_MESSAGES_URL, json=payload, headers=headers)


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
