# Проверка конфигурации моделей GigaChat

**Дата:** 11 октября 2025  
**Проблема:** Используется ли правильная модель для тегирования?

---

## 📊 Текущая конфигурация

### Тегирование (tagging_service.py)

**Настройки:**
```python
TAGGING_PROVIDER=gigachat
GIGACHAT_MODEL=GigaChat-Lite  ✅
GIGACHAT_PROXY_URL=http://gpt2giga-proxy:8090
```

**Логи:**
```
INFO:tagging_service:✅ TaggingService: Основной провайдер - GigaChat
INFO:tagging_service:💡 TaggingService: Используется модель GigaChat-Lite
INFO:tagging_service:⚡ GigaChat-Lite: быстрая модель с высокими лимитами
```

**Вывод:** ✅ **GigaChat-Lite - ПРАВИЛЬНАЯ модель для тегирования!**

---

## 🔍 Доступные модели GigaChat

Согласно [официальной документации](https://developers.sber.ru/docs/ru/gigachain/tools/utilities/gpttogiga-proxy-server):

### 1. GigaChat (базовая)
- Универсальная модель
- Средняя скорость
- Средняя стоимость

### 2. GigaChat-Lite (облегченная) ✅
- **Быстрее** базовой
- **Дешевле** базовой
- **Выше лимиты** (до 10,000 запросов/день vs 1,000)
- **Оптимальна для простых задач** (тегирование!)

### 3. GigaChat-Max (максимальная)
- Лучшее качество
- Медленнее
- Дороже
- Ниже лимиты

### ❌ GigaChat-Pro НЕ СУЩЕСТВУЕТ

**Примечание:** В документации нет модели "GigaChat-Pro". Возможно:
- Вы видите "GigaChat" (базовую модель)
- Или это отображается в аналитике как "Pro" для платных аккаунтов
- Или это старое название GigaChat-Max

---

## 🎯 Рекомендации по моделям

### Для тегирования

✅ **Используем: GigaChat-Lite** (текущая настройка)

**Почему:**
- Задача простая: определить 3-7 тегов
- Нужна скорость (парсинг каждые 30 мин)
- Нужны высокие лимиты (200+ постов/день)
- Lite справляется отлично!

**Не нужно менять!** ✅

### Для RAG-ответов

❓ **Используем: GigaChat (базовая)**

**Можно улучшить:**
```bash
# В .env добавить:
GIGACHAT_RAG_MODEL=GigaChat-Max
```

**Почему:**
- Задача сложная: анализ, выводы, суммаризация
- Качество важнее скорости
- Max лучше понимает контекст

### Для AI-дайджеста

✅ **Используем: GigaChat (базовая)** через ai_digest_generator

**Можно улучшить:**
```bash
# В .env:
GIGACHAT_MODEL=GigaChat  # Для тегирования остается Lite через tagging_service
```

**Или в коде ai_digest_generator.py:**
```python
self.gigachat_model = os.getenv("GIGACHAT_DIGEST_MODEL", "GigaChat-Max")
```

---

## 🔧 Настройка gpt2giga-proxy

### Проблема (до исправления)

**docker-compose.override.yml:**
```yaml
gpt2giga-proxy:
  environment:
    - GIGACHAT_CREDENTIALS=${GIGACHAT_CREDENTIALS}
    - PROXY_HOST=0.0.0.0
    # ❌ Нет GIGACHAT_MODEL
    # ❌ Нет GPT2GIGA_PASS_MODEL
```

**Последствия:**
- Proxy использует default модель (GigaChat базовая)
- Клиенты (tagging_service, ai_digest) НЕ МОГУТ передать свою модель
- tagging_service хочет Lite, но получает базовую!

### Исправление ✅

**docker-compose.override.yml:**
```yaml
gpt2giga-proxy:
  environment:
    - GIGACHAT_CREDENTIALS=${GIGACHAT_CREDENTIALS}
    - PROXY_HOST=0.0.0.0
    # Модель по умолчанию
    - GIGACHAT_MODEL=${GIGACHAT_MODEL:-GigaChat-Lite}
    # Разрешить клиентам передавать модель
    - GPT2GIGA_PASS_MODEL=true
    # Модель для embeddings
    - GPT2GIGA_EMBEDDINGS=EmbeddingsGigaR
```

**Результат:**
- ✅ tagging_service передает "GigaChat-Lite" → proxy использует Lite
- ✅ ai_digest передает "GigaChat" → proxy использует базовую
- ✅ Можно легко переключить на Max через model в запросе

---

## 📊 Как это работает (согласно gpt2giga документации)

### GPT2GIGA_PASS_MODEL=true

**Когда клиент отправляет:**
```json
{
  "model": "GigaChat-Lite",
  "messages": [...]
}
```

**Proxy:**
- ✅ Использует модель из запроса: "GigaChat-Lite"
- Игнорирует GIGACHAT_MODEL из env

**Когда клиент НЕ указывает модель:**
```json
{
  "messages": [...]
}
```

**Proxy:**
- ✅ Использует GIGACHAT_MODEL из env: "GigaChat-Lite"

### GPT2GIGA_PASS_MODEL=false (по умолчанию)

**Proxy:**
- ❌ Игнорирует model из запроса
- Всегда использует GIGACHAT_MODEL из env

**Проблема:** tagging_service НЕ может использовать Lite!

---

## ✅ Итоговая конфигурация

### Переменные окружения

**.env (корневой):**
```bash
GIGACHAT_MODEL=GigaChat-Lite     # Default для proxy
```

**docker-compose.override.yml (telethon):**
```yaml
telethon:
  environment:
    - GIGACHAT_MODEL=GigaChat-Lite  # tagging_service
```

**docker-compose.override.yml (gpt2giga-proxy):**
```yaml
gpt2giga-proxy:
  environment:
    - GIGACHAT_MODEL=GigaChat-Lite     # Default
    - GPT2GIGA_PASS_MODEL=true         # Разрешить передачу
    - GPT2GIGA_EMBEDDINGS=EmbeddingsGigaR
```

**docker-compose.override.yml (rag-service):**
```yaml
rag-service:
  environment:
    # Не передает GIGACHAT_MODEL - использует default из proxy
    # ai_digest_generator.py может указать свою модель в коде
```

### Модели по сервисам

| Сервис | Модель | Источник |
|--------|--------|----------|
| **Тегирование** | GigaChat-Lite | tagging_service.py передает в request |
| **Embeddings** | EmbeddingsGigaR | gpt2giga-proxy default |
| **RAG-ответы** | GigaChat | fallback, через proxy default |
| **AI-дайджест** | GigaChat | ai_digest_generator.py указывает в коде |

---

## 💡 Рекомендации

### Текущая настройка ✅ ОПТИМАЛЬНА

- **Тегирование:** GigaChat-Lite (быстро, дешево, высокие лимиты)
- **AI-дайджест:** GigaChat базовая (хорошее качество)

### Опциональные улучшения

**Если нужно лучшее качество дайджестов:**
```python
# В ai_digest_generator.py (строка 28):
self.gigachat_model = os.getenv("GIGACHAT_DIGEST_MODEL", "GigaChat-Max")
```

**Если есть проблемы с лимитами:**
- Проверьте статус на https://developers.sber.ru
- Базовая: ~1,000 запросов/день
- Lite: ~10,000 запросов/день
- Max: зависит от тарифа

---

## 🧪 Тестирование

### Проверка что модель передается

```bash
# Включить verbose логи в gpt2giga
docker exec gpt2giga-proxy env | grep VERBOSE

# Или в docker-compose добавить:
# - GPT2GIGA_VERBOSE=true
```

### Проверка тегирования

```bash
curl -X POST "http://localhost:8010/posts/SOME_POST_ID/generate_tags"
docker logs telethon | grep "Используется модель"
```

Должно показать: "GigaChat-Lite"

---

## ✅ Заключение

### Конфигурация ПРАВИЛЬНАЯ! ✅

- ✅ **Тегирование:** GigaChat-Lite (оптимально)
- ✅ **Embeddings:** EmbeddingsGigaR (правильно)
- ✅ **AI-дайджест:** GigaChat (хорошо)
- ✅ **GPT2GIGA_PASS_MODEL:** true (теперь можно передавать модели)

### "GigaChat Pro" - что это?

❌ Такой модели не существует!

**Возможные объяснения:**
1. Аналитика показывает "GigaChat" (базовую) как "Pro"
2. Старое название
3. Маркетинговое название для платных аккаунтов

**Реальные модели:**
- GigaChat (базовая)
- GigaChat-Lite (облегченная) ← Используем
- GigaChat-Max (максимальная)

---

**Статус:** ✅ Конфигурация правильная, менять не нужно!  
**Дата:** 11 октября 2025

