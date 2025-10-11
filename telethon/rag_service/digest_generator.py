"""
Генератор дайджестов постов
"""
import logging
import sys
import os
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict

# Добавляем родительскую директорию в path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import Post, Channel, DigestSettings
from generator import rag_generator
import config

logger = logging.getLogger(__name__)


class DigestGenerator:
    """Генератор дайджестов"""
    
    def __init__(self):
        """Инициализация генератора дайджестов"""
        self.rag_generator = rag_generator
        self.ai_digest_generator = None  # Lazy load
        logger.info("✅ Digest Generator инициализирован")
    
    async def generate_digest(
        self,
        user_id: int,
        date_from: datetime,
        date_to: datetime,
        channels: Optional[List[int]] = None,
        tags: Optional[List[str]] = None,
        format: str = "markdown",
        max_posts: int = 20
    ) -> Dict[str, Any]:
        """
        Сгенерировать дайджест постов
        
        Args:
            user_id: ID пользователя
            date_from: Начало периода
            date_to: Конец периода
            channels: Фильтр по каналам
            tags: Фильтр по тегам
            format: Формат (markdown/html/plain)
            max_posts: Максимум постов в дайджесте
            
        Returns:
            Словарь с дайджестом
        """
        try:
            logger.info(f"📰 Генерация дайджеста для user {user_id}: {date_from} - {date_to}")
            
            # Проверяем, включена ли AI-суммаризация
            db = SessionLocal()
            settings = db.query(DigestSettings).filter(
                DigestSettings.user_id == user_id
            ).first()
            
            # Если AI включен - используем AI-дайджест
            if settings and settings.ai_summarize:
                db.close()
                logger.info(f"🤖 Используем AI-дайджест для user {user_id}")
                
                # Lazy load AI generator
                if self.ai_digest_generator is None:
                    from ai_digest_generator import ai_digest_generator
                    self.ai_digest_generator = ai_digest_generator
                
                digest_text = await self.ai_digest_generator.generate_ai_digest(
                    user_id=user_id,
                    date_from=date_from,
                    date_to=date_to,
                    preferred_topics=settings.preferred_topics,
                    topics_limit=settings.topics_limit,
                    summary_style=settings.summary_style
                )
                
                # Подсчитаем количество постов для статистики
                db2 = SessionLocal()
                try:
                    posts_count = db2.query(Post).filter(
                        Post.user_id == user_id,
                        Post.posted_at >= date_from,
                        Post.posted_at <= date_to
                    ).count()
                finally:
                    db2.close()
                
                return {
                    "user_id": user_id,
                    "period": {"from": date_from, "to": date_to},
                    "posts_count": posts_count,
                    "digest": digest_text,
                    "format": "markdown",
                    "ai_generated": True,
                    "generated_at": datetime.now()
                }
            
            # Обычный дайджест (без AI)
            # Получаем посты за период
            try:
                query = db.query(Post).filter(
                    Post.user_id == user_id,
                    Post.posted_at >= date_from,
                    Post.posted_at <= date_to
                )
                
                if channels:
                    query = query.filter(Post.channel_id.in_(channels))
                
                if tags:
                    # Фильтр по тегам (JSON содержит хотя бы один из тегов)
                    from sqlalchemy import func
                    for tag in tags:
                        query = query.filter(
                            func.json_contains(Post.tags, f'"{tag}"')
                        )
                
                posts = query.order_by(Post.posted_at.desc()).limit(max_posts).all()
                
                if not posts:
                    return {
                        "user_id": user_id,
                        "period": {"from": date_from, "to": date_to},
                        "posts_count": 0,
                        "digest": "За указанный период постов не найдено.",
                        "format": format,
                        "generated_at": datetime.now()
                    }
                
                # Группируем посты по каналам
                posts_by_channel = defaultdict(list)
                for post in posts:
                    posts_by_channel[post.channel.channel_username].append(post)
                
                # Генерируем дайджест в зависимости от формата
                if format == "markdown":
                    digest = self._generate_markdown_digest(posts_by_channel, date_from, date_to)
                elif format == "html":
                    digest = self._generate_html_digest(posts_by_channel, date_from, date_to)
                else:  # plain
                    digest = self._generate_plain_digest(posts_by_channel, date_from, date_to)
                
                logger.info(f"✅ Дайджест сгенерирован для user {user_id} ({len(posts)} постов)")
                
                return {
                    "user_id": user_id,
                    "period": {"from": date_from, "to": date_to},
                    "posts_count": len(posts),
                    "digest": digest,
                    "format": format,
                    "generated_at": datetime.now()
                }
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Ошибка генерации дайджеста: {e}")
            raise
    
    def _generate_markdown_digest(
        self,
        posts_by_channel: Dict[str, List],
        date_from: datetime,
        date_to: datetime
    ) -> str:
        """Сгенерировать дайджест в формате Markdown"""
        lines = []
        
        # Заголовок
        lines.append(f"# 📰 Дайджест постов")
        lines.append(f"**Период:** {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
        lines.append("")
        
        # Посты по каналам
        for channel_username, posts in sorted(posts_by_channel.items()):
            lines.append(f"## 📢 @{channel_username}")
            lines.append(f"*Постов: {len(posts)}*")
            lines.append("")
            
            for post in posts:
                # Дата и теги
                date_str = post.posted_at.strftime('%d.%m.%Y %H:%M')
                tags_str = ""
                if post.tags:
                    tags_str = " | " + ", ".join([f"`{tag}`" for tag in post.tags[:3]])
                
                lines.append(f"### {date_str}{tags_str}")
                
                # Текст (первые 300 символов)
                text = post.text[:300] + "..." if len(post.text) > 300 else post.text
                lines.append(text)
                
                # Ссылка
                if post.url:
                    lines.append(f"[Читать полностью →]({post.url})")
                
                lines.append("")
        
        return "\n".join(lines)
    
    def _generate_html_digest(
        self,
        posts_by_channel: Dict[str, List],
        date_from: datetime,
        date_to: datetime
    ) -> str:
        """Сгенерировать дайджест в формате HTML"""
        lines = []
        
        lines.append("<html><body>")
        lines.append(f"<h1>📰 Дайджест постов</h1>")
        lines.append(f"<p><b>Период:</b> {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}</p>")
        
        for channel_username, posts in sorted(posts_by_channel.items()):
            lines.append(f"<h2>📢 @{channel_username}</h2>")
            lines.append(f"<p><i>Постов: {len(posts)}</i></p>")
            
            for post in posts:
                date_str = post.posted_at.strftime('%d.%m.%Y %H:%M')
                
                lines.append("<div style='margin-bottom: 20px;'>")
                lines.append(f"<h3>{date_str}</h3>")
                
                text = post.text[:300] + "..." if len(post.text) > 300 else post.text
                lines.append(f"<p>{text}</p>")
                
                if post.url:
                    lines.append(f"<a href='{post.url}'>Читать полностью →</a>")
                
                lines.append("</div>")
        
        lines.append("</body></html>")
        
        return "\n".join(lines)
    
    def _generate_plain_digest(
        self,
        posts_by_channel: Dict[str, List],
        date_from: datetime,
        date_to: datetime
    ) -> str:
        """Сгенерировать дайджест в plain text"""
        lines = []
        
        lines.append("=" * 60)
        lines.append("ДАЙДЖЕСТ ПОСТОВ")
        lines.append(f"Период: {date_from.strftime('%d.%m.%Y')} - {date_to.strftime('%d.%m.%Y')}")
        lines.append("=" * 60)
        lines.append("")
        
        for channel_username, posts in sorted(posts_by_channel.items()):
            lines.append(f"@{channel_username} ({len(posts)} постов)")
            lines.append("-" * 60)
            
            for post in posts:
                date_str = post.posted_at.strftime('%d.%m.%Y %H:%M')
                lines.append(f"{date_str}")
                
                text = post.text[:300] + "..." if len(post.text) > 300 else post.text
                lines.append(text)
                
                if post.url:
                    lines.append(f"Ссылка: {post.url}")
                
                lines.append("")
        
        return "\n".join(lines)


# Глобальный экземпляр генератора
digest_generator = DigestGenerator()

