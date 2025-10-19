# 🏷️ Workflow Тегирования и Индексации Постов

**Дата создания:** 11 октября 2025  
**Версия:** 1.0

## 📋 Описание

Этот документ описывает полный workflow обработки постов от парсинга до векторной индексации.

---

## 🔄 Общий Workflow

```
┌─────────────────┐
│   Парсер        │
│  (каждые 30м)   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Новые посты    │
│  сохранены в БД │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Тегирование    │◄──────────┐
│  (GigaChat/     │           │ Retry при ошибках
│   OpenRouter)   │           │ (max 5 попыток)
└────────┬────────┘           │
         │                    │
         ▼                    │
┌─────────────────┐           │
│ Теги сохранены  │───────────┘
│  в Post.tags    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ HTTP запрос к   │
│  RAG-сервису    │◄──────────┐
│ /rag/index/batch│           │ Retry 3 попытки
└────────┬────────┘           │ (2/4/6 сек)
         │                    │
         ├────────────────────┘
         │ Если все retry неудачны
         ▼
┌─────────────────┐
│ Статус: pending │
│ в IndexingStatus│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ RAG-сервис:     │
│ - Генерация     │
│   embeddings    │
│   (GigaChat)    │
│ - Chunking для  │
│   длинных       │
│ - Запись в      │
│   Qdrant        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Индексация      │
│ завершена       │
│ (success/failed)│
└─────────────────┘
```

---

## 🎯 Компоненты Системы

### 1. **ParserService** (`parser_service.py`)

**Задачи:**
- Парсинг каналов каждые 30 минут
- Создание новых постов в БД
- Запуск фонового тегирования
- Уведомление RAG-сервиса о новых постах

**Ключевые методы:**
```python
async def parse_all_channels()
    # Парсит каналы всех аутентифицированных пользователей
    # Собирает ID новых постов в self.new_post_ids

async def _tag_new_posts_background()
    # 1. Вызывает TaggingService для генерации тегов
    # 2. Вызывает _notify_rag_service для индексации

async def _notify_rag_service(post_ids: List[int])
    # Отправляет HTTP POST на /rag/index/batch
    # Retry: 3 попытки с экспоненциальной задержкой
    # Fallback: сохраняет в IndexingStatus со статусом 'pending'
```

**Переменные окружения:**
```env
PARSER_INTERVAL_MINUTES=30
RAG_SERVICE_URL=http://rag-service:8020
RAG_SERVICE_ENABLED=true
```

---

### 2. **TaggingService** (`tagging_service.py`)

**Задачи:**
- Генерация тегов для текста поста через AI
- Основной провайдер: GigaChat (GigaChat-Lite)
- Fallback провайдер: OpenRouter (при ошибках GigaChat)
- Retry механизм для неудачных попыток

**Workflow тегирования:**

```python
async def generate_tags_for_text(text: str) -> List[str]
    # 1. Проверка длины текста (мин 10 символов)
    # 2. Формирование промпта
    # 3. Отправка запроса к GigaChat API
    # 4. Парсинг JSON ответа (улучшенный regex)
    # 5. Валидация и очистка тегов:
    #    - Удаление дубликатов
    #    - Проверка длины (2-50 символов)
    #    - Lowercase нормализация
    # 6. Ограничение: максимум 7 тегов

async def update_post_tags(post_id: int) -> bool
    # 1. Проверка лимита попыток (max 5)
    # 2. Генерация тегов
    # 3. Обновление Post.tags в БД
    # 4. Обновление статуса (success/failed/retrying)
```

**Статусы тегирования:**
- `pending` - ожидает обработки
- `success` - теги успешно сгенерированы
- `failed` - все попытки исчерпаны
- `retrying` - промежуточный статус при retry

**Поля в модели Post:**
```python
tags = Column(JSON, nullable=True)  # ["технологии", "AI", "новости"]
tagging_status = Column(String, default="pending")
tagging_attempts = Column(Integer, default=0)
last_tagging_attempt = Column(DateTime, nullable=True)
tagging_error = Column(Text, nullable=True)
```

