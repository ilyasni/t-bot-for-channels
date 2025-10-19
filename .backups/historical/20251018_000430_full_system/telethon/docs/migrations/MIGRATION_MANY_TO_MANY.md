# Миграция к структуре многие-ко-многим (Many-to-Many)

## 📋 Обзор изменений

Эта миграция устраняет дублирование каналов в базе данных, когда несколько пользователей подписываются на один и тот же канал.

### Проблема (до миграции)
```
channels:
  id | user_id | channel_username
  1  | 100     | durov
  2  | 200     | durov  ← дубликат!
  3  | 100     | news
  4  | 200     | news   ← дубликат!
```

### Решение (после миграции)
```
channels:
  id | channel_username
  1  | durov
  2  | news

user_channel (связующая таблица):
  user_id | channel_id | is_active | created_at | last_parsed_at
  100     | 1          | true      | ...        | ...
  200     | 1          | true      | ...        | ...
  100     | 2          | true      | ...        | ...
  200     | 2          | true      | ...        | ...
```

## 🎯 Преимущества

1. **Нет дублирования**: Один канал = одна запись
2. **Эффективность**: Меньше записей в БД
3. **Масштабируемость**: Легко добавлять новых пользователей к существующим каналам
4. **Гибкость**: Индивидуальные настройки подписки для каждого пользователя

## 🏗️ Изменения в структуре данных

### 1. Таблица `channels`

**Было:**
```sql
CREATE TABLE channels (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,          -- ← удалено
    channel_username VARCHAR NOT NULL,
    channel_id BIGINT,
    channel_title VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,    -- ← перенесено в user_channel
    created_at TIMESTAMP,
    last_parsed_at TIMESTAMP           -- ← перенесено в user_channel
)
```

**Стало:**
```sql
CREATE TABLE channels (
    id INTEGER PRIMARY KEY,
    channel_username VARCHAR NOT NULL UNIQUE,  -- ← теперь уникальный
    channel_id BIGINT UNIQUE,
    channel_title VARCHAR,
    created_at TIMESTAMP
)
```

### 2. Новая таблица `user_channel`

```sql
CREATE TABLE user_channel (
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,        -- активность подписки
    created_at TIMESTAMP,                  -- дата подписки
    last_parsed_at TIMESTAMP,              -- последний парсинг для пользователя
    PRIMARY KEY (user_id, channel_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (channel_id) REFERENCES channels(id) ON DELETE CASCADE
)
```

## 🔄 Процесс миграции

### Шаг 1: Резервное копирование

```bash
# Автоматически создается при запуске скрипта миграции (для SQLite)
# Файл: telegram.db.backup_YYYYMMDD_HHMMSS
```

### Шаг 2: Запуск миграции

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python3 migrate_to_many_to_many.py
```

### Что делает скрипт:

1. ✅ Создает таблицу `user_channel`
2. ✅ Читает все записи из старой таблицы `channels`
3. ✅ Группирует каналы по `channel_username`
4. ✅ Создает уникальные записи каналов
5. ✅ Создает связи в таблице `user_channel`
6. ✅ Обновляет ссылки в таблице `posts`
7. ✅ Удаляет старую таблицу и переименовывает новую
8. ✅ Создает индексы

### Шаг 3: Проверка результатов

```bash
# Посмотреть статистику
sqlite3 telegram.db "SELECT COUNT(*) as channels FROM channels;"
sqlite3 telegram.db "SELECT COUNT(*) as subscriptions FROM user_channel;"

# Посмотреть подписки
sqlite3 telegram.db "SELECT * FROM user_channel LIMIT 10;"
```

## 📝 Изменения в коде

### 1. Модели (`models.py`)

#### Новая промежуточная таблица:
```python
user_channel = Table(
    'user_channel',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True),
    Column('channel_id', Integer, ForeignKey('channels.id'), primary_key=True),
    Column('is_active', Boolean, default=True),
    Column('created_at', DateTime),
    Column('last_parsed_at', DateTime)
)
```

#### Обновленные отношения:
```python
# User
channels = relationship(
    "Channel",
    secondary=user_channel,
    back_populates="users"
)

# Channel
users = relationship(
    "User",
    secondary=user_channel,
    back_populates="channels"
)
```

#### Новые вспомогательные методы:

**Channel:**
- `get_or_create(db, channel_username, ...)` - получить или создать канал
- `add_user(db, user, is_active)` - добавить пользователя к каналу
- `remove_user(db, user)` - удалить пользователя из канала
- `get_user_subscription(db, user)` - получить информацию о подписке
- `update_user_subscription(db, user, ...)` - обновить подписку

**User:**
- `get_active_channels(db)` - получить активные каналы
- `get_all_channels(db)` - получить все каналы с информацией о подписке

### 2. Использование новых методов

#### Добавление канала (bot.py):
```python
# Было:
new_channel = Channel(
    user_id=db_user.id,
    channel_username=channel_username
)
db.add(new_channel)

