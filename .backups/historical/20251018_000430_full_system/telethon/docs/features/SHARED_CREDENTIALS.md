# Shared Master Credentials - Технические детали

## 🎯 Концепция

**Shared Master Credentials** - архитектурный подход, при котором все пользователи используют один набор Telegram API credentials (API_ID/API_HASH), но каждый имеет индивидуальную сессию.

## 🏗️ Как это работает

### Традиционный подход (старый)

```
User A → Own API_ID_A + API_HASH_A → Session A → Telegram
User B → Own API_ID_B + API_HASH_B → Session B → Telegram
User C → Own API_ID_C + API_HASH_C → Session C → Telegram
```

**Проблемы:**
- Каждый пользователь должен создавать приложение на my.telegram.org
- Сложный onboarding (7+ шагов)
- Технический барьер для неопытных пользователей

### Shared Credentials (новый)

```
                  ┌─→ Session A (telegram_id: 123) → Telegram
MASTER_API_ID ────┼─→ Session B (telegram_id: 456) → Telegram
MASTER_API_HASH   └─→ Session C (telegram_id: 789) → Telegram
```

**Преимущества:**
- Пользователю НЕ нужны собственные credentials
- Простой onboarding (3 шага)
- Низкий технический барьер

## 🔐 Изоляция и безопасность

### Session файлы - ключ к изоляции

**Критично понимать:** Даже используя один `API_ID`, каждый session файл содержит **уникальный auth_key**, привязанный к конкретному номеру телефона пользователя.

```python
# User A (telegram_id: 123456789, phone: +7999111)
session_A = "sessions/user_123456789.session"
# Содержит: auth_key_A привязанный к +7999111

# User B (telegram_id: 987654321, phone: +7999222)
session_B = "sessions/user_987654321.session"
# Содержит: auth_key_B привязанный к +7999222
```

### Как Telegram идентифицирует пользователя

```
Запрос к Telegram API:
1. Client отправляет auth_key (из session файла)
2. Telegram проверяет auth_key в своей БД
3. Telegram определяет какому пользователю принадлежит auth_key
4. Возвращает данные ЭТОГО пользователя

API_ID используется только для:
- Идентификации приложения (не пользователя!)
- Rate limiting на уровне приложения
```

**Вывод:** Пользователь A НЕ МОЖЕТ получить данные пользователя B, даже используя один API_ID, т.к. у них разные auth_keys в session файлах.

### Проверки безопасности в коде

#### 1. Session Path по telegram_id

```python
def _get_session_path(self, telegram_id: int) -> str:
    """СТРОГО по telegram_id, НЕ по user.id из БД"""
    return f"sessions/user_{telegram_id}.session"
```

**Почему важно:**
- `user.id` - auto-increment, может быть 1, 2, 3...
- `telegram_id` - уникальный ID от Telegram, привязан к пользователю навсегда

#### 2. Session Validation после подключения

```python
async def get_user_client(self, telegram_id: int) -> TelegramClient:
    client = await self._create_client(telegram_id)
    await client.connect()
    
    # ✅ КРИТИЧНО: Проверка владельца
    me = await client.get_me()
    if me.id != telegram_id:
        logger.error(f"🚨 SECURITY: Session mismatch!")
        raise SecurityError("Session belongs to another user!")
    
    return client
```

**Защита от:**
- Перепутанных session файлов
- Подмены telegram_id
- Race conditions

#### 3. File Permissions

```python
# После создания session файла
os.chmod(session_path, 0o600)  # rw------- (только owner)
```

**Защита от:**
- Чтения session файлов другими пользователями системы
- Копирования session файлов

#### 4. Async Locks

```python
self.client_locks = {}  # telegram_id -> asyncio.Lock

async def get_user_client(self, telegram_id: int):
    lock = self._get_client_lock(telegram_id)
    
    async with lock:
        # Только один запрос за раз для этого пользователя
        client = self.active_clients.get(telegram_id)
        # ...
```

**Защита от:**
- Race conditions при параллельных запросах
- Перезаписи клиента другим запросом

## ⚠️ Риски и митигация

### Риск 1: Блокировка мастер приложения

**Причина:** Telegram ToS требуют индивидуальные API ключи для каждого пользователя

**Вероятность:** Низкая (многие сервисы так делают)

**Митигация:**
1. **Консервативный rate limiting:**
   ```python
   # Максимум 100-200 SMS в день с одного API_ID
   # Delay между парсингами каналов
   ```

2. **Обратная совместимость:**
   ```python
   # Сохранить возможность использования собственных credentials через /auth
   if user.api_id:  # Если у пользователя свои ключи
       use_user_credentials()
   else:  # Иначе используем мастер
       use_master_credentials()
   ```

3. **Подготовка запасного API_ID:**
   ```env
   MASTER_API_ID=12345678
   BACKUP_API_ID=87654321  # На случай блокировки основного
   ```

### Риск 2: Достижение rate limits

**Причина:** Все пользователи используют один API_ID

