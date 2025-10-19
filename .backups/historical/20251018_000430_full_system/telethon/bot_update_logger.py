"""
Telegram Bot Update Logger

Логирование всех входящих updates от Telegram Bot API в читабельном формате.
Использует TypeHandler с group=-1 для перехвата всех типов updates перед обработкой handlers.

Based on Context7 best practices for python-telegram-bot middleware pattern.
"""

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime, timezone
import logging

# Настройка логгера для updates
update_logger = logging.getLogger(__name__)

async def log_all_updates_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Логирует все входящие updates в читабельном формате.
    
    Best practice из Context7: TypeHandler с group=-1 для middleware логирования.
    НЕ вызывает ApplicationHandlerStop - продолжает обработку другими handlers.
    
    Args:
        update: Update объект от Telegram Bot API
        context: CallbackContext для доступа к bot и другим данным
    """
    try:
        log_incoming_update(update)
    except Exception as e:
        # Не ломаем обработку updates при ошибках логирования
        update_logger.error(f"❌ Ошибка логирования update: {e}")

def log_incoming_update(update: Update) -> None:
    """
    Извлекает и логирует ключевые поля из Update объекта.
    
    Поддерживает все типы updates:
    - Message (text, photo, voice, document, etc.)
    - CallbackQuery (button clicks)
    - InlineQuery (inline режим)
    - EditedMessage (редактирование сообщений)
    - Другие типы из update.to_dict().keys()
    
    Args:
        update: Update объект для логирования
    """
    # Текущее время UTC
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    
    # Определяем тип update
    update_type = _get_update_type(update)
    
    # Извлекаем информацию о пользователе
    user_info = _get_user_info(update)
    
    # Извлекаем информацию о чате
    chat_info = _get_chat_info(update)
    
    # Извлекаем содержимое в зависимости от типа
    content = _get_content_info(update)
    
    # Формируем читабельный лог
    log_lines = [
        f"📨 [INCOMING UPDATE] {timestamp}",
        f"   Type: {update_type}",
        f"   User: {user_info}",
        f"   Chat: {chat_info}"
    ]
    
    if content:
        log_lines.append(f"   Content: {content}")
    
    # Добавляем update_id для трассировки
    log_lines.append(f"   Update ID: {update.update_id}")
    
    # Логируем как INFO (видно в docker logs)
    update_logger.info("\n".join(log_lines))

def _get_update_type(update: Update) -> str:
    """Определяет тип update из его атрибутов."""
    # Проверяем основные типы updates
    if update.message:
        if update.message.text:
            return "message (text)"
        elif update.message.photo:
            return "message (photo)"
        elif update.message.voice:
            return "message (voice)"
        elif update.message.document:
            return "message (document)"
        elif update.message.sticker:
            return "message (sticker)"
        elif update.message.video:
            return "message (video)"
        elif update.message.audio:
            return "message (audio)"
        elif update.message.contact:
            return "message (contact)"
        elif update.message.location:
            return "message (location)"
        elif update.message.venue:
            return "message (venue)"
        else:
            return "message (other)"
    
    elif update.edited_message:
        return "edited_message"
    
    elif update.callback_query:
        return "callback_query"
    
    elif update.inline_query:
        return "inline_query"
    
    elif update.chosen_inline_result:
        return "chosen_inline_result"
    
    elif update.shipping_query:
        return "shipping_query"
    
    elif update.pre_checkout_query:
        return "pre_checkout_query"
    
    elif update.poll:
        return "poll"
    
    elif update.poll_answer:
        return "poll_answer"
    
    elif update.my_chat_member:
        return "my_chat_member"
    
    elif update.chat_member:
        return "chat_member"
    
    elif update.chat_join_request:
        return "chat_join_request"
    
    else:
        # Fallback: определяем из to_dict()
        update_dict = update.to_dict()
        keys = [k for k in update_dict.keys() if k != 'update_id']
        if keys:
            return f"unknown ({keys[0]})"
        return "unknown"

def _get_user_info(update: Update) -> str:
    """Извлекает информацию о пользователе."""
    user = update.effective_user
    if not user:
        return "Unknown User"
    
    # Формируем строку: @username (user_id) First Last
    parts = []
    
    if user.username:
        parts.append(f"@{user.username}")
    
    parts.append(f"({user.id})")
    
    if user.first_name:
        parts.append(user.first_name)
    
    if user.last_name:
        parts.append(user.last_name)
    
    return " ".join(parts)

def _get_chat_info(update: Update) -> str:
    """Извлекает информацию о чате."""
    chat = update.effective_chat
    if not chat:
        return "Unknown Chat"
    
    # Определяем тип чата
    if chat.type == "private":
        return f"Private Chat ({chat.id})"
    elif chat.type == "group":
        return f"Group Chat \"{chat.title}\" ({chat.id})"
    elif chat.type == "supergroup":
        return f"Supergroup \"{chat.title}\" ({chat.id})"
    elif chat.type == "channel":
        return f"Channel \"{chat.title}\" ({chat.id})"
    else:
        return f"{chat.type.title()} \"{chat.title}\" ({chat.id})"

def _get_content_info(update: Update) -> str:
    """Извлекает содержимое update в зависимости от типа."""
    
    # Текстовые сообщения
    if update.message and update.message.text:
        # Ограничиваем длину текста для читабельности
        text = update.message.text
        if len(text) > 100:
            text = text[:97] + "..."
        return f'"{text}"'
    
    # Callback queries
    elif update.callback_query and update.callback_query.data:
        return f'"{update.callback_query.data}"'
    
    # Inline queries
    elif update.inline_query and update.inline_query.query:
        query = update.inline_query.query
        if len(query) > 50:
            query = query[:47] + "..."
        return f'"{query}"'
    
    # Голосовые сообщения
    elif update.message and update.message.voice:
        duration = update.message.voice.duration
        return f"Voice message ({duration}s)"
    
    # Фото
    elif update.message and update.message.photo:
        return "Photo"
    
    # Документы
    elif update.message and update.message.document:
        filename = update.message.document.file_name or "Unknown"
        return f"Document: {filename}"
    
    # Стикеры
    elif update.message and update.message.sticker:
        emoji = update.message.sticker.emoji or ""
        return f"Sticker {emoji}"
    
    # Видео
    elif update.message and update.message.video:
        duration = update.message.video.duration
        return f"Video ({duration}s)"
    
    # Аудио
    elif update.message and update.message.audio:
        title = update.message.audio.title or "Unknown"
        return f"Audio: {title}"
    
    # Контакт
    elif update.message and update.message.contact:
        name = update.message.contact.first_name or ""
        phone = update.message.contact.phone_number or ""
        return f"Contact: {name} {phone}".strip()
    
    # Локация
    elif update.message and update.message.location:
        lat = update.message.location.latitude
        lon = update.message.location.longitude
        return f"Location: {lat}, {lon}"
    
    # Место
    elif update.message and update.message.venue:
        title = update.message.venue.title or "Unknown"
        return f"Venue: {title}"
    
    # Редактирование сообщения
    elif update.edited_message and update.edited_message.text:
        text = update.edited_message.text
        if len(text) > 100:
            text = text[:97] + "..."
        return f'Edited: "{text}"'
    
    # Poll
    elif update.poll:
        question = update.poll.question
        if len(question) > 50:
            question = question[:47] + "..."
        return f'Poll: "{question}"'
    
    # Chat member updates
    elif update.my_chat_member:
        status = update.my_chat_member.new_chat_member.status
        return f"Status changed to: {status}"
    
    elif update.chat_member:
        status = update.chat_member.new_chat_member.status
        return f"Member status changed to: {status}"
    
    # Chat join request
    elif update.chat_join_request:
        return "Join request"
    
    else:
        return None
