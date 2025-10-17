"""
Bot Evaluator с RAGAS integration

Оценивает качество ответов Telegram бота используя RAGAS metrics
и custom Telegram-specific метрики.

Best practices:
- Async/await для всех операций
- Graceful degradation если RAGAS недоступен
- Custom AspectCritic metrics для Telegram специфики
- LLM-as-Judge для оценки качества
- Context-aware evaluation для каналов и групп
"""

import logging
import time
import os
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

# RAGAS imports
try:
    from ragas import evaluate
    from ragas.metrics import (
        AnswerCorrectness,
        FactualCorrectness,
        Faithfulness,
        ContextRelevance,
        AspectCritic
    )
    from ragas.dataset import Dataset
    from ragas.llms import LangchainLLMWrapper
    RAGAS_AVAILABLE = True
except ImportError:
    RAGAS_AVAILABLE = False
    # Define dummy classes for when RAGAS is not available
    class LangchainLLMWrapper:
        def __init__(self, *args, **kwargs):
            pass
    logging.warning("⚠️ RAGAS not available - evaluation will be disabled")

# LangChain imports
from langchain_openai import ChatOpenAI
from langchain_community.llms import OpenAI

from .schemas import (
    GoldenDatasetItem,
    EvaluationResult,
    EvaluationMetrics,
    TelegramContext,
    ContextType
)
from .metrics import (
    observe_score,
    increment_counter,
    log_evaluation_metric_error,
    evaluation_answer_correctness,
    evaluation_faithfulness,
    evaluation_context_relevance,
    evaluation_channel_context_awareness,
    evaluation_group_synthesis_quality,
    evaluation_multi_source_coherence
)

logger = logging.getLogger(__name__)


