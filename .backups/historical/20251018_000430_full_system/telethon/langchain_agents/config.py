"""
Конфигурация LangChain агентов для Group Digest Generation

Интеграция с GigaChat через gpt2giga-proxy и настройки для всех агентов.
"""

import os
from dataclasses import dataclass
from typing import Dict, Any
from langchain_community.chat_models import ChatOpenAI


@dataclass
class LangChainConfig:
    """Конфигурация для LangChain агентов"""
    
    # GigaChat proxy settings
    GIGACHAT_BASE_URL: str = os.getenv("GIGACHAT_BASE_URL", "http://gpt2giga-proxy:8090/v1")
    GIGACHAT_TIMEOUT: float = 60.0
    
    # Model configurations
    GIGACHAT_MODEL: str = "GigaChat"
    GIGACHAT_PRO_MODEL: str = "GigaChat-Pro"
    
    # Temperature settings per agent type
    TEMPERATURE_CONSERVATIVE: float = 0.1  # Для извлечения фактов
    TEMPERATURE_CREATIVE: float = 0.3      # Для анализа эмоций, ролей
    TEMPERATURE_SYNTHESIS: float = 0.2     # Для финального синтеза
    
    # Timeouts
    AGENT_TIMEOUT: float = 30.0
    ORCHESTRATOR_TIMEOUT: float = 120.0
    
    # Langfuse settings
    LANGFUSE_PUBLIC_KEY: str = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    LANGFUSE_SECRET_KEY: str = os.getenv("LANGFUSE_SECRET_KEY", "")
    LANGFUSE_HOST: str = os.getenv("LANGFUSE_HOST", "https://langfuse.produman.studio")
    
    def get_llm(self, model_type: str = "gpt2giga") -> ChatOpenAI:
        """
        Получить LLM для агентов
        
        Args:
            model_type: Тип модели ("gpt2giga", "gpt2giga-pro")
            
        Returns:
            ChatOpenAI instance
        """
        if model_type == "gpt2giga-pro":
            model_name = self.GIGACHAT_PRO_MODEL
            temperature = self.TEMPERATURE_CREATIVE
        else:  # gpt2giga
            model_name = self.GIGACHAT_MODEL
            temperature = self.TEMPERATURE_CONSERVATIVE
            
        return ChatOpenAI(
            model=model_name,
            base_url=self.GIGACHAT_BASE_URL,
            api_key="dummy_key",  # Не используется для gpt2giga-proxy
            temperature=temperature,
            request_timeout=self.GIGACHAT_TIMEOUT,
            max_retries=2
        )
    
    @property
    def agent_timeouts(self) -> Dict[str, float]:
        """Timeout'ы для разных агентов"""
        return {
            "dialogue_assessor": 15.0,
            "topic_extractor": 30.0,
            "emotion_analyzer": 30.0,
            "speaker_analyzer": 30.0,
            "context_summarizer": 30.0,
            "key_moments": 25.0,
            "timeline_builder": 35.0,
            "context_links": 20.0,
            "supervisor_synthesizer": 45.0
        }
    
    @classmethod
    def from_env(cls) -> "LangChainConfig":
        """Создать конфиг из environment variables"""
        return cls(
            GIGACHAT_BASE_URL=os.getenv("GIGACHAT_BASE_URL", cls.GIGACHAT_BASE_URL),
            GIGACHAT_TIMEOUT=float(os.getenv("GIGACHAT_TIMEOUT", cls.GIGACHAT_TIMEOUT)),
            GIGACHAT_MODEL=os.getenv("GIGACHAT_MODEL", cls.GIGACHAT_MODEL),
            GIGACHAT_PRO_MODEL=os.getenv("GIGACHAT_PRO_MODEL", cls.GIGACHAT_PRO_MODEL),
            TEMPERATURE_CONSERVATIVE=float(os.getenv("TEMPERATURE_CONSERVATIVE", cls.TEMPERATURE_CONSERVATIVE)),
            TEMPERATURE_CREATIVE=float(os.getenv("TEMPERATURE_CREATIVE", cls.TEMPERATURE_CREATIVE)),
            TEMPERATURE_SYNTHESIS=float(os.getenv("TEMPERATURE_SYNTHESIS", cls.TEMPERATURE_SYNTHESIS)),
            LANGFUSE_PUBLIC_KEY=os.getenv("LANGFUSE_PUBLIC_KEY", ""),
            LANGFUSE_SECRET_KEY=os.getenv("LANGFUSE_SECRET_KEY", ""),
            LANGFUSE_HOST=os.getenv("LANGFUSE_HOST", cls.LANGFUSE_HOST)
        )


def get_gigachat_llm(model: str = "GigaChat", temperature: float = 0.1) -> ChatOpenAI:
    """
    Создать GigaChat LLM через gpt2giga-proxy
    
    Args:
        model: Модель GigaChat ("GigaChat" или "GigaChat-Pro")
        temperature: Температура для генерации (0.1-0.3)
    
    Returns:
        ChatOpenAI instance настроенный на GigaChat
    """
    config = LangChainConfig.from_env()
    
    # Определяем base URL и модель
    base_url = config.GIGACHAT_BASE_URL
    
    return ChatOpenAI(
        base_url=base_url,
        model=model,
        temperature=temperature,
        timeout=config.GIGACHAT_TIMEOUT,
        # Для совместимости с OpenAI API через proxy
        openai_api_key="dummy-key",  # gpt2giga-proxy игнорирует это
        max_tokens=4000,
        request_timeout=config.GIGACHAT_TIMEOUT
    )


def get_llm_for_agent(agent_type: str) -> ChatOpenAI:
    """
    Получить LLM с оптимальными настройками для типа агента
    
    Args:
        agent_type: Тип агента ("fact_extraction", "emotion_analysis", "synthesis")
    
    Returns:
        Настроенный ChatOpenAI instance
    """
    config = LangChainConfig.from_env()
    
    if agent_type == "fact_extraction":
        # Для извлечения тем, ключевых моментов - консервативно
        return get_gigachat_llm(config.GIGACHAT_MODEL, config.TEMPERATURE_CONSERVATIVE)
    
    elif agent_type == "emotion_analysis":
        # Для анализа эмоций, ролей - более творчески
        return get_gigachat_llm(config.GIGACHAT_MODEL, config.TEMPERATURE_CREATIVE)
    
    elif agent_type == "synthesis":
        # Для финального синтеза - баланс
        return get_gigachat_llm(config.GIGACHAT_MODEL, config.TEMPERATURE_SYNTHESIS)
    
    else:
        # По умолчанию
        return get_gigachat_llm(config.GIGACHAT_MODEL, config.TEMPERATURE_CONSERVATIVE)


# Глобальный конфиг
config = LangChainConfig.from_env()
