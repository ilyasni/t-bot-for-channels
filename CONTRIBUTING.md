# Contributing to n8n Server + Telegram Parser

Спасибо за интерес к проекту! Это форк [n8n-installer](https://github.com/kossakovsky/n8n-installer) с дополнительной функциональностью Telegram Channel Parser + RAG System.

## 📋 Структура проекта

```
n8n-server/
├── n8n-installer/              # Корень проекта
│   ├── telethon/               # Telegram Channel Parser + RAG
│   ├── gpt2giga/               # GigaChat proxy
│   ├── scripts/                # Скрипты установки/обновления
│   ├── n8n/, flowise/, ...     # Оригинальные компоненты
│   └── docker-compose*.yml     # Docker конфигурация
```

## 🔧 Как внести изменения

### 1. Изменения в Telegram Parser (telethon)

**Следуйте Cursor Rules в `.cursor/rules`:**
- Документация в `telethon/docs/` (НЕ в корне!)
- Скрипты в `telethon/scripts/{setup|migrations|utils}/`
- Тесты в `telethon/tests/`
- Всегда используйте PostgreSQL (НЕ SQLite)
- Redis обязателен для shared state

**Workflow разработки:**

```bash
cd telethon

# Docker разработка
./scripts/utils/dev.sh rebuild  # Пересборка + restart
./scripts/utils/dev.sh logs     # Просмотр логов
./scripts/utils/dev.sh shell    # Bash в контейнере

# Локальная разработка
./scripts/utils/dev.sh setup    # Настройка venv
./scripts/utils/dev.sh local    # Запуск локально
./scripts/utils/dev.sh test     # Тесты

# Коммит
git add telethon/...
git commit -m "feat(telethon): Add new feature"
```

### 2. Изменения в основном стеке (n8n, flowise, etc.)

Следуйте структуре оригинального проекта [n8n-installer](https://github.com/kossakovsky/n8n-installer).

**При изменении docker-compose конфигурации:**
- Тестируйте на чистой установке
- Обновите `.env.example`
- Документируйте в README.md

### 3. Обновление документации

**Корневая документация (README.md):**
- Краткий обзор проекта
- Инструкции по установке
- Ссылки на детальную документацию

**Telegram Parser документация:**
- Всё в `telethon/docs/`
- Структура: `quickstart/`, `features/`, `migrations/`, `troubleshooting/`, `archive/`
- На русском языке
- Markdown с эмодзи

## 🧪 Тестирование

### Telegram Parser тесты

```bash
cd telethon
pytest tests/ -v
pytest tests/test_many_to_many.py
pytest tests/test_retention_system.py

# С покрытием
pytest tests/ --cov=. --cov-report=html
```

### Интеграционные тесты

```bash
# Полная пересборка и запуск
python3 start_services.py

# Проверка логов
docker compose -p localai logs -f

# Проверка healthchecks
docker ps --filter "name=localai" --format "table {{.Names}}\t{{.Status}}"
```

## 📝 Commit Guidelines

Используйте [Conventional Commits](https://www.conventionalcommits.org/):

```
feat(telethon): Add QR login system
fix(rag): Fix embeddings cache invalidation
docs(telethon): Update RAG quickstart guide
chore(docker): Update Qdrant to v1.7.0
```

**Scope примеры:**
- `telethon` - Telegram Parser
- `rag` - RAG System
- `docker` - Docker конфигурация
- `scripts` - Скрипты установки
- `docs` - Документация

## 🔄 Pull Request Process

1. **Fork проекта** (если нет доступа к основному репозиторию)
2. **Создайте ветку:**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Внесите изменения** и закоммитьте
4. **Запустите тесты:**
   ```bash
   cd telethon && pytest tests/
   ```
5. **Обновите документацию** если нужно
6. **Создайте PR** с описанием:
   - Что изменено
   - Зачем это нужно
   - Как тестировалось
   - Скриншоты (для UI изменений)

## 🐛 Reporting Bugs

**Для Telegram Parser:**
- Создайте issue с меткой `telethon`
- Приложите логи: `docker logs telethon`
- Укажите версию: `cat telethon/docs/quickstart/QUICK_START.md | grep "Версия"`

**Для оригинального стека:**
- Проверьте [upstream issues](https://github.com/kossakovsky/n8n-installer/issues)
- Создайте issue в этом репозитории

## 💡 Feature Requests

**Новые функции для Telegram Parser:**
1. Опишите use case
2. Проверьте что функция не дублирует существующую
3. Создайте issue с меткой `enhancement`

**Для основного стека:**
- Предложите в [upstream](https://github.com/kossakovsky/n8n-installer)

## 🔐 Security

**НЕ коммитьте:**
- `.env` файлы
- `*.session` файлы (Telegram)
- `*.db` файлы (базы данных)
- API ключи и credentials

**Если нашли уязвимость:**
- НЕ создавайте публичный issue
- Свяжитесь с мейнтейнерами напрямую

## 📜 License

Проект распространяется под Apache License 2.0. При добавлении кода:
- Убедитесь что у вас есть права на код
- Код будет под Apache 2.0
- Добавьте себя в Contributors (опционально)

## 🙏 Благодарности

- **Cole Medin** и team за оригинальный n8n-installer
- **n8n.io** за платформу
- Все open-source проекты в стеке

---

**Вопросы?** Создайте issue с меткой `question`.

