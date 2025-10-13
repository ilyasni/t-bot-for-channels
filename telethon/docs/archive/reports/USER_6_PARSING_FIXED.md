# Пользователь 6 - Парсинг восстановлен

**Дата:** 13 октября 2025 01:56 UTC  
**User ID:** 6 (telegram_id=8124731874)  
**Проблема:** Event loop конфликт после объединения контейнеров  
**Статус:** ✅ ИСПРАВЛЕНО

---

## 🐛 Исходная проблема

### Симптомы:

```
ERROR:parser_service:❌ ParserService: Ошибка парсинга каналов пользователя 8124731874: 
The asyncio event loop must not change after connection
```

**Состояние:**
- ✅ Авторизация: `is_authenticated = true`
- ✅ Session файл: существует (28KB)
- ✅ Каналов: 15 активных
- ❌ Парсинг: не работает с 12.10.2025 10:35:30
- ❌ Новых постов: 0 за последние 15 часов

---

## 🔍 Корневая причина

### Event Loop конфликт после unified container

**Что произошло:**

1. **QR Auth Manager** создает Telethon client в своем event loop:
   ```python
   # В async task QR авторизации
   client = TelegramClient(session_path, api_id, api_hash)
   client.loop = <event loop A>
   active_clients[telegram_id] = client
   ```

2. **Parser Service** пытается использовать тот же client в другом event loop:
   ```python
   # В main event loop парсера
   client = shared_auth_manager.get_user_client(telegram_id)
   client.loop = <event loop A>  # ← ПРОБЛЕМА!
   current_loop = <event loop B>
   
   # Telethon: "Event loop must not change after connection!"
   ```

**Timeline:**

```
13.10 01:43:14 - QR авторизация (event loop A)
    ↓
Client сохранен в active_clients
    ↓
13.10 01:53:00 - Parser запускается (event loop B)
    ↓
Пытается использовать client из loop A
    ↓
ERROR: Event loop mismatch
```

**Причина конфликта:**

После объединения `telethon-bot` в основной контейнер `telethon`:
- **Bot** работает в async task (свой event loop)
- **Parser** работает в main event loop
- **QR Auth** создает clients в Bot event loop
- **Parser** пытается использовать эти clients → **КОНФЛИКТ**

---

## ✅ Решение

### Исправление в `shared_auth_manager.py`

**Добавлена проверка event loop при получении client:**

```python
async def get_user_client(self, telegram_id: int) -> Optional[TelegramClient]:
    """
    Получить активный клиент пользователя
    С проверкой правильности event loop
    """
    lock = self._get_client_lock(telegram_id)
    
    async with lock:
        # Если клиент уже активен - проверяем event loop
        if telegram_id in self.active_clients:
            client = self.active_clients[telegram_id]
            
            # ВАЖНО: Проверяем что клиент в правильном event loop
            try:
                if client.is_connected():
                    # Проверяем event loop
                    current_loop = asyncio.get_event_loop()
                    if client.loop != current_loop:
                        logger.warning(f"⚠️ Client {telegram_id} в другом event loop - пересоздаем")
                        await client.disconnect()
                        del self.active_clients[telegram_id]
                    else:
                        return client
                else:
                    await client.connect()
                    if client.is_connected():
                        return client
            except Exception as e:
                logger.warning(f"⚠️ Ошибка проверки клиента {telegram_id}: {e} - пересоздаем")
                if telegram_id in self.active_clients:
                    del self.active_clients[telegram_id]
        
        # Создаем новый клиент в текущем event loop
        client = await self._create_client(telegram_id)
        await client.connect()
        
        # ... проверки авторизации ...
        
        self.active_clients[telegram_id] = client
        logger.info(f"✅ Client {telegram_id} создан в event loop {id(client.loop)}")
        return client
```

**Ключевые изменения:**

1. ✅ Проверка `client.loop != current_loop`
2. ✅ Автоматическое пересоздание client в правильном loop
3. ✅ Логирование для отладки
4. ✅ Graceful cleanup старого client

---

## 🧪 Тестирование

### До исправления:

```bash
curl -X POST http://localhost:8010/parse_all_channels

# Результат:
ERROR: Event loop must not change after connection
✅ Добавлено 0 постов для пользователя 8124731874
```

### После исправления:

```bash
curl -X POST http://localhost:8010/parse_all_channels

# Результат:
INFO:parser_service:✅ ParserService: Пользователь 8124731874 - добавлено 36 постов
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 36 постов
```

**Логи (ключевые):**
```
INFO:shared_auth_manager:✅ Client 8124731874 создан в event loop 140282445968640
INFO:tagging_service:✅ TaggingService: Обработка завершена. Успешно: 35, Ошибок: 1
INFO:indexer:✅ Batch индексация завершена: успешно=36, пропущено=0, ошибок=0
```

---

## 📊 Результаты

### Пользователь 6 (8124731874)

