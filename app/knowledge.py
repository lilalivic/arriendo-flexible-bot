"""
Búsqueda en la base de conocimiento (RAG).
Encuentra intercambios similares del historial de chats para dar contexto al bot.
"""
import chromadb
from chromadb.utils import embedding_functions
from app.config import DB_DIR


_client = None
_collection = None


def _get_collection():
    global _client, _collection
    if _collection is None:
        _client = chromadb.PersistentClient(path=DB_DIR)
        ef = embedding_functions.DefaultEmbeddingFunction()
        _collection = _client.get_or_create_collection(
            name="arriendo_flexible_chats",
            embedding_function=ef,
            metadata={"hnsw:space": "cosine"}
        )
    return _collection


def find_similar_exchanges(query: str, n_results: int = 5) -> list[dict]:
    """
    Busca los intercambios más similares al mensaje del cliente.
    Retorna lista de ejemplos con client_message y marcela_response.
    """
    collection = _get_collection()
    count = collection.count()
    if count == 0:
        return []

    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, count)
    )

    exchanges = []
    if results and results.get("metadatas"):
        for meta in results["metadatas"][0]:
            exchanges.append({
                "client_message": meta.get("client_message", ""),
                "marcela_response": meta.get("marcela_response", ""),
                "client_name": meta.get("client_name", "")
            })
    return exchanges
