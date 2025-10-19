# 🚀 Quick Reference - Event Loop Fix

## ✅ Быстрая проверка работоспособности

```bash
# 1. Проверить что контейнер работает
docker ps | grep telethon

# 2. Проверить event loop (все должны быть в одном)
docker logs telethon | grep "event loop ID"

# 3. Запустить тестовый парсинг
curl -X POST http://localhost:8010/users/6/channels/parse

# 4. Проверить результат (должно быть > 0 постов)
docker logs telethon --tail 20 | grep "добавлено"
```

---

## 📊 Ожидаемые результаты

### ✅ ПРАВИЛЬНО (после исправления):
```
INFO:__main__:🔄 Главный event loop ID: 129796093177424
INFO:shared_auth_manager:✅ Client 8124731874 создан и подключен в event loop 129796093177424
INFO:parser_service:✅ ParserService: @banksta - добавлено 4 постов
{"posts_added":11,"status":"success"}
```

### ❌ НЕПРАВИЛЬНО (если проблема вернулась):
```
ERROR:parser_service:❌ ParserService: Ошибка event loop для @channel
The asyncio event loop must not change after connection
{"posts_added":0,"status":"success"}
```

---

## 🔧 Если проблема вернулась

### 1. Проверить код на новые `asyncio.run()`:
```bash
grep -r "asyncio.run(" telethon/*.py | grep -v "# КРИТИЧНО"
```

**Не должно быть результатов!** Кроме комментариев.

### 2. Пересобрать контейнер:
```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker compose down telethon
docker compose build telethon --no-cache
docker compose up -d telethon
```

### 3. Запустить автоматический тест:
```bash
cd telethon
./test_event_loop_fix.sh
```

---

## 📝 Ключевые принципы (Context7)

### ✅ ДЕЛАЙТЕ:
```python
# В главном event loop
asyncio.create_task(async_function())

# Из другого потока (API)
asyncio.run_coroutine_threadsafe(async_function(), main_loop)
```

### ❌ НЕ ДЕЛАЙТЕ:
```python
# НИКОГДА после инициализации:
asyncio.run(async_function())  # ❌ Создает НОВЫЙ loop!

# НИКОГДА:
await client.disconnect()
await client.connect()  # ❌ Если ошибка event loop
```

---

## 🔗 Полезные команды

### Мониторинг:
```bash
# Следить за логами в реальном времени
docker logs telethon -f

# Искать ошибки event loop
docker logs telethon | grep -i "event loop must not change"

# Статистика постов
docker exec telethon python3 -c "
from database import SessionLocal
from models import Post
db = SessionLocal()
print(f'Всего постов: {db.query(Post).count()}')
"
```

### Парсинг:
```bash
# Парсинг конкретного пользователя (ID=6)
curl -X POST http://localhost:8010/users/6/channels/parse

# Парсинг всех пользователей
curl -X POST http://localhost:8010/parse_all_channels

# Список пользователей
curl http://localhost:8010/users | jq
```

### Диагностика:
```bash
# Проверить активные клиенты
docker exec telethon python3 -c "
from shared_auth_manager import shared_auth_manager
print(f'Активных клиентов: {len(shared_auth_manager.active_clients)}')
for tid in shared_auth_manager.active_clients:
    print(f'  - Client {tid}')
"

# Проверить event loops
docker exec telethon python3 -c "
from shared_auth_manager import shared_auth_manager
loops = set(id(c.loop) for c in shared_auth_manager.active_clients.values())
print(f'Уникальных event loops: {len(loops)}')
if len(loops) == 1:
    print('✅ Все клиенты в ОДНОМ loop')
elif len(loops) > 1:
    print('❌ ПРОБЛЕМА: Клиенты в РАЗНЫХ loops!')
"
```

---

## 📚 Документация

- **`docs/EVENT_LOOP_FIX.md`** - Подробное объяснение проблемы и решения
- **`TESTING_EVENT_LOOP_FIX.md`** - Пошаговая инструкция по тестированию
- **`CHANGELOG_EVENT_LOOP.md`** - Список всех изменений
- **`VERIFICATION_REPORT.md`** - Отчет о проверке
- **`QUICK_REFERENCE.md`** - Эта шпаргалка

---

## 🆘 Помощь

### Если парсинг возвращает 0 постов:

1. **Проверить авторизацию:**
   ```bash
   curl http://localhost:8010/users | jq '.users[] | {id, first_name, is_authenticated}'
   ```

2. **Проверить каналы:**
   ```bash
   docker exec telethon python3 -c "
   from database import SessionLocal
   from models import Channel
   db = SessionLocal()
   channels = db.query(Channel).filter(Channel.is_active==True).count()
   print(f'Активных каналов: {channels}')
   "
   ```

3. **Проверить логи подробно:**
   ```bash
   docker logs telethon --tail 100 | grep -E "(ERROR|WARNING)"
   ```

### Если ошибки event loop вернулись:

1. Откатить последние изменения
2. Проверить что не добавили `asyncio.run()`
3. Проверить Context7 документацию перед изменениями
4. Пересобрать контейнер полностью

---

## ✅ Чеклист перед деплоем

- [ ] `docker logs telethon | grep "event loop" ` показывает один ID
- [ ] Тестовый парсинг возвращает > 0 постов
- [ ] Нет ERROR в логах за последние 10 минут
- [ ] API эндпоинты отвечают
- [ ] БД содержит посты
- [ ] `./test_event_loop_fix.sh` проходит успешно

---

**Версия:** 2.0  
**Дата:** 14.10.2025  
**Статус:** ✅ Production Ready
