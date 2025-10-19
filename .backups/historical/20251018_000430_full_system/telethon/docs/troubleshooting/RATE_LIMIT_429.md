# 🚦 Решение проблемы Rate Limit 429 (OpenRouter)

## 📋 Описание проблемы

**Ошибка:**
```
ERROR: ❌ TaggingService: Ошибка API: 429 - {
  "error": {
    "message": "Rate limit exceeded: free-models-per-day. 
                Add 10 credits to unlock 1000 free model requests per day",
    "code": 429
  }
}
```

**Причина:**
- OpenRouter ограничивает бесплатные модели **50 запросами в день**
- Лимит исчерпан, система не может генерировать теги
- Лимит сбросится в **00:00 UTC следующего дня**

---

## ✅ Решения

### 🔴 Краткосрочное: Подождать сброса лимита

Лимит автоматически сбросится в **00:00 UTC** (03:00 по Москве).

**Проверить когда сбросится:**
```bash
# Посмотрите в логах последнюю ошибку 429:
docker logs telethon 2>&1 | grep "X-RateLimit-Reset"

# Система автоматически покажет:
# ⏰ TaggingService: Rate limit достигнут. Лимит сбросится 2025-10-12 00:00:00 UTC
```

**Временно отключить тегирование:**
```bash
# В корневом .env закомментируйте или очистите:
OPENROUTER_API_KEY=""

# Перезапустите:
docker compose -p localai restart telethon
```

---

### 🟡 Среднесрочное: Переключиться на GigaChat

GigaChat от Сбер предоставляет больший лимит запросов.

**Шаг 1: Получить GigaChat credentials**

1. Регистрация: https://developers.sber.ru/gigachat
2. Создать проект и получить API ключ
3. Добавить в корневой `.env`:
   ```env
   GIGACHAT_CREDENTIALS=your_credentials_here
   ```

**Шаг 2: Переключить провайдера**

В корневом `.env` или `telethon/.env`:
```env
# Было:
TAGGING_PROVIDER=openrouter

# Стало:
TAGGING_PROVIDER=gigachat
GIGACHAT_MODEL=GigaChat-Lite  # Рекомендуется для тегирования
```

**Доступные модели GigaChat:**
- `GigaChat-Lite` - быстрая, экономичная, **рекомендуется для тегирования**
- `GigaChat` - стандартная модель (дороже, медленнее)
- `GigaChat-Pro` - для сложных задач (еще дороже)

**Шаг 3: Перезапустить сервис**
```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker compose -p localai restart telethon gpt2giga-proxy
```

**Шаг 4: Проверить работу**
```bash
# Логи telethon должны показать:
docker logs telethon | tail -20

# Ожидаемый вывод:
# ✅ TaggingService: Инициализирован с GigaChat (через http://gpt2giga-proxy:8090)
# 💡 TaggingService: Используется модель GigaChat
```

---

### 🟢 Долгосрочное: Добавить credits в OpenRouter

**Если нужна высокая стабильность и лимиты:**

1. Добавить **$10 credits** в OpenRouter: https://openrouter.ai/credits
2. Это даст **1000 запросов/день** для бесплатных моделей
3. Доступ к платным моделям (GPT-4, Claude и др.)

---

## 🔧 Обновления в системе

### Автоматическая обработка 429

**Система теперь:**
- ✅ Автоматически определяет когда сбросится лимит
- ✅ Если ожидание < 5 минут - ждет и повторяет запрос
- ✅ Если ожидание долгое - пропускает пост (обработает позже)
- ✅ Показывает понятные предупреждения в логах

**Пример логов:**
```
⏰ TaggingService: Rate limit достигнут. Лимит сбросится 2025-10-12 00:00:00 UTC
💡 Рекомендация: переключитесь на GigaChat или добавьте $10 credits в OpenRouter
⏸️ TaggingService: Rate limit превышен. Пост будет обработан при следующей попытке.
```

### Поддержка нескольких провайдеров

**Новые переменные в `.env`:**
```env
# Выбор провайдера
TAGGING_PROVIDER=openrouter  # или gigachat

# OpenRouter (если TAGGING_PROVIDER=openrouter)
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# GigaChat (если TAGGING_PROVIDER=gigachat)
GIGACHAT_PROXY_URL=http://gpt2giga-proxy:8090
GIGACHAT_MODEL=GigaChat-Lite  # Рекомендуется: быстро, экономично
# Альтернативы: GigaChat, GigaChat-Pro
# GIGACHAT_CREDENTIALS - в корневом .env
```

