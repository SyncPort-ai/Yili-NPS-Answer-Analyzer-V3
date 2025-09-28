"""
B1 - Technical Requirements Analysis Agent
Analysis Pass Agent for extracting technical requirements from feedback.
"""

import logging
from typing import Dict, Any, List, Optional
import re

from ..base import AnalysisAgent, AgentResult, AgentStatus
from ...state import TechnicalRequirement
from ...llm import LLMClient

logger = logging.getLogger(__name__)


class TechnicalRequirementsAgent(AnalysisAgent):
    """
    B1 - Technical Requirements Analysis Agent

    Responsibilities:
    - Extract technical requirements from customer feedback
    - Categorize requirements (product, packaging, service, digital)
    - Assess feasibility and priority
    - Map requirements to specific feedback
    """

    def __init__(self, agent_id: str = "B1", agent_name: str = "Technical Requirements Analysis Agent",
                 llm_client: Optional[LLMClient] = None, **kwargs):
        super().__init__(agent_id, agent_name, **kwargs)
        self.llm_client = llm_client

        # Technical requirement patterns
        self.requirement_patterns = {
            "product": {
                "keywords": ["口感", "味道", "浓度", "甜度", "质地", "配方", "成分", "营养"],
                "examples": ["减少甜度", "增加蛋白质", "改善口感", "添加益生菌"]
            },
            "packaging": {
                "keywords": ["包装", "瓶子", "盒子", "密封", "便携", "环保", "标签", "设计"],
                "examples": ["改进密封性", "更环保包装", "便携装", "透明标签"]
            },
            "service": {
                "keywords": ["配送", "客服", "售后", "物流", "速度", "响应", "处理"],
                "examples": ["加快配送", "改善客服", "优化物流", "提升响应速度"]
            },
            "digital": {
                "keywords": ["APP", "网站", "小程序", "扫码", "会员", "积分", "在线"],
                "examples": ["开发APP", "优化小程序", "会员系统", "积分兑换"]
            }
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Execute technical requirements extraction.

        Args:
            state: Current workflow state

        Returns:
            AgentResult with technical requirements
        """
        try:
            # Get tagged responses from Foundation Pass
            tagged_responses = state.get("tagged_responses", [])

            if not tagged_responses:
                logger.warning("No tagged responses available for technical analysis")
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.COMPLETED,
                    data={
                        "technical_requirements": [],
                        "requirements_summary": {
                            "total": 0,
                            "by_category": {},
                            "by_priority": {}
                        }
                    },
                    insights=[{"content": "无可用的标记响应数据进行技术需求分析", "priority": "low"}],
                    confidence_score=0.0
                )

            # Extract requirements from responses
            requirements = []

            for response in tagged_responses:
                extracted = await self._extract_requirements(response)
                requirements.extend(extracted)

            # Deduplicate and consolidate requirements
            consolidated = self._consolidate_requirements(requirements)

            # Prioritize requirements
            prioritized = self._prioritize_requirements(consolidated)

            # Generate summary
            summary = self._generate_requirements_summary(prioritized)

            # Generate insights
            insights = self._generate_requirements_insights(prioritized, summary)

            logger.info(f"Extracted {len(prioritized)} technical requirements")

            # Convert insights to proper format
            formatted_insights = [{"content": insight, "priority": "medium"} for insight in insights]

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "technical_requirements": prioritized,
                    "requirements_summary": summary,
                    "technical_insights": insights
                },
                insights=formatted_insights,
                confidence_score=0.8 if len(prioritized) > 0 else 0.3
            )

        except Exception as e:
            logger.error(f"Technical requirements analysis failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)],
                confidence_score=0.0
            )

    async def _extract_requirements(
        self,
        response: Dict[str, Any]
    ) -> List[TechnicalRequirement]:
        """
        Extract technical requirements from a response.

        Args:
            response: Tagged response

        Returns:
            List of technical requirements
        """
        requirements = []
        text = response.get("original_text", "")
        response_id = response.get("response_id", "")

        if not text:
            return requirements

        # Pattern-based extraction
        for category, patterns in self.requirement_patterns.items():
            # Check for keywords
            if any(keyword in text for keyword in patterns["keywords"]):
                # Extract specific requirements
                for example in patterns["examples"]:
                    if self._fuzzy_match(example, text):
                        req = TechnicalRequirement(
                            requirement_id=f"req_{len(requirements)}",
                            category=category,
                            description=example,
                            priority="medium",
                            feasibility="medium",
                            related_responses=[response_id],
                            technical_notes=""
                        )
                        requirements.append(req)

        # LLM-based extraction for deeper analysis
        if self.llm_client and len(text) > 50:
            llm_requirements = await self._llm_extract_requirements(text, response_id)
            requirements.extend(llm_requirements)

        return requirements

    def _fuzzy_match(self, pattern: str, text: str) -> bool:
        """
        Fuzzy match pattern in text.

        Args:
            pattern: Pattern to match
            text: Text to search in

        Returns:
            True if pattern found
        """
        # Simple keyword matching
        keywords = pattern.split()
        matches = sum(1 for keyword in keywords if keyword in text)
        return matches >= len(keywords) * 0.5

    async def _llm_extract_requirements(
        self,
        text: str,
        response_id: str
    ) -> List[TechnicalRequirement]:
        """
        Use LLM to extract technical requirements.

        Args:
            text: Response text
            response_id: Response ID

        Returns:
            List of requirements
        """
        if not self.llm_client:
            return []

        try:
            prompt = f"""
从以下客户反馈中提取技术需求：

反馈内容：
{text}

请识别并提取：
1. 产品改进需求（配方、口感、营养等）
2. 包装优化需求（材质、设计、功能等）
3. 服务提升需求（配送、客服、售后等）
4. 数字化需求（APP、会员系统等）

对每个需求，评估：
- 优先级（high/medium/low）
- 可行性（high/medium/low/unknown）

以JSON格式返回：
[
    {{
        "category": "product/packaging/service/digital",
        "description": "具体需求描述",
        "priority": "high/medium/low",
        "feasibility": "high/medium/low/unknown",
        "technical_notes": "技术实现说明"
    }}
]
"""

            response = await self.llm_client.generate(prompt, temperature=0.3)

            # Parse JSON response
            import json
            requirements_data = json.loads(response)

            requirements = []
            for idx, req_data in enumerate(requirements_data):
                req = TechnicalRequirement(
                    requirement_id=f"llm_req_{response_id}_{idx}",
                    category=req_data.get("category", "other"),
                    description=req_data.get("description", ""),
                    priority=req_data.get("priority", "medium"),
                    feasibility=req_data.get("feasibility", "unknown"),
                    related_responses=[response_id],
                    technical_notes=req_data.get("technical_notes", "")
                )
                requirements.append(req)

            return requirements

        except Exception as e:
            logger.debug(f"LLM requirement extraction failed: {e}")
            return []

    def _consolidate_requirements(
        self,
        requirements: List[TechnicalRequirement]
    ) -> List[TechnicalRequirement]:
        """
        Consolidate duplicate requirements.

        Args:
            requirements: List of requirements

        Returns:
            Consolidated requirements
        """
        consolidated = {}

        for req in requirements:
            # Create key from category and description
            key = f"{req['category']}_{req['description'][:30]}"

            if key in consolidated:
                # Merge related responses
                consolidated[key]["related_responses"].extend(req["related_responses"])
                consolidated[key]["related_responses"] = list(set(consolidated[key]["related_responses"]))

                # Upgrade priority if needed
                if req["priority"] == "high":
                    consolidated[key]["priority"] = "high"
                elif req["priority"] == "medium" and consolidated[key]["priority"] == "low":
                    consolidated[key]["priority"] = "medium"
            else:
                consolidated[key] = req

        return list(consolidated.values())

    def _prioritize_requirements(
        self,
        requirements: List[TechnicalRequirement]
    ) -> List[TechnicalRequirement]:
        """
        Prioritize requirements based on impact and frequency.

        Args:
            requirements: List of requirements

        Returns:
            Prioritized requirements
        """
        for req in requirements:
            # Adjust priority based on frequency
            response_count = len(req.get("related_responses", []))

            if response_count >= 5:
                req["priority"] = "critical"
            elif response_count >= 3 and req["priority"] != "high":
                req["priority"] = "high"

            # Consider feasibility in priority
            if req["feasibility"] == "low" and req["priority"] in ["critical", "high"]:
                req["technical_notes"] += " [需要技术突破]"

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        requirements.sort(key=lambda x: (priority_order.get(x["priority"], 4), -len(x["related_responses"])))

        return requirements

    def _generate_requirements_summary(
        self,
        requirements: List[TechnicalRequirement]
    ) -> Dict[str, Any]:
        """
        Generate requirements summary.

        Args:
            requirements: List of requirements

        Returns:
            Summary dictionary
        """
        summary = {
            "total": len(requirements),
            "by_category": {},
            "by_priority": {},
            "by_feasibility": {}
        }

        for req in requirements:
            # By category
            category = req["category"]
            if category not in summary["by_category"]:
                summary["by_category"][category] = 0
            summary["by_category"][category] += 1

            # By priority
            priority = req["priority"]
            if priority not in summary["by_priority"]:
                summary["by_priority"][priority] = 0
            summary["by_priority"][priority] += 1

            # By feasibility
            feasibility = req["feasibility"]
            if feasibility not in summary["by_feasibility"]:
                summary["by_feasibility"][feasibility] = 0
            summary["by_feasibility"][feasibility] += 1

        return summary

    def _generate_requirements_insights(
        self,
        requirements: List[TechnicalRequirement],
        summary: Dict[str, Any]
    ) -> List[str]:
        """
        Generate insights from requirements analysis.

        Args:
            requirements: List of requirements
            summary: Requirements summary

        Returns:
            List of insights
        """
        insights = []

        # Overall insight
        if summary["total"] > 0:
            insights.append(f"共识别出{summary['total']}项技术需求")

        # Priority insights
        critical = summary["by_priority"].get("critical", 0)
        high = summary["by_priority"].get("high", 0)

        if critical > 0:
            insights.append(f"存在{critical}项关键需求需要立即处理")
        if high > 0:
            insights.append(f"{high}项高优先级需求需要尽快安排")

        # Category insights
        top_category = max(summary["by_category"].items(), key=lambda x: x[1]) if summary["by_category"] else None

        if top_category:
            insights.append(f"{top_category[0]}类需求最多（{top_category[1]}项），是改进重点")

        # Feasibility insights
        low_feasibility = summary["by_feasibility"].get("low", 0)
        unknown_feasibility = summary["by_feasibility"].get("unknown", 0)

        if low_feasibility > 0:
            insights.append(f"{low_feasibility}项需求可行性较低，需要技术评估")
        if unknown_feasibility > 0:
            insights.append(f"{unknown_feasibility}项需求可行性待评估")

        # Specific requirement insights
        if requirements:
            top_req = requirements[0]
            if top_req["priority"] in ["critical", "high"]:
                insights.append(f"首要需求：{top_req['description']}（{len(top_req['related_responses'])}条反馈提及）")

        return insights