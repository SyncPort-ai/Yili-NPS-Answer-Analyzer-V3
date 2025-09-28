"""
Data validation schemas for NPS V3 API.
Provides Pydantic models for request/response validation.
"""

from pydantic import BaseModel, Field, validator
try:
    from pydantic import model_validator
except ImportError:
    from pydantic import root_validator as model_validator
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class NPSScore(int):
    """Custom type for NPS score validation"""

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v, validation_info=None):
        if not isinstance(v, (int, float)):
            raise ValueError("NPS score must be a number")

        v = int(v)
        if v < 0 or v > 10:
            raise ValueError("NPS score must be between 0 and 10")

        return v


class LanguageCode(str, Enum):
    """Supported language codes"""
    CHINESE = "zh"
    ENGLISH = "en"


class ReportFormat(str, Enum):
    """Supported report formats"""
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"
    EXCEL = "excel"


class AnalysisEmphasis(str, Enum):
    """Analysis emphasis areas"""
    PRODUCT = "product"
    SERVICE = "service"
    EXPERIENCE = "experience"
    COMPETITIVE = "competitive"
    TECHNICAL = "technical"
    STRATEGIC = "strategic"


# Request schemas

class SurveyResponseInput(BaseModel):
    """Input schema for individual survey response"""

    response_id: Optional[str] = Field(
        None,
        description="Unique response identifier"
    )
    timestamp: Optional[datetime] = Field(
        default_factory=datetime.now,
        description="Response timestamp"
    )
    nps_score: NPSScore = Field(
        ...,
        description="NPS score (0-10)"
    )
    comment: Optional[str] = Field(
        None,
        min_length=1,
        max_length=5000,
        description="Customer comment"
    )
    product_line: Optional[str] = Field(
        None,
        description="Product line (e.g., 安慕希, 金典)"
    )
    customer_segment: Optional[str] = Field(
        None,
        description="Customer segment"
    )
    channel: Optional[str] = Field(
        None,
        description="Feedback channel"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Additional metadata"
    )

    @validator("comment")
    def clean_comment(cls, v):
        """Clean and validate comment"""
        if v:
            # Remove excessive whitespace
            v = " ".join(v.split())
            # Check for minimum meaningful content
            if len(v) < 5:
                raise ValueError("Comment too short to be meaningful")
        return v

    @validator("product_line")
    def validate_product_line(cls, v):
        """Validate product line against known products"""
        known_products = [
            "安慕希", "金典", "舒化", "优酸乳", "味可滋",
            "QQ星", "伊小欢", "巧乐兹", "其他"
        ]

        if v and v not in known_products:
            # Allow but log warning
            print(f"Warning: Unknown product line: {v}")

        return v

    class Config:
        schema_extra = {
            "example": {
                "nps_score": 8,
                "comment": "安慕希酸奶口感很好，但是价格偏高",
                "product_line": "安慕希",
                "customer_segment": "年轻家庭"
            }
        }


