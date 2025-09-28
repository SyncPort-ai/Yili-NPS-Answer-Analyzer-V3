"""
NPS Analysis Core Library
=========================

A professional NPS analysis library for internal use within Yili Group systems.
Provides direct function calls without HTTP overhead for maximum performance.

Core Components:
- NPSAnalyzer: Main analysis engine with V1/V2 workflows
- TextAnalyzer: Traditional text analysis (cleaning-labeling-clustering)
- NPSCalculator: Statistical NPS calculations and distributions
- WorkflowManager: Multi-agent workflow orchestration

Usage:
    from nps_analysis import NPSAnalyzer
    
    analyzer = NPSAnalyzer()
    result = analyzer.analyze_survey_responses(survey_data)
"""

from .core import NPSAnalyzer
from .text_analyzer import TextAnalyzer  
from .nps_calculator import NPSCalculator
from .workflows import WorkflowManager
from .exceptions import (
    NPSAnalysisError,
    ModelCallError, 
    LabelingError,
    EmbeddingError,
    WorkflowError
)

__version__ = "1.0.0"
__author__ = "Yili Group AI Team"

# Main entry point for most use cases
analyze_survey_responses = NPSAnalyzer().analyze_survey_responses
analyze_text_responses = TextAnalyzer().analyze_comments
calculate_nps_distribution = NPSCalculator().calculate_from_scores

__all__ = [
    # Main classes
    "NPSAnalyzer",
    "TextAnalyzer", 
    "NPSCalculator",
    "WorkflowManager",
    
    # Convenience functions
    "analyze_survey_responses",
    "analyze_text_responses", 
    "calculate_nps_distribution",
    
    # Exceptions
    "NPSAnalysisError",
    "ModelCallError",
    "LabelingError", 
    "EmbeddingError",
    "WorkflowError",
]