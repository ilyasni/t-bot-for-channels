# 📋 Шпаргалка команд - Telegram Parser System

## 🚀 Быстрая проверка (30 секунд)

```bash
cd /home/ilyasni/n8n-server/n8n-installer/telethon
./test_full_system.sh
```

---

## 🔍 Мониторинг

### Логи в реальном времени:
```bash
docker logs telethon -f
docker logs rag-service -f
```

### Поиск ошибок:
```bash
# Event loop ошибки (должно быть пусто!)
docker logs telethon | grep -i "event loop must not change"

# Все ошибки
docker logs telethon --tail 100 | grep ERROR
```

### Event loop ID (все должны быть одинаковые):
```bash
docker logs telethon | grep "event loop ID"
```

---

## 📊 Статистика

### Посты:
```bash
docker exec telethon python3 -c "
from database import SessionLocal
from models import Post
db = SessionLocal()
print(f'Всего постов: {db.query(Post).count()}')
print(f'С тегами: {db.query(Post).filter(Post.tags != None).count()}')
"
```

### Пользователи:
```bash
curl http://localhost:8010/users | jq '.users[] | {id, first_name, is_authenticated, posts: .id}'
```

### Qdrant:
```bash
curl http://localhost:8020/rag/stats/6 | jq
```

---

## 🔄 Парсинг

### Один пользователь:
```bash
curl -X POST http://localhost:8010/users/6/channels/parse
```

### Все пользователи:
```bash
curl -X POST http://localhost:8010/parse_all_channels
```

### Результаты парсинга:
```bash
docker logs telethon --tail 50 | grep "добавлено"
```

---

## 🏷️ Тегирование

### Статистика:
```bash
docker exec telethon python3 -c "
from database import SessionLocal
from models import Post
db = SessionLocal()
with_tags = db.query(Post).filter(Post.tags != None).count()
total = db.query(Post).count()
print(f'{with_tags}/{total} ({with_tags/total*100:.1f}%)')
"
```

### Ручное тегирование:
```bash
docker exec telethon python3 -c "
import asyncio
from tagging_service import tagging_service
asyncio.run(tagging_service.process_posts_batch([POST_ID_1, POST_ID_2]))
"
```

---

## 🔍 Поиск

### Векторный поиск:
```bash
curl "http://localhost:8020/rag/search?user_id=6&query=автомобили&limit=5" | jq
```

### С фильтрами:
```bash
curl "http://localhost:8020/rag/search?user_id=6&query=Tesla&channel_id=11&limit=10&min_score=0.7" | jq
```

### Популярные теги:
```bash
curl http://localhost:8020/rag/tags/popular/6 | jq
```

---

## 📤 Индексация

### Batch индексация:
```bash
curl -X POST http://localhost:8020/rag/index/batch \
  -H "Content-Type: application/json" \
  -d '{"post_ids": [729, 730, 731, 732, 733]}'
```

### Один пост:
```bash
curl -X POST http://localhost:8020/rag/index/post/733
```

### Переиндексация всех постов пользователя:
```bash
curl -X POST http://localhost:8020/rag/reindex/user/6
```

### Retry failed индексаций:
```bash
curl -X POST http://localhost:8020/rag/retry/pending
```

---

## 🛠️ Обслуживание

### Перезапуск:
```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker compose restart telethon
```

### Пересборка:
```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker compose down telethon
docker compose build telethon
docker compose up -d telethon
```

### Проверка после перезапуска:
```bash
sleep 10 && docker logs telethon --tail 50 | grep "event loop"
```

---

## 🐛 Troubleshooting

### Если парсинг возвращает 0 постов:
```bash
# 1. Проверить авторизацию
curl http://localhost:8010/users | jq '.users[] | {id, is_authenticated}'

# 2. Проверить каналы
docker exec telethon python3 -c "
from database import SessionLocal
from models import Channel
db = SessionLocal()
print(f'Активных каналов: {db.query(Channel).filter(Channel.is_active==True).count()}')
"

# 3. Проверить последний парсинг
docker logs telethon --tail 200 | grep -E "(ParserService|добавлено)"
```

### Если вернулись ошибки event loop:
```bash
# 1. Проверить что нет новых asyncio.run()
grep -r "asyncio.run(" telethon/*.py | grep -v "# КРИТИЧНО"

# 2. Пересобрать
docker compose build telethon --no-cache
docker compose up -d telethon

# 3. Проверить event loop ID
docker logs telethon | grep "event loop ID"
```

---

## 📚 Документация

- **FINAL_SUMMARY.md** - Полный отчет
- **QUICK_REFERENCE.md** - Быстрая справка
- **README_FIXES.md** - Краткое резюме
- **COMMANDS_CHEATSHEET.md** - Эта шпаргалка

---

Версия: 2.0  
Дата: 14.10.2025
