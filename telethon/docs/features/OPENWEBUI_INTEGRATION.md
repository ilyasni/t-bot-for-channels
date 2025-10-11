# 🌐 Интеграция с Open WebUI

**Статус:** Опциональная интеграция  
**Сложность:** Средняя  
**Требуется:** Open WebUI, n8n, n8n_pipe.py

---

## 📋 Что такое Open WebUI интеграция?

Open WebUI - это ChatGPT-like веб-интерфейс для взаимодействия с AI-моделями.

**n8n_pipe.py** (в корне проекта) - это интеграционный модуль, который позволяет использовать n8n workflows как "pipe" (конвейер обработки) в Open WebUI.

---

## 🔗 Архитектура интеграции

### Текущая архитектура (Telegram Bot):
```
Telegram Bot → Telethon API → RAG Service → Ответ
```

### С Open WebUI (опционально):
```
Open WebUI → n8n_pipe → n8n Workflow → Telethon API → RAG Service → Ответ
```

---

## 🎯 Зачем это нужно?

### Use cases:

1. **Веб-интерфейс для RAG:**
   - Вместо Telegram можно использовать веб-чат
   - Удобно для desktop использования
   - Можно встроить в сайт

2. **n8n как middleware:**
   - Дополнительная обработка перед RAG
   - Комбинация нескольких источников
   - Логирование и аналитика

3. **Расширенная функциональность:**
   - История диалогов в Open WebUI
   - Markdown и code highlighting
   - Загрузка файлов
   - Поддержка разных моделей

---

## 🛠️ Как настроить (опционально)

### Шаг 1: Создать n8n workflow

**Webhook Trigger:**
- URL: `https://n8n.produman.studio/webhook/telegram-rag`
- Method: POST
- Response: JSON

**Workflow:**
```
1. Webhook Trigger
   ↓
2. HTTP Request (Telethon API)
   - GET http://telethon:8010/users/{user_id}/posts
   ↓
3. HTTP Request (RAG Service)
   - POST http://rag-service:8020/rag/query
   - Body: {"query": "{{ $json.chatInput }}", "user_id": ...}
   ↓
4. Response
   - Return: {{ $json.answer }}
```

### Шаг 2: Настроить n8n_pipe в Open WebUI

**Файл:** `/home/ilyasni/n8n-server/n8n-installer/n8n_pipe.py`

**Настройки (Valves):**
```python
n8n_url = "https://n8n.produman.studio/webhook/telegram-rag"
n8n_bearer_token = "your_n8n_webhook_token"
input_field = "query"
response_field = "answer"
```

### Шаг 3: Загрузить в Open WebUI

1. Откройте Open WebUI
2. Settings → Functions
3. Upload `n8n_pipe.py`
4. Configure Valves
5. Сохраните

### Шаг 4: Использовать

1. В Open WebUI выберите модель "n8n Pipe"
2. Задайте вопрос
3. n8n вызовет ваш RAG service
4. Получите ответ

---

## 📊 Сравнение подходов

### Telegram Bot (текущая реализация):
✅ Мобильный доступ  
✅ Push-уведомления  
✅ Простая настройка  
✅ Удобно для пользователей Telegram  
✅ Уже реализовано и работает  
❌ Только в Telegram  

### Open WebUI + n8n_pipe:
✅ Веб-интерфейс  
✅ Desktop доступ  
✅ Красивый UI  
✅ История чатов  
✅ Можно встроить на сайт  
❌ Требует дополнительную настройку  
❌ Требует n8n workflow  

---

## 💡 Рекомендация

### Для большинства пользователей:
**✅ Используйте Telegram Bot**
- Уже работает
- Все RAG команды реализованы
- Не требует дополнительной настройки

### Если нужен веб-интерфейс:
**⚙️ Добавьте Open WebUI интеграцию**
- Создайте n8n workflow
- Настройте n8n_pipe
- Используйте оба подхода параллельно

---

## 🔗 Полезные ссылки

**Open WebUI:**
- Сайт: https://openwebui.com/
- n8n_pipe: https://openwebui.com/f/coleam/n8n_pipe/

**n8n:**
- Документация: https://docs.n8n.io/
- Ваш instance: https://n8n.produman.studio

**Автор n8n_pipe:**
- Cole Medin: https://www.youtube.com/@ColeMedin

---

## 📝 Примечание

Эта интеграция **опциональна**.

Telegram Bot уже имеет все RAG команды:
- `/ask` - RAG-поиск
- `/search` - Гибридный поиск
- `/recommend` - Рекомендации
- `/digest` - AI-дайджесты

Open WebUI - это просто альтернативный интерфейс, если нужен веб-доступ.

---

**Версия:** 1.0  
**Статус:** Опциональная интеграция  
**Приоритет:** Низкий (уже есть Telegram Bot)