class BotEvaluator:
    """Evaluator для оценки качества ответов бота"""
    
    def __init__(self, model_provider: str = "openrouter", model_name: str = "gpt-4o-mini"):
        """
        Initialize Bot Evaluator
        
        Args:
            model_provider: Провайдер модели (openrouter, openai, gigachat)
            model_name: Название модели
        """
        self.model_provider = model_provider
        self.model_name = model_name
        self.evaluator_llm = None
        self.ragas_llm = None
        self.ragas_metrics = []
        
        if not RAGAS_AVAILABLE:
            logger.error("❌ RAGAS not available - BotEvaluator disabled")
            return
            
        self._setup_evaluator_llm()
        self._setup_ragas_metrics()
        
    def _setup_evaluator_llm(self):
        """Setup LLM для evaluation"""
        try:
            if self.model_provider == "openrouter":
                # OpenRouter configuration
                self.evaluator_llm = ChatOpenAI(
                    model=self.model_name,
                    openai_api_base="https://openrouter.ai/api/v1",
                    openai_api_key=os.getenv("OPENROUTER_API_KEY"),
                    temperature=0.1,  # Low temperature для consistency
                    max_tokens=1000
                )
            elif self.model_provider == "openai":
                self.evaluator_llm = ChatOpenAI(
                    model=self.model_name,
                    openai_api_key=os.getenv("OPENAI_API_KEY"),
                    temperature=0.1,
                    max_tokens=1000
                )
            elif self.model_provider == "gigachat":
                # GigaChat через gpt2giga-proxy
                self.evaluator_llm = ChatOpenAI(
                    model="gpt-4o-mini",  # Fallback для compatibility
                    openai_api_base="http://gpt2giga-proxy:8000/v1",
                    openai_api_key="dummy-key",  # Not used by proxy
                    temperature=0.1,
                    max_tokens=1000
                )
            else:
                raise ValueError(f"Unsupported model provider: {self.model_provider}")
                
            # Wrap для RAGAS
            self.ragas_llm = LangchainLLMWrapper(llm=self.evaluator_llm)
            logger.info(f"✅ Evaluator LLM configured: {self.model_provider}/{self.model_name}")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup evaluator LLM: {e}")
            self.evaluator_llm = None
            self.ragas_llm = None
    
    def _setup_ragas_metrics(self):
        """Setup RAGAS metrics"""
        if not self.evaluator_llm:
            return
            
        try:
            # Standard RAGAS metrics
            self.ragas_metrics = [
                AnswerCorrectness(llm=self.ragas_llm),
                FactualCorrectness(llm=self.ragas_llm),
                Faithfulness(llm=self.ragas_llm),
                ContextRelevance(llm=self.ragas_llm),
                
                # Custom Telegram-specific metrics
                self._create_channel_context_awareness_metric(),
                self._create_group_synthesis_quality_metric(),
                self._create_multi_source_coherence_metric(),
                self._create_tone_appropriateness_metric()
            ]
            
            # Filter out None values (when RAGAS is not available)
            self.ragas_metrics = [metric for metric in self.ragas_metrics if metric is not None]
            
            logger.info(f"✅ RAGAS metrics configured: {len(self.ragas_metrics)} metrics")
            
        except Exception as e:
            logger.error(f"❌ Failed to setup RAGAS metrics: {e}")
            self.ragas_metrics = []
    
    def _create_channel_context_awareness_metric(self):
        """Custom metric: понимает ли бот специфику канала"""
        if not RAGAS_AVAILABLE or not self.ragas_llm:
            return None
        return AspectCritic(
            name="channel_context_awareness",
            definition="""
            Оцените понимание специфики Telegram канала в ответе бота.
            
            Верните 1.0 если ответ:
            - Демонстрирует понимание специфики канала (automotive, tech, programming)
            - Использует подходящую терминологию для аудитории
            - Учитывает технический уровень канала
            - Соответствует тону и стилю канала
            
            Верните 0.0 если ответ:
            - Игнорирует специфику канала
            - Использует неподходящую терминологию
            - Не соответствует техническому уровню аудитории
            - Игнорирует контекст канала
            
            Учитывайте: automotive (технические детали), tech (программирование), 
            programming (код примеры, best practices).
            """,
            llm=self.ragas_llm
        )
    
    def _create_group_synthesis_quality_metric(self):
        """Custom metric: качество синтеза group discussions"""
        if not RAGAS_AVAILABLE or not self.ragas_llm:
            return None
        return AspectCritic(
            name="group_synthesis_quality",
            definition="""
            Оцените качество синтеза обсуждений в Telegram группе.
            
            Верните 1.0 если дайджест:
            - Выделяет ключевые темы и решения
            - Идентифицирует основных участников и их вклад
            - Сохраняет эмоциональный тон обсуждения
            - Подчеркивает важные решения и action items
            - Структурирован логично и читабельно
            
            Верните 0.0 если дайджест:
            - Пропускает ключевые темы
            - Не структурирован
            - Теряет важные решения
            - Не учитывает контекст группы
            - Плохо читается
            
            Фокус на: синтез, структурирование, выделение главного.
            """,
            llm=self.ragas_llm
        )
    
    def _create_multi_source_coherence_metric(self):
        """Custom metric: согласованность при синтезе из разных каналов"""
        if not RAGAS_AVAILABLE or not self.ragas_llm:
            return None
        return AspectCritic(
            name="multi_source_coherence",
            definition="""
            Оцените согласованность при объединении информации из разных источников.
            
            Верните 1.0 если ответ:
            - Согласованно объединяет информацию из разных каналов
            - Не содержит противоречий между источниками
            - Логично связывает данные из разных источников
            - Создает единую картину без конфликтов
            
            Верните 0.0 если ответ:
            - Содержит противоречия между источниками
            - Плохо связывает информацию
            - Создает путаницу
            - Не может синтезировать разные точки зрения
            
            Фокус на: согласованность, отсутствие противоречий, логичность.
            """,
            llm=self.ragas_llm
        )
    
    def _create_tone_appropriateness_metric(self):
        """Custom metric: соответствие тона аудитории"""
        if not RAGAS_AVAILABLE or not self.ragas_llm:
            return None
        return AspectCritic(
            name="tone_appropriateness",
            definition="""
            Оцените соответствие тона ответа аудитории канала/группы.
            
            Верните 1.0 если тон:
            - Соответствует аудитории (technical, professional, casual)
            - Подходит для контекста (канал vs группа)
            - Сохраняет дружелюбность
            - Профессиональный для бизнес-контекста
            
            Верните 0.0 если тон:
            - Не подходит для аудитории
            - Слишком формальный/неформальный
            - Не соответствует контексту
            - Неуместный для канала/группы
            
            Учитывайте: technical (технический), professional (деловой), 
            casual (неформальный), friendly (дружелюбный).
            """,
            llm=self.ragas_llm
        )
    
    def evaluate_single_item(
        self,
        item: GoldenDatasetItem,
        actual_output: str,
        retrieved_contexts: Optional[List[str]] = None,
        timeout_seconds: int = 300
    ) -> EvaluationResult:
        """
        Оценить один элемент golden dataset с timeout pattern
        
        Args:
            item: Golden dataset item
            actual_output: Фактический ответ бота
            retrieved_contexts: Retrieved контексты (для RAG)
            timeout_seconds: Timeout для evaluation (default: 5 minutes)
            
        Returns:
            EvaluationResult с метриками
        """
        if not RAGAS_AVAILABLE or not self.ragas_metrics:
            return self._create_fallback_result(item, actual_output, "RAGAS not available")
        
        start_time = time.time()
        
        try:
            # Подготовить данные для RAGAS
            ragas_data = {
                "user_input": [item.query],
                "answer": [actual_output],
                "reference": [item.expected_output],
                "contexts": [retrieved_contexts or []]
            }
            
            # Создать EvaluationDataset
            dataset = EvaluationDataset.from_dict(ragas_data)
            
            # Запустить evaluation с timeout pattern (RAGAS best practice)
            result, error = self._evaluate_with_timeout(
                dataset=dataset,
                metrics=self.ragas_metrics,
                timeout_seconds=timeout_seconds
            )
            
            if error == "timeout":
                logger.warning(f"⏰ Evaluation timeout for item {item.item_id} after {timeout_seconds}s")
                return self._create_fallback_result(
                    item, actual_output, f"Evaluation timeout after {timeout_seconds}s"
                )
            elif error:
                logger.error(f"❌ Evaluation error for item {item.item_id}: {error}")
                return self._create_fallback_result(
                    item, actual_output, f"Evaluation error: {str(error)}"
                )
            
            # Извлечь scores
            scores = result.to_pandas().iloc[0].to_dict()
            
            # Создать EvaluationMetrics
            metrics = EvaluationMetrics(
                answer_correctness=scores.get('answer_correctness', 0.0),
                faithfulness=scores.get('faithfulness', 0.0),
                context_relevance=scores.get('context_relevance', 0.0),
                factual_correctness=scores.get('factual_correctness', 0.0),
                channel_context_awareness=scores.get('channel_context_awareness', 0.0),
                group_synthesis_quality=scores.get('group_synthesis_quality', 0.0),
                multi_source_coherence=scores.get('multi_source_coherence', 0.0),
                tone_appropriateness=scores.get('tone_appropriateness', 0.0),
                overall_score=self._calculate_overall_score(scores),
                evaluation_time=time.time() - start_time,
                model_used=f"{self.model_provider}/{self.model_name}"
            )
            
            # Обновить Prometheus metrics
            self._update_prometheus_metrics(metrics, item)
            
            # Создать результат
            result = EvaluationResult(
                item_id=item.item_id,
                query=item.query,
                expected_output=item.expected_output,
                actual_output=actual_output,
                metrics=metrics,
                retrieved_contexts=retrieved_contexts,
                telegram_context=item.telegram_context,
                debug_info={"scores": scores}
            )
            
            logger.info(f"✅ Evaluated item {item.item_id}: overall_score={metrics.overall_score:.3f}")
            return result
            
        except Exception as e:
            logger.error(f"❌ Evaluation failed for item {item.item_id}: {e}")
            return self._create_fallback_result(
                item, actual_output, f"Evaluation error: {str(e)}"
            )
    
    def _evaluate_with_timeout(self, dataset, metrics, timeout_seconds: int = 300):
        """
        Run evaluation with automatic timeout (RAGAS best practice)
        
        Args:
            dataset: RAGAS EvaluationDataset
            metrics: List of RAGAS metrics
            timeout_seconds: Timeout in seconds
            
        Returns:
            Tuple of (results, error) where error can be None, "timeout", or Exception
        """
        if not RAGAS_AVAILABLE:
            return None, "RAGAS not available"
        
        # Get cancellable executor
        executor = evaluate(dataset=dataset, metrics=metrics, return_executor=True)
        
        results = None
        exception = None
        
        def run_evaluation():
            nonlocal results, exception
            try:
                results = executor.results()
            except Exception as e:
                exception = e
        
        # Start evaluation in background thread
        thread = threading.Thread(target=run_evaluation)
        thread.start()
        
        # Wait for completion or timeout
        thread.join(timeout=timeout_seconds)
        
        if thread.is_alive():
            logger.warning(f"Evaluation exceeded {timeout_seconds}s timeout, cancelling...")
            executor.cancel()
            thread.join(timeout=10)  # Wait for cancellation
            return None, "timeout"
        
        if exception:
            return None, exception
        
        return results, None
    
    def _calculate_overall_score(self, scores: Dict[str, float]) -> float:
        """
        Вычислить общий score из всех метрик
        
        Args:
            scores: Dict с scores по метрикам
            
        Returns:
            Overall score (0.0-1.0)
        """
        # Веса для разных метрик
        weights = {
            'answer_correctness': 0.3,      # Основная метрика
            'faithfulness': 0.2,            # Важно для RAG
            'context_relevance': 0.15,      # Важно для поиска
            'factual_correctness': 0.15,    # Фактическая точность
            'channel_context_awareness': 0.1,  # Telegram специфика
            'group_synthesis_quality': 0.05,   # Для групп
            'multi_source_coherence': 0.03,    # Для multi-channel
            'tone_appropriateness': 0.02       # Дополнительно
        }
        
        weighted_sum = 0.0
        total_weight = 0.0
        
        for metric, weight in weights.items():
            if metric in scores and scores[metric] is not None:
                weighted_sum += scores[metric] * weight
                total_weight += weight
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
    
    def _update_prometheus_metrics(self, metrics: EvaluationMetrics, item: GoldenDatasetItem):
        """Обновить Prometheus metrics"""
        try:
            labels = {
                "dataset": item.dataset_name,
                "category": item.category,
                "model_provider": self.model_provider
            }
            
            # Update score distributions
            observe_score(
                evaluation_answer_correctness,
                metrics.answer_correctness,
                labels
            )
            
            observe_score(
                evaluation_faithfulness,
                metrics.faithfulness,
                labels
            )
            
            observe_score(
                evaluation_context_relevance,
                metrics.context_relevance,
                labels
            )
            
            observe_score(
                evaluation_channel_context_awareness,
                metrics.channel_context_awareness,
                labels
            )
            
            observe_score(
                evaluation_group_synthesis_quality,
                metrics.group_synthesis_quality,
                labels
            )
            
            observe_score(
                evaluation_multi_source_coherence,
                metrics.multi_source_coherence,
                labels
            )
            
        except Exception as e:
            log_evaluation_metric_error("prometheus_update", e)
    
    def _create_fallback_result(
        self,
        item: GoldenDatasetItem,
        actual_output: str,
        error_message: str
    ) -> EvaluationResult:
        """Создать fallback результат при ошибке"""
        fallback_metrics = EvaluationMetrics(
            answer_correctness=0.0,
            faithfulness=0.0,
            context_relevance=0.0,
            factual_correctness=0.0,
            channel_context_awareness=0.0,
            group_synthesis_quality=0.0,
            multi_source_coherence=0.0,
            tone_appropriateness=0.0,
            overall_score=0.0,
            evaluation_time=0.0,
            model_used=f"{self.model_provider}/{self.model_name}"
        )
        
        return EvaluationResult(
            item_id=item.item_id,
            query=item.query,
            expected_output=item.expected_output,
            actual_output=actual_output,
            metrics=fallback_metrics,
            telegram_context=item.telegram_context,
            error_message=error_message
        )


# ============================================================================
# Singleton Instance
# ============================================================================

_bot_evaluator: Optional[BotEvaluator] = None


def get_bot_evaluator(model_provider: str = "openrouter", model_name: str = "gpt-4o-mini") -> BotEvaluator:
    """
    Get singleton instance of Bot Evaluator
    
    Args:
        model_provider: Провайдер модели
        model_name: Название модели
        
    Returns:
        BotEvaluator instance
    """
    global _bot_evaluator
    
    if _bot_evaluator is None:
        _bot_evaluator = BotEvaluator(model_provider, model_name)
    
    return _bot_evaluator
