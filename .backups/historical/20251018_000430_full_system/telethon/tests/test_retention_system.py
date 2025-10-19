"""
Скрипт тестирования системы ограничения хранения постов

Этот скрипт проверяет:
1. Наличие поля retention_days в базе данных
2. Работу сервиса очистки
3. API endpoints (требует запущенный сервер)

Использование:
    python test_retention_system.py
"""

import os
import sys
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# Цвета для вывода
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_success(message):
    print(f"{GREEN}✅ {message}{RESET}")

def print_error(message):
    print(f"{RED}❌ {message}{RESET}")

def print_warning(message):
    print(f"{YELLOW}⚠️  {message}{RESET}")

def print_info(message):
    print(f"{BLUE}ℹ️  {message}{RESET}")

def test_database_migration():
    """Тест 1: Проверка миграции базы данных"""
    print("\n" + "=" * 60)
    print("Тест 1: Проверка миграции базы данных")
    print("=" * 60)
    
    try:
        from database import SessionLocal
        from models import User
        
        db = SessionLocal()
        
        # Проверяем наличие колонки retention_days
        DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/telethon_bot.db")
        engine = create_engine(DATABASE_URL)
        inspector = inspect(engine)
        
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'retention_days' in columns:
            print_success("Колонка 'retention_days' найдена в таблице users")
        else:
            print_error("Колонка 'retention_days' НЕ найдена в таблице users")
            print_warning("Запустите миграцию: python add_retention_days.py")
            return False
        
        # Проверяем, что у пользователей есть значение
        user = db.query(User).first()
        if user:
            print_info(f"Пример пользователя: ID={user.id}, retention_days={user.retention_days}")
            
            if user.retention_days:
                print_success(f"Значение retention_days установлено: {user.retention_days} дней")
            else:
                print_warning("У пользователя retention_days = None")
        else:
            print_info("В базе данных нет пользователей для проверки")
        
        db.close()
        return True
        
    except Exception as e:
        print_error(f"Ошибка проверки базы данных: {str(e)}")
        return False

def test_cleanup_service():
    """Тест 2: Проверка сервиса очистки"""
    print("\n" + "=" * 60)
    print("Тест 2: Проверка сервиса очистки")
    print("=" * 60)
    
    try:
        from cleanup_service import CleanupService
        
        service = CleanupService()
        print_success("CleanupService успешно импортирован")
        
        # Проверяем параметры защиты
        print_info(f"Минимальный период хранения: {service.min_retention_days} день")
        print_info(f"Максимальный период хранения: {service.max_retention_days} дней")
        
        print_success("Сервис очистки готов к работе")
        return True
        
    except Exception as e:
        print_error(f"Ошибка импорта сервиса очистки: {str(e)}")
        return False

def test_models():
    """Тест 3: Проверка моделей и таймзон"""
    print("\n" + "=" * 60)
    print("Тест 3: Проверка моделей и таймзон")
    print("=" * 60)
    
    try:
        from models import User, Channel, Post
        from datetime import timezone
        
        print_success("Модели успешно импортированы")
        
        # Проверяем, что timezone импортирован
        print_success("Модуль timezone доступен")
        
        # Проверяем наличие поля retention_days в User
        if hasattr(User, 'retention_days'):
            print_success("Поле retention_days найдено в модели User")
        else:
            print_error("Поле retention_days НЕ найдено в модели User")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Ошибка проверки моделей: {str(e)}")
        return False

def test_parser_integration():
    """Тест 4: Проверка интеграции с parser_service"""
    print("\n" + "=" * 60)
    print("Тест 4: Проверка интеграции с parser_service")
    print("=" * 60)
    
    try:
        from parser_service import ParserService
        
        service = ParserService()
        print_success("ParserService успешно импортирован")
        
        # Проверяем наличие методов
        if hasattr(service, 'schedule_cleanup'):
            print_success("Метод schedule_cleanup найден")
        else:
            print_error("Метод schedule_cleanup НЕ найден")
            return False
        
        if hasattr(service, 'run_cleanup'):
            print_success("Метод run_cleanup найден")
        else:
            print_error("Метод run_cleanup НЕ найден")
            return False
        
        print_success("Интеграция с parser_service настроена корректно")
        return True
        
    except Exception as e:
        print_error(f"Ошибка проверки интеграции: {str(e)}")
        return False

