"""
Pass 3 Consulting LangGraph Workflow
LangGraph-based workflow for executing the Consulting Pass (C1-C5) with confidence-based constraints.
"""

import logging
from typing import Dict, Any, List, TypedDict, Optional
import asyncio
from datetime import datetime

# LangGraph imports (we'll use a simplified implementation for now)
try:
    from langgraph.graph import StateGraph, END
    from langgraph.checkpoint.memory import MemorySaver
    LANGGRAPH_AVAILABLE = True
except ImportError:
    logging.warning("LangGraph not available, using simplified implementation")
    LANGGRAPH_AVAILABLE = False

from ..agents.factory import AgentFactory
from ..agents.base import AgentResult, AgentStatus
from ..state import NPSAnalysisState


def _compose_error_message(agent_id: str, result: Any) -> str:
    """Format error details from an agent result or exception."""
    if isinstance(result, AgentResult):
        details = result.errors or ["Unknown error"]
        return f"{agent_id}: {'; '.join(details)}"
    errors_attr = getattr(result, "errors", None)
    if errors_attr:
        if isinstance(errors_attr, (list, tuple)):
            details = [str(item) for item in errors_attr]
        else:
            details = [str(errors_attr)]
        return f"{agent_id}: {'; '.join(details)}"
    error_attr = getattr(result, "error", None)
    if error_attr:
        return f"{agent_id}: {error_attr}"
    status = getattr(result, "status", None)
    status_value = getattr(status, "value", None)
    if status_value:
        return f"{agent_id}: status={status_value}"
    return f"{agent_id}: {result}"


def _apply_low_confidence_warning(result: AgentResult) -> None:
    """Annotate an AgentResult to reflect low confidence inputs."""
    warnings_attr = getattr(result, "warnings", None)
    if warnings_attr is None:
        warnings_list = []
        try:
            setattr(result, "warnings", warnings_list)
        except Exception:
            warnings_list = []
    else:
        if isinstance(warnings_attr, list):
            warnings_list = warnings_attr
        elif isinstance(warnings_attr, tuple):
            warnings_list = list(warnings_attr)
            try:
                setattr(result, "warnings", warnings_list)
            except Exception:
                pass
        else:
            warnings_list = [warnings_attr]
            try:
                setattr(result, "warnings", warnings_list)
            except Exception:
                pass
    warnings_list.append("Underlying data confidence is low; review before execution.")

    confidence_score = getattr(result, "confidence_score", None)
    if confidence_score is not None:
        try:
            setattr(result, "confidence_score", min(float(confidence_score), 0.5))
        except Exception:
            pass
    else:
        try:
            setattr(result, "confidence_score", 0.5)
        except Exception:
            pass

    metadata = getattr(result, "metadata", None)
    if not isinstance(metadata, dict):
        metadata = {}
        try:
            setattr(result, "metadata", metadata)
        except Exception:
            pass
    metadata["confidence_level"] = "low"


def _is_success_result(result: Any) -> bool:
    if isinstance(result, AgentResult):
        return result.status == AgentStatus.COMPLETED
    status = getattr(result, "status", None)
    status_value = getattr(status, "value", None)
    return status_value == "completed"


def _iter_warnings(result: Any) -> List[str]:
    warnings_attr = getattr(result, "warnings", None)
    if not warnings_attr:
        return []
    if isinstance(warnings_attr, (list, tuple)):
        return [str(item) for item in warnings_attr]
    return [str(warnings_attr)]

logger = logging.getLogger(__name__)


class ConsultingPassState(TypedDict):
    """State for Consulting Pass workflow"""
    # Core data
    input_data: Dict[str, Any]
    workflow_id: str

    # Foundation and Analysis outputs (from Pass 1-2)
    cleaned_data: Dict[str, Any]
    nps_metrics: Dict[str, Any]
    tagged_responses: List[Dict[str, Any]]
    semantic_clusters: List[Dict[str, Any]]
    technical_requirements: List[Dict[str, Any]]
    analysis_synthesis: Dict[str, Any]

    # Consulting outputs (Pass 3)
    strategic_recommendations: List[Dict[str, Any]]
    product_recommendations: List[Dict[str, Any]]
    marketing_recommendations: List[Dict[str, Any]]
    risk_assessments: List[Dict[str, Any]]
    executive_recommendations: List[Dict[str, Any]]
    executive_dashboard: Dict[str, Any]

    # Confidence and quality control
    consulting_confidence: float
    confidence_assessment: Dict[str, Any]
    low_confidence_fallback: bool

    # Workflow control
    workflow_phase: str
    current_group: str
    completed_agents: List[str]
    failed_agents: List[str]
    skipped_agents: List[str]
    errors: List[str]
    warnings: List[str]


