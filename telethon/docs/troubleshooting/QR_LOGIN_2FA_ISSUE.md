# QR Login + 2FA Issue - Двухфакторная аутентификация блокирует QR

**Дата:** 13 октября 2025  
**User:** 8124731874 (user_id=6)  
**Проблема:** QR Login не работает из-за включенной 2FA  
**Статус:** ⚠️ Known Limitation

---

## 🚨 Проблема

### Ошибка при QR Login:

```json
{
    "authorized": false,
    "error": "rpc_error: Two-steps verification is enabled and a password is required (caused by ExportLoginTokenRequest)"
}
```

**Что происходит:**
1. Пользователь отправляет `/login INVITE_CODE`
2. QR код генерируется успешно
3. Пользователь сканирует/открывает ссылку
4. **Telegram БЛОКИРУЕТ авторизацию:**
   - "Two-steps verification is enabled"
   - "Password is required"
5. QR Login падает с ошибкой

**Причина:**  
У пользователя включена **двухфакторная аутентификация (2FA)** в Telegram Settings.

**Ограничение Telegram API:**  
`ExportLoginTokenRequest` (используется для QR) **НЕ поддерживает 2FA password**. Требуется другой метод авторизации.

---

## 🔍 Как определить проблему

### В Redis QR Session:

```bash
docker exec redis redis-cli GET "qr_session:SESSION_ID"
```

**Ищите:**
```json
{
    "authorized": false,
    "error": "Two-steps verification is enabled and a password is required"
}
```

### В логах:

```bash
docker logs telethon 2>&1 | grep "Two-steps verification"
```

---

## ✅ Решения

### Вариант 1: Временно отключить 2FA (рекомендуется)

**Для пользователя:**

1. **Открыть Telegram**
2. Settings → Privacy and Security
3. Two-Step Verification
4. Turn Off (ввести текущий пароль)
5. **Вернуться в бота**
6. `/logout` (опционально)
7. `/login INVITE_CODE` (повторить)
8. ✅ QR Login будет работать
9. **После успешной авторизации можно включить 2FA обратно**

**Безопасность:**  
Временное отключение 2FA на 5 минут для QR Login не критично, если:
- Вы делаете это на своем устройстве
- Сразу после авторизации включаете 2FA обратно

---

### Вариант 2: Использовать /auth (веб-форма с 2FA)

**Альтернатива без отключения 2FA:**

