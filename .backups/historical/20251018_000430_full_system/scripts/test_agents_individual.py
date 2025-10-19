#!/usr/bin/env python3
"""
Индивидуальное тестирование агентов LangChain
"""

import asyncio
import logging
import sys
import os

# Добавляем путь к модулям
sys.path.append('/app')

from langchain_agents.speaker_analyzer import SpeakerAnalyzerAgent
from langchain_agents.topic_extractor import TopicExtractorAgent
from langchain_agents.emotion_analyzer import EmotionAnalyzerAgent
from langchain_agents.key_moments import KeyMomentsAgent
from langchain_agents.timeline import TimelineBuilderAgent

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Тестовые данные
TEST_MESSAGES = """
[1] ilyasni (19:30): Привет всем! Как дела с проектом?
[2] matsony (19:31): Привет! У нас проблемы с авторизацией
[3] ilyasni (19:32): Какие именно проблемы?
[4] matsony (19:33): Не работает двухфакторная аутентификация
[5] nst_rght (19:35): У меня тоже проблемы с логином
[6] ilyasni (19:36): Понятно, нужно срочно исправить
[7] matsony (19:37): Да, это критично для безопасности
[8] ilyasni (19:38): Хорошо, займусь этим завтра
"""

async def test_speaker_analyzer():
    """Тест Speaker Analyzer агента"""
    logger.info("🧪 Тестирование Speaker Analyzer...")
    
    agent = SpeakerAnalyzerAgent()
    input_data = {
        "messages": TEST_MESSAGES,
        "assessment": {
            "detail_level": "standard",
            "dialogue_type": "discussion"
        }
    }
    
    try:
        result = await agent.ainvoke(input_data)
        logger.info(f"✅ Speaker Analyzer результат: {type(result)}")
        
        # Извлекаем данные из новой структуры
        if isinstance(result, dict) and 'pydantic_result' in result:
            pydantic_result = result['pydantic_result']
            processed_result = result['processed_result']
            logger.info(f"   Структура: pydantic_result + processed_result")
            
            if pydantic_result and hasattr(pydantic_result, 'speakers'):
                logger.info(f"   Участников найдено: {len(pydantic_result.speakers)}")
                for speaker in pydantic_result.speakers:
                    logger.info(f"   - {speaker.username}: {speaker.role}")
            elif processed_result and isinstance(processed_result, dict):
                speakers_list = processed_result.get('speakers', [])
                logger.info(f"   Участников найдено (processed): {len(speakers_list)}")
                for speaker in speakers_list:
                    logger.info(f"   - {speaker.get('username', 'unknown')}: {speaker.get('role', 'unknown')}")
            else:
                logger.error(f"   ❌ Нет поля speakers в результате")
        else:
            logger.error(f"   ❌ Неожиданная структура результата")
            
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка Speaker Analyzer: {e}")
        return None

async def test_topic_extractor():
    """Тест Topic Extractor агента"""
    logger.info("🧪 Тестирование Topic Extractor...")
    
    agent = TopicExtractorAgent()
    input_data = {
        "messages": TEST_MESSAGES,
        "assessment": {
            "detail_level": "standard",
            "dialogue_type": "discussion"
        }
    }
    
    try:
        result = await agent.ainvoke(input_data)
        logger.info(f"✅ Topic Extractor результат: {type(result)}")
        
        if hasattr(result, 'topics'):
            logger.info(f"   Тем найдено: {len(result.topics)}")
            for topic in result.topics:
                logger.info(f"   - {topic.name}: {topic.priority}")
        else:
            logger.error(f"   ❌ Нет поля topics в результате")
            
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка Topic Extractor: {e}")
        return None

async def test_emotion_analyzer():
    """Тест Emotion Analyzer агента"""
    logger.info("🧪 Тестирование Emotion Analyzer...")
    
    agent = EmotionAnalyzerAgent()
    input_data = {
        "messages": TEST_MESSAGES,
        "assessment": {
            "detail_level": "standard",
            "dialogue_type": "discussion"
        }
    }
    
    try:
        result = await agent.ainvoke(input_data)
        logger.info(f"✅ Emotion Analyzer результат: {type(result)}")
        
        if hasattr(result, 'overall_tone'):
            logger.info(f"   Тон: {result.overall_tone}")
            logger.info(f"   Атмосфера: {result.atmosphere}")
        else:
            logger.error(f"   ❌ Нет полей эмоций в результате")
            
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка Emotion Analyzer: {e}")
        return None

async def test_key_moments():
    """Тест Key Moments агента"""
    logger.info("🧪 Тестирование Key Moments...")
    
    agent = KeyMomentsAgent()
    input_data = {
        "messages": TEST_MESSAGES,
        "assessment": {
            "detail_level": "detailed",
            "dialogue_type": "discussion"
        },
        "topics": {
            "topics": [
                {"name": "Проблемы с авторизацией", "priority": "high"},
                {"name": "Безопасность", "priority": "high"}
            ]
        },
        "emotions": {
            "overall_tone": "neutral"
        }
    }
    
    try:
        result = await agent.ainvoke(input_data)
        logger.info(f"✅ Key Moments результат: {type(result)}")
        
        if hasattr(result, 'key_decisions'):
            logger.info(f"   Решений: {len(result.key_decisions)}")
            for decision in result.key_decisions:
                logger.info(f"   - {decision}")
        else:
            logger.error(f"   ❌ Нет поля key_decisions в результате")
            
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка Key Moments: {e}")
        return None

async def test_timeline_builder():
    """Тест Timeline Builder агента"""
    logger.info("🧪 Тестирование Timeline Builder...")
    
    agent = TimelineBuilderAgent()
    input_data = {
        "messages": TEST_MESSAGES,
        "assessment": {
            "detail_level": "detailed",
            "dialogue_type": "discussion"
        },
        "topics": {
            "topics": [
                {"name": "Проблемы с авторизацией", "priority": "high"}
            ]
        }
    }
    
    try:
        result = await agent.ainvoke(input_data)
        logger.info(f"✅ Timeline Builder результат: {type(result)}")
        
        if hasattr(result, 'timeline_events'):
            logger.info(f"   Событий: {len(result.timeline_events)}")
            for event in result.timeline_events:
                logger.info(f"   - {event.timestamp}: {event.event}")
        else:
            logger.error(f"   ❌ Нет поля timeline_events в результате")
            
        return result
    except Exception as e:
        logger.error(f"❌ Ошибка Timeline Builder: {e}")
        return None

async def main():
    """Главная функция тестирования"""
    logger.info("🚀 Начало индивидуального тестирования агентов")
    logger.info(f"📝 Тестовые сообщения: {len(TEST_MESSAGES.split(chr(10)))} строк")
    
    # Тестируем агентов последовательно
    results = {}
    
    results['speaker'] = await test_speaker_analyzer()
    results['topics'] = await test_topic_extractor()
    results['emotions'] = await test_emotion_analyzer()
    results['key_moments'] = await test_key_moments()
    results['timeline'] = await test_timeline_builder()
    
    # Итоговый отчет
    logger.info("📊 Итоговый отчет:")
    for agent_name, result in results.items():
        status = "✅" if result is not None else "❌"
        logger.info(f"   {status} {agent_name}: {'работает' if result else 'не работает'}")

if __name__ == "__main__":
    asyncio.run(main())
