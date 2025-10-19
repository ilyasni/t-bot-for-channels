#!/usr/bin/env python3
"""
CLI инструмент для управления evaluation system

Поддерживает:
- Создание и управление golden datasets
- Запуск batch evaluation
- Просмотр результатов evaluation
- Экспорт/импорт данных

Использование:
    python cli.py dataset list
    python cli.py dataset create --name my_dataset --file dataset.json
    python cli.py evaluation run --dataset my_dataset --model gpt-4
    python cli.py evaluation results --run-id abc123
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent.parent))

try:
    from evaluation.golden_dataset_manager import GoldenDatasetManager
    from evaluation.schemas import GoldenDatasetCreate, GoldenDatasetItem
except ImportError:
    # Fallback для случаев когда модули не найдены
    from golden_dataset_manager import GoldenDatasetManager
    from schemas import GoldenDatasetCreate, GoldenDatasetItem

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class EvaluationCLI:
    """CLI для управления evaluation system"""
    
    def __init__(self):
        # Заменяем supabase-db на localhost для CLI
        database_url = os.getenv(
            "TELEGRAM_DATABASE_URL", 
            "postgresql://postgres:password@localhost:5432/postgres"
        )
        # Заменяем имя контейнера на localhost
        if "supabase-db:5432" in database_url:
            database_url = database_url.replace("supabase-db:5432", "localhost:5432")
        
        self.database_url = database_url
        self.dataset_manager = GoldenDatasetManager(self.database_url)
    
    async def init_database(self):
        """Инициализация базы данных"""
        try:
            await self.dataset_manager.initialize()
            logger.info("✅ База данных инициализирована")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации БД: {e}")
            raise
    
    async def list_datasets(self):
        """Список всех golden datasets"""
        try:
            datasets = await self.dataset_manager.list_datasets()
            if not datasets:
                print("📭 Golden datasets не найдены")
                return
            
            print("📊 Golden Datasets:")
            for dataset in datasets:
                print(f"  • {dataset['name']} (v{dataset['version']}) - {dataset['item_count']} items")
                print(f"    Описание: {dataset['description']}")
                print(f"    Создан: {dataset['created_at']}")
                print()
        except Exception as e:
            logger.error(f"❌ Ошибка получения списка datasets: {e}")
    
    async def create_dataset_from_file(self, name: str, file_path: str):
        """Создание dataset из JSON файла"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Валидация структуры
            if 'items' not in data:
                raise ValueError("Файл должен содержать поле 'items'")
            
            # Создание dataset
            dataset_create = GoldenDatasetCreate(
                name=name,
                description=data.get('description', ''),
                version=data.get('version', '1.0.0')
            )
            
            # Создание items
            items = []
            for item_data in data['items']:
                item = GoldenDatasetItem(**item_data)
                items.append(item)
            
            dataset_id = await self.dataset_manager.create_dataset(dataset_create)
            await self.dataset_manager.add_items(dataset_id, items)
            
            print(f"✅ Dataset '{name}' создан успешно (ID: {dataset_id})")
            print(f"   Добавлено {len(items)} items")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания dataset: {e}")
    
    async def export_dataset(self, name: str, output_file: str):
        """Экспорт dataset в JSON файл"""
        try:
            dataset = await self.dataset_manager.get_dataset_by_name(name)
            if not dataset:
                print(f"❌ Dataset '{name}' не найден")
                return
            
            items = await self.dataset_manager.get_dataset_items(dataset['id'])
            
            export_data = {
                "dataset_name": dataset['name'],
                "description": dataset['description'],
                "version": dataset['version'],
                "created_at": dataset['created_at'].isoformat(),
                "items": [
                    {
                        "question": item['question'],
                        "expected_answer": item['expected_answer'],
                        "contexts": item['contexts'],
                        "difficulty": item['difficulty'],
                        "category": item['category'],
                        "tags": item['tags']
                    }
                    for item in items
                ]
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            
            print(f"✅ Dataset '{name}' экспортирован в {output_file}")
            print(f"   Экспортировано {len(items)} items")
            
        except Exception as e:
            logger.error(f"❌ Ошибка экспорта dataset: {e}")
    
    async def run_evaluation(self, dataset_name: str, model_name: str = "gpt-4"):
        """Запуск evaluation на dataset"""
        try:
            # Здесь будет интеграция с EvaluationRunner
            print(f"🚀 Запуск evaluation на dataset '{dataset_name}' с моделью '{model_name}'")
            print("⚠️  Полная интеграция с EvaluationRunner будет добавлена позже")
            
            # Пока что просто показываем информацию о dataset
            dataset = await self.dataset_manager.get_dataset_by_name(dataset_name)
            if not dataset:
                print(f"❌ Dataset '{dataset_name}' не найден")
                return
            
            items = await self.dataset_manager.get_dataset_items(dataset['id'])
            print(f"📊 Dataset содержит {len(items)} items для evaluation")
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска evaluation: {e}")


def main():
    """Главная функция CLI"""
    parser = argparse.ArgumentParser(description="Evaluation System CLI")
    subparsers = parser.add_subparsers(dest='command', help='Доступные команды')
    
    # Dataset commands
    dataset_parser = subparsers.add_parser('dataset', help='Управление golden datasets')
    dataset_subparsers = dataset_parser.add_subparsers(dest='dataset_action')
    
    dataset_subparsers.add_parser('list', help='Список всех datasets')
    
    create_parser = dataset_subparsers.add_parser('create', help='Создать dataset из файла')
    create_parser.add_argument('--name', required=True, help='Имя dataset')
    create_parser.add_argument('--file', required=True, help='Путь к JSON файлу')
    
    export_parser = dataset_subparsers.add_parser('export', help='Экспорт dataset в файл')
    export_parser.add_argument('--name', required=True, help='Имя dataset')
    export_parser.add_argument('--output', required=True, help='Путь к выходному файлу')
    
    # Evaluation commands
    eval_parser = subparsers.add_parser('evaluation', help='Управление evaluation')
    eval_subparsers = eval_parser.add_subparsers(dest='eval_action')
    
    run_parser = eval_subparsers.add_parser('run', help='Запустить evaluation')
    run_parser.add_argument('--dataset', required=True, help='Имя dataset')
    run_parser.add_argument('--model', default='gpt-4', help='Модель для evaluation')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Инициализация CLI
    cli = EvaluationCLI()
    
    async def run_command():
        await cli.init_database()
        
        if args.command == 'dataset':
            if args.dataset_action == 'list':
                await cli.list_datasets()
            elif args.dataset_action == 'create':
                await cli.create_dataset_from_file(args.name, args.file)
            elif args.dataset_action == 'export':
                await cli.export_dataset(args.name, args.output)
            else:
                dataset_parser.print_help()
        
        elif args.command == 'evaluation':
            if args.eval_action == 'run':
                await cli.run_evaluation(args.dataset, args.model)
            else:
                eval_parser.print_help()
    
    # Запуск асинхронной команды
    try:
        asyncio.run(run_command())
    except KeyboardInterrupt:
        print("\n⏹️  Операция прервана пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()