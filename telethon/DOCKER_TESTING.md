# 🐳 Docker Testing Guide

**Запуск тестов в Docker контейнерах**

---

## 🎯 Зачем Docker для тестов?

✅ **Изолированное окружение** - не влияет на локальную систему  
✅ **Консистентность** - одинаковое окружение на всех машинах  
✅ **Простота** - не нужно настраивать PostgreSQL/Redis локально  
✅ **CI/CD ready** - те же команды в CI pipeline  

---

## ⚡ Quick Start

### 1 команда для запуска:

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# Unit тесты (быстро, 30-60 сек)
./run_tests_docker.sh unit

# Все тесты + coverage
./run_tests_docker.sh coverage
```

---

## 📋 Доступные режимы

### Unit Tests (рекомендуется для разработки)

```bash
./run_tests_docker.sh unit
```

**Особенности:**
- ✅ Быстро (~30-60 секунд)
- ✅ Не требует PostgreSQL (SQLite in-memory)
- ✅ Не требует Redis (FakeRedis)
- ✅ Моки всех внешних API

**Использование:**
- Ежедневная разработка
- Проверка изменений
- Pre-commit hooks

---

### Integration Tests

```bash
./run_tests_docker.sh integration
```

**Особенности:**
- ⏱️ Медленнее (~2-5 минут)
- 🐘 Требует PostgreSQL test контейнер
- 🔴 Требует Redis test контейнер
- 🔗 Тестирует реальные интеграции

**Использование:**
- Перед PR/merge
- После больших изменений
- Проверка интеграций

---

### All Tests + Coverage (полная проверка)

```bash
./run_tests_docker.sh all
# или
./run_tests_docker.sh coverage
```

**Особенности:**
- ⏱️ Полный запуск (~3-6 минут)
- 📊 Генерирует HTML coverage report
- 🎯 Проверяет >60% coverage
- 🐘 PostgreSQL + Redis test контейнеры

**Результат:**
- Coverage report в `htmlcov/index.html`
- Terminal coverage summary

**Использование:**
- Еженедельная проверка
- Перед релизом
- CI/CD pipeline

---

### Build (пересборка test image)

```bash
./run_tests_docker.sh build
```

**Когда использовать:**
- После изменения requirements.txt
- После изменения requirements-test.txt
- После изменения Dockerfile.test

---

## 🏗️ Архитектура

### Docker Compose Setup

```yaml
services:
  postgres-test:      # Временная PostgreSQL БД
    - In-memory (tmpfs)
    - Port 5433 (не конфликтует с основной)
    - Auto-cleanup после тестов
  
  redis-test:         # Временный Redis
    - Port 6380 (не конфликтует)
    - Auto-cleanup
  
  telethon-test-unit: # Unit тесты
    - SQLite in-memory
    - FakeRedis
    - No external services
  
  telethon-test-integration: # Integration тесты
    - PostgreSQL test
    - Redis test
    - Real connections
  
  telethon-test-all:  # Все тесты + coverage
    - PostgreSQL + Redis
    - Coverage report
```

### Изоляция

**Unit тесты:**
- ✅ Полностью изолированы
- ✅ Никаких внешних зависимостей
- ✅ Быстрые (in-memory DB)

**Integration тесты:**
- 🔗 Отдельные test сервисы (postgres-test, redis-test)
- 🔒 Не влияют на production БД
- 🧹 Auto-cleanup после запуска

---

## 📊 Coverage Report

После запуска с coverage:

```bash
./run_tests_docker.sh coverage
```

**Результат:**
```
htmlcov/
  ├── index.html          # Главная страница
  ├── models_py.html      # Coverage для models.py
  ├── bot_py.html         # Coverage для bot.py
  └── ...
```

**Открыть:**
```bash
# Linux
firefox htmlcov/index.html

# macOS
open htmlcov/index.html

# Windows
start htmlcov/index.html
```

---

## 🔧 Продвинутое использование

### Запуск конкретного теста в Docker

```bash
# Войти в контейнер
docker-compose -f docker-compose.test.yml run --rm telethon-test-unit bash

# Внутри контейнера
pytest tests/test_models.py -v
pytest tests/test_qr_auth_manager.py::TestQRAuthManager::test_create_qr_session -v
```

### Debug режим

```bash
# С print() output
docker-compose -f docker-compose.test.yml run --rm telethon-test-unit \
    pytest tests/ -m "unit" -v -s

# Остановка на первой ошибке
docker-compose -f docker-compose.test.yml run --rm telethon-test-unit \
    pytest tests/ -m "unit" -x -v
```

### Параллельный запуск

```bash
# Используя pytest-xdist
docker-compose -f docker-compose.test.yml run --rm telethon-test-unit \
    pytest tests/ -m "unit" -n auto -v
```

---

## 🐛 Troubleshooting

### Проблема: "Cannot connect to PostgreSQL"

**Решение:**
```bash
# Проверьте что postgres-test запущен
docker-compose -f docker-compose.test.yml ps

# Перезапустите
docker-compose -f docker-compose.test.yml down
./run_tests_docker.sh integration
```

### Проблема: "Port already in use"

**Решение:**
```bash
# PostgreSQL test использует порт 5433 (не 5432)
# Redis test использует порт 6380 (не 6379)

