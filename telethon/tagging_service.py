import asyncio
import httpx
import json
import os
import logging
import re
from typing import List, Optional, Dict
from datetime import datetime, timezone
from database import SessionLocal
from models import Post
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaggingService:
    """Сервис для автоматического тегирования постов с использованием OpenRouter API"""
    
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        self.model = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-chat-v3.1:free")
        self.batch_size = int(os.getenv("TAGGING_BATCH_SIZE", "10"))
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # HTTP Transport с встроенным retry для сетевых ошибок
        self.transport = httpx.AsyncHTTPTransport(retries=3)
        
        # Fallback модели (по приоритету)
        self.fallback_models = [
            "deepseek/deepseek-chat-v3.1:free",
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "qwen/qwen-2-7b-instruct:free",
            "google/gemma-2-9b-it:free"
        ]
        
        # Retry настройки
        self.max_retries = int(os.getenv("TAGGING_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("TAGGING_RETRY_DELAY", "2.0"))  # секунды
        self.max_retry_attempts = int(os.getenv("TAGGING_MAX_ATTEMPTS", "5"))  # общее кол-во попыток для поста
        
        if not self.api_key or self.api_key == "your_openrouter_api_key_here":
            logger.warning("⚠️ TaggingService: OPENROUTER_API_KEY не установлен. Тегирование отключено.")
            self.enabled = False
        else:
            self.enabled = True
            logger.info(f"✅ TaggingService: Инициализирован с моделью {self.model}")
            logger.info(f"🔄 TaggingService: Fallback модели: {', '.join(self.fallback_models[:2])}")
            
            # Предупреждение о нестабильных моделях
            if self.model.startswith("deepseek"):
                logger.warning(f"⚠️ TaggingService: Модель {self.model} может быть нестабильной")
                logger.warning(f"💡 Рекомендуется: OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free")
            elif self.model.startswith("openai/gpt-oss"):
                logger.warning(f"⚠️ TaggingService: Модель {self.model} устарела и может не работать")
                logger.warning(f"💡 Рекомендуется: OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free")
    
    async def generate_tags_for_text(self, text: str, retry_count: int = 0) -> Optional[List[str]]:
        """
        Генерация тегов для текста с использованием LLM с retry и fallback механизмом
        
        Args:
            text: Текст поста для анализа
            retry_count: Номер попытки (для внутреннего использования)
            
        Returns:
            Список тегов или None в случае ошибки
        """
        if not self.enabled:
            logger.debug("TaggingService: Сервис тегирования отключен")
            return None
        
        if not text or len(text.strip()) < 10:
            logger.debug("TaggingService: Текст слишком короткий для тегирования")
            return []
        
        # Определяем модель для текущей попытки
        current_model = self.model
        if retry_count > 0 and retry_count <= len(self.fallback_models):
            current_model = self.fallback_models[retry_count - 1]
            logger.info(f"🔄 TaggingService: Попытка {retry_count + 1}, используем fallback модель: {current_model}")
        
        try:
            prompt = f"""Проанализируй следующий текст и определи 3-7 релевантных тегов для классификации.

Текст:
{text[:2000]}

Требования к тегам:
- Теги должны быть на русском языке
- Теги должны быть короткими (1-2 слова)
- Теги должны отражать основную тематику текста
- Избегай слишком общих тегов

ВАЖНО: Верни ТОЛЬКО JSON массив тегов, без markdown, без пояснений, без дополнительного текста.
Формат ответа: ["тег1", "тег2", "тег3"]

Пример:
["технологии", "искусственный интеллект", "новости"]"""

            async with httpx.AsyncClient(transport=self.transport, timeout=30.0) as client:
                response = await client.post(
                    self.api_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": current_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.3,
                        "max_tokens": 150
                    }
                )
                
                if response.status_code != 200:
                    error_msg = f"API Error {response.status_code}: {response.text[:200]}"
                    logger.error(f"❌ TaggingService: Ошибка API: {response.status_code} - {response.text[:500]}")
                    
                    # Retry для 5xx ошибок
                    if response.status_code >= 500 and retry_count < self.max_retries:
                        delay = self.retry_delay * (2 ** retry_count)  # Экспоненциальная задержка
                        logger.info(f"⏳ TaggingService: Retry через {delay:.1f}с...")
                        await asyncio.sleep(delay)
                        return await self.generate_tags_for_text(text, retry_count + 1)
                    
                    return None
                
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # Проверяем что content не пустой
                if not content or content.strip() == "":
                    error_detail = result.get("error", {})
                    logger.error("❌ TaggingService: API вернул пустой ответ")
                    logger.error(f"Полный ответ API: {json.dumps(result, ensure_ascii=False)[:500]}")
                    
                    # Retry если это временная ошибка
                    if retry_count < self.max_retries and error_detail.get("code") in [502, 503, 504]:
                        delay = self.retry_delay * (2 ** retry_count)
                        logger.info(f"⏳ TaggingService: Retry через {delay:.1f}с...")
                        await asyncio.sleep(delay)
                        return await self.generate_tags_for_text(text, retry_count + 1)
                    
                    return None
                
                # Сохраняем оригинальный ответ для логирования
                original_content = content
                
                # Парсим JSON ответ
                # Убираем возможные markdown блоки
                content = content.strip()
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                    content = content.strip()
                
                # Удаляем префиксы типа "json" после ```
                if content.startswith("json"):
                    content = content[4:].strip()
                
                # Пытаемся найти JSON массив в тексте (используем жадный поиск для полного массива)
                # Ищем массив от первой [ до последней ]
                json_match = re.search(r'\[.*\]', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                else:
                    # Если не нашли массив, логируем полный ответ
                    logger.error(f"❌ TaggingService: Не найден JSON массив в ответе")
                    logger.error(f"Оригинальный ответ: {original_content[:300]}")
                    return None
                
                # Очищаем от возможных trailing запятых перед закрывающей скобкой
                content = re.sub(r',\s*\]', ']', content)
                
                # Пытаемся распарсить JSON
                tags = json.loads(content)
                
                if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
                    # Очистка и валидация тегов
                    tags = [tag.strip().lower() for tag in tags if tag.strip()]
                    tags = tags[:7]  # Максимум 7 тегов
                    logger.info(f"✅ TaggingService: Сгенерировано {len(tags)} тегов")
                    return tags
                else:
                    logger.error(f"❌ TaggingService: Неверный формат ответа: {content}")
                    return None
                    
        except json.JSONDecodeError as e:
            logger.error(f"❌ TaggingService: Ошибка парсинга JSON: {str(e)}")
            try:
                logger.error(f"Проблемный ответ API: {original_content[:300] if 'original_content' in locals() else content[:300]}")
            except:
                logger.error("Не удалось вывести ответ API")
            
            # Рекомендация по смене модели
            if self.model.startswith("deepseek"):
                logger.warning(f"⚠️ Модель {self.model} может быть нестабильной. Попробуйте: google/gemini-2.0-flash-exp:free")
            
            return None
        except httpx.TimeoutException:
            logger.error("❌ TaggingService: Превышено время ожидания API")
            return None
        except Exception as e:
            logger.error(f"❌ TaggingService: Ошибка генерации тегов: {str(e)}")
            return None
    
    async def update_post_tags(self, post_id: int, db: SessionLocal = None, force_retry: bool = False) -> bool:
        """
        Обновление тегов для конкретного поста с отслеживанием статуса
        
        Args:
            post_id: ID поста
            db: Сессия базы данных (опционально)
            force_retry: Принудительный retry (игнорирует max_retry_attempts)
            
        Returns:
            True если теги успешно обновлены, False в противном случае
        """
        if not self.enabled:
            return False
        
        close_db = False
        if db is None:
            db = SessionLocal()
            close_db = True
        
        try:
            post = db.query(Post).filter(Post.id == post_id).first()
            if not post:
                logger.warning(f"⚠️ TaggingService: Пост {post_id} не найден")
                return False
            
            # Проверяем количество попыток (если не force_retry)
            if not force_retry and post.tagging_attempts >= self.max_retry_attempts:
                logger.warning(f"⚠️ TaggingService: Пост {post_id} превысил лимит попыток ({self.max_retry_attempts})")
                post.tagging_status = "failed"
                db.commit()
                return False
            
            if not post.text:
                logger.debug(f"TaggingService: Пост {post_id} не содержит текста")
                post.tagging_status = "skipped"
                db.commit()
                return False
            
            # Обновляем счетчик попыток и время
            post.tagging_attempts += 1
            post.last_tagging_attempt = datetime.now(timezone.utc)
            post.tagging_status = "retrying" if post.tagging_attempts > 1 else "pending"
            db.commit()
            
            # Генерируем теги
            tags = await self.generate_tags_for_text(post.text)
            
            if tags is not None:
                post.tags = tags
                post.tagging_status = "success"
                post.tagging_error = None
                db.commit()
                logger.info(f"✅ TaggingService: Пост {post_id} обновлен с тегами: {tags}")
                return True
            else:
                post.tagging_status = "failed" if post.tagging_attempts >= self.max_retry_attempts else "retrying"
                post.tagging_error = "Failed to generate tags"
                db.commit()
                logger.warning(f"⚠️ TaggingService: Не удалось сгенерировать теги для поста {post_id} (попытка {post.tagging_attempts})")
                return False
                
        except Exception as e:
            db.rollback()
            logger.error(f"❌ TaggingService: Ошибка обновления тегов для поста {post_id}: {str(e)}")
            try:
                post = db.query(Post).filter(Post.id == post_id).first()
                if post:
                    post.tagging_status = "failed" if post.tagging_attempts >= self.max_retry_attempts else "retrying"
                    post.tagging_error = str(e)[:500]
                    db.commit()
            except:
                pass
            return False
        finally:
            if close_db:
                db.close()
    
    async def process_posts_batch(self, post_ids: List[int], delay_between_requests: float = 1.0):
        """
        Пакетная обработка постов для генерации тегов
        
        Args:
            post_ids: Список ID постов для обработки
            delay_between_requests: Задержка между запросами в секундах (для rate limiting)
        """
        if not self.enabled:
            logger.info("TaggingService: Тегирование отключено")
            return
        
        if not post_ids:
            logger.debug("TaggingService: Нет постов для обработки")
            return
        
        logger.info(f"🏷️ TaggingService: Начинаем обработку {len(post_ids)} постов")
        
        db = SessionLocal()
        try:
            success_count = 0
            failed_count = 0
            
            for i, post_id in enumerate(post_ids):
                try:
                    logger.debug(f"TaggingService: Обработка поста {i+1}/{len(post_ids)} (ID: {post_id})")
                    
                    success = await self.update_post_tags(post_id, db)
                    
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                    
                    # Задержка между запросами для соблюдения rate limits
                    if i < len(post_ids) - 1:
                        await asyncio.sleep(delay_between_requests)
                        
                except Exception as e:
                    logger.error(f"❌ TaggingService: Ошибка обработки поста {post_id}: {str(e)}")
                    failed_count += 1
            
            logger.info(
                f"✅ TaggingService: Обработка завершена. "
                f"Успешно: {success_count}, Ошибок: {failed_count}"
            )
            
        except Exception as e:
            logger.error(f"❌ TaggingService: Критическая ошибка пакетной обработки: {str(e)}")
        finally:
            db.close()
    
    async def retry_failed_posts(self, user_id: Optional[int] = None, limit: int = 50, force: bool = False):
        """
        Повторная генерация тегов для постов с ошибками
        
        Args:
            user_id: ID пользователя (если указан, обрабатывать только его посты)
            limit: Максимальное количество постов для обработки
            force: Принудительный retry даже для постов с превышенным лимитом попыток
        """
        if not self.enabled:
            logger.info("TaggingService: Тегирование отключено")
            return
        
        db = SessionLocal()
        try:
            # Ищем посты со статусом failed или retrying
            query = db.query(Post).filter(
                Post.tagging_status.in_(["failed", "retrying"]),
                Post.text != None
            )
            
            if user_id:
                query = query.filter(Post.user_id == user_id)
            
            if not force:
                # Только посты, не превысившие лимит попыток
                query = query.filter(Post.tagging_attempts < self.max_retry_attempts)
            
            posts = query.limit(limit).all()
            post_ids = [post.id for post in posts]
            
            if post_ids:
                logger.info(f"🔄 TaggingService: Найдено {len(post_ids)} постов с ошибками тегирования")
                logger.info(f"   Режим: {'принудительный' if force else 'обычный'}")
                
                success_count = 0
                failed_count = 0
                
                for post_id in post_ids:
                    success = await self.update_post_tags(post_id, db, force_retry=force)
                    if success:
                        success_count += 1
                    else:
                        failed_count += 1
                    
                    # Задержка между запросами
                    await asyncio.sleep(1.0)
                
                logger.info(
                    f"✅ TaggingService: Retry завершен. "
                    f"Успешно: {success_count}, Ошибок: {failed_count}"
                )
            else:
                logger.info("TaggingService: Нет постов с ошибками для повторной обработки")
                
        except Exception as e:
            logger.error(f"❌ TaggingService: Ошибка retry failed posts: {str(e)}")
        finally:
            db.close()
    
    async def tag_posts_without_tags(self, user_id: Optional[int] = None, limit: int = 100):
        """
        Тегирование постов без тегов
        
        Args:
            user_id: ID пользователя (если указан, обрабатывать только его посты)
            limit: Максимальное количество постов для обработки
        """
        if not self.enabled:
            return
        
        db = SessionLocal()
        try:
            query = db.query(Post).filter(Post.tags == None, Post.text != None)
            
            if user_id:
                query = query.filter(Post.user_id == user_id)
            
            posts = query.limit(limit).all()
            post_ids = [post.id for post in posts]
            
            if post_ids:
                logger.info(f"🏷️ TaggingService: Найдено {len(post_ids)} постов без тегов")
                await self.process_posts_batch(post_ids)
            else:
                logger.info("TaggingService: Все посты уже имеют теги")
                
        except Exception as e:
            logger.error(f"❌ TaggingService: Ошибка получения постов без тегов: {str(e)}")
        finally:
            db.close()


# Глобальный экземпляр сервиса
tagging_service = TaggingService()


# Функция для фонового запуска тегирования
async def tag_new_posts_background(post_ids: List[int]):
    """
    Фоновая задача для тегирования новых постов
    
    Args:
        post_ids: Список ID новых постов
    """
    if post_ids:
        logger.info(f"🏷️ Запуск фонового тегирования для {len(post_ids)} постов")
        await tagging_service.process_posts_batch(post_ids)


if __name__ == "__main__":
    # Тестирование сервиса
    async def test():
        service = TaggingService()
        test_text = """
        Новый искусственный интеллект от OpenAI может генерировать изображения 
        по текстовому описанию. Технология использует диффузионные модели и 
        обучена на миллионах изображений.
        """
        tags = await service.generate_tags_for_text(test_text)
        print(f"Сгенерированные теги: {tags}")
    
    asyncio.run(test())

