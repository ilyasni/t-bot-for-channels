#!/usr/bin/env python3
"""
Скрипт для очистки старых логов
Удаляет логи старше указанного количества дней
"""

import os
import time
import argparse
from pathlib import Path
from datetime import datetime, timedelta

def cleanup_logs(logs_dir: Path, days_to_keep: int = 7, dry_run: bool = False):
    """Очистка старых логов"""
    
    if not logs_dir.exists():
        print(f"❌ Logs directory not found: {logs_dir}")
        return
    
    # Вычисляем дату cutoff
    cutoff_date = datetime.now() - timedelta(days=days_to_keep)
    cutoff_timestamp = cutoff_date.timestamp()
    
    print(f"🧹 Cleaning logs older than {days_to_keep} days (before {cutoff_date.strftime('%Y-%m-%d %H:%M:%S')})")
    print(f"📁 Logs directory: {logs_dir}")
    
    if dry_run:
        print("🔍 DRY RUN - No files will be deleted")
    
    deleted_count = 0
    total_size = 0
    
    # Проходим по всем файлам в папке logs
    for log_file in logs_dir.iterdir():
        if log_file.is_file() and log_file.suffix == '.log':
            # Получаем время модификации файла
            file_mtime = log_file.stat().st_mtime
            file_date = datetime.fromtimestamp(file_mtime)
            
            # Проверяем нужно ли удалить файл
            if file_mtime < cutoff_timestamp:
                file_size = log_file.stat().st_size
                total_size += file_size
                
                if dry_run:
                    print(f"🗑️  Would delete: {log_file.name} ({file_date.strftime('%Y-%m-%d %H:%M:%S')}, {file_size} bytes)")
                else:
                    try:
                        log_file.unlink()
                        print(f"✅ Deleted: {log_file.name} ({file_date.strftime('%Y-%m-%d %H:%M:%S')}, {file_size} bytes)")
                        deleted_count += 1
                    except Exception as e:
                        print(f"❌ Error deleting {log_file.name}: {e}")
            else:
                print(f"📄 Keeping: {log_file.name} ({file_date.strftime('%Y-%m-%d %H:%M:%S')})")
    
    # Результаты
    if dry_run:
        print(f"\n🔍 DRY RUN COMPLETE")
        print(f"📊 Would delete {deleted_count} files ({total_size / 1024 / 1024:.2f} MB)")
    else:
        print(f"\n✅ CLEANUP COMPLETE")
        print(f"📊 Deleted {deleted_count} files ({total_size / 1024 / 1024:.2f} MB)")

def main():
    """Основная функция"""
    parser = argparse.ArgumentParser(description='Clean up old log files')
    parser.add_argument('--days', type=int, default=7, help='Keep logs for this many days (default: 7)')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be deleted without actually deleting')
    parser.add_argument('--logs-dir', type=str, help='Logs directory path (default: telethon/logs)')
    
    args = parser.parse_args()
    
    # Определяем папку с логами
    if args.logs_dir:
        logs_dir = Path(args.logs_dir)
    else:
        # По умолчанию используем telethon/logs
        script_dir = Path(__file__).parent.parent
        logs_dir = script_dir / "telethon" / "logs"
    
    # Проверяем что папка существует
    if not logs_dir.exists():
        print(f"❌ Logs directory not found: {logs_dir}")
        print("💡 Use --logs-dir to specify correct path")
        return 1
    
    # Выполняем очистку
    cleanup_logs(logs_dir, args.days, args.dry_run)
    
    return 0

if __name__ == "__main__":
    exit(main())
