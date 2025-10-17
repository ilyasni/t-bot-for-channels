"""
Observability для LangChain агентов

Интеграция с Langfuse для трейсинга и мониторинга работы агентов.
"""

import logging
import os
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

from .config import config


logger = logging.getLogger(__name__)


class LangfuseObserver:
    """
    Класс для интеграции с Langfuse для observability
    
    Обеспечивает:
    - Трейсинг вызовов агентов
    - Мониторинг производительности
    - Логирование ошибок
    - Анализ качества результатов
    """
    
    def __init__(self):
        self.enabled = self._check_langfuse_availability()
        self.callback_handler = None
        
        if self.enabled:
            try:
                from langfuse.callback import CallbackHandler as LangfuseCallback
                self.callback_handler = LangfuseCallback(
                    public_key=config.LANGFUSE_PUBLIC_KEY,
                    secret_key=config.LANGFUSE_SECRET_KEY,
                    host=config.LANGFUSE_HOST
                )
                logger.info("✅ Langfuse observer инициализирован")
            except ImportError as e:
                logger.warning(f"⚠️ Langfuse не доступен: {e}")
                self.enabled = False
            except Exception as e:
                logger.error(f"❌ Ошибка инициализации Langfuse: {e}")
                self.enabled = False
        else:
            logger.info("ℹ️ Langfuse observer отключен")
    
    def _check_langfuse_availability(self) -> bool:
        """Проверка доступности Langfuse"""
        return (
            bool(config.LANGFUSE_PUBLIC_KEY) and 
            bool(config.LANGFUSE_SECRET_KEY) and
            bool(config.LANGFUSE_HOST)
        )
    
    def get_callback_config(self, agent_name: str, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Получение конфигурации callback для LangChain
        
        Args:
            agent_name: Название агента
            user_id: ID пользователя (опционально)
            
        Returns:
            Dict с конфигурацией callbacks
        """
        if not self.enabled or not self.callback_handler:
            return {}
        
        try:
            # Создание уникального callback handler для каждого вызова
            from langfuse.callback import CallbackHandler as LangfuseCallback
            
            callback_handler = LangfuseCallback(
                public_key=config.LANGFUSE_PUBLIC_KEY,
                secret_key=config.LANGFUSE_SECRET_KEY,
                host=config.LANGFUSE_HOST,
                session_id=f"telegram_bot_{user_id}" if user_id else "telegram_bot",
                user_id=str(user_id) if user_id else None,
                tags=[agent_name, "telegram_bot", "group_digest"]
            )
            
            return {
                "callbacks": [callback_handler],
                "metadata": {
                    "agent_name": agent_name,
                    "user_id": user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания Langfuse callback: {e}")
            return {}
    
    def log_agent_start(self, agent_name: str, input_data: Dict[str, Any], user_id: Optional[int] = None):
        """Логирование начала работы агента"""
        if not self.enabled:
            return
        
        logger.info(f"🔍 Langfuse: Начало работы агента {agent_name}")
        logger.debug(f"   User ID: {user_id}")
        logger.debug(f"   Input keys: {list(input_data.keys())}")
    
    def log_agent_completion(
        self, 
        agent_name: str, 
        result: Dict[str, Any], 
        duration: float,
        user_id: Optional[int] = None
    ):
        """Логирование завершения работы агента"""
        if not self.enabled:
            return
        
        logger.info(f"✅ Langfuse: Агент {agent_name} завершен за {duration:.2f}s")
        logger.debug(f"   User ID: {user_id}")
        logger.debug(f"   Result keys: {list(result.keys())}")
    
    def log_agent_error(
        self, 
        agent_name: str, 
        error: Exception, 
        duration: float,
        user_id: Optional[int] = None
    ):
        """Логирование ошибки агента"""
        if not self.enabled:
            return
        
        logger.error(f"❌ Langfuse: Ошибка агента {agent_name} за {duration:.2f}s: {error}")
        logger.debug(f"   User ID: {user_id}")
    
    def log_orchestrator_start(self, user_id: int, group_id: int, message_count: int):
        """Логирование начала работы оркестратора"""
        if not self.enabled:
            return
        
        logger.info(f"🎯 Langfuse: Начало генерации дайджеста")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Group ID: {group_id}")
        logger.info(f"   Messages: {message_count}")
    
    def log_orchestrator_completion(
        self, 
        result: Dict[str, Any], 
        duration: float,
        user_id: int,
        group_id: int
    ):
        """Логирование завершения работы оркестратора"""
        if not self.enabled:
            return
        
        agents_executed = result.get("agent_statistics", {}).get("agents_executed", 0)
        detail_level = result.get("agent_statistics", {}).get("detail_level", "unknown")
        
        logger.info(f"🎉 Langfuse: Дайджест сгенерирован за {duration:.2f}s")
        logger.info(f"   User ID: {user_id}")
        logger.info(f"   Group ID: {group_id}")
        logger.info(f"   Agents executed: {agents_executed}")
        logger.info(f"   Detail level: {detail_level}")
    
    def log_orchestrator_error(
        self, 
        error: Exception, 
        duration: float,
        user_id: int,
        group_id: int
    ):
        """Логирование ошибки оркестратора"""
        if not self.enabled:
            return
        
        logger.error(f"💥 Langfuse: Ошибка генерации дайджеста за {duration:.2f}s: {error}")
        logger.error(f"   User ID: {user_id}")
        logger.error(f"   Group ID: {group_id}")


# Глобальный экземпляр observer
langfuse_observer = LangfuseObserver()


def get_langfuse_config(agent_name: str, user_id: Optional[int] = None) -> Dict[str, Any]:
    """
    Получение конфигурации Langfuse для агента
    
    Args:
        agent_name: Название агента
        user_id: ID пользователя
        
    Returns:
        Dict с конфигурацией
    """
    return langfuse_observer.get_callback_config(agent_name, user_id)


def log_agent_metrics(
    agent_name: str,
    start_time: datetime,
    end_time: datetime,
    success: bool,
    user_id: Optional[int] = None,
    error: Optional[Exception] = None,
    result: Optional[Dict[str, Any]] = None
):
    """
    Логирование метрик агента
    
    Args:
        agent_name: Название агента
        start_time: Время начала
        end_time: Время завершения
        success: Успешность выполнения
        user_id: ID пользователя
        error: Ошибка (если есть)
        result: Результат (если успешно)
    """
    duration = (end_time - start_time).total_seconds()
    
    if success and result:
        langfuse_observer.log_agent_completion(agent_name, result, duration, user_id)
    else:
        langfuse_observer.log_agent_error(agent_name, error or Exception("Unknown error"), duration, user_id)


def log_orchestrator_metrics(
    start_time: datetime,
    end_time: datetime,
    success: bool,
    user_id: int,
    group_id: int,
    error: Optional[Exception] = None,
    result: Optional[Dict[str, Any]] = None
):
    """
    Логирование метрик оркестратора
    
    Args:
        start_time: Время начала
        end_time: Время завершения
        success: Успешность выполнения
        user_id: ID пользователя
        group_id: ID группы
        error: Ошибка (если есть)
        result: Результат (если успешно)
    """
    duration = (end_time - start_time).total_seconds()
    
    if success and result:
        langfuse_observer.log_orchestrator_completion(result, duration, user_id, group_id)
    else:
        langfuse_observer.log_orchestrator_error(error or Exception("Unknown error"), duration, user_id, group_id)