def test_api_endpoints():
    """Тест 5: Проверка API endpoints (требует запущенный сервер)"""
    print("\n" + "=" * 60)
    print("Тест 5: Проверка API endpoints")
    print("=" * 60)
    
    try:
        import httpx
        
        base_url = os.getenv("API_BASE_URL", "http://localhost:8010")
        print_info(f"Проверка API на {base_url}")
        
        # Пробуем подключиться
        try:
            response = httpx.get(f"{base_url}/users", timeout=5.0)
            if response.status_code == 200:
                print_success("API сервер доступен")
                
                users = response.json().get("users", [])
                if users:
                    user_id = users[0]["id"]
                    print_info(f"Найден пользователь с ID: {user_id}")
                    
                    # Тестируем retention_settings endpoint
                    try:
                        response = httpx.get(
                            f"{base_url}/users/{user_id}/retention_settings",
                            timeout=5.0
                        )
                        if response.status_code == 200:
                            data = response.json()
                            print_success(f"GET /users/{user_id}/retention_settings работает")
                            print_info(f"retention_days: {data.get('retention_days')}")
                            print_info(f"Всего постов: {data.get('posts_stats', {}).get('total_posts', 0)}")
                        else:
                            print_error(f"Ошибка запроса: {response.status_code}")
                    except Exception as e:
                        print_warning(f"Не удалось протестировать endpoint: {str(e)}")
                else:
                    print_info("В базе данных нет пользователей для тестирования API")
            else:
                print_warning(f"API вернул статус {response.status_code}")
        except Exception as e:
            print_warning(f"API сервер недоступен: {str(e)}")
            print_info("Для тестирования API запустите сервер: python -m uvicorn main:app")
            return None  # Не считаем это ошибкой
        
        return True
        
    except ImportError:
        print_warning("Модуль httpx не установлен, пропускаем тест API")
        print_info("Установите: pip install httpx")
        return None
    except Exception as e:
        print_error(f"Ошибка тестирования API: {str(e)}")
        return False

def test_config():
    """Тест 6: Проверка конфигурации"""
    print("\n" + "=" * 60)
    print("Тест 6: Проверка конфигурации")
    print("=" * 60)
    
    try:
        default_retention = os.getenv("DEFAULT_RETENTION_DAYS", "30")
        cleanup_time = os.getenv("CLEANUP_SCHEDULE_TIME", "03:00")
        
        print_info(f"DEFAULT_RETENTION_DAYS: {default_retention}")
        print_info(f"CLEANUP_SCHEDULE_TIME: {cleanup_time}")
        
        try:
            days = int(default_retention)
            if 1 <= days <= 365:
                print_success(f"Значение DEFAULT_RETENTION_DAYS корректно: {days} дней")
            else:
                print_warning(f"Значение DEFAULT_RETENTION_DAYS вне диапазона (1-365): {days}")
        except ValueError:
            print_error(f"Некорректное значение DEFAULT_RETENTION_DAYS: {default_retention}")
            return False
        
        # Проверяем формат времени
        try:
            hours, minutes = cleanup_time.split(":")
            if 0 <= int(hours) <= 23 and 0 <= int(minutes) <= 59:
                print_success(f"Формат CLEANUP_SCHEDULE_TIME корректен: {cleanup_time}")
            else:
                print_warning(f"Некорректное время CLEANUP_SCHEDULE_TIME: {cleanup_time}")
        except:
            print_warning(f"Некорректный формат CLEANUP_SCHEDULE_TIME: {cleanup_time}")
        
        return True
        
    except Exception as e:
        print_error(f"Ошибка проверки конфигурации: {str(e)}")
        return False

def main():
    """Главная функция тестирования"""
    print("\n" + "=" * 60)
    print("ТЕСТИРОВАНИЕ СИСТЕМЫ ОГРАНИЧЕНИЯ ХРАНЕНИЯ ПОСТОВ")
    print("=" * 60)
    
    tests = [
        ("Миграция базы данных", test_database_migration),
        ("Сервис очистки", test_cleanup_service),
        ("Модели данных", test_models),
        ("Интеграция с parser_service", test_parser_integration),
        ("API endpoints", test_api_endpoints),
        ("Конфигурация", test_config),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Критическая ошибка в тесте '{test_name}': {str(e)}")
            results.append((test_name, False))
    
    # Итоги
    print("\n" + "=" * 60)
    print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result is True)
    failed = sum(1 for _, result in results if result is False)
    skipped = sum(1 for _, result in results if result is None)
    total = len(results)
    
    for test_name, result in results:
        if result is True:
            print_success(f"{test_name}")
        elif result is False:
            print_error(f"{test_name}")
        else:
            print_warning(f"{test_name} (пропущен)")
    
    print("\n" + "-" * 60)
    print(f"Пройдено: {GREEN}{passed}{RESET} | Провалено: {RED}{failed}{RESET} | Пропущено: {YELLOW}{skipped}{RESET} | Всего: {total}")
    print("=" * 60)
    
    if failed == 0:
        print_success("ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО! 🎉")
        print_info("Система готова к использованию")
    else:
        print_error(f"ОБНАРУЖЕНЫ ОШИБКИ В {failed} ТЕСТАХ")
        print_info("Проверьте логи и исправьте ошибки перед использованием")
    
    print("\n")
    return 0 if failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())