class NPSAnalysisRequest(BaseModel):
    """Main request schema for NPS analysis"""

    survey_responses: List[SurveyResponseInput] = Field(
        ...,
        min_items=1,
        max_items=10000,
        description="Survey responses to analyze"
    )
    language: LanguageCode = Field(
        default=LanguageCode.CHINESE,
        description="Analysis language"
    )
    report_formats: List[ReportFormat] = Field(
        default=[ReportFormat.HTML, ReportFormat.JSON],
        description="Desired report formats"
    )
    emphasis_areas: List[AnalysisEmphasis] = Field(
        default=[],
        description="Areas to emphasize in analysis"
    )
    excluded_topics: List[str] = Field(
        default=[],
        description="Topics to exclude from analysis"
    )
    include_competitive_analysis: bool = Field(
        default=True,
        description="Include competitive analysis"
    )
    include_technical_requirements: bool = Field(
        default=True,
        description="Extract technical requirements"
    )
    confidence_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold for insights"
    )
    enable_checkpointing: bool = Field(
        default=True,
        description="Enable workflow checkpointing"
    )
    checkpoint_dir: Optional[str] = Field(
        None,
        description="Custom checkpoint directory"
    )

    @validator("survey_responses")
    def validate_responses(cls, v):
        """Validate survey responses"""
        if not v:
            raise ValueError("At least one survey response required")

        # Check for duplicate response IDs
        ids = [r.response_id for r in v if r.response_id]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate response IDs found")

        # Warn if too many responses without comments
        no_comment_count = sum(1 for r in v if not r.comment)
        if no_comment_count > len(v) * 0.8:
            print(f"Warning: {no_comment_count}/{len(v)} responses have no comments")

        return v

    @model_validator(mode='before')
    def validate_config(cls, values):
        """Cross-field validation"""
        emphasis_areas = values.get("emphasis_areas", [])
        excluded_topics = values.get("excluded_topics", [])

        # Check for conflicts
        if AnalysisEmphasis.COMPETITIVE in emphasis_areas and not values.get("include_competitive_analysis"):
            raise ValueError("Cannot emphasize competitive analysis when it's disabled")

        if AnalysisEmphasis.TECHNICAL in emphasis_areas and not values.get("include_technical_requirements"):
            raise ValueError("Cannot emphasize technical requirements when extraction is disabled")

        return values

    class Config:
        schema_extra = {
            "example": {
                "survey_responses": [
                    {
                        "nps_score": 8,
                        "comment": "产品质量很好，但价格偏高",
                        "product_line": "金典"
                    },
                    {
                        "nps_score": 6,
                        "comment": "配送服务需要改进",
                        "product_line": "安慕希"
                    }
                ],
                "language": "zh",
                "report_formats": ["html", "json"],
                "emphasis_areas": ["product", "service"]
            }
        }


# Response schemas

class NPSMetricsOutput(BaseModel):
    """NPS metrics output schema"""

    nps_score: float = Field(..., ge=-100, le=100)
    promoters_count: int = Field(..., ge=0)
    passives_count: int = Field(..., ge=0)
    detractors_count: int = Field(..., ge=0)
    promoters_percentage: float = Field(..., ge=0, le=100)
    passives_percentage: float = Field(..., ge=0, le=100)
    detractors_percentage: float = Field(..., ge=0, le=100)
    confidence_interval: tuple[float, float]
    sample_size: int = Field(..., ge=0)
    statistical_significance: bool


class InsightOutput(BaseModel):
    """Generic insight output schema"""

    insight_id: str
    category: str
    title: str
    description: str
    confidence: float = Field(..., ge=0, le=1)
    supporting_data: List[str]
    recommendations: List[str]


class ExecutiveSummary(BaseModel):
    """Executive summary output schema"""

    key_findings: List[str]
    nps_overview: NPSMetricsOutput
    top_insights: List[InsightOutput]
    critical_issues: List[str]
    strategic_recommendations: List[str]
    immediate_actions: List[str]


class NPSAnalysisResponse(BaseModel):
    """Main response schema for NPS analysis"""

    workflow_id: str = Field(..., description="Unique workflow identifier")
    status: Literal["completed", "failed", "partial"] = Field(..., description="Analysis status")
    completion_percentage: float = Field(..., ge=0, le=100, description="Completion percentage")

    # Core outputs
    executive_summary: Optional[ExecutiveSummary] = None
    nps_metrics: Optional[NPSMetricsOutput] = None

    # Detailed analysis
    insights: List[InsightOutput] = Field(default_factory=list)
    recommendations: List[Dict[str, Any]] = Field(default_factory=list)
    action_plans: List[Dict[str, Any]] = Field(default_factory=list)

    # Report URLs/paths
    report_urls: Dict[str, str] = Field(
        default_factory=dict,
        description="URLs/paths to generated reports"
    )

    # Quality metrics
    data_quality_score: float = Field(0.0, ge=0, le=1)
    analysis_confidence: float = Field(0.0, ge=0, le=1)

    # Performance metrics
    processing_time_ms: int = Field(..., ge=0)
    tokens_used: int = Field(..., ge=0)

    # Errors and warnings
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)

    class Config:
        schema_extra = {
            "example": {
                "workflow_id": "wf-123456",
                "status": "completed",
                "completion_percentage": 100.0,
                "executive_summary": {
                    "key_findings": ["NPS得分为45，处于良好水平"],
                    "nps_overview": {
                        "nps_score": 45.0,
                        "promoters_count": 60,
                        "sample_size": 100
                    }
                },
                "report_urls": {
                    "html": "/reports/wf-123456.html",
                    "json": "/reports/wf-123456.json"
                }
            }
        }


