"""
API endpoints for NPS V3 API.
"""

import logging
from typing import Optional
from datetime import datetime
import uuid

from fastapi import APIRouter, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse

from ..schemas import NPSAnalysisRequest, NPSAnalysisResponse
from ..workflow import WorkflowOrchestrator
from ..state import create_initial_state
from ..config import get_settings

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/v3", tags=["NPS Analysis V3"])


@router.post("/analyze", response_model=NPSAnalysisResponse)
async def analyze_nps(
    request: NPSAnalysisRequest,
    background_tasks: BackgroundTasks
) -> NPSAnalysisResponse:
    """
    Execute NPS analysis workflow.

    This endpoint triggers the three-pass analysis:
    - Foundation Pass (A0-A3): Data cleaning, NPS calculation, text analysis
    - Analysis Pass (B1-B9): Domain-specific analysis (if implemented)
    - Consulting Pass (C1-C5): Strategic recommendations (if implemented)
    """
    try:
        # Generate workflow ID
        workflow_id = f"wf_{uuid.uuid4().hex[:12]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        logger.info(f"Starting NPS analysis workflow: {workflow_id}")

        # Convert request to raw data format
        raw_data = [
            {
                "response_id": resp.response_id or f"r_{idx}",
                "timestamp": resp.timestamp,
                "nps_score": resp.nps_score,
                "comment": resp.comment,
                "product_line": resp.product_line,
                "customer_segment": resp.customer_segment,
                "channel": resp.channel,
                "metadata": resp.metadata
            }
            for idx, resp in enumerate(request.survey_responses)
        ]

        # Create workflow orchestrator
        orchestrator = WorkflowOrchestrator(
            workflow_id=workflow_id,
            enable_checkpointing=request.enable_checkpointing,
            enable_caching=get_settings().enable_cache,
            enable_profiling=get_settings().enable_monitoring
        )

        # Prepare config
        config = {
            "language": request.language.value,
            "report_formats": [fmt.value for fmt in request.report_formats],
            "emphasis_areas": [area.value for area in request.emphasis_areas],
            "excluded_topics": request.excluded_topics,
            "include_competitive_analysis": request.include_competitive_analysis,
            "include_technical_requirements": request.include_technical_requirements,
            "confidence_threshold": request.confidence_threshold
        }

        if request.checkpoint_dir:
            config["checkpoint_dir"] = request.checkpoint_dir

        # Execute workflow
        final_state = await orchestrator.execute(raw_data, config)

        # Prepare response
        response = _prepare_response(workflow_id, final_state)

        # Schedule background cleanup if needed
        if request.enable_checkpointing:
            background_tasks.add_task(
                _cleanup_old_checkpoints,
                workflow_id
            )

        logger.info(f"Workflow {workflow_id} completed successfully")

        return response

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


@router.post("/recover/{workflow_id}")
async def recover_workflow(
    workflow_id: str,
    checkpoint_id: Optional[str] = None
) -> NPSAnalysisResponse:
    """
    Recover and continue workflow from checkpoint.

    Args:
        workflow_id: Workflow to recover
        checkpoint_id: Specific checkpoint (latest if None)
    """
    try:
        logger.info(f"Recovering workflow {workflow_id} from checkpoint {checkpoint_id or 'latest'}")

        # Create orchestrator
        orchestrator = WorkflowOrchestrator(
            workflow_id=workflow_id,
            enable_checkpointing=True
        )

        # Execute with recovery
        config = {
            "recover_from_checkpoint": True,
            "checkpoint_id": checkpoint_id
        }

        # Dummy raw data (will be overridden by checkpoint)
        final_state = await orchestrator.execute([], config)

        # Prepare response
        response = _prepare_response(workflow_id, final_state)

        logger.info(f"Workflow {workflow_id} recovered and completed")

        return response

    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=f"Checkpoint not found: {str(e)}")

    except Exception as e:
        logger.error(f"Recovery failed: {e}")
        raise HTTPException(status_code=500, detail=f"Recovery failed: {str(e)}")


@router.get("/status/{workflow_id}")
async def get_workflow_status(workflow_id: str) -> dict:
    """
    Get workflow status and progress.

    Args:
        workflow_id: Workflow identifier

    Returns:
        Status information
    """
    try:
        from ..checkpoint import get_checkpoint_manager

        checkpoint_manager = get_checkpoint_manager()

        # Get checkpoints
        checkpoints = await checkpoint_manager.list_checkpoints(workflow_id)

        if not checkpoints:
            raise HTTPException(status_code=404, detail=f"Workflow {workflow_id} not found")

        # Get latest checkpoint
        latest = checkpoints[0] if checkpoints else None

        return {
            "workflow_id": workflow_id,
            "status": latest.get("phase") if latest else "unknown",
            "checkpoints": len(checkpoints),
            "latest_checkpoint": latest.get("checkpoint_id") if latest else None,
            "last_updated": latest.get("timestamp") if latest else None,
            "agents_completed": latest.get("agents_completed", []) if latest else [],
            "next_agent": latest.get("next_agent") if latest else None
        }

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Status check failed: {str(e)}")


