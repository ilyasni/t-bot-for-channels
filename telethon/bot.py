from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler, 
    ContextTypes, filters, PicklePersistence
)
from sqlalchemy.orm import Session
from database import get_db, SessionLocal
from models import User, Channel, Post, user_group
from auth import create_auth_session, get_auth_url, check_user_auth_status, logout_user
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import re
import os
import time
import logging
import httpx
import asyncio
from dotenv import load_dotenv

# Импорты новых модулей
from bot_login_handlers_qr import get_login_conversation_handler, subscription_command
from bot_admin_handlers import (
    admin_invite_command, admin_users_command, admin_user_command,
    admin_grant_command, admin_stats_command, get_admin_callback_handler,
    admin_panel_command
)
from bot_debug_commands import (
    debug_test_phone_command, debug_check_sessions_command, debug_force_auth_command,
    debug_reset_auth_command, debug_delete_user_command
)
from voice_transcription_service import voice_transcription_service
from subscription_config import SUBSCRIPTION_TIERS

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

# DEBUG логи для отладки (управляется через переменную окружения)
# Установите DEBUG_LOGS=true в .env для включения детальных логов
if os.getenv('DEBUG_LOGS', 'false').lower() == 'true':
    logger.info("🐛 DEBUG логи включены (telegram.ext, ConversationHandler, httpx)")
    logging.getLogger('telegram.ext.ConversationHandler').setLevel(logging.DEBUG)
    logging.getLogger('telegram.ext').setLevel(logging.DEBUG)
    logging.getLogger('telethon').setLevel(logging.DEBUG)
    logging.getLogger('httpx').setLevel(logging.DEBUG)
else:
    # По умолчанию - только WARNING для библиотек
    logging.getLogger('telegram.ext').setLevel(logging.WARNING)
    logging.getLogger('telethon').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)

BOT_TOKEN = os.getenv("BOT_TOKEN")

