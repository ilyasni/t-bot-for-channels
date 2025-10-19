#!/bin/bash
#
# Скрипт для запуска тестов в разных режимах
# Использование: ./tests/run_tests.sh [mode]
#
# Modes:
#   unit        - Только unit тесты (быстро, с моками)
#   integration - Только integration тесты (с реальными сервисами)
#   all         - Все тесты (по умолчанию)
#   coverage    - Тесты + HTML coverage report
#   fast        - Параллельный запуск (-n auto)
#

set -e

MODE=${1:-all}
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$PROJECT_ROOT"

echo "============================================"
echo "🧪 Telegram Parser Tests"
echo "============================================"
echo "Mode: $MODE"
echo "Project: $PROJECT_ROOT"
echo ""

# Проверка виртуального окружения
if [[ -z "$VIRTUAL_ENV" ]]; then
    echo "⚠️  Виртуальное окружение не активировано"
    echo "💡 Активируйте: source venv/bin/activate"
    echo ""
fi

# Установка test dependencies если нужно
if ! python -c "import pytest" 2>/dev/null; then
    echo "📦 Установка test dependencies..."
    pip install -r requirements-test.txt
    echo ""
fi

# Функция для unit тестов
run_unit_tests() {
    echo "🔬 Запуск Unit Tests..."
    pytest tests/ \
        -m "unit" \
        --tb=short \
        -v \
        --ignore=tests/integration/ \
        "$@"
}

# Функция для integration тестов
run_integration_tests() {
    echo "🔗 Запуск Integration Tests..."
    echo "⚠️  Требуются: PostgreSQL, Redis, Qdrant"
    echo ""
    
    pytest tests/integration/ \
        -m "integration" \
        --tb=short \
        -v \
        "$@"
}

# Функция для всех тестов
run_all_tests() {
    echo "🚀 Запуск всех тестов..."
    pytest tests/ \
        --tb=short \
        -v \
        "$@"
}

# Функция для coverage
run_with_coverage() {
    echo "📊 Запуск с Coverage..."
    pytest tests/ \
        --cov=. \
        --cov-report=html \
        --cov-report=term-missing \
        --cov-fail-under=60 \
        --tb=short \
        -v \
        "$@"
    
    echo ""
    echo "✅ Coverage report: htmlcov/index.html"
    echo "💡 Откройте в браузере: open htmlcov/index.html"
}

# Функция для параллельного запуска
run_fast_tests() {
    echo "⚡ Параллельный запуск тестов..."
    pytest tests/ \
        -n auto \
        --tb=short \
        -v \
        "$@"
}

# Выбор режима
case "$MODE" in
    unit)
        run_unit_tests "${@:2}"
        ;;
    integration)
        run_integration_tests "${@:2}"
        ;;
    all)
        run_all_tests "${@:2}"
        ;;
    coverage)
        run_with_coverage "${@:2}"
        ;;
    fast)
        run_fast_tests "${@:2}"
        ;;
    *)
        echo "❌ Неизвестный режим: $MODE"
        echo ""
        echo "Доступные режимы:"
        echo "  unit        - Unit тесты (быстро)"
        echo "  integration - Integration тесты (требуют сервисы)"
        echo "  all         - Все тесты (по умолчанию)"
        echo "  coverage    - С coverage отчетом"
        echo "  fast        - Параллельный запуск"
        echo ""
        echo "Примеры:"
        echo "  ./tests/run_tests.sh unit"
        echo "  ./tests/run_tests.sh coverage"
        echo "  ./tests/run_tests.sh all -k test_auth"
        exit 1
        ;;
esac

echo ""
echo "============================================"
echo "✅ Тесты завершены"
echo "============================================"

