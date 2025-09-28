"""
NPS报告分析系统V2 - 原始问卷数据处理器
处理Excel格式的原始问卷数据，包括数据清洗、验证、转换和初步分析
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import logging
from pathlib import Path

from .data_quality_assessment import DataQualityAssessment, ReliabilityMetrics
from .auxiliary_data_manager import AuxiliaryDataManager, BusinessContext
from .questionnaire_classifier import QuestionnaireClassifier, ClassificationResult

logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """原始问卷处理结果"""
    processed_data: pd.DataFrame
    quality_assessment: Dict[str, Any]
    reliability_metrics: ReliabilityMetrics
    classification_result: ClassificationResult
    business_context: BusinessContext
    processing_summary: Dict[str, Any]
    validation_errors: List[str]
    recommendations: List[str]


class RawQuestionnaireProcessor:
    """原始问卷数据处理器"""
    
    def __init__(self, auxiliary_data_path: Optional[str] = None):
        """
        初始化处理器
        
        Args:
            auxiliary_data_path: 辅助数据文件路径
        """
        self.auxiliary_data_path = auxiliary_data_path
        
        # 初始化组件
        self.quality_assessor = DataQualityAssessment()
        self.auxiliary_manager = AuxiliaryDataManager(auxiliary_data_path)
        self.classifier = QuestionnaireClassifier(auxiliary_data_path)
        
        # 数据清洗规则
        self.cleaning_rules = self._initialize_cleaning_rules()
        
        # 标准化映射
        self.standardization_maps = self._initialize_standardization_maps()

    def process_questionnaire(self, 
                            data_source: str,
                            questionnaire_type: Optional[str] = None,
                            processing_options: Optional[Dict[str, Any]] = None) -> ProcessingResult:
        """
        处理原始问卷数据
        
        Args:
            data_source: 数据源路径或数据
            questionnaire_type: 问卷类型提示
            processing_options: 处理选项
            
        Returns:
            ProcessingResult: 处理结果
        """
        try:
            # 1. 数据加载和初步验证
            raw_data = self._load_questionnaire_data(data_source)
            
            # 2. 问卷分类
            classification_result = self.classifier.classify_questionnaire(
                raw_data.to_dict('records') if isinstance(raw_data, pd.DataFrame) else raw_data
            )
            
            # 3. 数据清洗和标准化
            cleaned_data = self._clean_and_standardize_data(raw_data, classification_result)
            
            # 4. 数据质量评估
            quality_assessment = self.quality_assessor.assess_data_quality(cleaned_data)
            
            # 5. 可靠性评估
            reliability_metrics = self.quality_assessor.calculate_reliability_metrics(
                cleaned_data, quality_assessment
            )
            
            # 6. 业务上下文识别
            business_context = self.auxiliary_manager.identify_business_context(
                cleaned_data, classification_result.target_products
            )
            
            # 7. 数据验证
            validation_errors = self._validate_processed_data(cleaned_data, classification_result)
            
            # 8. 处理摘要生成
            processing_summary = self._generate_processing_summary(
                raw_data, cleaned_data, quality_assessment, classification_result
            )
            
            # 9. 改进建议生成
            recommendations = self._generate_recommendations(
                quality_assessment, reliability_metrics, validation_errors
            )
            
            return ProcessingResult(
                processed_data=cleaned_data,
                quality_assessment=quality_assessment,
                reliability_metrics=reliability_metrics,
                classification_result=classification_result,
                business_context=business_context,
                processing_summary=processing_summary,
                validation_errors=validation_errors,
                recommendations=recommendations
            )
            
        except Exception as e:
            logger.error(f"问卷处理失败: {str(e)}")
            raise

    def _load_questionnaire_data(self, data_source: str) -> pd.DataFrame:
        """加载问卷数据"""
        if isinstance(data_source, str):
            if data_source.endswith('.xlsx') or data_source.endswith('.xls'):
                # Excel文件
                df = pd.read_excel(data_source)
            elif data_source.endswith('.csv'):
                # CSV文件
                df = pd.read_csv(data_source, encoding='utf-8')
            else:
                raise ValueError(f"不支持的文件格式: {data_source}")
        elif isinstance(data_source, pd.DataFrame):
            df = data_source.copy()
        else:
            raise ValueError("数据源必须是文件路径或DataFrame")
        
        logger.info(f"成功加载问卷数据: {df.shape[0]} 行, {df.shape[1]} 列")
        return df

    def _initialize_cleaning_rules(self) -> Dict[str, Any]:
        """初始化数据清洗规则"""
        return {
            'remove_test_responses': True,
            'remove_incomplete_responses': True,
            'remove_duplicate_responses': True,
            'remove_extreme_outliers': True,
            'standardize_text_responses': True,
            'validate_numeric_ranges': True,
            'clean_date_formats': True,
            'handle_missing_values': True
        }

    def _initialize_standardization_maps(self) -> Dict[str, Dict[str, Any]]:
        """初始化标准化映射"""
        return {
            'gender_mapping': {
                '男': 'M', '女': 'F', 'Male': 'M', 'Female': 'F',
                'male': 'M', 'female': 'F', '1': 'M', '2': 'F'
            },
            'age_groups': {
                '18-25': '18-25岁', '26-35': '26-35岁', '36-45': '36-45岁',
                '46-55': '46-55岁', '56以上': '56岁以上'
            },
            'education_levels': {
                '高中及以下': '高中及以下', '大专': '大专', '本科': '本科',
                '硕士': '硕士', '博士及以上': '博士及以上'
            },
            'income_levels': {
                '3000以下': '3000元以下', '3000-5000': '3000-5000元',
                '5000-8000': '5000-8000元', '8000-12000': '8000-12000元',
                '12000以上': '12000元以上'
            },
            'satisfaction_scale': {
                '非常不满意': 1, '不满意': 2, '一般': 3, '满意': 4, '非常满意': 5
            },
            'recommendation_scale': {
                '绝对不会推荐': 0, '不太可能推荐': 1, '可能推荐': 2, '很可能推荐': 3, '一定会推荐': 4
            }
        }

    def _clean_and_standardize_data(self, 
                                  raw_data: pd.DataFrame, 
                                  classification_result: ClassificationResult) -> pd.DataFrame:
        """清洗和标准化数据"""
        df = raw_data.copy()
        
        # 1. 移除测试回答
        if self.cleaning_rules['remove_test_responses']:
            df = self._remove_test_responses(df)
        
        # 2. 处理缺失值
        if self.cleaning_rules['handle_missing_values']:
            df = self._handle_missing_values(df)
        
        # 3. 移除重复回答
        if self.cleaning_rules['remove_duplicate_responses']:
            df = self._remove_duplicate_responses(df)
        
        # 4. 标准化文本回答
        if self.cleaning_rules['standardize_text_responses']:
            df = self._standardize_text_responses(df)
        
        # 5. 验证数值范围
        if self.cleaning_rules['validate_numeric_ranges']:
            df = self._validate_numeric_ranges(df)
        
        # 6. 清理日期格式
        if self.cleaning_rules['clean_date_formats']:
            df = self._clean_date_formats(df)
        
        # 7. 移除极端异常值
        if self.cleaning_rules['remove_extreme_outliers']:
            df = self._remove_extreme_outliers(df)
        
        # 8. 基于问卷类型的特定清洗
        df = self._apply_type_specific_cleaning(df, classification_result)
        
        logger.info(f"数据清洗完成: 从 {raw_data.shape[0]} 行清洗至 {df.shape[0]} 行")
        return df

    def _remove_test_responses(self, df: pd.DataFrame) -> pd.DataFrame:
        """移除测试回答"""
        # 识别测试回答的模式
        test_patterns = [
            r'测试', r'test', r'Test', r'TEST',
            r'aaa', r'bbb', r'ccc',
            r'111', r'222', r'333',
            r'张三', r'李四', r'王五'
        ]
        
        # 检查文本列中的测试模式
        text_columns = df.select_dtypes(include=['object']).columns
        
        test_mask = pd.Series([False] * len(df))
        for col in text_columns:
            for pattern in test_patterns:
                pattern_mask = df[col].astype(str).str.contains(pattern, na=False, regex=True)
                test_mask = test_mask | pattern_mask
        
        cleaned_df = df[~test_mask]
        removed_count = len(df) - len(cleaned_df)
        
        if removed_count > 0:
            logger.info(f"移除 {removed_count} 条测试回答")
        
        return cleaned_df

    def _handle_missing_values(self, df: pd.DataFrame) -> pd.DataFrame:
        """处理缺失值"""
        # 计算每行的缺失率
        missing_rate = df.isnull().sum(axis=1) / len(df.columns)
        
        # 移除缺失率超过50%的行
        complete_enough = missing_rate <= 0.5
        df = df[complete_enough]
        
        # 对于数值列，使用中位数填充
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        for col in numeric_columns:
            if df[col].isnull().sum() > 0:
                median_value = df[col].median()
                df[col].fillna(median_value, inplace=True)
        
        # 对于文本列，使用"未填写"填充
        text_columns = df.select_dtypes(include=['object']).columns
        for col in text_columns:
            df[col].fillna('未填写', inplace=True)
        
        return df

    def _remove_duplicate_responses(self, df: pd.DataFrame) -> pd.DataFrame:
        """移除重复回答"""
        # 寻找可能的用户标识列
        id_columns = []
        for col in df.columns:
            col_lower = col.lower()
            if any(keyword in col_lower for keyword in ['id', '编号', 'user', '用户', 'phone', '手机']):
                id_columns.append(col)
        
        if id_columns:
            # 基于用户ID去重
            df = df.drop_duplicates(subset=id_columns, keep='first')
        else:
            # 基于所有列去重
            df = df.drop_duplicates(keep='first')
        
        return df

    def _standardize_text_responses(self, df: pd.DataFrame) -> pd.DataFrame:
        """标准化文本回答"""
        text_columns = df.select_dtypes(include=['object']).columns
        
        for col in text_columns:
            # 移除前后空格
            df[col] = df[col].astype(str).str.strip()
            
            # 标准化常见回答
            for mapping_name, mapping_dict in self.standardization_maps.items():
                if any(keyword in col.lower() for keyword in mapping_name.split('_')):
                    df[col] = df[col].map(mapping_dict).fillna(df[col])
        
        return df

    def _validate_numeric_ranges(self, df: pd.DataFrame) -> pd.DataFrame:
        """验证数值范围"""
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        # 常见评分范围验证
        for col in numeric_columns:
            col_lower = col.lower()
            
            # NPS评分 (0-10)
            if any(keyword in col_lower for keyword in ['nps', '推荐', '推荐度', '推荐分数']):
                df.loc[~df[col].between(0, 10), col] = np.nan
            
            # 满意度评分 (1-5)
            elif any(keyword in col_lower for keyword in ['满意度', 'satisfaction', '评分', '得分']):
                df.loc[~df[col].between(1, 5), col] = np.nan
            
            # 年龄验证 (18-80)
            elif any(keyword in col_lower for keyword in ['age', '年龄']):
                df.loc[~df[col].between(18, 80), col] = np.nan
        
        return df

    def _clean_date_formats(self, df: pd.DataFrame) -> pd.DataFrame:
        """清理日期格式"""
        date_columns = []
        
        # 识别日期列
        for col in df.columns:
            if any(keyword in col.lower() for keyword in ['date', '日期', '时间', 'time', '完成时间']):
                date_columns.append(col)
        
        # 标准化日期格式
        for col in date_columns:
            try:
                df[col] = pd.to_datetime(df[col], errors='coerce')
            except Exception:
                logger.warning(f"无法解析日期列: {col}")
        
        return df

    def _remove_extreme_outliers(self, df: pd.DataFrame) -> pd.DataFrame:
        """移除极端异常值"""
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            Q1 = df[col].quantile(0.25)
            Q3 = df[col].quantile(0.75)
            IQR = Q3 - Q1
            
            # 使用3倍IQR规则识别异常值
            lower_bound = Q1 - 3 * IQR
            upper_bound = Q3 + 3 * IQR
            
            # 将异常值设为NaN而不是删除整行
            outlier_mask = (df[col] < lower_bound) | (df[col] > upper_bound)
            df.loc[outlier_mask, col] = np.nan
        
        return df

    def _apply_type_specific_cleaning(self, 
                                    df: pd.DataFrame, 
                                    classification_result: ClassificationResult) -> pd.DataFrame:
        """应用特定问卷类型的清洗规则"""
        questionnaire_type = classification_result.category
        
        if questionnaire_type.value == 'nps_research':
            # NPS问卷特定清洗
            df = self._clean_nps_specific(df)
        elif questionnaire_type.value == 'taste_test':
            # 口味测试特定清洗
            df = self._clean_taste_test_specific(df)
        elif questionnaire_type.value == 'concept_test':
            # 概念测试特定清洗
            df = self._clean_concept_test_specific(df)
        
        return df

    def _clean_nps_specific(self, df: pd.DataFrame) -> pd.DataFrame:
        """NPS问卷特定清洗"""
        # 确保NPS分数在0-10范围内
        nps_columns = [col for col in df.columns if any(keyword in col.lower() 
                      for keyword in ['nps', '推荐', '推荐度', '推荐分数'])]
        
        for col in nps_columns:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                df.loc[~df[col].between(0, 10), col] = np.nan
        
        return df

    def _clean_taste_test_specific(self, df: pd.DataFrame) -> pd.DataFrame:
        """口味测试特定清洗"""
        # 标准化口味相关的文本回答
        taste_keywords = ['甜度', '酸度', '口感', '香味', '质地']
        
        for col in df.columns:
            if any(keyword in col for keyword in taste_keywords):
                # 标准化口味描述
                taste_mapping = {
                    '太甜': '甜度过高', '偏甜': '甜度偏高', '刚好': '甜度适中',
                    '偏淡': '甜度偏低', '太淡': '甜度过低'
                }
                if df[col].dtype == 'object':
                    df[col] = df[col].map(taste_mapping).fillna(df[col])
        
        return df

    def _clean_concept_test_specific(self, df: pd.DataFrame) -> pd.DataFrame:
        """概念测试特定清洗"""
        # 标准化概念评价相关回答
        concept_keywords = ['吸引力', '独特性', '相关性', '可信度']
        
        for col in df.columns:
            if any(keyword in col for keyword in concept_keywords):
                if df[col].dtype in ['int64', 'float64']:
                    # 确保评分在合理范围内(1-5或1-10)
                    max_score = df[col].max()
                    if max_score <= 5:
                        df.loc[~df[col].between(1, 5), col] = np.nan
                    elif max_score <= 10:
                        df.loc[~df[col].between(1, 10), col] = np.nan
        
        return df

    def _validate_processed_data(self, 
                               df: pd.DataFrame, 
                               classification_result: ClassificationResult) -> List[str]:
        """验证处理后的数据"""
        errors = []
        
        # 1. 基本数据完整性检查
        if len(df) == 0:
            errors.append("处理后数据为空")
            return errors
        
        # 2. 样本量充足性检查
        if len(df) < 30:
            errors.append(f"样本量不足: 当前 {len(df)} 个样本，建议至少 30 个")
        
        # 3. 关键字段存在性检查
        required_fields = self._get_required_fields(classification_result.category)
        missing_fields = []
        for field in required_fields:
            if not any(keyword in col.lower() for col in df.columns for keyword in field):
                missing_fields.append(field[0])
        
        if missing_fields:
            errors.append(f"缺少关键字段: {', '.join(missing_fields)}")
        
        # 4. 数据质量检查
        numeric_columns = df.select_dtypes(include=[np.number]).columns
        if len(numeric_columns) == 0:
            errors.append("缺少数值型字段，无法进行定量分析")
        
        # 5. NPS特定验证
        if classification_result.category.value == 'nps_research':
            nps_errors = self._validate_nps_data(df)
            errors.extend(nps_errors)
        
        return errors

    def _get_required_fields(self, questionnaire_type) -> List[List[str]]:
        """获取不同问卷类型的必需字段"""
        field_requirements = {
            'nps_research': [
                ['nps', '推荐', '推荐度', '推荐分数'],
                ['满意度', 'satisfaction']
            ],
            'taste_test': [
                ['口味', '口感', 'taste'],
                ['甜度', 'sweetness'],
                ['整体评价', 'overall']
            ],
            'concept_test': [
                ['吸引力', 'attractiveness'],
                ['独特性', 'uniqueness'],
                ['购买意愿', 'purchase_intent']
            ]
        }
        
        return field_requirements.get(questionnaire_type.value, [])

    def _validate_nps_data(self, df: pd.DataFrame) -> List[str]:
        """验证NPS数据特定要求"""
        errors = []
        
        # 寻找NPS分数列
        nps_columns = [col for col in df.columns if any(keyword in col.lower() 
                      for keyword in ['nps', '推荐', '推荐度', '推荐分数'])]
        
        if not nps_columns:
            errors.append("未找到NPS评分字段")
        else:
            nps_col = nps_columns[0]
            valid_scores = df[nps_col].dropna()
            
            if len(valid_scores) == 0:
                errors.append("NPS评分字段中无有效数据")
            elif len(valid_scores) < 10:
                errors.append(f"有效NPS评分数量不足: {len(valid_scores)} 个")
            
            # 检查分数分布
            if len(valid_scores) > 0:
                score_range = valid_scores.max() - valid_scores.min()
                if score_range < 3:
                    errors.append("NPS评分分布过于集中，可能影响分析结果")
        
        return errors

    def _generate_processing_summary(self, 
                                   raw_data: pd.DataFrame,
                                   processed_data: pd.DataFrame,
                                   quality_assessment: Dict[str, Any],
                                   classification_result: ClassificationResult) -> Dict[str, Any]:
        """生成处理摘要"""
        return {
            'processing_time': datetime.now().isoformat(),
            'data_transformation': {
                'original_rows': len(raw_data),
                'processed_rows': len(processed_data),
                'rows_removed': len(raw_data) - len(processed_data),
                'removal_rate': (len(raw_data) - len(processed_data)) / len(raw_data),
                'original_columns': len(raw_data.columns),
                'processed_columns': len(processed_data.columns)
            },
            'questionnaire_info': {
                'detected_type': classification_result.category.value,
                'business_unit': classification_result.business_unit.value,
                'target_products': classification_result.target_products,
                'classification_confidence': classification_result.confidence_score
            },
            'data_quality_summary': {
                'overall_quality': quality_assessment.get('overall_quality_score', 0),
                'completeness': quality_assessment.get('completeness', {}).get('score', 0),
                'validity': quality_assessment.get('validity', {}).get('score', 0),
                'consistency': quality_assessment.get('consistency', {}).get('score', 0)
            },
            'processing_applied': {
                'test_responses_removed': True,
                'duplicates_removed': True,
                'missing_values_handled': True,
                'text_standardized': True,
                'outliers_removed': True
            }
        }

    def _generate_recommendations(self, 
                                quality_assessment: Dict[str, Any],
                                reliability_metrics: ReliabilityMetrics,
                                validation_errors: List[str]) -> List[str]:
        """生成改进建议"""
        recommendations = []
        
        # 基于数据质量的建议
        overall_quality = quality_assessment.get('overall_quality_score', 0)
        if overall_quality < 0.7:
            recommendations.append("数据质量较低，建议重新收集数据或增加质量控制措施")
        
        completeness = quality_assessment.get('completeness', {}).get('score', 0)
        if completeness < 0.8:
            recommendations.append("数据完整性不足，建议优化问卷设计减少必填项缺失")
        
        consistency = quality_assessment.get('consistency', {}).get('score', 0)
        if consistency < 0.7:
            recommendations.append("数据一致性较差，建议加强数据收集过程的标准化")
        
        # 基于可靠性指标的建议
        if reliability_metrics.overall_reliability < 0.7:
            recommendations.append("整体可靠性较低，建议扩大样本量并改善数据质量")
        
        if reliability_metrics.sample_representativeness < 0.6:
            recommendations.append("样本代表性不足，建议调整抽样策略以更好覆盖目标群体")
        
        # 基于验证错误的建议
        if validation_errors:
            if any("样本量不足" in error for error in validation_errors):
                recommendations.append("增加样本收集，建议样本量至少达到100个以上")
            
            if any("缺少关键字段" in error for error in validation_errors):
                recommendations.append("补充关键字段数据或在后续问卷中添加相关问题")
        
        # 如果没有特别的问题，给出通用建议
        if not recommendations:
            recommendations.append("数据质量良好，可以进行深入分析")
            recommendations.append("建议进行细分群体分析以获得更深入洞察")
        
        return recommendations

    def export_processed_data(self, 
                            processing_result: ProcessingResult,
                            output_path: str,
                            include_metadata: bool = True) -> str:
        """导出处理后的数据"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 导出主数据
        data_file = output_path.with_suffix('.xlsx')
        with pd.ExcelWriter(data_file, engine='openpyxl') as writer:
            # 处理后的数据
            processing_result.processed_data.to_excel(
                writer, sheet_name='处理后数据', index=False
            )
            
            if include_metadata:
                # 处理摘要
                summary_df = pd.DataFrame([processing_result.processing_summary])
                summary_df.to_excel(writer, sheet_name='处理摘要', index=False)
                
                # 质量评估
                quality_df = pd.DataFrame([processing_result.quality_assessment])
                quality_df.to_excel(writer, sheet_name='质量评估', index=False)
                
                # 分类结果
                classification_df = pd.DataFrame([{
                    'category': processing_result.classification_result.category.value,
                    'business_unit': processing_result.classification_result.business_unit.value,
                    'confidence_score': processing_result.classification_result.confidence_score,
                    'target_products': ', '.join(processing_result.classification_result.target_products)
                }])
                classification_df.to_excel(writer, sheet_name='分类结果', index=False)
        
        logger.info(f"处理结果已导出至: {data_file}")
        return str(data_file)