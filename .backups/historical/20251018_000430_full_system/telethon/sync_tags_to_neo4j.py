#!/usr/bin/env python3
"""
Скрипт для синхронизации тегов из PostgreSQL в Neo4j
Best practice: синхронизация данных между системами
"""

import asyncio
import os
import sys
from typing import List, Optional

# Добавляем путь к модулям
sys.path.append('/app')

from database import SessionLocal
from models import Post
from graph.neo4j_client import neo4j_client
from logging_config import get_logger

logger = get_logger('sync_tags')

async def sync_tags_to_neo4j(limit: Optional[int] = None):
    """
    Синхронизирует теги из PostgreSQL в Neo4j
    
    Args:
        limit: Максимальное количество постов для обработки (None = все)
    """
    if not neo4j_client.enabled:
        logger.error("❌ Neo4j client disabled")
        return
    
    db = SessionLocal()
    try:
        # Получаем посты с тегами
        query = db.query(Post).filter(Post.tags.isnot(None))
        if limit:
            query = query.limit(limit)
        
        posts = query.all()
        logger.info(f"📊 Found {len(posts)} posts with tags")
        
        if not posts:
            logger.warning("⚠️ No posts with tags found")
            return
        
        # Синхронизируем каждый пост
        synced_count = 0
        error_count = 0
        
        for post in posts:
            try:
                # Обновляем пост в Neo4j с тегами
                await neo4j_client.create_post_node(
                    post_id=post.id,
                    user_id=post.user_id,
                    channel_id=f"@{post.channel.channel_username}" if post.channel else "unknown",
                    title=post.text[:100] if post.text else "No title",
                    content=post.text,
                    tags=post.tags or [],
                    created_at=post.posted_at.isoformat() if post.posted_at else None
                )
                
                synced_count += 1
                if synced_count % 50 == 0:
                    logger.info(f"📊 Synced {synced_count}/{len(posts)} posts")
                    
            except Exception as e:
                logger.error(f"❌ Failed to sync post {post.id}: {e}")
                error_count += 1
        
        logger.info(f"✅ Sync completed: {synced_count} synced, {error_count} errors")
        
        # Проверяем результат
        await verify_sync()
        
    except Exception as e:
        logger.error(f"❌ Sync failed: {e}")
    finally:
        db.close()

async def verify_sync():
    """Проверяет результат синхронизации"""
    try:
        async with neo4j_client.driver.session() as session:
            # Проверяем количество тегов
            result = await session.run('MATCH (t:Tag) RETURN count(t) as tag_count')
            record = await result.single()
            tag_count = record['tag_count'] if record else 0
            
            # Проверяем количество связей HAS_TAG
            result = await session.run('MATCH ()-[r:HAS_TAG]->() RETURN count(r) as has_tag_count')
            record = await result.single()
            has_tag_count = record['has_tag_count'] if record else 0
            
            logger.info(f"📊 Neo4j after sync:")
            logger.info(f"  - Tags: {tag_count}")
            logger.info(f"  - HAS_TAG relationships: {has_tag_count}")
            
            if tag_count > 0 and has_tag_count > 0:
                logger.info("✅ Tags successfully synced to Neo4j!")
            else:
                logger.warning("⚠️ No tags found in Neo4j after sync")
                
    except Exception as e:
        logger.error(f"❌ Verification failed: {e}")

async def main():
    """Главная функция"""
    logger.info("🚀 Starting tags sync to Neo4j...")
    
    # Проверяем подключение к Neo4j
    if not await neo4j_client.health_check():
        logger.error("❌ Neo4j health check failed")
        return
    
    # Синхронизируем теги
    await sync_tags_to_neo4j(limit=100)  # Начнем с 100 постов
    
    logger.info("🎉 Tags sync completed!")

if __name__ == "__main__":
    asyncio.run(main())
