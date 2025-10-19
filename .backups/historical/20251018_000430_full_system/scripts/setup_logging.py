#!/usr/bin/env python3
"""
Скрипт для настройки правильного логирования в telethon/
Убеждается что все логи пишутся в папку logs/
"""

import os
import logging
import sys
from pathlib import Path

def setup_logging():
    """Настройка логирования для telethon"""
    
    # Определяем пути
    telethon_dir = Path(__file__).parent.parent / "telethon"
    logs_dir = telethon_dir / "logs"
    
    # Создаем папку logs если не существует
    logs_dir.mkdir(exist_ok=True)
    
    # Настраиваем базовое логирование
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    log_file = logs_dir / "telethon.log"
    
    # Конфигурация логирования
    logging.basicConfig(
        level=logging.INFO,
        format=log_format,
        handlers=[
            # Файловый хендлер - пишет в logs/telethon.log
            logging.FileHandler(log_file, encoding='utf-8'),
            # Консольный хендлер - для отладки
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Создаем логгер для telethon
    logger = logging.getLogger('telethon')
    logger.info("✅ Logging configured - logs will be written to logs/telethon.log")
    
    return logger

def create_logging_config():
    """Создает конфигурационный файл для логирования"""
    
    telethon_dir = Path(__file__).parent.parent / "telethon"
    config_file = telethon_dir / "logging_config.py"
    
    config_content = '''"""
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
            # Лог файл для ошибок
            logging.FileHandler(error_log, encoding='utf-8', level=logging.ERROR),
            # Консольный вывод
            logging.StreamHandler(sys.stdout)
        ]
    )
    
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
'''
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    print(f"✅ Created logging config: {config_file}")

def update_main_py():
    """Обновляет main.py для использования правильного логирования"""
    
    telethon_dir = Path(__file__).parent.parent / "telethon"
    main_py = telethon_dir / "main.py"
    
    if not main_py.exists():
        print("❌ main.py not found")
        return
    
    # Читаем файл
    with open(main_py, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Проверяем есть ли уже импорт logging_config
    if 'from logging_config import' in content:
        print("✅ main.py already uses logging_config")
        return
    
    # Добавляем импорт в начало файла
    lines = content.split('\n')
    import_line = None
    
    for i, line in enumerate(lines):
        if line.startswith('import ') or line.startswith('from '):
            import_line = i
        elif line.strip() and not line.startswith('#') and not line.startswith('"""'):
            break
    
    if import_line is not None:
        lines.insert(import_line + 1, 'from logging_config import get_logger')
        lines.insert(import_line + 2, '')
        
        # Заменяем logger = logging.getLogger(__name__) на logger = get_logger('main')
        for i, line in enumerate(lines):
            if 'logger = logging.getLogger(__name__)' in line:
                lines[i] = "logger = get_logger('main')"
                break
        
        # Записываем обновленный файл
        with open(main_py, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))
        
        print("✅ Updated main.py to use logging_config")
    else:
        print("❌ Could not find import section in main.py")

def main():
    """Основная функция"""
    print("🔧 Setting up telethon logging...")
    
    # Создаем конфигурацию логирования
    create_logging_config()
    
    # Обновляем main.py
    update_main_py()
    
    # Тестируем логирование
    logger = setup_logging()
    logger.info("✅ Logging setup completed successfully")
    
    print("✅ Logging setup completed!")
    print("📁 Logs will be written to: telethon/logs/")
    print("📄 Main log file: telethon/logs/telethon.log")
    print("🚨 Error log file: telethon/logs/telethon_errors.log")

if __name__ == "__main__":
    main()
