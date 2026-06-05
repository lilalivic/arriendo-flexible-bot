"""
Script de ejecución única para procesar los chats de WhatsApp
y cargarlos en la base de conocimiento (ChromaDB).

Uso: python scripts/process_chats.py
"""
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from chromadb.utils import embedding_functions

CHATS_DIR = Path(__file__).parent.parent.parent / "chats_extraidos"
DB_DIR = Path(__file__).parent.parent / "data" / "chats"

LINE_RE = re.compile(
    r"\[(\d{2}-\d{2}-\d{2}), (\d{2}:\d{2}:\d{2})\] ([^:]+): (.+)"
)

SKIP_PATTERNS = [
    "omitido", "cifrado de extremo", "es un contacto",
    "Llamada perdida", "Videollamada perdida", "Eliminaste este mensaje",
    "Los mensajes y las llamadas"
]


def parse_chat(filepath: Path) -> list[dict]:
    """Parsea un archivo _chat.txt y retorna lista de mensajes limpios."""
    messages = []
    try:
        text = filepath.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = filepath.read_text(encoding="latin-1")

    for line in text.splitlines():
        m = LINE_RE.match(line.strip())
        if not m:
            continue
        date, time, sender, content = m.groups()
        content = content.strip()
        if any(p.lower() in content.lower() for p in SKIP_PATTERNS):
            continue
        if not content or content == "\u200E":
            continue
        messages.append({
            "date": date,
            "time": time,
            "sender": sender.strip(),
            "content": content,
            "is_marcela": "Marcela Radonic" in sender
        })
    return messages


def build_exchanges(messages: list[dict], client_name: str) -> list[dict]:
    """
    Agrupa mensajes en intercambios (pregunta/problema del cliente + respuesta de Marcela).
    Cada exchange es un documento para RAG.
    """
    exchanges = []
    i = 0
    while i < len(messages):
        msg = messages[i]
        if not msg["is_marcela"]:
            # Agrupa mensajes consecutivos del cliente
            client_msgs = []
            while i < len(messages) and not messages[i]["is_marcela"]:
                client_msgs.append(messages[i]["content"])
                i += 1
            # Agrupa respuestas consecutivas de Marcela
            marcela_msgs = []
            while i < len(messages) and messages[i]["is_marcela"]:
                marcela_msgs.append(messages[i]["content"])
                i += 1
            if marcela_msgs:
                exchanges.append({
                    "client_message": " | ".join(client_msgs),
                    "marcela_response": " | ".join(marcela_msgs),
                    "client_name": client_name,
                    "date": msg["date"]
                })
        else:
            i += 1
    return exchanges


def main():
    print("Iniciando procesamiento de chats...")

    client = chromadb.PersistentClient(path=str(DB_DIR))

    ef = embedding_functions.DefaultEmbeddingFunction()

    collection = client.get_or_create_collection(
        name="arriendo_flexible_chats",
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"}
    )

    total_exchanges = 0
    chat_dirs = [d for d in CHATS_DIR.iterdir() if d.is_dir()]

    for chat_dir in sorted(chat_dirs):
        chat_file = chat_dir / "_chat.txt"
        if not chat_file.exists():
            continue

        client_name = chat_dir.name.replace("WhatsApp Chat - ", "").replace("Copia de WhatsApp Chat - ", "")
        messages = parse_chat(chat_file)
        exchanges = build_exchanges(messages, client_name)

        if not exchanges:
            print(f"  Sin intercambios: {client_name}")
            continue

        documents = []
        metadatas = []
        ids = []

        for j, ex in enumerate(exchanges):
            doc_id = f"{chat_dir.name}_{j}"
            document = f"Cliente: {ex['client_message']}\nRespuesta: {ex['marcela_response']}"
            documents.append(document)
            metadatas.append({
                "client_name": client_name,
                "date": ex["date"],
                "client_message": ex["client_message"][:200],
                "marcela_response": ex["marcela_response"][:500]
            })
            ids.append(doc_id)

        collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
        total_exchanges += len(exchanges)
        print(f"  OK {client_name}: {len(exchanges)} intercambios")

    print(f"\nTotal cargado: {total_exchanges} intercambios en ChromaDB")
    print(f"Base de conocimiento lista en: {DB_DIR}")


if __name__ == "__main__":
    main()
