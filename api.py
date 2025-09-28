from fastapi import FastAPI, HTTPException, Request, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import logging
from logging.handlers import RotatingFileHandler
import json
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import Form
import random
from pathlib import Path
import pandas as pd
from opening_question_analysis import auto_analysis, ModelCallError, LabelingError, EmbeddingError
import asyncio
from functools import partial
from pathlib import Path
from dotenv import load_dotenv

# Load .env if present (project root)
try:
    load_dotenv()
except Exception:
    pass

# Setup detailed logging system
try:
    from nps_report_v2.utils.logging_config import setup_detailed_logging, get_logger
    logging_config = setup_detailed_logging()
    logger = get_logger("api")
except ImportError:
    # Fallback to basic logging if detailed logging is not available
    logger = logging.getLogger("nps_report_analyzer")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        logs_dir = Path(__file__).resolve().parent / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)
        fh = RotatingFileHandler(logs_dir / "app.log", maxBytes=2_000_000, backupCount=3, encoding="utf-8")
        fh.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s - %(message)s")
        fh.setFormatter(fmt)
        ch.setFormatter(fmt)
        logger.addHandler(fh)
        logger.addHandler(ch)

# Integrated v1 workflow (migrated from demo) with import diagnostics
V1_IMPORT_ERROR: Optional[str] = None
try:
    from nps_report_v1.workflow import NPSAnalysisWorkflow  # type: ignore
except Exception as e:  # pragma: no cover
    NPSAnalysisWorkflow = None  # type: ignore
    import traceback
    V1_IMPORT_ERROR = f"{e}\n{traceback.format_exc()}"
    logger.error("Failed to import v1 workflow: %s", V1_IMPORT_ERROR)

# V2 workflow import diagnostics
V2_IMPORT_ERROR: Optional[str] = None
try:
    from nps_report_v2.seven_agent_workflow import SevenAgentWorkflow  # type: ignore
    ParallelProcessor = None  # Legacy - deprecated in favor of SevenAgentWorkflow
except Exception as e:  # pragma: no cover
    SevenAgentWorkflow = None  # type: ignore
    ParallelProcessor = None  # type: ignore
    import traceback
    V2_IMPORT_ERROR = f"{e}\n{traceback.format_exc()}"
    logger.error("Failed to import v2 seven agent workflow: %s", V2_IMPORT_ERROR)



__version__ = "0.0.1"

app = FastAPI(title="NPS Report Analyzer", version=__version__)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Register experimental V3 API routes from isolated module
try:  # pragma: no cover - optional dependency during initialization
    from api_v3 import router as v3_router
    app.include_router(v3_router)
    logger.info("✅ V3 API router successfully registered")
except Exception as exc:  # pragma: no cover
    logger.warning("V3 router not registered: %s", exc)

# 创建一个信号量来限制并发请求数为2
request_semaphore = asyncio.Semaphore(2)

# 自定义验证错误类
class CustomValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

# 自定义验证错误处理器
@app.exception_handler(CustomValidationError)
async def custom_validation_exception_handler(request: Request, exc: CustomValidationError):
    return JSONResponse(
        status_code=400,
        content={"status_code": 400, "status_message": exc.message},
    )

# 验证值不为 None
def validate_not_none(value, field_name):
    if value is None:
        raise CustomValidationError(f'{field_name} 不能为 None')
    return value

# 验证值在有效列表中
def validate_in_list(value, field_name, valid_list):
    if value not in valid_list:
        raise CustomValidationError(f'{field_name} 必须是 {valid_list} 中的一个')
    return value

# 验证 ids 列表
def validate_ids(ids):
    validate_not_none(ids, 'ids')
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise CustomValidationError('ids需要是list[int]类型')
    if not ids:
        raise CustomValidationError('ids 不能为空列表')
    return ids

# 验证 word 字符串
def validate_word(word):
    validate_not_none(word, 'word')
    return word.strip() if word else word

@app.post("/analyze")
async def analyze(request: Request):
    try:
        # 使用信号量控制并发
        async with request_semaphore:
            # 从请求中读取 JSON 数据
            body = await request.json()
            
            # 读取并验证 emotionalType
            emotionalType = validate_not_none(body.get('emotionalType'), 'emotionalType')
            validate_in_list(emotionalType, 'emotionalType', [0, 1, 2])
            
            # 读取并验证 taskType
            taskType = validate_not_none(body.get('taskType'), 'taskType')
            validate_in_list(taskType, 'taskType', [0, 1, 2, 3])
            
            # 读取并验证 question
            question = body.get('question')
            if taskType == 0 and not question:
                raise CustomValidationError('当taskType为0时，question不能为空')
                
            # 读取并验证题号
            questionId = validate_not_none(body.get('questionId'), 'questionId')
            
            # 读取并验证 wordInfos
            wordInfos = validate_not_none(body.get('wordInfos'), 'wordInfos')
            if not isinstance(wordInfos, list) or not wordInfos:
                raise CustomValidationError('wordInfos 不能为空')
            
            # 验证每个 wordInfo
            for wordInfo in wordInfos:
                ids = validate_ids(wordInfo.get('ids'))
                word = validate_word(wordInfo.get('word'))
            
            # 检查 ids 列是否有重复值
            ids_list = [wordInfo.get('ids') for wordInfo in wordInfos]
            flat_ids_list = [item for sublist in ids_list for item in sublist]
            if len(flat_ids_list) != len(set(flat_ids_list)):
                raise CustomValidationError("输入数据中的 'ids' 列存在重复值，请确保 'ids' 列中的值唯一。")
            
            # 将情感类型和任务类型转换为对应的字符串
            emotion_map = {0: "其他", 1: "喜欢", 2: "不喜欢"}
            emotion = emotion_map[emotionalType]
            theme_map = {0: "其他设计", 1: "概念设计", 2: "口味设计", 3: "包装设计"}
            theme = theme_map[taskType]

            # 将输入数据转换为 DataFrame
            data = [{"origion": word_info['word'], "mark": word_info['ids']} for word_info in wordInfos]
            df = pd.DataFrame(data)

            # 验证 DataFrame 是否包含必要的列
            required_columns = ['origion', 'mark']
            if not all(col in df.columns for col in required_columns):
                raise ValueError(f"DataFrame 必须包含以下列: {', '.join(required_columns)}")
            
            # 调用 auto_analysis 函数
            result =await auto_analysis(question, theme, emotion, df, mode='prod')
            # # 将同步的 auto_analysis 转换为异步操作
            # loop = asyncio.get_event_loop()
            # result = await loop.run_in_executor(
            #     None,
            #     partial(auto_analysis, question, theme, emotion, df, mode='prod')
            # )

            
            # 将结果 DataFrame 转换为字典列表
            result_json = result.to_dict(orient='records')
            
            return JSONResponse(
                status_code=200,
                content={
                    "status_code": 200,
                    "status_message": "分析成功完成",
                    "result": result_json,
                    "questionId": questionId
                }
            )
    except ModelCallError as e:
        return JSONResponse(
            status_code=503,
            content={
                "status_code": 503,
                "status_message": f"模型调用错误: {e.stage}: {str(e)}",
                "result": None,
                "questionId": body.get('questionId')
            }
        )
    except LabelingError as e:
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500,
                "status_message": f"标注错误: {str(e)}",
                "result": None,
                "questionId": body.get('questionId')
            }
        )
    except EmbeddingError as e:
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500,
                "status_message": f"嵌入错误: {str(e)}",
                "result": None,
                "questionId": body.get('questionId')
            }
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "status_code": 400,
                "status_message": f"无效输入: {str(e)}",
                "result": None,
                "questionId": body.get('questionId')
            }
        )
    except CustomValidationError as e:
        return JSONResponse(
            status_code=400,
            content={
                "status_code": 400,
                "status_message": e.message,
                "result": None,
                "questionId": body.get('questionId')
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500,
                "status_message": f"意外错误: {str(e)}",
                "result": None,
                "questionId": body.get('questionId')
            }
    )

