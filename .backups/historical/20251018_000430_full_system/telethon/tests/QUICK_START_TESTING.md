# 🚀 Quick Start - Testing

**Быстрый старт для запуска тестов проекта**

---

## ⚡ 3 шага для начала

### 🐳 Вариант 1: Docker (рекомендуется)

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# Unit тесты в Docker (не требует установки dependencies)
./run_tests_docker.sh unit
```

**Время:** ~40-60 секунд  
**Преимущества:** Изолированное окружение, не требует локальной установки

### 💻 Вариант 2: Local

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# Установить test dependencies
pip install -r requirements-test.txt
```

**Время:** ~1 минута  
**Преимущества:** Быстрее для разработки

---

### Шаг 2: Запуск Unit тестов

**Docker (рекомендуется):**
```bash
./run_tests_docker.sh unit
```

**Local:**
```bash
pytest tests/ -m "unit" -v
```

**Ожидаемый результат:**
```
============ test session starts ============
collected 100+ items

tests/test_models.py::TestUserModel::test_user_creation_with_timezone PASSED
tests/test_models.py::TestUserModel::test_user_subscription_active PASSED
...
============ 100+ passed in 30s ============
```

**Время:** ~30-60 секунд

---

### Шаг 3: Coverage Report

```bash
# Запуск с coverage
pytest tests/ --cov=. --cov-report=html

# Открыть отчет
open htmlcov/index.html
# или
firefox htmlcov/index.html
```

**Ожидаемый coverage:** 60-70%

---

## 🎯 Режимы запуска

### Helper Script (рекомендуется)

```bash
chmod +x tests/run_tests.sh

# Unit тесты (быстро)
./tests/run_tests.sh unit

# Coverage
./tests/run_tests.sh coverage

# Параллельно (быстрее)
./tests/run_tests.sh fast
```

### Прямой pytest

```bash
# Все тесты
pytest tests/ -v

# Только unit
pytest tests/ -m "unit" -v

# Только integration
pytest tests/ -m "integration" -v

# Specific component
pytest tests/ -m "auth" -v
pytest tests/ -m "rag" -v
pytest tests/ -m "groups" -v
```

---

## 📊 Что тестируется?

✅ **Models** (15+ тестов)
- User, Channel, Post, Group, InviteCode
- Relationships, validation, timezone

✅ **Authentication** (21+ тестов)
- QR login через Mini App
- Shared credentials
- Admin sessions

✅ **Bot Handlers** (42+ тестов)
- Все команды бота
- RAG команды (/ask, /search)
- Голосовые команды (Premium)
- Group команды

✅ **Services** (35+ тестов)
- Parser service
- Tagging service
- RAG service (vector DB, embeddings, search)
- Voice transcription
- Group monitoring

✅ **API Endpoints** (19+ тестов)
- Main API
- Admin API
- RAG API

✅ **Integration** (6+ тестов)
- Полные workflows
- Multi-user scenarios

**Всего:** 120+ тестовых функций

---

## 🔍 Примеры команд

### Запуск конкретного файла

```bash
pytest tests/test_models.py -v
pytest tests/test_qr_auth_manager.py -v
pytest tests/rag_service/test_embeddings.py -v
```

### Запуск конкретного теста

```bash
pytest tests/test_models.py::TestUserModel::test_user_creation_with_timezone -v
```

### Фильтрация по markers

```bash
# Auth тесты
pytest tests/ -m "auth" -v

# RAG тесты (без slow)
pytest tests/ -m "rag and not slow" -v

# Только быстрые unit
pytest tests/ -m "unit and not slow" -v
```

### Debug режим

```bash
# С print() output
pytest tests/ -v -s

# Остановка на первой ошибке
pytest tests/ -x -v

# Только failed tests
pytest tests/ --lf -v
```

---

## 🎨 Markers

| Marker | Описание | Пример |
|--------|----------|--------|
| `unit` | Unit тесты (моки) | `pytest -m "unit"` |
| `integration` | Integration тесты | `pytest -m "integration"` |
| `slow` | Медленные тесты (>1s) | `pytest -m "not slow"` |
| `auth` | Authentication | `pytest -m "auth"` |
| `rag` | RAG system | `pytest -m "rag"` |
| `groups` | Groups функционал | `pytest -m "groups"` |
| `voice` | Voice transcription | `pytest -m "voice"` |

---

## 💡 Tips

**Быстрая проверка:**
```bash
# Только критичные тесты (auth + models)
pytest tests/ -m "auth or test_models" -v
```

**Параллельный запуск:**
```bash
# Используйте все CPU cores
pytest tests/ -n auto -v
```

**Watch mode (перезапуск при изменениях):**
```bash
# Требует pytest-watch
pip install pytest-watch
ptw tests/ -- -m "unit"
```

---

## ✅ Checklist

**Перед первым запуском:**
- [ ] Python 3.9+ установлен
- [ ] Virtual environment активирован
- [ ] `pip install -r requirements-test.txt`
- [ ] Находитесь в директории `telethon/`

**Для unit тестов:**
- [ ] Не требуют внешние сервисы
- [ ] Запуск: `pytest tests/ -m "unit" -v`
- [ ] Должно pass: 100+ тестов

**Для integration тестов:**
- [ ] PostgreSQL running (localhost:5432)
- [ ] Redis running (localhost:6379)
- [ ] `.env` с `TELEGRAM_DATABASE_URL`
- [ ] Запуск: `pytest tests/ -m "integration" -v`

---

## 📚 Дополнительная информация

- **Полная документация:** `tests/README.md`
- **Testing guide:** `TESTING.md`
- **Coverage config:** `.coveragerc`
- **Pytest config:** `pytest.ini`

---

**Версия:** 3.3.0  
**Статус:** ✅ Готово к использованию  
**Обновлено:** 14 октября 2025

