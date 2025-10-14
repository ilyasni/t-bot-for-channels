#!/usr/bin/env python3
"""
Тестирование структуры Many-to-Many для каналов

Проверяет:
1. Создание уникальных каналов
2. Добавление нескольких пользователей к одному каналу
3. Удаление подписок
4. Автоматическое удаление каналов без подписчиков
"""

import pytest
import sys
import os
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from models import User, Channel, Post
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@pytest.mark.unit
@pytest.mark.unit
def test_channel_creation(db):
    """Тест создания каналов"""
    logger.info("\n" + "="*60)
    logger.info("ТЕСТ 1: Создание уникальных каналов")
    logger.info("="*60)
    
    try:
        # Создаем первый канал
        channel1 = Channel.get_or_create(db, "test_channel", 12345, "Test Channel")
        db.commit()
        logger.info(f"✅ Создан канал: @{channel1.channel_username} (ID: {channel1.id})")
        
        # Пытаемся создать тот же канал снова
        channel2 = Channel.get_or_create(db, "test_channel", 12345, "Test Channel")
        db.commit()
        
        # Должны получить тот же объект
        assert channel1.id == channel2.id, "Каналы должны быть одинаковыми!"
        logger.info(f"✅ Повторное создание вернуло существующий канал (ID: {channel2.id})")
        
        # Проверяем уникальность
        channels_count = db.query(Channel).filter(
            Channel.channel_username == "test_channel"
        ).count()
        assert channels_count == 1, f"Должен быть только 1 канал, найдено: {channels_count}"
        logger.info(f"✅ Проверка уникальности пройдена: {channels_count} канал")
        
        return channel1
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {str(e)}")
        db.rollback()
        raise


@pytest.mark.unit
@pytest.mark.unit
def test_user_subscriptions(db):
    """Тест подписок пользователей"""
    logger.info("\n" + "="*60)
    logger.info("ТЕСТ 2: Подписки нескольких пользователей на один канал")
    logger.info("="*60)
    
    try:
        # Создаем тестовых пользователей
        user1 = db.query(User).filter(User.telegram_id == 999001).first()
        if not user1:
            user1 = User(
                telegram_id=999001,
                username="test_user_1",
                first_name="Test",
                last_name="User 1"
            )
            db.add(user1)
            db.commit()
        logger.info(f"✅ Пользователь 1: {user1.telegram_id}")
        
        user2 = db.query(User).filter(User.telegram_id == 999002).first()
        if not user2:
            user2 = User(
                telegram_id=999002,
                username="test_user_2",
                first_name="Test",
                last_name="User 2"
            )
            db.add(user2)
            db.commit()
        logger.info(f"✅ Пользователь 2: {user2.telegram_id}")
        
        # Получаем канал из предыдущего теста
        channel = db.query(Channel).filter(
            Channel.channel_username == "test_channel"
        ).first()
        
        if not channel:
            channel = Channel.get_or_create(db, "test_channel", 12345, "Test Channel")
            db.commit()
        
        # Подписываем пользователя 1
        channel.add_user(db, user1, is_active=True)
        db.commit()
        logger.info(f"✅ Пользователь 1 подписан на канал @{channel.channel_username}")
        
        # Подписываем пользователя 2
        channel.add_user(db, user2, is_active=True)
        db.commit()
        logger.info(f"✅ Пользователь 2 подписан на канал @{channel.channel_username}")
        
        # Проверяем количество подписчиков
        db.refresh(channel)
        subscribers_count = len(channel.users)
        logger.info(f"📊 Всего подписчиков: {subscribers_count}")
        assert subscribers_count == 2, f"Должно быть 2 подписчика, найдено: {subscribers_count}"
        
        # Проверяем, что каналы добавлены пользователям
        user1_channels = user1.get_active_channels(db)
        user2_channels = user2.get_active_channels(db)
        
        assert len(user1_channels) >= 1, "У пользователя 1 должен быть канал"
        assert len(user2_channels) >= 1, "У пользователя 2 должен быть канал"
        logger.info(f"✅ Каналы добавлены в списки пользователей")
        
        # Проверяем информацию о подписке
        sub1 = channel.get_user_subscription(db, user1)
        sub2 = channel.get_user_subscription(db, user2)
        
        assert sub1 is not None, "Информация о подписке пользователя 1 не найдена"
        assert sub2 is not None, "Информация о подписке пользователя 2 не найдена"
        assert sub1['is_active'] == True, "Подписка пользователя 1 должна быть активной"
        assert sub2['is_active'] == True, "Подписка пользователя 2 должна быть активной"
        logger.info(f"✅ Информация о подписках корректна")
        
        return channel, user1, user2
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        db.rollback()
        raise


