#!/usr/bin/env python3
"""
Скрипт для первоначальной настройки Telegram Channel Parser Bot
"""

import os
import sys
from pathlib import Path

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 8):
        print("❌ Требуется Python 3.8 или выше")
        sys.exit(1)
    print("✅ Версия Python подходит")

def check_env_file():
    """Проверка файла .env"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ Файл .env не найден")
        print("📝 Создайте файл .env на основе .env.example")
        print("   cp .env.example .env")
        return False
    
    print("✅ Файл .env найден")
    return True

def check_required_env_vars():
    """Проверка обязательных переменных окружения"""
    required_vars = [
        "API_ID",
        "API_HASH", 
        "PHONE",
        "BOT_TOKEN"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Отсутствуют обязательные переменные: {', '.join(missing_vars)}")
        return False
    
    print("✅ Все обязательные переменные окружения настроены")
    return True

def create_directories():
    """Создание необходимых директорий"""
    directories = ["sessions", "logs"]
    
    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Директория {directory} создана")

def install_dependencies():
    """Установка зависимостей"""
    print("📦 Установка зависимостей...")
    os.system("pip install -r requirements.txt")

def main():
    """Главная функция настройки"""
    print("🚀 Настройка Telegram Channel Parser Bot")
    print("=" * 50)
    
    # Проверки
    check_python_version()
    
    if not check_env_file():
        print("\n📋 Инструкции по настройке:")
        print("1. Скопируйте .env.example в .env")
        print("2. Заполните обязательные переменные в .env")
        print("3. Запустите этот скрипт снова")
        return
    
    if not check_required_env_vars():
        print("\n📋 Заполните следующие переменные в .env:")
        print("- API_ID: ID вашего Telegram приложения")
        print("- API_HASH: Hash вашего Telegram приложения")
        print("- PHONE: Ваш номер телефона в международном формате")
        print("- BOT_TOKEN: Токен вашего Telegram бота")
        return
    
    # Создание директорий
    create_directories()
    
    # Установка зависимостей
    install_dependencies()
    
    print("\n✅ Настройка завершена!")
    print("\n📋 Следующие шаги:")
    print("1. Запустите первоначальную аутентификацию:")
    print("   python auth.py")
    print("\n2. Запустите систему:")
    print("   python run_system.py")
    print("\n3. Найдите вашего бота в Telegram и отправьте /start")

if __name__ == "__main__":
    main() 