"""
Group Monitor Service
Real-time мониторинг упоминаний пользователей в Telegram группах
"""
import asyncio
import logging
import os
from typing import Dict, List, Optional
from datetime import datetime, timezone
from telethon import TelegramClient, events
from telethon.tl.types import Message

from database import SessionLocal
from models import User, Group, GroupMention, GroupSettings, user_group
from shared_auth_manager import shared_auth_manager
from group_digest_generator import group_digest_generator
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GroupMonitorService:
    """Сервис мониторинга упоминаний в Telegram группах"""
    
    def __init__(self):
        # Активные мониторы: {user_telegram_id: TelegramClient}
        self.active_monitors: Dict[int, TelegramClient] = {}
        
        # Группы для мониторинга: {user_telegram_id: [group_ids]}
        self.monitored_groups: Dict[int, List[int]] = {}
        
        logger.info("✅ GroupMonitorService инициализирован")
    
    async def start_monitoring(self, user_telegram_id: int) -> bool:
        """
        Запустить мониторинг упоминаний для пользователя
        
        Args:
            user_telegram_id: Telegram ID пользователя
            
        Returns:
            True если мониторинг запущен, False если ошибка
        """
        try:
            logger.info(f"🔄 Запуск мониторинга для пользователя {user_telegram_id}")
            
            # Получаем клиент пользователя
            client = await shared_auth_manager.get_user_client(user_telegram_id)
            
            if not client:
                logger.error(f"❌ Не удалось получить клиент для {user_telegram_id}")
                return False
            
            # Проверяем подключение
            if not client.is_connected():
                logger.error(f"❌ Клиент не подключен для {user_telegram_id}")
                return False
            
            # Получаем информацию о пользователе
            me = await client.get_me()
            username = me.username or me.first_name or "Unknown"
            
            # Получаем список групп пользователя из БД
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_id == user_telegram_id).first()
                if not user:
                    logger.error(f"❌ Пользователь {user_telegram_id} не найден в БД")
                    return False
                
                # Получаем активные группы
                active_groups = db.query(Group).join(
                    user_group,
                    Group.id == user_group.c.group_id
                ).filter(
                    user_group.c.user_id == user.id,
                    user_group.c.is_active == True,
                    user_group.c.mentions_enabled == True
                ).all()
                
                if not active_groups:
                    logger.info(f"📭 У пользователя {user_telegram_id} нет активных групп для мониторинга")
                    return True  # Не ошибка, просто нет групп
                
                # Сохраняем group_ids для этого пользователя
                group_ids = [g.group_id for g in active_groups]
                self.monitored_groups[user_telegram_id] = group_ids
                
                logger.info(f"📊 Групп для мониторинга: {len(active_groups)}")
                for group in active_groups:
                    logger.info(f"   • {group.group_title or group.group_id}")
                
            finally:
                db.close()
            
            # Регистрируем event handler для упоминаний
            @client.on(events.NewMessage(chats=group_ids))
            async def mention_handler(event):
                """Обработчик новых сообщений в группах"""
                try:
                    # Проверяем упоминание
                    if not event.message.text:
                        return
                    
                    # Проверяем упоминание по username или ID
                    mentioned = False
                    
                    # Проверка по @username
                    if username and f"@{username}" in event.message.text:
                        mentioned = True
                    
                    # Проверка по entities (упоминание через клик)
                    if hasattr(event.message, 'entities') and event.message.entities:
                        for entity in event.message.entities:
                            if hasattr(entity, 'user_id') and entity.user_id == user_telegram_id:
                                mentioned = True
                                break
                    
                    if mentioned:
                        logger.info(f"🔔 Упоминание @{username} в группе {event.chat_id}")
                        await self._process_mention(user_telegram_id, event)
                        
                except Exception as e:
                    logger.error(f"❌ Ошибка в mention_handler: {e}")
            
            # Сохраняем клиент
            self.active_monitors[user_telegram_id] = client
            
            logger.info(f"✅ Мониторинг запущен для @{username} ({len(group_ids)} групп)")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка запуска мониторинга для {user_telegram_id}: {e}")
            return False
    
    async def stop_monitoring(self, user_telegram_id: int):
        """
        Остановить мониторинг для пользователя
        
        Args:
            user_telegram_id: Telegram ID пользователя
        """
        if user_telegram_id in self.active_monitors:
            # Удаляем клиент
            del self.active_monitors[user_telegram_id]
            
            # Удаляем список групп
            if user_telegram_id in self.monitored_groups:
                del self.monitored_groups[user_telegram_id]
            
            logger.info(f"🛑 Мониторинг остановлен для {user_telegram_id}")
    
    async def _process_mention(self, user_telegram_id: int, event):
        """
        Обработка упоминания пользователя
        
        Args:
            user_telegram_id: Telegram ID упомянутого пользователя
            event: Telethon NewMessage event
        """
        try:
            logger.info(f"📝 Обработка упоминания для {user_telegram_id}")
            
            # Получаем клиент
            client = self.active_monitors.get(user_telegram_id)
            if not client:
                logger.error(f"❌ Клиент не найден для {user_telegram_id}")
                return
            
            # Получаем настройки контекста
            db = SessionLocal()
            try:
                user = db.query(User).filter(User.telegram_id == user_telegram_id).first()
                if not user:
                    logger.error(f"❌ Пользователь {user_telegram_id} не найден")
                    return
                
                # Получаем настройки
                settings = db.query(GroupSettings).filter(GroupSettings.user_id == user.id).first()
                context_size = settings.mention_context_messages if settings else 5
                
                # Получаем контекст (сообщения до/после)
                logger.info(f"🔍 Получение контекста ({context_size} сообщений до/после)")
                context_messages = await self._get_context_messages(
                    client, 
                    event.chat_id, 
                    event.message.id,
                    context_size
                )
                
                # Анализируем через n8n workflow
                logger.info(f"🤖 Анализ контекста через n8n workflow...")
                me = await client.get_me()
                analysis = await group_digest_generator.analyze_mention(
                    mentioned_user=me.username or str(user_telegram_id),
                    context_messages=context_messages
                )
                
                # Получаем информацию о группе
                group_entity = await client.get_entity(event.chat_id)
                group_title = getattr(group_entity, 'title', str(event.chat_id))
                
                # Сохраняем в БД
                group = db.query(Group).filter(Group.group_id == event.chat_id).first()
                if group:
                    mention = GroupMention(
                        user_id=user.id,
                        group_id=group.id,
                        message_id=event.message.id,
                        mentioned_at=event.message.date,
                        context=analysis.get('context_summary', ''),
                        reason=analysis.get('mention_reason', ''),
                        urgency=analysis.get('urgency', 'medium'),
                        notified=False  # Пока не отправили
                    )
                    db.add(mention)
                    db.commit()
                    logger.info(f"💾 Упоминание сохранено в БД (mention_id: {mention.id})")
                
                # Отправляем уведомление пользователю
                await self._notify_user(user_telegram_id, analysis, group_title, event)
                
                # Обновляем статус уведомления
                if group:
                    mention.notified = True
                    mention.notified_at = datetime.now(timezone.utc)
                    db.commit()
                
            finally:
                db.close()
                
        except Exception as e:
            logger.error(f"❌ Ошибка обработки упоминания: {e}", exc_info=True)
    
    async def _get_context_messages(
        self, 
        client: TelegramClient, 
        chat_id: int, 
        message_id: int,
        context_size: int = 5
    ) -> List[Message]:
        """
        Получить контекст вокруг упоминания (N сообщений до/после)
        
        Args:
            client: Telethon клиент
            chat_id: ID группы
            message_id: ID сообщения с упоминанием
            context_size: Количество сообщений до/после
            
        Returns:
            Список сообщений (контекст)
        """
        try:
            messages = []
            
            # Получаем сообщения до упоминания
            async for msg in client.iter_messages(
                chat_id,
                limit=context_size,
                offset_id=message_id,
                reverse=False
            ):
                messages.insert(0, msg)  # Добавляем в начало
            
            # Получаем само сообщение с упоминанием
            mention_msg = await client.get_messages(chat_id, ids=message_id)
            if mention_msg:
                messages.append(mention_msg)
            
            # Получаем сообщения после упоминания
            async for msg in client.iter_messages(
                chat_id,
                limit=context_size,
                min_id=message_id,
                reverse=True
            ):
                if msg.id != message_id:  # Пропускаем само упоминание
                    messages.append(msg)
            
            logger.info(f"📨 Получено {len(messages)} сообщений контекста")
            return messages
            
        except Exception as e:
            logger.error(f"❌ Ошибка получения контекста: {e}")
            return []
    
    async def _notify_user(
        self, 
        user_telegram_id: int,
        analysis: Dict,
        group_title: str,
        event
    ):
        """
        Отправить уведомление пользователю об упоминании
        
        Args:
            user_telegram_id: Telegram ID пользователя
            analysis: Результат анализа упоминания
            group_title: Название группы
            event: Telethon event
        """
        try:
            # Получаем клиент
            client = self.active_monitors.get(user_telegram_id)
            if not client:
                logger.error(f"❌ Клиент не найден для отправки уведомления")
                return
            
            # Формируем ссылку на сообщение
            message_link = f"https://t.me/c/{str(event.chat_id)[4:]}/{event.message.id}"
            
            # Форматируем уведомление
            notification = group_digest_generator.format_mention_for_telegram(
                analysis=analysis,
                group_title=group_title,
                message_link=message_link
            )
            
            # Отправляем уведомление в личные сообщения
            await client.send_message(
                user_telegram_id,
                notification,
                parse_mode='HTML'
            )
            
            logger.info(f"📬 Уведомление отправлено пользователю {user_telegram_id}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка отправки уведомления: {e}")
    
    async def start_all_monitors(self) -> int:
        """
        Запустить мониторинг для всех аутентифицированных пользователей
        
        Returns:
            Количество запущенных мониторов
        """
        db = SessionLocal()
        try:
            # Получаем всех аутентифицированных пользователей с активными группами
            users = db.query(User).filter(
                User.is_authenticated == True
            ).all()
            
            logger.info(f"🚀 Запуск мониторинга для {len(users)} пользователей...")
            
            started = 0
            for user in users:
                try:
                    success = await self.start_monitoring(user.telegram_id)
                    if success:
                        started += 1
                        # Задержка между запусками
                        await asyncio.sleep(1)
                except Exception as e:
                    logger.error(f"❌ Ошибка запуска мониторинга для {user.telegram_id}: {e}")
            
            logger.info(f"✅ Запущено мониторов: {started}/{len(users)}")
            return started
            
        finally:
            db.close()
    
    async def stop_all_monitors(self):
        """Остановить все активные мониторы"""
        user_ids = list(self.active_monitors.keys())
        
        for user_id in user_ids:
            await self.stop_monitoring(user_id)
        
        logger.info(f"🛑 Все мониторы остановлены ({len(user_ids)} шт.)")
    
    def get_status(self) -> Dict:
        """
        Получить статус сервиса
        
        Returns:
            {
                "active_monitors": int,
                "monitored_groups_total": int,
                "users": List[int]
            }
        """
        total_groups = sum(len(groups) for groups in self.monitored_groups.values())
        
        return {
            "active_monitors": len(self.active_monitors),
            "monitored_groups_total": total_groups,
            "users": list(self.active_monitors.keys())
        }


# Глобальный экземпляр
group_monitor_service = GroupMonitorService()

