"""
Форматирование сообщений для Telegram

Этот модуль предоставляет функции для безопасного форматирования
сообщений для отправки через Telegram Bot API.

ВАЖНО: Используем HTML формат вместо MarkdownV2, так как:
- telegramify-markdown НЕ экранирует двоеточия (:)
- HTML проще и надежнее для динамического контента
- Telegram полностью поддерживает HTML
"""
from html import escape
from typing import Dict, Any
from datetime import datetime
import re


def format_digest_for_telegram(digest: Dict[str, Any], group_title: str) -> str:
    """
    Форматирует дайджест группы в Markdown для отправки в Telegram
    
    Args:
        digest: Словарь с результатом от generate_digest()
            - period: строка с периодом (например, "последние 24ч")
            - message_count: количество проанализированных сообщений
            - topics: список основных тем
            - speakers_summary: словарь {username: summary}
            - overall_summary: общее резюме
        group_title: Название группы
        
    Returns:
        Отформатированное сообщение в MarkdownV2 формате
    """
    
    markdown = f"""# 📊 Дайджест группы: {group_title}

**Период:** {digest.get('period', 'unknown')}
**Сообщений проанализировано:** {digest.get('message_count', 0)}

"""
    
    # Темы
    topics = digest.get('topics', [])
    if topics:
        markdown += "## 🎯 Основные темы:\n\n"
        for i, topic in enumerate(topics, 1):
            markdown += f"{i}. {topic}\n"
        markdown += "\n"
    
    # Спикеры
    speakers = digest.get('speakers_summary', {})
    if speakers:
        markdown += "## 👥 Активные участники:\n\n"
        for username, summary in speakers.items():
            markdown += f"• @{username}: {summary}\n"
        markdown += "\n"
    
    # Резюме
    overall = digest.get('overall_summary', '')
    if overall:
        markdown += f"## 📝 Резюме:\n\n{overall}\n"
    
    # Конвертируем в HTML для Telegram
    return markdown_to_html(markdown)


def format_mention_for_telegram(
    analysis: Dict[str, Any],
    group_title: str,
    message_link: str = None
) -> str:
    """
    Форматирует уведомление об упоминании для отправки в Telegram
    
    Args:
        analysis: Результат анализа упоминания
            - urgency: уровень срочности ('urgent', 'important', 'normal')
            - context: контекст упоминания
            - mention_reason: причина упоминания
            - key_points: список ключевых моментов
        group_title: Название группы
        message_link: Ссылка на сообщение (опционально)
        
    Returns:
        Отформатированное уведомление в MarkdownV2 формате
    """
    
    urgency = analysis.get('urgency', 'normal')
    urgency_emoji = {
        'urgent': '🔴',
        'important': '🟡',
        'normal': '🟢'
    }.get(urgency, '🟢')
    
    markdown = f"""{urgency_emoji} **Упоминание в группе**

**Группа:** {group_title}

"""
    
    # Контекст
    context = analysis.get('context', '')
    if context:
        markdown += f"**Контекст:**\n{context}\n\n"
    
    # Причина
    reason = analysis.get('mention_reason', '')
    if reason:
        markdown += f"**Почему упомянули:** {reason}\n\n"
    
    # Ключевые моменты
    key_points = analysis.get('key_points', [])
    if key_points:
        markdown += "**Ключевые моменты:**\n"
        for point in key_points:
            markdown += f"• {point}\n"
        markdown += "\n"
    
    # Ссылка на сообщение (HTML формат)
    if message_link:
        markdown += f'<a href="{message_link}">Перейти к сообщению</a>\n\n'
    
    # Футер с временем
    markdown += f"*Срочность: {urgency.upper()} • {datetime.now().strftime('%H:%M')}*"
    
    # Конвертируем в HTML для Telegram
    return markdown_to_html(markdown)


def markdown_to_html(text: str) -> str:
    """
    Конвертация простого Markdown в HTML для Telegram
    
    Поддерживает:
    - ## Заголовки → <b>Заголовки</b>
    - **жирный** → <b>жирный</b>
    - *курсив* → <i>курсив</i>
    - `код` → <code>код</code>
    - --- → ──────
    - Списки - → •
    
    Args:
        text: Текст с Markdown разметкой
        
    Returns:
        HTML форматированный текст для Telegram
    """
    if not text:
        return text
    
    # Сначала сохраняем уже существующие HTML ссылки
    html_links = []
    def save_html_link(match):
        html_links.append(match.group(0))
        return f"__HTML_LINK_{len(html_links)-1}__"
    
    text = re.sub(r'<a\s+href="[^"]+">.*?</a>', save_html_link, text)
    
    # Экранируем HTML спецсимволы
    text = escape(text)
    
    # Восстанавливаем HTML ссылки
    for i, link in enumerate(html_links):
        text = text.replace(f"__HTML_LINK_{i}__", link)
    
    # Конвертируем Markdown ссылки [text](url) → <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    # Заголовки ## → <b>
    text = re.sub(r'###\s+(.+?)(?=\n|$)', r'<b>\1</b>', text)
    text = re.sub(r'##\s+(.+?)(?=\n|$)', r'<b>\1</b>', text)
    text = re.sub(r'#\s+(.+?)(?=\n|$)', r'<b>\1</b>', text)
    
    # Жирный **текст** → <b>текст</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Курсив *текст* → <i>текст</i>  
    text = re.sub(r'\*([^\*]+?)\*', r'<i>\1</i>', text)
    
    # Код `текст` → <code>текст</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    # Разделители --- → ──────
    text = re.sub(r'^---+$', '──────────────', text, flags=re.MULTILINE)
    
    # Списки - → • (включая вложенные с отступами)
    text = re.sub(r'^\s*-\s+', lambda m: m.group(0).replace('-', '•'), text, flags=re.MULTILINE)
    
    return text


def markdownify(text: str) -> str:
    """
    Конвертация Markdown → HTML для Telegram
    
    Использовать для динамического контента (ошибки, RAG ответы и т.д.)
    
    Args:
        text: Исходный текст в Markdown формате
        
    Returns:
        HTML форматированный текст для Telegram
        
    Example:
        >>> from telegram_formatter import markdownify
        >>> safe_text = markdownify("Ошибка: файл_не_найден.txt")
        >>> await bot.send_message(chat_id, safe_text, parse_mode='HTML')
    """
    return markdown_to_html(text)

