"""
Voice Transcription Service
Транскрибация голосовых сообщений через SaluteSpeech API
"""
import logging
import os
import base64
import hashlib
import json
import asyncio
import uuid
import httpx
import redis
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SaluteSpeechClient:
    """
    Клиент для работы с SaluteSpeech API
    
    Документация: https://developers.sber.ru/docs/ru/salutespeech/overview
    """
    
    def __init__(self):
        # Credentials
        self.client_id = os.getenv("SALUTESPEECH_CLIENT_ID")
        self.client_secret = os.getenv("SALUTESPEECH_CLIENT_SECRET")
        self.scope = os.getenv("SALUTESPEECH_SCOPE", "SALUTE_SPEECH_PERS")
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "SALUTESPEECH_CLIENT_ID и SALUTESPEECH_CLIENT_SECRET обязательны!\n"
                "Получите их в https://developers.sber.ru/studio"
            )
        
        # URLs
        self.oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        self.base_url = os.getenv(
            "SALUTESPEECH_URL",
            "https://smartspeech.sber.ru/rest/v1"
        )
        
        # Settings
        self.max_duration = int(os.getenv("VOICE_MAX_DURATION_SEC", "60"))
        self.timeout = 30
        self.poll_interval = 1  # Проверка статуса каждую секунду
        self.max_poll_attempts = 30  # Максимум 30 секунд на распознавание
        
        # Redis cache
        self.redis_client = redis.Redis(
            host=os.getenv("REDIS_HOST", "redis"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            decode_responses=True
        )
        self.cache_ttl = int(os.getenv("VOICE_CACHE_TTL", "86400"))  # 24 часа
        
        # Access token cache
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        logger.info("✅ SaluteSpeechClient инициализирован")
        logger.info(f"   Base URL: {self.base_url}")
        logger.info(f"   Max duration: {self.max_duration}s")
        logger.info(f"   Cache TTL: {self.cache_ttl}s")
    
    async def get_access_token(self) -> str:
        """
        Получить OAuth2 access token
        
        Token действует 30 минут, кешируем в памяти
        """
        # Проверяем кеш
        if self.access_token and self.token_expires_at:
            if datetime.now(timezone.utc) < self.token_expires_at:
                return self.access_token
        
        # Encode credentials в base64
        credentials = f"{self.client_id}:{self.client_secret}"
        credentials_b64 = base64.b64encode(credentials.encode()).decode()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.post(
                    self.oauth_url,
                    headers={
                        "Authorization": f"Basic {credentials_b64}",
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Accept": "application/json",
                        "RqUID": str(uuid.uuid4())  # Уникальный ID запроса
                    },
                    data={
                        "scope": self.scope
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                self.access_token = data["access_token"]
                # Token живет 30 минут, обновим за 1 минуту до истечения
                expires_in = data.get("expires_in", 1800)  # 30 минут
                from datetime import timedelta
                self.token_expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in - 60)
                
                logger.info(f"✅ SaluteSpeech access token получен (expires in {expires_in}s)")
                
                return self.access_token
        
        except Exception as e:
            logger.error(f"❌ Ошибка получения access token: {e}")
            raise
    
    async def upload_audio(self, audio_bytes: bytes) -> str:
        """
        Загрузить аудио файл
        
        Returns:
            request_file_id для дальнейшего использования
        """
        token = await self.get_access_token()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                # Multipart form data
                files = {
                    'audio_data': ('voice.ogg', audio_bytes, 'audio/ogg')
                }
                
                response = await client.post(
                    f"{self.base_url}/data:upload",
                    headers={
                        "Authorization": f"Bearer {token}"
                    },
                    files=files
                )
                
                response.raise_for_status()
                data = response.json()
                
                request_file_id = data["result"]["request_file_id"]
                
                logger.info(f"✅ Аудио загружено: {request_file_id}")
                
                return request_file_id
        
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки аудио: {e}")
            raise
    
    async def async_recognize(self, request_file_id: str) -> str:
        """
        Запустить асинхронное распознавание речи
        
        Returns:
            task_id для polling статуса
        """
        token = await self.get_access_token()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.post(
                    f"{self.base_url}/speech:async_recognize",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                        "RqUID": str(uuid.uuid4())
                    },
                    json={
                        "options": {
                            "audio_encoding": "OPUS",  # Попытка 1: OPUS без OGG_
                            "sample_rate": 48000,  # Telegram voice sample rate
                            "language": "ru-RU"  # Русский язык
                        },
                        "request_file_id": request_file_id
                    }
                )
                
                if response.status_code != 200:
                    logger.error(f"❌ Ошибка async_recognize: {response.status_code}")
                    logger.error(f"   Response body: {response.text}")
                    logger.error(f"   Request body: {json.dumps({'options': {'audio_encoding': 'OGG_OPUS', 'sample_rate': 48000, 'language': 'ru-RU'}, 'request_file_id': request_file_id})}")
                
                response.raise_for_status()
                data = response.json()
                
                task_id = data["result"]["id"]
                
                logger.info(f"✅ Распознавание запущено: task_id={task_id}")
                
                return task_id
        
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP ошибка запуска распознавания: {e}")
            logger.error(f"   Response text: {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка запуска распознавания: {e}")
            raise
    
    async def poll_status(self, task_id: str) -> Dict[str, Any]:
        """
        Polling статуса задачи распознавания
        
        Returns:
            Результат с response_file_id когда статус DONE
        """
        token = await self.get_access_token()
        
        for attempt in range(self.max_poll_attempts):
            try:
                async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                    response = await client.get(
                        f"{self.base_url}/task:get",
                        headers={
                            "Authorization": f"Bearer {token}"
                        },
                        params={
                            "id": task_id
                        }
                    )
                    
                    response.raise_for_status()
                    data = response.json()
                    
                    status = data["result"]["status"]
                    
                    if status == "DONE":
                        logger.info(f"✅ Распознавание завершено: {task_id}")
                        return data["result"]
                    
                    elif status == "ERROR":
                        error_msg = data["result"].get("error", "Unknown error")
                        logger.error(f"❌ Ошибка распознавания: {error_msg}")
                        raise Exception(f"Recognition failed: {error_msg}")
                    
                    # Status: NEW, PROCESSING - ждем
                    logger.debug(f"⏳ Статус: {status} (attempt {attempt + 1}/{self.max_poll_attempts})")
                    await asyncio.sleep(self.poll_interval)
            
            except httpx.HTTPStatusError as e:
                logger.error(f"❌ HTTP error при polling: {e}")
                raise
            except Exception as e:
                logger.error(f"❌ Ошибка polling: {e}")
                raise
        
        # Timeout
        raise TimeoutError(f"Recognition timeout after {self.max_poll_attempts}s")
    
    async def download_result(self, response_file_id: str) -> str:
        """
        Скачать результат распознавания
        
        Returns:
            Транскрибированный текст
        """
        token = await self.get_access_token()
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.get(
                    f"{self.base_url}/data:download",
                    headers={
                        "Authorization": f"Bearer {token}"
                    },
                    params={
                        "response_file_id": response_file_id
                    }
                )
                
                response.raise_for_status()
                data = response.json()
                
                # SaluteSpeech возвращает список с одним элементом
                if isinstance(data, list) and len(data) > 0:
                    # Берем первый элемент списка
                    result_data = data[0]
                    
                    # Внутри есть "results" список
                    results = result_data.get("results", [])
                    
                    if not results:
                        logger.warning("⚠️ Пустой результат распознавания")
                        return ""
                    
                    # Берем первый результат
                    first_result = results[0]
                    
                    # Используем normalized_text (с пунктуацией и заглавными буквами)
                    transcription = first_result.get("normalized_text", first_result.get("text", ""))
                    
                    logger.info(f"✅ Транскрипция получена: {transcription}")
                    
                    return transcription
                
                else:
                    logger.error(f"❌ Неожиданная структура ответа: {type(data)}")
                    logger.error(f"   Data: {json.dumps(data, ensure_ascii=False)[:500]}")
                    return ""
        
        except Exception as e:
            logger.error(f"❌ Ошибка скачивания результата: {e}")
            raise
    
    async def transcribe(self, audio_bytes: bytes) -> str:
        """
        Полный цикл транскрибации с кешированием
        
        Args:
            audio_bytes: Аудио файл в байтах
            
        Returns:
            Транскрибированный текст
        """
        # 1. Проверка кеша
        audio_hash = hashlib.md5(audio_bytes).hexdigest()
        cache_key = f"voice_transcription:{audio_hash}"
        
        cached = self.redis_client.get(cache_key)
        if cached:
            logger.info(f"✅ Транскрипция из кеша: {audio_hash[:8]}...")
            return cached
        
        logger.info(f"🎤 Начало транскрибации (размер: {len(audio_bytes) / 1024:.1f} KB)")
        
        try:
            # 2. Upload audio
            request_file_id = await self.upload_audio(audio_bytes)
            
            # 3. Start recognition
            task_id = await self.async_recognize(request_file_id)
            
            # 4. Poll status
            result = await self.poll_status(task_id)
            
            # 5. Download result
            response_file_id = result.get("response_file_id")
            if not response_file_id:
                raise ValueError("No response_file_id in result")
            
            transcription = await self.download_result(response_file_id)
            
            if not transcription:
                logger.warning("⚠️ Пустая транскрипция")
                return ""
            
            # 6. Сохранить в кеш
            self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                transcription
            )
            
            logger.info(f"✅ Транскрипция завершена и закеширована")
            
            return transcription
        
        except TimeoutError as e:
            logger.error(f"⏰ Timeout транскрибации: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка транскрибации: {e}")
            raise


