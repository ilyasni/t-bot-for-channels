# Тестирование исправления Event Loop

## 🎯 Цель
Проверить что исправление ошибок event loop работает и парсинг постов возобновлен.

## 📝 Быстрая проверка

### 1. Перезапустить контейнер

```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker-compose restart telethon
```

### 2. Проверить запуск без ошибок event loop

```bash
# Смотрим логи запуска (первые 2 минуты)
docker logs telethon --tail 50 -f
```

**Ожидаемое:**
- ✅ `🤖 Telegram Bot запущен в async task`
- ✅ `✅ ParserService инициализирован`
- ✅ Нет ошибок `event loop must not change`

**НЕ должно быть:**
- ❌ `ERROR:parser_service:❌ ParserService: Ошибка event loop`
- ❌ `RuntimeError: Event loop is closed`

### 3. Дождаться первого парсинга (или запустить вручную)

**Вариант А: Дождаться автоматического парсинга (30 минут)**

```bash
# Следим за логами
docker logs telethon -f | grep -E "(парсинг|добавлено|ParserService)"
```

**Вариант Б: Запустить парсинг вручную через API**

```bash
# Получить список пользователей
curl http://localhost:8010/users | jq

# Запустить парсинг для пользователя (замените USER_ID)
curl -X POST http://localhost:8010/parse/user/{USER_ID}
```

### 4. Проверить результаты

```bash
# Должны появиться строки с добавленными постами
docker logs telethon --tail 100 | grep "добавлено"
```

**Ожидаемое:**
```
INFO:parser_service:✅ ParserService: @channel1 - добавлено 5 постов
INFO:parser_service:✅ ParserService: @channel2 - добавлено 3 постов
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 47 постов
```

**НЕ должно быть:**
```
INFO:parser_service:✅ ParserService: Парсинг завершен. Всего добавлено 0 постов
```

## 🔍 Детальная диагностика

### Проверка event loop ID

Если хотите убедиться что клиенты создаются в одном loop:

```bash
# Включить DEBUG логи
docker exec -it telethon sh -c "echo 'DEBUG_LOGS=true' >> .env"
docker-compose restart telethon

# Искать в логах "event loop"
docker logs telethon -f | grep "event loop"
```

**Ожидаемое:**
```
✅ Client 8124731874 создан в event loop 140234567890
📅 ParserService: Задача парсинга создана в текущем event loop
♻️ Используем существующий клиент 8124731874 в loop 140234567890
```

**Все loop ID должны быть ОДИНАКОВЫЕ!**

### Проверка клиентов в памяти

```bash
# Зайти в контейнер
docker exec -it telethon python3

# В Python консоли
>>> from shared_auth_manager import shared_auth_manager
>>> len(shared_auth_manager.active_clients)
1  # Или сколько у вас пользователей

>>> import asyncio
>>> loop = asyncio.get_event_loop()
>>> id(loop)
140234567890  # Запомните этот ID

# Проверьте что клиенты в том же loop
>>> for tid, client in shared_auth_manager.active_clients.items():
...     print(f"Client {tid}: loop={id(client.loop)}, same={id(client.loop)==id(loop)}")
Client 8124731874: loop=140234567890, same=True  # ВАЖНО: same=True!
```

## ✅ Критерии успеха

- [ ] Контейнер запускается без ошибок event loop
- [ ] Парсинг добавляет посты (> 0 постов)
- [ ] Все клиенты работают в одном event loop ID
- [ ] Нет предупреждений "Client создан в другом event loop"
- [ ] Логи показывают "♻️ Используем существующий клиент"

## 🐛 Если проблемы остались

### Проблема: Все еще 0 постов

```bash
# Проверьте что пользователь авторизован
docker exec -it telethon python3 -c "
from database import SessionLocal
from models import User
db = SessionLocal()
users = db.query(User).all()
for u in users:
    print(f'User {u.telegram_id}: authenticated={u.is_authenticated}, channels={len(u.get_active_channels(db))}')
"
```

### Проблема: Ошибки подключения к каналам

```bash
# Проверьте что каналы валидные
docker exec -it telethon python3 -c "
from database import SessionLocal
from models import Channel
db = SessionLocal()
channels = db.query(Channel).filter(Channel.is_active==True).all()
for c in channels:
    print(f'Channel @{c.channel_username}: subscriptions={len(c.get_user_subscriptions(db))}')
"
```

### Проблема: Логи показывают "Client создан в другом event loop"

Это НЕ ДОЛЖНО происходить после исправления. Если видите это:

1. Проверьте что изменения применены:
```bash
docker exec -it telethon grep "КРИТИЧНО" parser_service.py
```

2. Пересоберите образ:
```bash
docker-compose down
docker-compose build telethon
docker-compose up -d telethon
```

## 📊 Мониторинг

### Автоматическая проверка каждые 5 минут

```bash
# Добавьте в crontab на хосте
*/5 * * * * docker logs telethon --tail 20 | grep -q "добавлено" && echo "✅ Parsing OK" || echo "⚠️ No posts parsed"
```

### Prometheus метрики (если настроены)

- `telethon_posts_parsed_total` - должна расти
- `telethon_event_loop_errors_total` - должна быть 0

## 🔗 Связанная документация

- [EVENT_LOOP_FIX.md](docs/EVENT_LOOP_FIX.md) - Подробное объяснение исправления
- [Context7 Telethon docs](https://docs.telethon.dev/en/v2/developing/faq) - Официальная документация

## 📞 Поддержка

Если проблемы не решены, проверьте:
1. Версия Telethon совместима (проверить в requirements.txt)
2. Python >= 3.9
3. Нет конфликтов в docker-compose.yml (порты, volumes)

---

**Дата создания:** 14 октября 2025  
**Автор:** AI Assistant + Context7  
**Статус:** ✅ Ready for Testing

