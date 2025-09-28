"""
Agent factory pattern for creating and managing NPS V3 agents.
Provides centralized agent creation with registration mechanism.
"""

from typing import Dict, Type, Optional
from dataclasses import dataclass
import logging

from nps_report_v3.agents.base import (
    BaseAgent, FoundationAgent, AnalysisAgent,
    ConsultingAgent, ConfidenceConstrainedAgent
)
from nps_report_v3.config.constants import (
    FOUNDATION_AGENTS, ANALYSIS_AGENTS, CONSULTING_AGENTS
)

logger = logging.getLogger(__name__)

# Import actual agent implementations
try:
    from nps_report_v3.agents.foundation.A0_ingestion_agent import DataIngestionAgent
    from nps_report_v3.agents.foundation.A1_quantitative_agent import QuantitativeAnalysisAgent
    from nps_report_v3.agents.foundation.A2_qualitative_agent import QualitativeAnalysisAgent
    from nps_report_v3.agents.foundation.A3_clustering_agent import SemanticClusteringAgent
    FOUNDATION_IMPLEMENTATIONS = {
        "A0": DataIngestionAgent,
        "A1": QuantitativeAnalysisAgent,
        "A2": QualitativeAnalysisAgent,
        "A3": SemanticClusteringAgent
    }
except ImportError as e:
    logger.warning(f"Foundation agent imports failed: {e}")
    FOUNDATION_IMPLEMENTATIONS = {}

try:
    from nps_report_v3.agents.analysis.B1_technical_requirements_agent import TechnicalRequirementsAgent
    from nps_report_v3.agents.analysis.B2_passive_analyst_agent import PassiveAnalystAgent
    from nps_report_v3.agents.analysis.B3_detractor_analyst_agent import DetractorAnalystAgent
    from nps_report_v3.agents.analysis.B4_text_clustering_agent import TextClusteringAgent
    from nps_report_v3.agents.analysis.B5_driver_analysis_agent import DriverAnalysisAgent
    from nps_report_v3.agents.analysis.B6_product_dimension_agent import ProductDimensionAgent
    from nps_report_v3.agents.analysis.B7_geographic_dimension_agent import GeographicDimensionAgent
    from nps_report_v3.agents.analysis.B8_channel_dimension_agent import ChannelDimensionAgent
    from nps_report_v3.agents.analysis.B9_analysis_coordinator import AnalysisCoordinatorAgent
    ANALYSIS_IMPLEMENTATIONS = {
        "B1": TechnicalRequirementsAgent,
        "B2": PassiveAnalystAgent,
        "B3": DetractorAnalystAgent,
        "B4": TextClusteringAgent,
        "B5": DriverAnalysisAgent,
        "B6": ProductDimensionAgent,
        "B7": GeographicDimensionAgent,
        "B8": ChannelDimensionAgent,
        "B9": AnalysisCoordinatorAgent
    }
except ImportError as e:
    logger.warning(f"Analysis agent imports failed: {e}")
    ANALYSIS_IMPLEMENTATIONS = {}

try:
    from nps_report_v3.agents.consulting.C1_strategic_recommendations_agent import StrategicRecommendationsAgent
    from nps_report_v3.agents.consulting.C2_product_consultant_agent import ProductConsultantAgent
    from nps_report_v3.agents.consulting.C3_marketing_advisor_agent import MarketingAdvisorAgent
    from nps_report_v3.agents.consulting.C4_risk_manager_agent import RiskManagerAgent
    from nps_report_v3.agents.consulting.C5_executive_synthesizer_agent import ExecutiveSynthesizerAgent
    CONSULTING_IMPLEMENTATIONS = {
        "C1": StrategicRecommendationsAgent,
        "C2": ProductConsultantAgent,
        "C3": MarketingAdvisorAgent,
        "C4": RiskManagerAgent,
        "C5": ExecutiveSynthesizerAgent
    }
except ImportError as e:
    logger.warning(f"Consulting agent imports failed: {e}")
    CONSULTING_IMPLEMENTATIONS = {}