@app.get("/healthz")
async def healthz():
    return {
        "status": "ok", 
        "v1_loaded": bool(NPSAnalysisWorkflow), 
        "v1_error": V1_IMPORT_ERROR is not None,
        "v2_loaded": bool(ParallelProcessor),
        "v2_error": V2_IMPORT_ERROR is not None
    }

@app.get("/version")
async def version():
    return {"api": "v0", "service": "nps-report-analyzer", "service_version": __version__}


# ---------- Logging Control Endpoints ----------

@app.get("/debug/logging/status")
async def get_logging_status():
    """获取当前日志配置状态"""
    try:
        from nps_report_v2.utils.logging_config import get_logging_config
        config = get_logging_config()
        return {
            "enabled": config.config.get("enabled", True),
            "level": config.config.get("level", "INFO"),
            "detailed_debug": config.config.get("detailed_debug", False),
            "output": config.config.get("output", {}),
            "files": config.config.get("files", {}),
            "modules": config.config.get("modules", {})
        }
    except ImportError:
        return {"error": "详细日志系统不可用"}

@app.post("/debug/logging/enable")
async def enable_detailed_logging():
    """启用详细调试日志"""
    try:
        from nps_report_v2.utils.logging_config import get_logging_config
        config = get_logging_config()
        config.enable_detailed_debug()
        logger.info("详细调试日志已通过API启用")
        return {"message": "详细调试日志已启用", "level": "DEBUG", "detailed_debug": True}
    except ImportError:
        return {"error": "详细日志系统不可用"}

@app.post("/debug/logging/disable")
async def disable_detailed_logging():
    """禁用详细调试日志"""
    try:
        from nps_report_v2.utils.logging_config import get_logging_config
        config = get_logging_config()
        config.disable_detailed_debug()
        logger.info("详细调试日志已通过API禁用")
        return {"message": "详细调试日志已禁用", "level": "INFO", "detailed_debug": False}
    except ImportError:
        return {"error": "详细日志系统不可用"}

@app.post("/debug/logging/module/{module_name}/level/{level}")
async def set_module_log_level(module_name: str, level: str):
    """设置特定模块的日志级别"""
    try:
        from nps_report_v2.utils.logging_config import get_logging_config
        config = get_logging_config()
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if level.upper() not in valid_levels:
            return {"error": f"无效的日志级别，必须是: {valid_levels}"}
        
        config.set_module_level(module_name, level)
        logger.info(f"模块 {module_name} 日志级别已设置为 {level}")
        return {"message": f"模块 {module_name} 日志级别已设置为 {level}"}
    except ImportError:
        return {"error": "详细日志系统不可用"}


# ---------- v0 compatibility endpoint ----------

class FlowInput(BaseModel):
    input_text_0: Optional[str] = None

class FlowRequest(BaseModel):
    input: FlowInput

def _safe_percentage(x: float) -> str:
    try:
        return f"{x * 100:.0f}%" if x <= 1 else f"{x:.0f}%"
    except Exception:
        return "-"

def _infer_segments(user_distribution: List[Dict[str, Any]]) -> Dict[str, float]:
    """Compute promoter/passive/detractor shares from score distribution if needed."""
    promoters = sum([item.get("percentage", 0) for item in user_distribution if item.get("score") in (9, 10)])
    passives = sum([item.get("percentage", 0) for item in user_distribution if item.get("score") in (7, 8)])
    detractors = sum([item.get("percentage", 0) for item in user_distribution if isinstance(item.get("score"), int) and 0 <= item.get("score") <= 6])
    return {
        "promoters": promoters,
        "passives": passives,
        "detractors": detractors,
    }

