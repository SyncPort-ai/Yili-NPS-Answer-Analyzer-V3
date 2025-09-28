"""
NPS分析多智能体系统的LangGraph工作流实现 (integrated)
"""

from typing import Dict, Any
import logging
from langgraph.graph import StateGraph, END
from .state import create_initial_state
from .agents import (
    ingestion_agent,
    quant_agent,
    qual_agent,
    context_agent,
    report_agent,
)
from .critique_agents import run_all_critics, generate_revision_summary


class NPSAnalysisWorkflow:
    """使用LangGraph进行NPS分析的主工作流类。"""
    
    def __init__(self):
        # Use a linear pipeline to avoid deep recursion
        self.workflow = self._create_workflow()
        self.app = self.workflow.compile()
        self.logger = logging.getLogger("nps_report_analyzer")
    
    def _create_workflow(self) -> StateGraph:
        """Linear pipeline to avoid recursive loops."""
        workflow = StateGraph(dict)
        workflow.add_node("ingestion", ingestion_agent)
        workflow.add_node("quantitative", quant_agent)
        workflow.add_node("qualitative", qual_agent)
        workflow.add_node("context", context_agent)
        workflow.add_node("report", report_agent)
        # Linear edges
        workflow.add_edge("ingestion", "quantitative")
        workflow.add_edge("quantitative", "qualitative")
        workflow.add_edge("qualitative", "context")
        workflow.add_edge("context", "report")
        workflow.set_entry_point("ingestion")
        # End after report
        workflow.add_edge("report", END)
        return workflow
    
    def _critique_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """使用4个专家批评家评估分析质量的批评智能体。"""
        try:
            nps_results = state.get("nps_results", {})
            qual_results = state.get("qual_results", {})
            context_results = state.get("context_results", {})
            final_output = state.get("final_output", {})
            
            analysis_data = {
                "nps_score": nps_results.get("nps_score", 0),
                "total_responses": len(state.get("clean_responses", [])),
                "sentiment_analysis": qual_results.get("sentiment_overview", {}),
                "themes": qual_results.get("top_themes", []),
                "entities": qual_results.get("entities", {}),
                "competitive_analysis": context_results.get("competitor_analysis", {}),
                "product_analysis": context_results.get("product_mapping", {}),
                "recommendations": context_results.get("business_insights", []),
                "market_trends": context_results.get("market_trends", []),
                "executive_summary": final_output.get("executive_summary", ""),
                "detailed_analysis": final_output.get("qualitative_analysis", {}),
                "charts": _extract_charts_metadata(final_output.get("html_report_string", "")),
                "html_report": final_output.get("html_report_string", ""),
                "nps_overview": state.get("nps_overview", {}),
                "appendix": state.get("appendix", {})
            }
            
            critique_results = run_all_critics(analysis_data)
            revision_summary = generate_revision_summary(critique_results)
            
            previous_score = state.get("previous_quality_score", 0)
            current_score = revision_summary['总体质量评分']
            total_iterations = state.get("total_critique_iterations", 0) + 1
            state["total_critique_iterations"] = total_iterations
            
            if total_iterations >= 5:
                state["needs_revision"] = False
            elif revision_summary['需要修订的专业领域']:
                if previous_score > 0 and abs(current_score - previous_score) < 0.5:
                    state["needs_revision"] = False
                elif current_score >= 7.0:
                    state["needs_revision"] = False
                else:
                    state["needs_revision"] = True
            else:
                state["needs_revision"] = False
                
            state["previous_quality_score"] = current_score
            state["critique_results"] = critique_results
            state["revision_summary"] = revision_summary
            state["critique_complete"] = True
            
            return state
            
        except Exception as e:
            state["errors"] = state.get("errors", []) + [
                {"agent": "critique", "message": f"批评系统失败: {str(e)}"}
            ]
            state["critique_complete"] = True
            state["needs_revision"] = False
            return state
    
    def _revision_agent(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """基于批评反馈应用改进的修订智能体。"""
        try:
            critique_results = state.get("critique_results", {})
            revision_count = state.get("revision_count", 0)
            max_revision_count = 3
            
            if revision_count >= max_revision_count:
                state["needs_revision"] = False
                state["revision_complete"] = True
                return state
            
            state["revision_count"] = revision_count + 1
            
            for reviewer_key, critique_result in critique_results.items():
                if getattr(critique_result, 'needs_revision', False):
                    self._apply_specific_revisions(state, reviewer_key, critique_result)
            
            if any("nps" in reviewer_key for reviewer_key in critique_results.keys()):
                state["quant_complete"] = False
            if any("linguistics" in reviewer_key for reviewer_key in critique_results.keys()):
                state["qual_complete"] = False
            if any("business" in reviewer_key for reviewer_key in critique_results.keys()):
                state["context_complete"] = False
            if any("report" in reviewer_key for reviewer_key in critique_results.keys()):
                state["report_complete"] = False
            
            state["critique_complete"] = False
            state["revision_complete"] = True
            return state
            
        except Exception as e:
            state["errors"] = state.get("errors", []) + [
                {"agent": "revision", "message": f"修订系统失败: {str(e)}"}
            ]
            state["needs_revision"] = False
            state["revision_complete"] = True
            return state
    
    def _apply_specific_revisions(self, state: Dict[str, Any], reviewer_key: str, critique_result) -> None:
        """通过为智能体存储反馈以便在重新运行时使用来应用特定修订。"""
        if "agent_feedback" not in state:
            state["agent_feedback"] = {}
        
        reviewer_to_agent = {
            "nps_expert": "quant",
            "linguistics_expert": "qual", 
            "business_expert": "context",
            "report_expert": "report"
        }
        
        agent_name = reviewer_to_agent.get(reviewer_key, reviewer_key)
        state["agent_feedback"][agent_name] = {
            "recommendations": getattr(critique_result, 'recommendations', []),
            "issues": getattr(critique_result, 'issues', []),
            "severity": getattr(critique_result, 'severity', ''),
            "score": getattr(critique_result, 'overall_score', 0)
        }
    
    def process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process NPS data with a linear pass + bounded critique cycles."""
        state = create_initial_state(input_data)
        self.logger.info("Pipeline: ingestion → quantitative → qualitative → context → report")
        # Single linear pass
        state = self.app.invoke(state, config={"recursion_limit": 50})
        # Bounded critique/revision cycles handled iteratively (no graph recursion)
        max_cycles = 2
        for i in range(max_cycles):
            self.logger.info("Critique cycle %s/%s", i + 1, max_cycles)
            state = self._critique_agent(state)
            if not state.get("needs_revision"):
                self.logger.info("No revision needed after critique cycle %s", i + 1)
                break
            state = self._revision_agent(state)
            # Re-run affected agents sequentially
            # Always refresh quant/qual/context/report to converge
            state["quant_complete"] = False
            state["qual_complete"] = False
            state["context_complete"] = False
            state["report_complete"] = False
            state = quant_agent(state)
            state = qual_agent(state)
            state = context_agent(state)
            state = report_agent(state)
        return state


def _extract_charts_metadata(html_content: str) -> list:
    """从 HTML 报告中提取图表元数据供批评家验证。"""
    charts = []
    
    if not html_content:
        return charts
        
    import re
    chart_patterns = [
        r'getElementById\([\'\"](\w+Chart)[\'\"]',
        r'new Chart\(.*?title.*?text.*?[\'\"]([^\'\"]+)[\'\"]',
    ]
    
    chart_ids = re.findall(chart_patterns[0], html_content)
    for chart_id in chart_ids:
        chart_title = ""
        if "nps" in chart_id.lower():
            chart_title = "NPS构成分析"
        elif "sentiment" in chart_id.lower():
            chart_title = "客户情感分布"
        else:
            chart_title = f"{chart_id}图表"
            
        charts.append({
            "id": chart_id,
            "title": chart_title,
            "type": "interactive",
            "library": "Chart.js"
        })
    
    return charts
