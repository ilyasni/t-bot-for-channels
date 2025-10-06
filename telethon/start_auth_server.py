#!/usr/bin/env python3
"""
Скрипт для запуска веб-сервера аутентификации
Запускает HTTPS сервер для безопасной аутентификации пользователей
"""

import asyncio
import logging
import os
import sys
import argparse
from dotenv import load_dotenv

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from auth_web_server import start_auth_server
from database import create_tables

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def main():
    """Главная функция для запуска веб-сервера аутентификации"""
    parser = argparse.ArgumentParser(description="Telegram Auth Web Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    parser.add_argument("--ssl-cert", help="SSL certificate file")
    parser.add_argument("--ssl-key", help="SSL private key file")
    parser.add_argument("--dev", action="store_true", help="Development mode (no SSL)")
    
    args = parser.parse_args()
    
    logger.info("🔐 Запуск веб-сервера аутентификации")
    logger.info("=" * 50)
    
    # Проверяем переменные окружения
    auth_base_url = os.getenv("AUTH_BASE_URL")
    encryption_key = os.getenv("ENCRYPTION_KEY")
    
    if not encryption_key or encryption_key == "your_32_byte_base64_encryption_key_here":
        logger.error("❌ ENCRYPTION_KEY не установлен в .env файле")
        logger.info("💡 Сгенерируйте ключ командой:")
        logger.info("   python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"")
        return
    
    if not auth_base_url or auth_base_url == "https://yourdomain.com:8000":
        logger.warning("⚠️ AUTH_BASE_URL не настроен в .env файле")
        logger.info("💡 Добавьте в .env файл:")
        logger.info(f"   AUTH_BASE_URL=https://{args.host}:{args.port}")
    
    try:
        # Создаем таблицы базы данных
        logger.info("📊 Инициализация базы данных...")
        create_tables()
        logger.info("✅ База данных готова")
        
        # Настройки SSL
        ssl_cert = args.ssl_cert or os.getenv("SSL_CERT_PATH")
        ssl_key = args.ssl_key or os.getenv("SSL_KEY_PATH")
        
        if args.dev:
            logger.warning("⚠️ Режим разработки - SSL отключен")
            ssl_cert = None
            ssl_key = None
        elif not ssl_cert or not ssl_key:
            logger.warning("⚠️ SSL сертификаты не настроены")
            logger.info("💡 Для продакшена настройте SSL:")
            logger.info("   1. Получите SSL сертификат")
            logger.info("   2. Укажите пути в .env файле:")
            logger.info("      SSL_CERT_PATH=/path/to/certificate.crt")
            logger.info("      SSL_KEY_PATH=/path/to/private.key")
            logger.info("   3. Или используйте --ssl-cert и --ssl-key")
        
        logger.info("🚀 Запуск веб-сервера...")
        logger.info(f"📍 Адрес: https://{args.host}:{args.port}")
        logger.info("💡 Для остановки нажмите Ctrl+C")
        
        # Запускаем сервер
        start_auth_server(
            host=args.host,
            port=args.port,
            ssl_cert=ssl_cert,
            ssl_key=ssl_key
        )
        
    except KeyboardInterrupt:
        logger.info("🛑 Получен сигнал остановки...")
    except Exception as e:
        logger.error(f"❌ Ошибка запуска веб-сервера: {str(e)}")
        logger.info("💡 Проверьте:")
        logger.info("   1. Правильность настроек в .env файле")
        logger.info("   2. Доступность порта")
        logger.info("   3. Наличие SSL сертификатов (для продакшена)")

if __name__ == "__main__":
    main()
