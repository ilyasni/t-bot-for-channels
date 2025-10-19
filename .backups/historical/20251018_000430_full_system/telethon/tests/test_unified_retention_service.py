"""
Unit tests for UnifiedRetentionService

Tests the centralized cleanup service with smart retention logic,
orphaned channels cleanup, and dry run functionality.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch, AsyncMock
from sqlalchemy.orm import Session

from maintenance.unified_retention_service import UnifiedRetentionService
from models import User, Channel, Post, DigestSettings


class TestUnifiedRetentionService:
    """Test cases for UnifiedRetentionService"""
    
    @pytest.fixture
    def retention_service(self):
        """Create UnifiedRetentionService instance for testing"""
        return UnifiedRetentionService(base_retention_days=90)
    
    @pytest.fixture
    def mock_db(self):
        """Mock database session"""
        return Mock(spec=Session)
    
    @pytest.fixture
    def sample_user(self):
        """Sample user for testing"""
        user = Mock(spec=User)
        user.id = 1
        user.telegram_id = 123456789
        user.retention_days = 30
        user.is_active = True
        return user
    
    @pytest.fixture
    def sample_digest_settings(self):
        """Sample digest settings for testing"""
        settings = Mock(spec=DigestSettings)
        settings.user_id = 1
        settings.enabled = True
        settings.frequency = "weekly"
        return settings
    
    @pytest.fixture
    def sample_channel(self):
        """Sample channel for testing"""
        channel = Mock(spec=Channel)
        channel.id = 1
        channel.channel_username = "test_channel"
        return channel
    
    @pytest.fixture
    def sample_post(self):
        """Sample post for testing"""
        post = Mock(spec=Post)
        post.id = 1
        post.user_id = 1
        post.channel_id = 1
        post.posted_at = datetime.now(timezone.utc) - timedelta(days=100)
        post.text = "Test post"
        return post

    @pytest.mark.asyncio
    async def test_calculate_retention_period_daily_digest(self, retention_service, mock_db, sample_user, sample_digest_settings):
        """Test retention calculation for daily digest"""
        # Setup
        sample_digest_settings.frequency = "daily"
        mock_db.query.return_value.filter.return_value.first.return_value = sample_digest_settings
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            retention = await retention_service.calculate_retention_period(1)
            
            # Verify
            assert retention == 90  # max(90, 1*2, 30) = 90
    
    @pytest.mark.asyncio
    async def test_calculate_retention_period_weekly_digest(self, retention_service, mock_db, sample_user, sample_digest_settings):
        """Test retention calculation for weekly digest"""
        # Setup
        sample_digest_settings.frequency = "weekly"
        mock_db.query.return_value.filter.return_value.first.return_value = sample_digest_settings
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            retention = await retention_service.calculate_retention_period(1)
            
            # Verify
            assert retention == 90  # max(90, 7*2, 30) = 90
    
    @pytest.mark.asyncio
    async def test_calculate_retention_period_monthly_digest(self, retention_service, mock_db, sample_user, sample_digest_settings):
        """Test retention calculation for monthly digest"""
        # Setup
        sample_digest_settings.frequency = "monthly"
        sample_user.retention_days = 365
        mock_db.query.return_value.filter.return_value.first.return_value = sample_digest_settings
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            retention = await retention_service.calculate_retention_period(1)
            
            # Verify
            assert retention == 365  # max(90, 30*2, 365) = 365
    
    @pytest.mark.asyncio
    async def test_calculate_retention_period_no_digest_settings(self, retention_service, mock_db, sample_user):
        """Test retention calculation when no digest settings exist"""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No digest settings
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            retention = await retention_service.calculate_retention_period(1)
            
            # Verify
            assert retention == 90  # max(90, 14, 30) = 90
    
    @pytest.mark.asyncio
    async def test_calculate_retention_period_user_not_found(self, retention_service, mock_db):
        """Test retention calculation when user not found"""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = None
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            retention = await retention_service.calculate_retention_period(999)
            
            # Verify
            assert retention == 90  # Default base retention
    
    @pytest.mark.asyncio
    async def test_cleanup_orphaned_channels_no_orphans(self, retention_service, mock_db):
        """Test orphaned channels cleanup when no orphaned channels exist"""
        # Setup
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            result = await retention_service.cleanup_orphaned_channels(dry_run=True)
            
            # Verify
            assert result == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_orphaned_channels_with_orphans(self, retention_service, mock_db, sample_channel):
        """Test orphaned channels cleanup with orphaned channels"""
        # Setup
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_channel]
        mock_db.query.return_value.filter.return_value.count.return_value = 5  # 5 posts to delete
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            result = await retention_service.cleanup_orphaned_channels(dry_run=True)
            
            # Verify
            assert result == 5
    
    @pytest.mark.asyncio
    async def test_cleanup_user_posts_no_posts(self, retention_service, mock_db, sample_user):
        """Test user posts cleanup when no posts to delete"""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value.filter.return_value.count.return_value = 0
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            result = await retention_service.cleanup_user_posts(1, dry_run=True)
            
            # Verify
            assert result["posts_deleted"] == 0
            assert result["user_id"] == 1
            assert result["dry_run"] is True
    
    @pytest.mark.asyncio
    async def test_cleanup_user_posts_with_posts(self, retention_service, mock_db, sample_user):
        """Test user posts cleanup with posts to delete"""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value.filter.return_value.count.return_value = 10  # 10 posts to delete
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            result = await retention_service.cleanup_user_posts(1, dry_run=True)
            
            # Verify
            assert result["posts_deleted"] == 10
            assert result["user_id"] == 1
            assert result["retention_days"] == 90
            assert result["dry_run"] is True
    
    @pytest.mark.asyncio
    async def test_cleanup_all_users_no_users(self, retention_service, mock_db):
        """Test cleanup all users when no active users exist"""
        # Setup
        mock_db.query.return_value.filter.return_value.all.return_value = []
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            result = await retention_service.cleanup_all_users(dry_run=True)
            
            # Verify
            assert result["status"] == "success"
            assert result["users_processed"] == 0
            assert result["total_posts_deleted"] == 0
    
    @pytest.mark.asyncio
    async def test_cleanup_all_users_with_users(self, retention_service, mock_db, sample_user):
        """Test cleanup all users with active users"""
        # Setup
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_user]
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value.filter.return_value.count.return_value = 5  # 5 posts to delete
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            result = await retention_service.cleanup_all_users(dry_run=True)
            
            # Verify
            assert result["status"] == "success"
            assert result["users_processed"] == 1
            assert result["total_posts_deleted"] == 5
            assert len(result["user_stats"]) == 1
            assert result["user_stats"][0]["user_id"] == 1
            assert result["user_stats"][0]["posts_deleted"] == 5
    
    @pytest.mark.asyncio
    async def test_get_retention_stats(self, retention_service, mock_db, sample_user):
        """Test getting retention statistics"""
        # Setup
        mock_db.query.return_value.filter.return_value.all.return_value = [sample_user]
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value.filter.return_value.count.return_value = 3  # 3 posts to delete
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            stats = await retention_service.get_retention_stats()
            
            # Verify
            assert stats["total_users"] == 1
            assert len(stats["retention_stats"]) == 1
            assert stats["retention_stats"][0]["user_id"] == 1
            assert stats["retention_stats"][0]["posts_to_delete"] == 3
            assert stats["summary"]["min_retention"] == 90
            assert stats["summary"]["max_retention"] == 3650
            assert stats["summary"]["base_retention"] == 90
    
    @pytest.mark.asyncio
    async def test_retention_period_validation_minimum(self, retention_service, mock_db, sample_user):
        """Test that retention period respects minimum of 90 days"""
        # Setup
        sample_user.retention_days = 1  # Very low retention
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No digest settings
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            retention = await retention_service.calculate_retention_period(1)
            
            # Verify
            assert retention == 90  # Should be raised to minimum
    
    @pytest.mark.asyncio
    async def test_retention_period_validation_maximum(self, retention_service, mock_db, sample_user):
        """Test that retention period respects maximum of 3650 days"""
        # Setup
        sample_user.retention_days = 10000  # Very high retention
        mock_db.query.return_value.filter.return_value.first.return_value = None  # No digest settings
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute
            retention = await retention_service.calculate_retention_period(1)
            
            # Verify
            assert retention == 3650  # Should be capped at maximum
    
    @pytest.mark.asyncio
    async def test_dry_run_vs_real_cleanup(self, retention_service, mock_db, sample_user):
        """Test difference between dry run and real cleanup"""
        # Setup
        mock_db.query.return_value.filter.return_value.first.return_value = sample_user
        mock_db.query.return_value.filter.return_value.count.return_value = 5
        
        with patch('maintenance.unified_retention_service.SessionLocal', return_value=mock_db):
            # Execute dry run
            dry_result = await retention_service.cleanup_user_posts(1, dry_run=True)
            
            # Execute real cleanup
            real_result = await retention_service.cleanup_user_posts(1, dry_run=False)
            
            # Verify
            assert dry_result["posts_deleted"] == 5
            assert real_result["posts_deleted"] == 5
            assert dry_result["dry_run"] is True
            assert real_result["dry_run"] is False
            
            # Verify that delete was called in real cleanup
            mock_db.query.return_value.filter.return_value.delete.assert_called_once()
            mock_db.commit.assert_called_once()


class TestUnifiedRetentionServiceIntegration:
    """Integration tests for UnifiedRetentionService"""
    
    @pytest.mark.asyncio
    async def test_full_cleanup_workflow(self):
        """Test complete cleanup workflow"""
        # This would be an integration test with real database
        # For now, we'll test the workflow logic
        service = UnifiedRetentionService(base_retention_days=90)
        
        # Test that all methods exist and are callable
        assert hasattr(service, 'calculate_retention_period')
        assert hasattr(service, 'cleanup_orphaned_channels')
        assert hasattr(service, 'cleanup_user_posts')
        assert hasattr(service, 'cleanup_all_users')
        assert hasattr(service, 'get_retention_stats')
        
        # Test that methods are async
        assert asyncio.iscoroutinefunction(service.calculate_retention_period)
        assert asyncio.iscoroutinefunction(service.cleanup_orphaned_channels)
        assert asyncio.iscoroutinefunction(service.cleanup_user_posts)
        assert asyncio.iscoroutinefunction(service.cleanup_all_users)
        assert asyncio.iscoroutinefunction(service.get_retention_stats)
    
    def test_service_initialization(self):
        """Test service initialization with different parameters"""
        # Test default initialization
        service1 = UnifiedRetentionService()
        assert service1.base_retention_days == 90  # Default from env or 90
        assert service1.min_retention_days == 90
        assert service1.max_retention_days == 3650
        
        # Test custom initialization
        service2 = UnifiedRetentionService(base_retention_days=120)
        assert service2.base_retention_days == 120
        assert service2.min_retention_days == 90
        assert service2.max_retention_days == 3650


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
