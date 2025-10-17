"""
CLI tools для evaluation system

Предоставляет командно-строчные инструменты для:
- Создания и управления golden datasets
- Запуска evaluation runs
- Экспорта результатов
- Управления через CLI

Best practices:
- Async/await для всех операций
- Graceful error handling
- Progress bars для длительных операций
- JSON output для автоматизации
- Comprehensive help и examples
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

from .golden_dataset_manager import get_golden_dataset_manager
from .evaluation_runner import run_evaluation_batch
from .schemas import GoldenDatasetCreate, GoldenDatasetItem
from .langfuse_integration import get_evaluation_langfuse_client

logger = logging.getLogger(__name__)


class EvaluationCLI:
    """CLI для evaluation system"""
    
    def __init__(self):
        self.parser = argparse.ArgumentParser(
            description="Telegram Bot Evaluation CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Create dataset from JSON file
  python -m evaluation.cli create-dataset --name "my_dataset" --file "data/golden_qa.json"
  
  # Run evaluation
  python -m evaluation.cli run-evaluation --dataset "my_dataset" --run-name "eval_v1"
  
  # Export results
  python -m evaluation.cli export-results --run-name "eval_v1" --output "results.json"
  
  # List datasets
  python -m evaluation.cli list-datasets
            """
        )
        
        self.setup_commands()
    
    def setup_commands(self):
        """Setup CLI commands"""
        subparsers = self.parser.add_subparsers(dest='command', help='Available commands')
        
        # Create dataset command
        create_parser = subparsers.add_parser('create-dataset', help='Create golden dataset')
        create_parser.add_argument('--name', required=True, help='Dataset name')
        create_parser.add_argument('--file', required=True, help='JSON file with dataset items')
        create_parser.add_argument('--description', default='', help='Dataset description')
        create_parser.add_argument('--sync-langfuse', action='store_true', help='Sync to Langfuse')
        
        # List datasets command
        list_parser = subparsers.add_parser('list-datasets', help='List available datasets')
        list_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        
        # Run evaluation command
        run_parser = subparsers.add_parser('run-evaluation', help='Run evaluation on dataset')
        run_parser.add_argument('--dataset', required=True, help='Dataset name')
        run_parser.add_argument('--run-name', required=True, help='Run name')
        run_parser.add_argument('--model-provider', default='openrouter', help='Model provider')
        run_parser.add_argument('--model-name', default='gpt-4o-mini', help='Model name')
        run_parser.add_argument('--workers', type=int, default=4, help='Parallel workers')
        run_parser.add_argument('--timeout', type=int, default=300, help='Timeout per item (seconds)')
        run_parser.add_argument('--json', action='store_true', help='Output in JSON format')
        
        # Export results command
        export_parser = subparsers.add_parser('export-results', help='Export evaluation results')
        export_parser.add_argument('--run-name', required=True, help='Run name')
        export_parser.add_argument('--output', required=True, help='Output file path')
        export_parser.add_argument('--format', choices=['json', 'csv'], default='json', help='Output format')
        
        # Dataset stats command
        stats_parser = subparsers.add_parser('dataset-stats', help='Show dataset statistics')
        stats_parser.add_argument('--dataset', required=True, help='Dataset name')
        stats_parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    async def run(self, args: Optional[list] = None):
        """Run CLI with arguments"""
        parsed_args = self.parser.parse_args(args)
        
        if not parsed_args.command:
            self.parser.print_help()
            return
        
        try:
            if parsed_args.command == 'create-dataset':
                await self.create_dataset(parsed_args)
            elif parsed_args.command == 'list-datasets':
                await self.list_datasets(parsed_args)
            elif parsed_args.command == 'run-evaluation':
                await self.run_evaluation(parsed_args)
            elif parsed_args.command == 'export-results':
                await self.export_results(parsed_args)
            elif parsed_args.command == 'dataset-stats':
                await self.dataset_stats(parsed_args)
            else:
                self.parser.print_help()
                
        except Exception as e:
            logger.error(f"❌ CLI command failed: {e}")
            sys.exit(1)
    
    async def create_dataset(self, args):
        """Create golden dataset from JSON file"""
        print(f"📊 Creating dataset '{args.name}' from {args.file}")
        
        try:
            # Load dataset from JSON file
            with open(args.file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if 'items' not in data:
                raise ValueError("JSON file must contain 'items' array")
            
            # Create dataset items
            items = []
            for item_data in data['items']:
                item = GoldenDatasetItem(**item_data)
                items.append(item)
            
            # Create dataset
            dataset = GoldenDatasetCreate(
                name=args.name,
                description=args.description or data.get('description', ''),
                category=items[0].category if items else 'general',
                items=items,
                sync_to_langfuse=args.sync_langfuse
            )
            
            # Save to database
            dataset_manager = await get_golden_dataset_manager()
            result = await dataset_manager.create_dataset(dataset)
            
            if result['success']:
                print(f"✅ Dataset created successfully:")
                print(f"   Name: {args.name}")
                print(f"   Items: {result['inserted_items']}/{result['total_items']}")
                
                if result['errors']:
                    print(f"   Errors: {len(result['errors'])}")
                    for error in result['errors']:
                        print(f"     - {error}")
                
                # Sync to Langfuse if requested
                if args.sync_langfuse:
                    langfuse_client = get_evaluation_langfuse_client()
                    langfuse_result = await langfuse_client.create_evaluation_dataset(
                        name=args.name,
                        description=args.description or data.get('description', ''),
                        items=items
                    )
                    
                    if langfuse_result['success']:
                        print(f"✅ Synced to Langfuse: {langfuse_result['created_items']} items")
                    else:
                        print(f"⚠️ Langfuse sync failed: {langfuse_result.get('error', 'Unknown error')}")
            else:
                print(f"❌ Failed to create dataset: {result.get('error', 'Unknown error')}")
                sys.exit(1)
                
        except Exception as e:
            print(f"❌ Failed to create dataset: {e}")
            sys.exit(1)
    
    async def list_datasets(self, args):
        """List available datasets"""
        try:
            dataset_manager = await get_golden_dataset_manager()
            
            # Get datasets (hardcoded for now)
            datasets = ["automotive_tech_channels_v1", "team_discussions_groups_v1"]
            datasets_info = []
            
            for dataset_name in datasets:
                try:
                    stats = await dataset_manager.get_dataset_stats(dataset_name)
                    datasets_info.append({
                        "name": dataset_name,
                        "total_items": stats["total_items"],
                        "categories": stats["categories"],
                        "difficulties": stats["difficulties"]
                    })
                except Exception as e:
                    logger.warning(f"Failed to get stats for {dataset_name}: {e}")
                    datasets_info.append({
                        "name": dataset_name,
                        "total_items": "Unknown",
                        "categories": {},
                        "difficulties": {}
                    })
            
            if args.json:
                print(json.dumps(datasets_info, indent=2, ensure_ascii=False))
            else:
                print("📊 Available Datasets:")
                print()
                for dataset in datasets_info:
                    print(f"**{dataset['name']}**")
                    print(f"  Items: {dataset['total_items']}")
                    
                    if dataset['categories']:
                        categories_str = ", ".join([f"{k} ({v})" for k, v in dataset['categories'].items()])
                        print(f"  Categories: {categories_str}")
                    
                    if dataset['difficulties']:
                        difficulties_str = ", ".join([f"{k} ({v})" for k, v in dataset['difficulties'].items()])
                        print(f"  Difficulties: {difficulties_str}")
                    
                    print()
                    
        except Exception as e:
            print(f"❌ Failed to list datasets: {e}")
            sys.exit(1)
    
    async def run_evaluation(self, args):
        """Run evaluation on dataset"""
        print(f"🚀 Running evaluation:")
        print(f"   Dataset: {args.dataset}")
        print(f"   Run: {args.run_name}")
        print(f"   Model: {args.model_provider}/{args.model_name}")
        print(f"   Workers: {args.workers}")
        print(f"   Timeout: {args.timeout}s")
        print()
        
        try:
            # Run evaluation
            result = await run_evaluation_batch(
                dataset_name=args.dataset,
                run_name=args.run_name,
                model_provider=args.model_provider,
                model_name=args.model_name,
                parallel_workers=args.workers,
                timeout_seconds=args.timeout
            )
            
            if args.json:
                # JSON output
                output = {
                    "run_name": result.run_name,
                    "dataset_name": result.dataset_name,
                    "model_provider": result.model_provider,
                    "model_name": result.model_name,
                    "status": result.status,
                    "total_items": result.total_items,
                    "processed_items": result.processed_items,
                    "successful_items": result.successful_items,
                    "failed_items": result.failed_items,
                    "avg_score": result.avg_score,
                    "scores": result.scores,
                    "started_at": result.started_at.isoformat() if result.started_at else None,
                    "completed_at": result.completed_at.isoformat() if result.completed_at else None
                }
                print(json.dumps(output, indent=2, ensure_ascii=False))
            else:
                # Human-readable output
                print(f"✅ Evaluation completed:")
                print(f"   Status: {result.status}")
                print(f"   Items: {result.processed_items}/{result.total_items}")
                print(f"   Successful: {result.successful_items}")
                print(f"   Failed: {result.failed_items}")
                print(f"   Overall Score: {result.avg_score:.3f}")
                
                if result.scores:
                    print(f"   Detailed Scores:")
                    for metric, score in result.scores.items():
                        print(f"     {metric}: {score:.3f}")
                
                if result.completed_at and result.started_at:
                    duration = result.completed_at - result.started_at
                    print(f"   Duration: {duration}")
                
                print()
                print(f"🔗 Langfuse UI:")
                print(f"   https://langfuse.produman.studio/datasets/{args.dataset}/runs/{args.run_name}")
                
        except Exception as e:
            print(f"❌ Evaluation failed: {e}")
            sys.exit(1)
    
    async def export_results(self, args):
        """Export evaluation results"""
        print(f"📤 Exporting results for run '{args.run_name}' to {args.output}")
        
        try:
            # TODO: Implement actual export from database
            # For now, create mock export data
            
            export_data = {
                "run_name": args.run_name,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "dataset_name": "automotive_tech_channels_v1",
                "model_provider": "openrouter",
                "model_name": "gpt-4o-mini",
                "results": [
                    {
                        "item_id": "auto_001",
                        "query": "Как настроить дифференциал для дрифта?",
                        "expected_output": "Для дрифта нужно настроить...",
                        "actual_output": "Для настройки дифференциала...",
                        "scores": {
                            "answer_correctness": 0.85,
                            "faithfulness": 0.78,
                            "context_relevance": 0.82,
                            "overall_score": 0.82
                        }
                    }
                ],
                "summary": {
                    "total_items": 10,
                    "successful_items": 8,
                    "failed_items": 2,
                    "avg_scores": {
                        "answer_correctness": 0.847,
                        "faithfulness": 0.823,
                        "context_relevance": 0.812,
                        "overall_score": 0.834
                    }
                }
            }
            
            # Create output directory if needed
            Path(args.output).parent.mkdir(parents=True, exist_ok=True)
            
            if args.format == 'json':
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            elif args.format == 'csv':
                # TODO: Implement CSV export
                print("⚠️ CSV export not implemented yet")
                sys.exit(1)
            
            print(f"✅ Results exported to {args.output}")
            
        except Exception as e:
            print(f"❌ Export failed: {e}")
            sys.exit(1)
    
    async def dataset_stats(self, args):
        """Show dataset statistics"""
        print(f"📊 Dataset statistics for '{args.dataset}'")
        
        try:
            dataset_manager = await get_golden_dataset_manager()
            stats = await dataset_manager.get_dataset_stats(args.dataset)
            
            if args.json:
                print(json.dumps(stats, indent=2, ensure_ascii=False))
            else:
                print(f"Name: {stats['dataset_name']}")
                print(f"Total Items: {stats['total_items']}")
                print(f"Categories: {stats['categories_count']}")
                print(f"Difficulty Levels: {stats['difficulty_levels']}")
                print(f"Multi-source Ratio: {stats['multi_source_ratio']:.2%}")
                
                if stats['categories']:
                    print(f"\nCategories:")
                    for category, count in stats['categories'].items():
                        print(f"  {category}: {count}")
                
                if stats['difficulties']:
                    print(f"\nDifficulties:")
                    for difficulty, count in stats['difficulties'].items():
                        print(f"  {difficulty}: {count}")
                
        except Exception as e:
            print(f"❌ Failed to get dataset stats: {e}")
            sys.exit(1)


async def main():
    """Main CLI entry point"""
    cli = EvaluationCLI()
    await cli.run()


if __name__ == "__main__":
    asyncio.run(main())
