"""
QR Login handlers для Telegram бота
Авторизация через Telegram Mini App с QR кодом (без SMS)
"""

import logging
import os
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters
)

from database import SessionLocal
from models import User, InviteCode, SubscriptionHistory
from qr_auth_manager import qr_auth_manager
from subscription_config import get_subscription_info, format_subscription_info

logger = logging.getLogger(__name__)

# States для ConversationHandler
WAITING_QR_SCAN = 0


async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начало QR авторизации через Mini App
    
    Команда: /login INVITE_CODE
    """
    user = update.effective_user
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "💡 **Использование:** `/login INVITE_CODE`\n\n"
            "Инвайт код можно получить у администратора.\n\n"
            "Пример: `/login TRIAL7ABC123`",
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    invite_code = args[0].strip().upper()
    
    # Валидация invite code
    db = SessionLocal()
    
    try:
        invite = db.query(InviteCode).filter(InviteCode.code == invite_code).first()
        
        if not invite:
            await update.message.reply_text("❌ Инвайт код не найден")
            return ConversationHandler.END
        
        if not invite.is_valid():
            await update.message.reply_text(
                "❌ Инвайт код истек или уже использован\n\n"
                "Обратитесь к администратору за новым кодом"
            )
            return ConversationHandler.END
        
        # Создаем или получаем пользователя
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if not db_user:
            # Создаем нового пользователя С подпиской из invite code
            logger.info(f"👤 Создание нового пользователя: {user.id}")
            
            # Получаем лимиты из subscription tier
            subscription_info = get_subscription_info(invite.default_subscription)
            
            db_user = User(
                telegram_id=user.id,
                first_name=user.first_name or "User",
                last_name=user.last_name,
                username=user.username,
                role="user",
                # ВАЖНО: Устанавливаем подписку сразу при создании
                subscription_type=invite.default_subscription,
                max_channels=subscription_info['max_channels'],
                invited_by=invite.created_by
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            
            # ВАЖНО: Отмечаем использование инвайт кода
            # НЕ вызываем invite.use() здесь - это сделает _finalize_authorization
            # после успешной QR авторизации
            
            logger.info(f"✅ Пользователь создан: {db_user.id} с подпиской {invite.default_subscription}")
            
            # subscription_info уже получен выше
        else:
            # Пользователь существует
            logger.info(f"👤 Пользователь {user.id} уже существует, обновим подписку после авторизации")
            subscription_info = get_subscription_info(invite.default_subscription)
        
        # Сохраняем данные для conversation
        context.user_data['invite_code'] = invite_code
        context.user_data['telegram_id'] = user.id
        context.user_data['subscription_type'] = invite.default_subscription
        
        logger.info(f"🎫 Инвайт код {invite_code} валиден для {user.id}")
        
    finally:
        db.close()
    
    # Создаем QR сессию
    try:
        await update.message.reply_text("⏳ Генерация QR кода...")
        
        session_data = await qr_auth_manager.create_qr_session(user.id, invite_code)
        
        # Формируем URL для Mini App
        auth_base_url = os.getenv("AUTH_BASE_URL", "https://telegram-auth.produman.studio")
        mini_app_url = f"{auth_base_url}/qr-auth?session_id={session_data['session_id']}"
        
        logger.info(f"🔗 Mini App URL: {mini_app_url}")
        
        # Создаем кнопку с Mini App
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton(
                "🔐 Открыть QR авторизацию",
                web_app=WebAppInfo(url=mini_app_url)
            )]
        ])
        
        # Отправляем сообщение с кнопкой
        await update.message.reply_text(
            f"✅ **Инвайт код принят!**\n\n"
            f"🎁 **Подписка:** {subscription_info['name']}\n"
            f"📊 **Лимиты:**\n"
            f"  • Каналов: {subscription_info['max_channels']}\n"
            f"  • Постов/день: {subscription_info['max_posts_per_day']}\n"
            f"  • RAG запросов/день: {subscription_info['rag_queries_per_day']}\n\n"
            f"👇 **Нажмите кнопку для авторизации:**\n\n"
            f"**В Mini App доступны 3 способа:**\n"
            f"  1️⃣ Сканировать QR код камерой\n"
            f"  2️⃣ Открыть ссылку в Telegram\n"
            f"  3️⃣ Скопировать ссылку\n\n"
            f"⚠️ **Важно:** После сканирования/открытия ссылки\n"
            f"**подтвердите авторизацию** в диалоге Telegram!\n\n"
            f"⏰ QR код действителен 5 минут",
            reply_markup=keyboard,
            parse_mode='HTML'
        )
        
        # Сохраняем session_id
        context.user_data['qr_session_id'] = session_data['session_id']
        
        logger.info(f"✅ Mini App кнопка отправлена для {user.id}")
        
        return WAITING_QR_SCAN
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания QR сессии: {e}")
        await update.message.reply_text(
            f"❌ Произошла ошибка при генерации QR кода\n\n"
            f"Попробуйте снова через несколько минут или используйте `/auth`"
        )
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена авторизации"""
    await update.message.reply_text(
        "❌ Процесс авторизации отменен.\n\n"
        "Для повторной попытки используйте: `/login INVITE_CODE`",
        parse_mode='HTML'
    )
    return ConversationHandler.END


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о подписке"""
    user = update.effective_user
    db = SessionLocal()
    
    try:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        # Проверяем активность подписки (timezone-aware)
        is_active = db_user.check_subscription_active()
        subscription_info = get_subscription_info(db_user.subscription_type)
        
        text = f"💎 **Ваша подписка**\n\n"
        text += f"📊 **Тариф:** {subscription_info['name']}\n"
        text += f"🔐 **Статус:** {'✅ Активна' if is_active else '❌ Истекла'}\n\n"
        
        text += f"**Лимиты:**\n"
        text += f"  • Каналов: {db_user.max_channels}\n"
        text += f"  • Постов/день: {subscription_info['max_posts_per_day']}\n"
        text += f"  • RAG запросов/день: {subscription_info['rag_queries_per_day']}\n"
        text += f"  • AI дайджесты: {'✅' if subscription_info['ai_digest'] else '❌'}\n\n"
        
        if db_user.subscription_started_at:
            started = db_user.subscription_started_at
            if started.tzinfo is None:
                started = started.replace(tzinfo=timezone.utc)
            text += f"📅 **Начало:** {started.strftime('%d.%m.%Y')}\n"
        
        if db_user.subscription_expires:
            expires = db_user.subscription_expires
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            days_left = (expires - now).days
            
            text += f"📅 **Истекает:** {expires.strftime('%d.%m.%Y')} ({days_left} дней)\n"
        else:
            text += f"⏳ **Срок:** Безлимитная\n"
        
        # Текущее использование
        channel_count = len(db_user.channels)
        text += f"\n**Использование:**\n"
        text += f"  • Каналов: {channel_count}/{db_user.max_channels}\n"
        
        if not is_active:
            text += f"\n⚠️ **Подписка истекла!** Обратитесь к администратору для продления."
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Subscription command error: {e}")
        from telegram_formatter import markdownify
        await update.message.reply_text(
            markdownify(f"❌ Ошибка: {str(e)}"),
            parse_mode='HTML'
        )
    finally:
        db.close()


# Создаем ConversationHandler
def get_login_conversation_handler():
    """Получить ConversationHandler для QR авторизации"""
    return ConversationHandler(
        entry_points=[CommandHandler('login', login_start)],
        states={
            WAITING_QR_SCAN: [
                # Пользователь взаимодействует с Mini App, не с ботом
                # Авторизация происходит асинхронно через polling
            ]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True,
        per_chat=False,
        name='login_conversation',
        persistent=True,
        allow_reentry=True
    )

