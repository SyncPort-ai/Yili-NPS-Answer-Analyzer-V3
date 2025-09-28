"""
State definition for NPS V3 API workflow.
Defines the shared state structure used across all agents and passes.
"""

from typing import TypedDict, List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class WorkflowPhase(str, Enum):
    """Workflow execution phases"""
    INITIALIZATION = "initialization"
    FOUNDATION_PASS = "foundation_pass"
    ANALYSIS_PASS = "analysis_pass"
    CONSULTING_PASS = "consulting_pass"
    FINALIZATION = "finalization"
    COMPLETED = "completed"
    FAILED = "failed"


class AgentStatus(str, Enum):
    """Agent execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class DataQuality(str, Enum):
    """Data quality levels"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INSUFFICIENT = "insufficient"


class ConfidenceLevel(str, Enum):
    """Confidence levels for analysis results"""
    VERY_HIGH = "very_high"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    VERY_LOW = "very_low"


class SurveyResponse(TypedDict):
    """Individual survey response"""
    response_id: str
    timestamp: datetime
    nps_score: int  # 0-10
    comment: Optional[str]
    product_line: Optional[str]
    customer_segment: Optional[str]
    channel: Optional[str]
    metadata: Optional[Dict[str, Any]]


class CleanedData(TypedDict):
    """Cleaned and validated data"""
    total_responses: int
    valid_responses: int
    invalid_responses: int
    cleaned_responses: List[SurveyResponse]
    data_quality: DataQuality
    cleaning_notes: List[str]
    pii_scrubbed: bool


class NPSMetrics(TypedDict):
    """NPS calculation metrics"""
    nps_score: float
    promoters_count: int
    passives_count: int
    detractors_count: int
    promoters_percentage: float
    passives_percentage: float
    detractors_percentage: float
    confidence_interval: tuple[float, float]
    sample_size: int
    statistical_significance: bool


class TaggedResponse(TypedDict, total=False):
    """Response with semantic tags and contextual metadata"""
    response_id: str
    original_text: str
    tags: List[str]
    sentiment: Literal["positive", "negative", "neutral", "mixed"]
    emotion_scores: Dict[str, float]
    key_phrases: List[str]
    nps_score: int
    product_line: Optional[str]
    customer_segment: Optional[str]
    channel: Optional[str]
    metadata: Dict[str, Any]


class SemanticCluster(TypedDict):
    """Semantic cluster of responses"""
    cluster_id: str
    theme: str
    description: str
    response_ids: List[str]
    size: int
    representative_quotes: List[str]
    sentiment_distribution: Dict[str, float]


class TechnicalRequirement(TypedDict):
    """Technical requirement identified"""
    requirement_id: str
    category: str
    description: str
    priority: Literal["critical", "high", "medium", "low"]
    feasibility: Literal["high", "medium", "low", "unknown"]
    related_responses: List[str]
    technical_notes: str


class BusinessInsight(TypedDict):
    """Business insight"""
    insight_id: str
    category: str
    title: str
    description: str
    impact: Literal["strategic", "tactical", "operational"]
    confidence: ConfidenceLevel
    supporting_data: List[str]
    recommendations: List[str]


class CompetitiveInsight(TypedDict):
    """Competitive analysis insight"""
    competitor: str
    comparison_aspect: str
    yili_position: str
    competitor_position: str
    gap_analysis: str
    recommendations: List[str]


class MarketTrend(TypedDict):
    """Market trend identification"""
    trend_id: str
    trend_name: str
    description: str
    relevance_score: float
    time_horizon: Literal["short_term", "medium_term", "long_term"]
    opportunities: List[str]
    threats: List[str]


class StrategicRecommendation(TypedDict):
    """Strategic recommendation"""
    recommendation_id: str
    title: str
    description: str
    rationale: str
    priority: Literal["immediate", "short_term", "medium_term", "long_term"]
    impact_areas: List[str]
    success_metrics: List[str]
    dependencies: List[str]


class ProductRecommendation(TypedDict):
    """Product improvement recommendation"""
    recommendation_id: str
    title: str
    description: str
    category: str  # taste, nutrition, packaging, quality, variety
    priority: Literal["immediate", "short_term", "medium_term", "long_term"]
    impact_areas: List[str]
    success_metrics: List[str]
    target_products: List[str]  # Which Yili products this applies to
    development_effort: Literal["low", "medium", "high"]
    estimated_timeline: str  # e.g., "2-4 months"


