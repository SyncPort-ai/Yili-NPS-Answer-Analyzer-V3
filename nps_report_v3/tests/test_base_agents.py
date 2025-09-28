"""Unit tests for agent base classes"""

import pytest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime

from nps_report_v3.agents.base import (
    BaseAgent, FoundationAgent, AnalysisAgent, ConsultingAgent,
    ConfidenceConstrainedAgent, AgentStatus, AgentResult
)


class TestableAgent(BaseAgent):
    """Concrete implementation for testing"""

    async def process(self, state):
        return AgentResult(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED,
            data={"test": "data"}
        )


class TestableFoundationAgent(FoundationAgent):
    """Concrete foundation agent for testing"""

    async def process(self, state):
        return AgentResult(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED,
            data={"foundation": "result"}
        )


class TestableAnalysisAgent(AnalysisAgent):
    """Concrete analysis agent for testing"""

    async def process(self, state):
        return AgentResult(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED,
            data={"analysis": "result"}
        )


class TestableConsultingAgent(ConsultingAgent):
    """Concrete consulting agent for testing"""

    async def process(self, state):
        return AgentResult(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED,
            insights=[{"content": "Strategic recommendation"}]
        )


class TestableConfidenceConstrainedAgent(ConfidenceConstrainedAgent):
    """Concrete confidence constrained agent for testing"""

    async def process(self, state):
        return AgentResult(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED,
            insights=[{"content": "Full strategic analysis"}]
        )


class TestBaseAgent:
    """Test BaseAgent class"""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        agent = TestableAgent("TEST1", "Test Agent")
        state = {"input_data": {"test": "data"}}

        result = await agent.execute(state)

        assert result.agent_id == "TEST1"
        assert result.status == AgentStatus.COMPLETED
        assert result.data == {"test": "data"}
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 0

    @pytest.mark.asyncio
    async def test_input_validation_failure(self):
        agent = TestableAgent("TEST1", "Test Agent")
        state = {}  # Missing input_data

        result = await agent.execute(state)

        assert result.status == AgentStatus.FAILED
        assert len(result.errors) > 0
        assert "input_data is required" in result.errors[0]

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        agent = TestableAgent("TEST1", "Test Agent", max_retries=2)
        agent.process = MagicMock(side_effect=[Exception("First failure"), Exception("Second failure")])

        state = {"input_data": {"test": "data"}}
        result = await agent.execute(state)

        assert result.status == AgentStatus.FAILED
        assert agent.process.call_count == 2
        assert "Agent failed after 2 attempts" in result.errors[0]

    @pytest.mark.asyncio
    async def test_retry_with_eventual_success(self):
        agent = TestableAgent("TEST1", "Test Agent", max_retries=3)
        successful_result = AgentResult(
            agent_id="TEST1",
            status=AgentStatus.COMPLETED,
            data={"success": True}
        )

        # Fail twice, then succeed
        agent.process = MagicMock(side_effect=[
            Exception("First failure"),
            Exception("Second failure"),
            successful_result
        ])

        state = {"input_data": {"test": "data"}}

        # Mock sleep to speed up test
        with patch('asyncio.sleep', return_value=None):
            result = await agent.execute(state)

        assert result.status == AgentStatus.COMPLETED
        assert result.data == {"success": True}
        assert agent.process.call_count == 3


class TestFoundationAgent:
    """Test FoundationAgent class"""

    @pytest.mark.asyncio
    async def test_foundation_validation_success(self):
        agent = TestableFoundationAgent("A0", "Data Preprocessor")
        state = {
            "input_data": {
                "survey_responses": [
                    {"nps_score": 9, "comment": "Great product"}
                ]
            }
        }

        result = await agent.execute(state)

        assert result.status == AgentStatus.COMPLETED
        assert result.data == {"foundation": "result"}

    @pytest.mark.asyncio
    async def test_foundation_validation_failure(self):
        agent = TestableFoundationAgent("A0", "Data Preprocessor")
        state = {
            "input_data": {}  # Missing survey_responses
        }

        result = await agent.execute(state)

        assert result.status == AgentStatus.FAILED
        assert "Foundation agents require survey_responses" in str(result.errors)


