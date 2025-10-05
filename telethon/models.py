from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

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
    
    # Связи
    channels = relationship("Channel", back_populates="user", cascade="all, delete-orphan")
    posts = relationship("Post", back_populates="user", cascade="all, delete-orphan")

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