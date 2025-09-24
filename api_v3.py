"""FastAPI router for the NPS V3 Multi-Agent Analysis System.

This module provides the API endpoints for the new V3 system featuring
three-pass analysis: Foundation, Analysis, and Consulting passes.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import numpy as np

from fastapi import APIRouter, Body, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel

# Import agent logger
from agent_logger import get_agent_logger

router = APIRouter()

logger = logging.getLogger("nps_report_v3.api")
request_semaphore = asyncio.Semaphore(2)


async def execute_workflow_with_logging(workflow, raw_data: List[Dict],
                                        config: Optional[Dict] = None,
                                        request_id: Optional[str] = None) -> Dict[str, Any]:
    """Execute workflow with comprehensive agent logging.

    Args:
        workflow: The workflow instance to execute
        raw_data: Raw survey data
        config: Analysis configuration
        request_id: Request identifier for logging

    Returns:
        Workflow execution result with agent logs
    """
    # Initialize agent logger for this request
    agent_log = get_agent_logger(
        log_dir=f"outputs/agent_logs/{datetime.now().strftime('%Y%m%d')}",
        log_level="DEBUG",
        reset=True  # Create new logger for each request
    )

    # Log workflow start
    agent_log.logger.info(f"Starting workflow for request: {request_id or 'unknown'}")
    agent_log.logger.info(f"Input data: {len(raw_data)} survey responses")

    try:
        # Execute the workflow
        result = await workflow.execute(raw_data, config)

        # Extract and log agent outputs from the result
        if isinstance(result, dict):
            # Log Foundation Pass agents (A0-A3)
            if "agent_outputs" in result:
                agent_outputs = result.get("agent_outputs", {})

                # Foundation Pass
                for agent_id in ["A0", "A1", "A2", "A3"]:
                    if agent_id in agent_outputs:
                        agent_name = _get_agent_name(agent_id)
                        agent_log.log_agent_start(agent_id, agent_name,
                                                 {"input_size": len(raw_data)})
                        agent_log.log_agent_output(agent_id, agent_outputs[agent_id],
                                                  success=True)

                # Analysis Pass
                for agent_id in ["B1", "B2", "B3", "B4", "B5", "B6", "B7", "B8", "B9"]:
                    if agent_id in agent_outputs:
                        agent_name = _get_agent_name(agent_id)
                        agent_log.log_agent_start(agent_id, agent_name,
                                                 result.get("pass1_foundation"))
                        agent_log.log_agent_output(agent_id, agent_outputs[agent_id],
                                                  success=True)

                # Consulting Pass
                for agent_id in ["C1", "C2", "C3", "C4", "C5"]:
                    if agent_id in agent_outputs:
                        agent_name = _get_agent_name(agent_id)
                        agent_log.log_agent_start(agent_id, agent_name,
                                                 result.get("pass2_analysis"))
                        agent_log.log_agent_output(agent_id, agent_outputs[agent_id],
                                                  success=True)

            # Check for any failed agents
            if "failed_agents" in result and result["failed_agents"]:
                for failed_agent in result["failed_agents"]:
                    agent_log.log_agent_output(failed_agent, None,
                                              success=False,
                                              error=f"Agent {failed_agent} failed")

            # Log workflow summary
            agent_log.log_workflow_summary(result)

            # Add agent log summary to result
            result["agent_log_summary"] = agent_log.get_session_summary()
            result["agent_log_dir"] = str(agent_log.log_dir)

    except Exception as e:
        agent_log.logger.error(f"Workflow execution failed: {e}")
        agent_log.logger.error(traceback.format_exc())
        agent_log.log_workflow_summary({"error": str(e)})
        raise

    return result

def _get_agent_name(agent_id: str) -> str:
    """Get human-readable agent name from agent ID."""
    agent_names = {
        # Foundation Pass
        "A0": "Data Ingestion Agent",
        "A1": "Quantitative Analysis Agent",
        "A2": "Qualitative Analysis Agent",
        "A3": "Semantic Clustering Agent",

        # Analysis Pass
        "B1": "Technical Requirements Agent",
        "B2": "Passive Customer Analyst",
        "B3": "Detractor Customer Analyst",
        "B4": "Text Clustering Agent",
        "B5": "Driver Analysis Agent",
        "B6": "Product Dimension Agent",
        "B7": "Geographic Dimension Agent",
        "B8": "Channel Dimension Agent",
        "B9": "Analysis Coordinator Agent",

        # Consulting Pass
        "C1": "Strategic Advisor Agent",
        "C2": "Product Consultant Agent",
        "C3": "Marketing Advisor Agent",
        "C4": "Risk Manager Agent",
        "C5": "Executive Synthesizer Agent"
    }
    return agent_names.get(agent_id, f"Unknown Agent ({agent_id})")

def make_json_serializable(obj: Any) -> Any:
    """Convert numpy objects and other non-serializable objects to JSON-compatible types."""
    if isinstance(obj, dict):
        return {key: make_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, (np.integer, np.floating, np.bool_, np.complexfloating)):
        return obj.item()  # Convert numpy scalars to Python scalars
    elif isinstance(obj, np.ndarray):
        return obj.tolist()  # Convert numpy arrays to lists
    elif hasattr(obj, '__dict__'):
        try:
            # Try to convert objects with __dict__ to dictionaries
            return make_json_serializable(vars(obj))
        except (TypeError, AttributeError):
            # If that fails, try to convert to string
            return str(obj)
    elif obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    else:
        # Convert other objects to string as fallback
        return str(obj)

# Global V3 system state
V3_IMPORT_ERROR: Optional[str] = None
V3_AVAILABLE = False
_v3_workflow: Optional[Any] = None
_v3_monitoring: Optional[Any] = None

try:
    from nps_report_v3.workflow import WorkflowOrchestrator
    from nps_report_v3.models.request import NPSAnalysisRequest
    from nps_report_v3.models.response import NPSAnalysisResponse
    from nps_report_v3.monitoring.integration import MonitoringIntegration
    V3_AVAILABLE = True
    logger.info("✅ NPS V3 multi-agent system successfully imported")
except Exception as exc:  # pragma: no cover
    WorkflowOrchestrator = None  # type: ignore
    NPSAnalysisRequest = None  # type: ignore
    NPSAnalysisResponse = None  # type: ignore
    MonitoringIntegration = None  # type: ignore
    V3_IMPORT_ERROR = f"{exc}\n{traceback.format_exc()}"
    logger.error("Failed to import NPS V3 system: %s", V3_IMPORT_ERROR)


def get_v3_workflow():
    """Get or create the V3 workflow instance."""
    global _v3_workflow, _v3_monitoring

    if not V3_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=f"NPS V3 system unavailable. Import error: {V3_IMPORT_ERROR}"
        )

    if _v3_workflow is None:
        try:
            # Initialize monitoring
            _v3_monitoring = MonitoringIntegration()
            logger.info("🔧 Initialized V3 performance monitoring")

            # Initialize workflow
            _v3_workflow = WorkflowOrchestrator()
            logger.info("🚀 Initialized V3 analysis workflow")

        except Exception as e:
            logger.error(f"❌ Failed to initialize V3 workflow: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to initialize V3 workflow: {e}")

    return _v3_workflow, _v3_monitoring


def _persist_v3_outputs(result: Dict[str, Any]) -> None:
    """Persist V3 analysis outputs to filesystem."""
    try:
        outputs_dir = Path(__file__).resolve().parent / "outputs"
        v3_results_dir = outputs_dir / "v3_results"
        v3_reports_dir = outputs_dir / "v3_reports"

        # Ensure directories exist
        v3_results_dir.mkdir(parents=True, exist_ok=True)
        v3_reports_dir.mkdir(parents=True, exist_ok=True)

        # Generate timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        request_id = result.get("response_id", f"v3_{timestamp}")

        # Save JSON result
        result_file = v3_results_dir / f"v3_{request_id}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)

        # Save HTML report if available
        html_report = result.get("executive_dashboard", {}).get("html_report")
        if html_report:
            report_file = v3_reports_dir / f"v3_{request_id}.html"
            with open(report_file, 'w', encoding='utf-8') as f:
                f.write(html_report)

        logger.info(f"💾 V3 outputs persisted successfully: {request_id}")

    except Exception as exc:  # pragma: no cover - persistence is best-effort
        logger.warning(f"Failed to persist V3 outputs: {exc}")


def _load_v3_sample_payload() -> Dict[str, Any]:
    """Load V2 client format as default example for backward compatibility."""
    try:
        # Load actual V2 client format file
        import json
        from pathlib import Path

        data_file = Path(__file__).resolve().parent / "data" / "V2-sample-product-survey-input-100-yili-format.json"

        with open(data_file, 'r', encoding='utf-8') as f:
            v2_data = json.load(f)

        # Return the actual V2 format that clients will send
        # V3 API will handle the conversion internally
        return v2_data

    except Exception as e:
        logger.warning(f"Failed to load V2 sample data: {e}, falling back to minimal V2 format")
        # Fallback to minimal V2 format structure
        return {
            "yili_survey_data_input": {
                "base_analysis_result": "样本分析结果：NPS为示例数据，用于API测试。",
                "cross_analysis_result": None,
                "kano_analysis_result": None,
                "psm_analysis_result": None,
                "maxdiff_analysis_result": None,
                "nps_analysis_result": "示例NPS分析结果：用于V3 API兼容性测试。",
                "data_list": [
                    {
                        "样本编码": "1",
                        "作答类型": "正式",
                        "AI标记状态": "未标记",
                        "AI标记原因": "",
                        "人工标记状态": "未标记",
                        "人工标记原因": "",
                        "作答ID": "demo_001",
                        "投放方式": "链接二维码",
                        "作答状态": "已完成",
                        "答题时间": "2024-01-15 10:00:00",
                        "提交时间": "2024-01-15 10:05:00",
                        "作答时长": "5分钟",
                        "Q1您向朋友或同事推荐我们的可能性多大？": "9分",
                        "Q2 您不愿意推荐我们的主要因素有哪些？": {
                            "不喜欢品牌或代言人、赞助综艺等宣传内容": "-",
                            "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）": "-",
                            "产品价格太贵，性价比不高": "-",
                            "促销活动不好（如对赠品、活动力度/规则等不满意）": "-",
                            "产品口味口感不好": "-",
                            "饮用后感觉不舒服（如身体有腹胀、腹泻等不良反应）": "-",
                            "产品品质不稳定性（如发生变质、有异物等）": "-",
                            "没有感知到产品宣传的功能": "-",
                            "物流配送、门店导购、售后等服务体验不好": "-",
                            "其他": "-"
                        },
                        "Q3 您不愿意推荐我们的具体原因是什么？": "",
                        "Q4 您愿意推荐我们的主要因素有哪些？": {
                            "喜欢品牌或代言人、赞助综艺等宣传内容": "喜欢品牌或代言人、赞助综艺等宣传内容",
                            "包装设计好（如醒目、美观，材质好，便携、方便打开等）": "包装设计好（如醒目、美观，材质好，便携、方便打开等）",
                            "产品物有所值、性价比高": "-",
                            "对促销活动满意（如赠品、活动力度/规则等）": "-",
                            "产品口味口感好": "产品口味口感好",
                            "饮用后体感舒适，无不良反应": "-",
                            "满意产品宣传的功能（如促进消化、增强免疫、助睡眠等）": "-",
                            "物流配送、门店导购、售后等服务体验好": "-",
                            "其他": "-"
                        },
                        "Q5 您愿意推荐我们的具体原因是什么？": "产品质量很好，口感不错，包装也很精美。"
                    }
                ]
            }
        }


# === HEALTH AND INFO ENDPOINTS ===

@router.get("/nps-report-v3/agent-logs")
async def get_agent_logs(
    date: str = Query(default=None, description="Date in YYYYMMDD format"),
    session_id: str = Query(default=None, description="Session ID to retrieve logs for")
):
    """Retrieve agent execution logs.

    Args:
        date: Date for log files (YYYYMMDD format)
        session_id: Specific session ID to retrieve

    Returns:
        Agent log files or summary
    """
    try:
        log_base = Path("outputs/agent_logs")

        # If no date provided, use today
        if not date:
            date = datetime.now().strftime("%Y%m%d")

        log_dir = log_base / date

        if not log_dir.exists():
            return JSONResponse(
                status_code=404,
                content={
                    "error": "No logs found for the specified date",
                    "date": date,
                    "available_dates": [d.name for d in log_base.iterdir() if d.is_dir()]
                }
            )

        # If session_id provided, return specific session
        if session_id:
            session_file = log_dir / f"{session_id}_session_summary.json"
            if session_file.exists():
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                return JSONResponse(content={
                    "session_id": session_id,
                    "date": date,
                    "data": session_data
                })
            else:
                return JSONResponse(
                    status_code=404,
                    content={
                        "error": f"Session {session_id} not found",
                        "date": date
                    }
                )

        # Otherwise, list available sessions
        session_files = list(log_dir.glob("*_session_summary.json"))
        sessions = []

        for sf in session_files:
            try:
                with open(sf, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    metadata = data.get("metadata", {})
                    sessions.append({
                        "session_id": metadata.get("session_id", sf.stem.replace("_session_summary", "")),
                        "start_time": metadata.get("start_time"),
                        "agents_executed": len(metadata.get("agents_executed", [])),
                        "total_execution_time_ms": metadata.get("total_execution_time_ms", 0),
                        "errors_count": len(metadata.get("errors", [])),
                        "warnings_count": len(metadata.get("warnings", [])),
                        "file": sf.name
                    })
            except Exception as e:
                logger.warning(f"Could not read session file {sf}: {e}")

        return JSONResponse(content={
            "date": date,
            "sessions_count": len(sessions),
            "sessions": sessions
        })

    except Exception as e:
        logger.error(f"Error retrieving agent logs: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Failed to retrieve agent logs",
                "details": str(e)
            }
        )

@router.get("/nps-report-v3/health")
async def v3_health():
    """V3 system health check."""
    return {
        "status": "healthy" if V3_AVAILABLE else "unavailable",
        "v3_available": V3_AVAILABLE,
        "v3_import_error": V3_IMPORT_ERROR,
        "timestamp": datetime.now().isoformat(),
        "system": "NPS V3 Multi-Agent Analysis System"
    }


@router.get("/nps-report-v3/info")
async def v3_info():
    """V3 system information."""
    info = {
        "system": "NPS V3 Multi-Agent Analysis System",
        "version": "3.0.0",
        "available": V3_AVAILABLE,
        "capabilities": [
            "Foundation Pass (A0-A3): Data validation and preprocessing",
            "Analysis Pass (B1-B9): Multi-dimensional NPS analysis",
            "Consulting Pass (C1-C5): Strategic insights and recommendations"
        ] if V3_AVAILABLE else [],
        "endpoints": [
            "/nps-report-v3 - Complete V3 analysis workflow",
            "/nps-report-v3/demo - Run with demo data",
            "/nps-report-v3/health - Health check",
            "/nps-report-v3/info - System info"
        ] if V3_AVAILABLE else []
    }

    if V3_IMPORT_ERROR:
        info["import_error"] = V3_IMPORT_ERROR

    return info


# === MAIN ANALYSIS ENDPOINT ===

def _convert_v2_to_v3_format(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Convert V2 client format to V3 internal format for backward compatibility."""
    # Check if it's already V3 format
    if "survey_data" in payload and "survey_responses" in payload["survey_data"]:
        return payload

    # Check if it's V2 format
    if "yili_survey_data_input" not in payload:
        raise ValueError("Invalid input format: must contain either 'survey_data' (V3) or 'yili_survey_data_input' (V2)")

    yili_data = payload["yili_survey_data_input"]
    data_list = yili_data.get("data_list", [])

    # Convert V2 format to V3 format
    survey_responses = []

    for i, item in enumerate(data_list):
        nps_score_str = item.get("Q1您向朋友或同事推荐我们的可能性多大？", "5分")
        nps_score = int(nps_score_str.replace("分", "")) if nps_score_str.replace("分", "").isdigit() else 5

        # Combine feedback from multiple fields
        feedback_parts = []
        if item.get("Q3 您不愿意推荐我们的具体原因是什么？"):
            feedback_parts.append(f"不推荐原因: {item['Q3 您不愿意推荐我们的具体原因是什么？']}")
        if item.get("Q5 您愿意推荐我们的具体原因是什么？"):
            feedback_parts.append(f"推荐原因: {item['Q5 您愿意推荐我们的具体原因是什么？']}")

        # Add structured feedback from multiple choice questions
        q2_factors = item.get("Q2 您不愿意推荐我们的主要因素有哪些？", {})
        for factor, value in q2_factors.items():
            if value != "-":
                feedback_parts.append(f"不满意因素: {factor}")

        q4_factors = item.get("Q4 您愿意推荐我们的主要因素有哪些？", {})
        for factor, value in q4_factors.items():
            if value != "-":
                feedback_parts.append(f"满意因素: {factor}")

        feedback_text = ". ".join(feedback_parts) if feedback_parts else f"NPS评分{nps_score}分的用户反馈"

        survey_responses.append({
            "response_id": item.get("作答ID", f"resp_{i+1}"),
            "customer_data": {
                "customer_id": item.get("样本编码", f"cust_{i+1}"),
                "demographics": {
                    "survey_method": item.get("投放方式", ""),
                    "completion_time": item.get("作答时长", ""),
                    "status": item.get("作答状态", ""),
                    "ai_tag_status": item.get("AI标记状态", ""),
                    "response_type": item.get("作答类型", "")
                }
            },
            "nps_score": nps_score,
            "feedback_text": feedback_text,
            "metadata": {
                "survey_date": item.get("答题时间", "2024-01-01"),
                "submit_time": item.get("提交时间", ""),
                "channel": item.get("投放方式", "问卷调查"),
                "response_type": item.get("作答类型", "正式"),
                "duration": item.get("作答时长", ""),
                "ai_tag_reason": item.get("AI标记原因", ""),
                "manual_tag_status": item.get("人工标记状态", ""),
                "manual_tag_reason": item.get("人工标记原因", "")
            }
        })

    # Generate request ID from metadata or create one
    request_id = f"v2_converted_{int(time.time())}"

    return {
        "request_id": request_id,
        "survey_data": {
            "survey_responses": survey_responses
        },
        "analysis_config": {
            "enable_foundation_pass": True,
            "enable_analysis_pass": True,
            "enable_consulting_pass": True,
            "output_format": "comprehensive",
            "language": "zh-CN",
            "include_html_report": True,
            "confidence_threshold": 0.6
        },
        "metadata": {
            "source": "v2_client_data",
            "analyst_id": "system",
            "priority": "normal",
            "original_format": "yili_survey_data_input",
            "original_nps": yili_data.get("base_analysis_result", ""),
            "total_samples": len(data_list),
            "conversion_timestamp": datetime.now().isoformat()
        }
    }


