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
    """Сервис для автоматического тегирования постов с использованием OpenRouter или GigaChat API"""
    
    def __init__(self):
        # Определяем провайдера (gigachat - основной, openrouter - fallback)
        self.provider = os.getenv("TAGGING_PROVIDER", "gigachat").lower()
        self.fallback_to_openrouter = os.getenv("TAGGING_FALLBACK_OPENROUTER", "true").lower() == "true"
        
        # OpenRouter настройки
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL", "google/gemini-2.0-flash-exp:free")
        self.openrouter_url = "https://openrouter.ai/api/v1/chat/completions"
        
        # GigaChat настройки (через gpt2giga-proxy)
        self.gigachat_proxy_url = os.getenv("GIGACHAT_PROXY_URL", "http://gpt2giga-proxy:8090")
        self.gigachat_url = f"{self.gigachat_proxy_url}/v1/chat/completions"
        # GigaChat Lite оптимален для тегирования: быстрее, дешевле, выше лимиты
        self.gigachat_model = os.getenv("GIGACHAT_MODEL", "GigaChat-Lite")
        
        # Выбираем API в зависимости от провайдера
        if self.provider == "gigachat":
            self.api_key = "dummy"  # GigaChat proxy не требует отдельного ключа
            self.api_url = self.gigachat_url
            self.model = self.gigachat_model
        else:
            self.api_key = self.openrouter_api_key
            self.api_url = self.openrouter_url
            self.model = self.openrouter_model
        
        self.batch_size = int(os.getenv("TAGGING_BATCH_SIZE", "10"))
        
        # HTTP Transport с встроенным retry для сетевых ошибок
        self.transport = httpx.AsyncHTTPTransport(retries=3)
        
        # Fallback модели (только для OpenRouter)
        self.fallback_models = [
            "google/gemini-2.0-flash-exp:free",
            "meta-llama/llama-3.2-3b-instruct:free",
            "qwen/qwen-2-7b-instruct:free",
            "google/gemma-2-9b-it:free"
        ]
        
        # Retry настройки
        self.max_retries = int(os.getenv("TAGGING_MAX_RETRIES", "3"))
        self.retry_delay = float(os.getenv("TAGGING_RETRY_DELAY", "2.0"))  # секунды
        self.max_retry_attempts = int(os.getenv("TAGGING_MAX_ATTEMPTS", "5"))  # общее кол-во попыток для поста
        
        # Проверяем доступность API
        if self.provider == "gigachat":
            # GigaChat - основной провайдер (не требует API ключа, работает через proxy)
            self.enabled = True
            logger.info(f"✅ TaggingService: Основной провайдер - GigaChat (через {self.gigachat_proxy_url})")
            logger.info(f"💡 TaggingService: Используется модель {self.model}")
            if self.model == "GigaChat-Lite":
                logger.info("⚡ GigaChat-Lite: быстрая модель с высокими лимитами - оптимально для тегирования")
            
            # Проверяем доступность fallback на OpenRouter
            if self.fallback_to_openrouter and self.openrouter_api_key and self.openrouter_api_key != "your_openrouter_api_key_here":
                logger.info(f"🔄 Fallback: OpenRouter ({self.openrouter_model}) - используется при ошибках GigaChat")
            elif self.fallback_to_openrouter:
                logger.warning("⚠️ Fallback на OpenRouter включен, но OPENROUTER_API_KEY не установлен")
                
        elif self.provider == "openrouter":
            # OpenRouter - вспомогательный провайдер
            if not self.api_key or self.api_key == "your_openrouter_api_key_here":
                logger.warning("⚠️ TaggingService: OPENROUTER_API_KEY не установлен. Тегирование отключено.")
                logger.warning("💡 Рекомендация: установите TAGGING_PROVIDER=gigachat (основной провайдер)")
                self.enabled = False
            else:
                self.enabled = True
                logger.info(f"✅ TaggingService: Основной провайдер - OpenRouter")
                logger.info(f"   Модель: {self.model}")
                logger.info(f"   Fallback модели: {', '.join(self.fallback_models[:2])}")
                
                # Предупреждение о лимитах бесплатных моделей
                if ":free" in self.model:
                    logger.warning("⚠️ TaggingService: Бесплатные модели имеют лимит 50 запросов/день")
                    logger.warning("💡 Рекомендация: TAGGING_PROVIDER=gigachat (лимит ~10,000/день)")
                
                # Предупреждение о нестабильных моделях
                if self.model.startswith("deepseek"):
                    logger.warning(f"⚠️ TaggingService: Модель {self.model} может быть нестабильной")
                    logger.warning(f"💡 Рекомендуется: OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free")
                elif self.model.startswith("openai/gpt-oss"):
                    logger.warning(f"⚠️ TaggingService: Модель {self.model} устарела и может не работать")
                    logger.warning(f"💡 Рекомендуется: OPENROUTER_MODEL=google/gemini-2.0-flash-exp:free")
        else:
            logger.error(f"❌ Неизвестный провайдер: {self.provider}")
            logger.error("💡 Доступные: gigachat (рекомендуется), openrouter")
            self.enabled = False
    
    async def generate_tags_for_text(self, text: str, retry_count: int = 0, use_fallback: bool = False) -> Optional[List[str]]:
        """
        Генерация тегов для текста с использованием LLM с retry и fallback механизмом
        
        Args:
            text: Текст поста для анализа
            retry_count: Номер попытки (для внутреннего использования)
            use_fallback: Использовать fallback провайдер (OpenRouter если основной GigaChat)
            
        Returns:
            Список тегов или None в случае ошибки
        """
        if not self.enabled:
            logger.debug("TaggingService: Сервис тегирования отключен")
            return None
        
        if not text or len(text.strip()) < 10:
            logger.debug("TaggingService: Текст слишком короткий для тегирования")
            return []
        
        # Определяем провайдер и модель для текущей попытки
        current_provider = self.provider
        current_api_url = self.api_url
        current_api_key = self.api_key
        current_model = self.model
        
        # Если используем fallback на OpenRouter (при ошибках GigaChat)
        if use_fallback and self.provider == "gigachat" and self.fallback_to_openrouter:
            if self.openrouter_api_key and self.openrouter_api_key != "your_openrouter_api_key_here":
                current_provider = "openrouter"
                current_api_url = self.openrouter_url
                current_api_key = self.openrouter_api_key
                current_model = self.openrouter_model
                logger.info(f"🔄 TaggingService: Используем fallback - OpenRouter ({current_model})")
            else:
                logger.warning("⚠️ Fallback на OpenRouter недоступен (нет API ключа)")
                return None
        
        # Fallback модели для OpenRouter (если основной провайдер OpenRouter)
        elif self.provider == "openrouter" and retry_count > 0 and retry_count <= len(self.fallback_models):
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
                    current_api_url,
                    headers={
                        "Authorization": f"Bearer {current_api_key}",
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
                    
                    # Обработка 429 Rate Limit
                    if response.status_code == 429:
                        try:
                            error_data = response.json()
                            reset_timestamp = error_data.get("error", {}).get("metadata", {}).get("headers", {}).get("X-RateLimit-Reset")
                            
                            if reset_timestamp:
                                reset_time = datetime.fromtimestamp(int(reset_timestamp) / 1000, timezone.utc)
                                now = datetime.now(timezone.utc)
                                wait_seconds = (reset_time - now).total_seconds()
                                
                                if wait_seconds > 0:
                                    logger.warning(f"⏰ TaggingService: Rate limit достигнут. Лимит сбросится {reset_time.strftime('%Y-%m-%d %H:%M:%S')} UTC")
                                    logger.warning(f"💡 Рекомендация: переключитесь на GigaChat или добавьте $10 credits в OpenRouter")
                                    
                                    # Если ожидание меньше 5 минут - ждем
                                    if wait_seconds <= 300:
                                        logger.info(f"⏳ Ожидаем {wait_seconds:.0f}с до сброса лимита...")
                                        await asyncio.sleep(wait_seconds + 5)  # +5 секунд запас
                                        return await self.generate_tags_for_text(text, retry_count + 1)
                            
                            # Если ожидание долгое или нет timestamp - пропускаем
                            logger.warning("⏸️ TaggingService: Rate limit превышен. Пост будет обработан при следующей попытке.")
                        except Exception as e:
                            logger.error(f"❌ Ошибка обработки 429: {e}")
                        
                        return None
                    
                    # Retry для 5xx ошибок
                    if response.status_code >= 500 and retry_count < self.max_retries:
                        delay = self.retry_delay * (2 ** retry_count)  # Экспоненциальная задержка
                        logger.info(f"⏳ TaggingService: Retry через {delay:.1f}с...")
                        await asyncio.sleep(delay)
                        return await self.generate_tags_for_text(text, retry_count + 1, use_fallback)
                    
                    # Fallback на OpenRouter если GigaChat не работает (только при серьезных ошибках)
                    if not use_fallback and self.provider == "gigachat" and self.fallback_to_openrouter:
                        if response.status_code in [502, 503, 504]:
                            logger.warning(f"⚠️ GigaChat недоступен ({response.status_code}), переключаемся на OpenRouter")
                            return await self.generate_tags_for_text(text, retry_count=0, use_fallback=True)
                    
                    return None
                
                result = response.json()
                content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
                
                # DEBUG: Логируем raw bytes для отладки проблем с кодировкой
                if content:
                    logger.debug(f"Raw content bytes (первые 100): {content.encode('utf-8')[:100]}")
                    logger.debug(f"Content type: {type(content)}, len={len(content)}")
                
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
                        return await self.generate_tags_for_text(text, retry_count + 1, use_fallback)
                    
                    # Fallback на OpenRouter если GigaChat вернул пустой ответ
                    if not use_fallback and self.provider == "gigachat" and self.fallback_to_openrouter:
                        logger.warning("⚠️ GigaChat вернул пустой ответ, переключаемся на OpenRouter")
                        return await self.generate_tags_for_text(text, retry_count=0, use_fallback=True)
                    
                    return None
                
                # Сохраняем оригинальный ответ для логирования
                original_content = content
                logger.debug(f"Step 0 - Original: {repr(content[:100])}")
                
                # Парсим JSON ответ
                # Убираем возможные markdown блоки
                content = content.strip()
                logger.debug(f"Step 1 - After strip: {repr(content[:100])}")
                
                if content.startswith("```"):
                    lines = content.split("\n")
                    content = "\n".join(lines[1:-1]) if len(lines) > 2 else content
                    content = content.strip()
                    logger.debug(f"Step 2 - After markdown removal: {repr(content[:100])}")
                
                # Удаляем префиксы типа "json" после ```
                if content.startswith("json"):
                    content = content[4:].strip()
                    logger.debug(f"Step 3 - After 'json' prefix removal: {repr(content[:100])}")
                
                # Пытаемся найти JSON массив в тексте
                # Используем НЕ-жадный квантификатор для точного поиска первого массива
                json_match = re.search(r'\[.*?\]', content, re.DOTALL)
                if json_match:
                    content = json_match.group(0)
                    logger.debug(f"Step 4 - After regex extract: {repr(content[:100])}")
                    logger.debug(f"         Content bytes: {content.encode('utf-8')[:100]}")
                else:
                    # Если не нашли массив, логируем полный ответ
                    logger.error(f"❌ TaggingService: Не найден JSON массив в ответе")
                    logger.error(f"Полный оригинальный ответ: {original_content[:500]}")
                    return None
                
                # Очищаем от возможных trailing запятых перед закрывающей скобкой
                before_sub = content
                content = re.sub(r',\s*\]', ']', content)
                if before_sub != content:
                    logger.debug(f"Step 5 - After trailing comma removal: {repr(content[:100])}")
                
                # КРИТИЧЕСКОЕ ИСПРАВЛЕНИЕ: Заменяем типографские кавычки на обычные
                # API может возвращать U+201C (") и U+201D (") вместо ASCII " (34)
                content = content.replace('\u201c', '"').replace('\u201d', '"')  # Двойные кавычки
                content = content.replace('\u2018', "'").replace('\u2019', "'")  # Одинарные кавычки (на всякий случай)
                logger.debug(f"Step 5b - After quote normalization: {repr(content[:100])}")
                logger.debug(f"         Quote check: {[ord(c) for c in content if ord(c) in [34, 8220, 8221]]}")
                
                # Пытаемся распарсить JSON
                try:
                    logger.debug(f"Step 6 - Trying json.loads()...")
                    tags = json.loads(content)
                    logger.debug(f"Step 7 - Success! Got {len(tags)} tags")
                except json.JSONDecodeError as json_err:
                    # Дополнительная отладочная информация
                    logger.error(f"❌ JSON decode error: {json_err}")
                    logger.error(f"Пытались распарсить: {repr(content[:200])}")
                    logger.error(f"Content length: {len(content)}, bytes length: {len(content.encode('utf-8'))}")
                    logger.error(f"First 50 chars: {[ord(c) for c in content[:50]]}")
                    logger.error(f"Полный ответ API: {repr(original_content[:500])}")
                    raise
                
                if isinstance(tags, list) and all(isinstance(tag, str) for tag in tags):
                    # Очистка и валидация тегов
                    cleaned_tags = []
                    seen_tags = set()  # Для отслеживания дубликатов
                    
                    for tag in tags:
                        tag_cleaned = tag.strip().lower()
                        # Пропускаем пустые теги и дубликаты
                        if tag_cleaned and tag_cleaned not in seen_tags:
                            # Дополнительная валидация: длина тега
                            if 2 <= len(tag_cleaned) <= 50:  # Минимум 2 символа, макс 50
                                cleaned_tags.append(tag_cleaned)
                                seen_tags.add(tag_cleaned)
                    
                    # Ограничиваем количество тегов
                    cleaned_tags = cleaned_tags[:7]  # Максимум 7 тегов
                    
                    if cleaned_tags:
                        logger.info(f"✅ TaggingService: Сгенерировано {len(cleaned_tags)} уникальных тегов")
                        return cleaned_tags
                    else:
                        logger.warning(f"⚠️ TaggingService: После очистки не осталось валидных тегов")
                        return []
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
            
            # Fallback на OpenRouter при timeout GigaChat
            if not use_fallback and self.provider == "gigachat" and self.fallback_to_openrouter:
                logger.warning("⚠️ GigaChat timeout, переключаемся на OpenRouter")
                return await self.generate_tags_for_text(text, retry_count=0, use_fallback=True)
            
            return None
        except Exception as e:
            logger.error(f"❌ TaggingService: Ошибка генерации тегов: {str(e)}")
            
            # Fallback на OpenRouter при критических ошибках GigaChat
            if not use_fallback and self.provider == "gigachat" and self.fallback_to_openrouter:
                logger.warning("⚠️ GigaChat ошибка, пробуем OpenRouter")
                return await self.generate_tags_for_text(text, retry_count=0, use_fallback=True)
            
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