def _format_conclusions(payload: Dict[str, Any]) -> str:
    # Extract fields
    count = payload.get("count")
    nps_value = payload.get("nps_value")
    user_distribution = payload.get("user_distribution", [])
    analysis_type_list = payload.get("analysis_type_list", [])

    # Percentages from analysis_type_list if present
    promoters = next((x.get("type_percentage") for x in analysis_type_list if x.get("type_name") in ["推荐者", "Promoters"]), None)
    passives = next((x.get("type_percentage") for x in analysis_type_list if x.get("type_name") in ["中立者", "Passives"]), None)
    detractors = next((x.get("type_percentage") for x in analysis_type_list if x.get("type_name") in ["贬损者", "Detractors"]), None)

    if promoters is None or passives is None or detractors is None:
        segs = _infer_segments(user_distribution)
        promoters = segs["promoters"]
        passives = segs["passives"]
        detractors = segs["detractors"]

    low_share = sum([item.get("percentage", 0) for item in user_distribution if isinstance(item.get("score"), int) and 0 <= item.get("score") <= 6])
    high_share = sum([item.get("percentage", 0) for item in user_distribution if item.get("score") in (9, 10)])

    # Determine tone
    tone = "较低" if (nps_value is not None and nps_value < 0) or (detractors and promoters and detractors > promoters) else "良好"

    lines: List[str] = []
    # 1. NPS总览
    if nps_value is not None:
        lines.append(f"1. NPS值为{nps_value:.4f}，表明用户整体满意度{tone}，贬损者比例{'显著高于' if detractors and promoters and detractors > promoters else '低于或接近'}推荐者。")
    else:
        lines.append("1. 基于当前样本计算的NPS表明整体满意度水平稳定，需结合细分进一步评估。")

    # 2. 结构占比
    lines.append(
        f"2. 贬损者占比{_safe_percentage(detractors or 0)}，推荐者占比{_safe_percentage(promoters or 0)}，中立者占比{_safe_percentage(passives or 0)}，需针对性优化差评来源。"
    )

    # 3. 评分分布（可解释性）
    lines.append(
        f"3. 评分分布中，低分（0-6分）用户占比{_safe_percentage(low_share)}，高分（9-10分）用户占比{_safe_percentage(high_share)}，进一步印证满意度结构。"
    )

    # 4. 总体推断
    overall = (
        "较多用户对关键体验点不满，应优先化解贬损者核心痛点，并通过产品与服务改进提升中立者转化，以持续改善NPS。"
        if (detractors or 0) > (promoters or 0)
        else "核心体验具备竞争力，但仍需通过持续优化与差异化价值巩固推荐者优势，稳步提升NPS。"
    )
    lines.append(f"4. 总体来看，{overall}")

    return "\n".join(lines)

@app.post("/nps-report-v0/execute")
@app.post("/nps-report-v0")
async def nps_report_v0(payload: Dict[str, Any] = Body(...)):
    """Compatibility endpoint that mirrors the external flow-based API.

    Expected payload: {"input": {"input_text_0": "<json string with NPS metrics>"}}
    Returns: {"output_text_0": "<Chinese conclusions>"}
    """
    try:
        body = payload
        input_text = body.get("input", {}).get("input_text_0")
        # Accept either a JSON string or an object directly for convenience
        if isinstance(input_text, str) and input_text.strip():
            metrics = json.loads(input_text)
        elif isinstance(input_text, dict):
            metrics = input_text
        else:
            # Fallback: maybe the caller posted metrics at root
            metrics = body

        text = _format_conclusions(metrics)
        return {"output_text_0": text, "output": text}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid payload: {e}")


# ---------- Web UI routes ----------

def _demo_kpis() -> Dict[str, Any]:
    return {
        "overall_nps": 68.5,
        "promoters": 78.2,
        "detractors": 9.7,
        "passives": 12.1,
        "note": "示例数据（可替换为真实接口）",
    }

def _calc_segments_from_distribution(user_distribution: List[Dict[str, Any]]):
    segs = _infer_segments(user_distribution)
    p = segs["promoters"]
    d = segs["detractors"]
    nps_value = p - d  # range [-1,1] if input in 0..1
    return {
        "promoters": p,
        "passives": segs["passives"],
        "detractors": d,
        "nps_value": nps_value,
        "nps_percent": round(nps_value * 100.0, 2),
    }


@app.get("/")
async def ui_index(request: Request):
    kpis = _demo_kpis()
    cards = [
        {"title": "整体NPS得分", "value": kpis["overall_nps"], "desc": "较行业平均高15.3分"},
        {"title": "推荐者比例", "value": f"{kpis['promoters']:.1f}%", "desc": "推荐者占比持续提升"},
        {"title": "贬损者比例", "value": f"{kpis['detractors']:.1f}%", "desc": "贬损者比例有效降低"},
        {"title": "中性者比例", "value": f"{kpis['passives']:.1f}%", "desc": "中性态度持续转化"},
    ]
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "kpis": kpis, "cards": cards},
    )


@app.get("/analytics")
async def ui_analytics(request: Request):
    # Sample product line comparison
    nps_data = [
        {"category": "伊利金典", "nps": 67, "change": "+5", "trend": "up"},
        {"category": "安慕希", "nps": 72, "change": "+3", "trend": "up"},
        {"category": "QQ星", "nps": 58, "change": "-2", "trend": "down"},
        {"category": "舒化", "nps": 64, "change": "+7", "trend": "up"},
        {"category": "植选", "nps": 45, "change": "+12", "trend": "up"},
    ]
    return templates.TemplateResponse(
        "analytics.html",
        {"request": request, "nps_data": nps_data},
    )


# ---------- v1 Multi-Agent Workflow (Integrated) ----------

class SurveyResponse(BaseModel):
    score: int
    comment: Optional[str] = None
    customer_id: Optional[str] = None
    timestamp: Optional[str] = None
    region: Optional[str] = None
    age_group: Optional[str] = None

class V1Request(BaseModel):
    survey_responses: List[SurveyResponse]
    metadata: Optional[Dict[str, Any]] = None
    optional_data: Optional[Dict[str, Any]] = None
    persist_outputs: Optional[bool] = True

class V2Request(BaseModel):
    # Support both legacy and new Chinese format
    survey_responses: Optional[List[SurveyResponse]] = None  # Legacy format
    yili_survey_data_input: Optional[Dict[str, Any]] = None  # New Chinese flat format
    metadata: Optional[Dict[str, Any]] = None
    optional_data: Optional[Dict[str, Any]] = None
    persist_outputs: Optional[bool] = True
    processing_mode: Optional[str] = "enhanced"  # "enhanced", "parallel", "v2_only"
    include_v1_comparison: Optional[bool] = True
    
    @classmethod
    def model_validate(cls, data):
        # Custom validation to ensure at least one format is provided
        result = super().model_validate(data)
        if not result.survey_responses and not result.yili_survey_data_input:
            raise ValueError("Either 'survey_responses' or 'yili_survey_data_input' must be provided")
        return result

