from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, BigInteger, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import event
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Персональные данные для аутентификации (зашифрованы)
    api_id = Column(String, nullable=True)  # API ID пользователя (зашифрован)
    api_hash = Column(Text, nullable=True)  # API Hash пользователя (зашифрован)
    phone_number = Column(Text, nullable=True)  # Номер телефона пользователя (зашифрован)
    session_file = Column(String, nullable=True)  # Путь к файлу сессии
    is_authenticated = Column(Boolean, default=False)  # Статус аутентификации
    last_auth_check = Column(DateTime, nullable=True)  # Время последней проверки аутентификации
    auth_error = Column(Text, nullable=True)  # Последняя ошибка аутентификации
    
    # Новые поля для безопасной аутентификации
    auth_session_id = Column(String, nullable=True)  # ID сессии аутентификации
    auth_session_expires = Column(DateTime, nullable=True)  # Время истечения сессии
    failed_auth_attempts = Column(Integer, default=0)  # Количество неудачных попыток
    last_auth_attempt = Column(DateTime, nullable=True)  # Время последней попытки
    is_blocked = Column(Boolean, default=False)  # Заблокирован ли пользователь
    block_expires = Column(DateTime, nullable=True)  # Время окончания блокировки
    
    # Связи
    channels = relationship("Channel", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    
    def set_encrypted_api_hash(self, api_hash: str):
        """Установить зашифрованный API hash"""
        try:
            from crypto_utils import crypto_manager
            if api_hash:
                self.api_hash = crypto_manager.encrypt(api_hash)
            else:
                self.api_hash = None
        except Exception as e:
            logger.error(f"❌ Ошибка шифрования API hash: {str(e)}")
            raise
    
    def get_decrypted_api_hash(self) -> str:
        """Получить расшифрованный API hash"""
        try:
            from crypto_utils import crypto_manager
            if self.api_hash:
                return crypto_manager.decrypt(self.api_hash)
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка дешифрования API hash: {str(e)}")
            return None
    
    def set_encrypted_phone_number(self, phone_number: str):
        """Установить зашифрованный номер телефона"""
        try:
            from crypto_utils import crypto_manager
            if phone_number:
                self.phone_number = crypto_manager.encrypt(phone_number)
            else:
                self.phone_number = None
        except Exception as e:
            logger.error(f"❌ Ошибка шифрования номера телефона: {str(e)}")
            raise
    
    def get_decrypted_phone_number(self) -> str:
        """Получить расшифрованный номер телефона"""
        try:
            from crypto_utils import crypto_manager
            if self.phone_number:
                return crypto_manager.decrypt(self.phone_number)
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка дешифрования номера телефона: {str(e)}")
            return None
    
    def get_masked_phone_number(self) -> str:
        """Получить маскированный номер телефона для логирования"""
        try:
            from crypto_utils import crypto_manager
            if self.phone_number:
                phone = crypto_manager.decrypt(self.phone_number)
                return crypto_manager.hash_sensitive_data(phone)
            return "None"
        except Exception as e:
            logger.error(f"❌ Ошибка маскирования номера телефона: {str(e)}")
            return "Error"
    
    def get_masked_api_hash(self) -> str:
        """Получить маскированный API hash для логирования"""
        try:
            from crypto_utils import crypto_manager
            if self.api_hash:
                api_hash = crypto_manager.decrypt(self.api_hash)
                return crypto_manager.hash_sensitive_data(api_hash)
            return "None"
        except Exception as e:
            logger.error(f"❌ Ошибка маскирования API hash: {str(e)}")
            return "Error"

class Channel(Base):
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_username = Column(String, nullable=False)
    channel_id = Column(BigInteger, nullable=True)
    channel_title = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_parsed_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="channels")
    posts = relationship("Post", back_populates="channel", cascade="all, delete-orphan")

class Post(Base):
    __tablename__ = "posts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    telegram_message_id = Column(BigInteger, nullable=False)
    text = Column(Text, nullable=True)
    views = Column(Integer, nullable=True)
    url = Column(String, nullable=True)
    posted_at = Column(DateTime, nullable=False)
    parsed_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="posts")
    channel = relationship("Channel", back_populates="posts") 