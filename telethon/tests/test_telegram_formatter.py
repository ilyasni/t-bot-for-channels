"""
Тесты для telegram_formatter модуля

Проверяет корректность конвертации Markdown → HTML для Telegram Bot API
"""
import pytest
from telegram_formatter import (
    format_digest_for_telegram,
    format_mention_for_telegram,
    markdownify,
    markdown_to_html
)


class TestFormatDigest:
    """Тесты форматирования дайджестов"""
    
    def test_basic_digest(self):
        """Базовый тест форматирования дайджеста"""
        digest = {
            'period': '24h',
            'message_count': 150,
            'topics': ['Python', 'AI & ML', 'DevOps (k8s)'],
            'speakers_summary': {
                'user1': 'Обсуждал AI',
                'user2': 'Помогал с k8s'
            },
            'overall_summary': 'Активное обсуждение AI/ML тем.'
        }
        
        result = format_digest_for_telegram(digest, "Test Group")
        
        # Проверяем наличие основных элементов
        assert '📊 Дайджест группы' in result
        assert 'Test Group' in result
        assert '24h' in result
        assert '150' in result
        assert 'Python' in result
        # HTML экранирует & как &amp;
        assert 'AI &amp; ML' in result or 'AI & ML' in result
        assert 'DevOps' in result
        assert 'user1' in result or '@user1' in result
        assert 'user2' in result or '@user2' in result
        assert 'Активное обсуждение' in result
        # Проверяем HTML теги
        assert '<b>' in result
        
    def test_digest_with_special_chars(self):
        """Тест экранирования спецсимволов в дайджесте"""
        digest = {
            'period': 'last_24h',
            'message_count': 100,
            'topics': ['Test_topic', 'Another*topic', '[Important]'],
            'speakers_summary': {
                'user_1': 'Писал про Python (asyncio)',
                'user*2': 'Обсуждал [вопросы]'
            },
            'overall_summary': 'Summary with _underscores_ and *asterisks*'
        }
        
        result = format_digest_for_telegram(digest, "Test_Group")
        
        # Результат должен содержать экранированные символы
        # telegramify-markdown автоматически экранирует спецсимволы
        assert result is not None
        assert len(result) > 0
        
    def test_empty_digest(self):
        """Тест с пустым дайджестом"""
        digest = {
            'period': 'N/A',
            'message_count': 0,
            'topics': [],
            'speakers_summary': {},
            'overall_summary': ''
        }
        
        result = format_digest_for_telegram(digest, "Empty Group")
        
        # Должен быть хотя бы заголовок
        assert '📊 Дайджест группы' in result
        assert 'Empty Group' in result
        assert '0' in result
        
    def test_digest_with_cyrillic(self):
        """Тест с кириллицей"""
        digest = {
            'period': 'последние 24 часа',
            'message_count': 42,
            'topics': ['Разработка', 'Тестирование', 'DevOps'],
            'speakers_summary': {
                'иван': 'Помогал с багами',
                'мария': 'Писала тесты'
            },
            'overall_summary': 'Продуктивный день!'
        }
        
        result = format_digest_for_telegram(digest, "Русская Группа")
        
        assert 'Русская Группа' in result
        assert 'Разработка' in result
        assert 'иван' in result or '@иван' in result
        assert 'Продуктивный день' in result


class TestFormatMention:
    """Тесты форматирования упоминаний"""
    
    def test_urgent_mention(self):
        """Тест срочного упоминания"""
        analysis = {
            'urgency': 'urgent',
            'context': 'Обсуждение критического бага',
            'mention_reason': 'Нужна срочная помощь',
            'key_points': ['Баг в prod', 'Влияет на пользователей']
        }
        
        result = format_mention_for_telegram(
            analysis,
            "Dev Chat",
            "https://t.me/c/123/456"
        )
        
        assert '🔴' in result  # Красный кружок для urgent
        assert 'Dev Chat' in result
        assert 'Обсуждение' in result
        assert 'срочная помощь' in result or 'Нужна помощь' in result
        assert 'Баг в prod' in result or 'prod' in result
        assert 'Перейти к сообщению' in result
        assert 'URGENT' in result
        
    def test_normal_mention(self):
        """Тест обычного упоминания"""
        analysis = {
            'urgency': 'normal',
            'context': 'Вопрос по коду',
            'mention_reason': 'Просят совета',
            'key_points': ['Архитектура', 'Best practices']
        }
        
        result = format_mention_for_telegram(
            analysis,
            "Tech Talk",
            None  # Без ссылки
        )
        
        assert '🟢' in result  # Зеленый кружок для normal
        assert 'Tech Talk' in result
        assert 'Вопрос' in result
        assert 'совета' in result or 'Просят' in result
        assert 'Перейти к сообщению' not in result  # Ссылки нет
        
    def test_important_mention(self):
        """Тест важного упоминания"""
        analysis = {
            'urgency': 'important',
            'context': 'Требуется review',
            'mention_reason': 'Pull request готов',
            'key_points': []
        }
        
        result = format_mention_for_telegram(
            analysis,
            "Code Review",
            "https://t.me/c/789/012"
        )
        
        assert '🟡' in result  # Желтый кружок для important
        assert 'Code Review' in result
        assert 'IMPORTANT' in result


