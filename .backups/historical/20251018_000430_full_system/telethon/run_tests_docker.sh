#!/bin/bash
#
# Запуск тестов в Docker контейнере
# Использование: ./run_tests_docker.sh [mode]
#
# Modes:
#   unit        - Unit тесты (быстро, SQLite in-memory)
#   integration - Integration тесты (PostgreSQL + Redis)
#   all         - Все тесты + coverage (по умолчанию)
#   coverage    - Все тесты + HTML coverage report
#   build       - Пересборка test image
#

set -e

MODE=${1:-all}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

echo "╔════════════════════════════════════════════════════════════════╗"
echo "║                                                                ║"
echo "║     🧪 Telegram Parser Tests (Docker)                         ║"
echo "║                                                                ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo ""
echo "Mode: $MODE"
echo "Directory: $SCRIPT_DIR"
echo ""

# Функция для unit тестов
run_unit_tests() {
    echo "🔬 Запуск Unit Tests в Docker..."
    echo "   Используется: SQLite in-memory (не требует PostgreSQL)"
    echo ""
    
    docker compose -f docker-compose.test.yml run --rm telethon-test-unit
    
    RESULT=$?
    
    if [ $RESULT -eq 0 ]; then
        echo ""
        echo "✅ Unit тесты завершены успешно!"
    else
        echo ""
        echo "❌ Unit тесты завершены с ошибками (exit code: $RESULT)"
    fi
    
    return $RESULT
}

# Функция для integration тестов
run_integration_tests() {
    echo "🔗 Запуск Integration Tests в Docker..."
    echo "   Запуск PostgreSQL и Redis test контейнеров..."
    echo ""
    
    # Запускаем сервисы
    docker compose -f docker-compose.test.yml up -d postgres-test redis-test
    
    # Ждем готовности
    echo "⏳ Ожидание готовности сервисов..."
    sleep 5
    
    # Запускаем integration тесты
    docker compose -f docker-compose.test.yml run --rm telethon-test-integration
    
    RESULT=$?
    
    # Останавливаем test сервисы
    docker compose -f docker-compose.test.yml down
    
    if [ $RESULT -eq 0 ]; then
        echo ""
        echo "✅ Integration тесты завершены успешно!"
    else
        echo ""
        echo "❌ Integration тесты завершены с ошибками (exit code: $RESULT)"
    fi
    
    return $RESULT
}

# Функция для всех тестов
run_all_tests() {
    echo "🚀 Запуск всех тестов в Docker..."
    echo "   Запуск PostgreSQL и Redis test контейнеров..."
    echo ""
    
    # Запускаем сервисы
    docker compose -f docker-compose.test.yml up -d postgres-test redis-test
    
    # Ждем готовности
    echo "⏳ Ожидание готовности сервисов..."
    sleep 5
    
    # Запускаем все тесты
    docker compose -f docker-compose.test.yml run --rm telethon-test-all
    
    RESULT=$?
    
    # Останавливаем test сервисы
    docker compose -f docker-compose.test.yml down
    
    if [ $RESULT -eq 0 ]; then
        echo ""
        echo "✅ Все тесты завершены успешно!"
        echo "📊 Coverage report: htmlcov/index.html"
    else
        echo ""
        echo "❌ Тесты завершены с ошибками (exit code: $RESULT)"
    fi
    
    return $RESULT
}

# Функция для coverage
run_coverage() {
    echo "📊 Запуск с Coverage в Docker..."
    echo ""
    
    # То же что all, но подчеркиваем coverage
    run_all_tests
    
    RESULT=$?
    
    if [ $RESULT -eq 0 ]; then
        echo ""
        echo "💡 Откройте coverage report:"
        echo "   open htmlcov/index.html"
        echo "   или: firefox htmlcov/index.html"
    fi
    
    return $RESULT
}

# Функция для пересборки
build_test_image() {
    echo "🔨 Пересборка test image..."
    echo ""
    
    docker compose -f docker-compose.test.yml build telethon-test-unit
    
    echo ""
    echo "✅ Test image пересобран!"
    echo "💡 Теперь запустите: ./run_tests_docker.sh unit"
}

# Выбор режима
case "$MODE" in
    unit)
        run_unit_tests
        ;;
    integration)
        run_integration_tests
        ;;
    all)
        run_all_tests
        ;;
    coverage)
        run_coverage
        ;;
    build)
        build_test_image
        ;;
    *)
        echo "❌ Неизвестный режим: $MODE"
        echo ""
        echo "Доступные режимы:"
        echo "  unit        - Unit тесты (SQLite in-memory, быстро)"
        echo "  integration - Integration тесты (PostgreSQL + Redis)"
        echo "  all         - Все тесты + coverage (по умолчанию)"
        echo "  coverage    - Алиас для 'all' с акцентом на coverage"
        echo "  build       - Пересборка test Docker image"
        echo ""
        echo "Примеры:"
        echo "  ./run_tests_docker.sh unit"
        echo "  ./run_tests_docker.sh integration"
        echo "  ./run_tests_docker.sh coverage"
        echo "  ./run_tests_docker.sh build"
        exit 1
        ;;
esac

echo ""
echo "════════════════════════════════════════════════════════════════"
echo "✅ Готово!"
echo "════════════════════════════════════════════════════════════════"

exit $?