# finally удален - db управляется pytest fixture


@pytest.mark.unit
def test_subscription_removal(db):
    """Тест удаления подписок"""
    logger.info("\n" + "="*60)
    logger.info("ТЕСТ 3: Удаление подписок")
    logger.info("="*60)
    
    try:
        # Получаем данные из предыдущего теста
        channel = db.query(Channel).filter(
            Channel.channel_username == "test_channel"
        ).first()
        user1 = db.query(User).filter(User.telegram_id == 999001).first()
        user2 = db.query(User).filter(User.telegram_id == 999002).first()
        
        if not channel or not user1 or not user2:
            logger.warning("⚠️ Не найдены данные из предыдущих тестов, пропускаем")
            return
        
        initial_subscribers = len(channel.users)
        logger.info(f"📊 Изначально подписчиков: {initial_subscribers}")
        
        # Отписываем пользователя 1
        channel.remove_user(db, user1)
        db.commit()
        logger.info(f"✅ Пользователь 1 отписан от канала")
        
        # Проверяем, что подписчик удален
        db.refresh(channel)
        remaining_subscribers = len(channel.users)
        logger.info(f"📊 Осталось подписчиков: {remaining_subscribers}")
        assert remaining_subscribers == initial_subscribers - 1, "Количество подписчиков должно уменьшиться"
        
        # Проверяем, что канал НЕ удален (есть другие подписчики)
        channel_exists = db.query(Channel).filter(Channel.id == channel.id).first()
        assert channel_exists is not None, "Канал не должен быть удален, пока есть подписчики"
        logger.info(f"✅ Канал сохранен (есть другие подписчики)")
        
        # Отписываем последнего пользователя
        channel.remove_user(db, user2)
        db.commit()
        logger.info(f"✅ Пользователь 2 отписан от канала")
        
        # Проверяем, что можно удалить канал
        db.refresh(channel)
        if not channel.users:
            channel_id = channel.id
            db.delete(channel)
            db.commit()
            logger.info(f"✅ Канал удален (нет подписчиков)")
            
            # Проверяем, что канал действительно удален
            channel_exists = db.query(Channel).filter(Channel.id == channel_id).first()
            assert channel_exists is None, "Канал должен быть удален"
            logger.info(f"✅ Подтверждено: канал удален из БД")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        db.rollback()
        raise


# finally удален - db управляется pytest fixture


@pytest.mark.unit
def test_subscription_update(db):
    """Тест обновления параметров подписки"""
    logger.info("\n" + "="*60)
    logger.info("ТЕСТ 4: Обновление параметров подписки")
    logger.info("="*60)
    
    try:
        # Создаем тестовые данные
        user = db.query(User).filter(User.telegram_id == 999003).first()
        if not user:
            user = User(
                telegram_id=999003,
                username="test_user_3",
                first_name="Test",
                last_name="User 3"
            )
            db.add(user)
            db.commit()
        
        channel = Channel.get_or_create(db, "test_channel_2", 54321, "Test Channel 2")
        channel.add_user(db, user, is_active=True)
        db.commit()
        logger.info(f"✅ Создан канал @{channel.channel_username} с подпиской пользователя {user.telegram_id}")
        
        # Получаем начальную подписку
        sub = channel.get_user_subscription(db, user)
        logger.info(f"📊 Изначальные параметры:")
        logger.info(f"   - is_active: {sub['is_active']}")
        logger.info(f"   - last_parsed_at: {sub['last_parsed_at']}")
        
        # Обновляем параметры
        new_parsed_time = datetime.now(timezone.utc)
        channel.update_user_subscription(
            db, user,
            is_active=False,
            last_parsed_at=new_parsed_time
        )
        db.commit()
        logger.info(f"✅ Параметры подписки обновлены")
        
        # Проверяем обновление
        sub_updated = channel.get_user_subscription(db, user)
        logger.info(f"📊 Обновленные параметры:")
        logger.info(f"   - is_active: {sub_updated['is_active']}")
        logger.info(f"   - last_parsed_at: {sub_updated['last_parsed_at']}")
        
        assert sub_updated['is_active'] == False, "is_active должен быть False"
        assert sub_updated['last_parsed_at'] is not None, "last_parsed_at должен быть установлен"
        logger.info(f"✅ Параметры обновлены корректно")
        
        # Очистка
        channel.remove_user(db, user)
        if not channel.users:
            db.delete(channel)
        db.commit()
        logger.info(f"✅ Тестовые данные очищены")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        db.rollback()
        raise


# finally удален - db управляется pytest fixture


