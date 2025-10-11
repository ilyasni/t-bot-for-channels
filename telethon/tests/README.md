# Тесты Telegram Channel Parser

## 📋 Доступные тесты

### `test_many_to_many.py`
Тесты многопользовательской системы:
- Тестирование миграции на many-to-many
- Проверка связей пользователей и каналов
- Валидация данных после миграции

### `test_retention_system.py`
Тесты системы хранения постов:
- Тестирование автоматической очистки
- Проверка retention_days
- Валидация логики удаления старых постов

## 🚀 Запуск тестов

```bash
# Запуск всех тестов
cd /home/ilyasni/n8n-server/n8n-installer/telethon
pytest tests/

# Запуск конкретного теста
pytest tests/test_many_to_many.py
pytest tests/test_retention_system.py

# Запуск с подробным выводом
pytest tests/ -v

# Запуск с покрытием кода
pytest tests/ --cov=. --cov-report=html
```

## 📝 Требования

Убедитесь, что установлены все зависимости:
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov
```

## ⚠️ Важно

- Тесты должны запускаться из корневой папки проекта
- Перед запуском создайте тестовую базу данных или используйте SQLite
- Некоторые тесты требуют настроенного .env файла

