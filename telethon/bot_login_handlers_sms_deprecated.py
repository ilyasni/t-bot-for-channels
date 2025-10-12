"""
Обработчики для упрощенной авторизации через /login

Использует ConversationHandler для multi-step процесса:
1. Проверка инвайт кода
2. Ввод номера телефона
3. Ввод SMS кода
4. (Опционально) Ввод 2FA пароля
"""

import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, ConversationHandler, CommandHandler, 
    MessageHandler, filters
)

from database import SessionLocal
from models import User, InviteCode, SubscriptionHistory
from shared_auth_manager import shared_auth_manager
from subscription_config import get_subscription_info, format_subscription_info

logger = logging.getLogger(__name__)

# States для ConversationHandler
PHONE, CODE, TWO_FA = range(3)


async def login_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """
    Начало процесса авторизации
    Команда: /login INVITE_CODE
    """
    user = update.effective_user
    args = context.args
    
    if not args or len(args) < 1:
        await update.message.reply_text(
            "📝 **Использование:** `/login INVITE_CODE`\n\n"
            "Для получения инвайт кода обратитесь к администратору.\n\n"
            "💡 Если у вас уже есть аккаунт, используйте расширенную авторизацию: /auth",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    invite_code = args[0].upper()
    db = SessionLocal()
    
    try:
        # Получаем или создаем пользователя
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if not db_user:
            # Создаем нового пользователя
            db_user = User(
                telegram_id=user.id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name
            )
            db.add(db_user)
            db.commit()
            db.refresh(db_user)
            logger.info(f"✅ Создан новый пользователь: {user.first_name} ({user.id})")
        
        if db_user.is_authenticated:
            await update.message.reply_text(
                "✅ Вы уже авторизованы!\n\n"
                "Используйте:\n"
                "• /my_channels - ваши каналы\n"
                "• /subscription - информация о подписке"
            )
            return ConversationHandler.END
        
        # Проверяем инвайт код
        invite = db.query(InviteCode).filter(InviteCode.code == invite_code).first()
        
        if not invite:
            await update.message.reply_text("❌ Инвайт код не найден")
            return ConversationHandler.END
        
        if not invite.is_valid():
            # Проверяем причину недействительности
            now = datetime.now(timezone.utc)
            expires = invite.expires_at
            
            # Убеждаемся что expires_at timezone-aware
            if expires and expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            
            reason = "истек срок действия" if (expires and now > expires) else "исчерпан лимит использований"
            await update.message.reply_text(f"❌ Инвайт код недействителен: {reason}")
            return ConversationHandler.END
        
        # Сохраняем инвайт код в context
        context.user_data['invite_code'] = invite_code
        context.user_data['invite_subscription'] = invite.default_subscription
        context.user_data['invite_trial_days'] = invite.default_trial_days
        
        subscription_info = get_subscription_info(invite.default_subscription)
        
        await update.message.reply_text(
            f"✅ Инвайт код принят!\n\n"
            f"🎁 Вам будет активирована подписка: **{subscription_info['name']}**\n\n"
            f"📱 Введите ваш номер телефона в международном формате:\n"
            f"Пример: `+79991234567`",
            parse_mode='Markdown'
        )
        
        return PHONE
        
    except Exception as e:
        logger.error(f"Ошибка в login_start: {e}")
        await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
        return ConversationHandler.END
    finally:
        db.close()


async def phone_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получили номер телефона - отправляем SMS код"""
    phone = update.message.text.strip()
    telegram_id = update.effective_user.id
    
    # Валидация формата номера
    if not phone.startswith('+') or len(phone) < 10:
        await update.message.reply_text(
            "❌ Неверный формат номера телефона.\n\n"
            "Используйте международный формат: `+79991234567`",
            parse_mode='Markdown'
        )
        return PHONE
    
    # Сохраняем номер
    context.user_data['phone'] = phone
    context.user_data['telegram_id'] = telegram_id  # Сохраняем для verify
    
    # Отправляем код через Telethon
    await update.message.reply_text("⏳ Отправка кода...")
    
    result = await shared_auth_manager.send_code(telegram_id, phone)
    
    # Сохраняем phone_code_hash если вернулся
    if result.get('phone_code_hash'):
        context.user_data['phone_code_hash'] = result['phone_code_hash']
        logger.info(f"💾 Сохранен phone_code_hash для {telegram_id}")
    
    if result['success']:
        if result.get('already_authorized'):
            await update.message.reply_text(
                "✅ Вы уже авторизованы с этим номером!\n\n"
                "Активирую подписку..."
            )
            # Активируем подписку
            await activate_subscription_from_invite(telegram_id, context.user_data)
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                "✅ SMS код отправлен на ваш номер!\n\n"
                "💬 Введите код из SMS:"
            )
            return CODE
    else:
        await update.message.reply_text(f"❌ {result['error']}\n\nПопробуйте снова или /cancel")
        return PHONE


async def code_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получили SMS код - авторизуемся"""
    code = update.message.text.strip()
    telegram_id = update.effective_user.id
    phone = context.user_data.get('phone')
    
    if not phone:
        await update.message.reply_text("❌ Сессия истекла. Начните снова: /login INVITE_CODE")
        return ConversationHandler.END
    
    await update.message.reply_text("⏳ Проверка кода...")
    
    result = await shared_auth_manager.verify_code(telegram_id, phone, code)
    
    if result['success']:
        # Успешная авторизация!
        await activate_subscription_from_invite(telegram_id, context.user_data)
        
        await update.message.reply_text(
            "🎉 **Авторизация успешна!**\n\n"
            "Теперь вы можете:\n"
            "• /add_channel @channel_name - добавить канал\n"
            "• /my_channels - ваши каналы\n"
            "• /subscription - информация о подписке\n"
            "• /ask <вопрос> - RAG поиск\n"
            "• /help - справка",
            parse_mode='Markdown'
        )
        
        # Очищаем временные данные
        context.user_data.clear()
        
        return ConversationHandler.END
        
    elif result.get('requires_2fa'):
        await update.message.reply_text(
            "🔐 **Требуется двухфакторная аутентификация**\n\n"
            "Введите ваш пароль 2FA:"
        )
        return TWO_FA
    else:
        await update.message.reply_text(
            f"❌ {result['error']}\n\n"
            f"Попробуйте снова или /cancel"
        )
        return CODE


async def password_received(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получили 2FA пароль"""
    password = update.message.text
    telegram_id = update.effective_user.id
    
    await update.message.reply_text("⏳ Проверка пароля...")
    
    result = await shared_auth_manager.verify_2fa(telegram_id, password)
    
    if result['success']:
        # Успешная авторизация!
        await activate_subscription_from_invite(telegram_id, context.user_data)
        
        await update.message.reply_text(
            "🎉 **Авторизация успешна!**\n\n"
            "Добро пожаловать! Используйте:\n"
            "• /add_channel - добавить канал\n"
            "• /my_channels - ваши каналы\n"
            "• /subscription - информация о подписке",
            parse_mode='Markdown'
        )
        
        context.user_data.clear()
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            f"❌ {result['error']}\n\n"
            f"Попробуйте снова или /cancel"
        )
        return TWO_FA


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена процесса авторизации"""
    user = update.effective_user
    
    await update.message.reply_text(
        "❌ Процесс авторизации отменен.\n\n"
        "Для повторной попытки используйте: /login INVITE_CODE"
    )
    
    # Очищаем временные данные
    context.user_data.clear()
    
    return ConversationHandler.END


async def activate_subscription_from_invite(telegram_id: int, user_data: dict):
    """Активировать подписку пользователю по инвайт коду"""
    db = SessionLocal()
    
    try:
        invite_code = user_data.get('invite_code')
        subscription_type = user_data.get('invite_subscription', 'free')
        trial_days = user_data.get('invite_trial_days', 0)
        
        # Получаем или создаем пользователя
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        if not user:
            logger.error(f"User {telegram_id} not found during subscription activation!")
            return
        
        # Используем инвайт код
        invite = db.query(InviteCode).filter(InviteCode.code == invite_code).first()
        if invite and invite.is_valid():
            invite.use(user.id)
            user.invited_by = invite.created_by
        
        # Активируем подписку
        old_type = user.subscription_type
        user.subscription_type = subscription_type
        user.subscription_started_at = datetime.now(timezone.utc)
        
        # Устанавливаем срок действия
        if trial_days > 0:
            user.subscription_expires = datetime.now(timezone.utc) + timedelta(days=trial_days)
        elif subscription_type != "free":
            tier = get_subscription_info(subscription_type)
            user.subscription_expires = datetime.now(timezone.utc) + timedelta(days=tier.get('duration_days', 30))
        
        # Устанавливаем лимиты
        tier = get_subscription_info(subscription_type)
        user.max_channels = tier['max_channels']
        
        db.commit()
        
        # Записываем в историю
        history = SubscriptionHistory(
            user_id=user.id,
            action="created",
            old_type=old_type,
            new_type=subscription_type,
            changed_by=invite.created_by if invite else None,
            notes=f"Activated via invite code: {invite_code}"
        )
        db.add(history)
        db.commit()
        
        logger.info(f"✅ Подписка {subscription_type} активирована для пользователя {telegram_id}")
        
    except Exception as e:
        logger.error(f"Ошибка активации подписки для {telegram_id}: {e}")
        db.rollback()
    finally:
        db.close()


async def subscription_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать информацию о подписке"""
    user = update.effective_user
    db = SessionLocal()
    
    try:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
            return
        
        if not db_user.is_authenticated:
            await update.message.reply_text(
                "❌ Для просмотра подписки необходимо авторизоваться.\n"
                "Используйте: /login INVITE_CODE"
            )
            return
        
        # Проверяем активность подписки
        is_active = db_user.check_subscription_active()
        tier = get_subscription_info(db_user.subscription_type)
        
        text = f"📊 **Ваша подписка**\n\n"
        text += format_subscription_info(db_user.subscription_type)
        text += f"\n\n📍 **Статус:** {'✅ Активна' if is_active else '❌ Истекла'}\n"
        
        if db_user.subscription_expires:
            if is_active:
                # Убеждаемся что даты timezone-aware
                expires = db_user.subscription_expires
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                
                days_left = (expires - datetime.now(timezone.utc)).days
                text += f"⏰ Осталось дней: {days_left}\n"
            else:
                text += f"⏰ Истекла: {db_user.subscription_expires.strftime('%d.%m.%Y')}\n"
        
        # Использование
        channels_count = len(db_user.channels)
        text += f"\n📈 **Использование:**\n"
        text += f"• Каналов: {channels_count}/{db_user.max_channels}\n"
        
        # Upgrade опции
        if db_user.subscription_type in ["free", "trial"]:
            text += f"\n💎 Хотите больше возможностей?\n"
            text += f"Обратитесь к администратору для upgrade подписки."
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в subscription_command: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
    finally:
        db.close()


# Создаем ConversationHandler
def get_login_conversation_handler():
    """Получить ConversationHandler для /login"""
    return ConversationHandler(
        entry_points=[CommandHandler('login', login_start)],
        states={
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, phone_received)],
            CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, code_received)],
            TWO_FA: [MessageHandler(filters.TEXT & ~filters.COMMAND, password_received)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        per_user=True,          # ✅ КРИТИЧНО: изоляция по пользователям
        per_chat=False,
        name='login_conversation',  # ✅ Для persistence
        persistent=True,        # ✅ Сохранение состояния
        allow_reentry=True      # ✅ КРИТИЧНО: позволяет начать заново с /login
    )