class VoiceTranscriptionService:
    """
    Сервис для транскрибации голосовых сообщений Telegram
    """
    
    def __init__(self):
        self.enabled = os.getenv("VOICE_TRANSCRIPTION_ENABLED", "true").lower() == "true"
        
        if not self.enabled:
            logger.warning("⚠️ Voice transcription DISABLED (VOICE_TRANSCRIPTION_ENABLED=false)")
            self.client = None
            return
        
        try:
            self.client = SaluteSpeechClient()
            logger.info("✅ VoiceTranscriptionService инициализирован")
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации SaluteSpeech: {e}")
            self.enabled = False
            self.client = None
    
    async def transcribe_voice_message(self, audio_bytes: bytes, duration_seconds: int) -> Optional[str]:
        """
        Транскрибировать голосовое сообщение
        
        Args:
            audio_bytes: Аудио файл в байтах
            duration_seconds: Длительность голосового в секундах
            
        Returns:
            Транскрибированный текст или None при ошибке
        """
        if not self.enabled or not self.client:
            logger.warning("⚠️ Voice transcription disabled")
            return None
        
        # Проверка длительности
        max_duration = self.client.max_duration
        if duration_seconds > max_duration:
            logger.warning(f"⚠️ Голосовое слишком длинное: {duration_seconds}s > {max_duration}s")
            raise ValueError(f"Максимальная длительность: {max_duration} секунд")
        
        try:
            transcription = await self.client.transcribe(audio_bytes)
            
            if not transcription:
                logger.warning("⚠️ Пустая транскрипция")
                return None
            
            return transcription
        
        except TimeoutError:
            logger.error("⏰ Timeout транскрибации")
            raise
        except Exception as e:
            logger.error(f"❌ Ошибка транскрибации: {e}")
            raise
    
    def is_enabled(self) -> bool:
        """Проверка доступности сервиса"""
        return self.enabled and self.client is not None


# Singleton instance
voice_transcription_service = VoiceTranscriptionService()

