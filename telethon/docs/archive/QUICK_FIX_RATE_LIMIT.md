# ⚡ Быстрое решение: Переключение на GigaChat Lite

## Проблема
```
ERROR: 429 Rate limit exceeded: free-models-per-day
```

OpenRouter исчерпал лимит 50 запросов/день.

---

## ✅ Решение за 2 минуты

### Шаг 1: Проверьте что у вас есть GigaChat credentials

```bash
# Проверьте корневой .env
cat /home/ilyasni/n8n-server/n8n-installer/.env | grep GIGACHAT_CREDENTIALS
```

**Если НЕТ:**
1. Получите credentials: https://developers.sber.ru/gigachat
2. Добавьте в `.env`:
   ```env
   GIGACHAT_CREDENTIALS=your_credentials_here
   ```

### Шаг 2: Переключите провайдера

Отредактируйте корневой `.env` или `telethon/.env`:

```bash
# Добавьте или измените:
TAGGING_PROVIDER=gigachat
GIGACHAT_MODEL=GigaChat-Lite
```

### Шаг 3: Перезапустите сервис

```bash
cd /home/ilyasni/n8n-server/n8n-installer
docker compose -p localai restart telethon gpt2giga-proxy
```

### Шаг 4: Проверьте работу

```bash
# Логи должны показать:
docker logs telethon 2>&1 | grep TaggingService

# Ожидается:
# ✅ TaggingService: Инициализирован с GigaChat
# 💡 TaggingService: Используется модель GigaChat-Lite
# ⚡ GigaChat-Lite: быстрая модель с высокими лимитами
```

---

## 🎯 Почему GigaChat Lite?

- ⚡ **Быстрее** - генерация тегов занимает меньше времени
- 💰 **Экономичнее** - стоимость запроса ниже
- 📈 **Выше лимиты** - можно обрабатывать больше постов
- ✅ **Достаточно качества** - для тегов не нужна самая мощная модель

---

## 📊 Сравнение для тегирования

| Модель | Скорость | Лимит/день | Качество тегов |
|--------|----------|------------|----------------|
| OpenRouter (free) | Средняя | 50 | Отлично ⭐⭐⭐⭐⭐ |
| **GigaChat Lite** | **Быстрая** ⚡ | **~10,000** | **Хорошо** ⭐⭐⭐⭐ |
| GigaChat | Средняя | ~5,000 | Отлично ⭐⭐⭐⭐⭐ |
| GigaChat Pro | Медленная | ~2,000 | Отлично ⭐⭐⭐⭐⭐ |

**Вывод:** GigaChat Lite - оптимальный баланс для автоматического тегирования!

---

## 🔄 Обработка старых постов

После переключения обработайте посты с ошибками:

```bash
# Вручную через API
curl -X POST "http://localhost:8010/users/YOUR_USER_ID/posts/retry_tagging?limit=100"

# Или автоматически (парсер сам повторит попытки)
# Ничего не делать - система сама обработает при следующем парсинге
```

---

## 🆘 Troubleshooting

**GigaChat не отвечает:**
```bash
# Проверьте gpt2giga-proxy
docker logs gpt2giga-proxy

# Проверьте GIGACHAT_CREDENTIALS в .env
docker exec telethon env | grep GIGACHAT
```

**Теги не генерируются:**
```bash
# Проверьте что TAGGING_PROVIDER установлен
docker exec telethon env | grep TAGGING_PROVIDER

# Должно быть:
# TAGGING_PROVIDER=gigachat
```

---

## 📚 Полная документация

- [Подробное решение Rate Limit 429](docs/troubleshooting/RATE_LIMIT_429.md)
- [Конфигурация Tagging Service](docs/features/TAGGING_RETRY_SYSTEM.md)
- [RAG Service + GigaChat](docs/quickstart/RAG_QUICKSTART.md)

---

**Создано:** 11 октября 2025  
**Обновлено:** После внедрения GigaChat Lite по умолчанию

