"""Unit tests for agent factory"""

import pytest
from typing import Dict, Any

from nps_report_v3.agents.factory import (
    AgentFactory, AgentConfig, AgentRegistry, get_factory
)
from nps_report_v3.agents.base import (
    BaseAgent, FoundationAgent, AnalysisAgent,
    ConsultingAgent, ConfidenceConstrainedAgent, AgentResult, AgentStatus
)


class CustomTestAgent(BaseAgent):
    """Custom agent for testing registration"""

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED,
            data={"custom": "result"}
        )


class CustomFoundationAgent(FoundationAgent):
    """Custom foundation agent for testing"""

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        return AgentResult(
            agent_id=self.agent_id,
            status=AgentStatus.COMPLETED,
            data={"custom_foundation": "result"}
        )


class TestAgentRegistry:
    """Test AgentRegistry class"""

    def test_register_agent(self):
        registry = AgentRegistry()
        config = AgentConfig(
            agent_id="TEST1",
            agent_name="Test Agent",
            layer="custom"
        )

        registry.register("TEST1", CustomTestAgent, config)

        assert registry.get_agent_class("TEST1") == CustomTestAgent
        assert registry.get_agent_config("TEST1") == config

    def test_register_duplicate_agent(self, caplog):
        registry = AgentRegistry()
        config1 = AgentConfig("TEST1", "Test Agent 1", "custom")
        config2 = AgentConfig("TEST1", "Test Agent 2", "custom")

        registry.register("TEST1", CustomTestAgent, config1)
        registry.register("TEST1", CustomTestAgent, config2)

        assert "Overwriting existing registration" in caplog.text
        assert registry.get_agent_config("TEST1").agent_name == "Test Agent 2"

    def test_list_agents(self):
        registry = AgentRegistry()
        config1 = AgentConfig("TEST1", "Test Agent 1", "custom")
        config2 = AgentConfig("TEST2", "Test Agent 2", "custom")

        registry.register("TEST1", CustomTestAgent, config1)
        registry.register("TEST2", CustomFoundationAgent, config2)

        agents = registry.list_agents()
        assert agents == {
            "TEST1": "CustomTestAgent",
            "TEST2": "CustomFoundationAgent"
        }


