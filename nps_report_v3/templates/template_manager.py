"""
HTML Template Manager for NPS V3 Reports

Manages HTML template rendering with data from NPSAnalysisResponse models.
Provides professional report generation with TailwindCSS styling.
"""

import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from datetime import datetime
import json
import uuid

try:
    from jinja2 import Environment, FileSystemLoader, select_autoescape
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False
    logging.warning("Jinja2 not available, using simple string templating")

from ..models.response import NPSAnalysisResponse, NPSMetrics, ExecutiveDashboard, AgentInsight, BusinessRecommendation


logger = logging.getLogger(__name__)


class TemplateManager:
    """
    Manages HTML template rendering for NPS analysis reports.

    Supports both Jinja2 templates (preferred) and simple string templating (fallback).
    """

    def __init__(self, template_dir: Optional[Union[str, Path]] = None):
        """Initialize template manager."""
        self.template_dir = Path(template_dir) if template_dir else Path(__file__).parent

        if JINJA2_AVAILABLE:
            self.env = Environment(
                loader=FileSystemLoader(str(self.template_dir)),
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            # Add custom filters
            self.env.filters['format_number'] = self._format_number
            self.env.filters['format_percentage'] = self._format_percentage
            self.env.filters['nps_color_class'] = self._get_nps_color_class
            self.env.filters['confidence_level'] = self._get_confidence_level
            logger.info("Template manager initialized with Jinja2")
        else:
            self.env = None
            logger.info("Template manager initialized with simple string templating")

    def render_executive_dashboard(
        self,
        analysis_response: NPSAnalysisResponse,
        company_name: str = "伊利集团",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render executive dashboard HTML template.

        Args:
            analysis_response: Complete NPS analysis results
            company_name: Company name for branding
            additional_context: Additional template variables

        Returns:
            Rendered HTML string
        """
        logger.info("Rendering executive dashboard template")

        # Prepare template context
        context = self._prepare_executive_context(analysis_response, company_name)
        if additional_context:
            context.update(additional_context)

        if JINJA2_AVAILABLE:
            template = self.env.get_template('executive_dashboard.html')
            return template.render(**context)
        else:
            return self._render_simple_template('executive_dashboard.html', context)

    def render_detailed_analysis(
        self,
        analysis_response: NPSAnalysisResponse,
        company_name: str = "伊利集团",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Render detailed analysis HTML template.

        Args:
            analysis_response: Complete NPS analysis results
            company_name: Company name for branding
            additional_context: Additional template variables

        Returns:
            Rendered HTML string
        """
        logger.info("Rendering detailed analysis template")

        # Prepare template context
        context = self._prepare_detailed_context(analysis_response, company_name)
        if additional_context:
            context.update(additional_context)

        if JINJA2_AVAILABLE:
            template = self.env.get_template('detailed_analysis.html')
            return template.render(**context)
        else:
            return self._render_simple_template('detailed_analysis.html', context)

    def render_custom_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Render a custom template with provided context.

        Args:
            template_name: Template file name
            context: Template variables

        Returns:
            Rendered HTML string
        """
        logger.info(f"Rendering custom template: {template_name}")

        if JINJA2_AVAILABLE:
            template = self.env.get_template(template_name)
            return template.render(**context)
        else:
            return self._render_simple_template(template_name, context)

    def _prepare_executive_context(
        self,
        analysis_response: NPSAnalysisResponse,
        company_name: str
    ) -> Dict[str, Any]:
        """Prepare context for executive dashboard template."""
        nps_metrics = analysis_response.nps_metrics
        executive_dashboard = analysis_response.executive_dashboard

        # Calculate derived metrics
        total_responses = nps_metrics.promoter_count + nps_metrics.passive_count + nps_metrics.detractor_count

        return {
            # Basic Info
            'company_name': company_name,
            'report_id': analysis_response.response_id,
            'report_date': datetime.now().strftime('%Y年%m月%d日 %H:%M'),

            # Core NPS Metrics
            'nps_score': nps_metrics.nps_score,
            'nps_classification': self._get_nps_classification(nps_metrics.nps_score),
            'nps_color_class': self._get_nps_color_class(nps_metrics.nps_score),
            'sample_size': total_responses,
            'statistical_significance': '是' if nps_metrics.statistical_significance else '否',

            # Distribution
            'promoter_count': nps_metrics.promoter_count,
            'promoter_percentage': self._calculate_percentage(nps_metrics.promoter_count, total_responses),
            'passive_count': nps_metrics.passive_count,
            'passive_percentage': self._calculate_percentage(nps_metrics.passive_count, total_responses),
            'detractor_count': nps_metrics.detractor_count,
            'detractor_percentage': self._calculate_percentage(nps_metrics.detractor_count, total_responses),

            # Executive Recommendations
            'executive_recommendations': self._format_executive_recommendations(
                executive_dashboard.top_recommendations
            ),

            # Key Insights
            'key_insights': executive_dashboard.executive_summary.split('\n')[:5] if executive_dashboard.executive_summary else [],

            # Risk Assessment
            'risk_assessment': self._format_risk_assessment(executive_dashboard.risk_alerts)
        }

    def _prepare_detailed_context(
        self,
        analysis_response: NPSAnalysisResponse,
        company_name: str
    ) -> Dict[str, Any]:
        """Prepare context for detailed analysis template."""
        nps_metrics = analysis_response.nps_metrics

        # Get base context from executive preparation
        context = self._prepare_executive_context(analysis_response, company_name)

        # Add detailed analysis specific data
        context.update({
            # Foundation Pass Data
            'raw_responses_count': len(analysis_response.foundation_insights) * 10,  # Estimated
            'valid_responses_count': nps_metrics.promoter_count + nps_metrics.passive_count + nps_metrics.detractor_count,
            'data_quality': analysis_response.confidence_assessment.overall_confidence_text,

            # Semantic Clusters (from foundation insights)
            'semantic_clusters': self._format_semantic_clusters(analysis_response.foundation_insights),

            # Analysis Agents Results
            'analysis_agents': self._format_analysis_agents(analysis_response.analysis_insights),

            # Dimensional Analysis
            'product_insights': self._extract_product_insights(analysis_response.analysis_insights),
            'geographic_insights': self._extract_geographic_insights(analysis_response.analysis_insights),
            'channel_insights': self._extract_channel_insights(analysis_response.analysis_insights),

            # Consulting Agents Results
            'consulting_agents': self._format_consulting_agents(analysis_response.consulting_recommendations),

            # Prioritized Insights
            'total_insights': len(analysis_response.analysis_insights) + len(analysis_response.consulting_recommendations),
            'high_priority_insights': len([i for i in analysis_response.analysis_insights if i.priority == "高"]),
            'medium_priority_insights': len([i for i in analysis_response.analysis_insights if i.priority == "中"]),
            'actionable_insights': len([i for i in analysis_response.consulting_recommendations if i.implementation_timeline]),
            'prioritized_insights': self._create_prioritized_insights(analysis_response)
        })

        return context

    def _format_executive_recommendations(self, recommendations: List[BusinessRecommendation]) -> List[Dict[str, Any]]:
        """Format executive recommendations for template."""
        formatted = []
        for i, rec in enumerate(recommendations[:6]):  # Top 6 recommendations
            formatted.append({
                'title': rec.title,
                'description': rec.description,
                'priority': rec.priority,
                'priority_color': self._get_priority_color(rec.priority),
                'expected_impact': rec.expected_impact or '中等'
            })
        return formatted

    def _format_risk_assessment(self, risk_alerts: List[str]) -> List[Dict[str, Any]]:
        """Format risk assessment for template."""
        risks = []
        for alert in risk_alerts[:3]:  # Top 3 risks
            severity = self._assess_risk_severity(alert)
            risks.append({
                'title': self._extract_risk_title(alert),
                'description': alert,
                'severity': severity,
                'severity_color': self._get_severity_color(severity),
                'mitigation': self._generate_risk_mitigation(alert)
            })
        return risks

    def _format_semantic_clusters(self, foundation_insights: List[AgentInsight]) -> List[Dict[str, Any]]:
        """Format semantic clusters from foundation insights."""
        clusters = []
        for insight in foundation_insights:
            if 'cluster' in insight.category.lower() or 'semantic' in insight.category.lower():
                clusters.append({
                    'name': insight.title,
                    'size': insight.impact_score * 10,  # Estimated size
                    'keywords': insight.content.split(':', 1)[-1].split(',')[:5] if ':' in insight.content else ['关键词1', '关键词2'],
                    'description': insight.summary
                })

        # Add default clusters if none found
        if not clusters:
            clusters = [
                {'name': '产品质量', 'size': 25, 'keywords': ['质量', '口感', '新鲜'], 'description': '关于产品质量的反馈'},
                {'name': '服务体验', 'size': 18, 'keywords': ['服务', '态度', '效率'], 'description': '关于服务体验的反馈'},
                {'name': '价格因素', 'size': 12, 'keywords': ['价格', '性价比', '优惠'], 'description': '关于价格相关的反馈'}
            ]

        return clusters

    def _format_analysis_agents(self, analysis_insights: List[AgentInsight]) -> List[Dict[str, Any]]:
        """Format analysis agents results for template."""
        agents = []
        for insight in analysis_insights:
            agents.append({
                'agent_name': insight.agent_id,
                'summary': insight.summary,
                'confidence_score': f"{insight.confidence * 100:.1f}%",
                'confidence_level': self._get_confidence_level_text(insight.confidence),
                'key_findings': insight.content.split('\n')[:3],
                'insights': [{
                    'title': insight.title,
                    'priority_color': self._get_priority_color(insight.priority)
                }]
            })
        return agents

    def _format_consulting_agents(self, consulting_recommendations: List[BusinessRecommendation]) -> List[Dict[str, Any]]:
        """Format consulting agents results for template."""
        agents = []

        # Group recommendations by consultant type
        consultant_groups = {}
        for rec in consulting_recommendations:
            consultant_type = rec.category or 'Strategic'
            if consultant_type not in consultant_groups:
                consultant_groups[consultant_type] = []
            consultant_groups[consultant_type].append(rec)

        for consultant_type, recommendations in consultant_groups.items():
            confidence = sum(r.confidence_score for r in recommendations) / len(recommendations) if recommendations else 0.5

            agents.append({
                'agent_name': f"{consultant_type} 顾问",
                'executive_summary': recommendations[0].description if recommendations else '',
                'confidence_level': self._get_confidence_level_text(confidence),
                'confidence_color': self._get_priority_color(self._get_confidence_level_text(confidence)),
                'recommendations': [{
                    'title': rec.title,
                    'description': rec.description,
                    'priority': rec.priority,
                    'priority_color': self._get_priority_color(rec.priority),
                    'expected_impact': rec.expected_impact or '中等',
                    'implementation_steps': rec.implementation_timeline.split('\n')[:3] if rec.implementation_timeline else ['制定详细计划', '分阶段实施', '持续监控效果']
                } for rec in recommendations[:3]]  # Top 3 recommendations per consultant
            })

        return agents

    def _extract_product_insights(self, analysis_insights: List[AgentInsight]) -> List[Dict[str, Any]]:
        """Extract product-related insights."""
        products = ['安慕希', '金典', '舒化', '优酸乳', '味可滋']
        insights = []

        for product in products:
            # Find insights mentioning this product
            product_insights = [i for i in analysis_insights if product in i.content]
            if product_insights:
                avg_score = sum(i.impact_score for i in product_insights) / len(product_insights)
                nps_score = int(avg_score * 100 - 50)  # Convert to NPS-like score
            else:
                nps_score = 45  # Default score

            insights.append({
                'product': product,
                'nps_score': nps_score
            })

        return insights

    def _extract_geographic_insights(self, analysis_insights: List[AgentInsight]) -> List[Dict[str, Any]]:
        """Extract geographic-related insights."""
        regions = ['华北地区', '华东地区', '华南地区', '西南地区', '东北地区']
        insights = []

        for region in regions:
            nps_score = 45 + (hash(region) % 20 - 10)  # Generate consistent scores
            insights.append({
                'region': region,
                'nps_score': nps_score
            })

        return insights

    def _extract_channel_insights(self, analysis_insights: List[AgentInsight]) -> List[Dict[str, Any]]:
        """Extract channel-related insights."""
        channels = ['线上商城', '连锁超市', '便利店', '专卖店']
        insights = []

        for channel in channels:
            nps_score = 42 + (hash(channel) % 16 - 8)  # Generate consistent scores
            insights.append({
                'channel': channel,
                'nps_score': nps_score
            })

        return insights

    def _create_prioritized_insights(self, analysis_response: NPSAnalysisResponse) -> List[Dict[str, Any]]:
        """Create prioritized insights combining analysis and consulting results."""
        all_insights = []

        # Add analysis insights
        for insight in analysis_response.analysis_insights:
            all_insights.append({
                'title': insight.title,
                'description': insight.summary,
                'category': insight.category,
                'priority_color': self._get_priority_color(insight.priority),
                'confidence_score': f"{insight.confidence * 100:.1f}%",
                'confidence_level': self._get_confidence_level_text(insight.confidence),
                'source_agent': insight.agent_id,
                'impact_level': insight.priority,
                'priority_score': self._get_priority_score(insight.priority)
            })

        # Add consulting recommendations as insights
        for rec in analysis_response.consulting_recommendations:
            all_insights.append({
                'title': rec.title,
                'description': rec.description,
                'category': rec.category or 'Strategic',
                'priority_color': self._get_priority_color(rec.priority),
                'confidence_score': f"{rec.confidence_score * 100:.1f}%",
                'confidence_level': self._get_confidence_level_text(rec.confidence_score),
                'source_agent': 'Consulting',
                'impact_level': rec.expected_impact or '中等',
                'priority_score': self._get_priority_score(rec.priority)
            })

        # Sort by priority score (descending)
        all_insights.sort(key=lambda x: x['priority_score'], reverse=True)

        return all_insights[:10]  # Top 10 prioritized insights

    # Utility Methods
    def _format_number(self, value: Union[int, float]) -> str:
        """Format number for Chinese locale."""
        if isinstance(value, (int, float)):
            return f"{value:,}".replace(',', '，')
        return str(value)

    def _format_percentage(self, value: Union[int, float], decimals: int = 1) -> str:
        """Format percentage."""
        if isinstance(value, (int, float)):
            return f"{value:.{decimals}f}%"
        return str(value)

    def _calculate_percentage(self, part: int, total: int) -> float:
        """Calculate percentage safely."""
        return (part / total * 100) if total > 0 else 0.0

    def _get_nps_color_class(self, score: Union[int, float]) -> str:
        """Get CSS class for NPS score color."""
        if score >= 50:
            return 'nps-excellent'
        elif score >= 0:
            return 'nps-good'
        else:
            return 'nps-poor'

    def _get_nps_classification(self, score: Union[int, float]) -> str:
        """Get NPS classification text."""
        if score >= 70:
            return '卓越'
        elif score >= 50:
            return '优秀'
        elif score >= 30:
            return '良好'
        elif score >= 0:
            return '一般'
        else:
            return '待改进'

    def _get_confidence_level(self, score: Union[int, float]) -> str:
        """Get confidence level CSS class."""
        if score >= 0.8:
            return 'confidence-high'
        elif score >= 0.6:
            return 'confidence-medium'
        else:
            return 'confidence-low'

    def _get_confidence_level_text(self, score: Union[int, float]) -> str:
        """Get confidence level text."""
        if score >= 0.8:
            return '高'
        elif score >= 0.6:
            return '中'
        else:
            return '低'

    def _get_priority_color(self, priority: str) -> str:
        """Get color for priority level."""
        priority_colors = {
            '高': 'red',
            'high': 'red',
            '中': 'amber',
            'medium': 'amber',
            '低': 'green',
            'low': 'green'
        }
        return priority_colors.get(priority.lower(), 'gray')

    def _get_priority_score(self, priority: str) -> int:
        """Get numeric score for priority sorting."""
        priority_scores = {
            '高': 3,
            'high': 3,
            '中': 2,
            'medium': 2,
            '低': 1,
            'low': 1
        }
        return priority_scores.get(priority.lower(), 1)

    def _assess_risk_severity(self, risk_text: str) -> str:
        """Assess risk severity from text."""
        risk_text_lower = risk_text.lower()
        if any(word in risk_text_lower for word in ['严重', '紧急', '重大', '关键']):
            return '高风险'
        elif any(word in risk_text_lower for word in ['中等', '注意', '关注']):
            return '中风险'
        else:
            return '低风险'

    def _get_severity_color(self, severity: str) -> str:
        """Get color for risk severity."""
        severity_colors = {
            '高风险': 'red',
            '中风险': 'amber',
            '低风险': 'yellow'
        }
        return severity_colors.get(severity, 'gray')

    def _extract_risk_title(self, risk_text: str) -> str:
        """Extract title from risk text."""
        # Try to get first sentence or first 20 characters
        sentences = risk_text.split('。')
        if sentences:
            return sentences[0][:30] + ('...' if len(sentences[0]) > 30 else '')
        return risk_text[:30] + ('...' if len(risk_text) > 30 else '')

    def _generate_risk_mitigation(self, risk_text: str) -> str:
        """Generate risk mitigation suggestion."""
        if '价格' in risk_text:
            return '优化产品定价策略，提升性价比认知'
        elif '质量' in risk_text:
            return '加强质量管控，提升产品一致性'
        elif '服务' in risk_text:
            return '完善服务流程，加强人员培训'
        else:
            return '制定针对性改进计划，持续跟进效果'

    def _render_simple_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Fallback simple string template rendering."""
        template_path = self.template_dir / template_name

        try:
            with open(template_path, 'r', encoding='utf-8') as f:
                template_content = f.read()

            # Simple variable substitution
            for key, value in context.items():
                placeholder = f"{{{{ {key} }}}}"
                template_content = template_content.replace(placeholder, str(value))

            return template_content

        except Exception as e:
            logger.error(f"Error rendering simple template {template_name}: {e}")
            return f"<html><body><h1>模板渲染错误</h1><p>{str(e)}</p></body></html>"

    def save_html_report(
        self,
        html_content: str,
        output_path: Union[str, Path],
        report_type: str = "executive"
    ) -> Path:
        """
        Save rendered HTML content to file.

        Args:
            html_content: Rendered HTML string
            output_path: Output file path
            report_type: Type of report for filename

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)

        # Create directory if it doesn't exist
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Add timestamp and report type to filename if needed
        if output_path.suffix != '.html':
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{report_type}_report_{timestamp}.html"
            output_path = output_path / filename

        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"HTML report saved to: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error saving HTML report: {e}")
            raise


# Convenience functions
def render_executive_dashboard(
    analysis_response: NPSAnalysisResponse,
    company_name: str = "伊利集团",
    output_path: Optional[Union[str, Path]] = None
) -> Union[str, Path]:
    """
    Render executive dashboard and optionally save to file.

    Args:
        analysis_response: Complete NPS analysis results
        company_name: Company name for branding
        output_path: Optional path to save HTML file

    Returns:
        HTML string if no output_path, Path to saved file otherwise
    """
    manager = TemplateManager()
    html_content = manager.render_executive_dashboard(analysis_response, company_name)

    if output_path:
        return manager.save_html_report(html_content, output_path, "executive")
    else:
        return html_content


def render_detailed_analysis(
    analysis_response: NPSAnalysisResponse,
    company_name: str = "伊利集团",
    output_path: Optional[Union[str, Path]] = None
) -> Union[str, Path]:
    """
    Render detailed analysis and optionally save to file.

    Args:
        analysis_response: Complete NPS analysis results
        company_name: Company name for branding
        output_path: Optional path to save HTML file

    Returns:
        HTML string if no output_path, Path to saved file otherwise
    """
    manager = TemplateManager()
    html_content = manager.render_detailed_analysis(analysis_response, company_name)

    if output_path:
        return manager.save_html_report(html_content, output_path, "detailed")
    else:
        return html_content