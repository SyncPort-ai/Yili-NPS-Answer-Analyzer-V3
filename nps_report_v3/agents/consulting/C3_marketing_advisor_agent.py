"""
C3 - Marketing Advisor Agent
Consulting Pass Agent for generating marketing strategy recommendations.
"""

import logging
from typing import Dict, Any, List, Optional
from collections import Counter

from ..base import ConsultingAgent, ConfidenceConstrainedAgent, AgentResult, AgentStatus
from ...llm import LLMClient

logger = logging.getLogger(__name__)


class MarketingRecommendation(dict):
    """Marketing recommendation structure"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure required fields exist
        self.setdefault("recommendation_id", "")
        self.setdefault("title", "")
        self.setdefault("description", "")
        self.setdefault("category", "")
        self.setdefault("priority", "medium_term")
        self.setdefault("target_audience", [])
        self.setdefault("channels", [])
        self.setdefault("budget_range", "")
        self.setdefault("expected_outcomes", [])
        self.setdefault("kpi_metrics", [])


class MarketingAdvisorAgent(ConfidenceConstrainedAgent):
    """
    C3 - Marketing Advisor Agent

    Responsibilities:
    - Analyze brand perception and marketing effectiveness
    - Generate marketing strategy recommendations
    - Identify target audience insights and segments
    - Suggest channel optimization and messaging strategies
    - Provide competitive marketing intelligence
    """

    def __init__(self, agent_id: str = "C3", agent_name: str = "Marketing Advisor Agent",
                 llm_client: Optional[LLMClient] = None, **kwargs):
        super().__init__(agent_id, agent_name, **kwargs)
        self.llm_client = llm_client
        self.min_confidence = 0.6  # Marketing recommendations can be made with moderate confidence

        # Marketing strategy categories
        self.marketing_categories = {
            "brand_positioning": {
                "title": "品牌定位",
                "keywords": ["品牌", "形象", "认知", "定位", "价值"],
                "metrics": ["品牌认知度", "品牌好感度", "品牌联想"]
            },
            "messaging": {
                "title": "信息传达",
                "keywords": ["宣传", "广告", "信息", "沟通", "传达"],
                "metrics": ["信息传达效果", "消息记忆度", "理解准确性"]
            },
            "channel_optimization": {
                "title": "渠道优化",
                "keywords": ["渠道", "平台", "推广", "投放", "媒体"],
                "metrics": ["渠道效率", "触达率", "转化率"]
            },
            "customer_engagement": {
                "title": "客户互动",
                "keywords": ["互动", "参与", "活动", "体验", "关系"],
                "metrics": ["互动率", "参与度", "客户活跃度"]
            },
            "digital_marketing": {
                "title": "数字营销",
                "keywords": ["数字", "在线", "社交", "电商", "网络"],
                "metrics": ["在线曝光", "数字转化", "社交参与"]
            }
        }

        # Target audience segments
        self.audience_segments = {
            "young_families": {
                "name": "年轻家庭",
                "characteristics": ["25-35岁", "有孩子", "注重健康", "价格敏感"],
                "channels": ["社交媒体", "母婴平台", "电商直播"]
            },
            "health_conscious": {
                "name": "健康意识群体",
                "characteristics": ["30-45岁", "重视健康", "愿意溢价", "信息敏感"],
                "channels": ["健康平台", "专业媒体", "KOL推荐"]
            },
            "premium_consumers": {
                "name": "高端消费者",
                "characteristics": ["35-50岁", "收入较高", "品质导向", "品牌忠诚"],
                "channels": ["高端媒体", "线下体验", "会员营销"]
            },
            "price_sensitive": {
                "name": "价格敏感群体",
                "characteristics": ["25-40岁", "价格导向", "促销敏感", "比价习惯"],
                "channels": ["促销平台", "比价应用", "团购渠道"]
            }
        }

        # Marketing channels
        self.marketing_channels = {
            "social_media": {
                "name": "社交媒体",
                "platforms": ["微信", "微博", "抖音", "小红书"],
                "strengths": ["高互动", "病毒传播", "年轻用户"],
                "considerations": ["内容质量", "KOL合作", "用户生成内容"]
            },
            "ecommerce": {
                "name": "电商营销",
                "platforms": ["天猫", "京东", "拼多多", "抖音电商"],
                "strengths": ["直接转化", "数据精准", "个性推荐"],
                "considerations": ["站内SEO", "评价管理", "促销策略"]
            },
            "traditional_media": {
                "name": "传统媒体",
                "platforms": ["电视", "广播", "户外", "平面媒体"],
                "strengths": ["覆盖面广", "权威性", "品牌建设"],
                "considerations": ["媒体选择", "时段优化", "创意质量"]
            },
            "digital_advertising": {
                "name": "数字广告",
                "platforms": ["百度", "腾讯广告", "头条系", "阿里妈妈"],
                "strengths": ["精准定向", "数据跟踪", "灵活调整"],
                "considerations": ["定向策略", "创意优化", "转化跟踪"]
            }
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Execute marketing advisory analysis.

        Args:
            state: Current workflow state with all analysis results

        Returns:
            AgentResult with marketing recommendations
        """
        try:
            # Check confidence in marketing-related data
            confidence_check = self._assess_marketing_confidence(state)

            if confidence_check["confidence"] < self.min_confidence:
                logger.warning(f"Marketing confidence {confidence_check['confidence']:.2f} below threshold {self.min_confidence}")
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.FAILED,
                    errors=[f"Insufficient confidence in marketing data: {confidence_check['issues']}"],
                    confidence_score=0.0
                )

            # Extract marketing insights
            marketing_insights = await self._extract_marketing_insights(state)

            # Analyze brand perception
            brand_analysis = self._analyze_brand_perception(marketing_insights, state)

            # Identify audience segments and needs
            audience_analysis = self._analyze_audience_segments(marketing_insights, state)

            # Analyze channel performance
            channel_analysis = self._analyze_channel_effectiveness(marketing_insights, state)

            # Generate marketing recommendations
            recommendations = await self._generate_marketing_recommendations(
                marketing_insights, brand_analysis, audience_analysis, channel_analysis, state
            )

            # Prioritize recommendations
            prioritized = self._prioritize_marketing_recommendations(recommendations)

            # Create marketing action plan
            action_plan = self._create_marketing_action_plan(prioritized)

            # Generate competitive insights
            competitive_insights = self._generate_competitive_marketing_insights(brand_analysis, state)

            logger.info(f"Generated {len(prioritized)} marketing recommendations")

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "marketing_recommendations": prioritized,
                    "marketing_action_plan": action_plan,
                    "brand_analysis": brand_analysis,
                    "audience_analysis": audience_analysis,
                    "channel_analysis": channel_analysis,
                    "competitive_insights": competitive_insights,
                    "marketing_insights": marketing_insights,
                    "confidence": confidence_check["confidence"]
                },
                insights=[{"type": "marketing", "count": len(prioritized)}],
                confidence_score=confidence_check["confidence"]
            )

        except Exception as e:
            logger.error(f"Marketing advisory failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)],
                confidence_score=0.0
            )

    def _assess_marketing_confidence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess confidence in marketing-related data.

        Args:
            state: Current workflow state

        Returns:
            Confidence assessment
        """
        confidence_factors = []
        issues = []

        # Check customer feedback volume
        tagged_responses = state.get("tagged_responses", [])
        if len(tagged_responses) >= 20:
            confidence_factors.append(0.9)
        elif len(tagged_responses) >= 10:
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.4)
            issues.append("Limited customer feedback for marketing analysis")

        # Check brand-related mentions
        brand_mentions = sum(1 for response in tagged_responses
                           if any(keyword in str(response).lower()
                                 for category in self.marketing_categories.values()
                                 for keyword in category["keywords"]))

        if brand_mentions >= 10:
            confidence_factors.append(0.8)
        elif brand_mentions >= 5:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.3)
            issues.append("Few brand/marketing-related mentions")

        # Check sentiment distribution
        sentiment_counts = Counter(r.get("sentiment", "neutral") for r in tagged_responses)
        if len(sentiment_counts) >= 2:  # Has both positive and negative feedback
            confidence_factors.append(0.7)
        else:
            confidence_factors.append(0.5)
            issues.append("Limited sentiment diversity for marketing insights")

        # Check channel dimension analysis
        channel_insights = state.get("channel_dimension_analysis")
        if channel_insights and len(channel_insights.get("insights", [])) > 0:
            confidence_factors.append(0.8)
        else:
            confidence_factors.append(0.4)
            issues.append("Limited channel performance data")

        overall_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0

        return {
            "confidence": overall_confidence,
            "factors": confidence_factors,
            "issues": issues
        }

    async def _extract_marketing_insights(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract marketing-specific insights from analysis results.

        Args:
            state: Current workflow state

        Returns:
            Marketing insights
        """
        insights = {
            "brand_mentions": [],
            "channel_feedback": {},
            "messaging_themes": [],
            "customer_journey_issues": [],
            "competitive_references": []
        }

        tagged_responses = state.get("tagged_responses", [])

        # Extract brand and marketing related feedback
        for response in tagged_responses:
            response_text = str(response.get("comment", "")).lower()

            # Brand mentions
            if any(brand in response_text for brand in ["伊利", "安慕希", "金典", "舒化"]):
                insights["brand_mentions"].append({
                    "response_id": response.get("response_id"),
                    "sentiment": response.get("sentiment", "neutral"),
                    "content": response.get("comment", "")[:200]
                })

            # Channel feedback
            for channel, config in self.marketing_channels.items():
                if any(platform in response_text for platform in config["platforms"]):
                    if channel not in insights["channel_feedback"]:
                        insights["channel_feedback"][channel] = []
                    insights["channel_feedback"][channel].append({
                        "sentiment": response.get("sentiment", "neutral"),
                        "feedback": response.get("comment", "")[:150]
                    })

        # Analyze semantic clusters for marketing themes
        clusters = state.get("semantic_clusters", [])
        for cluster in clusters[:5]:  # Top 5 clusters
            theme = cluster.get("theme", "")

            # Check if cluster relates to marketing categories
            for category, config in self.marketing_categories.items():
                if any(keyword in theme.lower() for keyword in config["keywords"]):
                    insights["messaging_themes"].append({
                        "category": category,
                        "theme": theme,
                        "size": cluster.get("size", 0),
                        "sentiment_dist": cluster.get("sentiment_distribution", {}),
                        "representative_quotes": cluster.get("representative_quotes", [])[:2]
                    })

        # Extract competitive references
        competitive_keywords = ["蒙牛", "光明", "君乐宝", "三元", "竞争", "对比", "比较"]
        for response in tagged_responses:
            response_text = str(response.get("comment", "")).lower()
            if any(keyword in response_text for keyword in competitive_keywords):
                insights["competitive_references"].append({
                    "sentiment": response.get("sentiment", "neutral"),
                    "content": response.get("comment", "")[:200]
                })

        # Extract customer journey issues from technical requirements
        tech_reqs = state.get("technical_requirements", [])
        journey_categories = ["渠道", "购买", "服务", "体验", "沟通"]

        for req in tech_reqs:
            description = req.get("description", "").lower()
            if any(category in description for category in journey_categories):
                insights["customer_journey_issues"].append({
                    "category": req.get("category", ""),
                    "description": req["description"],
                    "priority": req.get("priority", "medium"),
                    "impact": len(req.get("related_responses", []))
                })

        return insights

    def _analyze_brand_perception(
        self,
        marketing_insights: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze brand perception from customer feedback.

        Args:
            marketing_insights: Marketing insights
            state: Current workflow state

        Returns:
            Brand perception analysis
        """
        analysis = {
            "overall_sentiment": "neutral",
            "brand_strengths": [],
            "brand_weaknesses": [],
            "brand_associations": [],
            "perception_gaps": []
        }

        # Analyze overall brand sentiment
        brand_mentions = marketing_insights["brand_mentions"]
        if brand_mentions:
            sentiment_counts = Counter(mention["sentiment"] for mention in brand_mentions)
            total = len(brand_mentions)

            positive_ratio = sentiment_counts.get("positive", 0) / total
            negative_ratio = sentiment_counts.get("negative", 0) / total

            if positive_ratio > 0.6:
                analysis["overall_sentiment"] = "positive"
            elif negative_ratio > 0.5:
                analysis["overall_sentiment"] = "negative"
            else:
                analysis["overall_sentiment"] = "mixed"

        # Extract brand strengths and weaknesses from messaging themes
        for theme in marketing_insights["messaging_themes"]:
            sentiment_dist = theme["sentiment_dist"]
            if sentiment_dist.get("positive", 0) > 0.7:
                analysis["brand_strengths"].append({
                    "area": theme["category"],
                    "theme": theme["theme"],
                    "supporting_evidence": theme["representative_quotes"]
                })
            elif sentiment_dist.get("negative", 0) > 0.6:
                analysis["brand_weaknesses"].append({
                    "area": theme["category"],
                    "issue": theme["theme"],
                    "severity": "high" if sentiment_dist["negative"] > 0.8 else "medium",
                    "supporting_evidence": theme["representative_quotes"]
                })

        # Identify brand associations
        nps_score = state.get("nps_metrics", {}).get("nps_score", 0)
        if nps_score >= 50:
            analysis["brand_associations"].append("高客户忠诚度品牌")
        elif nps_score >= 30:
            analysis["brand_associations"].append("良好口碑品牌")
        elif nps_score < 0:
            analysis["brand_associations"].append("品牌形象需要提升")

        # Identify perception gaps
        quality_themes = [t for t in marketing_insights["messaging_themes"] if t["category"] == "brand_positioning"]
        if quality_themes and any(t["sentiment_dist"].get("negative", 0) > 0.5 for t in quality_themes):
            analysis["perception_gaps"].append("品牌定位与客户期望存在差距")

        return analysis

    def _analyze_audience_segments(
        self,
        marketing_insights: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze audience segments and their characteristics.

        Args:
            marketing_insights: Marketing insights
            state: Current workflow state

        Returns:
            Audience analysis
        """
        analysis = {
            "identified_segments": [],
            "segment_needs": {},
            "high_value_segments": [],
            "underserved_segments": []
        }

        # Analyze geographic dimension for regional segments
        geo_analysis = state.get("geographic_dimension_analysis", {})
        if geo_analysis:
            regional_insights = geo_analysis.get("insights", [])
            for insight in regional_insights[:3]:
                analysis["identified_segments"].append({
                    "segment_type": "geographic",
                    "name": f"地域细分：{insight.get('region', '')}",
                    "characteristics": insight.get("characteristics", []),
                    "needs": insight.get("specific_needs", [])
                })

        # Analyze NPS distribution for loyalty segments
        nps_metrics = state.get("nps_metrics", {})
        if nps_metrics:
            promoters_pct = nps_metrics.get("promoters_percentage", 0)
            passives_pct = nps_metrics.get("passives_percentage", 0)
            detractors_pct = nps_metrics.get("detractors_percentage", 0)

            if promoters_pct > 30:
                analysis["high_value_segments"].append({
                    "name": "品牌忠诚者",
                    "size_percentage": promoters_pct,
                    "characteristics": ["高满意度", "推荐意愿强", "复购率高"],
                    "marketing_approach": "品牌大使培养"
                })

            if passives_pct > 40:
                analysis["underserved_segments"].append({
                    "name": "观望客户",
                    "size_percentage": passives_pct,
                    "characteristics": ["满意度一般", "转化潜力大", "需要激活"],
                    "marketing_approach": "针对性激活营销"
                })

        # Analyze messaging themes for behavioral segments
        messaging_themes = marketing_insights["messaging_themes"]
        behavior_segments = {}

        for theme in messaging_themes:
            category = theme["category"]
            if category not in behavior_segments:
                behavior_segments[category] = []
            behavior_segments[category].append(theme)

        for category, themes in behavior_segments.items():
            if len(themes) >= 2:  # Significant behavior pattern
                analysis["segment_needs"][category] = {
                    "primary_themes": [t["theme"] for t in themes[:2]],
                    "sentiment_pattern": themes[0]["sentiment_dist"],
                    "engagement_level": sum(t["size"] for t in themes)
                }

        return analysis

    def _analyze_channel_effectiveness(
        self,
        marketing_insights: Dict[str, Any],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze marketing channel effectiveness.

        Args:
            marketing_insights: Marketing insights
            state: Current workflow state

        Returns:
            Channel effectiveness analysis
        """
        analysis = {
            "channel_performance": {},
            "channel_gaps": [],
            "optimization_opportunities": [],
            "recommended_channels": []
        }

        # Analyze channel feedback
        channel_feedback = marketing_insights["channel_feedback"]

        for channel, feedbacks in channel_feedback.items():
            if feedbacks:
                sentiment_counts = Counter(f["sentiment"] for f in feedbacks)
                total = len(feedbacks)

                positive_ratio = sentiment_counts.get("positive", 0) / total
                negative_ratio = sentiment_counts.get("negative", 0) / total

                analysis["channel_performance"][channel] = {
                    "feedback_volume": total,
                    "positive_ratio": positive_ratio,
                    "negative_ratio": negative_ratio,
                    "effectiveness_score": positive_ratio - negative_ratio,
                    "key_feedback": [f["feedback"] for f in feedbacks[:2]]
                }

        # Identify channel gaps
        channel_analysis = state.get("channel_dimension_analysis", {})
        if channel_analysis:
            channel_issues = channel_analysis.get("issues", [])
            for issue in channel_issues:
                if issue.get("severity") in ["high", "critical"]:
                    analysis["channel_gaps"].append({
                        "channel": issue.get("channel", ""),
                        "issue": issue.get("description", ""),
                        "impact": issue.get("impact", "medium")
                    })

        # Identify optimization opportunities
        for channel, perf in analysis["channel_performance"].items():
            if perf["feedback_volume"] >= 3:  # Sufficient data
                if perf["effectiveness_score"] < 0:
                    analysis["optimization_opportunities"].append({
                        "channel": channel,
                        "opportunity": "改善负面体验",
                        "priority": "high",
                        "specific_issues": perf["key_feedback"]
                    })
                elif 0 <= perf["effectiveness_score"] < 0.3:
                    analysis["optimization_opportunities"].append({
                        "channel": channel,
                        "opportunity": "提升整体效果",
                        "priority": "medium",
                        "potential": "中等提升空间"
                    })

        # Recommend high-potential channels
        for segment_name, segment in self.audience_segments.items():
            if segment_name in ["young_families", "health_conscious"]:  # Key target segments
                for channel in segment["channels"]:
                    if channel not in [c.lower().replace(" ", "_") for c in channel_feedback.keys()]:
                        analysis["recommended_channels"].append({
                            "channel": channel,
                            "target_segment": segment["name"],
                            "rationale": f"适合{segment['name']}的未充分利用渠道"
                        })

        return analysis

    async def _generate_marketing_recommendations(
        self,
        marketing_insights: Dict[str, Any],
        brand_analysis: Dict[str, Any],
        audience_analysis: Dict[str, Any],
        channel_analysis: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[MarketingRecommendation]:
        """
        Generate marketing recommendations based on analysis.

        Args:
            marketing_insights: Marketing insights
            brand_analysis: Brand perception analysis
            audience_analysis: Audience segment analysis
            channel_analysis: Channel effectiveness analysis
            state: Current workflow state

        Returns:
            List of marketing recommendations
        """
        recommendations = []

        # Brand positioning recommendations
        if brand_analysis["overall_sentiment"] in ["negative", "mixed"]:
            rec = MarketingRecommendation(
                recommendation_id=f"brand_{len(recommendations)}",
                title="品牌形象重塑营销策略",
                description="基于客户反馈优化品牌定位和传播策略",
                category="brand_positioning",
                priority="immediate",
                target_audience=["所有客户群体"],
                channels=["社交媒体", "品牌官网", "传统媒体"],
                budget_range="中高预算",
                expected_outcomes=["品牌认知度提升", "客户满意度改善"],
                kpi_metrics=["品牌提及率", "正面情绪比例", "NPS改善"]
            )
            recommendations.append(rec)

        # Channel optimization recommendations
        for opp in channel_analysis["optimization_opportunities"]:
            if opp["priority"] == "high":
                rec = MarketingRecommendation(
                    recommendation_id=f"channel_{len(recommendations)}",
                    title=f"{opp['channel']}渠道优化",
                    description=f"优化{opp['channel']}渠道的{opp['opportunity']}",
                    category="channel_optimization",
                    priority="short_term",
                    target_audience=["活跃用户"],
                    channels=[opp["channel"]],
                    budget_range="中等预算",
                    expected_outcomes=["渠道效率提升", "用户体验改善"],
                    kpi_metrics=["转化率", "用户满意度", "渠道ROI"]
                )
                recommendations.append(rec)

        # Audience segment targeting recommendations
        for segment in audience_analysis["underserved_segments"]:
            rec = MarketingRecommendation(
                recommendation_id=f"segment_{len(recommendations)}",
                title=f"{segment['name']}细分营销",
                description=f"针对{segment['name']}制定专属营销方案",
                category="customer_engagement",
                priority="medium_term",
                target_audience=[segment["name"]],
                channels=["精准数字广告", "个性化内容"],
                budget_range="中等预算",
                expected_outcomes=["细分市场渗透", "客户转化提升"],
                kpi_metrics=["细分市场份额", "转化率", "客户获取成本"]
            )
            recommendations.append(rec)

        # Competitive response recommendations
        if len(marketing_insights["competitive_references"]) >= 3:
            negative_competitive = [ref for ref in marketing_insights["competitive_references"]
                                  if ref["sentiment"] == "negative"]
            if len(negative_competitive) >= 2:
                rec = MarketingRecommendation(
                    recommendation_id=f"competitive_{len(recommendations)}",
                    title="竞争差异化营销策略",
                    description="基于竞争对比反馈制定差异化传播策略",
                    category="brand_positioning",
                    priority="short_term",
                    target_audience=["比价敏感客户"],
                    channels=["比较内容营销", "KOL推荐"],
                    budget_range="中等预算",
                    expected_outcomes=["竞争优势突出", "品牌差异化"],
                    kpi_metrics=["品牌选择率", "竞争提及率", "价值认知度"]
                )
                recommendations.append(rec)

        # LLM-enhanced recommendations
        if self.llm_client:
            llm_recs = await self._llm_generate_marketing_recommendations(
                marketing_insights, brand_analysis, audience_analysis, state
            )
            recommendations.extend(llm_recs)

        return recommendations

    async def _llm_generate_marketing_recommendations(
        self,
        marketing_insights: Dict[str, Any],
        brand_analysis: Dict[str, Any],
        audience_analysis: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[MarketingRecommendation]:
        """
        Use LLM to generate marketing recommendations.

        Args:
            marketing_insights: Marketing insights
            brand_analysis: Brand analysis
            audience_analysis: Audience analysis
            state: Current workflow state

        Returns:
            LLM-generated marketing recommendations
        """
        if not self.llm_client:
            return []

        try:
            nps_score = state.get("nps_metrics", {}).get("nps_score", 0)
            brand_sentiment = brand_analysis.get("overall_sentiment", "neutral")

            # Extract key themes
            key_themes = [theme["theme"] for theme in marketing_insights.get("messaging_themes", [])[:3]]
            brand_strengths = [s["theme"] for s in brand_analysis.get("brand_strengths", [])]
            brand_weaknesses = [w["issue"] for w in brand_analysis.get("brand_weaknesses", [])]

            prompt = f"""
作为伊利集团的营销顾问，基于以下客户洞察提供营销策略建议：

NPS得分：{nps_score:.1f}
品牌情绪：{brand_sentiment}

关键主题：
{chr(10).join([f"• {theme}" for theme in key_themes])}

品牌优势：
{chr(10).join([f"• {strength}" for strength in brand_strengths])}

品牌弱点：
{chr(10).join([f"• {weakness}" for weakness in brand_weaknesses])}

请提供3-4个营销策略建议，每个建议包括：
1. 策略标题
2. 具体描述
3. 营销类别（brand_positioning/messaging/channel_optimization/customer_engagement/digital_marketing）
4. 目标受众
5. 推荐渠道
6. 优先级（immediate/short_term/medium_term）
7. 预期成果
8. 关键指标

以JSON格式返回：
[
    {{
        "title": "营销策略标题",
        "description": "详细描述",
        "category": "营销类别",
        "target_audience": ["目标受众1", "目标受众2"],
        "channels": ["渠道1", "渠道2"],
        "priority": "优先级",
        "expected_outcomes": ["预期成果1", "预期成果2"],
        "kpi_metrics": ["指标1", "指标2"]
    }}
]
"""

            response = await self.llm_client.generate(prompt, temperature=0.3)

            # Parse JSON response
            import json
            recommendations_data = json.loads(response)

            recommendations = []
            for idx, rec_data in enumerate(recommendations_data):
                rec = MarketingRecommendation(
                    recommendation_id=f"llm_marketing_{idx}",
                    title=rec_data.get("title", ""),
                    description=rec_data.get("description", ""),
                    category=rec_data.get("category", "messaging"),
                    priority=rec_data.get("priority", "medium_term"),
                    target_audience=rec_data.get("target_audience", []),
                    channels=rec_data.get("channels", []),
                    budget_range="中等预算",
                    expected_outcomes=rec_data.get("expected_outcomes", []),
                    kpi_metrics=rec_data.get("kpi_metrics", [])
                )
                recommendations.append(rec)

            return recommendations

        except Exception as e:
            logger.debug(f"LLM marketing recommendation generation failed: {e}")
            return []

    def _prioritize_marketing_recommendations(
        self,
        recommendations: List[MarketingRecommendation]
    ) -> List[MarketingRecommendation]:
        """
        Prioritize marketing recommendations.

        Args:
            recommendations: List of marketing recommendations

        Returns:
            Prioritized recommendations
        """
        # Priority weights
        priority_order = {
            "immediate": 0,
            "short_term": 1,
            "medium_term": 2,
            "long_term": 3
        }

        # Category importance weights
        category_weights = {
            "brand_positioning": 0,      # Highest priority
            "channel_optimization": 1,
            "customer_engagement": 2,
            "messaging": 3,
            "digital_marketing": 4
        }

        def sort_key(rec):
            priority_score = priority_order.get(rec.get("priority", "medium_term"), 2)
            category_score = category_weights.get(rec.get("category", "messaging"), 3) * 0.1
            return priority_score + category_score

        recommendations.sort(key=sort_key)
        return recommendations

    def _create_marketing_action_plan(
        self,
        recommendations: List[MarketingRecommendation]
    ) -> Dict[str, Any]:
        """
        Create marketing action plan with timeline and resource allocation.

        Args:
            recommendations: Prioritized marketing recommendations

        Returns:
            Marketing action plan
        """
        action_plan = {
            "immediate_actions": [],
            "short_term_initiatives": [],
            "medium_term_campaigns": [],
            "long_term_strategies": [],
            "resource_requirements": {},
            "timeline_overview": {}
        }

        # Organize by priority
        for rec in recommendations:
            priority = rec.get("priority", "medium_term")
            action_item = {
                "title": rec["title"],
                "description": rec["description"],
                "channels": rec.get("channels", []),
                "target_audience": rec.get("target_audience", []),
                "expected_outcomes": rec.get("expected_outcomes", []),
                "kpi_metrics": rec.get("kpi_metrics", []),
                "budget_range": rec.get("budget_range", "中等预算")
            }

            if priority == "immediate":
                action_plan["immediate_actions"].append(action_item)
            elif priority == "short_term":
                action_plan["short_term_initiatives"].append(action_item)
            elif priority == "medium_term":
                action_plan["medium_term_campaigns"].append(action_item)
            else:
                action_plan["long_term_strategies"].append(action_item)

        # Aggregate resource requirements
        budget_categories = Counter(rec.get("budget_range", "中等预算") for rec in recommendations)
        action_plan["resource_requirements"] = {
            "budget_distribution": dict(budget_categories),
            "total_initiatives": len(recommendations),
            "high_priority_count": len([r for r in recommendations if r.get("priority") == "immediate"])
        }

        # Create timeline overview
        action_plan["timeline_overview"] = {
            "month_1_3": f"{len(action_plan['immediate_actions'])}项紧急营销行动",
            "month_4_6": f"{len(action_plan['short_term_initiatives'])}项短期营销计划",
            "month_7_12": f"{len(action_plan['medium_term_campaigns'])}项中期营销活动",
            "year_2_plus": f"{len(action_plan['long_term_strategies'])}项长期营销战略"
        }

        return action_plan

    def _generate_competitive_marketing_insights(
        self,
        brand_analysis: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[str]:
        """
        Generate competitive marketing insights.

        Args:
            brand_analysis: Brand perception analysis
            state: Current workflow state

        Returns:
            List of competitive marketing insights
        """
        insights = []

        # Competitive positioning insights
        nps_score = state.get("nps_metrics", {}).get("nps_score", 0)
        brand_sentiment = brand_analysis.get("overall_sentiment", "neutral")

        if nps_score >= 50:
            insights.append("伊利在客户忠诚度方面具有明显竞争优势，可重点强化推荐营销")
        elif nps_score >= 30:
            insights.append("品牌具有良好基础，建议加强与竞品的差异化传播")
        elif nps_score < 10:
            insights.append("需要紧急启动品牌修复营销，重建客户信任")

        # Brand strength vs weakness balance
        strengths_count = len(brand_analysis.get("brand_strengths", []))
        weaknesses_count = len(brand_analysis.get("brand_weaknesses", []))

        if strengths_count > weaknesses_count * 2:
            insights.append("品牌优势明显，建议采用攻势营销策略扩大市场份额")
        elif weaknesses_count > strengths_count:
            insights.append("品牌存在多项弱点，建议优先修复核心问题再进行扩张营销")

        # Market opportunity insights
        if brand_sentiment == "positive":
            insights.append("正面品牌情绪为口碑营销和推荐计划提供良好基础")
        elif brand_sentiment == "mixed":
            insights.append("品牌情绪分化，建议细分市场定制化营销策略")

        # Competitive threat assessment
        perception_gaps = brand_analysis.get("perception_gaps", [])
        if len(perception_gaps) >= 2:
            insights.append("品牌认知存在多项空隙，竞争对手可能利用这些弱点，需要防御性营销")

        return insights
