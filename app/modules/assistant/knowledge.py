import re
from collections.abc import Callable
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_core.vectorstores import VectorStore
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.core.config import settings
from app.domain.entities import MenuItem
from app.modules.assistant.llm import embeddings

COLLECTION = "sirius_knowledge"
FAQ_PATH = Path(__file__).with_name("faq.md")


def menu_documents(items: list[MenuItem]) -> list[Document]:
    return [
        Document(
            page_content=f"Блюдо «{item.name}», цена {item.price:.0f} ₽, {'есть в наличии' if item.is_available else 'нет в наличии'}.",
            metadata={"source": "menu", "item_id": item.id},
        )
        for item in items
    ]


def faq_documents(text: str) -> list[Document]:
    sections = [section.strip() for section in re.split(r"^# ", text, flags=re.MULTILINE) if section.strip()]
    return [
        Document(page_content=f"{title}. {body.strip()}", metadata={"source": "faq", "topic": title})
        for title, _, body in (section.partition("\n") for section in sections)
    ]


class KnowledgeBase:
    def __init__(self, store: Callable[[], VectorStore]):
        self.store = store

    def search(self, query: str, k: int = 4) -> list[Document]:
        return self.store().similarity_search(query, k=k)


@lru_cache
def qdrant_store() -> VectorStore:
    return QdrantVectorStore(client=QdrantClient(url=settings.QDRANT_URL), collection_name=COLLECTION, embedding=embeddings())


qdrant_knowledge_base = KnowledgeBase(qdrant_store)


def reindex(items: list[MenuItem]) -> int:
    documents = menu_documents(items) + faq_documents(FAQ_PATH.read_text(encoding="utf-8"))
    QdrantVectorStore.from_documents(
        documents,
        embeddings(),
        url=settings.QDRANT_URL,
        collection_name=COLLECTION,
        force_recreate=True,
    )
    return len(documents)

