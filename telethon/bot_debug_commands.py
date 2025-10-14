"""
Debug команды для диагностики проблем с авторизацией
"""

import asyncio
import logging
import os
from datetime import datetime, timezone
from telegram import Update
from telegram.ext import ContextTypes
from telethon import TelegramClient
from telethon.errors import FloodWaitError, PhoneNumberBannedError, PhoneNumberInvalidError
from telethon.sessions import StringSession

from database import SessionLocal
from models import User
from shared_auth_manager import shared_auth_manager

logger = logging.getLogger(__name__)


async def debug_test_phone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Проверить доступность номера для авторизации через Telegram
    Команда: /debug_test_phone +79991234567
    """
    user = update.effective_user
    args = context.args
    
    if not args:
        await update.message.reply_text(
            "📱 **Тест номера телефона**\n\n"
            "Использование: `/debug_test_phone +79991234567`\n\n"
            "Проверяет:\n"
            "• Можно ли отправить SMS код на номер\n"
            "• Не заблокирован ли номер Telegram'ом\n"
            "• FloodWait ограничения\n\n"
            "⚠️ **Внимание:** Отправит реальный SMS код!",
            parse_mode='HTML'
        )
        return
    
    phone = args[0]
    
    await update.message.reply_text("🔍 Проверка номера телефона...\nЭто займет несколько секунд.")
    
    # Создаем временный клиент для теста
    test_client = None
    
    try:
        master_api_id = os.getenv("MASTER_API_ID")
        master_api_hash = os.getenv("MASTER_API_HASH")
        
        # Используем StringSession (в памяти, не сохраняется)
        test_client = TelegramClient(
            StringSession(),
            int(master_api_id),
            master_api_hash,
            connection_retries=2,
            timeout=15
        )
        
        await test_client.connect()
        
        if not test_client.is_connected():
            await update.message.reply_text("❌ Не удалось подключиться к Telegram")
            return
        
        # Пробуем отправить код
        logger.info(f"🧪 Тестовая отправка кода на {phone} для диагностики")
        sent_code = await test_client.send_code_request(phone)
        
        # Успешно!
        text = f"✅ **Номер телефона доступен!**\n\n"
        text += f"📱 Номер: `{phone}`\n"
        text += f"📤 SMS код успешно отправлен\n"
        text += f"🔑 phone_code_hash: `{sent_code.phone_code_hash[:15]}...`\n\n"
        text += f"**Вывод:**\n"
        text += f"• Номер НЕ заблокирован Telegram ✅\n"
        text += f"• Можно использовать для авторизации ✅\n\n"
        text += f"💡 Если при `/login` возникает ошибка 'код истек' - проблема в другом:\n"
        text += f"• Номер уже авторизован в других клиентах\n"
        text += f"• Telegram считает активность подозрительной\n"
        text += f"• Нужно подождать 30-60 минут между попытками"
        
        await update.message.reply_text(text, parse_mode='HTML')
        
    except PhoneNumberBannedError:
        await update.message.reply_text(
            f"❌ **Номер заблокирован Telegram!**\n\n"
            f"📱 Номер: `{phone}`\n"
            f"🚫 Статус: BANNED\n\n"
            f"**Причина:**\n"
            f"• Нарушение правил Telegram\n"
            f"• Спам активность\n"
            f"• Множественные жалобы\n\n"
            f"**Решение:**\n"
            f"• Используйте другой номер телефона\n"
            f"• Обратитесь в поддержку Telegram",
            parse_mode='HTML'
        )
    
    except PhoneNumberInvalidError:
        await update.message.reply_text(
            f"❌ **Неверный формат номера!**\n\n"
            f"📱 Номер: `{phone}`\n\n"
            f"Используйте международный формат:\n"
            f"• `+79991234567` (Россия)\n"
            f"• `+380991234567` (Украина)\n"
            f"• `+12025551234` (США)",
            parse_mark='Markdown'
        )
    
    except FloodWaitError as e:
        await update.message.reply_text(
            f"⏳ **FloodWait ограничение**\n\n"
            f"📱 Номер: `{phone}`\n"
            f"⏰ Подождите: {e.seconds} секунд\n\n"
            f"**Причина:**\n"
            f"• Слишком много SMS кодов за короткий период\n"
            f"• Telegram временно ограничил отправку\n\n"
            f"**Решение:**\n"
            f"• Подождите указанное время\n"
            f"• Попробуйте снова",
            parse_mode='HTML'
        )
    
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        await update.message.reply_text(
            f"⚠️ **Ошибка при проверке номера**\n\n"
            f"📱 Номер: `{phone}`\n"
            f"❌ Тип: `{error_type}`\n"
            f"📝 Сообщение: {error_msg}\n\n"
            f"Скопируйте эту ошибку и отправьте администратору",
            parse_mode='HTML'
        )
        
        logger.error(f"Debug test phone error for {phone}: {error_type} - {error_msg}")
    
    finally:
        if test_client:
            await test_client.disconnect()
            logger.info("🔌 Тестовый клиент отключен")


async def debug_check_sessions_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Проверить активные сессии Telegram (терминал всех сессий кроме текущей)
    Команда: /debug_check_sessions
    """
    user = update.effective_user
    
    text = f"🔍 **Проверка активных сессий**\n\n"
    text += f"Эта команда показывает сколько активных сессий у вашего номера.\n\n"
    text += f"**Для терминации всех сессий:**\n"
    text += f"1. Откройте Telegram Desktop/Mobile\n"
    text += f"2. Settings → Privacy and Security → Active Sessions\n"
    text += f"3. Terminate all other sessions\n\n"
    text += f"После терминации подождите 5-10 минут и попробуйте `/login` снова."
    
    await update.message.reply_text(text, parse_mode='HTML')


