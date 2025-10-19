"""
Prometheus Metrics для Graph-Enhanced RAG

Best practices:
- Используем Counter, Histogram, Gauge из prometheus_client
- Labeling для детальной аналитики
- Graceful degradation (работает без Prometheus)
"""
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy import Prometheus (может быть недоступен)
try:
    from prometheus_client import Counter, Histogram, Gauge, Summary
    PROMETHEUS_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ prometheus_client not installed, metrics disabled")
    PROMETHEUS_AVAILABLE = False
    Counter = Histogram = Gauge = Summary = None


# ========================================
# Graph Query Metrics
# ========================================

if PROMETHEUS_AVAILABLE:
    # Latency для graph queries
    graph_query_latency = Histogram(
        'graph_query_latency_seconds',
        'Neo4j graph query latency',
        ['query_type'],  # get_post_context, get_trending_tags, expand_with_graph
        buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
    )
    
    # Graph availability (0/1)
    graph_availability = Gauge(
        'graph_availability',
        'Neo4j graph availability (1=up, 0=down)'
    )
    
    # Graph query errors
    graph_query_errors_total = Counter(
        'graph_query_errors_total',
        'Total graph query errors',
        ['query_type', 'error_type']
    )
    
    # Cache metrics
    graph_cache_hits_total = Counter(
        'graph_cache_hits_total',
        'Graph cache hit rate',
        ['cache_type']  # interests, trending, post_context
    )
    
    graph_cache_misses_total = Counter(
        'graph_cache_misses_total',
        'Graph cache misses',
        ['cache_type']
    )
else:
    # Mock metrics (noop)
    graph_query_latency = None
    graph_availability = None
    graph_query_errors_total = None
    graph_cache_hits_total = None
    graph_cache_misses_total = None


# ========================================
# Hybrid Search Metrics
# ========================================

if PROMETHEUS_AVAILABLE:
    # Hybrid search latency
    hybrid_search_duration_seconds = Histogram(
        'hybrid_search_duration_seconds',
        'Hybrid search total duration',
        buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0, 5.0]
    )
    
    # Hybrid search quality (precision estimation)
    hybrid_search_results_total = Counter(
        'hybrid_search_results_total',
        'Total hybrid search results returned',
        ['search_mode']  # hybrid, fallback_vector_only
    )
    
    # Graph expansion stats
    graph_expansion_added_docs = Summary(
        'graph_expansion_added_docs',
        'Number of additional documents added via graph expansion'
    )
    
    # Combined score distribution
    combined_score_distribution = Histogram(
        'combined_score_distribution',
        'Distribution of combined scores',
        buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
    )
else:
    # Mock metrics
    hybrid_search_duration_seconds = None
    hybrid_search_results_total = None
    graph_expansion_added_docs = None
    combined_score_distribution = None


# ========================================
# Data Retention Metrics
# ========================================

if PROMETHEUS_AVAILABLE:
    # Cleanup operations
    data_cleanup_total = Counter(
        'data_cleanup_total',
        'Total data cleanup operations',
        ['database', 'status']  # postgres/neo4j/qdrant, success/failed
    )
    
    # Cleanup duration
    data_cleanup_duration_seconds = Histogram(
        'data_cleanup_duration_seconds',
        'Data cleanup operation duration',
        ['database'],
        buckets=[1, 5, 10, 30, 60, 120, 300, 600]
    )
    
    # Records deleted
    data_cleanup_records_deleted = Counter(
        'data_cleanup_records_deleted_total',
        'Total records deleted by cleanup',
        ['database']
    )
    
    # Database size (gauge для мониторинга роста)
    database_size_bytes = Gauge(
        'database_size_bytes',
        'Current database size estimation',
        ['database']
    )
else:
    # Mock metrics
    data_cleanup_total = None
    data_cleanup_duration_seconds = None
    data_cleanup_records_deleted = None
    database_size_bytes = None


# ========================================
# Helper Functions
# ========================================

def record_graph_query(query_type: str, duration: float, success: bool = True):
    """
    Записать метрики для graph query
    
    Args:
        query_type: Тип запроса (get_post_context, get_trending_tags, etc)
        duration: Длительность в секундах
        success: Успешен ли запрос
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    try:
        if graph_query_latency:
            graph_query_latency.labels(query_type=query_type).observe(duration)
        
        if not success and graph_query_errors_total:
            graph_query_errors_total.labels(
                query_type=query_type,
                error_type='query_failed'
            ).inc()
    except Exception as e:
        logger.warning(f"Failed to record graph query metric: {e}")


def set_graph_availability(available: bool):
    """
    Установить статус доступности графа
    
    Args:
        available: True если Neo4j доступен
    """
    if not PROMETHEUS_AVAILABLE or not graph_availability:
        return
    
    try:
        graph_availability.set(1 if available else 0)
    except Exception as e:
        logger.warning(f"Failed to set graph availability: {e}")


def record_cache_hit(cache_type: str, hit: bool = True):
    """
    Записать cache hit/miss
    
    Args:
        cache_type: Тип cache (interests, trending, post_context)
        hit: True если cache hit, False если miss
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    try:
        if hit and graph_cache_hits_total:
            graph_cache_hits_total.labels(cache_type=cache_type).inc()
        elif not hit and graph_cache_misses_total:
            graph_cache_misses_total.labels(cache_type=cache_type).inc()
    except Exception as e:
        logger.warning(f"Failed to record cache metric: {e}")


def record_hybrid_search(
    duration: float,
    results_count: int,
    mode: str = "hybrid",
    avg_combined_score: Optional[float] = None
):
    """
    Записать метрики для hybrid search
    
    Args:
        duration: Длительность search в секундах
        results_count: Количество результатов
        mode: Режим поиска (hybrid, fallback_vector_only)
        avg_combined_score: Средний combined score
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    try:
        if hybrid_search_duration_seconds:
            hybrid_search_duration_seconds.observe(duration)
        
        if hybrid_search_results_total:
            hybrid_search_results_total.labels(search_mode=mode).inc(results_count)
        
        if avg_combined_score is not None and combined_score_distribution:
            combined_score_distribution.observe(avg_combined_score)
    except Exception as e:
        logger.warning(f"Failed to record hybrid search metric: {e}")


def record_cleanup(database: str, duration: float, deleted_count: int, success: bool = True):
    """
    Записать метрики для cleanup operation
    
    Args:
        database: База данных (postgres, neo4j, qdrant)
        duration: Длительность операции
        deleted_count: Количество удаленных записей
        success: Успешна ли операция
    """
    if not PROMETHEUS_AVAILABLE:
        return
    
    try:
        if data_cleanup_total:
            status = 'success' if success else 'failed'
            data_cleanup_total.labels(database=database, status=status).inc()
        
        if data_cleanup_duration_seconds:
            data_cleanup_duration_seconds.labels(database=database).observe(duration)
        
        if deleted_count > 0 and data_cleanup_records_deleted:
            data_cleanup_records_deleted.labels(database=database).inc(deleted_count)
    except Exception as e:
        logger.warning(f"Failed to record cleanup metric: {e}")


logger.info(f"✅ Metrics module loaded (Prometheus available: {PROMETHEUS_AVAILABLE})")

