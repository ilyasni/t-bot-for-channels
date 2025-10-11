from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import User, Channel, Post
from auth import create_auth_session, get_auth_url, check_user_auth_status, logout_user
from datetime import datetime, timedelta
import re
import os
import time
import logging
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
        # Словарь для хранения состояний пользователей
        self.user_states = {}
        # Таймаут для состояний (30 минут)
        self.state_timeout = 30 * 60  # 30 минут в секундах
    
    def _cleanup_expired_states(self):
        """Очистка устаревших состояний пользователей"""
        current_time = time.time()
        expired_users = []
        
        for user_id, state in self.user_states.items():
            if isinstance(state, dict) and 'timestamp' in state:
                if current_time - state['timestamp'] > self.state_timeout:
                    expired_users.append(user_id)
        
        for user_id in expired_users:
            del self.user_states[user_id]
        
        if expired_users:
            logger.info(f"🧹 Очищено {len(expired_users)} устаревших состояний")
    
    async def _process_auth_code(self, user, code: str, update: Update = None):
        """Общий метод для обработки кода аутентификации"""
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                message = "❌ Пользователь не найден"
                if update:
                    await update.message.reply_text(message)
                return
            
            if db_user.is_authenticated:
                message = "✅ Вы уже аутентифицированы!"
                if update:
                    await update.message.reply_text(message)
                return
            
            # Код проверяется через веб-интерфейс
            result = False  # Эта функция больше не используется
            
            if result:
                message = (
                    "✅ Аутентификация успешна!\n"
                    "Теперь вы можете использовать все функции бота.\n"
                    "Используйте /add_channel для добавления каналов."
                )
                if update:
                    await update.message.reply_text(message)
                # Очищаем состояние пользователя
                if user.id in self.user_states:
                    del self.user_states[user.id]
            else:
                message = (
                    "❌ Неверный код аутентификации.\n"
                    "Попробуйте еще раз или начните процесс заново с /auth"
                )
                if update:
                    await update.message.reply_text(message)
            
        except Exception as e:
            message = f"❌ Ошибка: {str(e)}"
            if update:
                await update.message.reply_text(message)
        finally:
            db.close()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("auth", self.auth_command))
        self.application.add_handler(CommandHandler("auth_status", self.auth_status_command))
        self.application.add_handler(CommandHandler("logout", self.logout_command))
        self.application.add_handler(CommandHandler("clear_auth", self.clear_auth_command))
        self.application.add_handler(CommandHandler("reset_auth", self.reset_auth_command))
        self.application.add_handler(CommandHandler("add_channel", self.add_channel_command))
        self.application.add_handler(CommandHandler("my_channels", self.my_channels_command))
        self.application.add_handler(CommandHandler("remove_channel", self.remove_channel_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            # Проверяем, существует ли пользователь
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
                
                welcome_text = f"""
🤖 Добро пожаловать в Telegram Channel Parser Bot!

Я помогу вам отслеживать посты из ваших любимых каналов.

🔐 Для начала работы необходимо пройти аутентификацию:
/auth - Начать процесс аутентификации

📋 После аутентификации будут доступны команды:
/add_channel - Добавить канал для отслеживания
/my_channels - Показать ваши каналы
/remove_channel - Удалить канал
/help - Показать справку
                """
            else:
                if db_user.is_authenticated:
                    welcome_text = f"""
🤖 С возвращением, {user.first_name}!

✅ Вы аутентифицированы и можете использовать все функции.

📋 Ваши команды:
/add_channel - Добавить канал для отслеживания
/my_channels - Показать ваши каналы
/remove_channel - Удалить канал
/auth_status - Проверить статус аутентификации
/logout - Выйти из системы
/help - Показать справку
                    """
                else:
                    welcome_text = f"""
🤖 С возвращением, {user.first_name}!

⚠️ Для использования функций необходимо пройти аутентификацию:
/auth - Начать процесс аутентификации
/auth_status - Проверить статус аутентификации
                    """
            
            await update.message.reply_text(welcome_text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /auth - безопасная аутентификация через веб-интерфейс"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            if db_user.is_authenticated:
                await update.message.reply_text("✅ Вы уже аутентифицированы!")
                return
            
            # Проверяем блокировку
            if db_user.is_blocked and db_user.block_expires and db_user.block_expires > datetime.now():
                await update.message.reply_text(
                    f"🚫 Ваш аккаунт заблокирован до {db_user.block_expires.strftime('%d.%m.%Y %H:%M')}\n"
                    f"Причина: превышено количество неудачных попыток аутентификации"
                )
                return
            
            # Создаем сессию аутентификации
            session_id = await create_auth_session(db_user)
            if not session_id:
                await update.message.reply_text(
                    "❌ Не удалось создать сессию аутентификации.\n"
                    "Возможно, превышен лимит попыток. Попробуйте позже."
                )
                return
            
            # Получаем URL для аутентификации
            auth_url = await get_auth_url(session_id)
            if not auth_url:
                await update.message.reply_text("❌ Ошибка создания ссылки для аутентификации")
                return
            
            # Создаем кнопку с ссылкой
            keyboard = [[InlineKeyboardButton("🔐 Открыть форму аутентификации", url=auth_url)]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "🔐 Безопасная аутентификация\n\n"
                "Для аутентификации используйте защищенную веб-форму:\n\n"
                "⚠️ **ВАЖНО:** Никогда не вводите коды аутентификации в Telegram чат!\n\n"
                "📋 Инструкция:\n"
                "1. Нажмите кнопку ниже\n"
                "2. Введите ваши API данные\n"
                "3. Получите код в Telegram\n"
                "4. Введите код в веб-форме\n\n"
                "🔗 Ссылка действительна 10 минут",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def auth_code_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /auth_code - ОТКЛЮЧЕНА по соображениям безопасности"""
        await update.message.reply_text(
            "🚫 **Команда отключена по соображениям безопасности**\n\n"
            "⚠️ Ввод кодов аутентификации в Telegram чат небезопасен!\n\n"
            "✅ **Безопасный способ:**\n"
            "1. Используйте команду /auth\n"
            "2. Откройте защищенную веб-форму\n"
            "3. Введите код там\n\n"
            "🔐 Веб-форма использует HTTPS шифрование",
            parse_mode='Markdown'
        )
    
    async def auth_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /auth_status - проверка статуса аутентификации"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            if db_user.is_authenticated:
                status_text = f"""
✅ Статус аутентификации: АУТЕНТИФИЦИРОВАН

👤 Пользователь: {db_user.first_name} {db_user.last_name or ''}
🆔 Telegram ID: {db_user.telegram_id}
📅 Последняя проверка: {db_user.last_auth_check.strftime('%d.%m.%Y %H:%M') if db_user.last_auth_check else 'Не проводилась'}

Вы можете использовать все функции бота.
                """
            else:
                status_text = f"""
❌ Статус аутентификации: НЕ АУТЕНТИФИЦИРОВАН

👤 Пользователь: {db_user.first_name} {db_user.last_name or ''}
🆔 Telegram ID: {db_user.telegram_id}
📅 Последняя проверка: {db_user.last_auth_check.strftime('%d.%m.%Y %H:%M') if db_user.last_auth_check else 'Не проводилась'}

Для использования функций пройдите аутентификацию: /auth
                """
                
                if db_user.auth_error:
                    status_text += f"\n⚠️ Последняя ошибка: {db_user.auth_error}"
            
            await update.message.reply_text(status_text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def logout_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /logout - выход из системы"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            if not db_user.is_authenticated:
                await update.message.reply_text("❌ Вы не аутентифицированы")
                return
            
            # Выходим из системы
            await logout_user(db_user)
            
            # Очищаем состояние пользователя
            if user.id in self.user_states:
                del self.user_states[user.id]
            
            await update.message.reply_text(
                "✅ Вы успешно вышли из системы.\n"
                "Для повторного использования функций пройдите аутентификацию: /auth"
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def clear_auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /clear_auth - полная очистка аутентификации"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            # Очищаем состояние пользователя
            if user.id in self.user_states:
                del self.user_states[user.id]
            
            # Полностью сбрасываем все данные аутентификации
            db_user.is_authenticated = False
            db_user.auth_error = None
            db_user.api_id = None
            db_user.api_hash = None
            db_user.phone_number = None
            db_user.auth_session_id = None
            db_user.auth_session_expires = None
            db_user.failed_auth_attempts = 0
            db_user.last_auth_attempt = None
            db_user.is_blocked = False
            db_user.block_expires = None
            db_user.last_auth_check = None
            db.commit()
            
            logger.info(f"🧹 Пользователь {user.id} очистил все данные аутентификации")
            
            await update.message.reply_text(
                "🧹 **Полная очистка аутентификации выполнена!**\n\n"
                "✅ Удалено:\n"
                "• API данные (ID, Hash, телефон)\n"
                "• Сессии аутентификации\n"
                "• Счетчики попыток\n"
                "• Статусы блокировки\n\n"
                "🔄 Используйте /auth для новой аутентификации"
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка очистки аутентификации для пользователя {user.id}: {str(e)}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def reset_auth_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /reset_auth - алиас для /clear_auth"""
        await self.clear_auth_command(update, context)
    
    async def add_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды добавления канала"""
        user = update.effective_user
        args = context.args
        
        if not args:
            await update.message.reply_text(
                "📝 Использование: /add_channel @channel_name\n"
                "Пример: /add_channel @example_channel"
            )
            return
        
        channel_username = args[0].lstrip('@')
        db = SessionLocal()
        
        try:
            # Получаем пользователя
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            # Проверяем аутентификацию
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Для добавления каналов необходимо пройти аутентификацию.\n"
                    "Используйте команду /auth"
                )
                return
            
            # Проверяем, не подписан ли уже пользователь на этот канал
            if db_user.channels:
                for channel in db_user.channels:
                    if channel.channel_username == channel_username:
                        await update.message.reply_text(f"❌ Канал @{channel_username} уже добавлен в ваш список")
                        return
            
            # Получаем или создаем канал (может быть уже добавлен другими пользователями)
            channel = Channel.get_or_create(db, channel_username)
            
            # Добавляем пользователя к каналу
            channel.add_user(db, db_user, is_active=True)
            db.commit()
            
            await update.message.reply_text(
                f"✅ Канал @{channel_username} успешно добавлен!\n"
                f"Теперь я буду отслеживать новые посты из этого канала."
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка при добавлении канала: {str(e)}")
        finally:
            db.close()
    
    async def my_channels_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать каналы пользователя"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            # Проверяем аутентификацию
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Для просмотра каналов необходимо пройти аутентификацию.\n"
                    "Используйте команду /auth"
                )
                return
            
            # Получаем каналы пользователя с информацией о подписке
            channels_with_info = db_user.get_all_channels(db)
            
            if not channels_with_info:
                await update.message.reply_text(
                    "📭 У вас пока нет добавленных каналов.\n"
                    "Добавьте канал командой /add_channel @channel_name"
                )
                return
            
            text = "📋 Ваши каналы:\n\n"
            keyboard = []
            
            for i, (channel, sub_info) in enumerate(channels_with_info):
                status = "✅ Активен" if sub_info['is_active'] else "❌ Неактивен"
                text += f"{i+1}. @{channel.channel_username} - {status}\n"
                
                # Создаем кнопку для удаления
                keyboard.append([
                    InlineKeyboardButton(
                        f"🗑️ Удалить @{channel.channel_username}",
                        callback_data=f"remove_{channel.id}"
                    )
                ])
            
            text += "\n💡 Используйте кнопки ниже для удаления каналов"
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(text, reply_markup=reply_markup)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def remove_channel_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды удаления канала"""
        await self.my_channels_command(update, context)
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        await query.answer()
        
        if query.data.startswith("remove_"):
            channel_id = int(query.data.split("_")[1])
            await self.remove_channel_by_id(query, channel_id)
    
    async def remove_channel_by_id(self, query, channel_id: int):
        """Удаление канала (отписка пользователя от канала)"""
        user = query.from_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await query.edit_message_text("❌ Пользователь не найден")
                return
            
            # Получаем канал
            channel = db.query(Channel).filter(Channel.id == channel_id).first()
            
            if not channel:
                await query.edit_message_text("❌ Канал не найден")
                return
            
            # Проверяем, подписан ли пользователь на этот канал
            if channel not in db_user.channels:
                await query.edit_message_text("❌ Вы не подписаны на этот канал")
                return
            
            channel_username = channel.channel_username
            
            # Отписываем пользователя от канала
            channel.remove_user(db, db_user)
            db.commit()
            
            # Проверяем, остались ли еще подписчики у канала
            if not channel.users:
                # Если это был последний подписчик, удаляем канал
                db.delete(channel)
                db.commit()
                await query.edit_message_text(
                    f"✅ Канал @{channel_username} успешно удален!\n"
                    f"(Больше нет подписчиков на этот канал)"
                )
            else:
                await query.edit_message_text(f"✅ Вы отписались от канала @{channel_username}!")
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при удалении: {str(e)}")
        finally:
            db.close()
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        user = update.effective_user
        text = update.message.text
        
        # Очищаем устаревшие состояния
        self._cleanup_expired_states()
        
        # Если пользователь пытается ввести код аутентификации в чат
        if text.isdigit() and len(text) == 5:
            await update.message.reply_text(
                "🚫 **Небезопасно!**\n\n"
                "⚠️ Не вводите коды аутентификации в Telegram чат!\n\n"
                "✅ **Безопасный способ:**\n"
                "1. Используйте команду /auth\n"
                "2. Откройте веб-форму по ссылке\n"
                "3. Введите код там\n\n"
                "🔐 Веб-форма защищена HTTPS шифрованием",
                parse_mode='Markdown'
            )
            return
        
        # Если сообщение начинается с @, предлагаем добавить канал
        if text.startswith('@'):
            await update.message.reply_text(
                f"💡 Хотите добавить канал {text} для отслеживания?\n"
                f"Используйте команду: /add_channel {text}"
            )
        else:
            await update.message.reply_text(
                "💡 Используйте команды:\n"
                "/auth - Безопасная аутентификация\n"
                "/add_channel - Добавить канал\n"
                "/my_channels - Ваши каналы\n"
                "/help - Справка\n\n"
                "⚠️ Для аутентификации используйте веб-форму из команды /auth"
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по командам"""
        help_text = """
🤖 Telegram Channel Parser Bot - Справка

🔐 Команды аутентификации:
/auth - Безопасная аутентификация через веб-форму
/auth_status - Проверить статус аутентификации
/logout - Выйти из системы
/clear_auth - Очистить данные аутентификации (при блокировке)
/reset_auth - Полный сброс аутентификации (алиас для /clear_auth)

📋 Команды управления каналами:
/add_channel @channel_name - Добавить канал для отслеживания
Пример: /add_channel @example_channel

/my_channels - Показать список ваших каналов

/remove_channel - Удалить канал из списка

/help - Показать эту справку

💡 Как это работает:
1. Пройдите безопасную аутентификацию командой /auth
2. Откройте веб-форму по ссылке из бота
3. Введите ваши API данные и код в защищенной форме
4. Добавьте каналы командой /add_channel
5. Бот автоматически будет парсить новые посты
6. Посты сохраняются в базе данных
7. Вы можете анализировать их через n8n

🔐 Для получения API_ID и API_HASH:
1. Перейдите на https://my.telegram.org
2. Войдите в свой аккаунт Telegram
3. Создайте новое приложение
4. Скопируйте API_ID и API_HASH

⚠️ БЕЗОПАСНОСТЬ:
- Никогда не вводите коды аутентификации в Telegram чат!
- Используйте только веб-форму из команды /auth
- Веб-форма защищена HTTPS шифрованием
- Ваши данные зашифрованы в базе данных

❓ Если у вас есть вопросы, обратитесь к администратору.
        """
        await update.message.reply_text(help_text)
    
    def run(self):
        """Запуск бота"""
        print("🤖 Запуск Telegram бота...")
        self.application.run_polling()

if __name__ == "__main__":
    from database import create_tables
    create_tables()
    
    bot = TelegramBot()
    bot.run() 