# 🧪 Проверьте тесты прямо сейчас!

**3 простых команды для проверки что все работает**

---

## ⚡ Шаг 1: Установка (1 минута)

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon

# Установить test dependencies
pip install -r requirements-test.txt
```

**Ожидаемый вывод:**
```
Successfully installed pytest-7.4.x pytest-asyncio-0.21.x ...
```

---

## ⚡ Шаг 2: Запуск тестов (30 секунд)

```bash
# Unit тесты (быстрые, с моками)
pytest tests/ -m "unit" -v --tb=short
```

**Ожидаемый вывод:**
```
============ test session starts ============
collected 150+ items

tests/test_models.py::TestUserModel::test_user_creation_with_timezone PASSED [ 1%]
tests/test_models.py::TestUserModel::test_user_subscription_active PASSED [ 2%]
tests/test_qr_auth_manager.py::TestQRAuthManager::test_create_qr_session PASSED [ 3%]
...

============ 150+ passed in 30s ============
```

✅ **Если все PASSED - отлично!**

---

## ⚡ Шаг 3: Coverage Report (1 минута)

```bash
# Генерация coverage report
pytest tests/ -m "unit" --cov=. --cov-report=html --cov-report=term

# Открыть HTML отчет
open htmlcov/index.html
# или для Linux:
firefox htmlcov/index.html
```

**Ожидаемый coverage:**
```
Name                          Stmts   Miss  Cover
-------------------------------------------------
models.py                       450     90    80%
qr_auth_manager.py             180     45    75%
bot.py                         800    280    65%
parser_service.py              250     75    70%
...
-------------------------------------------------
TOTAL                         5000   1750    65%
```

✅ **Если >60% - target достигнут!**

---

## 🔍 Быстрая проверка компонентов

### Models
```bash
pytest tests/test_models.py -v
# Ожидается: 24 теста PASSED
```

### Authentication
```bash
pytest tests/ -m "auth" -v
# Ожидается: 21+ тестов PASSED
```

### Bot Handlers
```bash
pytest tests/test_bot_commands.py -v
pytest tests/test_bot_rag_commands.py -v
# Ожидается: 20+ тестов PASSED
```

### RAG Service
```bash
pytest tests/rag_service/ -v
# Ожидается: 37+ тестов PASSED
```

---

## 🐛 Если тесты не проходят

### ImportError

```bash
# Убедитесь что в правильной директории
pwd
# Должно быть: /home/ilyasni/n8n-server/n8n-installer/telethon

# Установите PYTHONPATH
export PYTHONPATH=$PWD:$PWD/rag_service
pytest tests/ -m "unit" -v
```

### Database Errors

```bash
# Unit тесты НЕ требуют PostgreSQL (используют SQLite in-memory)
# Просто запустите:
pytest tests/ -m "unit" -v
```

### Module not found: fakeredis

```bash
# Установите dependencies
pip install fakeredis pytest-httpx pytest-mock
pytest tests/ -m "unit" -v
```

### Async warnings

```bash
# Проверьте что pytest-asyncio установлен
pip install pytest-asyncio

# Проверьте pytest.ini
cat pytest.ini | grep asyncio_mode
# Должно быть: asyncio_mode = auto
```

---

## 📊 Ожидаемые результаты

### Unit Tests (марка "unit")

```
Файлов с тестами:    25+
Тестовых функций:    150+
Время выполнения:    30-60 секунд
Требуемые сервисы:   Нет (все моки)
Expected coverage:   60-70%
```

### Integration Tests (марка "integration")

```
Файлов с тестами:    3
Тестовых функций:    8+
Время выполнения:    2-5 минут
Требуемые сервисы:   PostgreSQL, Redis
Expected coverage:   Дополнительные 5-10%
```

---

## ✅ Checklist проверки

**После установки:**
- [ ] `pytest --version` показывает 7.4+
- [ ] `pytest tests/ --co` показывает 150+ тестов
- [ ] Файл `tests/conftest.py` существует
- [ ] Файл `pytest.ini` существует

**После запуска unit:**
- [ ] Все тесты PASSED (или >95%)
- [ ] Нет FAILED тестов
- [ ] Время выполнения <2 минут
- [ ] Нет import errors

**После coverage:**
- [ ] Overall coverage >60%
- [ ] HTML отчет создан в `htmlcov/`
- [ ] Models coverage >75%
- [ ] Auth coverage >70%

---

## 🎯 Быстрые команды

```bash
# Алиасы для удобства (добавьте в ~/.bashrc)
alias pytest-unit='pytest tests/ -m "unit" -v'
alias pytest-cov='pytest tests/ --cov=. --cov-report=html'
alias pytest-fast='pytest tests/ -n auto -v'
alias pytest-auth='pytest tests/ -m "auth" -v'
alias pytest-rag='pytest tests/ -m "rag" -v'
```

---

## 💡 Рекомендации

**Development workflow:**

1. **При изменении кода → запустить unit тесты:**
   ```bash
   pytest tests/ -m "unit" -k "test_models" -v
   ```

2. **Перед commit → проверить coverage:**
   ```bash
   ./tests/run_tests.sh coverage
   ```

3. **Перед PR → запустить все тесты:**
   ```bash
   ./tests/run_tests.sh all
   ```

**CI/CD:**
- Unit тесты на каждый commit
- Integration тесты на develop/main
- Coverage reports в Codecov/Coveralls

---

## 📚 Помощь

**Документация:**
- `tests/QUICK_START_TESTING.md` - этот файл
- `tests/README.md` - полное руководство
- `TESTING.md` - project-level guide

**Примеры:**
- Смотрите любой `tests/test_*.py` файл
- Изучите `tests/conftest.py` для fixtures
- Проверьте `tests/utils/` для utilities

**Troubleshooting:**
- Секция в `tests/README.md`
- Или запустите с `-v -s` для debug

---

## 🎉 Готово!

Test suite полностью реализован и готов к использованию.

**Следующий шаг:**
```bash
./tests/run_tests.sh unit
```

**Удачи! 🚀**

---

**Версия:** 3.3.0  
**Статус:** ✅ Ready to Test  
**Обновлено:** 14 октября 2025

