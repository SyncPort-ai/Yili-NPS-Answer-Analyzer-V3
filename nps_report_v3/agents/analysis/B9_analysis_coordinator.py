"""
B9 - Analysis Coordinator
Analysis Pass Agent for synthesizing and coordinating all analysis results.
"""

import logging
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict, Counter
import math

from ..base import AnalysisAgent, AgentResult, AgentStatus
from ...llm import LLMClient

logger = logging.getLogger(__name__)


class AnalysisCoordinatorAgent(AnalysisAgent):
    """
    B9 - Analysis Coordinator

    Responsibilities:
    - Synthesize and coordinate insights from all analysis agents (B1-B8)
    - Implement insight deduplication and conflict resolution
    - Add weighted ranking logic and quality scoring
    - Create cross-agent validation and consistency checks
    - Generate comprehensive analysis summary and priority insights
    """

    def __init__(self, agent_id: str = "B9", agent_name: str = "Analysis Coordinator",
                 llm_client: Optional[LLMClient] = None, **kwargs):
        super().__init__(agent_id, agent_name, **kwargs)
        self.llm_client = llm_client

        # Agent weights for insight prioritization
        self.agent_weights = {
            "B1": 0.9,   # Technical Requirements - high importance
            "B2": 1.2,   # Passive Analysis - critical for conversion
            "B3": 1.3,   # Detractor Analysis - critical for retention
            "B4": 0.8,   # Text Clustering - supportive analysis
            "B5": 1.1,   # Driver Analysis - strategic importance
            "B6": 1.0,   # Product Dimension - balanced importance
            "B7": 0.9,   # Geographic Dimension - market specific
            "B8": 0.9    # Channel Dimension - tactical importance
        }

        # Insight categories and their priority weights
        self.insight_categories = {
            "critical_issue": {"weight": 1.5, "urgency": "immediate"},
            "improvement_opportunity": {"weight": 1.2, "urgency": "short_term"},
            "competitive_advantage": {"weight": 1.1, "urgency": "medium_term"},
            "market_trend": {"weight": 0.9, "urgency": "long_term"},
            "operational_insight": {"weight": 1.0, "urgency": "short_term"},
            "strategic_direction": {"weight": 1.3, "urgency": "long_term"}
        }

        # Conflict resolution rules
        self.conflict_resolution_rules = {
            "contradictory_recommendations": "prioritize_by_agent_weight",
            "overlapping_insights": "merge_and_enhance",
            "inconsistent_data": "validate_and_flag",
            "priority_conflicts": "use_business_impact"
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Execute analysis coordination and synthesis.

        Args:
            state: Current workflow state with all analysis agent results

        Returns:
            AgentResult with coordinated analysis summary
        """
        try:
            # Collect results from all analysis agents
            analysis_results = self._collect_analysis_results(state)

            if not analysis_results:
                logger.warning("No analysis results available for coordination")
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.COMPLETED,
                    data={
                        "analysis_coordination": {
                            "total_insights": 0,
                            "coordinated_insights": [],
                            "priority_recommendations": [],
                            "synthesis_summary": {}
                        }
                    },
                    insights=[{"content": "暂无分析结果可供协调整合", "priority": "low"}],
                    confidence_score=0.1
                )

            # Extract and categorize insights
            raw_insights = self._extract_all_insights(analysis_results)

            # Perform insight deduplication
            deduplicated_insights = self._deduplicate_insights(raw_insights)

            # Resolve conflicts and inconsistencies
            resolved_insights = await self._resolve_conflicts(deduplicated_insights, analysis_results)

            # Score and rank insights
            scored_insights = self._score_and_rank_insights(resolved_insights, analysis_results)

            # Generate priority recommendations
            priority_recommendations = self._generate_priority_recommendations(scored_insights, analysis_results)

            # Perform cross-agent validation
            validation_results = self._perform_cross_validation(scored_insights, analysis_results)

            # Create synthesis summary
            synthesis_summary = await self._create_synthesis_summary(
                scored_insights, priority_recommendations, validation_results, analysis_results
            )

            # Generate meta-insights
            meta_insights = self._generate_meta_insights(scored_insights, analysis_results)

            logger.info(f"Coordinated {len(raw_insights)} raw insights into {len(scored_insights)} prioritized insights")

            # Convert scored insights and meta insights to the proper format
            formatted_insights = []

            # Add top scored insights
            for insight in scored_insights[:5]:  # Top 5 insights
                priority = "high" if insight.get("overall_score", 0) > 0.7 else "medium" if insight.get("overall_score", 0) > 0.5 else "low"
                formatted_insights.append({
                    "content": insight["content"],
                    "priority": priority
                })

            # Add meta insights
            for meta_insight in meta_insights:
                formatted_insights.append({
                    "content": meta_insight,
                    "priority": "medium"
                })

            # Calculate overall confidence based on average quality score
            avg_quality = sum(insight.get("quality_score", 0.5) for insight in scored_insights) / len(scored_insights) if scored_insights else 0.5

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "analysis_coordination": {
                        "total_raw_insights": len(raw_insights),
                        "total_coordinated_insights": len(scored_insights),
                        "coordinated_insights": scored_insights,
                        "priority_recommendations": priority_recommendations,
                        "validation_results": validation_results,
                        "synthesis_summary": synthesis_summary,
                        "meta_insights": meta_insights
                    }
                },
                insights=formatted_insights,
                confidence_score=min(avg_quality, 1.0)
            )

        except Exception as e:
            logger.error(f"Analysis coordination failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)],
                confidence_score=0.0
            )

    def _collect_analysis_results(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Collect results from all analysis agents."""
        analysis_results = {}

        # Expected analysis agent outputs
        expected_agents = [
            ("B1", "technical_requirements"),  # B1 Technical Requirements
            ("B2", "passive_analysis"),        # B2 Passive Analysis
            ("B3", "detractor_analysis"),      # B3 Detractor Analysis
            ("B4", "text_clustering"),         # B4 Text Clustering
            ("B5", "driver_analysis"),         # B5 Driver Analysis
            ("B6", "product_dimension"),       # B6 Product Dimension
            ("B7", "geographic_dimension"),    # B7 Geographic Dimension
            ("B8", "channel_dimension")        # B8 Channel Dimension
        ]

        for agent_id, output_key in expected_agents:
            if output_key in state:
                analysis_results[agent_id] = state[output_key]

        return analysis_results

    def _extract_all_insights(self, analysis_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract insights from all analysis results."""
        raw_insights = []

        for agent_id, results in analysis_results.items():
            agent_insights = self._extract_agent_insights(agent_id, results)
            raw_insights.extend(agent_insights)

        return raw_insights

    def _extract_agent_insights(self, agent_id: str, results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract insights from a specific agent's results."""
        insights = []

        # Extract insights based on agent type and result structure
        if agent_id == "B1":  # Technical Requirements
            tech_insights = results.get("technical_insights", [])
            for insight in tech_insights:
                insights.append({
                    "agent_id": agent_id,
                    "insight_type": "technical_requirement",
                    "content": insight,
                    "category": "improvement_opportunity",
                    "source_data": "technical_requirements"
                })

        elif agent_id == "B2":  # Passive Analysis
            passive_insights = results.get("passive_insights", [])
            for insight in passive_insights:
                insights.append({
                    "agent_id": agent_id,
                    "insight_type": "conversion_opportunity",
                    "content": insight,
                    "category": "improvement_opportunity",
                    "source_data": "passive_analysis"
                })

        elif agent_id == "B3":  # Detractor Analysis
            detractor_insights = results.get("detractor_insights", [])
            for insight in detractor_insights:
                insights.append({
                    "agent_id": agent_id,
                    "insight_type": "retention_risk",
                    "content": insight,
                    "category": "critical_issue",
                    "source_data": "detractor_analysis"
                })

        elif agent_id == "B4":  # Text Clustering
            theme_insights = results.get("theme_insights", [])
            for insight in theme_insights:
                insights.append({
                    "agent_id": agent_id,
                    "insight_type": "thematic_pattern",
                    "content": insight,
                    "category": "market_trend",
                    "source_data": "text_clustering"
                })

        elif agent_id == "B5":  # Driver Analysis
            driver_insights = results.get("driver_insights", [])
            for insight in driver_insights:
                insights.append({
                    "agent_id": agent_id,
                    "insight_type": "satisfaction_driver",
                    "content": insight,
                    "category": "strategic_direction",
                    "source_data": "driver_analysis"
                })

        elif agent_id == "B6":  # Product Dimension
            product_insights = results.get("product_insights", [])
            for insight in product_insights:
                insights.append({
                    "agent_id": agent_id,
                    "insight_type": "product_performance",
                    "content": insight,
                    "category": "competitive_advantage",
                    "source_data": "product_dimension"
                })

        elif agent_id == "B7":  # Geographic Dimension
            geographic_insights = results.get("geographic_insights", [])
            for insight in geographic_insights:
                insights.append({
                    "agent_id": agent_id,
                    "insight_type": "regional_pattern",
                    "content": insight,
                    "category": "market_trend",
                    "source_data": "geographic_dimension"
                })

        elif agent_id == "B8":  # Channel Dimension
            channel_insights = results.get("channel_insights", [])
            for insight in channel_insights:
                insights.append({
                    "agent_id": agent_id,
                    "insight_type": "channel_experience",
                    "content": insight,
                    "category": "operational_insight",
                    "source_data": "channel_dimension"
                })

        return insights

    def _deduplicate_insights(self, raw_insights: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove duplicate and highly similar insights."""
        deduplicated = []
        seen_content = set()

        for insight in raw_insights:
            content = insight["content"].strip().lower()

            # Check for exact duplicates
            if content in seen_content:
                continue

            # Check for high similarity with existing insights
            is_similar = False
            for existing in deduplicated:
                if self._calculate_similarity(content, existing["content"].lower()) > 0.8:
                    # Merge insights from different agents
                    existing["supporting_agents"] = existing.get("supporting_agents", [existing["agent_id"]])
                    if insight["agent_id"] not in existing["supporting_agents"]:
                        existing["supporting_agents"].append(insight["agent_id"])
                    is_similar = True
                    break

            if not is_similar:
                insight["supporting_agents"] = [insight["agent_id"]]
                deduplicated.append(insight)
                seen_content.add(content)

        logger.info(f"Deduplicated {len(raw_insights)} insights to {len(deduplicated)}")
        return deduplicated

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        # Simple Jaccard similarity based on words
        words1 = set(text1.split())
        words2 = set(text2.split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1.intersection(words2))
        union = len(words1.union(words2))

        return intersection / union if union > 0 else 0.0

    async def _resolve_conflicts(
        self,
        insights: List[Dict[str, Any]],
        analysis_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Resolve conflicts and inconsistencies between insights."""
        resolved_insights = []

        # Group potentially conflicting insights
        conflict_groups = self._identify_conflicts(insights)

        for group in conflict_groups:
            if len(group) == 1:
                # No conflict, add as is
                resolved_insights.extend(group)
            else:
                # Resolve conflict
                resolved = await self._resolve_conflict_group(group, analysis_results)
                resolved_insights.extend(resolved)

        return resolved_insights

    def _identify_conflicts(self, insights: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Identify groups of potentially conflicting insights."""
        # Simple approach: group by insight type and look for contradictions
        groups_by_type = defaultdict(list)

        for insight in insights:
            key = f"{insight['insight_type']}_{insight['category']}"
            groups_by_type[key].append(insight)

        # Return all groups (conflicting and non-conflicting)
        return list(groups_by_type.values())

    async def _resolve_conflict_group(
        self,
        conflict_group: List[Dict[str, Any]],
        analysis_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Resolve conflicts within a group of insights."""
        # Sort by agent weight and supporting evidence
        sorted_insights = sorted(
            conflict_group,
            key=lambda x: (
                self.agent_weights.get(x["agent_id"], 0.5) * len(x.get("supporting_agents", [x["agent_id"]])),
                -len(x["content"])  # Prefer more detailed insights
            ),
            reverse=True
        )

        # If insights are contradictory, use LLM to resolve
        if len(conflict_group) > 1 and self._are_contradictory(conflict_group):
            if self.llm_client:
                resolved = await self._llm_resolve_conflict(conflict_group, analysis_results)
                if resolved:
                    return resolved

        # Default: keep the highest-weighted insight and merge supporting agents
        primary_insight = sorted_insights[0]
        all_supporting_agents = set()
        for insight in conflict_group:
            all_supporting_agents.update(insight.get("supporting_agents", [insight["agent_id"]]))

        primary_insight["supporting_agents"] = list(all_supporting_agents)
        primary_insight["conflict_resolved"] = True

        return [primary_insight]

    def _are_contradictory(self, insights: List[Dict[str, Any]]) -> bool:
        """Check if insights are contradictory."""
        # Simple heuristic: look for opposing keywords
        opposing_pairs = [
            ("好", "差"), ("高", "低"), ("增长", "下降"),
            ("优势", "劣势"), ("机会", "威胁"), ("改善", "恶化")
        ]

        contents = [insight["content"] for insight in insights]

        for content1 in contents:
            for content2 in contents:
                if content1 != content2:
                    for pos_word, neg_word in opposing_pairs:
                        if pos_word in content1 and neg_word in content2:
                            return True
                        if neg_word in content1 and pos_word in content2:
                            return True

        return False

    def _score_and_rank_insights(
        self,
        insights: List[Dict[str, Any]],
        analysis_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Score and rank insights based on multiple criteria."""
        scored_insights = []

        for insight in insights:
            # Calculate composite score
            score = self._calculate_insight_score(insight, analysis_results)

            # Add quality assessment
            quality_score = self._assess_insight_quality(insight)

            # Add business impact estimation
            business_impact = self._estimate_business_impact(insight, analysis_results)

            scored_insight = {
                **insight,
                "priority_score": score,
                "quality_score": quality_score,
                "business_impact": business_impact,
                "overall_score": (score * 0.4 + quality_score * 0.3 + business_impact * 0.3)
            }

            scored_insights.append(scored_insight)

        # Sort by overall score
        scored_insights.sort(key=lambda x: x["overall_score"], reverse=True)

        return scored_insights

    def _calculate_insight_score(self, insight: Dict[str, Any], analysis_results: Dict[str, Any]) -> float:
        """Calculate priority score for insight."""
        base_score = 0.5  # Base score

        # Agent weight contribution
        agent_weight = self.agent_weights.get(insight["agent_id"], 0.5)
        base_score += agent_weight * 0.3

        # Category weight contribution
        category = insight["category"]
        category_info = self.insight_categories.get(category, {"weight": 1.0})
        base_score += category_info["weight"] * 0.2

        # Supporting agents boost
        supporting_count = len(insight.get("supporting_agents", [insight["agent_id"]]))
        base_score += min(supporting_count * 0.1, 0.3)  # Cap at 0.3

        # Content richness
        content_length = len(insight["content"])
        if content_length > 50:
            base_score += 0.1
        if content_length > 100:
            base_score += 0.1

        return min(base_score, 1.0)  # Cap at 1.0

    def _assess_insight_quality(self, insight: Dict[str, Any]) -> float:
        """Assess the quality of an insight."""
        quality_score = 0.5  # Base quality

        content = insight["content"]

        # Specificity indicators
        specific_indicators = ["具体", "明确", "详细", "数据", "比例", "提升", "改进"]
        specificity_count = sum(1 for indicator in specific_indicators if indicator in content)
        quality_score += min(specificity_count * 0.1, 0.3)

        # Actionability indicators
        action_indicators = ["需要", "建议", "应该", "可以", "推荐", "实施", "执行"]
        actionability_count = sum(1 for indicator in action_indicators if indicator in content)
        quality_score += min(actionability_count * 0.1, 0.2)

        # Evidence indicators
        evidence_indicators = ["发现", "分析", "显示", "表明", "证明", "结果"]
        evidence_count = sum(1 for indicator in evidence_indicators if indicator in content)
        quality_score += min(evidence_count * 0.05, 0.15)

        return min(quality_score, 1.0)

    def _estimate_business_impact(self, insight: Dict[str, Any], analysis_results: Dict[str, Any]) -> float:
        """Estimate business impact of insight."""
        impact_score = 0.5  # Base impact

        category = insight["category"]
        insight_type = insight["insight_type"]

        # Category-based impact
        if category == "critical_issue":
            impact_score += 0.3
        elif category == "strategic_direction":
            impact_score += 0.2
        elif category in ["improvement_opportunity", "competitive_advantage"]:
            impact_score += 0.15

        # Type-based impact
        high_impact_types = ["retention_risk", "conversion_opportunity", "satisfaction_driver"]
        if insight_type in high_impact_types:
            impact_score += 0.2

        # Supporting agents impact (cross-validation)
        supporting_count = len(insight.get("supporting_agents", []))
        if supporting_count > 1:
            impact_score += min(supporting_count * 0.05, 0.2)

        return min(impact_score, 1.0)

    def _generate_priority_recommendations(
        self,
        scored_insights: List[Dict[str, Any]],
        analysis_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate priority recommendations based on top insights."""
        recommendations = []

        # Top insights by category
        critical_insights = [i for i in scored_insights if i["category"] == "critical_issue"][:3]
        strategic_insights = [i for i in scored_insights if i["category"] == "strategic_direction"][:3]
        opportunity_insights = [i for i in scored_insights if i["category"] == "improvement_opportunity"][:3]

        # Generate recommendations for critical issues
        for i, insight in enumerate(critical_insights):
            rec = {
                "recommendation_id": f"critical_{i}",
                "priority": "critical",
                "title": f"紧急处理：{self._extract_action_from_insight(insight['content'])}",
                "description": insight["content"],
                "category": insight["category"],
                "source_agents": insight.get("supporting_agents", []),
                "business_impact": insight["business_impact"],
                "urgency": "immediate",
                "implementation_complexity": self._assess_complexity(insight),
                "expected_outcome": self._predict_outcome(insight)
            }
            recommendations.append(rec)

        # Generate recommendations for strategic directions
        for i, insight in enumerate(strategic_insights):
            rec = {
                "recommendation_id": f"strategic_{i}",
                "priority": "high",
                "title": f"战略重点：{self._extract_action_from_insight(insight['content'])}",
                "description": insight["content"],
                "category": insight["category"],
                "source_agents": insight.get("supporting_agents", []),
                "business_impact": insight["business_impact"],
                "urgency": "medium_term",
                "implementation_complexity": self._assess_complexity(insight),
                "expected_outcome": self._predict_outcome(insight)
            }
            recommendations.append(rec)

        # Generate recommendations for opportunities
        for i, insight in enumerate(opportunity_insights):
            rec = {
                "recommendation_id": f"opportunity_{i}",
                "priority": "medium",
                "title": f"改进机会：{self._extract_action_from_insight(insight['content'])}",
                "description": insight["content"],
                "category": insight["category"],
                "source_agents": insight.get("supporting_agents", []),
                "business_impact": insight["business_impact"],
                "urgency": "short_term",
                "implementation_complexity": self._assess_complexity(insight),
                "expected_outcome": self._predict_outcome(insight)
            }
            recommendations.append(rec)

        return recommendations

    def _extract_action_from_insight(self, content: str) -> str:
        """Extract actionable title from insight content."""
        # Simple extraction - take first sentence or meaningful phrase
        sentences = content.split("。")
        first_sentence = sentences[0].strip()

        # Limit length and clean
        if len(first_sentence) > 30:
            first_sentence = first_sentence[:30] + "..."

        return first_sentence or "采取相应措施"

    def _assess_complexity(self, insight: Dict[str, Any]) -> str:
        """Assess implementation complexity of insight."""
        content = insight["content"]
        category = insight["category"]

        # Complexity indicators
        high_complexity_words = ["系统", "架构", "重构", "变革", "转型", "全面"]
        medium_complexity_words = ["改进", "优化", "调整", "提升", "加强"]
        low_complexity_words = ["修复", "解决", "处理", "关注", "监控"]

        if any(word in content for word in high_complexity_words):
            return "high"
        elif any(word in content for word in medium_complexity_words):
            return "medium"
        elif any(word in content for word in low_complexity_words):
            return "low"
        else:
            # Default based on category
            if category in ["strategic_direction", "competitive_advantage"]:
                return "high"
            elif category in ["improvement_opportunity", "operational_insight"]:
                return "medium"
            else:
                return "low"

    def _predict_outcome(self, insight: Dict[str, Any]) -> str:
        """Predict expected outcome of implementing insight."""
        category = insight["category"]
        insight_type = insight["insight_type"]

        outcome_map = {
            "critical_issue": "风险缓解，客户流失减少",
            "improvement_opportunity": "客户满意度提升，NPS改善",
            "competitive_advantage": "市场地位强化，竞争优势扩大",
            "strategic_direction": "长期价值创造，业务增长",
            "operational_insight": "运营效率提升，成本优化",
            "market_trend": "市场适应性增强，前瞻性布局"
        }

        return outcome_map.get(category, "整体表现改善")

    def _perform_cross_validation(
        self,
        insights: List[Dict[str, Any]],
        analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform cross-agent validation of insights."""
        validation_results = {
            "consistency_score": 0.0,
            "validation_flags": [],
            "cross_confirmations": [],
            "data_gaps": []
        }

        # Check for consistency across agents
        consistency_checks = []
        agent_pairs = []

        # Create agent pairs for cross-validation
        agent_ids = list(analysis_results.keys())
        for i in range(len(agent_ids)):
            for j in range(i+1, len(agent_ids)):
                agent_pairs.append((agent_ids[i], agent_ids[j]))

        # Validate insights consistency
        for insight in insights:
            supporting_agents = insight.get("supporting_agents", [])
            if len(supporting_agents) > 1:
                # Multi-agent confirmation
                validation_results["cross_confirmations"].append({
                    "insight": insight["content"][:100] + "...",
                    "confirming_agents": supporting_agents,
                    "confidence_boost": len(supporting_agents) * 0.1
                })

        # Check for data completeness
        expected_data_types = ["nps_scores", "response_count", "satisfaction_metrics"]
        for agent_id, results in analysis_results.items():
            missing_data = []
            # Simple check for common data structures
            if not results:
                missing_data.append("no_results")
            elif isinstance(results, dict):
                # Check for minimum expected structure
                if not any(key in results for key in ["insights", "analysis", "metrics", "recommendations"]):
                    missing_data.append("incomplete_structure")

            if missing_data:
                validation_results["data_gaps"].append({
                    "agent": agent_id,
                    "missing_data": missing_data
                })

        # Calculate overall consistency score
        total_insights = len(insights)
        confirmed_insights = len(validation_results["cross_confirmations"])
        validation_results["consistency_score"] = (
            confirmed_insights / total_insights if total_insights > 0 else 0
        )

        return validation_results

    async def _create_synthesis_summary(
        self,
        insights: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]],
        validation_results: Dict[str, Any],
        analysis_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create comprehensive synthesis summary."""
        summary = {
            "executive_overview": "",
            "key_findings": [],
            "strategic_priorities": [],
            "immediate_actions": [],
            "performance_metrics": {},
            "confidence_assessment": {}
        }

        # Generate executive overview
        total_insights = len(insights)
        critical_count = len([i for i in insights if i["category"] == "critical_issue"])
        strategic_count = len([i for i in insights if i["category"] == "strategic_direction"])

        summary["executive_overview"] = (
            f"综合分析识别出{total_insights}项关键洞察，其中{critical_count}项紧急议题需要立即关注，"
            f"{strategic_count}项战略性发现指引长期发展方向。"
        )

        # Extract key findings
        top_insights = insights[:5]  # Top 5 insights
        for insight in top_insights:
            summary["key_findings"].append({
                "finding": insight["content"],
                "category": insight["category"],
                "confidence": insight["quality_score"],
                "impact": insight["business_impact"]
            })

        # Strategic priorities
        strategic_recommendations = [r for r in recommendations if r["priority"] in ["critical", "high"]]
        for rec in strategic_recommendations[:3]:  # Top 3
            summary["strategic_priorities"].append({
                "priority": rec["title"],
                "description": rec["description"],
                "urgency": rec["urgency"],
                "complexity": rec["implementation_complexity"]
            })

        # Immediate actions
        critical_recommendations = [r for r in recommendations if r["priority"] == "critical"]
        for rec in critical_recommendations:
            summary["immediate_actions"].append({
                "action": rec["title"],
                "rationale": rec["description"],
                "expected_outcome": rec["expected_outcome"]
            })

        # Performance metrics summary
        summary["performance_metrics"] = {
            "total_insights_generated": total_insights,
            "cross_validated_insights": len(validation_results.get("cross_confirmations", [])),
            "high_confidence_insights": len([i for i in insights if i["quality_score"] > 0.7]),
            "agent_coverage": len(analysis_results),
            "consistency_score": validation_results.get("consistency_score", 0)
        }

        # Confidence assessment
        avg_quality = sum(i["quality_score"] for i in insights) / len(insights) if insights else 0
        summary["confidence_assessment"] = {
            "overall_confidence": "high" if avg_quality > 0.7 else "medium" if avg_quality > 0.5 else "low",
            "data_completeness": 1.0 - (len(validation_results.get("data_gaps", [])) / len(analysis_results)),
            "cross_validation_rate": validation_results.get("consistency_score", 0),
            "recommendation_confidence": avg_quality
        }

        # Enhanced synthesis with LLM
        if self.llm_client:
            enhanced_summary = await self._enhance_synthesis_with_llm(summary, insights, recommendations)
            if enhanced_summary:
                summary.update(enhanced_summary)

        return summary

    def _generate_meta_insights(
        self,
        insights: List[Dict[str, Any]],
        analysis_results: Dict[str, Any]
    ) -> List[str]:
        """Generate meta-insights about the analysis process and results."""
        meta_insights = []

        # Analysis coverage insights
        agent_count = len(analysis_results)
        meta_insights.append(f"多角度分析覆盖{agent_count}个维度，确保洞察全面性")

        # Insight quality insights
        high_quality_count = len([i for i in insights if i["quality_score"] > 0.7])
        quality_ratio = high_quality_count / len(insights) if insights else 0

        if quality_ratio > 0.6:
            meta_insights.append(f"高质量洞察占比{quality_ratio:.1%}，分析结果可靠性强")
        elif quality_ratio < 0.4:
            meta_insights.append("部分洞察质量有待提升，需要更多数据验证")

        # Cross-validation insights
        cross_validated = len([i for i in insights if len(i.get("supporting_agents", [])) > 1])
        if cross_validated > 0:
            meta_insights.append(f"{cross_validated}项洞察获得多维度验证，增强了结论可信度")

        # Category distribution insights
        category_counts = Counter(i["category"] for i in insights)
        dominant_category = category_counts.most_common(1)[0] if category_counts else None

        if dominant_category:
            category_name = dominant_category[0]
            category_count = dominant_category[1]
            if category_name == "critical_issue":
                meta_insights.append(f"识别出{category_count}个关键问题，建议优先处理")
            elif category_name == "improvement_opportunity":
                meta_insights.append(f"发现{category_count}个改进机会，具有较好的优化潜力")

        # Analysis completeness
        if agent_count >= 6:
            meta_insights.append("分析覆盖面广，从多个角度深入理解客户反馈")
        else:
            meta_insights.append("分析范围可进一步扩展，增加更多维度的洞察")

        return meta_insights

    async def _llm_resolve_conflict(
        self,
        conflict_group: List[Dict[str, Any]],
        analysis_results: Dict[str, Any]
    ) -> Optional[List[Dict[str, Any]]]:
        """Use LLM to resolve conflicts between insights."""
        if not self.llm_client:
            return None

        try:
            # Prepare conflict information for LLM
            conflict_texts = [insight["content"] for insight in conflict_group]
            agent_info = [f"{insight['agent_id']}: {insight['content']}" for insight in conflict_group]

            prompt = f"""
分析以下可能存在冲突的洞察，并提供解决方案：

冲突洞察：
{chr(10).join(agent_info)}

请分析：
1. 这些洞察是否真的冲突？
2. 如果冲突，如何调和？
3. 如果不冲突，如何整合？

以JSON格式返回：
{{
    "has_conflict": true/false,
    "resolution_approach": "merge/prioritize/contextualize",
    "resolved_insight": "整合后的洞察内容",
    "confidence": 0.0-1.0,
    "explanation": "解决方案说明"
}}
"""

            response = await self.llm_client.generate(prompt, temperature=0.3)

            import json
            resolution = json.loads(response)

            if resolution.get("has_conflict", False):
                # Create resolved insight
                resolved_insight = {
                    "agent_id": "B9",  # Coordinator resolved
                    "insight_type": "conflict_resolved",
                    "content": resolution.get("resolved_insight", ""),
                    "category": conflict_group[0]["category"],  # Use first insight's category
                    "source_data": "conflict_resolution",
                    "supporting_agents": [i["agent_id"] for i in conflict_group],
                    "conflict_resolved": True,
                    "resolution_confidence": resolution.get("confidence", 0.5)
                }
                return [resolved_insight]
            else:
                # No real conflict, merge insights
                merged_content = " | ".join(set(i["content"] for i in conflict_group))
                merged_insight = conflict_group[0].copy()
                merged_insight["content"] = merged_content
                merged_insight["supporting_agents"] = list(set(
                    agent for insight in conflict_group
                    for agent in insight.get("supporting_agents", [insight["agent_id"]])
                ))
                return [merged_insight]

        except Exception as e:
            logger.debug(f"LLM conflict resolution failed: {e}")
            return None

    async def _enhance_synthesis_with_llm(
        self,
        summary: Dict[str, Any],
        insights: List[Dict[str, Any]],
        recommendations: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Use LLM to enhance synthesis summary."""
        if not self.llm_client:
            return None

        try:
            # Prepare summary for LLM enhancement
            key_findings = [f["finding"] for f in summary.get("key_findings", [])]
            priorities = [p["priority"] for p in summary.get("strategic_priorities", [])]

            prompt = f"""
基于以下分析结果，提供战略层面的综合总结：

关键发现：
{chr(10).join(key_findings)}

战略优先级：
{chr(10).join(priorities)}

请提供：
1. 战略层面的核心洞察
2. 关键成功因素识别
3. 风险评估和缓解建议
4. 长期发展建议

以JSON格式返回：
{{
    "strategic_insights": ["洞察1", "洞察2"],
    "success_factors": ["因素1", "因素2"],
    "risk_assessment": {{"risks": ["风险1"], "mitigations": ["缓解措施1"]}},
    "long_term_recommendations": ["建议1", "建议2"]
}}
"""

            response = await self.llm_client.generate(prompt, temperature=0.3)

            import json
            enhancement = json.loads(response)

            return {
                "strategic_insights": enhancement.get("strategic_insights", []),
                "success_factors": enhancement.get("success_factors", []),
                "risk_assessment": enhancement.get("risk_assessment", {}),
                "long_term_recommendations": enhancement.get("long_term_recommendations", [])
            }

        except Exception as e:
            logger.debug(f"LLM synthesis enhancement failed: {e}")
            return None
