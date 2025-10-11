"""
AI-генератор дайджестов с использованием GigaChat
Анализирует интересы пользователя и создает краткие саммари по темам
"""
import logging
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import Counter
import httpx
import re

# Добавляем родительскую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import Post, Channel, RAGQueryHistory, DigestSettings
from search import search_service
import config

logger = logging.getLogger(__name__)


class AIDigestGenerator:
    """AI-генератор дайджестов с анализом интересов пользователя"""
    
    def __init__(self):
        """Инициализация AI генератора"""
        self.search_service = search_service
        self.gigachat_url = f"{config.GIGACHAT_PROXY_URL}/v1/chat/completions"
        self.gigachat_model = os.getenv("GIGACHAT_MODEL", "GigaChat")
        logger.info(f"✅ AI Digest Generator инициализирован (модель: {self.gigachat_model})")
    
    async def generate_ai_digest(
        self,
        user_id: int,
        date_from: datetime,
        date_to: datetime,
        preferred_topics: Optional[List[str]] = None,
        topics_limit: int = 5,
        summary_style: str = "concise"
    ) -> str:
        """
        Сгенерировать AI-дайджест на основе интересов пользователя
        
        Args:
            user_id: ID пользователя
            date_from: Начало периода
            date_to: Конец периода
            preferred_topics: Предпочитаемые темы (вручную указанные)
            topics_limit: Максимум тем в дайджесте (3-5)
            summary_style: Стиль саммари (concise/detailed/executive)
            
        Returns:
            Markdown-дайджест с AI-саммари по темам
        """
        try:
            logger.info(f"🤖 AI-дайджест для user {user_id}: {date_from.date()} - {date_to.date()}")
            
            # 1. Определяем темы интересов (вручную + история запросов)
            topics = await self._get_user_interests(user_id, preferred_topics or [])
            
            if not topics:
                logger.warning(f"⚠️ Темы не найдены для user {user_id}, используем общий анализ")
                # Fallback: анализ по популярным тегам
                topics = await self._get_popular_topics(user_id, date_from, date_to)
            
            logger.info(f"📋 Выбранные темы ({len(topics)}): {', '.join(topics[:topics_limit])}")
            
            # 2. Для каждой темы: поиск постов и суммаризация
            topic_summaries = []
            for topic in topics[:topics_limit]:
                logger.info(f"🔍 Обработка темы: {topic}")
                
                # Поиск релевантных постов через RAG
                posts = await self._search_posts_for_topic(
                    user_id, topic, date_from, date_to
                )
                
                if posts:
                    # Суммаризация через GigaChat
                    summary = await self._summarize_topic(
                        topic, posts, summary_style
                    )
                    topic_summaries.append(summary)
                    logger.info(f"✅ Тема '{topic}': {summary['post_count']} постов")
            
            if not topic_summaries:
                return self._generate_empty_digest(date_from, date_to)
            
            # 3. Форматирование финального дайджеста
            digest = self._format_ai_digest(topic_summaries, date_from, date_to)
            
            logger.info(f"✅ AI-дайджест сгенерирован: {len(topic_summaries)} тем")
            
            return digest
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации AI-дайджеста: {e}", exc_info=True)
            raise
    
    async def _get_user_interests(
        self, 
        user_id: int, 
        preferred_topics: List[str]
    ) -> List[str]:
        """
        Определить темы интересов пользователя
        Комбинация: вручную указанные темы + темы из истории запросов
        
        Returns:
            Список тем с приоритетом preferred_topics
        """
        topics = []
        
        # 1. Вручную указанные темы (высокий приоритет)
        if preferred_topics:
            topics.extend(preferred_topics)
            logger.info(f"📌 Вручную указанные темы: {preferred_topics}")
        
        # 2. Темы из истории RAG-запросов (последние 30 дней)
        inferred_topics = await self._get_topics_from_history(user_id)
        
        if inferred_topics:
            logger.info(f"🔍 Темы из истории запросов: {inferred_topics[:5]}")
            # Добавляем темы из истории, если их еще нет
            for topic in inferred_topics:
                if topic.lower() not in [t.lower() for t in topics]:
                    topics.append(topic)
        
        return topics
    
    async def _get_topics_from_history(self, user_id: int) -> List[str]:
        """
        Извлечь темы из истории RAG-запросов
        Анализирует последние N дней (QUERY_HISTORY_DAYS)
        """
        db = SessionLocal()
        try:
            # Получаем последние запросы (от новых к старым)
            cutoff_date = datetime.now() - timedelta(days=config.QUERY_HISTORY_DAYS)
            
            queries = db.query(RAGQueryHistory).filter(
                RAGQueryHistory.user_id == user_id,
                RAGQueryHistory.created_at >= cutoff_date
            ).order_by(RAGQueryHistory.created_at.desc()).limit(50).all()
            
            if not queries:
                return []
            
            # Извлекаем ключевые слова из запросов
            all_keywords = []
            for q in queries:
                keywords = self._extract_keywords_from_query(q.query)
                all_keywords.extend(keywords)
            
            # Подсчитываем частоту (с учетом времени: новые запросы важнее)
            # Используем простую схему: берем топ-N слов по частоте
            if all_keywords:
                counter = Counter(all_keywords)
                # Возвращаем топ-10 тем
                top_topics = [word for word, count in counter.most_common(10)]
                return top_topics
            
            return []
            
        except Exception as e:
            logger.error(f"❌ Ошибка извлечения тем из истории: {e}")
            return []
        finally:
            db.close()
    
    def _extract_keywords_from_query(self, query: str) -> List[str]:
        """
        Простое извлечение ключевых слов из запроса
        Удаляет стоп-слова и берет существительные
        """
        # Стоп-слова (вопросительные и служебные)
        stop_words = {
            'что', 'где', 'когда', 'как', 'почему', 'какие', 'какой', 'какая',
            'про', 'для', 'был', 'были', 'было', 'есть', 'это', 'эти', 'этот',
            'можно', 'нужно', 'расскажи', 'сделай', 'покажи', 'дай',
            'писали', 'говорили', 'произошло', 'случилось', 'за', 'на', 'в', 'с'
        }
        
        # Очищаем и разбиваем
        query_clean = query.lower()
        query_clean = re.sub(r'[^\w\s]', ' ', query_clean)
        words = query_clean.split()
        
        # Фильтруем стоп-слова и короткие слова
        keywords = [
            w for w in words 
            if len(w) > 3 and w not in stop_words
        ]
        
        return keywords
    
    async def _get_popular_topics(
        self, 
        user_id: int, 
        date_from: datetime, 
        date_to: datetime
    ) -> List[str]:
        """
        Fallback: получить популярные темы из тегов постов за период
        """
        db = SessionLocal()
        try:
            posts = db.query(Post).filter(
                Post.user_id == user_id,
                Post.posted_at >= date_from,
                Post.posted_at <= date_to,
                Post.tags.isnot(None)
            ).all()
            
            # Собираем все теги
            all_tags = []
            for post in posts:
                if post.tags:
                    all_tags.extend(post.tags)
            
            if all_tags:
                # Топ-10 популярных тегов
                counter = Counter(all_tags)
                return [tag for tag, count in counter.most_common(10)]
            
            return []
            
        finally:
            db.close()
    
    async def _search_posts_for_topic(
        self,
        user_id: int,
        topic: str,
        date_from: datetime,
        date_to: datetime
    ) -> List[Dict[str, Any]]:
        """
        Найти релевантные посты для темы через RAG векторный поиск
        
        Returns:
            Список постов (топ-10-15 релевантных)
        """
        try:
            # Используем векторный поиск
            results = await self.search_service.search(
                query=topic,
                user_id=user_id,
                limit=config.DIGEST_POSTS_PER_TOPIC,
                date_from=date_from,
                date_to=date_to
            )
            
            # search() возвращает список напрямую, не dict
            return results if isinstance(results, list) else []
            
        except Exception as e:
            logger.error(f"❌ Ошибка поиска постов для темы '{topic}': {e}")
            return []
    
    async def _summarize_topic(
        self,
        topic: str,
        posts: List[Dict],
        style: str
    ) -> Dict[str, Any]:
        """
        Суммаризировать посты по одной теме через GigaChat
        
        Args:
            topic: Название темы
            posts: Список релевантных постов
            style: Стиль саммари (concise/detailed/executive)
            
        Returns:
            {
                "topic": str,
                "summary": str, 
                "post_count": int,
                "sources": List[Dict]
            }
        """
        try:
            # Подготовка контекста из постов
            contexts = []
            for i, post in enumerate(posts[:15], 1):  # Максимум 15 постов
                text = post.get('text', '')
                # Для малого количества постов берем весь текст, иначе 700 символов
                if len(posts) <= 3:
                    text = text[:1000]  # Весь пост или до 1000 символов
                else:
                    text = text[:700]  # Первые 700 символов
                
                channel = post.get('channel_username', '')
                date_str = post.get('posted_at', '')
                if isinstance(date_str, str):
                    date_str = date_str[:10]  # Только дата
                elif hasattr(date_str, 'strftime'):
                    date_str = date_str.strftime('%Y-%m-%d')
                
                contexts.append(f"{i}. [@{channel}, {date_str}]: {text}")
            
            context_block = "\n\n".join(contexts)
            
            # Создание промпта в зависимости от стиля
            if style == "concise":
                instruction = "Создай краткую сводку в 2-3 предложения, выделив только ключевые факты и цифры."
            elif style == "detailed":
                instruction = "Создай подробную сводку в 4-6 предложений с ключевыми фактами, цифрами и трендами."
            else:  # executive
                instruction = "Создай executive summary в формате списка (3-5 ключевых пунктов)."
            
            prompt = f"""Ты - аналитик, создающий дайджест новостей по теме "{topic}".

Ниже посты из Telegram-каналов по этой теме за день:

{context_block}

Задача: {instruction}

ВАЖНЫЕ ПРАВИЛА:
- Используй ТОЛЬКО информацию из предоставленных постов
- Если постов мало (1-2) - суммируй то, что есть
- НИКОГДА не отвечай "недостаточно информации" или "не хватает данных"
- Всегда создавай сводку на основе доступных фактов
- Конкретные цифры и данные обязательны
- Структурированный ответ на русском языке
- Не упоминай количество постов или источники в самой сводке

Краткая сводка по теме "{topic}":"""
            
            # Вызов GigaChat
            summary_text = await self._call_gigachat(prompt)
            
            # Формируем источники
            sources = []
            for post in posts[:5]:  # Топ-5 источников
                sources.append({
                    "post_id": post.get('post_id'),
                    "channel": post.get('channel_username'),
                    "date": post.get('posted_at'),
                    "url": post.get('url')
                })
            
            return {
                "topic": topic,
                "summary": summary_text.strip(),
                "post_count": len(posts),
                "sources": sources
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка суммаризации темы '{topic}': {e}")
            # Fallback: простое объединение
            return {
                "topic": topic,
                "summary": f"По теме '{topic}' найдено {len(posts)} постов за период.",
                "post_count": len(posts),
                "sources": []
            }
    
    async def _call_gigachat(
        self,
        prompt: str,
        temperature: float = None
    ) -> str:
        """
        Вызов GigaChat API для суммаризации
        
        Args:
            prompt: Промпт для модели
            temperature: Температура генерации (default: config.DIGEST_AI_TEMPERATURE)
            
        Returns:
            Сгенерированный текст
        """
        if temperature is None:
            temperature = config.DIGEST_AI_TEMPERATURE
        
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                payload = {
                    "model": self.gigachat_model,
                    "messages": [
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": temperature,
                    "max_tokens": 500  # Достаточно для краткой сводки
                }
                
                response = await client.post(
                    self.gigachat_url,
                    json=payload
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    if content:
                        return content
                    else:
                        logger.error("❌ Пустой ответ от GigaChat")
                        return "Ошибка генерации саммари"
                else:
                    logger.error(f"❌ GigaChat error {response.status_code}: {response.text[:200]}")
                    return "Ошибка генерации саммари"
                    
        except Exception as e:
            logger.error(f"❌ Ошибка вызова GigaChat: {e}")
            return "Ошибка генерации саммари"
    
    def _format_ai_digest(
        self,
        topic_summaries: List[Dict],
        date_from: datetime,
        date_to: datetime
    ) -> str:
        """
        Форматировать AI-дайджест в Markdown
        
        Args:
            topic_summaries: Список саммари по темам
            date_from, date_to: Период
            
        Returns:
            Markdown дайджест
        """
        lines = []
        
        # Заголовок
        lines.append("# 🤖 AI-Дайджест")
        lines.append(f"**Период:** {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
        lines.append(f"**Тем:** {len(topic_summaries)}")
        lines.append("")
        
        # Саммари по темам
        for i, ts in enumerate(topic_summaries, 1):
            topic = ts['topic']
            summary = ts['summary']
            count = ts['post_count']
            sources = ts['sources']
            
            # Эмодзи для топика
            emoji = self._get_topic_emoji(topic)
            
            lines.append(f"## {emoji} {i}. {topic.title()}")
            lines.append(f"*Постов проанализировано: {count}*")
            lines.append("")
            lines.append(summary)
            lines.append("")
            
            # Источники
            if sources:
                lines.append("**Источники:**")
                for src in sources[:3]:  # Топ-3 источника
                    channel = src.get('channel', '')
                    date = src.get('date', '')
                    url = src.get('url', '')
                    if isinstance(date, str):
                        date = date[:10]
                    lines.append(f"- [@{channel}, {date}]({url})")
                lines.append("")
        
        # Футер
        lines.append("---")
        lines.append(f"*Дайджест сгенерирован AI (GigaChat) • {datetime.now().strftime('%d.%m.%Y %H:%M')}*")
        
        return "\n".join(lines)
    
    def _generate_empty_digest(self, date_from: datetime, date_to: datetime) -> str:
        """Сгенерировать пустой дайджест"""
        return f"""# 🤖 AI-Дайджест
**Период:** {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}

За указанный период постов по интересующим вас темам не найдено.

Попробуйте:
- Расширить период поиска
- Настроить темы в настройках дайджеста
- Задать вопросы через RAG для формирования истории запросов
"""
    
    def _get_topic_emoji(self, topic: str) -> str:
        """Подобрать эмодзи для темы"""
        topic_lower = topic.lower()
        
        emoji_map = {
            'крипт': '💰',
            'авто': '🚗',
            'машин': '🚗',
            'финанс': '💵',
            'банк': '🏦',
            'технолог': '💻',
            'бизнес': '📊',
            'недвиж': '🏠',
            'инвест': '📈',
            'рынок': '📊',
            'эконом': '💹',
            'политик': '🌍',
            'новост': '📰',
            'спорт': '⚽',
            'наук': '🔬'
        }
        
        for keyword, emoji in emoji_map.items():
            if keyword in topic_lower:
                return emoji
        
        return '📌'
    
    async def get_user_interests_summary(self, user_id: int) -> Dict[str, Any]:
        """
        Получить сводку интересов пользователя (для API endpoint)
        
        Returns:
            {
                "preferred_topics": List[str],
                "inferred_topics": List[str],
                "combined_topics": List[str]
            }
        """
        db = SessionLocal()
        try:
            settings = db.query(DigestSettings).filter(
                DigestSettings.user_id == user_id
            ).first()
            
            preferred = settings.preferred_topics if settings and settings.preferred_topics else []
            inferred = await self._get_topics_from_history(user_id)
            
            # Комбинируем (preferred имеют приоритет)
            combined = list(preferred)  # Копия
            for topic in inferred:
                if topic.lower() not in [t.lower() for t in combined]:
                    combined.append(topic)
            
            return {
                "preferred_topics": preferred,
                "inferred_topics": inferred,
                "combined_topics": combined
            }
            
        finally:
            db.close()


# Глобальный экземпляр
ai_digest_generator = AIDigestGenerator()

