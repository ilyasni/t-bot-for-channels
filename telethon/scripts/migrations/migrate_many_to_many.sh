#!/bin/bash
#
# Миграция к Many-to-Many структуре
# Аналог docker-run.sh и других скриптов из проекта
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Загрузка утилит
if [ -f "utils_migration.sh" ]; then
    source utils_migration.sh
else
    echo "❌ Файл utils_migration.sh не найден!"
    exit 1
fi

# Заголовок
echo ""
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   🔄 МИГРАЦИЯ К MANY-TO-MANY СТРУКТУРЕ                         ║"
echo "║   Устранение дублирования каналов в базе данных               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

log_info "Переход от структуры One-to-Many к Many-to-Many"
echo ""

# Проверка флага --force
FORCE=0
DRY_RUN=0
SKIP_TESTS=0

while [[ $# -gt 0 ]]; do
    case $1 in
        --force)
            FORCE=1
            shift
            ;;
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --skip-tests)
            SKIP_TESTS=1
            shift
            ;;
        --help)
            echo "Использование: $0 [ОПЦИИ]"
            echo ""
            echo "Опции:"
            echo "  --force        Пропустить подтверждения"
            echo "  --dry-run      Показать что будет сделано, без выполнения"
            echo "  --skip-tests   Пропустить автоматические тесты"
            echo "  --help         Показать эту справку"
            echo ""
            exit 0
            ;;
        *)
            log_error "Неизвестная опция: $1"
            echo "Используйте --help для справки"
            exit 1
            ;;
    esac
done

# Режим dry-run
if [ $DRY_RUN -eq 1 ]; then
    log_warning "Режим DRY-RUN: изменения не будут применены"
    echo ""
fi

# Проверка окружения
log_step "Проверка окружения"
echo ""

# Проверка Python
if ! command -v python3 &> /dev/null; then
    log_error "Python 3 не установлен"
    exit 1
fi
log_success "Python 3 установлен: $(python3 --version)"

# Проверка SQLite (опционально)
if command -v sqlite3 &> /dev/null; then
    log_success "SQLite установлен: $(sqlite3 --version | head -n 1)"
else
    log_warning "SQLite не установлен (опционально для проверок)"
fi

# Проверка файлов
log_step "Проверка необходимых файлов"
echo ""

required_files=(
    "migrate_to_many_to_many.py"
    "models.py"
    "database.py"
)

for file in "${required_files[@]}"; do
    if [ ! -f "$file" ]; then
        log_error "Файл не найден: $file"
        exit 1
    fi
    log_success "Найден: $file"
done

# Проверка зависимостей
if [ -f "requirements.txt" ]; then
    check_python_requirements || log_warning "Возможны проблемы с зависимостями"
fi

echo ""

# Проверка БД
log_step "Проверка базы данных"
echo ""

DB_FILE="telegram.db"
if [ -f "$DB_FILE" ]; then
    log_success "База данных найдена: $DB_FILE"
    
    # Статистика до миграции
    get_db_stats "$DB_FILE"
    
    # Проверка целостности
    check_database "$DB_FILE" || log_warning "Проверьте целостность БД вручную"
else
    log_warning "База данных не найдена: $DB_FILE"
    log_info "Миграция создаст новую структуру при первом запуске"
fi

echo ""

# Подтверждение
if [ $FORCE -eq 0 ] && [ $DRY_RUN -eq 0 ]; then
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "📋 Что будет сделано:"
    echo "  1. Остановка всех сервисов"
    echo "  2. Создание резервной копии БД"
    echo "  3. Создание таблицы user_channel"
    echo "  4. Перенос данных из старой структуры"
    echo "  5. Объединение дубликатов каналов"
    echo "  6. Обновление связей в таблице posts"
    echo "  7. Замена таблицы channels"
    echo "  8. Создание индексов"
    if [ $SKIP_TESTS -eq 0 ]; then
        echo "  9. Запуск тестов (опционально)"
        echo "  10. Перезапуск сервисов"
    else
        echo "  9. Перезапуск сервисов"
    fi
    echo ""
    echo "⏱️  Время выполнения: обычно 1-5 секунд"
    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    
    if ! confirm_action "Продолжить миграцию?" "n"; then
        log_warning "Миграция отменена пользователем"
        exit 0
    fi
fi

echo ""

# Режим dry-run - выход
if [ $DRY_RUN -eq 1 ]; then
    log_info "Режим dry-run завершен. Запустите без --dry-run для применения"
    exit 0
fi

# ========== ВЫПОЛНЕНИЕ МИГРАЦИИ ==========

# Шаг 1: Остановка сервисов
log_step "Остановка сервисов"
echo ""

services=(
    "python.*main.py"
    "python.*bot.py"
    "python.*run_system.py"
    "python.*start_secure_system.py"
)

for service in "${services[@]}"; do
    stop_process "$service" 5
done

log_success "Все сервисы остановлены"
sleep 2
echo ""

# Шаг 2: Создание резервной копии
log_step "Создание резервной копии"
echo ""

if [ -f "$DB_FILE" ]; then
    BACKUP_FILE=$(create_backup "$DB_FILE" ".")
    if [ $? -eq 0 ]; then
        log_success "Резервная копия: $BACKUP_FILE"
        echo ""
        echo "  💾 Для отката выполните:"
        echo "     cp $BACKUP_FILE $DB_FILE"
        echo ""
    else
        log_error "Не удалось создать резервную копию"
        
        if ! confirm_action "Продолжить без резервной копии?" "n"; then
            log_error "Миграция прервана"
            exit 1
        fi
    fi
