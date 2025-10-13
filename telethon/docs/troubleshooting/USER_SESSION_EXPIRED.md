# Session Expired - Пользователь не авторизован

**Дата:** 13 октября 2025  
**User ID:** 6 (telegram_id=8124731874)  
**Проблема:** Parser не может получить посты из-за невалидной сессии  
**Статус:** ⚠️ Требуется повторная авторизация

---

## 🐛 Симптомы

```
ERROR:parser_service:❌ ParserService: Ошибка парсинга каналов пользователя 8124731874: Пользователь не авторизован
```

**При этом:**
- ✅ В БД: `is_authenticated = true`
- ✅ Session файл существует: `user_8124731874.session` (28KB)
- ✅ Каналов: 15 активных
- ✅ Постов в БД: 101 (с 10.10 по 12.10)

---

## 🔍 Диагностика

### Проверка в БД

```sql
SELECT 
    id, 
    telegram_id, 
    is_authenticated, 
    last_auth_check,
    auth_error
FROM users 
WHERE telegram_id = 8124731874;

-- Результат:
--  id | telegram_id | is_authenticated | last_auth_check     | auth_error
-- ----|-------------|------------------|---------------------|-----------
--   6 | 8124731874  | t                | 2025-10-06 11:22:37 | NULL
```

### История постов

```sql
SELECT 
    COUNT(*) as total,
    MIN(posted_at) as first_post,
    MAX(posted_at) as last_post
FROM posts 
WHERE user_id = 6;

-- Результат:
--  total | first_post          | last_post
-- -------|---------------------|---------------------
--    101 | 2025-10-10 13:01:38 | 2025-10-12 10:35:30
```

### Timeline

```
06.10.2025 11:22:37 - Последняя проверка авторизации ✅
        ↓
10-12.10.2025 - Парсинг работал (101 пост добавлен) ✅
        ↓
12.10.2025 10:35:30 - Последний успешный пост ✅
        ↓
[GAP - что-то произошло]
        ↓
13.10.2025 01:30+ - Parser: "Пользователь не авторизован" ❌
```

---

## 🚨 Корневая причина

### Код проверки авторизации

**`shared_auth_manager.py:487-488`**
```python
# Проверяем авторизацию
if not await client.is_user_authorized():
    raise ValueError("Пользователь не авторизован")
```

**Что происходит:**
1. Parser создает Telethon client с мастер credentials
2. Client подключается к Telegram API
3. Telegram проверяет валидность session файла
4. **Telegram возвращает:** `is_user_authorized() = False`
5. Parser выбрасывает исключение

**Несоответствие:**
- БД говорит: `is_authenticated = true`
- Telegram API говорит: `is_user_authorized() = False`

---

## 💡 Возможные причины

### 1. Session Expired (наиболее вероятно)

**Что произошло:**
- Session файл был валиден до 12.10.2025 10:35:30
- После этого истек срок действия (TTL session)
- Telegram требует повторной авторизации

**Telegram Session TTL:**
- По умолчанию: **до 1 года** для активных сессий
- Для неактивных: **3-6 месяцев**
- Может быть сброшен при подозрительной активности

### 2. Session Revoked

**Что произошло:**
- Пользователь зашел в Telegram Settings → Privacy → Active Sessions
- Отозвал доступ для этой сессии
- Session файл стал невалидным

### 3. Logout на другом устройстве

**Что произошло:**
- Пользователь нажал "Log out" на мобильном/десктопном клиенте
- Все sessions этого аккаунта стали невалидными
- Требуется повторная авторизация

### 4. IP Change / Security Check

**Что произошло:**
- Сменился IP адрес сервера
- Telegram заблокировал сессию из-за подозрительной активности
- Требуется подтверждение через код или QR

---

## ✅ Решение

### Вариант 1: Повторная QR авторизация (рекомендуется)

**Через Telegram бота:**

1. Пользователь отправляет `/logout` в бота (опционально)
2. Пользователь отправляет `/login INVITE_CODE`
3. Бот отправляет кнопку с QR авторизацией
4. Пользователь сканирует QR или использует deep link
5. Подтверждает в Telegram
6. ✅ Новая сессия создана

**Команды бота:**
```
/logout           # Очистить старую сессию (опционально)
/login ABC123XYZ  # Начать QR авторизацию
```

### Вариант 2: Админ сброс авторизации

**Если пользователь не может самостоятельно:**

