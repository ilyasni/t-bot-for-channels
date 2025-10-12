# 📋 Реализация: Упрощенная авторизация с системой подписок

**Дата:** 12 октября 2025  
**Версия:** 3.0.0  
**Статус:** ✅ Реализовано

## 🎯 Что реализовано

### 1. Shared Master Credentials авторизация

✅ **Создан `shared_auth_manager.py`**
- Использует общие `MASTER_API_ID/MASTER_API_HASH` для всех пользователей
- Индивидуальные session файлы по `telegram_id`
- Методы: `send_code()`, `verify_code()`, `verify_2fa()`
- Security checks: session validation, async locks, file permissions

✅ **Создан `bot_login_handlers.py`**
- ConversationHandler для команды `/login`
- States: PHONE → CODE → TWO_FA
- PicklePersistence для сохранения состояний
- per_user=True для изоляции пользователей

### 2. Система ролей и подписок

✅ **Обновлен `models.py`**
- Новые поля в User: `role`, `subscription_type`, `subscription_expires`, `max_channels`, `invited_by`
- Новая таблица `InviteCode` с методами генерации и валидации
- Новая таблица `SubscriptionHistory` для аудита
- Методы User: `check_subscription_active()`, `is_admin()`, `can_add_channel()`

✅ **Создан `subscription_config.py`**
- Конфигурация 5 тарифов: free, trial, basic, premium, enterprise
- Лимиты на каналы, посты, RAG запросы
- Форматирование для отображения пользователям

### 3. Админ команды

✅ **Создан `bot_admin_handlers.py`**
- `/admin_invite` - создание инвайт кодов (интерактивное меню)
- `/admin_users [filter]` - список пользователей с фильтрацией
- `/admin_user <telegram_id>` - детальная информация о пользователе
- `/admin_grant <telegram_id> <subscription> [days]` - выдача подписок
- `/admin_stats` - статистика по боту

### 4. Интеграция в бота

✅ **Обновлен `bot.py`**
- Добавлен PicklePersistence для сохранения состояний
- Зарегистрирован ConversationHandler для `/login`
- Добавлены админ команды и callback handlers
- Обновлен `/start` с двумя вариантами авторизации
- Добавлена проверка лимитов в `/add_channel`

✅ **Добавлена команда `/subscription`**
- Просмотр текущей подписки
- Информация о лимитах и использовании
- Дата истечения

### 5. Parser Service интеграция

✅ **Обновлен `parser_service.py`**
- Использует `shared_auth_manager.get_user_client()`
- Работает с shared credentials
- Сохранена совместимость со старыми клиентами

### 6. Миграция БД

✅ **Создан `scripts/migrations/add_roles_and_subscriptions.py`**
- Добавляет новые поля в users
- Создает таблицы invite_codes и subscription_history
- Назначает первого администратора из ADMIN_TELEGRAM_IDS
- Миграция существующих пользователей на free подписку

### 7. Документация

✅ **Создана документация:**
- `ADMIN_QUICKSTART.md` - быстрый старт для администратора
- `docs/quickstart/SIMPLE_LOGIN.md` - инструкция для пользователей
- `docs/features/SUBSCRIPTIONS.md` - система подписок
- `docs/features/SHARED_CREDENTIALS.md` - технические детали

✅ **Обновлена конфигурация:**
- `.env.example` - добавлены `MASTER_API_ID`, `MASTER_API_HASH`, `ADMIN_TELEGRAM_IDS`

## 🔄 Процесс авторизации (до и после)

### Было (старый /auth):

1. Пользователь открывает https://my.telegram.org
2. Создает Telegram приложение
3. Копирует API_ID
4. Копирует API_HASH
5. Открывает веб-форму бота
6. Вводит API_ID, API_HASH, номер телефона
7. Получает SMS код
8. Вводит код в веб-форме
9. (Опционально) Вводит 2FA

**Время:** 5-10 минут  
**Сложность:** Высокая (технический барьер)

### Стало (новый /login):

