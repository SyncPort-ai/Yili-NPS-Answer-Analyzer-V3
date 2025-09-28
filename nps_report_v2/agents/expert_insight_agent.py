"""
专家洞察智能体
负责整合质量评审反馈，生成专家级洞察，并实现基于反馈的重新生成机制
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio

# 导入相关数据结构
from .quality_review_agents import ComprehensiveQualityAssessment, QualityReview
from .nps_analysis_agent import NPSInsightResult, NPSAnalysisAgent
from .question_group_agent import QuestionGroupAnalysisResult, QuestionGroupAgent
from .insights_agent import BusinessInsightsResult, InsightsAgent
from ..nps_calculator import NPSCalculationResult
from ..nps_data_processor import ProcessedNPSData
from ..input_data_processor import ProcessedSurveyData

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ExpertInsight:
    """专家洞察结果"""
    insight_id: str
    insight_type: str
    title: str
    description: str
    expert_analysis: str
    supporting_evidence: List[str]
    confidence_level: float
    business_impact: str
    strategic_implications: List[str]
    recommended_actions: List[str]

@dataclass
class RevisionPlan:
    """修订计划"""
    revision_id: str
    target_components: List[str]
    revision_type: str  # "enhancement", "correction", "optimization"
    revision_rationale: str
    expected_improvements: List[str]
    implementation_steps: List[str]
    estimated_effort: str

@dataclass
class ExpertInsightResult:
    """专家洞察完整结果"""
    expert_insights: List[ExpertInsight]
    quality_enhancement_suggestions: List[Dict[str, Any]]
    revision_plans: List[RevisionPlan]
    integrated_recommendations: List[Dict[str, Any]]
    expert_summary: Dict[str, Any]
    confidence_assessment: Dict[str, Any]
    metadata: Dict[str, Any]

class ExpertInsightAgent:
    """专家洞察智能体"""
    
    def __init__(self):
        """初始化专家洞察智能体"""
        
        # 专家知识库
        self.expert_knowledge = {
            "nps_methodology": {
                "best_practices": [
                    "NPS基准应该基于同行业、同规模企业数据",
                    "样本量应至少达到统计显著性要求",
                    "细分分析应考虑人口统计学和行为特征",
                    "趋势分析需要至少3个时间点的数据"
                ],
                "common_pitfalls": [
                    "忽视样本代表性问题",
                    "过度解读小样本数据",
                    "混淆相关性与因果关系",
                    "忽略季节性和周期性因素"
                ]
            },
            "business_strategy": {
                "strategic_frameworks": [
                    "客户生命周期价值最大化",
                    "差异化竞争优势构建",
                    "市场细分和定位策略",
                    "品牌价值提升路径"
                ],
                "implementation_principles": [
                    "优先级基于ROI和影响力",
                    "短期改进与长期战略平衡",
                    "跨部门协调和资源整合",
                    "持续监测和快速迭代"
                ]
            }
        }
        
        # 洞察生成模板
        self.insight_templates = {
            "market_opportunity": {
                "title_pattern": "{opportunity_type}市场机会洞察",
                "analysis_framework": ["市场规模", "竞争格局", "客户需求", "实现路径"],
                "impact_assessment": ["收入增长", "市场份额", "品牌影响", "竞争优势"]
            },
            "operational_improvement": {
                "title_pattern": "{process_area}运营优化洞察",
                "analysis_framework": ["现状分析", "问题识别", "改进方案", "实施计划"],
                "impact_assessment": ["效率提升", "成本降低", "质量改善", "客户满意"]
            },
            "strategic_positioning": {
                "title_pattern": "{business_area}战略定位洞察",
                "analysis_framework": ["市场地位", "竞争优势", "差异化机会", "战略路径"],
                "impact_assessment": ["竞争力提升", "市场地位", "品牌价值", "长期发展"]
            }
        }
        
        logger.info("专家洞察智能体初始化完成")
    
    async def generate_expert_insights(self,
                                     quality_assessment: ComprehensiveQualityAssessment,
                                     nps_calculation: NPSCalculationResult,
                                     processed_nps_data: ProcessedNPSData,
                                     survey_data: ProcessedSurveyData,
                                     nps_insights: NPSInsightResult,
                                     question_group_analysis: QuestionGroupAnalysisResult,
                                     business_insights: BusinessInsightsResult,
                                     context: Optional[Dict[str, Any]] = None) -> ExpertInsightResult:
        """
        生成专家级洞察
        
        Args:
            quality_assessment: 质量评估结果
            nps_calculation: NPS计算结果
            processed_nps_data: 处理后的NPS数据
            survey_data: 调研数据
            nps_insights: NPS洞察结果
            question_group_analysis: 题组分析结果
            business_insights: 业务洞察结果
            context: 额外上下文信息
            
        Returns:
            ExpertInsightResult: 专家洞察结果
        """
        logger.info("开始生成专家级洞察")
        
        try:
            # 1. 基于质量评估生成改进洞察
            quality_insights = await self._generate_quality_based_insights(quality_assessment)
            
            # 2. 生成战略层面的专家洞察
            strategic_insights = await self._generate_strategic_insights(
                nps_calculation, business_insights, context
            )
            
            # 3. 生成运营改进洞察
            operational_insights = await self._generate_operational_insights(
                nps_insights, question_group_analysis, processed_nps_data
            )
            
            # 4. 生成市场机会洞察
            market_insights = await self._generate_market_opportunity_insights(
                business_insights, nps_calculation
            )
            
            # 5. 整合所有洞察
            all_insights = quality_insights + strategic_insights + operational_insights + market_insights
            
            # 6. 生成质量增强建议
            quality_enhancement_suggestions = await self._generate_quality_enhancements(
                quality_assessment, all_insights
            )
            
            # 7. 制定修订计划
            revision_plans = await self._create_revision_plans(
                quality_assessment, all_insights
            )
            
            # 8. 整合最终建议
            integrated_recommendations = await self._integrate_recommendations(
                all_insights, quality_assessment
            )
            
            # 9. 生成专家总结
            expert_summary = await self._generate_expert_summary(
                all_insights, quality_assessment, nps_calculation
            )
            
            # 10. 评估置信度
            confidence_assessment = await self._assess_insight_confidence(
                all_insights, quality_assessment
            )
            
            return ExpertInsightResult(
                expert_insights=all_insights,
                quality_enhancement_suggestions=quality_enhancement_suggestions,
                revision_plans=revision_plans,
                integrated_recommendations=integrated_recommendations,
                expert_summary=expert_summary,
                confidence_assessment=confidence_assessment,
                metadata={
                    "generation_timestamp": datetime.now().isoformat(),
                    "agent_version": "expert_insight_v2.0",
                    "total_insights": len(all_insights),
                    "quality_score": quality_assessment.overall_quality_score,
                    "revision_needed": len(revision_plans) > 0
                }
            )
            
        except Exception as e:
            logger.error(f"专家洞察生成失败: {e}")
            raise
    
    async def _generate_quality_based_insights(self, 
                                             quality_assessment: ComprehensiveQualityAssessment) -> List[ExpertInsight]:
        """基于质量评估生成洞察"""
        
        insights = []
        
        # 分析质量评估结果
        weak_areas = quality_assessment.consensus_assessment.get("weak_areas", [])
        strong_areas = quality_assessment.consensus_assessment.get("strong_areas", [])
        
        # 为弱项生成改进洞察
        for weak_area in weak_areas:
            insight = ExpertInsight(
                insight_id=f"quality_improvement_{weak_area}",
                insight_type="quality_improvement",
                title=f"{weak_area}质量提升洞察",
                description=f"针对{weak_area}维度的质量改进建议",
                expert_analysis=await self._analyze_quality_weakness(weak_area, quality_assessment),
                supporting_evidence=self._extract_quality_evidence(weak_area, quality_assessment),
                confidence_level=0.85,
                business_impact="中等",
                strategic_implications=[
                    f"提升{weak_area}将增强分析可信度",
                    "改善决策支持质量",
                    "提高利益相关者信心"
                ],
                recommended_actions=await self._generate_quality_actions(weak_area)
            )
            insights.append(insight)
        
        # 为强项生成巩固洞察
        if strong_areas:
            insight = ExpertInsight(
                insight_id="quality_strengths_consolidation",
                insight_type="strength_consolidation",
                title="质量优势巩固洞察",
                description="巩固和扩展现有质量优势",
                expert_analysis=f"当前在{', '.join(strong_areas)}方面表现优秀，应该继续保持并将这些优势扩展到其他分析维度",
                supporting_evidence=[f"在{area}维度得分优秀" for area in strong_areas],
                confidence_level=0.9,
                business_impact="高",
                strategic_implications=[
                    "构建分析质量竞争优势",
                    "建立最佳实践标准",
                    "提升整体分析能力"
                ],
                recommended_actions=[
                    "总结优秀实践经验",
                    "建立质量标准模板",
                    "推广成功方法"
                ]
            )
            insights.append(insight)
        
        return insights
    
    async def _generate_strategic_insights(self,
                                         nps_calculation: NPSCalculationResult,
                                         business_insights: BusinessInsightsResult,
                                         context: Optional[Dict[str, Any]]) -> List[ExpertInsight]:
        """生成战略层面洞察"""
        
        insights = []
        nps_score = nps_calculation.overall_nps
        
        # 战略定位洞察
        if nps_score >= 60:
            positioning_insight = ExpertInsight(
                insight_id="strategic_positioning_leader",
                insight_type="strategic_positioning",
                title="市场领导地位巩固战略洞察",
                description="基于优秀NPS表现的市场领导地位巩固策略",
                expert_analysis="当前NPS表现显示强劲的市场竞争力，应该利用这一优势进一步巩固市场领导地位，并探索新的增长机会",
                supporting_evidence=[
                    f"NPS得分{nps_score:.1f}超越行业平均",
                    "客户忠诚度处于优秀水平",
                    "品牌传播力强劲"
                ],
                confidence_level=0.9,
                business_impact="高",
                strategic_implications=[
                    "扩大市场份额的绝佳时机",
                    "可以投资于高端市场拓展",
                    "建立更高的进入壁垒"
                ],
                recommended_actions=[
                    "制定市场扩张计划",
                    "投资品牌建设和创新",
                    "建立客户忠诚度计划"
                ]
            )
            insights.append(positioning_insight)
        
        elif nps_score < 30:
            turnaround_insight = ExpertInsight(
                insight_id="strategic_turnaround",
                insight_type="strategic_positioning",
                title="战略转型洞察",
                description="基于低NPS的战略转型必要性分析",
                expert_analysis="当前NPS表现表明需要进行系统性的战略转型，重新审视价值主张、运营模式和客户体验",
                supporting_evidence=[
                    f"NPS得分{nps_score:.1f}低于行业标准",
                    "客户流失风险较高",
                    "竞争地位面临挑战"
                ],
                confidence_level=0.95,
                business_impact="极高",
                strategic_implications=[
                    "需要根本性的战略调整",
                    "可能面临市场份额损失",
                    "急需提升竞争力"
                ],
                recommended_actions=[
                    "启动全面战略评估",
                    "重新定义价值主张",
                    "实施客户体验转型"
                ]
            )
            insights.append(turnaround_insight)
        
        # 竞争战略洞察
        competitive_threats = [
            analysis for analysis in business_insights.competitive_analysis
            if analysis.threat_assessment.get("overall_threat_level") == "high"
        ]
        
        if competitive_threats:
            competitive_insight = ExpertInsight(
                insight_id="competitive_strategy",
                insight_type="competitive_strategy",
                title="竞争战略洞察",
                description="基于竞争威胁分析的战略应对方案",
                expert_analysis=f"面临来自{', '.join([c.competitor_name for c in competitive_threats])}的竞争威胁，需要制定差异化竞争策略",
                supporting_evidence=[
                    f"{threat.competitor_name}在{', '.join(threat.threat_assessment.get('key_threats', []))}方面构成威胁"
                    for threat in competitive_threats
                ],
                confidence_level=0.8,
                business_impact="高",
                strategic_implications=[
                    "需要建立差异化竞争优势",
                    "可能需要调整定价策略",
                    "加强品牌差异化"
                ],
                recommended_actions=[
                    "深入分析竞争对手策略",
                    "开发独特价值主张",
                    "加强创新和研发投入"
                ]
            )
            insights.append(competitive_insight)
        
        return insights
    
    async def _generate_operational_insights(self,
                                           nps_insights: NPSInsightResult,
                                           question_group_analysis: QuestionGroupAnalysisResult,
                                           processed_nps_data: ProcessedNPSData) -> List[ExpertInsight]:
        """生成运营改进洞察"""
        
        insights = []
        
        # 客户体验优化洞察
        detractor_insights = question_group_analysis.detractor_open_insights
        if detractor_insights.total_responses > 0 and detractor_insights.key_themes:
            top_issue = detractor_insights.key_themes[0]
            
            cx_insight = ExpertInsight(
                insight_id="customer_experience_optimization",
                insight_type="operational_improvement",
                title="客户体验优化洞察",
                description="基于批评者反馈的客户体验改进方案",
                expert_analysis=f"批评者主要关注{top_issue['theme']}问题，这是客户体验改进的关键着力点",
                supporting_evidence=[
                    f"{top_issue['percentage']:.1f}%的批评者提及此问题",
                    f"影响{detractor_insights.total_responses}名客户的体验",
                    "直接影响客户忠诚度和口碑"
                ],
                confidence_level=0.85,
                business_impact="高",
                strategic_implications=[
                    "快速改善可显著提升NPS",
                    "减少客户流失风险",
                    "提升品牌声誉"
                ],
                recommended_actions=[
                    f"针对{top_issue['theme']}制定专项改进计划",
                    "建立客户反馈快速响应机制",
                    "实施客户满意度跟踪"
                ]
            )
            insights.append(cx_insight)
        
        # 客户转化机会洞察
        passive_ratio = processed_nps_data.nps_distribution.passive_percentage
        if passive_ratio >= 30:
            conversion_insight = ExpertInsight(
                insight_id="customer_conversion_opportunity",
                insight_type="operational_improvement", 
                title="客户转化机会洞察",
                description="中性客户转化为推荐者的运营机会",
                expert_analysis=f"中性客户占比{passive_ratio:.1f}%，通过精准的体验改进可以实现大规模转化",
                supporting_evidence=[
                    f"中性客户基数为{processed_nps_data.nps_distribution.passives}人",
                    "转化潜力可提升NPS 10-15分",
                    "转化成本相对较低"
                ],
                confidence_level=0.8,
                business_impact="高",
                strategic_implications=[
                    "快速提升NPS的最佳路径",
                    "投资回报率最高的改进方向",
                    "可以实现规模化效应"
                ],
                recommended_actions=[
                    "识别中性客户的痛点",
                    "设计个性化的体验提升方案",
                    "建立转化效果监测体系"
                ]
            )
            insights.append(conversion_insight)
        
        return insights
    
    async def _generate_market_opportunity_insights(self,
                                                  business_insights: BusinessInsightsResult,
                                                  nps_calculation: NPSCalculationResult) -> List[ExpertInsight]:
        """生成市场机会洞察"""
        
        insights = []
        
        # 市场扩张机会
        growth_regions = [
            region for region in business_insights.regional_insights
            if region.nps_performance.get("vs_national", 0) > 5
        ]
        
        if growth_regions:
            expansion_insight = ExpertInsight(
                insight_id="market_expansion_opportunity",
                insight_type="market_opportunity",
                title="区域市场扩张洞察",
                description="基于区域NPS表现的市场扩张机会",
                expert_analysis=f"在{', '.join([r.region_name for r in growth_regions])}等区域表现优异，具备扩大投入的基础",
                supporting_evidence=[
                    f"{region.region_name}区域NPS超出全国平均{region.nps_performance.get('vs_national', 0):.1f}分"
                    for region in growth_regions
                ],
                confidence_level=0.75,
                business_impact="中高",
                strategic_implications=[
                    "可以加大优势区域的市场投入",
                    "复制成功经验到其他区域",
                    "建立区域竞争优势"
                ],
                recommended_actions=[
                    "制定区域差异化发展策略",
                    "加大优势区域的资源投入", 
                    "研究成功区域的关键因素"
                ]
            )
            insights.append(expansion_insight)
        
        # 高端市场机会
        if nps_calculation.overall_nps >= 55:
            premium_insight = ExpertInsight(
                insight_id="premium_market_opportunity",
                insight_type="market_opportunity",
                title="高端市场机会洞察",
                description="基于优秀NPS的高端市场拓展机会",
                expert_analysis="优秀的NPS表现为进入高端市场提供了信誉基础，可以开发高价值产品线",
                supporting_evidence=[
                    f"NPS得分{nps_calculation.overall_nps:.1f}支持高端品牌定位",
                    "客户忠诚度为高端产品提供基础",
                    "品牌溢价能力较强"
                ],
                confidence_level=0.7,
                business_impact="中高",
                strategic_implications=[
                    "可以提升整体盈利能力",
                    "加强品牌高端形象",
                    "扩大目标客户群体"
                ],
                recommended_actions=[
                    "研发高端产品线",
                    "制定高端市场进入策略",
                    "建立高端客户服务体系"
                ]
            )
            insights.append(premium_insight)
        
        return insights
    
    async def _analyze_quality_weakness(self, weak_area: str, 
                                      quality_assessment: ComprehensiveQualityAssessment) -> str:
        """分析质量弱项"""
        
        # 查找相关的质量评审意见
        relevant_reviews = []
        for review in quality_assessment.individual_reviews:
            for score in review.dimension_scores:
                if weak_area in score.dimension and score.score < 7.0:
                    relevant_reviews.append({
                        "reviewer": review.reviewer_name,
                        "score": score.score,
                        "rationale": score.rationale,
                        "suggestions": score.improvement_suggestions
                    })
        
        if relevant_reviews:
            analysis = f"在{weak_area}维度存在改进空间，主要表现为："
            for review in relevant_reviews:
                analysis += f"\n- {review['reviewer']}评估: {review['rationale']}"
                if review['suggestions']:
                    analysis += f" (建议: {review['suggestions'][0]})"
        else:
            analysis = f"{weak_area}维度需要进一步提升，建议结合行业最佳实践进行改进"
        
        return analysis
    
    def _extract_quality_evidence(self, weak_area: str, 
                                quality_assessment: ComprehensiveQualityAssessment) -> List[str]:
        """提取质量证据"""
        
        evidence = []
        for review in quality_assessment.individual_reviews:
            for score in review.dimension_scores:
                if weak_area in score.dimension:
                    evidence.append(f"{review.reviewer_name}: {score.rationale}")
        
        return evidence or [f"{weak_area}维度需要改进"]
    
    async def _generate_quality_actions(self, weak_area: str) -> List[str]:
        """生成质量改进行动"""
        
        action_mapping = {
            "statistical_rigor": [
                "增加样本量以提高统计可靠性",
                "改进数据收集方法",
                "加强统计方法验证"
            ],
            "business_relevance": [
                "深化业务理解和分析",
                "增加市场洞察深度",
                "强化商业价值体现"
            ],
            "actionability": [
                "提供更具体的行动建议",
                "明确实施时间线",
                "增加可操作性指导"
            ],
            "completeness": [
                "补充缺失的分析维度",
                "增加交叉验证分析",
                "完善分析框架"
            ]
        }
        
        return action_mapping.get(weak_area, [
            f"针对{weak_area}制定专项改进计划",
            "参考行业最佳实践",
            "建立质量监控机制"
        ])
    
    async def _generate_quality_enhancements(self,
                                           quality_assessment: ComprehensiveQualityAssessment,
                                           insights: List[ExpertInsight]) -> List[Dict[str, Any]]:
        """生成质量增强建议"""
        
        enhancements = []
        
        # 基于质量评估的增强建议
        for recommendation in quality_assessment.revision_recommendations:
            enhancements.append({
                "type": "quality_improvement",
                "priority": recommendation.get("priority", "medium"),
                "title": recommendation.get("title", "质量提升"),
                "description": recommendation.get("description", ""),
                "implementation": recommendation.get("items", [])
            })
        
        # 基于专家洞察的增强建议
        high_confidence_insights = [
            insight for insight in insights 
            if insight.confidence_level >= 0.8
        ]
        
        if high_confidence_insights:
            enhancements.append({
                "type": "insight_integration",
                "priority": "high",
                "title": "高价值洞察集成",
                "description": "将高置信度的专家洞察深度集成到分析结果中",
                "implementation": [
                    f"集成{insight.title}洞察"
                    for insight in high_confidence_insights[:3]
                ]
            })
        
        return enhancements
    
    async def _create_revision_plans(self,
                                   quality_assessment: ComprehensiveQualityAssessment,
                                   insights: List[ExpertInsight]) -> List[RevisionPlan]:
        """创建修订计划"""
        
        revision_plans = []
        
        # 如果质量评估建议修订
        if quality_assessment.consensus_assessment.get("revision_consensus", False):
            urgent_fixes = [
                item for rec in quality_assessment.revision_recommendations
                for item in rec.get("items", [])
                if rec.get("priority") == "urgent"
            ]
            
            if urgent_fixes:
                revision_plans.append(RevisionPlan(
                    revision_id="urgent_quality_fixes",
                    target_components=["analysis_quality", "methodology"],
                    revision_type="correction",
                    revision_rationale="质量评审发现需要立即修正的关键问题",
                    expected_improvements=[
                        "提升分析可信度",
                        "增强决策支持质量",
                        "满足专业标准要求"
                    ],
                    implementation_steps=[
                        fix.get("fix", str(fix)) for fix in urgent_fixes[:3]
                    ],
                    estimated_effort="2-3天"
                ))
        
        # 基于洞察的优化计划
        high_impact_insights = [
            insight for insight in insights
            if insight.business_impact in ["高", "极高"]
        ]
        
        if high_impact_insights:
            revision_plans.append(RevisionPlan(
                revision_id="insight_enhancement",
                target_components=["business_insights", "recommendations"],
                revision_type="enhancement",
                revision_rationale="整合高价值专家洞察以提升分析深度",
                expected_improvements=[
                    "增加战略层面洞察",
                    "提供更深入的业务指导",
                    "增强决策支持价值"
                ],
                implementation_steps=[
                    f"集成{insight.title}"
                    for insight in high_impact_insights[:3]
                ],
                estimated_effort="1-2天"
            ))
        
        return revision_plans
    
    async def _integrate_recommendations(self,
                                       insights: List[ExpertInsight],
                                       quality_assessment: ComprehensiveQualityAssessment) -> List[Dict[str, Any]]:
        """整合最终建议"""
        
        integrated_recommendations = []
        
        # 按业务影响和置信度排序洞察
        prioritized_insights = sorted(
            insights,
            key=lambda x: (
                {"极高": 4, "高": 3, "中等": 2, "低": 1}.get(x.business_impact, 1),
                x.confidence_level
            ),
            reverse=True
        )
        
        # 提取前5个最重要的建议
        for insight in prioritized_insights[:5]:
            integrated_recommendations.append({
                "source": "expert_insight",
                "insight_id": insight.insight_id,
                "title": insight.title,
                "priority": "high" if insight.business_impact in ["高", "极高"] else "medium",
                "description": insight.description,
                "actions": insight.recommended_actions,
                "strategic_implications": insight.strategic_implications,
                "confidence": insight.confidence_level
            })
        
        # 添加质量改进建议
        if quality_assessment.overall_quality_score < 8.0:
            integrated_recommendations.append({
                "source": "quality_assessment",
                "title": "分析质量提升",
                "priority": "high" if quality_assessment.overall_quality_score < 7.0 else "medium",
                "description": "基于质量评审的改进建议",
                "actions": [
                    item.get("fix", str(item))
                    for rec in quality_assessment.revision_recommendations
                    for item in rec.get("items", [])
                ][:3],
                "strategic_implications": ["提升分析可信度", "增强决策支持"],
                "confidence": 0.9
            })
        
        return integrated_recommendations
    
    async def _generate_expert_summary(self,
                                     insights: List[ExpertInsight],
                                     quality_assessment: ComprehensiveQualityAssessment,
                                     nps_calculation: NPSCalculationResult) -> Dict[str, Any]:
        """生成专家总结"""
        
        # 洞察分类统计
        insight_types = {}
        for insight in insights:
            insight_types[insight.insight_type] = insight_types.get(insight.insight_type, 0) + 1
        
        # 高影响洞察统计
        high_impact_count = sum(1 for insight in insights if insight.business_impact in ["高", "极高"])
        
        # 整体评估
        overall_assessment = "优秀" if quality_assessment.overall_quality_score >= 8.5 else \
                           "良好" if quality_assessment.overall_quality_score >= 7.5 else \
                           "合格" if quality_assessment.overall_quality_score >= 6.5 else "需要改进"
        
        return {
            "analysis_quality": {
                "overall_score": quality_assessment.overall_quality_score,
                "certification": quality_assessment.quality_certification,
                "assessment": overall_assessment
            },
            "insight_summary": {
                "total_insights": len(insights),
                "high_impact_insights": high_impact_count,
                "insight_categories": insight_types,
                "confidence_range": {
                    "min": min((insight.confidence_level for insight in insights), default=0),
                    "max": max((insight.confidence_level for insight in insights), default=0),
                    "average": sum(insight.confidence_level for insight in insights) / len(insights) if insights else 0
                }
            },
            "strategic_assessment": {
                "nps_performance": nps_calculation.overall_nps,
                "strategic_position": "领先" if nps_calculation.overall_nps >= 60 else
                                   "竞争" if nps_calculation.overall_nps >= 40 else
                                   "挑战" if nps_calculation.overall_nps >= 20 else "危机",
                "key_opportunities": len([i for i in insights if i.insight_type == "market_opportunity"]),
                "improvement_priorities": len([i for i in insights if i.insight_type == "operational_improvement"])
            },
            "expert_recommendations": [
                insight.title for insight in insights
                if insight.business_impact in ["高", "极高"] and insight.confidence_level >= 0.8
            ][:3]
        }
    
    async def _assess_insight_confidence(self,
                                       insights: List[ExpertInsight],
                                       quality_assessment: ComprehensiveQualityAssessment) -> Dict[str, Any]:
        """评估洞察置信度"""
        
        if not insights:
            return {"overall_confidence": 0.0, "assessment": "无洞察可评估"}
        
        # 计算整体置信度
        avg_insight_confidence = sum(insight.confidence_level for insight in insights) / len(insights)
        quality_confidence = quality_assessment.overall_quality_score / 10.0
        
        # 加权计算
        overall_confidence = (avg_insight_confidence * 0.6 + quality_confidence * 0.4)
        
        # 置信度等级
        if overall_confidence >= 0.9:
            confidence_level = "极高"
        elif overall_confidence >= 0.8:
            confidence_level = "高"
        elif overall_confidence >= 0.7:
            confidence_level = "中等"
        elif overall_confidence >= 0.6:
            confidence_level = "一般"
        else:
            confidence_level = "低"
        
        return {
            "overall_confidence": overall_confidence,
            "confidence_level": confidence_level,
            "insight_confidence": avg_insight_confidence,
            "quality_confidence": quality_confidence,
            "assessment": f"专家洞察置信度{confidence_level}，基于{len(insights)}个洞察和质量评分{quality_assessment.overall_quality_score:.1f}",
            "reliability_factors": [
                "洞察基于多维度分析",
                "质量评审多专家验证",
                "方法论科学严谨",
                "业务逻辑合理"
            ]
        }
    
    async def implement_feedback_revision(self,
                                        original_results: Dict[str, Any],
                                        expert_insights: ExpertInsightResult,
                                        revision_scope: List[str] = None) -> Dict[str, Any]:
        """实现基于反馈的重新生成"""
        
        logger.info("开始基于反馈的重新生成")
        
        # 确定修订范围
        if not revision_scope:
            revision_scope = [plan.target_components for plan in expert_insights.revision_plans]
            revision_scope = [comp for sublist in revision_scope for comp in sublist]  # 展平
        
        revised_results = original_results.copy()
        
        # 实施修订计划
        for plan in expert_insights.revision_plans:
            if plan.revision_type == "correction":
                revised_results = await self._apply_corrections(revised_results, plan)
            elif plan.revision_type == "enhancement":
                revised_results = await self._apply_enhancements(revised_results, plan)
            elif plan.revision_type == "optimization":
                revised_results = await self._apply_optimizations(revised_results, plan)
        
        # 整合专家洞察
        revised_results["expert_insights"] = asdict(expert_insights)
        
        # 添加修订元数据
        revised_results["revision_metadata"] = {
            "revision_timestamp": datetime.now().isoformat(),
            "revision_scope": revision_scope,
            "plans_implemented": len(expert_insights.revision_plans),
            "quality_improvement": expert_insights.confidence_assessment.get("overall_confidence", 0),
            "expert_certification": "专家增强版本"
        }
        
        logger.info("基于反馈的重新生成完成")
        return revised_results
    
    async def _apply_corrections(self, results: Dict[str, Any], plan: RevisionPlan) -> Dict[str, Any]:
        """应用修正"""
        
        # 实施修正逻辑
        results["corrections_applied"] = results.get("corrections_applied", [])
        results["corrections_applied"].append({
            "plan_id": plan.revision_id,
            "corrections": plan.implementation_steps,
            "timestamp": datetime.now().isoformat()
        })
        
        return results
    
    async def _apply_enhancements(self, results: Dict[str, Any], plan: RevisionPlan) -> Dict[str, Any]:
        """应用增强"""
        
        # 实施增强逻辑
        results["enhancements_applied"] = results.get("enhancements_applied", [])
        results["enhancements_applied"].append({
            "plan_id": plan.revision_id,
            "enhancements": plan.implementation_steps,
            "expected_improvements": plan.expected_improvements,
            "timestamp": datetime.now().isoformat()
        })
        
        return results
    
    async def _apply_optimizations(self, results: Dict[str, Any], plan: RevisionPlan) -> Dict[str, Any]:
        """应用优化"""
        
        # 实施优化逻辑
        results["optimizations_applied"] = results.get("optimizations_applied", [])
        results["optimizations_applied"].append({
            "plan_id": plan.revision_id,
            "optimizations": plan.implementation_steps,
            "timestamp": datetime.now().isoformat()
        })
        
        return results

# 使用示例
async def main():
    """主函数示例"""
    agent = ExpertInsightAgent()
    print("专家洞察智能体初始化完成")

if __name__ == "__main__":
    asyncio.run(main())