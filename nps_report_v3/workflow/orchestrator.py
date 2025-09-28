"""
Workflow orchestrator for NPS V3 three-pass architecture.

Orchestrates the execution of Foundation, Analysis, and Consulting passes
with checkpointing, memory management, and error recovery.
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import uuid
from pathlib import Path

from nps_report_v3.config import get_settings
from nps_report_v3.state import NPSAnalysisState, create_initial_state
from nps_report_v3.agents.factory import AgentFactory


logger = logging.getLogger(__name__)


class WorkflowOrchestrator:
    """
    Orchestrates the three-pass NPS analysis workflow:
    1. Foundation Pass (A0-A3): Data preparation and basic analysis
    2. Analysis Pass (B1-B9): Deep domain-specific analysis
    3. Consulting Pass (C1-C5): Strategic recommendations
    """

    def __init__(
        self,
        workflow_id: Optional[str] = None,
        enable_checkpointing: bool = True,
        enable_caching: bool = True,
        enable_profiling: bool = True
    ):
        """Initialize workflow orchestrator."""
        self.workflow_id = workflow_id or f"workflow_{uuid.uuid4().hex[:8]}"
        self.enable_checkpointing = enable_checkpointing
        self.enable_caching = enable_caching
        self.enable_profiling = enable_profiling

        self.settings = get_settings()
        self.factory = AgentFactory()

        logger.info(f"Initialized WorkflowOrchestrator {self.workflow_id}")

    async def execute(
        self,
        raw_data: List[Dict[str, Any]],
        config: Optional[Dict[str, Any]] = None
    ) -> NPSAnalysisState:
        """
        Execute the complete three-pass workflow.

        Args:
            raw_data: Raw survey response data
            config: Optional configuration overrides

        Returns:
            Final analysis state with all agent outputs
        """
        logger.info(f"Starting workflow execution for {len(raw_data)} responses")

        # Create initial state
        state = create_initial_state(
            workflow_id=self.workflow_id,
            raw_data=raw_data,
            **config or {}
        )

        # Add input_data structure expected by agent validation
        state["input_data"] = {
            "survey_responses": raw_data,
            "responses": raw_data  # Alternative format for compatibility
        }

        try:
            # Foundation Pass (A0-A3)
            state = await self._execute_foundation_pass(state)

            # Analysis Pass (B1-B9)
            state = await self._execute_analysis_pass(state)

            # Consulting Pass (C1-C5)
            state = await self._execute_consulting_pass(state)

            # Generate HTML reports after all analysis is complete
            state = await self._generate_html_reports(state)

            state["workflow_phase"] = "completed"
            state["completion_time"] = datetime.utcnow().isoformat()

            logger.info(f"Workflow {self.workflow_id} completed successfully")
            return state

        except Exception as e:
            logger.error(f"Workflow {self.workflow_id} failed: {e}")
            state["workflow_phase"] = "failed"
            state["error_details"] = str(e)
            raise

    async def _execute_foundation_pass(self, state: NPSAnalysisState) -> NPSAnalysisState:
        """Execute Foundation Pass agents (A0-A3)."""
        logger.info("Executing Foundation Pass (A0-A3)")

        state["workflow_phase"] = "foundation"

        # Sequential execution of Foundation agents
        foundation_agents = ["A0", "A1", "A2", "A3"]

        for agent_id in foundation_agents:
            try:
                logger.info(f"Executing agent {agent_id}")
                agent = self.factory.create_agent(agent_id)
                result = await agent.execute(state)

                if result.status.value == "completed":
                    # Update state with agent output while preserving core structure
                    if result.data:
                        # Preserve essential state fields during merge
                        preserved_fields = ["input_data", "workflow_id", "workflow_phase", "raw_data", "language"]
                        preserved_state = {k: v for k, v in state.items() if k in preserved_fields}
                        state = {**state, **result.data, **preserved_state}
                    logger.info(f"Agent {agent_id} completed successfully")
                else:
                    error_msg = f"Agent {agent_id} failed: {result.errors or ['Unknown error']}"
                    logger.error(error_msg)
                    raise RuntimeError(error_msg)

            except Exception as e:
                logger.error(f"Foundation Pass failed at agent {agent_id}: {e}")
                raise

        # Store Foundation Pass results under pass1_foundation for Analysis Pass agents
        foundation_data = {}
        for key, value in state.items():
            if key not in ["input_data", "workflow_id", "workflow_phase", "raw_data", "language"]:
                foundation_data[key] = value

        state["pass1_foundation"] = foundation_data

        logger.info("Foundation Pass completed")
        return state

    async def _execute_analysis_pass(self, state: NPSAnalysisState) -> NPSAnalysisState:
        """Execute Analysis Pass agents (B1-B9) with parallel execution."""
        logger.info("Executing Analysis Pass (B1-B9)")

        state["workflow_phase"] = "analysis"

        try:
            # Group 1: Segment Analysis (B1-B3) - run in parallel
            segment_results = await self._run_segment_analysis_parallel(state)
            state = self._merge_agent_results(state, segment_results)

            # Group 2: Advanced Analytics (B4-B5) - run in parallel
            analytics_results = await self._run_advanced_analytics_parallel(state)
            state = self._merge_agent_results(state, analytics_results)

            # Group 3: Dimensional Analysis (B6-B8) - run in parallel
            dimension_results = await self._run_dimension_analysis_parallel(state)
            state = self._merge_agent_results(state, dimension_results)

            # Group 4: Analysis Coordinator (B9) - runs last to synthesize
            logger.info("Executing Analysis Coordinator (B9)")
            coordinator_agent = self.factory.create_agent("B9")
            coordinator_result = await coordinator_agent.execute(state)

            if coordinator_result.status.value == "completed":
                if coordinator_result.data:
                    state = self._merge_single_agent_result(state, coordinator_result)
                logger.info("Analysis Coordinator (B9) completed successfully")
            else:
                error_msg = f"Analysis Coordinator (B9) failed: {coordinator_result.errors or ['Unknown error']}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Store Analysis Pass results under pass2_analysis for Consulting Pass agents
            analysis_data = {}
            for key, value in state.items():
                if key not in ["input_data", "workflow_id", "workflow_phase", "raw_data", "language", "pass1_foundation"]:
                    analysis_data[key] = value

            state["pass2_analysis"] = analysis_data

            # Propagate confidence assessment from analysis synthesis to foundation snapshot
            confidence_summary = state.get("analysis_coordination", {}).get("synthesis_summary", {})
            confidence_assessment = confidence_summary.get("confidence_assessment")
            if confidence_assessment:
                normalized_confidence = self._normalize_confidence_assessment(confidence_assessment)
                pass1_foundation = state.get("pass1_foundation", {})
                pass1_foundation["confidence_assessment"] = normalized_confidence
                state["pass1_foundation"] = pass1_foundation
                state["confidence_assessment"] = normalized_confidence
                recommendation_confidence = normalized_confidence.get("overall_confidence_score")
                if recommendation_confidence is not None:
                    state["confidence"] = recommendation_confidence

            logger.info("Analysis Pass completed")
            return state

        except Exception as e:
            logger.error(f"Analysis Pass failed: {e}")
            raise

    async def _run_segment_analysis_parallel(self, state: NPSAnalysisState) -> List[Any]:
        """Run segment analysis agents (B1-B3) in parallel."""
        logger.info("Running segment analysis agents (B1-B3) in parallel")

        segment_agents = ["B1", "B2", "B3"]
        tasks = []

        for agent_id in segment_agents:
            agent = self.factory.create_agent(agent_id)
            tasks.append(agent.execute(state))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for failures and log results
        processed_results = []
        for i, result in enumerate(results):
            agent_id = segment_agents[i]
            if isinstance(result, Exception):
                logger.error(f"Segment agent {agent_id} failed with exception: {result}")
                raise result
            elif result.status.value != "completed":
                error_msg = f"Segment agent {agent_id} failed: {result.errors or ['Unknown error']}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                logger.info(f"Segment agent {agent_id} completed successfully")
                processed_results.append(result)

        return processed_results

    async def _run_advanced_analytics_parallel(self, state: NPSAnalysisState) -> List[Any]:
        """Run advanced analytics agents (B4-B5) in parallel."""
        logger.info("Running advanced analytics agents (B4-B5) in parallel")

        analytics_agents = ["B4", "B5"]
        tasks = []

        for agent_id in analytics_agents:
            agent = self.factory.create_agent(agent_id)
            tasks.append(agent.execute(state))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for failures and log results
        processed_results = []
        for i, result in enumerate(results):
            agent_id = analytics_agents[i]
            if isinstance(result, Exception):
                logger.error(f"Analytics agent {agent_id} failed with exception: {result}")
                raise result
            elif result.status.value != "completed":
                error_msg = f"Analytics agent {agent_id} failed: {result.errors or ['Unknown error']}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                logger.info(f"Analytics agent {agent_id} completed successfully")
                processed_results.append(result)

        return processed_results

    async def _run_dimension_analysis_parallel(self, state: NPSAnalysisState) -> List[Any]:
        """Run dimensional analysis agents (B6-B8) in parallel."""
        logger.info("Running dimensional analysis agents (B6-B8) in parallel")

        dimension_agents = ["B6", "B7", "B8"]
        tasks = []

        for agent_id in dimension_agents:
            agent = self.factory.create_agent(agent_id)
            tasks.append(agent.execute(state))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for failures and log results
        processed_results = []
        for i, result in enumerate(results):
            agent_id = dimension_agents[i]
            if isinstance(result, Exception):
                logger.error(f"Dimension agent {agent_id} failed with exception: {result}")
                raise result
            elif result.status.value != "completed":
                error_msg = f"Dimension agent {agent_id} failed: {result.errors or ['Unknown error']}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)
            else:
                logger.info(f"Dimension agent {agent_id} completed successfully")
                processed_results.append(result)

        return processed_results

    def _merge_agent_results(self, state: NPSAnalysisState, results: List[Any]) -> NPSAnalysisState:
        """Merge multiple agent results into the state."""
        for result in results:
            if result.data:
                state = self._merge_single_agent_result(state, result)
        return state

    def _merge_single_agent_result(self, state: NPSAnalysisState, result: Any) -> NPSAnalysisState:
        """Merge a single agent result into the state, preserving essential fields."""
        if result.data:
            # Preserve essential state fields during merge
            preserved_fields = [
                "input_data", "workflow_id", "workflow_phase", "raw_data", "language",
                "completion_time", "error_details"
            ]
            preserved_state = {k: v for k, v in state.items() if k in preserved_fields}
            state = {**state, **result.data, **preserved_state}
        return state

    def _normalize_confidence_assessment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize confidence payloads into ConfidenceAssessment-compatible dicts."""
        score = payload.get("overall_confidence_score")
        if score is None:
            score = payload.get("recommendation_confidence")
        if score is None:
            score = payload.get("confidence", 0.6)

        text = payload.get("overall_confidence_text") or payload.get("overall_confidence") or "medium"
        text_map = {
            "very_high": "极高",
            "high": "高",
            "medium": "中",
            "low": "低",
            "very_low": "很低",
            "高": "高",
            "中": "中",
            "低": "低"
        }
        normalized_text = text_map.get(text, "中")

        data_quality = payload.get("data_quality_score")
        if data_quality is None:
            data_quality = payload.get("data_completeness", 0.6)

        analysis_score = payload.get("analysis_completeness_score")
        if analysis_score is None:
            analysis_score = payload.get("cross_validation_rate", 0.6)

        statistical_score = payload.get("statistical_significance_score")
        if statistical_score is None:
            statistical_score = payload.get("statistical_significance", 0.6)

        factors = payload.get("confidence_factors") or payload.get("factors") or {}

        return {
            "overall_confidence_score": round(float(score), 3),
            "overall_confidence_text": normalized_text,
            "data_quality_score": round(float(data_quality), 3),
            "analysis_completeness_score": round(float(analysis_score), 3),
            "statistical_significance_score": round(float(statistical_score), 3),
            "confidence_factors": factors
        }

    async def _execute_consulting_pass(self, state: NPSAnalysisState) -> NPSAnalysisState:
        """Execute Consulting Pass agents (C1-C5) with confidence constraints."""
        logger.info("Executing Consulting Pass (C1-C5)")

        state["workflow_phase"] = "consulting"

        try:
            # Strategic advisors (C1-C4) - run in parallel with confidence constraints
            strategic_results = await self._run_strategic_advisors_parallel(state)
            state = self._merge_agent_results(state, strategic_results)

            # Executive Synthesizer (C5) - runs last to synthesize all consulting outputs
            logger.info("Executing Executive Synthesizer (C5)")
            synthesizer_agent = self.factory.create_agent("C5")
            synthesizer_result = await synthesizer_agent.execute(state)

            if synthesizer_result.status.value == "completed":
                if synthesizer_result.data:
                    state = self._merge_single_agent_result(state, synthesizer_result)
                logger.info("Executive Synthesizer (C5) completed successfully")
            else:
                error_msg = f"Executive Synthesizer (C5) failed: {synthesizer_result.errors or ['Unknown error']}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            logger.info("Consulting Pass completed")
            return state

        except Exception as e:
            logger.error(f"Consulting Pass failed: {e}")
            raise

    async def _run_strategic_advisors_parallel(self, state: NPSAnalysisState) -> List[Any]:
        """Run strategic advisor agents (C1-C4) in parallel with confidence-based constraints."""
        logger.info("Running strategic advisor agents (C1-C4) in parallel")

        strategic_agents = ["C1", "C2", "C3", "C4"]
        tasks = []

        # Check overall confidence for consulting recommendations
        confidence_level = self._assess_consulting_confidence(state)
        state["consulting_confidence"] = confidence_level

        # Apply confidence constraints - skip agents if confidence too low
        low_confidence_agents = set()
        for agent_id in strategic_agents:
            if self._agent_meets_confidence_requirements(agent_id, confidence_level, state):
                pass
            else:
                logger.warning(
                    f"Agent {agent_id} operating under low confidence conditions "
                    f"({confidence_level:.2f}); proceeding with caution"
                )
                low_confidence_agents.add(agent_id)

        for agent_id in strategic_agents:
            agent = self.factory.create_agent(agent_id)
            tasks.append(agent.execute(state))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Check for failures and log results
        processed_results = []
        for i, result in enumerate(results):
            agent_id = strategic_agents[i]
            if isinstance(result, Exception):
                logger.error(f"Strategic advisor {agent_id} failed with exception: {result}")
                # For consulting agents, we continue with partial results rather than failing completely
                logger.info(f"Continuing without {agent_id} results")
            elif result.status.value != "completed":
                error_msg = f"Strategic advisor {agent_id} failed: {result.errors or ['Unknown error']}"
                logger.warning(error_msg)
                # Log warning but continue with other results
            else:
                if agent_id in low_confidence_agents:
                    if result.warnings is None:
                        result.warnings = []
                    result.warnings.append(
                        "Confidence level is low for this recommendation set; review before action."
                    )
                    adjusted_score = result.confidence_score if result.confidence_score is not None else 0.6
                    result.confidence_score = min(adjusted_score, 0.5)
                    if result.metadata is None:
                        result.metadata = {}
                    result.metadata["confidence_level"] = "low"
                logger.info(f"Strategic advisor {agent_id} completed successfully")
                processed_results.append(result)

        if not processed_results:
            logger.warning("No strategic advisors completed successfully")

        return processed_results

    def _assess_consulting_confidence(self, state: NPSAnalysisState) -> float:
        """
        Assess overall confidence level for consulting recommendations.

        Args:
            state: Current workflow state

        Returns:
            Confidence level (0.0 to 1.0)
        """
        confidence_factors = []

        # Check NPS sample size and significance
        nps_metrics = state.get("nps_metrics", {})
        sample_size = nps_metrics.get("sample_size", 0)
        statistical_significance = nps_metrics.get("statistical_significance", False)

        if statistical_significance:
            confidence_factors.append(0.9)
        elif sample_size >= 100:
            confidence_factors.append(0.8)
        elif sample_size >= 50:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)

        # Check data quality
        cleaned_data = state.get("cleaned_data", {})
        data_quality = cleaned_data.get("data_quality", "low")

        quality_scores = {"high": 0.9, "medium": 0.7, "low": 0.4, "insufficient": 0.2}
        confidence_factors.append(quality_scores.get(data_quality, 0.4))

        # Check analysis completeness
        analysis_outputs = ["technical_requirements", "semantic_clusters", "tagged_responses"]
        completed_analyses = sum(1 for output in analysis_outputs if state.get(output))

        confidence_factors.append(min(0.9, completed_analyses / len(analysis_outputs)))

        # Check for critical issues that would undermine consulting recommendations
        nps_score = nps_metrics.get("nps_score", 0)
        if nps_score < 0:  # Very negative NPS requires careful consulting
            confidence_factors.append(0.5)
        elif nps_score < 20:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.9)

        overall_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0.5

        logger.info(f"Consulting confidence assessment: {overall_confidence:.2f}")
        return overall_confidence

    def _agent_meets_confidence_requirements(self, agent_id: str, confidence_level: float, state: NPSAnalysisState) -> bool:
        """
        Check if an agent meets confidence requirements for execution.

        Args:
            agent_id: Agent identifier
            confidence_level: Overall confidence level
            state: Current workflow state

        Returns:
            True if agent should be executed
        """
        # Agent-specific confidence requirements
        agent_requirements = {
            "C1": 0.5,  # Strategic recommendations - lower threshold as always valuable
            "C2": 0.6,  # Product recommendations - moderate threshold
            "C3": 0.6,  # Marketing recommendations - moderate threshold
            "C4": 0.7,  # Risk management - higher threshold for accuracy
            "C5": 0.6   # Executive synthesis - moderate threshold
        }

        required_confidence = agent_requirements.get(agent_id, 0.7)
        meets_requirement = confidence_level >= required_confidence

        # Additional checks for specific agents
        if agent_id == "C2":  # Product consultant
            # Need sufficient product-related feedback
            tagged_responses = state.get("tagged_responses", [])
            product_mentions = sum(1 for r in tagged_responses if any(p in str(r).lower() for p in ["产品", "质量", "口味", "包装"]))
            if product_mentions < 5:
                meets_requirement = False

        elif agent_id == "C3":  # Marketing advisor
            # Need sufficient brand/marketing feedback
            tagged_responses = state.get("tagged_responses", [])
            marketing_mentions = sum(1 for r in tagged_responses if any(m in str(r).lower() for m in ["品牌", "营销", "广告", "推广", "服务"]))
            if marketing_mentions < 3:
                meets_requirement = False

        elif agent_id == "C4":  # Risk manager
            # Risk analysis always valuable but needs minimum data quality
            data_quality = state.get("cleaned_data", {}).get("data_quality", "low")
            if data_quality == "insufficient":
                meets_requirement = False

        return meets_requirement

    async def _generate_html_reports(self, state: NPSAnalysisState) -> NPSAnalysisState:
        """
        Generate HTML reports from analysis results and add to state.

        Args:
            state: Current workflow state with all analysis results

        Returns:
            State with HTML reports added
        """
        try:
            logger.info("Generating HTML reports from analysis results")

            # Generate simple HTML report directly without complex Pydantic models
            html_report = await self._generate_simple_html_report(state)

            # Add HTML report to state
            state["html_report"] = html_report

            # Save HTML report to file
            report_id = state.get("workflow_id", f"v3_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
            output_dir = Path("outputs/v3_reports")
            output_dir.mkdir(parents=True, exist_ok=True)

            html_file = output_dir / f"{report_id}_executive_report.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_report)

            state["html_reports"] = {
                "executive_dashboard": str(html_file)
            }

            logger.info(f"HTML report generated successfully: {html_file}")

        except Exception as e:
            logger.error(f"HTML report generation failed: {e}")
            # Don't fail the entire workflow for HTML generation issues
            state["html_generation_error"] = str(e)

        return state

    async def _generate_simple_html_report(self, state: Dict[str, Any]) -> str:
        """
        Generate a simple HTML report directly from state data.

        Args:
            state: Current workflow state

        Returns:
            HTML report string
        """
        nps_metrics = state.get("nps_metrics", {})
        executive_dashboard = state.get("executive_dashboard", {})
        executive_recommendations = state.get("executive_recommendations", [])
        raw_data = state.get("raw_data", [])

        nps_score = nps_metrics.get("nps_score", 0)
        sample_size = len(raw_data)

        # Generate simple HTML report
        html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>伊利集团 NPS 分析报告</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header .subtitle {{
            margin-top: 10px;
            font-size: 1.2em;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            border-left: 4px solid #007bff;
        }}
        .metric-value {{
            font-size: 2.5em;
            font-weight: bold;
            color: #007bff;
            margin: 10px 0;
        }}
        .metric-label {{
            color: #6c757d;
            text-transform: uppercase;
            font-size: 0.9em;
            letter-spacing: 1px;
        }}
        .section {{
            margin-bottom: 40px;
        }}
        .section h2 {{
            color: #333;
            border-bottom: 2px solid #e9ecef;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .recommendation {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 4px;
        }}
        .recommendation h3 {{
            margin: 0 0 10px 0;
            color: #856404;
        }}
        .recommendation p {{
            margin: 0;
            color: #664d03;
        }}
        .nps-gauge {{
            text-align: center;
            margin: 20px 0;
        }}
        .nps-score {{
            font-size: 4em;
            font-weight: bold;
            color: {"#dc3545" if nps_score < 0 else "#ffc107" if nps_score < 50 else "#28a745"};
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #6c757d;
            border-top: 1px solid #e9ecef;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
            text-transform: uppercase;
        }}
        .status-completed {{
            background: #d4edda;
            color: #155724;
        }}
        .dashboard-summary {{
            background: #e7f3ff;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>伊利集团 NPS 分析报告</h1>
            <div class="subtitle">基于 {sample_size} 个客户样本的综合分析</div>
            <div class="subtitle">
                <span class="status-badge status-completed">分析完成</span>
            </div>
        </div>

        <div class="content">
            <!-- NPS Score Section -->
            <div class="section">
                <h2>📊 NPS 核心指标</h2>
                <div class="nps-gauge">
                    <div class="nps-score">{nps_score:.1f}</div>
                    <div>净推荐值 (NPS)</div>
                </div>

                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{nps_metrics.get("promoters_count", 0)}</div>
                        <div class="metric-label">推荐者数量</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{nps_metrics.get("passives_count", 0)}</div>
                        <div class="metric-label">中性客户数量</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{nps_metrics.get("detractors_count", 0)}</div>
                        <div class="metric-label">批评者数量</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{sample_size}</div>
                        <div class="metric-label">样本总量</div>
                    </div>
                </div>
            </div>

            <!-- Executive Dashboard -->
            {"" if not executive_dashboard else f'''
            <div class="section">
                <h2>🎯 执行层仪表板</h2>
                <div class="dashboard-summary">
                    <strong>整体健康得分:</strong> {executive_dashboard.get("overall_health_score", "N/A")}/100<br>
                    <strong>业务状态:</strong> {executive_dashboard.get("business_status", "分析中")}<br>
                    <strong>战略就绪度:</strong> {executive_dashboard.get("strategic_readiness", "待评估")}
                </div>
            </div>
            '''}

            <!-- Recommendations Section -->
            {"" if not executive_recommendations else self._generate_recommendations_html(executive_recommendations)}

            <!-- Workflow Summary -->
            <div class="section">
                <h2>⚙️ 分析流程概览</h2>
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div class="metric-value">{len(state.get("agent_sequence", []))}</div>
                        <div class="metric-label">完成的分析模块</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{state.get("total_processing_time_ms", 0) // 1000}s</div>
                        <div class="metric-label">处理时间</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">3</div>
                        <div class="metric-label">完成的分析阶段</div>
                    </div>
                    <div class="metric-card">
                        <div class="metric-value">{state.get("confidence", 0.7):.1f}</div>
                        <div class="metric-label">置信度评分</div>
                    </div>
                </div>
            </div>
        </div>

        <div class="footer">
            <p>报告生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>🤖 由伊利集团 NPS V3 智能分析系统生成</p>
        </div>
    </div>
</body>
</html>
        """

        return html_content.strip()

    def _generate_recommendations_html(self, executive_recommendations: list) -> str:
        """Generate HTML for executive recommendations."""
        recommendations_html = []
        for rec in executive_recommendations[:5]:
            rec_html = f'''
                <div class="recommendation">
                    <h3>{rec.get("title", "执行建议")}</h3>
                    <p><strong>优先级:</strong> {rec.get("strategic_priority", "常规")}</p>
                    <p><strong>实施复杂度:</strong> {rec.get("implementation_complexity", "中等")}</p>
                    <p><strong>时间线:</strong> {rec.get("timeline", "待定")}</p>
                    <p>{rec.get("executive_summary", "详细建议内容待完善")}</p>
                </div>
            '''
            recommendations_html.append(rec_html)

        return f'''
            <div class="section">
                <h2>💡 执行建议</h2>
                {"".join(recommendations_html)}
            </div>
        '''

    async def recover_from_checkpoint(self, checkpoint_id: str) -> NPSAnalysisState:
        """Recover workflow from a checkpoint."""
        # TODO: Implement checkpoint recovery
        logger.warning("Checkpoint recovery not yet implemented")
        raise NotImplementedError("Checkpoint recovery not yet implemented")
