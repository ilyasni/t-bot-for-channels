# 🖼️ Vision AI для анализа изображений в Groups - Future Feature

**Статус:** 📋 Planned (не реализовано)  
**Дата создания:** 13 октября 2025  
**Приоритет:** Medium  
**Сложность:** Medium

---

## 🎯 Описание идеи

Расширить функционал Groups дайджестов **автоматическим анализом изображений** через Vision AI.

**Что будет:**
- 📸 Автоматическое распознавание изображений в группах
- 🤖 AI-описание содержимого картинок
- 📊 Включение информации об изображениях в дайджесты
- 🔍 Контекстный анализ (связь изображения с обсуждением)

**Use Case:**
```
Пользователь: /group_digest 6

Дайджест:
📊 Группа: Design Team
Период: 6 hours
Сообщений: 45
Изображений: 12 📸

Темы:
• Редизайн главного экрана
• Новая цветовая палитра

Изображения:
📸 @designer1: Макет главного экрана с карточками продуктов
📸 @designer2: Палитра в синих тонах (#1E40AF, #3B82F6)
📸 @developer1: Скриншот бага с красной кнопкой

Резюме: Команда утвердила новый дизайн...
```

---

## ⚠️ Важное уточнение

### ❌ GigaChat-Vision НЕ существует

**Ошибка в первоначальном предложении:**
```python
# ❌ НЕПРАВИЛЬНО - такой модели нет!
"model": "GigaChat-Vision"  # NO! Doesn't exist!
```

