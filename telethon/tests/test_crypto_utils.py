"""
Тесты для Crypto Utils
Шифрование чувствительных данных
"""

import pytest
from unittest.mock import patch
import os

from crypto_utils import CryptoManager, crypto_manager


@pytest.mark.unit
class TestCryptoManager:
    """Тесты для CryptoManager"""
    
    def test_crypto_manager_initialization(self):
        """Тест инициализации с ENCRYPTION_KEY из env"""
        with patch.dict(os.environ, {'ENCRYPTION_KEY': 'test_key_32_bytes_long_string!!'}):
            manager = CryptoManager()
            
            assert manager._fernet is not None
    
    def test_encrypt_decrypt_string(self):
        """Тест шифрования и дешифрования строки"""
        test_string = "sensitive_api_hash_123456"
        
        # Шифруем
        encrypted = crypto_manager.encrypt(test_string)
        
        # Проверяем что зашифровано (не plaintext)
        assert encrypted != test_string
        assert len(encrypted) > 0
        
        # Дешифруем
        decrypted = crypto_manager.decrypt(encrypted)
        
        # Должен совпадать с оригиналом
        assert decrypted == test_string
    
    def test_encrypt_empty_string(self):
        """Тест шифрования пустой строки"""
        encrypted = crypto_manager.encrypt("")
        
        assert encrypted == ""
    
    def test_decrypt_empty_string(self):
        """Тест дешифрования пустой строки"""
        decrypted = crypto_manager.decrypt("")
        
        assert decrypted == ""
    
    def test_hash_sensitive_data(self):
        """Тест маскирования чувствительных данных для логов"""
        sensitive = "secret_api_hash_1234567890"
        
        masked = crypto_manager.hash_sensitive_data(sensitive)
        
        # Должно показать только первые и последние символы
        assert masked.startswith("se")
        assert masked.endswith("90")
        assert "*" in masked
        
        # Оригинальная строка не должна быть видна полностью
        assert sensitive not in masked
    
    def test_hash_short_string(self):
        """Тест маскирования короткой строки"""
        short = "abc"
        
        masked = crypto_manager.hash_sensitive_data(short)
        
        # Короткая строка полностью маскируется
        assert masked == "***"
    
    def test_encrypt_decrypt_cyrillic(self):
        """Тест шифрования кириллицы"""
        cyrillic = "секретный_ключ_шифрования"
        
        encrypted = crypto_manager.encrypt(cyrillic)
        decrypted = crypto_manager.decrypt(encrypted)
        
        assert decrypted == cyrillic

