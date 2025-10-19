#!/bin/bash
# Автоматический бэкап PostgreSQL для n8n
# Использование: ./scripts/backup-n8n-postgres.sh

set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Директория для бэкапов
BACKUP_DIR="/home/ilyasni/n8n-server/n8n-installer/.backups/postgres"
TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_FILE="n8n-postgres-backup-${TIMESTAMP}.sql"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

# Создаем директорию для бэкапов
mkdir -p "${BACKUP_DIR}"

echo -e "${YELLOW}🔄 Создание бэкапа PostgreSQL для n8n...${NC}"
echo "Файл: ${BACKUP_FILE}"
echo ""

# Проверяем, запущен ли PostgreSQL
if ! docker ps | grep -q "postgres"; then
    echo -e "${RED}❌ Контейнер postgres не запущен!${NC}"
    exit 1
fi

# Создаем SQL дамп
echo -e "${YELLOW}📦 Экспорт БД postgres...${NC}"
docker exec postgres pg_dump -U postgres -d postgres -F p -f /tmp/backup.sql

# Копируем дамп из контейнера
docker cp postgres:/tmp/backup.sql "${BACKUP_PATH}"

# Удаляем временный файл из контейнера
docker exec postgres rm /tmp/backup.sql

# Сжимаем бэкап
echo -e "${YELLOW}📦 Сжатие бэкапа...${NC}"
gzip "${BACKUP_PATH}"
BACKUP_PATH="${BACKUP_PATH}.gz"

# Проверяем размер
BACKUP_SIZE=$(du -h "${BACKUP_PATH}" | cut -f1)

echo ""
echo -e "${GREEN}✅ Бэкап создан успешно!${NC}"
echo "📁 Путь: ${BACKUP_PATH}"
echo "📊 Размер: ${BACKUP_SIZE}"
echo ""

# Статистика БД
echo -e "${YELLOW}📊 Статистика БД:${NC}"
docker exec postgres psql -U postgres -d postgres -c "
SELECT 
  (SELECT COUNT(*) FROM workflow_entity) as workflows,
  (SELECT COUNT(*) FROM credentials_entity) as credentials,
  (SELECT COUNT(*) FROM execution_entity) as executions,
  (SELECT COUNT(*) FROM \"user\") as users;
"

# Сохраняем только последние 30 бэкапов
echo ""
echo -e "${YELLOW}🗑️ Очистка старых бэкапов (храним последние 30)...${NC}"
cd "${BACKUP_DIR}"
ls -t n8n-postgres-backup-*.sql.gz 2>/dev/null | tail -n +31 | xargs -r rm -v

echo ""
echo -e "${GREEN}✅ Готово!${NC}"
echo ""
echo "📋 Для восстановления используйте:"
echo "   ./scripts/restore-n8n-postgres.sh ${BACKUP_FILE}.gz"

