#!/usr/bin/env python3
"""
Однократный скрипт для индексации старых постов в Neo4j

Использование:
    docker exec rag-service python /app/scripts/backfill_neo4j.py

Индексирует посты с тегами в Neo4j Knowledge Graph
"""
import asyncio
import sys
import os

# Добавляем путь к родительской директории
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import Post, User
from graph.neo4j_client import neo4j_client


async def backfill_posts(limit: int = 1000):
    """
    Индексировать старые посты в Neo4j
    
    Args:
        limit: Максимальное количество постов для индексации
    """
    
    if not neo4j_client or not neo4j_client.enabled:
        print("❌ Neo4j не включен в конфигурации")
        print("   Проверьте переменные окружения:")
        print("   - NEO4J_URI")
        print("   - NEO4J_USER")
        print("   - NEO4J_PASSWORD")
        return
    
    db = SessionLocal()
    try:
        # Посты с тегами (только они имеют смысл для графа)
        print(f"🔍 Поиск постов для индексации (limit={limit})...")
        
        posts = db.query(Post).filter(
            Post.tags.isnot(None)
        ).limit(limit).all()
        
        if not posts:
            print("✅ Нет постов для индексации")
            return
        
        print(f"📊 Найдено {len(posts)} постов для индексации в Neo4j...")
        print(f"   (Посты с тегами)")
        print()
        
        success_count = 0
        error_count = 0
        
        for i, post in enumerate(posts):
            try:
                user = post.user
                channel = post.channel
                
                if not user or not channel:
                    print(f"   ⚠️  Post {post.id}: пропущен (нет user или channel)")
                    continue
                
                # Создать User node
                await neo4j_client.create_user_node(
                    telegram_id=user.telegram_id,
                    username=user.username
                )
                
                # Создать Post node со связями
                await neo4j_client.create_post_node(
                    post_id=post.id,
                    user_id=user.telegram_id,
                    channel_id=f"@{channel.channel_username}",
                    title=post.text[:100] if post.text else "No title",
                    content=post.text,
                    tags=post.tags,
                    created_at=post.posted_at.isoformat() if post.posted_at else None
                )
                
                success_count += 1
                
                # Прогресс каждые 100 постов
                if (i + 1) % 100 == 0:
                    print(f"   ✅ {i+1}/{len(posts)} постов проиндексировано")
                
            except Exception as e:
                error_count += 1
                print(f"   ❌ Post {post.id}: {str(e)[:100]}")
        
        print()
        print("=" * 60)
        print(f"✅ Backfill завершен:")
        print(f"   Успешно: {success_count} постов")
        print(f"   Ошибок: {error_count}")
        print(f"   Всего обработано: {success_count + error_count}")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Критическая ошибка backfill: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


async def verify_backfill():
    """Проверить результаты backfill"""
    
    if not neo4j_client or not neo4j_client.enabled:
        print("❌ Neo4j недоступен для проверки")
        return
    
    try:
        # Проверяем health check
        is_healthy = await neo4j_client.health_check()
        
        if is_healthy:
            print("✅ Neo4j подключение активно")
        else:
            print("❌ Neo4j не отвечает")
            
    except Exception as e:
        print(f"❌ Ошибка проверки: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("Neo4j Backfill Script")
    print("=" * 60)
    print()
    
    # Проверяем аргументы
    limit = 1000
    if len(sys.argv) > 1:
        try:
            limit = int(sys.argv[1])
            print(f"📊 Лимит установлен: {limit} постов")
        except ValueError:
            print(f"⚠️  Неверный лимит: {sys.argv[1]}, используем {limit}")
    
    print()
    
    # Запускаем backfill
    asyncio.run(backfill_posts(limit=limit))
    
    print()
    print("🔍 Проверка подключения к Neo4j...")
    asyncio.run(verify_backfill())

