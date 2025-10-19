"""
Глобальный Rate Limiter для GigaChat API

Тариф: 1 concurrent request
Best practice: Context7 aiolimiter - leaky bucket algorithm для защиты от Rate Limit
"""
from aiolimiter import AsyncLimiter
import logging

logger = logging.getLogger(__name__)

# КРИТИЧНО: max_rate=1 для одного потока GigaChat
# time_period=1.0 = минимум 1 секунда между запросами
# Это гарантирует что одновременно выполняется только 1 запрос к GigaChat API
gigachat_rate_limiter = AsyncLimiter(
    max_rate=1,      # 1 запрос
    time_period=1.0  # за 1 секунду
)

logger.info("✅ GigaChat Rate Limiter инициализирован: 1 request per 1 second")

