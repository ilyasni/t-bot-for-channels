#!/usr/bin/env python3
"""
Скрипт для запуска безопасной системы Telegram парсера
Запускает бота и веб-сервер аутентификации
"""

import asyncio
import logging
import os
import sys
import subprocess
import signal
import time
from multiprocessing import Process
from dotenv import load_dotenv

# Добавляем текущую директорию в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Загружаем переменные окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SecureSystemManager:
    """Менеджер для запуска безопасной системы"""
    
    def __init__(self):
        self.processes = []
        self.running = True
        
        # Обработчик сигналов для graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Обработчик сигналов для остановки системы"""
        logger.info(f"🛑 Получен сигнал {signum}, останавливаем систему...")
        self.running = False
        self.stop_all_processes()
    
    def check_requirements(self):
        """Проверка требований системы"""
        logger.info("🔍 Проверка требований...")
        
        # Проверяем переменные окружения
        required_vars = ['BOT_TOKEN', 'ENCRYPTION_KEY']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var) or os.getenv(var) == f"your_{var.lower()}_here":
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"❌ Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
            logger.info("💡 Проверьте .env файл")
            return False
        
        # Проверяем ENCRYPTION_KEY
        encryption_key = os.getenv("ENCRYPTION_KEY")
        try:
            from cryptography.fernet import Fernet
            Fernet(encryption_key.encode())
            logger.info("✅ Ключ шифрования валиден")
        except Exception as e:
            logger.error(f"❌ Неверный ключ шифрования: {str(e)}")
            logger.info("💡 Сгенерируйте новый ключ: python generate_encryption_key.py")
            return False
        
        # Проверяем BOT_TOKEN
        bot_token = os.getenv("BOT_TOKEN")
        if not bot_token or len(bot_token) < 40:
            logger.error("❌ Неверный BOT_TOKEN")
            logger.info("💡 Получите токен у @BotFather")
            return False
        
        logger.info("✅ Все требования выполнены")
        return True
    
    def start_bot(self):
        """Запуск Telegram бота"""
        logger.info("🤖 Запуск Telegram бота...")
        try:
            process = Process(target=self._run_bot)
            process.start()
            self.processes.append(('bot', process))
            logger.info(f"✅ Бот запущен (PID: {process.pid})")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка запуска бота: {str(e)}")
            return False
    
    def start_auth_server(self):
        """Запуск веб-сервера аутентификации"""
        logger.info("🔐 Запуск веб-сервера аутентификации...")
        try:
            # Проверяем SSL настройки
            ssl_cert = os.getenv("SSL_CERT_PATH")
            ssl_key = os.getenv("SSL_KEY_PATH")
            
            if ssl_cert and ssl_key:
                logger.info("🔒 SSL сертификаты найдены")
                process = Process(target=self._run_auth_server, args=(True, ssl_cert, ssl_key))
            else:
                logger.warning("⚠️ SSL сертификаты не найдены - запуск в режиме разработки")
                process = Process(target=self._run_auth_server, args=(False, None, None))
            
            process.start()
            self.processes.append(('auth_server', process))
            logger.info(f"✅ Веб-сервер запущен (PID: {process.pid})")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка запуска веб-сервера: {str(e)}")
            return False
    
    def _run_bot(self):
        """Внутренняя функция запуска бота"""
        try:
            from bot_standalone import main as bot_main
            bot_main()
        except Exception as e:
            logger.error(f"❌ Ошибка в боте: {str(e)}")
    
    def _run_auth_server(self, use_ssl, ssl_cert, ssl_key):
        """Внутренняя функция запуска веб-сервера"""
        try:
            from auth_web_server import start_auth_server
            
            if use_ssl:
                start_auth_server(ssl_cert=ssl_cert, ssl_key=ssl_key)
            else:
                start_auth_server()
        except Exception as e:
            logger.error(f"❌ Ошибка в веб-сервере: {str(e)}")
    
    def monitor_processes(self):
        """Мониторинг процессов"""
        logger.info("👁️ Запуск мониторинга процессов...")
        
        while self.running:
            try:
                for name, process in self.processes[:]:  # Копируем список
                    if not process.is_alive():
                        logger.error(f"❌ Процесс {name} завершился неожиданно")
                        self.processes.remove((name, process))
                        
                        # Перезапускаем процесс
                        if name == 'bot':
                            logger.info("🔄 Перезапуск бота...")
                            if self.start_bot():
                                logger.info("✅ Бот перезапущен")
                            else:
                                logger.error("❌ Не удалось перезапустить бота")
                        
                        elif name == 'auth_server':
                            logger.info("🔄 Перезапуск веб-сервера...")
                            if self.start_auth_server():
                                logger.info("✅ Веб-сервер перезапущен")
                            else:
                                logger.error("❌ Не удалось перезапустить веб-сервер")
                
                time.sleep(5)  # Проверяем каждые 5 секунд
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"❌ Ошибка мониторинга: {str(e)}")
                time.sleep(5)
    
    def stop_all_processes(self):
        """Остановка всех процессов"""
        logger.info("🛑 Остановка всех процессов...")
        
        for name, process in self.processes:
            try:
                if process.is_alive():
                    logger.info(f"🛑 Остановка процесса {name} (PID: {process.pid})")
                    process.terminate()
                    process.join(timeout=10)
                    
                    if process.is_alive():
                        logger.warning(f"⚠️ Принудительное завершение {name}")
                        process.kill()
                        process.join()
                    
                    logger.info(f"✅ Процесс {name} остановлен")
            except Exception as e:
                logger.error(f"❌ Ошибка остановки {name}: {str(e)}")
        
        self.processes.clear()
    
    def run(self):
        """Основной метод запуска системы"""
        logger.info("🚀 Запуск безопасной системы Telegram парсера")
        logger.info("=" * 60)
        
        # Проверяем требования
        if not self.check_requirements():
            logger.error("❌ Требования не выполнены, выход...")
            return False
        
        try:
            # Создаем таблицы БД
            logger.info("📊 Инициализация базы данных...")
            from database import create_tables
            create_tables()
            logger.info("✅ База данных готова")
            
            # Запускаем компоненты
            if not self.start_auth_server():
                logger.error("❌ Не удалось запустить веб-сервер")
                return False
            
            # Небольшая задержка перед запуском бота
            time.sleep(2)
            
            if not self.start_bot():
                logger.error("❌ Не удалось запустить бота")
                return False
            
            logger.info("✅ Все компоненты запущены!")
            logger.info("📋 Статус системы:")
            logger.info("   🤖 Telegram бот: активен")
            logger.info("   🔐 Веб-сервер аутентификации: активен")
            logger.info("   📊 База данных: готова")
            logger.info("")
            logger.info("💡 Для остановки нажмите Ctrl+C")
            logger.info("=" * 60)
            
            # Запускаем мониторинг
            self.monitor_processes()
            
        except KeyboardInterrupt:
            logger.info("🛑 Получен сигнал остановки...")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {str(e)}")
        finally:
            self.stop_all_processes()
            logger.info("✅ Система остановлена")

def main():
    """Главная функция"""
    manager = SecureSystemManager()
    manager.run()

if __name__ == "__main__":
    main()
