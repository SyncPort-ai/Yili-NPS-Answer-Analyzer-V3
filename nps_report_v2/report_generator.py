"""
综合报告生成器
整合所有Agent分析结果，生成结构化的HTML报告和JSON数据
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import json
import os
import asyncio
from jinja2 import Template, Environment, FileSystemLoader

# 导入相关数据结构
from .nps_calculator import NPSCalculationResult
from .nps_data_processor import ProcessedNPSData
from .input_data_processor import ProcessedSurveyData
from .agents.nps_analysis_agent import NPSInsightResult
from .agents.question_group_agent import QuestionGroupAnalysisResult
from .agents.insights_agent import BusinessInsightsResult

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class ReportSection:
    """报告章节"""
    section_id: str
    title: str
    content: Dict[str, Any]
    priority: str
    visualization_data: Optional[Dict[str, Any]] = None

@dataclass
class ComprehensiveReport:
    """综合报告结构"""
    report_id: str
    generation_timestamp: str
    executive_summary: Dict[str, Any]
    nps_overview: ReportSection
    detailed_analysis: ReportSection
    question_group_insights: ReportSection
    business_intelligence: ReportSection
    recommendations: ReportSection
    appendix: ReportSection
    metadata: Dict[str, Any]

class ReportGenerator:
    """综合报告生成器"""
    
    def __init__(self, output_dir: str = "outputs"):
        """
        初始化报告生成器
        
        Args:
            output_dir: 输出目录
        """
        self.output_dir = output_dir
        self.reports_dir = os.path.join(output_dir, "reports")
        self.results_dir = os.path.join(output_dir, "results")
        
        # 确保输出目录存在
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 初始化模板引擎
        self._setup_template_engine()
        
        logger.info(f"报告生成器初始化完成，输出目录: {output_dir}")
    
    def _setup_template_engine(self):
        """设置模板引擎"""
        # 模板目录路径
        template_dir = os.path.join(os.path.dirname(__file__), "..", "templates")
        
        if os.path.exists(template_dir):
            self.jinja_env = Environment(loader=FileSystemLoader(template_dir))
        else:
            # 如果模板目录不存在，使用内置模板
            self.jinja_env = Environment(loader=FileSystemLoader("."))
            logger.warning(f"模板目录不存在: {template_dir}，将使用内置模板")
        
        # 添加自定义过滤器
        self.jinja_env.filters['tojson'] = json.dumps
        self.jinja_env.filters['round'] = round
    
    async def generate_comprehensive_report(self,
                                          nps_calculation: NPSCalculationResult,
                                          processed_nps_data: ProcessedNPSData,
                                          survey_data: ProcessedSurveyData,
                                          nps_insights: NPSInsightResult,
                                          question_group_analysis: QuestionGroupAnalysisResult,
                                          business_insights: BusinessInsightsResult,
                                          v1_comparison_data: Optional[Dict[str, Any]] = None,
                                          context: Optional[Dict[str, Any]] = None) -> Tuple[str, str]:
        """
        生成综合报告
        
        Args:
            nps_calculation: NPS计算结果
            processed_nps_data: 处理后的NPS数据
            survey_data: 调研数据
            nps_insights: NPS洞察结果
            question_group_analysis: 题组分析结果
            business_insights: 业务洞察结果
            v1_comparison_data: V1对比数据（可选）
            context: 额外上下文信息
            
        Returns:
            Tuple[str, str]: (HTML报告路径, JSON结果路径)
        """
        logger.info("开始生成综合报告")
        
        try:
            # 生成报告ID
            report_id = f"v2_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # 1. 生成执行摘要
            executive_summary = await self._generate_executive_summary(
                nps_calculation, nps_insights, business_insights
            )
            
            # 2. 生成各个报告章节
            nps_overview = await self._generate_nps_overview_section(
                nps_calculation, processed_nps_data, nps_insights
            )
            
            detailed_analysis = await self._generate_detailed_analysis_section(
                nps_calculation, processed_nps_data, nps_insights
            )
            
            question_group_insights = await self._generate_question_group_section(
                question_group_analysis
            )
            
            business_intelligence = await self._generate_business_intelligence_section(
                business_insights
            )
            
            recommendations = await self._generate_recommendations_section(
                nps_insights, question_group_analysis, business_insights
            )
            
            appendix = await self._generate_appendix_section(
                survey_data, v1_comparison_data, context
            )
            
            # 3. 构建完整报告
            comprehensive_report = ComprehensiveReport(
                report_id=report_id,
                generation_timestamp=datetime.now().isoformat(),
                executive_summary=executive_summary,
                nps_overview=nps_overview,
                detailed_analysis=detailed_analysis,
                question_group_insights=question_group_insights,
                business_intelligence=business_intelligence,
                recommendations=recommendations,
                appendix=appendix,
                metadata={
                    "generator_version": "v2.0",
                    "total_responses": len(survey_data.response_data),
                    "analysis_depth": "comprehensive",
                    "agent_components": ["nps_analysis", "question_group", "business_insights"],
                    "v1_comparison_included": v1_comparison_data is not None
                }
            )
            
            # 4. 生成HTML报告
            html_path = await self._generate_html_report(comprehensive_report)
            
            # 5. 保存JSON结果
            json_path = await self._save_json_results(comprehensive_report)
            
            logger.info(f"综合报告生成完成 - HTML: {html_path}, JSON: {json_path}")
            return html_path, json_path
            
        except Exception as e:
            logger.error(f"综合报告生成失败: {e}")
            raise
    
    async def _generate_executive_summary(self,
                                        nps_calculation: NPSCalculationResult,
                                        nps_insights: NPSInsightResult,
                                        business_insights: BusinessInsightsResult) -> Dict[str, Any]:
        """生成执行摘要"""
        
        # 关键指标
        key_metrics = {
            "overall_nps": nps_calculation.overall_nps,
            "confidence_level": nps_calculation.confidence_level,
            "sample_size": nps_calculation.calculation_metadata.get("total_responses", 0),
            "analysis_confidence": nps_insights.confidence_score
        }
        
        # 主要发现
        key_findings = []
        
        # 从NPS洞察中提取关键发现
        nps_grade = nps_insights.nps_score_analysis.get("grade", "unknown")
        nps_interpretation = nps_insights.nps_score_analysis.get("interpretation", "")
        key_findings.append(f"NPS表现: {nps_interpretation}")
        
        # 从业务洞察中提取关键发现
        urgent_market_insights = [
            insight for insight in business_insights.market_insights 
            if insight.priority == "urgent"
        ]
        if urgent_market_insights:
            key_findings.append(f"紧急关注: {urgent_market_insights[0].title}")
        
        high_priority_insights = [
            insight for insight in business_insights.market_insights 
            if insight.priority == "high"
        ]
        if high_priority_insights:
            key_findings.append(f"重要机会: {high_priority_insights[0].title}")
        
        # 核心建议
        core_recommendations = []
        
        # 从NPS建议中提取
        if nps_insights.business_recommendations:
            core_recommendations.append(nps_insights.business_recommendations[0]["title"])
        
        # 从业务洞察中提取
        if business_insights.action_priorities:
            priority_actions = [action for action in business_insights.action_priorities if action["priority"] in ["P0", "P1"]]
            if priority_actions:
                core_recommendations.extend([action["title"] for action in priority_actions[:2]])
        
        # 风险警示
        risk_alerts = []
        if nps_insights.risk_alerts:
            high_risk_alerts = [alert for alert in nps_insights.risk_alerts if alert["level"] in ["critical", "high"]]
            risk_alerts.extend([alert["message"] for alert in high_risk_alerts[:2]])
        
        return {
            "key_metrics": key_metrics,
            "key_findings": key_findings[:4],  # 最多4个关键发现
            "core_recommendations": core_recommendations[:3],  # 最多3个核心建议
            "risk_alerts": risk_alerts[:2],  # 最多2个风险警示
            "overall_assessment": {
                "performance_level": nps_grade,
                "market_position": business_insights.strategic_summary.get("overall_assessment", {}).get("market_position", "待评估"),
                "improvement_priority": "high" if nps_calculation.overall_nps < 40 else "medium" if nps_calculation.overall_nps < 60 else "low"
            }
        }
    
    async def _generate_nps_overview_section(self,
                                           nps_calculation: NPSCalculationResult,
                                           processed_nps_data: ProcessedNPSData,
                                           nps_insights: NPSInsightResult) -> ReportSection:
        """生成NPS概览章节"""
        
        content = {
            "nps_score": {
                "value": nps_calculation.overall_nps,
                "grade": nps_insights.nps_score_analysis.get("grade", "unknown"),
                "interpretation": nps_insights.nps_score_analysis.get("interpretation", ""),
                "confidence": nps_calculation.confidence_level
            },
            "distribution": {
                "promoters": {
                    "count": processed_nps_data.nps_distribution.promoters,
                    "percentage": processed_nps_data.nps_distribution.promoter_percentage
                },
                "passives": {
                    "count": processed_nps_data.nps_distribution.passives,
                    "percentage": processed_nps_data.nps_distribution.passive_percentage
                },
                "detractors": {
                    "count": processed_nps_data.nps_distribution.detractors,
                    "percentage": processed_nps_data.nps_distribution.detractor_percentage
                }
            },
            "benchmark_comparison": nps_insights.benchmark_comparison,
            "key_insights": nps_insights.nps_score_analysis
        }
        
        # 可视化数据
        visualization_data = {
            "nps_gauge": {
                "value": nps_calculation.overall_nps,
                "min": -100,
                "max": 100,
                "ranges": [
                    {"from": -100, "to": 0, "color": "#ff4444", "label": "需要改进"},
                    {"from": 0, "to": 50, "color": "#ffaa00", "label": "一般"},
                    {"from": 50, "to": 100, "color": "#44ff44", "label": "优秀"}
                ]
            },
            "distribution_pie": {
                "data": [
                    {"label": "推荐者", "value": processed_nps_data.nps_distribution.promoters, "color": "#44ff44"},
                    {"label": "中性者", "value": processed_nps_data.nps_distribution.passives, "color": "#ffaa00"},
                    {"label": "批评者", "value": processed_nps_data.nps_distribution.detractors, "color": "#ff4444"}
                ]
            }
        }
        
        return ReportSection(
            section_id="nps_overview",
            title="NPS总览",
            content=content,
            priority="high",
            visualization_data=visualization_data
        )
    
    async def _generate_detailed_analysis_section(self,
                                                nps_calculation: NPSCalculationResult,
                                                processed_nps_data: ProcessedNPSData,
                                                nps_insights: NPSInsightResult) -> ReportSection:
        """生成详细分析章节"""
        
        content = {
            "score_analysis": nps_insights.nps_score_analysis,
            "distribution_analysis": nps_insights.distribution_analysis,
            "segment_insights": nps_insights.segment_insights,
            "trend_analysis": nps_insights.trend_analysis,
            "improvement_opportunities": {
                "conversion_potential": nps_insights.distribution_analysis.get("conversion_opportunities", {}),
                "improvement_suggestions": nps_calculation.improvement_suggestions
            },
            "confidence_assessment": {
                "analysis_confidence": nps_insights.confidence_score,
                "data_quality": processed_nps_data.data_quality.overall_score,
                "sample_adequacy": "充足" if processed_nps_data.nps_distribution.total_responses >= 100 else "有限"
            }
        }
        
        # 可视化数据 - NPS分布直方图
        visualization_data = {
            "score_distribution": {
                "data": [
                    {"score": i, "count": 0} for i in range(0, 11)
                ]
                # 注意：这里需要实际的分数分布数据，目前使用占位符
            },
            "segment_comparison": {
                "segments": [
                    {
                        "name": "推荐者",
                        "size": processed_nps_data.nps_distribution.promoters,
                        "characteristics": ["高忠诚度", "口碑传播", "重复购买"]
                    },
                    {
                        "name": "中性者", 
                        "size": processed_nps_data.nps_distribution.passives,
                        "characteristics": ["转化潜力", "观望态度", "价格敏感"]
                    },
                    {
                        "name": "批评者",
                        "size": processed_nps_data.nps_distribution.detractors,
                        "characteristics": ["改进机会", "风险警示", "负面口碑"]
                    }
                ]
            }
        }
        
        return ReportSection(
            section_id="detailed_analysis",
            title="深度分析",
            content=content,
            priority="high",
            visualization_data=visualization_data
        )
    
    async def _generate_question_group_section(self,
                                             question_group_analysis: QuestionGroupAnalysisResult) -> ReportSection:
        """生成题组分析章节"""
        
        content = {
            "promoter_analysis": {
                "choice_questions": asdict(question_group_analysis.promoter_choice_insights),
                "open_questions": asdict(question_group_analysis.promoter_open_insights)
            },
            "detractor_analysis": {
                "choice_questions": asdict(question_group_analysis.detractor_choice_insights),
                "open_questions": asdict(question_group_analysis.detractor_open_insights)
            },
            "cross_group_comparison": question_group_analysis.cross_group_comparison,
            "priority_actions": question_group_analysis.priority_actions
        }
        
        # 可视化数据 - 主题对比
        visualization_data = {
            "theme_comparison": {
                "promoter_themes": [
                    {"theme": theme["theme"], "percentage": theme["percentage"]}
                    for theme in question_group_analysis.promoter_open_insights.key_themes[:5]
                ],
                "detractor_themes": [
                    {"theme": theme["theme"], "percentage": theme["percentage"]}
                    for theme in question_group_analysis.detractor_open_insights.key_themes[:5]
                ]
            },
            "sentiment_analysis": {
                "promoter_sentiment": question_group_analysis.promoter_open_insights.sentiment_analysis.get("overall_tone", "neutral"),
                "detractor_sentiment": question_group_analysis.detractor_open_insights.sentiment_analysis.get("overall_tone", "neutral")
            }
        }
        
        return ReportSection(
            section_id="question_group_insights",
            title="题组洞察分析",
            content=content,
            priority="medium",
            visualization_data=visualization_data
        )
    
    async def _generate_business_intelligence_section(self,
                                                    business_insights: BusinessInsightsResult) -> ReportSection:
        """生成商业智能章节"""
        
        content = {
            "market_insights": [asdict(insight) for insight in business_insights.market_insights],
            "competitive_analysis": [asdict(analysis) for analysis in business_insights.competitive_analysis],
            "regional_insights": [asdict(insight) for insight in business_insights.regional_insights],
            "trend_predictions": [asdict(prediction) for prediction in business_insights.trend_predictions],
            "strategic_summary": business_insights.strategic_summary
        }
        
        # 可视化数据 - 竞争分析雷达图
        visualization_data = {
            "competitive_radar": {
                "dimensions": ["品牌知名度", "产品质量", "价格竞争力", "渠道覆盖", "创新能力"],
                "companies": [
                    {
                        "name": "伊利",
                        "scores": [90, 85, 75, 90, 80]  # 示例数据
                    }
                ]
            },
            "market_opportunities": [
                {
                    "opportunity": insight.title,
                    "impact": insight.impact_assessment,
                    "confidence": insight.confidence_level
                }
                for insight in business_insights.market_insights[:5]
            ]
        }
        
        return ReportSection(
            section_id="business_intelligence",
            title="商业智能洞察",
            content=content,
            priority="medium",
            visualization_data=visualization_data
        )
    
    async def _generate_recommendations_section(self,
                                              nps_insights: NPSInsightResult,
                                              question_group_analysis: QuestionGroupAnalysisResult,
                                              business_insights: BusinessInsightsResult) -> ReportSection:
        """生成建议章节"""
        
        # 整合所有建议
        all_recommendations = []
        
        # NPS建议
        for rec in nps_insights.business_recommendations:
            all_recommendations.append({
                "source": "NPS分析",
                "priority": rec.get("priority", "medium"),
                "category": rec.get("category", "general"),
                "title": rec.get("title", ""),
                "description": rec.get("description", ""),
                "actions": rec.get("actions", [])
            })
        
        # 题组分析建议
        for action in question_group_analysis.priority_actions:
            all_recommendations.append({
                "source": "题组分析",
                "priority": action.get("priority", "medium"),
                "category": action.get("category", "general"),
                "title": action.get("title", ""),
                "description": action.get("description", ""),
                "actions": [action.get("expected_impact", "")]
            })
        
        # 业务洞察建议
        for action in business_insights.action_priorities:
            all_recommendations.append({
                "source": "业务洞察",
                "priority": action.get("priority", "P2"),
                "category": action.get("category", "general"),
                "title": action.get("title", ""),
                "description": action.get("description", ""),
                "actions": [action.get("timeline", ""), action.get("expected_impact", "")]
            })
        
        # 按优先级排序
        priority_order = {"urgent": 0, "high": 1, "medium": 2, "low": 3, "P0": 0, "P1": 1, "P2": 2, "P3": 3}
        all_recommendations.sort(key=lambda x: priority_order.get(x["priority"], 99))
        
        content = {
            "immediate_actions": [rec for rec in all_recommendations if rec["priority"] in ["urgent", "P0"]][:3],
            "short_term_actions": [rec for rec in all_recommendations if rec["priority"] in ["high", "P1"]][:5],
            "medium_term_actions": [rec for rec in all_recommendations if rec["priority"] in ["medium", "P2"]][:5],
            "implementation_roadmap": {
                "phase_1": "立即执行（1-4周）",
                "phase_2": "短期规划（1-3个月）",
                "phase_3": "中期规划（3-6个月）"
            },
            "success_metrics": [
                "NPS得分提升",
                "推荐者比例增加",
                "客户满意度改善",
                "市场份额增长"
            ]
        }
        
        return ReportSection(
            section_id="recommendations",
            title="行动建议",
            content=content,
            priority="high"
        )
    
    async def _generate_appendix_section(self,
                                       survey_data: ProcessedSurveyData,
                                       v1_comparison_data: Optional[Dict[str, Any]],
                                       context: Optional[Dict[str, Any]]) -> ReportSection:
        """生成附录章节"""
        
        content = {
            "data_summary": {
                "total_responses": len(survey_data.response_data),
                "survey_metadata": asdict(survey_data.survey_metadata),
                "data_collection_period": survey_data.survey_metadata.collection_date,
                "survey_type": survey_data.survey_metadata.survey_type
            },
            "methodology": {
                "analysis_approach": "多智能体综合分析",
                "agents_used": ["NPS分析智能体", "题组分析智能体", "洞察智能体"],
                "data_processing": "V2增强处理管道",
                "quality_assurance": "多层质量检验"
            },
            "technical_details": {
                "processing_pipeline": "V2并行处理架构",
                "analysis_version": "2.0",
                "generation_timestamp": datetime.now().isoformat()
            }
        }
        
        # 如果有V1对比数据，添加到附录
        if v1_comparison_data:
            content["v1_comparison"] = {
                "comparison_available": True,
                "v1_results": v1_comparison_data.get("v1_result", {}),
                "v2_enhancements": v1_comparison_data.get("comparison_analysis", {}),
                "improvement_details": "V2版本在分析深度、业务洞察和建议质量方面的提升"
            }
        
        # 添加上下文信息
        if context:
            content["additional_context"] = context
        
        return ReportSection(
            section_id="appendix",
            title="附录",
            content=content,
            priority="low"
        )
    
    async def _generate_html_report(self, report: ComprehensiveReport) -> str:
        """生成HTML报告"""
        
        # 尝试使用自定义模板
        try:
            template = self.jinja_env.get_template("comprehensive_report.html")
        except:
            # 如果没有自定义模板，使用内置模板
            template = Template(self._get_builtin_html_template())
        
        # 渲染HTML
        html_content = template.render(
            report=report,
            generation_time=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
        
        # 保存HTML文件
        html_filename = f"{report.report_id}.html"
        html_path = os.path.join(self.reports_dir, html_filename)
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML报告已保存: {html_path}")
        return html_path
    
    async def _save_json_results(self, report: ComprehensiveReport) -> str:
        """保存JSON结果"""
        
        # 转换为可序列化的字典
        report_dict = asdict(report)
        
        # 保存JSON文件
        json_filename = f"{report.report_id}.json"
        json_path = os.path.join(self.results_dir, json_filename)
        
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, ensure_ascii=False, indent=2)
        
        logger.info(f"JSON结果已保存: {json_path}")
        return json_path
    
    def _get_builtin_html_template(self) -> str:
        """获取内置HTML模板"""
        
        return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NPS综合分析报告 - {{ report.report_id }}</title>
    <style>
        body { 
            font-family: 'Microsoft YaHei', Arial, sans-serif; 
            line-height: 1.6; 
            margin: 0; 
            padding: 20px; 
            background-color: #f5f5f5; 
        }
        .container { 
            max-width: 1200px; 
            margin: 0 auto; 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            box-shadow: 0 0 20px rgba(0,0,0,0.1); 
        }
        .header { 
            text-align: center; 
            border-bottom: 3px solid #2c5aa0; 
            padding-bottom: 20px; 
            margin-bottom: 30px; 
        }
        .header h1 { 
            color: #2c5aa0; 
            font-size: 2.5em; 
            margin: 0; 
        }
        .header .subtitle { 
            color: #666; 
            font-size: 1.1em; 
            margin-top: 10px; 
        }
        .section { 
            margin-bottom: 40px; 
            padding: 20px; 
            border-left: 5px solid #2c5aa0; 
            background-color: #fafafa; 
        }
        .section h2 { 
            color: #2c5aa0; 
            font-size: 1.8em; 
            margin-top: 0; 
        }
        .metric-card { 
            display: inline-block; 
            background: white; 
            padding: 20px; 
            margin: 10px; 
            border-radius: 8px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
            text-align: center; 
            min-width: 150px; 
        }
        .metric-value { 
            font-size: 2.5em; 
            font-weight: bold; 
            color: #2c5aa0; 
        }
        .metric-label { 
            color: #666; 
            font-size: 0.9em; 
            margin-top: 5px; 
        }
        .recommendation { 
            background: #e8f4f8; 
            padding: 15px; 
            margin: 10px 0; 
            border-left: 5px solid #2c5aa0; 
            border-radius: 5px; 
        }
        .recommendation .priority { 
            font-weight: bold; 
            color: #d32f2f; 
        }
        .insight-item { 
            background: white; 
            padding: 15px; 
            margin: 10px 0; 
            border-radius: 5px; 
            border-left: 3px solid #4caf50; 
        }
        .footer { 
            text-align: center; 
            color: #666; 
            font-size: 0.9em; 
            margin-top: 40px; 
            padding-top: 20px; 
            border-top: 1px solid #ddd; 
        }
        .alert { 
            background: #ffebee; 
            color: #c62828; 
            padding: 15px; 
            border-radius: 5px; 
            margin: 10px 0; 
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 15px 0; 
        }
        th, td { 
            padding: 12px; 
            text-align: left; 
            border-bottom: 1px solid #ddd; 
        }
        th { 
            background-color: #f5f5f5; 
            font-weight: bold; 
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- 报告头部 -->
        <div class="header">
            <h1>NPS综合分析报告</h1>
            <div class="subtitle">报告ID: {{ report.report_id }} | 生成时间: {{ generation_time }}</div>
        </div>

        <!-- 执行摘要 -->
        <div class="section">
            <h2>📊 执行摘要</h2>
            
            <!-- 关键指标 -->
            <div style="text-align: center; margin: 20px 0;">
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(report.executive_summary.key_metrics.overall_nps) }}</div>
                    <div class="metric-label">NPS得分</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ report.executive_summary.key_metrics.sample_size }}</div>
                    <div class="metric-label">样本量</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1%"|format(report.executive_summary.key_metrics.confidence_level) }}</div>
                    <div class="metric-label">置信度</div>
                </div>
            </div>

            <!-- 关键发现 -->
            <h3>🎯 关键发现</h3>
            {% for finding in report.executive_summary.key_findings %}
            <div class="insight-item">{{ finding }}</div>
            {% endfor %}

            <!-- 核心建议 -->
            <h3>💡 核心建议</h3>
            {% for recommendation in report.executive_summary.core_recommendations %}
            <div class="recommendation">{{ recommendation }}</div>
            {% endfor %}

            <!-- 风险警示 -->
            {% if report.executive_summary.risk_alerts %}
            <h3>⚠️ 风险警示</h3>
            {% for alert in report.executive_summary.risk_alerts %}
            <div class="alert">{{ alert }}</div>
            {% endfor %}
            {% endif %}
        </div>

        <!-- NPS总览 -->
        <div class="section">
            <h2>📈 NPS总览</h2>
            
            <h3>整体表现</h3>
            <p><strong>NPS得分:</strong> {{ "%.1f"|format(report.nps_overview.content.nps_score.value) }} 
               ({{ report.nps_overview.content.nps_score.grade }}级)</p>
            <p><strong>解读:</strong> {{ report.nps_overview.content.nps_score.interpretation }}</p>

            <h3>客户分布</h3>
            <table>
                <tr>
                    <th>客户类型</th>
                    <th>数量</th>
                    <th>比例</th>
                </tr>
                <tr>
                    <td>推荐者 (9-10分)</td>
                    <td>{{ report.nps_overview.content.distribution.promoters.count }}</td>
                    <td>{{ "%.1f"|format(report.nps_overview.content.distribution.promoters.percentage) }}%</td>
                </tr>
                <tr>
                    <td>中性者 (7-8分)</td>
                    <td>{{ report.nps_overview.content.distribution.passives.count }}</td>
                    <td>{{ "%.1f"|format(report.nps_overview.content.distribution.passives.percentage) }}%</td>
                </tr>
                <tr>
                    <td>批评者 (0-6分)</td>
                    <td>{{ report.nps_overview.content.distribution.detractors.count }}</td>
                    <td>{{ "%.1f"|format(report.nps_overview.content.distribution.detractors.percentage) }}%</td>
                </tr>
            </table>
        </div>

        <!-- 题组洞察分析 -->
        <div class="section">
            <h2>🔍 题组洞察分析</h2>
            
            <h3>推荐者洞察</h3>
            {% for insight in report.question_group_insights.content.promoter_analysis.open_questions.actionable_insights %}
            <div class="insight-item">{{ insight }}</div>
            {% endfor %}

            <h3>批评者洞察</h3>
            {% for insight in report.question_group_insights.content.detractor_analysis.open_questions.actionable_insights %}
            <div class="insight-item">{{ insight }}</div>
            {% endfor %}
        </div>

        <!-- 商业智能洞察 -->
        <div class="section">
            <h2>🧠 商业智能洞察</h2>
            
            <h3>市场洞察</h3>
            {% for insight in report.business_intelligence.content.market_insights[:3] %}
            <div class="insight-item">
                <strong>{{ insight.title }}</strong><br>
                {{ insight.description }}
            </div>
            {% endfor %}

            <h3>竞争分析</h3>
            {% for analysis in report.business_intelligence.content.competitive_analysis[:2] %}
            <div class="insight-item">
                <strong>vs {{ analysis.competitor_name }}</strong>: {{ analysis.competitive_position }}
            </div>
            {% endfor %}
        </div>

        <!-- 行动建议 -->
        <div class="section">
            <h2>🎯 行动建议</h2>
            
            <h3>立即行动</h3>
            {% for action in report.recommendations.content.immediate_actions %}
            <div class="recommendation">
                <span class="priority">[{{ action.priority }}]</span> 
                <strong>{{ action.title }}</strong><br>
                {{ action.description }}
            </div>
            {% endfor %}

            <h3>短期规划</h3>
            {% for action in report.recommendations.content.short_term_actions[:3] %}
            <div class="recommendation">
                <span class="priority">[{{ action.priority }}]</span> 
                <strong>{{ action.title }}</strong><br>
                {{ action.description }}
            </div>
            {% endfor %}
        </div>

        <!-- 附录 -->
        <div class="section">
            <h2>📋 附录</h2>
            
            <h3>数据概要</h3>
            <p><strong>总回应数:</strong> {{ report.appendix.content.data_summary.total_responses }}</p>
            <p><strong>调研类型:</strong> {{ report.appendix.content.data_summary.survey_type }}</p>
            <p><strong>分析方法:</strong> {{ report.appendix.content.methodology.analysis_approach }}</p>
            
            {% if report.appendix.content.v1_comparison %}
            <h3>V1/V2对比</h3>
            <p>{{ report.appendix.content.v1_comparison.improvement_details }}</p>
            {% endif %}
        </div>

        <!-- 页脚 -->
        <div class="footer">
            <p>本报告由NPS分析系统V2.0自动生成 | 伊利集团NPS分析项目</p>
            <p>报告生成时间: {{ generation_time }}</p>
        </div>
    </div>
</body>
</html>
        """

# 使用示例
async def main():
    """主函数示例"""
    generator = ReportGenerator()
    print("报告生成器初始化完成")

if __name__ == "__main__":
    asyncio.run(main())