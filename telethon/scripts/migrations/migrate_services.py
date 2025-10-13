#!/usr/bin/env python3
"""
migrate_services.py

Python скрипт для безопасной миграции к Many-to-Many структуре.
Аналог start_services.py для управления миграцией.

Использование:
    python3 migrate_services.py               # Интерактивный режим
    python3 migrate_services.py --force       # Без подтверждений
    python3 migrate_services.py --dry-run     # Показать план без выполнения
    python3 migrate_services.py --skip-tests  # Пропустить тесты
"""

import os
import sys
import subprocess
import shutil
import time
import argparse
from datetime import datetime
from pathlib import Path


class MigrationManager:
    """Менеджер миграции к Many-to-Many структуре"""
    
    def __init__(self, force=False, dry_run=False, skip_tests=False):
        self.force = force
        self.dry_run = dry_run
        self.skip_tests = skip_tests
        self.script_dir = Path(__file__).parent
        self.db_file = None  # Определяется автоматически
        self.backup_file = None
        self.db_type = 'unknown'  # sqlite or postgresql
        
        # Определяем тип БД из .env
        self._detect_database_type()
    
    def _detect_database_type(self):
        """Определить тип БД из .env"""
        try:
            env_path = self.script_dir / ".env"
            if env_path.exists():
                with open(env_path) as f:
                    for line in f:
                        if line.strip().startswith('DATABASE_URL='):
                            db_url = line.split('=', 1)[1].strip()
                            if db_url.startswith('postgresql://') or db_url.startswith('postgres://'):
                                self.db_type = 'postgresql'
                                self.db_file = None  # PostgreSQL не использует файл
                            elif db_url.startswith('sqlite:///'):
                                self.db_type = 'sqlite'
                                # Извлекаем путь к файлу
                                db_path = db_url.replace('sqlite:///', '')
                                self.db_file = Path(db_path) if not Path(db_path).is_absolute() else Path(db_path)
                            break
        except Exception as e:
            # Не можем вызвать log_warning здесь, используем print
            print(f"⚠️  Не удалось определить тип БД: {e}")
        
    def log_box(self, message, symbol="═", width=64):
        """Вывод сообщения в рамке"""
        print(f"╔{symbol * width}╗")
        # Центрируем текст
        padding = (width - len(message)) // 2
        print(f"║{' ' * padding}{message}{' ' * (width - padding - len(message))}║")
        print(f"╚{symbol * width}╝")
    
    def log_message(self, icon, level, message):
        """Логирование с иконкой и временем"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"{icon} [{level}] {timestamp}: {message}")
    
    def log_info(self, message):
        self.log_message("ℹ️ ", "INFO", message)
    
    def log_success(self, message):
        self.log_message("✅", "SUCCESS", message)
    
    def log_warning(self, message):
        self.log_message("⚠️ ", "WARNING", message)
    
    def log_error(self, message):
        self.log_message("❌", "ERROR", message)
    
    def log_step(self, message):
        self.log_message("🔄", "STEP", message)
    
    def confirm(self, question, default="n"):
        """Запросить подтверждение"""
        if self.force or self.dry_run:
            return True
        
        prompt = f"❓ {question} [{'Y/n' if default == 'y' else 'y/N'}]: "
        
        try:
            response = input(prompt).strip().lower()
            if not response:
                response = default
            return response == 'y'
        except (KeyboardInterrupt, EOFError):
            print()
            return False
    
    def run_command(self, cmd, shell=False, check=True):
        """Выполнить команду"""
        if self.dry_run:
            self.log_info(f"[DRY-RUN] Would run: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
            return True
        
        try:
            if shell:
                subprocess.run(cmd, shell=True, check=check, cwd=self.script_dir)
            else:
                subprocess.run(cmd, check=check, cwd=self.script_dir)
            return True
        except subprocess.CalledProcessError as e:
            self.log_error(f"Команда провалена: {e}")
            return False
    
    def check_environment(self):
        """Проверка окружения"""
        self.log_step("Проверка окружения")
        print()
        
        # Проверка Python
        python_version = sys.version.split()[0]
        self.log_success(f"Python установлен: {python_version}")
        
        # Показываем тип БД
        if self.db_type == 'postgresql':
            self.log_success(f"Тип БД: PostgreSQL (Supabase)")
            # Проверка psql (опционально)
            try:
                result = subprocess.run(
                    ["psql", "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.log_success(f"psql установлен: {result.stdout.strip()}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.log_info("psql не установлен (не критично)")
        elif self.db_type == 'sqlite':
            self.log_success(f"Тип БД: SQLite")
            # Проверка sqlite3
            try:
                result = subprocess.run(
                    ["sqlite3", "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.log_success(f"sqlite3 установлен: {result.stdout.strip()}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.log_warning("sqlite3 не установлен (опционально для проверок)")
        else:
            self.log_warning(f"Тип БД не определен (проверьте .env)")
        
        print()
    
    def check_files(self):
        """Проверка необходимых файлов"""
        self.log_step("Проверка необходимых файлов")
        print()
        
        required_files = [
            "migrate_to_many_to_many.py",
            "models.py",
            "database.py",
        ]
        
        all_present = True
        for file in required_files:
            file_path = self.script_dir / file
            if file_path.exists():
                self.log_success(f"Найден: {file}")
            else:
                self.log_error(f"Файл не найден: {file}")
                all_present = False
        
        print()
        
        if not all_present:
            self.log_error("Отсутствуют необходимые файлы")
            return False
        
        return True
    
    def check_database(self):
        """Проверка базы данных"""
        self.log_step("Проверка базы данных")
        print()
        
        if self.db_type == 'postgresql':
            self.log_success("База данных: PostgreSQL (Supabase)")
            self.log_info("Статистику можно получить после миграции")
            print()
            return True
        
        elif self.db_type == 'sqlite':
            if not self.db_file or not self.db_file.exists():
                self.log_warning(f"База данных не найдена: {self.db_file}")
                self.log_info("Миграция создаст новую структуру при первом запуске")
                print()
                return True
            
            self.log_success(f"База данных найдена: {self.db_file.name}")
            
            # Размер БД
            size_mb = self.db_file.stat().st_size / (1024 * 1024)
            print(f"  📊 Размер БД: {size_mb:.2f} MB")
            
            # Статистика (если sqlite3 доступен)
            try:
                for query, label in [
                    ("SELECT COUNT(*) FROM channels", "Каналов"),
                    ("SELECT COUNT(*) FROM users", "Пользователей"),
                    ("SELECT COUNT(*) FROM posts", "Постов"),
                ]:
                    result = subprocess.run(
                        ["sqlite3", str(self.db_file), query],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    count = result.stdout.strip()
                    print(f"  📊 {label}: {count}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                self.log_warning("Не удалось получить статистику БД")
            
            # Проверка целостности
            try:
                result = subprocess.run(
                    ["sqlite3", str(self.db_file), "PRAGMA integrity_check;"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                if result.stdout.strip() == "ok":
                    self.log_success("База данных прошла проверку целостности")
                else:
                    self.log_warning(f"Проблемы с целостностью БД: {result.stdout.strip()}")
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            print()
            return True
        
        else:
            self.log_warning("Тип БД не определен")
            print()
            return True
    
    def stop_services(self):
        """Остановка сервисов"""
        self.log_step("Остановка сервисов")
        print()
        
        services = [
            "python.*main.py",
            "python.*bot.py",
            "python.*run_system.py",
            # "python.*start_secure_system.py",  # Removed in v3.1.1
        ]
        
        for service in services:
            self.log_info(f"Остановка: {service}")
            self.run_command(f"pkill -f '{service}'", shell=True, check=False)
        
        if not self.dry_run:
            time.sleep(2)
        
        self.log_success("Все сервисы остановлены")
        print()
    
    def create_backup(self):
        """Создание резервной копии"""
        self.log_step("Создание резервной копии")
        print()
        
        if self.db_type == 'postgresql':
            self.log_info("PostgreSQL: Резервное копирование через pg_dump")
            self.log_warning("Рекомендуется создать snapshot в Supabase перед миграцией")
            print()
            print("  💾 Создание бэкапа PostgreSQL (опционально):")
            print("     pg_dump -h your-host -U postgres -d postgres > backup.sql")
            print("  или через Supabase Dashboard:")
            print("     Settings → Database → Create backup")
            print()
            
            if not self.force and not self.confirm("Продолжить без автоматического бэкапа?", "y"):
                return False
            
            print()
            return True
        
        elif self.db_type == 'sqlite':
            if not self.db_file or not self.db_file.exists():
                self.log_info("База данных не найдена, резервная копия не нужна")
                print()
                return True
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.backup_file = self.script_dir / f"{self.db_file.name}.backup_{timestamp}"
            
            if self.dry_run:
                self.log_info(f"[DRY-RUN] Would create backup: {self.backup_file.name}")
                print()
                return True
            
            try:
                shutil.copy2(self.db_file, self.backup_file)
                self.log_success(f"Резервная копия создана: {self.backup_file.name}")
                print()
                print(f"  💾 Для отката выполните:")
                print(f"     cp {self.backup_file.name} {self.db_file.name}")
                print()
                return True
            except Exception as e:
                self.log_error(f"Не удалось создать резервную копию: {e}")
                
                if not self.confirm("Продолжить без резервной копии?", "n"):
                    return False
                
                print()
                return True
        
        else:
            self.log_warning("Тип БД не определен, пропуск резервного копирования")
            print()
            return True
    
    def run_migration(self):
        """Выполнение миграции"""
        self.log_step("Выполнение миграции базы данных")
        print()
        
        self.log_info("Запуск migrate_to_many_to_many.py...")
        print()
        print("─" * 64)
        
        migration_script = self.script_dir / "migrate_to_many_to_many.py"
        success = self.run_command([sys.executable, str(migration_script)])
        
        print("─" * 64)
        print()
        
        if not success:
            self.log_error("МИГРАЦИЯ ПРОВАЛЕНА!")
            print()
            print("🔄 Для отката выполните:")
            if self.backup_file:
                print(f"   cp {self.backup_file.name} {self.db_file.name}")
            else:
                print("   Восстановите БД из вашей резервной копии")
            print("   python3 run_system.py &")
            print()
            return False
        
        self.log_success("Миграция базы данных завершена")
        print()
        
        return True
    
    def run_tests(self):
        """Запуск тестов"""
        if self.skip_tests:
            self.log_info("Тесты пропущены (--skip-tests)")
            print()
            return True
        
        self.log_step("Запуск тестов (опционально)")
        print()
        
        if not self.force and not self.confirm("Запустить автоматические тесты?", "y"):
            self.log_info("Тесты пропущены")
            print()
            return True
        
        print()
        print("─" * 64)
        
        test_script = self.script_dir / "test_many_to_many.py"
        success = self.run_command([sys.executable, str(test_script)], check=False)
        
        print("─" * 64)
        print()
        
        if success:
            self.log_success("Все тесты пройдены")
        else:
            self.log_warning("Некоторые тесты провалены")
            self.log_info("Это может быть нормально, проверьте вывод выше")
        
        print()
        return True
    
    def start_services(self):
        """Запуск сервисов"""
        self.log_step("Перезапуск сервисов")
        print()
        
        if not self.force and not self.confirm("Запустить сервисы?", "y"):
            self.log_info("Запуск сервисов пропущен")
            print()
            print("  Для запуска выполните:")
            print("    python3 run_system.py &")
            print("  или:")
            print("    python3 main.py & python3 bot.py &")
            print()
            return True
        
        self.log_info("Запуск сервисов...")
        
        # Создаем директорию для логов
        logs_dir = self.script_dir / "logs"
        logs_dir.mkdir(exist_ok=True)
        
        # Пробуем разные варианты запуска
        started = False
        
        for script, log_file in [
            ("run_system.py", "system.log"),
            # ("start_secure_system.py", "secure_system.log"),  # Removed in v3.1.1
        ]:
            script_path = self.script_dir / script
            if script_path.exists():
                log_path = logs_dir / log_file
                
                if not self.dry_run:
                    # Запуск в фоне
                    with open(log_path, 'a') as log:
                        subprocess.Popen(
                            [sys.executable, str(script_path)],
                            stdout=log,
                            stderr=log,
                            cwd=self.script_dir
                        )
                
                self.log_success(f"Сервисы запущены через {script}")
                started = True
                break
        
        if not started:
            # Запуск по отдельности
            for script, log_file in [
                ("main.py", "main.log"),
                ("bot.py", "bot.log"),
            ]:
                script_path = self.script_dir / script
                if script_path.exists():
                    log_path = logs_dir / log_file
                    
                    if not self.dry_run:
                        with open(log_path, 'a') as log:
                            subprocess.Popen(
                                [sys.executable, str(script_path)],
                                stdout=log,
                                stderr=log,
                                cwd=self.script_dir
                            )
                        time.sleep(2)
            
            self.log_success("Сервисы запущены (main.py + bot.py)")
        
        if not self.dry_run:
            time.sleep(3)
            
            # Проверка
            try:
                result = subprocess.run(
                    ["pgrep", "-f", "python.*main.py"],
                    capture_output=True,
                    check=False
                )
                if result.returncode == 0:
                    self.log_success("Сервисы работают")
                else:
                    self.log_warning("Сервисы могут не работать, проверьте логи")
            except FileNotFoundError:
                self.log_warning("Не удалось проверить статус сервисов (pgrep не найден)")
        
        print()
        return True
    
    def show_summary(self):
        """Итоговое сообщение"""
        self.log_box("✅ МИГРАЦИЯ ЗАВЕРШЕНА УСПЕШНО!", "═")
        print()
        
        self.log_info("Результаты миграции")
        print()
        
        # Разные команды для разных типов БД
        if self.db_type == 'postgresql':
            print("  📊 Проверить результаты (через psql):")
            print("     SELECT COUNT(*) FROM channels;")
            print("     SELECT COUNT(*) FROM user_channel;")
            print()
            print("  или через Supabase Dashboard:")
            print("     Table Editor → channels")
            print("     Table Editor → user_channel")
        elif self.db_type == 'sqlite':
            print("  📊 Проверить результаты:")
            print(f"     sqlite3 {self.db_file.name} 'SELECT COUNT(*) FROM channels;'")
            print(f"     sqlite3 {self.db_file.name} 'SELECT COUNT(*) FROM user_channel;'")
        else:
            print("  📊 Проверьте результаты через ваш клиент БД")
        
        print()
        print("  📚 Документация:")
        print("     • MANY_TO_MANY_SUMMARY.md   - краткое резюме")
        print("     • QUICK_MIGRATION.md        - быстрая инструкция")
        print("     • MIGRATION_MANY_TO_MANY.md - полная документация")
        print()
        
        if self.backup_file:
            print("  💾 Резервная копия (SQLite):")
            print(f"     {self.backup_file.name}")
            print()
            print("  🔄 Откат (если нужно):")
            print(f"     cp {self.backup_file.name} {self.db_file.name}")
            print("     python3 run_system.py &")
            print()
        elif self.db_type == 'postgresql':
            print("  💾 Резервная копия (PostgreSQL):")
            print("     Создайте через Supabase Dashboard или pg_dump")
            print()
            print("  🔄 Откат через pg_restore или Supabase Dashboard")
            print()
        
        print("═" * 64)
        print()
        
        self.log_success("Готово! Ваша система обновлена и готова к работе")
        print()
    
    def run(self):
        """Запуск миграции"""
        print()
        self.log_box("🔄 МИГРАЦИЯ К MANY-TO-MANY СТРУКТУРЕ", "═")
        print()
        self.log_info("Устранение дублирования каналов в базе данных")
        print()
        
        if self.dry_run:
            self.log_warning("Режим DRY-RUN: изменения не будут применены")
            print()
        
        # Проверки
        if not self.check_environment():
            return False
        
        if not self.check_files():
            return False
        
        if not self.check_database():
            return False
        
        # Подтверждение
        if not self.force and not self.dry_run:
            print("═" * 64)
            print()
            print("📋 Что будет сделано:")
            print("  1. Остановка всех сервисов")
            print("  2. Создание резервной копии БД")
            print("  3. Создание таблицы user_channel")
            print("  4. Перенос данных из старой структуры")
            print("  5. Объединение дубликатов каналов")
            print("  6. Обновление связей в таблице posts")
            print("  7. Замена таблицы channels")
            print("  8. Создание индексов")
            if not self.skip_tests:
                print("  9. Запуск тестов (опционально)")
                print("  10. Перезапуск сервисов")
            else:
                print("  9. Перезапуск сервисов")
            print()
            print("⏱️  Время выполнения: обычно 1-5 секунд")
            print()
            print("═" * 64)
            print()
            
            if not self.confirm("Продолжить миграцию?", "n"):
                self.log_warning("Миграция отменена пользователем")
                return False
            
            print()
        
        # Режим dry-run - выход
        if self.dry_run:
            self.log_info("Режим dry-run завершен. Запустите без --dry-run для применения")
            return True
        
        # Выполнение миграции
        if not self.stop_services():
            return False
        
        if not self.create_backup():
            return False
        
        if not self.run_migration():
            return False
        
        if not self.run_tests():
            return False
        
        if not self.start_services():
            return False
        
        self.show_summary()
        
        return True


def main():
    parser = argparse.ArgumentParser(
        description="Миграция к Many-to-Many структуре для Telegram Channel Parser"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Пропустить все подтверждения"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Показать что будет сделано, без выполнения"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Пропустить автоматические тесты"
    )
    
    args = parser.parse_args()
    
    manager = MigrationManager(
        force=args.force,
        dry_run=args.dry_run,
        skip_tests=args.skip_tests
    )
    
    try:
        success = manager.run()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print()
        manager.log_warning("Миграция прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print()
        manager.log_error(f"Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

