"""
洞察智能体
负责市场洞察、区域细分分析、竞品对比分析、趋势预测等业务智能分析
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import asyncio
import json

# 导入相关数据结构
from ..nps_calculator import NPSCalculationResult
from ..nps_data_processor import ProcessedNPSData
from ..input_data_processor import ProcessedSurveyData
from ..persistent_knowledge_manager import PersistentKnowledgeManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class MarketInsight:
    """市场洞察结果"""
    insight_type: str
    title: str
    description: str
    confidence_level: float
    impact_assessment: str
    supporting_data: Dict[str, Any]
    recommendations: List[str]
    priority: str

@dataclass
class CompetitiveAnalysis:
    """竞品分析结果"""
    competitor_name: str
    competitive_position: str
    strength_gaps: List[str]
    opportunity_areas: List[str]
    threat_assessment: Dict[str, Any]
    strategic_recommendations: List[str]

@dataclass
class RegionalInsight:
    """区域洞察结果"""
    region_name: str
    nps_performance: Dict[str, Any]
    demographic_patterns: Dict[str, Any]
    regional_preferences: List[str]
    growth_opportunities: List[str]
    market_penetration: float

@dataclass
class TrendPrediction:
    """趋势预测结果"""
    trend_name: str
    prediction_confidence: float
    time_horizon: str
    predicted_impact: Dict[str, Any]
    supporting_indicators: List[str]
    risk_factors: List[str]

@dataclass
class BusinessInsightsResult:
    """完整业务洞察结果"""
    market_insights: List[MarketInsight]
    competitive_analysis: List[CompetitiveAnalysis]
    regional_insights: List[RegionalInsight]
    trend_predictions: List[TrendPrediction]
    strategic_summary: Dict[str, Any]
    action_priorities: List[Dict[str, Any]]
    insights_metadata: Dict[str, Any]

class InsightsAgent:
    """洞察智能体"""
    
    def __init__(self, knowledge_manager: Optional[PersistentKnowledgeManager] = None):
        """
        初始化洞察智能体
        
        Args:
            knowledge_manager: 知识管理器实例
        """
        self.knowledge_manager = knowledge_manager or PersistentKnowledgeManager()
        
        # 加载业务知识
        self._load_business_knowledge()
        
        # 市场基准数据
        self.market_benchmarks = {
            "dairy_industry": {
                "nps_benchmark": 45,
                "growth_rate": 0.08,
                "market_share_leader": 0.25
            },
            "yili_historical": {
                "average_nps": 52,
                "premium_products_nps": 65,
                "regional_variations": {
                    "north": 55,
                    "south": 48,
                    "east": 60,
                    "west": 45
                }
            }
        }
        
        # 竞争对手信息
        self.competitors = {
            "蒙牛": {
                "market_position": "main_competitor",
                "known_strengths": ["品牌知名度", "渠道覆盖", "产品创新"],
                "known_weaknesses": ["价格竞争", "质量波动"]
            },
            "光明": {
                "market_position": "regional_strong",
                "known_strengths": ["区域优势", "传统工艺", "新鲜度"],
                "known_weaknesses": ["全国扩张", "品牌年轻化"]
            },
            "君乐宝": {
                "market_position": "fast_growing",
                "known_strengths": ["性价比", "增长速度", "创新力"],
                "known_weaknesses": ["品牌积淀", "高端市场"]
            }
        }
        
        logger.info("洞察智能体初始化完成")
    
    def _load_business_knowledge(self):
        """加载业务知识"""
        try:
            # 从知识管理器加载业务规则和产品信息
            self.business_context = self.knowledge_manager.get_business_context()
            self.product_catalog = self.knowledge_manager.get_product_catalog()
            
            # 设置默认值
            if not self.business_context:
                self.business_context = {
                    "company": "伊利集团",
                    "industry": "乳制品",
                    "market_position": "market_leader",
                    "key_products": ["安慕希", "金典", "舒化", "QQ星"]
                }
                
            if not self.product_catalog:
                self.product_catalog = {
                    "安慕希": {"category": "酸奶", "position": "premium", "target": "年轻消费者"},
                    "金典": {"category": "牛奶", "position": "premium", "target": "家庭消费"},
                    "舒化": {"category": "牛奶", "position": "functional", "target": "乳糖不耐人群"},
                    "QQ星": {"category": "儿童奶", "position": "specialty", "target": "儿童"}
                }
                
        except Exception as e:
            logger.warning(f"加载业务知识失败，使用默认配置: {e}")
            self.business_context = {}
            self.product_catalog = {}
    
    async def generate_business_insights(self, 
                                       nps_result: NPSCalculationResult,
                                       processed_nps_data: ProcessedNPSData,
                                       survey_data: ProcessedSurveyData,
                                       context: Optional[Dict[str, Any]] = None) -> BusinessInsightsResult:
        """
        生成综合业务洞察
        
        Args:
            nps_result: NPS计算结果
            processed_nps_data: 处理后的NPS数据
            survey_data: 调研数据
            context: 额外上下文信息
            
        Returns:
            BusinessInsightsResult: 完整业务洞察结果
        """
        logger.info("开始生成业务洞察")
        
        try:
            # 1. 市场洞察分析
            market_insights = await self._generate_market_insights(
                nps_result, processed_nps_data, survey_data, context
            )
            
            # 2. 竞品分析
            competitive_analysis = await self._analyze_competitive_position(
                nps_result, processed_nps_data, context
            )
            
            # 3. 区域洞察分析
            regional_insights = await self._analyze_regional_patterns(
                nps_result, survey_data, context
            )
            
            # 4. 趋势预测
            trend_predictions = await self._predict_market_trends(
                nps_result, processed_nps_data, context
            )
            
            # 5. 战略总结
            strategic_summary = await self._generate_strategic_summary(
                market_insights, competitive_analysis, regional_insights, trend_predictions
            )
            
            # 6. 行动优先级
            action_priorities = await self._prioritize_actions(
                market_insights, competitive_analysis, regional_insights, trend_predictions
            )
            
            # 构建最终结果
            result = BusinessInsightsResult(
                market_insights=market_insights,
                competitive_analysis=competitive_analysis,
                regional_insights=regional_insights,
                trend_predictions=trend_predictions,
                strategic_summary=strategic_summary,
                action_priorities=action_priorities,
                insights_metadata={
                    "generation_timestamp": datetime.now().isoformat(),
                    "agent_version": "insights_v2.0",
                    "analysis_scope": "comprehensive",
                    "data_sources": ["nps_survey", "business_knowledge", "market_benchmarks"],
                    "confidence_level": self._calculate_overall_confidence(nps_result, processed_nps_data)
                }
            )
            
            logger.info("业务洞察生成完成")
            return result
            
        except Exception as e:
            logger.error(f"业务洞察生成失败: {e}")
            raise
    
    async def _generate_market_insights(self, 
                                      nps_result: NPSCalculationResult,
                                      processed_nps_data: ProcessedNPSData,
                                      survey_data: ProcessedSurveyData,
                                      context: Optional[Dict[str, Any]]) -> List[MarketInsight]:
        """生成市场洞察"""
        
        insights = []
        nps_score = nps_result.overall_nps
        
        # 1. 市场定位洞察
        industry_benchmark = self.market_benchmarks["dairy_industry"]["nps_benchmark"]
        if nps_score > industry_benchmark + 15:
            insights.append(MarketInsight(
                insight_type="market_position",
                title="市场领先地位稳固",
                description=f"NPS得分{nps_score:.1f}显著高于行业平均{industry_benchmark}，显示强劲的市场竞争优势",
                confidence_level=0.9,
                impact_assessment="positive",
                supporting_data={
                    "nps_gap": nps_score - industry_benchmark,
                    "market_position": "leader",
                    "competitive_advantage": "significant"
                },
                recommendations=[
                    "利用领先优势扩大市场份额",
                    "投资品牌建设巩固优势地位",
                    "探索高端市场机会"
                ],
                priority="high"
            ))
        elif nps_score < industry_benchmark - 10:
            insights.append(MarketInsight(
                insight_type="market_position",
                title="市场地位需要提升",
                description=f"NPS得分{nps_score:.1f}低于行业平均{industry_benchmark}，存在竞争劣势",
                confidence_level=0.85,
                impact_assessment="negative",
                supporting_data={
                    "nps_gap": nps_score - industry_benchmark,
                    "market_position": "challenger",
                    "improvement_needed": True
                },
                recommendations=[
                    "深入分析竞争对手优势",
                    "制定差异化竞争策略",
                    "重点改善客户体验"
                ],
                priority="urgent"
            ))
        
        # 2. 客户价值洞察
        promoter_ratio = processed_nps_data.nps_distribution.promoter_percentage
        if promoter_ratio >= 60:
            insights.append(MarketInsight(
                insight_type="customer_value",
                title="高价值客户群体强大",
                description=f"推荐者比例达到{promoter_ratio:.1f}%，拥有强大的品牌传播力",
                confidence_level=0.88,
                impact_assessment="positive",
                supporting_data={
                    "promoter_ratio": promoter_ratio,
                    "brand_advocacy": "strong",
                    "word_of_mouth_potential": "high"
                },
                recommendations=[
                    "开发客户忠诚度计划",
                    "利用推荐者进行品牌传播",
                    "建立客户社区平台"
                ],
                priority="medium"
            ))
        
        # 3. 增长机会洞察
        passive_ratio = processed_nps_data.nps_distribution.passive_percentage
        if passive_ratio >= 30:
            conversion_potential = passive_ratio * 0.3  # 假设30%的转化率
            insights.append(MarketInsight(
                insight_type="growth_opportunity",
                title="中性客户转化机会巨大",
                description=f"中性客户占比{passive_ratio:.1f}%，转化潜力可提升NPS约{conversion_potential:.1f}分",
                confidence_level=0.75,
                impact_assessment="opportunity",
                supporting_data={
                    "passive_ratio": passive_ratio,
                    "conversion_potential": conversion_potential,
                    "growth_strategy": "customer_conversion"
                },
                recommendations=[
                    "设计个性化客户体验",
                    "提供额外价值服务",
                    "主动收集改进建议"
                ],
                priority="high"
            ))
        
        # 4. 产品生命周期洞察
        if context and "product_category" in context:
            category = context["product_category"]
            if category in self.product_catalog:
                product_info = self.product_catalog[category]
                if product_info.get("position") == "premium" and nps_score < 60:
                    insights.append(MarketInsight(
                        insight_type="product_lifecycle",
                        title="高端产品期望落差",
                        description="高端定位产品的NPS表现未达到预期，可能影响品牌溢价能力",
                        confidence_level=0.8,
                        impact_assessment="risk",
                        supporting_data={
                            "product_position": "premium",
                            "nps_expectation": 60,
                            "actual_nps": nps_score,
                            "expectation_gap": 60 - nps_score
                        },
                        recommendations=[
                            "重新审视产品价值主张",
                            "优化产品体验关键环节",
                            "加强高端品质传播"
                        ],
                        priority="medium"
                    ))
        
        return insights
    
    async def _analyze_competitive_position(self, 
                                          nps_result: NPSCalculationResult,
                                          processed_nps_data: ProcessedNPSData,
                                          context: Optional[Dict[str, Any]]) -> List[CompetitiveAnalysis]:
        """分析竞争地位"""
        
        competitive_analyses = []
        nps_score = nps_result.overall_nps
        
        for competitor, info in self.competitors.items():
            # 估算竞争对手NPS（基于市场地位）
            if info["market_position"] == "main_competitor":
                estimated_competitor_nps = self.market_benchmarks["dairy_industry"]["nps_benchmark"] + 5
            elif info["market_position"] == "regional_strong":
                estimated_competitor_nps = self.market_benchmarks["dairy_industry"]["nps_benchmark"]
            else:  # fast_growing
                estimated_competitor_nps = self.market_benchmarks["dairy_industry"]["nps_benchmark"] - 5
            
            # 竞争地位分析
            if nps_score > estimated_competitor_nps:
                position = "领先"
                threat_level = "low"
            elif nps_score > estimated_competitor_nps - 5:
                position = "竞争激烈"
                threat_level = "medium"
            else:
                position = "落后"
                threat_level = "high"
            
            # 识别优势差距
            strength_gaps = []
            opportunity_areas = []
            
            for strength in info["known_strengths"]:
                if strength not in ["品牌知名度", "市场领导力"]:  # 假设伊利在这些方面有优势
                    strength_gaps.append(f"在{strength}方面可能存在差距")
                    opportunity_areas.append(f"加强{strength}建设")
            
            # 威胁评估
            threat_assessment = {
                "overall_threat_level": threat_level,
                "nps_gap": nps_score - estimated_competitor_nps,
                "key_threats": info["known_strengths"][:2],
                "competitive_pressure": "high" if threat_level == "high" else "medium"
            }
            
            # 战略建议
            strategic_recommendations = []
            if position == "落后":
                strategic_recommendations.extend([
                    f"深入研究{competitor}的成功因素",
                    "制定追赶策略",
                    "寻找差异化竞争优势"
                ])
            elif position == "竞争激烈":
                strategic_recommendations.extend([
                    f"密切监控{competitor}的市场动向",
                    "保持创新领先",
                    "巩固现有优势"
                ])
            else:
                strategic_recommendations.extend([
                    f"防范{competitor}的追赶",
                    "扩大领先优势",
                    "进入新的竞争领域"
                ])
            
            competitive_analyses.append(CompetitiveAnalysis(
                competitor_name=competitor,
                competitive_position=position,
                strength_gaps=strength_gaps,
                opportunity_areas=opportunity_areas,
                threat_assessment=threat_assessment,
                strategic_recommendations=strategic_recommendations
            ))
        
        return competitive_analyses
    
    async def _analyze_regional_patterns(self, 
                                       nps_result: NPSCalculationResult,
                                       survey_data: ProcessedSurveyData,
                                       context: Optional[Dict[str, Any]]) -> List[RegionalInsight]:
        """分析区域模式"""
        
        regional_insights = []
        
        # 从调研数据中提取区域信息
        regional_data = defaultdict(list)
        
        for response in survey_data.response_data:
            # 假设区域信息在响应元数据中
            region = response.response_metadata.additional_data.get("region", "unknown")
            if region != "unknown":
                regional_data[region].append(response.nps_score.value)
        
        # 如果没有区域数据，使用默认区域分析
        if not regional_data and context and "estimated_regions" in context:
            regional_data = context["estimated_regions"]
        
        # 分析每个区域
        for region, nps_scores in regional_data.items():
            if not nps_scores:
                continue
                
            region_nps = sum(nps_scores) / len(nps_scores)
            national_nps = nps_result.overall_nps
            
            # 区域表现分析
            performance_vs_national = region_nps - national_nps
            if performance_vs_national > 5:
                performance_desc = "显著高于全国平均"
                opportunity_level = "expansion"
            elif performance_vs_national > 0:
                performance_desc = "略高于全国平均"
                opportunity_level = "optimization"
            elif performance_vs_national > -5:
                performance_desc = "接近全国平均"
                opportunity_level = "improvement"
            else:
                performance_desc = "显著低于全国平均"
                opportunity_level = "urgent_attention"
            
            # 获取历史基准（如果有）
            historical_benchmark = self.market_benchmarks["yili_historical"]["regional_variations"].get(region.lower(), national_nps)
            
            # 人口特征模式（模拟数据）
            demographic_patterns = {
                "age_preference": "根据区域特点推断的年龄偏好",
                "income_correlation": "收入水平与NPS的关联性",
                "urban_rural_split": "城乡分布特征"
            }
            
            # 区域偏好
            regional_preferences = [
                f"{region}地区客户偏好分析",
                "基于历史数据的偏好模式",
                "文化和消费习惯影响"
            ]
            
            # 增长机会
            growth_opportunities = []
            if opportunity_level == "expansion":
                growth_opportunities = [
                    "扩大市场投入",
                    "复制成功经验到其他区域",
                    "开发区域特色产品"
                ]
            elif opportunity_level == "urgent_attention":
                growth_opportunities = [
                    "深入调研区域问题",
                    "调整区域策略",
                    "加强本地化服务"
                ]
            
            # 市场渗透率（模拟计算）
            market_penetration = min(0.95, max(0.1, (region_nps + 50) / 100))
            
            regional_insights.append(RegionalInsight(
                region_name=region,
                nps_performance={
                    "region_nps": region_nps,
                    "vs_national": performance_vs_national,
                    "performance_desc": performance_desc,
                    "vs_historical": region_nps - historical_benchmark,
                    "sample_size": len(nps_scores)
                },
                demographic_patterns=demographic_patterns,
                regional_preferences=regional_preferences,
                growth_opportunities=growth_opportunities,
                market_penetration=market_penetration
            ))
        
        # 如果没有区域数据，创建全国性洞察
        if not regional_insights:
            regional_insights.append(RegionalInsight(
                region_name="全国",
                nps_performance={
                    "region_nps": nps_result.overall_nps,
                    "vs_national": 0,
                    "performance_desc": "全国整体表现",
                    "vs_historical": 0,
                    "sample_size": len(survey_data.response_data)
                },
                demographic_patterns={
                    "note": "需要收集更详细的区域和人口统计数据"
                },
                regional_preferences=[
                    "建议在未来调研中增加区域标识",
                    "收集人口统计学信息"
                ],
                growth_opportunities=[
                    "建立区域化数据收集机制",
                    "开展区域对比分析"
                ],
                market_penetration=0.5  # 默认值
            ))
        
        return regional_insights
    
    async def _predict_market_trends(self, 
                                   nps_result: NPSCalculationResult,
                                   processed_nps_data: ProcessedNPSData,
                                   context: Optional[Dict[str, Any]]) -> List[TrendPrediction]:
        """预测市场趋势"""
        
        predictions = []
        current_nps = nps_result.overall_nps
        
        # 1. NPS发展趋势预测
        if current_nps >= 60:
            trend_direction = "稳定增长"
            predicted_impact = {"nps_change": "+3到+7", "time_frame": "6-12个月"}
            risk_factors = ["市场饱和", "竞争加剧", "消费者期望提升"]
        elif current_nps >= 40:
            trend_direction = "温和改善"
            predicted_impact = {"nps_change": "+5到+10", "time_frame": "6-12个月"}
            risk_factors = ["改进措施效果", "市场环境变化", "执行力度"]
        else:
            trend_direction = "需要大幅改善"
            predicted_impact = {"nps_change": "+10到+20", "time_frame": "12-18个月"}
            risk_factors = ["改进执行难度", "客户信心恢复", "竞争对手动作"]
        
        predictions.append(TrendPrediction(
            trend_name="NPS表现趋势",
            prediction_confidence=0.7,
            time_horizon="6-18个月",
            predicted_impact=predicted_impact,
            supporting_indicators=[
                f"当前NPS基线: {current_nps:.1f}",
                f"行业平均增长趋势",
                f"客户群体分布特征"
            ],
            risk_factors=risk_factors
        ))
        
        # 2. 客户行为趋势预测
        passive_ratio = processed_nps_data.nps_distribution.passive_percentage
        if passive_ratio >= 40:
            predictions.append(TrendPrediction(
                trend_name="客户行为变化趋势",
                prediction_confidence=0.6,
                time_horizon="3-6个月",
                predicted_impact={
                    "customer_conversion": "中性客户转化机会增加",
                    "engagement_improvement": "客户参与度有望提升"
                },
                supporting_indicators=[
                    f"中性客户比例达到{passive_ratio:.1f}%",
                    "市场教育和沟通机会增加",
                    "产品改进空间明确"
                ],
                risk_factors=[
                    "竞争对手抢夺中性客户",
                    "客户期望快速上升",
                    "改进措施不够及时"
                ]
            ))
        
        # 3. 市场竞争趋势预测
        industry_growth = self.market_benchmarks["dairy_industry"]["growth_rate"]
        if current_nps > self.market_benchmarks["dairy_industry"]["nps_benchmark"]:
            competitive_outlook = "竞争优势将继续扩大"
            market_share_trend = "有望获得更大市场份额"
        else:
            competitive_outlook = "面临更激烈的竞争压力"
            market_share_trend = "需要努力保持市场地位"
        
        predictions.append(TrendPrediction(
            trend_name="市场竞争格局趋势",
            prediction_confidence=0.65,
            time_horizon="12个月",
            predicted_impact={
                "competitive_position": competitive_outlook,
                "market_share": market_share_trend,
                "industry_growth": f"行业预期增长{industry_growth*100:.1f}%"
            },
            supporting_indicators=[
                "当前市场地位分析",
                "竞争对手动态监测",
                "行业发展趋势"
            ],
            risk_factors=[
                "新进入者威胁",
                "技术创新颠覆",
                "消费趋势变化",
                "政策环境影响"
            ]
        ))
        
        return predictions
    
    async def _generate_strategic_summary(self, 
                                        market_insights: List[MarketInsight],
                                        competitive_analysis: List[CompetitiveAnalysis],
                                        regional_insights: List[RegionalInsight],
                                        trend_predictions: List[TrendPrediction]) -> Dict[str, Any]:
        """生成战略总结"""
        
        # 综合分析各个维度的洞察
        high_priority_insights = [insight for insight in market_insights if insight.priority == "high"]
        urgent_insights = [insight for insight in market_insights if insight.priority == "urgent"]
        
        # 竞争威胁评估
        high_threat_competitors = [
            analysis for analysis in competitive_analysis 
            if analysis.threat_assessment.get("overall_threat_level") == "high"
        ]
        
        # 区域机会评估
        growth_regions = [
            insight for insight in regional_insights 
            if insight.nps_performance.get("vs_national", 0) > 0
        ]
        
        # 趋势风险评估
        high_confidence_trends = [
            prediction for prediction in trend_predictions 
            if prediction.prediction_confidence >= 0.7
        ]
        
        strategic_summary = {
            "overall_assessment": {
                "market_position": "根据NPS分析的整体市场地位",
                "competitive_strength": "基于竞争分析的实力评估",
                "growth_potential": "增长潜力和机会评估"
            },
            "key_opportunities": [
                insight.title for insight in high_priority_insights
            ],
            "urgent_actions": [
                insight.title for insight in urgent_insights
            ],
            "competitive_priorities": [
                f"应对{analysis.competitor_name}的竞争威胁" 
                for analysis in high_threat_competitors
            ],
            "regional_focus": [
                f"{insight.region_name}：{insight.growth_opportunities[0] if insight.growth_opportunities else '待进一步分析'}"
                for insight in growth_regions[:3]
            ],
            "strategic_themes": [
                "客户体验提升",
                "品牌价值强化", 
                "竞争优势巩固",
                "市场份额扩大"
            ],
            "success_metrics": [
                "NPS得分提升",
                "推荐者比例增加",
                "市场份额增长",
                "客户满意度改善"
            ]
        }
        
        return strategic_summary
    
    async def _prioritize_actions(self, 
                                market_insights: List[MarketInsight],
                                competitive_analysis: List[CompetitiveAnalysis],
                                regional_insights: List[RegionalInsight],
                                trend_predictions: List[TrendPrediction]) -> List[Dict[str, Any]]:
        """优先级行动建议"""
        
        actions = []
        
        # 从市场洞察中提取紧急行动
        for insight in market_insights:
            if insight.priority == "urgent":
                actions.append({
                    "priority": "P0",
                    "category": "market_urgent",
                    "title": insight.title,
                    "description": insight.description,
                    "timeline": "立即执行",
                    "expected_impact": "高",
                    "resource_requirement": "中等",
                    "success_metrics": ["NPS改善", "客户满意度提升"]
                })
        
        # 高优先级市场机会
        for insight in market_insights:
            if insight.priority == "high" and insight.impact_assessment == "opportunity":
                actions.append({
                    "priority": "P1",
                    "category": "market_opportunity",
                    "title": insight.title,
                    "description": insight.description,
                    "timeline": "1-3个月",
                    "expected_impact": "中高",
                    "resource_requirement": "中等",
                    "success_metrics": ["转化率提升", "客户增长"]
                })
        
        # 竞争防御行动
        high_threat_competitors = [
            analysis for analysis in competitive_analysis 
            if analysis.threat_assessment.get("overall_threat_level") == "high"
        ]
        
        for analysis in high_threat_competitors[:2]:  # 最多2个最高威胁
            actions.append({
                "priority": "P1",
                "category": "competitive_defense",
                "title": f"应对{analysis.competitor_name}竞争威胁",
                "description": f"针对{analysis.competitor_name}的竞争优势制定防御策略",
                "timeline": "2-4个月",
                "expected_impact": "中高",
                "resource_requirement": "高",
                "success_metrics": ["市场份额保持", "竞争优势巩固"]
            })
        
        # 区域增长行动
        for insight in regional_insights:
            if insight.nps_performance.get("vs_national", 0) < -10:  # 表现差的区域
                actions.append({
                    "priority": "P2",
                    "category": "regional_improvement",
                    "title": f"提升{insight.region_name}区域表现",
                    "description": f"{insight.region_name}区域NPS表现需要改善",
                    "timeline": "3-6个月",
                    "expected_impact": "中等",
                    "resource_requirement": "中等",
                    "success_metrics": ["区域NPS提升", "市场渗透率增加"]
                })
        
        # 趋势应对行动
        for prediction in trend_predictions:
            if prediction.prediction_confidence >= 0.7 and prediction.risk_factors:
                actions.append({
                    "priority": "P2",
                    "category": "trend_preparation",
                    "title": f"应对{prediction.trend_name}",
                    "description": f"为{prediction.trend_name}做好准备",
                    "timeline": prediction.time_horizon,
                    "expected_impact": "中等",
                    "resource_requirement": "中等",
                    "success_metrics": ["趋势适应性", "前瞻性优势"]
                })
        
        # 按优先级排序
        priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
        actions.sort(key=lambda x: priority_order.get(x["priority"], 99))
        
        return actions[:10]  # 返回前10个最重要的行动
    
    def _calculate_overall_confidence(self, 
                                    nps_result: NPSCalculationResult,
                                    processed_nps_data: ProcessedNPSData) -> float:
        """计算整体洞察置信度"""
        
        # 基于数据质量和样本量的置信度
        data_quality = processed_nps_data.data_quality.overall_score
        sample_size = processed_nps_data.nps_distribution.total_responses
        
        # 样本量置信度
        if sample_size >= 200:
            sample_confidence = 1.0
        elif sample_size >= 100:
            sample_confidence = 0.8
        elif sample_size >= 50:
            sample_confidence = 0.6
        else:
            sample_confidence = 0.4
        
        # NPS计算置信度
        nps_confidence = nps_result.confidence_level
        
        # 业务知识完整度
        knowledge_completeness = 0.8 if self.business_context and self.product_catalog else 0.6
        
        # 加权平均
        overall_confidence = (
            data_quality * 0.4 + 
            sample_confidence * 0.3 + 
            nps_confidence * 0.2 + 
            knowledge_completeness * 0.1
        )
        
        return round(overall_confidence, 3)

# 使用示例
async def main():
    """主函数示例"""
    agent = InsightsAgent()
    print("洞察智能体初始化完成")

if __name__ == "__main__":
    asyncio.run(main())