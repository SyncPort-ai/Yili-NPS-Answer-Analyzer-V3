"""
Workflow Management
==================

Manages V1 and V2 multi-agent workflows for advanced NPS analysis.
Provides clean interface to complex workflow orchestration.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from .exceptions import WorkflowError, ConfigurationError

logger = logging.getLogger(__name__)


class WorkflowManager:
    """
    Multi-agent workflow orchestration manager.
    
    Provides unified interface to:
    - V1 LangGraph-based multi-agent workflow
    - V2 Seven-agent enhanced analysis workflow
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize workflow manager.
        
        Args:
            config: Configuration with:
                - workflow_timeout: Timeout in seconds (default: 300)
                - enable_v1: Enable V1 workflow (default: True)
                - enable_v2: Enable V2 workflow (default: True)
        """
        self.config = config or {}
        self.timeout = self.config.get("workflow_timeout", 300)
        
        # Import workflow classes with error handling
        self.v1_workflow = self._import_v1_workflow()
        self.v2_workflow = self._import_v2_workflow()
        self.v3_workflow = self._import_v3_workflow()
        
        logger.info("WorkflowManager initialized - V1: %s, V2: %s, V3: %s", 
                   bool(self.v1_workflow), bool(self.v2_workflow), bool(self.v3_workflow))
    
    def run_v1_workflow(
        self, 
        responses: List[Any], 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute V1 multi-agent workflow.
        
        Args:
            responses: List of SurveyResponse objects
            options: Workflow options and parameters
            
        Returns:
            Dict: V1 workflow results with complete analysis
            
        Raises:
            WorkflowError: If V1 workflow execution fails
        """
        if not self.v1_workflow:
            raise WorkflowError("V1 workflow not available", "v1_init")
        
        try:
            logger.info("Starting V1 workflow with %d responses", len(responses))
            
            # Convert responses to V1 format
            survey_data = self._format_for_v1(responses)
            
            # Execute V1 workflow
            workflow = self.v1_workflow()
            result = workflow.process({
                "survey_responses": survey_data,
                "metadata": options.get("metadata", {}),
                "optional_data": options.get("optional_data", {})
            })
            
            logger.info("V1 workflow completed successfully")
            return result
            
        except Exception as e:
            logger.error("V1 workflow failed: %s", e)
            raise WorkflowError("V1 workflow execution failed", "v1_execution", cause=e)
    
    def run_v2_workflow(
        self, 
        responses: List[Any], 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute V2 seven-agent workflow.
        
        Args:
            responses: List of SurveyResponse objects
            options: Workflow options and parameters
            
        Returns:
            Dict: V2 workflow results with enhanced analysis
            
        Raises:
            WorkflowError: If V2 workflow execution fails
        """
        if not self.v2_workflow:
            raise WorkflowError("V2 workflow not available", "v2_init")
        
        try:
            logger.info("Starting V2 workflow with %d responses", len(responses))
            
            # Convert responses to V2 format
            survey_data = self._format_for_v2(responses, options)
            
            # Execute V2 workflow
            workflow = self.v2_workflow()
            result = workflow.process_nps_data(survey_data)
            
            logger.info("V2 workflow completed successfully")
            return result
            
        except Exception as e:
            logger.error("V2 workflow failed: %s", e)
            raise WorkflowError("V2 workflow execution failed", "v2_execution", cause=e)
    
    def run_v3_workflow(
        self, 
        responses: List[Any], 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute V3 enhanced seven-agent workflow.
        
        Args:
            responses: List of SurveyResponse objects
            options: Workflow options and parameters
            
        Returns:
            Dict: V3 workflow results with enhanced analysis
            
        Raises:
            WorkflowError: If V3 workflow execution fails
        """
        if not self.v3_workflow:
            raise WorkflowError("V3 workflow not available", "v3_init")
        
        try:
            logger.info("Starting V3 enhanced workflow with %d responses", len(responses))
            
            # Convert responses to V3 format (same as V2 but with V3 enhancements)
            survey_data = self._format_for_v2(responses, options)
            
            # Execute V3 workflow
            workflow = self.v3_workflow()
            result = workflow.process_nps_data(survey_data)
            
            # Add V3 metadata
            result["v3_enhancements"] = {
                "isolated_development": True,
                "enhanced_ai_prompts": True,
                "improved_error_handling": True,
                "independent_evolution": True
            }
            
            logger.info("V3 enhanced workflow completed successfully")
            return result
            
        except Exception as e:
            logger.error("V3 workflow failed: %s", e)
            raise WorkflowError("V3 workflow execution failed", "v3_execution", cause=e)
    
    def get_available_workflows(self) -> Dict[str, bool]:
        """
        Check which workflows are available.
        
        Returns:
            Dict: Availability status for each workflow
        """
        return {
            "v1_available": bool(self.v1_workflow),
            "v2_available": bool(self.v2_workflow),
            "v3_available": bool(self.v3_workflow),
            "v1_error": getattr(self, "_v1_import_error", None),
            "v2_error": getattr(self, "_v2_import_error", None),
            "v3_error": getattr(self, "_v3_import_error", None)
        }
    
    def _import_v1_workflow(self):
        """Import V1 workflow with error handling."""
        try:
            from nps_report_v1.workflow import NPSAnalysisWorkflow
            return NPSAnalysisWorkflow
        except ImportError as e:
            self._v1_import_error = str(e)
            logger.warning("V1 workflow not available: %s", e)
            return None
    
    def _import_v2_workflow(self):
        """Import V2 workflow with error handling."""
        try:
            from nps_report_v2.seven_agent_workflow import SevenAgentWorkflow
            return SevenAgentWorkflow
        except ImportError as e:
            self._v2_import_error = str(e)
            logger.warning("V2 workflow not available: %s", e)
            return None
    
    def _import_v3_workflow(self):
        """Import V3 workflow with error handling."""
        try:
            from nps_report_v3.seven_agent_workflow import SevenAgentWorkflow as SevenAgentWorkflowV3
            return SevenAgentWorkflowV3
        except ImportError as e:
            self._v3_import_error = str(e)
            logger.warning("V3 workflow not available: %s", e)
            return None
    
    def _format_for_v1(self, responses: List[Any]) -> List[Dict[str, Any]]:
        """Format responses for V1 workflow."""
        formatted = []
        for response in responses:
            formatted.append({
                "score": response.score,
                "comment": response.comment,
                "customer_id": response.customer_id,
                "timestamp": response.timestamp,
                "region": response.region,
                "age_group": response.age_group
            })
        return formatted
    
    def _format_for_v2(self, responses: List[Any], options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Format responses for V2 workflow."""
        options = options or {}
        
        # Check if Chinese flat format is requested
        if options.get("use_chinese_format", False):
            return self._format_chinese_flat(responses, options)
        
        # Default to legacy format
        return {
            "survey_responses": self._format_for_v1(responses),
            "metadata": options.get("metadata", {"source": "internal_library"}),
            "optional_data": options.get("optional_data", {}),
            "processing_mode": options.get("processing_mode", "enhanced")
        }
    
    def _format_chinese_flat(self, responses: List[Any], options: Dict[str, Any]) -> Dict[str, Any]:
        """Format responses in Chinese flat format for V2."""
        # Convert to Chinese survey format
        response_data = []
        
        for i, response in enumerate(responses):
            response_data.append({
                "response_id": f"resp_{i+1}",
                "response_metadata": {
                    "user_id": response.customer_id or f"user_{i+1}",
                    "status": "已完成",
                    "timing": {
                        "submit_time": response.timestamp or datetime.now().isoformat()
                    }
                },
                "nps_score": {
                    "value": response.score
                },
                "open_responses": {
                    "specific_reasons": {
                        "positive": response.comment if response.score >= 7 else "",
                        "negative": response.comment if response.score <= 6 else ""
                    }
                },
                "demographic_info": {
                    "region": response.region or "未知",
                    "age_group": response.age_group or "未知"
                }
            })
        
        return {
            "yili_survey_data_input": {
                "survey_response_data": {
                    "response_data": response_data,
                    "survey_metadata": {
                        "survey_id": options.get("survey_id", "internal_survey"),
                        "survey_name": options.get("survey_name", "NPS调研"),
                        "total_responses": len(responses)
                    }
                }
            },
            "metadata": options.get("metadata", {"source": "internal_library_chinese"}),
            "processing_mode": options.get("processing_mode", "enhanced")
        }