"""
Безопасный менеджер аутентификации с веб-интерфейсом
Устраняет небезопасный ввод кодов через Telegram чат
"""

import asyncio
import logging
import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from telethon import TelegramClient
from telethon.errors import FloodWaitError, AuthKeyError, RPCError, SessionPasswordNeededError
from sqlalchemy.orm import Session

from models import User
from crypto_utils import crypto_manager
from database import SessionLocal

logger = logging.getLogger(__name__)

class SecureAuthManager:
    """Безопасный менеджер аутентификации"""
    
    def __init__(self):
        self.active_clients = {}  # Словарь активных клиентов по user_id
        self.auth_sessions = {}  # Временные сессии аутентификации
        self.sessions_dir = "sessions"
        self._ensure_sessions_dir()
        
        # Настройки безопасности
        self.max_failed_attempts = 5  # Максимум неудачных попыток
        self.block_duration = timedelta(hours=1)  # Время блокировки
        self.session_timeout = timedelta(hours=2)  # Таймаут сессии аутентификации
        
        # Настройка часового пояса
        import os
        self.timezone_name = os.getenv('TZ', 'Europe/Moscow')
        try:
            import zoneinfo
            self.local_tz = zoneinfo.ZoneInfo(self.timezone_name)
        except ImportError:
            # Fallback для старых версий Python
            from datetime import timezone
            # Для MSK (UTC+3)
            self.local_tz = timezone(timedelta(hours=3))
        self.rate_limit_window = timedelta(minutes=5)  # Окно для rate limiting
        self.max_requests_per_window = 3  # Максимум запросов в окне
    
    def _ensure_sessions_dir(self):
        """Создает директорию для сессий если её нет"""
        import os
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
    
    def _get_session_path(self, user_id: int) -> str:
        """Генерирует путь к файлу сессии для пользователя"""
        import os
        return os.path.join(self.sessions_dir, f"user_{user_id}.session")
    
    def _generate_session_id(self) -> str:
        """Генерирует уникальный ID сессии аутентификации"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(32))
    
    def _now(self) -> datetime:
        """Получает текущее время в UTC для сохранения в БД"""
        return datetime.now(timezone.utc)
    
    def _is_user_blocked(self, user: User) -> bool:
        """Проверяет, заблокирован ли пользователь"""
        if not user.is_blocked:
            return False
        
        if user.block_expires and user.block_expires > self._now():
            return True
        
        # Разблокируем пользователя если время блокировки истекло
        user.is_blocked = False
        user.block_expires = None
        user.failed_auth_attempts = 0
        return False
    
    def _check_rate_limit(self, user: User) -> bool:
        """Проверяет rate limiting для пользователя"""
        now = self._now()
        
        if not user.last_auth_attempt:
            return True
        
        time_since_last = now - user.last_auth_attempt
        if time_since_last < self.rate_limit_window:
            # В окне rate limiting - проверяем количество попыток
            # Для простоты считаем только последние попытки
            return user.failed_auth_attempts < self.max_requests_per_window
        
        # Окно истекло - сбрасываем счетчик
        user.failed_auth_attempts = 0
        return True
    
    async def _update_user_auth_status(self, user: User, is_authenticated: bool, error: str = None):
        """Обновление статуса аутентификации в БД"""
        try:
            db = SessionLocal()
            db_user = db.query(User).filter(User.id == user.id).first()
            
            if db_user:
                db_user.is_authenticated = is_authenticated
                db_user.last_auth_check = self._now()
                db_user.last_auth_attempt = self._now()
                
                if error:
                    db_user.auth_error = error
                    db_user.failed_auth_attempts += 1
                    
                    # Блокируем пользователя при превышении лимита
                    if db_user.failed_auth_attempts >= self.max_failed_attempts:
                        db_user.is_blocked = True
                        db_user.block_expires = self._now() + self.block_duration
                        logger.warning(f"🚫 Пользователь {user.telegram_id} заблокирован до {db_user.block_expires}")
                else:
                    db_user.auth_error = None
                    db_user.failed_auth_attempts = 0
                    db_user.is_blocked = False
                    db_user.block_expires = None
                
                db.commit()
            
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса аутентификации: {str(e)}")
    
    async def create_auth_session(self, user: User) -> Optional[str]:
        """
        Создает сессию аутентификации для пользователя
        
        Args:
            user: Пользователь
            
        Returns:
            str: ID сессии или None при ошибке
        """
        try:
            # Проверяем блокировку
            if self._is_user_blocked(user):
                logger.warning(f"🚫 Пользователь {user.telegram_id} заблокирован")
                return None
            
            # Проверяем rate limiting
            if not self._check_rate_limit(user):
                logger.warning(f"🚫 Rate limit для пользователя {user.telegram_id}")
                return None
            
            # Генерируем ID сессии
            session_id = self._generate_session_id()
            
            # Создаем временную сессию
            self.auth_sessions[session_id] = {
                'user_id': user.id,
                'telegram_id': user.telegram_id,
                'created_at': self._now(),
                'expires_at': self._now() + self.session_timeout,
                'status': 'created'
            }
            
            # Обновляем пользователя в БД
            db = SessionLocal()
            db_user = db.query(User).filter(User.id == user.id).first()
            if db_user:
                db_user.auth_session_id = session_id
                db_user.auth_session_expires = self._now() + self.session_timeout
                db.commit()
                logger.info(f"✅ Сессия {session_id[:8]}... сохранена в БД до {db_user.auth_session_expires}")
            db.close()
            
            logger.info(f"✅ Создана сессия аутентификации {session_id[:8]}... для пользователя {user.telegram_id}")
            return session_id
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания сессии аутентификации для пользователя {user.telegram_id}: {str(e)}")
            return None
    
    async def validate_auth_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Валидирует сессию аутентификации
        
        Args:
            session_id: ID сессии
            
        Returns:
            dict: Данные сессии или None если невалидна
        """
        try:
            # Проверяем сессию в базе данных
            db = SessionLocal()
            user = db.query(User).filter(User.auth_session_id == session_id).first()
            
            if not user:
                db.close()
                return None
            
            # Проверяем истечение
            now = self._now()
            
            # Убеждаемся что время в БД тоже с timezone
            expires_at = user.auth_session_expires
            if expires_at and expires_at.tzinfo is None:
                # Если время в БД без timezone, считаем его UTC
                expires_at = expires_at.replace(tzinfo=timezone.utc)
            
            logger.info(f"🔍 Проверка сессии {session_id[:8]}...: сейчас {now}, истекает {expires_at}")
            
            if not expires_at or now > expires_at:
                # Очищаем истекшую сессию
                logger.warning(f"⏰ Сессия {session_id[:8]}... истекла: {now} > {expires_at}")
                user.auth_session_id = None
                user.auth_session_expires = None
                db.commit()
                db.close()
                return None
            
            # Возвращаем данные сессии
            session_data = {
                'user_id': user.id,
                'telegram_id': user.telegram_id,
                'created_at': user.auth_session_expires - self.session_timeout,
                'expires_at': user.auth_session_expires,
                'status': 'valid'
            }
            
            db.close()
            return session_data
            
        except Exception as e:
            logger.error(f"❌ Ошибка валидации сессии {session_id}: {str(e)}")
            return None
    
    async def process_auth_data(self, session_id: str, api_id: str, api_hash: str, phone: str) -> Dict[str, Any]:
        """
        Обрабатывает данные аутентификации из веб-формы
        
        Args:
            session_id: ID сессии
            api_id: API ID
            api_hash: API Hash
            phone: Номер телефона
            
        Returns:
            dict: Результат обработки
        """
        try:
            # Валидируем сессию
            session = await self.validate_auth_session(session_id)
            if not session:
                return {
                    'success': False,
                    'error': 'Сессия истекла или недействительна',
                    'requires_code': False
                }
            
            user_id = session['user_id']
            
            # Получаем пользователя из БД
            db = SessionLocal()
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                db.close()
                return {
                    'success': False,
                    'error': 'Пользователь не найден',
                    'requires_code': False
                }
            
            # Проверяем блокировку
            if self._is_user_blocked(user):
                db.close()
                return {
                    'success': False,
                    'error': 'Пользователь заблокирован',
                    'requires_code': False
                }
            
            # Сохраняем данные (зашифрованными)
            try:
                user.api_id = api_id
                user.set_encrypted_api_hash(api_hash)
                user.set_encrypted_phone_number(phone)
                db.commit()
                
                logger.info(f"✅ Данные аутентификации сохранены для пользователя {user.telegram_id}")
                
            except Exception as e:
                db.close()
                return {
                    'success': False,
                    'error': f'Ошибка сохранения данных: {str(e)}',
                    'requires_code': False
                }
            
            # Создаем клиент и начинаем аутентификацию
            try:
                client = await self._create_client(user, api_id, api_hash)
                await client.connect()
                
                if not client.is_connected():
                    db.close()
                    return {
                        'success': False,
                        'error': 'Не удалось подключиться к Telegram',
                        'requires_code': False
                    }
                
                # Проверяем авторизацию
                if await client.is_user_authorized():
                    # Уже авторизован
                    await self._update_user_auth_status(user, True, None)
                    self.active_clients[user.id] = client
                    
                    # Очищаем сессию
                    del self.auth_sessions[session_id]
                    user.auth_session_id = None
                    user.auth_session_expires = None
                    db.commit()
                    db.close()
                    
                    return {
                        'success': True,
                        'error': None,
                        'requires_code': False,
                        'message': 'Аутентификация успешна'
                    }
                
                # Отправляем код
                await client.send_code_request(phone)
                
                # Сохраняем клиент для последующего ввода кода
                self.active_clients[user.id] = client
                session['status'] = 'waiting_code'
                session['client_created'] = True
                
                await self._update_user_auth_status(user, False, "Ожидается ввод кода аутентификации")
                
                db.close()
                
                return {
                    'success': True,
                    'error': None,
                    'requires_code': True,
                    'message': 'Код отправлен на номер телефона'
                }
                
            except FloodWaitError as e:
                error_msg = f"Необходимо подождать {e.seconds} секунд"
                await self._update_user_auth_status(user, False, error_msg)
                db.close()
                
                return {
                    'success': False,
                    'error': error_msg,
                    'requires_code': False
                }
                
            except Exception as e:
                error_msg = f"Ошибка аутентификации: {str(e)}"
                await self._update_user_auth_status(user, False, error_msg)
                db.close()
                
                return {
                    'success': False,
                    'error': error_msg,
                    'requires_code': False
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки данных аутентификации: {str(e)}")
            return {
                'success': False,
                'error': f'Внутренняя ошибка: {str(e)}',
                'requires_code': False
            }
    
    async def verify_auth_code(self, session_id: str, code: str) -> Dict[str, Any]:
        """
        Проверяет код аутентификации из веб-формы
        
        Args:
            session_id: ID сессии
            code: Код аутентификации
            
        Returns:
            dict: Результат проверки
        """
        try:
            # Валидируем сессию
            session = await self.validate_auth_session(session_id)
            if not session:
                return {
                    'success': False,
                    'error': 'Сессия истекла или недействительна'
                }
            
            user_id = session['user_id']
            
            # Проверяем, что клиент создан
            if user_id not in self.active_clients:
                return {
                    'success': False,
                    'error': 'Клиент не найден. Начните процесс заново'
                }
            
            client = self.active_clients[user_id]
            
            # Получаем пользователя из БД
            db = SessionLocal()
            user = db.query(User).filter(User.id == user_id).first()
            if not user:
                db.close()
                return {
                    'success': False,
                    'error': 'Пользователь не найден'
                }
            
            phone = user.get_decrypted_phone_number()
            if not phone:
                db.close()
                return {
                    'success': False,
                    'error': 'Номер телефона не найден'
                }
            
            try:
                # Вводим код
                await client.sign_in(phone=phone, code=code)
                
                # Проверяем успешность
                if await client.is_user_authorized():
                    await self._update_user_auth_status(user, True, None)
                    
                    # Очищаем сессию
                    del self.auth_sessions[session_id]
                    user.auth_session_id = None
                    user.auth_session_expires = None
                    db.commit()
                    db.close()
                    
                    return {
                        'success': True,
                        'error': None,
                        'message': 'Аутентификация успешна'
                    }
                else:
                    error_msg = "Неверный код аутентификации"
                    await self._update_user_auth_status(user, False, error_msg)
                    db.close()
                    
                    return {
                        'success': False,
                        'error': error_msg
                    }
                    
            except SessionPasswordNeededError:
                # Требуется 2FA пароль
                session['status'] = 'waiting_2fa'
                return {
                    'success': True,
                    'requires_2fa': True,
                    'message': 'Введите пароль двухфакторной аутентификации'
                }
                
            except Exception as e:
                error_msg = f"Ошибка проверки кода: {str(e)}"
                await self._update_user_auth_status(user, False, error_msg)
                db.close()
                
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки кода аутентификации: {str(e)}")
            return {
                'success': False,
                'error': f'Внутренняя ошибка: {str(e)}'
            }
    
    async def _create_client(self, user: User, api_id: str, api_hash: str) -> TelegramClient:
        """Создает Telegram клиент для пользователя"""
        try:
            # Проверяем валидность API_ID
            try:
                api_id_int = int(api_id)
            except ValueError:
                raise ValueError("API_ID должен быть числом")
            
            # Создаем путь к сессии
            session_path = self._get_session_path(user.id)
            
            # Создаем клиент
            client = TelegramClient(
                session_path,
                api_id_int,
                api_hash,
                connection_retries=3,
                retry_delay=5,
                timeout=30,
                request_retries=3
            )
            
            logger.info(f"✅ Создан клиент для пользователя {user.telegram_id}")
            return client
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания клиента для пользователя {user.telegram_id}: {str(e)}")
            raise
    
    async def cleanup_expired_sessions(self):
        """Очистка истекших сессий"""
        now = self._now()
        expired_sessions = []
        
        for session_id, session in self.auth_sessions.items():
            if now > session['expires_at']:
                expired_sessions.append(session_id)
        
        for session_id in expired_sessions:
            del self.auth_sessions[session_id]
        
        if expired_sessions:
            logger.info(f"🧹 Очищено {len(expired_sessions)} истекших сессий")
    
    async def get_user_client(self, user: User) -> Optional[TelegramClient]:
        """Получить клиент пользователя"""
        try:
            # Если клиент уже активен, возвращаем его
            if user.id in self.active_clients:
                client = self.active_clients[user.id]
                if client.is_connected():
                    return client
                else:
                    # Переподключаемся
                    await client.connect()
                    if client.is_connected():
                        return client
            
            # Создаем новый клиент
            api_hash = user.get_decrypted_api_hash()
            if not user.api_id or not api_hash:
                raise ValueError("API данные пользователя не установлены")
            
            client = await self._create_client(user, user.api_id, api_hash)
            await client.connect()
            
            if not client.is_connected():
                raise ConnectionError("Не удалось подключиться к Telegram")
            
            # Проверяем авторизацию
            if not await client.is_user_authorized():
                raise ValueError("Пользователь не авторизован")
            
            self.active_clients[user.id] = client
            return client
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения клиента для пользователя {user.telegram_id}: {str(e)}")
            raise

    async def verify_two_factor(self, session_id: str, password: str) -> Dict[str, Any]:
        """
        Проверяет пароль двухфакторной аутентификации
        
        Args:
            session_id: ID сессии
            password: Пароль 2FA
            
        Returns:
            dict: Результат проверки
        """
        try:
            # Валидируем сессию
            session = await self.validate_auth_session(session_id)
            if not session:
                return {
                    'success': False,
                    'error': 'Сессия истекла или недействительна'
                }
            
            user_id = session['user_id']
            
            # Проверяем, что клиент создан
            if user_id not in self.active_clients:
                return {
                    'success': False,
                    'error': 'Клиент не найден. Начните процесс заново'
                }
            
            client = self.active_clients[user_id]
            
            try:
                # Проверяем пароль 2FA
                await client.sign_in(password=password)
                
                # Успешная аутентификация
                logger.info(f"✅ 2FA аутентификация успешна для пользователя {user_id}")
                
                # Обновляем статус пользователя
                db = SessionLocal()
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    await self._update_user_auth_status(user, True, None)
                    
                    # Очищаем сессию
                    user.auth_session_id = None
                    user.auth_session_expires = None
                    db.commit()
                
                db.close()
                
                # Очищаем временную сессию
                if session_id in self.auth_sessions:
                    del self.auth_sessions[session_id]
                
                return {
                    'success': True,
                    'message': 'Аутентификация успешна'
                }
                
            except Exception as e:
                error_msg = f"Неверный пароль 2FA: {str(e)}"
                logger.warning(f"⚠️ {error_msg}")
                
                return {
                    'success': False,
                    'error': error_msg
                }
                
        except Exception as e:
            logger.error(f"❌ Ошибка проверки 2FA: {str(e)}")
            return {
                'success': False,
                'error': f'Внутренняя ошибка: {str(e)}'
            }

# Глобальный экземпляр менеджера
secure_auth_manager = SecureAuthManager()
