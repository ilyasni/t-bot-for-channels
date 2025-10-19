# Система подписок и инвайт-кодов

## 📋 Обзор

Система подписок и инвайт-кодов обеспечивает:
- Контролируемую регистрацию новых пользователей
- Монетизацию через тарифные планы
- Ограничение ресурсов по уровню подписки
- Аудит изменений подписок

## 🏗️ Архитектура

### Таблицы БД

#### 1. Users - расширенная таблица

**Новые поля для подписок:**

```python
role = Column(String, default="user")  # admin, user
subscription_type = Column(String, default="free")  # free, trial, basic, premium, enterprise
subscription_expires = Column(DateTime, nullable=True)
subscription_started_at = Column(DateTime, nullable=True)
max_channels = Column(Integer, default=3)
invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)
```

**Методы:**

```python
user.check_subscription_active() -> bool  # Проверка активности подписки
user.is_admin() -> bool                    # Проверка роли администратора
user.can_add_channel() -> bool             # Проверка лимита каналов
```

#### 2. InviteCode - инвайт коды

```python
class InviteCode(Base):
    code = Column(String, primary_key=True)  # INVITE2024ABC
    created_by = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime)
    
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    used_at = Column(DateTime, nullable=True)
    
    expires_at = Column(DateTime)
    max_uses = Column(Integer, default=1)
    uses_count = Column(Integer, default=0)
    
    default_subscription = Column(String, default="free")
    default_trial_days = Column(Integer, default=0)
```

**Методы:**

```python
InviteCode.generate_code() -> str  # Генерация случайного кода
invite.is_valid() -> bool          # Проверка валидности
invite.use(user_id) -> bool        # Использование кода
```

#### 3. SubscriptionHistory - история изменений

```python
class SubscriptionHistory(Base):
    user_id = Column(Integer, ForeignKey("users.id"))
    action = Column(String)  # created, upgraded, downgraded, renewed, expired, revoked
    old_type = Column(String, nullable=True)
    new_type = Column(String)
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    changed_at = Column(DateTime)
    notes = Column(Text, nullable=True)
```

## 💎 Тарифные планы

### Конфигурация (subscription_config.py)

```python
SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free",
        "max_channels": 3,
        "max_posts_per_day": 100,
        "rag_queries_per_day": 10,
        "ai_digest": False,
        "priority_parsing": False,
        "price_rub": 0
    },
    "trial": {
        "name": "Trial (7 дней)",
        "max_channels": 10,
        "max_posts_per_day": 500,
        "rag_queries_per_day": 50,
        "ai_digest": True,
        "priority_parsing": True,
        "duration_days": 7
    },
    # ... basic, premium, enterprise
}
```

### Сравнение тарифов

| Тариф | Каналы | Посты/день | RAG/день | AI-дайджесты | Цена |
|-------|--------|------------|----------|--------------|------|
| **Free** | 3 | 100 | 10 | ❌ | Бесплатно |
| **Trial** | 10 | 500 | 50 | ✅ | Бесплатно (7 дн) |
| **Basic** | 10 | 500 | 50 | ✅ | 500₽/мес |
| **Premium** | 50 | 2000 | 200 | ✅ | 1500₽/мес |
| **Enterprise** | 999 | 99999 | 999 | ✅ | 5000₽/мес |

## 🎫 Работа с инвайт кодами

### Создание кода (администратор)

```bash
# Интерактивное меню
/admin_invite

# Процесс:
1. Выбрать тип подписки: Trial, Basic, Premium, Enterprise, Free
2. Выбрать срок действия кода: 1 день, 7 дней, 30 дней, без срока
3. Получить код: TRIAL7ABC123
```

**Программно:**

