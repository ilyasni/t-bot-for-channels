#!/usr/bin/env python3
"""
Тест полного пайплайна генерации дайджеста
"""

import asyncio
import logging
import sys
import os

# Добавляем путь к модулям
sys.path.append('/app')

from langchain_agents.orchestrator import DigestOrchestrator

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Тестовые данные (реальные сообщения из группы)
TEST_MESSAGES = [
    type('Message', (), {
        'text': 'Привет всем! Как дела с проектом?',
        'sender': type('Sender', (), {'username': 'ilyasni', 'first_name': 'Ilya'}),
        'date': type('Date', (), {'strftime': lambda fmt: '19:30'})
    })(),
    type('Message', (), {
        'text': 'Привет! У нас проблемы с авторизацией',
        'sender': type('Sender', (), {'username': 'matsony', 'first_name': 'Matsony'}),
        'date': type('Date', (), {'strftime': lambda fmt: '19:31'})
    })(),
    type('Message', (), {
        'text': 'Какие именно проблемы?',
        'sender': type('Sender', (), {'username': 'ilyasni', 'first_name': 'Ilya'}),
        'date': type('Date', (), {'strftime': lambda fmt: '19:32'})
    })(),
    type('Message', (), {
        'text': 'Не работает двухфакторная аутентификация',
        'sender': type('Sender', (), {'username': 'matsony', 'first_name': 'Matsony'}),
        'date': type('Date', (), {'strftime': lambda fmt: '19:33'})
    })(),
    type('Message', (), {
        'text': 'У меня тоже проблемы с логином',
        'sender': type('Sender', (), {'username': 'nst_rght', 'first_name': 'NST'}),
        'date': type('Date', (), {'strftime': lambda fmt: '19:35'})
    })(),
    type('Message', (), {
        'text': 'Понятно, нужно срочно исправить',
        'sender': type('Sender', (), {'username': 'ilyasni', 'first_name': 'Ilya'}),
        'date': type('Date', (), {'strftime': lambda fmt: '19:36'})
    })(),
    type('Message', (), {
        'text': 'Да, это критично для безопасности',
        'sender': type('Sender', (), {'username': 'matsony', 'first_name': 'Matsony'}),
        'date': type('Date', (), {'strftime': lambda fmt: '19:37'})
    })(),
    type('Message', (), {
        'text': 'Хорошо, займусь этим завтра',
        'sender': type('Sender', (), {'username': 'ilyasni', 'first_name': 'Ilya'}),
        'date': type('Date', (), {'strftime': lambda fmt: '19:38'})
    })(),
]

async def test_full_pipeline():
    """Тест полного пайплайна генерации дайджеста"""
    logger.info("🚀 Тестирование полного пайплайна генерации дайджеста")
    logger.info(f"📝 Тестовых сообщений: {len(TEST_MESSAGES)}")
    
    try:
        # Инициализация orchestrator
        orchestrator = DigestOrchestrator()
        logger.info("✅ Orchestrator инициализирован")
        
        # Генерация дайджеста
        result = await orchestrator.generate_digest(
            messages=TEST_MESSAGES,
            hours=24,
            user_id=19,
            group_id=1
        )
        
        # Анализ результата
        logger.info("📊 Результат генерации:")
        logger.info(f"   Success: {result.get('success', False)}")
        logger.info(f"   Execution time: {result.get('execution_time', 0):.2f}s")
        
        if result.get('success'):
            digest = result.get('digest')
            if digest:
                logger.info("✅ Дайджест сгенерирован успешно!")
                
                # Проверяем структуру дайджеста
                if isinstance(digest, dict):
                    logger.info("📄 Структура дайджеста:")
                    logger.info(f"   - html_digest: {len(digest.get('html_digest', ''))} символов")
                    logger.info(f"   - metadata: {'есть' if 'metadata' in digest else 'нет'}")
                    logger.info(f"   - sections: {'есть' if 'sections' in digest else 'нет'}")
                    
                    # Показываем HTML дайджест
                    html_digest = digest.get('html_digest', '')
                    if html_digest:
                        logger.info("📄 HTML дайджест:")
                        logger.info("=" * 50)
                        logger.info(html_digest)
                        logger.info("=" * 50)
                    else:
                        logger.warning("⚠️ HTML дайджест пустой")
                        
                    # Проверяем метаданные
                    metadata = digest.get('metadata', {})
                    if metadata:
                        logger.info("📊 Метаданные:")
                        logger.info(f"   - participants_count: {metadata.get('participants_count', 0)}")
                        logger.info(f"   - message_count: {metadata.get('message_count', 0)}")
                        logger.info(f"   - detail_level: {metadata.get('detail_level', 'unknown')}")
                        logger.info(f"   - dialogue_type: {metadata.get('dialogue_type', 'unknown')}")
                        
                        # Статус агентов
                        agents_status = metadata.get('agents_status', [])
                        logger.info(f"   - agents_status: {len(agents_status)} агентов")
                        
                        success_count = sum(1 for status in agents_status if status.get('status') == 'success')
                        error_count = sum(1 for status in agents_status if status.get('status') == 'error')
                        fallback_count = sum(1 for status in agents_status if status.get('status') == 'fallback')
                        
                        logger.info(f"     ✅ Успешно: {success_count}")
                        logger.info(f"     ❌ Ошибки: {error_count}")
                        logger.info(f"     🔄 Fallback: {fallback_count}")
                else:
                    logger.info(f"📄 Дайджест (тип: {type(digest)}):")
                    logger.info(str(digest)[:500] + "..." if len(str(digest)) > 500 else str(digest))
            else:
                logger.error("❌ Дайджест не сгенерирован")
        else:
            error = result.get('error', 'Unknown error')
            logger.error(f"❌ Ошибка генерации: {error}")
            
        return result
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка тестирования: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """Главная функция"""
    logger.info("🧪 Начало тестирования полного пайплайна")
    
    result = await test_full_pipeline()
    
    if result and result.get('success'):
        logger.info("🎉 ТЕСТ ПРОЙДЕН: Полный пайплайн работает корректно!")
    else:
        logger.error("💥 ТЕСТ НЕ ПРОЙДЕН: Есть проблемы в пайплайне")

if __name__ == "__main__":
    asyncio.run(main())
