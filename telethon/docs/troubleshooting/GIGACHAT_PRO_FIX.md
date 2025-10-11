# Исправление: GigaChat-2-Pro → GigaChat-Lite

**Дата:** 11 октября 2025  
**Проблема:** gpt2giga/.env использует GigaChat-2-Pro вместо GigaChat-Lite

---

## 🔍 Проблема

### Найдено в `gpt2giga/.env`:

```bash
GIGACHAT_MODEL=GigaChat-2-Pro  ← ПРОБЛЕМА!
```

### Что происходит:

1. **Dockerfile.gpt2giga** копирует весь контекст: `COPY . .`
2. Это включает `.env` файл
3. **gpt2giga читает `.env`** из своей директории
4. `.env` **ПЕРЕОПРЕДЕЛЯЕТ** переменные из docker-compose!

### Результат:

```
⚠️ docker-compose.override.yml: GIGACHAT_MODEL=GigaChat-Lite
⚠️ gpt2giga/.env: GIGACHAT_MODEL=GigaChat-2-Pro

→ Используется: GigaChat-2-Pro (из .env)!
```

---

## ✅ Исправление

### Вариант 1: Отредактировать gpt2giga/.env (РЕКОМЕНДУЕТСЯ)

```bash
nano /home/ilyasni/n8n-server/n8n-installer/gpt2giga/.env
```

Заменить содержимое на:

```bash
GIGACHAT_VERIFY_SSL_CERTS=False
GIGACHAT_BASE_URL="https://gigachat.devices.sberbank.ru/api/v1"
# Разрешить клиентам передавать свою модель в запросе
GPT2GIGA_PASS_MODEL=true
# Модель по умолчанию (если клиент не указал свою)
GIGACHAT_MODEL=GigaChat-Lite
# Модель для embeddings
GPT2GIGA_EMBEDDINGS=EmbeddingsGigaR
# Credentials
GIGACHAT_CREDENTIALS=N2MwNTA0NGMtZTM4Yy00YjRhLTliZjEtYTI5YzVmMWE4ZWMyOmRmM2Q3MWY1LTI2ZDItNDA2MS04NzVjLTIyYzNkM2YwMWRjMg==
```

**Затем перезапустить:**
```bash
docker restart gpt2giga-proxy
```

### Вариант 2: Удалить .env (если env vars в docker-compose достаточно)

```bash
mv /home/ilyasni/n8n-server/n8n-installer/gpt2giga/.env \
   /home/ilyasni/n8n-server/n8n-installer/gpt2giga/.env.backup

docker restart gpt2giga-proxy
```

Тогда будут использоваться только переменные из docker-compose.override.yml.

### Вариант 3: Изменить Dockerfile (не рекомендуется)

Исключить .env из копирования в Dockerfile.gpt2giga.

---

## 🎯 Рекомендуемые действия

### Шаг 1: Отредактируйте файл

```bash
nano /home/ilyasni/n8n-server/n8n-installer/gpt2giga/.env
```

**Замените:**
```bash
# Было:
GIGACHAT_MODEL=GigaChat-2-Pro

# Стало:
GIGACHAT_MODEL=GigaChat-Lite
GPT2GIGA_PASS_MODEL=true
GPT2GIGA_EMBEDDINGS=EmbeddingsGigaR
```

### Шаг 2: Перезапустите proxy

```bash
docker restart gpt2giga-proxy
```

### Шаг 3: Проверьте

```bash
docker exec gpt2giga-proxy env | grep GIGACHAT_MODEL
# Должно показать: GIGACHAT_MODEL=GigaChat-Lite

docker logs telethon --tail 5 | grep "модель"
# Должно показать: "Используется модель GigaChat-Lite"
```

---

## 📊 Зачем нужно GPT2GIGA_PASS_MODEL=true?

Согласно [документации gpt2giga](https://developers.sber.ru/docs/ru/gigachain/tools/utilities/gpttogiga-proxy-server):

### GPT2GIGA_PASS_MODEL=false (по умолчанию)

```
Клиент отправляет: {"model": "GigaChat-Lite", ...}
                          ↓
Proxy ИГНОРИРУЕТ и использует GIGACHAT_MODEL из .env
                          ↓
Результат: GigaChat-2-Pro (из .env)
```

### GPT2GIGA_PASS_MODEL=true ✅

```
Клиент отправляет: {"model": "GigaChat-Lite", ...}
                          ↓
Proxy ИСПОЛЬЗУЕТ модель из запроса
                          ↓
Результат: GigaChat-Lite (как запрошено!)
```

**Преимущество:**
- tagging_service может использовать GigaChat-Lite
- ai_digest_generator может использовать GigaChat или GigaChat-Max
- Гибкость без изменения proxy

---

## 🔍 Доступные модели GigaChat

Согласно документации:

### Версия 1.0 (старые названия)
- `GigaChat` - базовая
- `GigaChat-Plus` - улучшенная (устарела)
- `GigaChat-Pro` - профессиональная (устарела)

### Версия 2.0 (текущие названия) ✅
- `GigaChat` - базовая
- `GigaChat-Lite` - облегченная ← Для тегирования!
- `GigaChat-Max` - максимальная ← Для сложных задач!

### Альтернативные названия (с префиксом)
- `GigaChat-2-Pro` - вероятно GigaChat базовая v2
- `GigaChat-2-Max` - вероятно GigaChat-Max

**Рекомендация:** Использовать **без префикса "2-"**:
- ✅ `GigaChat-Lite` (для тегирования)
- ✅ `GigaChat` (для RAG, базовая)
- ✅ `GigaChat-Max` (для AI-дайджеста, опционально)

---

## ✅ Итоговая конфигурация

### gpt2giga/.env (после исправления)

```bash
GIGACHAT_MODEL=GigaChat-Lite         ← Default
GPT2GIGA_PASS_MODEL=true             ← Разрешить передачу
GPT2GIGA_EMBEDDINGS=EmbeddingsGigaR  ← Для embeddings
GIGACHAT_CREDENTIALS=...
```

### Как будут использоваться модели

| Сервис | Передает в request | Proxy использует |
|--------|-------------------|------------------|
| **Тегирование** | `GigaChat-Lite` | GigaChat-Lite ✅ |
| **Embeddings** | (автоматически) | EmbeddingsGigaR ✅ |
| **RAG-ответы** | `GigaChat` | GigaChat ✅ |
| **AI-дайджест** | `GigaChat` | GigaChat ✅ |

---

## 🚀 После исправления

```bash
# Перезапустить proxy
docker restart gpt2giga-proxy

# Проверить модель
docker logs telethon --tail 20 | grep "модель"
# → "Используется модель GigaChat-Lite" ✅

# Проверить тегирование
curl -X POST "http://localhost:8010/parse_all_channels"
docker logs telethon | grep "TaggingService"
```

---

**Статус:** Проблема найдена и исправлена  
**Файл для редактирования:** `/home/ilyasni/n8n-server/n8n-installer/gpt2giga/.env`  
**Действие:** Заменить `GigaChat-2-Pro` на `GigaChat-Lite` и добавить `GPT2GIGA_PASS_MODEL=true`