```python
from models import InviteCode
from datetime import datetime, timedelta, timezone

db = SessionLocal()

# Генерация кода
code = InviteCode.generate_code()  # XYZABC123456

# Создание инвайта
invite = InviteCode(
    code=code,
    created_by=admin_user.id,
    created_at=datetime.now(timezone.utc),
    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
    max_uses=1,
    default_subscription="trial",
    default_trial_days=7
)

db.add(invite)
db.commit()
```

### Использование кода (пользователь)

```bash
/login TRIAL7ABC123
```

**Процесс:**
1. Проверка валидности кода
2. Авторизация пользователя (номер + SMS)
3. Автоматическая активация подписки
4. Маркировка кода как использованного

## 👥 Роли пользователей

### Admin (Администратор)

**Возможности:**
- Создание инвайт кодов (`/admin_invite`)
- Просмотр списка пользователей (`/admin_users`)
- Просмотр информации о пользователе (`/admin_user`)
- Выдача/изменение подписок (`/admin_grant`)
- Просмотр статистики (`/admin_stats`)

**Назначение:**

Автоматически при миграции (первый ID из `ADMIN_TELEGRAM_IDS`):

```bash
python scripts/migrations/add_roles_and_subscriptions.py
```

Вручную в БД:

```sql
UPDATE users SET role = 'admin' WHERE telegram_id = 123456789;
```

### User (Обычный пользователь)

**Возможности:**
- Авторизация через инвайт код
- Добавление каналов (в пределах лимита)
- Использование функций согласно подписке
- Просмотр своей подписки (`/subscription`)

## 🔐 Процесс регистрации

### Вариант 1: Invite-only (рекомендуется)

`.env`:
```env
REGISTRATION_MODE=invite
```

**Процесс:**
1. Админ создает инвайт через `/admin_invite`
2. Админ отправляет код пользователю
3. Пользователь использует `/login INVITE_CODE`
4. Автоматическая активация подписки

### Вариант 2: Open (открытая)

`.env`:
```env
REGISTRATION_MODE=open
DEFAULT_SUBSCRIPTION=free
```

**Процесс:**
1. Любой пользователь может использовать `/login` без кода
2. Автоматически получает подписку `free`

## 📊 Проверка лимитов

### В коде бота

Перед каждой операцией проверяется лимит:

```python
async def add_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = get_user(update.effective_user.id)
    
    # Проверка лимита каналов
    if not db_user.can_add_channel():
        tier = get_subscription_info(db_user.subscription_type)
        await update.message.reply_text(
            f"❌ Достигнут лимит каналов: {db_user.max_channels}\n"
            f"Текущая подписка: {tier['name']}\n"
            f"Для увеличения обратитесь к администратору"
        )
        return
    
    # Продолжаем добавление канала...
```

### Автоматическая проверка истечения

При каждом запросе:

```python
if user.subscription_expires and user.subscription_expires < datetime.now(timezone.utc):
    # Downgrade до free
    user.subscription_type = "free"
    user.max_channels = 3
    db.commit()
```

## 👑 Админ команды

### /admin_invite - Создание инвайт кода

**Интерактивное меню:**

1. Выбор типа подписки
2. Выбор срока действия кода
3. Получение кода

**Результат:**

```
✅ Инвайт код создан!

🎫 Код: TRIAL7ABC123

📊 Параметры:
• Подписка: Trial (7 дней)
• Действует до: 19.10.2025 18:00
• Использований: 0/1

💡 Отправьте этот код пользователю:
/login TRIAL7ABC123
```

### /admin_users [filter] - Список пользователей

**Фильтры:**
- `all` - все пользователи (по умолчанию)
- `active` - только авторизованные
- `expired` - с истекшей подпиской
- `free`, `premium` - по типу подписки

**Пример:**

```bash
/admin_users premium

# Результат:
👥 Пользователи (premium)

👤 ✅ Иван Иванов (@ivan)
   ID: 123456789
   Подписка: premium
   До истечения: 25 дн.

👤 ✅ Петр Петров (@petr)
   ID: 987654321
   Подписка: premium
   До истечения: 10 дн.
```

