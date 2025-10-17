"""
Unit tests для Dialogue Assessor Agent
"""

import pytest
from unittest.mock import Mock
from datetime import datetime, timezone

from langchain_agents.assessor import DialogueAssessorAgent


class TestDialogueAssessorAgent:
    """Тесты для Dialogue Assessor Agent"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.agent = DialogueAssessorAgent()
    
    def test_agent_initialization(self):
        """Тест инициализации агента"""
        assert self.agent.agent_name == "DialogueAssessor"
        assert self.agent.MICRO_THRESHOLD == 5
        assert self.agent.BRIEF_THRESHOLD == 15
        assert self.agent.STANDARD_THRESHOLD == 50
        assert self.agent.DETAILED_THRESHOLD == 100
    
    @pytest.mark.asyncio
    async def test_empty_messages(self):
        """Тест обработки пустых сообщений"""
        input_data = {
            "messages": [],
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["detail_level"] == "micro"
        assert result["dialogue_type"] == "announcement"
        assert result["message_count"] == 0
        assert result["participants"] == 0
        assert result["has_links"] == False
    
    @pytest.mark.asyncio
    async def test_micro_level_assessment(self):
        """Тест определения micro уровня детализации"""
        # Создаем mock сообщения
        messages = []
        for i in range(3):
            msg = Mock()
            msg.username = f"user{i}"
            msg.message = f"Message {i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["detail_level"] == "micro"
        assert result["message_count"] == 3
        assert result["participants"] == 3
    
    @pytest.mark.asyncio
    async def test_single_participant_assessment(self):
        """Тест определения micro для одного участника"""
        # Создаем mock сообщения от одного пользователя
        messages = []
        for i in range(10):  # Много сообщений, но один участник
            msg = Mock()
            msg.username = "single_user"
            msg.message = f"Message {i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["detail_level"] == "micro"
        assert result["participants"] == 1
    
    @pytest.mark.asyncio
    async def test_brief_level_assessment(self):
        """Тест определения brief уровня детализации"""
        # Создаем mock сообщения для brief уровня
        messages = []
        for i in range(10):  # 10 сообщений
            msg = Mock()
            msg.username = f"user{i % 3}"  # 3 участника
            msg.message = f"Message {i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["detail_level"] == "brief"
        assert result["message_count"] == 10
        assert result["participants"] == 3
    
    @pytest.mark.asyncio
    async def test_standard_level_assessment(self):
        """Тест определения standard уровня детализации"""
        # Создаем mock сообщения для standard уровня
        messages = []
        for i in range(30):  # 30 сообщений
            msg = Mock()
            msg.username = f"user{i % 5}"  # 5 участников
            msg.message = f"Message {i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["detail_level"] == "standard"
        assert result["message_count"] == 30
        assert result["participants"] == 5
    
    @pytest.mark.asyncio
    async def test_detailed_level_assessment(self):
        """Тест определения detailed уровня детализации"""
        # Создаем mock сообщения для detailed уровня
        messages = []
        for i in range(80):  # 80 сообщений
            msg = Mock()
            msg.username = f"user{i % 6}"  # 6 участников
            msg.message = f"Message {i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["detail_level"] == "detailed"
        assert result["message_count"] == 80
        assert result["participants"] == 6
    
    @pytest.mark.asyncio
    async def test_comprehensive_level_assessment(self):
        """Тест определения comprehensive уровня детализации"""
        # Создаем mock сообщения для comprehensive уровня
        messages = []
        for i in range(150):  # 150 сообщений
            msg = Mock()
            msg.username = f"user{i % 8}"  # 8 участников
            msg.message = f"Message {i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["detail_level"] == "comprehensive"
        assert result["message_count"] == 150
        assert result["participants"] == 8
    
    @pytest.mark.asyncio
    async def test_links_detection(self):
        """Тест обнаружения ссылок в сообщениях"""
        messages = []
        
        # Сообщение с HTTP ссылкой
        msg1 = Mock()
        msg1.username = "user1"
        msg1.message = "Check this: https://example.com"
        msg1.date = datetime.now(timezone.utc)
        messages.append(msg1)
        
        # Сообщение с Telegram ссылкой
        msg2 = Mock()
        msg2.username = "user2"
        msg2.message = "Join our channel: @channel_name"
        msg2.date = datetime.now(timezone.utc)
        messages.append(msg2)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["has_links"] == True
    
    @pytest.mark.asyncio
    async def test_no_links_detection(self):
        """Тест отсутствия ссылок в сообщениях"""
        messages = []
        
        # Сообщения без ссылок
        for i in range(5):
            msg = Mock()
            msg.username = f"user{i}"
            msg.message = f"Just regular message {i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["has_links"] == False
    
    @pytest.mark.asyncio
    async def test_dialogue_type_detection(self):
        """Тест определения типа диалога"""
        messages = []
        
        # Создаем диалог с вопросами и ответами
        msg1 = Mock()
        msg1.username = "user1"
        msg1.message = "Как дела?"
        msg1.date = datetime.now(timezone.utc)
        messages.append(msg1)
        
        msg2 = Mock()
        msg2.username = "user2"
        msg2.message = "Все хорошо, спасибо!"
        msg2.date = datetime.now(timezone.utc)
        messages.append(msg2)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["dialogue_type"] == "question_answer"
    
    @pytest.mark.asyncio
    async def test_time_span_calculation(self):
        """Тест расчета временного диапазона"""
        messages = []
        base_time = datetime.now(timezone.utc)
        
        # Сообщения с небольшим временным разбросом
        for i in range(3):
            msg = Mock()
            msg.username = f"user{i}"
            msg.message = f"Message {i}"
            msg.date = base_time
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert result["time_span"] == "burst"
    
    @pytest.mark.asyncio
    async def test_reasoning_generation(self):
        """Тест генерации обоснования"""
        messages = []
        for i in range(10):
            msg = Mock()
            msg.username = f"user{i % 3}"
            msg.message = f"Message {i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        input_data = {
            "messages": messages,
            "hours": 24,
            "user_id": 123
        }
        
        result = await self.agent.ainvoke(input_data)
        
        assert "assessment_reasoning" in result
        assert "Сообщений:" in result["assessment_reasoning"]
        assert "Участников:" in result["assessment_reasoning"]
    
    def test_count_unique_participants(self):
        """Тест подсчета уникальных участников"""
        messages = []
        
        # Создаем сообщения с повторяющимися usernames
        for username in ["alice", "bob", "alice", "charlie", "bob"]:
            msg = Mock()
            msg.username = username
            msg.message = "Test message"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        count = self.agent._count_unique_participants(messages)
        assert count == 3  # alice, bob, charlie
    
    def test_has_links_detection(self):
        """Тест обнаружения ссылок"""
        messages = []
        
        # Сообщение со ссылкой
        msg = Mock()
        msg.message = "Check https://example.com for details"
        messages.append(msg)
        
        # Сообщение без ссылки
        msg2 = Mock()
        msg2.message = "Just regular text"
        messages.append(msg2)
        
        has_links = self.agent._has_links(messages)
        assert has_links == True
    
    def test_determine_detail_level_edge_cases(self):
        """Тест граничных случаев определения уровня детализации"""
        # Тест micro (1 участник, много сообщений)
        level = self.agent._determine_detail_level(50, 1, "short")
        assert level == "micro"
        
        # Тест brief (мало участников, средний объем)
        level = self.agent._determine_detail_level(10, 2, "medium")
        assert level == "brief"
        
        # Тест standard (много участников)
        level = self.agent._determine_detail_level(20, 5, "short")
        assert level == "standard"
        
        # Тест detailed (длительный период)
        level = self.agent._determine_detail_level(30, 3, "long")
        assert level == "detailed"
        
        # Тест comprehensive (очень много сообщений)
        level = self.agent._determine_detail_level(150, 5, "medium")
        assert level == "comprehensive"