@router.post("/nps-report-v3")
async def nps_report_v3(payload: Dict[str, Any] = Body(..., example=_load_v3_sample_payload())):
    """
    Complete NPS V3 Multi-Agent Analysis Workflow

    Supports both V2 client format (yili_survey_data_input) and V3 format for backward compatibility.

    Executes the full three-pass analysis:
    - Foundation Pass (A0-A3): Data validation, preprocessing, quality assurance
    - Analysis Pass (B1-B9): Multi-dimensional analysis across 9 specialized agents
    - Consulting Pass (C1-C5): Strategic insights and actionable recommendations

    Returns comprehensive analysis results with dual-format output (JSON + HTML).
    """
    if not V3_AVAILABLE:
        error_msg = f"V3 system unavailable: {V3_IMPORT_ERROR}"
        logger.error(error_msg)
        return JSONResponse(
            status_code=503,
            content={
                "error": "V3 系统不可用",
                "details": error_msg,
                "available_alternatives": [
                    "/nps-report-v1 - V1 multi-agent workflow",
                    "/nps-report-v2 - V2 seven-agent workflow"
                ],
            },
        )

    async with request_semaphore:
        start_time = time.perf_counter()

        try:
            workflow, monitoring = get_v3_workflow()

            # Convert V2 format to V3 format for backward compatibility
            try:
                v3_payload = _convert_v2_to_v3_format(payload)
                logger.info(f"🔄 Converted input format: {v3_payload['metadata'].get('original_format', 'v3_native')}")
            except Exception as e:
                logger.error(f"Format conversion failed: {e}")
                raise HTTPException(status_code=400, detail=f"Invalid input format: {e}")

            # Validate request using V3 models
            validated_request = NPSAnalysisRequest(**v3_payload)
            logger.info(f"🔍 Starting V3 analysis for request: {validated_request.request_id}")

            # Execute workflow with monitoring
            with monitoring.monitor.track_workflow("nps_v3_analysis", "complete_workflow"):
                # Extract raw survey data and config from validated request
                raw_data = [resp.dict() for resp in validated_request.survey_data.survey_responses]
                config = validated_request.analysis_config.dict() if validated_request.analysis_config else None

                # Execute with comprehensive agent logging
                result = await execute_workflow_with_logging(
                    workflow, raw_data, config, validated_request.request_id
                )

            processing_time = time.perf_counter() - start_time
            logger.info(f"✅ V3 analysis completed successfully for: {validated_request.request_id} (took {processing_time:.2f}s)")

            # Add processing metadata
            if isinstance(result, dict):
                result["request_id"] = validated_request.request_id
                result["analysis_status"] = "completed"
                result["timestamp"] = datetime.now().isoformat()

                # Add compatibility aliases
                if "pass1_foundation" in result:
                    result["foundation_pass"] = result["pass1_foundation"]
                    # Add field mappings for compatibility
                    if "nps_metrics" in result["foundation_pass"]:
                        nps_calc = dict(result["foundation_pass"]["nps_metrics"])
                        # Add missing fields for compatibility
                        if "sample_size" in nps_calc:
                            nps_calc["total_responses"] = nps_calc["sample_size"]
                            nps_calc["valid_responses"] = nps_calc["sample_size"]
                        result["foundation_pass"]["nps_calculation"] = nps_calc
                    # Add confidence assessment from the confidence field if present
                    if "confidence" in result:
                        result["foundation_pass"]["confidence_assessment"] = {
                            "confidence": result["confidence"],
                            "status": "completed" if result.get("confidence", 0) >= 0.7 else "low_confidence"
                        }

                result["processing_metadata"] = {
                    "version": "v3-multi-agent",
                    "workflow_type": "three_pass_analysis",
                    "processing_time_seconds": processing_time,
                    "model_version": "nps-report-v3-multi-agent",
                    "passes_completed": ["foundation", "analysis", "consulting"],
                    "agents_executed": 17,  # 4 + 9 + 4 agents
                    "timestamp": datetime.now().isoformat()
                }

            # Persist outputs if requested
            if payload.get("persist_outputs", True):
                _persist_v3_outputs(result)

            # Make result JSON serializable
            serializable_result = make_json_serializable(result)

            return serializable_result

        except Exception as exc:
            processing_time = time.perf_counter() - start_time
            logger.error(f"V3 analysis failed after {processing_time:.2f}s: %s", exc, exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": "V3 分析失败",
                    "details": str(exc),
                    "processing_time_seconds": processing_time,
                    "fallback_options": [
                        "/nps-report-v2 - Try V2 workflow",
                        "/nps-report-v1 - Try V1 workflow"
                    ],
                },
            )


@router.get("/nps-report-v3/demo")
async def nps_report_v3_demo():
    """Run V3 analysis with demo data."""
    logger.info("🎯 Running V3 demo analysis")
    sample = _load_v3_sample_payload()
    return await nps_report_v3(sample)


@router.get("/nps-report-v3/sample")
async def v3_sample():
    """Get sample input format for V3 analysis."""
    return {
        "description": "Sample input format for NPS V3 Multi-Agent Analysis",
        "format": "NPSAnalysisRequest",
        "example": _load_v3_sample_payload(),
        "documentation": "Complete three-pass workflow: Foundation → Analysis → Consulting"
    }


# === LEGACY COMPATIBILITY ===

@router.post("/api/v3/nps/workflow/analyze")
async def api_v3_workflow_analyze(payload: Dict[str, Any] = Body(...)):
    """Legacy compatibility endpoint."""
    return await nps_report_v3(payload)
