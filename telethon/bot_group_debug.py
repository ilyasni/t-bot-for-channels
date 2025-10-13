"""
Debug команды для анализа работы Groups функционала
"""
import logging
from telegram import Update
from telegram.ext import ContextTypes
from database import SessionLocal
from models import User, Group, user_group
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)


async def debug_group_digest_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug версия group_digest с детальным выводом"""
    user = update.effective_user
    args = context.args
    
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.telegram_id == user.id).first()
        if not db_user:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        
        # Получаем группы
        from models import Group
        groups = db.query(Group).join(
            user_group,
            Group.id == user_group.c.group_id
        ).filter(
            user_group.c.user_id == db_user.id,
            user_group.c.is_active == True
        ).all()
        
        if not groups:
            await update.message.reply_text("📭 Нет групп")
            return
        
        target_group = groups[0]
        hours = int(args[0]) if args and args[0].isdigit() else 24
        
        await update.message.reply_text("🔍 DEBUG MODE - Генерация дайджеста...")
        
        # Получаем клиент
        from shared_auth_manager import shared_auth_manager
        client = await shared_auth_manager.get_user_client(user.id)
        
        if not client:
            await update.message.reply_text("❌ Клиент недоступен")
            return
        
        # Получаем сообщения
        date_from = datetime.now(timezone.utc) - timedelta(hours=hours)
        
        messages = []
        async for msg in client.iter_messages(target_group.group_id, limit=50):
            msg_date = msg.date
            if msg_date.tzinfo is None:
                msg_date = msg_date.replace(tzinfo=timezone.utc)
            else:
                msg_date = msg_date.astimezone(timezone.utc)
            
            if msg_date < date_from:
                break
            if msg.text:
                messages.append(msg)
        
        await update.message.reply_text(
            f"📊 DEBUG: Получено {len(messages)} сообщений\n"
            f"Период: {hours} часов\n"
            f"Группа ID: {target_group.group_id}"
        )
        
        # Генерируем дайджест
        from group_digest_generator import group_digest_generator
        import json
        
        try:
            digest = await group_digest_generator.generate_digest(
                user_id=db_user.id,
                group_id=target_group.id,
                messages=messages,
                hours=hours
            )
            
            # Показываем RAW результат
            raw_json = json.dumps(digest, indent=2, ensure_ascii=False)
            
            await update.message.reply_text(
                f"🔍 **DEBUG: RAW результат от n8n:**\n\n"
                f"```json\n{raw_json[:3000]}\n```",
                parse_mode='Markdown'
            )
            
            # Показываем отформатированный
            formatted = group_digest_generator.format_digest_for_telegram(
                digest=digest,
                group_title=target_group.group_title or str(target_group.group_id)
            )
            
            await update.message.reply_text(
                f"📝 **Отформатированный:**\n\n{formatted[:3000]}",
                parse_mode='Markdown'
            )
            
        except Exception as e:
            await update.message.reply_text(
                f"❌ DEBUG ERROR:\n{str(e)}"
            )
            logger.error(f"Debug group_digest error: {e}", exc_info=True)
    
    finally:
        db.close()


async def debug_n8n_test_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тест прямого вызова n8n workflow"""
    import httpx
    import json
    
    await update.message.reply_text("🧪 Тестирую n8n workflow напрямую...")
    
    payload = {
        "messages": [
            {"username": "alice", "text": "Тест сообщение 1", "date": "2025-01-15T10:00:00Z"},
            {"username": "bob", "text": "Тест сообщение 2", "date": "2025-01-15T10:05:00Z"}
        ],
        "user_id": 1,
        "group_id": 1,
        "hours": 6
    }
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                'http://n8n:5678/webhook/group-digest',
                json=payload
            )
            
            result = response.json()
            raw_json = json.dumps(result, indent=2, ensure_ascii=False)
            
            await update.message.reply_text(
                f"✅ HTTP {response.status_code}\n\n"
                f"```json\n{raw_json[:3000]}\n```",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {str(e)}")