# Если конфликт, остановите test сервисы:
docker-compose -f docker-compose.test.yml down

# Проверьте что порты свободны:
lsof -i :5433
lsof -i :6380
```

### Проблема: Старый test image

**Решение:**
```bash
# Пересоберите test image
./run_tests_docker.sh build

# Или принудительно:
docker-compose -f docker-compose.test.yml build --no-cache telethon-test-unit
```

### Проблема: "No space left on device"

**Решение:**
```bash
# Очистка старых test контейнеров и volumes
docker-compose -f docker-compose.test.yml down -v

# Удаление неиспользуемых Docker объектов
docker system prune -f
```

---

## 📚 Сравнение: Local vs Docker

| Аспект | Local Tests | Docker Tests |
|--------|-------------|--------------|
| **Установка** | `pip install -r requirements-test.txt` | `./run_tests_docker.sh build` |
| **Запуск unit** | `pytest tests/ -m "unit"` | `./run_tests_docker.sh unit` |
| **PostgreSQL** | Нужна локальная установка | Автоматический контейнер |
| **Redis** | Нужна локальная установка | Автоматический контейнер |
| **Изоляция** | Зависит от окружения | Полная изоляция |
| **CI/CD** | Требует setup | Готово из коробки |
| **Скорость unit** | ~30 сек | ~40 сек (+overhead) |
| **Скорость integration** | ~2 мин | ~3 мин (+overhead) |

**Рекомендация:**
- 🏠 **Local** - для быстрой разработки (unit тесты)
- 🐳 **Docker** - для integration тестов и CI/CD

---

## 🚀 CI/CD Integration

### GitHub Actions

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Run unit tests
        run: |
          cd telethon
          ./run_tests_docker.sh unit
      
      - name: Run integration tests
        run: |
          cd telethon
          ./run_tests_docker.sh integration
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./telethon/coverage.xml
```

### GitLab CI

```yaml
test:
  image: docker:latest
  services:
    - docker:dind
  
  script:
    - cd telethon
    - ./run_tests_docker.sh all
  
  coverage: '/TOTAL.*\s+(\d+%)$/'
  
  artifacts:
    reports:
      coverage_report:
        coverage_format: cobertura
        path: coverage.xml
```

---

## 💡 Best Practices

### Development Workflow

**Ежедневно:**
```bash
# Быстрая проверка unit тестов
./run_tests_docker.sh unit
```

**Перед commit:**
```bash
# Unit тесты должны проходить
./run_tests_docker.sh unit
```

**Перед PR:**
```bash
# Полная проверка + coverage
./run_tests_docker.sh coverage
```

**Перед релизом:**
```bash
# Все тесты включая integration
./run_tests_docker.sh all
```

### Cleanup

```bash
# Остановить test сервисы
docker-compose -f docker-compose.test.yml down

# Удалить volumes (полная очистка)
docker-compose -f docker-compose.test.yml down -v

# Удалить test images
docker rmi telethon-test-unit telethon-test-integration telethon-test-all
```

---

## 📁 Структура файлов

```
telethon/
├── Dockerfile.test              # Docker image для тестов
├── docker-compose.test.yml      # Test services (PostgreSQL, Redis)
├── run_tests_docker.sh          # Helper script (этот гайд)
│
├── requirements.txt             # Production dependencies
├── requirements-test.txt        # Test dependencies
│
├── pytest.ini                   # Pytest configuration
├── .coveragerc                  # Coverage configuration
│
└── tests/                       # Тесты
    ├── conftest.py             # Fixtures
    ├── test_*.py               # Unit тесты
    ├── rag_service/            # RAG тесты
    ├── integration/            # Integration тесты
    └── utils/                  # Test utilities
```

---

## ✅ Checklist

**Первый запуск:**
- [ ] Docker и docker-compose установлены
- [ ] `chmod +x run_tests_docker.sh`
- [ ] Находитесь в `telethon/` директории
- [ ] Запустили `./run_tests_docker.sh build` (опционально)

**Unit тесты:**
- [ ] `./run_tests_docker.sh unit`
- [ ] Ожидается: 150+ tests passed
- [ ] Время: ~40-60 секунд

**Integration тесты:**
- [ ] `./run_tests_docker.sh integration`
- [ ] PostgreSQL и Redis контейнеры запускаются
- [ ] Ожидается: 8+ tests passed
- [ ] Время: ~3-5 минут

**Coverage:**
- [ ] `./run_tests_docker.sh coverage`
- [ ] Coverage report создан в `htmlcov/`
- [ ] Coverage >60%

---

## 🎉 Готово!

**Запустите прямо сейчас:**

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
./run_tests_docker.sh unit
```

**Ожидаемый результат:**
```
✅ Unit тесты завершены успешно!
150+ passed in 40s
```

---

**Версия:** 3.3.0  
**Дата:** 14 октября 2025  
**Статус:** ✅ Ready to Use

**Документация:**
- Local тесты: `tests/README.md`
- Docker тесты: `DOCKER_TESTING.md` (этот файл)
- Quick Start: `tests/QUICK_START_TESTING.md`

