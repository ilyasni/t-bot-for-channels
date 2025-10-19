"""
Модуль для шифрования чувствительных данных в БД
Использует Fernet для симметричного шифрования
"""

import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger(__name__)

class CryptoManager:
    """Менеджер для шифрования/дешифрования данных"""
    
    def __init__(self):
        self._fernet = None
        self._initialize_fernet()
    
    def _initialize_fernet(self):
        """Инициализация Fernet с ключом из переменных окружения"""
        try:
            # Получаем ключ из переменных окружения
            encryption_key = os.getenv("ENCRYPTION_KEY")
            
            if not encryption_key:
                # Генерируем новый ключ если его нет
                encryption_key = Fernet.generate_key()
                logger.warning(
                    "⚠️ ENCRYPTION_KEY не установлен в .env файле. "
                    "Сгенерирован новый ключ. Добавьте в .env файл:\n"
                    f"ENCRYPTION_KEY={encryption_key.decode()}"
                )
            else:
                # Конвертируем строку в байты если нужно
                if isinstance(encryption_key, str):
                    encryption_key = encryption_key.encode()
            
            self._fernet = Fernet(encryption_key)
            logger.info("✅ Криптографический менеджер инициализирован")
            
        except Exception as e:
            logger.error(f"❌ Ошибка инициализации криптографического менеджера: {str(e)}")
            raise
    
    def encrypt(self, data: str) -> str:
        """
        Шифрует строку
        
        Args:
            data: Строка для шифрования
            
        Returns:
            str: Зашифрованная строка в base64
        """
        try:
            if not data:
                return ""
            
            # Конвертируем строку в байты
            data_bytes = data.encode('utf-8')
            
            # Шифруем
            encrypted_bytes = self._fernet.encrypt(data_bytes)
            
            # Конвертируем в base64 строку
            encrypted_str = base64.b64encode(encrypted_bytes).decode('utf-8')
            
            return encrypted_str
            
        except Exception as e:
            logger.error(f"❌ Ошибка шифрования: {str(e)}")
            raise
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Дешифрует строку
        
        Args:
            encrypted_data: Зашифрованная строка в base64
            
        Returns:
            str: Расшифрованная строка
        """
        try:
            if not encrypted_data:
                return ""
            
            # Конвертируем из base64 в байты
            encrypted_bytes = base64.b64decode(encrypted_data.encode('utf-8'))
            
            # Дешифруем
            decrypted_bytes = self._fernet.decrypt(encrypted_bytes)
            
            # Конвертируем в строку
            decrypted_str = decrypted_bytes.decode('utf-8')
            
            return decrypted_str
            
        except Exception as e:
            logger.error(f"❌ Ошибка дешифрования: {str(e)}")
            raise
    
    def hash_sensitive_data(self, data: str) -> str:
        """
        Создает хеш от чувствительных данных для логирования
        Показывает только первые и последние символы
        
        Args:
            data: Данные для хеширования
            
        Returns:
            str: Маскированные данные
        """
        if not data:
            return "None"
        
        if len(data) <= 4:
            return "*" * len(data)
        
        return f"{data[:2]}{'*' * (len(data) - 4)}{data[-2:]}"

# Глобальный экземпляр менеджера
crypto_manager = CryptoManager()
