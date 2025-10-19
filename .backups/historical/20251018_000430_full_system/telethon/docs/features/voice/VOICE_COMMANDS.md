# 🎤 Голосовые команды - Voice Commands

**Версия:** 3.3.0  
**Дата:** 13 октября 2025  
**Статус:** ✅ Реализовано  
**Доступ:** Premium/Enterprise only

---

## 🎯 Обзор

Голосовые команды позволяют использовать `/ask` и `/search` через голосовые сообщения.

**Как работает:**
```
Голосовое сообщение (OGG, до 60s)
    ↓
SaluteSpeech API (распознавание речи)
    ↓
Транскрибация в текст
    ↓
Выполнение /ask или /search с распознанным текстом
    ↓
Текстовый ответ от бота
```

**Технологии:**
- [SaluteSpeech API](https://developers.sber.ru/docs/ru/salutespeech/overview) - распознавание речи от Sber
- Redis - кеширование транскрипций (24 часа)
- OAuth2 - автоматическое обновление токенов

---

## ✨ Возможности

### 1. /ask через голосовое

**Сценарий:**
```
User: /ask
Bot: 💡 Использование: /ask <вопрос>
     🎤 Premium: Отправьте голосовое сообщение!

User: [голосовое: "Что писали про нейросети?"]
Bot: 🎤 Обрабатываю голосовое (5s)...
     ⏳ Это может занять 5-10 секунд

Bot: ✅ Распознано: "Что писали про нейросети?"
     🔍 Выполняю /ask...

Bot: 💡 Ответ: На этой неделе обсуждали...
     📚 Источники: [AI News] (95%)
```

### 2. /search через голосовое

**Сценарий:**
```
User: /search
Bot: 🔍 Использование: /search <запрос>
     🎤 Premium: Отправьте голосовое сообщение!

User: [голосовое: "Квантовые компьютеры"]
Bot: 🎤 Обрабатываю...

Bot: ✅ Распознано: "Квантовые компьютеры"
     🔍 Выполняю /search...

Bot: 🔍 Результаты:
     📱 Ваши посты (3)
     🌐 Интернет (5)
```

### 3. Два способа использования

**📌 Способ 1: Команда → Голосовое (рекомендуется)**
```
User: /ask              # Выбираем команду
User: [голосовое]       # Отправляем запрос
Bot: Автоматически выполняет /ask

User: /search           # Выбираем другую команду
User: [голосовое]       # Отправляем запрос
Bot: Автоматически выполняет /search
```

**📌 Способ 2: Голосовое → Выбор кнопки**
```
User: [голосовое без команды]
Bot: ✅ Распознано: "Ваш текст"
     🤔 Выберите команду:
     [💡 /ask - RAG поиск]
     [🔍 /search - Гибридный поиск]

User: [нажимает нужную кнопку]
Bot: Выполняет выбранную команду
```

---

## 💎 Подписки и лимиты

### Free Tier
- ❌ Голосовые команды **НЕ доступны**
- Используйте текстовые команды

### Trial (7 дней)
- ✅ Голосовые команды **доступны**
- Лимит: **20 запросов в день**
- Максимум: 60 секунд на голосовое

### Basic
- ❌ Голосовые команды **НЕ доступны**
- Обновитесь до Premium

### Premium
- ✅ Голосовые команды **доступны**
- Лимит: **50 запросов в день**
- Максимум: 60 секунд на голосовое

### Enterprise
- ✅ Голосовые команды **доступны**
- Лимит: **999 запросов в день**
- Максимум: 60 секунд на голосовое

---

## 📋 Как использовать

### Вариант 1: После команды (рекомендуется)

```
1. Отправьте /ask или /search
2. Сразу отправьте голосовое сообщение
3. Бот автоматически выполнит команду
```

### Вариант 2: Без команды

```
1. Отправьте голосовое сообщение
2. Бот распознает текст и покажет кнопки
3. Нажмите /ask или /search
4. Бот выполнит выбранную команду
```

### Вариант 3: Текстовая команда (если голосовые недоступны)

```
/ask Что писали про нейросети?
/search квантовые компьютеры
```

---

## ⚙️ Технические детали

### Формат голосовых

- **Формат:** OGG/Opus (стандарт Telegram)
- **Sample Rate:** 48000 Hz
- **Максимальная длительность:** 60 секунд
- **Максимальный размер:** ~1 МБ (60 секунд)

### SaluteSpeech API Flow

```
1. Upload Audio
   POST /data:upload
   → request_file_id

2. Start Recognition
   POST /speech:async_recognize
   Body: {options, request_file_id}
   → task_id

3. Poll Status (каждую секунду)
   GET /task:get?id={task_id}
   → status: NEW → PROCESSING → DONE

4. Download Result
   GET /data:download?response_file_id={response_file_id}
   → transcription text
```

### Кеширование

```python
# Redis cache (24 часа TTL)
Key: voice_transcription:{md5_hash}
Value: "распознанный текст"
TTL: 86400 секунд (24 часа)

# Повторное голосовое → instant response из кеша
```

### OAuth2 Token

```python
# Access token обновляется автоматически
Token lifetime: 30 минут
Refresh: за 1 минуту до истечения
Cache: в памяти VoiceTranscriptionService
```

---

## 🚨 Ограничения

### 1. Длительность

```
❌ Голосовое 61 секунда
→ "Максимальная длительность: 60 секунд"

✅ Голосовое 30 секунд
→ Успешная транскрибация
```

### 2. Подписка

```
❌ Free tier пользователь
→ "Голосовые команды доступны только для Premium"

✅ Premium пользователь
→ Транскрибация и выполнение команды
```

### 3. Дневной лимит

```
Premium: 50 запросов/день

❌ 51-й запрос
→ "Достигнут дневной лимит: 50"

✅ На следующий день счетчик сбрасывается
```

### 4. Качество записи

**Для лучшего распознавания:**
- ✅ Говорите четко и медленно
- ✅ Записывайте в тихом месте
- ✅ Избегайте фонового шума
- ✅ Держите микрофон близко

**Проблемы:**
- ❌ Шумная обстановка → плохое распознавание
- ❌ Быстрая речь → пропущенные слова
- ❌ Акцент → возможные ошибки

---

## 🐛 Troubleshooting

### "Сервис транскрибации временно недоступен"

**Причины:**
- SaluteSpeech API недоступен
- Неверные credentials
- Истек OAuth2 token

**Решение:**
```bash
# 1. Проверьте credentials в .env
grep SALUTESPEECH telethon/.env

# 2. Проверьте логи
docker logs telethon | grep -i "salutespeech\|voice"

# 3. Проверьте доступность API
curl https://smartspeech.sber.ru/rest/v1/

# 4. Перезапустите контейнер
docker restart telethon
```

### "Не удалось распознать речь"

**Причины:**
- Плохое качество записи
- Фоновый шум
- Слишком тихо
- Не русский язык

**Решение:**
- Перезапишите в тихом месте
- Говорите четче
- Проверьте что говорите на русском
- Используйте текстовую команду

### "Timeout транскрибации"

**Причины:**
- SaluteSpeech API перегружен
- Сетевые проблемы

**Решение:**
```bash
# Увеличьте timeout в .env
VOICE_MAX_DURATION_SEC=120  # Было 60

# Перезапустите
docker restart telethon
```

### "Достигнут дневной лимит"

**Решение:**
- Подождите до следующего дня (счетчик сбросится в 00:00 UTC)
- Или обновите подписку до Enterprise (999 запросов/день)

---

## 📊 Примеры использования

### Пример 1: Quick Question

```
User: /ask
User: [голосовое 5s: "Что нового в AI?"]

Bot: 🎤 Обрабатываю... (5s)
Bot: ✅ Распознано: "Что нового в AI?"
     🔍 Выполняю /ask...
Bot: 💡 Ответ: На этой неделе вышла новая модель...
```

### Пример 2: Complex Query

```
User: /search
User: [голосовое 30s: "Я хочу найти информацию про квантовые компьютеры и их применение в криптографии"]

Bot: 🎤 Обрабатываю... (30s)
Bot: ✅ Распознано: "Я хочу найти информацию про квантовые компьютеры и их применение в криптографии"
     🔍 Выполняю /search...
Bot: 🔍 Результаты:
     📱 Ваши посты (5)
     🌐 Интернет (10)
```

### Пример 3: Choose Command

```
User: [голосовое без команды: "Блокчейн технологии"]

Bot: ✅ Распознано: "Блокчейн технологии"
     🤔 Выберите команду:
     [💡 /ask] [🔍 /search]

User: [нажимает /ask]
Bot: 🔍 Выполняю /ask...
Bot: 💡 Ответ: Блокчейн - это...
```

---

## ⚡ Best Practices

### Для пользователей

1. **Отправляйте голосовое сразу после команды**
   - `/ask` → [голосовое]
   - Бот автоматически поймет что делать

2. **Говорите четко и медленно**
   - Лучше распознавание
   - Меньше ошибок

3. **Записывайте в тихом месте**
   - Без фонового шума
   - Четкий звук

4. **Используйте короткие запросы**
   - 10-30 секунд оптимально
   - Быстрее обработка

5. **Проверяйте транскрипцию**
   - Бот покажет что распознал
   - Если неправильно - перезапишите

### Для разработчиков

1. **Кеширование обязательно**
   - Повторное голосовое → instant
   - Экономия API calls
   - TTL 24 часа

2. **Graceful degradation**
   - Если SaluteSpeech недоступен → текстовые команды
   - Если timeout → сообщение пользователю

3. **Subscription checks**
   - Premium/Enterprise only
   - Проверка лимитов
   - Информативные сообщения об ошибках

4. **Async everywhere**
   - `async def transcribe()`
   - `await client.post()`
   - Non-blocking polling

---

## 📝 Configuration

### Environment Variables

```bash
# SaluteSpeech API
SALUTESPEECH_CLIENT_ID=your_client_id
SALUTESPEECH_CLIENT_SECRET=your_secret
SALUTESPEECH_SCOPE=SALUTE_SPEECH_PERS
SALUTESPEECH_URL=https://smartspeech.sber.ru/rest/v1

# Voice settings
VOICE_TRANSCRIPTION_ENABLED=true
VOICE_MAX_DURATION_SEC=60
VOICE_CACHE_TTL=86400  # 24h
```

### Subscription Tiers

```python
# subscription_config.py

"premium": {
    "voice_transcription_enabled": True,
    "voice_queries_per_day": 50
}

"enterprise": {
    "voice_transcription_enabled": True,
    "voice_queries_per_day": 999
}
```

### Database Migration

```bash
# Запустить миграцию
python telethon/scripts/migrations/add_voice_transcription_support.py

# Добавляет поля:
# - users.voice_queries_today
# - users.voice_queries_reset_at
```

---

## ✅ Verification

### 1. Проверка credentials

```bash
# Проверить что credentials установлены
docker exec telethon printenv | grep SALUTESPEECH

# Должно показать:
# SALUTESPEECH_CLIENT_ID=...
# SALUTESPEECH_CLIENT_SECRET=...
```

### 2. Проверка доступности API

```bash
# Тест OAuth2 token
curl -X POST https://ngw.devices.sberbank.ru:9443/api/v2/oauth \
  -H "Authorization: Basic BASE64_CREDENTIALS" \
  -d "scope=SALUTE_SPEECH_PERS"

# Должен вернуть access_token
```

### 3. Проверка Redis cache

```bash
# Проверить кеш транскрипций
docker exec redis redis-cli KEYS "voice_transcription:*"

# Должно показать закешированные транскрипции
```

### 4. Тестирование в боте

```
1. Отправьте /ask
2. Отправьте голосовое 10s: "Что нового?"
3. Проверьте транскрипцию
4. Проверьте RAG ответ
```

---

## 🔐 Безопасность

### Credentials Storage

```bash
# ✅ Правильно - в .env (не в коде!)
SALUTESPEECH_CLIENT_SECRET=d944b976-...

# ❌ Неправильно
client_secret = "d944b976-..."  # NO! Hardcoded!
```

### OAuth2 Token Refresh

```python
# ✅ Автоматическое обновление
if token_expires_at < now:
    token = await get_access_token()

# Token cache в памяти (не в Redis!)
# Причина: короткий TTL (30 мин), высокая частота использования
```

### Audio Data

```python
# ✅ Голосовые НЕ сохраняются
# Только транскрипция кешируется в Redis

# ❌ НЕ сохраняйте аудио файлы
# Причина: приватность, размер, GDPR
```

---

## 💰 Стоимость

### SaluteSpeech API

**Цены (ориентировочные):**
- Проверьте актуальные тарифы в [Studio](https://developers.sber.ru/studio)
- Обычно: аналогично Google Speech-to-Text

**Оценка (примерная):**
- 1 минута аудио ≈ стоимость генерации ~100 токенов GigaChat
- 100 голосовых по 30s/день ≈ 50 минут/день

### Альтернативы

**Если SaluteSpeech дорого:**

1. **OpenAI Whisper API**
   - $0.006 за минуту
   - 100 голосовых по 30s = $3/месяц

2. **Whisper Local** (бесплатно)
   - Установить локально
   - Медленнее (30-60s на CPU)
   - Нужна реализация

---

## 📚 Ссылки

**SaluteSpeech:**
- [Официальная документация](https://developers.sber.ru/docs/ru/salutespeech/overview)
- [API Reference](https://developers.sber.ru/docs/ru/salutespeech/api)
- [Studio (credentials)](https://developers.sber.ru/studio)
- [Postman Collection](https://www.postman.com/salute-developers-7605/public/documentation/luv5vaf/salutespeech-api)

**Код:**
- `telethon/voice_transcription_service.py` - SaluteSpeech клиент
- `telethon/bot.py` - Обработчик голосовых
- `telethon/subscription_config.py` - Лимиты
- `telethon/models.py` - Voice statistics

**Миграция:**
- `telethon/scripts/migrations/add_voice_transcription_support.py`

---

## 🆘 Support

**Проблемы:**
- Создайте issue в GitHub
- Опишите ошибку и приложите логи

**Логи:**
```bash
# Логи транскрибации
docker logs telethon | grep -i "voice\|salutespeech"

# Логи Redis cache
docker exec redis redis-cli KEYS "voice_*"
```

---

**Version:** 3.3.0  
**Last Updated:** 13 октября 2025  
**Maintainer:** Telegram Bot Team