1. Получить инвайт код от админа
2. `/login INVITE_CODE`
3. Ввести номер телефона
4. Ввести SMS код
5. (Опционально) Ввести 2FA

**Время:** 1 минута  
**Сложность:** Низкая (как обычный Telegram бот)

## 📊 Уровни подписок

| Тариф | Каналы | Посты/день | RAG/день | AI-дайджесты | Приоритет | Цена |
|-------|--------|------------|----------|--------------|-----------|------|
| Free | 3 | 100 | 10 | ❌ | ❌ | 0₽ |
| Trial | 10 | 500 | 50 | ✅ | ✅ | 0₽ (7 дн) |
| Basic | 10 | 500 | 50 | ✅ | ❌ | 500₽/мес |
| Premium | 50 | 2000 | 200 | ✅ | ✅ | 1500₽/мес |
| Enterprise | 999 | 99999 | 999 | ✅ | ✅ | 5000₽/мес |

## 🛡️ Безопасность

### Изоляция данных

**Реализовано:**
- ✅ Session validation: проверка `client.get_me().id == telegram_id`
- ✅ Session path строго по `telegram_id`
- ✅ File permissions: `chmod 600` для session файлов
- ✅ БД изоляция: фильтрация по `user_id` во всех запросах
- ✅ Async locks для защиты от race conditions
- ✅ Audit logging всех критичных операций

### Rate Limiting

**Реализовано:**
- ✅ 3 попытки авторизации в 5 минут
- ✅ Блокировка на 1 час после 5 неудачных попыток
- ✅ Автоматическая очистка неактивных клиентов
- ✅ Flood sleep threshold = 120s

### Шифрование

