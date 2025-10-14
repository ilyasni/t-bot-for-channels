#!/bin/bash
# Восстановление PostgreSQL бэкапа для n8n
# Использование: ./scripts/restore-n8n-postgres.sh <backup-file.sql.gz>

set -euo pipefail

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка аргументов
if [ $# -eq 0 ]; then
    echo -e "${RED}❌ Ошибка: укажите файл бэкапа${NC}"
    echo ""
    echo "Использование:"
    echo "  $0 <backup-file.sql.gz>"
    echo ""
    echo "Доступные бэкапы:"
    ls -lh /home/ilyasni/n8n-server/n8n-installer/.backups/postgres/*.sql.gz 2>/dev/null || echo "  Нет бэкапов"
    exit 1
fi

BACKUP_FILE="$1"
BACKUP_DIR="/home/ilyasni/n8n-server/n8n-installer/.backups/postgres"

# Проверяем, существует ли файл
if [ ! -f "${BACKUP_FILE}" ] && [ ! -f "${BACKUP_DIR}/${BACKUP_FILE}" ]; then
    echo -e "${RED}❌ Файл бэкапа не найден: ${BACKUP_FILE}${NC}"
    exit 1
fi

# Если указан только имя файла, добавляем путь
if [ ! -f "${BACKUP_FILE}" ]; then
    BACKUP_FILE="${BACKUP_DIR}/${BACKUP_FILE}"
fi

echo -e "${YELLOW}⚠️  ВНИМАНИЕ: Восстановление УДАЛИТ все текущие данные n8n!${NC}"
echo ""
echo "Файл бэкапа: ${BACKUP_FILE}"
echo ""
read -p "Продолжить? (yes/no): " -r
if [[ ! $REPLY =~ ^[Yy]es$ ]]; then
    echo "Отменено"
    exit 0
fi

# Проверяем, запущен ли PostgreSQL
if ! docker ps | grep -q "postgres"; then
    echo -e "${RED}❌ Контейнер postgres не запущен!${NC}"
    exit 1
fi

# Останавливаем n8n
echo -e "${YELLOW}🛑 Останавливаем n8n...${NC}"
cd /home/ilyasni/n8n-server/n8n-installer
docker compose stop n8n n8n-worker || true

# Разархивируем бэкап
TEMP_SQL="/tmp/restore-$(basename ${BACKUP_FILE} .gz)"
echo -e "${YELLOW}📦 Распаковка бэкапа...${NC}"
gunzip -c "${BACKUP_FILE}" > "${TEMP_SQL}"

# Копируем SQL в контейнер
docker cp "${TEMP_SQL}" postgres:/tmp/restore.sql

# Удаляем существующие данные и восстанавливаем
echo -e "${YELLOW}🔄 Восстановление БД...${NC}"
docker exec postgres psql -U postgres -d postgres -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
docker exec postgres psql -U postgres -d postgres -f /tmp/restore.sql

# Удаляем временные файлы
rm "${TEMP_SQL}"
docker exec postgres rm /tmp/restore.sql

# Перезапускаем n8n
echo -e "${YELLOW}🚀 Запускаем n8n...${NC}"
docker compose up -d n8n

echo ""
echo -e "${GREEN}✅ Восстановление завершено!${NC}"
echo ""
echo "📊 Статистика БД:"
sleep 3
docker exec postgres psql -U postgres -d postgres -c "
SELECT 
  (SELECT COUNT(*) FROM workflow_entity) as workflows,
  (SELECT COUNT(*) FROM credentials_entity) as credentials,
  (SELECT COUNT(*) FROM execution_entity) as executions,
  (SELECT COUNT(*) FROM \"user\") as users;
"

echo ""
echo -e "${GREEN}✅ n8n готов к работе!${NC}"
echo "🌐 Откройте: http://localhost:5678 или https://ваш-домен"