class TestAnalysisAgent:
    """Test AnalysisAgent class"""

    @pytest.mark.asyncio
    async def test_analysis_validation_success(self):
        agent = TestableAnalysisAgent("B1", "Promoter Analyst")
        state = {
            "input_data": {"test": "data"},
            "pass1_foundation": {
                "nps_calculation": {
                    "nps_score": 45.5,
                    "promoter_percentage": 60
                }
            }
        }

        result = await agent.execute(state)

        assert result.status == AgentStatus.COMPLETED
        assert result.data == {"analysis": "result"}

    @pytest.mark.asyncio
    async def test_analysis_validation_missing_foundation(self):
        agent = TestableAnalysisAgent("B1", "Promoter Analyst")
        state = {"input_data": {"test": "data"}}

        result = await agent.execute(state)

        assert result.status == AgentStatus.FAILED
        assert "Analysis agents require pass1_foundation" in str(result.errors)

    @pytest.mark.asyncio
    async def test_analysis_validation_missing_nps_calculation(self):
        agent = TestableAnalysisAgent("B1", "Promoter Analyst")
        state = {
            "input_data": {"test": "data"},
            "pass1_foundation": {}  # Missing nps_calculation
        }

        result = await agent.execute(state)

        assert result.status == AgentStatus.FAILED
        assert "NPS calculation results" in str(result.errors)


class TestConsultingAgent:
    """Test ConsultingAgent class"""

    @pytest.mark.asyncio
    async def test_consulting_validation_success(self):
        agent = TestableConsultingAgent("C1", "Strategic Advisor")
        state = {
            "input_data": {"test": "data"},
            "pass1_foundation": {
                "nps_calculation": {"nps_score": 45.5},
                "confidence_assessment": {"level": "high"}
            },
            "pass2_analysis": {
                "insights": ["Analysis complete"]
            }
        }

        result = await agent.execute(state)

        assert result.status == AgentStatus.COMPLETED
        assert len(result.insights) > 0

    @pytest.mark.asyncio
    async def test_consulting_validation_missing_dependencies(self):
        agent = TestableConsultingAgent("C1", "Strategic Advisor")
        state = {"input_data": {"test": "data"}}

        result = await agent.execute(state)

        assert result.status == AgentStatus.FAILED
        assert "pass1_foundation" in str(result.errors)
        assert "pass2_analysis" in str(result.errors)


class TestConfidenceConstrainedAgent:
    """Test ConfidenceConstrainedAgent class"""

    @pytest.mark.asyncio
    async def test_low_confidence_constraint(self):
        agent = TestableConfidenceConstrainedAgent("C1", "Strategic Advisor")
        state = {
            "input_data": {"test": "data"},
            "pass1_foundation": {
                "nps_calculation": {"nps_score": 45.5},
                "confidence_assessment": {"level": "low"}
            },
            "pass2_analysis": {"insights": ["Analysis complete"]}
        }

        result = await agent.execute(state)

        assert result.status == AgentStatus.COMPLETED
        assert result.insights[0]["content"] == "Full strategic analysis"
        assert result.confidence_score == 0.5
        assert any("confidence" in warning.lower() for warning in result.warnings)

    @pytest.mark.asyncio
    async def test_high_confidence_full_processing(self):
        agent = TestableConfidenceConstrainedAgent("C1", "Strategic Advisor")
        state = {
            "input_data": {"test": "data"},
            "pass1_foundation": {
                "nps_calculation": {"nps_score": 45.5},
                "confidence_assessment": {"level": "high"}
            },
            "pass2_analysis": {"insights": ["Analysis complete"]}
        }

        result = await agent.execute(state)

        assert result.status == AgentStatus.COMPLETED
        assert result.insights[0]["content"] == "Full strategic analysis"
        assert result.warnings is None or len(result.warnings) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
