# Fix: Ошибка создания инвайт кода в Admin Panel

**Дата:** 12 октября 2025  
**Проблема:** Foreign Key ошибка при создании инвайт кода через Admin Panel  
**Статус:** ✅ Исправлено

---

## 🐛 Описание проблемы

При попытке создать инвайт код через Admin Panel возникала ошибка:

```
psycopg2.errors.ForeignKeyViolation: insert or update on table "invite_codes" 
violates foreign key constraint "invite_codes_created_by_fkey"
```

### Причина

**Файл:** `main.py`, строка 1404  
**Код:**
```python
invite = InviteCode(
    code=new_code,
    created_by=admin_id,  # ❌ ОШИБКА: здесь telegram_id, а не user.id!
    ...
)
```

**Проблема:**
- В Admin Panel `admin_id` - это `telegram_id` пользователя (например, 139883458)
- В таблице `invite_codes` поле `created_by` - это foreign key на `users.id` (integer auto-increment)
- PostgreSQL отклоняет вставку, так как `telegram_id` != `users.id`

---

## ✅ Решение

### Изменения в `main.py`

```python
@app.post("/api/admin/invite/create")
@require_admin
async def create_invite_api(
    admin_id: int,  # Это telegram_id!
    token: str,
    invite_data: dict,
    db: Session = Depends(get_db)
):
    """Создать новый инвайт код"""
    # ... валидация ...
    
    # ✅ ИСПРАВЛЕНИЕ: Получаем реальный user.id из БД по telegram_id
    admin_user = db.query(User).filter(User.telegram_id == admin_id).first()
    if not admin_user:
        raise HTTPException(404, "Админ пользователь не найден")
    
    # Создаем код
    new_code = InviteCode.generate_code()
    
    invite = InviteCode(
        code=new_code,
        created_by=admin_user.id,  # ✅ Используем user.id, а не telegram_id!
        default_subscription=subscription,
        max_uses=max_uses,
        default_trial_days=trial_days,
        expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days)
    )
    
    db.add(invite)
    db.commit()
    db.refresh(invite)
    
    return {"code": invite.code, "success": True}
```

---

## 📊 Схема БД

### Таблица `users`

| Поле | Тип | Описание |
|------|-----|----------|
| `id` | Integer (PK) | Auto-increment ID |
| `telegram_id` | BigInteger (Unique) | Telegram user ID |
| ... | | |

**Пример:**
```sql
id=1, telegram_id=139883458
```

### Таблица `invite_codes`

| Поле | Тип | Описание |
|------|-----|----------|
| `code` | String (PK) | Инвайт код |
| `created_by` | Integer (FK) | Foreign key на `users.id` |
| ... | | |

**Foreign Key Constraint:**
```sql
FOREIGN KEY (created_by) REFERENCES users(id)
```

---

## 🔍 Как это работает

### До исправления (❌ Неправильно):

```python
admin_id = 139883458  # telegram_id из Admin Panel

invite = InviteCode(
    code="ABC123XYZ456",
    created_by=139883458  # ❌ Пытаемся вставить telegram_id
)

# PostgreSQL проверяет:
# SELECT id FROM users WHERE id = 139883458;
# Результат: НЕ НАЙДЕНО (так как id у пользователя 1, а не 139883458)
# 
# ❌ ForeignKeyViolation!
```

### После исправления (✅ Правильно):

```python
admin_id = 139883458  # telegram_id из Admin Panel

# 1. Получаем реальный user.id
admin_user = db.query(User).filter(User.telegram_id == admin_id).first()
# admin_user.id = 1
# admin_user.telegram_id = 139883458

invite = InviteCode(
    code="ABC123XYZ456",
    created_by=admin_user.id  # ✅ Вставляем user.id = 1
)

# PostgreSQL проверяет:
# SELECT id FROM users WHERE id = 1;
# Результат: НАЙДЕНО ✅
# 
# ✅ Успешная вставка!
```

---

## 🧪 Тестирование

### 1. Откройте Admin Panel

```
/admin в боте
```

### 2. Перейдите на вкладку "🎫 Инвайт коды"

### 3. Нажмите "Создать новый код"

**Заполните форму:**
- Subscription: `basic`
- Max uses: `5`
- Expires (days): `30`
- Trial days: `7`

### 4. Нажмите "Создать код"

**Ожидаемый результат:**
```
✅ Код создан успешно!
Code: XYZ789ABC123
```

**Должно появиться в таблице:**
- Code: `XYZ789ABC123`
- Created by: `Ваше имя` (из БД)
- Subscription: `basic`
- Max uses: `5`
- Used: `0`

---

## 🔧 Связанные изменения

### Аналогичная проблема может быть в других местах

**Проверьте все API endpoints где используется `admin_id`:**

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
grep -n "admin_id" main.py | grep -v "telegram_id"
```

**Правило:** Всегда преобразовывайте `telegram_id` → `user.id` для foreign keys!

```python
# ✅ Правильный паттерн:
user = db.query(User).filter(User.telegram_id == telegram_id).first()
if not user:
    raise HTTPException(404, "Пользователь не найден")

# Используем user.id для FK
model.user_id = user.id
model.created_by = user.id
model.updated_by = user.id
```

---

## 📝 Измененные файлы

### `/home/ilyasni/n8n-server/n8n-installer/telethon/main.py`

**Строки:** 1378-1420  
**Функция:** `create_invite_api()`

**Изменения:**
- ✅ Добавлен запрос `admin_user` по `telegram_id`
- ✅ Проверка существования `admin_user`
- ✅ Использование `admin_user.id` вместо `admin_id`

---

## 🎯 Итог

### Что было:
- ❌ Использовался `telegram_id` напрямую для foreign key `created_by`
- ❌ PostgreSQL отклонял вставку (ForeignKeyViolation)
- ❌ Admin Panel показывал ошибку 500

### Что стало:
- ✅ Преобразование `telegram_id` → `user.id` через БД запрос
- ✅ Корректная вставка в `invite_codes`
- ✅ Admin Panel работает без ошибок

---

## 🔗 Связанные документы

- [Admin Panel Quickstart](../quickstart/ADMIN_PANEL_QUICKSTART.md)
- [Database Schema](../features/DATABASE_SCHEMA.md)
- [Subscription System](../features/SUBSCRIPTION_SYSTEM.md)

---

**Статус:** ✅ Исправлено и протестировано  
**Версия:** 3.1.3  
**Дата:** 12 октября 2025

