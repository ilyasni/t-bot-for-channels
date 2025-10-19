#!/usr/bin/env python3
"""
Простой тест для evaluation system
"""

import asyncio
import json
import os
import sys
from pathlib import Path

# Добавляем путь к модулям
sys.path.append(str(Path(__file__).parent))

from evaluation.golden_dataset_manager import GoldenDatasetManager
from evaluation.schemas import GoldenDatasetCreate, GoldenDatasetItem

async def test_evaluation():
    """Тест evaluation system"""
    
    # Database URL
    database_url = os.getenv(
        "TELEGRAM_DATABASE_URL", 
        "postgresql://postgres:xiNmSysbbcqTOWT4eb1KkQtM2fb8X7Ms@supabase-db:5432/postgres?sslmode=disable"
    )
    
    print(f"🔗 Подключение к БД: {database_url}")
    
    # Создаем manager
    manager = GoldenDatasetManager(database_url)
    
    try:
        # Подключаемся
        await manager.initialize()
        print("✅ Подключение к БД успешно")
        
        # Создаем тестовый item
        test_item = GoldenDatasetItem(
            question="Что такое ИИ?",
            expected_answer="Искусственный интеллект - это технология...",
            contexts=["ИИ - это технология", "Машинное обучение - часть ИИ"],
            difficulty="easy",
            category="technology",
            tags=["AI", "технологии"]
        )
        
        # Создаем тестовый dataset
        dataset_create = GoldenDatasetCreate(
            name="test_dataset",
            description="Тестовый dataset для проверки",
            version="1.0.0",
            category="technology",
            items=[test_item]
        )
        
        # Создаем dataset
        result = await manager.create_dataset(dataset_create)
        print(f"✅ Dataset создан: {result}")
        
        # Получаем список datasets
        datasets = await manager.list_datasets()
        print(f"📊 Найдено datasets: {len(datasets)}")
        for dataset in datasets:
            print(f"  • {dataset['name']} (v{dataset['version']})")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Закрываем соединение
        await manager.disconnect()
        print("✅ Соединение закрыто")

if __name__ == "__main__":
    asyncio.run(test_evaluation())
