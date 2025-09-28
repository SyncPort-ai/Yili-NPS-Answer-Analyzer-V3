"""
NPS Report V3 API - Multi-Agent Analysis System

A three-pass, 14-agent system for comprehensive NPS analysis:
- Foundation Pass (A0-A3): Data cleaning, metrics, text analysis, clustering
- Analysis Pass (B1-B9): Domain-specific deep analysis
- Consulting Pass (C1-C5): Strategic recommendations and reporting

Version: 3.0.0
"""

__version__ = "3.0.0"

# Core components
from .workflow.orchestrator import WorkflowOrchestrator
from .config import get_settings, Settings
from .state import NPSAnalysisState, create_initial_state

# Agent factory
from .agents.factory import AgentFactory

# Schemas
from .schemas import (
    NPSAnalysisRequest,
    NPSAnalysisResponse,
    SurveyResponseInput
)

# Utilities
from .checkpoint import CheckpointManager, get_checkpoint_manager
from .cache import CacheManager, get_cache_manager
try:
    from .monitoring import WorkflowProfiler
except ImportError:
    WorkflowProfiler = None

__all__ = [
    # Version
    "__version__",

    # Core
    "WorkflowOrchestrator",
    "get_settings",
    "Settings",
    "NPSAnalysisState",
    "create_initial_state",

    # Agents
    "AgentFactory",

    # Schemas
    "NPSAnalysisRequest",
    "NPSAnalysisResponse",
    "SurveyResponseInput",

    # Utilities
    "CheckpointManager",
    "get_checkpoint_manager",
    "CacheManager",
    "get_cache_manager"
]

# Add WorkflowProfiler if available
if WorkflowProfiler:
    __all__.append("WorkflowProfiler")