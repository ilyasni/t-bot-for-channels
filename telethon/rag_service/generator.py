"""
Генератор ответов на вопросы с использованием RAG
(Retrieval-Augmented Generation)
"""
import logging
import httpx
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from search import search_service
import config

# Инициализируем logger до использования
logger = logging.getLogger(__name__)

# Feature flags для A/B testing
try:
    from rag_service.feature_flags import feature_flags
    from rag_service.enhanced_search import enhanced_search_service
    ENHANCED_SEARCH_AVAILABLE = True
except ImportError:
    logger.warning("⚠️ Enhanced search not available, using baseline only")
    ENHANCED_SEARCH_AVAILABLE = False
    feature_flags = None
    enhanced_search_service = None


class RAGGenerator:
    """Генератор ответов с использованием RAG"""
    
    def __init__(self):
        """Инициализация генератора"""
        self.openrouter_api_key = config.OPENROUTER_API_KEY
        self.openrouter_model = config.OPENROUTER_MODEL
        self.openrouter_url = config.OPENROUTER_API_URL
        self.gigachat_url = f"{config.GIGACHAT_PROXY_URL}/v1/chat/completions"
        
        self.enabled = self.openrouter_api_key is not None
        
        if self.enabled:
            logger.info(f"✅ RAG Generator инициализирован (модель: {self.openrouter_model})")
        else:
            logger.warning("⚠️ RAG Generator отключен (отсутствует OPENROUTER_API_KEY)")
    
    def _create_rag_prompt(
        self,
        query: str,
        contexts: List[Dict[str, Any]]
    ) -> str:
        """
        Создать промпт для RAG
        
        Args:
            query: Вопрос пользователя
            contexts: Список найденных документов (постов)
            
        Returns:
            Промпт для LLM
        """
        # Форматируем контексты
        formatted_contexts = []
        for i, ctx in enumerate(contexts, 1):
            channel = ctx.get("channel_username", "Unknown")
            posted_at = ctx.get("posted_at", "")
            if isinstance(posted_at, datetime):
                posted_at = posted_at.strftime("%Y-%m-%d %H:%M")
            text = ctx.get("text", "")
            url = ctx.get("url", "")
            
            context_str = f"""
Источник {i}:
Канал: @{channel}
Дата: {posted_at}
Ссылка: {url}
Текст:
{text}
"""
            formatted_contexts.append(context_str.strip())
        
        contexts_block = "\n\n---\n\n".join(formatted_contexts)
        
        # Создаем промпт
        prompt = f"""Ты — ассистент для анализа постов из Telegram каналов.

Контекст (посты):
{contexts_block}

Вопрос пользователя:
{query}

Инструкции:
- Отвечай ТОЛЬКО на основе предоставленных постов
- Если информации нет — скажи "По данному вопросу информации в постах не найдено"
- Цитируй источники: укажи канал и дату поста в формате [@канал, дата]
- Ответ должен быть структурированным и информативным
- Используй русский язык
- Если в постах есть противоречивая информация, укажи на это
- Будь объективным и точным

Ответ:"""
        
        return prompt
    
    async def _generate_with_openrouter(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        Генерация ответа через OpenRouter
        
        Args:
            prompt: Промпт
            temperature: Temperature для генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            Сгенерированный ответ или None
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.openrouter_url,
                    headers={
                        "Authorization": f"Bearer {self.openrouter_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.openrouter_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ OpenRouter error {response.status_code}: {response.text[:200]}")
                    return None
                
                result = response.json()
                answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if answer:
                    logger.debug("✅ Ответ успешно сгенерирован через OpenRouter")
                    return answer
                else:
                    logger.error("❌ Пустой ответ от OpenRouter")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка генерации через OpenRouter: {e}")
            return None
    
    async def _generate_with_gigachat(
        self,
        prompt: str,
        temperature: float = 0.3,
        max_tokens: int = 1000
    ) -> Optional[str]:
        """
        Генерация ответа через GigaChat (fallback)
        
        Args:
            prompt: Промпт
            temperature: Temperature для генерации
            max_tokens: Максимальное количество токенов
            
        Returns:
            Сгенерированный ответ или None
        """
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    self.gigachat_url,
                    json={
                        "model": "GigaChat",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": temperature,
                        "max_tokens": max_tokens
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ GigaChat error {response.status_code}: {response.text[:200]}")
                    return None
                
                result = response.json()
                answer = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                if answer:
                    logger.debug("✅ Ответ успешно сгенерирован через GigaChat")
                    return answer
                else:
                    logger.error("❌ Пустой ответ от GigaChat")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Ошибка генерации через GigaChat: {e}")
            return None
    
    async def _log_query_to_history(self, user_id: int, query: str):
        """
        Логировать RAG-запрос в историю для анализа интересов
        
        Args:
            user_id: ID пользователя
            query: Текст запроса
        """
        try:
            import sys
            import os
            sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
            
            from database import SessionLocal
            from models import RAGQueryHistory
            
            db = SessionLocal()
            try:
                history_entry = RAGQueryHistory(
                    user_id=user_id,
                    query=query,
                    extracted_topics=None  # Можно добавить извлечение тем позже
                )
                db.add(history_entry)
                db.commit()
                logger.debug(f"📝 Запрос сохранен в историю user {user_id}")
            finally:
                db.close()
                
        except Exception as e:
            # Не критично, просто логируем
            logger.warning(f"⚠️ Не удалось сохранить запрос в историю: {e}")
    
    async def generate_answer(
        self,
        query: str,
        user_id: int,
        context_limit: int = 10,
        channels: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Сгенерировать ответ на вопрос с использованием RAG
        
        Args:
            query: Вопрос пользователя
            user_id: ID пользователя
            context_limit: Количество документов для контекста
            channels: Фильтр по каналам
            tags: Фильтр по тегам
            date_from: Фильтр по дате (от)
            date_to: Фильтр по дате (до)
            
        Returns:
            Словарь с ответом и источниками
        """
        if not self.enabled:
            return {
                "error": "RAG Generator отключен",
                "query": query,
                "answer": None,
                "sources": []
            }
        
        try:
            logger.info(f"🤖 Генерация ответа для user {user_id}: '{query}'")
            
            # Логируем запрос в историю для анализа интересов
            await self._log_query_to_history(user_id, query)
            
            # A/B Test: Hybrid search vs Baseline
            use_hybrid = (
                ENHANCED_SEARCH_AVAILABLE and 
                feature_flags and 
                feature_flags.is_enabled('hybrid_search', user_id=user_id)
            )
            
            # Получаем релевантные документы через поиск
            search_results = []
            
            if use_hybrid:
                # Новый: Hybrid search (Qdrant + Neo4j)
                logger.info(f"🔬 A/B Test: Using HYBRID search for user {user_id}")
                
                try:
                    search_results = await enhanced_search_service.search_with_graph_context(
                        query=query,
                        user_id=user_id,
                        limit=context_limit,
                        channel_id=channels[0] if channels else None,
                        tags=tags,
                        date_from=date_from,
                        date_to=date_to
                    )
                except Exception as e:
                    logger.error(f"❌ Hybrid search failed, fallback to baseline: {e}")
                    use_hybrid = False  # Fallback
            
            if not use_hybrid:
                # Baseline: Обычный поиск через Qdrant
                logger.info(f"📊 A/B Test: Using BASELINE search for user {user_id}")
                
                if channels:
                    # Ищем по каждому каналу и объединяем результаты
                    for channel_id in channels:
                        results = await search_service.search(
                            query=query,
                            user_id=user_id,
                            limit=context_limit // len(channels) + 1,
                            channel_id=channel_id,
                            tags=tags,
                            date_from=date_from,
                            date_to=date_to
                        )
                        search_results.extend(results)
                else:
                    # Обычный поиск
                    search_results = await search_service.search(
                        query=query,
                        user_id=user_id,
                        limit=context_limit,
                        tags=tags,
                        date_from=date_from,
                        date_to=date_to
                    )
            
            if not search_results:
                return {
                    "query": query,
                    "answer": "По данному вопросу информации в постах не найдено. Попробуйте переформулировать запрос или расширить критерии поиска.",
                    "sources": [],
                    "context_used": 0
                }
            
            # Ограничиваем количество документов для контекста
            search_results = search_results[:context_limit]
            
            # Создаем промпт
            prompt = self._create_rag_prompt(query, search_results)
            
            # Генерируем ответ
            answer = None
            
            # Пробуем OpenRouter
            answer = await self._generate_with_openrouter(
                prompt,
                temperature=config.RAG_TEMPERATURE
            )
            
            # Fallback на GigaChat
            if not answer and config.GIGACHAT_ENABLED:
                logger.info("🔄 Fallback на GigaChat для генерации ответа")
                answer = await self._generate_with_gigachat(
                    prompt,
                    temperature=config.RAG_TEMPERATURE
                )
            
            if not answer:
                return {
                    "query": query,
                    "error": "Не удалось сгенерировать ответ",
                    "answer": None,
                    "sources": [],
                    "context_used": len(search_results)
                }
            
            # Форматируем источники
            sources = [
                {
                    "post_id": result["post_id"],
                    "channel_username": result["channel_username"],
                    "posted_at": result["posted_at"],
                    "url": result["url"],
                    "excerpt": result["text"][:200] + "..." if len(result["text"]) > 200 else result["text"],
                    "score": result["score"]
                }
                for result in search_results
            ]
            
            logger.info(f"✅ Ответ сгенерирован для user {user_id} (использовано {len(sources)} источников)")
            
            return {
                "query": query,
                "answer": answer,
                "sources": sources,
                "context_used": len(sources)
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации ответа: {e}")
            return {
                "query": query,
                "error": str(e),
                "answer": None,
                "sources": [],
                "context_used": 0
            }


# Глобальный экземпляр генератора
rag_generator = RAGGenerator()

