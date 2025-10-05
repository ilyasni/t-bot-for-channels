from telethon import TelegramClient
from telethon.errors import FloodWaitError, AuthKeyError, RPCError
import os
import logging
import asyncio
from dotenv import load_dotenv
import time

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для хранения клиента
_global_client = None

async def get_client(max_retries=5, base_delay=5):
    """
    Создает и подключает Telegram клиент с повторными попытками
    
    Args:
        max_retries (int): Максимальное количество попыток подключения
        base_delay (int): Базовая задержка между попытками в секундах
    
    Returns:
        TelegramClient: Подключенный клиент или None при неудаче
    """
    global _global_client
    
    # Если клиент уже подключен, возвращаем его
    if _global_client and _global_client.is_connected():
        logger.info("♻️ Используем существующее подключение к Telegram API")
        return _global_client
    
    # Проверяем наличие обязательных переменных окружения
    api_id = os.getenv('API_ID')
    api_hash = os.getenv('API_HASH')
    
    if not api_id or not api_hash:
        logger.error("❌ Отсутствуют API_ID или API_HASH в переменных окружения")
        raise ValueError("API_ID и API_HASH должны быть установлены")
    
    try:
        api_id = int(api_id)
    except ValueError:
        logger.error("❌ API_ID должен быть числом")
        raise ValueError("API_ID должен быть числом")
    
    client = TelegramClient(
        'sessions/session',
        api_id,
        api_hash,
        connection_retries=max_retries,
        retry_delay=base_delay,
        timeout=30,  # Увеличиваем таймаут
        request_retries=max_retries
    )
    
    # Попытки подключения с экспоненциальной задержкой
    for attempt in range(max_retries):
        try:
            logger.info(f"🔄 Попытка подключения к Telegram API (попытка {attempt + 1}/{max_retries})")
            
            await client.connect()
            
            if client.is_connected():
                logger.info("✅ Успешное подключение к Telegram API")
                
                # Проверяем авторизацию пользователя
                if not await client.is_user_authorized():
                    logger.warning("⚠️ Пользователь не авторизован, требуется аутентификация")
                    await handle_authentication(client)
                
                # Сохраняем клиента в глобальной переменной
                _global_client = client
                return client
            else:
                logger.warning(f"⚠️ Подключение не установлено (попытка {attempt + 1})")
                
        except (ConnectionError, OSError, TimeoutError) as e:
            logger.warning(f"⚠️ Ошибка подключения (попытка {attempt + 1}): {str(e)}")
            
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)  # Экспоненциальная задержка
                logger.info(f"⏳ Ожидание {delay} секунд перед следующей попыткой...")
                await asyncio.sleep(delay)
            else:
                logger.error(f"❌ Не удалось подключиться после {max_retries} попыток")
                raise
                
        except AuthKeyError as e:
            logger.error(f"❌ Ошибка авторизации: {str(e)}")
            logger.info("💡 Попробуйте удалить файл sessions/session.session и перезапустить")
            raise
            
        except Exception as e:
            logger.error(f"❌ Неожиданная ошибка подключения: {str(e)}")
            if attempt < max_retries - 1:
                delay = base_delay * (2 ** attempt)
                await asyncio.sleep(delay)
            else:
                raise
    
    return None

async def handle_authentication(client):
    """
    Обрабатывает аутентификацию пользователя
    
    Args:
        client: TelegramClient
    """
    phone = os.getenv('PHONE')
    auth_code = os.getenv('AUTH_CODE')
    
    if not phone:
        logger.error("❌ Отсутствует номер телефона (PHONE) в переменных окружения")
        raise ValueError("PHONE должен быть установлен")
    
    try:
        if auth_code:
            # Автоматическая аутентификация с кодом
            logger.info("🔐 Попытка автоматической аутентификации с кодом")
            await client.send_code_request(phone)
            await client.sign_in(phone=phone, code=auth_code)
            logger.info("✅ Автоматическая аутентификация успешна")
        else:
            # Интерактивная аутентификация
            logger.info("🔐 Требуется интерактивная аутентификация")
            await client.send_code_request(phone)
            
            # В продакшене это должно быть заменено на интерактивный ввод
            logger.warning("⚠️ Для интерактивной аутентификации требуется AUTH_CODE в .env")
            raise ValueError("Установите AUTH_CODE в .env файле для автоматической аутентификации")
            
    except FloodWaitError as e:
        logger.warning(f"⏳ Необходимо подождать {e.seconds} секунд из-за ограничений Telegram")
        await asyncio.sleep(e.seconds)
        await handle_authentication(client)  # Повторная попытка
    except Exception as e:
        logger.error(f"❌ Ошибка аутентификации: {str(e)}")
        raise

async def main():
    """Функция для первоначальной аутентификации"""
    logger.info("🔐 Первоначальная аутентификация в Telegram")
    logger.info("=" * 50)
    
    try:
        client = await get_client(max_retries=3, base_delay=5)
        
        if client and client.is_connected():
            logger.info("✅ Успешная аутентификация!")
            logger.info("📱 Теперь вы можете запустить систему")
            
            # Тестируем подключение
            try:
                me = await client.get_me()
                logger.info(f"👤 Авторизован как: {me.first_name} (@{me.username})")
            except Exception as e:
                logger.warning(f"⚠️ Не удалось получить информацию о пользователе: {str(e)}")
            
            # Корректно отключаемся
            await client.disconnect()
            logger.info("🔌 Соединение закрыто")
            
        else:
            logger.error("❌ Не удалось установить соединение")
            
    except ValueError as e:
        logger.error(f"❌ Ошибка конфигурации: {str(e)}")
        logger.info("💡 Проверьте файл .env и убедитесь, что все переменные установлены")
    except Exception as e:
        logger.error(f"❌ Ошибка аутентификации: {str(e)}")
        logger.info("💡 Возможные решения:")
        logger.info("   1. Проверьте интернет-соединение")
        logger.info("   2. Убедитесь, что API_ID и API_HASH корректны")
        logger.info("   3. Проверьте, что номер телефона указан в международном формате")
        logger.info("   4. Попробуйте удалить sessions/session.session и перезапустить")

if __name__ == "__main__":
    asyncio.run(main())