def _run_v1_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
    if NPSAnalysisWorkflow is None:
        raise HTTPException(status_code=501, detail="v1 workflow unavailable (import failed)")
    survey = payload.get("survey_responses")
    if not isinstance(survey, list) or len(survey) == 0:
        raise HTTPException(status_code=400, detail="survey_responses must be a non-empty list")
    wf = NPSAnalysisWorkflow()
    logger.info("Starting v1 workflow: %s responses", len(survey))
    result = wf.process({
        "survey_responses": survey,
        "metadata": payload.get("metadata", {}),
        "optional_data": payload.get("optional_data", {}),
    })
    # Always return the full final state with HTML
    full_state = dict(result)
    # Serialize critique_results dataclasses if present
    if isinstance(full_state.get("critique_results"), dict):
        serialized = {}
        for k, v in full_state["critique_results"].items():
            serialized[k] = {
                "reviewer": getattr(v, "reviewer", ""),
                "severity": getattr(v, "severity", ""),
                "overall_score": getattr(v, "overall_score", 0),
                "issues": getattr(v, "issues", []),
                "recommendations": getattr(v, "recommendations", []),
                "needs_revision": getattr(v, "needs_revision", False),
            }
        full_state["critique_results"] = serialized
    # Apply demo-shaped mapping by default
    full_state = _to_demo_strict(full_state)
    # Persist if requested
    if payload.get("persist_outputs", True):
        _persist_outputs(full_state)
    return full_state


def _persist_outputs(final_state: Dict[str, Any]) -> None:
    """Write JSON (and optional HTML) under project outputs directory."""
    try:
        out_dir = Path(__file__).resolve().parent / "outputs"
        results_dir = out_dir / "results"
        reports_dir = out_dir / "reports"
        results_dir.mkdir(parents=True, exist_ok=True)
        reports_dir.mkdir(parents=True, exist_ok=True)
        ts = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        # Serialize critique objects if present
        state = dict(final_state)
        if isinstance(state.get("critique_results"), dict):
            serialized = {}
            for k, v in state["critique_results"].items():
                serialized[k] = {
                    "reviewer": getattr(v, "reviewer", ""),
                    "severity": getattr(v, "severity", ""),
                    "overall_score": getattr(v, "overall_score", 0),
                    "issues": getattr(v, "issues", []),
                    "recommendations": getattr(v, "recommendations", []),
                    "needs_revision": getattr(v, "needs_revision", False),
                }
            state["critique_results"] = serialized
        (results_dir / f"v1_{ts}.json").write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
        html = state.get("final_output", {}).get("html_report_string")
        if html:
            (reports_dir / f"v1_{ts}.html").write_text(html, encoding="utf-8")
        else:
            logger.warning("No HTML report string found in final_output; only JSON written (ts=%s)", ts)
    except Exception:
        # best-effort persistence; ignore failures in API response
        pass


def _to_demo_strict(state: Dict[str, Any]) -> Dict[str, Any]:
    """Map internal final state to a shape very close to the historical demo JSON."""
    import copy
    from nps_report_v1.report_helpers import (
        calculate_statistical_confidence,
        extract_quantitative_trends,
    )
    s = copy.deepcopy(state)

    # Ensure yili_products_csv is present at top-level if found in optional_data
    if "yili_products_csv" not in s:
        opt = s.get("optional_data", {})
        if isinstance(opt, dict) and opt.get("yili_products_csv") is not None:
            s["yili_products_csv"] = opt.get("yili_products_csv")

    # Normalize score_distribution keys to strings '0'..'10'
    nps = s.get("nps_results", {})
    dist = nps.get("score_distribution")
    if isinstance(dist, dict):
        nps["score_distribution"] = {str(int(k)): int(v) for k, v in dist.items()}
        s["nps_results"] = nps

    # Add statistical confidence and trend indicators at top-level (common in demo outputs)
    s["statistical_confidence"] = calculate_statistical_confidence(nps)
    s["trend_indicators"] = extract_quantitative_trends(nps)

    # Provide qualitative_analysis.nlp_results nesting similar to demo
    qual = s.get("qual_results", {})
    s.setdefault("qualitative_analysis", {})
    s["qualitative_analysis"]["nlp_results"] = qual

    # Expand mapping_confidence shape under context_results.product_mapping
    ctx = s.get("context_results", {})
    pm = ctx.get("product_mapping", {}) if isinstance(ctx, dict) else {}
    mention_mapping = pm.get("mention_mapping", [])
    mapped_products = len([m for m in mention_mapping if m.get("official_product") and m.get("official_product") != "未匹配"])
    total_mentions = 0
    try:
        for m in mention_mapping:
            total_mentions += int(m.get("mention_data", {}).get("mentions", 0))
    except Exception:
        pass
    conf_val = pm.get("mapping_confidence")
    if isinstance(conf_val, (int, float)):
        pm["mapping_confidence"] = {
            "overall_confidence": conf_val,
            "mapped_products": mapped_products,
            "total_mentions": total_mentions,
        }
        ctx["product_mapping"] = pm
        s["context_results"] = ctx

    return s


def _load_v1_sample_payload() -> Dict[str, Any]:
    """Load the default V1 sample input JSON from data/V1-sample-input.json."""
    try:
        sample_path = Path(__file__).resolve().parent / "data" / "V1-sample-input.json"
        return json.loads(sample_path.read_text(encoding="utf-8"))
    except Exception:
        # Minimal fallback example
        return {
            "survey_responses": [
                {"score": 9, "comment": "安慕希口感很好", "region": "华东"},
                {"score": 3, "comment": "金典有怪味", "region": "华北"},
                {"score": 8, "comment": "舒化奶帮助乳糖不耐", "region": "华南"}
            ]
        }


