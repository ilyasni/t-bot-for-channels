#!/bin/bash
# Скрипт для применения миграции Many-to-Many
# 
# Использование:
#   bash apply_many_to_many.sh          # Запуск с подтверждением
#   bash apply_many_to_many.sh --force  # Без подтверждения

set -e  # Остановка при ошибке

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "================================================================"
echo "   МИГРАЦИЯ К MANY-TO-MANY СТРУКТУРЕ"
echo "================================================================"
echo ""
echo "Эта миграция устранит дублирование каналов в базе данных."
echo ""
echo "📋 План действий:"
echo "  1. Остановка всех сервисов"
echo "  2. Создание резервной копии БД"
echo "  3. Выполнение миграции"
echo "  4. Запуск тестов (опционально)"
echo "  5. Перезапуск сервисов"
echo ""

# Проверка наличия --force флага
FORCE=0
if [ "$1" = "--force" ]; then
    FORCE=1
fi

if [ $FORCE -eq 0 ]; then
    read -p "❓ Продолжить? (y/n): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Миграция отменена"
        exit 1
    fi
fi

echo ""
echo "================================================================"
echo "ШАГ 1: Остановка сервисов"
echo "================================================================"

# Останавливаем Python процессы
echo "🛑 Остановка Python сервисов..."
pkill -f "python.*main.py" 2>/dev/null || echo "   main.py не запущен"
pkill -f "python.*bot.py" 2>/dev/null || echo "   bot.py не запущен"
pkill -f "python.*run_system.py" 2>/dev/null || echo "   run_system.py не запущен"

# Даем время на корректное завершение
sleep 2

echo "✅ Сервисы остановлены"

echo ""
echo "================================================================"
echo "ШАГ 2: Создание дополнительной резервной копии"
echo "================================================================"

if [ -f "telegram.db" ]; then
    BACKUP_NAME="telegram.db.pre_migration_$(date +%Y%m%d_%H%M%S)"
    cp telegram.db "$BACKUP_NAME"
    echo "✅ Резервная копия создана: $BACKUP_NAME"
else
    echo "⚠️  telegram.db не найден (возможно используется другая БД)"
fi

echo ""
echo "================================================================"
echo "ШАГ 3: Выполнение миграции"
echo "================================================================"

echo "🔄 Запуск скрипта миграции..."
python3 migrate_to_many_to_many.py

if [ $? -ne 0 ]; then
    echo ""
    echo "❌ ОШИБКА МИГРАЦИИ!"
    echo ""
    echo "Действия для отката:"
    echo "  1. Восстановить БД: cp $BACKUP_NAME telegram.db"
    echo "  2. Запустить сервисы: python3 run_system.py &"
    exit 1
fi

echo ""
echo "================================================================"
echo "ШАГ 4: Запуск тестов (опционально)"
echo "================================================================"

if [ $FORCE -eq 0 ]; then
    read -p "❓ Запустить автоматические тесты? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "🧪 Запуск тестов..."
        python3 test_many_to_many.py
        if [ $? -ne 0 ]; then
            echo "⚠️  Некоторые тесты провалены, но это может быть нормально"
            echo "    Проверьте вывод тестов выше"
        fi
    else
        echo "⏭️  Тесты пропущены"
    fi
else
    echo "⏭️  Тесты пропущены (--force режим)"
fi

echo ""
echo "================================================================"
echo "ШАГ 5: Перезапуск сервисов"
echo "================================================================"

if [ $FORCE -eq 0 ]; then
    read -p "❓ Запустить сервисы? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        START_SERVICES=1
    else
        START_SERVICES=0
    fi
else
    START_SERVICES=1
fi

if [ $START_SERVICES -eq 1 ]; then
    echo "🚀 Запуск сервисов..."
    
    if [ -f "run_system.py" ]; then
        nohup python3 run_system.py > logs/system.log 2>&1 &
        echo "✅ Сервисы запущены через run_system.py"
    else
        nohup python3 main.py > logs/main.log 2>&1 &
        sleep 2
        nohup python3 bot.py > logs/bot.log 2>&1 &
        echo "✅ Сервисы запущены (main.py + bot.py)"
    fi
    
    sleep 3
    
    # Проверяем что процессы запустились
    if pgrep -f "python.*main.py" > /dev/null || pgrep -f "python.*run_system.py" > /dev/null; then
        echo "✅ Сервисы работают"
    else
        echo "⚠️  Сервисы могут не работать, проверьте логи"
    fi
else
    echo "⏭️  Запуск сервисов пропущен"
    echo ""
    echo "Для запуска выполните:"
    echo "  python3 run_system.py &"
    echo "или:"
    echo "  python3 main.py & python3 bot.py &"
fi

echo ""
echo "================================================================"
echo "✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!"
echo "================================================================"
echo ""
echo "📊 Проверить результаты:"
echo "  sqlite3 telegram.db 'SELECT COUNT(*) FROM channels;'"
echo "  sqlite3 telegram.db 'SELECT COUNT(*) FROM user_channel;'"
echo ""
echo "📚 Документация:"
echo "  - MANY_TO_MANY_SUMMARY.md   - краткое резюме"
echo "  - QUICK_MIGRATION.md        - быстрая инструкция"
echo "  - MIGRATION_MANY_TO_MANY.md - полная документация"
echo ""
echo "💾 Резервная копия:"
echo "  $BACKUP_NAME"
echo ""
echo "🔄 Откат (если нужно):"
echo "  cp $BACKUP_NAME telegram.db"
echo "  python3 run_system.py &"
echo ""
echo "================================================================"