# Checkpoint schemas

class CheckpointRequest(BaseModel):
    """Request to save checkpoint"""

    workflow_id: str
    phase: str
    state_data: Dict[str, Any]
    compress: bool = True


class CheckpointResponse(BaseModel):
    """Checkpoint save response"""

    checkpoint_id: str
    saved_at: datetime
    size_bytes: int
    compression_ratio: Optional[float]
    file_path: str


class RecoveryRequest(BaseModel):
    """Request to recover from checkpoint"""

    workflow_id: str
    checkpoint_id: Optional[str] = None  # Use latest if not specified
    resume_from_next: bool = True


class RecoveryResponse(BaseModel):
    """Recovery response"""

    checkpoint_id: str
    recovered_phase: str
    next_agent: Optional[str]
    state_data: Dict[str, Any]
    recovery_time_ms: int


# Validation helpers

def validate_chinese_text(text: str, min_length: int = 5, max_length: int = 5000) -> str:
    """
    Validate Chinese text input.

    Args:
        text: Text to validate
        min_length: Minimum text length
        max_length: Maximum text length

    Returns:
        Validated text

    Raises:
        ValueError: If validation fails
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    text = text.strip()

    if len(text) < min_length:
        raise ValueError(f"Text too short (min {min_length} characters)")

    if len(text) > max_length:
        raise ValueError(f"Text too long (max {max_length} characters)")

    # Check for basic Chinese characters (simplified and traditional)
    chinese_chars = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')

    # Warn if no Chinese characters detected
    if chinese_chars == 0 and len(text) > 20:
        print(f"Warning: No Chinese characters detected in text: {text[:50]}...")

    return text


def validate_product_line(product: str) -> str:
    """
    Validate and normalize product line name.

    Args:
        product: Product line name

    Returns:
        Normalized product name
    """
    # Product name mapping
    product_map = {
        "amx": "安慕希",
        "anmuxi": "安慕希",
        "金典": "金典",
        "jindian": "金典",
        "舒化": "舒化",
        "shuhua": "舒化",
        "优酸乳": "优酸乳",
        "yousuan": "优酸乳",
        "味可滋": "味可滋",
        "weikezi": "味可滋",
        "qq星": "QQ星",
        "qqxing": "QQ星",
        "伊小欢": "伊小欢",
        "yixiaohuan": "伊小欢",
        "巧乐兹": "巧乐兹",
        "qiaolezi": "巧乐兹"
    }

    # Normalize
    product_lower = product.lower().strip()

    # Try to map
    if product_lower in product_map:
        return product_map[product_lower]

    # Return original if not found
    return product


def validate_nps_batch(responses: List[Dict[str, Any]]) -> tuple[List[Dict], List[str]]:
    """
    Validate batch of NPS responses.

    Args:
        responses: Raw response data

    Returns:
        Tuple of (valid_responses, errors)
    """
    valid_responses = []
    errors = []

    for idx, response in enumerate(responses):
        try:
            # Validate using Pydantic
            validated = SurveyResponseInput(**response)
            valid_responses.append(validated.dict())
        except Exception as e:
            errors.append(f"Response {idx}: {str(e)}")

    return valid_responses, errors