async def debug_force_auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    [ADMIN ONLY] Форсировать авторизацию пользователя если session файл существует
    Команда: /debug_force_auth USER_ID или /debug_force_auth TELEGRAM_ID
    """
    user = update.effective_user
    args = context.args
    
    # Проверка админа
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not admin_user or not admin_user.is_admin():
            await update.message.reply_text("❌ Эта команда доступна только администраторам")
            return
    finally:
        db.close()
    
    if not args:
        await update.message.reply_text(
            "🔧 **Force Auth - Admin Tool**\n\n"
            "Использование: `/debug_force_auth USER_ID`\n"
            "или: `/debug_force_auth TELEGRAM_ID`\n\n"
            "⚠️ Использовать только если:\n"
            "• Session файл существует\n"
            "• Пользователь завершил QR auth но БД не обновилась\n"
            "• Нужно вручную активировать авторизацию",
            parse_mode='HTML'
        )
        return
    
    target_id = args[0]
    
    await update.message.reply_text(f"🔍 Поиск пользователя {target_id}...")
    
    db = SessionLocal()
    try:
        # Ищем по ID или telegram_id
        if target_id.isdigit():
            target_user = db.query(User).filter(
                (User.id == int(target_id)) | (User.telegram_id == int(target_id))
            ).first()
        else:
            await update.message.reply_text("❌ ID должен быть числом")
            return
        
        if not target_user:
            await update.message.reply_text(f"❌ Пользователь {target_id} не найден в БД")
            return
        
        # Проверяем существование session файла
        session_file = f"/app/sessions/user_{target_user.telegram_id}.session"
        
        if not os.path.exists(session_file):
            await update.message.reply_text(
                f"❌ Session файл не найден!\n\n"
                f"👤 User ID: {target_user.id}\n"
                f"📱 Telegram ID: {target_user.telegram_id}\n"
                f"📂 Ожидаемый файл: `user_{target_user.telegram_id}.session`\n\n"
                f"**Решение:**\n"
                f"• Пользователь должен завершить QR авторизацию\n"
                f"• Или использовать старый `/login` с SMS",
                parse_mode='HTML'
            )
            return
        
        # Проверяем что сессия валидна
        try:
            test_client = await shared_auth_manager.get_client(target_user.telegram_id)
            if test_client and await test_client.is_user_authorized():
                # Сессия валидна! Обновляем БД
                target_user.is_authenticated = True
                target_user.failed_auth_attempts = 0
                target_user.auth_error = None
                target_user.last_auth_check = datetime.now(timezone.utc)
                
                db.commit()
                
                await update.message.reply_text(
                    f"✅ **Авторизация активирована!**\n\n"
                    f"👤 User ID: {target_user.id}\n"
                    f"📱 Telegram ID: {target_user.telegram_id}\n"
                    f"💎 Подписка: {target_user.subscription_type}\n"
                    f"📊 Каналов: {len(target_user.channels)}/{target_user.max_channels}\n"
                    f"✅ is_authenticated: TRUE\n\n"
                    f"Пользователь может теперь использовать `/my_channels` и другие команды.",
                    parse_mode='HTML'
                )
                
                logger.info(f"✅ ADMIN {user.id} force activated auth for user {target_user.id}")
                
            else:
                await update.message.reply_text(
                    f"⚠️ **Session файл существует, но не валиден**\n\n"
                    f"👤 User ID: {target_user.id}\n"
                    f"📱 Telegram ID: {target_user.telegram_id}\n\n"
                    f"**Причины:**\n"
                    f"• Session файл поврежден\n"
                    f"• Сессия истекла\n"
                    f"• Пользователь разлогинился из Telegram\n\n"
                    f"**Решение:**\n"
                    f"• Пользователь должен пройти QR авторизацию заново",
                    parse_mode='HTML'
                )
        
        except Exception as e:
            await update.message.reply_text(
                f"❌ **Ошибка проверки сессии**\n\n"
                f"📝 {str(e)}\n\n"
                f"Возможно session файл поврежден или недоступен",
                parse_mode='HTML'
            )
            logger.error(f"Force auth error for user {target_user.id}: {e}")
    
    finally:
        db.close()


async def debug_reset_auth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    [ADMIN ONLY] Полный сброс авторизации пользователя для тестирования
    Команда: /debug_reset_auth USER_ID или TELEGRAM_ID
    
    ВАЖНО: Удаляет session файл, сбрасывает БД, очищает память
    Используется для тестирования QR login с нуля
    """
    user = update.effective_user
    args = context.args
    
    # Проверка админа
    db = SessionLocal()
    try:
        admin_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not admin_user or not admin_user.is_admin():
            await update.message.reply_text("❌ Эта команда доступна только администраторам")
            return
    finally:
        db.close()
    
    if not args:
        await update.message.reply_text(
            "🔧 **Reset Auth - Admin Tool**\n\n"
            "Использование: `/debug_reset_auth USER_ID`\n"
            "или: `/debug_reset_auth TELEGRAM_ID`\n\n"
            "⚠️ **ВНИМАНИЕ:** Полностью удаляет авторизацию:\n"
            "• Удаляет session файл\n"
            "• Сбрасывает is_authenticated = FALSE\n"
            "• Очищает из памяти активные клиенты\n"
            "• Удаляет QR сессии из Redis\n\n"
            "Используйте для тестирования QR login с нуля",
            parse_mode='HTML'
        )
        return
    
    target_id = args[0]
    
    await update.message.reply_text(f"🔍 Ищем пользователя {target_id}...")
    
    db = SessionLocal()
    try:
        # Ищем по ID или telegram_id
        if target_id.isdigit():
            target_user = db.query(User).filter(
                (User.id == int(target_id)) | (User.telegram_id == int(target_id))
            ).first()
        else:
            await update.message.reply_text("❌ ID должен быть числом")
            return
        
        if not target_user:
            await update.message.reply_text(f"❌ Пользователь {target_id} не найден в БД")
            return
        
        telegram_id = target_user.telegram_id
        user_id = target_user.id
        
        # Собираем информацию для отчета
        report = []
        report.append(f"👤 **Сброс авторизации пользователя**\n")
        report.append(f"• User ID: {user_id}")
        report.append(f"• Telegram ID: {telegram_id}")
        report.append(f"• Текущий статус: {'✅ Авторизован' if target_user.is_authenticated else '❌ Не авторизован'}")
        report.append(f"• Подписка: {target_user.subscription_type}")
        report.append(f"• Каналов: {len(target_user.channels)}")
        report.append(f"\n⚙️ **Начинаем очистку...**\n")
        
        # 1. Отключаем клиент если активен
        try:
            if telegram_id in shared_auth_manager.active_clients:
                client = shared_auth_manager.active_clients[telegram_id]
                if client.is_connected():
                    await client.disconnect()
                    logger.info(f"🔌 Клиент {telegram_id} отключен")
                    report.append("✅ Клиент отключен")
                
                # Удаляем из памяти
                del shared_auth_manager.active_clients[telegram_id]
                report.append("✅ Удален из памяти (shared_auth_manager)")
            else:
                report.append("• Клиент не был активен в памяти")
        except Exception as e:
            report.append(f"⚠️ Ошибка отключения клиента: {str(e)}")
            logger.error(f"Error disconnecting client {telegram_id}: {e}")
        
        # 2. Удаляем session файл
        session_file = f"/app/sessions/user_{telegram_id}.session"
        try:
            if os.path.exists(session_file):
                os.remove(session_file)
                report.append(f"✅ Session файл удален: `user_{telegram_id}.session`")
                logger.info(f"🗑️ Удален session файл: {session_file}")
            else:
                report.append(f"• Session файл не существовал")
            
            # Удаляем также -journal файл если есть
            journal_file = f"{session_file}-journal"
            if os.path.exists(journal_file):
                os.remove(journal_file)
                report.append(f"✅ Journal файл удален")
        except Exception as e:
            report.append(f"❌ Ошибка удаления session: {str(e)}")
            logger.error(f"Error deleting session file: {e}")
        
        # 3. Сбрасываем флаги в БД
        try:
            target_user.is_authenticated = False
            target_user.failed_auth_attempts = 0
            target_user.auth_error = None
            target_user.last_auth_check = None
            target_user.session_file = None
            
            db.commit()
            report.append("✅ Флаги авторизации сброшены в БД")
            logger.info(f"✅ БД обновлена для пользователя {telegram_id}")
        except Exception as e:
            db.rollback()
            report.append(f"❌ Ошибка обновления БД: {str(e)}")
            logger.error(f"Error updating DB: {e}")
        
        # 4. Очищаем QR сессии из Redis
        try:
            from qr_auth_manager import qr_auth_manager
            
            if qr_auth_manager.redis_client:
                # Ищем все QR сессии для этого пользователя
                keys = qr_auth_manager.redis_client.keys(f"qr_session:*")
                deleted_count = 0
                
                for key in keys:
                    try:
                        session_data = qr_auth_manager.redis_client.get(key)
                        if session_data:
                            import json
                            data = json.loads(session_data)
                            if data.get("telegram_id") == telegram_id:
                                qr_auth_manager.redis_client.delete(key)
                                deleted_count += 1
                    except:
                        pass
                
                if deleted_count > 0:
                    report.append(f"✅ Удалено {deleted_count} QR сессий из Redis")
                else:
                    report.append("• QR сессии не найдены в Redis")
            else:
                report.append("• Redis недоступен")
        except Exception as e:
            report.append(f"⚠️ Ошибка очистки Redis: {str(e)}")
            logger.error(f"Error cleaning Redis: {e}")
        
        # 5. Финальный отчет
        report.append(f"\n🎉 **Сброс завершен!**\n")
        report.append(f"Пользователь {telegram_id} может теперь:")
        report.append(f"• Попробовать `/login INVITE_CODE` заново")
        report.append(f"• Пройти QR авторизацию с нуля")
        report.append(f"• Протестировать весь процесс")
        
        await update.message.reply_text(
            "\n".join(report),
            parse_mode='HTML'
        )
        
        logger.info(f"✅ ADMIN {user.id} reset auth for user {user_id} (telegram_id: {telegram_id})")
        
    except Exception as e:
        await update.message.reply_text(
            f"❌ **Критическая ошибка**\n\n"
            f"📝 {str(e)}\n\n"
            f"Проверьте логи сервера",
            parse_mode='HTML'
        )
        logger.error(f"Critical error in debug_reset_auth: {e}", exc_info=True)
    
    finally:
        db.close()