class TestAgentFactory:
    """Test AgentFactory class"""

    def test_factory_initialization(self):
        factory = AgentFactory()

        # Check that default agents are configured
        assert factory.registry.get_agent_config("A0") is not None
        assert factory.registry.get_agent_config("B1") is not None
        assert factory.registry.get_agent_config("C1") is not None

        # Check layer assignments
        assert factory.registry.get_agent_config("A0").layer == "foundation"
        assert factory.registry.get_agent_config("B5").layer == "analysis"
        assert factory.registry.get_agent_config("C3").layer == "consulting"

    def test_create_default_foundation_agent(self):
        factory = AgentFactory()
        agent = factory.create_agent("A0")

        assert agent.agent_id == "A0"
        assert agent.agent_name == "Data Preprocessor"
        assert isinstance(agent, FoundationAgent)
        assert agent.layer == "foundation"

    def test_create_default_analysis_agent(self):
        factory = AgentFactory()
        agent = factory.create_agent("B1")

        assert agent.agent_id == "B1"
        assert agent.agent_name == "Promoter Analyst"
        assert isinstance(agent, AnalysisAgent)
        assert agent.layer == "analysis"

    def test_create_default_consulting_agent(self):
        factory = AgentFactory()

        # Test regular consulting agent (C5)
        agent_c5 = factory.create_agent("C5")
        assert agent_c5.agent_id == "C5"
        assert agent_c5.agent_name == "Executive Synthesizer"
        assert isinstance(agent_c5, ConsultingAgent)

        # Test confidence constrained agent (C1)
        agent_c1 = factory.create_agent("C1")
        assert agent_c1.agent_id == "C1"
        assert agent_c1.agent_name == "Strategic Advisor"
        assert isinstance(agent_c1, ConfidenceConstrainedAgent)

    def test_create_agent_with_custom_config(self):
        factory = AgentFactory()
        custom_config = {
            "max_retries": 5,
            "timeout_seconds": 120
        }

        agent = factory.create_agent("A0", custom_config)

        config = factory.get_agent_config("A0")
        assert config.max_retries == 5
        assert config.timeout_seconds == 120

    def test_create_unknown_agent_raises_error(self):
        factory = AgentFactory()

        with pytest.raises(ValueError, match="Agent UNKNOWN is not registered"):
            factory.create_agent("UNKNOWN")

    def test_register_custom_agent(self):
        factory = AgentFactory()
        config = AgentConfig(
            agent_id="CUSTOM1",
            agent_name="Custom Test Agent",
            layer="custom"
        )

        factory.register_custom_agent("CUSTOM1", CustomTestAgent, config)

        agent = factory.create_agent("CUSTOM1")
        assert agent.agent_id == "CUSTOM1"
        assert agent.agent_name == "Custom Test Agent"
        assert isinstance(agent, CustomTestAgent)

    def test_register_custom_agent_auto_config(self):
        factory = AgentFactory()

        # Register without config - should auto-generate
        factory.register_custom_agent("CUSTOM_FOUND", CustomFoundationAgent)

        config = factory.get_agent_config("CUSTOM_FOUND")
        assert config.agent_id == "CUSTOM_FOUND"
        assert config.agent_name == "CustomFoundationAgent"
        assert config.layer == "foundation"  # Auto-detected from base class

    def test_create_all_foundation_agents(self):
        factory = AgentFactory()
        agents = factory.create_foundation_agents()

        assert len(agents) == 4  # A0, A1, A2, A3
        assert "A0" in agents
        assert "A1" in agents
        assert "A2" in agents
        assert "A3" in agents

        for agent_id, agent in agents.items():
            assert isinstance(agent, FoundationAgent)
            assert agent.layer == "foundation"

    def test_create_all_analysis_agents(self):
        factory = AgentFactory()
        agents = factory.create_analysis_agents()

        assert len(agents) == 9  # B1-B9
        for i in range(1, 10):
            assert f"B{i}" in agents

        for agent_id, agent in agents.items():
            assert isinstance(agent, AnalysisAgent)
            assert agent.layer == "analysis"

    def test_create_all_consulting_agents(self):
        factory = AgentFactory()
        agents = factory.create_consulting_agents()

        assert len(agents) == 5  # C1-C5
        for i in range(1, 6):
            assert f"C{i}" in agents

        # Check that C1-C4 are confidence constrained
        for i in range(1, 5):
            assert isinstance(agents[f"C{i}"], ConfidenceConstrainedAgent)

        # Check that C5 is regular consulting agent
        assert isinstance(agents["C5"], ConsultingAgent)
        assert not isinstance(agents["C5"], ConfidenceConstrainedAgent)

    def test_list_available_agents(self):
        factory = AgentFactory()
        available = factory.list_available_agents()

        assert "foundation" in available
        assert "analysis" in available
        assert "consulting" in available

        assert len(available["foundation"]) == 4  # A0-A3
        assert len(available["analysis"]) == 9   # B1-B9
        assert len(available["consulting"]) == 5  # C1-C5

        assert available["foundation"]["A0"] == "Data Preprocessor"
        assert available["analysis"]["B1"] == "Promoter Analyst"
        assert available["consulting"]["C1"] == "Strategic Advisor"

    def test_singleton_factory(self):
        factory1 = get_factory()
        factory2 = get_factory()

        assert factory1 is factory2  # Should be the same instance

        # Register an agent using factory1
        factory1.register_custom_agent("SINGLETON_TEST", CustomTestAgent)

        # Should be accessible from factory2
        agent = factory2.create_agent("SINGLETON_TEST")
        assert agent.agent_id == "SINGLETON_TEST"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])