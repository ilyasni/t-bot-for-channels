"""
Тесты для Voice Transcription Service
SaluteSpeech API integration для Premium/Enterprise
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from voice_transcription_service import VoiceTranscriptionService, SaluteSpeechClient


@pytest.mark.unit
@pytest.mark.voice
class TestSaluteSpeechClient:
    """Тесты для SaluteSpeech API client"""
    
    @pytest.fixture
    def salute_client(self, redis_client):
        """Fixture для SaluteSpeechClient"""
        with patch.dict('os.environ', {
            'SALUTESPEECH_CLIENT_ID': 'test_client_id',
            'SALUTESPEECH_CLIENT_SECRET': 'test_secret',
            'VOICE_TRANSCRIPTION_ENABLED': 'true'
        }), patch('voice_transcription_service.redis.Redis', return_value=redis_client):
            client = SaluteSpeechClient()
            client.redis_client = redis_client
            return client
    
    @pytest.mark.asyncio
    async def test_oauth_flow(self, salute_client):
        """Тест OAuth2 получения access token"""
        # Mock OAuth response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "access_token": "test_access_token_abc123",
            "expires_at": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp())
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            token = await salute_client.get_access_token()
            
            assert token == "test_access_token_abc123"
    
    @pytest.mark.asyncio
    async def test_upload_audio(self, salute_client):
        """Тест загрузки аудио файла"""
        audio_bytes = b"fake_audio_data_12345"
        
        # Mock upload response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "result": "uploaded_file_id_abc"
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            # Mock OAuth token
            with patch.object(salute_client, 'get_access_token', return_value="test_token"):
                file_id = await salute_client.upload_audio(audio_bytes)
                
                assert file_id == "uploaded_file_id_abc"
    
    @pytest.mark.asyncio
    async def test_async_recognize(self, salute_client):
        """Тест запуска асинхронного распознавания"""
        file_id = "test_file_id"
        
        # Mock recognize response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json = MagicMock(return_value={
            "result": "task_id_xyz789"
        })
        
        with patch('httpx.AsyncClient') as mock_httpx:
            mock_client = AsyncMock()
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_httpx.return_value = mock_client
            
            with patch.object(salute_client, 'get_access_token', return_value="test_token"):
                task_id = await salute_client.async_recognize(file_id)
                
                assert task_id == "task_id_xyz789"
    
    @pytest.mark.asyncio
    async def test_transcribe_full_workflow(self, salute_client):
        """Тест полного workflow транскрибации"""
        audio_bytes = b"test_audio"
        
        # Mock все этапы
        with patch.object(salute_client, 'upload_audio', return_value="file_123"), \
             patch.object(salute_client, 'async_recognize', return_value="task_456"), \
             patch.object(salute_client, 'poll_status', return_value={
                 "status": "DONE",
                 "response_file_id": "response_789"
             }), \
             patch.object(salute_client, 'download_result', return_value="транскрипция текста"):
            
            result = await salute_client.transcribe(audio_bytes)
            
            assert result == "транскрипция текста"


@pytest.mark.unit
@pytest.mark.voice
class TestVoiceTranscriptionService:
    """Тесты для VoiceTranscriptionService"""
    
    @pytest.fixture
    def voice_service(self, redis_client):
        """Fixture для VoiceTranscriptionService"""
        with patch('voice_transcription_service.SaluteSpeechClient'):
            service = VoiceTranscriptionService()
            service.salute_client = MagicMock()
            return service
    
    @pytest.mark.asyncio
    async def test_transcribe_voice_message(self, voice_service):
        """Тест транскрибации голосового сообщения"""
        audio_bytes = b"voice_data"
        duration = 10
        
        # Mock транскрибацию
        voice_service.salute_client.transcribe = AsyncMock(
            return_value="тестовая транскрипция"
        )
        
        result = await voice_service.transcribe_voice_message(audio_bytes, duration)
        
        assert result == "тестовая транскрипция"
    
    @pytest.mark.asyncio
    async def test_transcribe_duration_limit(self, voice_service):
        """Тест лимита длительности (60 секунд)"""
        audio_bytes = b"long_voice"
        duration = 120  # Превышает лимит
        
        # Должен вызвать ValueError
        with pytest.raises(ValueError, match="слишком длинное"):
            await voice_service.transcribe_voice_message(audio_bytes, duration)
    
    def test_is_enabled(self, voice_service):
        """Тест проверки доступности сервиса"""
        with patch.dict('os.environ', {'VOICE_TRANSCRIPTION_ENABLED': 'true'}):
            assert voice_service.is_enabled() is True
        
        with patch.dict('os.environ', {'VOICE_TRANSCRIPTION_ENABLED': 'false'}):
            # Пересоздаем сервис
            service = VoiceTranscriptionService()
            assert service.is_enabled() is False