@dataclass
class AgentConfig:
    """Configuration for agent creation"""
    agent_id: str
    agent_name: str
    layer: str
    max_retries: int = 3
    timeout_seconds: int = 60
    enable_cache: bool = True
    llm_config: Optional[Dict] = None


class AgentRegistry:
    """Registry for agent classes"""

    def __init__(self):
        self._registry: Dict[str, Type[BaseAgent]] = {}
        self._configs: Dict[str, AgentConfig] = {}

    def register(self, agent_id: str, agent_class: Type[BaseAgent], config: AgentConfig):
        """Register an agent class with its configuration"""
        if agent_id in self._registry:
            logger.warning(f"Overwriting existing registration for agent {agent_id}")

        self._registry[agent_id] = agent_class
        self._configs[agent_id] = config
        logger.info(f"Registered agent {agent_id}: {agent_class.__name__}")

    def get_agent_class(self, agent_id: str) -> Optional[Type[BaseAgent]]:
        """Get agent class by ID"""
        return self._registry.get(agent_id)

    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Get agent configuration by ID"""
        return self._configs.get(agent_id)

    def list_agents(self) -> Dict[str, str]:
        """List all registered agents"""
        return {
            agent_id: agent_class.__name__
            for agent_id, agent_class in self._registry.items()
        }


class AgentFactory:
    """Factory for creating NPS V3 agents"""

    def __init__(self):
        self.registry = AgentRegistry()
        self._initialize_default_agents()

    def _initialize_default_agents(self):
        """Initialize default agent registrations"""

        # Foundation agents (A0-A3)
        for agent_id, agent_name in FOUNDATION_AGENTS.items():
            config = AgentConfig(
                agent_id=agent_id,
                agent_name=agent_name,
                layer="foundation"
            )

            # Register actual implementation if available
            if agent_id in FOUNDATION_IMPLEMENTATIONS:
                agent_class = FOUNDATION_IMPLEMENTATIONS[agent_id]
                self.registry.register(agent_id, agent_class, config)
            else:
                # Placeholder configuration
                self.registry._configs[agent_id] = config

        # Analysis agents (B1-B9)
        for agent_id, agent_name in ANALYSIS_AGENTS.items():
            config = AgentConfig(
                agent_id=agent_id,
                agent_name=agent_name,
                layer="analysis"
            )

            # Register actual implementation if available
            if agent_id in ANALYSIS_IMPLEMENTATIONS:
                agent_class = ANALYSIS_IMPLEMENTATIONS[agent_id]
                self.registry.register(agent_id, agent_class, config)
            else:
                # Placeholder configuration
                self.registry._configs[agent_id] = config

        # Consulting agents (C1-C5)
        for agent_id, agent_name in CONSULTING_AGENTS.items():
            config = AgentConfig(
                agent_id=agent_id,
                agent_name=agent_name,
                layer="consulting"
            )

            # Register actual implementation if available
            if agent_id in CONSULTING_IMPLEMENTATIONS:
                agent_class = CONSULTING_IMPLEMENTATIONS[agent_id]
                self.registry.register(agent_id, agent_class, config)
            else:
                # Placeholder configuration
                self.registry._configs[agent_id] = config

    def create_agent(self, agent_id: str, custom_config: Optional[Dict] = None) -> BaseAgent:
        """
        Create an agent instance by ID

        Args:
            agent_id: The agent identifier (e.g., 'A0', 'B1', 'C1')
            custom_config: Optional custom configuration overrides

        Returns:
            Instantiated agent

        Raises:
            ValueError: If agent_id is not registered
        """
        agent_class = self.registry.get_agent_class(agent_id)
        agent_config = self.registry.get_agent_config(agent_id)

        if not agent_class and not agent_config:
            raise ValueError(f"Agent {agent_id} is not registered")

        # If we don't have the actual class yet, use appropriate base class
        if not agent_class:
            if agent_config.layer == "foundation":
                agent_class = FoundationAgent
            elif agent_config.layer == "analysis":
                agent_class = AnalysisAgent
            elif agent_config.layer == "consulting":
                if agent_id in ["C1", "C2", "C3", "C4"]:
                    agent_class = ConfidenceConstrainedAgent
                else:
                    agent_class = ConsultingAgent
            else:
                agent_class = BaseAgent

        # Apply custom config overrides
        if custom_config:
            for key, value in custom_config.items():
                if hasattr(agent_config, key):
                    setattr(agent_config, key, value)

        # Create agent instance with appropriate parameters
        kwargs = {
            "agent_id": agent_config.agent_id,
            "agent_name": agent_config.agent_name
        }

        # Add LLM client if the agent needs it
        llm_capable_agents = ["A2", "A3"] + list(ANALYSIS_IMPLEMENTATIONS.keys()) + list(CONSULTING_IMPLEMENTATIONS.keys())
        if agent_id in llm_capable_agents and agent_id in (list(FOUNDATION_IMPLEMENTATIONS.keys()) +
                                                           list(ANALYSIS_IMPLEMENTATIONS.keys()) +
                                                           list(CONSULTING_IMPLEMENTATIONS.keys())):
            from nps_report_v3.llm import get_llm_client
            try:
                llm_client = get_llm_client()
                kwargs["llm_client"] = llm_client
            except Exception as e:
                logger.warning(f"Could not initialize LLM client for {agent_id}: {e}")

        agent = agent_class(**kwargs)

        # Apply additional configuration
        if hasattr(agent, 'max_retries'):
            agent.max_retries = agent_config.max_retries

        logger.info(f"Created agent {agent_id}: {agent_config.agent_name}")
        return agent

    def register_custom_agent(self, agent_id: str, agent_class: Type[BaseAgent],
                            config: Optional[AgentConfig] = None):
        """
        Register a custom agent implementation

        Args:
            agent_id: Unique identifier for the agent
            agent_class: The agent class implementation
            config: Optional configuration (will create default if not provided)
        """
        if not config:
            # Create default config based on agent class
            layer = "custom"
            if issubclass(agent_class, FoundationAgent):
                layer = "foundation"
            elif issubclass(agent_class, AnalysisAgent):
                layer = "analysis"
            elif issubclass(agent_class, ConsultingAgent):
                layer = "consulting"

            config = AgentConfig(
                agent_id=agent_id,
                agent_name=agent_class.__name__,
                layer=layer
            )

        self.registry.register(agent_id, agent_class, config)

    def create_foundation_agents(self) -> Dict[str, BaseAgent]:
        """Create all foundation layer agents (A0-A3)"""
        agents = {}
        for agent_id in FOUNDATION_AGENTS.keys():
            try:
                agents[agent_id] = self.create_agent(agent_id)
            except Exception as e:
                logger.error(f"Failed to create foundation agent {agent_id}: {e}")
        return agents

    def create_analysis_agents(self) -> Dict[str, BaseAgent]:
        """Create all analysis layer agents (B1-B9)"""
        agents = {}
        for agent_id in ANALYSIS_AGENTS.keys():
            try:
                agents[agent_id] = self.create_agent(agent_id)
            except Exception as e:
                logger.error(f"Failed to create analysis agent {agent_id}: {e}")
        return agents

    def create_consulting_agents(self) -> Dict[str, BaseAgent]:
        """Create all consulting layer agents (C1-C5)"""
        agents = {}
        for agent_id in CONSULTING_AGENTS.keys():
            try:
                agents[agent_id] = self.create_agent(agent_id)
            except Exception as e:
                logger.error(f"Failed to create consulting agent {agent_id}: {e}")
        return agents

    def get_agent_config(self, agent_id: str) -> Optional[AgentConfig]:
        """Get configuration for an agent"""
        return self.registry.get_agent_config(agent_id)

    def list_available_agents(self) -> Dict[str, Dict[str, str]]:
        """List all available agents organized by layer"""
        available = {
            "foundation": {},
            "analysis": {},
            "consulting": {}
        }

        for agent_id, config in self.registry._configs.items():
            if config.layer in available:
                available[config.layer][agent_id] = config.agent_name

        return available


# Singleton instance
_factory_instance = None


def get_factory() -> AgentFactory:
    """Get the singleton factory instance"""
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = AgentFactory()
    return _factory_instance