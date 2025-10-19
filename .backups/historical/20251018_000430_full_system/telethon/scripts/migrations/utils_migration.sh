#!/bin/bash

# Утилиты для миграции Many-to-Many
# Аналог utils.sh из scripts/

# Logging function that frames a message with a border and adds a timestamp
log_message() {
    local message="$1"
    local combined_message="${message}"
    local length=${#combined_message}
    local border_length=$((length + 4))
    
    # Create the top border
    local border=""
    for ((i=0; i<border_length; i++)); do
        border="${border}─"
    done
    
    # Display the framed message with timestamp
    echo "╭${border}╮"
    echo "│ ${combined_message}   │"
    echo "╰${border}╯"
}

log_success() {
    local message="$1"
    local timestamp=$(date +%H:%M:%S)
    local combined_message="✅ [SUCCESS] ${timestamp}: ${message}"
    log_message "${combined_message}"
}

log_error() {
    local message="$1"
    local timestamp=$(date +%H:%M:%S)
    local combined_message="❌ [ERROR] ${timestamp}: ${message}"
    log_message "${combined_message}"
}

log_warning() {
    local message="$1"
    local timestamp=$(date +%H:%M:%S)
    local combined_message="⚠️  [WARNING] ${timestamp}: ${message}"
    log_message "${combined_message}"
}

log_info() {
    local message="$1"
    local timestamp=$(date +%H:%M:%S)
    local combined_message="ℹ️  [INFO] ${timestamp}: ${message}"
    log_message "${combined_message}"
}

log_step() {
    local message="$1"
    local timestamp=$(date +%H:%M:%S)
    local combined_message="🔄 [STEP] ${timestamp}: ${message}"
    log_message "${combined_message}"
}

# Проверка существования процесса
check_process_running() {
    local process_name="$1"
    if pgrep -f "$process_name" > /dev/null 2>&1; then
        return 0  # Running
    else
        return 1  # Not running
    fi
}

# Остановка процесса
stop_process() {
    local process_name="$1"
    local timeout=${2:-10}  # Default 10 seconds
    
    if check_process_running "$process_name"; then
        log_info "Остановка процесса: $process_name"
        pkill -f "$process_name" 2>/dev/null
        
        # Ждем завершения
        local count=0
        while check_process_running "$process_name" && [ $count -lt $timeout ]; do
            sleep 1
            ((count++))
        done
        
        # Принудительное завершение если не остановился
        if check_process_running "$process_name"; then
            log_warning "Принудительное завершение: $process_name"
            pkill -9 -f "$process_name" 2>/dev/null
        fi
        
        return 0
    else
        log_info "Процесс не запущен: $process_name"
        return 1
    fi
}

# Создание резервной копии
create_backup() {
    local file="$1"
    local backup_dir="${2:-.}"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_name="${backup_dir}/$(basename ${file}).backup_${timestamp}"
    
    if [ -f "$file" ]; then
        cp "$file" "$backup_name"
        if [ $? -eq 0 ]; then
            log_success "Резервная копия создана: $backup_name"
            echo "$backup_name"
            return 0
        else
            log_error "Не удалось создать резервную копию"
            return 1
        fi
    else
        log_warning "Файл не найден: $file"
        return 1
    fi
}

# Проверка Python пакетов
check_python_requirements() {
    log_info "Проверка Python зависимостей..."
    
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3 не установлен"
        return 1
    fi
    
    if [ -f "requirements.txt" ]; then
        python3 -c "
import sys
import pkg_resources

try:
    with open('requirements.txt') as f:
        requirements = f.read().splitlines()
    
    for requirement in requirements:
        if requirement.strip() and not requirement.startswith('#'):
            try:
                pkg_resources.require(requirement)
            except:
                print(f'Missing: {requirement}')
                sys.exit(1)
    sys.exit(0)
except Exception as e:
    print(f'Error: {e}')
    sys.exit(1)
"
        if [ $? -eq 0 ]; then
            log_success "Все зависимости установлены"
            return 0
        else
            log_warning "Некоторые зависимости не установлены"
            log_info "Установка зависимостей: pip3 install -r requirements.txt"
            return 1
        fi
    else
        log_warning "requirements.txt не найден"
        return 1
    fi
}

# Подтверждение действия
confirm_action() {
    local message="$1"
    local default="${2:-n}"  # Default to 'n' (no)
    
    if [ "$default" = "y" ]; then
        prompt="[Y/n]"
    else
        prompt="[y/N]"
    fi
    
    read -p "❓ $message $prompt: " -n 1 -r
    echo
    
    if [ -z "$REPLY" ]; then
        REPLY="$default"
    fi
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        return 0
    else
        return 1
    fi
}

# Проверка БД
check_database() {
    local db_file="$1"
    
    if [ ! -f "$db_file" ]; then
        log_warning "База данных не найдена: $db_file"
        return 1
    fi
    
    # Проверка целостности SQLite БД
    if command -v sqlite3 &> /dev/null; then
        local integrity=$(sqlite3 "$db_file" "PRAGMA integrity_check;" 2>&1)
        if [ "$integrity" = "ok" ]; then
            log_success "База данных прошла проверку целостности"
            return 0
        else
            log_error "Проблемы с целостностью БД: $integrity"
            return 1
        fi
    else
        log_warning "sqlite3 не установлен, пропуск проверки целостности"
        return 0
    fi
}

# Получение статистики БД
get_db_stats() {
    local db_file="$1"
    
    if [ ! -f "$db_file" ] || ! command -v sqlite3 &> /dev/null; then
        return 1
    fi
    
    log_info "Статистика базы данных:"
    echo "  📊 Размер БД: $(du -h "$db_file" | cut -f1)"
    
    local channels_count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM channels;" 2>/dev/null || echo "N/A")
    echo "  📢 Каналов: $channels_count"
    
    local users_count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM users;" 2>/dev/null || echo "N/A")
    echo "  👥 Пользователей: $users_count"
    
    local posts_count=$(sqlite3 "$db_file" "SELECT COUNT(*) FROM posts;" 2>/dev/null || echo "N/A")
    echo "  📝 Постов: $posts_count"
}