# Стало:
channel = Channel.get_or_create(db, channel_username)
channel.add_user(db, db_user, is_active=True)
```

#### Получение каналов пользователя:
```python
# Было:
channels = db.query(Channel).filter(
    Channel.user_id == user.id,
    Channel.is_active == True
).all()

# Стало:
channels = user.get_active_channels(db)
```

#### Удаление канала:
```python
# Было:
db.delete(channel)

# Стало:
channel.remove_user(db, user)
# Канал автоматически удаляется, если больше нет подписчиков
if not channel.users:
    db.delete(channel)
```

### 3. Парсинг постов (parser_service.py)

```python
# Теперь parse_channel_posts принимает user
async def parse_channel_posts(self, channel: Channel, user, client, db):
    # Получаем подписку пользователя
    subscription = channel.get_user_subscription(db, user)
    last_parsed = subscription['last_parsed_at']
    
    # ... парсинг ...
    
    # Обновляем время парсинга для пользователя
    channel.update_user_subscription(db, user, last_parsed_at=datetime.now(timezone.utc))
```

## 🧪 Тестирование

### Тест 1: Добавление канала двумя пользователями
```python
# Пользователь 1 добавляет канал
user1 = db.query(User).filter(User.telegram_id == 123).first()
channel = Channel.get_or_create(db, "durov")
channel.add_user(db, user1)

# Пользователь 2 добавляет тот же канал
user2 = db.query(User).filter(User.telegram_id == 456).first()
channel = Channel.get_or_create(db, "durov")  # Вернет существующий
channel.add_user(db, user2)

# Проверка: в channels только одна запись для @durov
assert db.query(Channel).filter(Channel.channel_username == "durov").count() == 1

# Проверка: в user_channel две записи
assert len(channel.users) == 2
```

### Тест 2: Удаление подписки
```python
# Пользователь 1 удаляет канал
channel.remove_user(db, user1)

# Канал остается, т.к. есть другие подписчики
assert db.query(Channel).filter(Channel.id == channel.id).first() is not None

# Пользователь 2 удаляет канал
channel.remove_user(db, user2)

# Теперь можно удалить канал, т.к. нет подписчиков
if not channel.users:
    db.delete(channel)

# Канал удален
assert db.query(Channel).filter(Channel.id == channel.id).first() is None
```

## 📊 Совместимость

### API Endpoints

Все существующие API endpoints остаются совместимыми:

#### `GET /users/{telegram_id}/channels`
```json
{
  "channels": [
    {
      "id": 1,
      "channel_username": "durov",
      "is_active": true,
      "created_at": "2024-01-01T00:00:00",
      "subscription_created_at": "2024-01-01T00:00:00",  // новое поле
      "last_parsed_at": "2024-01-01T12:00:00"
    }
  ]
}
```

#### `GET /users/{telegram_id}/posts`
Без изменений - работает как раньше.

### Telegram Bot

Все команды бота работают без изменений:
- `/add_channel @username` - добавить канал
- `/my_channels` - список каналов
- Кнопки удаления каналов

## 🔍 Откат миграции

Если нужно откатиться:

```bash
# Остановить сервис
pkill -f "python.*main.py"
pkill -f "python.*bot.py"

# Восстановить из бэкапа (SQLite)
cd /home/ilyasni/n8n-server/n8n-installer/telethon
cp telegram.db.backup_YYYYMMDD_HHMMSS telegram.db

# Откатить код
git revert <commit-hash>

# Запустить сервис
python3 main.py &
python3 bot.py &
```

## ⚠️ Важные замечания

1. **Миграция необратима** (без отката из бэкапа)
2. **Проверьте бэкап** перед миграцией
3. **Остановите все сервисы** перед миграцией
4. **Посты не удаляются** - все данные сохраняются
5. **Дублирующиеся подписки** объединяются автоматически

## 🚀 Запуск после миграции

```bash
# 1. Запустить миграцию
python3 migrate_to_many_to_many.py

# 2. Проверить результаты
# Смотреть логи скрипта на наличие ошибок

# 3. Запустить сервисы
python3 main.py &
python3 bot.py &

# 4. Проверить работу
# Попробовать добавить/удалить канал через бота
# Проверить API endpoints
```

## 📞 Поддержка

При проблемах проверьте:
1. Логи миграции
2. Существование резервной копии
3. Права доступа к файлам БД
4. Целостность данных после миграции

## 📈 Статистика после миграции

Скрипт миграции выведет:
```
✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО
📊 Итоговая статистика:
  - Уникальных каналов: 50
  - Подписок пользователей: 120
  - Устранено дубликатов: 70
```

Это означает, что было 120 записей в старой таблице `channels`, а после миграции осталось только 50 уникальных каналов и 120 связей в таблице `user_channel`.