class ConsultingPassWorkflow:
    """
    LangGraph workflow for Consulting Pass execution.

    Executes C1-C5 agents with confidence-based constraints:
    - Confidence Assessment: Evaluate data quality for consulting
    - Strategic Advisors (C1-C4): Run in parallel with confidence checks
    - Executive Synthesizer (C5): Generate final recommendations
    """

    def __init__(self, enable_checkpoints: bool = True):
        """Initialize Consulting Pass workflow."""
        self.factory = AgentFactory()
        self.enable_checkpoints = enable_checkpoints
        self.memory = MemorySaver() if LANGGRAPH_AVAILABLE and enable_checkpoints else None

        # Define confidence thresholds for each agent
        self.confidence_thresholds = {
            "C1": 0.5,  # Strategic recommendations - always valuable
            "C2": 0.6,  # Product recommendations - moderate threshold
            "C3": 0.6,  # Marketing recommendations - moderate threshold
            "C4": 0.7,  # Risk management - higher threshold for accuracy
            "C5": 0.6   # Executive synthesis - moderate threshold
        }

        # Define agent groups
        self.agent_groups = {
            "strategic_advisors": ["C1", "C2", "C3", "C4"],
            "executive_synthesis": ["C5"]
        }

        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_langgraph()
        else:
            self.graph = None
            logger.warning("LangGraph not available, using simplified execution")

    def _build_langgraph(self) -> StateGraph:
        """Build LangGraph StateGraph for Consulting Pass."""
        workflow = StateGraph(ConsultingPassState)

        # Add nodes
        workflow.add_node("confidence_assessment", self._assess_confidence)
        workflow.add_node("strategic_advisors", self._execute_strategic_advisors)
        workflow.add_node("executive_synthesis", self._execute_executive_synthesis)
        workflow.add_node("low_confidence_fallback", self._execute_low_confidence_fallback)

        # Define conditional routing based on confidence (always reach advisors)
        def route_after_confidence(state):
            return "strategic_advisors"

        # Define flow
        workflow.add_edge("confidence_assessment", route_after_confidence)
        workflow.add_edge("strategic_advisors", "executive_synthesis")
        workflow.add_edge("executive_synthesis", END)
        workflow.add_edge("low_confidence_fallback", END)

        # Set entry point
        workflow.set_entry_point("confidence_assessment")

        return workflow.compile(checkpointer=self.memory)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Consulting Pass workflow.

        Args:
            state: Input state from Analysis Pass

        Returns:
            Updated state with consulting results
        """
        logger.info("Starting Consulting Pass workflow execution")

        # Convert to workflow state
        consulting_state = self._prepare_consulting_state(state)

        if self.graph and LANGGRAPH_AVAILABLE:
            # Use LangGraph execution
            config = {"thread_id": consulting_state["workflow_id"]}
            final_state = await self.graph.ainvoke(consulting_state, config=config)
        else:
            # Use simplified execution
            final_state = await self._execute_simplified(consulting_state)

        # Convert back to NPSAnalysisState format
        result_state = self._prepare_output_state(final_state, state)

        logger.info("Consulting Pass workflow completed")
        return result_state

    def _prepare_consulting_state(self, state: Dict[str, Any]) -> ConsultingPassState:
        """Prepare state for consulting workflow."""
        return ConsultingPassState(
            input_data=state.get("input_data", {}),
            workflow_id=state.get("workflow_id", "unknown"),

            # Previous pass outputs
            cleaned_data=state.get("cleaned_data", {}),
            nps_metrics=state.get("nps_metrics", {}),
            tagged_responses=state.get("tagged_responses", []),
            semantic_clusters=state.get("semantic_clusters", []),
            technical_requirements=state.get("technical_requirements", []),
            analysis_synthesis=state.get("analysis_synthesis", {}),

            # Initialize consulting outputs
            strategic_recommendations=[],
            product_recommendations=[],
            marketing_recommendations=[],
            risk_assessments=[],
            executive_recommendations=[],
            executive_dashboard={},

            # Initialize confidence control
            consulting_confidence=0.0,
            confidence_assessment={},
            low_confidence_fallback=False,

            # Workflow control
            workflow_phase="consulting",
            current_group="confidence_assessment",
            completed_agents=[],
            failed_agents=[],
            skipped_agents=[],
            errors=[],
            warnings=[]
        )

    def _prepare_output_state(self, consulting_state: ConsultingPassState, original_state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert consulting state back to NPSAnalysisState format."""
        result_state = original_state.copy()

        # Add consulting outputs
        if consulting_state.get("strategic_recommendations"):
            result_state["strategic_recommendations"] = consulting_state["strategic_recommendations"]
        if consulting_state.get("product_recommendations"):
            result_state["product_recommendations"] = consulting_state["product_recommendations"]
        if consulting_state.get("marketing_recommendations"):
            result_state["marketing_recommendations"] = consulting_state["marketing_recommendations"]
        if consulting_state.get("risk_assessments"):
            result_state["risk_assessments"] = consulting_state["risk_assessments"]
        if consulting_state.get("executive_recommendations"):
            result_state["executive_recommendations"] = consulting_state["executive_recommendations"]
        if consulting_state.get("executive_dashboard"):
            result_state["executive_dashboard"] = consulting_state["executive_dashboard"]

        # Add confidence information
        result_state["consulting_confidence"] = consulting_state.get("consulting_confidence", 0.0)
        result_state["confidence_assessment"] = consulting_state.get("confidence_assessment", {})

        if consulting_state.get("errors"):
            result_state.setdefault("errors", [])
            result_state["errors"].extend(consulting_state["errors"])

        if consulting_state.get("warnings"):
            result_state.setdefault("warnings", [])
            result_state["warnings"].extend(consulting_state["warnings"])

        # Update workflow metadata
        result_state["workflow_phase"] = "consulting_completed"
        result_state["completed_agents"] = consulting_state.get("completed_agents", [])
        result_state["failed_agents"] = consulting_state.get("failed_agents", [])
        result_state["skipped_agents"] = consulting_state.get("skipped_agents", [])

        return result_state

    async def _execute_simplified(self, state: ConsultingPassState) -> ConsultingPassState:
        """Simplified execution without LangGraph."""
        logger.info("Executing simplified Consulting Pass workflow")

        # Assess confidence but always execute full consulting stack
        state = await self._assess_confidence(state)

        state = await self._execute_strategic_advisors(state)
        state = await self._execute_executive_synthesis(state)

        return state

    async def _assess_confidence(self, state: ConsultingPassState) -> ConsultingPassState:
        """Assess confidence level for consulting recommendations."""
        logger.info("Assessing consulting confidence")

        state["current_group"] = "confidence_assessment"
        confidence_factors = []

        # Check NPS sample size and significance
        nps_metrics = state["nps_metrics"]
        sample_size = nps_metrics.get("sample_size", 0)
        statistical_significance = nps_metrics.get("statistical_significance", False)

        if statistical_significance:
            confidence_factors.append(("statistical_significance", 0.9))
        elif sample_size >= 100:
            confidence_factors.append(("large_sample", 0.8))
        elif sample_size >= 50:
            confidence_factors.append(("medium_sample", 0.6))
        else:
            confidence_factors.append(("small_sample", 0.4))

        # Check data quality
        cleaned_data = state["cleaned_data"]
        data_quality = cleaned_data.get("data_quality", "low")

        quality_scores = {"high": 0.9, "medium": 0.7, "low": 0.4, "insufficient": 0.2}
        confidence_factors.append(("data_quality", quality_scores.get(data_quality, 0.4)))

        # Check analysis completeness
        analysis_outputs = ["technical_requirements", "semantic_clusters", "tagged_responses"]
        completed_analyses = sum(1 for output in analysis_outputs if state.get(output))
        analysis_completeness = completed_analyses / len(analysis_outputs)
        confidence_factors.append(("analysis_completeness", min(0.9, analysis_completeness)))

        # Check NPS score for strategic context
        nps_score = nps_metrics.get("nps_score", 0)
        if nps_score < -20:  # Very negative NPS
            confidence_factors.append(("nps_context", 0.5))
        elif nps_score < 10:
            confidence_factors.append(("nps_context", 0.7))
        else:
            confidence_factors.append(("nps_context", 0.9))

        # Calculate overall confidence
        overall_confidence = sum(score for _, score in confidence_factors) / len(confidence_factors)

        state["consulting_confidence"] = overall_confidence
        if overall_confidence >= 0.75:
            confidence_label = "high"
        elif overall_confidence >= 0.5:
            confidence_label = "medium"
        else:
            confidence_label = "low"

        state["confidence_assessment"] = {
            "factors": dict(confidence_factors),
            "overall_confidence": overall_confidence,
            "meets_minimum_threshold": overall_confidence >= 0.5,
            "sample_size": sample_size,
            "data_quality": data_quality,
            "nps_score": nps_score,
            "confidence_label": confidence_label
        }

        logger.info(f"Consulting confidence assessment: {overall_confidence:.2f}")
        return state

    async def _execute_strategic_advisors(self, state: ConsultingPassState) -> ConsultingPassState:
        """Execute strategic advisor agents (C1-C4) in parallel with confidence constraints."""
        logger.info("Executing strategic advisors (C1-C4)")

        state["current_group"] = "strategic_advisors"
        all_agents = self.agent_groups["strategic_advisors"]

        low_confidence_agents = {
            agent_id for agent_id in all_agents
            if not self._agent_meets_confidence_requirements(agent_id, state)
        }

        for agent_id in low_confidence_agents:
            logger.warning(
                f"Consulting agent {agent_id} executing under low confidence conditions "
                f"({state['consulting_confidence']:.2f})"
            )

        # Execute all agents and annotate outputs instead of skipping
        results = await self._execute_agent_group(all_agents, state)

        # Process results
        for agent_id, result in results.items():
            if _is_success_result(result):
                state["completed_agents"].append(agent_id)

                if agent_id in low_confidence_agents:
                    _apply_low_confidence_warning(result)

                if agent_id == "C1" and result.data:
                    state["strategic_recommendations"] = result.data.get("strategic_recommendations", [])
                elif agent_id == "C2" and result.data:
                    state["product_recommendations"] = result.data.get("product_recommendations", [])
                elif agent_id == "C3" and result.data:
                    state["marketing_recommendations"] = result.data.get("marketing_recommendations", [])
                elif agent_id == "C4" and result.data:
                    state["risk_assessments"] = result.data.get("risk_assessments", [])

                warnings = _iter_warnings(result)
                if warnings:
                    state["warnings"].extend([f"{agent_id}: {warn}" for warn in warnings])

            else:
                state["failed_agents"].append(agent_id)
                error_msg = _compose_error_message(agent_id, result)
                state["errors"].append(error_msg)

        success_count = len([r for r in results.values() if _is_success_result(r)])
        logger.info(f"Strategic advisors completed. Success: {success_count}/{len(all_agents)}")
        return state

    async def _execute_executive_synthesis(self, state: ConsultingPassState) -> ConsultingPassState:
        """Execute executive synthesizer (C5)."""
        logger.info("Executing executive synthesizer (C5)")

        state["current_group"] = "executive_synthesis"
        agents = self.agent_groups["executive_synthesis"]

        results = await self._execute_agent_group(agents, state)

        # Process results
        for agent_id, result in results.items():
            if _is_success_result(result):
                state["completed_agents"].append(agent_id)

                warnings = _iter_warnings(result)
                if warnings:
                    state["warnings"].extend([f"{agent_id}: {warn}" for warn in warnings])

                if agent_id == "C5" and result.data:
                    state["executive_recommendations"] = result.data.get("executive_recommendations", [])
                    state["executive_dashboard"] = result.data.get("executive_dashboard", {})

            else:
                state["failed_agents"].append(agent_id)
                error_msg = _compose_error_message(agent_id, result)
                state["errors"].append(error_msg)

        success_count = len([r for r in results.values() if _is_success_result(r)])
        logger.info(f"Executive synthesis completed. Success: {success_count}/{len(agents)}")
        return state

    async def _execute_low_confidence_fallback(self, state: ConsultingPassState) -> ConsultingPassState:
        """Legacy fallback retained for LangGraph routing; now a no-op."""
        logger.info("Low confidence fallback no longer alters execution; continuing with existing state")
        state["current_group"] = "low_confidence_fallback"
        state["low_confidence_fallback"] = True
        return state

    def _agent_meets_confidence_requirements(self, agent_id: str, state: ConsultingPassState) -> bool:
        """Check if an agent meets confidence requirements for execution."""
        overall_confidence = state["consulting_confidence"]
        required_confidence = self.confidence_thresholds.get(agent_id, 0.7)

        meets_threshold = overall_confidence >= required_confidence

        # Agent-specific additional checks
        if agent_id == "C2":  # Product consultant
            # Need sufficient product-related feedback
            tagged_responses = state["tagged_responses"]
            product_mentions = sum(1 for r in tagged_responses
                                 if any(p in str(r).lower() for p in ["产品", "质量", "口味", "包装"]))
            if product_mentions < 5:
                meets_threshold = False

        elif agent_id == "C3":  # Marketing advisor
            # Need sufficient brand/marketing feedback
            tagged_responses = state["tagged_responses"]
            marketing_mentions = sum(1 for r in tagged_responses
                                   if any(m in str(r).lower() for m in ["品牌", "营销", "广告", "推广", "服务"]))
            if marketing_mentions < 3:
                meets_threshold = False

        elif agent_id == "C4":  # Risk manager
            # Risk analysis needs minimum data quality
            data_quality = state["cleaned_data"].get("data_quality", "low")
            if data_quality == "insufficient":
                meets_threshold = False

        return meets_threshold

    async def _execute_agent_group(self, agent_ids: List[str], state: ConsultingPassState) -> Dict[str, AgentResult]:
        """Execute a group of agents in parallel."""
        tasks = []

        for agent_id in agent_ids:
            task = self._execute_single_agent(agent_id, state)
            tasks.append(task)

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        agent_results: Dict[str, AgentResult] = {}
        for agent_id, result in zip(agent_ids, results):
            if isinstance(result, Exception):
                agent_results[agent_id] = AgentResult(
                    agent_id=agent_id,
                    status=AgentStatus.FAILED,
                    errors=[str(result)]
                )
            else:
                agent_results[agent_id] = result

        return agent_results

    async def _execute_single_agent(self, agent_id: str, state: ConsultingPassState) -> AgentResult:
        """Execute a single agent."""
        try:
            logger.debug(f"Executing consulting agent {agent_id}")

            # Create agent
            agent = self.factory.create_agent(agent_id)

            # Convert state to format expected by agent
            agent_state = self._convert_state_for_agent(state)

            # Execute agent
            result = await agent.execute(agent_state)

            return result

        except Exception as e:
            logger.error(f"Consulting agent {agent_id} execution failed: {e}")
            return AgentResult(
                agent_id=agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)]
            )

    def _convert_state_for_agent(self, state: ConsultingPassState) -> Dict[str, Any]:
        """Convert workflow state to format expected by agents."""
        agent_state = {
            "input_data": state["input_data"],
            "workflow_id": state["workflow_id"],
            "cleaned_data": state["cleaned_data"],
            "nps_metrics": state["nps_metrics"],
            "tagged_responses": state["tagged_responses"],
            "semantic_clusters": state["semantic_clusters"],
            "technical_requirements": state["technical_requirements"],
            "analysis_synthesis": state["analysis_synthesis"],
            "workflow_phase": state["workflow_phase"],
            "consulting_confidence": state["consulting_confidence"],
            "confidence_assessment": state["confidence_assessment"]
        }

        # Add any consulting outputs already generated
        if state.get("strategic_recommendations"):
            agent_state["strategic_recommendations"] = state["strategic_recommendations"]
        if state.get("product_recommendations"):
            agent_state["product_recommendations"] = state["product_recommendations"]
        if state.get("marketing_recommendations"):
            agent_state["marketing_recommendations"] = state["marketing_recommendations"]
        if state.get("risk_assessments"):
            agent_state["risk_assessments"] = state["risk_assessments"]

        return agent_state

    def get_status(self) -> Dict[str, Any]:
        """Get workflow status."""
        return {
            "workflow_type": "Consulting Pass (C1-C5)",
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "checkpoints_enabled": self.enable_checkpoints,
            "confidence_thresholds": self.confidence_thresholds,
            "agent_groups": self.agent_groups,
            "total_agents": sum(len(agents) for agents in self.agent_groups.values())
        }


# Convenience function for direct usage
async def execute_consulting_pass(state: Dict[str, Any], enable_checkpoints: bool = True) -> Dict[str, Any]:
    """
    Execute Consulting Pass workflow.

    Args:
        state: Input state from Analysis Pass
        enable_checkpoints: Whether to enable checkpointing

    Returns:
        Updated state with consulting results
    """
    workflow = ConsultingPassWorkflow(enable_checkpoints=enable_checkpoints)
    return await workflow.execute(state)
