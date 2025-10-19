"""
Тестовые данные для использования в тестах
Sample texts, structured data, etc.
"""

from datetime import datetime, timezone, timedelta


# ============================================================================
# Sample Texts
# ============================================================================

SAMPLE_POST_TEXTS = [
    """
    🚀 Революция в области искусственного интеллекта!
    
    Новая модель от OpenAI превосходит все существующие аналоги.
    Подробности в статье: https://example.com/ai-revolution
    
    #AI #технологии #инновации
    """,
    """
    💼 Блокчейн технологии продолжают развиваться
    
    Ethereum 2.0 показывает отличные результаты в тестовой сети.
    Скорость транзакций увеличилась в 100 раз!
    
    #блокчейн #ethereum #криптовалюты
    """,
    """
    🎮 Игровая индустрия переходит на новый уровень
    
    Виртуальная реальность становится доступнее с каждым днем.
    Новые VR гарнитуры стоят всего $299.
    
    #gaming #VR #технологии
    """,
    """
    📱 Обзор смартфонов 2025 года
    
    Топ-5 устройств по соотношению цена/качество.
    Все модели с поддержкой 5G и AI-камерой.
    
    #смартфоны #обзор #гаджеты
    """,
    """
    🌍 Экологические инициативы Tech компаний
    
    Apple, Google и Microsoft обязались достичь углеродной нейтральности к 2030 году.
    Инвестиции в зеленую энергетику превысили $10 млрд.
    
    #экология #технологии #будущее
    """
]


SAMPLE_CHANNEL_NAMES = [
    ("tech_news", "Tech News Channel"),
    ("ai_digest", "AI Digest"),
    ("blockchain_updates", "Blockchain Updates"),
    ("startup_weekly", "Startup Weekly"),
    ("science_daily", "Science Daily")
]


SAMPLE_GROUP_NAMES = [
    ("Tech Discussion", "tech_chat"),
    ("AI Researchers", None),  # Приватная группа без username
    ("Blockchain Community", "blockchain_group"),
    ("Startup Founders", None),
    ("Science Enthusiasts", "science_talk")
]


# ============================================================================
# Sample RAG Queries
# ============================================================================

SAMPLE_RAG_QUERIES = [
    "Что нового в области искусственного интеллекта?",
    "Расскажи про блокчейн технологии",
    "Какие новости про Tesla?",
    "Что писали о квантовых компьютерах?",
    "Обзор смартфонов в этом месяце"
]


# ============================================================================
# Sample Tags
# ============================================================================

SAMPLE_TAGS = [
    ["AI", "технологии", "инновации"],
    ["блокчейн", "криптовалюты", "финансы"],
    ["наука", "исследования", "открытия"],
    ["стартапы", "бизнес", "инвестиции"],
    ["гаджеты", "обзоры", "смартфоны"]
]


# ============================================================================
# Sample Embeddings
# ============================================================================

def generate_sample_embedding(dimension: int = 1024) -> list:
    """
    Генерировать фейковый embedding вектор
    GigaChat использует 1024-мерные векторы
    """
    import random
    return [random.uniform(-1.0, 1.0) for _ in range(dimension)]


# ============================================================================
# Sample API Responses
# ============================================================================

SAMPLE_GIGACHAT_EMBEDDING_RESPONSE = {
    "data": [{
        "embedding": generate_sample_embedding(1024),
        "index": 0
    }],
    "model": "EmbeddingsGigaR",
    "usage": {
        "prompt_tokens": 10,
        "total_tokens": 10
    }
}


SAMPLE_GIGACHAT_CHAT_RESPONSE = {
    "choices": [{
        "message": {
            "content": "Это тестовый ответ от GigaChat на ваш запрос о технологиях.",
            "role": "assistant"
        },
        "finish_reason": "stop",
        "index": 0
    }],
    "model": "GigaChat-Lite",
    "usage": {
        "prompt_tokens": 50,
        "completion_tokens": 20,
        "total_tokens": 70
    }
}


SAMPLE_OPENROUTER_RESPONSE = {
    "choices": [{
        "message": {
            "content": "This is a test response from OpenRouter.",
            "role": "assistant"
        },
        "finish_reason": "stop"
    }],
    "model": "google/gemini-2.0-flash-exp:free"
}


SAMPLE_SALUTESPEECH_TRANSCRIPTION = {
    "result": [{
        "normalized_text": "тестовая транскрипция голосового сообщения о технологиях",
        "confidence": 0.95,
        "words": [
            {"word": "тестовая", "start_time": 0.0, "end_time": 0.5},
            {"word": "транскрипция", "start_time": 0.5, "end_time": 1.0}
        ]
    }]
}


SAMPLE_N8N_GROUP_DIGEST = {
    "summary": "Обсуждались новые технологии в AI и блокчейне",
    "topics": [
        "Искусственный интеллект",
        "Блокчейн технологии",
        "Стартапы"
    ],
    "key_speakers": ["Alice", "Bob", "Charlie"],
    "message_count": 45,
    "time_period": "24 hours",
    "sentiment": "positive"
}


SAMPLE_N8N_MENTION_ANALYSIS = {
    "reason": "Пользователь запросил мнение о новой технологии",
    "context": "В группе обсуждали новый AI framework",
    "urgency": "medium",
    "sentiment": "neutral",
    "requires_response": True
}


SAMPLE_N8N_VOICE_CLASSIFICATION = {
    "command": "ask",
    "confidence": 0.85,
    "reasoning": "Detected question pattern in transcription",
    "alternative": "search"
}


# ============================================================================
# Sample Qdrant Responses
# ============================================================================

SAMPLE_QDRANT_SEARCH_RESULTS = [
    {
        "id": "post_1_chunk_0",
        "score": 0.95,
        "payload": {
            "post_id": 1,
            "user_id": 1,
            "channel_id": 1,
            "channel_username": "tech_news",
            "text": "Sample post about AI technology",
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "tags": ["AI", "технологии"],
            "url": "https://t.me/tech_news/1"
        }
    },
    {
        "id": "post_2_chunk_0",
        "score": 0.88,
        "payload": {
            "post_id": 2,
            "user_id": 1,
            "channel_id": 1,
            "channel_username": "tech_news",
            "text": "Another post about blockchain",
            "posted_at": (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(),
            "tags": ["блокчейн", "криптовалюты"],
            "url": "https://t.me/tech_news/2"
        }
    }
]


# ============================================================================
# Helper Functions
# ============================================================================

def create_sample_posts_with_dates(
    count: int = 10,
    start_date: datetime = None
) -> list:
    """
    Создать список sample постов с разными датами
    Полезно для тестирования retention и cleanup
    """
    if start_date is None:
        start_date = datetime.now(timezone.utc) - timedelta(days=count)
    
    posts = []
    for i in range(count):
        posts.append({
            'text': SAMPLE_POST_TEXTS[i % len(SAMPLE_POST_TEXTS)],
            'posted_at': start_date + timedelta(days=i),
            'telegram_message_id': i + 1,
            'tags': SAMPLE_TAGS[i % len(SAMPLE_TAGS)]
        })
    
    return posts

