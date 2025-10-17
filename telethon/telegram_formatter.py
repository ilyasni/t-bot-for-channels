"""
Форматирование сообщений для Telegram

Этот модуль предоставляет функции для безопасного форматирования
сообщений для отправки через Telegram Bot API.

ВАЖНО: Используем HTML формат вместо MarkdownV2, так как:
- telegramify-markdown НЕ экранирует двоеточия (:)
- HTML проще и надежнее для динамического контента
- Telegram полностью поддерживает HTML

Поддерживаемые HTML теги:
- <b>, <strong>, <i>, <em>, <u>, <s>
- <code>, <pre>, <pre><code class="language-X">
- <a href="url">text</a>
- <blockquote>, <blockquote expandable>
- <tg-spoiler>
"""
from html import escape
from typing import Dict, Any, List, Optional
from datetime import datetime
import re


def format_digest_for_telegram(digest: Dict[str, Any], group_title: str) -> str:
    """
    Форматирует дайджест группы в HTML для отправки в Telegram
    
    Args:
        digest: Словарь с результатом от generate_digest()
            - period: строка с периодом (например, "последние 24ч")
            - message_count: количество проанализированных сообщений
            - topics: список основных тем
            - speakers_summary: словарь {username: summary}
            - overall_summary: общее резюме
        group_title: Название группы
        
    Returns:
        HTML форматированное сообщение для Telegram
    """
    html_parts = []
    
    # Заголовок
    html_parts.append(f"<b>📊 Дайджест группы: {escape(group_title)}</b>")
    html_parts.append("")
    html_parts.append(f"<i>Период: {escape(digest.get('period', 'unknown'))}</i>")
    html_parts.append(f"<i>Сообщений проанализировано: {digest.get('message_count', 0)}</i>")
    html_parts.append("")
    
    # Темы
    topics = digest.get('topics', [])
    if topics:
        html_parts.append("<b>🎯 Основные темы:</b>")
        html_parts.append("")
        for i, topic in enumerate(topics, 1):
            html_parts.append(f"<b>{i}.</b> {escape(topic)}")
        html_parts.append("")
    
    # Спикеры
    speakers = digest.get('speakers_summary', {})
    if speakers:
        html_parts.append("<b>👥 Активные участники:</b>")
        html_parts.append("")
        for username, summary in speakers.items():
            # Создаем кликабельную ссылку на username
            # Проверяем, что username не содержит пробелов (значит это username, а не first_name)
            if ' ' not in username and len(username) > 0:
                # Это username - создаем кликабельную ссылку
                username_link = f'<a href="tg://resolve?domain={escape(username)}">@{escape(username)}</a>'
                html_parts.append(f"• {username_link}: {escape(summary)}")
            else:
                # Это имя пользователя без username - просто текст
                html_parts.append(f"• <b>{escape(username)}</b>: {escape(summary)}")
        html_parts.append("")
    
    # Резюме в blockquote для лучшей читаемости
    overall = digest.get('overall_summary', '')
    if overall:
        html_parts.append("<b>📝 Резюме:</b>")
        html_parts.append("")
        # Если резюме длинное (>300 символов), используем expandable blockquote
        if len(overall) > 300:
            html_parts.append(f"<blockquote expandable>{escape(overall)}</blockquote>")
        else:
            html_parts.append(f"<blockquote>{escape(overall)}</blockquote>")
    
    return "\n".join(html_parts)


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
        HTML форматированное уведомление для Telegram
    """
    html_parts = []
    
    # Urgency индикатор
    urgency = analysis.get('urgency', 'normal')
    urgency_emoji = {
        'urgent': '🔴',
        'important': '🟡',
        'normal': '🟢'
    }.get(urgency, '🟢')
    
    # Заголовок
    html_parts.append(f"{urgency_emoji} <b>Упоминание в группе</b>")
    html_parts.append("")
    html_parts.append(f"<b>Группа:</b> {escape(group_title)}")
    html_parts.append("")
    
    # Контекст в blockquote для лучшей читаемости
    context = analysis.get('context', '')
    if context:
        html_parts.append("<b>Контекст:</b>")
        html_parts.append(f"<blockquote>{escape(context)}</blockquote>")
        html_parts.append("")
    
    # Причина упоминания
    reason = analysis.get('mention_reason', '')
    if reason:
        html_parts.append(f"<b>Почему упомянули:</b> <i>{escape(reason)}</i>")
        html_parts.append("")
    
    # Ключевые моменты
    key_points = analysis.get('key_points', [])
    if key_points:
        html_parts.append("<b>Ключевые моменты:</b>")
        for point in key_points:
            html_parts.append(f"• <i>{escape(point)}</i>")
        html_parts.append("")
    
    # Ссылка на сообщение
    if message_link:
        html_parts.append(f'<a href="{message_link}">📬 Перейти к сообщению</a>')
        html_parts.append("")
    
    # Футер с уровнем срочности и временем
    time_str = datetime.now().strftime('%H:%M')
    html_parts.append(f"<i>Срочность: {urgency.upper()} • {time_str}</i>")
    
    return "\n".join(html_parts)


def markdown_to_html(text: str) -> str:
    """
    Конвертация расширенного Markdown в HTML для Telegram
    
    Поддерживает:
    - ## Заголовки → <b>Заголовки</b>
    - **жирный** → <b>жирный</b>
    - *курсив* → <i>курсив</i>
    - `код` → <code>код</code>
    - ```python код``` → <pre><code class="language-python">код</code></pre>
    - > quote → <blockquote>quote</blockquote>
    - ||spoiler|| → <tg-spoiler>spoiler</tg-spoiler>
    - --- → ──────
    - Списки - → •
    
    Args:
        text: Текст с Markdown разметкой
        
    Returns:
        HTML форматированный текст для Telegram
    """
    if not text:
        return text
    
    # Шаг 1: Сохраняем уже существующие HTML теги
    html_tags = []
    def save_html_tag(match):
        html_tags.append(match.group(0))
        return f"\x00HTML_TAG_{len(html_tags)-1}\x00"
    
    # Сохраняем HTML ссылки, blockquote, code blocks, spoilers
    text = re.sub(r'<a\s+href="[^"]+">.*?</a>', save_html_tag, text, flags=re.DOTALL)
    text = re.sub(r'<blockquote(?:\s+expandable)?>.*?</blockquote>', save_html_tag, text, flags=re.DOTALL)
    text = re.sub(r'<pre>.*?</pre>', save_html_tag, text, flags=re.DOTALL)
    text = re.sub(r'<code>.*?</code>', save_html_tag, text, flags=re.DOTALL)
    text = re.sub(r'<tg-spoiler>.*?</tg-spoiler>', save_html_tag, text, flags=re.DOTALL)
    
    # Шаг 2: Обрабатываем code blocks с языком (```language\ncode\n```)
    code_blocks = []
    def save_code_block(match):
        language = match.group(1) or ''
        code = match.group(2)
        if language:
            formatted = f'<pre><code class="language-{language}">{escape(code)}</code></pre>'
        else:
            formatted = f'<pre>{escape(code)}</pre>'
        code_blocks.append(formatted)
        return f"\x00CODE_BLOCK_{len(code_blocks)-1}\x00"
    
    text = re.sub(r'```(\w+)?\n(.*?)```', save_code_block, text, flags=re.DOTALL)
    
    # Шаг 3: Обрабатываем blockquote (> текст)
    blockquotes = []
    def save_blockquote(match):
        lines = match.group(0).split('\n')
        content = '\n'.join(line.lstrip('> ').strip() for line in lines if line.strip().startswith('>'))
        # Рекурсивно обрабатываем содержимое blockquote
        formatted = f'<blockquote>{markdown_to_html(content)}</blockquote>'
        blockquotes.append(formatted)
        return f"\x00BLOCKQUOTE_{len(blockquotes)-1}\x00"
    
    text = re.sub(r'^>.*(?:\n>.*)*', save_blockquote, text, flags=re.MULTILINE)
    
    # Шаг 4: Экранируем HTML спецсимволы
    text = escape(text)
    
    # Шаг 5: Конвертируем Markdown разметку
    
    # Спойлеры ||текст|| → <tg-spoiler>текст</tg-spoiler>
    text = re.sub(r'\|\|(.+?)\|\|', r'<tg-spoiler>\1</tg-spoiler>', text)
    
    # Markdown ссылки [text](url) → <a href="url">text</a>
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', text)
    
    # Заголовки ## → <b>
    text = re.sub(r'###\s+(.+?)(?=\n|$)', r'<b>\1</b>', text)
    text = re.sub(r'##\s+(.+?)(?=\n|$)', r'<b>\1</b>', text)
    text = re.sub(r'#\s+(.+?)(?=\n|$)', r'<b>\1</b>', text)
    
    # Жирный **текст** → <b>текст</b>
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    
    # Курсив *текст* → <i>текст</i>
    text = re.sub(r'\*([^\*]+?)\*', r'<i>\1</i>', text)
    
    # Inline код `текст` → <code>текст</code>
    text = re.sub(r'`(.+?)`', r'<code>\1</code>', text)
    
    # Подчеркивание __текст__ → <u>текст</u>
    text = re.sub(r'__(.+?)__', r'<u>\1</u>', text)
    
    # Зачеркивание ~~текст~~ → <s>текст</s>
    text = re.sub(r'~~(.+?)~~', r'<s>\1</s>', text)
    
    # Разделители --- → ──────
    text = re.sub(r'^---+$', '──────────────', text, flags=re.MULTILINE)
    
    # Списки - → •
    text = re.sub(r'^\s*-\s+', lambda m: m.group(0).replace('-', '•'), text, flags=re.MULTILINE)
    
    # Шаг 6: Восстанавливаем сохраненные элементы
    for i, block in enumerate(code_blocks):
        text = text.replace(f"\x00CODE_BLOCK_{i}\x00", block)
    
    for i, quote in enumerate(blockquotes):
        text = text.replace(f"\x00BLOCKQUOTE_{i}\x00", quote)
    
    for i, tag in enumerate(html_tags):
        text = text.replace(f"\x00HTML_TAG_{i}\x00", tag)
    
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


def format_rag_answer(answer: str, sources: Optional[List[Dict[str, Any]]] = None) -> str:
    """
    Форматирует RAG ответ с источниками в expandable blockquote
    
    Args:
        answer: Основной ответ от RAG (может содержать Markdown)
        sources: Список источников с полями:
            - url: ссылка на пост
            - channel_username: имя канала
            - posted_at: дата поста (строка или datetime)
            - excerpt: краткая выдержка (опционально)
            
    Returns:
        HTML форматированный текст для Telegram
        
    Example:
        >>> answer = "Python - это **язык программирования**"
        >>> sources = [
        ...     {"url": "https://t.me/channel/123", "channel_username": "python_news", "posted_at": "2024-01-15"}
        ... ]
        >>> formatted = format_rag_answer(answer, sources)
    """
    # Основной ответ через markdown_to_html
    html = markdown_to_html(answer)
    
    # Добавляем источники в expandable blockquote
    if sources and len(sources) > 0:
        html += "\n\n<blockquote expandable>📚 <b>Источники:</b>\n"
        
        for i, src in enumerate(sources[:5], 1):  # Максимум 5 источников
            channel = escape(src.get('channel_username', 'Unknown'))
            url = src.get('url', '')
            
            # Форматируем дату
            posted_at = src.get('posted_at', '')
            if hasattr(posted_at, 'strftime'):
                date_str = posted_at.strftime('%d.%m.%Y')
            elif isinstance(posted_at, str):
                # Берем только дату из строки (обрезаем время)
                date_str = posted_at[:10] if len(posted_at) >= 10 else posted_at
            else:
                date_str = ''
            
            # Формируем строку источника
            if url:
                html += f'{i}. <a href="{url}">@{channel}</a>'
            else:
                html += f'{i}. @{channel}'
            
            if date_str:
                html += f' <i>({date_str})</i>'
            
            # Добавляем excerpt если есть
            excerpt = src.get('excerpt', '')
            if excerpt:
                # Ограничиваем длину excerpt
                if len(excerpt) > 100:
                    excerpt = excerpt[:100] + '...'
                html += f'\n   <code>{escape(excerpt)}</code>'
            
            html += '\n'
        
        html += "</blockquote>"
    
    return html


def format_long_digest(digest_text: str, max_visible: int = 500) -> str:
    """
    Форматирует длинный дайджест с expandable blockquote
    
    Если текст дайджеста превышает max_visible символов,
    видимая часть остается открытой, а остальное скрывается
    в expandable blockquote.
    
    Args:
        digest_text: Текст дайджеста (может содержать Markdown)
        max_visible: Максимальное количество символов в видимой части
        
    Returns:
        HTML форматированный текст для Telegram
        
    Example:
        >>> digest = "Очень длинный текст дайджеста..." * 100
        >>> formatted = format_long_digest(digest, max_visible=500)
    """
    if not digest_text:
        return ""
    
    # Если текст короткий, просто конвертируем
    if len(digest_text) <= max_visible:
        return markdown_to_html(digest_text)
    
    # Находим ближайший перенос строки или пробел для красивого разрыва
    break_point = max_visible
    
    # Ищем перенос строки в пределах ±50 символов от max_visible
    for offset in range(0, min(50, len(digest_text) - max_visible)):
        if digest_text[max_visible + offset] == '\n':
            break_point = max_visible + offset
            break
        if digest_text[max_visible - offset] == '\n':
            break_point = max_visible - offset
            break
    
    # Если не нашли перенос строки, ищем пробел
    if break_point == max_visible:
        for offset in range(0, min(50, len(digest_text) - max_visible)):
            if digest_text[max_visible + offset] == ' ':
                break_point = max_visible + offset
                break
            if digest_text[max_visible - offset] == ' ':
                break_point = max_visible - offset
                break
    
    # Разделяем текст
    visible = digest_text[:break_point].strip()
    hidden = digest_text[break_point:].strip()
    
    # Форматируем обе части
    html = markdown_to_html(visible)
    
    if hidden:
        html += f'\n\n<blockquote expandable>{markdown_to_html(hidden)}</blockquote>'
    
    return html

