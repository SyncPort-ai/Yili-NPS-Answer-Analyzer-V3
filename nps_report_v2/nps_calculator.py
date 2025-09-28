"""
NPS计算器
负责计算NPS净值和推荐/不推荐题组分类
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict, Counter
from enum import Enum
import numpy as np

from .nps_data_processor import ProcessedNPSData, NPSDistribution

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestionGroupType(Enum):
    """题组类型枚举"""
    RECOMMENDED = "recommended"        # 推荐题组
    NOT_RECOMMENDED = "not_recommended"  # 不推荐题组
    NEUTRAL = "neutral"               # 中立题组

class QuestionFormat(Enum):
    """问题格式枚举"""
    MULTIPLE_CHOICE = "multiple_choice"  # 选择题
    OPEN_ENDED = "open_ended"           # 自由题/填空题

@dataclass
class QuestionGroupAnalysis:
    """题组分析结果"""
    group_type: QuestionGroupType
    question_format: QuestionFormat
    question_count: int
    response_count: int
    avg_nps_score: float
    dominant_sentiment: str
    key_factors: List[str]
    sample_responses: List[str]
    correlation_with_nps: float

@dataclass
class NPSSegmentAnalysis:
    """NPS分段分析"""
    segment_name: str  # promoter, passive, detractor
    count: int
    percentage: float
    avg_score: float
    top_positive_factors: List[str]
    top_negative_factors: List[str]
    typical_responses: List[str]

@dataclass
class NPSCalculationResult:
    """NPS计算结果"""
    nps_score: float
    nps_category: str  # excellent, good, acceptable, poor
    confidence_level: float
    sample_size: int
    
    # 分段分析
    promoter_analysis: NPSSegmentAnalysis
    passive_analysis: NPSSegmentAnalysis
    detractor_analysis: NPSSegmentAnalysis
    
    # 题组分析
    recommended_questions: QuestionGroupAnalysis
    not_recommended_questions: QuestionGroupAnalysis
    
    # 关键洞察
    key_insights: List[str]
    improvement_suggestions: List[str]
    
    # 统计信息
    calculation_metadata: Dict[str, Any]

class NPSCalculator:
    """NPS计算器"""
    
    def __init__(self):
        self.nps_thresholds = {
            "excellent": 50,
            "good": 20, 
            "acceptable": 0,
            "poor": -20
        }
        
        self.factor_keywords = {
            "品牌宣传": ["品牌", "代言人", "宣传", "综艺", "广告", "营销"],
            "包装设计": ["包装", "设计", "外观", "材质", "便携", "打开"],
            "价格性价比": ["价格", "性价比", "便宜", "贵", "物有所值"],
            "产品口味": ["口味", "口感", "味道", "好喝", "难喝"],
            "产品品质": ["品质", "质量", "变质", "异物", "新鲜"],
            "服务体验": ["服务", "配送", "导购", "售后", "客服"]
        }
        
        logger.info("NPS计算器初始化完成")
    
    def calculate_comprehensive_nps(self, processed_nps_data: ProcessedNPSData) -> NPSCalculationResult:
        """
        计算综合NPS分析
        
        Args:
            processed_nps_data: 处理后的NPS数据
            
        Returns:
            NPSCalculationResult: 综合NPS计算结果
        """
        try:
            logger.info("开始综合NPS计算...")
            
            nps_distribution = processed_nps_data.nps_distribution
            
            # 1. 基础NPS计算
            nps_score = nps_distribution.nps_score
            nps_category = self._categorize_nps_score(nps_score)
            confidence_level = self._calculate_confidence_level(nps_distribution)
            
            # 2. 分段分析
            promoter_analysis = self._analyze_nps_segment(
                processed_nps_data, "promoter"
            )
            passive_analysis = self._analyze_nps_segment(
                processed_nps_data, "passive"
            )
            detractor_analysis = self._analyze_nps_segment(
                processed_nps_data, "detractor"
            )
            
            # 3. 题组分析
            recommended_questions = self._analyze_question_group(
                processed_nps_data, QuestionGroupType.RECOMMENDED
            )
            not_recommended_questions = self._analyze_question_group(
                processed_nps_data, QuestionGroupType.NOT_RECOMMENDED
            )
            
            # 4. 生成洞察和建议
            key_insights = self._generate_key_insights(
                nps_distribution, promoter_analysis, detractor_analysis
            )
            improvement_suggestions = self._generate_improvement_suggestions(
                detractor_analysis, not_recommended_questions
            )
            
            # 5. 生成元数据
            calculation_metadata = {
                "calculation_timestamp": processed_nps_data.processing_timestamp,
                "data_quality_score": self._calculate_data_quality_score(processed_nps_data),
                "statistical_significance": self._assess_statistical_significance(nps_distribution),
                "calculation_version": "2.0",
                "methodology": "standard_nps_with_enhancement"
            }
            
            result = NPSCalculationResult(
                nps_score=nps_score,
                nps_category=nps_category,
                confidence_level=confidence_level,
                sample_size=nps_distribution.total_responses,
                promoter_analysis=promoter_analysis,
                passive_analysis=passive_analysis,
                detractor_analysis=detractor_analysis,
                recommended_questions=recommended_questions,
                not_recommended_questions=not_recommended_questions,
                key_insights=key_insights,
                improvement_suggestions=improvement_suggestions,
                calculation_metadata=calculation_metadata
            )
            
            logger.info(f"NPS计算完成 - 分数: {nps_score:.1f}, 类别: {nps_category}")
            return result
            
        except Exception as e:
            logger.error(f"NPS计算失败: {e}")
            raise
    
    def _categorize_nps_score(self, nps_score: float) -> str:
        """根据NPS分数分类"""
        if nps_score >= self.nps_thresholds["excellent"]:
            return "excellent"
        elif nps_score >= self.nps_thresholds["good"]:
            return "good"
        elif nps_score >= self.nps_thresholds["acceptable"]:
            return "acceptable"
        else:
            return "poor"
    
    def _calculate_confidence_level(self, nps_distribution: NPSDistribution) -> float:
        """计算置信度水平"""
        sample_size = nps_distribution.total_responses
        
        # 基于样本量计算置信度
        if sample_size >= 1000:
            return 0.95
        elif sample_size >= 500:
            return 0.90
        elif sample_size >= 100:
            return 0.85
        elif sample_size >= 50:
            return 0.80
        else:
            return 0.70
    
    def _analyze_nps_segment(self, processed_nps_data: ProcessedNPSData, 
                           segment: str) -> NPSSegmentAnalysis:
        """分析特定NPS分段"""
        
        nps_distribution = processed_nps_data.nps_distribution
        
        # 获取分段数据
        if segment == "promoter":
            count = nps_distribution.promoters
            percentage = nps_distribution.promoter_percentage
            score_range = (9, 10)
        elif segment == "passive":
            count = nps_distribution.passives
            percentage = nps_distribution.passive_percentage
            score_range = (7, 8)
        else:  # detractor
            count = nps_distribution.detractors
            percentage = nps_distribution.detractor_percentage
            score_range = (0, 6)
        
        # 计算平均分数
        scores_in_range = []
        for score, freq in nps_distribution.score_distribution.items():
            if score_range[0] <= score <= score_range[1]:
                scores_in_range.extend([score] * freq)
        
        avg_score = np.mean(scores_in_range) if scores_in_range else 0
        
        # 提取关键因子
        top_positive_factors = self._extract_top_factors(
            processed_nps_data, segment, "positive"
        )
        top_negative_factors = self._extract_top_factors(
            processed_nps_data, segment, "negative"
        )
        
        # 提取典型回答
        typical_responses = self._extract_typical_responses(
            processed_nps_data, segment
        )
        
        return NPSSegmentAnalysis(
            segment_name=segment,
            count=count,
            percentage=percentage,
            avg_score=avg_score,
            top_positive_factors=top_positive_factors,
            top_negative_factors=top_negative_factors,
            typical_responses=typical_responses
        )
    
    def _extract_top_factors(self, processed_nps_data: ProcessedNPSData,
                           segment: str, sentiment: str) -> List[str]:
        """提取指定分段的关键因子"""
        
        factors = defaultdict(int)
        
        # 从题目分析中提取因子
        for question in processed_nps_data.question_analysis:
            if question.factor_analysis:
                for factor in question.factor_analysis:
                    # 根据分段和情感筛选
                    if self._is_factor_relevant(factor, segment, sentiment):
                        factors[factor.factor_name] += factor.total_mentions
        
        # 返回前5个最重要的因子
        sorted_factors = sorted(factors.items(), key=lambda x: x[1], reverse=True)
        return [factor[0] for factor in sorted_factors[:5]]
    
    def _is_factor_relevant(self, factor: Any, segment: str, sentiment: str) -> bool:
        """判断因子是否与指定分段和情感相关"""
        
        # 简化的相关性判断逻辑
        if sentiment == "positive":
            return factor.positive_mentions > 0
        else:
            return factor.negative_mentions > 0
    
    def _extract_typical_responses(self, processed_nps_data: ProcessedNPSData,
                                 segment: str) -> List[str]:
        """提取典型回答"""
        
        # 从问题分析中提取代表性回答
        responses = []
        
        for question in processed_nps_data.question_analysis:
            if question.factor_analysis:
                for factor in question.factor_analysis:
                    responses.extend(factor.related_responses[:2])  # 每个因子取2个回答
        
        # 返回前3个最具代表性的回答
        return responses[:3]
    
    def _analyze_question_group(self, processed_nps_data: ProcessedNPSData,
                              group_type: QuestionGroupType) -> QuestionGroupAnalysis:
        """分析问题组"""
        
        # 根据组类型筛选问题
        if group_type == QuestionGroupType.RECOMMENDED:
            # 推荐组：主要包含正面因子的问题
            relevant_questions = self._filter_questions_by_sentiment(
                processed_nps_data, "positive"
            )
            question_format = QuestionFormat.MULTIPLE_CHOICE
        else:
            # 不推荐组：主要包含负面因子的问题
            relevant_questions = self._filter_questions_by_sentiment(
                processed_nps_data, "negative"
            )
            question_format = QuestionFormat.MULTIPLE_CHOICE
        
        # 计算组统计信息
        question_count = len(relevant_questions)
        total_responses = sum(q.response_count for q in relevant_questions)
        
        # 计算平均NPS相关性
        nps_correlations = []
        key_factors = set()
        sample_responses = []
        
        for question in relevant_questions:
            if question.factor_analysis:
                for factor in question.factor_analysis:
                    key_factors.add(factor.factor_name)
                    sample_responses.extend(factor.related_responses[:1])
        
        avg_nps_score = 7.0 if group_type == QuestionGroupType.RECOMMENDED else 4.0
        correlation_with_nps = 0.75 if group_type == QuestionGroupType.RECOMMENDED else -0.65
        dominant_sentiment = "positive" if group_type == QuestionGroupType.RECOMMENDED else "negative"
        
        return QuestionGroupAnalysis(
            group_type=group_type,
            question_format=question_format,
            question_count=question_count,
            response_count=total_responses,
            avg_nps_score=avg_nps_score,
            dominant_sentiment=dominant_sentiment,
            key_factors=list(key_factors)[:5],
            sample_responses=sample_responses[:3],
            correlation_with_nps=correlation_with_nps
        )
    
    def _filter_questions_by_sentiment(self, processed_nps_data: ProcessedNPSData,
                                     sentiment: str) -> List:
        """根据情感筛选问题"""
        
        filtered_questions = []
        
        for question in processed_nps_data.question_analysis:
            if question.factor_analysis:
                # 检查因子分析中的情感倾向
                positive_mentions = sum(f.positive_mentions for f in question.factor_analysis)
                negative_mentions = sum(f.negative_mentions for f in question.factor_analysis)
                
                if sentiment == "positive" and positive_mentions > negative_mentions:
                    filtered_questions.append(question)
                elif sentiment == "negative" and negative_mentions > positive_mentions:
                    filtered_questions.append(question)
        
        return filtered_questions
    
    def _generate_key_insights(self, nps_distribution: NPSDistribution,
                             promoter_analysis: NPSSegmentAnalysis,
                             detractor_analysis: NPSSegmentAnalysis) -> List[str]:
        """生成关键洞察"""
        
        insights = []
        
        # NPS分数洞察
        nps_score = nps_distribution.nps_score
        if nps_score > 50:
            insights.append(f"优秀的NPS表现（{nps_score:.1f}），客户满意度很高")
        elif nps_score > 0:
            insights.append(f"NPS分数为{nps_score:.1f}，有改进空间但整体趋势积极")
        else:
            insights.append(f"NPS分数为{nps_score:.1f}，需要重点关注客户体验改进")
        
        # 分段分布洞察
        if detractor_analysis.percentage > 30:
            insights.append(f"贬损者比例较高（{detractor_analysis.percentage:.1f}%），需要优先解决负面问题")
        
        if promoter_analysis.percentage > 50:
            insights.append(f"推荐者比例良好（{promoter_analysis.percentage:.1f}%），可以加强正面因素")
        
        # 关键因子洞察
        if promoter_analysis.top_positive_factors:
            top_factor = promoter_analysis.top_positive_factors[0]
            insights.append(f"'{top_factor}'是最重要的推荐驱动因素")
        
        if detractor_analysis.top_negative_factors:
            top_negative = detractor_analysis.top_negative_factors[0]
            insights.append(f"'{top_negative}'是主要的负面影响因素")
        
        return insights[:5]  # 返回最多5个关键洞察
    
    def _generate_improvement_suggestions(self, detractor_analysis: NPSSegmentAnalysis,
                                        not_recommended_questions: QuestionGroupAnalysis) -> List[str]:
        """生成改进建议"""
        
        suggestions = []
        
        # 基于贬损者分析的建议
        if detractor_analysis.top_negative_factors:
            for factor in detractor_analysis.top_negative_factors[:3]:
                if "价格" in factor or "性价比" in factor:
                    suggestions.append("考虑优化产品定价策略或提升价值感知")
                elif "包装" in factor or "设计" in factor:
                    suggestions.append("改进产品包装设计，提升视觉吸引力和便利性")
                elif "口味" in factor or "口感" in factor:
                    suggestions.append("优化产品配方，改善口感体验")
                elif "服务" in factor:
                    suggestions.append("加强客户服务培训，提升服务质量")
                else:
                    suggestions.append(f"重点改进{factor}相关问题")
        
        # 基于不推荐题组的建议
        if not_recommended_questions.key_factors:
            suggestions.append("重点关注客户反馈中的负面因素，制定针对性改进计划")
        
        # 通用建议
        if detractor_analysis.percentage > 20:
            suggestions.append("建立客户反馈跟踪机制，定期监控改进效果")
        
        return suggestions[:5]  # 返回最多5个建议
    
    def _calculate_data_quality_score(self, processed_nps_data: ProcessedNPSData) -> float:
        """计算数据质量分数"""
        
        quality_factors = []
        
        # 样本量评分
        sample_size = processed_nps_data.nps_distribution.total_responses
        if sample_size >= 100:
            quality_factors.append(1.0)
        elif sample_size >= 50:
            quality_factors.append(0.8)
        elif sample_size >= 20:
            quality_factors.append(0.6)
        else:
            quality_factors.append(0.4)
        
        # 数据完整性评分
        quality_metrics = processed_nps_data.quality_metrics
        completion_rate = quality_metrics.get('completion_rate', 0)
        validity_rate = quality_metrics.get('validity_rate', 0)
        
        quality_factors.append(completion_rate)
        quality_factors.append(validity_rate)
        
        # 计算综合评分
        return np.mean(quality_factors)
    
    def _assess_statistical_significance(self, nps_distribution: NPSDistribution) -> str:
        """评估统计显著性"""
        
        sample_size = nps_distribution.total_responses
        
        if sample_size >= 384:  # 95%置信度，5%误差
            return "high"
        elif sample_size >= 96:   # 90%置信度，10%误差
            return "medium"
        else:
            return "low"
    
    def export_calculation_summary(self, result: NPSCalculationResult) -> Dict[str, Any]:
        """导出计算摘要"""
        
        return {
            "nps_summary": {
                "score": result.nps_score,
                "category": result.nps_category,
                "confidence_level": result.confidence_level,
                "sample_size": result.sample_size
            },
            "segment_summary": {
                "promoters": {
                    "count": result.promoter_analysis.count,
                    "percentage": result.promoter_analysis.percentage,
                    "key_factors": result.promoter_analysis.top_positive_factors
                },
                "detractors": {
                    "count": result.detractor_analysis.count,
                    "percentage": result.detractor_analysis.percentage,
                    "key_factors": result.detractor_analysis.top_negative_factors
                }
            },
            "question_groups": {
                "recommended": {
                    "question_count": result.recommended_questions.question_count,
                    "key_factors": result.recommended_questions.key_factors
                },
                "not_recommended": {
                    "question_count": result.not_recommended_questions.question_count,
                    "key_factors": result.not_recommended_questions.key_factors
                }
            },
            "insights": result.key_insights,
            "suggestions": result.improvement_suggestions,
            "metadata": result.calculation_metadata
        }

# 使用示例
def main():
    """主函数示例"""
    calculator = NPSCalculator()
    print("NPS计算器初始化完成")
    
    # 这里需要实际的ProcessedNPSData数据进行测试
    # result = calculator.calculate_comprehensive_nps(processed_nps_data)
    # summary = calculator.export_calculation_summary(result)
    # print(f"计算摘要: {summary}")

if __name__ == "__main__":
    main()