@app.post("/nps-report-v1")
async def nps_report_v1(
    payload: V1Request = Body(
        ..., 
        example=_load_v1_sample_payload()
    )
):
    """v1 Multi-Agent NPS workflow (integrated).

    Request body:
    - survey_responses: list of {score:int, comment?:str, customer_id?:str, timestamp?:str, region?:str, age_group?:str}
    - metadata?: object
    - optional_data?: object
    - response_mode?: "demo" (default full-state) | "compact" (summary blocks)
    - include_html_report?: bool (include HTML string if available)
    """
    try:
        if NPSAnalysisWorkflow is None:
            # Provide clearer diagnostics instead of 501
            msg = "v1 workflow import failed; check dependencies (langgraph) and PYTHONPATH."
            if V1_IMPORT_ERROR:
                msg += f" Details: {V1_IMPORT_ERROR.splitlines()[0]}"
            raise HTTPException(status_code=500, detail=msg)
        data = payload.model_dump(exclude_none=True)
        return _run_v1_workflow(data)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"workflow failed: {e}")


@app.get("/api/v1/nps/sample")
async def api_v1_sample_input():
    """Return the default sample payload for v1 requests."""
    return _load_v1_sample_payload()


@app.post("/api/v1/nps/workflow/analyze")
async def api_v1_workflow_analyze(payload: V1Request = Body(...)):
    """Backward-compatible v1 path; same as /nps-report-v1."""
    return await nps_report_v1(payload)

@app.get("/nps-report-v1/demo")
async def nps_report_v1_demo():
    """Run the v1 workflow on a tiny built-in demo dataset for testing."""
    sample = {
        "survey_responses": [
            {"score": 10, "comment": "安慕希口感很好，家人都喜欢", "region": "华东"},
            {"score": 6, "comment": "价格有点贵，希望有活动", "region": "华北"},
            {"score": 9, "comment": "金典质量稳定，味道不错", "region": "华南"},
            {"score": 3, "comment": "最近买到一瓶有怪味，体验差", "region": "西南"},
            {"score": 8, "comment": "整体还行，但竞争对手蒙牛也在促销", "region": "华东"},
        ],
        "metadata": {"source": "demo"},
    }
    return _run_v1_workflow(sample)


# ---------- v2 Multi-Agent Workflow (Enhanced) ----------

