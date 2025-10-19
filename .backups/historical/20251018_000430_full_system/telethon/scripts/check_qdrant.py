#!/usr/bin/env python3
"""
Проверка состояния Qdrant коллекций и индексации
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import SessionLocal
from models import User, Post, IndexingStatus
from datetime import datetime, timedelta, timezone

def check_qdrant():
    """Проверить состояние индексации"""
    db = SessionLocal()
    
    try:
        print("=" * 80)
        print("🔍 ПРОВЕРКА ИНДЕКСАЦИИ В QDRANT")
        print("=" * 80)
        print()
        
        # Получаем всех пользователей
        users = db.query(User).all()
        
        for user in users:
            print(f"{'='*80}")
            print(f"🔹 USER ID: {user.id} | Telegram ID: {user.telegram_id}")
            print(f"{'='*80}")
            
            # Посты за последние 24 часа
            now = datetime.now(timezone.utc)
            date_from = now - timedelta(days=1)
            
            posts_count = db.query(Post).filter(
                Post.user_id == user.id,
                Post.posted_at >= date_from
            ).count()
            
            print(f"📰 Посты за последние 24 часа: {posts_count}")
            
            # Индексированные посты
            indexed_count = db.query(IndexingStatus).filter(
                IndexingStatus.user_id == user.id,
                IndexingStatus.status == "success"
            ).count()
            
            print(f"✅ Проиндексировано в Qdrant: {indexed_count}")
            
            # Ошибки индексации
            failed_count = db.query(IndexingStatus).filter(
                IndexingStatus.user_id == user.id,
                IndexingStatus.status == "failed"
            ).count()
            
            if failed_count > 0:
                print(f"❌ Ошибки индексации: {failed_count}")
                
                # Последние ошибки
                failed = db.query(IndexingStatus).filter(
                    IndexingStatus.user_id == user.id,
                    IndexingStatus.status == "failed"
                ).order_by(IndexingStatus.indexed_at.desc()).limit(3).all()
                
                print(f"\n   Последние ошибки:")
                for idx in failed:
                    error_preview = idx.error[:100] if idx.error else "N/A"
                    print(f"      • Post {idx.post_id}: {error_preview}...")
            
            # Посты без индексации
            posts_without_index = db.query(Post).filter(
                Post.user_id == user.id,
                ~Post.id.in_(
                    db.query(IndexingStatus.post_id).filter(
                        IndexingStatus.user_id == user.id
                    )
                )
            ).count()
            
            print(f"⚠️  Посты без индексации: {posts_without_index}")
            
            if posts_without_index > 0:
                print(f"   → Эти посты не попадут в векторный поиск!")
                print(f"   → Нужно запустить индексацию: POST /rag/index/user/{user.id}")
            
            # Последняя индексация
            last_indexed = db.query(IndexingStatus).filter(
                IndexingStatus.user_id == user.id,
                IndexingStatus.status == "success"
            ).order_by(IndexingStatus.indexed_at.desc()).first()
            
            if last_indexed:
                print(f"\n📅 Последняя индексация: {last_indexed.indexed_at}")
            else:
                print(f"\n❌ Индексация НИКОГДА не выполнялась!")
            
            print()
        
        print("=" * 80)
        print("✅ Проверка завершена")
        print("=" * 80)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    check_qdrant()

