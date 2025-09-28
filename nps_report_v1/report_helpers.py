"""
Helper functions for comprehensive report generation
"""

from typing import Dict, List, Any
from datetime import datetime
import os
from pathlib import Path


def get_quality_grade(overall_quality: float) -> str:
    """Convert quality score to grade."""
    if overall_quality >= 8.0:
        return "优秀"
    elif overall_quality >= 6.0:
        return "良好"
    elif overall_quality >= 4.0:
        return "一般"
    else:
        return "需改进"


def get_quality_suggestions(quality_metrics: Dict[str, float]) -> List[str]:
    """Generate improvement suggestions based on quality metrics."""
    suggestions = []
    
    if quality_metrics["data_completeness"] < 0.8:
        suggestions.append("提高数据清洗质量，减少无效响应")
    
    if quality_metrics["analysis_depth"] < 0.7:
        suggestions.append("增强分析深度，完善所有分析组件")
    
    if quality_metrics["confidence_level"] < 0.6:
        suggestions.append("提升分析方法置信度，考虑使用高级NLP技术")
    
    if quality_metrics["coverage_score"] < 0.8:
        suggestions.append("扩大评论覆盖率，收集更多定性反馈")
    
    return suggestions


def calculate_processing_time(state: Dict[str, Any]) -> str:
    """Calculate processing time if timestamps are available."""
    start_time = state.get("workflow_start_time")
    if start_time:
        try:
            start_dt = datetime.fromisoformat(start_time)
            duration = datetime.now() - start_dt
            return f"{duration.total_seconds():.2f}秒"
        except:
            return "未知"
    return "未记录"