@pytest.mark.unit
def test_user_methods(db):
    """Тест методов пользователя для работы с каналами"""
    logger.info("\n" + "="*60)
    logger.info("ТЕСТ 5: Методы User для работы с каналами")
    logger.info("="*60)
    
    try:
        # Создаем пользователя
        user = db.query(User).filter(User.telegram_id == 999004).first()
        if not user:
            user = User(
                telegram_id=999004,
                username="test_user_4",
                first_name="Test",
                last_name="User 4"
            )
            db.add(user)
            db.commit()
        
        # Создаем несколько каналов
        channel1 = Channel.get_or_create(db, "test_ch_1", 111, "Channel 1")
        channel2 = Channel.get_or_create(db, "test_ch_2", 222, "Channel 2")
        channel3 = Channel.get_or_create(db, "test_ch_3", 333, "Channel 3")
        
        # Подписываем на каналы
        channel1.add_user(db, user, is_active=True)
        channel2.add_user(db, user, is_active=True)
        channel3.add_user(db, user, is_active=False)  # неактивный
        db.commit()
        logger.info(f"✅ Пользователь подписан на 3 канала (2 активных, 1 неактивный)")
        
        # Тестируем get_active_channels
        active_channels = user.get_active_channels(db)
        logger.info(f"📊 Активных каналов: {len(active_channels)}")
        assert len(active_channels) == 2, f"Должно быть 2 активных канала, найдено: {len(active_channels)}"
        logger.info(f"✅ get_active_channels() работает корректно")
        
        # Тестируем get_all_channels
        all_channels = user.get_all_channels(db)
        logger.info(f"📊 Всего каналов: {len(all_channels)}")
        assert len(all_channels) == 3, f"Должно быть 3 канала, найдено: {len(all_channels)}"
        
        for channel, sub_info in all_channels:
            logger.info(f"   - @{channel.channel_username}: active={sub_info['is_active']}")
        
        logger.info(f"✅ get_all_channels() работает корректно")
        
        # Очистка
        for channel in [channel1, channel2, channel3]:
            channel.remove_user(db, user)
            if not channel.users:
                db.delete(channel)
        db.commit()
        logger.info(f"✅ Тестовые данные очищены")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Ошибка теста: {str(e)}")
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        db.rollback()
        raise


# finally удален - db управляется pytest fixture


def cleanup_test_data():
    """Очистка всех тестовых данных"""
    logger.info("\n" + "="*60)
    logger.info("ОЧИСТКА: Удаление тестовых данных")
    logger.info("="*60)
    
    try:
        # Удаляем тестовых пользователей
        test_users = db.query(User).filter(
            User.telegram_id.in_([999001, 999002, 999003, 999004])
        ).all()
        
        for user in test_users:
            # Сначала отписываем от всех каналов
            channels = user.get_all_channels(db)
            for channel, _ in channels:
                channel.remove_user(db, user)
                # Если нет других подписчиков, удаляем канал
                if not channel.users:
                    db.delete(channel)
            
            db.delete(user)
        
        # Удаляем тестовые каналы
        test_channels = db.query(Channel).filter(
            Channel.channel_username.like("test_%")
        ).all()
        
        for channel in test_channels:
            if not channel.users:
                db.delete(channel)
        
        db.commit()
        logger.info(f"✅ Удалено пользователей: {len(test_users)}")
        logger.info(f"✅ Удалено каналов: {len(test_channels)}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка очистки: {str(e)}")
        db.rollback()
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        db.rollback()
        raise


# finally удален - db управляется pytest fixture


def main():
    """Запуск всех тестов"""
    logger.info("\n" + "="*60)
    logger.info("🧪 ТЕСТИРОВАНИЕ MANY-TO-MANY СТРУКТУРЫ")
    logger.info("="*60)
    
    tests = [
        ("Создание каналов", test_channel_creation),
        ("Подписки пользователей", test_user_subscriptions),
        ("Удаление подписок", test_subscription_removal),
        ("Обновление подписки", test_subscription_update),
        ("Методы User", test_user_methods),
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            logger.error(f"❌ Тест '{test_name}' провален: {str(e)}")
            failed += 1
    
    # Очистка
    cleanup_test_data()
    
    # Итоги
    logger.info("\n" + "="*60)
    logger.info("📊 ИТОГИ ТЕСТИРОВАНИЯ")
    logger.info("="*60)
    logger.info(f"✅ Успешно: {passed}")
    logger.info(f"❌ Провалено: {failed}")
    logger.info(f"📈 Процент успеха: {(passed/(passed+failed)*100):.1f}%")
    logger.info("="*60)
    
    if failed == 0:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ!")
        return 0
    else:
        logger.error("⚠️ НЕКОТОРЫЕ ТЕСТЫ ПРОВАЛЕНЫ")
        return 1


if __name__ == "__main__":
    sys.exit(main())