**Лимиты Telegram:**
- ~300 requests/second
- ~100-200 SMS codes/day
- FloodWait при превышении

**Митигация:**

1. **Queue система для парсинга:**
   ```python
   async def parse_with_queue(users: List[User]):
       for user in users:
           await parse_user_channels(user)
           await asyncio.sleep(2.0)  # Delay между пользователями
   ```

2. **Flood sleep threshold:**
   ```python
   client.flood_sleep_threshold = 120  # Авто-ожидание до 2 минут
   ```

3. **Приоритетный парсинг:**
   ```python
   # Premium пользователи парсятся чаще
   if user.subscription_type == "premium":
       parse_interval = 15  # минут
   else:
       parse_interval = 60  # минут
   ```

### Риск 3: Утечка session файлов

**Причина:** Session файл = полный доступ к аккаунту пользователя

**Митигация:**

1. **File permissions:**
   ```bash
   chmod 600 sessions/*.session
   chmod 700 sessions/
   ```

2. **.gitignore:**
   ```gitignore
   sessions/
   *.session
   *.session-journal
   ```

3. **Шифрование volume:**
   ```yaml
   # docker-compose
   volumes:
     - sessions-volume:/app/sessions
   ```

4. **Автоочистка неактивных:**
   ```python
   # Удалять session если не использовался >30 дней
   if last_used < now() - timedelta(days=30):
       os.remove(session_path)
   ```

## 🔬 Технические детали

### Telethon Session Structure

```python
# session.sqlite (упрощенно)
tables:
  - sessions (dc_id, server_address, port, auth_key, date, takeout_id)
  - entities (id, hash, username, phone, name)
  - sent_files (md5_digest, file_size, type, id, hash)
  - update_state (id, pts, qts, date, seq)
```

**auth_key** - главное:
- 256-byte ключ для шифрования
- Генерируется при первой авторизации
- Привязан к номеру телефона пользователя
- Уникален для каждого пользователя

### MTProto под капотом

```
User Request → Telethon → MTProto Layer
                              ↓
                    Шифрование с auth_key
                              ↓
                    Telegram Server
                              ↓
                    Проверка auth_key
                              ↓
                    Определение user_id
                              ↓
                    Возврат данных пользователя
```

**API_ID роль:**
- Идентифицирует приложение (не пользователя)
- Rate limiting на уровне приложения
- Статистика использования API

### StringSession альтернатива

**Для будущего масштабирования:**

```python
# Вместо file-based sessions можно использовать StringSession
from telethon.sessions import StringSession

# Сохранить в БД
client = TelegramClient(StringSession(), api_id, api_hash)
await client.start(phone)
session_string = client.session.save()  # Строка

# Сохранить в БД (зашифрованным)
user.session_string = crypto_manager.encrypt(session_string)
db.commit()

# Восстановить из БД
session_string = crypto_manager.decrypt(user.session_string)
client = TelegramClient(StringSession(session_string), api_id, api_hash)
await client.connect()
```

**Преимущества:**
- Проще backup (все в БД)
- Нет файлов на диске
- Легче миграция между серверами

**Недостатки:**
- Больше нагрузка на БД
- Сложнее отладка

## 🚀 Масштабирование

### Horizontal Scaling

**Проблема:** Несколько инстансов бота с shared sessions

**Решение 1: Shared storage для sessions**

```yaml
# docker-compose
services:
  telethon-1:
    volumes:
      - nfs-sessions:/app/sessions
  telethon-2:
    volumes:
      - nfs-sessions:/app/sessions

volumes:
  nfs-sessions:
    driver: nfs
```

**Решение 2: StringSession в БД**

См. выше - сессии хранятся в PostgreSQL, доступны всем инстансам.

### Балансировка нагрузки

**Telegram rate limits per API_ID:**

При 1000+ пользователей:

```env
# Несколько мастер приложений
MASTER_API_IDS=12345678,87654321,11122233
MASTER_API_HASHES=hash1,hash2,hash3
```

```python
# Распределение пользователей
api_index = user.id % len(MASTER_API_IDS)
api_id = MASTER_API_IDS[api_index]
api_hash = MASTER_API_HASHES[api_index]
```

## 📊 Мониторинг

### Метрики для shared credentials

```python
from prometheus_client import Counter, Gauge

telegram_api_calls = Counter('telegram_api_calls_total', 'API calls', ['api_id'])
telegram_flood_waits = Counter('telegram_flood_waits_total', 'Flood waits', ['api_id'])
active_sessions = Gauge('active_telegram_sessions', 'Active sessions')
```

### Логирование

```python
logger.info(
    "Telegram API call",
    extra={
        "api_id": MASTER_API_ID,
        "user_telegram_id": telegram_id,
        "method": "get_messages",
        "channel": channel_username
    }
)
```

## 🔗 Связанные документы

- [Система подписок](SUBSCRIPTIONS.md)
- [Упрощенная авторизация](../quickstart/SIMPLE_LOGIN.md)
- [Админ команды](../../ADMIN_QUICKSTART.md)
- [Безопасность](README_SECURE.md)

