"""
Shared Auth Manager - упрощенная авторизация с мастер credentials

Использует один набор API_ID/API_HASH для всех пользователей,
но каждый пользователь имеет свою индивидуальную сессию.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError, AuthKeyError, RPCError, SessionPasswordNeededError, PhoneCodeInvalidError
from sqlalchemy.orm import Session

from models import User
from crypto_utils import crypto_manager
from database import SessionLocal

logger = logging.getLogger(__name__)

# Включаем DEBUG для Telethon
logging.getLogger('telethon').setLevel(logging.DEBUG)


class SharedAuthManager:
    """Менеджер авторизации с shared master credentials"""
    
    def __init__(self):
        self.active_clients = {}  # telegram_id -> TelegramClient
        self.phone_code_hashes = {}  # telegram_id -> phone_code_hash
        self.sent_codes = {}  # telegram_id -> SentCode object
        self.sessions_dir = "sessions"
        self._ensure_sessions_dir()
        
        # Загружаем мастер credentials
        self.master_api_id = os.getenv("MASTER_API_ID")
        self.master_api_hash = os.getenv("MASTER_API_HASH")
        
        if not self.master_api_id or not self.master_api_hash:
            logger.error("🚨 MASTER_API_ID и MASTER_API_HASH не установлены в .env!")
            raise ValueError("MASTER_API_ID и MASTER_API_HASH обязательны")
        
        # Настройки безопасности
        self.max_failed_attempts = 5
        self.block_duration = timedelta(hours=1)
        self.rate_limit_window = timedelta(minutes=5)
        self.max_requests_per_window = 3
        
        # Async locks для безопасности
        self.client_locks = {}  # telegram_id -> asyncio.Lock
        
        logger.info(f"✅ SharedAuthManager инициализирован с MASTER_API_ID: {self.master_api_id}")
    
    def _ensure_sessions_dir(self):
        """Создает директорию для сессий"""
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
            os.chmod(self.sessions_dir, 0o700)  # Только owner
    
    def _get_session_path(self, telegram_id: int) -> str:
        """Путь к session файлу пользователя"""
        return os.path.join(self.sessions_dir, f"user_{telegram_id}.session")
    
    def _get_client_lock(self, telegram_id: int) -> asyncio.Lock:
        """Получить или создать lock для пользователя"""
        if telegram_id not in self.client_locks:
            self.client_locks[telegram_id] = asyncio.Lock()
        return self.client_locks[telegram_id]
    
    async def _create_client(self, telegram_id: int) -> TelegramClient:
        """Создать Telethon client для пользователя"""
        session_path = self._get_session_path(telegram_id)
        
        client = TelegramClient(
            session_path,
            int(self.master_api_id),
            self.master_api_hash,
            connection_retries=3,
            retry_delay=5,
            timeout=30,
            request_retries=3
        )
        
        # Автоматический sleep при flood wait < 2 минут
        client.flood_sleep_threshold = 120
        
        # Устанавливаем права доступа на session файл
        if os.path.exists(session_path):
            os.chmod(session_path, 0o600)
        
        logger.info(f"✅ Создан Telethon client для пользователя {telegram_id}")
        return client
    
    def _is_user_blocked(self, user: User) -> bool:
        """Проверка блокировки пользователя"""
        if not user.is_blocked:
            return False
        
        if user.block_expires:
            # Убеждаемся что block_expires timezone-aware
            block_expires = user.block_expires
            if block_expires.tzinfo is None:
                block_expires = block_expires.replace(tzinfo=timezone.utc)
            
            if block_expires > datetime.now(timezone.utc):
                return True
        
        # Разблокируем если время истекло
        user.is_blocked = False
        user.block_expires = None
        user.failed_auth_attempts = 0
        return False
    
    def _check_rate_limit(self, user: User) -> bool:
        """Rate limiting для пользователя"""
        now = datetime.now(timezone.utc)
        
        if not user.last_auth_attempt:
            return True
        
        # Убеждаемся что last_auth_attempt timezone-aware
        last_attempt = user.last_auth_attempt
        if last_attempt.tzinfo is None:
            last_attempt = last_attempt.replace(tzinfo=timezone.utc)
        
        time_since_last = now - last_attempt
        if time_since_last < self.rate_limit_window:
            return user.failed_auth_attempts < self.max_requests_per_window
        
        # Окно истекло - сбрасываем счетчик
        user.failed_auth_attempts = 0
        return True
    
    async def send_code(self, telegram_id: int, phone: str) -> Dict[str, Any]:
        """
        Отправить SMS код на номер телефона
        
        Args:
            telegram_id: Telegram ID пользователя
            phone: Номер телефона в международном формате
            
        Returns:
            Dict с результатом: {"success": bool, "error": str}
        """
        db = SessionLocal()
        
        try:
            # Получаем пользователя
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return {"success": False, "error": "Пользователь не найден"}
            
            # Проверяем блокировку
            if self._is_user_blocked(user):
                return {
                    "success": False, 
                    "error": f"Аккаунт заблокирован до {user.block_expires.strftime('%H:%M')}"
                }
            
            # Проверяем rate limit
            if not self._check_rate_limit(user):
                return {
                    "success": False,
                    "error": "Слишком много попыток. Подождите 5 минут."
                }
            
            # Сохраняем номер (зашифрованный)
            user.set_encrypted_phone_number(phone)
            user.last_auth_attempt = datetime.now(timezone.utc)
            db.commit()
            
            # Создаем клиент с lock
            lock = self._get_client_lock(telegram_id)
            async with lock:
                # КРИТИЧНО: Используем существующий клиент если есть, иначе создаем новый
                if telegram_id in self.active_clients:
                    client = self.active_clients[telegram_id]
                    logger.info(f"♻️ Использую существующий клиент для {telegram_id}")
                    
                    # Переподключаемся если отключен
                    if not client.is_connected():
                        await client.connect()
                else:
                    client = await self._create_client(telegram_id)
                    await client.connect()
                    logger.info(f"🆕 Создан новый клиент для {telegram_id}")
                
                if not client.is_connected():
                    return {"success": False, "error": "Не удалось подключиться к Telegram"}
                
                # Проверяем авторизацию
                if await client.is_user_authorized():
                    logger.info(f"✅ Пользователь {telegram_id} уже авторизован")
                    user.is_authenticated = True
                    db.commit()
                    self.active_clients[telegram_id] = client
                    return {"success": True, "already_authorized": True}
                
                # Отправляем код
                logger.info(f"📱 Отправка кода на {phone} для {telegram_id}")
                sent_code = await client.send_code_request(phone)
                logger.info(f"✅ SMS код отправлен (phone_code_hash: {sent_code.phone_code_hash[:10]}...)")
                
                # КРИТИЧНО: Явно сохраняем session файл после send_code_request
                # Это гарантирует что состояние авторизации записано на диск
                logger.info(f"💾 Сохранение session файла для {telegram_id}")
                client.session.save()
                logger.info(f"✅ Session сохранен на диск")
                
                # КРИТИЧНО: Сохраняем клиент И phone_code_hash для последующего sign_in
                # Этот же клиент и hash ДОЛЖНЫ быть использованы для verify_code!
                self.active_clients[telegram_id] = client
                
                # Сохраняем phone_code_hash в памяти для verify
                self.phone_code_hashes[telegram_id] = sent_code.phone_code_hash
                
                # Сохраняем весь sent_code объект
                self.sent_codes[telegram_id] = sent_code
                
                return {
                    "success": True,
                    "phone_code_hash": sent_code.phone_code_hash
                }
        
        except FloodWaitError as e:
            error_msg = f"Нужно подождать {e.seconds} секунд"
            logger.warning(f"⏳ FloodWait для {telegram_id}: {e.seconds}s")
            user.failed_auth_attempts += 1
            user.auth_error = error_msg
            db.commit()
            return {"success": False, "error": error_msg}
        
        except RPCError as e:
            error_msg = str(e)
            logger.error(f"❌ RPCError при отправке кода для {telegram_id}: {error_msg}")
            user.failed_auth_attempts += 1
            user.auth_error = error_msg
            db.commit()
            return {"success": False, "error": f"Ошибка Telegram: {error_msg}"}
        
        except Exception as e:
            logger.error(f"❌ Ошибка отправки кода для {telegram_id}: {e}")
            user.failed_auth_attempts += 1
            user.auth_error = str(e)
            db.commit()
            return {"success": False, "error": str(e)}
        
        finally:
            db.close()
    
    async def verify_code(self, telegram_id: int, phone: str, code: str) -> Dict[str, Any]:
        """
        Проверить SMS код и авторизовать пользователя
        
        Args:
            telegram_id: Telegram ID пользователя
            phone: Номер телефона
            code: SMS код
            
        Returns:
            Dict с результатом: {"success": bool, "requires_2fa": bool, "error": str}
        """
        db = SessionLocal()
        
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return {"success": False, "error": "Пользователь не найден"}
            
            # Проверяем наличие активного клиента
            if telegram_id not in self.active_clients:
                return {
                    "success": False,
                    "error": "Сессия истекла. Начните процесс заново с /login"
                }
            
            client = self.active_clients[telegram_id]
            
            # КРИТИЧНО: Убеждаемся что клиент подключен
            if not client.is_connected():
                logger.warning(f"⚠️ Клиент отключен! Переподключаемся...")
                await client.connect()
                logger.info(f"✅ Клиент переподключен")
            
            logger.info(f"🔗 Клиент подключен: {client.is_connected()}")
            
            # Получаем сохраненный phone_code_hash
            phone_code_hash = None
            if telegram_id in self.phone_code_hashes:
                phone_code_hash = self.phone_code_hashes[telegram_id]
                logger.info(f"💾 Использую сохраненный phone_code_hash: {phone_code_hash[:10]}...")
            
            try:
                # Авторизуемся по коду с phone_code_hash
                logger.info(f"🔐 Попытка sign_in для {telegram_id} с кодом {code[:2]}***")
                
                if phone_code_hash:
                    await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                else:
                    await client.sign_in(phone, code)
                
                logger.info(f"✅ sign_in выполнен успешно для {telegram_id}")
                
                # Проверяем успешность
                if await client.is_user_authorized():
                    # ✅ КРИТИЧНО: Проверка session владельца
                    me = await client.get_me()
                    if me.id != telegram_id:
                        logger.error(f"🚨 SECURITY: Session mismatch! Expected {telegram_id}, got {me.id}")
                        await client.disconnect()
                        del self.active_clients[telegram_id]
                        return {"success": False, "error": "Ошибка безопасности: несоответствие сессии"}
                    
                    # Все ОК - обновляем пользователя
                    user.is_authenticated = True
                    user.failed_auth_attempts = 0
                    user.auth_error = None
                    user.last_auth_check = datetime.now(timezone.utc)
                    db.commit()
                    
                    # Очищаем phone_code_hash после успешной авторизации
                    if hasattr(self, 'phone_code_hashes') and telegram_id in self.phone_code_hashes:
                        del self.phone_code_hashes[telegram_id]
                    
                    logger.info(f"✅ Пользователь {telegram_id} успешно авторизован")
                    return {"success": True}
                else:
                    return {"success": False, "error": "Не удалось авторизоваться"}
            
            except SessionPasswordNeededError:
                # Требуется 2FA пароль
                logger.info(f"🔐 Пользователю {telegram_id} требуется 2FA")
                return {"success": False, "requires_2fa": True}
            
            except PhoneCodeInvalidError:
                user.failed_auth_attempts += 1
                user.auth_error = "Неверный код"
                
                # Блокируем при превышении лимита
                if user.failed_auth_attempts >= self.max_failed_attempts:
                    user.is_blocked = True
                    user.block_expires = datetime.now(timezone.utc) + self.block_duration
                    logger.warning(f"🚫 Пользователь {telegram_id} заблокирован")
                
                db.commit()
                return {"success": False, "error": "Неверный код"}
            
            except RPCError as e:
                # Специфичные ошибки Telegram
                error_message = str(e)
                logger.error(f"🚨 RPCError при verify_code для {telegram_id}:")
                logger.error(f"   Тип: {type(e).__name__}")
                logger.error(f"   Сообщение: {error_message}")
                
                # Считаем время с учетом timezone
                if user.last_auth_attempt:
                    last_attempt = user.last_auth_attempt
                    if last_attempt.tzinfo is None:
                        last_attempt = last_attempt.replace(tzinfo=timezone.utc)
                    seconds_since = (datetime.now(timezone.utc) - last_attempt).total_seconds()
                    logger.error(f"   Код введен через: {seconds_since:.1f} секунд")
                else:
                    logger.error(f"   Время: N/A")
                
                if "confirmation code has expired" in error_message.lower():
                    return {
                        "success": False,
                        "error": "Код истек. Попробуйте снова и вводите код быстрее (в течение 2-3 минут)"
                    }
                elif "previously shared" in error_message.lower() or "not allowed" in error_message.lower():
                    return {
                        "success": False,
                        "error": "Telegram заблокировал вход по соображениям безопасности. Попробуйте через несколько минут."
                    }
                else:
                    return {"success": False, "error": f"Ошибка Telegram: {error_message}"}
        
        except Exception as e:
            logger.error(f"❌ Ошибка верификации кода для {telegram_id}: {e}")
            return {"success": False, "error": str(e)}
        
        finally:
            db.close()
    
    async def verify_2fa(self, telegram_id: int, password: str) -> Dict[str, Any]:
        """
        Проверить 2FA пароль
        
        Args:
            telegram_id: Telegram ID пользователя
            password: 2FA пароль
            
        Returns:
            Dict с результатом: {"success": bool, "error": str}
        """
        db = SessionLocal()
        
        try:
            user = db.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return {"success": False, "error": "Пользователь не найден"}
            
            if telegram_id not in self.active_clients:
                return {"success": False, "error": "Сессия истекла"}
            
            client = self.active_clients[telegram_id]
            
            try:
                await client.sign_in(password=password)
                
                # ✅ Проверка владельца сессии
                me = await client.get_me()
                if me.id != telegram_id:
                    logger.error(f"🚨 SECURITY: Session mismatch in 2FA!")
                    await client.disconnect()
                    del self.active_clients[telegram_id]
                    return {"success": False, "error": "Ошибка безопасности"}
                
                # Успешная авторизация
                user.is_authenticated = True
                user.failed_auth_attempts = 0
                user.auth_error = None
                user.last_auth_check = datetime.now(timezone.utc)
                db.commit()
                
                logger.info(f"✅ Пользователь {telegram_id} успешно прошел 2FA")
                return {"success": True}
            
            except Exception as e:
                logger.error(f"❌ Неверный 2FA пароль для {telegram_id}: {e}")
                return {"success": False, "error": "Неверный пароль"}
        
        finally:
            db.close()
    
    async def disconnect_client(self, telegram_id: int):
        """Отключить и удалить клиент из активных"""
        if telegram_id in self.active_clients:
            client = self.active_clients[telegram_id]
            try:
                await client.disconnect()
            except:
                pass
            del self.active_clients[telegram_id]
            logger.info(f"🔌 Клиент для {telegram_id} отключен и удален")
        
        # Очищаем также phone_code_hashes и sent_codes
        if telegram_id in self.phone_code_hashes:
            del self.phone_code_hashes[telegram_id]
        if telegram_id in self.sent_codes:
            del self.sent_codes[telegram_id]
    
    async def get_user_client(self, telegram_id: int) -> Optional[TelegramClient]:
        """
        Получить активный клиент пользователя
        
        Args:
            telegram_id: Telegram ID пользователя
            
        Returns:
            TelegramClient или None
        """
        lock = self._get_client_lock(telegram_id)
        
        async with lock:
            # Если клиент уже активен - проверяем event loop
            if telegram_id in self.active_clients:
                client = self.active_clients[telegram_id]
                
                # ВАЖНО: Проверяем что клиент в правильном event loop
                try:
                    if client.is_connected():
                        # Проверяем event loop
                        current_loop = asyncio.get_event_loop()
                        if client.loop != current_loop:
                            logger.warning(f"⚠️ Client {telegram_id} в другом event loop - пересоздаем")
                            await client.disconnect()
                            del self.active_clients[telegram_id]
                        else:
                            return client
                    else:
                        await client.connect()
                        if client.is_connected():
                            return client
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка проверки клиента {telegram_id}: {e} - пересоздаем")
                    if telegram_id in self.active_clients:
                        del self.active_clients[telegram_id]
            
            # Создаем новый клиент в текущем event loop
            client = await self._create_client(telegram_id)
            await client.connect()
            
            if not client.is_connected():
                raise ConnectionError("Не удалось подключиться к Telegram")
            
            # Проверяем авторизацию
            if not await client.is_user_authorized():
                raise ValueError("Пользователь не авторизован")
            
            # ✅ Проверка владельца сессии
            me = await client.get_me()
            if me.id != telegram_id:
                logger.error(f"🚨 SECURITY: Session belongs to {me.id}, not {telegram_id}")
                await client.disconnect()
                raise SecurityError("Session file belongs to another user!")
            
            self.active_clients[telegram_id] = client
            logger.info(f"✅ Client {telegram_id} создан в event loop {id(client.loop)}")
            return client
    
    async def disconnect_client(self, telegram_id: int):
        """Отключить клиент пользователя"""
        if telegram_id in self.active_clients:
            try:
                client = self.active_clients[telegram_id]
                if client.is_connected():
                    await client.disconnect()
                del self.active_clients[telegram_id]
                logger.info(f"🔌 Клиент {telegram_id} отключен")
            except Exception as e:
                logger.error(f"Ошибка отключения клиента {telegram_id}: {e}")
    
    async def cleanup_inactive_clients(self):
        """Очистка неактивных клиентов"""
        inactive = []
        
        for telegram_id, client in self.active_clients.items():
            try:
                if not client.is_connected():
                    inactive.append(telegram_id)
                elif not await client.is_user_authorized():
                    inactive.append(telegram_id)
            except:
                inactive.append(telegram_id)
        
        for telegram_id in inactive:
            await self.disconnect_client(telegram_id)
        
        if inactive:
            logger.info(f"🧹 Очищено {len(inactive)} неактивных клиентов")


# Глобальный экземпляр
shared_auth_manager = SharedAuthManager()

