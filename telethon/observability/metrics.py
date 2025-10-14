"""
Prometheus metrics для Telegram Bot

Best practices from Context7 (/prometheus/client_python):
- Counter для монотонно возрастающих значений (requests, errors)
- Histogram для latency measurements с правильными buckets
- Gauge для текущих значений (queue size)
- Labels для группировки метрик (provider, user_id, error_type)

Metrics экспортируются на /metrics endpoint (FastAPI + make_asgi_app)
"""
from prometheus_client import Counter, Histogram, Gauge
import os
import logging

logger = logging.getLogger(__name__)

# Проверяем включен ли Prometheus
ENABLED = os.getenv("PROMETHEUS_METRICS_ENABLED", "true").lower() == "true"

if not ENABLED:
    logger.info("⚠️ Prometheus metrics disabled (PROMETHEUS_METRICS_ENABLED=false)")

# ============================================================================
# RAG Metrics (Vector Search & Embeddings)
# ============================================================================

rag_search_duration_seconds = Histogram(
    'rag_search_duration_seconds',
    'RAG vector search latency in Qdrant',
    buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)
"""
Latency поиска в Qdrant

Buckets:
- 50ms - очень быстрый поиск
- 100ms - нормальный
- 200ms - медленный
- 500ms+ - требует оптимизации

Example:
    with rag_search_duration_seconds.time():
        results = await qdrant_search(query)
"""

rag_embeddings_duration_seconds = Histogram(
    'rag_embeddings_duration_seconds',
    'Embeddings generation latency',
    ['provider'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
)
"""
Latency генерации embeddings

Labels:
- provider: Провайдер (gigachat, openai, local)

Buckets:
- 100ms - очень быстро
- 500ms - нормально
- 1s - медленно
- 2s+ - требует оптимизации

Example:
    with rag_embeddings_duration_seconds.labels(provider='gigachat').time():
        embeddings = await create_embeddings(text)
"""

rag_query_errors_total = Counter(
    'rag_query_errors_total',
    'Total RAG query errors',
    ['error_type']
)
"""
Счетчик ошибок RAG

Labels:
- error_type: Тип ошибки (qdrant_timeout, embedding_failed, no_results, api_error)

Example:
    try:
        results = await search(query)
    except TimeoutError:
        rag_query_errors_total.labels(error_type='qdrant_timeout').inc()
"""

# ============================================================================
# Parsing Metrics
# ============================================================================

parsing_queue_size = Gauge(
    'bot_parsing_queue_size',
    'Number of channels in parsing queue'
)
"""
Размер очереди парсинга (сколько каналов ждут обработки)

Example:
    parsing_queue_size.set(len(channels_to_parse))
    
    # Или increment/decrement:
    parsing_queue_size.inc()  # Добавлен в очередь
    parsing_queue_size.dec()  # Удален из очереди
"""

posts_parsed_total = Counter(
    'bot_posts_parsed_total',
    'Total posts parsed from Telegram channels',
    ['user_id']
)
"""
Счетчик спарсенных постов

Labels:
- user_id: ID пользователя (для отслеживания активности)

Example:
    posts_parsed_total.labels(user_id=str(user_id)).inc(5)  # Добавлено 5 постов
"""

# ============================================================================
# Helper Functions
# ============================================================================

def log_metric_error(metric_name: str, error: Exception):
    """
    Логирование ошибок при обновлении метрик
    
    Args:
        metric_name: Имя метрики
        error: Исключение
    """
    logger.error(f"❌ Prometheus metric '{metric_name}' update error: {error}")


# ============================================================================
# Startup/Shutdown
# ============================================================================

def init_metrics():
    """
    Инициализация метрик при запуске приложения
    
    Вызывается из FastAPI startup event
    """
    if ENABLED:
        logger.info("✅ Prometheus metrics initialized")
        logger.info(f"   RAG metrics: search_duration, embeddings_duration, query_errors")
        logger.info(f"   Parsing metrics: queue_size, posts_parsed")
    else:
        logger.info("⚠️ Prometheus metrics disabled")


# Автоинициализация при импорте
init_metrics()

