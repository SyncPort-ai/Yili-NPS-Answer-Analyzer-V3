"""
Pass 2 Analysis LangGraph Workflow
LangGraph-based workflow for executing the Analysis Pass (B1-B9) with parallel execution groups.
"""

import logging
from typing import Dict, Any, List, TypedDict
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


def _is_success_result(result: Any) -> bool:
    """Determine if a result represents a successful agent run."""
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


class AnalysisPassState(TypedDict):
    """State for Analysis Pass workflow"""
    # Core data
    input_data: Dict[str, Any]
    workflow_id: str

    # Foundation outputs (from Pass 1)
    cleaned_data: Dict[str, Any]
    nps_metrics: Dict[str, Any]
    tagged_responses: List[Dict[str, Any]]
    semantic_clusters: List[Dict[str, Any]]

    # Analysis outputs (Pass 2)
    technical_requirements: List[Dict[str, Any]]
    passive_analysis: Dict[str, Any]
    detractor_analysis: Dict[str, Any]
    text_clustering: Dict[str, Any]
    driver_analysis: Dict[str, Any]
    product_dimension_analysis: Dict[str, Any]
    geographic_dimension_analysis: Dict[str, Any]
    channel_dimension_analysis: Dict[str, Any]
    analysis_synthesis: Dict[str, Any]

    # Workflow control
    workflow_phase: str
    current_group: str
    completed_agents: List[str]
    failed_agents: List[str]
    errors: List[str]
    warnings: List[str]


