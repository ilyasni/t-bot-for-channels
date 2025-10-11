"""
Конфигурация RAG Service
"""
import os
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

# ============================================================================
# Server Configuration
# ============================================================================
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8020"))

# ============================================================================
# Database Configuration
# ============================================================================
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./data/telethon_bot.db"
)

# ============================================================================
# Qdrant Configuration
# ============================================================================
QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
QDRANT_EXTERNAL_URL = os.getenv("QDRANT_EXTERNAL_URL", "https://qdrant.produman.studio")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
QDRANT_TIMEOUT = int(os.getenv("QDRANT_TIMEOUT", "60"))

# ============================================================================
# Embeddings Configuration
# ============================================================================
# Основной провайдер: gpt2giga (GigaChat)
GIGACHAT_PROXY_URL = os.getenv("GIGACHAT_PROXY_URL", "http://gpt2giga-proxy:8090")
GIGACHAT_ENABLED = os.getenv("GIGACHAT_ENABLED", "true").lower() == "true"

# Fallback провайдер: sentence-transformers
EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL",
    "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
)
EMBEDDING_BATCH_SIZE = int(os.getenv("EMBEDDING_BATCH_SIZE", "32"))

# Chunking стратегия
# Для EmbeddingsGigaR: до 4096 токенов
EMBEDDING_MAX_TOKENS_GIGACHAT = int(os.getenv("EMBEDDING_MAX_TOKENS_GIGACHAT", "1536"))
EMBEDDING_OVERLAP_TOKENS_GIGACHAT = int(os.getenv("EMBEDDING_OVERLAP_TOKENS_GIGACHAT", "256"))

# Для sentence-transformers: до 512 токенов
EMBEDDING_MAX_TOKENS_FALLBACK = int(os.getenv("EMBEDDING_MAX_TOKENS_FALLBACK", "384"))
EMBEDDING_OVERLAP_TOKENS_FALLBACK = int(os.getenv("EMBEDDING_OVERLAP_TOKENS_FALLBACK", "64"))

# ============================================================================
# LLM Configuration (для RAG-генерации)
# ============================================================================
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

# ============================================================================
# RAG Settings
# ============================================================================
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "10"))
RAG_MIN_SCORE = float(os.getenv("RAG_MIN_SCORE", "0.7"))
RAG_CONTEXT_WINDOW = int(os.getenv("RAG_CONTEXT_WINDOW", "4000"))
RAG_TEMPERATURE = float(os.getenv("RAG_TEMPERATURE", "0.3"))

# ============================================================================
# Digest Settings
# ============================================================================
DIGEST_DEFAULT_TIME = os.getenv("DIGEST_DEFAULT_TIME", "09:00")
DIGEST_MAX_POSTS = int(os.getenv("DIGEST_MAX_POSTS", "200"))  # Увеличено для активных пользователей
DIGEST_SUMMARY_LENGTH = os.getenv("DIGEST_SUMMARY_LENGTH", "short")  # short, medium, detailed

# ============================================================================
# AI Digest Settings
# ============================================================================
AI_DIGEST_ENABLED = os.getenv("AI_DIGEST_ENABLED", "true").lower() == "true"
GIGACHAT_MODEL = os.getenv("GIGACHAT_MODEL", "GigaChat")  # GigaChat или GigaChatMAX
DIGEST_AI_TEMPERATURE = float(os.getenv("DIGEST_AI_TEMPERATURE", "0.3"))
DIGEST_POSTS_PER_TOPIC = int(os.getenv("DIGEST_POSTS_PER_TOPIC", "10"))  # Постов для анализа на тему
QUERY_HISTORY_DAYS = int(os.getenv("QUERY_HISTORY_DAYS", "30"))  # Анализ запросов за N дней

# ============================================================================
# Service Settings
# ============================================================================
RAG_SERVICE_ENABLED = os.getenv("RAG_SERVICE_ENABLED", "true").lower() == "true"

# Timezone
TZ = os.getenv("TZ", "Europe/Moscow")

# Logging
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

