# 🚀 Voice Commands - Quick Start

**Время настройки:** 10 минут  
**Уровень:** Средний

---

## ✅ Checklist

- [ ] Premium или Enterprise подписка
- [ ] SaluteSpeech credentials из Studio
- [ ] Redis запущен
- [ ] Обновлен .env
- [ ] Выполнена миграция БД
- [ ] Перезапущен Docker

---

## 🎯 Шаг 1: Получить Credentials (5 минут)

### 1.1 Регистрация в Studio

1. Перейдите в [Sber Studio](https://developers.sber.ru/studio)
2. Войдите через Сбер ID
3. Создайте новый проект "Telegram Bot Voice"

### 1.2 Получить Client ID и Secret

1. В проекте выберите **SaluteSpeech API**
2. Скопируйте:
   - **Client ID:** `0199deda-86df-7467-b2be-7f3d6d12541b`
   - **Client Secret:** `d944b976-a759-4fc8-8297-13258aa37a82`
   - **Scope:** `SALUTE_SPEECH_PERS`

3. Сохраните credentials в безопасном месте

---

## 🔧 Шаг 2: Настроить Environment (2 минуты)

### 2.1 Обновить telethon/.env

```bash
# Добавьте в конец файла:

############################################################
# SaluteSpeech API Configuration
############################################################

SALUTESPEECH_CLIENT_ID=0199deda-86df-7467-b2be-7f3d6d12541b
SALUTESPEECH_CLIENT_SECRET=d944b976-a759-4fc8-8297-13258aa37a82
SALUTESPEECH_SCOPE=SALUTE_SPEECH_PERS
SALUTESPEECH_URL=https://smartspeech.sber.ru/rest/v1

VOICE_TRANSCRIPTION_ENABLED=true
VOICE_MAX_DURATION_SEC=60
VOICE_CACHE_TTL=86400
```

### 2.2 Проверить Redis

```bash
# Redis должен быть запущен (без пароля)
docker ps | grep redis

# Проверить доступность
docker exec redis redis-cli PING
# Должен вернуть: PONG
```

---

## 📊 Шаг 3: Database Migration (1 минута)

```bash
# Запустить миграцию
python telethon/scripts/migrations/add_voice_transcription_support.py

# Должен вывести:
# ✅ Миграция успешно завершена!
# Добавлены поля:
#   • users.voice_queries_today
#   • users.voice_queries_reset_at
```

---

## 🐳 Шаг 4: Перезапуск Docker (2 минуты)

```bash
# Скопировать обновленные файлы
docker cp telethon/voice_transcription_service.py telethon:/app/
docker cp telethon/bot.py telethon:/app/
docker cp telethon/subscription_config.py telethon:/app/
docker cp telethon/models.py telethon:/app/
docker cp telethon/.env telethon:/app/

# Перезапустить
docker restart telethon telethon-bot

# Проверить логи
docker logs telethon --tail 50 | grep -E "(Voice|SaluteSpeech|✅|ERROR)"
```

**Ожидаемый вывод:**
```
✅ SaluteSpeechClient инициализирован
   Base URL: https://smartspeech.sber.ru/rest/v1
   Max duration: 60s
   Cache TTL: 86400s
✅ VoiceTranscriptionService инициализирован
✅ Handler голосовых сообщений зарегистрирован
```

---

## 🧪 Шаг 5: Тестирование (5 минут)

### Test 1: Premium user + voice

```
1. Отправьте /subscription
   → Проверьте что subscription = premium или enterprise

2. Отправьте /ask

3. Отправьте голосовое (10s): "Что нового в AI?"

4. Ожидайте:
   • "🎤 Обрабатываю..."
   • "✅ Распознано: Что нового в AI?"
   • "💡 Ответ: ..."
```

### Test 2: Free user (должен получить ошибку)

```
1. Отправьте голосовое

2. Ожидайте ошибку:
   "🎤 Голосовые команды доступны только для Premium/Enterprise"
```

### Test 3: Cache (повторное голосовое)

```
1. Отправьте то же голосовое еще раз

2. Ожидайте:
   • Instant response (< 1s)
   • "✅ Транскрипция из кеша"
```

### Test 4: Duration limit

```
1. Отправьте голосовое 61+ секунд

2. Ожидайте ошибку:
   "❌ Максимальная длительность: 60 секунд"
```

---

## ✅ Готово!

Если все тесты прошли успешно:

✅ SaluteSpeech API подключен  
✅ Голосовые команды работают  
✅ Кеш работает  
✅ Лимиты проверяются  
✅ Subscription controls работают

**Используйте:**
- `/ask` + голосовое для RAG поиска
- `/search` + голосовое для гибридного поиска

---

## 🐛 Troubleshooting

### "SaluteSpeech credentials обязательны"

```bash
# Проверьте что credentials установлены
grep SALUTESPEECH telethon/.env

# Если пусто:
nano telethon/.env
# Добавьте credentials из Studio
```

### "Ошибка получения access token"

```bash
# Проверьте credentials
echo -n "CLIENT_ID:CLIENT_SECRET" | base64

# Должно совпадать с Authorization Key из Studio

# Проверьте доступность OAuth API
curl https://ngw.devices.sberbank.ru:9443/api/v2/oauth
```

### "Voice transcription disabled"

```bash
# Проверьте настройки
docker exec telethon printenv | grep VOICE

# Убедитесь что:
# VOICE_TRANSCRIPTION_ENABLED=true
```

### "Redis недоступен"

```bash
# Проверьте Redis
docker ps | grep redis

# Запустите если не запущен
docker-compose up -d redis

# Проверьте подключение
docker exec redis redis-cli PING
```

---

## 📞 Support

**Если что-то не работает:**

1. Проверьте логи:
   ```bash
   docker logs telethon | grep -i "voice\|error"
   ```

2. Проверьте credentials в Studio

3. Создайте issue с логами

---

**Готово!** Голосовые команды работают! 🎤🚀