class TelegramBot:
    def __init__(self):
        # Создаем persistence для сохранения состояний
        persistence = PicklePersistence(filepath='data/bot_persistence.pkl')
        
        # Создаем application с persistence
        self.application = (
            Application.builder()
            .token(BOT_TOKEN)
            .persistence(persistence)
            .build()
        )
        self.setup_handlers()
        # Словарь для хранения состояний пользователей
        self.user_states = {}
        # Таймаут для состояний (30 минут)
        self.state_timeout = 30 * 60  # 30 минут в секундах
        
        logger.info("✅ TelegramBot инициализирован с Persistence и поддержкой всех типов updates")
    
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
    
    async def _call_rag_service(self, endpoint: str, method: str = "POST", **kwargs) -> Optional[Dict]:
        """
        Универсальный метод для вызова RAG service
        
        Args:
            endpoint: Endpoint RAG service (например, "/rag/query")
            method: HTTP метод (GET, POST, PUT)
            **kwargs: Параметры запроса (для POST/PUT - json, для GET - params)
            
        Returns:
            Dict с ответом или None в случае ошибки
        """
        rag_url = os.getenv("RAG_SERVICE_URL", "http://rag-service:8020")
        rag_enabled = os.getenv("RAG_SERVICE_ENABLED", "true").lower() == "true"
        
        if not rag_enabled:
            logger.warning("RAG service отключен в конфигурации")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                method_upper = method.upper()
                
                if method_upper == "GET":
                    response = await client.get(
                        f"{rag_url}{endpoint}",
                        params=kwargs
                    )
                elif method_upper == "PUT":
                    response = await client.put(
                        f"{rag_url}{endpoint}",
                        json=kwargs
                    )
                else:  # POST
                    response = await client.post(
                        f"{rag_url}{endpoint}",
                        json=kwargs
                    )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"RAG service error {response.status_code}: {response.text[:200]}")
                    return None
                    
        except httpx.TimeoutException:
            logger.error(f"RAG service timeout: {endpoint}")
            return None
        except httpx.ConnectError:
            logger.error(f"RAG service недоступен: {endpoint}")
            return None
        except Exception as e:
            logger.error(f"RAG service error: {e}")
            return None
    
    def setup_handlers(self):
        """Настройка обработчиков команд"""
        logger.info("🔧 Настройка обработчиков команд...")
        
        # ✅ НОВОЕ: ConversationHandler для /login (должен быть первым!)
        self.application.add_handler(get_login_conversation_handler())
        logger.info("  ✅ ConversationHandler для /login зарегистрирован")
        
        # Основные команды
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
        
        # ✅ НОВОЕ: Команды для групп
        self.application.add_handler(CommandHandler("add_group", self.add_group_command))
        self.application.add_handler(CommandHandler("my_groups", self.my_groups_command))
        self.application.add_handler(CommandHandler("group_digest", self.group_digest_command))
        self.application.add_handler(CommandHandler("group_settings", self.group_settings_command))
        logger.info("  ✅ Команды групп зарегистрированы")
        
        # ✅ НОВОЕ: Команда для просмотра подписки
        self.application.add_handler(CommandHandler("subscription", subscription_command))
        
        # ✅ НОВОЕ: Админ команды
        self.application.add_handler(CommandHandler("admin", admin_panel_command))  # Mini App панель
        self.application.add_handler(CommandHandler("admin_invite", admin_invite_command))
        self.application.add_handler(CommandHandler("admin_users", admin_users_command))
        self.application.add_handler(CommandHandler("admin_user", admin_user_command))
        self.application.add_handler(CommandHandler("admin_grant", admin_grant_command))
        self.application.add_handler(CommandHandler("admin_stats", admin_stats_command))
        
        # ✅ НОВОЕ: Debug команды
        self.application.add_handler(CommandHandler("debug_status", self.debug_status_command))
        self.application.add_handler(CommandHandler("debug_unblock", self.debug_unblock_command))
        self.application.add_handler(CommandHandler("debug_reset", self.debug_reset_command))
        self.application.add_handler(CommandHandler("debug_test_phone", debug_test_phone_command))
        self.application.add_handler(CommandHandler("debug_check_sessions", debug_check_sessions_command))
        self.application.add_handler(CommandHandler("debug_force_auth", debug_force_auth_command))
        self.application.add_handler(CommandHandler("debug_reset_auth", debug_reset_auth_command))
        self.application.add_handler(CommandHandler("debug_delete_user", debug_delete_user_command))
        
        # ✅ НОВОЕ: Debug команды для групп
        from bot_group_debug import debug_group_digest_command, debug_n8n_test_command
        self.application.add_handler(CommandHandler("debug_group_digest", debug_group_digest_command))
        self.application.add_handler(CommandHandler("debug_n8n", debug_n8n_test_command))
        logger.info("  ✅ Админ и Debug команды зарегистрированы")
        
        # RAG команды
        self.application.add_handler(CommandHandler("ask", self.ask_command))
        self.application.add_handler(CommandHandler("search", self.search_command))
        self.application.add_handler(CommandHandler("recommend", self.recommend_command))
        self.application.add_handler(CommandHandler("digest", self.digest_command))
        
        # Callback handlers
        self.application.add_handler(get_admin_callback_handler())  # ✅ НОВОЕ: Админ callbacks
        self.application.add_handler(CallbackQueryHandler(self.button_callback))
        
        # ✅ НОВОЕ: Голосовые сообщения для /ask и /search (Premium)
        self.application.add_handler(MessageHandler(
            filters.VOICE & ~filters.COMMAND,
            self.handle_voice_command
        ))
        logger.info("  ✅ Handler голосовых сообщений зарегистрирован")
        
        # Команда сброса состояния голосовых команд
        self.application.add_handler(CommandHandler("reset", self.reset_command))
        
        # Текстовые сообщения (должен быть последним!)
        self.application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_text))
        
        logger.info("✅ Все обработчики зарегистрированы (включая голосовые команды и Persistence)")
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /start"""
        # Сбрасываем last_command чтобы голосовые использовали AI классификатор
        context.user_data.pop('last_command', None)
        
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
🤖 **Добро пожаловать в Telegram Channel Parser Bot!**

Я помогу вам отслеживать посты из ваших любимых каналов и искать информацию с помощью AI.

🎫 **Для начала работы нужен инвайт код**

Обратитесь к администратору для получения инвайт кода, затем:

📱 **Авторизация (QR код - БЕЗ SMS!):**
/login INVITE_CODE

**Пример:**
`/login ABC123XYZ`

✨ **Процесс авторизации:**
1️⃣ Отправьте /login с вашим кодом
2️⃣ Нажмите кнопку "🔐 Открыть QR авторизацию"
3️⃣ Отсканируйте QR код или используйте ссылку
4️⃣ Подтвердите в Telegram
5️⃣ Готово! ✅

📋 **После авторизации доступны:**
• /add_channel - Добавить канал для парсинга
• /my_channels - Список ваших каналов
• /ask - Поиск ответа в постах (RAG)
• /subscription - Ваша подписка и лимиты
• /help - Полная справка

⚡ **Особенности:**
• Авторизация за 30 секунд (БЕЗ SMS кодов!)
• Автоматический парсинг каналов каждые 30 минут
• AI поиск по постам
• Персональные дайджесты

🤖 RAG & AI команды:
• /ask - Поиск ответа в постах
• /search - Гибридный поиск
• /recommend - Персональные рекомендации
• /digest - AI-дайджесты

/help - Полная справка
                """
            else:
                # Определяем роль пользователя
                is_admin = db_user.is_admin()
                role_badge = "👑 Администратор" if is_admin else "👤 Пользователь"
                
                if db_user.is_authenticated:
                    # Базовые команды для всех
                    base_commands = f"""
📋 **Управление каналами:**
/add_channel - Добавить канал
/my_channels - Ваши каналы ({len(db_user.channels)}/{db_user.max_channels})

🤖 **RAG & AI:**
/ask <вопрос> - Поиск ответа в постах
/search <запрос> - Гибридный поиск
/recommend - Персональные рекомендации
/digest - AI-дайджесты

💎 **Подписка:**
/subscription - Ваша подписка ({db_user.subscription_type})
"""
                    
                    # Админские команды
                    admin_commands = """
👑 **Команды администратора:**
/admin - Открыть админ панель (управление пользователями)
/admin_invite - Создать инвайт код
/admin_stats - Статистика системы
/admin_users - Список пользователей
/admin_grant - Выдать подписку напрямую
""" if is_admin else ""
                    
                    welcome_text = f"""
🤖 **С возвращением, {user.first_name}!** {role_badge}

✅ Статус: Авторизован
💎 Подписка: {db_user.subscription_type}

{base_commands}
{admin_commands}
/help - Полная справка
                    """
                else:
                    welcome_text = f"""
🤖 **С возвращением, {user.first_name}!** {role_badge}

⚠️ **Для использования функций необходимо авторизоваться:**

📱 **Авторизация через QR код (рекомендуется):**
/login INVITE_CODE

**Альтернативный способ (свои API ключи):**
/auth - Аутентификация через веб-форму
/auth_status - Проверить статус

💡 Инвайт код можно получить у администратора
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
            
            # Выходим из системы (обновляет user объект)
            await logout_user(db_user)
            
            # ВАЖНО: Сохраняем изменения в БД
            db.commit()
            
            # Очищаем состояние пользователя
            if user.id in self.user_states:
                del self.user_states[user.id]
            
            await update.message.reply_text(
                "✅ Вы успешно вышли из системы.\n\n"
                "Для повторного использования:\n"
                "• `/login INVITE_CODE` - QR авторизация\n"
                "• `/auth` - Веб-форма (свои API ключи)"
            )
            
        except Exception as e:
            db.rollback()
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
            logger.error(f"Logout error: {e}", exc_info=True)
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
            
            # ✅ НОВОЕ: Проверяем лимиты подписки
            if not db_user.can_add_channel():
                tier_name = db_user.subscription_type
                from subscription_config import get_subscription_info
                tier = get_subscription_info(tier_name)
                
                await update.message.reply_text(
                    f"❌ Достигнут лимит каналов для подписки **{tier['name']}**: {db_user.max_channels}\n\n"
                    f"💎 Для увеличения лимита обратитесь к администратору\n"
                    f"Текущая подписка: /subscription",
                    parse_mode='Markdown'
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
        # Сбрасываем last_command чтобы голосовые использовали AI классификатор
        context.user_data.pop('last_command', None)
        
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
    
    async def add_group_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Добавить Telegram группу для мониторинга"""
        user = update.effective_user
        args = context.args
        
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /login")
                return
            
            # Проверка аутентификации
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Вы не аутентифицированы\n"
                    "Используйте /login для QR-авторизации"
                )
                return
            
            # Получаем клиент
            from shared_auth_manager import shared_auth_manager
            client = await shared_auth_manager.get_user_client(user.id)
            
            if not client:
                await update.message.reply_text("❌ Не удалось подключиться к Telegram")
                return
            
            # Если нет аргументов - показываем список доступных групп
            if not args:
                await update.message.reply_text("⏳ Получаю список ваших групп...")
                
                # Получаем все диалоги пользователя
                from telethon.tl.types import Chat, Channel as TelegramChannel
                
                user_groups = []
                async for dialog in client.iter_dialogs(limit=100):
                    entity = dialog.entity
                    # Только группы и супергруппы (не каналы, не личные чаты)
                    if isinstance(entity, (Chat, TelegramChannel)):
                        # Проверяем что это группа (не канал)
                        if isinstance(entity, TelegramChannel) and not entity.broadcast:
                            # Супергруппа
                            user_groups.append({
                                'id': entity.id,
                                'title': entity.title,
                                'username': getattr(entity, 'username', None)
                            })
                        elif isinstance(entity, Chat):
                            # Обычная группа
                            user_groups.append({
                                'id': entity.id,
                                'title': entity.title,
                                'username': None
                            })
                
                if not user_groups:
                    await update.message.reply_text(
                        "📭 Вы не состоите ни в одной группе\n\n"
                        "Добавьте группу по ID: `/add_group -1001234567890`"
                    )
                    return
                
                # Показываем список
                text = f"👥 **Ваши группы** ({len(user_groups)}):\n\n"
                text += "Для добавления используйте ID группы:\n\n"
                
                for i, g in enumerate(user_groups[:20], 1):  # Показываем до 20
                    # Экранируем спецсимволы Markdown в названии
                    safe_title = g['title'].replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                    text += f"{i}. **{safe_title}**\n"
                    text += f"   `/add_group {g['id']}`\n\n"
                
                if len(user_groups) > 20:
                    text += f"... и еще {len(user_groups) - 20} групп\n\n"
                
                text += "💡 Скопируйте команду и отправьте"
                
                await update.message.reply_text(text, parse_mode='Markdown')
                return
            
            # Проверка лимита групп
            if not db_user.can_add_group():
                from subscription_config import get_subscription_info
                current_tier = get_subscription_info(db_user.subscription_type)
                max_groups = current_tier.get('max_groups', 0)
                
                await update.message.reply_text(
                    f"❌ Достигнут лимит групп ({max_groups})\n\n"
                    f"Текущая подписка: {current_tier['name']}\n"
                    f"Для увеличения лимита обратитесь к администратору"
                )
                return
            
            # Парсим input (ссылка или ID)
            group_input = args[0]
            group_id = None
            group_entity = None
            
            # Если это число - это group_id
            if group_input.lstrip('-').isdigit():
                group_id = int(group_input)
                
                await update.message.reply_text("⏳ Проверяю доступ к группе...")
                
                # Получаем entity
                try:
                    group_entity = await client.get_entity(group_id)
                except Exception as e:
                    # Возможно группа приватная - ищем в диалогах
                    logger.info(f"Не удалось получить entity по ID {group_id}, ищем в диалогах...")
                    
                    from telethon.tl.types import Chat, Channel as TelegramChannel
                    async for dialog in client.iter_dialogs(limit=200):
                        if dialog.entity.id == group_id:
                            group_entity = dialog.entity
                            break
                    
                    if not group_entity:
                        await update.message.reply_text(
                            f"❌ Группа не найдена\n\n"
                            f"Возможные причины:\n"
                            f"• Вы не состоите в этой группе\n"
                            f"• ID группы неверный\n\n"
                            f"💡 Используйте `/add_group` без параметров чтобы увидеть список ваших групп"
                        )
                        return
            
            # Если ссылка - обрабатываем
            elif 't.me/' in group_input or 'telegram.me/' in group_input:
                parts = group_input.rstrip('/').split('/')
                last_part = parts[-1]
                
                # Проверяем приватная ли группа (начинается с +)
                if last_part.startswith('+'):
                    # Приватная группа - ищем в диалогах пользователя
                    await update.message.reply_text(
                        "🔍 Приватная группа обнаружена\n"
                        "Ищу в ваших диалогах..."
                    )
                    
                    # Invite hash для поиска
                    invite_hash = last_part[1:]  # Убираем +
                    
                    from telethon.tl.types import Chat, Channel as TelegramChannel
                    
                    # Получаем все группы и ищем
                    found_groups = []
                    async for dialog in client.iter_dialogs(limit=200):
                        entity = dialog.entity
                        if isinstance(entity, (Chat, TelegramChannel)):
                            # Проверяем что это группа (не канал)
                            if isinstance(entity, TelegramChannel) and not entity.broadcast:
                                found_groups.append(entity)
                            elif isinstance(entity, Chat):
                                found_groups.append(entity)
                    
                    if not found_groups:
                        await update.message.reply_text(
                            "📭 Вы не состоите ни в одной группе\n\n"
                            "💡 Сначала вступите в группу через invite link в Telegram,\n"
                            "затем используйте `/add_group` для выбора из списка"
                        )
                        return
                    
                    # Показываем список для выбора
                    text = f"👥 **Найдено групп:** {len(found_groups)}\n\n"
                    text += "Выберите нужную группу:\n\n"
                    
                    for i, g in enumerate(found_groups[:20], 1):
                        # Экранируем спецсимволы Markdown
                        safe_title = g.title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                        text += f"{i}. **{safe_title}**\n"
                        text += f"   `/add_group {g.id}`\n\n"
                    
                    if len(found_groups) > 20:
                        text += f"... и еще {len(found_groups) - 20} групп\n\n"
                    
                    text += "💡 Найдите нужную группу и скопируйте команду"
                    
                    await update.message.reply_text(text, parse_mode='Markdown')
                    return
                
                elif last_part.lstrip('-').isdigit():
                    # ID в ссылке
                    group_id = int(last_part)
                    group_entity = await client.get_entity(group_id)
                else:
                    # Публичный username
                    await update.message.reply_text("⏳ Получение информации о группе...")
                    try:
                        group_entity = await client.get_entity(last_part)
                        group_id = group_entity.id
                    except Exception as e:
                        await update.message.reply_text(
                            f"❌ Не удалось найти группу: {str(e)}\n\n"
                            f"💡 Для приватных групп используйте `/add_group` без параметров"
                        )
                        return
            else:
                await update.message.reply_text("❌ Неверный формат ссылки или ID")
                return
            
            # Проверяем что получили entity
            if not group_entity and group_id:
                # Пытаемся получить entity по ID
                try:
                    group_entity = await client.get_entity(group_id)
                except Exception as e:
                    await update.message.reply_text(
                        f"❌ Не удалось получить информацию о группе\n\n"
                        f"Используйте `/add_group` без параметров для выбора из списка"
                    )
                    return
            
            if not group_entity:
                await update.message.reply_text("❌ Не удалось получить информацию о группе")
                return
            
            # Извлекаем данные
            group_title = getattr(group_entity, 'title', 'Unknown')
            group_username = getattr(group_entity, 'username', None)
            final_group_id = group_entity.id
            
            # Проверяем что это группа
            from telethon.tl.types import Chat, Channel as TelegramChannel
            if isinstance(group_entity, TelegramChannel) and group_entity.broadcast:
                await update.message.reply_text(
                    "❌ Это канал, не группа\n"
                    "Используйте /add_channel для каналов"
                )
                return
            
            # Создаем или получаем группу в БД
            from models import Group
            group = Group.get_or_create(
                db, 
                group_id=final_group_id,
                group_title=group_title,
                group_username=group_username
            )
            
            # Проверяем не добавлена ли уже
            if db_user in group.users:
                safe_title = group_title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                await update.message.reply_text(
                    f"ℹ️ Группа **{safe_title}** уже добавлена\n\n"
                    f"Используйте /my_groups для просмотра",
                    parse_mode='Markdown'
                )
                return
            
            # Добавляем пользователя к группе
            group.add_user(db, db_user, is_active=True, mentions_enabled=True)
            db.commit()
            
            # Запускаем мониторинг для этого пользователя
            from group_monitor_service import group_monitor_service
            await group_monitor_service.start_monitoring(user.id)
            
            # Экранируем спецсимволы Markdown
            safe_title = group_title.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
            
            await update.message.reply_text(
                f"✅ Группа **{safe_title}** добавлена!\n\n"
                f"🔔 Мониторинг упоминаний активирован\n"
                f"📊 Используйте /group_digest для получения резюме разговоров\n\n"
                f"Настройки: /group_settings",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка add_group: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ Ошибка: {str(e)}\n\n"
                "💡 Для приватных групп:\n"
                "1. Используйте `/add_group` без параметров\n"
                "2. Выберите группу из списка\n"
                "3. Скопируйте команду с ID"
            )
        finally:
            db.close()
    
    async def my_groups_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать список отслеживаемых групп"""
        # Сбрасываем last_command чтобы голосовые использовали AI классификатор
        context.user_data.pop('last_command', None)
        
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            # Получаем группы пользователя
            from models import Group
            groups = db.query(Group).join(
                user_group,
                Group.id == user_group.c.group_id
            ).filter(
                user_group.c.user_id == db_user.id
            ).all()
            
            if not groups:
                await update.message.reply_text(
                    "📭 У вас нет отслеживаемых групп\n\n"
                    "Добавьте группу: /add_group <ссылка>"
                )
                return
            
            # Формируем список
            from subscription_config import get_subscription_info
            tier = get_subscription_info(db_user.subscription_type)
            max_groups = tier.get('max_groups', 0)
            
            text = f"📊 **Ваши группы** ({len(groups)}/{max_groups}):\n\n"
            
            for i, group in enumerate(groups, 1):
                # Получаем настройки для группы
                subscription = db.execute(
                    user_group.select().where(
                        (user_group.c.user_id == db_user.id) &
                        (user_group.c.group_id == group.id)
                    )
                ).fetchone()
                
                status = "🟢" if subscription.is_active else "🔴"
                mentions = "🔔" if subscription.mentions_enabled else "🔕"
                
                # Экранируем спецсимволы Markdown в названии
                display_name = group.group_title or str(group.group_id)
                safe_name = display_name.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                
                text += f"{i}. {status} **{safe_name}**\n"
                text += f"   {mentions} Упоминания | ID: `{group.group_id}`\n"
            
            text += f"\n💡 Используйте /group_settings для настройки уведомлений"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def group_digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сгенерировать дайджест разговора в группе"""
        # Сбрасываем last_command чтобы голосовые использовали AI классификатор
        context.user_data.pop('last_command', None)
        
        user = update.effective_user
        args = context.args
        
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            # Проверка аутентификации
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Вы не аутентифицированы\n"
                    "Используйте /login для авторизации"
                )
                return
            
            # Получаем группы пользователя
            from models import Group
            groups = db.query(Group).join(
                user_group,
                Group.id == user_group.c.group_id
            ).filter(
                user_group.c.user_id == db_user.id,
                user_group.c.is_active == True
            ).all()
            
            if not groups:
                await update.message.reply_text(
                    "📭 У вас нет активных групп\n\n"
                    "Добавьте группу: /add_group <ссылка>"
                )
                return
            
            # Парсим аргументы
            hours = 24
            target_group = None
            
            if len(args) == 1:
                # /group_digest 24
                if args[0].isdigit():
                    hours = int(args[0])
                else:
                    # /group_digest group_name - пока не поддерживаем
                    await update.message.reply_text(
                        "💡 Укажите количество часов: `/group_digest 24`",
                        parse_mode='Markdown'
                    )
                    return
            elif len(args) == 2:
                # /group_digest group_name 24 - будущая функция
                pass
            
            # Если у пользователя одна группа - используем её
            if len(groups) == 1:
                target_group = groups[0]
            else:
                # Если несколько групп - показываем список для выбора
                text = "📊 Выберите группу для дайджеста:\n\n"
                for i, group in enumerate(groups, 1):
                    display = group.group_title or str(group.group_id)
                    safe_display = display.replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
                    text += f"{i}. {safe_display}\n"
                text += f"\nИспользуйте: `/group_digest <номер> <часы>`"
                
                await update.message.reply_text(text, parse_mode='Markdown')
                return
            
            # Генерируем дайджест
            safe_group_title = (target_group.group_title or str(target_group.group_id)).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace('`', '\\`')
            await update.message.reply_text(
                f"⏳ Генерация дайджеста для группы **{safe_group_title}**...\n"
                f"Период: {hours} часов\n\n"
                "Это может занять 20-30 секунд ⏰",
                parse_mode='Markdown'
            )
            
            # Получаем клиент
            from shared_auth_manager import shared_auth_manager
            client = await shared_auth_manager.get_user_client(user.id)
            
            if not client:
                await update.message.reply_text("❌ Не удалось подключиться к Telegram")
                return
            
            # Получаем сообщения из группы
            from datetime import timedelta
            date_from = datetime.now(timezone.utc) - timedelta(hours=hours)
            
            logger.info(f"📨 Получение сообщений из группы {target_group.group_id}")
            logger.info(f"   Период: с {date_from} до {datetime.now(timezone.utc)}")
            logger.info(f"   Часов: {hours}")
            
            messages = []
            total_fetched = 0
            async for msg in client.iter_messages(
                target_group.group_id,
                limit=200,  # Лимит сообщений
                offset_date=datetime.now(timezone.utc)
            ):
                total_fetched += 1
                
                # Конвертируем msg.date в timezone-aware если нужно
                msg_date = msg.date
                if msg_date.tzinfo is None:
                    msg_date = msg_date.replace(tzinfo=timezone.utc)
                else:
                    msg_date = msg_date.astimezone(timezone.utc)
                
                if msg_date < date_from:
                    break
                    
                if msg.text:  # Только текстовые сообщения
                    messages.append(msg)
            
            logger.info(f"📊 Получено сообщений: {total_fetched} всего, {len(messages)} с текстом")
            
            if not messages:
                await update.message.reply_text(
                    f"📭 За последние {hours} часов в группе нет текстовых сообщений\n\n"
                    f"Проверено сообщений: {total_fetched}"
                )
                return
            
            # Генерируем дайджест через n8n workflow
            from group_digest_generator import group_digest_generator
            
            try:
                digest = await group_digest_generator.generate_digest(
                    user_id=db_user.id,
                    group_id=target_group.id,
                    messages=messages,
                    hours=hours
                )
                
                # Форматируем для Telegram
                formatted = group_digest_generator.format_digest_for_telegram(
                    digest=digest,
                    group_title=target_group.group_title or str(target_group.group_id)
                )
                
                # Отправляем результат
                await update.message.reply_text(formatted, parse_mode='Markdown')
                
            except Exception as e:
                logger.error(f"❌ Ошибка генерации дайджеста: {e}")
                await update.message.reply_text(
                    f"❌ Ошибка генерации дайджеста: {str(e)}\n\n"
                    "Проверьте:\n"
                    "• n8n workflows импортированы и активны\n"
                    "• gpt2giga-proxy доступен"
                )
                
        finally:
            db.close()
    
    async def group_settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Настройки уведомлений для групп"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            # Получаем или создаем настройки
            from models import GroupSettings
            settings = db.query(GroupSettings).filter(
                GroupSettings.user_id == db_user.id
            ).first()
            
            if not settings:
                # Создаем настройки по умолчанию
                settings = GroupSettings(
                    user_id=db_user.id,
                    mentions_enabled=True,
                    mention_context_messages=5,
                    digest_default_hours=24,
                    digest_max_messages=200
                )
                db.add(settings)
                db.commit()
            
            # Показываем текущие настройки
            text = "⚙️ **Настройки групп:**\n\n"
            text += f"🔔 Уведомления об упоминаниях: {'✅ Включены' if settings.mentions_enabled else '❌ Выключены'}\n"
            text += f"📨 Контекст упоминаний: {settings.mention_context_messages} сообщений\n"
            text += f"⏰ Период дайджестов по умолчанию: {settings.digest_default_hours} часов\n"
            text += f"📊 Макс. сообщений для анализа: {settings.digest_max_messages}\n\n"
            text += "💡 Для изменения настроек используйте команды:\n"
            text += "• `/group_settings mentions on|off` - вкл/выкл уведомления\n"
            text += "• `/group_settings context <N>` - количество сообщений контекста\n"
            text += "• `/group_settings digest_hours <N>` - период по умолчанию"
            
            # Обработка аргументов для изменения настроек
            args = context.args
            if args:
                setting = args[0].lower()
                
                if setting == "mentions" and len(args) > 1:
                    value = args[1].lower() in ['on', 'true', '1', 'yes']
                    settings.mentions_enabled = value
                    db.commit()
                    text = f"✅ Уведомления об упоминаниях: {'включены' if value else 'выключены'}"
                    
                elif setting == "context" and len(args) > 1 and args[1].isdigit():
                    value = int(args[1])
                    if 1 <= value <= 20:
                        settings.mention_context_messages = value
                        db.commit()
                        text = f"✅ Контекст установлен: {value} сообщений"
                    else:
                        text = "❌ Контекст должен быть от 1 до 20 сообщений"
                
                elif setting == "digest_hours" and len(args) > 1 and args[1].isdigit():
                    value = int(args[1])
                    if 1 <= value <= 168:  # Максимум неделя
                        settings.digest_default_hours = value
                        db.commit()
                        text = f"✅ Период дайджестов по умолчанию: {value} часов"
                    else:
                        text = "❌ Период должен быть от 1 до 168 часов (неделя)"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка нажатий на кнопки"""
        query = update.callback_query
        user = query.from_user
        
        logger.info(f"🔘 Получен callback от пользователя {user.id}: {query.data}")
        
        await query.answer()
        
        if query.data.startswith("remove_"):
            logger.info(f"  → Обработка remove_channel: {query.data}")
            channel_id = int(query.data.split("_")[1])
            await self.remove_channel_by_id(query, channel_id)
        elif query.data.startswith("voice_ask:"):
            logger.info(f"  → Обработка voice_ask callback")
            await self.handle_voice_ask_callback(query, context)
        elif query.data.startswith("voice_search:"):
            logger.info(f"  → Обработка voice_search callback")
            await self.handle_voice_search_callback(query, context)
        elif query.data.startswith("digest_"):
            logger.info(f"  → Обработка digest callback: {query.data}")
            await self.handle_digest_callback(query, context)
        elif query.data.startswith("search_"):
            logger.info(f"  → Обработка search callback: {query.data}")
            await self.handle_search_callback(query, context)
        else:
            logger.warning(f"  → Неизвестный callback: {query.data}")
    
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
        
        # Обработка кнопок режима голосовых команд
        if text in ["🤖 AI режим", "💡 Ask режим", "🔍 Search режим"]:
            if text == "🤖 AI режим":
                context.user_data['voice_mode'] = 'ai'
                context.user_data.pop('last_command', None)
                context.user_data.pop('last_command_time', None)
                await update.message.reply_text(
                    "✅ Режим: 🤖 **AI классификатор**\n\n"
                    "Голосовые сообщения будут автоматически определяться как /ask или /search",
                    reply_markup=self.get_voice_mode_keyboard()
                )
            elif text == "💡 Ask режим":
                context.user_data['voice_mode'] = 'ask'
                context.user_data['last_command'] = '/ask'
                context.user_data['last_command_time'] = datetime.now(timezone.utc)
                await update.message.reply_text(
                    "✅ Режим: 💡 **Ask**\n\n"
                    "Все голосовые сообщения будут выполняться как /ask",
                    reply_markup=self.get_voice_mode_keyboard()
                )
            elif text == "🔍 Search режим":
                context.user_data['voice_mode'] = 'search'
                context.user_data['last_command'] = '/search'
                context.user_data['last_command_time'] = datetime.now(timezone.utc)
                await update.message.reply_text(
                    "✅ Режим: 🔍 **Search**\n\n"
                    "Все голосовые сообщения будут выполняться как /search",
                    reply_markup=self.get_voice_mode_keyboard()
                )
            return
        
        # Очищаем устаревшие состояния
        self._cleanup_expired_states()
        
        # Проверяем, есть ли активное состояние для пользователя
        if user.id in self.user_states:
            state = self.user_states[user.id]
            
            # Обработка ввода тем для дайджеста
            if state.get('action') == 'digest_topics_input':
                # Парсим темы
                topics = [topic.strip() for topic in text.split(',') if topic.strip()]
                
                if not topics:
                    await update.message.reply_text("❌ Темы не распознаны. Попробуйте еще раз.")
                    return
                
                db = SessionLocal()
                try:
                    db_user = db.query(User).filter(User.telegram_id == user.id).first()
                    if not db_user:
                        await update.message.reply_text("❌ Пользователь не найден")
                        return
                    
                    # Получаем текущие настройки
                    result = await self._call_rag_service(
                        f"/rag/digest/settings/{db_user.id}",
                        method="GET"
                    )
                    
                    if result:
                        settings = result  # API возвращает данные напрямую
                        
                        # Обновляем с новыми темами
                        update_result = await self._call_rag_service(
                            f"/rag/digest/settings/{db_user.id}",
                            method="PUT",
                            enabled=settings.get("enabled", True),
                            frequency=settings.get("frequency", "daily"),
                            time=settings.get("time", "09:00"),
                            ai_summarize=settings.get("ai_summarize", False),
                            summary_style=settings.get("summary_style", "concise"),
                            preferred_topics=topics
                        )
                        
                        if update_result:
                            await update.message.reply_text(
                                f"✅ Темы сохранены: {', '.join(topics)}\n\n"
                                "Используйте /digest для просмотра всех настроек."
                            )
                        else:
                            await update.message.reply_text("❌ Ошибка сохранения тем")
                    
                    # Очищаем состояние
                    del self.user_states[user.id]
                    
                finally:
                    db.close()
                
                return
        
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
                "/ask - Поиск ответа в постах (RAG)\n"
                "/search - Гибридный поиск\n"
                "/help - Справка\n\n"
                "⚠️ Для аутентификации используйте веб-форму из команды /auth"
            )
    
    async def ask_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /ask - RAG-поиск ответа в постах"""
        user = update.effective_user
        args = context.args
        
        # Сохраняем команду для голосовых сообщений (с таймстампом)
        context.user_data['last_command'] = '/ask'
        context.user_data['last_command_time'] = datetime.now(timezone.utc)
        
        if not args:
            await update.message.reply_text(
                "💡 **Использование:** `/ask <ваш вопрос>`\n\n"
                "**Примеры:**\n"
                "• `/ask Что писали про нейросети на этой неделе?`\n"
                "• `/ask Какие новости про Tesla?`\n"
                "• `/ask Расскажи о блокчейн технологиях`\n\n"
                "🎤 **Голосовой ввод (Premium/Enterprise):**\n"
                "1️⃣ Отправьте эту команду `/ask`\n"
                "2️⃣ Отправьте голосовое с вопросом\n"
                "   → Автоматически выполнится поиск!\n\n"
                "💡 **Альтернатива:**\n"
                "• Отправьте голосовое БЕЗ команды\n"
                "• Выберите кнопку \"💡 /ask\"",
                parse_mode='Markdown'
            )
            return
        
        query_text = " ".join(args)
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Для использования RAG-поиска необходимо пройти аутентификацию.\n"
                    "Используйте команду /auth"
                )
                return
            
            # Проверяем наличие постов
            posts_count = db.query(Post).filter(Post.user_id == db_user.id).count()
            if posts_count == 0:
                await update.message.reply_text(
                    "📭 У вас пока нет постов в базе данных.\n\n"
                    "💡 Добавьте каналы командой `/add_channel @channel_name`\n"
                    "Парсинг начнется автоматически через несколько минут.",
                    parse_mode='Markdown'
                )
                return
            
            # Отправляем "печатает..." индикатор
            await update.message.chat.send_action(action="typing")
            
            # Вызов RAG service
            result = await self._call_rag_service(
                "/rag/query",
                user_id=db_user.id,
                query=query_text,
                top_k=5,
                min_score=0.7
            )
            
            if not result:
                await update.message.reply_text(
                    "❌ RAG-сервис временно недоступен.\n\n"
                    "💡 Попробуйте позже или обратитесь к администратору."
                )
                return
            
            # Проверяем ответ
            if "error" in result:
                await update.message.reply_text(f"❌ Ошибка: {result['error']}")
                return
            
            answer = result.get("answer", "Не удалось сгенерировать ответ")
            sources = result.get("sources", [])
            
            # Форматируем ответ
            response_text = f"💡 **Ответ:**\n\n{answer}\n\n"
            
            if sources:
                response_text += "📚 **Источники:**\n"
                for i, source in enumerate(sources[:5], 1):
                    channel = source.get("channel", "Неизвестный канал")
                    url = source.get("url", "#")
                    score = source.get("score", 0) * 100
                    response_text += f"{i}. [{channel}]({url}) (релевантность: {score:.0f}%)\n"
            else:
                response_text += "\n💡 Источники не найдены. Попробуйте изменить запрос."
            
            await update.message.reply_text(
                response_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка команды /ask: {e}")
            await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
        finally:
            db.close()
    
    async def recommend_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /recommend - персональные рекомендации"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Для получения рекомендаций необходимо пройти аутентификацию.\n"
                    "Используйте команду /auth"
                )
                return
            
            # Отправляем "печатает..." индикатор
            await update.message.chat.send_action(action="typing")
            
            # Вызов RAG service
            result = await self._call_rag_service(
                f"/rag/recommend/{db_user.id}",
                method="GET",
                limit=5
            )
            
            if not result:
                await update.message.reply_text(
                    "❌ Сервис рекомендаций временно недоступен.\n\n"
                    "💡 Попробуйте позже."
                )
                return
            
            recommendations = result.get("recommendations", [])
            
            if not recommendations:
                await update.message.reply_text(
                    "💡 **Недостаточно данных для рекомендаций**\n\n"
                    "Используйте команду `/ask` для поиска информации.\n"
                    "Система проанализирует ваши интересы и начнет давать персональные рекомендации.\n\n"
                    "**Пример:**\n"
                    "• `/ask Что нового в AI?`\n"
                    "• `/ask Расскажи про блокчейн`",
                    parse_mode='Markdown'
                )
                return
            
            # Форматируем ответ
            response_text = "🎯 **Рекомендации для вас:**\n\n"
            
            for i, rec in enumerate(recommendations, 1):
                channel = rec.get("channel", "Неизвестный канал")
                title = rec.get("title", "Без названия")
                url = rec.get("url", "#")
                score = rec.get("score", 0) * 100
                
                # Обрезаем длинный title
                if len(title) > 100:
                    title = title[:97] + "..."
                
                response_text += f"{i}. **[{channel}]({url})**\n"
                response_text += f"   {title}\n"
                response_text += f"   Релевантность: {score:.0f}%\n\n"
            
            response_text += "💡 Рекомендации основаны на анализе ваших интересов"
            
            await update.message.reply_text(
                response_text,
                parse_mode='Markdown',
                disable_web_page_preview=True
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка команды /recommend: {e}")
            await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
        finally:
            db.close()
    
    async def search_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /search - гибридный поиск (посты + веб)"""
        user = update.effective_user
        args = context.args
        
        # Сохраняем команду для голосовых сообщений (с таймстампом)
        context.user_data['last_command'] = '/search'
        context.user_data['last_command_time'] = datetime.now(timezone.utc)
        
        if not args:
            await update.message.reply_text(
                "🔍 **Использование:** `/search <запрос>`\n\n"
                "**Примеры:**\n"
                "• `/search квантовые компьютеры`\n"
                "• `/search искусственный интеллект`\n"
                "• `/search блокчейн технологии`\n\n"
                "Поиск осуществляется в ваших постах + в интернете через Searxng\n\n"
                "🎤 **Голосовой ввод (Premium/Enterprise):**\n"
                "1️⃣ Отправьте эту команду `/search`\n"
                "2️⃣ Отправьте голосовое с запросом\n"
                "   → Автоматически выполнится поиск!\n\n"
                "💡 **Альтернатива:**\n"
                "• Отправьте голосовое БЕЗ команды\n"
                "• Выберите кнопку \"🔍 /search\"",
                parse_mode='Markdown'
            )
            return
        
        query_text = " ".join(args)
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Для поиска необходимо пройти аутентификацию.\n"
                    "Используйте команду /auth"
                )
                return
            
            # Отправляем "печатает..." индикатор
            await update.message.chat.send_action(action="typing")
            
            # Вызов RAG service (hybrid search)
            result = await self._call_rag_service(
                "/rag/hybrid_search",
                user_id=db_user.id,
                query=query_text,
                include_web=True,
                include_posts=True,
                limit=5
            )
            
            if not result:
                await update.message.reply_text(
                    "❌ Сервис поиска временно недоступен.\n\n"
                    "💡 Попробуйте позже."
                )
                return
            
            posts = result.get("posts", [])
            web_results = result.get("web", [])
            
            # Сохраняем запрос в состоянии пользователя для callback
            self.user_states[user.id] = {
                'action': 'search_query',
                'query': query_text,
                'timestamp': time.time()
            }
            
            # Форматируем ответ
            response_text = f"🔍 **Результаты поиска:** {query_text}\n\n"
            
            if posts:
                response_text += f"📱 **Ваши посты ({len(posts)}):**\n"
                for i, post in enumerate(posts[:3], 1):
                    channel = post.get("channel", "Неизвестный канал")
                    snippet = post.get("snippet", post.get("text", ""))[:100]
                    url = post.get("url", "#")
                    response_text += f"{i}. [{channel}]({url})\n   {snippet}...\n\n"
            else:
                response_text += "📱 **Ваши посты:** Не найдено\n\n"
            
            if web_results:
                response_text += f"🌐 **Интернет ({len(web_results)}):**\n"
                for i, web in enumerate(web_results[:3], 1):
                    title = web.get("title", "Без названия")
                    url = web.get("url", "#")
                    response_text += f"{i}. [{title}]({url})\n\n"
            else:
                response_text += "🌐 **Интернет:** Не найдено\n\n"
            
            # Добавляем кнопки фильтрации (без текста запроса в callback_data)
            keyboard = [
                [
                    InlineKeyboardButton("📱 Только посты", callback_data="search_posts"),
                    InlineKeyboardButton("🌐 Только веб", callback_data="search_web")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                response_text,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка команды /search: {e}")
            await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
        finally:
            db.close()
    
    async def handle_search_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок для команды /search"""
        user = query.from_user
        data = query.data
        
        # Получаем запрос из состояния пользователя
        user_state = self.user_states.get(user.id)
        if not user_state or user_state.get('action') != 'search_query':
            await query.answer("❌ Запрос устарел. Повторите /search", show_alert=True)
            return
        
        search_query = user_state.get('query')
        
        # Определяем тип поиска из callback_data
        if data == "search_posts":
            search_type = "posts"
        elif data == "search_web":
            search_type = "web"
        elif data == "search_both":
            search_type = "both"
        else:
            await query.answer("❌ Неверный тип поиска")
            return
        
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await query.answer("❌ Пользователь не найден")
                return
            
            # Вызов RAG service с фильтрацией
            result = await self._call_rag_service(
                "/rag/hybrid_search",
                user_id=db_user.id,
                query=search_query,
                include_web=(search_type in ["web", "both"]),
                include_posts=(search_type in ["posts", "both"]),
                limit=5
            )
            
            if not result:
                await query.answer("❌ Сервис недоступен")
                return
            
            posts = result.get("posts", [])
            web_results = result.get("web", [])
            
            # Форматируем ответ
            response_text = f"🔍 **Результаты:** {search_query}\n\n"
            
            if search_type == "posts" or search_type == "both":
                if posts:
                    response_text += f"📱 **Посты ({len(posts)}):**\n"
                    for i, post in enumerate(posts[:3], 1):
                        channel = post.get("channel", "Неизвестный канал")
                        snippet = post.get("snippet", post.get("text", ""))[:100]
                        url = post.get("url", "#")
                        response_text += f"{i}. [{channel}]({url})\n   {snippet}...\n\n"
                else:
                    response_text += "📱 **Посты:** Не найдено\n\n"
            
            if search_type == "web" or search_type == "both":
                if web_results:
                    response_text += f"🌐 **Интернет ({len(web_results)}):**\n"
                    for i, web in enumerate(web_results[:3], 1):
                        title = web.get("title", "Без названия")
                        url = web.get("url", "#")
                        response_text += f"{i}. [{title}]({url})\n\n"
                else:
                    response_text += "🌐 **Интернет:** Не найдено\n\n"
            
            # Кнопки для переключения режима (без текста запроса)
            if search_type != "both":
                keyboard = [[
                    InlineKeyboardButton("🔄 Полный поиск", callback_data="search_both")
                ]]
            else:
                keyboard = [
                    [
                        InlineKeyboardButton("📱 Только посты", callback_data="search_posts"),
                        InlineKeyboardButton("🌐 Только веб", callback_data="search_web")
                    ]
                ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                response_text,
                parse_mode='Markdown',
                disable_web_page_preview=True,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки search callback: {e}")
            await query.answer("❌ Произошла ошибка")
        finally:
            db.close()
    
    async def digest_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработка команды /digest - настройка AI-дайджестов"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден. Используйте /start")
                return
            
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Для настройки дайджестов необходимо пройти аутентификацию.\n"
                    "Используйте команду /auth"
                )
                return
            
            # Получаем текущие настройки из RAG service
            result = await self._call_rag_service(
                f"/rag/digest/settings/{db_user.id}",
                method="GET"
            )
            
            if not result:
                await update.message.reply_text(
                    "❌ Не удалось получить настройки дайджеста.\n\n"
                    "💡 RAG-сервис может быть недоступен."
                )
                return
            
            # API возвращает данные напрямую (не в "settings" ключе)
            settings = result
            enabled = settings.get("enabled", False)
            frequency = settings.get("frequency", "daily")
            time_str = settings.get("time", "09:00")
            ai_summarize = settings.get("ai_summarize", False)
            summary_style = settings.get("summary_style", "concise")
            preferred_topics = settings.get("preferred_topics", [])
            
            # Форматируем текущие настройки
            freq_text = "📅 Ежедневно" if frequency == "daily" else "📅 Еженедельно"
            ai_text = "🤖 AI-суммаризация: Включена ✅" if ai_summarize else "🤖 AI-суммаризация: Отключена ⚪"
            style_map = {"concise": "Краткий", "detailed": "Детальный", "executive": "Executive"}
            style_text = f"📊 {style_map.get(summary_style, summary_style)}"
            topics_text = f"🏷️ Темы: {', '.join(preferred_topics)}" if preferred_topics else "🏷️ Темы: Не заданы"
            
            status_text = "✅ Включен" if enabled else "❌ Отключен"
            
            # Пояснение AI-суммаризации
            ai_description = ""
            if ai_summarize:
                ai_description = "\n💡 AI создаст краткую выжимку вместо списка постов"
            else:
                ai_description = "\n💡 Дайджест будет содержать полные посты списком"
            
            message_text = f"""
⚙️ **Настройки дайджестов**

📊 **Статус:** {status_text}
{freq_text}
🕐 Время: {time_str}
{ai_text}{ai_description}
{style_text}
{topics_text}

💡 Выберите параметр для изменения:
            """
            
            # Создаем кнопки управления
            ai_button_text = "🤖 AI-суммаризация: Выключить ❌" if ai_summarize else "🤖 AI-суммаризация: Включить ✅"
            
            keyboard = [
                [InlineKeyboardButton("📅 Изменить частоту", callback_data="digest_frequency")],
                [InlineKeyboardButton("🕐 Изменить время", callback_data="digest_time")],
                [InlineKeyboardButton(ai_button_text, callback_data="digest_ai_toggle")],
                [InlineKeyboardButton("📊 Стиль суммаризации", callback_data="digest_style")],
                [InlineKeyboardButton("🏷️ Мои темы", callback_data="digest_topics")],
            ]
            
            if enabled:
                keyboard.append([InlineKeyboardButton("❌ Отключить дайджест", callback_data="digest_disable")])
            else:
                keyboard.append([InlineKeyboardButton("✅ Включить дайджест", callback_data="digest_enable")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"❌ Ошибка команды /digest: {e}")
            await update.message.reply_text(f"❌ Произошла ошибка: {str(e)}")
        finally:
            db.close()
    
    async def handle_voice_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Обработка голосовых сообщений для команд /ask и /search
        
        Premium/Enterprise only feature
        """
        user = update.effective_user
        voice = update.message.voice
        
        db = SessionLocal()
        
        try:
            # 1. Получаем пользователя
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await update.message.reply_text(
                    "❌ Пользователь не найден. Используйте /start для регистрации"
                )
                return
            
            # 2. Проверка аутентификации
            if not db_user.is_authenticated:
                await update.message.reply_text(
                    "❌ Для использования голосовых команд необходимо пройти аутентификацию.\n"
                    "Используйте команду /login <INVITE_CODE>"
                )
                return
            
            # 3. Проверка подписки (premium/enterprise only)
            tier = SUBSCRIPTION_TIERS.get(db_user.subscription_type, {})
            voice_enabled = tier.get("voice_transcription_enabled", False)
            
            if not voice_enabled:
                await update.message.reply_text(
                    "🎤 **Голосовые команды доступны только для Premium/Enterprise подписки**\n\n"
                    f"Ваша подписка: {db_user.subscription_type}\n\n"
                    "💡 Обновите подписку для использования голосовых команд:\n"
                    "/subscription",
                    parse_mode='Markdown'
                )
                return
            
            # 4. Проверка лимитов
            voice_limit = tier.get("voice_queries_per_day", 0)
            
            # Reset счетчика если новый день
            now = datetime.now(timezone.utc)
            if db_user.voice_queries_reset_at is None or db_user.voice_queries_reset_at < now:
                db_user.voice_queries_today = 0
                db_user.voice_queries_reset_at = now.replace(
                    hour=0, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                db.commit()
            
            if db_user.voice_queries_today >= voice_limit:
                await update.message.reply_text(
                    f"❌ Достигнут дневной лимит голосовых запросов: {voice_limit}\n\n"
                    f"Попробуйте завтра или обновите подписку: /subscription",
                    parse_mode='Markdown'
                )
                return
            
            # 5. Проверка длительности
            duration = voice.duration
            max_duration = int(os.getenv("VOICE_MAX_DURATION_SEC", "60"))
            
            if duration > max_duration:
                await update.message.reply_text(
                    f"❌ Голосовое сообщение слишком длинное: {duration}s\n\n"
                    f"Максимальная длительность: {max_duration} секунд\n\n"
                    f"💡 Попробуйте записать более короткое сообщение"
                )
                return
            
            # 6. Проверка доступности сервиса
            if not voice_transcription_service.is_enabled():
                await update.message.reply_text(
                    "❌ Сервис транскрибации временно недоступен\n\n"
                    "💡 Попробуйте позже или используйте текстовые команды"
                )
                return
            
            # 7. Уведомление о процессе
            status_message = await update.message.reply_text(
                f"🎤 Обрабатываю голосовое сообщение ({duration}s)...\n"
                "⏳ Это может занять 5-10 секунд"
            )
            
            try:
                # 8. Скачиваем голосовое
                voice_file = await voice.get_file()
                voice_bytes = await voice_file.download_as_bytearray()
                
                # 9. Транскрибация через SaluteSpeech
                transcription = await voice_transcription_service.transcribe_voice_message(
                    bytes(voice_bytes),
                    duration
                )
                
                if not transcription:
                    await status_message.edit_text(
                        "❌ Не удалось распознать речь в голосовом сообщении\n\n"
                        "💡 Попробуйте:\n"
                        "• Говорить четче и медленнее\n"
                        "• Записать в тихом месте\n"
                        "• Использовать текстовую команду"
                    )
                    return
                
                # 10. Увеличиваем счетчик
                db_user.voice_queries_today += 1
                db.commit()
                
                # 11. Определяем команду
                # Проверяем контекст (последняя команда пользователя)
                last_command = context.user_data.get('last_command')
                last_command_time = context.user_data.get('last_command_time')
                
                # Сбрасываем last_command если прошло больше 5 минут (300 секунд)
                if last_command_time and (datetime.now(timezone.utc) - last_command_time).total_seconds() > 300:
                    logger.info("⏰ Сброс last_command (прошло >5 минут)")
                    last_command = None
                    context.user_data.pop('last_command', None)
                    context.user_data.pop('last_command_time', None)
                
                if last_command in ['/ask', '/search']:
                    # Автоматически выполняем последнюю команду
                    await status_message.edit_text(
                        f"✅ Распознано: \"{transcription[:100]}...\"\n\n"
                        f"🔍 Выполняю команду {last_command}..."
                    )
                    
                    # Выполняем команду
                    if last_command == '/ask':
                        await self._execute_ask_with_text(update, context, transcription, db_user)
                    else:  # /search
                        await self._execute_search_with_text(update, context, transcription, db_user)
                
                else:
                    # AI-классификация через n8n
                    await status_message.edit_text(
                        f"✅ Распознано: \"{transcription[:100]}...\"\n\n"
                        f"🤖 Определяю подходящую команду..."
                    )
                    
                    classification = await self._classify_voice_command(transcription, db_user.id)
                    
                    if classification and classification.get('command'):
                        command = classification['command']
                        confidence = classification.get('confidence', 0)
                        reasoning = classification.get('reasoning', '')
                        
                        logger.info(
                            f"🤖 AI классификация: {command} "
                            f"(confidence: {confidence:.0%}, reason: {reasoning})"
                        )
                        
                        # Выполняем определенную команду
                        await status_message.edit_text(
                            f"✅ Распознано: \"{transcription[:100]}...\"\n\n"
                            f"🤖 AI выбрал: /{command} ({confidence:.0%} уверенности)\n"
                            f"🔍 Выполняю..."
                        )
                        
                        if command == 'ask':
                            await self._execute_ask_with_text(update, context, transcription, db_user)
                        elif command == 'search':
                            await self._execute_search_with_text(update, context, transcription, db_user)
                        else:
                            # Fallback для неизвестных команд
                            await self._execute_ask_with_text(update, context, transcription, db_user)
                    
                    else:
                        # Fallback: показываем кнопки если AI не сработал
                        logger.warning("⚠️ AI классификация недоступна, показываем кнопки")
                        keyboard = [
                            [InlineKeyboardButton("💡 /ask - RAG поиск", callback_data=f"voice_ask:{transcription[:200]}")],
                            [InlineKeyboardButton("🔍 /search - Гибридный поиск", callback_data=f"voice_search:{transcription[:200]}")]
                        ]
                        reply_markup = InlineKeyboardMarkup(keyboard)
                        
                        await status_message.edit_text(
                            f"✅ **Распознано:**\n\n"
                            f"\"{transcription}\"\n\n"
                            f"🤔 Выберите команду для выполнения:",
                            parse_mode='Markdown',
                            reply_markup=reply_markup
                        )
                        
                        # Сохраняем транскрипцию в контексте
                        context.user_data['voice_transcription'] = transcription
            
            except ValueError as e:
                # Ошибка длительности
                await status_message.edit_text(f"❌ {str(e)}")
            except TimeoutError:
                await status_message.edit_text(
                    "⏰ Timeout транскрибации\n\n"
                    "💡 Попробуйте записать более короткое сообщение"
                )
            except Exception as e:
                logger.error(f"❌ Ошибка обработки голосового: {e}")
                await status_message.edit_text(
                    f"❌ Ошибка обработки голосового сообщения\n\n"
                    f"💡 Попробуйте еще раз или используйте текстовую команду"
                )
        
        finally:
            db.close()
    
    async def _classify_voice_command(self, transcription: str, user_id: int) -> Optional[Dict]:
        """
        Классифицировать голосовую команду через n8n AI агента
        
        Args:
            transcription: Транскрипция голосового сообщения
            user_id: ID пользователя
            
        Returns:
            Dict с полями: command, confidence, reasoning
            или None если классификация не удалась
        """
        n8n_url = os.getenv("N8N_WEBHOOK_URL", "http://n8n:5678")
        n8n_enabled = os.getenv("VOICE_AI_CLASSIFIER_ENABLED", "true").lower() == "true"
        
        if not n8n_enabled:
            logger.info("🤖 AI классификатор отключен в конфигурации")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{n8n_url}/webhook/voice-classify",
                    json={
                        "transcription": transcription,
                        "user_id": user_id
                    }
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Проверяем что result содержит command
                    if result and result.get('command'):
                        logger.info(
                            f"🤖 AI classification: {result.get('command')} "
                            f"({result.get('confidence', 0):.0%})"
                        )
                        return result
                    else:
                        logger.error(f"❌ n8n classifier returned invalid response: {result}")
                        return None
                else:
                    logger.error(f"❌ n8n classifier error {response.status_code}: {response.text}")
                    return None
        
        except httpx.TimeoutException:
            logger.error("⏰ n8n classifier timeout")
            return None
        except Exception as e:
            logger.error(f"❌ Error calling n8n classifier: {e}")
            return None
    
    async def _execute_ask_with_text(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query_text: str,
        db_user: User
    ):
        """Выполнить /ask с текстом запроса"""
        try:
            # Отправляем запрос к RAG service
            await update.message.reply_text("🔍 Ищу ответ в ваших постах...")
            
            result = await self._call_rag_service(
                "/rag/ask",
                method="POST",
                user_id=db_user.id,
                query=query_text,
                top_k=5
            )
            
            if not result:
                await update.message.reply_text(
                    "❌ RAG-сервис недоступен\n\n"
                    "💡 Попробуйте позже"
                )
                return
            
            answer = result.get("answer", "Не удалось найти ответ")
            
            # Форматируем ответ (источники уже включены в answer от RAG service)
            # НЕ используем parse_mode, так как RAG может вернуть спецсимволы Markdown
            response_text = f"💡 Ответ:\n\n{answer}"
            
            await update.message.reply_text(response_text)
        
        except Exception as e:
            logger.error(f"❌ Ошибка _execute_ask_with_text: {e}")
            await update.message.reply_text("❌ Ошибка выполнения команды")
    
    async def _execute_search_with_text(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        query_text: str,
        db_user: User
    ):
        """Выполнить /search с текстом запроса"""
        try:
            await update.message.reply_text("🔍 Ищу в ваших постах и в интернете...")
            
            # Гибридный поиск (посты + веб через SearXNG)
            hybrid_result = await self._call_rag_service(
                "/rag/hybrid_search",
                method="POST",
                user_id=db_user.id,
                query=query_text,
                include_posts=True,
                include_web=True,
                limit=5
            )
            
            response_text = f"🔍 Результаты поиска: \"{query_text}\"\n\n"
            
            # Посты пользователя
            if hybrid_result and hybrid_result.get("posts"):
                posts = hybrid_result["posts"]
                response_text += f"📱 Ваши посты ({len(posts)}):\n"
                for i, post in enumerate(posts[:5], 1):
                    channel = post.get("channel", "Unknown")
                    score = int(post.get("score", 0) * 100)
                    snippet = post.get("snippet", post.get("text", ""))[:80]
                    response_text += f"{i}. @{channel} ({score}%)\n   {snippet}...\n\n"
            else:
                response_text += "📱 Ваши посты: Ничего не найдено\n\n"
            
            # Интернет (реальные результаты из SearXNG)
            if hybrid_result and hybrid_result.get("web"):
                web_results = hybrid_result["web"]
                response_text += f"🌐 Интернет ({len(web_results)}):\n"
                for i, web in enumerate(web_results[:3], 1):
                    title = web.get("title", "Без названия")[:70]
                    url = web.get("url", "#")
                    response_text += f"{i}. {title}\n   {url}\n\n"
            else:
                response_text += "🌐 Интернет: Ничего не найдено"
            
            await update.message.reply_text(response_text)
        
        except Exception as e:
            logger.error(f"❌ Ошибка _execute_search_with_text: {e}")
            await update.message.reply_text("❌ Ошибка выполнения команды")
    
    async def handle_voice_ask_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки voice_ask - выполнить /ask с транскрипцией"""
        user = query.from_user
        transcription = query.data.split(":", 1)[1] if ":" in query.data else context.user_data.get('voice_transcription', '')
        
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await query.edit_message_text("❌ Пользователь не найден")
                return
            
            # Обновляем сообщение
            await query.edit_message_text(
                f"✅ Распознано: \"{transcription[:100]}...\"\n\n"
                f"🔍 Выполняю /ask..."
            )
            
            # Выполняем /ask
            # Создаем фиктивный update для вызова команды
            class FakeMessage:
                def __init__(self, chat_id):
                    self.chat_id = chat_id
                    self.message_id = query.message.message_id
                
                async def reply_text(self, text, **kwargs):
                    await query.message.reply_text(text, **kwargs)
            
            class FakeUpdate:
                def __init__(self, user, message):
                    self.effective_user = user
                    self.message = message
            
            fake_update = FakeUpdate(query.from_user, FakeMessage(query.message.chat_id))
            
            await self._execute_ask_with_text(fake_update, context, transcription, db_user)
        
        except Exception as e:
            logger.error(f"❌ Ошибка handle_voice_ask_callback: {e}")
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def handle_voice_search_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка кнопки voice_search - выполнить /search с транскрипцией"""
        user = query.from_user
        transcription = query.data.split(":", 1)[1] if ":" in query.data else context.user_data.get('voice_transcription', '')
        
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await query.edit_message_text("❌ Пользователь не найден")
                return
            
            # Обновляем сообщение
            await query.edit_message_text(
                f"✅ Распознано: \"{transcription[:100]}...\"\n\n"
                f"🔍 Выполняю /search..."
            )
            
            # Выполняем /search
            class FakeMessage:
                def __init__(self, chat_id):
                    self.chat_id = chat_id
                    self.message_id = query.message.message_id
                
                async def reply_text(self, text, **kwargs):
                    await query.message.reply_text(text, **kwargs)
            
            class FakeUpdate:
                def __init__(self, user, message):
                    self.effective_user = user
                    self.message = message
            
            fake_update = FakeUpdate(query.from_user, FakeMessage(query.message.chat_id))
            
            await self._execute_search_with_text(fake_update, context, transcription, db_user)
        
        except Exception as e:
            logger.error(f"❌ Ошибка handle_voice_search_callback: {e}")
            await query.edit_message_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def handle_digest_callback(self, query, context: ContextTypes.DEFAULT_TYPE):
        """Обработка callback кнопок для настройки дайджестов"""
        user = query.from_user
        data = query.data
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await query.answer("❌ Пользователь не найден")
                return
            
            # Получаем текущие настройки
            result = await self._call_rag_service(
                f"/rag/digest/settings/{db_user.id}",
                method="GET"
            )
            
            if not result:
                await query.answer("❌ Ошибка получения настроек")
                return
            
            # API возвращает данные напрямую (не в "settings" ключе)
            settings = result
            
            # Обработка разных callback actions
            if data == "digest_frequency":
                # Показываем выбор частоты
                keyboard = [
                    [InlineKeyboardButton("📅 Ежедневно", callback_data="digest_freq_daily")],
                    [InlineKeyboardButton("📅 Еженедельно", callback_data="digest_freq_weekly")],
                    [InlineKeyboardButton("← Назад", callback_data="digest_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📅 **Выберите частоту дайджестов:**",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            
            elif data.startswith("digest_freq_"):
                frequency = data.split("_")[-1]
                # Обновляем настройки
                update_result = await self._call_rag_service(
                    f"/rag/digest/settings/{db_user.id}",
                    method="PUT",
                    enabled=settings.get("enabled", True),
                    frequency=frequency,
                    time=settings.get("time", "09:00"),
                    ai_summarize=settings.get("ai_summarize", False),
                    summary_style=settings.get("summary_style", "concise")
                )
                
                if update_result:
                    await query.answer("✅ Частота обновлена")
                    # Возвращаемся к главному меню
                    await self._show_digest_menu(query, db_user.id, edit=True)
                else:
                    await query.answer("❌ Ошибка обновления")
            
            elif data == "digest_time":
                # Показываем выбор времени
                keyboard = [
                    [InlineKeyboardButton("🕘 09:00", callback_data="digest_time_09:00")],
                    [InlineKeyboardButton("🕛 12:00", callback_data="digest_time_12:00")],
                    [InlineKeyboardButton("🕕 18:00", callback_data="digest_time_18:00")],
                    [InlineKeyboardButton("🕘 21:00", callback_data="digest_time_21:00")],
                    [InlineKeyboardButton("← Назад", callback_data="digest_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "🕐 **Выберите время отправки:**",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            
            elif data.startswith("digest_time_"):
                time_value = data.split("_", 2)[-1]
                # Обновляем настройки
                update_result = await self._call_rag_service(
                    f"/rag/digest/settings/{db_user.id}",
                    method="PUT",
                    enabled=settings.get("enabled", True),
                    frequency=settings.get("frequency", "daily"),
                    time=time_value,
                    ai_summarize=settings.get("ai_summarize", False),
                    summary_style=settings.get("summary_style", "concise")
                )
                
                if update_result:
                    await query.answer("✅ Время обновлено")
                    await self._show_digest_menu(query, db_user.id, edit=True)
                else:
                    await query.answer("❌ Ошибка обновления")
            
            elif data == "digest_ai_toggle":
                # Переключаем AI-суммаризацию
                new_ai_state = not settings.get("ai_summarize", False)
                update_result = await self._call_rag_service(
                    f"/rag/digest/settings/{db_user.id}",
                    method="PUT",
                    enabled=settings.get("enabled", True),
                    frequency=settings.get("frequency", "daily"),
                    time=settings.get("time", "09:00"),
                    ai_summarize=new_ai_state,
                    summary_style=settings.get("summary_style", "concise")
                )
                
                if update_result:
                    if new_ai_state:
                        await query.answer("✅ AI будет создавать краткую выжимку", show_alert=True)
                    else:
                        await query.answer("✅ Дайджест будет содержать полные посты", show_alert=True)
                    await self._show_digest_menu(query, db_user.id, edit=True)
                else:
                    await query.answer("❌ Ошибка обновления")
            
            elif data == "digest_style":
                # Показываем выбор стиля
                keyboard = [
                    [InlineKeyboardButton("📄 Краткий", callback_data="digest_style_concise")],
                    [InlineKeyboardButton("📋 Детальный", callback_data="digest_style_detailed")],
                    [InlineKeyboardButton("📊 Executive", callback_data="digest_style_executive")],
                    [InlineKeyboardButton("← Назад", callback_data="digest_back")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await query.edit_message_text(
                    "📊 **Выберите стиль суммаризации:**\n\n"
                    "• **Краткий** - только ключевые моменты\n"
                    "• **Детальный** - подробный обзор\n"
                    "• **Executive** - для руководителей",
                    parse_mode='Markdown',
                    reply_markup=reply_markup
                )
            
            elif data.startswith("digest_style_"):
                style = data.split("_")[-1]
                # Обновляем настройки
                update_result = await self._call_rag_service(
                    f"/rag/digest/settings/{db_user.id}",
                    method="PUT",
                    enabled=settings.get("enabled", True),
                    frequency=settings.get("frequency", "daily"),
                    time=settings.get("time", "09:00"),
                    ai_summarize=settings.get("ai_summarize", False),
                    summary_style=style
                )
                
                if update_result:
                    await query.answer("✅ Стиль обновлен")
                    await self._show_digest_menu(query, db_user.id, edit=True)
                else:
                    await query.answer("❌ Ошибка обновления")
            
            elif data == "digest_topics":
                # Устанавливаем state для ввода тем
                self.user_states[user.id] = {
                    'action': 'digest_topics_input',
                    'timestamp': time.time()
                }
                
                await query.edit_message_text(
                    "🏷️ **Введите ваши предпочитаемые темы**\n\n"
                    "Отправьте темы через запятую.\n\n"
                    "**Пример:**\n"
                    "`AI, блокчейн, стартапы, технологии`\n\n"
                    "Или отправьте `/cancel` для отмены",
                    parse_mode='Markdown'
                )
            
            elif data == "digest_enable":
                # Включаем дайджест
                update_result = await self._call_rag_service(
                    f"/rag/digest/settings/{db_user.id}",
                    method="PUT",
                    enabled=True,
                    frequency=settings.get("frequency", "daily"),
                    time=settings.get("time", "09:00"),
                    ai_summarize=settings.get("ai_summarize", False),
                    summary_style=settings.get("summary_style", "concise")
                )
                
                if update_result:
                    await query.answer("✅ Дайджест включен")
                    await self._show_digest_menu(query, db_user.id, edit=True)
                else:
                    await query.answer("❌ Ошибка обновления")
            
            elif data == "digest_disable":
                # Отключаем дайджест
                update_result = await self._call_rag_service(
                    f"/rag/digest/settings/{db_user.id}",
                    method="PUT",
                    enabled=False,
                    frequency=settings.get("frequency", "daily"),
                    time=settings.get("time", "09:00"),
                    ai_summarize=settings.get("ai_summarize", False),
                    summary_style=settings.get("summary_style", "concise")
                )
                
                if update_result:
                    await query.answer("✅ Дайджест отключен")
                    await self._show_digest_menu(query, db_user.id, edit=True)
                else:
                    await query.answer("❌ Ошибка обновления")
            
            elif data == "digest_back":
                # Возврат к главному меню дайджестов
                await self._show_digest_menu(query, db_user.id, edit=True)
            
        except Exception as e:
            logger.error(f"❌ Ошибка обработки digest callback: {e}")
            await query.answer("❌ Произошла ошибка")
        finally:
            db.close()
    
    async def _show_digest_menu(self, query_or_update, user_id: int, edit: bool = False):
        """Показать меню настроек дайджестов"""
        # Получаем настройки
        result = await self._call_rag_service(
            f"/rag/digest/settings/{user_id}",
            method="GET"
        )
        
        if not result:
            message = "❌ Не удалось загрузить настройки"
            if edit:
                await query_or_update.edit_message_text(message)
            else:
                await query_or_update.message.reply_text(message)
            return
        
        # API возвращает данные напрямую (не в "settings" ключе)
        settings = result
        enabled = settings.get("enabled", False)
        frequency = settings.get("frequency", "daily")
        time_str = settings.get("time", "09:00")
        ai_summarize = settings.get("ai_summarize", False)
        summary_style = settings.get("summary_style", "concise")
        preferred_topics = settings.get("preferred_topics", [])
        
        # Форматируем текущие настройки
        freq_text = "📅 Ежедневно" if frequency == "daily" else "📅 Еженедельно"
        ai_text = "🤖 AI-суммаризация: Включена ✅" if ai_summarize else "🤖 AI-суммаризация: Отключена ⚪"
        style_map = {"concise": "Краткий", "detailed": "Детальный", "executive": "Executive"}
        style_text = f"📊 {style_map.get(summary_style, summary_style)}"
        topics_text = f"🏷️ Темы: {', '.join(preferred_topics)}" if preferred_topics else "🏷️ Темы: Не заданы"
        status_text = "✅ Включен" if enabled else "❌ Отключен"
        
        # Пояснение AI-суммаризации
        ai_description = ""
        if ai_summarize:
            ai_description = "\n💡 AI создаст краткую выжимку вместо списка постов"
        else:
            ai_description = "\n💡 Дайджест будет содержать полные посты списком"
        
        message_text = f"""
⚙️ **Настройки дайджестов**

📊 **Статус:** {status_text}
{freq_text}
🕐 Время: {time_str}
{ai_text}{ai_description}
{style_text}
{topics_text}

💡 Выберите параметр для изменения:
        """
        
        # Кнопки
        ai_button_text = "🤖 AI-суммаризация: Выключить ❌" if ai_summarize else "🤖 AI-суммаризация: Включить ✅"
        
        keyboard = [
            [InlineKeyboardButton("📅 Изменить частоту", callback_data="digest_frequency")],
            [InlineKeyboardButton("🕐 Изменить время", callback_data="digest_time")],
            [InlineKeyboardButton(ai_button_text, callback_data="digest_ai_toggle")],
            [InlineKeyboardButton("📊 Стиль суммаризации", callback_data="digest_style")],
            [InlineKeyboardButton("🏷️ Мои темы", callback_data="digest_topics")],
        ]
        
        if enabled:
            keyboard.append([InlineKeyboardButton("❌ Отключить дайджест", callback_data="digest_disable")])
        else:
            keyboard.append([InlineKeyboardButton("✅ Включить дайджест", callback_data="digest_enable")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if edit:
            await query_or_update.edit_message_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
        else:
            await query_or_update.reply_text(
                message_text,
                parse_mode='Markdown',
                reply_markup=reply_markup
            )
    
    def get_voice_mode_keyboard(self) -> ReplyKeyboardMarkup:
        """Создать Reply клавиатуру для выбора режима голосовых команд"""
        keyboard = [
            [
                KeyboardButton("🤖 AI режим"),
                KeyboardButton("💡 Ask режим"),
                KeyboardButton("🔍 Search режим")
            ]
        ]
        return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    async def reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Сбросить состояние голосовых команд"""
        context.user_data.pop('last_command', None)
        context.user_data.pop('last_command_time', None)
        context.user_data.pop('voice_transcription', None)
        context.user_data['voice_mode'] = 'ai'  # Сбрасываем в AI режим
        
        await update.message.reply_text(
            "🔄 **Состояние сброшено!**\n\n"
            "Режим: 🤖 AI классификатор\n\n"
            "Голосовые сообщения будут автоматически распознаваться как /ask или /search",
            reply_markup=self.get_voice_mode_keyboard()
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Справка по командам с учетом роли пользователя"""
        # Сбрасываем last_command чтобы голосовые использовали AI классификатор
        context.user_data.pop('last_command', None)
        
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            
            if not db_user:
                await update.message.reply_text(
                    "❌ Пользователь не найден. Используйте /start для регистрации"
                )
                return
            
            is_admin = db_user.is_admin()
            
            # Базовая справка для всех
            base_help = """
🤖 **Telegram Channel Parser Bot - Справка**

🔐 **Аутентификация:**
/login INVITE\\_CODE - QR авторизация (БЕЗ SMS!)
/auth - Веб-форма (свои API ключи)
/auth\\_status - Проверить статус
/logout - Выйти из системы

📋 **Управление каналами:**
/add\\_channel @channel\\_name - Добавить канал
/my\\_channels - Список ваших каналов
/remove\\_channel - Удалить канал

👥 **Управление группами:**
/add\\_group <ссылка> - Добавить группу для мониторинга
/my\\_groups - Список отслеживаемых групп
/group\\_digest <часы> - Дайджест разговора (AI)
/group\\_settings - Настройки уведомлений

🤖 **RAG & AI:**
/ask <вопрос> - Поиск ответа в постах
/search <запрос> - Гибридный поиск (посты + веб)
/recommend - Персональные рекомендации
/digest - Настроить AI-дайджесты

🎤 **Голосовые команды (Premium/Enterprise):**
📌 **Вариант 1:** Команда → Голосовое
• Отправьте `/ask` или `/search`
• Затем отправьте голосовое с запросом
• Автоматически выполнится выбранная команда

📌 **Вариант 2:** Голосовое → AI выбирает
• Отправьте голосовое БЕЗ команды
• AI автоматически выберет /ask или /search

🔄 **Сброс режима:**
• `/reset` - сбросить состояние (вернуться к AI)
• Авто-сброс через 5 минут после команды

⚠️ Ограничения: макс. 60 сек, лимиты по подписке

💎 **Подписка:**
/subscription - Информация о вашей подписке

**Примеры команд:**
• `/ask Что нового в AI?`
• `/search квантовые компьютеры`
• `/add_channel @durov`
• `/add_group https://t.me/my\\_group`
• `/group_digest 24`
"""
            
            # Админские команды
            admin_help = """
👑 **КОМАНДЫ АДМИНИСТРАТОРА:**

📱 **Админ панель (рекомендуется):**
/admin - Открыть Admin Panel Mini App
  • Управление пользователями (роли, подписки)
  • Создание инвайт кодов
  • Статистика и графики
  • Блокировка/разблокировка

📝 **Текстовые админ команды:**
/admin\\_invite - Создать инвайт код
/admin\\_users - Список всех пользователей
/admin\\_user <telegram\\_id> - Информация о пользователе
/admin\\_grant <telegram\\_id> <subscription> <days> - Выдать подписку
/admin\\_stats - Общая статистика

💡 **Рекомендация:** Используйте `/admin` для удобного управления через Mini App
""" if is_admin else ""
            
            footer = """
💡 **Полезная информация:**
• Парсинг каналов: автоматически каждые 30 минут
• QR авторизация: без SMS кодов, за 30 секунд
• RAG поиск: по всем вашим постам с AI
• Дайджесты: персонализированные сводки

📚 **Документация:**
Подробные гайды и примеры: /help\\_docs
            """
            
            help_text = base_help + admin_help + footer
            
            await update.message.reply_text(help_text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Ошибка в help_command: {e}")
            await update.message.reply_text("❌ Произошла ошибка")
        finally:
            db.close()
    
    async def debug_status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Показать детальный статус пользователя для отладки"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            text = f"🔍 **Debug Status**\n\n"
            text += f"👤 User: {db_user.first_name} ({db_user.telegram_id})\n"
            text += f"🆔 DB ID: {db_user.id}\n"
            text += f"📍 Role: {db_user.role}\n"
            text += f"💎 Subscription: {db_user.subscription_type}\n"
            text += f"🔐 Authenticated: {db_user.is_authenticated}\n\n"
            
            text += f"**Auth Status:**\n"
            text += f"• Blocked: {'❌ YES' if db_user.is_blocked else '✅ NO'}\n"
            text += f"• Failed attempts: {db_user.failed_auth_attempts}\n"
            
            if db_user.block_expires:
                # Timezone-aware сравнение
                expires = db_user.block_expires
                if expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                
                if expires > datetime.now(timezone.utc):
                    text += f"• Block expires: {expires.strftime('%d.%m.%Y %H:%M UTC')}\n"
                else:
                    text += f"• Block expired ✅\n"
            
            if db_user.last_auth_attempt:
                text += f"• Last attempt: {db_user.last_auth_attempt.strftime('%d.%m.%Y %H:%M:%S UTC')}\n"
            
            if db_user.auth_error:
                text += f"• Last error: {db_user.auth_error}\n"
            
            # Session файл
            from shared_auth_manager import shared_auth_manager
            session_path = shared_auth_manager._get_session_path(user.id)
            import os
            session_exists = os.path.exists(session_path)
            text += f"\n**Session:**\n"
            text += f"• File exists: {'✅ YES' if session_exists else '❌ NO'}\n"
            text += f"• Active client: {'✅ YES' if user.id in shared_auth_manager.active_clients else '❌ NO'}\n"
            
            await update.message.reply_text(text, parse_mode='Markdown')
            
        except Exception as e:
            logger.error(f"Debug status error: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def debug_unblock_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Разблокировать пользователя (для отладки)"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            # Разблокируем
            db_user.is_blocked = False
            db_user.block_expires = None
            db_user.failed_auth_attempts = 0
            db_user.auth_error = None
            db.commit()
            
            await update.message.reply_text(
                "✅ **Разблокировка выполнена!**\n\n"
                "• Блокировка снята\n"
                "• Счетчик попыток сброшен\n"
                "• Ошибки очищены\n\n"
                "Теперь можете попробовать `/login` снова",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    async def debug_reset_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Полный сброс для отладки (session + БД)"""
        user = update.effective_user
        db = SessionLocal()
        
        try:
            db_user = db.query(User).filter(User.telegram_id == user.id).first()
            if not db_user:
                await update.message.reply_text("❌ Пользователь не найден")
                return
            
            # Очищаем все данные авторизации
            db_user.is_authenticated = False
            db_user.is_blocked = False
            db_user.block_expires = None
            db_user.failed_auth_attempts = 0
            db_user.auth_error = None
            db_user.last_auth_attempt = None
            db_user.last_auth_check = None
            db_user.phone_number = None
            db.commit()
            
            # Удаляем session файл
            from shared_auth_manager import shared_auth_manager
            await shared_auth_manager.disconnect_client(user.id)
            
            session_path = shared_auth_manager._get_session_path(user.id)
            if os.path.exists(session_path):
                os.remove(session_path)
                logger.info(f"🗑️ Session файл удален для {user.id}")
            
            await update.message.reply_text(
                "✅ **Полный сброс выполнен!**\n\n"
                "Очищено:\n"
                "• Данные авторизации\n"
                "• Блокировки\n"
                "• Session файл\n"
                "• Счетчики попыток\n\n"
                "🔄 Используйте `/login INVITE_CODE` для новой попытки",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            logger.error(f"Debug reset error: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
        finally:
            db.close()
    
    def run(self):
        """Запуск бота (синхронный для standalone)"""
        print("🤖 Запуск Telegram бота...")
        # Явно указываем, что хотим получать callback_query updates
        self.application.run_polling(
            allowed_updates=["message", "callback_query", "edited_message"]
        )
        logger.info("✅ Бот запущен с поддержкой: message, callback_query, edited_message")
    
    async def run_async(self):
        """Запуск бота (async для интеграции в run_system.py)"""
        logger.info("🤖 Запуск Telegram бота (async)...")
        # Инициализируем и запускаем бота
        await self.application.initialize()
        await self.application.start()
        await self.application.updater.start_polling(
            allowed_updates=["message", "callback_query", "edited_message"]
        )
        logger.info("✅ Telegram Bot запущен в async режиме")

if __name__ == "__main__":
    from database import create_tables
    create_tables()
    
    bot = TelegramBot()
    bot.run() 