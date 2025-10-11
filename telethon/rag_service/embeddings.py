"""
Генерация embeddings для текстов

Поддерживает:
1. EmbeddingsGigaR через gpt2giga-proxy (основной)
2. sentence-transformers (fallback)
"""
import logging
import httpx
import tiktoken
from typing import List, Optional, Tuple
import config

logger = logging.getLogger(__name__)


class EmbeddingsService:
    """Сервис для генерации embeddings"""
    
    def __init__(self):
        """Инициализация сервиса embeddings"""
        self.gigachat_url = f"{config.GIGACHAT_PROXY_URL}/v1/embeddings"
        self.gigachat_enabled = config.GIGACHAT_ENABLED
        
        # Tokenizer для подсчета токенов (cl100k_base - для OpenAI-совместимых моделей)
        try:
            self.tokenizer = tiktoken.get_encoding("cl100k_base")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось загрузить tokenizer: {e}")
            self.tokenizer = None
        
        # Sentence-transformers для fallback (ленивая загрузка)
        self.sentence_transformer_model = None
        self.fallback_model_name = config.EMBEDDING_MODEL
        
        # Размерности векторов (определяются динамически при первом использовании)
        self.gigachat_vector_size = None
        self.fallback_vector_size = 768  # Известно для sentence-transformers
        
        logger.info(f"✅ Embeddings сервис инициализирован")
        logger.info(f"   GigaChat proxy: {self.gigachat_url} (enabled={self.gigachat_enabled})")
        logger.info(f"   Fallback model: {self.fallback_model_name}")
    
    def count_tokens(self, text: str) -> int:
        """
        Подсчитать количество токенов в тексте
        
        Args:
            text: Текст для подсчета
            
        Returns:
            Количество токенов
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Приблизительная оценка: 1 токен ≈ 4 символа
            return len(text) // 4
    
    def chunk_text(
        self,
        text: str,
        max_tokens: int,
        overlap_tokens: int
    ) -> List[Tuple[str, int, int]]:
        """
        Разбить текст на chunks с overlap
        
        Args:
            text: Текст для разбиения
            max_tokens: Максимальное количество токенов в chunk
            overlap_tokens: Количество токенов для overlap
            
        Returns:
            Список кортежей (chunk_text, start_pos, end_pos)
        """
        if not text or not text.strip():
            return []
        
        total_tokens = self.count_tokens(text)
        
        # Если текст короче max_tokens, возвращаем его целиком
        if total_tokens <= max_tokens:
            return [(text, 0, len(text))]
        
        # Разбиваем на chunks
        chunks = []
        
        if self.tokenizer:
            # Используем tokenizer для точного разбиения
            tokens = self.tokenizer.encode(text)
            
            start = 0
            while start < len(tokens):
                end = min(start + max_tokens, len(tokens))
                chunk_tokens = tokens[start:end]
                chunk_text = self.tokenizer.decode(chunk_tokens)
                
                # Определяем позицию в оригинальном тексте (приблизительно)
                char_start = len(self.tokenizer.decode(tokens[:start]))
                char_end = len(self.tokenizer.decode(tokens[:end]))
                
                chunks.append((chunk_text, char_start, char_end))
                
                # Двигаемся вперед с учетом overlap
                start = end - overlap_tokens if end < len(tokens) else end
        else:
            # Простое разбиение по символам (fallback)
            chars_per_chunk = max_tokens * 4  # Приблизительно
            overlap_chars = overlap_tokens * 4
            
            start = 0
            while start < len(text):
                end = min(start + chars_per_chunk, len(text))
                chunk_text = text[start:end]
                chunks.append((chunk_text, start, end))
                
                start = end - overlap_chars if end < len(text) else end
        
        logger.debug(f"Текст разбит на {len(chunks)} chunks (max_tokens={max_tokens}, overlap={overlap_tokens})")
        return chunks
    
    async def generate_embedding_gigachat(self, text: str) -> Optional[List[float]]:
        """
        Генерация embedding через GigaChat (gpt2giga-proxy)
        
        Args:
            text: Текст для embeddings
            
        Returns:
            Вектор embeddings или None при ошибке
        """
        if not self.gigachat_enabled:
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.gigachat_url,
                    json={
                        "input": text,
                        "model": "EmbeddingsGigaR"  # Модель для embeddings в GigaChat
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ GigaChat embeddings error {response.status_code}: {response.text[:200]}")
                    return None
                
                result = response.json()
                embedding = result["data"][0]["embedding"]
                
                # Сохраняем размерность при первом запросе
                if self.gigachat_vector_size is None:
                    self.gigachat_vector_size = len(embedding)
                    logger.info(f"✅ GigaChat vector size: {self.gigachat_vector_size}")
                
                return embedding
                
        except Exception as e:
            logger.error(f"❌ Ошибка GigaChat embeddings: {e}")
            return None
    
    def _load_sentence_transformer(self):
        """Ленивая загрузка sentence-transformers модели"""
        if self.sentence_transformer_model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"📥 Загрузка fallback модели: {self.fallback_model_name}")
                self.sentence_transformer_model = SentenceTransformer(self.fallback_model_name)
                logger.info(f"✅ Fallback модель загружена")
            except ImportError:
                logger.warning("⚠️ sentence-transformers не установлен. Fallback недоступен.")
                logger.warning("   Установите: pip install sentence-transformers torch")
                return
            except Exception as e:
                logger.error(f"❌ Ошибка загрузки fallback модели: {e}")
                return
    
    async def generate_embedding_fallback(self, text: str) -> Optional[List[float]]:
        """
        Генерация embedding через sentence-transformers (fallback)
        
        Args:
            text: Текст для embeddings
            
        Returns:
            Вектор embeddings или None при ошибке
        """
        try:
            self._load_sentence_transformer()
            
            if self.sentence_transformer_model is None:
                return None
            
            # Генерируем embedding
            embedding = self.sentence_transformer_model.encode(
                text,
                convert_to_numpy=True,
                show_progress_bar=False
            )
            
            return embedding.tolist()
            
        except Exception as e:
            logger.error(f"❌ Ошибка fallback embeddings: {e}")
            return None
    
    async def generate_embedding(self, text: str) -> Optional[Tuple[List[float], str]]:
        """
        Генерация embedding с автоматическим fallback
        
        Args:
            text: Текст для embeddings
            
        Returns:
            Кортеж (вектор embeddings, провайдер) или None при ошибке
        """
        if not text or not text.strip():
            logger.warning("⚠️ Пустой текст для embeddings")
            return None
        
        # Пробуем GigaChat
        if self.gigachat_enabled:
            embedding = await self.generate_embedding_gigachat(text)
            if embedding:
                return embedding, "gigachat"
            else:
                logger.warning("⚠️ GigaChat embeddings не удался, используем fallback")
        
        # Fallback на sentence-transformers
        embedding = await self.generate_embedding_fallback(text)
        if embedding:
            return embedding, "sentence-transformers"
        
        logger.error("❌ Не удалось сгенерировать embeddings ни одним провайдером")
        return None
    
    async def generate_embeddings_batch(
        self,
        texts: List[str]
    ) -> List[Optional[Tuple[List[float], str]]]:
        """
        Batch генерация embeddings
        
        Args:
            texts: Список текстов
            
        Returns:
            Список embeddings (или None для ошибок)
        """
        results = []
        
        # TODO: Оптимизировать batch processing для GigaChat API
        # Пока делаем последовательно
        for text in texts:
            result = await self.generate_embedding(text)
            results.append(result)
        
        return results
    
    def get_chunking_params(self, provider: str = "gigachat") -> Tuple[int, int]:
        """
        Получить параметры chunking для провайдера
        
        Args:
            provider: Провайдер embeddings (gigachat или sentence-transformers)
            
        Returns:
            Кортеж (max_tokens, overlap_tokens)
        """
        if provider == "gigachat":
            return (
                config.EMBEDDING_MAX_TOKENS_GIGACHAT,
                config.EMBEDDING_OVERLAP_TOKENS_GIGACHAT
            )
        else:
            return (
                config.EMBEDDING_MAX_TOKENS_FALLBACK,
                config.EMBEDDING_OVERLAP_TOKENS_FALLBACK
            )


# Глобальный экземпляр сервиса
embeddings_service = EmbeddingsService()

