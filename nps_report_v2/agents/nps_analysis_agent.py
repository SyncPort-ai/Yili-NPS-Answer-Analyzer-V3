"""
NPS分析智能体
负责NPS净值解读、分布分析、趋势洞察和业务建议
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import asyncio

# 导入相关数据结构
from ..nps_calculator import NPSCalculationResult, NPSSegmentAnalysis, QuestionGroupClassification
from ..nps_data_processor import ProcessedNPSData, NPSDistribution
from ..persistent_knowledge_manager import PersistentKnowledgeManager

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class NPSInsightResult:
    """NPS洞察分析结果"""
    nps_score_analysis: Dict[str, Any]
    distribution_analysis: Dict[str, Any] 
    benchmark_comparison: Dict[str, Any]
    trend_analysis: Dict[str, Any]
    segment_insights: Dict[str, List[Dict[str, Any]]]
    business_recommendations: List[Dict[str, Any]]
    risk_alerts: List[Dict[str, Any]]
    confidence_score: float
    analysis_metadata: Dict[str, Any]

class NPSAnalysisAgent:
    """NPS分析智能体"""
    
    def __init__(self, knowledge_manager: Optional[PersistentKnowledgeManager] = None):
        """
        初始化NPS分析智能体
        
        Args:
            knowledge_manager: 知识管理器实例（可选）
        """
        self.knowledge_manager = knowledge_manager or PersistentKnowledgeManager()
        
        # 行业基准数据
        self.industry_benchmarks = {
            "dairy_industry": {
                "excellent": 70,
                "good": 50,
                "average": 30,
                "poor": 10,
                "critical": -10
            },
            "yili_historical": {
                "premium_products": 65,
                "standard_products": 45,
                "seasonal_products": 35
            }
        }
        
        # NPS解读模板
        self.nps_interpretation_templates = {
            "excellent": "卓越表现",
            "good": "良好表现", 
            "average": "平均水平",
            "poor": "亟需改进",
            "critical": "严重风险"
        }
        
        logger.info("NPS分析智能体初始化完成")
    
    async def analyze_nps_comprehensive(self, 
                                      nps_calculation_result: NPSCalculationResult,
                                      processed_nps_data: ProcessedNPSData,
                                      context: Optional[Dict[str, Any]] = None) -> NPSInsightResult:
        """
        综合NPS分析主入口
        
        Args:
            nps_calculation_result: NPS计算结果
            processed_nps_data: 处理后的NPS数据
            context: 额外的上下文信息
            
        Returns:
            NPSInsightResult: 综合分析结果
        """
        logger.info("开始综合NPS分析")
        
        try:
            # 1. NPS得分深度分析
            nps_score_analysis = await self._analyze_nps_score(
                nps_calculation_result.overall_nps,
                nps_calculation_result.confidence_level
            )
            
            # 2. 分布分析
            distribution_analysis = await self._analyze_distribution(
                processed_nps_data.nps_distribution
            )
            
            # 3. 基准对比
            benchmark_comparison = await self._compare_with_benchmarks(
                nps_calculation_result.overall_nps,
                context
            )
            
            # 4. 趋势分析（如果有历史数据）
            trend_analysis = await self._analyze_trends(
                nps_calculation_result,
                context
            )
            
            # 5. 细分洞察
            segment_insights = await self._analyze_segments(
                nps_calculation_result.segment_analysis
            )
            
            # 6. 业务建议
            business_recommendations = await self._generate_business_recommendations(
                nps_calculation_result,
                processed_nps_data
            )
            
            # 7. 风险预警
            risk_alerts = await self._identify_risk_alerts(
                nps_calculation_result,
                processed_nps_data
            )
            
            # 8. 计算置信度
            confidence_score = await self._calculate_analysis_confidence(
                nps_calculation_result,
                processed_nps_data
            )
            
            # 构建最终结果
            result = NPSInsightResult(
                nps_score_analysis=nps_score_analysis,
                distribution_analysis=distribution_analysis,
                benchmark_comparison=benchmark_comparison,
                trend_analysis=trend_analysis,
                segment_insights=segment_insights,
                business_recommendations=business_recommendations,
                risk_alerts=risk_alerts,
                confidence_score=confidence_score,
                analysis_metadata={
                    "analysis_timestamp": datetime.now().isoformat(),
                    "agent_version": "nps_analysis_v2.0",
                    "data_quality_score": processed_nps_data.data_quality.overall_score,
                    "sample_size": processed_nps_data.nps_distribution.total_responses
                }
            )
            
            logger.info("综合NPS分析完成")
            return result
            
        except Exception as e:
            logger.error(f"综合NPS分析失败: {e}")
            raise
    
    async def _analyze_nps_score(self, nps_score: float, confidence_level: float) -> Dict[str, Any]:
        """分析NPS得分"""
        
        # 确定得分等级
        if nps_score >= 70:
            grade = "excellent"
            grade_desc = "卓越"
        elif nps_score >= 50:
            grade = "good"
            grade_desc = "良好"
        elif nps_score >= 30:
            grade = "average"
            grade_desc = "平均"
        elif nps_score >= 10:
            grade = "poor"
            grade_desc = "较差"
        else:
            grade = "critical"
            grade_desc = "严重"
            
        # 生成详细解读
        interpretation = f"NPS得分为{nps_score:.1f}，属于{grade_desc}水平。"
        
        if grade == "excellent":
            interpretation += "客户忠诚度极高，品牌传播力强，市场竞争优势明显。"
        elif grade == "good":
            interpretation += "客户满意度较高，有良好的口碑传播基础，需保持并提升。"
        elif grade == "average":
            interpretation += "客户态度中性，存在改进空间，需重点关注客户体验提升。"
        elif grade == "poor":
            interpretation += "客户满意度偏低，存在较多不满情绪，需立即采取改进措施。"
        else:
            interpretation += "客户严重不满，品牌声誉面临风险，需要紧急干预和全面改进。"
        
        return {
            "nps_score": nps_score,
            "grade": grade,
            "grade_description": grade_desc,
            "interpretation": interpretation,
            "confidence_level": confidence_level,
            "improvement_potential": max(0, 70 - nps_score),  # 相对于卓越水平的提升空间
            "performance_indicators": {
                "customer_loyalty": "high" if nps_score >= 50 else "medium" if nps_score >= 30 else "low",
                "word_of_mouth": "positive" if nps_score >= 30 else "neutral" if nps_score >= 0 else "negative",
                "competitive_position": "strong" if nps_score >= 50 else "average" if nps_score >= 30 else "weak"
            }
        }
    
    async def _analyze_distribution(self, nps_distribution: NPSDistribution) -> Dict[str, Any]:
        """分析NPS分布"""
        
        total = nps_distribution.total_responses
        promoters = nps_distribution.promoters
        passives = nps_distribution.passives
        detractors = nps_distribution.detractors
        
        # 计算分布特征
        promoter_ratio = promoters / total if total > 0 else 0
        passive_ratio = passives / total if total > 0 else 0
        detractor_ratio = detractors / total if total > 0 else 0
        
        # 分布健康度分析
        if promoter_ratio >= 0.6:
            health_status = "健康"
            health_desc = "推荐者占比很高，客户群体非常积极"
        elif promoter_ratio >= 0.4:
            health_status = "良好"
            health_desc = "推荐者占比较高，客户态度积极"
        elif detractor_ratio <= 0.2:
            health_status = "稳定"
            health_desc = "批评者比例较低，客户态度总体稳定"
        elif detractor_ratio >= 0.4:
            health_status = "风险"
            health_desc = "批评者比例较高，存在口碑风险"
        else:
            health_status = "一般"
            health_desc = "客户态度分化明显，需要关注提升"
        
        return {
            "distribution_summary": {
                "promoters": {"count": promoters, "percentage": promoter_ratio * 100},
                "passives": {"count": passives, "percentage": passive_ratio * 100},
                "detractors": {"count": detractors, "percentage": detractor_ratio * 100}
            },
            "health_status": health_status,
            "health_description": health_desc,
            "key_insights": [
                f"推荐者比例{promoter_ratio:.1%}，{'超出' if promoter_ratio >= 0.5 else '低于'}期望水平",
                f"中性客户比例{passive_ratio:.1%}，{'转化潜力较大' if passive_ratio >= 0.3 else '转化空间有限'}",
                f"批评者比例{detractor_ratio:.1%}，{'需要重点关注' if detractor_ratio >= 0.2 else '控制良好'}"
            ],
            "conversion_opportunities": {
                "passive_to_promoter": passives,
                "detractor_to_passive": detractors,
                "estimated_nps_gain": (passives * 0.3 + detractors * 0.1) * 100 / total if total > 0 else 0
            }
        }
    
    async def _compare_with_benchmarks(self, nps_score: float, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """与基准进行对比"""
        
        comparisons = {}
        
        # 行业基准对比
        industry_bench = self.industry_benchmarks["dairy_industry"]
        if nps_score >= industry_bench["excellent"]:
            industry_position = "行业领先"
        elif nps_score >= industry_bench["good"]:
            industry_position = "高于行业平均"
        elif nps_score >= industry_bench["average"]:
            industry_position = "行业平均水平"
        elif nps_score >= industry_bench["poor"]:
            industry_position = "低于行业平均"
        else:
            industry_position = "显著低于行业水平"
            
        comparisons["industry"] = {
            "position": industry_position,
            "benchmarks": industry_bench,
            "gap_to_excellent": max(0, industry_bench["excellent"] - nps_score)
        }
        
        # 伊利历史基准对比（如果有上下文信息）
        if context and "product_category" in context:
            category = context["product_category"]
            yili_bench = self.industry_benchmarks["yili_historical"]
            
            if category in ["premium", "high_end"]:
                target_benchmark = yili_bench["premium_products"]
            elif category in ["seasonal", "limited"]:
                target_benchmark = yili_bench["seasonal_products"]
            else:
                target_benchmark = yili_bench["standard_products"]
                
            comparisons["yili_internal"] = {
                "target_benchmark": target_benchmark,
                "performance": "超出预期" if nps_score >= target_benchmark else "低于预期",
                "gap": nps_score - target_benchmark
            }
        
        return comparisons
    
    async def _analyze_trends(self, nps_result: NPSCalculationResult, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """分析趋势（如果有历史数据）"""
        
        # 当前实现为静态分析，未来可以集成时间序列数据
        trend_analysis = {
            "trend_available": False,
            "current_snapshot": {
                "nps_score": nps_result.overall_nps,
                "confidence": nps_result.confidence_level,
                "timestamp": datetime.now().isoformat()
            },
            "recommendations": [
                "建议建立NPS定期监测机制",
                "记录各时间点的NPS表现以建立趋势分析",
                "关注季节性波动和产品生命周期影响"
            ]
        }
        
        # 如果有历史数据的话（通过context提供）
        if context and "historical_nps" in context:
            historical_data = context["historical_nps"]
            current_nps = nps_result.overall_nps
            
            if len(historical_data) > 0:
                latest_historical = historical_data[-1]["nps"]
                trend_direction = "上升" if current_nps > latest_historical else "下降" if current_nps < latest_historical else "稳定"
                trend_magnitude = abs(current_nps - latest_historical)
                
                trend_analysis.update({
                    "trend_available": True,
                    "trend_direction": trend_direction,
                    "trend_magnitude": trend_magnitude,
                    "change_significance": "显著" if trend_magnitude >= 10 else "轻微" if trend_magnitude >= 5 else "微小",
                    "historical_comparison": {
                        "previous_nps": latest_historical,
                        "current_nps": current_nps,
                        "change": current_nps - latest_historical
                    }
                })
        
        return trend_analysis
    
    async def _analyze_segments(self, segment_analysis: Dict[str, NPSSegmentAnalysis]) -> Dict[str, List[Dict[str, Any]]]:
        """分析细分客户群体"""
        
        segment_insights = {}
        
        for segment_name, segment_data in segment_analysis.items():
            insights = []
            
            # 基本统计洞察
            insights.append({
                "type": "size_analysis",
                "insight": f"{segment_name}群体共{segment_data.count}人，占比{segment_data.percentage:.1f}%",
                "significance": "high" if segment_data.percentage >= 30 else "medium" if segment_data.percentage >= 15 else "low"
            })
            
            # 行为特征洞察
            if segment_name == "promoter":
                insights.append({
                    "type": "behavior_pattern",
                    "insight": "推荐者群体是品牌最强有力的支持者，具有高忠诚度和传播价值",
                    "action_items": ["深化关系维护", "发展品牌大使项目", "收集成功案例"]
                })
            elif segment_name == "passive":
                insights.append({
                    "type": "conversion_opportunity", 
                    "insight": "中性客户群体转化潜力大，是NPS提升的关键目标",
                    "action_items": ["了解满意度障碍", "提供个性化体验", "主动收集反馈"]
                })
            elif segment_name == "detractor":
                insights.append({
                    "type": "risk_management",
                    "insight": "批评者群体需要重点关注，防止负面口碑扩散",
                    "action_items": ["主动服务恢复", "深度问题调研", "建立预警机制"]
                })
            
            segment_insights[segment_name] = insights
        
        return segment_insights
    
    async def _generate_business_recommendations(self, 
                                               nps_result: NPSCalculationResult,
                                               processed_data: ProcessedNPSData) -> List[Dict[str, Any]]:
        """生成业务建议"""
        
        recommendations = []
        nps_score = nps_result.overall_nps
        distribution = processed_data.nps_distribution
        
        # 基于NPS得分等级的建议
        if nps_score >= 70:
            recommendations.append({
                "priority": "high",
                "category": "maintain_excellence",
                "title": "保持卓越表现",
                "description": "NPS表现卓越，应继续保持现有优势并探索进一步提升空间",
                "actions": [
                    "分析推荐者反馈中的成功因素",
                    "将成功经验复制到其他产品线",
                    "建立客户忠诚度奖励机制"
                ]
            })
        elif nps_score < 30:
            recommendations.append({
                "priority": "urgent",
                "category": "immediate_improvement",
                "title": "紧急改进措施",
                "description": "NPS得分偏低，需要立即采取改进行动",
                "actions": [
                    "深入分析批评者反馈找到核心问题",
                    "制定专项改进计划",
                    "加强客户服务和产品质量管控"
                ]
            })
        
        # 基于分布特征的建议
        passive_ratio = distribution.passives / distribution.total_responses
        if passive_ratio >= 0.4:
            recommendations.append({
                "priority": "medium",
                "category": "conversion_strategy",
                "title": "中性客户转化策略",
                "description": f"中性客户比例较高({passive_ratio:.1%})，具有很大转化潜力",
                "actions": [
                    "开展中性客户深度访谈",
                    "优化产品体验关键触点",
                    "设计个性化的客户关怀方案"
                ]
            })
        
        # 基于数据质量的建议
        if processed_data.data_quality.overall_score < 0.8:
            recommendations.append({
                "priority": "medium",
                "category": "data_quality",
                "title": "提升数据质量",
                "description": "当前数据质量有提升空间，影响分析准确性",
                "actions": [
                    "优化问卷设计和调研流程",
                    "增加样本量确保代表性",
                    "建立数据质量监控机制"
                ]
            })
        
        return recommendations
    
    async def _identify_risk_alerts(self, 
                                  nps_result: NPSCalculationResult,
                                  processed_data: ProcessedNPSData) -> List[Dict[str, Any]]:
        """识别风险预警"""
        
        alerts = []
        nps_score = nps_result.overall_nps
        distribution = processed_data.nps_distribution
        
        # NPS得分风险
        if nps_score < 0:
            alerts.append({
                "level": "critical",
                "type": "negative_nps",
                "message": "NPS得分为负值，品牌声誉面临严重风险",
                "impact": "可能导致客户流失加速和负面口碑传播",
                "action_required": "立即启动危机管理预案"
            })
        elif nps_score < 20:
            alerts.append({
                "level": "high",
                "type": "low_nps",
                "message": "NPS得分较低，存在客户满意度问题",
                "impact": "可能影响客户保留和品牌竞争力",
                "action_required": "制定系统性改进计划"
            })
        
        # 批评者比例风险
        detractor_ratio = distribution.detractors / distribution.total_responses
        if detractor_ratio >= 0.3:
            alerts.append({
                "level": "medium",
                "type": "high_detractor_ratio",
                "message": f"批评者比例过高({detractor_ratio:.1%})",
                "impact": "负面口碑传播风险增加",
                "action_required": "重点关注批评者反馈并采取针对性措施"
            })
        
        # 数据质量风险
        if processed_data.data_quality.overall_score < 0.7:
            alerts.append({
                "level": "medium", 
                "type": "data_quality",
                "message": "数据质量偏低，可能影响分析可靠性",
                "impact": "决策基础不够稳固",
                "action_required": "改进数据收集和处理流程"
            })
        
        # 样本量风险
        if distribution.total_responses < 100:
            alerts.append({
                "level": "low",
                "type": "small_sample",
                "message": "样本量较小，统计显著性有限",
                "impact": "分析结果的代表性和准确性可能受限",
                "action_required": "考虑扩大样本量以提高分析可靠性"
            })
        
        return alerts
    
    async def _calculate_analysis_confidence(self, 
                                           nps_result: NPSCalculationResult,
                                           processed_data: ProcessedNPSData) -> float:
        """计算分析置信度"""
        
        confidence_factors = []
        
        # 样本量置信度
        sample_size = processed_data.nps_distribution.total_responses
        if sample_size >= 500:
            sample_confidence = 1.0
        elif sample_size >= 200:
            sample_confidence = 0.9
        elif sample_size >= 100:
            sample_confidence = 0.8
        elif sample_size >= 50:
            sample_confidence = 0.7
        else:
            sample_confidence = 0.6
        confidence_factors.append(sample_confidence)
        
        # 数据质量置信度
        data_quality_confidence = processed_data.data_quality.overall_score
        confidence_factors.append(data_quality_confidence)
        
        # NPS计算置信度
        nps_confidence = nps_result.confidence_level
        confidence_factors.append(nps_confidence)
        
        # 分布平衡度置信度（避免极端分布）
        total = processed_data.nps_distribution.total_responses
        promoters = processed_data.nps_distribution.promoters
        detractors = processed_data.nps_distribution.detractors
        
        if total > 0:
            balance_score = 1.0 - abs((promoters - detractors) / total)
            balance_confidence = max(0.6, balance_score)
        else:
            balance_confidence = 0.5
        confidence_factors.append(balance_confidence)
        
        # 加权平均计算总置信度
        weights = [0.3, 0.3, 0.25, 0.15]  # 样本量、数据质量、NPS计算、分布平衡
        overall_confidence = sum(factor * weight for factor, weight in zip(confidence_factors, weights))
        
        return round(overall_confidence, 3)

# 使用示例
async def main():
    """主函数示例"""
    agent = NPSAnalysisAgent()
    print("NPS分析智能体初始化完成")

if __name__ == "__main__":
    asyncio.run(main())