```bash
# Через debug команды (только для админов)
# В Telegram боте:
/debug_reset_auth 8124731874

# Или напрямую:
docker exec telethon python -c "
from database import SessionLocal
from models import User
from shared_auth_manager import shared_auth_manager
import asyncio

async def reset_user():
    db = SessionLocal()
    user = db.query(User).filter(User.telegram_id == 8124731874).first()
    user.is_authenticated = False
    user.auth_error = 'Session expired - требуется повторная авторизация'
    db.commit()
    
    # Удаляем клиент из памяти
    await shared_auth_manager.disconnect_client(8124731874)
    print('✅ Авторизация сброшена')
    db.close()

asyncio.run(reset_user())
"
```

**Затем пользователь должен снова пройти `/login`**

### Вариант 3: Удаление session файла

**Крайняя мера (удаляет всю историю сессии):**

```bash
# Остановить контейнер
docker stop telethon

# Удалить session файл
rm /home/ilyasni/n8n-server/n8n-installer/telethon/sessions/user_8124731874.session

# Сбросить флаг в БД
docker exec supabase-db psql -U postgres -d postgres -c \
  "UPDATE users SET is_authenticated = false, auth_error = 'Session file removed' WHERE telegram_id = 8124731874;"

# Запустить контейнер
docker start telethon
```

**Затем пользователь проходит `/login` заново**

---

## 🔧 Автоматическая проверка сессий

### Добавить периодическую валидацию

**Идея:** Проверять `is_user_authorized()` раз в сутки и обновлять `is_authenticated` в БД

**Реализация в `parser_service.py`:**

```python
async def validate_user_sessions(self):
    """Проверка валидности сессий всех пользователей"""
    db = SessionLocal()
    try:
        users = db.query(User).filter(User.is_authenticated == True).all()
        
        for user in users:
            try:
                client = await shared_auth_manager.get_user_client(user.telegram_id)
                
                if client and client.is_connected():
                    # Session валиден
                    user.last_auth_check = datetime.now(timezone.utc)
                    user.auth_error = None
                else:
                    # Session невалиден
                    user.is_authenticated = False
                    user.auth_error = "Session expired or revoked"
                    logger.warning(f"⚠️ Session для пользователя {user.telegram_id} стал невалидным")
                
            except Exception as e:
                user.is_authenticated = False
                user.auth_error = f"Validation error: {str(e)}"
                logger.error(f"❌ Ошибка валидации сессии {user.telegram_id}: {e}")
        
        db.commit()
        
    finally:
        db.close()

def schedule_session_validation(self):
    """Планировщик проверки сессий (раз в сутки)"""
    schedule.every().day.at("04:00").do(
        lambda: asyncio.run(self.validate_user_sessions())
    )
    logger.info("📅 Валидация сессий запланирована ежедневно в 04:00")
```

**Добавить в `run_system.py`:**
```python
# В методе initialize()
self.parser_service.schedule_session_validation()
```

---

## 📊 Мониторинг

### Команды для проверки

**Найти пользователей с устаревшими сессиями:**
```sql
SELECT 
    telegram_id,
    is_authenticated,
    last_auth_check,
    AGE(NOW(), last_auth_check) as days_since_check
FROM users
WHERE is_authenticated = true
  AND last_auth_check < NOW() - INTERVAL '7 days'
ORDER BY last_auth_check ASC;
```

**Найти пользователей с ошибками авторизации:**
```sql
SELECT 
    telegram_id,
    is_authenticated,
    auth_error,
    last_auth_check
FROM users
WHERE auth_error IS NOT NULL
ORDER BY last_auth_check DESC;
```

---

## 🎯 Рекомендации

### Для пользователей

1. **Не выходите из аккаунта** на других устройствах без необходимости
2. **Не отзывайте сессии** в Telegram Settings → Active Sessions
3. При проблемах с парсингом → `/logout` + `/login` для перелогина

### Для системы

1. ✅ Добавить **автоматическую валидацию** сессий (раз в сутки)
2. ✅ Обновлять `is_authenticated` на основе реальной проверки
3. ✅ **Уведомлять пользователя** через бота при невалидной сессии:
   ```
   ⚠️ Ваша сессия устарела. Для продолжения парсинга используйте /login
   ```
4. ✅ Логировать историю проверок сессий для анализа

---

## 📝 Итог для пользователя 6

**Текущее состояние:**
- ❌ Session невалиден (Telegram API: `is_user_authorized() = False`)
- ✅ В БД ошибочно `is_authenticated = true`
- ⏸️ Парсинг остановлен с 12.10.2025

**Что нужно сделать:**

**Пользователь должен:**
```
1. Открыть Telegram бота
2. Отправить: /login INVITE_CODE
3. Нажать кнопку QR авторизации
4. Отсканировать или использовать ссылку
5. Подтвердить в Telegram
```

**Через 30 минут** парсинг автоматически возобновится!

---

**Создано:** 13 октября 2025  
**Статус:** ⚠️ Требуется действие пользователя  
**Приоритет:** High (парсинг остановлен)

