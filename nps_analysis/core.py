"""
Core NPS Analysis Engine
========================

Main NPSAnalyzer class providing unified interface for all analysis workflows.
Designed for internal use with direct function calls - no HTTP overhead.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass
from datetime import datetime
import pandas as pd

from .exceptions import NPSAnalysisError, WorkflowError, ValidationError
from .text_analyzer import TextAnalyzer
from .nps_calculator import NPSCalculator
from .workflows import WorkflowManager

logger = logging.getLogger(__name__)


@dataclass
class SurveyResponse:
    """Individual survey response data structure."""
    score: int
    comment: Optional[str] = None
    customer_id: Optional[str] = None
    timestamp: Optional[str] = None
    region: Optional[str] = None
    age_group: Optional[str] = None
    
    def __post_init__(self):
        if not isinstance(self.score, int) or self.score < 0 or self.score > 10:
            raise ValidationError("Score must be an integer between 0 and 10", {"score": self.score})


@dataclass
class AnalysisResult:
    """Comprehensive analysis result with all workflow outputs."""
    nps_score: float
    distribution: Dict[str, int]
    total_responses: int
    promoters: int
    passives: int
    detractors: int
    text_analysis: Optional[Dict[str, Any]] = None
    workflow_results: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    processing_time: Optional[float] = None
    timestamp: Optional[str] = None


class NPSAnalyzer:
    """
    Main NPS Analysis Engine
    
    Provides unified interface for all NPS analysis workflows:
    - Basic NPS calculation and distribution analysis
    - V1 multi-agent workflow (LangGraph-based)
    - V2 seven-agent enhanced analysis
    - Traditional text analysis (cleaning-labeling-clustering)
    
    Usage:
        analyzer = NPSAnalyzer()
        result = analyzer.analyze_survey_responses(survey_data)
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize NPS analyzer with optional configuration.
        
        Args:
            config: Optional configuration dictionary with:
                - llm_provider: 'openai' or 'yili' (default: 'openai')
                - enable_v1_workflow: bool (default: True)
                - enable_v2_workflow: bool (default: True)
                - enable_text_analysis: bool (default: True)
                - timeout_seconds: int (default: 300)
        """
        self.config = config or {}
        self.text_analyzer = TextAnalyzer(self.config)
        self.nps_calculator = NPSCalculator()
        self.workflow_manager = WorkflowManager(self.config)
        
        logger.info("NPSAnalyzer initialized with config: %s", self.config)
    
    def analyze_survey_responses(
        self,
        responses: Union[List[Dict[str, Any]], List[SurveyResponse], pd.DataFrame],
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Comprehensive analysis of survey responses.
        
        Args:
            responses: Survey responses in various formats:
                - List of dicts: [{"score": 9, "comment": "Great!"}, ...]
                - List of SurveyResponse objects
                - pandas DataFrame with required columns
            analysis_options: Optional analysis configuration:
                - include_text_analysis: bool (default: True)
                - include_v1_workflow: bool (default: False)  
                - include_v2_workflow: bool (default: False)
                - workflow_timeout: int (default: 300)
        
        Returns:
            AnalysisResult: Comprehensive analysis with NPS metrics and insights
            
        Raises:
            ValidationError: If input data is invalid
            NPSAnalysisError: If analysis fails
        """
        start_time = datetime.now()
        options = analysis_options or {}
        
        try:
            # Validate and normalize input
            normalized_responses = self._normalize_responses(responses)
            
            if not normalized_responses:
                raise ValidationError("No valid responses provided", {"count": len(responses)})
            
            logger.info("Analyzing %d survey responses", len(normalized_responses))
            
            # Calculate basic NPS metrics
            nps_metrics = self.nps_calculator.calculate_from_responses(normalized_responses)
            
            # Optional text analysis
            text_analysis = None
            if options.get("include_text_analysis", True):
                comments = [r.comment for r in normalized_responses if r.comment and r.comment.strip()]
                if comments:
                    text_analysis = self.text_analyzer.analyze_comments(comments)
            
            # Optional workflow analysis
            workflow_results = None
            if options.get("include_v1_workflow") or options.get("include_v2_workflow"):
                workflow_results = self._run_workflows(normalized_responses, options)
            
            # Build comprehensive result
            processing_time = (datetime.now() - start_time).total_seconds()
            
            result = AnalysisResult(
                nps_score=nps_metrics["nps_score"],
                distribution=nps_metrics["distribution"], 
                total_responses=nps_metrics["total_responses"],
                promoters=nps_metrics["promoters"],
                passives=nps_metrics["passives"],
                detractors=nps_metrics["detractors"],
                text_analysis=text_analysis,
                workflow_results=workflow_results,
                metadata={
                    "analysis_options": options,
                    "config": self.config
                },
                processing_time=processing_time,
                timestamp=start_time.isoformat()
            )
            
            logger.info("Analysis completed in %.2f seconds", processing_time)
            return result
            
        except Exception as e:
            logger.error("Analysis failed: %s", e)
            if isinstance(e, NPSAnalysisError):
                raise
            raise NPSAnalysisError("Survey analysis failed", cause=e)
    
    def calculate_nps_only(
        self, 
        responses: Union[List[Dict[str, Any]], List[SurveyResponse], pd.DataFrame]
    ) -> Dict[str, Any]:
        """
        Fast NPS calculation without additional analysis.
        
        Args:
            responses: Survey responses with score field
            
        Returns:
            Dict with NPS metrics: nps_score, distribution, promoters, passives, detractors
        """
        try:
            normalized_responses = self._normalize_responses(responses)
            return self.nps_calculator.calculate_from_responses(normalized_responses)
        except Exception as e:
            raise NPSAnalysisError("NPS calculation failed", cause=e)
    
    async def analyze_survey_responses_async(
        self,
        responses: Union[List[Dict[str, Any]], List[SurveyResponse], pd.DataFrame],
        analysis_options: Optional[Dict[str, Any]] = None
    ) -> AnalysisResult:
        """
        Async version of analyze_survey_responses for concurrent processing.
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, 
            self.analyze_survey_responses, 
            responses, 
            analysis_options
        )
    
    def _normalize_responses(
        self, 
        responses: Union[List[Dict[str, Any]], List[SurveyResponse], pd.DataFrame]
    ) -> List[SurveyResponse]:
        """Convert various input formats to standardized SurveyResponse objects."""
        if isinstance(responses, pd.DataFrame):
            return self._from_dataframe(responses)
        elif isinstance(responses, list):
            if not responses:
                return []
            if isinstance(responses[0], SurveyResponse):
                return responses
            elif isinstance(responses[0], dict):
                return self._from_dict_list(responses)
        
        raise ValidationError("Unsupported response format", {"type": type(responses)})
    
    def _from_dataframe(self, df: pd.DataFrame) -> List[SurveyResponse]:
        """Convert DataFrame to SurveyResponse objects."""
        required_cols = ["score"]
        missing_cols = [col for col in required_cols if col not in df.columns]
        if missing_cols:
            raise ValidationError("Missing required columns", {"missing": missing_cols})
        
        responses = []
        for _, row in df.iterrows():
            responses.append(SurveyResponse(
                score=int(row["score"]),
                comment=row.get("comment"),
                customer_id=row.get("customer_id"),
                timestamp=row.get("timestamp"),
                region=row.get("region"),
                age_group=row.get("age_group")
            ))
        return responses
    
    def _from_dict_list(self, dict_list: List[Dict[str, Any]]) -> List[SurveyResponse]:
        """Convert list of dicts to SurveyResponse objects."""
        responses = []
        for i, data in enumerate(dict_list):
            if "score" not in data:
                raise ValidationError(f"Missing 'score' in response {i}", {"response": data})
            responses.append(SurveyResponse(**data))
        return responses
    
    def _run_workflows(
        self, 
        responses: List[SurveyResponse], 
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute requested workflow analysis."""
        results = {}
        
        try:
            if options.get("include_v1_workflow"):
                logger.info("Running V1 workflow analysis")
                results["v1"] = self.workflow_manager.run_v1_workflow(responses, options)
                
            if options.get("include_v2_workflow"):
                logger.info("Running V2 workflow analysis")  
                results["v2"] = self.workflow_manager.run_v2_workflow(responses, options)
                
            return results
            
        except Exception as e:
            raise WorkflowError("Workflow execution failed", "multi_workflow", cause=e)