**До исправления:**
- 📄 Постов: 101
- 🏷️ С тегами: ~95
- 📦 Индексировано: 101
- ⏸️ Последний пост: 12.10.2025 10:35:30
- ❌ Парсинг: НЕ РАБОТАЕТ

**После исправления:**
- 📄 Постов: **137** (+36!)
- 🏷️ С тегами: **136** (+35)
- 📦 Индексировано: **137** (+36)
- ✅ Последний пост: **12.10.2025 22:50:06**
- ✅ Парсинг: **РАБОТАЕТ**

**Improvement:**
```
+36 новых постов за 1 парсинг
+35 тегированных постов
+36 векторов в Qdrant
```

---

## 🎯 Что было сделано

### 1. Диагностика

- ✅ Выявлена проблема event loop конфликта
- ✅ Определена причина: unified container архитектура
- ✅ Найдено место в коде: `shared_auth_manager.py:470`

### 2. Исправление

- ✅ Добавлена проверка event loop
- ✅ Автоматическое пересоздание client при mismatch
- ✅ Логирование для мониторинга

### 3. Тестирование

- ✅ Ручной запуск парсинга: 36 постов
- ✅ Тегирование: 35 из 36 (1 rate limit)
- ✅ Индексация: все 36 в Qdrant
- ✅ Нет ошибок event loop

### 4. Документация

- ✅ `USER_SESSION_EXPIRED.md` - диагностика session проблем
- ✅ `QR_LOGIN_2FA_ISSUE.md` - проблема с 2FA
- ✅ `USER_6_PARSING_FIXED.md` - решение event loop

---

## 🔄 Pipeline работы

### До unified container (2 контейнера):

```
telethon-bot:           telethon:
  QR Auth                Parser Service
  (loop A)               (loop B)
     ↓                        ↓
  Client A            Использует Client A
     └─────────────────────────┘
           ❌ КОНФЛИКТ
```

**Проблема:** SQLite session locks

### После unified container + fix:

```
telethon (один контейнер):
  QR Auth (loop A)      Parser Service (loop B)
     ↓                        ↓
  Client A             Проверка loop mismatch
     ↓                        ↓
  active_clients       Удаление client A
     ↓                        ↓
     └────────────→    Создание Client B (loop B)
                              ↓
                       ✅ РАБОТАЕТ
```

**Решение:**
- ✅ Нет SQLite locks (один процесс)
- ✅ Автоматическое пересоздание clients в правильном loop

---

## 🚨 Известные ограничения

### 1. GigaChat Rate Limits

**Проблема (логи):**
```
ERROR:tagging_service:❌ TaggingService: Ошибка генерации тегов: 
illegal header line: ... HTTP/1.0 500 Error processing the request
```

**Fallback:**
```
INFO:tagging_service:🔄 TaggingService: Используем fallback - OpenRouter (deepseek/deepseek-chat-v3.1:free)
ERROR:tagging_service:❌ TaggingService: Ошибка API: 429 - rate-limited upstream
```

**Результат:**
- 35 из 36 постов тегировано
- 1 пост без тегов (будет обработан при следующей попытке)

**Решение:**
- ✅ Автоматический retry при следующем парсинге
- ✅ Fallback chain работает
- ⚠️ Рассмотреть платные API keys для стабильности

### 2. 2FA блокирует QR Login

**См. документацию:** `QR_LOGIN_2FA_ISSUE.md`

**Workaround:** Отключить 2FA на 5 минут для QR или использовать `/auth`

---

## ✅ Итог

### Проблема решена! ✅

**Было:**
- ❌ Event loop конфликт
- ❌ Парсинг не работает с 12.10
- ❌ 0 новых постов

**Стало:**
- ✅ Event loop проверка работает
- ✅ Парсинг восстановлен
- ✅ 36 новых постов за 1 запуск
- ✅ 35 постов тегировано
- ✅ 36 векторов в Qdrant

**Пользователь 6:**
- ✅ 137 постов всего
- ✅ 136 тегированных
- ✅ 137 проиндексированных
- ✅ Парсинг работает автоматически (каждые 30 минут)

---

## 🎯 Рекомендации

### Мониторинг event loops

Добавить логирование:
```python
logger.debug(f"Current loop: {id(asyncio.get_event_loop())}")
logger.debug(f"Client loop: {id(client.loop)}")
```

### Автоматическая очистка clients

Периодически очищать `active_clients` для предотвращения накопления stale clients:
```python
async def cleanup_stale_clients(self):
    """Очистка неактивных clients"""
    for telegram_id, client in list(self.active_clients.items()):
        if not client.is_connected():
            del self.active_clients[telegram_id]
```

### Healthcheck для парсинга

Добавить мониторинг успешности парсинга:
```bash
# Проверка что посты добавляются
SELECT COUNT(*) FROM posts 
WHERE created_at > NOW() - INTERVAL '1 hour';
```

---

**Создано:** 13 октября 2025  
**Статус:** ✅ Решено  
**Версия:** 3.2.2

