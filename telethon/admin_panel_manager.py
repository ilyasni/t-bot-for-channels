"""
Admin Panel Manager для Telegram Mini App

Управляет admin sessions через Redis для безопасного доступа к админ панели
Изолирован от QR Login (разные prefixes: admin_session: vs qr_session:)
"""

import logging
import os
import uuid
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

import redis

from database import SessionLocal
from models import User

logger = logging.getLogger(__name__)


class AdminPanelManager:
    """
    Менеджер админ панели
    
    Использует Redis для хранения admin sessions
    TTL: 1 час (после этого нужно заново открыть /admin)
    """
    
    def __init__(self):
        # Redis для admin sessions
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD")
        
        try:
            redis_kwargs = {
                "host": redis_host,
                "port": redis_port,
                "decode_responses": True
            }
            
            if redis_password:
                redis_kwargs["password"] = redis_password
            
            self.redis_client = redis.Redis(**redis_kwargs)
            self.redis_client.ping()
            
            logger.info(f"✅ AdminPanelManager подключен к Redis ({redis_host}:{redis_port})")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Redis: {e}")
            self.redis_client = None
            raise RuntimeError("AdminPanelManager требует Redis для работы")
        
        self.session_ttl = 3600  # 1 час
        logger.info("✅ AdminPanelManager инициализирован")
    
    def create_admin_session(self, telegram_id: int) -> Optional[str]:
        """
        Создать admin session в Redis
        
        Args:
            telegram_id: Telegram ID администратора
            
        Returns:
            Session token или None если не админ
        """
        # Проверяем права админа в PostgreSQL
        db = SessionLocal()
        
        try:
            user = db.query(User).filter(
                User.telegram_id == telegram_id,
                User.role == "admin"
            ).first()
            
            if not user:
                logger.warning(f"⚠️ Попытка создания admin session от не-админа: {telegram_id}")
                return None
            
            # Генерируем уникальный token
            session_token = str(uuid.uuid4())
            
            # Создаем session data
            session_data = {
                "admin_id": telegram_id,
                "admin_name": user.first_name,
                "role": user.role,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires": (datetime.now(timezone.utc) + timedelta(seconds=self.session_ttl)).isoformat()
            }
            
            # Сохраняем в Redis с TTL
            redis_key = f"admin_session:{session_token}"
            self.redis_client.setex(
                redis_key,
                self.session_ttl,
                json.dumps(session_data)
            )
            
            logger.info(f"✅ Admin session создана для {telegram_id} ({user.first_name})")
            
            return session_token
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания admin session: {e}")
            return None
        finally:
            db.close()
    
    def verify_admin_session(self, token: str, admin_id: int) -> bool:
        """
        Проверить валидность admin session
        
        Args:
            token: Session token
            admin_id: Telegram ID для проверки
            
        Returns:
            True если session валидна и принадлежит admin_id
        """
        if not self.redis_client:
            return False
        
        try:
            redis_key = f"admin_session:{token}"
            data = self.redis_client.get(redis_key)
            
            if not data:
                logger.warning(f"⚠️ Admin session не найдена: {token[:8]}...")
                return False
            
            session_data = json.loads(data)
            
            # Проверяем что admin_id совпадает
            if session_data["admin_id"] != admin_id:
                logger.warning(f"🚨 Admin session mismatch: {admin_id} != {session_data['admin_id']}")
                return False
            
            # Проверяем expires (timezone-aware)
            expires = datetime.fromisoformat(session_data["expires"])
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            
            if datetime.now(timezone.utc) > expires:
                logger.warning(f"⏰ Admin session истекла: {token[:8]}...")
                self.redis_client.delete(redis_key)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка проверки admin session: {e}")
            return False
    
    def get_session_data(self, token: str) -> Optional[Dict[str, Any]]:
        """
        Получить данные admin session
        
        Args:
            token: Session token
            
        Returns:
            Session data или None
        """
        if not self.redis_client:
            return None
        
        try:
            redis_key = f"admin_session:{token}"
            data = self.redis_client.get(redis_key)
            
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"❌ Ошибка чтения session: {e}")
        
        return None
    
    def invalidate_session(self, token: str):
        """
        Инвалидировать admin session
        
        Args:
            token: Session token
        """
        if not self.redis_client:
            return
        
        try:
            redis_key = f"admin_session:{token}"
            self.redis_client.delete(redis_key)
            logger.info(f"✅ Admin session удалена: {token[:8]}...")
        except Exception as e:
            logger.error(f"❌ Ошибка удаления session: {e}")


# Глобальный экземпляр
admin_panel_manager = AdminPanelManager()

