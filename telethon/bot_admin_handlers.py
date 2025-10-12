"""
Админ команды для управления пользователями, инвайтами и подписками
"""

import logging
from datetime import datetime, timedelta, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler

from database import SessionLocal
from models import User, InviteCode, SubscriptionHistory
from subscription_config import get_subscription_info, SUBSCRIPTION_TIERS

logger = logging.getLogger(__name__)


def is_admin(telegram_id: int) -> bool:
    """Проверка является ли пользователь администратором"""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.telegram_id == telegram_id).first()
        return user and user.is_admin()
    finally:
        db.close()


async def admin_invite_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Создать инвайт код (интерактивное меню)
    Команда: /admin_invite
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    # Показываем меню выбора типа подписки
    keyboard = [
        [InlineKeyboardButton("🎁 Trial (7 дней)", callback_data="invite_trial")],
        [InlineKeyboardButton("💼 Basic", callback_data="invite_basic")],
        [InlineKeyboardButton("💎 Premium", callback_data="invite_premium")],
        [InlineKeyboardButton("🏢 Enterprise", callback_data="invite_enterprise")],
        [InlineKeyboardButton("🆓 Free", callback_data="invite_free")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📝 **Создание инвайт кода**\n\n"
        "Выберите тип подписки:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def admin_invite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка выбора типа подписки для инвайта"""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    if not is_admin(user.id):
        await query.edit_message_text("❌ Нет доступа")
        return
    
    data = query.data
    
    if data.startswith("invite_"):
        subscription_type = data.replace("invite_", "")
        
        # Показываем меню выбора срока действия
        keyboard = [
            [InlineKeyboardButton("1 день", callback_data=f"expire_{subscription_type}_1")],
            [InlineKeyboardButton("7 дней", callback_data=f"expire_{subscription_type}_7")],
            [InlineKeyboardButton("30 дней", callback_data=f"expire_{subscription_type}_30")],
            [InlineKeyboardButton("Без срока (365 дней)", callback_data=f"expire_{subscription_type}_365")],
            [InlineKeyboardButton("← Назад", callback_data="invite_back")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        tier = get_subscription_info(subscription_type)
        await query.edit_message_text(
            f"🎯 **Подписка:** {tier['name']}\n\n"
            f"⏰ Выберите срок действия инвайт кода:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    elif data.startswith("expire_"):
        # Создаем инвайт код
        parts = data.split("_")
        subscription_type = parts[1]
        expire_days = int(parts[2])
        
        await create_invite_code(query, user.id, subscription_type, expire_days)
    
    elif data == "invite_back":
        # Возврат к выбору подписки
        await admin_invite_command(update, context)


async def create_invite_code(query, admin_telegram_id: int, subscription_type: str, expire_days: int):
    """Создать инвайт код"""
    db = SessionLocal()
    
    try:
        # Получаем админа
        admin = db.query(User).filter(User.telegram_id == admin_telegram_id).first()
        if not admin:
            await query.edit_message_text("❌ Админ не найден")
            return
        
        # Генерируем код
        code = InviteCode.generate_code()
        
        # Определяем trial period
        trial_days = 0
        if subscription_type == "trial":
            trial_days = 7
        
        # Создаем инвайт
        invite = InviteCode(
            code=code,
            created_by=admin.id,
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=expire_days),
            max_uses=1,
            uses_count=0,
            default_subscription=subscription_type,
            default_trial_days=trial_days
        )
        
        db.add(invite)
        db.commit()
        
        tier = get_subscription_info(subscription_type)
        expires_at = invite.expires_at.strftime('%d.%m.%Y %H:%M')
        
        text = f"✅ **Инвайт код создан!**\n\n"
        text += f"🎫 Код: `{code}`\n\n"
        text += f"📊 **Параметры:**\n"
        text += f"• Подписка: {tier['name']}\n"
        text += f"• Действует до: {expires_at}\n"
        text += f"• Использований: 0/1\n\n"
        text += f"💡 Отправьте этот код пользователю:\n"
        text += f"`/login {code}`"
        
        await query.edit_message_text(text, parse_mode='Markdown')
        logger.info(f"✅ Админ {admin_telegram_id} создал инвайт код {code} ({subscription_type})")
        
    except Exception as e:
        logger.error(f"Ошибка создания инвайт кода: {e}")
        await query.edit_message_text(f"❌ Ошибка: {str(e)}")
    finally:
        db.close()


async def admin_users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Список пользователей с фильтрацией
    Команда: /admin_users [filter]
    Фильтры: all, active, expired, free, premium
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    args = context.args
    filter_type = args[0] if args else "all"
    
    db = SessionLocal()
    
    try:
        query = db.query(User)
        
        if filter_type == "active":
            query = query.filter(User.is_authenticated == True)
        elif filter_type == "expired":
            # Для PostgreSQL используем timezone-aware сравнение
            now = datetime.now(timezone.utc)
            query = query.filter(
                User.subscription_expires != None,
                User.subscription_expires < now
            )
        elif filter_type in SUBSCRIPTION_TIERS:
            query = query.filter(User.subscription_type == filter_type)
        
        users = query.order_by(User.created_at.desc()).limit(50).all()
        
        if not users:
            await update.message.reply_text("📭 Пользователи не найдены")
            return
        
        text = f"👥 **Пользователи** ({filter_type})\n\n"
        
        for u in users[:20]:  # Показываем первых 20
            name = u.first_name or u.username or "Unknown"
            status = "✅" if u.is_authenticated else "❌"
            role = "👑" if u.role == "admin" else "👤"
            
            text += f"{role} {status} {name} (@{u.username or 'none'})\n"
            text += f"   ID: `{u.telegram_id}`\n"
            text += f"   Подписка: {u.subscription_type}\n"
            
            if u.subscription_expires:
                if u.check_subscription_active():
                    # Убеждаемся что даты timezone-aware
                    expires = u.subscription_expires
                    if expires.tzinfo is None:
                        expires = expires.replace(tzinfo=timezone.utc)
                    
                    days = (expires - datetime.now(timezone.utc)).days
                    text += f"   До истечения: {days} дн.\n"
                else:
                    text += f"   Истекла ❌\n"
            
            text += "\n"
        
        if len(users) > 20:
            text += f"... и еще {len(users) - 20} пользователей\n"
        
        text += f"\n💡 Для деталей: /admin_user <telegram_id>"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в admin_users: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
    finally:
        db.close()


async def admin_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Информация о конкретном пользователе
    Команда: /admin_user <telegram_id>
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("Использование: /admin_user <telegram_id>")
        return
    
    target_telegram_id = int(args[0])
    db = SessionLocal()
    
    try:
        target_user = db.query(User).filter(User.telegram_id == target_telegram_id).first()
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        name = target_user.first_name or "Unknown"
        tier = get_subscription_info(target_user.subscription_type)
        
        text = f"👤 **Пользователь:** {name}\n"
        text += f"🆔 Telegram ID: `{target_telegram_id}`\n"
        text += f"👤 Username: @{target_user.username or 'none'}\n"
        text += f"📅 Регистрация: {target_user.created_at.strftime('%d.%m.%Y')}\n\n"
        
        text += f"📊 **Подписка:** {tier['name']}\n"
        text += f"📍 Статус: {'✅ Активна' if target_user.check_subscription_active() else '❌ Истекла'}\n"
        
        if target_user.subscription_expires:
            text += f"⏰ До: {target_user.subscription_expires.strftime('%d.%m.%Y')}\n"
        
        text += f"\n📈 **Использование:**\n"
        text += f"• Каналов: {len(target_user.channels)}/{target_user.max_channels}\n"
        text += f"• Постов: {len(target_user.posts)}\n"
        
        text += f"\n🔐 **Статус:**\n"
        text += f"• Авторизован: {'✅' if target_user.is_authenticated else '❌'}\n"
        text += f"• Роль: {target_user.role}\n"
        
        if target_user.invited_by:
            inviter = db.query(User).filter(User.id == target_user.invited_by).first()
            if inviter:
                text += f"• Приглашен: {inviter.first_name} ({inviter.telegram_id})\n"
        
        # История подписок
        history = db.query(SubscriptionHistory).filter(
            SubscriptionHistory.user_id == target_user.id
        ).order_by(SubscriptionHistory.changed_at.desc()).limit(5).all()
        
        if history:
            text += f"\n📜 **История подписок:**\n"
            for h in history:
                text += f"• {h.action}: {h.old_type} → {h.new_type} ({h.changed_at.strftime('%d.%m.%Y')})\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в admin_user: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
    finally:
        db.close()


async def admin_grant_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Выдать подписку пользователю
    Команда: /admin_grant <telegram_id> <subscription> [days]
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "Использование: /admin_grant <telegram_id> <subscription> [days]\n\n"
            "Пример: /admin_grant 123456789 premium 30"
        )
        return
    
    target_telegram_id = int(args[0])
    subscription_type = args[1]
    days = int(args[2]) if len(args) > 2 else 30
    
    if subscription_type not in SUBSCRIPTION_TIERS:
        await update.message.reply_text(
            f"❌ Неверный тип подписки. Доступные: {', '.join(SUBSCRIPTION_TIERS.keys())}"
        )
        return
    
    db = SessionLocal()
    
    try:
        target_user = db.query(User).filter(User.telegram_id == target_telegram_id).first()
        admin_user = db.query(User).filter(User.telegram_id == user.id).first()
        
        if not target_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        old_type = target_user.subscription_type
        target_user.subscription_type = subscription_type
        target_user.subscription_started_at = datetime.now(timezone.utc)
        target_user.subscription_expires = datetime.now(timezone.utc) + timedelta(days=days)
        
        # Обновляем лимиты
        tier = get_subscription_info(subscription_type)
        target_user.max_channels = tier['max_channels']
        
        db.commit()
        
        # Записываем в историю
        history = SubscriptionHistory(
            user_id=target_user.id,
            action="upgraded",
            old_type=old_type,
            new_type=subscription_type,
            changed_by=admin_user.id,
            notes=f"Granted by admin for {days} days"
        )
        db.add(history)
        db.commit()
        
        await update.message.reply_text(
            f"✅ Подписка **{tier['name']}** выдана пользователю {target_user.first_name}\n"
            f"Срок: {days} дней",
            parse_mode='Markdown'
        )
        
        logger.info(f"✅ Админ {user.id} выдал подписку {subscription_type} пользователю {target_telegram_id}")
        
    except Exception as e:
        logger.error(f"Ошибка в admin_grant: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
    finally:
        db.close()


async def admin_stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Статистика по боту
    Команда: /admin_stats
    """
    user = update.effective_user
    
    if not is_admin(user.id):
        await update.message.reply_text("❌ Эта команда доступна только администраторам")
        return
    
    db = SessionLocal()
    
    try:
        total_users = db.query(User).count()
        authenticated_users = db.query(User).filter(User.is_authenticated == True).count()
        
        # Подписки
        subscription_counts = {}
        for tier_name in SUBSCRIPTION_TIERS.keys():
            count = db.query(User).filter(User.subscription_type == tier_name).count()
            subscription_counts[tier_name] = count
        
        # Активные подписки
        now = datetime.now(timezone.utc)
        active_subscriptions = db.query(User).filter(
            User.subscription_expires != None,
            User.subscription_expires > now
        ).count()
        
        # Инвайт коды
        total_invites = db.query(InviteCode).count()
        used_invites = db.query(InviteCode).filter(InviteCode.uses_count > 0).count()
        
        text = f"📊 **Статистика бота**\n\n"
        text += f"👥 **Пользователи:**\n"
        text += f"• Всего: {total_users}\n"
        text += f"• Авторизовано: {authenticated_users}\n\n"
        
        text += f"💎 **Подписки:**\n"
        for tier_name, count in subscription_counts.items():
            if count > 0:
                tier = get_subscription_info(tier_name)
                text += f"• {tier['name']}: {count}\n"
        
        text += f"\n✅ Активных подписок: {active_subscriptions}\n"
        
        text += f"\n🎫 **Инвайт коды:**\n"
        text += f"• Всего создано: {total_invites}\n"
        text += f"• Использовано: {used_invites}\n"
        
        await update.message.reply_text(text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Ошибка в admin_stats: {e}")
        await update.message.reply_text("❌ Произошла ошибка")
    finally:
        db.close()


def get_admin_callback_handler():
    """Получить CallbackQueryHandler для админ меню"""
    return CallbackQueryHandler(admin_invite_callback, pattern="^(invite_|expire_)")


# ============================================================
# Admin Panel Mini App
# ============================================================

async def admin_panel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Открыть Admin Panel через Telegram Mini App
    Команда: /admin
    """
    from telegram import WebAppInfo
    from admin_panel_manager import admin_panel_manager
    import os
    
    user = update.effective_user
    
    # Проверяем права администратора
    if not is_admin(user.id):
        await update.message.reply_text(
            "❌ **Доступ запрещен**\n\n"
            "Эта команда доступна только администраторам",
            parse_mode='Markdown'
        )
        return
    
    # Создаем admin session в Redis
    session_token = admin_panel_manager.create_admin_session(user.id)
    
    if not session_token:
        await update.message.reply_text(
            "❌ **Ошибка**\n\n"
            "Не удалось создать админ сессию. Попробуйте позже.",
            parse_mode='Markdown'
        )
        return
    
    # Формируем URL для Mini App
    base_url = os.getenv("AUTH_BASE_URL", "https://telegram-auth.produman.studio")
    admin_panel_url = f"{base_url}/admin-panel?admin_id={user.id}&token={session_token}"
    
    # Кнопка для открытия Mini App
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton(
            "👑 Открыть Админ Панель",
            web_app=WebAppInfo(url=admin_panel_url)
        )
    ]])
    
    await update.message.reply_text(
        "👑 **Админ Панель**\n\n"
        "Нажмите кнопку ниже чтобы открыть админ панель:\n\n"
        "**Функции:**\n"
        "• 👥 Управление пользователями\n"
        "• 🎫 Создание инвайт кодов\n"
        "• 📊 Статистика\n"
        "• 📈 Графики и аналитика\n\n"
        "⏰ Session действует 1 час",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )
    
    logger.info(f"👑 Админ {user.id} ({user.first_name}) открыл админ панель")

