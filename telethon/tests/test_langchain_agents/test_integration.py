"""
Integration tests для LangChain Agents

Тесты интеграции всех компонентов вместе.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime, timezone

from langchain_agents.orchestrator import DigestOrchestrator


class TestLangChainIntegration:
    """Интеграционные тесты для LangChain агентов"""
    
    def setup_method(self):
        """Настройка перед каждым тестом"""
        self.orchestrator = DigestOrchestrator()
    
    @pytest.mark.asyncio
    async def test_full_pipeline_micro_level(self):
        """Тест полной pipeline для micro уровня детализации"""
        # Создаем mock сообщения для micro уровня
        messages = []
        for i in range(3):
            msg = Mock()
            msg.message = f"Test message {i}"
            msg.username = f"user{i}"
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        # Mock всех LLM агентов для избежания реальных вызовов
        with patch.object(self.orchestrator.topic_extractor, 'ainvoke', new_callable=AsyncMock) as mock_topics, \
             patch.object(self.orchestrator.emotion_analyzer, 'ainvoke', new_callable=AsyncMock) as mock_emotions, \
             patch.object(self.orchestrator.speaker_analyzer, 'ainvoke', new_callable=AsyncMock) as mock_speakers, \
             patch.object(self.orchestrator.summarizer, 'ainvoke', new_callable=AsyncMock) as mock_summarizer, \
             patch.object(self.orchestrator.supervisor, 'ainvoke', new_callable=AsyncMock) as mock_supervisor:
            
            # Настройка mock результатов
            mock_topics.return_value = {
                "topics": [
                    {"name": "Test Topic", "priority": "high"}
                ]
            }
            
            mock_emotions.return_value = {
                "overall_tone": "positive",
                "atmosphere": "casual",
                "emotional_indicators": ["smile", "excited"],
                "intensity_level": "low",
                "key_emotions": ["happy"],
                "conflict_indicators": False,
                "support_indicators": True
            }
            
            mock_speakers.return_value = {
                "speakers": [
                    {
                        "username": "user0",
                        "role": "leader",
                        "activity_level": "high",
                        "message_count": 2,
                        "contribution_types": ["question"],
                        "key_contributions": ["Asked questions"]
                    }
                ],
                "group_dynamics": {
                    "dominant_speaker": "user0",
                    "most_helpful": "user0",
                    "most_questions": "user0",
                    "collaboration_level": "high"
                }
            }
            
            mock_summarizer.return_value = {
                "summary": {
                    "main_points": ["Point 1", "Point 2"],
                    "key_decisions": ["Decision 1"],
                    "outstanding_issues": [],
                    "next_steps": [],
                    "summary_text": "Test summary"
                },
                "context_adaptation": {
                    "detail_level": "micro",
                    "dialogue_type": "discussion",
                    "focus_areas": ["topic1"],
                    "summary_style": "concise"
                }
            }
            
            mock_supervisor.return_value = {
                "html_digest": "<b>Test Digest</b><p>Summary content</p>",
                "metadata": {
                    "detail_level": "micro",
                    "dialogue_type": "discussion",
                    "participants_count": 3,
                    "message_count": 3,
                    "generation_timestamp": "2024-01-01T12:00:00Z"
                },
                "sections": {
                    "summary": "Test summary",
                    "topics": "Test topics",
                    "decisions": "Test decisions",
                    "participants": "Test participants",
                    "resources": "Test resources"
                }
            }
            
            # Выполняем полную pipeline
            result = await self.orchestrator.generate_digest(
                messages=messages,
                hours=24,
                user_id=123,
                group_id=456
            )
            
            # Проверяем результат
            assert "html_digest" in result
            assert "metadata" in result
            assert "sections" in result
            assert "generation_metadata" in result
            assert "agent_results" in result
            assert "agent_statistics" in result
            
            # Проверяем метаданные
            assert result["generation_metadata"]["user_id"] == 123
            assert result["generation_metadata"]["group_id"] == 456
            assert result["generation_metadata"]["message_count"] == 3
            
            # Проверяем статистику агентов
            assert result["agent_statistics"]["detail_level"] == "micro"
            assert result["agent_statistics"]["participants"] == 3
            
            # Проверяем, что условные агенты были пропущены
            assert result["agent_results"]["key_moments"]["skipped"] == True
            assert result["agent_results"]["timeline"]["skipped"] == True
            assert result["agent_results"]["context_links"]["skipped"] == True
    
    @pytest.mark.asyncio
    async def test_full_pipeline_standard_level(self):
        """Тест полной pipeline для standard уровня детализации"""
        # Создаем mock сообщения для standard уровня
        messages = []
        for i in range(25):
            msg = Mock()
            msg.message = f"Test message {i}"
            msg.username = f"user{i % 5}"  # 5 участников
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        # Mock всех агентов
        with patch.object(self.orchestrator.topic_extractor, 'ainvoke', new_callable=AsyncMock) as mock_topics, \
             patch.object(self.orchestrator.emotion_analyzer, 'ainvoke', new_callable=AsyncMock) as mock_emotions, \
             patch.object(self.orchestrator.speaker_analyzer, 'ainvoke', new_callable=AsyncMock) as mock_speakers, \
             patch.object(self.orchestrator.summarizer, 'ainvoke', new_callable=AsyncMock) as mock_summarizer, \
             patch.object(self.orchestrator.key_moments, 'ainvoke', new_callable=AsyncMock) as mock_key_moments, \
             patch.object(self.orchestrator.supervisor, 'ainvoke', new_callable=AsyncMock) as mock_supervisor:
            
            # Настройка mock результатов
            mock_topics.return_value = {
                "topics": [
                    {"name": "Main Topic", "priority": "high"},
                    {"name": "Secondary Topic", "priority": "medium"}
                ]
            }
            
            mock_emotions.return_value = {
                "overall_tone": "neutral",
                "atmosphere": "collaborative",
                "emotional_indicators": ["focused", "productive"],
                "intensity_level": "medium",
                "key_emotions": ["determined"],
                "conflict_indicators": False,
                "support_indicators": True
            }
            
            mock_speakers.return_value = {
                "speakers": [
                    {
                        "username": "user0",
                        "role": "leader",
                        "activity_level": "high",
                        "message_count": 8,
                        "contribution_types": ["question", "answer"],
                        "key_contributions": ["Led discussion", "Answered questions"]
                    },
                    {
                        "username": "user1",
                        "role": "contributor",
                        "activity_level": "medium",
                        "message_count": 5,
                        "contribution_types": ["suggestion"],
                        "key_contributions": ["Made suggestions"]
                    }
                ],
                "group_dynamics": {
                    "dominant_speaker": "user0",
                    "most_helpful": "user0",
                    "most_questions": "user0",
                    "collaboration_level": "high"
                }
            }
            
            mock_summarizer.return_value = {
                "summary": {
                    "main_points": ["Point 1", "Point 2", "Point 3"],
                    "key_decisions": ["Decision 1", "Decision 2"],
                    "outstanding_issues": ["Issue 1"],
                    "next_steps": ["Step 1"],
                    "summary_text": "Comprehensive test summary"
                },
                "context_adaptation": {
                    "detail_level": "standard",
                    "dialogue_type": "discussion",
                    "focus_areas": ["topic1", "topic2"],
                    "summary_style": "balanced"
                }
            }
            
            mock_key_moments.return_value = {
                "key_decisions": [
                    {
                        "decision": "Important decision",
                        "context": "Context of decision",
                        "impact": "high",
                        "decision_maker": "user0"
                    }
                ],
                "critical_questions": [
                    {
                        "question": "Important question?",
                        "asked_by": "user1",
                        "status": "answered",
                        "importance": "high"
                    }
                ],
                "turning_points": [],
                "action_items": [],
                "important_insights": []
            }
            
            mock_supervisor.return_value = {
                "html_digest": "<b>Standard Digest</b><p>Comprehensive summary</p>",
                "metadata": {
                    "detail_level": "standard",
                    "dialogue_type": "discussion",
                    "participants_count": 5,
                    "message_count": 25,
                    "generation_timestamp": "2024-01-01T12:00:00Z"
                },
                "sections": {
                    "summary": "Comprehensive summary",
                    "topics": "Main topics covered",
                    "decisions": "Key decisions made",
                    "participants": "Active participants",
                    "resources": "Resources mentioned"
                }
            }
            
            # Выполняем полную pipeline
            result = await self.orchestrator.generate_digest(
                messages=messages,
                hours=24,
                user_id=123,
                group_id=456
            )
            
            # Проверяем результат
            assert "html_digest" in result
            assert result["agent_statistics"]["detail_level"] == "standard"
            assert result["agent_statistics"]["participants"] == 5
            
            # Проверяем, что Key Moments выполнился
            assert result["agent_results"]["key_moments"]["skipped"] != True
            assert "key_decisions" in result["agent_results"]["key_moments"]
            
            # Проверяем, что Timeline и Context Links пропущены
            assert result["agent_results"]["timeline"]["skipped"] == True
            assert result["agent_results"]["context_links"]["skipped"] == True
    
    @pytest.mark.asyncio
    async def test_full_pipeline_comprehensive_level(self):
        """Тест полной pipeline для comprehensive уровня детализации"""
        # Создаем mock сообщения для comprehensive уровня
        messages = []
        for i in range(120):
            msg = Mock()
            msg.message = f"Test message {i} with https://example.com"
            msg.username = f"user{i % 8}"  # 8 участников
            msg.date = datetime.now(timezone.utc)
            messages.append(msg)
        
        # Mock всех агентов
        with patch.object(self.orchestrator.topic_extractor, 'ainvoke', new_callable=AsyncMock) as mock_topics, \
             patch.object(self.orchestrator.emotion_analyzer, 'ainvoke', new_callable=AsyncMock) as mock_emotions, \
             patch.object(self.orchestrator.speaker_analyzer, 'ainvoke', new_callable=AsyncMock) as mock_speakers, \
             patch.object(self.orchestrator.summarizer, 'ainvoke', new_callable=AsyncMock) as mock_summarizer, \
             patch.object(self.orchestrator.key_moments, 'ainvoke', new_callable=AsyncMock) as mock_key_moments, \
             patch.object(self.orchestrator.timeline, 'ainvoke', new_callable=AsyncMock) as mock_timeline, \
             patch.object(self.orchestrator.context_links, 'ainvoke', new_callable=AsyncMock) as mock_context_links, \
             patch.object(self.orchestrator.supervisor, 'ainvoke', new_callable=AsyncMock) as mock_supervisor:
            
            # Настройка всех mock результатов
            mock_topics.return_value = {
                "topics": [
                    {"name": "Topic 1", "priority": "high"},
                    {"name": "Topic 2", "priority": "high"},
                    {"name": "Topic 3", "priority": "medium"}
                ]
            }
            
            mock_emotions.return_value = {
                "overall_tone": "positive",
                "atmosphere": "collaborative",
                "emotional_indicators": ["enthusiastic", "focused"],
                "intensity_level": "high",
                "key_emotions": ["excited", "determined"],
                "conflict_indicators": False,
                "support_indicators": True
            }
            
            mock_speakers.return_value = {
                "speakers": [
                    {
                        "username": "user0",
                        "role": "leader",
                        "activity_level": "high",
                        "message_count": 20,
                        "contribution_types": ["question", "answer", "suggestion"],
                        "key_contributions": ["Led discussion", "Made decisions"]
                    }
                ],
                "group_dynamics": {
                    "dominant_speaker": "user0",
                    "most_helpful": "user0",
                    "most_questions": "user0",
                    "collaboration_level": "high"
                }
            }
            
            mock_summarizer.return_value = {
                "summary": {
                    "main_points": ["Point 1", "Point 2", "Point 3", "Point 4"],
                    "key_decisions": ["Decision 1", "Decision 2"],
                    "outstanding_issues": ["Issue 1"],
                    "next_steps": ["Step 1", "Step 2"],
                    "summary_text": "Comprehensive detailed summary"
                },
                "context_adaptation": {
                    "detail_level": "comprehensive",
                    "dialogue_type": "discussion",
                    "focus_areas": ["topic1", "topic2", "topic3"],
                    "summary_style": "detailed"
                }
            }
            
            mock_key_moments.return_value = {
                "key_decisions": [
                    {
                        "decision": "Major decision",
                        "context": "Important context",
                        "impact": "high",
                        "decision_maker": "user0"
                    }
                ],
                "critical_questions": [
                    {
                        "question": "Critical question?",
                        "asked_by": "user1",
                        "status": "answered",
                        "importance": "high"
                    }
                ],
                "turning_points": [
                    {
                        "moment": "Turning point",
                        "trigger": "Important event",
                        "impact": "Changed direction"
                    }
                ],
                "action_items": [
                    {
                        "action": "Action item",
                        "assigned_to": "user2",
                        "priority": "high",
                        "deadline": "Next week"
                    }
                ],
                "important_insights": [
                    {
                        "insight": "Important insight",
                        "discovered_by": "user3",
                        "significance": "high"
                    }
                ]
            }
            
            mock_timeline.return_value = {
                "timeline_events": [
                    {
                        "timestamp": "Event 1",
                        "event": "Important event",
                        "participant": "user0",
                        "event_type": "decision",
                        "significance": "high"
                    }
                ],
                "discussion_phases": [
                    {
                        "phase": "Planning",
                        "start_event": "Started planning",
                        "end_event": "Finished planning",
                        "description": "Planning phase",
                        "duration": "30 minutes"
                    }
                ],
                "topic_evolution": [
                    {
                        "topic": "Topic evolution",
                        "first_mentioned": "Early",
                        "evolution": "Developed over time",
                        "resolution": "Resolved"
                    }
                ],
                "participant_engagement": [
                    {
                        "username": "user0",
                        "engagement_pattern": "consistent",
                        "peak_activity": "Middle",
                        "contribution_focus": "Leadership"
                    }
                ],
                "chronological_summary": "Chronological summary"
            }
            
            mock_context_links.return_value = {
                "external_links": [
                    {
                        "url": "https://example.com",
                        "domain": "example.com",
                        "context": "Reference link",
                        "shared_by": "user0",
                        "relevance": "high",
                        "link_type": "article"
                    }
                ],
                "telegram_links": [],
                "mentions": [],
                "file_references": [],
                "resource_context": {
                    "total_resources": 1,
                    "most_active_sharer": "user0",
                    "resource_categories": ["external"],
                    "quality_assessment": "high"
                }
            }
            
            mock_supervisor.return_value = {
                "html_digest": "<b>Comprehensive Digest</b><p>Detailed comprehensive summary</p>",
                "metadata": {
                    "detail_level": "comprehensive",
                    "dialogue_type": "discussion",
                    "participants_count": 8,
                    "message_count": 120,
                    "generation_timestamp": "2024-01-01T12:00:00Z"
                },
                "sections": {
                    "summary": "Comprehensive summary",
                    "topics": "All topics covered",
                    "decisions": "All decisions made",
                    "participants": "All participants",
                    "resources": "All resources"
                }
            }
            
            # Выполняем полную pipeline
            result = await self.orchestrator.generate_digest(
                messages=messages,
                hours=24,
                user_id=123,
                group_id=456
            )
            
            # Проверяем результат
            assert "html_digest" in result
            assert result["agent_statistics"]["detail_level"] == "comprehensive"
            assert result["agent_statistics"]["participants"] == 8
            
            # Проверяем, что все условные агенты выполнились
            assert result["agent_results"]["key_moments"]["skipped"] != True
            assert result["agent_results"]["timeline"]["skipped"] != True
            assert result["agent_results"]["context_links"]["skipped"] != True
            
            # Проверяем наличие данных от всех агентов
            assert "key_decisions" in result["agent_results"]["key_moments"]
            assert "timeline_events" in result["agent_results"]["timeline"]
            assert "external_links" in result["agent_results"]["context_links"]
    
    @pytest.mark.asyncio
    async def test_pipeline_error_handling(self):
        """Тест обработки ошибок в pipeline"""
        messages = [Mock()]
        
        # Mock ошибки в одном из агентов
        with patch.object(self.orchestrator.topic_extractor, 'ainvoke', new_callable=AsyncMock) as mock_topics:
            mock_topics.side_effect = Exception("Topic extraction failed")
            
            result = await self.orchestrator.generate_digest(
                messages=messages,
                hours=24,
                user_id=123,
                group_id=456
            )
            
            # Проверяем, что ошибка обработана
            assert "html_digest" in result
            assert "generation_metadata" in result
            assert "error" in result["generation_metadata"]
            assert result["agent_statistics"]["error"] == True
