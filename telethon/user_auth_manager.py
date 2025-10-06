from telethon import TelegramClient
from telethon.errors import FloodWaitError, AuthKeyError, RPCError
from sqlalchemy.orm import Session
from models import User
from datetime import datetime, timezone
import os
import logging
import asyncio
import hashlib

# Этот модуль устарел - используйте secure_auth_manager.py

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UserAuthManager:
    """Менеджер для управления аутентификацией пользователей"""
    
    def __init__(self):
        self.active_clients = {}  # Словарь активных клиентов по user_id
        self.sessions_dir = "sessions"
        self._ensure_sessions_dir()
    
    def _ensure_sessions_dir(self):
        """Создает директорию для сессий если её нет"""
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)
    
    def _get_session_path(self, user_id: int) -> str:
        """Генерирует путь к файлу сессии для пользователя"""
        return os.path.join(self.sessions_dir, f"user_{user_id}.session")
    
    def _hash_credentials(self, api_id: str, api_hash: str) -> str:
        """Создает хеш от учетных данных для безопасности"""
        return hashlib.sha256(f"{api_id}_{api_hash}".encode()).hexdigest()[:16]
    
    async def create_client(self, user: User) -> TelegramClient:
        """Создает Telegram клиент для пользователя"""
        try:
            if not user.api_id or not user.api_hash:
                raise ValueError("API_ID и API_HASH пользователя не установлены")
            
            # Проверяем валидность API_ID
            try:
                api_id = int(user.api_id)
            except ValueError:
                raise ValueError("API_ID должен быть числом")
            
            # Создаем путь к сессии
            session_path = self._get_session_path(user.id)
            
            # Создаем клиент
            client = TelegramClient(
                session_path,
                api_id,
                user.api_hash,
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
    
    async def authenticate_user(self, user: User, phone: str = None) -> bool:
        """Аутентификация пользователя"""
        try:
            client = await self.create_client(user)
            
            # Подключаемся
            await client.connect()
            
            if not client.is_connected():
                raise ConnectionError("Не удалось подключиться к Telegram")
            
            # Проверяем авторизацию
            if await client.is_user_authorized():
                logger.info(f"✅ Пользователь {user.telegram_id} уже авторизован")
                await self._update_user_auth_status(user, True, None)
                self.active_clients[user.id] = client
                return True
            
            # Если не авторизован, начинаем процесс аутентификации
            if not phone:
                phone = user.phone_number
                
            if not phone:
                raise ValueError("Номер телефона не указан")
            
            # Отправляем код
            await client.send_code_request(phone)
            logger.info(f"📱 Код отправлен на номер {phone} для пользователя {user.telegram_id}")
            
            # Сохраняем клиент для последующего ввода кода
            self.active_clients[user.id] = client
            await self._update_user_auth_status(user, False, "Ожидается ввод кода аутентификации")
            
            return False  # Требуется код
            
        except FloodWaitError as e:
            error_msg = f"Необходимо подождать {e.seconds} секунд"
            logger.warning(f"⏳ {error_msg} для пользователя {user.telegram_id}")
            await self._update_user_auth_status(user, False, error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Ошибка аутентификации: {str(e)}"
            logger.error(f"❌ {error_msg} для пользователя {user.telegram_id}")
            await self._update_user_auth_status(user, False, error_msg)
            return False
    
    async def verify_code(self, user: User, code: str) -> bool:
        """Проверка кода аутентификации"""
        try:
            if user.id not in self.active_clients:
                raise ValueError("Клиент не найден. Начните процесс аутентификации заново")
            
            client = self.active_clients[user.id]
            
            if not user.phone_number:
                raise ValueError("Номер телефона не указан")
            
            # Вводим код
            await client.sign_in(phone=user.phone_number, code=code)
            
            # Проверяем успешность
            if await client.is_user_authorized():
                logger.info(f"✅ Пользователь {user.telegram_id} успешно авторизован")
                await self._update_user_auth_status(user, True, None)
                return True
            else:
                raise ValueError("Неверный код аутентификации")
                
        except Exception as e:
            error_msg = f"Ошибка проверки кода: {str(e)}"
            logger.error(f"❌ {error_msg} для пользователя {user.telegram_id}")
            await self._update_user_auth_status(user, False, error_msg)
            return False
    
    async def get_user_client(self, user: User) -> TelegramClient:
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
            client = await self.create_client(user)
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
    
    async def check_auth_status(self, user: User) -> bool:
        """Проверка статуса аутентификации пользователя"""
        try:
            client = await self.get_user_client(user)
            
            if client.is_connected() and await client.is_user_authorized():
                await self._update_user_auth_status(user, True, None)
                return True
            else:
                await self._update_user_auth_status(user, False, "Клиент не авторизован")
                return False
                
        except Exception as e:
            error_msg = f"Ошибка проверки статуса: {str(e)}"
            logger.error(f"❌ {error_msg} для пользователя {user.telegram_id}")
            await self._update_user_auth_status(user, False, error_msg)
            return False
    
    async def logout_user(self, user: User):
        """Выход пользователя из системы"""
        try:
            if user.id in self.active_clients:
                client = self.active_clients[user.id]
                if client.is_connected():
                    await client.disconnect()
                del self.active_clients[user.id]
            
            # Удаляем файл сессии
            session_path = self._get_session_path(user.id)
            if os.path.exists(session_path):
                os.remove(session_path)
            
            await self._update_user_auth_status(user, False, "Пользователь вышел из системы")
            logger.info(f"✅ Пользователь {user.telegram_id} вышел из системы")
            
        except Exception as e:
            logger.error(f"❌ Ошибка выхода пользователя {user.telegram_id}: {str(e)}")
    
    async def _update_user_auth_status(self, user: User, is_authenticated: bool, error: str = None):
        """Обновление статуса аутентификации в БД"""
        try:
            from database import SessionLocal
            db = SessionLocal()
            
            user.is_authenticated = is_authenticated
            user.last_auth_check = datetime.now(timezone.utc)
            if error:
                user.auth_error = error
            else:
                user.auth_error = None
            
            db.commit()
            db.close()
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления статуса аутентификации: {str(e)}")
    
    async def cleanup_inactive_clients(self):
        """Очистка неактивных клиентов"""
        inactive_users = []
        
        for user_id, client in self.active_clients.items():
            try:
                if not client.is_connected():
                    inactive_users.append(user_id)
                else:
                    # Проверяем авторизацию
                    if not await client.is_user_authorized():
                        inactive_users.append(user_id)
            except:
                inactive_users.append(user_id)
        
        for user_id in inactive_users:
            if user_id in self.active_clients:
                try:
                    await self.active_clients[user_id].disconnect()
                except:
                    pass
                del self.active_clients[user_id]
        
        if inactive_users:
            logger.info(f"🧹 Очищено {len(inactive_users)} неактивных клиентов")
    
    async def get_all_authenticated_users(self, db: Session) -> list:
        """Получить всех аутентифицированных пользователей"""
        return db.query(User).filter(
            User.is_authenticated == True,
            User.is_active == True
        ).all()
    
    async def disconnect_all(self):
        """Отключение всех клиентов"""
        for user_id, client in self.active_clients.items():
            try:
                if client.is_connected():
                    await client.disconnect()
            except:
                pass
        
        self.active_clients.clear()
        logger.info("🔌 Все клиенты отключены")
    
    async def clear_all_sessions(self):
        """Очистка всех файлов сессий"""
        import os
        import glob
        
        try:
            # Удаляем все файлы сессий
            session_files = glob.glob(os.path.join(self.sessions_dir, "*.session*"))
            for session_file in session_files:
                try:
                    os.remove(session_file)
                    logger.info(f"🗑️ Удален файл сессии: {session_file}")
                except Exception as e:
                    logger.warning(f"⚠️ Не удалось удалить {session_file}: {str(e)}")
            
            # Очищаем активные клиенты
            self.active_clients.clear()
            
            logger.info("🧹 Все сессии очищены")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки сессий: {str(e)}")
            return False


# Глобальный экземпляр менеджера
auth_manager = UserAuthManager()
