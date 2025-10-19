#!/usr/bin/env python3
"""
Migration: Update retention_days to minimum 90 days

This script updates all users' retention_days to ensure minimum 90 days
for RAG/search functionality and digest generation.

Usage:
    python scripts/migrations/update_retention_days.py
"""

import os
import sys
import logging
from datetime import datetime, timezone

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from database import SessionLocal, engine
from models import User
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def update_retention_days():
    """Update retention_days for all users to minimum 90 days"""
    
    db = SessionLocal()
    try:
        logger.info("🔄 Starting retention_days migration...")
        
        # Check current state
        users_below_90 = db.query(User).filter(
            User.retention_days < 90
        ).count()
        
        total_users = db.query(User).count()
        
        logger.info(f"📊 Current state:")
        logger.info(f"   Total users: {total_users}")
        logger.info(f"   Users with retention_days < 90: {users_below_90}")
        
        if users_below_90 == 0:
            logger.info("✅ All users already have retention_days >= 90")
            return
        
        # Update retention_days using SQL for efficiency
        logger.info("🔄 Updating retention_days to minimum 90...")
        
        result = db.execute(text("""
            UPDATE users 
            SET retention_days = GREATEST(retention_days, 90)
            WHERE retention_days < 90
        """))
        
        db.commit()
        
        updated_count = result.rowcount
        logger.info(f"✅ Updated {updated_count} users")
        
        # Verify update
        users_below_90_after = db.query(User).filter(
            User.retention_days < 90
        ).count()
        
        logger.info(f"📊 After update:")
        logger.info(f"   Users with retention_days < 90: {users_below_90_after}")
        
        if users_below_90_after == 0:
            logger.info("✅ Migration completed successfully")
        else:
            logger.error(f"❌ Migration failed: {users_below_90_after} users still have retention_days < 90")
            
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def show_retention_stats():
    """Show current retention statistics"""
    
    db = SessionLocal()
    try:
        logger.info("📊 Current retention statistics:")
        
        # Get retention distribution
        stats = db.execute(text("""
            SELECT 
                CASE 
                    WHEN retention_days < 30 THEN '< 30 days'
                    WHEN retention_days < 60 THEN '30-59 days'
                    WHEN retention_days < 90 THEN '60-89 days'
                    WHEN retention_days < 120 THEN '90-119 days'
                    WHEN retention_days < 365 THEN '120-364 days'
                    ELSE '365+ days'
                END as retention_range,
                COUNT(*) as user_count
            FROM users 
            WHERE is_active = true
            GROUP BY 
                CASE 
                    WHEN retention_days < 30 THEN '< 30 days'
                    WHEN retention_days < 60 THEN '30-59 days'
                    WHEN retention_days < 90 THEN '60-89 days'
                    WHEN retention_days < 120 THEN '90-119 days'
                    WHEN retention_days < 365 THEN '120-364 days'
                    ELSE '365+ days'
                END
            ORDER BY MIN(retention_days)
        """)).fetchall()
        
        for row in stats:
            logger.info(f"   {row.retention_range}: {row.user_count} users")
            
    except Exception as e:
        logger.error(f"❌ Error getting stats: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    logger.info("=" * 60)
    logger.info("RETENTION DAYS MIGRATION")
    logger.info("=" * 60)
    
    # Show current stats
    show_retention_stats()
    
    # Update retention_days
    update_retention_days()
    
    # Show final stats
    logger.info("\n" + "=" * 60)
    logger.info("FINAL STATISTICS")
    logger.info("=" * 60)
    show_retention_stats()
    
    logger.info("\n✅ Migration completed!")
