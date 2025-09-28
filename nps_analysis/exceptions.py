"""
Exception classes for NPS Analysis Library
==========================================

Professional exception hierarchy with detailed error information.
Following FAIL-FAST principle with comprehensive error context.
"""

class NPSAnalysisError(Exception):
    """Base exception for all NPS analysis errors."""
    
    def __init__(self, message: str, details: dict = None, cause: Exception = None):
        self.message = message
        self.details = details or {}
        self.cause = cause
        super().__init__(self.message)
    
    def __str__(self):
        result = self.message
        if self.details:
            result += f" | Details: {self.details}"
        if self.cause:
            result += f" | Caused by: {self.cause}"
        return result


class ModelCallError(NPSAnalysisError):
    """Raised when LLM model calls fail."""
    
    def __init__(self, message: str, stage: str, model_details: dict = None, cause: Exception = None):
        self.stage = stage
        self.model_details = model_details or {}
        details = {"stage": stage, "model_details": self.model_details}
        super().__init__(message, details, cause)


class LabelingError(NPSAnalysisError):
    """Raised when text labeling/annotation fails."""
    
    def __init__(self, message: str, text_sample: str = None, cause: Exception = None):
        details = {"text_sample": text_sample[:100] if text_sample else None}
        super().__init__(message, details, cause)


class EmbeddingError(NPSAnalysisError):
    """Raised when text embedding generation fails."""
    
    def __init__(self, message: str, embedding_details: dict = None, cause: Exception = None):
        super().__init__(message, embedding_details or {}, cause)


class WorkflowError(NPSAnalysisError):
    """Raised when multi-agent workflow execution fails."""
    
    def __init__(self, message: str, workflow_stage: str, agent_info: dict = None, cause: Exception = None):
        self.workflow_stage = workflow_stage
        details = {"workflow_stage": workflow_stage, "agent_info": agent_info or {}}
        super().__init__(message, details, cause)


class ValidationError(NPSAnalysisError):
    """Raised when input data validation fails."""
    
    def __init__(self, message: str, validation_details: dict = None, cause: Exception = None):
        super().__init__(message, validation_details or {}, cause)


class ConfigurationError(NPSAnalysisError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(self, message: str, config_section: str = None, cause: Exception = None):
        details = {"config_section": config_section} if config_section else {}
        super().__init__(message, details, cause)