# 🎯 Обновление: GigaChat Lite для тегирования

**Дата:** 11 октября 2025  
**Версия:** 2.2  
**Статус:** ✅ Реализовано

---

## 📋 Краткое описание

Система автоматического тегирования обновлена для **оптимального использования GigaChat Lite**:

- ✅ GigaChat Lite установлен как **модель по умолчанию** для GigaChat провайдера
- ✅ Добавлена **автоматическая обработка Rate Limit 429** от OpenRouter
- ✅ Поддержка **переключения между провайдерами** (OpenRouter ↔ GigaChat)
- ✅ Обновлена документация с рекомендациями по выбору модели

---

## 🎯 Проблема

**Ошибка 429 от OpenRouter:**
```
Rate limit exceeded: free-models-per-day
Лимит: 50 запросов/день (бесплатные модели)
```

**Решение:** Использовать **GigaChat Lite** - быстрая модель с лимитом ~10,000 запросов/день.

---

## ✨ Что изменилось

### 1. `tagging_service.py`

**Добавлено:**
- Поддержка выбора провайдера через `TAGGING_PROVIDER` (openrouter/gigachat)
- Автоматическое определение модели GigaChat Lite как оптимальной
- Обработка 429 ошибок с автоматическим ожиданием сброса лимита
- Информативные логи при использовании GigaChat Lite

**Ключевые изменения:**
```python
# Новые переменные
TAGGING_PROVIDER=gigachat
GIGACHAT_MODEL=GigaChat-Lite  # по умолчанию

# Автоматическая обработка 429
if response.status_code == 429:
    # Определяем когда сбросится лимит
    # Ждем если < 5 минут, иначе пропускаем
```

### 2. `.env.example`

**Обновлено:**
```env
# Выбор провайдера
TAGGING_PROVIDER=openrouter  # или gigachat

# GigaChat настройки
GIGACHAT_MODEL=GigaChat-Lite  # Рекомендуется для тегирования
# Доступные: GigaChat-Lite, GigaChat, GigaChat-Pro
```

### 3. `docker-compose.override.yml`

**Добавлены переменные:**
```yaml
environment:
  - TAGGING_PROVIDER=${TAGGING_PROVIDER:-openrouter}
  - GIGACHAT_MODEL=${GIGACHAT_MODEL:-GigaChat-Lite}
  - GIGACHAT_PROXY_URL=http://gpt2giga-proxy:8090
```

### 4. Документация

**Новые файлы:**
- `docs/troubleshooting/RATE_LIMIT_429.md` - полное руководство по решению 429
- `QUICK_FIX_RATE_LIMIT.md` - быстрое решение за 2 минуты
- `switch_to_gigachat_lite.sh` - автоматический скрипт переключения

**Обновлено:**
- Сравнительные таблицы провайдеров
- Рекомендации по выбору модели
- Инструкции по troubleshooting

---

## 🚀 Быстрый старт

