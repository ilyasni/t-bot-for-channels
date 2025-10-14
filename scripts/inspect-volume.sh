#!/bin/bash
# Инспекция Docker volume для проверки содержимого
# Использование: ./scripts/inspect-volume.sh <volume-name>

set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [ $# -eq 0 ]; then
    echo "Использование: $0 <volume-name>"
    echo ""
    echo "Доступные volumes:"
    docker volume ls
    exit 1
fi

VOLUME="$1"

echo -e "${YELLOW}🔍 Инспекция volume: ${VOLUME}${NC}"
echo ""

# Информация о volume
echo "📋 Metadata:"
docker volume inspect "${VOLUME}" --format '
Created: {{.CreatedAt}}
Mountpoint: {{.Mountpoint}}
Driver: {{.Driver}}
'

echo ""
echo "📁 Содержимое (топ-уровень):"
docker run --rm -v "${VOLUME}:/data:ro" alpine ls -lah /data/

echo ""
echo "📊 Размер:"
docker run --rm -v "${VOLUME}:/data:ro" alpine du -sh /data/

echo ""
echo "🔢 Количество файлов:"
docker run --rm -v "${VOLUME}:/data:ro" alpine find /data -type f | wc -l

echo ""
echo -e "${GREEN}✅ Готово!${NC}"

