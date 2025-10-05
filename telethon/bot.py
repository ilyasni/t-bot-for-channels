from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import User, Channel, Post
from datetime import datetime
import re
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

class TelegramBot:
    def __init__(self):
        self.application = Application.builder().token(BOT_TOKEN).build()
        self.setup_handlers()
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        self.application.add_handler(CommandHandler("start", self.start_command))
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

📋 Доступные команды:
/add_channel - Добавить канал для отслеживания
/my_channels - Показать ваши каналы
/remove_channel - Удалить канал
/help - Показать справку

Начните с добавления канала командой /add_channel @channel_name
                """
            else:
                welcome_text = f"""
🤖 С возвращением, {user.first_name}!

📋 Ваши команды:
/add_channel - Добавить канал для отслеживания
/my_channels - Показать ваши каналы
/remove_channel - Удалить канал
/help - Показать справку
                """
            
            await update.message.reply_text(welcome_text)
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
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
            
            # Проверяем, не добавлен ли уже канал
            existing_channel = db.query(Channel).filter(
                Channel.user_id == db_user.id,
                Channel.channel_username == channel_username
            ).first()
            
            if existing_channel:
                await update.message.reply_text(f"❌ Канал @{channel_username} уже добавлен в ваш список")
                return
            
            # Создаем новый канал
            new_channel = Channel(
                user_id=db_user.id,
                channel_username=channel_username
            )
            db.add(new_channel)
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
            
            channels = db.query(Channel).filter(Channel.user_id == db_user.id).all()
            
            if not channels:
                await update.message.reply_text(
                    "📭 У вас пока нет добавленных каналов.\n"
                    "Добавьте канал командой /add_channel @channel_name"
                )
                return
            
            text = "📋 Ваши каналы:\n\n"
            keyboard = []
            
            for i, channel in enumerate(channels):
                status = "✅ Активен" if channel.is_active else "❌ Неактивен"
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
        """Удаление канала по ID"""
        user = query.from_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await query.edit_message_text("❌ Пользователь не найден")
                return
            
            channel = db.query(Channel).filter(
                Channel.id == channel_id,
                Channel.user_id == db_user.id
            ).first()
            
            if not channel:
                await query.edit_message_text("❌ Канал не найден")
                return
            
            channel_username = channel.channel_username
            db.delete(channel)
            db.commit()
            
            await query.edit_message_text(f"✅ Канал @{channel_username} успешно удален!")
            
        except Exception as e:
            await query.edit_message_text(f"❌ Ошибка при удалении: {str(e)}")
        finally:
            db.close()
    
    async def handle_text(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка текстовых сообщений"""
        text = update.message.text
        
        # Если сообщение начинается с @, предлагаем добавить канал
        if text.startswith('@'):
            await update.message.reply_text(
                f"💡 Хотите добавить канал {text} для отслеживания?\n"
                f"Используйте команду: /add_channel {text}"
            )
        else:
            await update.message.reply_text(
                "💡 Используйте команды:\n"
                "/add_channel - Добавить канал\n"
                "/my_channels - Ваши каналы\n"
                "/help - Справка"
            )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по командам"""
        help_text = """
🤖 Telegram Channel Parser Bot - Справка

📋 Доступные команды:

/add_channel @channel_name - Добавить канал для отслеживания
Пример: /add_channel @example_channel

/my_channels - Показать список ваших каналов

/remove_channel - Удалить канал из списка

/help - Показать эту справку

💡 Как это работает:
1. Добавьте каналы командой /add_channel
2. Бот автоматически будет парсить новые посты
3. Посты сохраняются в базе данных
4. Вы можете анализировать их через n8n

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