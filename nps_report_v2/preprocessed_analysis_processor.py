"""
NPS报告分析系统V2 - 预处理分析结果处理器
处理已经过预处理的分析结果JSON数据，进行质量验证、增强分析和报告生成
"""

import json
import re
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from .data_quality_assessment import DataQualityAssessment, ReliabilityMetrics
from .auxiliary_data_manager import AuxiliaryDataManager, BusinessContext, TagAnalysisResult

logger = logging.getLogger(__name__)


@dataclass
class PreprocessedValidationResult:
    """预处理结果验证结果"""
    is_valid: bool
    quality_score: float
    missing_components: List[str]
    data_completeness: float
    analysis_depth: float
    insights_quality: float
    validation_errors: List[str]
    enhancement_opportunities: List[str]


@dataclass
class EnhancedAnalysisResult:
    """增强分析结果"""
    original_analysis: Dict[str, Any]
    quality_assessment: Dict[str, Any]
    reliability_metrics: ReliabilityMetrics
    business_context: BusinessContext
    enhanced_insights: Dict[str, Any]
    tag_analysis: TagAnalysisResult
    actionable_recommendations: List[str]
    risk_alerts: List[str]
    metadata: Dict[str, Any]


class PreprocessedAnalysisProcessor:
    """预处理分析结果处理器"""
    
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
        
        # 初始化分析规则
        self.analysis_validation_rules = self._initialize_validation_rules()
        self.enhancement_templates = self._initialize_enhancement_templates()

    def process_preprocessed_analysis(self, 
                                    analysis_data: Dict[str, Any],
                                    enhancement_options: Optional[Dict[str, Any]] = None) -> EnhancedAnalysisResult:
        """
        处理预处理的分析结果
        
        Args:
            analysis_data: 预处理的分析结果数据
            enhancement_options: 增强选项
            
        Returns:
            EnhancedAnalysisResult: 增强分析结果
        """
        try:
            # 1. 验证分析结果质量
            validation_result = self._validate_analysis_quality(analysis_data)
            
            # 2. 评估数据质量和可靠性
            quality_assessment = self._assess_analysis_quality(analysis_data, validation_result)
            reliability_metrics = self._calculate_analysis_reliability(analysis_data, validation_result)
            
            # 3. 业务上下文识别和增强
            business_context = self._identify_business_context_from_analysis(analysis_data)
            
            # 4. 业务领域标签分析
            tag_analysis = self._analyze_business_domain_tags(analysis_data, business_context)
            
            # 5. 生成增强洞察
            enhanced_insights = self._generate_enhanced_insights(
                analysis_data, business_context, tag_analysis
            )
            
            # 6. 生成可操作建议
            actionable_recommendations = self._generate_actionable_recommendations(
                analysis_data, business_context, enhanced_insights
            )
            
            # 7. 风险警报识别
            risk_alerts = self._identify_risk_alerts(analysis_data, validation_result)
            
            # 8. 生成元数据
            metadata = self._generate_processing_metadata(analysis_data, validation_result)
            
            return EnhancedAnalysisResult(
                original_analysis=analysis_data,
                quality_assessment=quality_assessment,
                reliability_metrics=reliability_metrics,
                business_context=business_context,
                enhanced_insights=enhanced_insights,
                tag_analysis=tag_analysis,
                actionable_recommendations=actionable_recommendations,
                risk_alerts=risk_alerts,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"预处理分析结果处理失败: {str(e)}")
            raise

    def _initialize_validation_rules(self) -> Dict[str, Any]:
        """初始化验证规则"""
        return {
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
            'nps_patterns': [
                r'NPS值.*?[+-]?\d+\.?\d*',
                r'推荐者.*?\d+%',
                r'中立者.*?\d+%',
                r'贬损者.*?\d+%'
            ],
            'analysis_quality_indicators': [
                '占比', '比例', '百分比', '主要原因', '次要原因',
                '显著', '明显', '趋势', '建议', '改进'
            ],
            'insight_quality_patterns': [
                r'\d+\.?\d*%',  # 百分比数据
                r'占比.*?\d+',  # 占比描述
                r'主要.*?原因', # 原因分析
                r'建议.*?改进'  # 改进建议
            ]
        }

    def _initialize_enhancement_templates(self) -> Dict[str, Any]:
        """初始化增强模板"""
        return {
            'nps_enhancement': {
                'score_interpretation': {
                    'excellent': {'range': (50, 100), 'description': '优秀，用户忠诚度极高'},
                    'good': {'range': (0, 49), 'description': '良好，用户整体满意'},
                    'poor': {'range': (-100, -1), 'description': '较差，需要重点改进'}
                },
                'benchmark_comparison': {
                    'industry_average': 30,
                    'top_quartile': 50,
                    'yili_target': 45
                }
            },
            'satisfaction_enhancement': {
                'dimension_weights': {
                    '产品质量': 0.35,
                    '价格合理性': 0.25,
                    '品牌信任度': 0.20,
                    '购买便利性': 0.20
                }
            },
            'recommendation_templates': {
                'high_priority': [
                    '立即关注贬损者反馈，制定针对性改进方案',
                    '优化核心不满因素，提升用户体验',
                    '加强与推荐者的关系维护，扩大正面口碑'
                ],
                'medium_priority': [
                    '深入分析中立者转化机会',
                    '持续监控NPS变化趋势',
                    '建立客户反馈闭环机制'
                ]
            }
        }

    def _validate_analysis_quality(self, analysis_data: Dict[str, Any]) -> PreprocessedValidationResult:
        """验证分析质量"""
        validation_errors = []
        missing_components = []
        
        # 1. 检查必需字段
        required_fields = self.analysis_validation_rules['required_fields']
        for field in required_fields:
            if field not in analysis_data:
                missing_components.append(field)
                validation_errors.append(f"缺少必需字段: {field}")
            elif not analysis_data[field]:
                validation_errors.append(f"字段 {field} 为空")
        
        # 2. 数据完整性评估
        total_expected_fields = len(required_fields) + len(self.analysis_validation_rules['optional_fields'])
        present_fields = sum(1 for field in required_fields + self.analysis_validation_rules['optional_fields'] 
                           if field in analysis_data and analysis_data[field])
        data_completeness = present_fields / total_expected_fields
        
        # 3. 分析深度评估
        analysis_depth = self._evaluate_analysis_depth(analysis_data)
        
        # 4. 洞察质量评估
        insights_quality = self._evaluate_insights_quality(analysis_data)
        
        # 5. 整体质量分数
        quality_score = (data_completeness * 0.3 + analysis_depth * 0.4 + insights_quality * 0.3)
        
        # 6. 增强机会识别
        enhancement_opportunities = self._identify_enhancement_opportunities(analysis_data)
        
        return PreprocessedValidationResult(
            is_valid=len(validation_errors) == 0 and quality_score >= 0.6,
            quality_score=quality_score,
            missing_components=missing_components,
            data_completeness=data_completeness,
            analysis_depth=analysis_depth,
            insights_quality=insights_quality,
            validation_errors=validation_errors,
            enhancement_opportunities=enhancement_opportunities
        )

    def _evaluate_analysis_depth(self, analysis_data: Dict[str, Any]) -> float:
        """评估分析深度"""
        depth_score = 0.0
        total_weight = 0.0
        
        # NPS分析深度
        if 'nps_analysis_result' in analysis_data:
            nps_text = analysis_data['nps_analysis_result']
            nps_depth = 0.0
            
            # 检查NPS核心要素
            nps_patterns = self.analysis_validation_rules['nps_patterns']
            for pattern in nps_patterns:
                if re.search(pattern, nps_text):
                    nps_depth += 0.25
            
            depth_score += nps_depth * 0.4
            total_weight += 0.4
        
        # 基础分析深度
        if 'base_analysis_result' in analysis_data:
            base_text = analysis_data['base_analysis_result']
            base_depth = 0.0
            
            # 检查分析质量指标
            quality_indicators = self.analysis_validation_rules['analysis_quality_indicators']
            indicator_count = sum(1 for indicator in quality_indicators if indicator in base_text)
            base_depth = min(indicator_count / len(quality_indicators), 1.0)
            
            depth_score += base_depth * 0.4
            total_weight += 0.4
        
        # 扩展分析深度
        extended_analyses = ['cross_analysis_result', 'kano_analysis_result', 'psm_analysis_result']
        extended_present = sum(1 for analysis in extended_analyses 
                             if analysis in analysis_data and analysis_data[analysis])
        extended_depth = extended_present / len(extended_analyses)
        
        depth_score += extended_depth * 0.2
        total_weight += 0.2
        
        return depth_score / total_weight if total_weight > 0 else 0.0

    def _evaluate_insights_quality(self, analysis_data: Dict[str, Any]) -> float:
        """评估洞察质量"""
        quality_score = 0.0
        text_content = ""
        
        # 收集所有文本内容
        for key, value in analysis_data.items():
            if isinstance(value, str):
                text_content += value + " "
        
        if not text_content:
            return 0.0
        
        # 1. 数据支撑度 (40%)
        insight_patterns = self.analysis_validation_rules['insight_quality_patterns']
        pattern_matches = sum(1 for pattern in insight_patterns 
                            if re.search(pattern, text_content))
        data_support = min(pattern_matches / len(insight_patterns), 1.0)
        quality_score += data_support * 0.4
        
        # 2. 结构化程度 (30%)
        structure_indicators = ['1.', '2.', '3.', '第一', '第二', '首先', '其次', '最后']
        structure_count = sum(1 for indicator in structure_indicators if indicator in text_content)
        structure_score = min(structure_count / 3, 1.0)  # 至少3个结构化标识
        quality_score += structure_score * 0.3
        
        # 3. 可操作性 (30%)
        actionable_keywords = ['建议', '应该', '需要', '可以', '改进', '优化', '提升', '加强']
        actionable_count = sum(1 for keyword in actionable_keywords if keyword in text_content)
        actionable_score = min(actionable_count / 3, 1.0)  # 至少3个可操作关键词
        quality_score += actionable_score * 0.3
        
        return quality_score

    def _identify_enhancement_opportunities(self, analysis_data: Dict[str, Any]) -> List[str]:
        """识别增强机会"""
        opportunities = []
        
        # 检查缺失的分析类型
        optional_analyses = {
            'cross_analysis_result': '交叉分析可提供更深入的群体差异洞察',
            'kano_analysis_result': 'Kano分析可识别用户需求优先级',
            'psm_analysis_result': 'PSM分析可优化价格策略',
            'maxdiff_analysis_result': 'MaxDiff分析可确定特性重要性排序'
        }
        
        for analysis_type, description in optional_analyses.items():
            if analysis_type not in analysis_data or not analysis_data[analysis_type]:
                opportunities.append(description)
        
        # 检查分析深度不足的领域
        if 'nps_analysis_result' in analysis_data:
            nps_text = analysis_data['nps_analysis_result']
            if '驱动因素' not in nps_text:
                opportunities.append('可以补充NPS驱动因素分析')
            if '改进建议' not in nps_text:
                opportunities.append('可以增加具体的改进建议')
        
        # 检查业务上下文
        text_content = " ".join(str(v) for v in analysis_data.values() if isinstance(v, str))
        if '伊利' not in text_content and '安慕希' not in text_content:
            opportunities.append('可以结合伊利集团产品特点进行分析')
        
        return opportunities

    def _assess_analysis_quality(self, 
                               analysis_data: Dict[str, Any], 
                               validation_result: PreprocessedValidationResult) -> Dict[str, Any]:
        """评估分析质量"""
        return {
            'overall_quality_score': validation_result.quality_score,
            'completeness': {
                'score': validation_result.data_completeness,
                'description': self._get_completeness_description(validation_result.data_completeness)
            },
            'depth': {
                'score': validation_result.analysis_depth,
                'description': self._get_depth_description(validation_result.analysis_depth)
            },
            'insights_quality': {
                'score': validation_result.insights_quality,
                'description': self._get_insights_description(validation_result.insights_quality)
            },
            'missing_components': validation_result.missing_components,
            'enhancement_opportunities': validation_result.enhancement_opportunities
        }

    def _get_completeness_description(self, score: float) -> str:
        """获取完整性描述"""
        if score >= 0.9:
            return "分析非常完整，包含了主要和扩展分析模块"
        elif score >= 0.7:
            return "分析相对完整，包含了核心分析模块"
        elif score >= 0.5:
            return "分析基本完整，但缺少部分重要模块"
        else:
            return "分析不完整，缺少多个核心模块"

    def _get_depth_description(self, score: float) -> str:
        """获取深度描述"""
        if score >= 0.8:
            return "分析深度优秀，提供了详细的数据支撑和洞察"
        elif score >= 0.6:
            return "分析深度良好，包含了基本的数据和结论"
        elif score >= 0.4:
            return "分析深度一般，需要更多数据支撑"
        else:
            return "分析深度不足，缺乏充分的数据支撑"

    def _get_insights_description(self, score: float) -> str:
        """获取洞察描述"""
        if score >= 0.8:
            return "洞察质量优秀，结构清晰且具有可操作性"
        elif score >= 0.6:
            return "洞察质量良好，有一定的实用价值"
        elif score >= 0.4:
            return "洞察质量一般，需要更好的结构化和可操作性"
        else:
            return "洞察质量较差，缺乏实用价值"

    def _calculate_analysis_reliability(self, 
                                      analysis_data: Dict[str, Any],
                                      validation_result: PreprocessedValidationResult) -> ReliabilityMetrics:
        """计算分析可靠性"""
        # 基于分析结果估算可靠性指标
        data_quality = validation_result.quality_score
        
        # 从分析文本中提取统计信息
        statistical_confidence = self._extract_statistical_confidence(analysis_data)
        response_quality = validation_result.insights_quality
        sample_representativeness = self._estimate_sample_representativeness(analysis_data)
        temporal_consistency = self._estimate_temporal_consistency(analysis_data)
        
        overall_reliability = (
            data_quality * 0.25 +
            statistical_confidence * 0.25 +
            response_quality * 0.2 +
            sample_representativeness * 0.15 +
            temporal_consistency * 0.15
        )
        
        return ReliabilityMetrics(
            overall_reliability=overall_reliability,
            data_quality=data_quality,
            statistical_confidence=statistical_confidence,
            response_quality=response_quality,
            sample_representativeness=sample_representativeness,
            temporal_consistency=temporal_consistency
        )

    def _extract_statistical_confidence(self, analysis_data: Dict[str, Any]) -> float:
        """从分析结果中提取统计置信度"""
        text_content = " ".join(str(v) for v in analysis_data.values() if isinstance(v, str))
        
        # 寻找统计显著性指标
        confidence_indicators = [
            r'\d+%',  # 百分比数据
            r'显著', r'明显', r'统计', r'置信',
            r'样本量', r'样本数', r'有效回答'
        ]
        
        matches = sum(1 for indicator in confidence_indicators 
                     if re.search(indicator, text_content))
        
        return min(matches / len(confidence_indicators), 1.0)

    def _estimate_sample_representativeness(self, analysis_data: Dict[str, Any]) -> float:
        """估算样本代表性"""
        text_content = " ".join(str(v) for v in analysis_data.values() if isinstance(v, str))
        
        # 查找样本多样性指标
        diversity_indicators = [
            '年龄', '性别', '地区', '收入', '教育',
            '分层', '分群', '群体', '差异'
        ]
        
        diversity_score = sum(1 for indicator in diversity_indicators 
                            if indicator in text_content)
        
        return min(diversity_score / len(diversity_indicators), 1.0)

    def _estimate_temporal_consistency(self, analysis_data: Dict[str, Any]) -> float:
        """估算时间一致性"""
        text_content = " ".join(str(v) for v in analysis_data.values() if isinstance(v, str))
        
        # 查找时间一致性指标
        temporal_indicators = [
            '趋势', '变化', '稳定', '持续',
            '时间', '期间', '阶段'
        ]
        
        temporal_score = sum(1 for indicator in temporal_indicators 
                           if indicator in text_content)
        
        # 默认给较高的一致性评分，因为是已处理的分析结果
        return max(0.7, min(temporal_score / len(temporal_indicators), 1.0))

    def _identify_business_context_from_analysis(self, analysis_data: Dict[str, Any]) -> BusinessContext:
        """从分析结果中识别业务上下文"""
        text_content = " ".join(str(v) for v in analysis_data.values() if isinstance(v, str))
        
        # 使用辅助数据管理器识别业务上下文
        # 这里传入一个模拟的数据结构
        mock_data = {'content': text_content}
        return self.auxiliary_manager.identify_business_context(mock_data, [])

    def _analyze_business_domain_tags(self, 
                                    analysis_data: Dict[str, Any],
                                    business_context: BusinessContext) -> TagAnalysisResult:
        """分析业务领域标签"""
        text_content = " ".join(str(v) for v in analysis_data.values() if isinstance(v, str))
        
        return self.auxiliary_manager.analyze_business_domain_tags(
            text_content, business_context.primary_products
        )

    def _generate_enhanced_insights(self, 
                                  analysis_data: Dict[str, Any],
                                  business_context: BusinessContext,
                                  tag_analysis: TagAnalysisResult) -> Dict[str, Any]:
        """生成增强洞察"""
        enhanced_insights = {
            'nps_insights': {},
            'business_insights': {},
            'competitive_insights': {},
            'improvement_insights': {}
        }
        
        # NPS增强洞察
        if 'nps_analysis_result' in analysis_data:
            nps_text = analysis_data['nps_analysis_result']
            enhanced_insights['nps_insights'] = self._enhance_nps_insights(nps_text)
        
        # 业务洞察增强
        enhanced_insights['business_insights'] = self._generate_business_insights(
            analysis_data, business_context
        )
        
        # 竞争洞察
        enhanced_insights['competitive_insights'] = self._generate_competitive_insights(
            analysis_data, business_context
        )
        
        # 改进洞察
        enhanced_insights['improvement_insights'] = self._generate_improvement_insights(
            analysis_data, tag_analysis
        )
        
        return enhanced_insights

    def _enhance_nps_insights(self, nps_text: str) -> Dict[str, Any]:
        """增强NPS洞察"""
        insights = {}
        
        # 提取NPS值
        nps_match = re.search(r'NPS值.*?([+-]?\d+\.?\d*)', nps_text)
        if nps_match:
            nps_value = float(nps_match.group(1))
            insights['nps_value'] = nps_value
            
            # NPS解释和基准对比
            benchmark = self.enhancement_templates['nps_enhancement']['benchmark_comparison']
            if nps_value >= benchmark['top_quartile']:
                insights['performance_level'] = '优秀'
                insights['vs_industry'] = f'超出行业平均水平 {nps_value - benchmark["industry_average"]} 分'
            elif nps_value >= benchmark['industry_average']:
                insights['performance_level'] = '良好'
                insights['vs_industry'] = f'高于行业平均水平 {nps_value - benchmark["industry_average"]} 分'
            else:
                insights['performance_level'] = '需要改进'
                insights['vs_industry'] = f'低于行业平均水平 {benchmark["industry_average"] - nps_value} 分'
        
        # 提取群体比例
        promoter_match = re.search(r'推荐者.*?(\d+)%', nps_text)
        passive_match = re.search(r'中立者.*?(\d+)%', nps_text)
        detractor_match = re.search(r'贬损者.*?(\d+)%', nps_text)
        
        if promoter_match and passive_match and detractor_match:
            insights['segment_distribution'] = {
                'promoters': int(promoter_match.group(1)),
                'passives': int(passive_match.group(1)),
                'detractors': int(detractor_match.group(1))
            }
        
        return insights

    def _generate_business_insights(self, 
                                  analysis_data: Dict[str, Any],
                                  business_context: BusinessContext) -> Dict[str, Any]:
        """生成业务洞察"""
        insights = {
            'product_focus': business_context.primary_products,
            'business_unit': business_context.business_units,
            'market_position': [],
            'growth_opportunities': []
        }
        
        # 基于检测到的产品生成市场定位洞察
        if business_context.primary_products:
            for product in business_context.primary_products[:3]:  # 前3个主要产品
                insights['market_position'].append(f"{product}品牌在目标细分市场的表现分析")
        
        # 基于业务单元生成增长机会
        for unit in business_context.business_units:
            if '液奶' in unit:
                insights['growth_opportunities'].append('液奶品类中高端化和功能化产品机会')
            elif '酸奶' in unit:
                insights['growth_opportunities'].append('酸奶品类中益生菌和低糖产品创新机会')
            elif '冷饮' in unit:
                insights['growth_opportunities'].append('冷饮品类中健康化和季节性产品机会')
        
        return insights

    def _generate_competitive_insights(self, 
                                     analysis_data: Dict[str, Any],
                                     business_context: BusinessContext) -> Dict[str, Any]:
        """生成竞争洞察"""
        text_content = " ".join(str(v) for v in analysis_data.values() if isinstance(v, str))
        
        insights = {
            'competitive_advantages': [],
            'competitive_gaps': [],
            'market_threats': [],
            'differentiation_opportunities': []
        }
        
        # 分析竞争优势
        if '功能' in text_content or '完善' in text_content:
            insights['competitive_advantages'].append('产品功能完善性是重要竞争优势')
        
        if '活动' in text_content or '丰富' in text_content:
            insights['competitive_advantages'].append('营销活动丰富性提升品牌活跃度')
        
        # 分析竞争劣势
        if '数据帮助' in text_content or '透明' in text_content:
            insights['competitive_gaps'].append('信息透明度和数据价值需要提升')
        
        if '操作' in text_content or '复杂' in text_content:
            insights['competitive_gaps'].append('用户体验简化和操作便利性需要改进')
        
        # 基于伊利产品特点的差异化机会
        for product in business_context.primary_products:
            if product in ['安慕希', '金典']:
                insights['differentiation_opportunities'].append(f'{product}品牌的高端化定位强化机会')
        
        return insights

    def _generate_improvement_insights(self, 
                                     analysis_data: Dict[str, Any],
                                     tag_analysis: TagAnalysisResult) -> Dict[str, Any]:
        """生成改进洞察"""
        insights = {
            'priority_improvements': [],
            'quick_wins': [],
            'long_term_strategies': [],
            'innovation_directions': []
        }
        
        # 基于标签分析生成改进建议
        for domain, tags in tag_analysis.matched_tags.items():
            if domain == '概念设计' and tags:
                insights['innovation_directions'].extend([
                    '产品概念创新和差异化价值主张开发',
                    '目标人群细分和精准定位策略'
                ])
            
            elif domain == '口味设计' and tags:
                insights['priority_improvements'].extend([
                    '口味配方优化和新口味开发',
                    '消费者口味偏好跟踪和满足'
                ])
            
            elif domain == '包装设计' and tags:
                insights['quick_wins'].extend([
                    '包装视觉效果优化',
                    '包装便利性和功能性改进'
                ])
        
        # 基于分析结果生成具体改进点
        text_content = " ".join(str(v) for v in analysis_data.values() if isinstance(v, str))
        
        if '信息透明' in text_content:
            insights['priority_improvements'].append('提升产品信息透明度和分类展示')
        
        if '使用流程' in text_content:
            insights['quick_wins'].append('优化用户使用流程和界面设计')
        
        if '产品包装' in text_content:
            insights['long_term_strategies'].append('建立包装设计和价格策略的综合优势')
        
        return insights

    def _generate_actionable_recommendations(self, 
                                           analysis_data: Dict[str, Any],
                                           business_context: BusinessContext,
                                           enhanced_insights: Dict[str, Any]) -> List[str]:
        """生成可操作建议"""
        recommendations = []
        
        # 基于NPS洞察的建议
        nps_insights = enhanced_insights.get('nps_insights', {})
        if 'nps_value' in nps_insights:
            nps_value = nps_insights['nps_value']
            if nps_value < 0:
                recommendations.extend([
                    '立即启动贬损者挽回计划，深入了解不满原因',
                    '优先解决核心产品质量和服务问题',
                    '建立快速响应机制处理客户投诉和建议'
                ])
            elif nps_value < 30:
                recommendations.extend([
                    '重点关注中立者转化，分析阻碍推荐的因素',
                    '加强产品差异化和价值传播',
                    '建立系统性的客户满意度提升计划'
                ])
            else:
                recommendations.extend([
                    '维护推荐者关系，激励口碑传播',
                    '扩大成功经验到其他产品线',
                    '持续监控并保持竞争优势'
                ])
        
        # 基于业务洞察的建议
        business_insights = enhanced_insights.get('business_insights', {})
        for opportunity in business_insights.get('growth_opportunities', []):
            recommendations.append(f'探索{opportunity}的具体实施路径')
        
        # 基于改进洞察的建议
        improvement_insights = enhanced_insights.get('improvement_insights', {})
        for improvement in improvement_insights.get('priority_improvements', []):
            recommendations.append(f'优先推进{improvement}')
        
        # 基于产品特点的定制化建议
        for product in business_context.primary_products[:3]:
            if product == '安慕希':
                recommendations.append('强化安慕希高端酸奶的品质认知和价值传播')
            elif product == '金典':
                recommendations.append('提升金典有机奶的健康价值和信任度')
            elif product == '舒化':
                recommendations.append('扩大舒化无乳糖牛奶的目标人群覆盖')
        
        return recommendations[:10]  # 限制建议数量

    def _identify_risk_alerts(self, 
                            analysis_data: Dict[str, Any],
                            validation_result: PreprocessedValidationResult) -> List[str]:
        """识别风险警报"""
        alerts = []
        
        # 质量风险
        if validation_result.quality_score < 0.5:
            alerts.append('数据质量风险：分析结果质量较低，建议重新评估数据来源')
        
        # NPS风险
        if 'nps_analysis_result' in analysis_data:
            nps_text = analysis_data['nps_analysis_result']
            nps_match = re.search(r'NPS值.*?([+-]?\d+\.?\d*)', nps_text)
            if nps_match:
                nps_value = float(nps_match.group(1))
                if nps_value < -20:
                    alerts.append('严重NPS风险：净推荐值过低，需要立即采取行动')
                elif nps_value < 0:
                    alerts.append('NPS预警：净推荐值为负，建议重点关注和改进')
            
            # 贬损者比例风险
            detractor_match = re.search(r'贬损者.*?(\d+)%', nps_text)
            if detractor_match:
                detractor_rate = int(detractor_match.group(1))
                if detractor_rate > 30:
                    alerts.append(f'贬损者比例风险：{detractor_rate}%的贬损者比例过高')
        
        # 样本代表性风险
        if validation_result.data_completeness < 0.6:
            alerts.append('样本代表性风险：数据完整性不足，可能影响结论的普适性')
        
        # 分析深度风险
        if validation_result.analysis_depth < 0.5:
            alerts.append('分析深度风险：缺乏充分的数据支撑，建议补充详细分析')
        
        return alerts

    def _generate_processing_metadata(self, 
                                    analysis_data: Dict[str, Any],
                                    validation_result: PreprocessedValidationResult) -> Dict[str, Any]:
        """生成处理元数据"""
        return {
            'processing_time': datetime.now().isoformat(),
            'processor_version': '2.0.0',
            'input_analysis_components': list(analysis_data.keys()),
            'quality_assessment': {
                'overall_score': validation_result.quality_score,
                'completeness': validation_result.data_completeness,
                'depth': validation_result.analysis_depth,
                'insights_quality': validation_result.insights_quality
            },
            'enhancement_applied': {
                'business_context_enrichment': True,
                'tag_analysis': True,
                'competitive_insights': True,
                'actionable_recommendations': True,
                'risk_identification': True
            },
            'content_statistics': {
                'total_text_length': sum(len(str(v)) for v in analysis_data.values() if isinstance(v, str)),
                'analysis_components_count': len(analysis_data),
                'has_nps_analysis': 'nps_analysis_result' in analysis_data,
                'has_base_analysis': 'base_analysis_result' in analysis_data
            }
        }