async def debug_delete_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    [ADMIN ONLY] ПОЛНОЕ удаление пользователя из системы  
    Команда: /debug_delete_user USER_ID или TELEGRAM_ID
    
    ВНИМАНИЕ: Удаляет ВСЁ - пользователя, каналы, подписку, session
    Необратимая операция!
    """
    user = update.effective_user
    args = context.args
    
    logger.info(f"🔧 DEBUG: debug_delete_user вызвана пользователем {user.id}, args: {args}")
    print(f"🔧 DEBUG: debug_delete_user START - user={user.id}, args={args}")  # Force print
    
    try:
        await update.message.reply_text(f"🔧 Команда получена! args={args}")
        logger.info(f"📤 Sent initial reply")
        
        # Проверка админа  
        db = SessionLocal()
        try:
            admin_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not admin_user:
                await update.message.reply_text("❌ Пользователь не найден в БД")
                logger.warning(f"Admin user {user.id} not found in DB")
                return
            
            if not admin_user.is_admin():
                await update.message.reply_text("❌ Эта команда доступна только администраторам")
                logger.warning(f"User {user.id} tried to use admin command")
                return
            
            logger.info(f"✅ Admin check passed for {user.id}")
        finally:
            db.close()
        
        if not args:
            await update.message.reply_text(
                "🗑️ **Delete User - Admin Tool**\n\n"
                "Использование: `/debug_delete_user USER_ID`\n\n"
                "⚠️ **ВНИМАНИЕ - НЕОБРАТИМО:**\n"
                "• Полностью удаляет пользователя из БД\n"
                "• Удаляет все связанные данные\n"
                "• Удаляет session файл",
                parse_mode='HTML'
            )
            return
        
        target_id = args[0]
        logger.info(f"🔍 Ищем пользователя {target_id}")
        
        await update.message.reply_text(f"🔍 Ищем пользователя {target_id}...")
        
        db = SessionLocal()
        try:
            if target_id.isdigit():
                target_user = db.query(User).filter(
                    (User.id == int(target_id)) | (User.telegram_id == int(target_id))
                ).first()
            else:
                await update.message.reply_text("❌ ID должен быть числом")
                return
            
            if not target_user:
                await update.message.reply_text(f"❌ Пользователь {target_id} не найден")
                logger.warning(f"Target user {target_id} not found")
                return
            
            telegram_id = target_user.telegram_id
            user_id = target_user.id
            
            logger.info(f"✅ Найден: user_id={user_id}, telegram_id={telegram_id}")
            
            report = []
            report.append(f"🗑️ **Удаление пользователя {user_id}**\n")
            
            # 1. Отключаем клиент (БЕЗ await disconnect - может зависнуть!)
            try:
                if telegram_id in shared_auth_manager.active_clients:
                    # Просто удаляем из словаря, disconnect делать НЕ нужно
                    del shared_auth_manager.active_clients[telegram_id]
                    report.append("✅ Клиент удален из памяти")
                    logger.info(f"🗑️ Client {telegram_id} removed from memory")
                else:
                    report.append("• Клиент не был активен")
                    logger.info(f"Client {telegram_id} not in active_clients")
            except Exception as e:
                report.append(f"⚠️ Ошибка удаления клиента: {str(e)}")
                logger.error(f"Error removing client: {e}", exc_info=True)
            
            # 2. Удаляем session файл
            session_file = f"/app/sessions/user_{telegram_id}.session"
            try:
                deleted_files = []
                if os.path.exists(session_file):
                    os.remove(session_file)
                    deleted_files.append("session")
                
                journal_file = f"{session_file}-journal"
                if os.path.exists(journal_file):
                    os.remove(journal_file)
                    deleted_files.append("journal")
                
                if deleted_files:
                    report.append(f"✅ Удалено: {', '.join(deleted_files)}")
                    logger.info(f"🗑️ Deleted files for {telegram_id}: {deleted_files}")
                else:
                    report.append("• Session файлы не найдены")
                    logger.info(f"No session files found for {telegram_id}")
            except Exception as e:
                report.append(f"⚠️ Ошибка удаления файлов: {str(e)}")
                logger.error(f"Error deleting session: {e}", exc_info=True)
            
            # 3. Очищаем SubscriptionHistory (сначала changed_by, потом user_id)
            try:
                from models import SubscriptionHistory
                
                # 3.1. Обнуляем changed_by где пользователь был админом
                admin_records = db.query(SubscriptionHistory).filter(
                    SubscriptionHistory.changed_by == user_id
                ).all()
                
                if admin_records:
                    for record in admin_records:
                        record.changed_by = None
                        record.notes = f"{record.notes or ''} [Admin user deleted]".strip()
                    db.commit()
                    report.append(f"✅ Обнулено {len(admin_records)} записей где был админом")
                    logger.info(f"Nullified {len(admin_records)} admin references")
                
                # 3.2. Удаляем записи где пользователь - owner
                user_records = db.query(SubscriptionHistory).filter(
                    SubscriptionHistory.user_id == user_id
                ).delete()
                
                if user_records > 0:
                    db.commit()
                    report.append(f"✅ Удалено {user_records} записей подписки")
                    logger.info(f"Deleted {user_records} subscription history records")
                
            except Exception as e:
                logger.warning(f"Error cleaning subscription_history: {e}")
                report.append(f"⚠️ История подписок: {str(e)}")
            
            # 4. Удаляем пользователя из БД
            try:
                logger.info(f"🗑️ Deleting user {user_id} from DB...")
                db.delete(target_user)
                db.commit()
                report.append("✅ Пользователь удален из БД")
                report.append(f"\n🎉 Готово! User {telegram_id} полностью удален")
                logger.info(f"✅ User {user_id} deleted from DB")
                
                await update.message.reply_text(
                    "\n".join(report),
                    parse_mode='HTML'
                )
                logger.info(f"✅ ADMIN {user.id} deleted user {user_id}")
                
            except Exception as e:
                db.rollback()
                error_msg = str(e)
                report.append(f"❌ Ошибка БД: {error_msg}")
                await update.message.reply_text(
                    "\n".join(report),
                    parse_mode='HTML'
                )
                logger.error(f"Error deleting user from DB: {e}", exc_info=True)
        
        except Exception as e:
            logger.error(f"Critical error in try block: {e}", exc_info=True)
            from telegram_formatter import markdownify
            await update.message.reply_text(
                markdownify(f"❌ Ошибка: {str(e)}"),
                parse_mode='HTML'
            )
        finally:
            db.close()
            logger.info("🔒 DB session closed")
    
    except Exception as e:
        logger.error(f"❌ CRITICAL: Unhandled exception in debug_delete_user: {e}", exc_info=True)
        try:
            await update.message.reply_text(f"❌ Критическая ошибка: {str(e)}")
        except:
            pass

