"""
NPS报告分析系统V2 - 双输入模式检测器
负责自动检测和路由不同类型的输入数据
"""

import json
import pandas as pd
from typing import Dict, Any, Union, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


class InputMode(Enum):
    """输入模式枚举"""
    RAW_QUESTIONNAIRE = "raw_questionnaire"
    PREPROCESSED_ANALYSIS = "preprocessed_analysis"
    UNKNOWN = "unknown"


class QuestionnaireType(Enum):
    """问卷类型枚举"""
    GENERAL_NPS = "general_nps"
    CONCEPT_TEST = "concept_test"
    TASTE_TEST = "taste_test"
    PACKAGE_TEST = "package_test"
    BRAND_EVALUATION = "brand_evaluation"
    PRODUCT_COMPARISON = "product_comparison"
    UNKNOWN = "unknown"


@dataclass
class InputDetectionResult:
    """输入检测结果"""
    mode: InputMode
    questionnaire_type: Optional[QuestionnaireType] = None
    confidence: float = 0.0
    data_structure: Dict[str, Any] = None
    validation_errors: List[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.validation_errors is None:
            self.validation_errors = []
        if self.data_structure is None:
            self.data_structure = {}
        if self.metadata is None:
            self.metadata = {}


class InputModeDetector:
    """双输入模式检测器"""
    
    def __init__(self):
        """初始化检测器"""
        self.raw_questionnaire_indicators = {
            # Excel文件结构指标
            'excel_columns': [
                '问卷编号', '完成时间', '用户ID', '推荐分数', 'NPS得分',
                '年龄', '性别', '地区', '收入', '教育程度',
                '品牌偏好', '购买频次', '使用时长', '满意度',
                '开放性问题', '建议', '不满意原因', '推荐理由'
            ],
            # 数据内容指标
            'data_patterns': [
                r'\d{4}-\d{2}-\d{2}',  # 日期格式
                r'[0-9]{1,2}分',        # 评分格式
                r'很好|一般|不好',       # 评价词汇
                r'推荐|不推荐',          # 推荐状态
                r'男|女',               # 性别
                r'[1-9]\d{0,1}岁'       # 年龄格式
            ]
        }
        
        self.preprocessed_indicators = {
            # JSON结构指标
            'required_fields': [
                'base_analysis_result',
                'nps_analysis_result'
            ],
            'optional_fields': [
                'cross_analysis_result',
                'kano_analysis_result', 
                'psm_analysis_result',
                'maxdiff_analysis_result'
            ],
            # 分析结果特征
            'analysis_patterns': [
                r'NPS值为[+-]?\d+\.?\d*',
                r'推荐者.*?占比.*?\d+%',
                r'贬损者.*?占比.*?\d+%',
                r'主要原因.*?占比.*?\d+%'
            ]
        }
        
        self.questionnaire_type_patterns = {
            QuestionnaireType.GENERAL_NPS: [
                '净推荐值', 'NPS调研', '推荐度', '整体满意度'
            ],
            QuestionnaireType.CONCEPT_TEST: [
                '概念测试', '产品概念', '创意评估', '概念吸引力'
            ],
            QuestionnaireType.TASTE_TEST: [
                '口味测试', '味觉评估', '口感', '风味', '甜度', '酸度'
            ],
            QuestionnaireType.PACKAGE_TEST: [
                '包装测试', '包装设计', '外观评价', '包装吸引力'
            ],
            QuestionnaireType.BRAND_EVALUATION: [
                '品牌评估', '品牌形象', '品牌认知', '品牌偏好'
            ],
            QuestionnaireType.PRODUCT_COMPARISON: [
                '产品对比', '竞品分析', '产品比较', '优劣对比'
            ]
        }

    def detect_input_mode(self, data: Union[str, Dict, pd.DataFrame]) -> InputDetectionResult:
        """
        检测输入数据模式
        
        Args:
            data: 输入数据，可以是文件路径、字典或DataFrame
            
        Returns:
            InputDetectionResult: 检测结果
        """
        try:
            # 数据预处理
            processed_data = self._preprocess_data(data)
            
            # 检测输入模式
            if self._is_excel_questionnaire(processed_data):
                mode = InputMode.RAW_QUESTIONNAIRE
                questionnaire_type = self._detect_questionnaire_type(processed_data)
                confidence = self._calculate_raw_confidence(processed_data)
            elif self._is_preprocessed_analysis(processed_data):
                mode = InputMode.PREPROCESSED_ANALYSIS
                questionnaire_type = None
                confidence = self._calculate_preprocessed_confidence(processed_data)
            else:
                mode = InputMode.UNKNOWN
                questionnaire_type = None
                confidence = 0.0
            
            # 数据结构分析
            data_structure = self._analyze_data_structure(processed_data)
            
            # 验证错误检查
            validation_errors = self._validate_data(processed_data, mode)
            
            # 元数据提取
            metadata = self._extract_metadata(processed_data, mode)
            
            return InputDetectionResult(
                mode=mode,
                questionnaire_type=questionnaire_type,
                confidence=confidence,
                data_structure=data_structure,
                validation_errors=validation_errors,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"输入模式检测失败: {str(e)}")
            return InputDetectionResult(
                mode=InputMode.UNKNOWN,
                confidence=0.0,
                validation_errors=[f"检测过程中出现错误: {str(e)}"]
            )

    def _preprocess_data(self, data: Union[str, Dict, pd.DataFrame]) -> Dict[str, Any]:
        """预处理输入数据"""
        if isinstance(data, str):
            # 假设是文件路径
            if data.endswith('.xlsx') or data.endswith('.xls'):
                df = pd.read_excel(data)
                return {
                    'type': 'excel',
                    'data': df,
                    'columns': df.columns.tolist(),
                    'shape': df.shape,
                    'sample_data': df.head().to_dict('records') if not df.empty else []
                }
            elif data.endswith('.json'):
                with open(data, 'r', encoding='utf-8') as f:
                    json_data = json.load(f)
                return {
                    'type': 'json',
                    'data': json_data,
                    'keys': list(json_data.keys()) if isinstance(json_data, dict) else [],
                    'sample_data': json_data
                }
        elif isinstance(data, dict):
            return {
                'type': 'dict',
                'data': data,
                'keys': list(data.keys()),
                'sample_data': data
            }
        elif isinstance(data, pd.DataFrame):
            return {
                'type': 'dataframe',
                'data': data,
                'columns': data.columns.tolist(),
                'shape': data.shape,
                'sample_data': data.head().to_dict('records') if not data.empty else []
            }
        else:
            return {
                'type': 'unknown',
                'data': data,
                'sample_data': data
            }

    def _is_excel_questionnaire(self, processed_data: Dict[str, Any]) -> bool:
        """判断是否为Excel格式的原始问卷数据"""
        if processed_data.get('type') not in ['excel', 'dataframe']:
            return False
        
        columns = processed_data.get('columns', [])
        if not columns:
            return False
        
        # 检查是否包含问卷特征列
        questionnaire_indicators = 0
        for indicator in self.raw_questionnaire_indicators['excel_columns']:
            for col in columns:
                if indicator in str(col):
                    questionnaire_indicators += 1
                    break
        
        # 至少包含3个问卷指标列才认为是问卷数据
        return questionnaire_indicators >= 3

    def _is_preprocessed_analysis(self, processed_data: Dict[str, Any]) -> bool:
        """判断是否为预处理的分析结果"""
        if processed_data.get('type') not in ['dict', 'json']:
            return False
        
        data = processed_data.get('data', {})
        if not isinstance(data, dict):
            return False
        
        # 检查必需字段
        required_fields = self.preprocessed_indicators['required_fields']
        has_required = sum(1 for field in required_fields if field in data)
        
        # 检查分析结果模式
        analysis_patterns = 0
        for key, value in data.items():
            if isinstance(value, str):
                import re
                for pattern in self.preprocessed_indicators['analysis_patterns']:
                    if re.search(pattern, value):
                        analysis_patterns += 1
                        break
        
        # 必须包含至少1个必需字段且包含分析模式
        return has_required >= 1 and analysis_patterns >= 1

    def _detect_questionnaire_type(self, processed_data: Dict[str, Any]) -> QuestionnaireType:
        """检测问卷类型"""
        # 获取文本内容进行模式匹配
        text_content = ""
        
        if processed_data.get('type') in ['excel', 'dataframe']:
            columns = processed_data.get('columns', [])
            sample_data = processed_data.get('sample_data', [])
            text_content = " ".join(str(col) for col in columns)
            if sample_data:
                text_content += " " + " ".join(str(val) for row in sample_data for val in row.values())
        
        # 模式匹配
        max_matches = 0
        detected_type = QuestionnaireType.UNKNOWN
        
        for q_type, patterns in self.questionnaire_type_patterns.items():
            matches = sum(1 for pattern in patterns if pattern in text_content)
            if matches > max_matches:
                max_matches = matches
                detected_type = q_type
        
        return detected_type if max_matches > 0 else QuestionnaireType.UNKNOWN

    def _calculate_raw_confidence(self, processed_data: Dict[str, Any]) -> float:
        """计算原始问卷数据的置信度"""
        if processed_data.get('type') not in ['excel', 'dataframe']:
            return 0.0
        
        columns = processed_data.get('columns', [])
        shape = processed_data.get('shape', (0, 0))
        
        confidence = 0.0
        
        # 列名匹配度 (40%)
        column_matches = 0
        for indicator in self.raw_questionnaire_indicators['excel_columns']:
            for col in columns:
                if indicator in str(col):
                    column_matches += 1
                    break
        
        if len(self.raw_questionnaire_indicators['excel_columns']) > 0:
            confidence += (column_matches / len(self.raw_questionnaire_indicators['excel_columns'])) * 0.4
        
        # 数据规模合理性 (30%)
        rows, cols = shape
        if rows >= 10 and cols >= 5:  # 至少10行5列
            confidence += 0.3
        elif rows >= 5 and cols >= 3:  # 至少5行3列
            confidence += 0.15
        
        # 数据完整性 (30%)
        sample_data = processed_data.get('sample_data', [])
        if sample_data:
            non_null_ratio = sum(1 for row in sample_data for val in row.values() if val is not None) / (len(sample_data) * len(columns)) if columns else 0
            confidence += non_null_ratio * 0.3
        
        return min(confidence, 1.0)

    def _calculate_preprocessed_confidence(self, processed_data: Dict[str, Any]) -> float:
        """计算预处理分析结果的置信度"""
        if processed_data.get('type') not in ['dict', 'json']:
            return 0.0
        
        data = processed_data.get('data', {})
        confidence = 0.0
        
        # 必需字段完整性 (50%)
        required_fields = self.preprocessed_indicators['required_fields']
        has_required = sum(1 for field in required_fields if field in data and data[field])
        confidence += (has_required / len(required_fields)) * 0.5
        
        # 分析结果模式匹配 (30%)
        import re
        pattern_matches = 0
        total_patterns = len(self.preprocessed_indicators['analysis_patterns'])
        
        for key, value in data.items():
            if isinstance(value, str):
                for pattern in self.preprocessed_indicators['analysis_patterns']:
                    if re.search(pattern, value):
                        pattern_matches += 1
                        break
        
        if total_patterns > 0:
            confidence += (pattern_matches / total_patterns) * 0.3
        
        # 数据结构完整性 (20%)
        optional_fields = self.preprocessed_indicators['optional_fields']
        has_optional = sum(1 for field in optional_fields if field in data and data[field])
        confidence += (has_optional / len(optional_fields)) * 0.2
        
        return min(confidence, 1.0)

    def _analyze_data_structure(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析数据结构"""
        data_type = processed_data.get('type', 'unknown')
        
        structure = {
            'data_type': data_type,
            'size': 0,
            'fields': [],
            'data_types': {},
            'missing_values': {}
        }
        
        if data_type in ['excel', 'dataframe']:
            shape = processed_data.get('shape', (0, 0))
            columns = processed_data.get('columns', [])
            structure.update({
                'size': shape[0],
                'fields': columns,
                'dimensions': {'rows': shape[0], 'columns': shape[1]}
            })
            
        elif data_type in ['dict', 'json']:
            data = processed_data.get('data', {})
            structure.update({
                'size': len(data),
                'fields': list(data.keys()),
                'nested_structure': self._analyze_nested_structure(data)
            })
        
        return structure

    def _analyze_nested_structure(self, data: Dict, max_depth: int = 3) -> Dict[str, Any]:
        """分析嵌套数据结构"""
        if max_depth <= 0:
            return {}
        
        structure = {}
        for key, value in data.items():
            if isinstance(value, dict):
                structure[key] = {
                    'type': 'dict',
                    'keys': list(value.keys()),
                    'nested': self._analyze_nested_structure(value, max_depth - 1)
                }
            elif isinstance(value, list):
                structure[key] = {
                    'type': 'list',
                    'length': len(value),
                    'item_types': list(set(type(item).__name__ for item in value[:5]))
                }
            else:
                structure[key] = {
                    'type': type(value).__name__,
                    'value_length': len(str(value)) if value else 0
                }
        
        return structure

    def _validate_data(self, processed_data: Dict[str, Any], mode: InputMode) -> List[str]:
        """验证数据完整性和格式"""
        errors = []
        
        if mode == InputMode.RAW_QUESTIONNAIRE:
            errors.extend(self._validate_raw_questionnaire(processed_data))
        elif mode == InputMode.PREPROCESSED_ANALYSIS:
            errors.extend(self._validate_preprocessed_analysis(processed_data))
        
        return errors

    def _validate_raw_questionnaire(self, processed_data: Dict[str, Any]) -> List[str]:
        """验证原始问卷数据"""
        errors = []
        
        # 检查数据规模
        shape = processed_data.get('shape', (0, 0))
        if shape[0] < 5:
            errors.append("问卷数据样本量过小，至少需要5个样本")
        
        if shape[1] < 3:
            errors.append("问卷数据字段过少，至少需要3个字段")
        
        # 检查必要字段
        columns = processed_data.get('columns', [])
        has_nps_score = any('推荐' in str(col) or 'NPS' in str(col) or '得分' in str(col) for col in columns)
        if not has_nps_score:
            errors.append("缺少NPS得分相关字段")
        
        return errors

    def _validate_preprocessed_analysis(self, processed_data: Dict[str, Any]) -> List[str]:
        """验证预处理分析结果"""
        errors = []
        
        data = processed_data.get('data', {})
        
        # 检查必需字段
        required_fields = self.preprocessed_indicators['required_fields']
        for field in required_fields:
            if field not in data:
                errors.append(f"缺少必需字段: {field}")
            elif not data[field]:
                errors.append(f"必需字段为空: {field}")
        
        # 检查分析结果格式
        if 'nps_analysis_result' in data:
            nps_result = data['nps_analysis_result']
            if isinstance(nps_result, str):
                import re
                if not re.search(r'NPS值', nps_result):
                    errors.append("NPS分析结果格式不正确，缺少NPS值")
        
        return errors

    def _extract_metadata(self, processed_data: Dict[str, Any], mode: InputMode) -> Dict[str, Any]:
        """提取元数据信息"""
        metadata = {
            'detection_time': pd.Timestamp.now().isoformat(),
            'input_mode': mode.value,
            'data_type': processed_data.get('type', 'unknown')
        }
        
        if mode == InputMode.RAW_QUESTIONNAIRE:
            shape = processed_data.get('shape', (0, 0))
            metadata.update({
                'sample_count': shape[0],
                'field_count': shape[1],
                'columns': processed_data.get('columns', [])
            })
            
        elif mode == InputMode.PREPROCESSED_ANALYSIS:
            data = processed_data.get('data', {})
            metadata.update({
                'analysis_fields': list(data.keys()),
                'has_base_analysis': 'base_analysis_result' in data,
                'has_nps_analysis': 'nps_analysis_result' in data,
                'additional_analyses': [k for k in data.keys() if k not in self.preprocessed_indicators['required_fields']]
            })
        
        return metadata

    def route_data(self, detection_result: InputDetectionResult, data: Any) -> Tuple[str, Dict[str, Any]]:
        """
        根据检测结果路由数据到相应的处理器
        
        Args:
            detection_result: 检测结果
            data: 原始数据
            
        Returns:
            Tuple[str, Dict]: (处理器名称, 路由配置)
        """
        if detection_result.mode == InputMode.RAW_QUESTIONNAIRE:
            processor = "RawQuestionnaireProcessor"
            config = {
                'questionnaire_type': detection_result.questionnaire_type.value if detection_result.questionnaire_type else 'unknown',
                'confidence': detection_result.confidence,
                'validation_errors': detection_result.validation_errors,
                'metadata': detection_result.metadata
            }
        elif detection_result.mode == InputMode.PREPROCESSED_ANALYSIS:
            processor = "PreprocessedAnalysisProcessor"
            config = {
                'confidence': detection_result.confidence,
                'validation_errors': detection_result.validation_errors,
                'metadata': detection_result.metadata
            }
        else:
            processor = "ErrorHandler"
            config = {
                'error': "未知输入模式",
                'detection_result': detection_result.__dict__
            }
        
        return processor, config