class ActionPlan(TypedDict):
    """Detailed action plan"""
    action_id: str
    action_title: str
    description: str
    owner: str
    timeline: str
    resources_required: List[str]
    expected_outcomes: List[str]
    risk_factors: List[str]


class AgentOutput(TypedDict):
    """Standard agent output structure"""
    agent_id: str
    status: AgentStatus
    start_time: datetime
    end_time: Optional[datetime]
    duration_ms: Optional[int]
    output: Dict[str, Any]
    errors: List[str]
    warnings: List[str]
    memory_usage_mb: Optional[float]


class CheckpointMetadata(TypedDict):
    """Checkpoint metadata"""
    checkpoint_id: str
    phase: WorkflowPhase
    timestamp: datetime
    state_size_bytes: int
    compression_ratio: Optional[float]
    agents_completed: List[str]
    next_agent: Optional[str]


class NPSAnalysisState(TypedDict, total=False):
    """
    Complete state definition for NPS analysis workflow.
    Uses total=False to allow partial updates during workflow execution.
    """

    # Workflow metadata
    workflow_id: str
    workflow_phase: WorkflowPhase
    workflow_start_time: datetime
    workflow_end_time: Optional[datetime]
    workflow_version: str

    # Input data
    raw_data: List[Dict[str, Any]]
    input_metadata: Dict[str, Any]

    # Foundation Pass outputs (A0-A3)
    cleaned_data: Optional[CleanedData]
    nps_metrics: Optional[NPSMetrics]
    tagged_responses: Optional[List[TaggedResponse]]
    semantic_clusters: Optional[List[SemanticCluster]]

    # Analysis Pass outputs (B1-B9)
    technical_requirements: Optional[List[TechnicalRequirement]]
    business_insights: Optional[List[BusinessInsight]]
    product_feedback_summary: Optional[Dict[str, Any]]
    service_feedback_summary: Optional[Dict[str, Any]]
    experience_feedback_summary: Optional[Dict[str, Any]]
    competitive_insights: Optional[List[CompetitiveInsight]]
    market_trends: Optional[List[MarketTrend]]
    customer_journey_analysis: Optional[Dict[str, Any]]
    sentiment_evolution: Optional[Dict[str, Any]]

    # Consulting Pass outputs (C1-C5)
    strategic_recommendations: Optional[List[StrategicRecommendation]]
    action_plans: Optional[List[ActionPlan]]
    executive_summary: Optional[str]
    detailed_report: Optional[str]
    visualizations: Optional[Dict[str, Any]]
    next_steps: Optional[List[str]]

    # Agent tracking
    agent_outputs: Dict[str, AgentOutput]
    agent_sequence: List[str]
    current_agent: Optional[str]

    # Quality and confidence metrics
    overall_confidence: Optional[ConfidenceLevel]
    data_quality_score: Optional[float]
    analysis_completeness: Optional[float]
    report_quality_score: Optional[float]

    # Checkpointing
    checkpoints: List[CheckpointMetadata]
    last_checkpoint: Optional[str]
    recovery_point: Optional[str]

    # Performance metrics
    total_tokens_used: int
    total_llm_calls: int
    total_processing_time_ms: int
    memory_peak_mb: float

    # Error handling
    errors: List[Dict[str, Any]]
    warnings: List[Dict[str, Any]]
    retry_count: int
    failed_agents: List[str]

    # Output formats
    output_html: Optional[str]
    output_json: Optional[Dict[str, Any]]
    output_markdown: Optional[str]
    output_excel_path: Optional[str]

    # Business context (from knowledge base)
    business_context: Optional[Dict[str, Any]]
    product_catalog: Optional[Dict[str, Any]]
    historical_benchmarks: Optional[Dict[str, Any]]

    # User preferences
    language: str  # "zh" or "en"
    report_format_preferences: Dict[str, Any]
    emphasis_areas: List[str]
    excluded_topics: List[str]


class PassTransition(TypedDict):
    """State transition between passes"""
    from_phase: WorkflowPhase
    to_phase: WorkflowPhase
    timestamp: datetime
    checkpoint_created: bool
    state_validated: bool
    memory_usage_mb: float
    agents_completed: List[str]
    agents_pending: List[str]


class StateValidation(TypedDict):
    """State validation result"""
    is_valid: bool
    validation_errors: List[str]
    missing_required_fields: List[str]
    invalid_field_types: Dict[str, str]
    data_consistency_issues: List[str]


