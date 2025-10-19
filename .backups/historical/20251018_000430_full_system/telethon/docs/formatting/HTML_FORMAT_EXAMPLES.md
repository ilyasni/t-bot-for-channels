# Примеры HTML форматирования в Telegram Bot

## 🎨 Базовые элементы

### 1. Жирный, курсив, подчеркнутый

**Input Markdown:**
```markdown
**Жирный текст**
*Курсив*
__Подчеркнутый__
~~Зачеркнутый~~
```

**Output HTML:**
```html
<b>Жирный текст</b>
<i>Курсив</i>
<u>Подчеркнутый</u>
<s>Зачеркнутый</s>
```

**Как выглядит в Telegram:**
> **Жирный текст**  
> *Курсив*  
> <u>Подчеркнутый</u>  
> ~~Зачеркнутый~~

---

## 📝 Цитаты (Blockquote)

### 2. Простая цитата

**Input Markdown:**
```markdown
> Это цитата
> Многострочная цитата
```

**Output HTML:**
```html
<blockquote>Это цитата
Многострочная цитата</blockquote>
```

**Как выглядит в Telegram:**
> Серый блок слева от текста, как в email клиентах

---

### 3. Раскрывающаяся цитата (Expandable)

**Input (через функцию):**
```python
from telegram_formatter import format_rag_answer

answer = "Python - язык программирования"
sources = [
    {"url": "https://t.me/python/123", "channel_username": "python_news", "posted_at": "2024-01-15"}
]

formatted = format_rag_answer(answer, sources)
```

**Output HTML:**
```html
Python - язык программирования

<blockquote expandable>📚 <b>Источники:</b>
1. <a href="https://t.me/python/123">@python_news</a> <i>(2024-01-15)</i>
</blockquote>
```

**Как выглядит в Telegram:**
```
Python - язык программирования

[▼ Раскрыть] 📚 Источники:     ← Клик показывает содержимое
```

После клика:
```
Python - язык программирования

[▲ Скрыть] 📚 Источники:
1. @python_news (2024-01-15)   ← Кликабельная ссылка
```

---

## 💬 Спойлеры

### 4. Скрытый текст

**Input Markdown:**
```markdown
Обычный текст ||спойлер|| еще текст
```

**Output HTML:**
```html
Обычный текст <tg-spoiler>спойлер</tg-spoiler> еще текст
```

**Как выглядит в Telegram:**
```
Обычный текст [■■■■■■] еще текст  ← Размытый текст
```

После клика:
```
Обычный текст спойлер еще текст   ← Видимый текст
```

---

## 💻 Код

### 5. Inline код

**Input Markdown:**
```markdown
Используй команду `docker ps`
```

**Output HTML:**
```html
Используй команду <code>docker ps</code>
```

**Как выглядит в Telegram:**
> Используй команду `docker ps` ← Серый фон, моноширинный шрифт

---

### 6. Code block с подсветкой

**Input Markdown:**
````markdown
```python
def hello():
    print("world")
```
````

**Output HTML:**
```html
<pre><code class="language-python">def hello():
    print("world")</code></pre>
```

**Как выглядит в Telegram:**
```
┌─────────────────┐
│ def hello():    │  ← Моноширинный шрифт
│     print("w")  │  ← Серый блок
└─────────────────┘
    Python          ← Метка языка снизу
```

---

## 📊 Практические примеры

### 7. RAG ответ с источниками

```python
from telegram_formatter import format_rag_answer

answer = """
**Python** - это высокоуровневый *язык программирования*.

Основные особенности:
- Простой синтаксис
- Динамическая типизация
- Большая экосистема

Используется для:
1. Веб-разработки
2. Data Science
3. Автоматизации
"""

sources = [
    {
        "url": "https://t.me/python_news/456",
        "channel_username": "python_news",
        "posted_at": "2024-01-15",
        "excerpt": "Python - один из самых популярных языков..."
    },
    {
        "url": "https://t.me/dev_channel/789",
        "channel_username": "dev_channel",
        "posted_at": "2024-01-10"
    }
]

result = format_rag_answer(answer, sources)
```

**Результат в Telegram:**

```
💡 Ответ:

Python - это высокоуровневый язык программирования.

Основные особенности:
• Простой синтаксис
• Динамическая типизация
• Большая экосистема

Используется для:
1. Веб-разработки
2. Data Science
3. Автоматизации

[▼ Раскрыть] 📚 Источники:
```

После раскрытия:
```
[▲ Скрыть] 📚 Источники:
1. @python_news (2024-01-15)
   Python - один из самых популярных языков...
2. @dev_channel (2024-01-10)
```

---

### 8. Длинный дайджест

```python
from telegram_formatter import format_long_digest

digest = """
# Новости за неделю

## AI & ML
Вышла новая версия PyTorch 2.0 с улучшенной производительностью.
OpenAI анонсировала GPT-5 с поддержкой мультимодальности.
Google представила новую модель Gemini Ultra.

## Web Development
React 19 добавил Server Components.
Next.js 14 улучшил производительность на 50%.
Vue 4 в разработке с новой архитектурой.

## DevOps
Kubernetes 1.29 стабилизировал новые API.
Docker добавил поддержку WASM.
Terraform 1.7 с новыми провайдерами.
""" * 3  # Делаем длинным

result = format_long_digest(digest, max_visible=500)
```

**Результат в Telegram:**

