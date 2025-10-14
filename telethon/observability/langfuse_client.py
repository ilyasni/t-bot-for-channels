"""
Langfuse observability client для трейсинга AI операций

Best practices from Context7 (/langfuse/langfuse-python):
- Использовать decorators для автоматического трейсинга
- Flush() before app shutdown
- Enable для production, disable для разработки через env
- Graceful degradation (работает без Langfuse)

Используется для трейсинга:
- OpenRouter API calls (команда /ask)
- GigaChat embeddings (RAG Service)
- Qdrant vector search
"""
import os
from typing import Optional, Dict, Any
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

# Lazy import Langfuse (может не быть установлен)
try:
    from langfuse import Langfuse
    from langfuse.decorators import observe, langfuse_context
    LANGFUSE_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Langfuse library not installed. Install with: pip install langfuse")
    LANGFUSE_AVAILABLE = False
    # Mock decorators для совместимости
    def observe(*args, **kwargs):
        def decorator(func):
            return func
        return decorator if args and callable(args[0]) else decorator
    
    langfuse_context = None


class LangfuseClient:
    """
    Централизованный клиент для Langfuse observability
    
    Features:
    - Automatic tracing с decorators
    - Manual tracing через trace()
    - Graceful degradation (работает без Langfuse)
    - Context manager для trace groups
    
    Example:
        ```python
        from observability.langfuse_client import langfuse_client
        
        # Автоматический трейсинг
        @langfuse_client.observe_function("embedding_generation")
        async def create_embeddings(text):
            ...
        
        # Ручной трейсинг
        with langfuse_client.trace_context("rag_search") as trace:
            results = await search(query)
            if trace:
                trace.update(metadata={"results_count": len(results)})
        ```
    """
    
    def __init__(self):
        """Инициализация Langfuse клиента из environment variables"""
        self.enabled = os.getenv("LANGFUSE_ENABLED", "false").lower() == "true"
        self.client = None
        
        if not LANGFUSE_AVAILABLE:
            logger.info("⚠️ Langfuse library not available, tracing disabled")
            self.enabled = False
            return
        
        if self.enabled:
            try:
                public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
                secret_key = os.getenv("LANGFUSE_SECRET_KEY")
                host = os.getenv("LANGFUSE_HOST", "https://langfuse.produman.studio")
                
                if not public_key or not secret_key:
                    logger.warning("⚠️ Langfuse keys not configured, tracing disabled")
                    self.enabled = False
                    return
                
                self.client = Langfuse(
                    public_key=public_key,
                    secret_key=secret_key,
                    host=host
                )
                logger.info(f"✅ Langfuse client initialized (host: {host})")
            except Exception as e:
                logger.error(f"❌ Langfuse initialization failed: {e}")
                self.enabled = False
        else:
            logger.info("⚠️ Langfuse disabled (LANGFUSE_ENABLED=false)")
    
    def trace(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Создать trace для группы операций
        
        Args:
            name: Имя trace (например, "bot_ask_command", "rag_search")
            metadata: Дополнительные метаданные (user_id, query_length, etc.)
        
        Returns:
            Trace object или None если disabled
            
        Example:
            trace = langfuse_client.trace("bot_ask_command", {"user_id": 123})
            if trace:
                # операции
                trace.score(name="quality", value=0.95)
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            return self.client.trace(name=name, metadata=metadata)
        except Exception as e:
            logger.error(f"❌ Langfuse trace creation failed: {e}")
            return None
    
    @contextmanager
    def trace_context(self, name: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Context manager для автоматического trace lifecycle
        
        Args:
            name: Имя trace
            metadata: Метаданные
            
        Example:
            with langfuse_client.trace_context("rag_search", {"user_id": 123}) as trace:
                results = await search()
                if trace:
                    trace.update(metadata={"results": len(results)})
        """
        trace = self.trace(name, metadata)
        try:
            yield trace
        except Exception as e:
            if trace:
                try:
                    trace.update(level="ERROR", status_message=str(e))
                except:
                    pass
            raise
        finally:
            if trace and self.enabled:
                try:
                    # Langfuse auto-flushes, но можно явно flush
                    pass
                except Exception as e:
                    logger.error(f"❌ Langfuse trace finalization error: {e}")
    
    def observe_function(self, name: Optional[str] = None):
        """
        Decorator для автоматического трейсинга функций
        
        Args:
            name: Имя observation (по умолчанию - имя функции)
            
        Example:
            @langfuse_client.observe_function("embedding_generation")
            async def create_embeddings(text: str):
                return embeddings
        """
        if not self.enabled or not LANGFUSE_AVAILABLE:
            # Return pass-through decorator
            def decorator(func):
                return func
            return decorator
        
        # Use Langfuse @observe decorator
        return observe(name=name) if name else observe
    
    def flush(self):
        """
        Принудительно отправить все pending traces
        
        Вызывается перед shutdown приложения
        """
        if self.enabled and self.client:
            try:
                self.client.flush()
                logger.info("✅ Langfuse traces flushed")
            except Exception as e:
                logger.error(f"❌ Langfuse flush error: {e}")
    
    def shutdown(self):
        """
        Gracefully shutdown Langfuse client
        
        Вызывается при остановке приложения
        """
        if self.enabled and self.client:
            try:
                self.client.shutdown()
                logger.info("✅ Langfuse client shutdown")
            except Exception as e:
                logger.error(f"❌ Langfuse shutdown error: {e}")


# Singleton instance
langfuse_client = LangfuseClient()

