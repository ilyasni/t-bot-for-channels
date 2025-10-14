# Changelog: Event Loop Fix

## [HOTFIX] Event Loop - 14.10.2025

### 🐛 Исправленные проблемы

**Критическая проблема:** Парсер возвращал 0 постов для всех каналов из-за ошибок event loop.

```
ERROR:parser_service:❌ ParserService: Ошибка event loop для @channel - переподключение клиента
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 0 постов
```

### 📚 Context7 анализ

Использованы источники:
- **Telethon Official Docs** - Managing Asyncio Event Loop
- **Telethon GitHub** - Asyncio best practices
- Ключевой принцип: "Only one call to asyncio.run() is needed for the entire application"

### 🔧 Изменения

#### 1. `parser_service.py`

**Строки 230-243: Исправлен `run_parsing()`**
```python
# ДО (❌ НЕПРАВИЛЬНО):
def run_parsing(self):
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(self.parse_all_channels())
    else:
        asyncio.run(self.parse_all_channels())  # Создавал НОВЫЙ loop!

# ПОСЛЕ (✅ ПРАВИЛЬНО):
def run_parsing(self):
    loop = asyncio.get_running_loop()  # Только текущий loop
    asyncio.create_task(self.parse_all_channels())  # Только task, не новый loop
```

**Строки 108-110: Убраны попытки переподключения**
```python
# ДО (❌ усугубляло проблему):
if "event loop must not change" in error_msg:
    await client.disconnect()
    await client.connect()  # Подключение в ДРУГОМ loop!

# ПОСЛЕ (✅ просто логирование):
logger.error(f"❌ ParserService: Ошибка парсинга @{channel}: {error_msg}")
```

**Строки 114-117: Клиенты НЕ удаляются после парсинга**
```python
# ДО (❌ заставляло создавать новые клиенты):
finally:
    if client:
        await client.disconnect()
        del secure_auth_manager.active_clients[user.id]

# ПОСЛЕ (✅ клиент остается в том же loop):
except Exception as e:
    return 0
# НЕ УДАЛЯЕМ клиент! Он должен оставаться в том же event loop
```

**Строки 484-501: Добавлена документация**
```python
async def run_parser_service(interval_minutes=30):
    """
    ВАЖНО: Согласно Context7 Telethon best practices:
    - asyncio.run() должен вызываться ТОЛЬКО ОДИН РАЗ для всего приложения
    - Telethon клиенты НЕ МОГУТ работать если event loop изменился после подключения
    - Все операции должны выполняться внутри одного event loop
    """
```

#### 2. `shared_auth_manager.py`

**Строки 456-529: Улучшена логика `get_user_client()`**
```python
# Добавлено подробное логирование при обнаружении неправильного loop
if client.loop != current_loop:
    logger.warning(
        f"⚠️ Client {telegram_id} создан в другом event loop!\n"
        f"   Client loop: {id(client.loop)}\n"
        f"   Current loop: {id(current_loop)}\n"
        f"   Это НЕ ДОЛЖНО происходить если приложение правильно использует asyncio.run() ОДИН РАЗ"
    )
```

#### 3. `run_system.py`

**Строки 183-187: Упрощен entry point**
```python
# ДО (❌ избыточные проверки):
try:
    loop = asyncio.get_event_loop()
    if loop.is_running():
        asyncio.create_task(main())
    else:
        asyncio.run(main())
except RuntimeError:
    asyncio.run(main())

# ПОСЛЕ (✅ простой и правильный):
# КРИТИЧНО (Context7 best practices):
# asyncio.run() вызывается ТОЛЬКО ОДИН РАЗ - это создает главный event loop
asyncio.run(main())
```

### 📄 Новые файлы документации

1. **`docs/EVENT_LOOP_FIX.md`**
   - Подробное объяснение проблемы и решения
   - Ссылки на Context7 источники
   - Примеры правильного и неправильного кода

2. **`TESTING_EVENT_LOOP_FIX.md`**
   - Пошаговая инструкция по тестированию
   - Команды для диагностики
   - Критерии успеха

3. **`CHANGELOG_EVENT_LOOP.md`** (этот файл)
   - Краткое резюме всех изменений

### 🎯 Ожидаемые результаты

#### До исправления:
```
INFO:parser_service:🔄 ParserService: Парсинг 15 каналов
ERROR:parser_service:❌ ParserService: Ошибка event loop для @channel1
ERROR:parser_service:❌ ParserService: Ошибка event loop для @channel2
...
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 0 постов
```

#### После исправления:
```
INFO:parser_service:🔄 ParserService: Парсинг 15 каналов
INFO:parser_service:✅ ParserService: @channel1 - добавлено 5 постов
INFO:parser_service:✅ ParserService: @channel2 - добавлено 3 постов
...
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 47 постов
```

### 🔍 Проверка

```bash
# 1. Перезапустить
docker-compose restart telethon

# 2. Проверить логи (НЕ должно быть ошибок event loop)
docker logs telethon --tail 50 -f

# 3. Запустить парсинг вручную
curl -X POST http://localhost:8010/parse/user/{USER_ID}

# 4. Проверить результат (должно быть > 0 постов)
docker logs telethon | grep "добавлено"
```

### 🏆 Принципы (Context7)

После этого исправления проект следует **Telethon best practices**:

1. ✅ **Один event loop** - `asyncio.run()` вызывается ОДИН РАЗ в entry point
2. ✅ **Переиспользование клиентов** - клиенты создаются один раз и остаются в том же loop
3. ✅ **Только create_task()** - для операций внутри running loop используется `asyncio.create_task()`
4. ✅ **Правильная обработка ошибок** - нет попыток переподключения клиентов при ошибках event loop

### 📖 Ссылки

- [Telethon FAQ - Event Loop](https://docs.telethon.dev/en/v2/developing/faq)
- [Context7 Analysis](docs/EVENT_LOOP_FIX.md)
- [Testing Guide](TESTING_EVENT_LOOP_FIX.md)

### 👥 Contributors

- **AI Assistant** - Анализ проблемы и исправление
- **Context7** - Официальная документация Telethon
- **User** - Обнаружение проблемы

---

**Version:** 1.0.0  
**Date:** 14.10.2025  
**Status:** ✅ Ready for Testing  
**Priority:** CRITICAL

