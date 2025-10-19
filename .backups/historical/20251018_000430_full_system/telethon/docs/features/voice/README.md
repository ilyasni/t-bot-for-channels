# 🎤 Voice Commands - Documentation

**Версия:** 3.3.0  
**Статус:** ✅ Реализовано  
**Доступ:** Premium/Enterprise only

---

## 📚 Документация

### 🚀 Quick Start (10 минут)

**Для новых пользователей:**
→ [VOICE_QUICK_START.md](VOICE_QUICK_START.md)

Пошаговая инструкция:
1. Получить SaluteSpeech credentials в Studio
2. Настроить .env
3. Выполнить миграцию БД
4. Перезапустить Docker
5. Протестировать

---

### 📖 Полное руководство

**Для детального изучения:**
→ [VOICE_COMMANDS.md](VOICE_COMMANDS.md)

Содержит:
- Обзор функционала
- Примеры использования
- Подписки и лимиты
- Технические детали
- Troubleshooting
- API flow
- Best practices

---

### 🔧 Implementation Summary

**Для разработчиков:**
→ [VOICE_IMPLEMENTATION_SUMMARY.md](VOICE_IMPLEMENTATION_SUMMARY.md)

Содержит:
- Список созданных файлов
- Обновленные файлы
- Code changes
- Deployment checklist
- Testing guide
- Metrics
- Rollback plan

---

## ⚡ Quick Reference

### Как использовать

```
1. Отправьте /ask или /search
2. Отправьте голосовое сообщение (до 60s)
3. Бот распознает и выполнит команду
```

### Доступность

| Tier | Voice | Limit/Day |
|------|-------|-----------|
| Free | ❌ | 0 |
| Trial | ✅ | 20 |
| Basic | ❌ | 0 |
| Premium | ✅ | 50 |
| Enterprise | ✅ | 999 |

### Технологии

- **SaluteSpeech API** - распознавание речи от Sber
- **Redis** - кеш транскрипций (24h)
- **OAuth2** - автоматическое обновление токенов
- **OGG/Opus** - формат Telegram voice

---

## 🔗 Related

**Code:**
- `telethon/voice_transcription_service.py` - SaluteSpeech клиент
- `telethon/bot.py` - Обработчик голосовых
- `telethon/subscription_config.py` - Лимиты

**Documentation:**
- [SaluteSpeech API](https://developers.sber.ru/docs/ru/salutespeech/overview)
- [Sber Studio](https://developers.sber.ru/studio)

**Future:**
- [FUTURE_FEATURES.md](../../groups/FUTURE_FEATURES.md) - Vision AI, Voice in Groups

---

## 🆘 Troubleshooting

**Проблемы:**
→ См. [VOICE_COMMANDS.md](VOICE_COMMANDS.md) → Troubleshooting

**Частые проблемы:**
- "Сервис недоступен" → проверьте credentials
- "Не распознало" → говорите четче
- "Лимит достигнут" → обновите подписку

---

**Version:** 3.3.0  
**Last Updated:** 13 октября 2025

