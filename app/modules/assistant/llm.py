from functools import lru_cache

from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from app.core.config import settings


@lru_cache
def chat_model() -> ChatOpenAI:
    return ChatOpenAI(
        model=settings.ASSISTANT_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        temperature=0.2,
        timeout=settings.ASSISTANT_TIMEOUT_SECONDS,
        max_retries=1,
    )


@lru_cache
def embeddings() -> OpenAIEmbeddings:
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        api_key=settings.OPENROUTER_API_KEY,
        base_url=settings.OPENROUTER_BASE_URL,
        check_embedding_ctx_length=False,
    )
