"""
LangChain Agents для Telegram Bot Group Digest Generation

Портирование n8n workflows в прямую LangChain интеграцию с использованием LCEL.
Архитектура: 9 агентов в sequential pipeline с conditional execution.
"""

from .base import BaseAgent
from .config import get_gigachat_llm, LangChainConfig
from .orchestrator import DigestOrchestrator

__all__ = [
    "BaseAgent",
    "get_gigachat_llm", 
    "LangChainConfig",
    "DigestOrchestrator"
]
