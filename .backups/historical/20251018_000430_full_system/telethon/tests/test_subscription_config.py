"""
Тесты для subscription configuration
Проверка тарифных планов и лимитов
"""

import pytest
from subscription_config import (
    SUBSCRIPTION_TIERS,
    get_subscription_info,
    format_subscription_info
)


@pytest.mark.unit
class TestSubscriptionConfig:
    """Тесты для конфигурации подписок"""
    
    def test_subscription_tiers_structure(self):
        """Тест структуры SUBSCRIPTION_TIERS"""
        required_tiers = ['free', 'trial', 'basic', 'premium', 'enterprise']
        
        for tier in required_tiers:
            assert tier in SUBSCRIPTION_TIERS
            
            tier_config = SUBSCRIPTION_TIERS[tier]
            
            # Проверяем обязательные поля
            assert 'name' in tier_config
            assert 'max_channels' in tier_config
            assert 'max_posts_per_day' in tier_config
            assert 'rag_queries_per_day' in tier_config
            assert 'ai_digest' in tier_config
            assert 'max_groups' in tier_config
    
    def test_subscription_limits_progression(self):
        """Тест что лимиты увеличиваются с tier"""
        free = SUBSCRIPTION_TIERS['free']
        premium = SUBSCRIPTION_TIERS['premium']
        enterprise = SUBSCRIPTION_TIERS['enterprise']
        
        # Каналы
        assert free['max_channels'] < premium['max_channels']
        assert premium['max_channels'] < enterprise['max_channels']
        
        # RAG запросы
        assert free['rag_queries_per_day'] < premium['rag_queries_per_day']
        assert premium['rag_queries_per_day'] < enterprise['rag_queries_per_day']
        
        # Группы
        assert free['max_groups'] < premium['max_groups']
    
    def test_voice_transcription_premium_only(self):
        """Тест что голосовые команды только для Premium/Enterprise"""
        free = SUBSCRIPTION_TIERS['free']
        basic = SUBSCRIPTION_TIERS['basic']
        premium = SUBSCRIPTION_TIERS['premium']
        enterprise = SUBSCRIPTION_TIERS['enterprise']
        
        assert free['voice_transcription_enabled'] is False
        assert basic['voice_transcription_enabled'] is False
        assert premium['voice_transcription_enabled'] is True
        assert enterprise['voice_transcription_enabled'] is True
    
    def test_get_subscription_info(self):
        """Тест helper функции get_subscription_info()"""
        info = get_subscription_info('premium')
        
        assert info is not None
        assert info['name'] == 'Premium'
        assert info['max_channels'] > 0
        
        # Несуществующий tier возвращает free
        default_info = get_subscription_info('nonexistent')
        assert default_info == SUBSCRIPTION_TIERS['free']
    
    def test_format_subscription_info(self):
        """Тест форматирования информации о подписке"""
        formatted = format_subscription_info('premium')
        
        assert 'Premium' in formatted
        assert 'Каналов' in formatted
        assert 'RAG запросов' in formatted

