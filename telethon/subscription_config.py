"""
Конфигурация тарифов подписок
"""

SUBSCRIPTION_TIERS = {
    "free": {
        "name": "Free",
        "max_channels": 3,
        "max_posts_per_day": 100,
        "rag_queries_per_day": 10,
        "ai_digest": False,
        "priority_parsing": False,
        "price_rub": 0,
        "price_usd": 0,
        "description": "Базовый функционал для начала работы"
    },
    "trial": {
        "name": "Trial (7 дней)",
        "max_channels": 10,
        "max_posts_per_day": 500,
        "rag_queries_per_day": 50,
        "ai_digest": True,
        "priority_parsing": True,
        "price_rub": 0,
        "price_usd": 0,
        "duration_days": 7,
        "description": "Пробный период с полным доступом"
    },
    "basic": {
        "name": "Basic",
        "max_channels": 10,
        "max_posts_per_day": 500,
        "rag_queries_per_day": 50,
        "ai_digest": True,
        "priority_parsing": False,
        "price_rub": 500,
        "price_usd": 5,
        "duration_days": 30,
        "description": "Для личного использования"
    },
    "premium": {
        "name": "Premium",
        "max_channels": 50,
        "max_posts_per_day": 2000,
        "rag_queries_per_day": 200,
        "ai_digest": True,
        "priority_parsing": True,
        "price_rub": 1500,
        "price_usd": 15,
        "duration_days": 30,
        "description": "Для профессионалов и команд"
    },
    "enterprise": {
        "name": "Enterprise",
        "max_channels": 999,
        "max_posts_per_day": 99999,
        "rag_queries_per_day": 999,
        "ai_digest": True,
        "priority_parsing": True,
        "price_rub": 5000,
        "price_usd": 50,
        "duration_days": 30,
        "description": "Без ограничений для бизнеса"
    }
}


def get_subscription_info(subscription_type: str) -> dict:
    """Получить информацию о подписке"""
    return SUBSCRIPTION_TIERS.get(subscription_type, SUBSCRIPTION_TIERS["free"])


def format_subscription_info(subscription_type: str) -> str:
    """Форматированное описание подписки для пользователя"""
    tier = get_subscription_info(subscription_type)
    
    text = f"🎯 **{tier['name']}**\n"
    text += f"📝 {tier['description']}\n\n"
    text += f"📊 **Возможности:**\n"
    text += f"• Каналов: {tier['max_channels']}\n"
    text += f"• Постов в день: {tier['max_posts_per_day']}\n"
    text += f"• RAG запросов в день: {tier['rag_queries_per_day']}\n"
    text += f"• AI-дайджесты: {'✅' if tier['ai_digest'] else '❌'}\n"
    text += f"• Приоритетный парсинг: {'✅' if tier['priority_parsing'] else '❌'}\n"
    
    if tier['price_rub'] > 0:
        text += f"\n💰 **Цена:** {tier['price_rub']}₽/месяц"
    
    return text