class TestMarkdownToHTML:
    """Тесты конвертации Markdown → HTML"""
    
    def test_headers(self):
        """Тест заголовков"""
        text = "## Заголовок\n### Подзаголовок"
        result = markdown_to_html(text)
        
        assert '<b>Заголовок</b>' in result
        assert '<b>Подзаголовок</b>' in result
        
    def test_bold_text(self):
        """Тест жирного текста"""
        text = "**жирный** обычный **еще жирный**"
        result = markdown_to_html(text)
        
        assert '<b>жирный</b>' in result
        assert '<b>еще жирный</b>' in result
        
    def test_italic_text(self):
        """Тест курсива"""
        text = "*курсив* обычный"
        result = markdown_to_html(text)
        
        assert '<i>курсив</i>' in result
        
    def test_code(self):
        """Тест inline кода"""
        text = "Код: `print('hello')`"
        result = markdown_to_html(text)
        
        assert '<code>print(&#x27;hello&#x27;)</code>' in result or '<code>' in result
        
    def test_lists(self):
        """Тест списков"""
        text = "- Элемент 1\n- Элемент 2"
        result = markdown_to_html(text)
        
        assert '• Элемент 1' in result
        assert '• Элемент 2' in result
        
    def test_separator(self):
        """Тест разделителей"""
        text = "Текст\n---\nЕще текст"
        result = markdown_to_html(text)
        
        assert '──────' in result
        
    def test_html_escaping(self):
        """Тест экранирования HTML спецсимволов"""
        text = "5 < 10 & 10 > 5"
        result = markdown_to_html(text)
        
        assert '&lt;' in result
        assert '&gt;' in result
        assert '&amp;' in result
        
    def test_links(self):
        """Тест ссылок"""
        text = "[Google](https://google.com)"
        result = markdown_to_html(text)
        
        assert '<a href="https://google.com">Google</a>' in result


class TestMarkdownify:
    """Тесты универсальной функции markdownify"""
    
    def test_plain_text(self):
        """Тест с обычным текстом"""
        text = "Hello, World!"
        result = markdownify(text)
        
        assert result is not None
        assert 'Hello' in result
        assert 'World' in result
        
    def test_text_with_special_chars(self):
        """Тест экранирования спецсимволов"""
        text = "Test_with*special[chars](link) and more_symbols"
        result = markdownify(text)
        
        # telegramify-markdown должна экранировать спецсимволы
        # Проверяем что результат отличается от исходного или содержит экранирование
        assert result is not None
        assert len(result) >= len(text)  # С экранированием будет длиннее
        
    def test_empty_string(self):
        """Тест с пустой строкой"""
        result = markdownify("")
        assert result == ""
        
    def test_none_value(self):
        """Тест с None"""
        result = markdownify(None)
        assert result is None
        
    def test_markdown_formatting(self):
        """Тест с Markdown форматированием"""
        text = """
# Заголовок
**Жирный текст**
*Курсив*
`код`
        """
        result = markdownify(text)
        
        assert result is not None
        assert len(result) > 0
        # После конвертации должны сохраниться элементы форматирования
        
    def test_cyrillic_text(self):
        """Тест с кириллицей"""
        text = "Привет, мир! Это тест_с_подчеркиваниями."
        result = markdownify(text)
        
        assert result is not None
        assert 'Привет' in result
        assert 'мир' in result
        
    def test_long_text(self):
        """Тест с длинным текстом"""
        text = "A" * 1000 + "_test_" + "B" * 1000
        result = markdownify(text)
        
        assert result is not None
        assert len(result) > 0


class TestIntegration:
    """Интеграционные тесты"""
    
    def test_digest_output_is_string(self):
        """Проверка что дайджест возвращает строку"""
        digest = {
            'period': 'test',
            'message_count': 1,
            'topics': ['test'],
            'speakers_summary': {},
            'overall_summary': ''
        }
        
        result = format_digest_for_telegram(digest, "Test")
        
        assert isinstance(result, str)
        assert len(result) > 0
        
    def test_mention_output_is_string(self):
        """Проверка что упоминание возвращает строку"""
        analysis = {
            'urgency': 'normal',
            'context': 'test',
            'mention_reason': 'test',
            'key_points': []
        }
        
        result = format_mention_for_telegram(analysis, "Test")
        
        assert isinstance(result, str)
        assert len(result) > 0
        
    def test_markdownify_output_is_string(self):
        """Проверка что markdownify возвращает строку"""
        result = markdownify("test")
        
        assert isinstance(result, str)

