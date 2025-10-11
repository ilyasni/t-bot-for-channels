from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, BigInteger, LargeBinary, JSON, Table, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import event
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)
Base = declarative_base()

# Промежуточная таблица для связи многие-ко-многим между User и Channel
user_channel = Table(
    'user_channel',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('channel_id', Integer, ForeignKey('channels.id', ondelete='CASCADE'), primary_key=True),
    Column('is_active', Boolean, default=True),  # Активность подписки конкретного пользователя
    Column('created_at', DateTime, default=lambda: datetime.now(timezone.utc)),
    Column('last_parsed_at', DateTime, nullable=True)  # Время последнего парсинга для этого пользователя
)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(BigInteger, unique=True, index=True, nullable=False)
    username = Column(String, nullable=True)
    first_name = Column(String, nullable=True)
    last_name = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active = Column(Boolean, default=True)
    
    # Настройки хранения постов
    retention_days = Column(Integer, default=30)  # Период хранения постов в днях
    
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
    channels = relationship(
        "Channel",
        secondary=user_channel,
        back_populates="users"
    )
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
    
    def get_active_channels(self, db):
        """
        Получить список активных каналов пользователя
        
        Args:
            db: Сессия базы данных
            
        Returns:
            List[Channel]: Список активных каналов
        """
        from sqlalchemy import select
        
        stmt = select(Channel).join(
            user_channel,
            Channel.id == user_channel.c.channel_id
        ).where(
            user_channel.c.user_id == self.id,
            user_channel.c.is_active == True
        )
        
        result = db.execute(stmt)
        return result.scalars().all()
    
    def get_all_channels(self, db):
        """
        Получить список всех каналов пользователя (включая неактивные)
        
        Args:
            db: Сессия базы данных
            
        Returns:
            List[tuple]: Список кортежей (Channel, subscription_info)
        """
        from sqlalchemy import select
        
        stmt = select(
            Channel,
            user_channel.c.is_active,
            user_channel.c.created_at,
            user_channel.c.last_parsed_at
        ).join(
            user_channel,
            Channel.id == user_channel.c.channel_id
        ).where(
            user_channel.c.user_id == self.id
        )
        
        result = db.execute(stmt)
        return [(row[0], {
            'is_active': row[1],
            'created_at': row[2],
            'last_parsed_at': row[3]
        }) for row in result.all()]

class Channel(Base):
    __tablename__ = "channels"
    
    id = Column(Integer, primary_key=True, index=True)
    channel_username = Column(String, unique=True, nullable=False, index=True)  # Уникальный username канала
    channel_id = Column(BigInteger, unique=True, nullable=True, index=True)  # Telegram ID канала
    channel_title = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Связи
    users = relationship(
        "User",
        secondary=user_channel,
        back_populates="channels"
    )
    posts = relationship("Post", back_populates="channel", cascade="all, delete-orphan")
    
    @staticmethod
    def get_or_create(db, channel_username: str, channel_id: int = None, channel_title: str = None):
        """
        Получить существующий канал или создать новый
        
        Args:
            db: Сессия базы данных
            channel_username: Username канала (без @)
            channel_id: Telegram ID канала
            channel_title: Название канала
            
        Returns:
            Объект Channel
        """
        channel = db.query(Channel).filter(
            Channel.channel_username == channel_username
        ).first()
        
        if not channel:
            channel = Channel(
                channel_username=channel_username,
                channel_id=channel_id,
                channel_title=channel_title
            )
            db.add(channel)
            db.flush()  # Получаем ID без commit
            logger.info(f"📢 Создан новый канал: @{channel_username}")
        elif channel_id and not channel.channel_id:
            # Обновляем ID и название если они были None
            channel.channel_id = channel_id
            if channel_title:
                channel.channel_title = channel_title
            logger.info(f"📢 Обновлены данные канала: @{channel_username}")
        
        return channel
    
    def add_user(self, db, user, is_active: bool = True):
        """
        Добавить пользователя к каналу
        
        Args:
            db: Сессия базы данных
            user: Объект User
            is_active: Активность подписки
        """
        if user not in self.users:
            self.users.append(user)
            # Установим is_active через прямой SQL
            db.execute(
                user_channel.update().where(
                    (user_channel.c.user_id == user.id) &
                    (user_channel.c.channel_id == self.id)
                ).values(is_active=is_active)
            )
            logger.info(f"✅ Пользователь {user.telegram_id} подключен к каналу @{self.channel_username}")
    
    def remove_user(self, db, user):
        """
        Удалить пользователя из канала
        
        Args:
            db: Сессия базы данных
            user: Объект User
        """
        if user in self.users:
            self.users.remove(user)
            logger.info(f"🗑️ Пользователь {user.telegram_id} отключен от канала @{self.channel_username}")
    
    def get_user_subscription(self, db, user):
        """
        Получить информацию о подписке пользователя на канал
        
        Args:
            db: Сессия базы данных
            user: Объект User
            
        Returns:
            Dict с информацией о подписке или None
        """
        result = db.execute(
            user_channel.select().where(
                (user_channel.c.user_id == user.id) &
                (user_channel.c.channel_id == self.id)
            )
        ).fetchone()
        
        if result:
            return {
                'is_active': result.is_active,
                'created_at': result.created_at,
                'last_parsed_at': result.last_parsed_at
            }
        return None
    
    def update_user_subscription(self, db, user, is_active: bool = None, last_parsed_at = None):
        """
        Обновить параметры подписки пользователя
        
        Args:
            db: Сессия базы данных
            user: Объект User
            is_active: Новый статус активности
            last_parsed_at: Время последнего парсинга
        """
        values = {}
        if is_active is not None:
            values['is_active'] = is_active
        if last_parsed_at is not None:
            values['last_parsed_at'] = last_parsed_at
        
        if values:
            db.execute(
                user_channel.update().where(
                    (user_channel.c.user_id == user.id) &
                    (user_channel.c.channel_id == self.id)
                ).values(**values)
            )

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
    parsed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    tags = Column(JSON, nullable=True)  # Массив тегов в формате JSON ["технологии", "новости"]
    
    # Поля для отслеживания тегирования
    tagging_status = Column(String, default="pending")  # pending, success, failed, retrying
    tagging_attempts = Column(Integer, default=0)  # Количество попыток тегирования
    last_tagging_attempt = Column(DateTime, nullable=True)  # Время последней попытки
    tagging_error = Column(Text, nullable=True)  # Последняя ошибка тегирования
    
    # Связи
    user = relationship("User", back_populates="posts")
    channel = relationship("Channel", back_populates="posts") 