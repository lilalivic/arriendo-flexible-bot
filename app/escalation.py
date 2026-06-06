"""
Sistema de escalación invisible.
Cuando el bot no puede resolver algo, notifica a Marcela por Telegram
y envía un mensaje puente al cliente para ganar tiempo.
"""
import httpx
from app.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

ESCALATION_KEYWORDS = [
    "problema", "reclamo", "queja", "molest", "enojad", "furioso",
    "legal", "abogado", "tribunal", "denuncia", "multa",
    "gotera", "gotear", "inundación", "inundacion", "incendio", "robo",
    "daño", "daños", "accidente", "emergencia", "urgente",
    "no funciona", "roto", "rota", "descompuesto", "se rompió", "se rompio",
    "no pago", "no puedo pagar", "sin dinero", "dificultad",
    "me voy", "me retiro", "abandono", "terminar contrato", "termino contrato",
    "devolver", "garantía", "garantia", "me voy a ir", "quiero salir",
]

PHYSICAL_PROBLEM_KEYWORDS = [
    "gotera", "gotear", "inundación", "inundacion", "incendio",
    "no funciona", "roto", "rota", "descompuesto", "se rompió", "se rompio",
    "daño", "daños", "accidente", "filtración", "filtracion",
]


def should_escalate(message: str) -> bool:
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in ESCALATION_KEYWORDS)


def is_physical_problem(message: str) -> bool:
    msg_lower = message.lower()
    return any(kw in msg_lower for kw in PHYSICAL_PROBLEM_KEYWORDS)


def get_bridge_message(client_name: str, message: str) -> str:
    first_name = client_name.split()[0] if client_name else ""
    greeting = f"{first_name}, " if first_name else ""
    if is_physical_problem(message):
        return f"{greeting}dame un momento que lo reviso. Mientras tanto, ¿puedes enviarme fotos o un video del problema?"
    return f"{greeting}déjame revisar tu caso y te respondo en unos minutos."


async def notify_marcela(
    client_name: str,
    client_phone: str,
    client_message: str,
    conversation_context: str
) -> bool:
    """Envía alerta a Marcela por Telegram con todo el contexto."""
    text = (
        f"🔔 ESCALACION REQUERIDA\n\n"
        f"Cliente: {client_name}\n"
        f"Telefono: {client_phone}\n\n"
        f"Mensaje del cliente:\n{client_message}\n\n"
        f"Contexto reciente:\n{conversation_context}\n\n"
        f"Tienes 30 minutos para responder."
    )

    async with httpx.AsyncClient() as http:
        resp = await http.post(
            f"{TELEGRAM_API}/sendMessage",
            json={
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text,
            }
        )
        return resp.status_code == 200
