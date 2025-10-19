"""
Конфигурация логирования для Telegram Bot
Все логи пишутся в папку logs/
"""

import os
import logging
import sys
from pathlib import Path

def setup_telethon_logging():
    """Настройка логирования для telethon"""
    
    # Определяем пути
    base_dir = Path(__file__).parent
    logs_dir = base_dir / "logs"
    
    # Создаем папку logs если не существует
    logs_dir.mkdir(exist_ok=True)
    
    # Настраиваем логирование
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Основной лог файл
    main_log = logs_dir / "telethon.log"
    
    # Лог файл для ошибок
    error_log = logs_dir / "telethon_errors.log"
    
    # Конфигурация
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # Основной лог файл
            logging.FileHandler(main_log, encoding='utf-8'),
            # Консольный вывод
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Добавляем отдельный handler для ошибок
    error_handler = logging.FileHandler(error_log, encoding='utf-8')
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter(log_format))
    logging.getLogger().addHandler(error_handler)
    
    # Создаем логгеры для разных компонентов
    loggers = {
        'telethon': logging.getLogger('telethon'),
        'telethon.bot': logging.getLogger('telethon.bot'),
        'telethon.parser': logging.getLogger('telethon.parser'),
        'telethon.rag': logging.getLogger('telethon.rag'),
        'telethon.neo4j': logging.getLogger('telethon.neo4j'),
    }
    
    # Настраиваем уровни логирования
    for logger in loggers.values():
        logger.setLevel(logging.INFO)
    
    return loggers

def get_logger(name: str) -> logging.Logger:
    """Получить логгер для компонента"""
    return logging.getLogger(f'telethon.{name}')

# Автоматическая настройка при импорте
if __name__ != "__main__":
    setup_telethon_logging()
