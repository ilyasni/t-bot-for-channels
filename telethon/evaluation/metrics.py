"""
Prometheus metrics для evaluation system

Импортирует метрики из observability/metrics.py для избежания дублирования.
"""

# Импортируем все evaluation метрики из observability/metrics.py
from observability.metrics import (
    evaluation_answer_correctness,
    evaluation_faithfulness,
    evaluation_context_relevance,
    evaluation_channel_context_awareness,
    evaluation_group_synthesis_quality,
    evaluation_multi_source_coherence,
    evaluation_runs_total,
    evaluation_duration_seconds,
    evaluation_runs_active,
    evaluation_items_processed
)

# Простые заглушки для функций, которые не существуют в observability/metrics.py
def observe_score(metric, labels, score):
    """Observe score metric"""
    try:
        metric.labels(**labels).observe(score)
    except Exception as e:
        pass

def increment_counter(metric, labels, amount=1):
    """Increment counter metric"""
    try:
        metric.labels(**labels).inc(amount)
    except Exception as e:
        pass

def increment_gauge(metric, labels, amount=1):
    """Increment gauge metric"""
    try:
        metric.labels(**labels).inc(amount)
    except Exception as e:
        pass

def decrement_gauge(metric, labels, amount=1):
    """Decrement gauge metric"""
    try:
        metric.labels(**labels).dec(amount)
    except Exception as e:
        pass

def set_gauge(metric, labels, value):
    """Set gauge metric value"""
    try:
        metric.labels(**labels).set(value)
    except Exception as e:
        pass

def log_evaluation_metric_error(metric_name: str, error: Exception):
    """Log evaluation metric error"""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Evaluation metric error in {metric_name}: {error}")