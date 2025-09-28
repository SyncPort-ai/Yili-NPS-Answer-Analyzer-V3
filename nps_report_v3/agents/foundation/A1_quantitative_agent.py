"""
A1 - Quantitative Analysis Agent
Foundation Pass Agent for NPS score calculation and statistical analysis.
"""

import logging
from typing import Dict, Any, List, Optional
import numpy as np
from scipy import stats
from collections import Counter

from ..base import FoundationAgent, AgentResult, AgentStatus
from ...state import NPSMetrics, CleanedData, SurveyResponse

logger = logging.getLogger(__name__)


class QuantitativeAnalysisAgent(FoundationAgent):
    """
    A1 - Quantitative Analysis Agent

    Responsibilities:
    - Calculate NPS scores and distributions
    - Perform statistical analysis
    - Calculate confidence intervals
    - Analyze score patterns by segments
    - Generate quantitative insights
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # NPS categories
        self.nps_categories = {
            "promoter": (9, 10),     # 推荐者
            "passive": (7, 8),        # 被动者
            "detractor": (0, 6)       # 贬损者
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Execute quantitative NPS analysis.

        Args:
            state: Current workflow state with cleaned_data

        Returns:
            AgentResult with NPS metrics
        """
        try:
            cleaned_data = state.get("cleaned_data")

            if not cleaned_data:
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.FAILED,
                    errors=["No cleaned data available"],
                    data={}
                )

            responses = cleaned_data.get("cleaned_responses", [])

            if not responses:
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.FAILED,
                    errors=["No valid responses to analyze"],
                    data={}
                )

            # Extract NPS scores
            scores = [r.get("nps_score") for r in responses if r.get("nps_score") is not None]

            if not scores:
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.FAILED,
                    errors=["No NPS scores found in responses"],
                    data={}
                )

            # Calculate basic NPS metrics
            nps_metrics = self._calculate_nps_metrics(scores)

            # Segment analysis
            segment_analysis = await self._analyze_segments(responses)

            # Temporal analysis if timestamps available
            temporal_analysis = self._analyze_temporal_patterns(responses)

            # Statistical tests
            statistical_analysis = self._perform_statistical_tests(scores)

            # Generate insights
            insights = self._generate_quantitative_insights(
                nps_metrics,
                segment_analysis,
                temporal_analysis,
                statistical_analysis
            )

            logger.info(
                f"Quantitative analysis complete: NPS = {nps_metrics['nps_score']:.1f}, "
                f"n = {nps_metrics['sample_size']}"
            )

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "nps_metrics": nps_metrics,
                    "segment_analysis": segment_analysis,
                    "temporal_analysis": temporal_analysis,
                    "statistical_analysis": statistical_analysis,
                    "quantitative_insights": insights
                }
            )

        except Exception as e:
            logger.error(f"Quantitative analysis failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)],
                data={}
            )

    def _calculate_nps_metrics(self, scores: List[int]) -> NPSMetrics:
        """
        Calculate NPS metrics from scores.

        Args:
            scores: List of NPS scores (0-10)

        Returns:
            NPSMetrics with calculated values
        """
        total = len(scores)

        # Categorize scores
        promoters = sum(1 for s in scores if s >= 9)
        passives = sum(1 for s in scores if 7 <= s <= 8)
        detractors = sum(1 for s in scores if s <= 6)

        # Calculate percentages
        promoters_pct = (promoters / total) * 100
        passives_pct = (passives / total) * 100
        detractors_pct = (detractors / total) * 100

        # Calculate NPS
        nps_score = promoters_pct - detractors_pct

        # Calculate confidence interval
        # Using standard error for proportion difference
        p_promoters = promoters / total
        p_detractors = detractors / total

        # Standard error for NPS
        se = np.sqrt((p_promoters * (1 - p_promoters) + p_detractors * (1 - p_detractors)) / total) * 100

        # 95% confidence interval
        ci_lower = nps_score - 1.96 * se
        ci_upper = nps_score + 1.96 * se

        # Statistical significance
        # Test if NPS is significantly different from 0
        z_score = nps_score / se if se > 0 else 0
        p_value = 2 * (1 - stats.norm.cdf(abs(z_score)))
        is_significant = p_value < 0.05

        return NPSMetrics(
            nps_score=nps_score,
            promoters_count=promoters,
            passives_count=passives,
            detractors_count=detractors,
            promoters_percentage=promoters_pct,
            passives_percentage=passives_pct,
            detractors_percentage=detractors_pct,
            confidence_interval=(ci_lower, ci_upper),
            sample_size=total,
            statistical_significance=is_significant
        )

    async def _analyze_segments(self, responses: List[SurveyResponse]) -> Dict[str, Any]:
        """
        Analyze NPS by different segments.

        Args:
            responses: Survey responses

        Returns:
            Segment analysis results
        """
        segments = {}

        # By product line
        product_segments = self._segment_by_attribute(responses, "product_line")

        if product_segments:
            segments["by_product"] = {
                product: self._calculate_segment_nps(data)
                for product, data in product_segments.items()
            }

        # By customer segment
        customer_segments = self._segment_by_attribute(responses, "customer_segment")

        if customer_segments:
            segments["by_customer"] = {
                segment: self._calculate_segment_nps(data)
                for segment, data in customer_segments.items()
            }

        # By channel
        channel_segments = self._segment_by_attribute(responses, "channel")

        if channel_segments:
            segments["by_channel"] = {
                channel: self._calculate_segment_nps(data)
                for channel, data in channel_segments.items()
            }

        # Score distribution analysis
        scores = [r.get("nps_score") for r in responses if r.get("nps_score") is not None]
        segments["score_distribution"] = dict(Counter(scores))

        # Quartile analysis
        if scores:
            segments["quartiles"] = {
                "q1": np.percentile(scores, 25),
                "median": np.percentile(scores, 50),
                "q3": np.percentile(scores, 75),
                "mean": np.mean(scores),
                "std": np.std(scores)
            }

        return segments

    def _segment_by_attribute(
        self,
        responses: List[SurveyResponse],
        attribute: str
    ) -> Dict[str, List[SurveyResponse]]:
        """
        Segment responses by attribute.

        Args:
            responses: Survey responses
            attribute: Attribute to segment by

        Returns:
            Dictionary of segmented responses
        """
        segments = {}

        for response in responses:
            value = response.get(attribute)

            if value:
                if value not in segments:
                    segments[value] = []
                segments[value].append(response)

        return segments

    def _calculate_segment_nps(self, responses: List[SurveyResponse]) -> Dict[str, Any]:
        """
        Calculate NPS for a segment.

        Args:
            responses: Segment responses

        Returns:
            Segment NPS metrics
        """
        scores = [r.get("nps_score") for r in responses if r.get("nps_score") is not None]

        if not scores:
            return {"nps": None, "count": 0}

        total = len(scores)
        promoters = sum(1 for s in scores if s >= 9)
        detractors = sum(1 for s in scores if s <= 6)

        nps = ((promoters - detractors) / total) * 100

        return {
            "nps": round(nps, 1),
            "count": total,
            "promoters": promoters,
            "detractors": detractors,
            "mean_score": round(np.mean(scores), 2)
        }

    def _analyze_temporal_patterns(self, responses: List[SurveyResponse]) -> Dict[str, Any]:
        """
        Analyze temporal patterns in NPS scores.

        Args:
            responses: Survey responses with timestamps

        Returns:
            Temporal analysis results
        """
        temporal = {}

        # Extract timestamped scores
        timed_scores = []

        for r in responses:
            if r.get("timestamp") and r.get("nps_score") is not None:
                timed_scores.append({
                    "timestamp": r["timestamp"],
                    "score": r["nps_score"]
                })

        if not timed_scores:
            return temporal

        # Sort by timestamp
        timed_scores.sort(key=lambda x: x["timestamp"])

        # Calculate rolling NPS (if enough data)
        if len(timed_scores) >= 10:
            window_size = max(10, len(timed_scores) // 5)
            rolling_nps = []

            for i in range(window_size, len(timed_scores) + 1):
                window_scores = [s["score"] for s in timed_scores[i-window_size:i]]
                window_nps = self._quick_nps(window_scores)
                rolling_nps.append(window_nps)

            temporal["rolling_nps"] = rolling_nps

            # Trend analysis
            if len(rolling_nps) > 1:
                # Simple linear regression for trend
                x = np.arange(len(rolling_nps))
                slope, intercept = np.polyfit(x, rolling_nps, 1)

                temporal["trend"] = {
                    "direction": "improving" if slope > 0 else "declining",
                    "slope": round(slope, 2),
                    "change_per_period": round(slope * len(rolling_nps), 1)
                }

        return temporal

    def _quick_nps(self, scores: List[int]) -> float:
        """Quick NPS calculation for a list of scores."""
        if not scores:
            return 0

        total = len(scores)
        promoters = sum(1 for s in scores if s >= 9)
        detractors = sum(1 for s in scores if s <= 6)

        return ((promoters - detractors) / total) * 100

    def _perform_statistical_tests(self, scores: List[int]) -> Dict[str, Any]:
        """
        Perform statistical tests on NPS data.

        Args:
            scores: NPS scores

        Returns:
            Statistical test results
        """
        tests = {}

        # Normality test
        if len(scores) >= 20:
            statistic, p_value = stats.shapiro(scores)
            tests["normality"] = {
                "test": "Shapiro-Wilk",
                "statistic": round(statistic, 4),
                "p_value": round(p_value, 4),
                "is_normal": p_value > 0.05
            }

        # Test against industry benchmark
        industry_benchmark = 30  # Example industry NPS benchmark

        if len(scores) >= 5:
            # One-sample t-test
            nps_values = []
            for _ in range(100):  # Bootstrap
                sample = np.random.choice(scores, size=len(scores), replace=True)
                nps_values.append(self._quick_nps(list(sample)))

            t_stat, p_value = stats.ttest_1samp(nps_values, industry_benchmark)

            tests["benchmark_comparison"] = {
                "benchmark": industry_benchmark,
                "mean_nps": round(np.mean(nps_values), 1),
                "t_statistic": round(t_stat, 2),
                "p_value": round(p_value, 4),
                "significantly_different": p_value < 0.05
            }

        return tests

    def _generate_quantitative_insights(
        self,
        nps_metrics: NPSMetrics,
        segment_analysis: Dict[str, Any],
        temporal_analysis: Dict[str, Any],
        statistical_analysis: Dict[str, Any]
    ) -> List[str]:
        """
        Generate quantitative insights from analysis.

        Args:
            nps_metrics: Basic NPS metrics
            segment_analysis: Segment analysis results
            temporal_analysis: Temporal patterns
            statistical_analysis: Statistical test results

        Returns:
            List of insights
        """
        insights = []

        # Overall NPS insight
        nps = nps_metrics["nps_score"]

        if nps >= 50:
            insights.append(f"NPS得分为{nps:.1f}，处于卓越水平，显示极高的客户忠诚度")
        elif nps >= 30:
            insights.append(f"NPS得分为{nps:.1f}，处于良好水平，客户满意度较高")
        elif nps >= 0:
            insights.append(f"NPS得分为{nps:.1f}，处于中等水平，有改进空间")
        else:
            insights.append(f"NPS得分为{nps:.1f}，处于警戒水平，需要重点关注")

        # Confidence interval insight
        ci_lower, ci_upper = nps_metrics["confidence_interval"]
        insights.append(
            f"95%置信区间为[{ci_lower:.1f}, {ci_upper:.1f}]，"
            f"样本量{nps_metrics['sample_size']}具有统计代表性"
        )

        # Segment insights
        if "by_product" in segment_analysis:
            products = segment_analysis["by_product"]

            if products:
                best_product = max(products.items(), key=lambda x: x[1].get("nps", -100))
                worst_product = min(products.items(), key=lambda x: x[1].get("nps", 100))

                if best_product[1]["nps"] is not None:
                    insights.append(
                        f"产品线表现差异明显：{best_product[0]}表现最佳(NPS={best_product[1]['nps']}), "
                        f"{worst_product[0]}需要改进(NPS={worst_product[1]['nps']})"
                    )

        # Temporal insights
        if temporal_analysis.get("trend"):
            trend = temporal_analysis["trend"]

            if trend["direction"] == "improving":
                insights.append(f"NPS呈上升趋势，每期平均提升{abs(trend['slope']):.1f}分")
            else:
                insights.append(f"NPS呈下降趋势，每期平均下降{abs(trend['slope']):.1f}分，需要关注")

        # Statistical insights
        if statistical_analysis.get("benchmark_comparison"):
            comparison = statistical_analysis["benchmark_comparison"]

            if comparison["significantly_different"]:
                if comparison["mean_nps"] > comparison["benchmark"]:
                    insights.append(f"NPS显著高于行业基准{comparison['benchmark']}分")
                else:
                    insights.append(f"NPS低于行业基准{comparison['benchmark']}分，需要改进")

        return insights