def calculate_statistical_confidence(nps_results: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate statistical confidence indicators."""
    total_responses = nps_results.get("total_responses", 0)
    
    if total_responses == 0:
        return {"confidence_level": "无效", "margin_of_error": "N/A", "sample_size": 0}
    
    # Simple confidence calculation
    if total_responses >= 100:
        confidence_level = "高"
        margin_of_error = "±5%"
    elif total_responses >= 30:
        confidence_level = "中"
        margin_of_error = "±10%"
    else:
        confidence_level = "低"
        margin_of_error = "±15%"
    
    return {
        "confidence_level": confidence_level,
        "margin_of_error": margin_of_error,
        "sample_size": total_responses
    }


def extract_quantitative_trends(nps_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract quantitative trend indicators."""
    trends = []
    
    score_breakdown = nps_results.get("score_breakdown", {})
    if score_breakdown:
        promoters_pct = score_breakdown.get("promoters", {}).get("percentage", 0)
        detractors_pct = score_breakdown.get("detractors", {}).get("percentage", 0)
        
        if promoters_pct > 50:
            trends.append({"indicator": "高推荐度", "value": f"{promoters_pct:.1f}%", "trend": "positive"})
        
        if detractors_pct > 30:
            trends.append({"indicator": "高反对度", "value": f"{detractors_pct:.1f}%", "trend": "negative"})
    
    return trends


def enhance_theme_analysis(qual_results: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance theme analysis with additional insights."""
    themes = qual_results.get("top_themes", [])
    if not themes:
        return {"theme_count": 0, "dominant_theme": None, "theme_diversity": "无"}
    
    # Find dominant theme
    dominant_theme = max(themes, key=lambda x: x.get("mentions", 0))
    
    return {
        "theme_count": len(themes),
        "dominant_theme": dominant_theme.get("theme", "未知"),
        "theme_diversity": "高" if len(themes) >= 5 else "中" if len(themes) >= 3 else "低"
    }


def enhance_sentiment_analysis(qual_results: Dict[str, Any]) -> Dict[str, Any]:
    """Enhance sentiment analysis with distribution metrics - with defensive dict handling."""
    sentiment_overview = qual_results.get("sentiment_overview", {})
    if not sentiment_overview:
        return {"sentiment_balance": "未分析", "primary_sentiment": "unknown"}
    
    # Safely extract sentiment counts, handling both number and dict values
    def extract_sentiment_count(sentiment_data, key):
        value = sentiment_data.get(key, 0)
        if isinstance(value, dict):
            # If it's a dict, try to get 'count' field or return 0
            return value.get('count', value.get('percentage', 0))
        elif isinstance(value, (int, float)):
            return value
        else:
            return 0
    
    positive = extract_sentiment_count(sentiment_overview, "positive")
    negative = extract_sentiment_count(sentiment_overview, "negative")
    neutral = extract_sentiment_count(sentiment_overview, "neutral")
    total = positive + negative + neutral
    
    if total == 0:
        return {"sentiment_balance": "无数据", "primary_sentiment": "unknown"}
    
    # Calculate sentiment balance
    if positive > negative * 1.5:
        sentiment_balance = "偏正面"
        primary_sentiment = "positive"
    elif negative > positive * 1.5:
        sentiment_balance = "偏负面"
        primary_sentiment = "negative"
    else:
        sentiment_balance = "平衡"
        primary_sentiment = "mixed"
    
    return {
        "sentiment_balance": sentiment_balance,
        "primary_sentiment": primary_sentiment,
        "sentiment_distribution": {
            "positive_ratio": f"{positive/total:.1%}",
            "negative_ratio": f"{negative/total:.1%}",
            "neutral_ratio": f"{neutral/total:.1%}"
        }
    }


def prioritize_strategic_insights(context_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extract and prioritize strategic insights."""
    business_insights = context_results.get("business_insights", [])
    
    # Filter for strategic insights only
    strategic_insights = []
    strategic_categories = ["产品策略", "竞争策略", "市场策略", "定价策略"]
    
    for insight in business_insights:
        if insight.get("category") in strategic_categories:
            strategic_insights.append({
                "insight": insight.get("insight", ""),
                "priority": insight.get("priority", "medium"),
                "category": insight.get("category", ""),
                "strategic_impact": "high" if insight.get("priority") == "high" else "medium"
            })
    
    return strategic_insights[:5]  # Top 5 strategic insights


def summarize_competitive_intelligence(context_results: Dict[str, Any]) -> Dict[str, Any]:
    """Summarize competitive intelligence findings."""
    competitor_analysis = context_results.get("competitor_analysis", {})
    
    total_mentions = competitor_analysis.get("total_competitor_mentions", 0)
    unique_competitors = competitor_analysis.get("unique_competitors", 0)
    threat_distribution = competitor_analysis.get("threat_distribution", {})
    
    return {
        "competitive_pressure": "高" if total_mentions > 3 else "中" if total_mentions > 0 else "低",
        "competitor_mentions": total_mentions,
        "unique_competitors": unique_competitors,
        "high_threats": threat_distribution.get("high", 0),
        "primary_threat": _identify_primary_threat(competitor_analysis)
    }


def identify_market_opportunities(context_results: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Identify market opportunities from analysis."""
    opportunities = []
    
    # From market trends
    market_trends = context_results.get("market_trends", [])
    for trend in market_trends:
        if trend.get("business_impact") == "high":
            opportunities.append({
                "opportunity": f"利用{trend.get('trend_name', '')}趋势",
                "description": trend.get("description", ""),
                "potential": trend.get("strength", "moderate")
            })
    
    # From business insights
    business_insights = context_results.get("business_insights", [])
    positive_insights = [i for i in business_insights if "优秀" in i.get("insight", "")]
    
    for insight in positive_insights[:2]:  # Top 2 positive insights
        opportunities.append({
            "opportunity": "扩大产品优势",
            "description": insight.get("insight", ""),
            "potential": "high"
        })
    
    return opportunities


def generate_next_steps(state: Dict[str, Any], quality_report: Dict[str, Any]) -> List[str]:
    """Generate concrete next steps based on analysis."""
    next_steps = []
    
    # Quality-based steps
    quality_score = quality_report["overall_quality_score"]
    if quality_score < 6.0:
        next_steps.append("改善数据收集质量，增加样本量")
    
    # NPS-based steps
    nps_score = state.get("nps_results", {}).get("nps_score", 0)
    if nps_score < -10:
        next_steps.append("启动客户满意度提升项目")
    elif nps_score > 30:
        next_steps.append("制定客户忠诚度维护计划")
    
    # Competitive steps
    # ... additional rules can be added
    
    return next_steps


def _identify_primary_threat(competitor_analysis: Dict[str, Any]) -> str:
    threats = competitor_analysis.get("competitor_threats", {})
    if not threats:
        return "无"
    # Find competitor with highest threat level
    max_threat = None
    max_level = 0
    for competitor, data in threats.items():
        level = {"low": 1, "medium": 2, "high": 3}.get(str(data.get("threat_level", "low")).lower(), 0)
        if level > max_level:
            max_level = level
            max_threat = competitor
    return max_threat or "无"


def _get_nps_color(nps_score: float) -> str:
    if nps_score >= 50:
        return "#4caf50"
    elif nps_score >= 0:
        return "#ff9800"
    else:
        return "#f44336"


def _get_nps_assessment(nps_score: float) -> str:
    if nps_score >= 70:
        return "优秀表现"
    elif nps_score >= 50:
        return "良好表现"
    elif nps_score >= 30:
        return "有待提升"
    elif nps_score >= 0:
        return "需要改进"
    else:
        return "亟需关注"


def generate_enhanced_html_report(state: Dict[str, Any], quality_report: Dict[str, Any]) -> str:
    """Ported from demo: comprehensive HTML report with charts and styles."""
    nps_results = state.get("nps_results", {})
    qual_results = state.get("qual_results", {})
    context_results = state.get("context_results", {})

    nps_score = nps_results.get("nps_score", 0)
    quality_score = quality_report.get("overall_quality_score", 0)
    total_responses = len(state.get("clean_responses", []))

    score_breakdown = nps_results.get("score_breakdown", {})
    promoters_pct = score_breakdown.get("promoters", {}).get("percentage", 0)
    passives_pct = score_breakdown.get("passives", {}).get("percentage", 0)
    detractors_pct = score_breakdown.get("detractors", {}).get("percentage", 0)

    themes = qual_results.get("top_themes", [])
    themes_html = ""
    for theme in themes[:5]:
        sentiment_color = {"positive": "#4caf50", "negative": "#f44336", "neutral": "#ff9800"}.get(theme.get("sentiment", "neutral"), "#9e9e9e")
        sentiment_map = {"positive": "正面", "negative": "负面", "neutral": "中性"}
        sentiment_text = sentiment_map.get(theme.get("sentiment", "neutral"), "未知")
        theme_mentions = theme.get("mentions", 0)
        mention_format = f"{theme_mentions}/{total_responses}"
        themes_html += f"""
        <div class=\"theme-item\" style=\"border-left: 4px solid {sentiment_color};\">
            <strong>{theme.get("theme", "未知主题")}</strong> ({mention_format}次提及)
            <div class=\"theme-sentiment\">情感: {sentiment_text}</div>
        </div>"""

    # Helper: map priority to label
    def priority_label(p: str) -> str:
        m = {"high": "HIGH", "medium": "MEDIUM", "low": "LOW"}
        return m.get(str(p).lower(), str(p).upper())

    # Helper: default action suggestions by category
    def default_action_for(insight: Dict[str, Any]) -> str:
        cat = insight.get("category", "")
        text = insight.get("insight", "")
        if "竞争" in cat or "对手" in text:
            return "强化品牌差异化，加大市场营销投入"
        if "质量" in text or "产品质量" in cat:
            return "加强质量控制体系，提升产品稳定性和口感"
        if "健康" in text:
            return "加强功能性产品开发，突出营养价值和健康益处"
        if "区域" in text:
            return "制定区域化营销策略，针对性投放资源"
        return "细化执行计划，明确负责人与时间节点"

    # Build a robust business_insights list (synthesize if empty)
    base_insights = context_results.get("business_insights", []) or []
    synthesized: List[Dict[str, Any]] = []
    # Synthesize from competitor analysis
    comp = context_results.get("competitor_analysis", {})
    total_comp = int(comp.get("total_competitor_mentions", 0) or 0)
    if total_comp > 0:
        synthesized.append({
            "insight": f"发现{total_comp}个竞争提及，需要关注",
            "priority": "high" if total_comp >= 1 else "medium",
            "category": "竞争策略",
            "action": "分析高威胁竞争对手的优势，制定差异化策略"
        })
    threats = comp.get("competitor_threats", {}) or {}
    # pick the worst
    high_threats = [ (k, v) for k,v in threats.items() if str(v.get('threat_level','')).lower()== 'high']
    if high_threats:
        name, v = high_threats[0]
        pos_mentions = 0
        mentions = int(v.get('mentions', 0) or 0)
        synthesized.append({
            "insight": f"{name}构成高威胁，客户正面提及{pos_mentions}/{mentions}次",
            "priority": "high",
            "category": "竞争策略",
            "action": "深入研究该竞争对手的产品优势，制定针对性竞争策略"
        })
    # Synthesize from trends
    trends = context_results.get("market_trends", []) or []
    for t in trends:
        if t.get('trend_id') == 'health_wellness':
            synthesized.append({
                "insight": "健康意识趋势明显：" + str(t.get('description','')),
                "priority": "high" if t.get('business_impact') == 'high' else 'medium',
                "category": "产品策略",
                "action": "加强功能性产品开发，突出营养价值和健康益处"
            })
        if t.get('trend_id') == 'quality_focus':
            synthesized.append({
                "insight": "质量关注度提升：" + str(t.get('description','')),
                "priority": "high",
                "category": "产品策略",
                "action": "加强质量控制体系，提升产品稳定性和口感"
            })
        if t.get('trend_id') == 'competitive_pressure':
            synthesized.append({
                "insight": "竞争环境变化：市场竞争压力" + str(t.get('description','')).replace('市场竞争压力',''),
                "priority": "high",
                "category": "市场策略",
                "action": "强化品牌差异化，加大市场营销投入"
            })
        if t.get('trend_id') == 'regional_variation':
            synthesized.append({
                "insight": "区域市场差异：" + str(t.get('description','')),
                "priority": "medium",
                "category": "市场策略",
                "action": "制定区域化营销策略，针对性投放资源"
            })

    all_insights: List[Dict[str, Any]] = base_insights + synthesized

    # Key metrics
    promoters_pct = score_breakdown.get("promoters", {}).get("percentage", 0)
    detractors_pct = score_breakdown.get("detractors", {}).get("percentage", 0)
    theme_count = len(themes)
    insights_count = len(all_insights)

    # Statistical confidence (top-level helper already used elsewhere)
    stats_conf = calculate_statistical_confidence(nps_results)
    conf_map = {"高": 90.0, "中": 70.0, "低": 50.0}
    confidence_percent = conf_map.get(str(stats_conf.get('confidence_level', '低')), 50.0)

    # Use CDN Chart.js by default (no inline). Optionally override via PUBLIC_BASE_URL.
    embed_chart = False
    chart_js_content = ""
    # Public base (if you want to serve from your host instead of CDN)
    base_url = os.getenv('PUBLIC_BASE_URL', '').rstrip('/')
    script_src = "https://cdn.jsdelivr.net/npm/chart.js" if not base_url else f"{base_url}/static/thirdparty/chart.umd.min.js"

    html_report = f"""<!DOCTYPE html>
<html lang=\"zh-CN\">
<head>
    <meta charset=\"UTF-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>伊利集团NPS分析报告</title>
    <script src=\"{script_src}\"></script>
    <style>
        * {{ box-sizing: border-box; }}
        body {{ 
            font-family: 'Microsoft YaHei', 'PingFang SC', 'Hiragino Sans GB', Arial, sans-serif; 
            margin: 0; padding: 20px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{ 
            max-width: 1400px; margin: 0 auto; background: white; 
            border-radius: 12px; box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            overflow: hidden;
        }}
        .header {{ 
            background: linear-gradient(135deg, #1e88e5 0%, #1565c0 100%);
            color: white; text-align: center; padding: 40px 20px;
        }}
        .header h1 {{ margin: 0; font-size: 2.5em; font-weight: 300; }}
        .header p {{ margin: 10px 0 0 0; opacity: 0.9; }}
        
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; padding: 30px; }}
        .metric-card {{ 
            background: white; padding: 25px; border-radius: 8px; 
            box-shadow: 0 2px 8px rgba(0,0,0,0.1); text-align: center;
            border-top: 4px solid #1e88e5;
        }}
        .metric-value {{ 
            font-size: 2.5em; font-weight: bold; 
            color: {_get_nps_color(nps_score)}; margin: 10px 0;
        }}
        .metric-label {{ font-size: 0.9em; color: #666; text-transform: uppercase; letter-spacing: 1px; }}
        .metric-trend {{ font-size: 0.8em; color: #999; margin-top: 5px; }}
        
        .content {{ padding: 0 30px 30px 30px; }}
        .section {{ 
            background: #fafafa; margin: 20px 0; padding: 25px; 
            border-radius: 8px; border-left: 4px solid #1e88e5;
        }}
        .section h2 {{ margin-top: 0; color: #333; font-weight: 500; }}
        
        .nps-breakdown {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .nps-segment {{ text-align: center; padding: 15px; }}
        .promoters {{ color: #4caf50; }}
        .passives {{ color: #ff9800; }}
        .detractors {{ color: #f44336; }}
        
        .insights-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 15px; }}
        .insight-card {{ 
            background: white; padding: 20px; border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .insight-card.high-priority {{ border-left: 4px solid #f44336; }}
        .insight-card.medium-priority {{ border-left: 4px solid #ff9800; }}
        .insight-card.low-priority {{ border-left: 4px solid #4caf50; }}
        
        .theme-item {{ 
            background: white; margin: 10px 0; padding: 15px; border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }}
        .theme-sentiment {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
        
        .chart-container {{ 
            position: relative; height: 300px; margin: 20px 0;
            background: white; padding: 20px; border-radius: 8px;
        }}
        
        .quality-bar {{ 
            background: #e0e0e0; height: 20px; border-radius: 10px; overflow: hidden;
            margin: 10px 0;
        }}
        .quality-fill {{ 
            height: 100%; background: linear-gradient(90deg, #f44336 0%, #ff9800 50%, #4caf50 100%);
            transition: width 0.3s ease;
        }}
        
        .footer {{ 
            background: #333; color: white; text-align: center; 
            padding: 20px; font-size: 0.9em;
        }}
    </style>
</head>
<body>
    <div class=\"container\">
        <div class=\"header\">
            <h1>伊利集团NPS客户满意度分析报告</h1>
            <p>智能分析报告 • {datetime.now().strftime('%Y年%m月%d日 %H:%M')} • 系统版本 1.0</p>
        </div>
        
        <div class=\"dashboard\">
            <div class=\"metric-card\">
                <div class=\"metric-value\">{nps_score:.1f}</div>
                <div class=\"metric-label\">NPS得分</div>
                <div class=\"metric-trend\">{_get_nps_assessment(nps_score)}</div>
            </div>
            <div class=\"metric-card\">
                <div class=\"metric-value\">{total_responses}</div>
                <div class=\"metric-label\">分析样本</div>
                <div class=\"metric-trend\">客户反馈数量</div>
            </div>
            <div class=\"metric-card\">
                <div class=\"metric-value\">{quality_score:.1f}</div>
                <div class=\"metric-label\">数据质量</div>
                <div class=\"metric-trend\">{quality_report.get("quality_grade", "")}等级</div>
            </div>
            <div class=\"metric-card\">
                <div class=\"metric-value\">{insights_count}</div>
                <div class=\"metric-label\">业务洞察</div>
                <div class=\"metric-trend\">战略建议数量</div>
            </div>
        </div>
        
        <div class=\"content\">
            <div class=\"section\">
                <h2>🔍 执行摘要</h2>
                <p>分析范围: 本报告基于 {total_responses} 份客户反馈进行综合分析</p>
                <p>NPS评估: {_get_nps_assessment(nps_score)} (得分: {nps_score:.1f})</p>
                <p>主要发现: 系统识别了 {insights_count} 项关键业务洞察</p>
                <p>技术说明: 采用多智能体架构，整合定量分析、NLP处理和业务智能分析</p>
            </div>

            <div class=\"section\">
                <h2>📊 关键指标一览</h2>
                <ul>
                    <li>• 推荐者比例: {promoters_pct:.1f}%</li>
                    <li>• 批评者比例: {detractors_pct:.1f}%</li>
                    <li>• 数据质量得分: {quality_score:.1f}/10</li>
                    <li>• 主题覆盖数量: {theme_count} 个关键主题</li>
                </ul>
            </div>

            <div class=\"section\">
                <h2>📊 NPS构成分析</h2>
                <div class=\"chart-container\">
                    <canvas id=\"npsChart\"></canvas>
                </div>
                <div class=\"nps-breakdown\">
                    <div class=\"nps-segment promoters\">
                        <h3>{promoters_pct:.1f}%</h3>
                        <p>推荐者</p>
                    </div>
                    <div class=\"nps-segment passives\">
                        <h3>{passives_pct:.1f}%</h3>
                        <p>被动者</p>
                    </div>
                    <div class=\"nps-segment detractors\">
                        <h3>{detractors_pct:.1f}%</h3>
                        <p>批评者</p>
                    </div>
                </div>
            </div>
            
            <div class=\"section\">
                <h2>🎯 关键主题分析</h2>
                {themes_html if themes_html else '<p>暂无主题数据</p>'}
            </div>
            
            <div class=\"section\">
                <h2>💡 战略业务洞察</h2>
                <div class=\"insights-grid\">"""

    for insight in all_insights[:20]:
        priority_class = f"{insight.get('priority','medium')}-priority"
        pr = priority_label(insight.get('priority', 'medium'))
        cat = insight.get('category', '业务洞察')
        text = insight.get('insight', '')
        action = insight.get('action') or default_action_for(insight)
        html_report += f"""
                    <div class=\"insight-card {priority_class}\">
                        <div class=\"muted\">📊 业务洞察</div>
                        <div><strong>[{pr}] {cat}：{text}</strong></div>
                        <div style=\"margin-top:8px\"><em>建议行动:</em> {action}</div>
                    </div>
        """

    html_report += f"""
                </div>
            </div>

            <div class=\"section\">
                <h2>📈 情感分布</h2>
                <div class=\"chart-container\" style=\"height:260px\">
                    <canvas id=\"sentimentChart\"></canvas>
                </div>
            </div>

            <div class=\"section\">
                <h2>🧩 产品映射与表现</h2>
                <div class=\"chart-container\" style=\"height:auto\">
                    <table>
                        <thead>
                            <tr><th>提及名</th><th>官方产品</th><th>品类</th><th>产品线</th><th>提及次数</th><th>情感</th><th>匹配置信</th></tr>
                        </thead>
                        <tbody>
                        {''.join(
                            f"<tr><td>{m.get('mentioned_name','')}</td><td>{m.get('official_product','')}</td><td>{m.get('product_category','')}</td><td>{m.get('product_line','')}</td><td>{m.get('mention_data',{}).get('mentions',0)}</td><td>{m.get('mention_data',{}).get('sentiment','')}</td><td>{m.get('confidence',0)}</td></tr>"
                            for m in context_results.get('product_mapping',{}).get('mention_mapping',[])[:50]
                        )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class=\"section\">
                <h2>🧭 竞争情报</h2>
                <div class=\"insights-grid\">
                    <div class=\"insight-card\">
                        <div class=\"muted\">汇总</div>
                        <div>总提及：{context_results.get('competitor_analysis',{}).get('total_competitor_mentions',0)}，唯一对手：{context_results.get('competitor_analysis',{}).get('unique_competitors',0)}</div>
                    </div>
                </div>
                <div style=\"margin-top:10px\">
                    <table>
                        <thead>
                            <tr><th>对手</th><th>提及</th><th>威胁等级</th></tr>
                        </thead>
                        <tbody>
                            {''.join(
                                f"<tr><td>{c}</td><td>{d.get('mentions',0)}</td><td>{d.get('threat_level','')}</td></tr>"
                                for c,d in (context_results.get('competitor_analysis',{}).get('competitor_threats',{})).items()
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class=\"section\">
                <h2>📈 市场趋势</h2>
                <ul>
                    {''.join(
                        f"<li><strong>{t.get('trend_name','')}</strong>：{t.get('description','')} (证据：{t.get('evidence','')})</li>" 
                        for t in context_results.get('market_trends',[])
                    )}
                </ul>
            </div>

            <div class=\"section\">
                <h2>🏁 区域NPS分布</h2>
                <div class=\"chart-container\" style=\"height:auto\">
                    <table>
                        <thead><tr><th>区域</th><th>样本</th><th>NPS</th></tr></thead>
                        <tbody>
                            {''.join(
                                f"<tr><td>{r}</td><td>{d.get('count',0)}</td><td>{d.get('nps',0)}</td></tr>" 
                                for r,d in nps_results.get('regional_breakdown',{}).items()
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class=\"section\">
                <h2>📋 质量评估报告</h2>
                <div class=\"insights-grid\">
                    <div class=\"insight-card\">
                        <div class=\"muted\">数据质量等级</div>
                        <div class=\"metric-value\">{quality_report.get('quality_grade', '未知')}</div>
                    </div>
                    <div class=\"insight-card\">
                        <div class=\"muted\">综合质量得分</div>
                        <div class=\"metric-value\">{quality_score:.1f}/10</div>
                    </div>
                </div>
                <div class=\"muted\" style=\"margin-top:12px\">质量指标详情:</div>
                <div>数据完整性: {quality_report.get('data_completeness', 0)*100:.1f}% | 分析深度: {quality_report.get('analysis_depth', 0)*100:.1f}% | 置信水平: {confidence_percent:.1f}%</div>
            </div>
        </div>
        
        <div class=\"footer\">
            <p>🚀 伊利集团NPS智能分析系统 v1.0 | 生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')} | Powered by Multi-Agent AI</p>
            <p>本报告由多智能体系统自动生成，包含定量分析、定性分析和业务智能洞察</p>
        </div>
    </div>
    <script>
            if (typeof Chart === 'undefined') {{
                console.warn('Chart.js 未加载，请将 chart.umd.min.js 放置于 /static/thirdparty/');
            }}
            (function() {{
                const el1 = document.getElementById('npsChart');
                if (typeof Chart !== 'undefined' && el1) {{
                    const ctx1 = el1.getContext('2d');
                    new Chart(ctx1, {{
                        type: 'doughnut',
                        data: {{
                            labels: ['推荐者', '被动者', '批评者'],
                            datasets: [{{
                                data: [{promoters_pct:.1f}, {passives_pct:.1f}, {detractors_pct:.1f}],
                                backgroundColor: ['#4caf50', '#ff9800', '#f44336']
                            }}]
                        }},
                        options: {{ responsive: true, maintainAspectRatio: false, plugins: {{ title: {{ display: true, text: 'NPS 构成' }} }} }}
                    }});
                }} else if (el1) {{
                    el1.insertAdjacentHTML('afterend', '<div class="muted">推荐者: {promoters_pct:.1f}% | 被动者: {passives_pct:.1f}% | 批评者: {detractors_pct:.1f}%</div>');
                }}
            }})();

            (function() {{
                const el2 = document.getElementById('sentimentChart');
                const sentimentData = {qual_results.get('sentiment_overview', {})};
                function getSentimentCount(data, key) {{
                    if (data && data[key]) {{
                        return typeof data[key] === 'object' ? (data[key].count || 0) : data[key];
                    }}
                    return 0;
                }}
                if (typeof Chart !== 'undefined' && el2) {{
                    const ctx2 = el2.getContext('2d');
                    new Chart(ctx2, {{
                        type: 'bar',
                        data: {{ labels: ['正面', '中性', '负面'], datasets: [{{ label: '情感分析', data: [getSentimentCount(sentimentData, 'positive'), getSentimentCount(sentimentData, 'neutral'), getSentimentCount(sentimentData, 'negative')], backgroundColor: ['#4caf50', '#ff9800', '#f44336'] }}] }},
                        options: {{ responsive: true, maintainAspectRatio: false, scales: {{ y: {{ beginAtZero: true }} }} }}
                    }});
                }} else if (el2) {{
                    el2.insertAdjacentHTML('afterend', '<div class="muted">正面: ' + getSentimentCount(sentimentData, 'positive') + ' | 中性: ' + getSentimentCount(sentimentData, 'neutral') + ' | 负面: ' + getSentimentCount(sentimentData, 'negative') + '</div>');
                }}
            }})();
    </script>
</body>
</html>"""
    # No inline embedding; rely on CDN or served static per script_src
    return html_report


def build_html_report(state: Dict[str, Any], final_output: Dict[str, Any]) -> str:
    """Build HTML with robust fallback so report never misses HTML.
    Tries enhanced generator; on failure, returns a minimal static HTML.
    """
    try:
        qr = final_output.get("quality_assessment", {}) if isinstance(final_output, dict) else {}
        return generate_enhanced_html_report(state, qr)
    except Exception:
        # Minimal fallback to guarantee HTML output exists
        nps = state.get("nps_results", {})
        nps_score = nps.get("nps_score", 0)
        total = nps.get("total_responses", len(state.get("clean_responses", [])))
        return f"""
<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='utf-8'/>
  <title>NPS 报告（最简）</title>
  <style>body{{font-family:-apple-system,Arial;max-width:900px;margin:24px auto;padding:0 16px;color:#111}}.card{{border:1px solid #eee;padding:16px;border-radius:8px;margin:12px 0}}</style>
  </head>
<body>
  <h1>NPS 分析报告（最简版）</h1>
  <div class='card'><strong>概览</strong><div>NPS: {nps_score} · 样本量: {total}</div></div>
  <div class='card'><strong>提示</strong><div>完整可视化报告生成失败，已回退到最简版本。请检查日志与数据完整性。</div></div>
</body>
</html>
"""