async def _run_v2_workflow(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Execute V2 seven-agent NPS analysis workflow."""
    # Get detailed logger for V2 workflow
    try:
        from nps_report_v2.utils.logging_config import get_logger
        v2_logger = get_logger("nps_report_v2.workflow")
    except ImportError:
        v2_logger = logger
    
    v2_logger.info("=" * 80)
    v2_logger.info("🚀 V2 七智能体NPS分析工作流开始执行")
    v2_logger.info("=" * 80)
    
    if SevenAgentWorkflow is None:
        v2_logger.error("❌ V2 工作流不可用: SevenAgentWorkflow 导入失败")
        raise HTTPException(status_code=501, detail="v2 seven agent workflow unavailable (import failed)")
    
    # Support both old format (survey_responses) and new Chinese format (yili_survey_data_input)
    survey_data = None
    input_format = "unknown"
    
    if "yili_survey_data_input" in payload:
        # New Chinese flat format
        survey_data = payload
        input_format = "chinese_flat"
        v2_logger.info("📋 检测到中文扁平格式数据 (yili_survey_data_input)")
    elif "survey_responses" in payload:
        # Legacy format
        survey = payload.get("survey_responses")
        if not isinstance(survey, list) or len(survey) == 0:
            v2_logger.error("❌ 无效的调研数据: survey_responses 必须是非空列表")
            raise HTTPException(status_code=400, detail="survey_responses must be a non-empty list")
        survey_data = payload
        input_format = "legacy"
        v2_logger.info(f"📊 检测到传统格式数据: {len(survey)} 个响应")
    else:
        v2_logger.error("❌ 未找到有效数据: 需要 'yili_survey_data_input' 或 'survey_responses'")
        raise HTTPException(status_code=400, detail="Missing required data: 'yili_survey_data_input' or 'survey_responses'")
    
    v2_logger.info(f"📊 输入格式: {input_format}")
    v2_logger.debug(f"📋 负载详情: {json.dumps(payload, ensure_ascii=False, indent=2, default=str)}")
    
    try:
        # Initialize seven agent workflow
        v2_logger.info("🔧 初始化七智能体工作流...")
        workflow = SevenAgentWorkflow()
        v2_logger.debug("✅ SevenAgentWorkflow 初始化成功")
        
        v2_logger.info(f"⚙️ 输入数据格式: {input_format}")
        v2_logger.debug(f"📥 工作流输入数据: {json.dumps(survey_data, ensure_ascii=False, indent=2, default=str)}")
        
        logger.info("Starting v2 seven agent workflow: format: %s", input_format)
        
        # Execute seven agent analysis
        v2_logger.info("🔄 开始执行七智能体分析...")
        result = workflow.process_nps_data(survey_data)
        v2_logger.info("✅ 七智能体分析执行成功")
        v2_logger.debug(f"📤 分析结果结构: {list(result.keys()) if isinstance(result, dict) else type(result)}")
        
        # Persist outputs if requested
        if payload.get("persist_outputs", True):
            v2_logger.info("💾 保存分析结果...")
            _persist_seven_agent_outputs(result)
            v2_logger.info("✅ 分析结果保存成功")
        else:
            v2_logger.info("⏭️ 跳过输出保存（persist_outputs=False）")
        
        # Create V2 seven agent analysis response structure
        v2_response = {
            "status": "success",
            "message": "七智能体NPS分析完成",
            "analysis_type": result.get("analysis_type", "七智能体NPS分析系统"),
            "timestamp": result.get("timestamp", None),
            "data": result,
            "metadata": {
                "input_format": input_format,
                "processing_successful": True,
                "agents_count": result.get("summary_statistics", {}).get("total_agents", 7),
                "total_statements": result.get("summary_statistics", {}).get("total_statements", 0),
                "total_business_questions": result.get("summary_statistics", {}).get("total_business_questions", 0),
                "analysis_coverage": result.get("summary_statistics", {}).get("analysis_coverage", ""),
                "model_version": "nps-report-v2-seven-agent",
                "language": "zh-CN"
            }
        }
        
        # Add summary insights for quick access
        if "agent_analysis_results" in result and result["agent_analysis_results"]:
            summary_agent = result["agent_analysis_results"][-1]  # Last agent is summary
            v2_response["summary_insights"] = {
                "agent_name": summary_agent.get("agent_name", ""),
                "key_statements": summary_agent.get("statements", [])[:4],  # First 4 statements
                "critical_questions": summary_agent.get("business_questions", [])[:3],  # First 3 questions
                "additional_info": summary_agent.get("additional_info", {})
            }
        
        v2_logger.debug(f"🔄 七智能体响应结构: {list(v2_response.keys())}")
        v2_logger.info("=" * 80)
        v2_logger.info("🎉 V2 七智能体NPS分析工作流执行完成")
        v2_logger.info("=" * 80)
        
        return v2_response
        
    except Exception as e:
        v2_logger.error("=" * 80)
        v2_logger.error("❌ V2 工作流执行失败")
        v2_logger.error(f"错误类型: {type(e).__name__}")
        v2_logger.error(f"错误信息: {str(e)}")
        import traceback
        v2_logger.error(f"错误堆栈:\n{traceback.format_exc()}")
        v2_logger.error("=" * 80)
        
        logger.error(f"V2 workflow execution failed: {e}")
        raise HTTPException(status_code=500, detail=f"v2 workflow failed: {e}")


def _persist_v2_outputs(result) -> None:
    """Write V2 outputs to the outputs directory."""
    try:
        # Import serialize_data function for proper data handling
        try:
            from nps_report_v2.data_recorder import serialize_data
        except ImportError:
            # Fallback serialization function
            def serialize_data(data):
                if hasattr(data, '__dict__'):
                    return {k: serialize_data(v) for k, v in data.__dict__.items()}
                elif isinstance(data, dict):
                    return {k: serialize_data(v) for k, v in data.items()}
                elif isinstance(data, (list, tuple)):
                    return [serialize_data(item) for item in data]
                else:
                    return data
        
        out_dir = Path(__file__).resolve().parent / "outputs"
        v2_results_dir = out_dir / "v2_results"
        v2_reports_dir = out_dir / "v2_reports"
        v2_results_dir.mkdir(parents=True, exist_ok=True)
        v2_reports_dir.mkdir(parents=True, exist_ok=True)
        
        ts = __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Convert ParallelProcessingResult to serializable format
        final_state = serialize_data(result)
        
        # Save complete V2 result
        (v2_results_dir / f"v2_{ts}.json").write_text(
            json.dumps(final_state, ensure_ascii=False, indent=2, default=str), 
            encoding="utf-8"
        )
        
        # Save V2 HTML report if available - handle both dict and dataclass
        v2_output = {}
        if isinstance(result, dict):
            v2_output = result.get("v2_output", {})
        elif hasattr(result, 'v2_result') and result.v2_result and result.v2_result.result:
            v2_output = result.v2_result.result.get("v2_output", {})
        
        html_report = v2_output.get("html_report") if isinstance(v2_output, dict) else None
        if html_report:
            (v2_reports_dir / f"v2_{ts}.html").write_text(html_report, encoding="utf-8")
        
        # Save comparison report if available - handle both dict and dataclass
        comparison = None
        if isinstance(result, dict):
            comparison = result.get("comparison_analysis")
        elif hasattr(result, 'comparison_analysis'):
            comparison = result.comparison_analysis
        
        if comparison:
            comparison_dir = out_dir / "comparison_reports"
            comparison_dir.mkdir(parents=True, exist_ok=True)
            (comparison_dir / f"v1_vs_v2_{ts}.json").write_text(
                json.dumps(serialize_data(comparison), ensure_ascii=False, indent=2, default=str),
                encoding="utf-8"
            )
        
        logger.info("V2 outputs persisted successfully (ts=%s)", ts)
        
    except Exception as e:
        logger.error(f"Failed to persist V2 outputs: {e}")
        # best-effort persistence; ignore failures in API response


def _persist_seven_agent_outputs(result: Dict[str, Any]) -> None:
    """Write seven agent analysis outputs to the outputs directory."""
    try:
        out_dir = Path(__file__).resolve().parent / "outputs"
        results_dir = out_dir / "results"
        logs_dir = out_dir / "logs"
        results_dir.mkdir(parents=True, exist_ok=True)
        logs_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = result.get("timestamp", __import__('datetime').datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3])
        
        # Save complete seven agent analysis result
        result_file = results_dir / f"v2_seven_agent_{timestamp}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        # Also save to logs directory for consistency
        log_file = logs_dir / f"seven_agent_api_result_{timestamp}.json"
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        
        logger.info("Seven agent outputs persisted successfully (ts=%s)", timestamp)
        
    except Exception as e:
        logger.error(f"Failed to persist seven agent outputs: {e}")
        # best-effort persistence; ignore failures in API response


def _load_v2_sample_payload() -> Dict[str, Any]:
    """Load the default V2 sample input JSON."""
    try:
        sample_path = Path(__file__).resolve().parent / "data" / "V2-中文-sample-product-survey-input.json"
        if sample_path.exists():
            # Return the Chinese format directly for seven agent workflow
            full_data = json.loads(sample_path.read_text(encoding="utf-8"))
            logger.info(f"Loading V2 sample data: Chinese format with yili_survey_data_input")
            return full_data
            
            
    except Exception as e:
        logger.warning(f"Failed to load V2 sample data: {e}")
    
    # Fallback to simple sample data
    return {
        "survey_responses": [
            {"score": 10, "comment": "安慕希口感很好，家人都喜欢", "region": "华东", "age_group": "26-35"},
            {"score": 6, "comment": "价格有点贵，希望有活动", "region": "华北", "age_group": "36-45"},
            {"score": 9, "comment": "金典质量稳定，味道不错", "region": "华南", "age_group": "18-25"},
            {"score": 3, "comment": "最近买到一瓶有怪味，体验差", "region": "西南", "age_group": "46-55"},
            {"score": 8, "comment": "整体还行，但竞争对手蒙牛也在促销", "region": "华东", "age_group": "26-35"}
        ],
        "metadata": {"source": "v2_demo_fallback", "survey_type": "nps_analysis"},
        "optional_data": {"product_category": "dairy_products"},
        "processing_mode": "enhanced",
        "include_v1_comparison": True
    }


@app.post("/nps-report-v2")
async def nps_report_v2(
    payload: V2Request = Body(
        ..., 
        example=_load_v2_sample_payload()
    )
):
    """v2 Enhanced Multi-Agent NPS workflow with parallel V1/V2 processing.

    Request body:
    - survey_responses: list of {score:int, comment?:str, customer_id?:str, timestamp?:str, region?:str, age_group?:str}
    - metadata?: object
    - optional_data?: object
    - processing_mode?: "enhanced" (default) | "parallel" | "v2_only"
    - include_v1_comparison?: bool (default true)
    - persist_outputs?: bool (default true)
    
    The V2 workflow provides:
    - Multi-agent analysis (NPS, question groups, insights, quality review)
    - V1/V2 parallel processing and comparison
    - Enhanced error handling and fault tolerance
    - Comprehensive HTML report generation
    - Business intelligence and competitive analysis
    """
    try:
        if SevenAgentWorkflow is None:
            # Provide clearer diagnostics
            msg = "v2 seven agent workflow import failed; check dependencies and PYTHONPATH."
            if V2_IMPORT_ERROR:
                msg += f" Details: {V2_IMPORT_ERROR.splitlines()[0]}"
            raise HTTPException(status_code=500, detail=msg)
        
        data = payload.model_dump(exclude_none=True)
        return await _run_v2_workflow(data)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"v2 workflow failed: {e}")


@app.get("/nps-report-v2/demo")
async def nps_report_v2_demo():
    """Run the v2 workflow on a demo dataset for testing."""
    sample = _load_v2_sample_payload()
    return await _run_v2_workflow(sample)


@app.get("/api/v2/nps/sample")
async def api_v2_sample_input():
    """Return the default sample payload for v2 requests."""
    return _load_v2_sample_payload()


@app.post("/api/v2/nps/workflow/analyze")
async def api_v2_workflow_analyze(payload: V2Request = Body(...)):
    """Backward-compatible v2 path; same as /nps-report-v2."""
    return await nps_report_v2(payload)


@app.get("/reports")
async def ui_reports(request: Request):
    # Load summaries from data file
    reports = []
    data_path = Path("data/mock_reports.json")
    if data_path.exists():
        try:
            data = json.loads(data_path.read_text(encoding="utf-8"))
            reports = data.get("reports", [])
        except Exception:
            reports = []
    return templates.TemplateResponse(
        "reports.html",
        {"request": request, "reports": reports},
    )


@app.get("/reports/{report_id}")
async def ui_report_detail(request: Request, report_id: str):
    data_path = Path("data/mock_reports.json")
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="report not found")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    items = data.get("reports", [])
    report = next((r for r in items if str(r.get("id")) == str(report_id)), None)
    if not report:
        raise HTTPException(status_code=404, detail="report not found")
    return templates.TemplateResponse("report_detail.html", {"request": request, "report": report})


# ---------- Simple KPI APIs for HTMX/clients ----------

@app.get("/api/kpi/overview")
async def api_kpi_overview():
    return _demo_kpis()

@app.get("/api/kpi/brands")
async def api_kpi_brands():
    return {
        "items": [
            {"brand": "安慕希", "nps": 72, "trend": "up"},
            {"brand": "金典", "nps": 69, "trend": "up"},
            {"brand": "舒化", "nps": 64, "trend": "up"},
            {"brand": "QQ星", "nps": 58, "trend": "down"},
        ]
    }

@app.get("/api/reports")
async def api_reports_list():
    data_path = Path("data/mock_reports.json")
    if not data_path.exists():
        return {"reports": []}
    return json.loads(data_path.read_text(encoding="utf-8"))

@app.get("/api/reports/{report_id}")
async def api_reports_get(report_id: str):
    data_path = Path("data/mock_reports.json")
    if not data_path.exists():
        raise HTTPException(status_code=404, detail="not found")
    data = json.loads(data_path.read_text(encoding="utf-8"))
    items = data.get("reports", [])
    report = next((r for r in items if str(r.get("id")) == str(report_id)), None)
    if not report:
        raise HTTPException(status_code=404, detail="not found")
    return report


# ---------- Extra UI pages to mirror prototype ----------

@app.get("/projects")
async def ui_projects(request: Request):
    projects = [
        {"title": "伊利舒化无乳糖牛奶NPS深度调研", "status": "active", "progress": 75, "dueDate": "2024-09-20", "teamMembers": 8, "responseRate": 82},
        {"title": "QQ星儿童奶品牌概念测试", "status": "active", "progress": 45, "dueDate": "2024-09-30", "teamMembers": 6, "responseRate": 67},
        {"title": "安慕希高端酸奶市场反馈分析", "status": "planning", "progress": 20, "dueDate": "2024-10-15", "teamMembers": 10},
    ]
    return templates.TemplateResponse("projects.html", {"request": request, "projects": projects})

@app.get("/surveys")
async def ui_surveys(request: Request):
    surveys = [
        {"id": 1, "title": "伊利金典品牌NPS调研", "description": "针对金典系列的NPS调研", "status": "进行中", "responses": 1247, "targetResponses": 2000, "createdDate": "2024-01-15", "type": "NPS调研"},
        {"id": 2, "title": "新品概念测试问卷", "description": "植物基酸奶新品概念接受度", "status": "草稿", "responses": 0, "targetResponses": 1500, "createdDate": "2024-01-20", "type": "概念测试"},
        {"id": 3, "title": "品牌认知度季度调研", "description": "品牌认知与偏好调研", "status": "已完成", "responses": 2000, "targetResponses": 2000, "createdDate": "2023-12-01", "type": "品牌调研"},
    ]
    return templates.TemplateResponse("surveys.html", {"request": request, "surveys": surveys})

@app.get("/insights")
async def ui_insights(request: Request):
    expert = [
        {"expert": "张教授", "title": "消费行为心理学专家", "institution": "清华大学经管学院", "insight": "建议通过情感营销策略强化品牌忠诚度。", "topic": "品牌心理学", "priority": "高", "date": "2024-01-20", "rating": 4.9},
        {"expert": "李博士", "title": "乳制品行业分析师", "institution": "中国乳制品工业协会", "insight": "植物基乳品市场增长迅速，建议加大布局。", "topic": "行业趋势", "priority": "高", "date": "2024-01-18", "rating": 4.8},
    ]
    ai = [
        {"title": "消费者偏好变化预测", "description": "健康化、功能性产品需求将增长35%", "confidence": "92%", "category": "市场预测"},
        {"title": "竞品分析洞察", "description": "蒙牛在下沉市场NPS增长加速", "confidence": "87%", "category": "竞争分析"},
    ]
    return templates.TemplateResponse("insights.html", {"request": request, "expert": expert, "ai": ai})

@app.get("/consumers")
async def ui_consumers(request: Request):
    segments = [
        {"segment": "18-25岁", "nps": 62, "satisfaction": 78, "loyaltyRate": 65, "sampleSize": 2156},
        {"segment": "26-35岁", "nps": 71, "satisfaction": 85, "loyaltyRate": 82, "sampleSize": 3924},
        {"segment": "36-45岁", "nps": 73, "satisfaction": 87, "loyaltyRate": 89, "sampleSize": 4367},
    ]
    return templates.TemplateResponse("consumers.html", {"request": request, "segments": segments})

@app.get("/calendar")
async def ui_calendar(request: Request):
    items = [
        {"date": "2024-09-20", "title": "舒化项目里程碑", "desc": "样本收集完成"},
        {"date": "2024-09-30", "title": "QQ星问卷截止", "desc": "关闭问卷入口"},
    ]
    return templates.TemplateResponse("calendar.html", {"request": request, "items": items})

@app.get("/settings")
async def ui_settings(request: Request):
    info = {"version": __version__, "api": "v0", "storage": "SQLite/DuckDB (dev)"}
    return templates.TemplateResponse("settings.html", {"request": request, "info": info})


# ---------- Calculation & Simulation APIs ----------

@app.post("/api/nps/calculate")
async def api_nps_calculate(payload: Dict[str, Any] = Body(...)):
    """Calculate NPS from either analysis_type_list or user_distribution.
    - analysis_type_list: [{type_name: 推荐者/中立者/贬损者, type_percentage: 0..1}]
    - user_distribution: [{score: 0..10, percentage: 0..1}]
    Returns nps_value in [-1,1] and percent.
    """
    atl = payload.get("analysis_type_list")
    dist = payload.get("user_distribution")
    if atl:
        p = next((x.get("type_percentage", 0) for x in atl if x.get("type_name") in ["推荐者", "Promoters"]), 0)
        d = next((x.get("type_percentage", 0) for x in atl if x.get("type_name") in ["贬损者", "Detractors"]), 0)
        nps_value = p - d
        return {
            "promoters": p,
            "detractors": d,
            "passives": next((x.get("type_percentage", 0) for x in atl if x.get("type_name") in ["中立者", "Passives"]), 0),
            "nps_value": nps_value,
            "nps_percent": round(nps_value * 100.0, 2),
        }
    if dist:
        return _calc_segments_from_distribution(dist)
    raise HTTPException(status_code=400, detail="provide analysis_type_list or user_distribution")


@app.post("/api/simulate/responses")
async def api_simulate_responses(
    payload: Optional[Dict[str, Any]] = Body(None),
    sample_size: Optional[int] = Form(None),
    promoter_bias: Optional[float] = Form(None),
    detractor_bias: Optional[float] = Form(None),
):
    """Generate a simple synthetic score distribution.
    Input: { sample_size?: int (default 200), promoter_bias?: float [0..1], detractor_bias?: float [0..1] }
    """
    # Prefer JSON body; fallback to form fields from HTMX
    if payload is None:
        payload = {}
    size = int(payload.get("sample_size", sample_size if sample_size is not None else 200))
    promoter_bias = float(payload.get("promoter_bias", promoter_bias if promoter_bias is not None else 0.3))
    detractor_bias = float(payload.get("detractor_bias", detractor_bias if detractor_bias is not None else 0.2))

    # Base probabilities for 0..10
    base = [0.03, 0.03, 0.04, 0.06, 0.08, 0.10, 0.10, 0.12, 0.14, 0.15, 0.15]
    # Bias promoters (9,10) and detractors (0..6)
    for i in range(11):
        if i >= 9:
            base[i] += promoter_bias / 2.0
        elif i <= 6:
            base[i] += detractor_bias / 7.0
    s = sum(base)
    probs = [x / s for x in base]

    counts = [0] * 11
    for _ in range(size):
        r = random.random()
        acc = 0.0
        for i, p in enumerate(probs):
            acc += p
            if r <= acc:
                counts[i] += 1
                break

    user_distribution = [
        {"score": i, "people_number": counts[i], "percentage": round(counts[i] / size, 4)} for i in range(11)
    ]
    result = _calc_segments_from_distribution(user_distribution)
    return {
        "count": size,
        "user_distribution": user_distribution,
        "analysis_type_list": [
            {"type_name": "推荐者", "type_percentage": result["promoters"]},
            {"type_name": "中立者", "type_percentage": result["passives"]},
            {"type_name": "贬损者", "type_percentage": result["detractors"]},
        ],
        "nps_value": result["nps_value"],
        "nps_percent": result["nps_percent"],
    }


# ---------- Report generation UI helpers ----------

@app.post("/ui/reports/generate")
async def ui_reports_generate(request: Request, metrics_text: str = Form(...)):
    try:
        metrics = json.loads(metrics_text)
        text = _format_conclusions(metrics)
        return templates.TemplateResponse(
            "partials/report_result.html",
            {"request": request, "text": text},
        )
    except Exception as e:
        return templates.TemplateResponse(
            "partials/report_result.html",
            {"request": request, "text": f"解析失败: {e}"},
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
