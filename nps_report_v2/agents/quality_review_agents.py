"""
质量评审智能体系统
包含NPS专家、业务分析师、报告质量专家等多个评审维度的智能体
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
import asyncio

# 导入相关数据结构
from ..nps_calculator import NPSCalculationResult
from ..nps_data_processor import ProcessedNPSData
from ..input_data_processor import ProcessedSurveyData
from .nps_analysis_agent import NPSInsightResult
from .question_group_agent import QuestionGroupAnalysisResult
from .insights_agent import BusinessInsightsResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QualityDimension(Enum):
    """质量评估维度"""
    STATISTICAL_RIGOR = "statistical_rigor"
    BUSINESS_RELEVANCE = "business_relevance"
    INSIGHT_DEPTH = "insight_depth"
    ACTIONABILITY = "actionability"
    CONSISTENCY = "consistency"
    COMPLETENESS = "completeness"

@dataclass
class QualityScore:
    """质量评分"""
    dimension: str
    score: float  # 0-10分
    rationale: str
    improvement_suggestions: List[str]
    confidence: float

@dataclass
class QualityReview:
    """质量评审结果"""
    reviewer_name: str
    reviewer_expertise: str
    overall_score: float
    dimension_scores: List[QualityScore]
    key_strengths: List[str]
    improvement_areas: List[str]
    revision_required: bool
    priority_fixes: List[str]
    review_metadata: Dict[str, Any]

@dataclass
class ComprehensiveQualityAssessment:
    """综合质量评估结果"""
    overall_quality_score: float
    individual_reviews: List[QualityReview]
    consensus_assessment: Dict[str, Any]
    revision_recommendations: List[Dict[str, Any]]
    quality_certification: str
    assessment_metadata: Dict[str, Any]

class NPSExpertCritic:
    """NPS专家评论员"""
    
    def __init__(self):
        self.expertise_areas = [
            "NPS计算方法论",
            "统计显著性检验", 
            "客户细分分析",
            "NPS基准对比",
            "数据质量评估"
        ]
        
        self.quality_criteria = {
            "statistical_rigor": {
                "sample_size_adequacy": "样本量是否足够统计分析",
                "calculation_accuracy": "NPS计算是否准确",
                "confidence_intervals": "置信区间是否合理",
                "bias_assessment": "是否存在抽样偏差"
            },
            "methodology_soundness": {
                "nps_formula": "NPS公式应用是否正确",
                "segmentation_logic": "客户细分逻辑是否合理",
                "benchmark_selection": "基准选择是否恰当",
                "trend_analysis": "趋势分析是否科学"
            }
        }
    
    async def review_analysis(self, 
                            nps_calculation: NPSCalculationResult,
                            processed_nps_data: ProcessedNPSData,
                            nps_insights: NPSInsightResult) -> QualityReview:
        """评审NPS分析质量"""
        
        logger.info("NPS专家开始质量评审")
        
        dimension_scores = []
        
        # 1. 统计严谨性评估
        statistical_score = await self._assess_statistical_rigor(
            nps_calculation, processed_nps_data
        )
        dimension_scores.append(statistical_score)
        
        # 2. 方法论正确性评估
        methodology_score = await self._assess_methodology(
            nps_calculation, nps_insights
        )
        dimension_scores.append(methodology_score)
        
        # 3. 洞察深度评估
        insight_score = await self._assess_insight_depth(nps_insights)
        dimension_scores.append(insight_score)
        
        # 4. 一致性评估
        consistency_score = await self._assess_consistency(
            nps_calculation, nps_insights
        )
        dimension_scores.append(consistency_score)
        
        # 计算总分
        overall_score = sum(score.score for score in dimension_scores) / len(dimension_scores)
        
        # 识别优势和改进点
        key_strengths = self._identify_strengths(dimension_scores)
        improvement_areas = self._identify_improvements(dimension_scores)
        
        # 确定是否需要修订
        revision_required = overall_score < 7.0 or any(score.score < 6.0 for score in dimension_scores)
        
        # 优先修复项
        priority_fixes = [
            score.improvement_suggestions[0] 
            for score in dimension_scores 
            if score.score < 6.0 and score.improvement_suggestions
        ]
        
        return QualityReview(
            reviewer_name="NPS专家评论员",
            reviewer_expertise="NPS方法论与统计分析",
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            key_strengths=key_strengths,
            improvement_areas=improvement_areas,
            revision_required=revision_required,
            priority_fixes=priority_fixes,
            review_metadata={
                "review_timestamp": datetime.now().isoformat(),
                "expertise_areas": self.expertise_areas,
                "review_focus": "statistical_and_methodological"
            }
        )
    
    async def _assess_statistical_rigor(self, 
                                      nps_calculation: NPSCalculationResult,
                                      processed_nps_data: ProcessedNPSData) -> QualityScore:
        """评估统计严谨性"""
        
        score = 8.0  # 基准分
        suggestions = []
        
        # 样本量评估
        sample_size = processed_nps_data.nps_distribution.total_responses
        if sample_size < 30:
            score -= 3.0
            suggestions.append("样本量过小(n<30)，建议增加样本量以提高统计可靠性")
        elif sample_size < 100:
            score -= 1.5
            suggestions.append("样本量偏小(n<100)，建议扩大样本量")
        elif sample_size < 200:
            score -= 0.5
            suggestions.append("样本量基本充足，可考虑进一步扩大")
        
        # 置信度评估
        confidence = nps_calculation.confidence_level
        if confidence < 0.7:
            score -= 2.0
            suggestions.append("计算置信度偏低，需要检查数据质量和计算方法")
        elif confidence < 0.8:
            score -= 1.0
            suggestions.append("置信度有提升空间，建议优化数据处理流程")
        
        # 数据质量评估
        data_quality = processed_nps_data.data_quality.overall_score
        if data_quality < 0.7:
            score -= 2.0
            suggestions.append("数据质量偏低，需要改进数据收集和清理流程")
        elif data_quality < 0.8:
            score -= 1.0
            suggestions.append("数据质量良好，可进一步优化")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="statistical_rigor",
            score=score,
            rationale=f"样本量{sample_size}，置信度{confidence:.2f}，数据质量{data_quality:.2f}",
            improvement_suggestions=suggestions or ["统计严谨性符合标准"],
            confidence=0.9
        )
    
    async def _assess_methodology(self, 
                                nps_calculation: NPSCalculationResult,
                                nps_insights: NPSInsightResult) -> QualityScore:
        """评估方法论正确性"""
        
        score = 9.0  # 基准分
        suggestions = []
        
        # NPS计算公式检查
        nps_score = nps_calculation.overall_nps
        if not (-100 <= nps_score <= 100):
            score -= 5.0
            suggestions.append("NPS得分超出正常范围(-100到100)，需要检查计算公式")
        
        # 基准对比合理性
        benchmark_comparison = nps_insights.benchmark_comparison
        if not benchmark_comparison or len(benchmark_comparison) == 0:
            score -= 1.5
            suggestions.append("缺少基准对比分析，建议添加行业或历史基准")
        
        # 细分分析完整性
        segment_insights = nps_insights.segment_insights
        if not segment_insights or len(segment_insights) < 2:
            score -= 1.0
            suggestions.append("客户细分分析不够充分，建议增加更多维度的分析")
        
        # 趋势分析科学性
        trend_analysis = nps_insights.trend_analysis
        if not trend_analysis.get("trend_available", False):
            score -= 0.5
            suggestions.append("建议收集历史数据进行趋势分析")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="methodology_soundness", 
            score=score,
            rationale="基于NPS计算准确性、基准对比合理性和分析完整性评估",
            improvement_suggestions=suggestions or ["方法论应用正确"],
            confidence=0.85
        )
    
    async def _assess_insight_depth(self, nps_insights: NPSInsightResult) -> QualityScore:
        """评估洞察深度"""
        
        score = 7.0  # 基准分
        suggestions = []
        
        # 分析维度丰富性
        analysis_dimensions = [
            nps_insights.nps_score_analysis,
            nps_insights.distribution_analysis,
            nps_insights.benchmark_comparison,
            nps_insights.segment_insights
        ]
        
        non_empty_dimensions = sum(1 for dim in analysis_dimensions if dim)
        if non_empty_dimensions >= 4:
            score += 1.5
        elif non_empty_dimensions >= 3:
            score += 0.5
        else:
            score -= 1.0
            suggestions.append("分析维度不够全面，建议增加更多分析角度")
        
        # 洞察质量评估
        recommendations_count = len(nps_insights.business_recommendations)
        if recommendations_count >= 5:
            score += 1.0
        elif recommendations_count >= 3:
            score += 0.5
        elif recommendations_count < 2:
            score -= 1.0
            suggestions.append("业务建议数量偏少，建议提供更多可操作的建议")
        
        # 风险识别能力
        risk_alerts_count = len(nps_insights.risk_alerts)
        if risk_alerts_count >= 2:
            score += 0.5
        elif risk_alerts_count == 0:
            score -= 0.5
            suggestions.append("建议增强风险识别能力")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="insight_depth",
            score=score,
            rationale=f"分析维度数量{non_empty_dimensions}，建议数量{recommendations_count}，风险识别{risk_alerts_count}",
            improvement_suggestions=suggestions or ["洞察深度符合标准"],
            confidence=0.8
        )
    
    async def _assess_consistency(self, 
                                nps_calculation: NPSCalculationResult,
                                nps_insights: NPSInsightResult) -> QualityScore:
        """评估一致性"""
        
        score = 8.5  # 基准分
        suggestions = []
        
        # NPS得分与解读一致性
        nps_score = nps_calculation.overall_nps
        score_analysis = nps_insights.nps_score_analysis
        
        if nps_score >= 50 and score_analysis.get("grade") not in ["excellent", "good"]:
            score -= 1.5
            suggestions.append("NPS得分与等级评定不一致")
        
        if nps_score < 30 and score_analysis.get("grade") not in ["poor", "critical"]:
            score -= 1.5
            suggestions.append("低NPS得分的严重性评估不足")
        
        # 建议与分析结果一致性
        recommendations = nps_insights.business_recommendations
        if nps_score < 40 and not any(rec.get("priority") == "urgent" for rec in recommendations):
            score -= 1.0
            suggestions.append("低NPS得分应对应紧急改进建议")
        
        # 置信度与分析质量一致性
        analysis_confidence = nps_insights.confidence_score
        calculation_confidence = nps_calculation.confidence_level
        
        if abs(analysis_confidence - calculation_confidence) > 0.2:
            score -= 0.5
            suggestions.append("分析置信度与计算置信度差异较大，需要检查一致性")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="consistency",
            score=score,
            rationale="评估NPS得分、分析结果、建议优先级等要素间的逻辑一致性",
            improvement_suggestions=suggestions or ["分析结果逻辑一致"],
            confidence=0.85
        )
    
    def _identify_strengths(self, dimension_scores: List[QualityScore]) -> List[str]:
        """识别优势"""
        strengths = []
        for score in dimension_scores:
            if score.score >= 8.0:
                strengths.append(f"{score.dimension}: {score.rationale}")
        return strengths
    
    def _identify_improvements(self, dimension_scores: List[QualityScore]) -> List[str]:
        """识别改进点"""
        improvements = []
        for score in dimension_scores:
            if score.score < 7.0:
                improvements.extend(score.improvement_suggestions)
        return improvements

class BusinessAnalystCritic:
    """业务分析师评论员"""
    
    def __init__(self):
        self.expertise_areas = [
            "商业洞察价值",
            "市场竞争分析",
            "行动建议可操作性",
            "ROI影响评估",
            "战略决策支持"
        ]
    
    async def review_analysis(self,
                            business_insights: BusinessInsightsResult,
                            question_group_analysis: QuestionGroupAnalysisResult) -> QualityReview:
        """评审业务分析质量"""
        
        logger.info("业务分析师开始质量评审")
        
        dimension_scores = []
        
        # 1. 商业相关性评估
        relevance_score = await self._assess_business_relevance(business_insights)
        dimension_scores.append(relevance_score)
        
        # 2. 可操作性评估
        actionability_score = await self._assess_actionability(
            business_insights, question_group_analysis
        )
        dimension_scores.append(actionability_score)
        
        # 3. 战略价值评估
        strategic_score = await self._assess_strategic_value(business_insights)
        dimension_scores.append(strategic_score)
        
        # 4. 完整性评估
        completeness_score = await self._assess_completeness(
            business_insights, question_group_analysis
        )
        dimension_scores.append(completeness_score)
        
        # 计算总分
        overall_score = sum(score.score for score in dimension_scores) / len(dimension_scores)
        
        # 识别优势和改进点
        key_strengths = [
            f"{score.dimension}: 得分{score.score:.1f}"
            for score in dimension_scores if score.score >= 8.0
        ]
        
        improvement_areas = [
            suggestion for score in dimension_scores 
            for suggestion in score.improvement_suggestions
            if score.score < 7.0
        ]
        
        # 确定是否需要修订
        revision_required = overall_score < 6.5 or any(score.score < 5.0 for score in dimension_scores)
        
        # 优先修复项
        priority_fixes = [
            f"{score.dimension}: {score.improvement_suggestions[0]}"
            for score in dimension_scores 
            if score.score < 6.0 and score.improvement_suggestions
        ]
        
        return QualityReview(
            reviewer_name="业务分析师评论员",
            reviewer_expertise="商业洞察与战略分析",
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            key_strengths=key_strengths,
            improvement_areas=improvement_areas,
            revision_required=revision_required,
            priority_fixes=priority_fixes,
            review_metadata={
                "review_timestamp": datetime.now().isoformat(),
                "expertise_areas": self.expertise_areas,
                "review_focus": "business_value_and_actionability"
            }
        )
    
    async def _assess_business_relevance(self, business_insights: BusinessInsightsResult) -> QualityScore:
        """评估商业相关性"""
        
        score = 7.5  # 基准分
        suggestions = []
        
        # 市场洞察相关性
        market_insights = business_insights.market_insights
        high_value_insights = [
            insight for insight in market_insights 
            if insight.impact_assessment in ["positive", "opportunity"]
        ]
        
        if len(high_value_insights) >= 3:
            score += 1.0
        elif len(high_value_insights) >= 1:
            score += 0.5
        else:
            score -= 1.0
            suggestions.append("缺少有价值的市场洞察，建议深入分析市场机会")
        
        # 竞争分析实用性
        competitive_analysis = business_insights.competitive_analysis
        actionable_competitive_insights = [
            analysis for analysis in competitive_analysis
            if analysis.strategic_recommendations
        ]
        
        if len(actionable_competitive_insights) >= 2:
            score += 0.5
        elif len(actionable_competitive_insights) == 0:
            score -= 0.5
            suggestions.append("竞争分析缺少可操作的战略建议")
        
        # 区域洞察价值
        regional_insights = business_insights.regional_insights
        growth_opportunities = sum(
            len(insight.growth_opportunities) for insight in regional_insights
        )
        
        if growth_opportunities >= 5:
            score += 0.5
        elif growth_opportunities == 0:
            score -= 0.5
            suggestions.append("区域分析缺少增长机会识别")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="business_relevance",
            score=score,
            rationale=f"市场洞察{len(high_value_insights)}个，竞争洞察{len(actionable_competitive_insights)}个，增长机会{growth_opportunities}个",
            improvement_suggestions=suggestions or ["商业相关性良好"],
            confidence=0.8
        )
    
    async def _assess_actionability(self,
                                  business_insights: BusinessInsightsResult,
                                  question_group_analysis: QuestionGroupAnalysisResult) -> QualityScore:
        """评估可操作性"""
        
        score = 7.0  # 基准分
        suggestions = []
        
        # 行动建议的具体性
        action_priorities = business_insights.action_priorities
        specific_actions = [
            action for action in action_priorities
            if action.get("timeline") and action.get("expected_impact")
        ]
        
        if len(specific_actions) >= 5:
            score += 1.5
        elif len(specific_actions) >= 3:
            score += 0.5
        else:
            score -= 1.0
            suggestions.append("行动建议缺少具体的时间线和预期影响")
        
        # 优先级明确性
        high_priority_actions = [
            action for action in action_priorities
            if action.get("priority") in ["P0", "P1", "urgent", "high"]
        ]
        
        if len(high_priority_actions) >= 3:
            score += 1.0
        elif len(high_priority_actions) >= 1:
            score += 0.5
        else:
            score -= 0.5
            suggestions.append("缺少明确的高优先级行动建议")
        
        # 题组分析的可操作性
        question_group_actions = question_group_analysis.priority_actions
        actionable_group_insights = [
            action for action in question_group_actions
            if action.get("expected_impact")
        ]
        
        if len(actionable_group_insights) >= 3:
            score += 0.5
        elif len(actionable_group_insights) == 0:
            score -= 0.5
            suggestions.append("题组分析缺少可操作的改进建议")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="actionability",
            score=score,
            rationale=f"具体行动{len(specific_actions)}个，高优先级{len(high_priority_actions)}个，题组建议{len(actionable_group_insights)}个",
            improvement_suggestions=suggestions or ["可操作性符合标准"],
            confidence=0.85
        )
    
    async def _assess_strategic_value(self, business_insights: BusinessInsightsResult) -> QualityScore:
        """评估战略价值"""
        
        score = 8.0  # 基准分
        suggestions = []
        
        # 战略摘要质量
        strategic_summary = business_insights.strategic_summary
        if not strategic_summary or len(strategic_summary) < 3:
            score -= 1.5
            suggestions.append("战略摘要不够充分，建议增加更多战略层面的总结")
        
        # 趋势预测价值
        trend_predictions = business_insights.trend_predictions
        high_confidence_predictions = [
            prediction for prediction in trend_predictions
            if prediction.prediction_confidence >= 0.7
        ]
        
        if len(high_confidence_predictions) >= 2:
            score += 1.0
        elif len(high_confidence_predictions) >= 1:
            score += 0.5
        else:
            score -= 0.5
            suggestions.append("高置信度的趋势预测不足，影响战略规划价值")
        
        # 市场定位洞察
        market_insights = business_insights.market_insights
        positioning_insights = [
            insight for insight in market_insights
            if "market_position" in insight.insight_type
        ]
        
        if len(positioning_insights) >= 1:
            score += 0.5
        else:
            score -= 0.5
            suggestions.append("缺少市场定位相关的战略洞察")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="strategic_value",
            score=score,
            rationale=f"战略摘要完整性，趋势预测{len(high_confidence_predictions)}个，定位洞察{len(positioning_insights)}个",
            improvement_suggestions=suggestions or ["战略价值突出"],
            confidence=0.8
        )
    
    async def _assess_completeness(self,
                                 business_insights: BusinessInsightsResult,
                                 question_group_analysis: QuestionGroupAnalysisResult) -> QualityScore:
        """评估完整性"""
        
        score = 8.0  # 基准分
        suggestions = []
        
        # 分析维度完整性检查
        required_components = [
            business_insights.market_insights,
            business_insights.competitive_analysis,
            business_insights.regional_insights,
            business_insights.trend_predictions,
            business_insights.action_priorities
        ]
        
        missing_components = sum(1 for comp in required_components if not comp or len(comp) == 0)
        
        if missing_components == 0:
            score += 1.0
        elif missing_components <= 1:
            score += 0.5
        else:
            score -= missing_components * 0.5
            suggestions.append(f"缺少{missing_components}个核心分析组件")
        
        # 题组分析完整性
        if (question_group_analysis.promoter_choice_insights.total_responses == 0 and
            question_group_analysis.detractor_choice_insights.total_responses == 0):
            score -= 1.0
            suggestions.append("题组分析缺少有效的推荐者和批评者洞察")
        
        # 交叉分析完整性
        cross_analysis = question_group_analysis.cross_group_comparison
        if not cross_analysis or len(cross_analysis) < 2:
            score -= 0.5
            suggestions.append("缺少充分的跨组对比分析")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="completeness",
            score=score,
            rationale=f"核心组件缺失{missing_components}个，分析覆盖度评估",
            improvement_suggestions=suggestions or ["分析完整性良好"],
            confidence=0.9
        )

class ReportQualityCritic:
    """报告质量评论员"""
    
    def __init__(self):
        self.expertise_areas = [
            "报告结构逻辑",
            "内容表达清晰度",
            "数据可视化效果",
            "专业性与可读性平衡",
            "决策支持有效性"
        ]
    
    async def review_report_quality(self, 
                                  report_content: Dict[str, Any]) -> QualityReview:
        """评审报告质量"""
        
        logger.info("报告质量专家开始评审")
        
        dimension_scores = []
        
        # 1. 结构逻辑评估
        structure_score = await self._assess_structure_logic(report_content)
        dimension_scores.append(structure_score)
        
        # 2. 内容清晰度评估
        clarity_score = await self._assess_content_clarity(report_content)
        dimension_scores.append(clarity_score)
        
        # 3. 专业性评估
        professionalism_score = await self._assess_professionalism(report_content)
        dimension_scores.append(professionalism_score)
        
        # 4. 决策支持度评估
        decision_support_score = await self._assess_decision_support(report_content)
        dimension_scores.append(decision_support_score)
        
        # 计算总分
        overall_score = sum(score.score for score in dimension_scores) / len(dimension_scores)
        
        # 识别优势和改进点
        key_strengths = [
            f"报告{score.dimension}表现优秀"
            for score in dimension_scores if score.score >= 8.0
        ]
        
        improvement_areas = [
            suggestion for score in dimension_scores 
            for suggestion in score.improvement_suggestions
            if score.score < 7.5
        ]
        
        # 确定是否需要修订
        revision_required = overall_score < 7.0 or any(score.score < 6.0 for score in dimension_scores)
        
        # 优先修复项
        priority_fixes = [
            f"报告{score.dimension}: {score.improvement_suggestions[0]}"
            for score in dimension_scores 
            if score.score < 6.5 and score.improvement_suggestions
        ]
        
        return QualityReview(
            reviewer_name="报告质量评论员",
            reviewer_expertise="报告撰写与信息传达",
            overall_score=overall_score,
            dimension_scores=dimension_scores,
            key_strengths=key_strengths,
            improvement_areas=improvement_areas,
            revision_required=revision_required,
            priority_fixes=priority_fixes,
            review_metadata={
                "review_timestamp": datetime.now().isoformat(),
                "expertise_areas": self.expertise_areas,
                "review_focus": "report_quality_and_presentation"
            }
        )
    
    async def _assess_structure_logic(self, report_content: Dict[str, Any]) -> QualityScore:
        """评估结构逻辑"""
        
        score = 8.5  # 基准分
        suggestions = []
        
        # 检查必要章节
        required_sections = [
            "executive_summary",
            "nps_overview", 
            "detailed_analysis",
            "recommendations"
        ]
        
        missing_sections = [
            section for section in required_sections 
            if section not in report_content or not report_content[section]
        ]
        
        if missing_sections:
            score -= len(missing_sections) * 1.0
            suggestions.append(f"缺少必要章节: {', '.join(missing_sections)}")
        
        # 检查逻辑流畅性
        if ("executive_summary" in report_content and 
            "detailed_analysis" in report_content):
            # 简单检查执行摘要是否与详细分析一致
            score += 0.5
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="structure_logic",
            score=score,
            rationale=f"报告结构完整性和逻辑流畅性评估",
            improvement_suggestions=suggestions or ["报告结构逻辑清晰"],
            confidence=0.9
        )
    
    async def _assess_content_clarity(self, report_content: Dict[str, Any]) -> QualityScore:
        """评估内容清晰度"""
        
        score = 7.5  # 基准分
        suggestions = []
        
        # 执行摘要清晰度
        if "executive_summary" in report_content:
            exec_summary = report_content["executive_summary"]
            
            if not exec_summary.get("key_findings"):
                score -= 1.0
                suggestions.append("执行摘要缺少关键发现")
            
            if not exec_summary.get("core_recommendations"):
                score -= 1.0
                suggestions.append("执行摘要缺少核心建议")
            
            # 检查关键指标展示
            if exec_summary.get("key_metrics"):
                score += 0.5
        
        # 建议部分的清晰度
        if "recommendations" in report_content:
            recommendations = report_content["recommendations"]
            
            if recommendations.get("content", {}).get("immediate_actions"):
                score += 0.5
            else:
                suggestions.append("缺少明确的立即行动建议")
            
            if recommendations.get("content", {}).get("implementation_roadmap"):
                score += 0.5
            else:
                suggestions.append("建议缺少实施路线图")
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="content_clarity",
            score=score,
            rationale="基于关键信息完整性和表达清晰度评估",
            improvement_suggestions=suggestions or ["内容表达清晰"],
            confidence=0.85
        )
    
    async def _assess_professionalism(self, report_content: Dict[str, Any]) -> QualityScore:
        """评估专业性"""
        
        score = 8.0  # 基准分
        suggestions = []
        
        # 数据支撑完整性
        if "nps_overview" in report_content:
            nps_overview = report_content["nps_overview"]
            if not nps_overview.get("content", {}).get("distribution"):
                score -= 1.0
                suggestions.append("缺少NPS分布数据支撑")
        
        # 分析深度
        if "detailed_analysis" in report_content:
            detailed = report_content["detailed_analysis"]
            analysis_components = [
                "score_analysis",
                "distribution_analysis", 
                "segment_insights",
                "confidence_assessment"
            ]
            
            missing_components = sum(
                1 for comp in analysis_components 
                if comp not in detailed.get("content", {})
            )
            
            if missing_components > 2:
                score -= 1.5
                suggestions.append("详细分析深度不足")
            elif missing_components > 0:
                score -= 0.5
        
        # 业务洞察专业性
        if "business_intelligence" in report_content:
            bi_content = report_content["business_intelligence"]
            if bi_content.get("content", {}).get("competitive_analysis"):
                score += 0.5
            if bi_content.get("content", {}).get("trend_predictions"):
                score += 0.5
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="professionalism",
            score=score,
            rationale="基于数据支撑、分析深度和业务洞察专业性评估",
            improvement_suggestions=suggestions or ["报告专业性良好"],
            confidence=0.8
        )
    
    async def _assess_decision_support(self, report_content: Dict[str, Any]) -> QualityScore:
        """评估决策支持度"""
        
        score = 7.0  # 基准分
        suggestions = []
        
        # 行动建议的决策支持性
        if "recommendations" in report_content:
            rec_content = report_content["recommendations"].get("content", {})
            
            # 检查优先级分类
            priority_categories = [
                "immediate_actions",
                "short_term_actions", 
                "medium_term_actions"
            ]
            
            available_categories = sum(
                1 for cat in priority_categories 
                if rec_content.get(cat)
            )
            
            if available_categories >= 3:
                score += 1.5
            elif available_categories >= 2:
                score += 0.5
            else:
                score -= 1.0
                suggestions.append("缺少分阶段的行动建议分类")
            
            # 检查成功指标
            if rec_content.get("success_metrics"):
                score += 1.0
            else:
                score -= 0.5
                suggestions.append("缺少成功评估指标")
        
        # 风险识别和应对
        if "nps_overview" in report_content:
            # 检查是否有风险警示
            if "risk_alerts" in report_content.get("executive_summary", {}):
                score += 0.5
        
        # 业务影响评估
        if "business_intelligence" in report_content:
            bi_content = report_content["business_intelligence"].get("content", {})
            if bi_content.get("market_insights"):
                score += 0.5
        
        score = max(0, min(10, score))
        
        return QualityScore(
            dimension="decision_support",
            score=score,
            rationale="基于行动建议明确性、优先级分类和业务影响评估",
            improvement_suggestions=suggestions or ["决策支持度良好"],
            confidence=0.8
        )

class QualityAssuranceOrchestrator:
    """质量保证协调器"""
    
    def __init__(self):
        self.nps_expert = NPSExpertCritic()
        self.business_analyst = BusinessAnalystCritic()
        self.report_critic = ReportQualityCritic()
        
        # 质量标准
        self.quality_thresholds = {
            "excellent": 8.5,
            "good": 7.5,
            "acceptable": 6.5,
            "needs_improvement": 5.0
        }
    
    async def conduct_comprehensive_review(self,
                                         nps_calculation: NPSCalculationResult,
                                         processed_nps_data: ProcessedNPSData,
                                         survey_data: ProcessedSurveyData,
                                         nps_insights: NPSInsightResult,
                                         question_group_analysis: QuestionGroupAnalysisResult,
                                         business_insights: BusinessInsightsResult,
                                         report_content: Dict[str, Any]) -> ComprehensiveQualityAssessment:
        """进行综合质量评审"""
        
        logger.info("开始综合质量评审")
        
        # 并行执行各专家评审
        review_tasks = [
            self.nps_expert.review_analysis(nps_calculation, processed_nps_data, nps_insights),
            self.business_analyst.review_analysis(business_insights, question_group_analysis),
            self.report_critic.review_report_quality(report_content)
        ]
        
        individual_reviews = await asyncio.gather(*review_tasks)
        
        # 计算综合质量分数
        overall_quality_score = sum(review.overall_score for review in individual_reviews) / len(individual_reviews)
        
        # 生成共识评估
        consensus_assessment = await self._generate_consensus_assessment(individual_reviews)
        
        # 生成修订建议
        revision_recommendations = await self._generate_revision_recommendations(individual_reviews)
        
        # 确定质量认证等级
        quality_certification = self._determine_quality_certification(overall_quality_score)
        
        return ComprehensiveQualityAssessment(
            overall_quality_score=overall_quality_score,
            individual_reviews=individual_reviews,
            consensus_assessment=consensus_assessment,
            revision_recommendations=revision_recommendations,
            quality_certification=quality_certification,
            assessment_metadata={
                "assessment_timestamp": datetime.now().isoformat(),
                "reviewers_count": len(individual_reviews),
                "quality_framework_version": "v2.0",
                "assessment_depth": "comprehensive"
            }
        )
    
    async def _generate_consensus_assessment(self, reviews: List[QualityReview]) -> Dict[str, Any]:
        """生成共识评估"""
        
        # 计算各维度的平均分
        all_dimensions = {}
        for review in reviews:
            for score in review.dimension_scores:
                if score.dimension not in all_dimensions:
                    all_dimensions[score.dimension] = []
                all_dimensions[score.dimension].append(score.score)
        
        dimension_averages = {
            dim: sum(scores) / len(scores) 
            for dim, scores in all_dimensions.items()
        }
        
        # 识别一致的强项和弱项
        strong_areas = [dim for dim, avg in dimension_averages.items() if avg >= 8.0]
        weak_areas = [dim for dim, avg in dimension_averages.items() if avg < 6.5]
        
        # 统计修订需求
        revision_needed_count = sum(1 for review in reviews if review.revision_required)
        
        return {
            "dimension_averages": dimension_averages,
            "strong_areas": strong_areas,
            "weak_areas": weak_areas,
            "revision_consensus": revision_needed_count >= 2,
            "reviewer_agreement": len(strong_areas) + len(weak_areas) >= 2,
            "priority_improvement_areas": weak_areas
        }
    
    async def _generate_revision_recommendations(self, reviews: List[QualityReview]) -> List[Dict[str, Any]]:
        """生成修订建议"""
        
        recommendations = []
        
        # 收集所有优先修复项
        all_priority_fixes = []
        for review in reviews:
            all_priority_fixes.extend([
                {"source": review.reviewer_name, "fix": fix}
                for fix in review.priority_fixes
            ])
        
        # 收集所有改进建议
        all_improvements = []
        for review in reviews:
            all_improvements.extend([
                {"source": review.reviewer_name, "area": area}
                for area in review.improvement_areas
            ])
        
        # 根据重要性生成建议
        if all_priority_fixes:
            recommendations.append({
                "priority": "urgent",
                "category": "critical_fixes",
                "title": "关键问题修复",
                "description": "需要立即解决的关键质量问题",
                "items": all_priority_fixes[:5],  # 最多5个最关键的
                "timeline": "立即"
            })
        
        if all_improvements:
            recommendations.append({
                "priority": "high",
                "category": "quality_improvement",
                "title": "质量提升建议",
                "description": "进一步提升分析和报告质量的建议",
                "items": all_improvements[:8],  # 最多8个改进建议
                "timeline": "短期内"
            })
        
        # 如果整体质量良好，提供优化建议
        overall_score = sum(review.overall_score for review in reviews) / len(reviews)
        if overall_score >= 7.5:
            recommendations.append({
                "priority": "medium",
                "category": "optimization",
                "title": "卓越化优化",
                "description": "在良好基础上的进一步优化建议",
                "items": [
                    {"suggestion": "考虑增加更多创新性洞察"},
                    {"suggestion": "探索更先进的分析方法"},
                    {"suggestion": "提升报告的可视化效果"}
                ],
                "timeline": "中长期"
            })
        
        return recommendations
    
    def _determine_quality_certification(self, overall_score: float) -> str:
        """确定质量认证等级"""
        
        if overall_score >= self.quality_thresholds["excellent"]:
            return "优秀"
        elif overall_score >= self.quality_thresholds["good"]:
            return "良好"
        elif overall_score >= self.quality_thresholds["acceptable"]:
            return "合格"
        elif overall_score >= self.quality_thresholds["needs_improvement"]:
            return "需要改进"
        else:
            return "不合格"

# 使用示例
async def main():
    """主函数示例"""
    orchestrator = QualityAssuranceOrchestrator()
    print("质量保证系统初始化完成")

if __name__ == "__main__":
    asyncio.run(main())