**Переменные окружения:**
```env
TAGGING_PROVIDER=gigachat  # gigachat или openrouter
TAGGING_FALLBACK_OPENROUTER=true
GIGACHAT_PROXY_URL=http://gpt2giga-proxy:8090
GIGACHAT_MODEL=GigaChat-Lite
OPENROUTER_API_KEY=sk-...
OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free
TAGGING_BATCH_SIZE=10
TAGGING_MAX_RETRIES=3
TAGGING_MAX_ATTEMPTS=5
```

**Исправленные проблемы:**

**✅ Проблема #1: Ошибка парсинга JSON**
- **Было:** Жадный regex `r'\[.*\]'` захватывал от первой до последней `]`
- **Стало:** Нежадный regex `r'\[.*?\]'` для точного поиска первого массива
- **Добавлено:** Улучшенное логирование с `repr()` для отладки

**✅ Проблема #2: Дубликаты тегов**
- **Добавлено:** Set для отслеживания уникальных тегов
- **Валидация:** Проверка длины тега (2-50 символов)
- **Очистка:** Lowercase нормализация и trim

---

### 3. **RAG Service** (Векторная Индексация)

**Компоненты:**
- `indexer.py` - IndexerService для индексации
- `embeddings.py` - EmbeddingsService для генерации векторов
- `vector_db.py` - QdrantClient для работы с Qdrant
- `main.py` - FastAPI endpoints

**Workflow индексации:**

```python
async def index_post(post_id: int)
    # 1. Получение поста из БД
    # 2. Проверка наличия текста
    # 3. Chunking если текст длинный (>1536 токенов)
    # 4. Генерация embeddings (GigaChat)
    # 5. Сохранение в Qdrant с payload:
    #    - post_id, text, channel_id, tags
    #    - posted_at, url, views
    #    - chunk_index, embedding_provider
    # 6. Обновление IndexingStatus
```

**Модель IndexingStatus:**
```python
user_id = Column(Integer, ForeignKey("users.id"))
post_id = Column(Integer, ForeignKey("posts.id"))
indexed_at = Column(DateTime)
vector_id = Column(String)  # UUID в Qdrant
status = Column(String)  # success, failed, pending
error = Column(Text)
```

**API Endpoints:**

| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/rag/index/post/{post_id}` | POST | Индексировать один пост |
| `/rag/index/batch` | POST | Batch индексация постов |
| `/rag/index/user/{user_id}` | POST | Индексировать все посты пользователя |
| `/rag/reindex/user/{user_id}` | POST | Переиндексация (включая существующие) |
| **`/rag/retry/pending`** | POST | **Retry для pending/failed постов** ✨ |
| `/rag/stats/{user_id}` | GET | Статистика индексации |
| `/rag/search` | GET | Векторный поиск по постам |

**✨ Новый endpoint: `/rag/retry/pending`**

```bash
# Retry всех pending постов для конкретного пользователя
curl -X POST "http://localhost:8020/rag/retry/pending?user_id=6&limit=100"

# Retry для всех пользователей
curl -X POST "http://localhost:8020/rag/retry/pending?limit=100"
```

**Переменные окружения:**
```env
QDRANT_URL=http://qdrant:6333
GIGACHAT_PROXY_URL=http://gpt2giga-proxy:8090
EMBEDDING_MAX_TOKENS_GIGACHAT=1536
EMBEDDING_OVERLAP_TOKENS_GIGACHAT=256
```

---

## 🔧 Исправленные Проблемы

### **Проблема #3: Слабая обработка ошибок RAG-сервиса**

**Было:**
```python
except Exception as e:
    logger.warning(f"⚠️ Не удалось уведомить RAG-сервис: {e}")
    # Посты просто пропускаются
