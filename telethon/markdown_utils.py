"""
Утилиты для работы с Telegram Markdown
"""


def escape_markdown(text: str) -> str:
    """
    Экранирует спецсимволы Markdown для Telegram
    
    Args:
        text: Исходный текст
        
    Returns:
        Текст с экранированными спецсимволами
    """
    if not text:
        return text
    
    # Спецсимволы Telegram Markdown
    escape_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
    result = str(text)
    for char in escape_chars:
        result = result.replace(char, f'\\{char}')
    
    return result


def escape_markdown_v2(text: str) -> str:
    """
    Экранирует спецсимволы для MarkdownV2 (более строгий)
    
    Args:
        text: Исходный текст
        
    Returns:
        Текст с экранированными спецсимволами
    """
    if not text:
        return text
    
    # Все спецсимволы MarkdownV2
    special_chars = [
        '_', '*', '[', ']', '(', ')', '~', '`', '>', '#', 
        '+', '-', '=', '|', '{', '}', '.', '!'
    ]
    
    result = str(text)
    for char in special_chars:
        result = result.replace(char, f'\\{char}')
    
    return result


def escape_markdown_basic(text: str) -> str:
    """
    Экранирует только основные спецсимволы Markdown (для обратной совместимости)
    
    Args:
        text: Исходный текст
        
    Returns:
        Текст с экранированными основными спецсимволами
    """
    if not text:
        return text
    
    # Только основные: подчеркивание, звездочка, квадратные скобки, backtick
    result = str(text)
    result = result.replace('_', '\\_')
    result = result.replace('*', '\\*')
    result = result.replace('[', '\\[')
    result = result.replace('`', '\\`')
    
    return result