### Вариант 1: Автоматический скрипт

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
./switch_to_gigachat_lite.sh
```

Скрипт автоматически:
1. Проверит наличие `GIGACHAT_CREDENTIALS`
2. Обновит `.env` файлы
3. Перезапустит сервисы
4. Покажет логи для проверки

### Вариант 2: Вручную

**Шаг 1:** Добавьте в корневой `.env` (если еще нет):
```bash
GIGACHAT_CREDENTIALS=your_credentials_here
```

**Шаг 2:** Обновите `telethon/.env`:
```bash
TAGGING_PROVIDER=gigachat
GIGACHAT_MODEL=GigaChat-Lite
```

**Шаг 3:** Перезапустите:
```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker compose -p localai restart telethon gpt2giga-proxy
```

**Шаг 4:** Проверьте логи:
```bash
docker logs telethon | grep TaggingService
```

Ожидаемый вывод:
```
✅ TaggingService: Инициализирован с GigaChat (через http://gpt2giga-proxy:8090)
💡 TaggingService: Используется модель GigaChat-Lite
⚡ GigaChat-Lite: быстрая модель с высокими лимитами - оптимально для тегирования
```

---

## 📊 Сравнение моделей для тегирования

| Модель | Скорость | Лимит/день | Стоимость | Качество | Рекомендация |
|--------|----------|------------|-----------|----------|--------------|
| OpenRouter Gemini (free) | Быстро | 50 | Бесплатно | ⭐⭐⭐⭐⭐ | Тестирование |
| **GigaChat Lite** | **Очень быстро** ⚡ | **~10,000** | **Низкая** | **⭐⭐⭐⭐** | **Продакшн** ⭐ |
| GigaChat | Средне | ~5,000 | Средняя | ⭐⭐⭐⭐⭐ | Высокое качество |
| GigaChat Pro | Медленно | ~2,000 | Высокая | ⭐⭐⭐⭐⭐ | Сложные задачи |
| OpenRouter GPT-4 (paid) | Быстро | 1,000 | $10=1000req | ⭐⭐⭐⭐⭐ | Премиум |

**Вывод:** GigaChat Lite - оптимальный баланс для автоматического тегирования!

---

## 🔧 Технические детали

### Автоматическая обработка Rate Limit

**Логика:**
1. При получении `429 Too Many Requests`
2. Система извлекает `X-RateLimit-Reset` из ответа API
3. Вычисляет время до сброса лимита
4. **Если < 5 минут:** ждет и повторяет запрос
5. **Если > 5 минут:** пропускает пост (обработает позже)
6. Показывает информативное сообщение с рекомендациями

**Пример лога:**
```
⏰ TaggingService: Rate limit достигнут. Лимит сбросится 2025-10-12 00:00:00 UTC
💡 Рекомендация: переключитесь на GigaChat или добавьте $10 credits в OpenRouter
⏸️ TaggingService: Rate limit превышен. Пост будет обработан при следующей попытке.
```

### Выбор модели при инициализации

**Приоритет:**
1. `TAGGING_PROVIDER` (openrouter или gigachat)
2. Если `gigachat` → `GIGACHAT_MODEL` (по умолчанию GigaChat-Lite)
3. Если `openrouter` → `OPENROUTER_MODEL` (по умолчанию google/gemini-2.0-flash-exp:free)

**Fallback модели** (только для OpenRouter):
- При ошибках переключается на резервные модели
- Порядок: Gemini → Llama → Qwen → Gemma

---

## 🧪 Тестирование

### Проверить текущую конфигурацию

```bash
# Провайдер
docker exec telethon env | grep TAGGING_PROVIDER

# Модель
docker exec telethon env | grep GIGACHAT_MODEL

# Логи инициализации
docker logs telethon | grep TaggingService | head -10
```

### Тестовая генерация тегов

```bash
# Через API
curl -X POST "http://localhost:8010/users/YOUR_USER_ID/posts/tag_without_tags?limit=5"

# Через Python
docker exec -it telethon python -c "
import asyncio
from tagging_service import tagging_service

async def test():
    text = 'Новости технологий: AI и машинное обучение'
    tags = await tagging_service.generate_tags_for_text(text)
    print(f'Теги: {tags}')

asyncio.run(test())
"
```

### Производительность

**Замеры:**
```bash
# Время генерации тегов для одного поста
time curl -X POST "http://localhost:8010/posts/420/generate_tags"

# Ожидается:
# OpenRouter Gemini: ~1-2 секунды
# GigaChat Lite: ~0.5-1 секунда
# GigaChat: ~2-3 секунды
```

---

## 📈 Миграция существующих постов

После переключения на GigaChat Lite, обработайте посты с ошибками тегирования:

### Через API

```bash
# Retry всех failed постов для пользователя
curl -X POST "http://localhost:8010/users/USER_ID/posts/retry_tagging?limit=100"

# Проверить статус тегирования
curl "http://localhost:8010/users/USER_ID/tagging_status"
```

### Через Python скрипт

```python
import asyncio
from tagging_service import tagging_service

async def migrate():
    # Retry для конкретного пользователя
    await tagging_service.retry_failed_posts(
        user_id=YOUR_USER_ID,
        limit=100,
        force=False  # True - игнорировать лимит попыток
    )

asyncio.run(migrate())
```

### Автоматически

Система **автоматически** повторит попытки при следующем парсинге каналов.

---

## 🎓 Рекомендации по выбору

### Когда использовать OpenRouter (free)

- ✅ Тестирование и разработка
- ✅ Малый трафик (<50 постов/день)
- ✅ Максимальное качество тегов критично
- ❌ Высокая нагрузка (упретесь в лимит)

### Когда использовать GigaChat Lite ⭐

- ✅ **Продакшн с средним трафиком** (50-500 постов/день)
- ✅ **Нужна скорость и высокие лимиты**
- ✅ Качество тегов достаточное (не нужно идеально)
- ✅ **Регистрация в РФ доступна**
- ✅ **Оптимальное соотношение цена/качество**

### Когда использовать GigaChat/Pro

- ✅ Максимальное качество тегов критично
- ✅ Бюджет позволяет
- ✅ Трафик умеренный
- ❌ Скорость не критична

### Когда использовать OpenRouter (paid)

- ✅ Нужны премиум модели (GPT-4, Claude)
- ✅ Международная аудитория
- ✅ Бюджет позволяет ($10+ в месяц)
- ✅ Высокая стабильность критична

---

## 🔄 Откат изменений

Если нужно вернуться на OpenRouter:

```bash
# В telethon/.env измените:
TAGGING_PROVIDER=openrouter
OPENROUTER_API_KEY=your_key_here
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free

# Перезапустите:
cd /home/ilyasni/n8n-server/n8n-installer
docker compose -p localai restart telethon
```

---

## 📚 Связанная документация

- [Rate Limit 429 - Полное руководство](docs/troubleshooting/RATE_LIMIT_429.md)
- [Быстрое решение за 2 минуты](QUICK_FIX_RATE_LIMIT.md)
- [Tagging Retry System](docs/features/TAGGING_RETRY_SYSTEM.md)
- [RAG Service Configuration](docs/quickstart/RAG_QUICKSTART.md)

---

## 📝 Changelog

### v2.2 - 2025-10-11

**Добавлено:**
- ✅ Поддержка GigaChat Lite как оптимальной модели для тегирования
- ✅ Автоматическая обработка 429 ошибок с ожиданием сброса лимита
- ✅ Переменная `TAGGING_PROVIDER` для выбора провайдера
- ✅ Переменная `GIGACHAT_MODEL` для выбора модели GigaChat
- ✅ Скрипт `switch_to_gigachat_lite.sh` для быстрого переключения
- ✅ Расширенная документация по выбору провайдера

**Изменено:**
- 📝 GigaChat Lite установлен как модель по умолчанию (вместо GigaChat)
- 📝 Обновлены рекомендации в логах при достижении лимитов
- 📝 Улучшены сообщения об ошибках с практическими советами

**Исправлено:**
- 🐛 Система больше не спамит запросы при достижении rate limit
- 🐛 Понятные сообщения о причине ошибки и времени сброса лимита

---

## 🙏 Благодарности

Спасибо за предложение использовать **GigaChat Lite** - это действительно оптимальное решение для тегирования! 🎯

---

**Авторы:** Telegram Channel Parser Team  
**Контакт:** https://github.com/your-repo  
**Лицензия:** MIT

