"""
Factory pattern для создания тестовых объектов
Упрощает генерацию реалистичных данных для тестов
"""

import random
from datetime import datetime, timezone, timedelta
from typing import Optional, List
from models import User, Channel, Post, Group, InviteCode


class UserFactory:
    """Factory для создания User объектов"""
    
    @staticmethod
    def create(
        db,
        telegram_id: Optional[int] = None,
        username: str = "testuser",
        first_name: str = "Test",
        last_name: str = "User",
        role: str = "user",
        subscription_type: str = "free",
        is_authenticated: bool = False,
        max_channels: int = 3,
        **kwargs
    ) -> User:
        """Создать пользователя с заданными параметрами"""
        if telegram_id is None:
            telegram_id = random.randint(100000000, 999999999)
        
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=role,
            subscription_type=subscription_type,
            is_authenticated=is_authenticated,
            max_channels=max_channels,
            created_at=datetime.now(timezone.utc),
            **kwargs
        )
        
        db.add(user)
        db.commit()
        db.refresh(user)
        return user
    
    @staticmethod
    def create_admin(db, **kwargs) -> User:
        """Создать администратора"""
        return UserFactory.create(
            db,
            role="admin",
            subscription_type="enterprise",
            max_channels=999,
            is_authenticated=True,
            **kwargs
        )
    
    @staticmethod
    def create_premium(db, **kwargs) -> User:
        """Создать premium пользователя"""
        return UserFactory.create(
            db,
            subscription_type="premium",
            max_channels=20,
            is_authenticated=True,
            subscription_started_at=datetime.now(timezone.utc),
            subscription_expires=datetime.now(timezone.utc) + timedelta(days=30),
            **kwargs
        )
    
    @staticmethod
    def create_batch(db, count: int = 3, **kwargs) -> List[User]:
        """Создать несколько пользователей"""
        return [UserFactory.create(db, **kwargs) for _ in range(count)]


class ChannelFactory:
    """Factory для создания Channel объектов"""
    
    @staticmethod
    def create(
        db,
        channel_username: Optional[str] = None,
        channel_id: Optional[int] = None,
        channel_title: str = "Test Channel",
        **kwargs
    ) -> Channel:
        """Создать канал"""
        if channel_username is None:
            channel_username = f"test_channel_{random.randint(1000, 9999)}"
        
        if channel_id is None:
            channel_id = random.randint(1000000000, 9999999999)
        
        channel = Channel(
            channel_username=channel_username,
            channel_id=channel_id,
            channel_title=channel_title,
            created_at=datetime.now(timezone.utc),
            **kwargs
        )
        
        db.add(channel)
        db.commit()
        db.refresh(channel)
        return channel
    
    @staticmethod
    def create_batch(db, count: int = 3, **kwargs) -> List[Channel]:
        """Создать несколько каналов"""
        return [ChannelFactory.create(db, **kwargs) for _ in range(count)]


class PostFactory:
    """Factory для создания Post объектов"""
    
    @staticmethod
    def create(
        db,
        user_id: int,
        channel_id: int,
        text: str = "Test post content",
        posted_at: Optional[datetime] = None,
        telegram_message_id: Optional[int] = None,
        tags: Optional[List[str]] = None,
        **kwargs
    ) -> Post:
        """Создать пост"""
        if posted_at is None:
            posted_at = datetime.now(timezone.utc)
        
        if telegram_message_id is None:
            telegram_message_id = random.randint(1, 999999)
        
        # Извлекаем tagging_status из kwargs чтобы избежать дублирования
        tagging_status = kwargs.pop('tagging_status', 'success')
        
        post = Post(
            user_id=user_id,
            channel_id=channel_id,
            text=text,
            posted_at=posted_at,
            telegram_message_id=telegram_message_id,
            url=f"https://t.me/channel/{telegram_message_id}",
            tags=tags,
            tagging_status=tagging_status,
            parsed_at=datetime.now(timezone.utc),
            **kwargs
        )
        
        db.add(post)
        db.commit()
        db.refresh(post)
        return post
    
    @staticmethod
    def create_batch(
        db,
        user_id: int,
        channel_id: int,
        count: int = 10,
        **kwargs
    ) -> List[Post]:
        """Создать несколько постов с разными датами"""
        posts = []
        base_time = datetime.now(timezone.utc) - timedelta(days=count)
        
        for i in range(count):
            post = PostFactory.create(
                db,
                user_id=user_id,
                channel_id=channel_id,
                text=f"Test post {i + 1}: Content about AI and technology",
                posted_at=base_time + timedelta(days=i),
                telegram_message_id=i + 1,
                tags=["технологии", "AI"] if i % 2 == 0 else ["новости"],
                **kwargs
            )
            posts.append(post)
        
        return posts


class GroupFactory:
    """Factory для создания Group объектов"""
    
    @staticmethod
    def create(
        db,
        group_id: Optional[int] = None,
        group_title: str = "Test Group",
        group_username: Optional[str] = None,
        **kwargs
    ) -> Group:
        """Создать группу"""
        if group_id is None:
            group_id = -random.randint(1000000000, 9999999999)
        
        group = Group(
            group_id=group_id,
            group_title=group_title,
            group_username=group_username,
            created_at=datetime.now(timezone.utc),
            **kwargs
        )
        
        db.add(group)
        db.commit()
        db.refresh(group)
        return group


class InviteCodeFactory:
    """Factory для создания InviteCode объектов"""
    
    @staticmethod
    def create(
        db,
        code: Optional[str] = None,
        created_by: Optional[int] = None,
        subscription_type: str = "trial",
        expires_days: int = 7,
        max_uses: int = 1,
        **kwargs
    ) -> InviteCode:
        """Создать инвайт код"""
        if code is None:
            code = InviteCode.generate_code()
        
        # Если created_by не указан, создаем или находим админа
        if created_by is None:
            import random
            # Создаем уникального админа для каждого теста
            admin_telegram_id = random.randint(990000, 999999)
            admin = db.query(User).filter(User.telegram_id == admin_telegram_id).first()
            if not admin:
                admin = UserFactory.create_admin(db, telegram_id=admin_telegram_id)
            created_by = admin.id
        
        invite = InviteCode(
            code=code,
            created_by=created_by,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=expires_days),
            default_subscription=subscription_type,
            max_uses=max_uses,
            uses_count=0,
            default_trial_days=7 if subscription_type == "trial" else 0,
            **kwargs
        )
        
        db.add(invite)
        db.commit()
        db.refresh(invite)
        return invite
    
    @staticmethod
    def create_expired(db, **kwargs) -> InviteCode:
        """Создать истекший инвайт код"""
        return InviteCodeFactory.create(
            db,
            expires_days=-1,  # Уже истек
            **kwargs
        )
    
    @staticmethod
    def create_used(db, used_by: int, **kwargs) -> InviteCode:
        """Создать использованный инвайт код"""
        invite = InviteCodeFactory.create(db, **kwargs)
        invite.use(used_by)
        db.commit()
        db.refresh(invite)
        return invite

