"""
HTML Report Generator for NPS V3 Analysis

Generates professional HTML reports from NPSAnalysisResponse data using templates.
Provides dual-format output (JSON + HTML) with comprehensive styling and interactivity.
"""

import logging
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
import uuid
import base64
import asyncio

from ..models.response import NPSAnalysisResponse, NPSMetrics, ExecutiveDashboard
from ..templates.template_manager import TemplateManager, render_executive_dashboard, render_detailed_analysis
from ..state.state_definition import NPSAnalysisState
from ..utils.file_utils import ensure_directory_exists, generate_safe_filename


logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """
    Generates comprehensive HTML reports from NPS V3 analysis results.

    Features:
    - Executive dashboard with KPI metrics and strategic recommendations
    - Detailed multi-agent analysis with tabbed interface
    - Professional styling with TailwindCSS and Chart.js
    - Responsive design for desktop and mobile viewing
    - Print-friendly formatting
    - Dual output format (JSON + HTML)
    """

    def __init__(
        self,
        template_manager: Optional[TemplateManager] = None,
        output_directory: Optional[Union[str, Path]] = None,
        company_name: str = "伊利集团"
    ):
        """
        Initialize HTML report generator.

        Args:
            template_manager: Custom template manager (uses default if None)
            output_directory: Directory for generated reports
            company_name: Company name for branding
        """
        self.template_manager = template_manager or TemplateManager()
        self.output_directory = Path(output_directory) if output_directory else Path("outputs/reports")
        self.company_name = company_name

        # Ensure output directory exists
        ensure_directory_exists(self.output_directory)

        logger.info(f"HTML Report Generator initialized with output directory: {self.output_directory}")

    async def generate_dual_format_report(
        self,
        analysis_state: Union[NPSAnalysisState, NPSAnalysisResponse],
        report_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate dual-format report (JSON + HTML) from analysis results.

        Args:
            analysis_state: Complete analysis state or response
            report_config: Optional configuration for report generation

        Returns:
            Dictionary containing paths to generated files and metadata
        """
        logger.info("Starting dual-format report generation")

        # Convert state to response if needed
        if isinstance(analysis_state, dict):
            response = self._convert_state_to_response(analysis_state)
        else:
            response = analysis_state

        # Apply configuration
        config = self._prepare_report_config(report_config or {})

        # Generate timestamp and unique ID
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_id = f"nps_v3_{timestamp}_{uuid.uuid4().hex[:8]}"

        try:
            # Generate JSON output
            json_path = await self._generate_json_report(response, report_id, config)

            # Generate HTML reports
            html_reports = await self._generate_html_reports(response, report_id, config)

            # Create report package
            report_package = {
                "report_id": report_id,
                "generation_time": datetime.now().isoformat(),
                "company_name": self.company_name,
                "json_report": str(json_path),
                "html_reports": html_reports,
                "metadata": {
                    "total_responses": self._calculate_total_responses(response),
                    "nps_score": response.nps_metrics.nps_score,
                    "confidence_level": response.confidence_assessment.overall_confidence_text,
                    "agent_count": len(response.analysis_insights) + len(response.consulting_recommendations),
                    "report_types": list(html_reports.keys())
                }
            }

            # Save package metadata
            package_path = self.output_directory / f"{report_id}_package.json"
            with open(package_path, 'w', encoding='utf-8') as f:
                json.dump(report_package, f, ensure_ascii=False, indent=2)

            logger.info(f"Dual-format report generation completed: {report_id}")
            return report_package

        except Exception as e:
            logger.error(f"Error generating dual-format report: {e}")
            raise

    async def generate_executive_dashboard(
        self,
        analysis_response: NPSAnalysisResponse,
        report_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Generate executive dashboard HTML report.

        Args:
            analysis_response: Complete NPS analysis results
            report_id: Optional report identifier
            additional_context: Additional template context

        Returns:
            Path to generated HTML file
        """
        logger.info("Generating executive dashboard")

        report_id = report_id or f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filename = f"{report_id}_executive_dashboard.html"
        output_path = self.output_directory / filename

        try:
            # Prepare enhanced context
            context = additional_context or {}
            context.update({
                "report_id": report_id,
                "generation_timestamp": datetime.now().isoformat(),
                "total_agents": len(analysis_response.analysis_insights) + len(analysis_response.consulting_recommendations)
            })

            # Generate HTML content
            html_content = self.template_manager.render_executive_dashboard(
                analysis_response,
                self.company_name,
                context
            )

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Executive dashboard generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating executive dashboard: {e}")
            raise

    async def generate_detailed_analysis(
        self,
        analysis_response: NPSAnalysisResponse,
        report_id: Optional[str] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Path:
        """
        Generate detailed analysis HTML report.

        Args:
            analysis_response: Complete NPS analysis results
            report_id: Optional report identifier
            additional_context: Additional template context

        Returns:
            Path to generated HTML file
        """
        logger.info("Generating detailed analysis report")

        report_id = report_id or f"detail_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        filename = f"{report_id}_detailed_analysis.html"
        output_path = self.output_directory / filename

        try:
            # Prepare enhanced context
            context = additional_context or {}
            context.update({
                "report_id": report_id,
                "generation_timestamp": datetime.now().isoformat(),
                "analysis_depth": "comprehensive",
                "agent_details": self._prepare_agent_details(analysis_response)
            })

            # Generate HTML content
            html_content = self.template_manager.render_detailed_analysis(
                analysis_response,
                self.company_name,
                context
            )

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Detailed analysis report generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating detailed analysis report: {e}")
            raise

    async def generate_custom_report(
        self,
        template_name: str,
        analysis_response: NPSAnalysisResponse,
        custom_context: Dict[str, Any],
        report_id: Optional[str] = None
    ) -> Path:
        """
        Generate custom report using specified template.

        Args:
            template_name: Name of template file
            analysis_response: Complete NPS analysis results
            custom_context: Custom template context
            report_id: Optional report identifier

        Returns:
            Path to generated HTML file
        """
        logger.info(f"Generating custom report with template: {template_name}")

        report_id = report_id or f"custom_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        template_base = Path(template_name).stem
        filename = f"{report_id}_{template_base}.html"
        output_path = self.output_directory / filename

        try:
            # Prepare context with analysis data
            context = {
                "analysis_response": analysis_response,
                "company_name": self.company_name,
                "report_id": report_id,
                "generation_timestamp": datetime.now().isoformat(),
                **custom_context
            }

            # Generate HTML content
            html_content = self.template_manager.render_custom_template(template_name, context)

            # Save to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html_content)

            logger.info(f"Custom report generated: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Error generating custom report: {e}")
            raise

    def create_report_summary(
        self,
        analysis_response: NPSAnalysisResponse,
        generated_files: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create comprehensive report summary.

        Args:
            analysis_response: Complete NPS analysis results
            generated_files: Dictionary of generated file paths

        Returns:
            Report summary dictionary
        """
        summary = {
            "report_metadata": {
                "generation_time": datetime.now().isoformat(),
                "company_name": self.company_name,
                "nps_score": analysis_response.nps_metrics.nps_score,
                "sample_size": self._calculate_total_responses(analysis_response),
                "confidence_level": analysis_response.confidence_assessment.overall_confidence_text
            },
            "analysis_summary": {
                "foundation_insights": len(analysis_response.foundation_insights),
                "analysis_insights": len(analysis_response.analysis_insights),
                "consulting_recommendations": len(analysis_response.consulting_recommendations),
                "risk_alerts": len(analysis_response.executive_dashboard.risk_alerts)
            },
            "generated_files": generated_files,
            "key_findings": self._extract_key_findings(analysis_response),
            "next_steps": self._suggest_next_steps(analysis_response)
        }

        return summary

    # Internal Methods
    async def _generate_json_report(
        self,
        analysis_response: NPSAnalysisResponse,
        report_id: str,
        config: Dict[str, Any]
    ) -> Path:
        """Generate JSON format report."""
        filename = f"{report_id}_analysis_results.json"
        output_path = self.output_directory / filename

        # Convert to JSON-serializable format
        json_data = {
            "report_metadata": {
                "report_id": report_id,
                "generation_time": datetime.now().isoformat(),
                "company_name": self.company_name,
                "version": "3.0"
            },
            "analysis_results": analysis_response.dict()
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)

        logger.info(f"JSON report generated: {output_path}")
        return output_path

    async def _generate_html_reports(
        self,
        analysis_response: NPSAnalysisResponse,
        report_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, str]:
        """Generate all HTML reports."""
        html_reports = {}

        # Generate executive dashboard
        if config.get("include_executive", True):
            exec_path = await self.generate_executive_dashboard(analysis_response, report_id)
            html_reports["executive_dashboard"] = str(exec_path)

        # Generate detailed analysis
        if config.get("include_detailed", True):
            detail_path = await self.generate_detailed_analysis(analysis_response, report_id)
            html_reports["detailed_analysis"] = str(detail_path)

        # Generate custom reports if specified
        for custom_report in config.get("custom_reports", []):
            template_name = custom_report.get("template")
            context = custom_report.get("context", {})

            if template_name:
                custom_path = await self.generate_custom_report(
                    template_name, analysis_response, context, report_id
                )
                html_reports[f"custom_{Path(template_name).stem}"] = str(custom_path)

        return html_reports

    def _convert_state_to_response(self, analysis_state: Dict[str, Any]) -> NPSAnalysisResponse:
        """Convert analysis state dict to NPSAnalysisResponse."""
        # This would implement the conversion logic from state to response
        # For now, create a basic response structure

        response_id = analysis_state.get("workflow_id", f"converted_{uuid.uuid4().hex[:8]}")

        # Extract NPS metrics
        nps_metrics = NPSMetrics(
            nps_score=analysis_state.get("nps_metrics", {}).get("nps_score", 0),
            promoter_count=analysis_state.get("nps_metrics", {}).get("promoter_count", 0),
            passive_count=analysis_state.get("nps_metrics", {}).get("passive_count", 0),
            detractor_count=analysis_state.get("nps_metrics", {}).get("detractor_count", 0),
            sample_size=analysis_state.get("nps_metrics", {}).get("sample_size", 0),
            statistical_significance=analysis_state.get("nps_metrics", {}).get("statistical_significance", False)
        )

        # Create basic response
        return NPSAnalysisResponse(
            response_id=response_id,
            nps_metrics=nps_metrics,
            executive_dashboard=ExecutiveDashboard(
                executive_summary="State converted to response format",
                top_recommendations=[],
                risk_alerts=[],
                key_performance_indicators={}
            )
        )

    def _prepare_report_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and validate report configuration."""
        default_config = {
            "include_executive": True,
            "include_detailed": True,
            "include_charts": True,
            "include_raw_data": False,
            "custom_reports": [],
            "styling": {
                "theme": "professional",
                "color_scheme": "yili_brand",
                "font_size": "standard"
            }
        }

        # Merge with provided config
        merged_config = {**default_config, **config}

        # Validate configuration
        if "styling" in config:
            merged_config["styling"].update(config["styling"])

        return merged_config

    def _calculate_total_responses(self, analysis_response: NPSAnalysisResponse) -> int:
        """Calculate total number of responses."""
        metrics = analysis_response.nps_metrics
        return metrics.promoter_count + metrics.passive_count + metrics.detractor_count

    def _prepare_agent_details(self, analysis_response: NPSAnalysisResponse) -> Dict[str, Any]:
        """Prepare detailed agent information for templates."""
        return {
            "foundation_agents": len(analysis_response.foundation_insights),
            "analysis_agents": len(analysis_response.analysis_insights),
            "consulting_agents": len(analysis_response.consulting_recommendations),
            "total_execution_time": "N/A",  # Would come from workflow timing
            "success_rate": "100%"  # Would be calculated from actual execution
        }

    def _extract_key_findings(self, analysis_response: NPSAnalysisResponse) -> List[str]:
        """Extract key findings from analysis results."""
        findings = []

        # Add NPS summary
        nps_score = analysis_response.nps_metrics.nps_score
        if nps_score >= 50:
            findings.append(f"客户满意度优秀，NPS得分达到 {nps_score}")
        elif nps_score >= 0:
            findings.append(f"客户满意度良好，NPS得分为 {nps_score}")
        else:
            findings.append(f"客户满意度待提升，NPS得分为 {nps_score}")

        # Add top insights
        for insight in analysis_response.analysis_insights[:3]:
            findings.append(f"{insight.category}: {insight.summary}")

        # Add top recommendations
        for rec in analysis_response.consulting_recommendations[:2]:
            findings.append(f"战略建议: {rec.title}")

        return findings

    def _suggest_next_steps(self, analysis_response: NPSAnalysisResponse) -> List[str]:
        """Suggest next steps based on analysis results."""
        next_steps = []

        nps_score = analysis_response.nps_metrics.nps_score

        if nps_score < 0:
            next_steps.extend([
                "立即制定客户体验改进计划",
                "分析贬损者反馈，识别核心问题",
                "实施紧急客户挽回措施"
            ])
        elif nps_score < 30:
            next_steps.extend([
                "深入分析中性客户转化机会",
                "优化产品和服务质量",
                "加强客户沟通和反馈收集"
            ])
        else:
            next_steps.extend([
                "维持现有优势，持续监控",
                "探索推荐者增长机会",
                "建立客户忠诚度计划"
            ])

        # Add recommendation-based next steps
        if analysis_response.consulting_recommendations:
            top_rec = analysis_response.consulting_recommendations[0]
            next_steps.append(f"优先实施: {top_rec.title}")

        return next_steps


# Convenience functions for direct usage
async def generate_comprehensive_report(
    analysis_state: Union[NPSAnalysisState, NPSAnalysisResponse],
    output_directory: Optional[Union[str, Path]] = None,
    company_name: str = "伊利集团"
) -> Dict[str, Any]:
    """
    Generate comprehensive dual-format report.

    Args:
        analysis_state: Complete analysis state or response
        output_directory: Output directory for reports
        company_name: Company name for branding

    Returns:
        Report package with generated file paths and metadata
    """
    generator = HTMLReportGenerator(
        output_directory=output_directory,
        company_name=company_name
    )

    return await generator.generate_dual_format_report(analysis_state)


async def generate_executive_report_only(
    analysis_response: NPSAnalysisResponse,
    output_path: Optional[Union[str, Path]] = None,
    company_name: str = "伊利集团"
) -> Path:
    """
    Generate executive dashboard report only.

    Args:
        analysis_response: Complete NPS analysis results
        output_path: Optional output file path
        company_name: Company name for branding

    Returns:
        Path to generated HTML file
    """
    if output_path:
        output_dir = Path(output_path).parent
        generator = HTMLReportGenerator(output_directory=output_dir, company_name=company_name)
        return await generator.generate_executive_dashboard(analysis_response)
    else:
        generator = HTMLReportGenerator(company_name=company_name)
        return await generator.generate_executive_dashboard(analysis_response)


# Report validation and quality checks
def validate_report_quality(html_content: str) -> Dict[str, Any]:
    """
    Validate HTML report quality and completeness.

    Args:
        html_content: HTML content to validate

    Returns:
        Validation results with scores and recommendations
    """
    validation_results = {
        "overall_score": 0,
        "checks": {},
        "recommendations": []
    }

    # Check HTML structure
    has_title = "<title>" in html_content
    has_header = "<header>" in html_content
    has_charts = "Chart.js" in html_content or "canvas" in html_content
    has_responsive = "viewport" in html_content

    validation_results["checks"] = {
        "html_structure": has_title and has_header,
        "interactive_elements": has_charts,
        "responsive_design": has_responsive,
        "chinese_content": "伊利" in html_content or "NPS" in html_content,
        "styling": "tailwindcss" in html_content or "style" in html_content
    }

    # Calculate overall score
    score = sum(validation_results["checks"].values()) / len(validation_results["checks"]) * 100
    validation_results["overall_score"] = round(score, 1)

    # Add recommendations based on checks
    if not validation_results["checks"]["interactive_elements"]:
        validation_results["recommendations"].append("添加图表增强数据可视化效果")

    if not validation_results["checks"]["responsive_design"]:
        validation_results["recommendations"].append("优化移动端显示效果")

    if score < 80:
        validation_results["recommendations"].append("提升整体报告质量和完整性")

    return validation_results