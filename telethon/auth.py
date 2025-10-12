"""
Безопасный модуль аутентификации для многопользовательской системы.
Использует SecureAuthManager для управления персональными клиентами пользователей.
Устраняет небезопасный ввод кодов через Telegram чат.
"""

from secure_auth_manager import secure_auth_manager
from models import User
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_user_client(user: User):
    """
    Получить клиент для конкретного пользователя
    
    Args:
        user: Объект пользователя из БД
    
    Returns:
        TelegramClient: Клиент пользователя или None при ошибке
    """
    try:
        return await secure_auth_manager.get_user_client(user)
    except Exception as e:
        logger.error(f"❌ Ошибка получения клиента для пользователя {user.telegram_id}: {str(e)}")
        return None

async def create_auth_session(user: User) -> str:
    """
    Создает сессию аутентификации для пользователя
    
    Args:
        user: Объект пользователя из БД
    
    Returns:
        str: ID сессии или None при ошибке
    """
    try:
        session_id = await secure_auth_manager.create_auth_session(user)
        if session_id:
            logger.info(f"✅ Создана сессия аутентификации для пользователя {user.telegram_id}")
        return session_id
    except Exception as e:
        logger.error(f"❌ Ошибка создания сессии для пользователя {user.telegram_id}: {str(e)}")
        return None

async def get_auth_url(session_id: str) -> str:
    """
    Получает URL для аутентификации
    
    Args:
        session_id: ID сессии аутентификации
    
    Returns:
        str: URL для аутентификации
    """
    try:
        base_url = os.getenv("AUTH_BASE_URL", "https://localhost:8000")
        return f"{base_url}/auth?sid={session_id}"
    except Exception as e:
        logger.error(f"❌ Ошибка создания URL аутентификации: {str(e)}")
        return None

async def check_user_auth_status(user: User) -> bool:
    """
    Проверка статуса аутентификации пользователя
    
    Args:
        user: Объект пользователя из БД
    
    Returns:
        bool: True если пользователь аутентифицирован, False если нет
    """
    try:
        # Простая проверка статуса из БД
        return user.is_authenticated and not user.is_blocked
    except Exception as e:
        logger.error(f"❌ Ошибка проверки статуса для пользователя {user.telegram_id}: {str(e)}")
        return False

async def logout_user(user: User):
    """
    Выход пользователя из системы
    
    Args:
        user: Объект пользователя из БД
    """
    try:
        # ВАЖНО: Используем shared_auth_manager (новая QR система)
        # Ключ - telegram_id, НЕ user.id
        from shared_auth_manager import shared_auth_manager
        
        telegram_id = user.telegram_id
        
        # Отключаем клиент если активен
        if telegram_id in shared_auth_manager.active_clients:
            client = shared_auth_manager.active_clients[telegram_id]
            if client.is_connected():
                await client.disconnect()
                logger.info(f"🔌 Клиент {telegram_id} отключен")
            del shared_auth_manager.active_clients[telegram_id]
            logger.info(f"🗑️ Клиент {telegram_id} удален из памяти")
        
        # Очищаем сессию аутентификации (старая система)
        if user.auth_session_id:
            if user.auth_session_id in secure_auth_manager.auth_sessions:
                del secure_auth_manager.auth_sessions[user.auth_session_id]
            user.auth_session_id = None
            user.auth_session_expires = None
        
        # Обновляем статус в БД
        user.is_authenticated = False
        user.auth_error = "Пользователь вышел из системы"
        
        logger.info(f"✅ Пользователь {user.telegram_id} вышел из системы")
        
    except Exception as e:
        logger.error(f"❌ Ошибка выхода пользователя {user.telegram_id}: {str(e)}")

async def get_authenticated_users(db) -> list:
    """
    Получить всех аутентифицированных пользователей
    
    Args:
        db: Сессия базы данных
    
    Returns:
        list: Список аутентифицированных пользователей
    """
    try:
        return db.query(User).filter(
            User.is_authenticated == True,
            User.is_active == True,
            User.is_blocked == False
        ).all()
    except Exception as e:
        logger.error(f"❌ Ошибка получения аутентифицированных пользователей: {str(e)}")
        return []

async def cleanup_inactive_clients():
    """Очистка неактивных клиентов"""
    try:
        # Очищаем истекшие сессии
        await secure_auth_manager.cleanup_expired_sessions()
        
        # Очищаем неактивные клиенты
        inactive_users = []
        for user_id, client in secure_auth_manager.active_clients.items():
            try:
                if not client.is_connected():
                    inactive_users.append(user_id)
            except:
                inactive_users.append(user_id)
        
        for user_id in inactive_users:
            if user_id in secure_auth_manager.active_clients:
                try:
                    await secure_auth_manager.active_clients[user_id].disconnect()
                except:
                    pass
                del secure_auth_manager.active_clients[user_id]
        
        if inactive_users:
            logger.info(f"🧹 Очищено {len(inactive_users)} неактивных клиентов")
            
    except Exception as e:
        logger.error(f"❌ Ошибка очистки неактивных клиентов: {str(e)}")

async def disconnect_all_clients():
    """Отключение всех клиентов"""
    try:
        for user_id, client in secure_auth_manager.active_clients.items():
            try:
                if client.is_connected():
                    await client.disconnect()
            except:
                pass
        
        secure_auth_manager.active_clients.clear()
        secure_auth_manager.auth_sessions.clear()
        logger.info("🔌 Все клиенты отключены")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отключения всех клиентов: {str(e)}")

async def clear_all_sessions():
    """Очистка всех сессий"""
    try:
        import os
        import glob
        
        # Удаляем все файлы сессий
        session_files = glob.glob(os.path.join(secure_auth_manager.sessions_dir, "*.session*"))
        for session_file in session_files:
            try:
                os.remove(session_file)
                logger.info(f"🗑️ Удален файл сессии: {session_file}")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить {session_file}: {str(e)}")
        
        # Очищаем активные клиенты и сессии
        secure_auth_manager.active_clients.clear()
        secure_auth_manager.auth_sessions.clear()
        
        logger.info("🧹 Все сессии очищены")
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки сессий: {str(e)}")
        return False

# Устаревшие функции удалены - используйте новые безопасные функции