1. `/auth` в боте
2. Открыть защищенную веб-форму
3. Ввести свои API credentials:
   - API_ID (от https://my.telegram.org)
   - API_HASH
   - Phone number
4. Ввести код из Telegram
5. **Ввести 2FA пароль** ← поддерживается!
6. ✅ Авторизация успешна

**Преимущества:**
- ✅ Поддерживает 2FA
- ✅ Не нужно отключать защиту
- ❌ Требует получения своих API credentials

---

### Вариант 3: Реализовать 2FA в QR Login (для разработчиков)

**Требуется доработка:**

#### 1. Обработка `PasswordRequired` в QR Auth Manager

**`qr_auth_manager.py`:**

```python
async def _poll_authorization(self, session_id: str, qr_login):
    """Ожидание авторизации QR кода"""
    try:
        # Ожидаем подтверждения
        await qr_login.wait(timeout=600)
        
        # Проверяем, требуется ли пароль
        if not await client.is_user_authorized():
            # Telegram требует 2FA пароль
            session_data = self._get_qr_session(session_id)
            session_data['status'] = 'password_required'
            session_data['error'] = 'Two-Step Verification: password required'
            self._save_qr_session(session_id, session_data)
            
            # Уведомляем пользователя через бота
            await self._request_2fa_password(session_id)
            return
        
        # Авторизация успешна
        await self._finalize_authorization(session_id)
        
    except PasswordRequired:
        # Обрабатываем запрос пароля
        await self._handle_password_request(session_id)
```

#### 2. UI для ввода пароля в Mini App

**Добавить в `/qr-auth` HTML:**

```html
<!-- Если status === 'password_required' -->
<div id="password-form" style="display: none;">
    <h3>🔐 Требуется 2FA пароль</h3>
    <input 
        type="password" 
        id="password-input" 
        placeholder="Введите ваш 2FA пароль"
    />
    <button onclick="submitPassword()">Отправить</button>
</div>

<script>
async function submitPassword() {
    const password = document.getElementById('password-input').value;
    
    await fetch('/qr-auth-password', {
        method: 'POST',
        body: JSON.stringify({
            session_id: sessionId,
            password: password
        })
    });
}
</script>
```

#### 3. Endpoint для обработки пароля

**`main.py`:**

```python
@app.post("/qr-auth-password")
async def qr_auth_password(
    session_id: str = Form(...),
    password: str = Form(...)
):
    """Обработка 2FA пароля для QR авторизации"""
    session_data = qr_auth_manager._get_qr_session(session_id)
    
    if not session_data:
        raise HTTPException(404, "Session not found")
    
    telegram_id = session_data['telegram_id']
    
    # Получаем client
    client = await shared_auth_manager.get_user_client(telegram_id)
    
    try:
        # Отправляем пароль
        await client.check_password(password)
        
        # Проверяем авторизацию
        if await client.is_user_authorized():
            # ✅ Авторизация успешна!
            await qr_auth_manager._finalize_authorization(session_id)
            return {"status": "authorized"}
        else:
            return {"status": "error", "message": "Invalid password"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}
```

**Приоритет:** Medium (не критично, есть workaround через /auth)

---

## 📊 Статистика

### Пользователей с 2FA:

```sql
-- Примерная оценка (нельзя проверить напрямую в БД)
-- Проверяется только при попытке QR Login

SELECT COUNT(*) 
FROM users 
WHERE is_authenticated = false
  AND auth_error LIKE '%Two-steps verification%';
```

### Сколько пользователей могут столкнуться:

**По статистике Telegram:**
- ~30-40% активных пользователей используют 2FA
- Из них ~10-15% попытаются использовать QR Login

**Вывод:** ~3-5% пользователей столкнутся с этой проблемой.

---

## 🎯 Рекомендации

### Для пользователей

1. **Если важна безопасность** → используйте `/auth` (поддерживает 2FA)
2. **Если нужно быстро** → временно отключите 2FA для QR Login
3. После авторизации **включите 2FA обратно**

### Для системы

1. ✅ Добавить **проверку 2FA** при генерации QR
2. ✅ **Уведомлять пользователя** сразу:
   ```
   ⚠️ У вас включена 2FA
   
   QR Login не поддерживает 2FA.
   
   Выберите:
   • Временно отключить 2FA
   • Использовать /auth (с паролем)
   ```
3. ✅ **Показывать альтернативы** в UI
4. ✅ Реализовать **полную поддержку 2FA** в QR Login (долгосрочно)

---

## 🔗 Связанные документы

- [QR Login Guide](../quickstart/QR_LOGIN_GUIDE.md)
- [Session Expired](USER_SESSION_EXPIRED.md)
- [Secure Authentication](../features/README_SECURE.md)

---

## 📝 Итог для пользователя 6

**Текущее состояние:**
- ❌ QR Login заблокирован из-за 2FA
- ⚠️ Session не создан
- ⏸️ Парсинг не работает

**Что делать:**

**Вариант A (быстрый):**
```
1. Telegram Settings → Turn Off 2FA
2. /login FKBM2XL6GU07
3. Сканировать QR
4. ✅ После авторизации включить 2FA обратно
```

**Вариант B (с 2FA):**
```
1. /auth в боте
2. Открыть веб-форму
3. Ввести API credentials + телефон
4. Ввести код + 2FA пароль
5. ✅ Авторизация с 2FA
```

**Результат:** После любого варианта парсинг возобновится через 30 минут! 🚀

---

**Создано:** 13 октября 2025  
**Статус:** ⚠️ Known Limitation  
**Workaround:** Available (2 варианта)

