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

# Промежуточная таблица для связи многие-ко-многим между User и Group
user_group = Table(
    'user_group',
    Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
    Column('group_id', Integer, ForeignKey('groups.id', ondelete='CASCADE'), primary_key=True),
    Column('is_active', Boolean, default=True),  # Активность мониторинга группы
    Column('mentions_enabled', Boolean, default=True),  # Уведомления об упоминаниях в этой группе
    Column('created_at', DateTime, default=lambda: datetime.now(timezone.utc))
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
    
    # Роли и подписки (новая система авторизации)
    role = Column(String, default="user")  # admin, user
    subscription_type = Column(String, default="free")  # free, trial, basic, premium, enterprise
    subscription_expires = Column(DateTime, nullable=True)
    subscription_started_at = Column(DateTime, nullable=True)
    max_channels = Column(Integer, default=3)  # Лимит каналов по подписке
    invited_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Кто пригласил
    
    # Voice transcription statistics (Premium/Enterprise feature)
    voice_queries_today = Column(Integer, default=0)  # Голосовых запросов сегодня
    voice_queries_reset_at = Column(DateTime(timezone=True), nullable=True)  # Время сброса счетчика
    
    # Связи
    channels = relationship(
        "Channel",
        secondary=user_channel,
        back_populates="users"
    )
    groups = relationship(
        "Group",
        secondary=user_group,
        back_populates="users"
    )
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")
    digest_settings = relationship("DigestSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    group_settings = relationship("GroupSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")
    query_history = relationship("RAGQueryHistory", back_populates="user", cascade="all, delete-orphan")
    
    # Связи для системы инвайтов и подписок
    inviter = relationship("User", remote_side=[id], foreign_keys=[invited_by])
    created_invites = relationship("InviteCode", foreign_keys="InviteCode.created_by", back_populates="creator")
    used_invites = relationship("InviteCode", foreign_keys="InviteCode.used_by", back_populates="user")
    
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
    
    def check_subscription_active(self) -> bool:
        """Проверка активности подписки"""
        if not self.subscription_expires:
            return True  # Безлимитная подписка
        
        # Убеждаемся что даты timezone-aware
        expires = self.subscription_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        
        return expires > datetime.now(timezone.utc)
    
    def is_admin(self) -> bool:
        """Проверка является ли пользователь администратором"""
        return self.role == "admin"
    
    def can_add_channel(self) -> bool:
        """Проверка может ли пользователь добавить еще канал"""
        if not self.check_subscription_active():
            return False
        current_count = len(self.channels)
        return current_count < self.max_channels
    
    def can_add_group(self) -> bool:
        """Проверка может ли пользователь добавить еще группу"""
        if not self.check_subscription_active():
            return False
        
        # Получаем лимит групп из subscription config
        from subscription_config import get_subscription_info
        subscription_info = get_subscription_info(self.subscription_type)
        max_groups = subscription_info.get('max_groups', 0)
        
        current_count = len(self.groups)
        return current_count < max_groups

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
    
    # Обогащенный контент (текст + контент из ссылок)
    enriched_content = Column(Text, nullable=True)  # Для RAG индексации с контентом ссылок
    
    # Поля для отслеживания тегирования
    tagging_status = Column(String, default="pending")  # pending, success, failed, retrying
    tagging_attempts = Column(Integer, default=0)  # Количество попыток тегирования
    last_tagging_attempt = Column(DateTime, nullable=True)  # Время последней попытки
    tagging_error = Column(Text, nullable=True)  # Последняя ошибка тегирования
    
    # Связи
    user = relationship("User", back_populates="posts")
    channel = relationship("Channel", back_populates="posts")


class DigestSettings(Base):
    """Настройки дайджестов пользователя"""
    __tablename__ = "digest_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Расписание
    enabled = Column(Boolean, default=False)
    frequency = Column(String, default="daily")  # daily, weekly, custom
    time = Column(String, default="09:00")       # HH:MM
    days_of_week = Column(JSON, nullable=True)   # [1,2,3] для weekly (1=Monday, 7=Sunday)
    timezone = Column(String, default="Europe/Moscow")
    
    # Контент
    channels = Column(JSON, nullable=True)        # channel_ids или null (все каналы)
    tags = Column(JSON, nullable=True)            # tags или null (все теги)
    format = Column(String, default="markdown")   # markdown, html, plain
    max_posts = Column(Integer, default=20)
    
    # Доставка
    delivery_method = Column(String, default="telegram")  # telegram, email
    email = Column(String, nullable=True)
    
    # История
    last_sent_at = Column(DateTime, nullable=True)
    next_scheduled_at = Column(DateTime, nullable=True)
    
    # AI Summarization
    ai_summarize = Column(Boolean, default=False)  # Включить AI-суммаризацию
    preferred_topics = Column(JSON, nullable=True)  # Список предпочитаемых тем: ["криптовалюты", "авто"]
    summary_style = Column(String, default="concise")  # concise, detailed, executive
    topics_limit = Column(Integer, default=5)  # Максимум тем в дайджесте (3-5)
    
    # Связи
    user = relationship("User", back_populates="digest_settings")


class IndexingStatus(Base):
    """Статус индексации постов в Qdrant"""
    __tablename__ = "indexing_status"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False, index=True)
    
    indexed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    vector_id = Column(String, nullable=True)  # ID в Qdrant
    status = Column(String, default="success", index=True)  # success, failed, pending
    error = Column(Text, nullable=True)
    
    # Связи
    user = relationship("User")
    post = relationship("Post")
    
    # Уникальность комбинации user_id + post_id
    __table_args__ = (
        UniqueConstraint('user_id', 'post_id', name='uix_user_post'),
    )


class RAGQueryHistory(Base):
    """История RAG-запросов пользователя для анализа интересов"""
    __tablename__ = "rag_query_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    query = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # Извлеченные темы/ключевые слова из запроса
    extracted_topics = Column(JSON, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="query_history")


class Group(Base):
    """Telegram группы для мониторинга диалогов и упоминаний"""
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(BigInteger, unique=True, nullable=False, index=True)  # Telegram ID группы
    group_title = Column(String, nullable=True)
    group_username = Column(String, nullable=True, index=True)  # Username группы (если есть)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Many-to-many с пользователями
    users = relationship(
        "User",
        secondary=user_group,
        back_populates="groups"
    )
    
    @staticmethod
    def get_or_create(db, group_id: int, group_title: str = None, group_username: str = None):
        """
        Получить существующую группу или создать новую
        
        Args:
            db: Сессия базы данных
            group_id: Telegram ID группы
            group_title: Название группы
            group_username: Username группы (без @)
            
        Returns:
            Объект Group
        """
        group = db.query(Group).filter(Group.group_id == group_id).first()
        
        if not group:
            group = Group(
                group_id=group_id,
                group_title=group_title,
                group_username=group_username
            )
            db.add(group)
            db.flush()  # Получаем ID без commit
            logger.info(f"📢 Создана новая группа: {group_title or group_id}")
        elif group_title and not group.group_title:
            # Обновляем данные если они были None
            group.group_title = group_title
            if group_username:
                group.group_username = group_username
            logger.info(f"📢 Обновлены данные группы: {group_title}")
        
        return group
    
    def add_user(self, db, user, is_active: bool = True, mentions_enabled: bool = True):
        """
        Добавить пользователя к группе
        
        Args:
            db: Сессия базы данных
            user: Объект User
            is_active: Активность мониторинга
            mentions_enabled: Уведомления об упоминаниях
        """
        if user not in self.users:
            self.users.append(user)
            # Установим настройки через прямой SQL
            db.execute(
                user_group.update().where(
                    (user_group.c.user_id == user.id) &
                    (user_group.c.group_id == self.id)
                ).values(is_active=is_active, mentions_enabled=mentions_enabled)
            )
            logger.info(f"✅ Пользователь {user.telegram_id} подключен к группе {self.group_title or self.group_id}")
    
    def remove_user(self, db, user):
        """
        Удалить пользователя из группы
        
        Args:
            db: Сессия базы данных
            user: Объект User
        """
        if user in self.users:
            self.users.remove(user)
            logger.info(f"🗑️ Пользователь {user.telegram_id} отключен от группы {self.group_title or self.group_id}")


class GroupMention(Base):
    """История упоминаний пользователя в группах"""
    __tablename__ = "group_mentions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False, index=True)
    message_id = Column(BigInteger, nullable=False)
    mentioned_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # AI-анализ упоминания
    context = Column(Text, nullable=True)  # Контекст разговора
    reason = Column(Text, nullable=True)  # Причина упоминания
    urgency = Column(String, nullable=True)  # low, medium, high
    
    # Статус уведомления
    notified = Column(Boolean, default=False)
    notified_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User")
    group = relationship("Group")
    
    # Уникальность комбинации user_id + group_id + message_id
    __table_args__ = (
        UniqueConstraint('user_id', 'group_id', 'message_id', name='uix_user_group_message'),
    )


class GroupSettings(Base):
    """Настройки групп для пользователя"""
    __tablename__ = "group_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Уведомления при упоминаниях
    mentions_enabled = Column(Boolean, default=True)
    mention_context_messages = Column(Integer, default=5)  # Сколько сообщений до/после брать для контекста
    
    # Дайджесты
    digest_default_hours = Column(Integer, default=24)  # По умолчанию за 24 часа
    digest_max_messages = Column(Integer, default=200)  # Макс сообщений для анализа
    
    # Связи
    user = relationship("User", back_populates="group_settings")


class InviteCode(Base):
    """Инвайт коды для регистрации новых пользователей"""
    __tablename__ = "invite_codes"
    
    code = Column(String, primary_key=True, index=True)  # INVITE2024ABC
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    used_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    used_at = Column(DateTime, nullable=True)
    
    expires_at = Column(DateTime, nullable=False)  # Срок действия кода
    max_uses = Column(Integer, default=1)  # Сколько раз можно использовать
    uses_count = Column(Integer, default=0)  # Сколько раз использован
    
    # Автоматические настройки для приглашенного
    default_subscription = Column(String, default="free")  # Какую подписку дать
    default_trial_days = Column(Integer, default=0)  # Trial период в днях
    
    # Связи
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_invites")
    user = relationship("User", foreign_keys=[used_by], back_populates="used_invites")
    
    @staticmethod
    def generate_code() -> str:
        """Генерация уникального инвайт кода"""
        import secrets
        import string
        alphabet = string.ascii_uppercase + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(12))
    
    def is_valid(self) -> bool:
        """Проверка валидности инвайт кода"""
        now = datetime.now(timezone.utc)
        
        # Убеждаемся что expires_at timezone-aware
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        
        if now > expires:
            return False
        if self.uses_count >= self.max_uses:
            return False
        return True
    
    def use(self, user_id: int) -> bool:
        """Использование инвайт кода"""
        if not self.is_valid():
            return False
        
        self.uses_count += 1
        if self.max_uses == 1:  # Одноразовый код
            self.used_by = user_id
            self.used_at = datetime.now(timezone.utc)
        
        return True


class SubscriptionHistory(Base):
    """История изменений подписок для аудита"""
    __tablename__ = "subscription_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    action = Column(String, nullable=False)  # created, upgraded, downgraded, renewed, expired, revoked
    old_type = Column(String, nullable=True)
    new_type = Column(String, nullable=False)
    
    changed_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # Админ который изменил
    changed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    notes = Column(Text, nullable=True)
    
    # Связи
    user = relationship("User", foreign_keys=[user_id])
    admin = relationship("User", foreign_keys=[changed_by]) 