### /admin_user <telegram_id> - Информация о пользователе

**Показывает:**
- Основные данные (имя, username, дата регистрации)
- Подписка и статус
- Использование ресурсов (каналы, посты)
- Статус авторизации
- Кто пригласил
- История изменений подписок

**Пример:**

```bash
/admin_user 123456789

# Результат:
👤 Пользователь: Иван Иванов
🆔 Telegram ID: 123456789
👤 Username: @ivan
📅 Регистрация: 01.10.2025

📊 Подписка: Premium
📍 Статус: ✅ Активна
⏰ До: 01.11.2025

📈 Использование:
• Каналов: 15/50
• Постов: 1234

🔐 Статус:
• Авторизован: ✅
• Роль: user
• Приглашен: Admin (987654321)

📜 История подписок:
• upgraded: free → premium (15.10.2025)
• created: free (01.10.2025)
```

### /admin_grant <telegram_id> <subscription> [days] - Выдать подписку

**Использование:**

```bash
# Trial на 7 дней
/admin_grant 123456789 trial 7

# Premium на месяц
/admin_grant 123456789 premium 30

# Enterprise на год
/admin_grant 123456789 enterprise 365
```

**Что происходит:**
1. Обновляется `subscription_type`
2. Устанавливается `subscription_expires`
3. Обновляются лимиты (`max_channels`)
4. Записывается в `subscription_history`
5. Уведомление пользователя (TODO: добавить)

### /admin_stats - Статистика

**Показывает:**
- Всего пользователей
- Авторизовано
- Распределение по подпискам
- Активные подписки
- Использовано инвайтов

**Пример:**

```
📊 Статистика бота

👥 Пользователи:
• Всего: 42
• Авторизовано: 35

💎 Подписки:
• Free: 20
• Trial (7 дней): 5
• Basic: 8
• Premium: 7
• Enterprise: 2

✅ Активных подписок: 22

🎫 Инвайт коды:
• Всего создано: 50
• Использовано: 42
```

## 🔄 Lifecycle подписки

### 1. Создание (через инвайт)

```
Админ: /admin_invite
  → Создает код TRIAL7ABC123 (trial, 7 дней)
  
User: /login TRIAL7ABC123
  → Активируется trial подписка на 7 дней
  → subscription_type = "trial"
  → subscription_expires = now + 7 days
  → max_channels = 10
```

### 2. Активная подписка

```
User: /add_channel @channel
  → Проверка: can_add_channel() ✅
  → Канал добавлен
```

### 3. Истечение подписки

```
Автоматическая проверка при каждом запросе:

if subscription_expires < now():
    subscription_type = "free"
    max_channels = 3
    # Если каналов > 3, они становятся неактивными
```

### 4. Upgrade подписки

```
Админ: /admin_grant 123456789 premium 30

История:
- action: "upgraded"
- old_type: "trial"
- new_type: "premium"
- changed_by: admin_id
- notes: "Granted by admin for 30 days"
```

## 🛡️ Безопасность

### Изоляция данных

**Каждый пользователь видит только свои данные:**

```python
# ✅ Правильно
posts = db.query(Post).filter(Post.user_id == current_user.id).all()

# ❌ Неправильно
posts = db.query(Post).all()  # Вернет данные ВСЕХ!
```

### Валидация лимитов

**На стороне бота:**

```python
if len(user.channels) >= user.max_channels:
    raise LimitExceededError("Channel limit reached")
```

**На стороне API:**

```python
@app.post("/channels")
async def add_channel(channel_id: int, user_id: int):
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user.can_add_channel():
        raise HTTPException(403, "Channel limit exceeded")
    
    # ...
```

### Аудит изменений

Все изменения подписок логируются:

```python
history = SubscriptionHistory(
    user_id=user.id,
    action="upgraded",
    old_type="free",
    new_type="premium",
    changed_by=admin.id,
    notes="Monthly payment"
)
db.add(history)
```