```

**Стало:**
```python
# 1. Retry с экспоненциальной задержкой (3 попытки)
for attempt in range(max_retries):
    try:
        response = await client.post(...)
        if response.status_code == 200:
            return  # Успех
        elif response.status_code >= 500:
            # Server error - retry
            await asyncio.sleep(retry_delay * (attempt + 1))
            continue
    except (httpx.TimeoutException, httpx.ConnectError):
        # Retry при сетевых ошибках
        ...

# 2. Fallback: сохранение в IndexingStatus
for post_id in post_ids:
    status = IndexingStatus(
        user_id=post.user_id,
        post_id=post_id,
        status="pending",
        error="RAG service unavailable during parsing"
    )
    db.add(status)
db.commit()
```

**Преимущества:**
- ✅ Посты не теряются при недоступности RAG-сервиса
- ✅ Автоматический retry через endpoint `/rag/retry/pending`
- ✅ Детальное логирование ошибок

---

## 📊 Мониторинг и Отладка

### **Проверка статуса тегирования:**

```sql
-- Статистика тегирования
SELECT 
    tagging_status,
    COUNT(*) as count,
    AVG(tagging_attempts) as avg_attempts
FROM posts
WHERE user_id = 6
GROUP BY tagging_status;
```

### **Проверка статуса индексации:**

```bash
# Статистика для пользователя
curl http://localhost:8020/rag/stats/6
```

```json
{
  "user_id": 6,
  "collection_name": "telegram_posts_6",
  "vectors_count": 150,
  "points_count": 150,
  "indexed_posts": 145,
  "pending_posts": 5,
  "failed_posts": 0
}
```

### **Логи для отладки:**

**Тегирование:**
```bash
docker logs telethon 2>&1 | grep TaggingService | tail -50
```

**Индексация:**
```bash
docker logs rag-service 2>&1 | grep indexer | tail -50
```

---

## 🚀 Ручная Обработка

### **Retry неудачного тегирования:**

```python
# Через API
curl -X POST "http://localhost:8010/tags/retry_failed?user_id=6&limit=50"
```

### **Retry неудачной индексации:**

```bash
# Все pending посты пользователя
curl -X POST "http://localhost:8020/rag/retry/pending?user_id=6"

# Все pending посты всех пользователей
curl -X POST "http://localhost:8020/rag/retry/pending"
```

### **Переиндексация всех постов:**

```bash
curl -X POST "http://localhost:8020/rag/reindex/user/6"
```

---

## ⚙️ Настройка и Оптимизация

### **Для высоких нагрузок:**

```env
# Увеличить batch size
TAGGING_BATCH_SIZE=20
EMBEDDING_BATCH_SIZE=50

# Уменьшить интервал парсинга
PARSER_INTERVAL_MINUTES=15

# Увеличить количество попыток
TAGGING_MAX_ATTEMPTS=10
```

### **Для экономии ресурсов:**

```env
# Уменьшить batch size
TAGGING_BATCH_SIZE=5

# Увеличить интервал парсинга
PARSER_INTERVAL_MINUTES=60

# Отключить RAG-индексацию (только теги)
RAG_SERVICE_ENABLED=false
```

---

## 📚 Дополнительные Ресурсы

- [API Документация](../../README.md)
- [RAG System Guide](./rag/AI_DIGEST_GUIDE.md)
- [Tagging Service Changelog](../CHANGELOG_TAGGING.md)
- [Troubleshooting](../troubleshooting/GIGACHAT_PRO_FIX.md)

---

## ✅ Checklist для Production

- [ ] Настроены переменные окружения для обоих провайдеров (GigaChat + OpenRouter)
- [ ] RAG-сервис запущен и доступен (`/health` возвращает 200)
- [ ] Qdrant доступен и работает
- [ ] Настроены мониторинг и алерты
- [ ] Периодический запуск `/rag/retry/pending` (cron или планировщик)
- [ ] Бэкапы базы данных (SQLite или PostgreSQL)
- [ ] Бэкапы Qdrant коллекций

---

**Автор:** Telegram Channel Parser Team  
**Обновлено:** 11 октября 2025

