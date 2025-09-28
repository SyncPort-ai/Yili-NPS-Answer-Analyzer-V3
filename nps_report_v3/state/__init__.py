"""
State management module for NPS V3 API.
"""

from .state_definition import (
    # Enums
    WorkflowPhase,
    AgentStatus,
    DataQuality,
    ConfidenceLevel,

    # Type definitions
    SurveyResponse,
    CleanedData,
    NPSMetrics,
    TaggedResponse,
    SemanticCluster,
    TechnicalRequirement,
    BusinessInsight,
    CompetitiveInsight,
    MarketTrend,
    StrategicRecommendation,
    ProductRecommendation,
    ActionPlan,
    AgentOutput,
    CheckpointMetadata,
    NPSAnalysisState,
    PassTransition,
    StateValidation,

    # Functions
    create_initial_state,
    validate_state,
    merge_states,
    get_phase_agents
)

__all__ = [
    # Enums
    "WorkflowPhase",
    "AgentStatus",
    "DataQuality",
    "ConfidenceLevel",

    # Type definitions
    "SurveyResponse",
    "CleanedData",
    "NPSMetrics",
    "TaggedResponse",
    "SemanticCluster",
    "TechnicalRequirement",
    "BusinessInsight",
    "CompetitiveInsight",
    "MarketTrend",
    "StrategicRecommendation",
    "ProductRecommendation",
    "ActionPlan",
    "AgentOutput",
    "CheckpointMetadata",
    "NPSAnalysisState",
    "PassTransition",
    "StateValidation",

    # Functions
    "create_initial_state",
    "validate_state",
    "merge_states",
    "get_phase_agents"
]