## 📈 Мониторинг

### Метрики подписок

```python
# Активные подписки
active = db.query(User).filter(
    User.subscription_expires > datetime.now(timezone.utc),
    User.subscription_type != "free"
).count()

# Revenue forecast (месяц)
premium_count = db.query(User).filter(User.subscription_type == "premium").count()
basic_count = db.query(User).filter(User.subscription_type == "basic").count()

revenue = (premium_count * 1500) + (basic_count * 500)
```

### Уведомления об истечении

**TODO (будущая функциональность):**

```python
# За 3 дня до истечения
if days_until_expiry == 3:
    await bot.send_message(
        user.telegram_id,
        "⏰ Ваша подписка Premium истекает через 3 дня!\n\n"
        "Для продления обратитесь к администратору."
    )
```

## 🔧 Настройка

### Переменные окружения

```env
# Администраторы
ADMIN_TELEGRAM_IDS=123456789,987654321

# Режим регистрации
REGISTRATION_MODE=invite  # invite или open

# Дефолтные значения
DEFAULT_SUBSCRIPTION=free
DEFAULT_MAX_CHANNELS=3
TRIAL_DURATION_DAYS=7
```

### Изменение тарифов

Отредактируйте `subscription_config.py`:

```python
SUBSCRIPTION_TIERS = {
    "premium": {
        "max_channels": 100,  # Было 50
        "price_rub": 2000,    # Было 1500
        # ...
    }
}
```

**После изменения:**
1. Перезапустите бота
2. Новые подписки будут с новыми лимитами
3. Существующие подписки сохранят старые лимиты до renewal

## 🧪 Тестирование

### Создание тестового инвайта

```bash
# Как админ
/admin_invite
  → Trial (7 дней)
  → 1 день
  → Получить код TEST123ABC
```

### Тестовая регистрация

```bash
# Как обычный пользователь
/login TEST123ABC
  → +79991234567
  → 12345
  → ✅ Успешно
```

### Проверка лимитов

```bash
# Попробовать добавить 11 каналов с trial подпиской (лимит 10)
/add_channel @channel1
...
/add_channel @channel10  # ✅ OK
/add_channel @channel11  # ❌ Лимит
```

## 📚 API Endpoints

### GET /users/{user_id}/subscription

Получить информацию о подписке:

```json
{
  "subscription_type": "premium",
  "tier_name": "Premium",
  "is_active": true,
  "expires_at": "2025-11-01T00:00:00Z",
  "days_remaining": 25,
  "limits": {
    "max_channels": 50,
    "max_posts_per_day": 2000,
    "rag_queries_per_day": 200
  },
  "usage": {
    "channels_count": 15,
    "posts_today": 234
  }
}
```

### POST /admin/grant_subscription

Выдать подписку (только для админов):

```json
{
  "user_id": 123456789,
  "subscription_type": "premium",
  "duration_days": 30
}
```

## 🆘 Troubleshooting

### Проблема: Пользователь не может добавить канал

**Причина:** Достигнут лимит подписки

**Решение:**
1. Проверить подписку: `/subscription`
2. Проверить количество каналов: `/my_channels`
3. Обратиться к админу для upgrade

### Проблема: Подписка истекла

**Причина:** `subscription_expires < now()`

**Решение:**
1. Админ выдает новую подписку: `/admin_grant <id> premium 30`
2. Или пользователь оплачивает (будущая функциональность)

### Проблема: Инвайт код не работает

**Причина:** Истек срок или исчерпан лимит

**Решение:**
1. Админ проверяет код в БД
2. Создает новый код: `/admin_invite`

## 🔗 Связанные документы

- [Упрощенная авторизация](../quickstart/SIMPLE_LOGIN.md)
- [Админ быстрый старт](../../ADMIN_QUICKSTART.md)
- [Shared Credentials](SHARED_CREDENTIALS.md)
- [Безопасность](README_SECURE.md)