---

## 📊 Сравнение провайдеров

| Параметр | OpenRouter (free) | GigaChat Lite | GigaChat | OpenRouter (paid) |
|----------|-------------------|---------------|----------|-------------------|
| **Лимит/день** | 50 запросов | ~10,000+ | ~5,000 | 1,000 |
| **Стоимость** | Бесплатно | Низкая 💰 | Средняя | $10 = 1000 req |
| **Регистрация** | Email | Номер телефона РФ | Номер телефона РФ | Email + карта |
| **Скорость** | Быстро | **Очень быстро** ⚡ | Средне | Быстро |
| **Качество тегов** | Отлично | **Хорошо** ✅ | Отлично | Отлично |
| **Стабильность** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Язык** | Русский ✅ | Русский ✅✅ | Русский ✅✅ | Русский ✅ |

**Рекомендация:**
- **Тестирование:** OpenRouter (free) - `google/gemini-2.0-flash-exp:free`
- **Малый трафик (<50 постов/день):** OpenRouter (free)
- **Средний трафик (50-500 постов/день):** **GigaChat Lite** ⭐ (оптимально!)
- **Высокий трафик (500+ постов/день):** GigaChat Lite или OpenRouter (paid)
- **Максимальное качество:** GigaChat или GigaChat Pro

---

## 🧪 Проверка и отладка

### Проверить текущий провайдер

```bash
# Посмотреть переменные окружения
docker exec telethon env | grep TAGGING_PROVIDER

# Посмотреть логи запуска
docker logs telethon | grep TaggingService
```

**Ожидаемый вывод (OpenRouter):**
```
✅ TaggingService: Инициализирован с OpenRouter
   Модель: google/gemini-2.0-flash-exp:free
⚠️ TaggingService: Бесплатные модели имеют лимит 50 запросов/день
💡 При достижении лимита рассмотрите: TAGGING_PROVIDER=gigachat
```

**Ожидаемый вывод (GigaChat Lite):**
```
✅ TaggingService: Инициализирован с GigaChat (через http://gpt2giga-proxy:8090)
💡 TaggingService: Используется модель GigaChat-Lite
⚡ GigaChat-Lite: быстрая модель с высокими лимитами - оптимально для тегирования
```

### Проверить статус rate limit

```bash
# Последние ошибки 429
docker logs telethon 2>&1 | grep "429"

# Проверить сколько постов ждут тегирования
curl "http://localhost:8010/users/YOUR_USER_ID/tagging_status"

# Вручную запустить retry (после сброса лимита)
curl -X POST "http://localhost:8010/users/YOUR_USER_ID/posts/retry_tagging"
```

### Тестирование GigaChat proxy

```bash
# Проверить что прокси запущен
docker ps | grep gpt2giga

# Проверить healthcheck
curl http://localhost:8090/health

# Тестовый запрос
curl -X POST http://localhost:8090/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "GigaChat",
    "messages": [{"role": "user", "content": "Привет!"}],
    "max_tokens": 50
  }'
```

---

## 🔄 Миграция постов с failed тегами

После переключения провайдера или сброса лимита, обработайте посты с ошибками:

```bash
# API запрос
curl -X POST "http://localhost:8010/users/YOUR_USER_ID/posts/retry_tagging?limit=100"

# Или через Python скрипт
cd /home/ilyasni/n8n-server/n8n-installer/telethon
docker exec -it telethon python -c "
import asyncio
from tagging_service import tagging_service
asyncio.run(tagging_service.retry_failed_posts(user_id=YOUR_USER_ID, limit=100))
"
```

---

## 📚 Дополнительные ресурсы

- [OpenRouter Rate Limits](https://openrouter.ai/docs#rate-limits)
- [GigaChat Documentation](https://developers.sber.ru/docs/ru/gigachat/api/overview)
- [Tagging Service README](../features/TAGGING_RETRY_SYSTEM.md)
- [RAG Service Configuration](../features/rag/RAG_CHECKLIST.md)

---

## 📝 Changelog

**2025-10-11:**
- ✅ Добавлена автоматическая обработка 429 с ожиданием сброса лимита
- ✅ Добавлена поддержка GigaChat как альтернативного провайдера
- ✅ Обновлена документация с инструкциями по переключению
- ✅ Добавлена переменная `TAGGING_PROVIDER` для выбора провайдера

---

**Автор:** Telegram Channel Parser Team  
**Версия:** 1.0  
**Дата:** 11 октября 2025

