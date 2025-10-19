"""
Тесты для telegram_formatter модуля

Проверяет корректность конвертации Markdown → HTML для Telegram Bot API
"""
import pytest
from telegram_formatter import (
    format_digest_for_telegram,
    format_mention_for_telegram,
    markdownify,
    markdown_to_html,
    format_rag_answer,
    format_long_digest
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


class TestAdvancedHTML:
    """Тесты расширенных HTML возможностей Telegram"""
    
    def test_blockquote(self):
        """Тест конвертации цитат"""
        text = "> Это цитата\n> Многострочная цитата"
        result = markdown_to_html(text)
        
        assert '<blockquote>' in result
        assert '</blockquote>' in result
        assert 'Это цитата' in result
        
    def test_spoiler(self):
        """Тест спойлеров"""
        text = "Текст ||спойлер|| еще текст"
        result = markdown_to_html(text)
        
        assert '<tg-spoiler>спойлер</tg-spoiler>' in result
        
    def test_code_block_with_language(self):
        """Тест code block с указанием языка"""
        text = """```python
def hello():
    print('world')
```"""
        result = markdown_to_html(text)
        
        assert '<pre><code class="language-python">' in result
        assert 'def hello():' in result
        assert '</code></pre>' in result
        
    def test_code_block_without_language(self):
        """Тест code block без языка"""
        text = """```
code here
```"""
        result = markdown_to_html(text)
        
        assert '<pre>' in result
        assert 'code here' in result
        assert '</pre>' in result
        
    def test_underline(self):
        """Тест подчеркивания"""
        text = "__подчеркнутый__ текст"
        result = markdown_to_html(text)
        
        assert '<u>подчеркнутый</u>' in result
        
    def test_strikethrough(self):
        """Тест зачеркивания"""
        text = "~~зачеркнутый~~ текст"
        result = markdown_to_html(text)
        
        assert '<s>зачеркнутый</s>' in result
        
    def test_nested_formatting(self):
        """Тест вложенного форматирования"""
        text = "**жирный *курсив* жирный**"
        result = markdown_to_html(text)
        
        # Должен сохранить вложенность
        assert '<b>' in result
        assert '<i>' in result


class TestFormatRAGAnswer:
    """Тесты функции format_rag_answer"""
    
    def test_answer_without_sources(self):
        """RAG ответ без источников"""
        answer = "Python - это **язык программирования**"
        result = format_rag_answer(answer, None)
        
        assert '<b>язык программирования</b>' in result
        assert 'blockquote' not in result
        
    def test_answer_with_sources(self):
        """RAG ответ с источниками"""
        answer = "Python is great"
        sources = [
            {
                'url': 'https://t.me/channel/123',
                'channel_username': 'python_news',
                'posted_at': '2024-01-15'
            }
        ]
        result = format_rag_answer(answer, sources)
        
        assert 'Python is great' in result
        assert '<blockquote expandable>' in result
        assert '📚' in result
        assert '<b>Источники:</b>' in result
        assert '@python_news' in result
        assert '2024-01-15' in result
        
    def test_answer_with_multiple_sources(self):
        """RAG ответ с несколькими источниками"""
        answer = "Answer"
        sources = [
            {'url': f'https://t.me/ch/{i}', 'channel_username': f'ch{i}', 'posted_at': '2024-01-01'}
            for i in range(10)
        ]
        result = format_rag_answer(answer, sources)
        
        # Должно быть максимум 5 источников
        assert result.count('<a href=') <= 5
        
    def test_answer_with_excerpt(self):
        """RAG ответ с excerpt в источниках"""
        answer = "Test"
        sources = [{
            'url': 'https://t.me/ch/1',
            'channel_username': 'test',
            'posted_at': '2024-01-01',
            'excerpt': 'Краткая выдержка из поста'
        }]
        result = format_rag_answer(answer, sources)
        
        assert '<code>' in result
        assert 'Краткая выдержка' in result


class TestFormatLongDigest:
    """Тесты функции format_long_digest"""
    
    def test_short_digest(self):
        """Короткий дайджест без expandable"""
        text = "Короткий текст дайджеста"
        result = format_long_digest(text, max_visible=500)
        
        assert 'Короткий текст' in result
        assert 'blockquote' not in result
        
    def test_long_digest(self):
        """Длинный дайджест с expandable"""
        text = "Начало дайджеста. " + "Средняя часть. " * 50 + "Конец дайджеста."
        result = format_long_digest(text, max_visible=100)
        
        assert 'Начало дайджеста' in result
        assert '<blockquote expandable>' in result
        assert '</blockquote>' in result
        
    def test_digest_break_at_newline(self):
        """Разрыв на переносе строки"""
        text = "First part.\n" * 10 + "Second part.\n" * 10
        result = format_long_digest(text, max_visible=60)
        
        # Должен разорвать по переносу строки
        assert '<blockquote expandable>' in result
        
    def test_empty_digest(self):
        """Пустой дайджест"""
        result = format_long_digest("", max_visible=100)
        assert result == ""


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
        
    def test_digest_uses_html(self):
        """Проверка что дайджест использует HTML теги"""
        digest = {
            'period': 'test',
            'message_count': 5,
            'topics': ['Topic1'],
            'speakers_summary': {'user': 'Summary'},
            'overall_summary': 'Overall'
        }
        
        result = format_digest_for_telegram(digest, "Test")
        
        # Должен использовать HTML, а не Markdown
        assert '<b>' in result
        assert '<i>' in result
        assert '**' not in result  # Не должно быть Markdown разметки
        
    def test_mention_uses_blockquote(self):
        """Проверка что упоминания используют blockquote для контекста"""
        analysis = {
            'urgency': 'normal',
            'context': 'Some important context',
            'mention_reason': 'reason',
            'key_points': ['point1']
        }
        
        result = format_mention_for_telegram(analysis, "Test")
        
        # Контекст должен быть в blockquote
        assert '<blockquote>' in result
        assert 'important context' in result