```
Новости за неделю

AI & ML
Вышла новая версия PyTorch 2.0 с улучшенной производительностью.
OpenAI анонсировала GPT-5 с поддержкой мультимодальности.
Google представила новую модель Gemini Ultra.

Web Development
React 19 добавил Server Components.
Next.js 14 улучшил производительность на 50%.
Vue 4 в разработке с...

[▼ Раскрыть]
```

После раскрытия показывается остальной текст.

---

### 9. Groups упоминание

```python
from telegram_formatter import format_mention_for_telegram

analysis = {
    "urgency": "urgent",
    "context": "Обсуждается критический баг в продакшене. Пользователи не могут войти в систему.",
    "mention_reason": "Нужна срочная помощь с исправлением auth сервиса",
    "key_points": [
        "Auth service падает с 500 ошибкой",
        "Затронуты 1000+ пользователей",
        "Нужен hotfix в течение часа"
    ]
}

result = format_mention_for_telegram(
    analysis, 
    "DevOps Chat", 
    "https://t.me/c/123456/789"
)
```

**Результат в Telegram:**

```
🔴 Упоминание в группе

Группа: DevOps Chat

Контекст:
┃ Обсуждается критический баг в продакшене. 
┃ Пользователи не могут войти в систему.

Почему упомянули: Нужна срочная помощь с исправлением auth сервиса

Ключевые моменты:
• Auth service падает с 500 ошибкой
• Затронуты 1000+ пользователей
• Нужен hotfix в течение часа

📬 Перейти к сообщению

Срочность: URGENT • 15:30
```

---

### 10. AI Дайджест

**Результат в Telegram:**

```
🤖 AI-Дайджест
Период: 01.10.2024 - 07.10.2024
Тем: 3

💰 1. Криптовалюты
Постов проанализировано: 45

Bitcoin достиг нового максимума в 2024 году. Ethereum 
обновил протокол с улучшенной масштабируемостью. 
Регуляторы обсуждают новые правила для DeFi.

[▼ Раскрыть] 📚 Источники:

🚗 2. Автомобили
Постов проанализировано: 32

Tesla представила новую модель с автопилотом 4.0.
BMW анонсировала электрический седан i7. Китайские
производители увеличили экспорт EV на 40%.

[▼ Раскрыть] 📚 Источники:

──────────────
Дайджест сгенерирован AI (GigaChat) • 07.10.2024 18:00
```

---

## 🎯 Best Practices

### ✅ Правильно

```python
# 1. Динамический контент всегда через функции
from telegram_formatter import markdownify, format_rag_answer

user_input = "Python & ML"
safe_text = markdownify(user_input)  # Экранирует &

# 2. RAG ответы с источниками
formatted = format_rag_answer(answer, sources)

# 3. Длинный контент
formatted = format_long_digest(long_text, max_visible=500)
```

### ❌ Неправильно

```python
# 1. НЕ отправлять динамический текст без обработки
await bot.send_message(chat_id, user_input, parse_mode='HTML')  # ОПАСНО!

# 2. НЕ забывать про экранирование
text = f"<b>{user_input}</b>"  # Если user_input содержит <, будет ошибка

# 3. НЕ смешивать Markdown и HTML
text = "**bold** <i>italic</i>"  # Не будет работать
```

---

## 📱 Как тестировать в Telegram

### 1. Отправить тестовое сообщение

```python
import asyncio
from telegram import Bot

async def test_formatting():
    bot = Bot(token="YOUR_BOT_TOKEN")
    
    test_html = """
<b>Жирный</b> и <i>курсив</i>

<blockquote>Это цитата</blockquote>

<blockquote expandable>Раскрывающийся блок
С несколькими строками
Скрыто по умолчанию</blockquote>

Спойлер: <tg-spoiler>секретный текст</tg-spoiler>

<code>inline code</code>

<pre><code class="language-python">
def test():
    print("hello")
</code></pre>
"""
    
    await bot.send_message(
        chat_id=YOUR_CHAT_ID,
        text=test_html,
        parse_mode='HTML'
    )

asyncio.run(test_formatting())
```

### 2. Проверить expandable

Кликнуть на блок в Telegram - должен раскрыться/скрыться

### 3. Проверить спойлер

Кликнуть на размытый текст - должен стать видимым

### 4. Проверить code block

Должен быть:
- Моноширинный шрифт
- Серый фон
- Метка языка снизу (если указан)

---

## 🔧 Troubleshooting

### Проблема: "Can't parse entities"

**Причина:** Некорректный HTML или не экранированные спецсимволы

**Решение:**
```python
from telegram_formatter import markdownify

# Всегда используйте markdownify для динамического контента
safe_text = markdownify(user_text)
```

### Проблема: Expandable не раскрывается

**Причина:** Неправильный атрибут

**Решение:**
```html
<!-- ❌ Неправильно -->
<blockquote expand>text</blockquote>

<!-- ✅ Правильно -->
<blockquote expandable>text</blockquote>
```

### Проблема: Code block без подсветки

**Причина:** Неправильный формат

**Решение:**
```html
<!-- ❌ Неправильно -->
<pre language="python">code</pre>

<!-- ✅ Правильно -->
<pre><code class="language-python">code</code></pre>
```

---

## 📚 Дополнительные ресурсы

- [Telegram Bot API - HTML Style](https://core.telegram.org/bots/api#html-style)
- [Telegram Bot API - Formatting Options](https://core.telegram.org/bots/api#formatting-options)
- Исходный код: `telethon/telegram_formatter.py`
- Тесты: `telethon/tests/test_telegram_formatter.py`

