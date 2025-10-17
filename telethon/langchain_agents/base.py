"""
Базовые классы для LangChain агентов

Основа для всех агентов с поддержкой LCEL, логирования и observability.
Поддерживает Pydantic structured output с retry logic.
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List, Type
from datetime import datetime, timezone

from langchain_core.runnables import Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import PydanticOutputParser, StrOutputParser
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel

from .config import config
from .observability import get_langfuse_config, log_agent_metrics


logger = logging.getLogger(__name__)


class BaseAgent(Runnable, ABC):
    """
    Базовый класс для всех LangChain агентов с Pydantic structured output
    
    Обеспечивает:
    - LCEL chain composition с format instructions
    - Pydantic structured output с валидацией
    - Retry logic при ошибках парсинга
    - Async execution с timeout
    - Structured logging
    - Error handling с fallback
    - Langfuse integration (опционально)
    """
    
    def __init__(
        self, 
        llm, 
        system_prompt: str,
        agent_name: str,
        output_model: Type[BaseModel],
        timeout: float = 30.0
    ):
        self.llm = llm
        self.system_prompt = system_prompt
        self.agent_name = agent_name
        self.timeout = timeout
        self.output_model = output_model
        
        # Structured output parser
        self.output_parser = PydanticOutputParser(pydantic_object=output_model)
        
        # LCEL chain с format instructions и retry logic
        self.chain = self._build_chain()
        
        logger.info(f"🤖 Инициализирован агент: {self.agent_name}")
    
    def _build_chain(self) -> Runnable:
        """Построить LCEL chain с format instructions"""
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt + "\n\n{format_instructions}"),
            ("human", "{user_message}")
        ])
        
        # Базовый chain
        return (
            prompt_template.partial(
                format_instructions=self.output_parser.get_format_instructions()
            )
            | self.llm
            | self.output_parser
        )
    
    @abstractmethod
    async def _process_input(self, input_data: Dict[str, Any]) -> str:
        """
        Обработать входные данные в user message
        
        Args:
            input_data: Входные данные агента
            
        Returns:
            Сформированное user message для LLM
        """
        pass
    
    @abstractmethod
    async def _process_output(self, output: BaseModel, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработать выходные данные LLM (Pydantic модель)
        
        Args:
            output: Результат от LLM (Pydantic модель)
            input_data: Исходные входные данные
            
        Returns:
            Обработанный результат агента
        """
        pass
    
    async def ainvoke(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Асинхронный вызов агента с полным pipeline
        
        Args:
            input_data: Входные данные
            **kwargs: Дополнительные параметры (callbacks, config)
            
        Returns:
            Результат работы агента
        """
        start_time = datetime.now(timezone.utc)
        
        try:
            logger.info(f"🚀 Запуск агента {self.agent_name}")
            logger.debug(f"   Входные данные: {input_data}")
            
            # Получение user_id для observability
            user_id = input_data.get("user_id")
            
            # Добавление Langfuse конфигурации
            langfuse_config = get_langfuse_config(self.agent_name, user_id)
            if langfuse_config:
                kwargs.update(langfuse_config)
            
            # 1. Подготовка user message
            user_message = await self._process_input(input_data)
            
            # 2. Вызов LLM с timeout
            try:
                result = await asyncio.wait_for(
                    self.chain.ainvoke({"user_message": user_message}, **kwargs),
                    timeout=self.timeout
                )
            except asyncio.TimeoutError:
                logger.error(f"⏰ Timeout агента {self.agent_name} ({self.timeout}s)")
                raise TimeoutError(f"Agent {self.agent_name} timeout after {self.timeout}s")
            
            # 3. Обработка результата
            processed_result = await self._process_output(result, input_data)
            
            # 4. Логирование результата и метрик
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            logger.info(f"✅ Агент {self.agent_name} завершен за {duration:.2f}s")
            logger.debug(f"   Результат: {processed_result}")
            
            # Логирование метрик в Langfuse
            log_agent_metrics(
                agent_name=self.agent_name,
                start_time=start_time,
                end_time=end_time,
                success=True,
                user_id=user_id,
                result=processed_result
            )
            
            # Возвращаем и Pydantic объект, и обработанный результат
            return {
                "pydantic_result": result,
                "processed_result": processed_result
            }
            
        except Exception as e:
            end_time = datetime.now(timezone.utc)
            duration = (end_time - start_time).total_seconds()
            logger.error(f"❌ Ошибка агента {self.agent_name} за {duration:.2f}s: {e}")
            
            # Логирование ошибки в Langfuse
            user_id = input_data.get("user_id")
            log_agent_metrics(
                agent_name=self.agent_name,
                start_time=start_time,
                end_time=end_time,
                success=False,
                user_id=user_id,
                error=e
            )
            
            # Fallback result
            return await self._handle_error(e, input_data)
    
    async def _handle_error(self, error: Exception, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Обработка ошибок с fallback результатом
        
        Args:
            error: Исключение
            input_data: Исходные данные
            
        Returns:
            Fallback результат
        """
        logger.warning(f"🔄 Использование fallback для агента {self.agent_name}")
        
        # Базовый fallback - пустой результат
        # Каждый агент может переопределить этот метод
        return {"error": str(error), "fallback": True}
    
    def invoke(self, input_data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """
        Синхронный wrapper для ainvoke
        
        Args:
            input_data: Входные данные
            **kwargs: Дополнительные параметры
            
        Returns:
            Результат работы агента
        """
        return asyncio.run(self.ainvoke(input_data, **kwargs))


# HeuristicAgent удален - все агенты теперь используют LLM