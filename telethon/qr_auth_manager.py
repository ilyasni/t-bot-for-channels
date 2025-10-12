"""
QR Authentication Manager для Telegram Mini App

Управляет QR-авторизацией через client.qr_login()
Пользователь сканирует QR код в своем Telegram без SMS кодов

ВАЖНО: Использует Redis для shared state между telethon-bot и telethon контейнерами
"""

import asyncio
import logging
import os
import uuid
import base64
import json
import qrcode
from io import BytesIO
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional

import redis

from telethon import TelegramClient
from telethon.errors import RPCError
from sqlalchemy.orm import Session

from models import User, InviteCode
from database import SessionLocal
from shared_auth_manager import shared_auth_manager
from subscription_config import get_subscription_info

logger = logging.getLogger(__name__)


class QRAuthManager:
    """
    Менеджер QR-авторизации через Telegram Mini App
    
    Использует Redis для shared state между telethon-bot и telethon контейнерами
    """
    
    def __init__(self):
        # In-memory хранение активных Telethon клиентов (не shared)
        self.active_clients: Dict[int, TelegramClient] = {}
        
        # Redis для shared state между контейнерами
        redis_host = os.getenv("REDIS_HOST", "redis")
        redis_port = int(os.getenv("REDIS_PORT", 6379))
        redis_password = os.getenv("REDIS_PASSWORD")  # Может быть None
        
        try:
            # Подключаемся к Redis/Valkey
            redis_kwargs = {
                "host": redis_host,
                "port": redis_port,
                "decode_responses": True  # Автоматическая конвертация bytes в str
            }
            
            # Добавляем пароль только если установлен
            if redis_password:
                redis_kwargs["password"] = redis_password
            
            self.redis_client = redis.Redis(**redis_kwargs)
            
            # Проверяем подключение
            self.redis_client.ping()
            logger.info(f"✅ QRAuthManager подключен к Redis ({redis_host}:{redis_port})")
        except Exception as e:
            logger.error(f"❌ Ошибка подключения к Redis: {e}")
            # Fallback на in-memory (для локальной разработки)
            self.redis_client = None
            logger.warning("⚠️ Redis недоступен, используется in-memory storage (не работает между контейнерами!)")
        
        logger.info("✅ QRAuthManager инициализирован")
    
    async def create_qr_session(self, telegram_id: int, invite_code: str) -> Dict[str, Any]:
        """
        Создать QR сессию для авторизации
        
        Args:
            telegram_id: Telegram ID пользователя
            invite_code: Инвайт код для активации подписки
            
        Returns:
            Dict с session_id, token, deep_link, expires
        """
        try:
            # Создаем клиент через shared_auth_manager
            client = await shared_auth_manager._create_client(telegram_id)
            await client.connect()
            
            if not client.is_connected():
                raise ConnectionError("Не удалось подключиться к Telegram")
            
            # Генерируем QR login
            logger.info(f"🔐 Генерация QR login для {telegram_id}")
            qr_login = await client.qr_login()
            
            # Создаем уникальную сессию
            session_id = str(uuid.uuid4())
            
            # ВАЖНО: Используем готовый URL от Telethon (уже с правильным base64 кодированием)
            # qr_login.url уже содержит 'tg://login?token=...' с правильным форматом
            deep_link = qr_login.url
            
            # Сохраняем токен для отображения (опционально, но уже НЕ используем для deep link)
            token_b64 = base64.urlsafe_b64encode(qr_login.token).decode('utf-8').rstrip('=')
            
            # ВАЖНО: Делаем expires timezone-aware (UTC)
            expires = qr_login.expires
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            
            # Сохраняем клиент in-memory (только в текущем процессе)
            self.active_clients[telegram_id] = client
            
            # Сохраняем session metadata в Redis (shared между контейнерами)
            session_data = {
                "token": token_b64,
                "deep_link": deep_link,
                "expires": expires.isoformat(),
                "telegram_id": telegram_id,
                "invite_code": invite_code,
                "authorized": False,
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            
            # Сохраняем в Redis с TTL 10 минут
            if self.redis_client:
                redis_key = f"qr_session:{session_id}"
                self.redis_client.setex(
                    redis_key,
                    600,  # 10 минут TTL
                    json.dumps(session_data)
                )
                logger.info(f"💾 QR сессия сохранена в Redis: {redis_key}")
            
            # Запускаем polling авторизации в фоне
            asyncio.create_task(self._poll_authorization(session_id, qr_login))
            
            logger.info(f"✅ QR сессия создана: {session_id[:8]}... (expires: {expires})")
            
            return {
                "session_id": session_id,
                "token": token_b64,
                "deep_link": deep_link,
                "expires": expires.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания QR сессии для {telegram_id}: {e}")
            raise
    
    def _get_session_from_redis(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Получить session данные из Redis"""
        if not self.redis_client:
            return None
        
        try:
            redis_key = f"qr_session:{session_id}"
            data = self.redis_client.get(redis_key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.error(f"❌ Ошибка чтения из Redis: {e}")
        
        return None
    
    def _update_session_status(self, session_id: str, status: str, error: Optional[str]):
        """Обновить статус сессии в Redis"""
        if not self.redis_client:
            return
        
        try:
            redis_key = f"qr_session:{session_id}"
            data = self.redis_client.get(redis_key)
            if data:
                session = json.loads(data)
                session["authorized"] = (status == "authorized")
                if error:
                    session["error"] = error
                # Сохраняем обратно с сохранением TTL
                ttl = self.redis_client.ttl(redis_key)
                if ttl > 0:
                    self.redis_client.setex(redis_key, ttl, json.dumps(session))
                logger.info(f"💾 Статус обновлен в Redis: {session_id[:8]}... → {status}")
        except Exception as e:
            logger.error(f"❌ Ошибка обновления Redis: {e}")
    
    async def _poll_authorization(self, session_id: str, qr_login):
        """
        Проверяем авторизацию в фоне
        
        Args:
            session_id: ID сессии  
            qr_login: QR login объект от Telethon
        """
        # Получаем session data из Redis
        session_data = self._get_session_from_redis(session_id)
        if not session_data:
            logger.warning(f"⚠️ Сессия {session_id[:8]}... не найдена в Redis")
            return
        
        telegram_id = session_data["telegram_id"]
        client = self.active_clients.get(telegram_id)
        
        if not client:
            logger.error(f"❌ Клиент не найден для {telegram_id} (создан в другом процессе)")
            return
        
        try:
            logger.info(f"⏳ Ожидание авторизации для сессии {session_id[:8]}...")
            
            # Ждем авторизации (timeout 5 минут)
            await qr_login.wait(timeout=300)
            
            # Проверяем что авторизовались
            if await client.is_user_authorized():
                logger.info(f"✅ QR авторизация успешна для {session_id[:8]}...")
                
                # Обновляем статус в Redis
                self._update_session_status(session_id, "authorized", None)
                
                # Финализируем
                await self._finalize_authorization(session_id)
            else:
                logger.warning(f"⚠️ Авторизация не завершена для {session_id[:8]}...")
                self._update_session_status(session_id, "waiting", "not_authorized")
                
        except asyncio.TimeoutError:
            logger.warning(f"⏰ Timeout авторизации для {session_id[:8]}...")
            self._update_session_status(session_id, "waiting", "timeout")
            
        except RPCError as e:
            logger.error(f"❌ RPCError при авторизации {session_id[:8]}...: {e}")
            self._update_session_status(session_id, "waiting", f"rpc_error: {str(e)}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка при авторизации {session_id[:8]}...: {e}")
            self._update_session_status(session_id, "waiting", str(e))
    
    async def _finalize_authorization(self, session_id: str):
        """
        Завершить авторизацию после успеха
        
        Args:
            session_id: ID сессии
        """
        # Получаем session data из Redis
        session_data = self._get_session_from_redis(session_id)
        if not session_data:
            logger.error(f"❌ Сессия {session_id[:8]}... не найдена при финализации")
            return
        
        telegram_id = session_data["telegram_id"]
        invite_code = session_data["invite_code"]
        client = self.active_clients.get(telegram_id)
        
        if not client:
            logger.error(f"❌ Клиент не найден для {telegram_id}")
            return
        
        try:
            # КРИТИЧНО: Проверка владельца session
            me = await client.get_me()
            if me.id != telegram_id:
                logger.error(f"🚨 SECURITY: Session mismatch! Expected {telegram_id}, got {me.id}")
                await client.disconnect()
                self._update_session_status(session_id, "waiting", "security_mismatch")
                return
            
            # Сохраняем клиент в shared_auth_manager
            shared_auth_manager.active_clients[telegram_id] = client
            
            # Обновляем пользователя в БД (только PostgreSQL)
            db = SessionLocal()
            
            try:
                user = db.query(User).filter(User.telegram_id == telegram_id).first()
                if not user:
                    logger.error(f"❌ Пользователь {telegram_id} не найден в БД")
                    self._update_session_status(session_id, "waiting", "user_not_found")
                    return
                
                # Обновляем статус авторизации (timezone-aware)
                user.is_authenticated = True
                user.failed_auth_attempts = 0
                user.auth_error = None
                user.last_auth_check = datetime.now(timezone.utc)
                
                # Активируем подписку из invite code
                invite = db.query(InviteCode).filter(InviteCode.code == invite_code).first()
                if invite and invite.is_valid():
                    # Используем метод use() для корректной активации
                    invite.use(user.id)
                    
                    # Получаем информацию о subscription tier
                    subscription_info = get_subscription_info(invite.default_subscription)
                    
                    # Устанавливаем подписку и лимиты
                    user.subscription_type = invite.default_subscription
                    user.subscription_started_at = datetime.now(timezone.utc)
                    user.max_channels = subscription_info['max_channels']
                    
                    # Если есть trial период
                    if invite.default_trial_days and invite.default_trial_days > 0:
                        user.subscription_expires = datetime.now(timezone.utc) + timedelta(days=invite.default_trial_days)
                    
                    logger.info(f"💎 Подписка {invite.default_subscription} активирована для {telegram_id} (лимит каналов: {user.max_channels})")
                
                db.commit()
                logger.info(f"✅ QR авторизация завершена для {telegram_id}")
                
            except Exception as e:
                db.rollback()
                logger.error(f"❌ Ошибка обновления БД для {telegram_id}: {e}")
                self._update_session_status(session_id, "waiting", f"db_error: {str(e)}")
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Ошибка финализации авторизации для {session_id[:8]}...: {e}")
            self._update_session_status(session_id, "waiting", str(e))
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Получить статус сессии из Redis
        
        Args:
            session_id: ID сессии
            
        Returns:
            Dict со статусом сессии
        """
        # Читаем из Redis
        session_data = self._get_session_from_redis(session_id)
        if not session_data:
            return {"status": "not_found"}
        
        # ВАЖНО: Сначала проверяем authorized (успешная авторизация не зависит от expires)
        if session_data.get("authorized"):
            return {
                "status": "authorized",
                "telegram_id": session_data["telegram_id"],
                "expires": session_data["expires"]
            }
        
        # Проверяем не истекла ли сессия (timezone-aware)
        expires_str = session_data["expires"]
        expires = datetime.fromisoformat(expires_str)
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        
        now = datetime.now(timezone.utc)
        
        if now > expires:
            return {
                "status": "expired",
                "error": "QR код истек"
            }
        
        # Ожидание авторизации
        return {
            "status": "waiting",
            "error": session_data.get("error"),
            "expires": expires_str,
            "telegram_id": session_data["telegram_id"]
        }
    
    def cleanup_old_sessions(self, max_age_hours: int = 1):
        """
        Очистка старых сессий в Redis
        
        Args:
            max_age_hours: Максимальный возраст сессии в часах
        """
        if not self.redis_client:
            return
        
        try:
            # Ищем все QR сессии в Redis
            pattern = "qr_session:*"
            keys = self.redis_client.keys(pattern)
            
            now = datetime.now(timezone.utc)
            removed = 0
            
            for key in keys:
                try:
                    data = self.redis_client.get(key)
                    if data:
                        session = json.loads(data)
                        created_at = datetime.fromisoformat(session["created_at"])
                        
                        if (now - created_at).total_seconds() > max_age_hours * 3600:
                            self.redis_client.delete(key)
                            removed += 1
                except Exception:
                    pass
            
            if removed > 0:
                logger.info(f"🗑️ Очищено старых QR сессий: {removed}")
                
        except Exception as e:
            logger.error(f"❌ Ошибка очистки сессий: {e}")


# Глобальный экземпляр
qr_auth_manager = QRAuthManager()