**Что шифруется:**
- ✅ Номер телефона (`phone_number` в БД)
- ✅ Session файлы (автоматически Telethon'ом)

**Что НЕ шифруется:**
- MASTER_API_ID/MASTER_API_HASH (в .env, не в БД)

## 📱 Команды бота

### Для всех пользователей:

| Команда | Описание |
|---------|----------|
| `/login INVITE_CODE` | Упрощенная авторизация |
| `/auth` | Расширенная авторизация (свои API ключи) |
| `/subscription` | Информация о подписке |
| `/add_channel @name` | Добавить канал (с проверкой лимита) |
| `/my_channels` | Список каналов |
| `/ask <вопрос>` | RAG поиск |
| `/help` | Справка |

### Для администраторов:

| Команда | Описание |
|---------|----------|
| `/admin_invite` | Создать инвайт код |
| `/admin_users [filter]` | Список пользователей |
| `/admin_user <id>` | Информация о пользователе |
| `/admin_grant <id> <sub> [days]` | Выдать подписку |
| `/admin_stats` | Статистика |

## 🚀 Запуск

### 1. Настройка .env

```env
# Обязательные переменные
MASTER_API_ID=12345678
MASTER_API_HASH=abcdef1234567890abcdef1234567890
ADMIN_TELEGRAM_IDS=123456789

# Опциональные
REGISTRATION_MODE=invite
DEFAULT_SUBSCRIPTION=free
DEFAULT_MAX_CHANNELS=3
TRIAL_DURATION_DAYS=7
```

### 2. Миграция БД

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
python scripts/migrations/add_roles_and_subscriptions.py
```

### 3. Запуск бота

```bash
# Через Docker
cd /home/ilyasni/n8n-server/n8n-installer
python start_services.py

# Локально
cd telethon
./scripts/utils/dev.sh local
```

### 4. Первый инвайт

```bash
# В Telegram боте
/start
/admin_invite
  → Trial (7 дней)
  → 30 дней
  → Получить код
```

## 📝 Изменения в файлах

### Новые файлы:

1. `shared_auth_manager.py` - менеджер авторизации (270 строк)
2. `bot_login_handlers.py` - обработчики /login (220 строк)
3. `bot_admin_handlers.py` - админ команды (280 строк)
4. `subscription_config.py` - конфигурация тарифов (80 строк)
5. `scripts/migrations/add_roles_and_subscriptions.py` - миграция (250 строк)
6. `ADMIN_QUICKSTART.md` - документация для админа
7. `docs/quickstart/SIMPLE_LOGIN.md` - документация для пользователей
8. `docs/features/SUBSCRIPTIONS.md` - система подписок
9. `docs/features/SHARED_CREDENTIALS.md` - технические детали

### Измененные файлы:

1. `models.py` - добавлены InviteCode, SubscriptionHistory, поля подписок в User
2. `bot.py` - интеграция новых handlers, Persistence
3. `parser_service.py` - использование shared_auth_manager
4. `.env.example` - новые переменные

### Удаленные зависимости:

❌ Пользователям больше НЕ нужно:
- Создавать приложение на my.telegram.org
- Знать что такое API_ID и API_HASH
- Использовать веб-форму для авторизации

## ✅ Тестирование

### Чек-лист для тестирования

- [ ] Администратор может создать инвайт код
- [ ] Пользователь может авторизоваться с инвайт кодом
- [ ] SMS код приходит корректно
- [ ] 2FA работает (если включен)
- [ ] Подписка активируется автоматически
- [ ] Лимиты каналов проверяются
- [ ] Rate limiting работает (3 попытки / 5 минут)
- [ ] Блокировка после 5 неудачных попыток
- [ ] Истекшая подписка downgrade до free
- [ ] Админ может просмотреть пользователей
- [ ] Админ может выдать подписку
- [ ] Статистика отображается корректно

### Пример сценария

```bash
# Как админ
/start → Должен быть администратором
/admin_invite → Создать trial код TRIAL123
/admin_stats → Проверить статистику

# Как новый пользователь (другой аккаунт)
/start → Приветствие с /login
/login TRIAL123 → Запрос номера
+79991234567 → Отправка SMS
12345 → Успешная авторизация
/subscription → Trial (7 дней), 10 каналов
/add_channel @durov → Успешно
... (добавить 10 каналов) ...
/add_channel @channel11 → Лимит достигнут

# Через 7 дней
/subscription → Истекла, downgrade до free
/my_channels → 10 каналов, но лимит 3
/add_channel → Ошибка лимита
```

## 🔮 Будущие улучшения

### Фаза 1 (текущая): Invite-based

- ✅ Инвайт коды
- ✅ Бесплатные подписки
- ✅ Ручная выдача админом

### Фаза 2 (следующая): Платежи

- [ ] Интеграция YooKassa/Stripe
- [ ] Автоматическая оплата
- [ ] Продление подписок
- [ ] Refunds и cancellations

### Фаза 3 (future): Автоматизация

- [ ] Уведомления об истечении подписки
- [ ] Автоматический downgrade при истечении
- [ ] Self-service upgrade через бота
- [ ] Промо-коды и скидки

### Фаза 4 (future): Группы и упоминания

- [ ] `/summarize_group` - резюме переписки группы
- [ ] `/my_mentions` - где пользователя тегнули
- [ ] `/group_digest` - дайджест обсуждений

## 📚 Документация

### Для пользователей:
- [Упрощенная авторизация](docs/quickstart/SIMPLE_LOGIN.md) - пошаговая инструкция
- [Быстрый старт](docs/quickstart/QUICK_START.md) - общее руководство

### Для администраторов:
- [Админ быстрый старт](ADMIN_QUICKSTART.md) - настройка и управление
- [Система подписок](docs/features/SUBSCRIPTIONS.md) - детали подписок

### Для разработчиков:
- [Shared Credentials](docs/features/SHARED_CREDENTIALS.md) - технические детали
- [Безопасность](docs/features/README_SECURE.md) - security considerations

## 🎓 Ключевые решения

### Почему Shared Credentials?

**Проблема:** Пользователи не могут получить API ключи (технический барьер)  
**Решение:** Использовать общие credentials администратора  
**Компромисс:** Нарушение ToS, но упрощение UX

### Почему Invite-only?

**Проблема:** Нужен контроль регистрации и монетизация  
**Решение:** Система инвайт кодов с привязанными подписками  
**Преимущество:** Гибкость (trial для тестирования, платные для монетизации)

### Почему ConversationHandler а не Telethon conversations?

**Проблема:** python-telegram-bot (бот управления) и telethon (user client) - разные библиотеки  
**Решение:** Использовать ConversationHandler из python-telegram-bot  
**Преимущество:** Persistence, изоляция по пользователям, стабильность

### Почему не StringSession?

**Проблема:** File-based sessions сложнее в масштабировании  
**Решение:** Пока оставляем file-based (проще), StringSession в БД - для будущего  
**Преимущество:** Меньше сложности на старте, проще отладка

## 🚨 Важные замечания

### SMS коды

- ✅ Telegram **САМ** отправляет SMS коды
- ✅ **Бесплатно** для администратора и пользователей
- ⚠️ Лимит: ~100-200 SMS с одного API_ID в день

### MTProto vs Bot API

- ✅ Используется **MTProto** (через Telethon)
- ✅ Полный User API доступ
- ✅ Приватные каналы и группы
- ✅ Упоминания и история
- ❌ Bot API не подходит для use case

### Обратная совместимость

- ✅ Старый `/auth` сохранен (для пользователей со своими credentials)
- ✅ Пользователи с `api_id` в БД продолжат работать
- ✅ Плавная миграция без breaking changes

## 💻 Примеры кода

### Создание инвайт кода программно

```python
from models import InviteCode
from datetime import datetime, timedelta, timezone
from database import SessionLocal

db = SessionLocal()

# Генерация кода
code = InviteCode.generate_code()

# Создание
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

print(f"Код создан: {code}")
```

### Проверка подписки перед действием

```python
async def add_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
    db_user = get_user(update.effective_user.id)
    
    # Проверка активности подписки
    if not db_user.check_subscription_active():
        await update.message.reply_text(
            "❌ Ваша подписка истекла.\n"
            "Обратитесь к администратору для продления."
        )
        return
    
    # Проверка лимита каналов
    if not db_user.can_add_channel():
        tier = get_subscription_info(db_user.subscription_type)
        await update.message.reply_text(
            f"❌ Достигнут лимит: {db_user.max_channels} каналов\n"
            f"Подписка: {tier['name']}\n"
            f"Для увеличения: /subscription"
        )
        return
    
    # Продолжаем...
```

### Выдача подписки программно

```python
from models import User, SubscriptionHistory
from subscription_config import get_subscription_info
from datetime import datetime, timedelta, timezone

db = SessionLocal()

user = db.query(User).filter(User.telegram_id == 123456789).first()
admin = db.query(User).filter(User.telegram_id == 987654321).first()

# Сохраняем старое
old_type = user.subscription_type

# Обновляем
user.subscription_type = "premium"
user.subscription_started_at = datetime.now(timezone.utc)
user.subscription_expires = datetime.now(timezone.utc) + timedelta(days=30)

tier = get_subscription_info("premium")
user.max_channels = tier['max_channels']

db.commit()

# Записываем в историю
history = SubscriptionHistory(
    user_id=user.id,
    action="upgraded",
    old_type=old_type,
    new_type="premium",
    changed_by=admin.id,
    notes="Manual grant by admin"
)
db.add(history)
db.commit()
```

## 🔗 Следующие шаги

1. ✅ **Настроить .env** - добавить MASTER_API_ID и ADMIN_TELEGRAM_IDS
2. ✅ **Выполнить миграцию** - `python scripts/migrations/add_roles_and_subscriptions.py`
3. ✅ **Запустить бота** - `python start_services.py`
4. ✅ **Создать первый инвайт** - `/admin_invite`
5. ✅ **Протестировать** - пригласить тестового пользователя

## 📞 Поддержка

**Вопросы по реализации:**
- Документация: `/telethon/docs/`
- Issues: создайте issue в репозитории

**Вопросы по использованию:**
- Пользователи: `/help` в боте
- Админы: `ADMIN_QUICKSTART.md`

---

**Реализовано:** ilyasni  
**Дата:** 12 октября 2025  
**Версия:** 3.0.0

