"""
Dual Output Generator for NPS V3 Analysis System

Orchestrates generation of both JSON and HTML outputs from NPS analysis results.
Provides comprehensive reporting with professional formatting and data validation.
"""

import logging
import asyncio
import json
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
from datetime import datetime
import uuid

from ..models.response import (
    NPSAnalysisResponse,
    NPSMetrics,
    ConfidenceAssessment,
    ExecutiveDashboard,
    AgentInsight,
    BusinessRecommendation
)
from ..state.state_definition import NPSAnalysisState
from ..generators.html_report_generator import HTMLReportGenerator
from ..utils.file_utils import ensure_directory_exists, safe_write_file, generate_safe_filename
from ..config import get_settings


logger = logging.getLogger(__name__)


class DualOutputGenerator:
    """
    Generates dual-format outputs (JSON + HTML) from NPS V3 analysis results.

    Provides comprehensive report generation with:
    - Structured JSON data for system integration
    - Professional HTML reports for human consumption
    - Executive dashboards and detailed analysis views
    - Automated file management and organization
    - Quality validation and error handling
    """

    def __init__(
        self,
        output_directory: Optional[Union[str, Path]] = None,
        company_name: str = "伊利集团",
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize dual output generator.

        Args:
            output_directory: Base directory for all outputs
            company_name: Company name for branding
            config: Optional configuration overrides
        """
        self.settings = get_settings()
        self.output_directory = Path(output_directory or "outputs")
        self.company_name = company_name
        self.config = self._prepare_config(config or {})

        # Initialize output directories
        self.json_dir = self.output_directory / "json"
        self.html_dir = self.output_directory / "html"
        self.reports_dir = self.output_directory / "reports"
        self.assets_dir = self.output_directory / "assets"

        # Create directory structure
        self._create_directory_structure()

        # Initialize HTML generator
        self.html_generator = HTMLReportGenerator(
            output_directory=self.html_dir,
            company_name=self.company_name
        )

        logger.info(f"Dual Output Generator initialized with directory: {self.output_directory}")

    async def generate_complete_report_package(
        self,
        analysis_result: Union[NPSAnalysisState, NPSAnalysisResponse],
        report_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate complete report package with all output formats.

        Args:
            analysis_result: Complete analysis results
            report_options: Optional report generation options

        Returns:
            Report package metadata with file paths and summaries
        """
        logger.info("Starting complete report package generation")

        # Generate unique report ID and timestamp
        report_id = self._generate_report_id()
        generation_time = datetime.now()

        try:
            # Convert to response format if needed
            analysis_response = self._ensure_response_format(analysis_result)

            # Validate analysis results
            validation_results = self._validate_analysis_results(analysis_response)
            if not validation_results["is_valid"]:
                logger.warning(f"Analysis validation issues: {validation_results['issues']}")

            # Prepare report options
            options = self._merge_report_options(report_options or {})

            # Generate all output formats concurrently
            tasks = []

            # JSON outputs
            if options.get("generate_json", True):
                tasks.append(self._generate_json_outputs(analysis_response, report_id, options))

            # HTML outputs
            if options.get("generate_html", True):
                tasks.append(self._generate_html_outputs(analysis_response, report_id, options))

            # Execute generation tasks
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            json_results = None
            html_results = None

            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    logger.error(f"Generation task {i} failed: {result}")
                    continue

                if "json" in str(result):
                    json_results = result
                elif "html" in str(result):
                    html_results = result

            # Create comprehensive report package
            report_package = await self._create_report_package(
                analysis_response,
                report_id,
                generation_time,
                json_results,
                html_results,
                validation_results,
                options
            )

            # Save package metadata
            package_path = await self._save_package_metadata(report_package, report_id)

            # Generate summary report
            if options.get("generate_summary", True):
                await self._generate_summary_report(report_package, report_id)

            logger.info(f"Complete report package generated successfully: {report_id}")
            return report_package

        except Exception as e:
            logger.error(f"Error generating complete report package: {e}")
            raise

    async def generate_json_only(
        self,
        analysis_result: Union[NPSAnalysisState, NPSAnalysisResponse],
        output_path: Optional[Union[str, Path]] = None,
        include_metadata: bool = True
    ) -> Path:
        """
        Generate JSON-only output.

        Args:
            analysis_result: Analysis results to export
            output_path: Optional specific output path
            include_metadata: Whether to include generation metadata

        Returns:
            Path to generated JSON file
        """
        logger.info("Generating JSON-only output")

        analysis_response = self._ensure_response_format(analysis_result)
        report_id = self._generate_report_id()

        # Determine output path
        if output_path:
            json_path = Path(output_path)
        else:
            filename = f"{report_id}_analysis_results.json"
            json_path = self.json_dir / filename

        # Prepare JSON data
        json_data = {
            "analysis_results": analysis_response.model_dump(mode='json'),
        }

        if include_metadata:
            json_data["metadata"] = {
                "report_id": report_id,
                "generation_time": datetime.now().isoformat(),
                "generator_version": "3.0",
                "company_name": self.company_name,
                "output_type": "json_only"
            }

        # Write JSON file
        json_path = await asyncio.to_thread(safe_write_file, json_path, json_data)

        logger.info(f"JSON output generated: {json_path}")
        return json_path

    async def generate_html_only(
        self,
        analysis_result: Union[NPSAnalysisState, NPSAnalysisResponse],
        report_type: str = "executive",
        output_path: Optional[Union[str, Path]] = None
    ) -> Path:
        """
        Generate HTML-only output.

        Args:
            analysis_result: Analysis results to export
            report_type: Type of HTML report ("executive" or "detailed")
            output_path: Optional specific output path

        Returns:
            Path to generated HTML file
        """
        logger.info(f"Generating {report_type} HTML-only output")

        analysis_response = self._ensure_response_format(analysis_result)

        if report_type == "executive":
            return await self.html_generator.generate_executive_dashboard(analysis_response)
        elif report_type == "detailed":
            return await self.html_generator.generate_detailed_analysis(analysis_response)
        else:
            raise ValueError(f"Unsupported report type: {report_type}")

    async def generate_custom_output(
        self,
        analysis_result: Union[NPSAnalysisState, NPSAnalysisResponse],
        template_config: Dict[str, Any],
        output_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate custom output with specific templates and configurations.

        Args:
            analysis_result: Analysis results to export
            template_config: Template configuration
            output_config: Output configuration

        Returns:
            Custom output results
        """
        logger.info("Generating custom output")

        analysis_response = self._ensure_response_format(analysis_result)
        report_id = self._generate_report_id()

        custom_results = {
            "report_id": report_id,
            "generation_time": datetime.now().isoformat(),
            "outputs": {}
        }

        # Process custom templates
        for template_name, template_settings in template_config.items():
            try:
                output_path = await self.html_generator.generate_custom_report(
                    template_name,
                    analysis_response,
                    template_settings.get("context", {}),
                    report_id
                )
                custom_results["outputs"][template_name] = str(output_path)

            except Exception as e:
                logger.error(f"Error generating custom template {template_name}: {e}")
                custom_results["outputs"][template_name] = f"Error: {str(e)}"

        # Process custom JSON outputs if specified
        if output_config.get("custom_json"):
            json_config = output_config["custom_json"]
            custom_json_path = await self._generate_custom_json(
                analysis_response,
                json_config,
                report_id
            )
            custom_results["outputs"]["custom_json"] = str(custom_json_path)

        logger.info(f"Custom output generation completed: {report_id}")
        return custom_results

    # Internal Methods

    async def _generate_json_outputs(
        self,
        analysis_response: NPSAnalysisResponse,
        report_id: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate all JSON outputs."""
        json_outputs = {}

        # Main analysis results
        main_json_path = self.json_dir / f"{report_id}_analysis_results.json"
        json_data = {
            "report_metadata": {
                "report_id": report_id,
                "generation_time": datetime.now().isoformat(),
                "generator_version": "3.0",
                "company_name": self.company_name
            },
            "analysis_results": analysis_response.model_dump(mode='json')
        }

        main_json_path = await asyncio.to_thread(safe_write_file, main_json_path, json_data)
        json_outputs["main_results"] = str(main_json_path)

        # Executive summary JSON (lightweight)
        if options.get("generate_executive_json", True):
            executive_json_path = self.json_dir / f"{report_id}_executive_summary.json"
            executive_data = {
                "report_id": report_id,
                "nps_metrics": analysis_response.nps_metrics.model_dump(mode='json'),
                "executive_dashboard": analysis_response.executive_dashboard.model_dump(mode='json'),
                "confidence_assessment": analysis_response.confidence_assessment.model_dump(mode='json')
            }

            executive_json_path = await asyncio.to_thread(safe_write_file, executive_json_path, executive_data)
            json_outputs["executive_summary"] = str(executive_json_path)

        # Raw insights JSON (for data analysis)
        if options.get("generate_raw_insights", False):
            insights_json_path = self.json_dir / f"{report_id}_raw_insights.json"
            insights_data = {
                "foundation_insights": [insight.model_dump(mode='json') for insight in analysis_response.foundation_insights],
                "analysis_insights": [insight.model_dump(mode='json') for insight in analysis_response.analysis_insights],
                "consulting_recommendations": [rec.model_dump(mode='json') for rec in analysis_response.consulting_recommendations]
            }

            insights_json_path = await asyncio.to_thread(safe_write_file, insights_json_path, insights_data)
            json_outputs["raw_insights"] = str(insights_json_path)

        return json_outputs

    async def _generate_html_outputs(
        self,
        analysis_response: NPSAnalysisResponse,
        report_id: str,
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate all HTML outputs."""
        html_outputs = {}

        # Executive dashboard
        if options.get("generate_executive_html", True):
            exec_path = await self.html_generator.generate_executive_dashboard(
                analysis_response, report_id
            )
            html_outputs["executive_dashboard"] = str(exec_path)

        # Detailed analysis
        if options.get("generate_detailed_html", True):
            detail_path = await self.html_generator.generate_detailed_analysis(
                analysis_response, report_id
            )
            html_outputs["detailed_analysis"] = str(detail_path)

        # Custom templates
        for custom_template in options.get("custom_templates", []):
            template_name = custom_template.get("name")
            template_context = custom_template.get("context", {})

            if template_name:
                try:
                    custom_path = await self.html_generator.generate_custom_report(
                        template_name,
                        analysis_response,
                        template_context,
                        report_id
                    )
                    html_outputs[f"custom_{Path(template_name).stem}"] = str(custom_path)

                except Exception as e:
                    logger.error(f"Error generating custom HTML template {template_name}: {e}")

        return html_outputs

    async def _create_report_package(
        self,
        analysis_response: NPSAnalysisResponse,
        report_id: str,
        generation_time: datetime,
        json_results: Optional[Dict[str, Any]],
        html_results: Optional[Dict[str, Any]],
        validation_results: Dict[str, Any],
        options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive report package metadata."""

        # Calculate metrics
        total_responses = (analysis_response.nps_metrics.promoter_count +
                          analysis_response.nps_metrics.passive_count +
                          analysis_response.nps_metrics.detractor_count)

        package = {
            "report_id": report_id,
            "package_info": {
                "report_id": report_id,
                "generation_time": generation_time.isoformat(),
                "generator_version": "3.0",
                "company_name": self.company_name,
                "package_type": "dual_output"
            },
            "analysis_summary": {
                "nps_score": analysis_response.nps_metrics.nps_score,
                "sample_size": total_responses,
                "statistical_significance": analysis_response.nps_metrics.statistical_significance,
                "confidence_level": analysis_response.confidence_assessment.overall_confidence_text,
                "total_insights": len(analysis_response.analysis_insights),
                "total_recommendations": len(analysis_response.consulting_recommendations),
                "risk_alerts": len(analysis_response.executive_dashboard.risk_alerts)
            },
            "generated_outputs": {
                "json_files": json_results or {},
                "html_files": html_results or {},
                "total_files": len((json_results or {}).values()) + len((html_results or {}).values())
            },
            "quality_assessment": validation_results,
            "generation_options": options,
            "file_manifest": await self._create_file_manifest(json_results, html_results),
            "next_steps": self._generate_next_steps(analysis_response)
        }

        return package

    async def _save_package_metadata(self, report_package: Dict[str, Any], report_id: str) -> Path:
        """Save report package metadata to file."""
        package_path = self.output_directory / f"{report_id}_package_metadata.json"
        return await asyncio.to_thread(safe_write_file, package_path, report_package)

    async def _generate_summary_report(self, report_package: Dict[str, Any], report_id: str) -> Path:
        """Generate human-readable summary report."""
        summary_content = self._create_summary_content(report_package)
        summary_path = self.reports_dir / f"{report_id}_summary.md"
        return await asyncio.to_thread(safe_write_file, summary_path, summary_content)

    async def _create_file_manifest(
        self,
        json_results: Optional[Dict[str, Any]],
        html_results: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Create manifest of all generated files."""
        manifest = []

        # Add JSON files
        if json_results:
            for file_type, file_path in json_results.items():
                file_info = await asyncio.to_thread(self._get_file_info, file_path)
                manifest.append({
                    "type": "json",
                    "subtype": file_type,
                    "path": file_path,
                    "size_mb": file_info.get("size_mb", 0),
                    "description": self._get_file_description(file_type, "json")
                })

        # Add HTML files
        if html_results:
            for file_type, file_path in html_results.items():
                file_info = await asyncio.to_thread(self._get_file_info, file_path)
                manifest.append({
                    "type": "html",
                    "subtype": file_type,
                    "path": file_path,
                    "size_mb": file_info.get("size_mb", 0),
                    "description": self._get_file_description(file_type, "html")
                })

        return manifest

    async def _generate_custom_json(
        self,
        analysis_response: NPSAnalysisResponse,
        json_config: Dict[str, Any],
        report_id: str
    ) -> Path:
        """Generate custom JSON output based on configuration."""
        custom_data = {}

        # Apply field selection
        if "fields" in json_config:
            for field in json_config["fields"]:
                if hasattr(analysis_response, field):
                    custom_data[field] = getattr(analysis_response, field).dict()

        # Apply custom transformations
        if "transformations" in json_config:
            for transform_name, transform_config in json_config["transformations"].items():
                custom_data[transform_name] = await self._apply_transformation(
                    analysis_response, transform_config
                )

        # Save custom JSON
        filename = json_config.get("filename", f"{report_id}_custom.json")
        custom_path = self.json_dir / filename

        return await asyncio.to_thread(safe_write_file, custom_path, custom_data)

    # Utility Methods

    def _prepare_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare and validate configuration."""
        default_config = {
            "output_formats": ["json", "html"],
            "html_templates": ["executive", "detailed"],
            "include_metadata": True,
            "include_raw_data": False,
            "file_organization": "by_type",
            "quality_validation": True
        }

        return {**default_config, **config}

    def _create_directory_structure(self):
        """Create output directory structure."""
        directories = [
            self.json_dir,
            self.html_dir,
            self.reports_dir,
            self.assets_dir,
            self.assets_dir / "css",
            self.assets_dir / "js",
            self.assets_dir / "images"
        ]

        for directory in directories:
            ensure_directory_exists(directory)

        logger.debug("Output directory structure created")

    def _generate_report_id(self) -> str:
        """Generate unique report ID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        short_uuid = uuid.uuid4().hex[:8]
        return f"nps_v3_{timestamp}_{short_uuid}"

    def _coerce_nps_metrics(self, metrics_data: Optional[Union[NPSMetrics, Dict[str, Any]]], context: Dict[str, Any]) -> NPSMetrics:
        """Coerce raw metrics data into NPSMetrics."""
        if isinstance(metrics_data, NPSMetrics):
            return metrics_data

        metrics_dict = metrics_data or {}

        promoters = metrics_dict.get("promoters_count", metrics_dict.get("promoter_count", 0))
        passives = metrics_dict.get("passives_count", metrics_dict.get("passive_count", 0))
        detractors = metrics_dict.get("detractors_count", metrics_dict.get("detractor_count", 0))
        sample_size = metrics_dict.get("sample_size")

        if sample_size is None:
            sample_size = context.get("sample_size")
        if sample_size is None:
            sample_size = promoters + passives + detractors

        return NPSMetrics(
            nps_score=float(metrics_dict.get("nps_score", 0.0)),
            promoter_count=int(promoters),
            passive_count=int(passives),
            detractor_count=int(detractors),
            sample_size=int(sample_size),
            statistical_significance=bool(metrics_dict.get("statistical_significance", False))
        )

    def _coerce_confidence_assessment(
        self,
        confidence_data: Optional[Union[ConfidenceAssessment, Dict[str, Any]]]
    ) -> ConfidenceAssessment:
        """Coerce raw confidence data into ConfidenceAssessment."""
        if isinstance(confidence_data, ConfidenceAssessment):
            return confidence_data

        data = confidence_data or {}
        overall_score = float(data.get("overall_confidence_score", 0.6))
        confidence_text = data.get("overall_confidence_text") or (
            "high" if overall_score >= 0.8 else "medium" if overall_score >= 0.6 else "low"
        )

        return ConfidenceAssessment(
            overall_confidence_score=overall_score,
            overall_confidence_text=str(confidence_text),
            data_quality_score=float(data.get("data_quality_score", 0.6)),
            analysis_completeness_score=float(data.get("analysis_completeness_score", 0.6)),
            statistical_significance_score=float(data.get("statistical_significance_score", 0.6))
        )

    def _coerce_executive_dashboard(
        self,
        dashboard_data: Optional[Union[ExecutiveDashboard, Dict[str, Any]]],
        metrics: NPSMetrics,
        confidence: ConfidenceAssessment
    ) -> ExecutiveDashboard:
        """Coerce raw executive dashboard data into ExecutiveDashboard."""
        if isinstance(dashboard_data, ExecutiveDashboard):
            return dashboard_data

        data = dashboard_data or {}

        key_insights = data.get("key_insights") or ["暂无关键洞察，建议补充分析数据"]
        critical_actions = data.get("critical_actions") or ["补充数据并重新运行分析"]
        strategic_priorities = data.get("strategic_priorities") or ["加强客户反馈收集", "提升服务满意度"]
        recommendation_summary = data.get("recommendation_summary") or {
            "strategic": 0,
            "product": 0,
            "operational": 0
        }

        performance_indicators = data.get("performance_indicators") or {
            "nps": {"score": metrics.nps_score, "trend": "+0"},
            "retention": {"rate": "--", "trend": "0%"}
        }

        return ExecutiveDashboard(
            overall_health_score=float(data.get("overall_health_score", max(min(metrics.nps_score + 50, 100), 0))),
            nps_summary=metrics,
            key_insights=key_insights,
            critical_actions=critical_actions,
            strategic_priorities=strategic_priorities,
            risk_alerts=data.get("risk_alerts") or [],
            performance_indicators=performance_indicators,
            recommendation_summary=recommendation_summary,
            confidence_overview=confidence,
            next_review_date=data.get("next_review_date")
        )

    def _coerce_agent_insights(
        self,
        insights: Optional[Union[List[AgentInsight], List[Dict[str, Any]]]]
    ) -> List[AgentInsight]:
        """Coerce raw insights into AgentInsight list."""
        if not insights:
            return []

        formatted: List[AgentInsight] = []
        for item in insights:
            if isinstance(item, AgentInsight):
                formatted.append(item)
            elif isinstance(item, dict):
                try:
                    formatted.append(AgentInsight(**item))
                except Exception:
                    logger.debug("Skipping invalid agent insight entry: %s", item)
        return formatted

    def _coerce_business_recommendations(
        self,
        recommendations: Optional[Union[List[BusinessRecommendation], List[Dict[str, Any]]]]
    ) -> List[BusinessRecommendation]:
        """Coerce raw recommendations into BusinessRecommendation list."""
        if not recommendations:
            return []

        formatted: List[BusinessRecommendation] = []
        for item in recommendations:
            if isinstance(item, BusinessRecommendation):
                formatted.append(item)
            elif isinstance(item, dict):
                try:
                    formatted.append(BusinessRecommendation(**item))
                except Exception:
                    logger.debug("Skipping invalid business recommendation entry: %s", item)
        return formatted

    def _ensure_response_format(self, analysis_result: Union[NPSAnalysisState, NPSAnalysisResponse]) -> NPSAnalysisResponse:
        """Ensure analysis result is in NPSAnalysisResponse format."""
        if analysis_result is None:
            raise ValueError("Analysis result cannot be None")

        if isinstance(analysis_result, NPSAnalysisResponse):
            return analysis_result

        if hasattr(analysis_result, "model_dump"):
            analysis_dict = analysis_result.model_dump()
        elif hasattr(analysis_result, "dict"):
            analysis_dict = analysis_result.dict()
        else:
            try:
                analysis_dict = dict(analysis_result)
            except TypeError as exc:
                raise ValueError(f"Unsupported analysis result type: {type(analysis_result)}") from exc

        if not analysis_dict or not analysis_dict.get("nps_metrics"):
            raise ValueError("Analysis result missing essential NPS metrics")

        metrics = self._coerce_nps_metrics(analysis_dict.get("nps_metrics"), analysis_dict)
        confidence = self._coerce_confidence_assessment(
            analysis_dict.get("confidence_assessment")
        )
        executive_dashboard = self._coerce_executive_dashboard(
            analysis_dict.get("executive_dashboard"),
            metrics,
            confidence
        )

        agent_insights = self._coerce_agent_insights(analysis_dict.get("agent_insights"))
        foundation_insights = self._coerce_agent_insights(analysis_dict.get("foundation_insights"))
        analysis_insights = self._coerce_agent_insights(analysis_dict.get("analysis_insights"))
        consulting_recommendations = self._coerce_business_recommendations(
            analysis_dict.get("consulting_recommendations")
        )
        business_recommendations = self._coerce_business_recommendations(
            analysis_dict.get("business_recommendations")
        ) or consulting_recommendations

        sample_size = analysis_dict.get("sample_size", metrics.sample_size)
        input_summary = analysis_dict.get("input_summary") or {
            "total_responses": sample_size,
            "valid_responses": sample_size,
            "sources": analysis_dict.get("response_sources", ["survey"])
        }

        return NPSAnalysisResponse(
            response_id=analysis_dict.get("response_id") or analysis_dict.get("workflow_id", "converted"),
            workflow_id=analysis_dict.get("workflow_id", "converted"),
            input_summary=input_summary,
            sample_size=sample_size,
            language=analysis_dict.get("language", "zh"),
            nps_metrics=metrics,
            confidence_assessment=confidence,
            agent_insights=agent_insights,
            foundation_insights=foundation_insights,
            analysis_insights=analysis_insights,
            consulting_recommendations=consulting_recommendations,
            business_recommendations=business_recommendations,
            executive_dashboard=executive_dashboard,
            workflow_status=analysis_dict.get("workflow_status", "completed"),
            completed_passes=analysis_dict.get("completed_passes") or ["foundation", "analysis", "consulting"],
            completed_agents=analysis_dict.get("completed_agents") or [],
            failed_agents=analysis_dict.get("failed_agents") or [],
            skipped_agents=analysis_dict.get("skipped_agents") or []
        )

    def _validate_analysis_results(self, analysis_response: NPSAnalysisResponse) -> Dict[str, Any]:
        """Validate analysis results for completeness and quality."""
        validation = {
            "is_valid": True,
            "issues": [],
            "warnings": [],
            "quality_score": 0
        }

        checks = []

        # Check NPS metrics
        if analysis_response.nps_metrics.sample_size > 0:
            checks.append(True)
        else:
            validation["issues"].append("No sample data available")
            checks.append(False)

        # Check insights availability
        if analysis_response.analysis_insights:
            checks.append(True)
        else:
            validation["warnings"].append("No analysis insights available")
            checks.append(False)

        # Check recommendations
        if analysis_response.consulting_recommendations:
            checks.append(True)
        else:
            validation["warnings"].append("No consulting recommendations available")
            checks.append(False)

        # Calculate quality score
        validation["quality_score"] = sum(checks) / len(checks) * 100
        validation["is_valid"] = validation["quality_score"] >= 60

        return validation

    def _merge_report_options(self, options: Dict[str, Any]) -> Dict[str, Any]:
        """Merge provided options with defaults."""
        default_options = {
            "generate_json": True,
            "generate_html": True,
            "generate_executive_json": True,
            "generate_executive_html": True,
            "generate_detailed_html": True,
            "generate_raw_insights": False,
            "generate_summary": True,
            "custom_templates": [],
            "custom_json": None
        }

        return {**default_options, **options}

    def _get_file_info(self, file_path: str) -> Dict[str, Any]:
        """Get file information."""
        try:
            path = Path(file_path)
            if path.exists():
                stat = path.stat()
                return {
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "created": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat()
                }
        except Exception:
            pass
        return {"size_mb": 0}

    def _get_file_description(self, file_type: str, format_type: str) -> str:
        """Get description for file type."""
        descriptions = {
            ("main_results", "json"): "Complete analysis results in JSON format",
            ("executive_summary", "json"): "Executive summary and key metrics",
            ("raw_insights", "json"): "Raw agent insights and recommendations",
            ("executive_dashboard", "html"): "Executive dashboard with KPI visualizations",
            ("detailed_analysis", "html"): "Comprehensive analysis with all agent results"
        }

        return descriptions.get((file_type, format_type), f"{file_type} in {format_type} format")

    def _create_summary_content(self, report_package: Dict[str, Any]) -> str:
        """Create human-readable summary content."""
        package_info = report_package["package_info"]
        analysis_summary = report_package["analysis_summary"]

        summary = f"""# NPS V3 分析报告总结

## 报告信息
- **报告ID**: {package_info['report_id']}
- **生成时间**: {package_info['generation_time']}
- **公司名称**: {package_info['company_name']}

## 核心指标
- **NPS得分**: {analysis_summary['nps_score']}
- **样本量**: {analysis_summary['sample_size']}
- **统计显著性**: {'是' if analysis_summary['statistical_significance'] else '否'}
- **置信度**: {analysis_summary['confidence_level']}

## 分析结果
- **洞察数量**: {analysis_summary['total_insights']}
- **战略建议**: {analysis_summary['total_recommendations']}
- **风险提示**: {analysis_summary['risk_alerts']}

## 生成文件
总计生成 {report_package['generated_outputs']['total_files']} 个文件

### JSON文件
"""

        for file_type, path in report_package["generated_outputs"]["json_files"].items():
            summary += f"- **{file_type}**: `{Path(path).name}`\n"

        summary += "\n### HTML文件\n"
        for file_type, path in report_package["generated_outputs"]["html_files"].items():
            summary += f"- **{file_type}**: `{Path(path).name}`\n"

        if report_package.get("next_steps"):
            summary += "\n## 建议后续行动\n"
            for step in report_package["next_steps"][:5]:
                summary += f"- {step}\n"

        return summary

    def _generate_next_steps(self, analysis_response: NPSAnalysisResponse) -> List[str]:
        """Generate suggested next steps based on analysis."""
        next_steps = []
        nps_score = analysis_response.nps_metrics.nps_score

        if nps_score < 0:
            next_steps.extend([
                "立即启动客户体验改进计划",
                "分析贬损者反馈，制定针对性改进措施",
                "建立客户关怀和挽回机制"
            ])
        elif nps_score < 30:
            next_steps.extend([
                "深入分析中性客户群体，寻找转化机会",
                "优化产品和服务体验",
                "建立持续反馈收集机制"
            ])
        else:
            next_steps.extend([
                "维护现有客户满意度水平",
                "探索推荐者增长机会",
                "建立客户忠诚度激励体系"
            ])

        # Add insight-based next steps
        if analysis_response.consulting_recommendations:
            top_rec = analysis_response.consulting_recommendations[0]
            next_steps.append(f"优先实施: {top_rec.title}")

        return next_steps

    async def _apply_transformation(
        self,
        analysis_response: NPSAnalysisResponse,
        transform_config: Dict[str, Any]
    ) -> Any:
        """Apply custom transformation to analysis data."""
        # This would implement various data transformations
        # For now, return basic summary
        return {
            "nps_score": analysis_response.nps_metrics.nps_score,
            "total_insights": len(analysis_response.analysis_insights),
            "confidence": analysis_response.confidence_assessment.overall_confidence_score
        }


# Convenience functions
async def generate_standard_reports(
    analysis_result: Union[NPSAnalysisState, NPSAnalysisResponse],
    output_directory: Optional[Union[str, Path]] = None,
    company_name: str = "伊利集团"
) -> Dict[str, Any]:
    """
    Generate standard dual-format reports.

    Args:
        analysis_result: Analysis results to export
        output_directory: Output directory for reports
        company_name: Company name for branding

    Returns:
        Report package with generated files
    """
    generator = DualOutputGenerator(
        output_directory=output_directory,
        company_name=company_name
    )

    return await generator.generate_complete_report_package(analysis_result)


async def quick_executive_report(
    analysis_result: Union[NPSAnalysisState, NPSAnalysisResponse],
    output_path: Optional[Union[str, Path]] = None
) -> Tuple[Path, Path]:
    """
    Generate quick executive report (JSON + HTML).

    Args:
        analysis_result: Analysis results to export
        output_path: Optional output directory

    Returns:
        Tuple of (JSON path, HTML path)
    """
    generator = DualOutputGenerator(output_directory=output_path)

    # Generate both formats
    json_task = generator.generate_json_only(analysis_result)
    html_task = generator.generate_html_only(analysis_result, "executive")

    json_path, html_path = await asyncio.gather(json_task, html_task)
    return json_path, html_path