else
    log_info "База данных не найдена, резервная копия не нужна"
fi

echo ""

# Шаг 3: Выполнение миграции
log_step "Выполнение миграции базы данных"
echo ""

log_info "Запуск migrate_to_many_to_many.py..."
echo ""
echo "────────────────────────────────────────────────────────────────"
python3 migrate_to_many_to_many.py
MIGRATION_STATUS=$?
echo "────────────────────────────────────────────────────────────────"
echo ""

if [ $MIGRATION_STATUS -ne 0 ]; then
    log_error "МИГРАЦИЯ ПРОВАЛЕНА!"
    echo ""
    echo "🔄 Для отката выполните:"
    if [ -n "$BACKUP_FILE" ]; then
        echo "   cp $BACKUP_FILE $DB_FILE"
    else
        echo "   Восстановите БД из вашей резервной копии"
    fi
    echo "   python3 run_system.py &"
    echo ""
    exit 1
fi

log_success "Миграция базы данных завершена"
echo ""

# Статистика после миграции
if [ -f "$DB_FILE" ]; then
    log_info "Статистика после миграции:"
    get_db_stats "$DB_FILE"
    echo ""
fi

# Шаг 4: Тесты (опционально)
if [ $SKIP_TESTS -eq 0 ]; then
    log_step "Запуск тестов (опционально)"
    echo ""
    
    RUN_TESTS=0
    if [ $FORCE -eq 1 ]; then
        RUN_TESTS=0  # В force режиме пропускаем тесты
        log_info "Тесты пропущены (--force режим)"
    else
        if confirm_action "Запустить автоматические тесты?" "y"; then
            RUN_TESTS=1
        fi
    fi
    
    if [ $RUN_TESTS -eq 1 ]; then
        echo ""
        echo "────────────────────────────────────────────────────────────────"
        python3 test_many_to_many.py
        TEST_STATUS=$?
        echo "────────────────────────────────────────────────────────────────"
        echo ""
        
        if [ $TEST_STATUS -eq 0 ]; then
            log_success "Все тесты пройдены"
        else
            log_warning "Некоторые тесты провалены"
            log_info "Это может быть нормально, проверьте вывод выше"
        fi
    else
        log_info "Тесты пропущены"
    fi
    echo ""
else
    log_info "Тесты пропущены (--skip-tests)"
    echo ""
fi

# Шаг 5: Перезапуск сервисов
log_step "Перезапуск сервисов"
echo ""

START_SERVICES=1
if [ $FORCE -eq 0 ]; then
    if ! confirm_action "Запустить сервисы?" "y"; then
        START_SERVICES=0
    fi
fi

if [ $START_SERVICES -eq 1 ]; then
    log_info "Запуск сервисов..."
    
    # Создаем директорию для логов если нет
    mkdir -p logs
    
    # Пробуем разные варианты запуска
    if [ -f "run_system.py" ]; then
        nohup python3 run_system.py > logs/system.log 2>&1 &
        log_success "Сервисы запущены через run_system.py"
    elif [ -f "start_secure_system.py" ]; then
        nohup python3 start_secure_system.py > logs/secure_system.log 2>&1 &
        log_success "Сервисы запущены через start_secure_system.py"
    else
        # Запуск по отдельности
        nohup python3 main.py > logs/main.log 2>&1 &
        sleep 2
        nohup python3 bot.py > logs/bot.log 2>&1 &
        log_success "Сервисы запущены (main.py + bot.py)"
    fi
    
    sleep 3
    
    # Проверка
    if pgrep -f "python.*main.py" > /dev/null || pgrep -f "python.*run_system.py" > /dev/null; then
        log_success "Сервисы работают"
    else
        log_warning "Сервисы могут не работать, проверьте логи"
    fi
else
    log_info "Запуск сервисов пропущен"
    echo ""
    echo "  Для запуска выполните:"
    echo "    python3 run_system.py &"
    echo "  или:"
    echo "    python3 main.py & python3 bot.py &"
fi

echo ""

# Итоговое сообщение
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║   ✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!                               ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""

log_info "Результаты миграции"
echo ""
echo "  📊 Проверить результаты:"
echo "     sqlite3 $DB_FILE 'SELECT COUNT(*) FROM channels;'"
echo "     sqlite3 $DB_FILE 'SELECT COUNT(*) FROM user_channel;'"
echo ""
echo "  📚 Документация:"
echo "     • MANY_TO_MANY_SUMMARY.md   - краткое резюме"
echo "     • QUICK_MIGRATION.md        - быстрая инструкция"
echo "     • MIGRATION_MANY_TO_MANY.md - полная документация"
echo ""

if [ -n "$BACKUP_FILE" ]; then
    echo "  💾 Резервная копия:"
    echo "     $BACKUP_FILE"
    echo ""
    echo "  🔄 Откат (если нужно):"
    echo "     cp $BACKUP_FILE $DB_FILE"
    echo "     python3 run_system.py &"
    echo ""
fi

echo "════════════════════════════════════════════════════════════════"
echo ""

log_success "Готово! Ваша система обновлена и готова к работе"
echo ""

exit 0

