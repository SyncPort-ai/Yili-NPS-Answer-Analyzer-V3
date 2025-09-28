"""
NPS报告分析器 V2.0版本

V2版本主要增强功能：
- 双输入模式支持 (原始问卷数据 + 预处理分析结果)
- 数据质量与可信度评估
- 伊利集团企业知识库集成
- 三大业务域标签体系智能分析
- 业务上下文识别和增强

遵循用户全局指令：内存最小化变更，最大兼容性，确保在Python3上运行。
"""

__version__ = "2.0.0"
__author__ = "伊利-阿里智能体项目组"

from .data_quality_assessment import DataQualityAssessment, ReliabilityMetrics
from .auxiliary_data_manager import AuxiliaryDataManager, BusinessContext, TagAnalysisResult
from .input_mode_detector import InputModeDetector, InputMode, InputDetectionResult
from .questionnaire_classifier import QuestionnaireClassifier, QuestionnaireCategory, ClassificationResult
from .raw_questionnaire_processor import RawQuestionnaireProcessor, ProcessingResult
from .preprocessed_analysis_processor import PreprocessedAnalysisProcessor, EnhancedAnalysisResult

__all__ = [
    "DataQualityAssessment",
    "ReliabilityMetrics", 
    "AuxiliaryDataManager",
    "BusinessContext",
    "TagAnalysisResult",
    "InputModeDetector",
    "InputMode",
    "InputDetectionResult",
    "QuestionnaireClassifier",
    "QuestionnaireCategory",
    "ClassificationResult",
    "RawQuestionnaireProcessor",
    "ProcessingResult",
    "PreprocessedAnalysisProcessor",
    "EnhancedAnalysisResult"
]