def _prepare_response(
    workflow_id: str,
    state: dict
) -> NPSAnalysisResponse:
    """
    Prepare API response from workflow state.

    Args:
        workflow_id: Workflow identifier
        state: Final workflow state

    Returns:
        NPSAnalysisResponse
    """
    # Determine status
    if state.get("workflow_phase") == "completed":
        status = "completed"
    elif state.get("failed_agents"):
        status = "partial"
    else:
        status = "failed"

    # Calculate completion percentage
    total_agents = 14  # A0-A3, B1-B9, C1-C5
    completed_agents = len(state.get("agent_outputs", {}))
    completion_pct = (completed_agents / total_agents) * 100

    # Prepare executive summary if available
    executive_summary = None

    if state.get("executive_summary"):
        from ..schemas import ExecutiveSummary, NPSMetricsOutput

        nps_metrics = state.get("nps_metrics")

        if nps_metrics:
            nps_output = NPSMetricsOutput(**nps_metrics)

            executive_summary = ExecutiveSummary(
                key_findings=state.get("key_findings", []),
                nps_overview=nps_output,
                top_insights=state.get("top_insights", []),
                critical_issues=state.get("critical_issues", []),
                strategic_recommendations=state.get("strategic_recommendations", []),
                immediate_actions=state.get("immediate_actions", [])
            )

    # Extract insights
    insights = []

    # From Foundation Pass
    if state.get("quantitative_insights"):
        for insight in state["quantitative_insights"]:
            insights.append({
                "insight_id": f"quant_{len(insights)}",
                "category": "quantitative",
                "title": "定量分析洞察",
                "description": insight,
                "confidence": 0.9,
                "supporting_data": [],
                "recommendations": []
            })

    if state.get("qualitative_insights"):
        for insight in state["qualitative_insights"]:
            insights.append({
                "insight_id": f"qual_{len(insights)}",
                "category": "qualitative",
                "title": "定性分析洞察",
                "description": insight,
                "confidence": 0.85,
                "supporting_data": [],
                "recommendations": []
            })

    if state.get("clustering_insights"):
        for insight in state["clustering_insights"]:
            insights.append({
                "insight_id": f"cluster_{len(insights)}",
                "category": "clustering",
                "title": "主题聚类洞察",
                "description": insight,
                "confidence": 0.8,
                "supporting_data": [],
                "recommendations": []
            })

    # Prepare report URLs
    report_urls = {}

    if state.get("output_html"):
        report_urls["html"] = f"/reports/{workflow_id}.html"

    if state.get("output_json"):
        report_urls["json"] = f"/reports/{workflow_id}.json"

    if state.get("output_excel_path"):
        report_urls["excel"] = state["output_excel_path"]

    # Calculate quality scores
    data_quality = state.get("data_quality_score", 0.0)

    if state.get("cleaned_data"):
        cleaned = state["cleaned_data"]
        valid_ratio = cleaned.get("valid_responses", 0) / max(cleaned.get("total_responses", 1), 1)
        data_quality = valid_ratio

    analysis_confidence = 0.0

    if state.get("nps_metrics") and state["nps_metrics"].get("statistical_significance"):
        analysis_confidence = 0.9
    elif state.get("nps_metrics"):
        analysis_confidence = 0.7

    return NPSAnalysisResponse(
        workflow_id=workflow_id,
        status=status,
        completion_percentage=completion_pct,
        executive_summary=executive_summary,
        nps_metrics=state.get("nps_metrics"),
        insights=insights,
        recommendations=state.get("strategic_recommendations", []),
        action_plans=state.get("action_plans", []),
        report_urls=report_urls,
        data_quality_score=data_quality,
        analysis_confidence=analysis_confidence,
        processing_time_ms=state.get("total_processing_time_ms", 0),
        tokens_used=state.get("total_tokens_used", 0),
        errors=state.get("errors", []),
        warnings=state.get("warnings", [])
    )


async def _cleanup_old_checkpoints(workflow_id: str):
    """Background task to cleanup old checkpoints."""
    try:
        from ..checkpoint import get_checkpoint_manager

        checkpoint_manager = get_checkpoint_manager()
        await checkpoint_manager._cleanup_old_checkpoints(workflow_id)

        logger.info(f"Cleaned up old checkpoints for workflow {workflow_id}")

    except Exception as e:
        logger.error(f"Checkpoint cleanup failed: {e}")