# 🚀 Future Features - Groups Functionality

Идеи для расширения функционала Groups.

---

## ✅ Реализованные Features

### 🎤 Voice Commands - Голосовые команды (v3.3.0)

**Статус:** ✅ Реализовано  
**Дата:** 13 октября 2025

**Описание:**
Голосовые команды для `/ask` и `/search` через SaluteSpeech API.

**Документация:**
- [VOICE_COMMANDS.md](../features/voice/VOICE_COMMANDS.md)
- [VOICE_QUICK_START.md](../features/voice/VOICE_QUICK_START.md)
- [VOICE_IMPLEMENTATION_SUMMARY.md](../features/voice/VOICE_IMPLEMENTATION_SUMMARY.md)

**Возможности:**
- ✅ Транскрибация голосовых через SaluteSpeech API
- ✅ Кеширование в Redis (24h TTL)
- ✅ Premium/Enterprise only
- ✅ Лимиты: 50/999 запросов в день
- ✅ Максимум: 60 секунд на голосовое

---

## 📋 Planned Features

### 1. 🖼️ Vision AI - Анализ изображений

**Статус:** 📋 Planned (Priority #1)  
**Приоритет:** High (после успешного тестирования Voice)  
**Сложность:** Medium  
**Время:** 2-3 дня

**Описание:**
Автоматический анализ изображений в группах через Vision AI с включением в дайджесты.

**Детали:** [VISION_AI_FUTURE_FEATURE.md](implementation/VISION_AI_FUTURE_FEATURE.md)

**Ключевые моменты:**
- ⚠️ **GigaChat-Vision НЕ существует** как отдельная модель!
- ✅ Рекомендуется **Ollama LLaVA** (локальный, бесплатный)
- ✅ Альтернатива: **Google Gemini 2.0** (бесплатный tier)
- ✅ Premium: **GPT-4o Vision** (платный, лучшее качество)

**Что нужно:**
- Database: добавить `has_media`, `media_description` в GroupMention
- Service: расширить GroupDigestGenerator._analyze_image()
- n8n: обновить workflows для учета изображений
- Bot: параметр `--no-images` для отключения

---

### 2. 🎤 Voice Messages in Groups - Транскрипция голосовых

**Статус:** 📋 Planned  
**Приоритет:** Medium  
**Сложность:** Low (уже есть SaluteSpeech integration!)

**Описание:**
Автоматическая транскрипция голосовых сообщений в group дайджестах.

**Возможности:**
- ✅ SaluteSpeech уже интегрирован для bot commands
- ✅ Легко расширить на Groups monitoring
- Включать транскрипцию в дайджесты
- Поиск по содержимому голосовых

**Реализация:**
```python
# В group_digest_generator.py
if msg.voice:
    voice_bytes = await msg.download_media(bytes)
    transcription = await voice_service.transcribe(voice_bytes)
    message_data["text"] = f"🎤 {transcription}"
```

---

### 3. 📊 Advanced Analytics

**Статус:** 💡 Idea  
**Приоритет:** Low  
**Сложность:** High

**Описание:**
Расширенная аналитика активности в группах.

**Метрики:**
- Самые активные участники
- Пики активности (графики по времени)
- Сентимент-анализ диалогов (позитив/негатив)
- Топ-темы за неделю/месяц
- Network analysis (кто с кем чаще общается)

**Технологии:**
- PostgreSQL для хранения метрик
- Redis для real-time счетчиков
- Chart.js для визуализации (в Mini App)

---

### 4. 🔔 Smart Notifications

**Статус:** 💡 Idea  
**Приоритет:** Medium  
**Сложность:** Medium

**Описание:**
Умные уведомления на основе AI-анализа.

**Возможности:**
- Уведомлять только о важных упоминаниях (urgency: high)
- Группировка упоминаний (не спамить)
- Отложенные дайджесты (утром/вечером)
- Персонализация (ML на основе реакций пользователя)

---

### 5. 📱 Mini App для Groups

**Статус:** 💡 Idea  
**Приоритет:** Low  
**Сложность:** High

**Описание:**
Telegram Mini App для управления группами и просмотра аналитики.

**Функции:**
- Список групп с метриками
- История дайджестов
- Настройки уведомлений
- Графики активности
- Поиск по упоминаниям

---

### 6. 🔗 Integration с другими платформами

**Статус:** 💡 Idea  
**Приоритет:** Low  
**Сложность:** Medium

**Описание:**
Отправка дайджестов в другие платформы.

**Возможности:**
- Email дайджесты (ежедневные/еженедельные)
- Slack integration
- Discord webhooks
- Notion/Obsidian экспорт
- RSS feed для дайджестов

---

## 📊 Priority Matrix

```
High Impact │ 🎤 Voice    │ 🖼️ Vision AI │
            │             │              │
            ├─────────────┼──────────────┤
            │ 📱 Mini App │ 🔔 Smart     │
Low Impact  │             │ Notifications│
            └─────────────┴──────────────┘
              Low Effort    High Effort
```

**Рекомендуемый порядок:**
1. 🖼️ **Vision AI** (средний effort, высокий impact)
2. 🔔 **Smart Notifications** (средний effort, средний impact)
3. 🎤 **Voice Messages** (низкий effort, средний impact)
4. 📊 **Advanced Analytics** (высокий effort, средний impact)
5. 📱 **Mini App** (высокий effort, низкий impact)
6. 🔗 **Integrations** (средний effort, низкий impact)

---

## 💡 Quick Wins

**Что можно сделать быстро (<1 день):**

1. ✅ Добавить эмодзи статусы в дайджесты (😊 позитив, 😐 нейтрал, 😠 негатив)
2. ✅ Экспорт дайджеста в PDF/HTML
3. ✅ Поиск по истории дайджестов
4. ✅ Scheduled digests (автоматически каждое утро)
5. ✅ Webhook notifications в Discord/Slack

---

## 📝 Как добавить новую feature

1. Создайте документ в `docs/groups/implementation/FEATURE_NAME.md`
2. Добавьте в этот файл в секцию "Planned Features"
3. Обновите Priority Matrix
4. Когда начнете реализацию:
   - Создайте branch `feature/groups-vision-ai`
   - Следуйте этапам из документа
   - Обновите Cursor Rules если нужно

---

**Last Updated:** 13 октября 2025  
**Maintainer:** Telegram Bot Team