def create_initial_state(
    workflow_id: str,
    raw_data: List[Dict[str, Any]],
    language: str = "zh",
    **kwargs
) -> NPSAnalysisState:
    """
    Create initial state for workflow execution.

    Args:
        workflow_id: Unique workflow identifier
        raw_data: Input survey data
        language: Language preference ("zh" or "en")
        **kwargs: Additional optional parameters

    Returns:
        Initialized NPSAnalysisState
    """
    return NPSAnalysisState(
        workflow_id=workflow_id,
        workflow_phase=WorkflowPhase.INITIALIZATION,
        workflow_start_time=datetime.now(),
        workflow_version="3.0.0",
        raw_data=raw_data,
        input_metadata=kwargs.get("input_metadata", {}),
        agent_outputs={},
        agent_sequence=[],
        checkpoints=[],
        total_tokens_used=0,
        total_llm_calls=0,
        total_processing_time_ms=0,
        memory_peak_mb=0.0,
        errors=[],
        warnings=[],
        retry_count=0,
        failed_agents=[],
        language=language,
        report_format_preferences=kwargs.get("report_format_preferences", {}),
        emphasis_areas=kwargs.get("emphasis_areas", []),
        excluded_topics=kwargs.get("excluded_topics", [])
    )


def validate_state(state: NPSAnalysisState) -> StateValidation:
    """
    Validate state structure and content.

    Args:
        state: State to validate

    Returns:
        Validation result
    """
    validation = StateValidation(
        is_valid=True,
        validation_errors=[],
        missing_required_fields=[],
        invalid_field_types={},
        data_consistency_issues=[]
    )

    # Check required fields
    required_fields = ["workflow_id", "workflow_phase", "raw_data"]
    for field in required_fields:
        if field not in state or state[field] is None:
            validation["missing_required_fields"].append(field)
            validation["is_valid"] = False

    # Check field types
    if "workflow_phase" in state and not isinstance(state["workflow_phase"], (str, WorkflowPhase)):
        validation["invalid_field_types"]["workflow_phase"] = "Expected str or WorkflowPhase"
        validation["is_valid"] = False

    if "raw_data" in state and not isinstance(state["raw_data"], list):
        validation["invalid_field_types"]["raw_data"] = "Expected list"
        validation["is_valid"] = False

    # Check data consistency
    if "agent_outputs" in state and "agent_sequence" in state:
        completed_agents = set(state["agent_outputs"].keys())
        sequence_agents = set(state["agent_sequence"])

        if not completed_agents.issubset(sequence_agents):
            validation["data_consistency_issues"].append(
                "Agent outputs contain agents not in sequence"
            )
            validation["is_valid"] = False

    # Check phase consistency
    if "workflow_phase" in state:
        phase = state["workflow_phase"]

        if phase == WorkflowPhase.ANALYSIS_PASS:
            # Should have foundation pass outputs
            if not state.get("cleaned_data") or not state.get("nps_metrics"):
                validation["data_consistency_issues"].append(
                    "Analysis pass requires foundation pass outputs"
                )
                validation["is_valid"] = False

        elif phase == WorkflowPhase.CONSULTING_PASS:
            # Should have analysis pass outputs
            if not state.get("business_insights"):
                validation["data_consistency_issues"].append(
                    "Consulting pass requires analysis pass outputs"
                )
                validation["is_valid"] = False

    return validation


def merge_states(
    base_state: NPSAnalysisState,
    updates: Dict[str, Any]
) -> NPSAnalysisState:
    """
    Merge state updates into base state.

    Args:
        base_state: Current state
        updates: Updates to apply

    Returns:
        Updated state
    """
    # Create a copy of base state
    new_state = dict(base_state)

    # Apply updates
    for key, value in updates.items():
        if key in ["agent_outputs", "checkpoints", "errors", "warnings"]:
            # These are cumulative fields
            if key not in new_state:
                new_state[key] = []

            if isinstance(value, list):
                new_state[key].extend(value)
            elif isinstance(value, dict) and key == "agent_outputs":
                new_state[key].update(value)
        else:
            # Direct replacement
            new_state[key] = value

    return NPSAnalysisState(**new_state)


def get_phase_agents(phase: WorkflowPhase) -> List[str]:
    """
    Get list of agents for a specific phase.

    Args:
        phase: Workflow phase

    Returns:
        List of agent IDs
    """
    phase_agents = {
        WorkflowPhase.FOUNDATION_PASS: ["A0", "A1", "A2", "A3"],
        WorkflowPhase.ANALYSIS_PASS: ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"],
        WorkflowPhase.CONSULTING_PASS: ["C1", "C2", "C3", "C4", "C5"]
    }

    return phase_agents.get(phase, [])
