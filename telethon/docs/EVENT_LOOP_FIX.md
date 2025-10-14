# Event Loop Fix - Решение проблемы "event loop must not change"

**Дата:** 14 октября 2025  
**Статус:** ✅ Исправлено  
**Приоритет:** КРИТИЧНЫЙ

---

## 🔴 Проблема

Парсер получал ошибки для ВСЕХ каналов:

```
ERROR:parser_service:❌ ParserService: Ошибка event loop для @channel_name - переподключение клиента
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 0 постов
```

**Результат:** 0 постов парсилось, система полностью не работала.

---

## 🔍 Корневая причина (Context7 Analysis)

Согласно официальной документации Telethon (через Context7):

> **"Telethon cannot function correctly if the asyncio event loop is changed after `Client.connect()` is called. Avoid using `asyncio.run()` multiple times."**

### Проблемные места в коде:

#### 1. **parser_service.py:252-267** - `run_parsing()` метод

```python
# ❌ НЕПРАВИЛЬНО - создавал НОВЫЙ event loop каждый раз
def run_parsing(self):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(self.parse_all_channels())
        else:
            asyncio.run(self.parse_all_channels())  # НОВЫЙ LOOP!
    except RuntimeError:
        asyncio.run(self.parse_all_channels())  # ЕЩЕ ОДИН НОВЫЙ LOOP!
```

**Почему это плохо:**
- `asyncio.run()` создает **совершенно новый** event loop
- Telethon клиенты уже подключены к **старому** event loop
- Telethon выбрасывает исключение при попытке использовать клиент в другом loop

#### 2. **parser_service.py:113-116** - попытки переподключения

```python
# ❌ НЕПРАВИЛЬНО - усугубляло проблему
if "event loop must not change" in error_msg:
    await client.disconnect()  # Отключаем в одном loop
    await client.connect()     # Подключаем в ДРУГОМ loop - ОШИБКА!
```

#### 3. **parser_service.py:127-139** - удаление клиентов после каждого парсинга

```python
# ❌ НЕПРАВИЛЬНО - заставляло создавать новые клиенты в новых loops
finally:
    if client:
        await client.disconnect()
        del secure_auth_manager.active_clients[user.id]
```

---

## ✅ Решение (Context7 Best Practices)

### Принципы (из Context7 Telethon documentation):

1. **asyncio.run() вызывается ТОЛЬКО ОДИН РАЗ для всего приложения**
2. **Все async операции выполняются внутри ОДНОГО event loop**
3. **Telethon клиенты НЕ ПЕРЕСОЗДАЮТСЯ без необходимости**

### Исправления:

#### 1. Исправлен `run_parsing()` - только `create_task()`

```python
# ✅ ПРАВИЛЬНО - использует текущий running loop
def run_parsing(self):
    try:
        # КРИТИЧНО: НЕ используем asyncio.run() - это создает НОВЫЙ event loop!
        # Telethon клиенты должны работать в ТОМ ЖЕ event loop где были созданы
        loop = asyncio.get_running_loop()
        asyncio.create_task(self.parse_all_channels())
        logger.debug("📅 ParserService: Задача парсинга создана в текущем event loop")
    except RuntimeError:
        # Если loop не запущен - это ОШИБКА конфигурации
        logger.error("❌ ParserService: ОШИБКА! run_parsing() вызван ВНЕ event loop.")
```

#### 2. Убраны попытки переподключения при ошибках event loop

```python
# ✅ ПРАВИЛЬНО - просто логируем ошибку
except Exception as e:
    error_msg = str(e)
    logger.error(f"❌ ParserService: Ошибка парсинга @{channel.channel_username}: {error_msg}")
```

#### 3. Клиенты НЕ удаляются после парсинга

```python
# ✅ ПРАВИЛЬНО - клиент остается в том же event loop для последующих парсингов
except Exception as e:
    logger.error(f"❌ ParserService: Ошибка парсинга каналов пользователя {user.telegram_id}: {str(e)}")
    return 0
# НЕ УДАЛЯЕМ клиент! Он должен оставаться в том же event loop для последующих парсингов
```

#### 4. Улучшено логирование в `shared_auth_manager.py`

```python
# ✅ ПРАВИЛЬНО - подробное логирование при обнаружении неправильного loop
current_loop = asyncio.get_running_loop()

if client.loop != current_loop:
    logger.warning(
        f"⚠️ Client {telegram_id} создан в другом event loop!\n"
        f"   Client loop: {id(client.loop)}\n"
        f"   Current loop: {id(current_loop)}\n"
        f"   Это НЕ ДОЛЖНО происходить если приложение правильно использует asyncio.run() ОДИН РАЗ"
    )
```

---

## 📚 Context7 References

Использованные источники из Context7:

1. **Managing Asyncio Event Loop with Telethon**
   - Source: https://docs.telethon.dev/en/v2/developing/faq
   - Key quote: "Only one call to asyncio.run() is needed for the entire application"

2. **Asyncio Client Initialization and Usage**
   - Source: https://github.com/lonamiwebs/telethon
   - Pattern: Single `async def main()` with `asyncio.run(main())`

3. **Run Multiple Telethon Tasks Concurrently**
   - Source: Telethon asyncio concepts
   - Pattern: `loop.create_task()` for concurrent operations

---

## 🧪 Проверка исправления

### До исправления:
```
ERROR:parser_service:❌ ParserService: Ошибка event loop для @channel1
ERROR:parser_service:❌ ParserService: Ошибка event loop для @channel2
...
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 0 постов
```

### После исправления (ожидаемое поведение):
```
INFO:parser_service:🔄 ParserService: Парсинг 15 каналов для пользователя 8124731874
INFO:parser_service:✅ ParserService: @channel1 - добавлено 5 постов
INFO:parser_service:✅ ParserService: @channel2 - добавлено 3 постов
...
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 47 постов
```

### Команды для проверки:

```bash
# 1. Перезапустить контейнер
docker-compose restart telethon

# 2. Проверить логи
docker logs telethon --tail 100 -f | grep -E "(парсинг|event loop|добавлено)"

# 3. Ожидаемое - нет ошибок event loop, есть добавленные посты
```

---

## 🎯 Ключевые выводы

1. **ВСЕГДА используйте Context7 перед изменением кода с asyncio/Telethon**
2. **asyncio.run() = ОДИН РАЗ** для всего приложения
3. **НЕ пересоздавайте Telethon клиенты** без крайней необходимости
4. **НЕ меняйте event loop** после подключения клиента
5. **Используйте asyncio.create_task()** для всех операций внутри running loop

---

## 📖 Дополнительная документация

- [Telethon FAQ - Event Loop](https://docs.telethon.dev/en/v2/developing/faq)
- [Telethon Asyncio Concepts](https://docs.telethon.dev/en/v2/concepts/asyncio)
- [Python asyncio Documentation](https://docs.python.org/3/library/asyncio.html)

---

**Автор:** AI Assistant с использованием Context7  
**Reviewers:** Требуется проверка после деплоя  
**Status:** ✅ Ready for Testing

