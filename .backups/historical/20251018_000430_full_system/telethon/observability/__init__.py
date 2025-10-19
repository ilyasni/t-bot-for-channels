"""
Observability модули для Telegram Bot

Компоненты:
- langfuse_client: AI tracing для OpenRouter, GigaChat, RAG
- metrics: Prometheus метрики для RAG и parsing
"""

from .langfuse_client import langfuse_client
from .metrics import (
    # RAG Metrics
    rag_search_duration_seconds,
    rag_embeddings_duration_seconds,
    rag_query_errors_total,
    # Parsing Metrics
    parsing_queue_size,
    posts_parsed_total,
)

__all__ = [
    "langfuse_client",
    "rag_search_duration_seconds",
    "rag_embeddings_duration_seconds",
    "rag_query_errors_total",
    "parsing_queue_size",
    "posts_parsed_total",
]