class AnalysisPassWorkflow:
    """
    LangGraph workflow for Analysis Pass execution.

    Executes B1-B9 agents in parallel groups:
    - Group 1: Segment Analysis (B1-B3)
    - Group 2: Advanced Analytics (B4-B5)
    - Group 3: Dimensional Analysis (B6-B8)
    - Group 4: Analysis Coordinator (B9)
    """

    def __init__(self, enable_checkpoints: bool = True):
        """Initialize Analysis Pass workflow."""
        self.factory = AgentFactory()
        self.enable_checkpoints = enable_checkpoints
        self.memory = MemorySaver() if LANGGRAPH_AVAILABLE and enable_checkpoints else None

        # Define agent groups for parallel execution
        self.agent_groups = {
            "segment_analysis": ["B1", "B2", "B3"],
            "advanced_analytics": ["B4", "B5"],
            "dimensional_analysis": ["B6", "B7", "B8"],
            "synthesis": ["B9"]
        }

        if LANGGRAPH_AVAILABLE:
            self.graph = self._build_langgraph()
        else:
            self.graph = None
            logger.warning("LangGraph not available, using simplified execution")

    def _build_langgraph(self) -> StateGraph:
        """Build LangGraph StateGraph for Analysis Pass."""
        workflow = StateGraph(AnalysisPassState)

        # Add nodes for each group
        workflow.add_node("segment_analysis", self._execute_segment_analysis)
        workflow.add_node("advanced_analytics", self._execute_advanced_analytics)
        workflow.add_node("dimensional_analysis", self._execute_dimensional_analysis)
        workflow.add_node("synthesis", self._execute_synthesis)

        # Define sequential flow
        workflow.add_edge("segment_analysis", "advanced_analytics")
        workflow.add_edge("advanced_analytics", "dimensional_analysis")
        workflow.add_edge("dimensional_analysis", "synthesis")
        workflow.add_edge("synthesis", END)

        # Set entry point
        workflow.set_entry_point("segment_analysis")

        return workflow.compile(checkpointer=self.memory)

    async def execute(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the Analysis Pass workflow.

        Args:
            state: Input state from Foundation Pass

        Returns:
            Updated state with analysis results
        """
        logger.info("Starting Analysis Pass workflow execution")

        # Convert to workflow state
        analysis_state = self._prepare_analysis_state(state)

        if self.graph and LANGGRAPH_AVAILABLE:
            # Use LangGraph execution
            config = {"thread_id": analysis_state["workflow_id"]}
            final_state = await self.graph.ainvoke(analysis_state, config=config)
        else:
            # Use simplified execution
            final_state = await self._execute_simplified(analysis_state)

        # Convert back to NPSAnalysisState format
        result_state = self._prepare_output_state(final_state, state)

        logger.info("Analysis Pass workflow completed")
        return result_state

    def _prepare_analysis_state(self, state: Dict[str, Any]) -> AnalysisPassState:
        """Prepare state for analysis workflow."""
        return AnalysisPassState(
            input_data=state.get("input_data", {}),
            workflow_id=state.get("workflow_id", "unknown"),

            # Foundation outputs
            cleaned_data=state.get("cleaned_data", {}),
            nps_metrics=state.get("nps_metrics", {}),
            tagged_responses=state.get("tagged_responses", []),
            semantic_clusters=state.get("semantic_clusters", []),

            # Initialize analysis outputs
            technical_requirements=[],
            passive_analysis={},
            detractor_analysis={},
            text_clustering={},
            driver_analysis={},
            product_dimension_analysis={},
            geographic_dimension_analysis={},
            channel_dimension_analysis={},
            analysis_synthesis={},

            # Workflow control
            workflow_phase="analysis",
            current_group="segment_analysis",
            completed_agents=[],
            failed_agents=[],
            errors=[],
            warnings=[]
        )

    def _prepare_output_state(self, analysis_state: AnalysisPassState, original_state: Dict[str, Any]) -> Dict[str, Any]:
        """Convert analysis state back to NPSAnalysisState format."""
        # Merge analysis results into original state
        result_state = original_state.copy()

        # Add analysis outputs
        if analysis_state.get("technical_requirements"):
            result_state["technical_requirements"] = analysis_state["technical_requirements"]
        if analysis_state.get("passive_analysis"):
            result_state["passive_analysis"] = analysis_state["passive_analysis"]
        if analysis_state.get("detractor_analysis"):
            result_state["detractor_analysis"] = analysis_state["detractor_analysis"]
        if analysis_state.get("text_clustering"):
            result_state["text_clustering"] = analysis_state["text_clustering"]
        if analysis_state.get("driver_analysis"):
            result_state["driver_analysis"] = analysis_state["driver_analysis"]
        if analysis_state.get("product_dimension_analysis"):
            result_state["product_dimension_analysis"] = analysis_state["product_dimension_analysis"]
        if analysis_state.get("geographic_dimension_analysis"):
            result_state["geographic_dimension_analysis"] = analysis_state["geographic_dimension_analysis"]
        if analysis_state.get("channel_dimension_analysis"):
            result_state["channel_dimension_analysis"] = analysis_state["channel_dimension_analysis"]
        if analysis_state.get("analysis_synthesis"):
            result_state["analysis_synthesis"] = analysis_state["analysis_synthesis"]

        # Update workflow metadata
        result_state["workflow_phase"] = "analysis_completed"
        result_state["completed_agents"] = analysis_state.get("completed_agents", [])
        result_state["failed_agents"] = analysis_state.get("failed_agents", [])

        if analysis_state.get("errors"):
            result_state.setdefault("errors", [])
            result_state["errors"].extend(analysis_state["errors"])

        if analysis_state.get("warnings"):
            result_state.setdefault("warnings", [])
            result_state["warnings"].extend(analysis_state["warnings"])

        return result_state

    async def _execute_simplified(self, state: AnalysisPassState) -> AnalysisPassState:
        """Simplified execution without LangGraph."""
        logger.info("Executing simplified Analysis Pass workflow")

        # Execute groups sequentially
        state = await self._execute_segment_analysis(state)
        state = await self._execute_advanced_analytics(state)
        state = await self._execute_dimensional_analysis(state)
        state = await self._execute_synthesis(state)

        return state

    async def _execute_segment_analysis(self, state: AnalysisPassState) -> AnalysisPassState:
        """Execute segment analysis agents (B1-B3) in parallel."""
        logger.info("Executing segment analysis group (B1-B3)")

        state["current_group"] = "segment_analysis"
        agents = self.agent_groups["segment_analysis"]

        results = await self._execute_agent_group(agents, state)

        # Process results
        for agent_id, result in results.items():
            if _is_success_result(result):
                state["completed_agents"].append(agent_id)

                # Store agent-specific outputs
                result_data = getattr(result, "data", None)
                if agent_id == "B1" and result_data:
                    state["technical_requirements"] = result_data.get("technical_requirements", [])
                elif agent_id == "B2" and result_data:
                    state["passive_analysis"] = result_data
                elif agent_id == "B3" and result_data:
                    state["detractor_analysis"] = result_data

                warnings = _iter_warnings(result)
                if warnings:
                    state["warnings"].extend([f"{agent_id}: {warn}" for warn in warnings])
            else:
                state["failed_agents"].append(agent_id)
                error_msg = _compose_error_message(agent_id, result)
                state["errors"].append(error_msg)

        success_count = len([r for r in results.values() if _is_success_result(r)])
        logger.info(f"Segment analysis completed. Success: {success_count}/{len(agents)}")
        return state

    async def _execute_advanced_analytics(self, state: AnalysisPassState) -> AnalysisPassState:
        """Execute advanced analytics agents (B4-B5) in parallel."""
        logger.info("Executing advanced analytics group (B4-B5)")

        state["current_group"] = "advanced_analytics"
        agents = self.agent_groups["advanced_analytics"]

        results = await self._execute_agent_group(agents, state)

        # Process results
        for agent_id, result in results.items():
            if _is_success_result(result):
                state["completed_agents"].append(agent_id)

                # Store agent-specific outputs
                result_data = getattr(result, "data", None)
                if agent_id == "B4" and result_data:
                    state["text_clustering"] = result_data
                elif agent_id == "B5" and result_data:
                    state["driver_analysis"] = result_data

                warnings = _iter_warnings(result)
                if warnings:
                    state["warnings"].extend([f"{agent_id}: {warn}" for warn in warnings])
            else:
                state["failed_agents"].append(agent_id)
                error_msg = _compose_error_message(agent_id, result)
                state["errors"].append(error_msg)

        success_count = len([r for r in results.values() if _is_success_result(r)])
        logger.info(f"Advanced analytics completed. Success: {success_count}/{len(agents)}")
        return state

    async def _execute_dimensional_analysis(self, state: AnalysisPassState) -> AnalysisPassState:
        """Execute dimensional analysis agents (B6-B8) in parallel."""
        logger.info("Executing dimensional analysis group (B6-B8)")

        state["current_group"] = "dimensional_analysis"
        agents = self.agent_groups["dimensional_analysis"]

        results = await self._execute_agent_group(agents, state)

        # Process results
        for agent_id, result in results.items():
            if _is_success_result(result):
                state["completed_agents"].append(agent_id)

                # Store agent-specific outputs
                result_data = getattr(result, "data", None)
                if agent_id == "B6" and result_data:
                    state["product_dimension_analysis"] = result_data
                elif agent_id == "B7" and result_data:
                    state["geographic_dimension_analysis"] = result_data
                elif agent_id == "B8" and result_data:
                    state["channel_dimension_analysis"] = result_data

                warnings = _iter_warnings(result)
                if warnings:
                    state["warnings"].extend([f"{agent_id}: {warn}" for warn in warnings])
            else:
                state["failed_agents"].append(agent_id)
                error_msg = _compose_error_message(agent_id, result)
                state["errors"].append(error_msg)

        success_count = len([r for r in results.values() if _is_success_result(r)])
        logger.info(f"Dimensional analysis completed. Success: {success_count}/{len(agents)}")
        return state

    async def _execute_synthesis(self, state: AnalysisPassState) -> AnalysisPassState:
        """Execute analysis coordinator (B9)."""
        logger.info("Executing analysis synthesis (B9)")

        state["current_group"] = "synthesis"
        agents = self.agent_groups["synthesis"]

        results = await self._execute_agent_group(agents, state)

        # Process results
        for agent_id, result in results.items():
            if _is_success_result(result):
                state["completed_agents"].append(agent_id)

                # Store synthesis results
                result_data = getattr(result, "data", None)
                if agent_id == "B9" and result_data:
                    state["analysis_synthesis"] = result_data

                warnings = _iter_warnings(result)
                if warnings:
                    state["warnings"].extend([f"{agent_id}: {warn}" for warn in warnings])
            else:
                state["failed_agents"].append(agent_id)
                error_msg = _compose_error_message(agent_id, result)
                state["errors"].append(error_msg)

        success_count = len([r for r in results.values() if _is_success_result(r)])
        logger.info(f"Analysis synthesis completed. Success: {success_count}/{len(agents)}")
        return state

    async def _execute_agent_group(self, agent_ids: List[str], state: AnalysisPassState) -> Dict[str, Dict[str, Any]]:
        """Execute a group of agents in parallel."""
        tasks = []

        for agent_id in agent_ids:
            task = self._execute_single_agent(agent_id, state)
            tasks.append(task)

        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        agent_results: Dict[str, Any] = {}
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

    async def _execute_single_agent(self, agent_id: str, state: AnalysisPassState) -> Dict[str, Any]:
        """Execute a single agent."""
        try:
            logger.debug(f"Executing agent {agent_id}")

            # Create agent
            agent = self.factory.create_agent(agent_id)

            # Convert state to format expected by agent
            agent_state = self._convert_state_for_agent(state)

            # Execute agent
            result = await agent.execute(agent_state)

            return result

        except Exception as e:
            logger.error(f"Agent {agent_id} execution failed: {e}")
            return AgentResult(
                agent_id=agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)]
            )

    def _convert_state_for_agent(self, state: AnalysisPassState) -> Dict[str, Any]:
        """Convert workflow state to format expected by agents."""
        return {
            "input_data": state["input_data"],
            "workflow_id": state["workflow_id"],
            "cleaned_data": state["cleaned_data"],
            "nps_metrics": state["nps_metrics"],
            "tagged_responses": state["tagged_responses"],
            "semantic_clusters": state["semantic_clusters"],
            "technical_requirements": state.get("technical_requirements", []),
            "passive_analysis": state.get("passive_analysis", {}),
            "detractor_analysis": state.get("detractor_analysis", {}),
            "text_clustering": state.get("text_clustering", {}),
            "driver_analysis": state.get("driver_analysis", {}),
            "product_dimension_analysis": state.get("product_dimension_analysis", {}),
            "geographic_dimension_analysis": state.get("geographic_dimension_analysis", {}),
            "channel_dimension_analysis": state.get("channel_dimension_analysis", {}),
            "workflow_phase": state["workflow_phase"]
        }

    def get_status(self) -> Dict[str, Any]:
        """Get workflow status."""
        return {
            "workflow_type": "Analysis Pass (B1-B9)",
            "langgraph_available": LANGGRAPH_AVAILABLE,
            "checkpoints_enabled": self.enable_checkpoints,
            "agent_groups": self.agent_groups,
            "total_agents": sum(len(agents) for agents in self.agent_groups.values())
        }


# Convenience function for direct usage
async def execute_analysis_pass(state: Dict[str, Any], enable_checkpoints: bool = True) -> Dict[str, Any]:
    """
    Execute Analysis Pass workflow.

    Args:
        state: Input state from Foundation Pass
        enable_checkpoints: Whether to enable checkpointing

    Returns:
        Updated state with analysis results
    """
    workflow = AnalysisPassWorkflow(enable_checkpoints=enable_checkpoints)
    return await workflow.execute(state)