**Факты:**
- GigaChat **умеет** распознавать изображения с октября 2024 ([источник](https://consult-cct.ru/gigachat-nauchilsya-raspoznavat-izobrazheniya))
- Распознает: текст (печатный/рукописный), формулы, графики, таблицы
- Работает через **обычную модель GigaChat** + API "Обработка файлов"
- Документация: [developers.sber.ru/docs/ru/gigachat/guides](https://developers.sber.ru/docs/ru/gigachat/guides/main) → "Обработка файлов"

---

## ✅ Рабочие варианты Vision AI

### Вариант 1: Ollama LLaVA (РЕКОМЕНДУЕТСЯ)

**Преимущества:**
- ✅ Локальный (нет затрат на API)
- ✅ Бесплатный
- ✅ Ollama уже есть в docker-compose
- ✅ Хорошее качество
- ✅ Приватность (данные не уходят в облако)

**Недостатки:**
- ⚠️ Требует GPU для быстрой работы
- ⚠️ Медленнее облачных решений (30-60 сек)

**Код:**
```python
async def _analyze_image_ollama(self, base64_image: str) -> str:
    """Анализ через Ollama LLaVA (локальный)"""
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            "http://ollama:11434/api/generate",
            json={
                "model": "llava",
                "prompt": "Describe this image briefly in Russian (1-2 sentences)",
                "images": [base64_image],
                "stream": False
            }
        )
        
        return response.json().get("response", "[изображение]")
```

**Установка:**
```bash
# Скачать модель LLaVA
docker exec ollama ollama pull llava

# Проверить
docker exec ollama ollama list | grep llava
```

---

### Вариант 2: Google Gemini 2.0 Flash

**Преимущества:**
- ✅ Бесплатный tier (15 requests/min)
- ✅ Быстрый (2-5 сек)
- ✅ Хорошо работает с русским
- ✅ OpenRouter уже используется в проекте

**Недостатки:**
- ⚠️ Требует интернет
- ⚠️ Rate limits

**Код:**
```python
async def _analyze_image_gemini(self, base64_image: str) -> str:
    """Анализ через Google Gemini (OpenRouter)"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "google/gemini-2.0-flash-exp:free",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Опиши изображение кратко на русском (1-2 предложения)"},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150
            }
        )
        
        return response.json()["choices"][0]["message"]["content"]
```

---

### Вариант 3: OpenAI GPT-4o

**Преимущества:**
- ✅ Лучшее качество
- ✅ Быстрый
- ✅ Стабильный

**Недостатки:**
- ❌ Платный (~$0.01 за изображение)
- ⚠️ Требует интернет

**Код:**
```python
async def _analyze_image_openai(self, base64_image: str) -> str:
    """Анализ через GPT-4o Vision (OpenRouter)"""
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
                "Content-Type": "application/json"
            },
            json={
                "model": "openai/gpt-4o",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Опиши кратко что на изображении (1-2 предложения на русском)"
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 150
            }
        )
        
        return response.json()["choices"][0]["message"]["content"]
```

---

### Вариант 4: GigaChat (через API "Обработка файлов")

**Статус:** Требует проверки в gpt2giga-proxy

**Предполагаемый код:**
```python
async def _analyze_image_gigachat(self, photo_bytes: bytes) -> str:
    """Анализ через GigaChat API (если поддерживается proxy)"""
    
    # 1. Загрузить файл
    async with httpx.AsyncClient(timeout=30.0) as client:
        files = {'file': ('image.jpg', photo_bytes, 'image/jpeg')}
        
        upload_response = await client.post(
            "http://gpt2giga-proxy:8090/v1/files",
            files=files
        )
        
        file_id = upload_response.json()['id']
        
        # 2. Использовать в чате
        chat_response = await client.post(
            "http://gpt2giga-proxy:8090/v1/chat/completions",
            json={
                "model": "GigaChat",  # Обычная модель
                "messages": [
                    {
                        "role": "user",
                        "content": "Опиши что на изображении кратко",
                        "attachments": [file_id]  # Файл через attachments
                    }
                ]
            }
        )
        
        return chat_response.json()["choices"][0]["message"]["content"]
```

**Требует:**
- Проверить версию gpt2giga-proxy
- Проверить поддержку `/v1/files` endpoint
- Протестировать с реальным изображением

---

## 🏗️ Архитектура реализации

### 1. Database Changes

```python
# models.py

class GroupMention(Base):
    # ... existing fields ...
    
    # 🆕 Media fields
    has_media = Column(Boolean, default=False)
    media_type = Column(String, nullable=True)  # photo, video, document
    media_description = Column(String, nullable=True)  # AI description
    media_analyzed = Column(Boolean, default=False)

class Group(Base):
    # ... existing fields ...
    
    # 🆕 Vision AI settings
    vision_ai_enabled = Column(Boolean, default=False)
    vision_ai_provider = Column(String, default="ollama")  # ollama, gemini, openai
```

### 2. Service Layer

```python
# group_digest_generator.py

class GroupDigestGenerator:
    
    async def generate_digest(
        self,
        user_id: int,
        group_id: int,
        messages: List[Message],
        hours: int = 24,
        analyze_images: bool = True  # 🆕 Параметр
    ) -> Dict[str, Any]:
        
        formatted_messages = []
        images_analyzed = 0
        
        for msg in messages:
            message_data = {
                "username": username,
                "text": msg.text or "",
                "date": msg.date.isoformat(),
                "media": None  # 🆕 Поле для медиа
            }
            
            # 🆕 Анализ изображений
            if analyze_images and msg.media:
                if isinstance(msg.media, MessageMediaPhoto):
                    try:
                        # Download image
                        photo_bytes = await msg.download_media(bytes)
                        
                        # Convert to base64
                        import base64
                        photo_base64 = base64.b64encode(photo_bytes).decode()
                        
                        # Check size limit
                        size_mb = len(photo_bytes) / (1024 * 1024)
                        max_size = float(os.getenv("VISION_MAX_SIZE_MB", "5"))
                        
                        if size_mb <= max_size:
                            # Analyze via Vision AI
                            description = await self._analyze_image(photo_base64)
                            
                            message_data["media"] = {
                                "type": "photo",
                                "description": description,
                                "size_mb": round(size_mb, 2)
                            }
                            
                            images_analyzed += 1
                        else:
                            message_data["media"] = {
                                "type": "photo",
                                "description": "[изображение слишком большое]"
                            }
                    
                    except Exception as e:
                        logger.error(f"❌ Ошибка обработки изображения: {e}")
                        message_data["media"] = {
                            "type": "photo",
                            "description": "[ошибка обработки]"
                        }
            
            formatted_messages.append(message_data)
        
        logger.info(f"📸 Проанализировано изображений: {images_analyzed}")
        
        # Send to n8n...
    
    async def _analyze_image(self, base64_image: str) -> str:
        """
        Анализ изображения через доступные Vision AI
        
        Cascading fallback:
        1. Ollama LLaVA (локальный)
        2. Google Gemini (бесплатный)
        3. GPT-4o (платный)
        """
        vision_provider = os.getenv("VISION_AI_PROVIDER", "ollama")
        
        try:
            if vision_provider == "ollama":
                return await self._analyze_image_ollama(base64_image)
            elif vision_provider == "gemini":
                return await self._analyze_image_gemini(base64_image)
            elif vision_provider == "openai":
                return await self._analyze_image_openai(base64_image)
            else:
                # Fallback to Ollama
                return await self._analyze_image_ollama(base64_image)
        
        except Exception as e:
            logger.error(f"❌ Vision AI error ({vision_provider}): {e}")
            
            # Cascading fallback
            if vision_provider != "gemini":
                try:
                    return await self._analyze_image_gemini(base64_image)
                except:
                    pass
            
            return "[изображение]"  # Final fallback
```

### 3. n8n Workflow Updates

```javascript
// group_digest_orchestrator.json

// В узле "Prepare Prompts" добавить обработку медиа
const messages = $json.messages;
const textMessages = [];
const imageMessages = [];

messages.forEach(msg => {
    if (msg.text) {
        textMessages.push(msg);
    }
    
    if (msg.media && msg.media.description) {
        imageMessages.push({
            sender: msg.username,
            description: msg.media.description,
            type: msg.media.type
        });
    }
});

// В промпт для Agent 1 (Topic Extractor)
const topicPrompt = `
Извлеки темы из диалога.

Текстовые сообщения: ${textMessages.length}
Изображения: ${imageMessages.length}

${imageMessages.length > 0 ? `
Описания изображений:
${imageMessages.map(img => `- @${img.sender}: ${img.description}`).join('\n')}
` : ''}

Текст диалога:
${textMessages.map(m => `@${m.username}: ${m.text}`).join('\n')}
`;

// В Agent 4 (Aggregator) добавить секцию images
const finalDigest = {
    topics: topics,
    speakers_summary: speakers,
    overall_summary: summary,
    images_count: imageMessages.length,
    images_summary: imageMessages.length > 0 
        ? imageMessages.map(img => `📸 @${img.sender}: ${img.description}`).join('\n')
        : null,
    message_count: messages.length,
    period: `${hours} hours`
};
```

### 4. Bot Command Updates

```python
# bot.py

async def group_digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/group_digest [hours] [--no-images]"""
    
    args = context.args
    hours = 24
    analyze_images = True  # Default
    
    if args:
        hours = int(args[0])
        
        # Опция отключения анализа изображений
        if "--no-images" in args:
            analyze_images = False
    
    # Generate digest with images
    digest = await group_digest_generator.generate_digest(
        user_id=user.id,
        group_id=group.id,
        messages=messages,
        hours=hours,
        analyze_images=analyze_images  # 🆕
    )
    
    # Format with images
    text = format_digest_with_images(digest)
    
    await update.message.reply_text(text, parse_mode="MarkdownV2")
```

---

## 🔧 Environment Variables

```bash
# .env

# Vision AI Configuration
VISION_AI_ENABLED=true
VISION_AI_PROVIDER=ollama  # ollama, gemini, openai, gigachat
VISION_MAX_SIZE_MB=5
VISION_TIMEOUT=60

# Caching
VISION_CACHE_TTL=604800  # 7 days (images don't change)

# Subscription limits
VISION_AI_FREE_TIER=false  # Only premium+
VISION_MAX_IMAGES_PER_DIGEST=20
```

---

## 📊 Subscription Tiers Update

```python
# subscription_config.py

SUBSCRIPTION_TIERS = {
    "free": {
        # ... existing ...
        "vision_ai_enabled": False,
        "max_images_per_digest": 0
    },
    "trial": {
        # ... existing ...
        "vision_ai_enabled": True,
        "max_images_per_digest": 10
    },
    "basic": {
        # ... existing ...
        "vision_ai_enabled": True,
        "max_images_per_digest": 20
    },
    "premium": {
        # ... existing ...
        "vision_ai_enabled": True,
        "max_images_per_digest": 50
    },
    "enterprise": {
        # ... existing ...
        "vision_ai_enabled": True,
        "max_images_per_digest": 999
    }
}
```

---

## 🎯 Этапы реализации

### Phase 1: Backend (Python)

1. ✅ Обновить `models.py`:
   - Добавить `has_media`, `media_description` в GroupMention
   - Добавить `vision_ai_enabled` в GroupSettings

2. ✅ Создать миграцию:
   ```bash
   telethon/scripts/migrations/add_vision_ai_support.py
   ```

3. ✅ Расширить `GroupDigestGenerator`:
   - Добавить `_analyze_image()` метод
   - Добавить поддержку `MessageMediaPhoto`
   - Добавить кеширование описаний в Redis

4. ✅ Обновить subscription limits:
   - Добавить `vision_ai_enabled` в тарифы
   - Добавить проверку лимитов

### Phase 2: n8n Workflows

1. ✅ Обновить `group_digest_orchestrator.json`:
   - Принимать `media` в messages
   - Передавать descriptions в агентов

2. ✅ Обновить Agent 1 (Topic Extractor):
   - Учитывать описания изображений при извлечении тем

3. ✅ Обновить Agent 4 (Aggregator):
   - Добавить секцию `images_summary` в финальный дайджест

### Phase 3: Bot Commands

1. ✅ Обновить `/group_digest`:
   - Добавить параметр `--no-images`
   - Показывать количество изображений

2. ✅ Обновить `/group_settings`:
   - Добавить настройку `vision_ai_enabled`

3. ✅ Обновить форматирование:
   - Включить информацию об изображениях в дайджест

### Phase 4: Testing

1. ✅ Установить Ollama LLaVA:
   ```bash
   docker exec ollama ollama pull llava
   ```

2. ✅ Протестировать анализ:
   ```bash
   curl -X POST http://ollama:11434/api/generate \
     -d '{"model":"llava","prompt":"Describe","images":["base64..."]}'
   ```

3. ✅ Интеграционные тесты:
   - Отправить изображение в тестовую группу
   - Запустить `/group_digest`
   - Проверить что описание включено

---

## 💰 Стоимость и производительность

### Ollama LLaVA (рекомендуется)

- **Стоимость:** $0 (локальный)
- **Скорость:** 30-60 сек на изображение (CPU), 2-5 сек (GPU)
- **Качество:** 7/10
- **Приватность:** ✅ Полная (данные не уходят)

### Google Gemini 2.0 Flash

- **Стоимость:** $0 (бесплатный tier: 15 req/min)
- **Скорость:** 2-5 сек
- **Качество:** 9/10
- **Приватность:** ⚠️ Данные уходят в Google

### GPT-4o Vision

- **Стоимость:** ~$0.01 за изображение
- **Скорость:** 1-3 сек
- **Качество:** 10/10
- **Приватность:** ⚠️ Данные уходят в OpenAI

### Рекомендация

**Для начала:** Ollama LLaVA (бесплатный, локальный)  
**Для production:** Google Gemini (быстрый, бесплатный tier)  
**Для качества:** GPT-4o (платный, но лучший)

---

## 🚨 Потенциальные проблемы

### 1. Размер изображений

**Проблема:** Telegram может отправлять изображения до 20 МБ

**Решение:**
```python
# Ограничить размер
max_size = float(os.getenv("VISION_MAX_SIZE_MB", "5"))
if size_mb > max_size:
    return "[изображение слишком большое]"
```

### 2. Скорость обработки

**Проблема:** Анализ 10 изображений = 30-60 сек задержка

**Решение:**
```python
# Обрабатывать асинхронно в фоне
background_tasks.add_task(
    analyze_and_cache_images,
    messages
)

# В дайджесте использовать кешированные описания
```

### 3. Rate Limits (для Gemini/GPT-4o)

**Проблема:** Gemini free tier = 15 req/min

**Решение:**
```python
# Лимитировать количество изображений
max_images = tier.get("max_images_per_digest", 10)
images_to_analyze = messages_with_photos[:max_images]
```

### 4. Стоимость (для GPT-4o)

**Проблема:** 100 изображений/день = $1/день = $30/месяц

**Решение:**
```python
# Vision AI только для premium/enterprise
if user.subscription_type not in ["premium", "enterprise"]:
    analyze_images = False
```

---

## 🎓 Рекомендации

### Для MVP (минимальная реализация)

1. ✅ Используйте **Ollama LLaVA** (бесплатный)
2. ✅ Лимитируйте до **10 изображений** на дайджест
3. ✅ **Кешируйте** описания в Redis (7 дней TTL)
4. ✅ Делайте **background processing** (не блокируйте бота)
5. ✅ Добавьте параметр `--no-images` для отключения

### Для Production

1. ✅ **Google Gemini** как primary (быстро + бесплатно)
2. ✅ **Ollama LLaVA** как fallback (если Gemini недоступен)
3. ✅ **GPT-4o** для enterprise tier (лучшее качество)
4. ✅ Мониторинг затрат и rate limits
5. ✅ A/B тестирование качества разных провайдеров

---

## 📚 Ссылки

**GigaChat:**
- [Руководства GigaChat API](https://developers.sber.ru/docs/ru/gigachat/guides/main)
- [Обработка файлов](https://developers.sber.ru/docs/ru/gigachat/guides/main) - секция "Обработка файлов"
- [GigaChat научился распознавать изображения](https://consult-cct.ru/gigachat-nauchilsya-raspoznavat-izobrazheniya)

**Vision AI:**
- [Ollama LLaVA](https://ollama.com/library/llava)
- [Google Gemini Vision](https://ai.google.dev/gemini-api/docs/vision)
- [GPT-4 Vision](https://platform.openai.com/docs/guides/vision)
- [OpenRouter Pricing](https://openrouter.ai/models)

**Related:**
- [Telegram Bot API - Photos](https://core.telegram.org/bots/api#photosize)
- [Telethon - MessageMediaPhoto](https://docs.telethon.dev/en/stable/modules/types.html#telethon.tl.types.MessageMediaPhoto)

---

## ✅ Когда реализовывать

**Триггеры для начала:**
- Пользователи запрашивают анализ изображений
- Группы активно используют визуальный контент (дизайн, макеты)
- Появляется budget для GPT-4o Vision
- Ollama LLaVA протестирован и работает хорошо

**Сначала сделать:**
- Убедиться что основной функционал Groups стабилен
- Протестировать Ollama LLaVA на реальных изображениях
- Оценить скорость и качество
- Посчитать стоимость для разных провайдеров

---

**Статус:** 📋 Documented for future implementation  
**Next Step:** Протестировать Ollama LLaVA на одном изображении  
**Estimated Effort:** 2-3 дня разработки + 1 день тестирования

