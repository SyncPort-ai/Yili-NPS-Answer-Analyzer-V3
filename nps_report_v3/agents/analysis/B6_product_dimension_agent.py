"""
B6 - Product Dimension Agent
Analysis Pass Agent for product-specific insights and competitive analysis.
"""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter

from ..base import AnalysisAgent, AgentResult, AgentStatus
from ...llm import LLMClient

logger = logging.getLogger(__name__)


class ProductDimensionAgent(AnalysisAgent):
    """
    B6 - Product Dimension Agent

    Responsibilities:
    - Analyze product-specific insights and performance comparisons
    - Implement competitive benchmarking against other dairy brands
    - Create product portfolio analysis and cross-selling opportunities
    - Generate product-specific recommendations and positioning insights
    """

    def __init__(self, agent_id: str = "B6", agent_name: str = "Product Dimension Agent",
                 llm_client: Optional[LLMClient] = None, **kwargs):
        super().__init__(agent_id, agent_name, **kwargs)
        self.llm_client = llm_client

        # Yili product portfolio
        self.yili_products = {
            "安慕希": {
                "category": "premium_yogurt",
                "type": "希腊酸奶",
                "price_tier": "premium",
                "target_audience": "高端消费者",
                "key_features": ["蛋白质含量高", "口感浓郁", "品质优良"],
                "competitors": ["蒙牛纯甄", "光明莫斯利安", "达能碧悠"]
            },
            "金典": {
                "category": "premium_milk",
                "type": "有机纯牛奶",
                "price_tier": "premium",
                "target_audience": "品质消费者",
                "key_features": ["有机认证", "营养丰富", "天然纯净"],
                "competitors": ["蒙牛特仑苏", "光明优倍", "现代牧业"]
            },
            "舒化": {
                "category": "functional_milk",
                "type": "无乳糖牛奶",
                "price_tier": "mid-premium",
                "target_audience": "乳糖不耐人群",
                "key_features": ["无乳糖", "易消化", "营养不减"],
                "competitors": ["蒙牛新养道", "光明优加"]
            },
            "优酸乳": {
                "category": "flavored_yogurt",
                "type": "风味酸奶",
                "price_tier": "mainstream",
                "target_audience": "大众消费者",
                "key_features": ["口味多样", "价格实惠", "营养均衡"],
                "competitors": ["蒙牛酸酸乳", "光明健能"]
            },
            "味可滋": {
                "category": "milk_drink",
                "type": "乳饮料",
                "price_tier": "economy",
                "target_audience": "学生群体",
                "key_features": ["口感好", "便携装", "价格便宜"],
                "competitors": ["蒙牛未来星", "光明小小光明"]
            },
            "QQ星": {
                "category": "kids_milk",
                "type": "儿童奶",
                "price_tier": "mid-premium",
                "target_audience": "儿童家庭",
                "key_features": ["营养均衡", "DHA添加", "钙含量高"],
                "competitors": ["蒙牛未来星", "光明优倍儿童"]
            }
        }

        # Competitive brands
        self.competitor_brands = {
            "蒙牛": {"market_position": "主要竞争对手", "strength": "渠道广泛", "weakness": "品质形象"},
            "光明": {"market_position": "区域强势", "strength": "历史悠久", "weakness": "创新不足"},
            "君乐宝": {"market_position": "性价比", "strength": "价格优势", "weakness": "品牌力弱"},
            "三元": {"market_position": "北方市场", "strength": "本土化", "weakness": "规模有限"},
            "达能": {"market_position": "国际品牌", "strength": "技术先进", "weakness": "价格较高"},
            "雀巢": {"market_position": "全球品牌", "strength": "品牌知名度", "weakness": "本土化不够"}
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Process product dimension analysis.

        Args:
            state: Current workflow state

        Returns:
            AgentResult with product insights and competitive analysis
        """
        try:
            # Get data from state
            tagged_responses = state.get("tagged_responses", [])
            nps_results = state.get("nps_results", {})

            if not tagged_responses:
                logger.warning("No responses available for product dimension analysis")
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.COMPLETED,
                    data={
                        "product_dimension": {
                            "total_responses": 0,
                            "product_performance": {},
                            "competitive_analysis": {},
                            "cross_selling_opportunities": [],
                            "product_recommendations": []
                        }
                    },
                    insights=["No responses available for product dimension analysis"],
                    confidence_score=1.0
                )

            # Analyze product-specific performance
            product_performance = self._analyze_product_performance(tagged_responses, nps_results)

            # Perform competitive analysis
            competitive_analysis = await self._perform_competitive_analysis(tagged_responses)

            # Identify cross-selling opportunities
            cross_selling_opportunities = self._identify_cross_selling_opportunities(tagged_responses, product_performance)

            # Analyze product portfolio
            portfolio_analysis = self._analyze_product_portfolio(product_performance, competitive_analysis)

            # Generate product-specific recommendations
            recommendations = await self._generate_product_recommendations(
                product_performance, competitive_analysis, portfolio_analysis
            )

            # Generate product insights
            insights = self._generate_product_insights(
                product_performance, competitive_analysis, cross_selling_opportunities
            )

            logger.info(f"Analyzed {len(tagged_responses)} responses across {len(product_performance)} products")

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "product_dimension": {
                        "total_responses": len(tagged_responses),
                        "product_performance": product_performance,
                        "competitive_analysis": competitive_analysis,
                        "portfolio_analysis": portfolio_analysis,
                        "cross_selling_opportunities": cross_selling_opportunities,
                        "product_recommendations": recommendations,
                        "product_insights": insights
                    }
                },
                insights=insights,
                confidence_score=0.8
            )

        except Exception as e:
            logger.error(f"Product dimension analysis failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                data={},
                errors=[str(e)],
                confidence_score=0.0
            )

    def _analyze_product_performance(
        self,
        tagged_responses: List[Dict[str, Any]],
        nps_results: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze performance of individual products.

        Args:
            tagged_responses: Tagged responses
            nps_results: NPS calculation results

        Returns:
            Product performance analysis
        """
        product_performance = {}

        # Initialize product metrics
        for product_name, product_info in self.yili_products.items():
            product_performance[product_name] = {
                "product_info": product_info,
                "mentions": [],
                "nps_scores": [],
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "key_themes": [],
                "performance_metrics": {}
            }

        # Analyze responses for product mentions
        for response in tagged_responses:
            text = response.get("original_text", "")
            nps_score = response.get("nps_score")
            response_id = response.get("response_id", "")

            # Identify product mentions
            mentioned_products = []
            for product_name in self.yili_products.keys():
                if product_name in text:
                    mentioned_products.append(product_name)

            # If no specific product mentioned, try to infer from context
            if not mentioned_products:
                inferred_product = self._infer_product_from_context(text)
                if inferred_product:
                    mentioned_products.append(inferred_product)

            # Record mentions and analyze sentiment
            for product_name in mentioned_products:
                if product_name in product_performance:
                    product_performance[product_name]["mentions"].append({
                        "response_id": response_id,
                        "text": text,
                        "nps_score": nps_score
                    })

                    if nps_score is not None:
                        product_performance[product_name]["nps_scores"].append(nps_score)

                    # Analyze sentiment
                    sentiment = self._analyze_product_sentiment(text, product_name)
                    product_performance[product_name]["sentiment_distribution"][sentiment] += 1

                    # Extract themes
                    themes = self._extract_product_themes(text, product_name)
                    product_performance[product_name]["key_themes"].extend(themes)

        # Calculate performance metrics
        for product_name, data in product_performance.items():
            metrics = self._calculate_product_metrics(data)
            product_performance[product_name]["performance_metrics"] = metrics

        # Filter products with sufficient data
        filtered_performance = {
            name: data for name, data in product_performance.items()
            if len(data["mentions"]) >= 3  # Minimum mentions for analysis
        }

        return filtered_performance

    def _infer_product_from_context(self, text: str) -> Optional[str]:
        """Infer product from context clues."""
        # Look for category indicators
        if any(keyword in text for keyword in ["酸奶", "希腊", "蛋白质"]):
            return "安慕希"
        elif any(keyword in text for keyword in ["有机", "纯牛奶", "品质"]):
            return "金典"
        elif any(keyword in text for keyword in ["乳糖", "消化", "肠胃"]):
            return "舒化"
        elif any(keyword in text for keyword in ["儿童", "小孩", "DHA", "钙"]):
            return "QQ星"
        elif any(keyword in text for keyword in ["便宜", "实惠", "学生"]):
            return "优酸乳"

        return None

    def _analyze_product_sentiment(self, text: str, product_name: str) -> str:
        """Analyze sentiment towards specific product."""
        # Product-specific sentiment analysis
        positive_indicators = ["好喝", "喜欢", "不错", "推荐", "满意", "棒", "优秀"]
        negative_indicators = ["难喝", "不好", "失望", "差", "贵", "不值", "糟糕"]

        # Check context around product mention
        product_pos = text.find(product_name)
        if product_pos != -1:
            # Get context window
            start = max(0, product_pos - 20)
            end = min(len(text), product_pos + len(product_name) + 20)
            context = text[start:end]

            positive_count = sum(1 for indicator in positive_indicators if indicator in context)
            negative_count = sum(1 for indicator in negative_indicators if indicator in context)

            if positive_count > negative_count:
                return "positive"
            elif negative_count > positive_count:
                return "negative"

        return "neutral"

    def _extract_product_themes(self, text: str, product_name: str) -> List[str]:
        """Extract themes related to specific product."""
        themes = []
        product_info = self.yili_products.get(product_name, {})

        # Check for mentions of key features
        for feature in product_info.get("key_features", []):
            if any(keyword in text for keyword in feature.split()):
                themes.append(feature)

        # Check for category-specific themes
        category = product_info.get("category", "")
        if category == "premium_yogurt" and any(word in text for word in ["蛋白质", "营养", "健康"]):
            themes.append("营养价值")
        elif category == "premium_milk" and any(word in text for word in ["有机", "天然", "品质"]):
            themes.append("品质优势")
        elif category == "functional_milk" and any(word in text for word in ["消化", "肠胃", "舒适"]):
            themes.append("功能性")

        return themes

    def _calculate_product_metrics(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics for a product."""
        mentions = product_data["mentions"]
        nps_scores = product_data["nps_scores"]
        sentiment_dist = product_data["sentiment_distribution"]

        if not mentions:
            return {}

        metrics = {
            "mention_count": len(mentions),
            "avg_nps": sum(nps_scores) / len(nps_scores) if nps_scores else 0,
            "nps_distribution": self._calculate_nps_distribution(nps_scores),
            "sentiment_score": self._calculate_sentiment_score(sentiment_dist),
            "engagement_level": self._assess_engagement_level(mentions),
            "theme_frequency": Counter(product_data["key_themes"])
        }

        return metrics

    def _calculate_nps_distribution(self, nps_scores: List[int]) -> Dict[str, float]:
        """Calculate NPS distribution for product."""
        if not nps_scores:
            return {"promoters": 0, "passives": 0, "detractors": 0}

        total = len(nps_scores)
        promoters = len([s for s in nps_scores if s >= 9])
        passives = len([s for s in nps_scores if 7 <= s <= 8])
        detractors = len([s for s in nps_scores if s <= 6])

        return {
            "promoters": round(promoters / total, 3),
            "passives": round(passives / total, 3),
            "detractors": round(detractors / total, 3)
        }

    def _calculate_sentiment_score(self, sentiment_dist: Dict[str, int]) -> float:
        """Calculate overall sentiment score."""
        total = sum(sentiment_dist.values())
        if total == 0:
            return 0.0

        score = (sentiment_dist["positive"] - sentiment_dist["negative"]) / total
        return round(score, 3)

    def _assess_engagement_level(self, mentions: List[Dict[str, Any]]) -> str:
        """Assess engagement level based on mention characteristics."""
        if not mentions:
            return "low"

        # Check for detailed comments (longer text)
        detailed_mentions = [m for m in mentions if len(m.get("text", "")) > 50]
        detail_ratio = len(detailed_mentions) / len(mentions)

        if detail_ratio > 0.7:
            return "high"
        elif detail_ratio > 0.4:
            return "medium"
        else:
            return "low"

    async def _perform_competitive_analysis(self, tagged_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Perform competitive analysis against other brands.

        Args:
            tagged_responses: Tagged responses

        Returns:
            Competitive analysis results
        """
        competitive_analysis = {
            "competitor_mentions": {},
            "brand_comparisons": [],
            "competitive_position": {},
            "market_insights": []
        }

        # Analyze competitor mentions
        for response in tagged_responses:
            text = response.get("original_text", "")

            for competitor, info in self.competitor_brands.items():
                if competitor in text:
                    if competitor not in competitive_analysis["competitor_mentions"]:
                        competitive_analysis["competitor_mentions"][competitor] = {
                            "mentions": [],
                            "context_analysis": {"positive": 0, "negative": 0, "neutral": 0}
                        }

                    # Analyze context of competitor mention
                    context_sentiment = self._analyze_competitor_context(text, competitor)
                    competitive_analysis["competitor_mentions"][competitor]["mentions"].append({
                        "text": text,
                        "context_sentiment": context_sentiment
                    })
                    competitive_analysis["competitor_mentions"][competitor]["context_analysis"][context_sentiment] += 1

        # Identify direct comparisons
        brand_comparisons = self._identify_brand_comparisons(tagged_responses)
        competitive_analysis["brand_comparisons"] = brand_comparisons

        # Assess competitive position
        competitive_position = self._assess_competitive_position(
            competitive_analysis["competitor_mentions"], brand_comparisons
        )
        competitive_analysis["competitive_position"] = competitive_position

        # Enhanced competitive analysis with LLM
        if self.llm_client and competitive_analysis["competitor_mentions"]:
            llm_insights = await self._llm_competitive_analysis(tagged_responses)
            competitive_analysis["llm_insights"] = llm_insights

        return competitive_analysis

    def _analyze_competitor_context(self, text: str, competitor: str) -> str:
        """Analyze context sentiment when competitor is mentioned."""
        # Find competitor position in text
        pos = text.find(competitor)
        if pos == -1:
            return "neutral"

        # Get surrounding context
        start = max(0, pos - 30)
        end = min(len(text), pos + len(competitor) + 30)
        context = text[start:end]

        # Analyze sentiment in context
        positive_indicators = ["比", "不如", "更好", "超过", "优于"]
        negative_indicators = ["像", "换", "改买", "转向", "选择"]

        # Check if comparing favorably to competitor
        if any(indicator in context for indicator in positive_indicators):
            # Check if Yili is mentioned positively relative to competitor
            if any(product in context for product in self.yili_products.keys()):
                return "positive"  # Yili compared favorably

        # Check if switching to competitor
        if any(indicator in context for indicator in negative_indicators):
            return "negative"

        return "neutral"

    def _identify_brand_comparisons(self, tagged_responses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Identify direct brand comparisons in responses."""
        comparisons = []

        for response in tagged_responses:
            text = response.get("original_text", "")

            # Look for comparison patterns
            comparison_keywords = ["比", "和", "对比", "相比", "不如", "更", "超过"]
            has_comparison = any(keyword in text for keyword in comparison_keywords)

            if has_comparison:
                # Check if both Yili products and competitors are mentioned
                yili_products_mentioned = [p for p in self.yili_products.keys() if p in text]
                competitors_mentioned = [c for c in self.competitor_brands.keys() if c in text]

                if yili_products_mentioned and competitors_mentioned:
                    comparison = {
                        "response_id": response.get("response_id", ""),
                        "text": text,
                        "yili_products": yili_products_mentioned,
                        "competitors": competitors_mentioned,
                        "comparison_aspect": self._extract_comparison_aspect(text),
                        "sentiment": self._analyze_comparison_sentiment(text, yili_products_mentioned, competitors_mentioned)
                    }
                    comparisons.append(comparison)

        return comparisons

    def _extract_comparison_aspect(self, text: str) -> str:
        """Extract what aspect is being compared."""
        aspects = {
            "price": ["价格", "便宜", "贵", "实惠", "性价比"],
            "taste": ["口感", "味道", "好喝", "香", "甜"],
            "quality": ["质量", "品质", "新鲜", "纯"],
            "nutrition": ["营养", "蛋白质", "钙", "维生素"],
            "packaging": ["包装", "设计", "便携", "美观"],
            "brand": ["品牌", "知名", "信任", "口碑"]
        }

        for aspect, keywords in aspects.items():
            if any(keyword in text for keyword in keywords):
                return aspect

        return "general"

    def _analyze_comparison_sentiment(
        self,
        text: str,
        yili_products: List[str],
        competitors: List[str]
    ) -> str:
        """Analyze sentiment of comparison towards Yili."""
        # Look for patterns indicating preference
        yili_positive_patterns = ["比.*好", "更.*", "超过", "优于", "不如.*" + "|".join(yili_products)]
        yili_negative_patterns = ["不如", "没有.*好", "差于", ".*比.*好"]

        # Check for positive indicators for Yili
        for pattern in yili_positive_patterns:
            import re
            if re.search(pattern, text):
                return "positive"

        # Check for negative indicators for Yili
        for pattern in yili_negative_patterns:
            import re
            if re.search(pattern, text):
                # Make sure it's not about competitors being worse than Yili
                if not any(comp in text[text.find(pattern):] for comp in competitors):
                    return "negative"

        return "neutral"

    def _assess_competitive_position(
        self,
        competitor_mentions: Dict[str, Any],
        brand_comparisons: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Assess Yili's competitive position."""
        position = {
            "market_perception": "neutral",
            "key_advantages": [],
            "competitive_threats": [],
            "market_share_indicators": {}
        }

        # Analyze comparison sentiment distribution
        if brand_comparisons:
            positive_comparisons = [c for c in brand_comparisons if c["sentiment"] == "positive"]
            negative_comparisons = [c for c in brand_comparisons if c["sentiment"] == "negative"]

            total_comparisons = len(brand_comparisons)
            positive_ratio = len(positive_comparisons) / total_comparisons

            if positive_ratio > 0.6:
                position["market_perception"] = "favorable"
            elif positive_ratio < 0.4:
                position["market_perception"] = "challenging"

        # Identify key advantages
        aspect_performance = defaultdict(lambda: {"positive": 0, "negative": 0})
        for comparison in brand_comparisons:
            aspect = comparison["comparison_aspect"]
            sentiment = comparison["sentiment"]
            aspect_performance[aspect][sentiment] += 1

        for aspect, sentiments in aspect_performance.items():
            if sentiments["positive"] > sentiments["negative"]:
                position["key_advantages"].append(aspect)
            elif sentiments["negative"] > sentiments["positive"]:
                position["competitive_threats"].append(aspect)

        return position

    def _identify_cross_selling_opportunities(
        self,
        tagged_responses: List[Dict[str, Any]],
        product_performance: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify cross-selling opportunities between products."""
        opportunities = []

        # Analyze product affinity patterns
        product_cooccurrence = defaultdict(int)
        customer_product_preferences = defaultdict(set)

        # Track which products customers mention together
        for response in tagged_responses:
            text = response.get("original_text", "")
            customer_id = response.get("response_id", "")  # Using response_id as customer proxy

            mentioned_products = [p for p in self.yili_products.keys() if p in text]
            customer_product_preferences[customer_id].update(mentioned_products)

            # Count co-occurrences
            for i, product1 in enumerate(mentioned_products):
                for product2 in mentioned_products[i+1:]:
                    pair = tuple(sorted([product1, product2]))
                    product_cooccurrence[pair] += 1

        # Identify high-affinity product pairs
        for (product1, product2), count in product_cooccurrence.items():
            if count >= 3:  # Minimum co-occurrence threshold
                # Calculate cross-selling potential
                product1_performance = product_performance.get(product1, {}).get("performance_metrics", {})
                product2_performance = product_performance.get(product2, {}).get("performance_metrics", {})

                if product1_performance and product2_performance:
                    opportunity = {
                        "primary_product": product1,
                        "cross_sell_product": product2,
                        "affinity_score": count,
                        "opportunity_type": self._determine_cross_sell_type(product1, product2),
                        "target_audience": self._identify_cross_sell_audience(product1, product2),
                        "expected_lift": self._estimate_cross_sell_lift(product1_performance, product2_performance)
                    }
                    opportunities.append(opportunity)

        # Sort by potential
        opportunities.sort(key=lambda x: x["expected_lift"], reverse=True)

        return opportunities[:10]  # Top 10 opportunities

    def _determine_cross_sell_type(self, product1: str, product2: str) -> str:
        """Determine type of cross-selling opportunity."""
        info1 = self.yili_products.get(product1, {})
        info2 = self.yili_products.get(product2, {})

        category1 = info1.get("category", "")
        category2 = info2.get("category", "")

        if "premium" in category1 and "premium" in category2:
            return "premium_bundle"
        elif "kids" in category1 or "kids" in category2:
            return "family_expansion"
        elif category1 != category2:
            return "category_expansion"
        else:
            return "within_category"

    def _identify_cross_sell_audience(self, product1: str, product2: str) -> str:
        """Identify target audience for cross-selling."""
        info1 = self.yili_products.get(product1, {})
        info2 = self.yili_products.get(product2, {})

        audience1 = info1.get("target_audience", "")
        audience2 = info2.get("target_audience", "")

        # Find common audience characteristics
        if "家庭" in audience1 or "家庭" in audience2:
            return "家庭用户"
        elif "高端" in audience1 or "高端" in audience2:
            return "高端消费者"
        elif "儿童" in audience1 or "儿童" in audience2:
            return "有孩家庭"
        else:
            return "普通消费者"

    def _estimate_cross_sell_lift(
        self,
        product1_metrics: Dict[str, Any],
        product2_metrics: Dict[str, Any]
    ) -> float:
        """Estimate cross-selling lift potential."""
        # Base calculation on NPS and sentiment scores
        nps1 = product1_metrics.get("avg_nps", 5)
        nps2 = product2_metrics.get("avg_nps", 5)
        sentiment1 = product1_metrics.get("sentiment_score", 0)
        sentiment2 = product2_metrics.get("sentiment_score", 0)

        # Higher performing products have better cross-sell potential
        combined_performance = (nps1 + nps2) / 20 + (sentiment1 + sentiment2) / 2
        lift_potential = min(combined_performance * 0.3, 0.8)  # Cap at 80%

        return round(lift_potential, 3)

    def _analyze_product_portfolio(
        self,
        product_performance: Dict[str, Dict[str, Any]],
        competitive_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Analyze overall product portfolio performance."""
        portfolio_analysis = {
            "portfolio_health": {},
            "category_performance": {},
            "strategic_gaps": [],
            "portfolio_optimization": {}
        }

        # Assess portfolio health
        performing_products = []
        underperforming_products = []

        for product, data in product_performance.items():
            metrics = data.get("performance_metrics", {})
            avg_nps = metrics.get("avg_nps", 0)
            sentiment_score = metrics.get("sentiment_score", 0)

            performance_score = (avg_nps / 10 + sentiment_score + 1) / 2  # Normalize to 0-1

            if performance_score > 0.7:
                performing_products.append(product)
            elif performance_score < 0.4:
                underperforming_products.append(product)

        portfolio_analysis["portfolio_health"] = {
            "performing_products": performing_products,
            "underperforming_products": underperforming_products,
            "portfolio_balance": len(performing_products) / len(product_performance) if product_performance else 0
        }

        # Category performance analysis
        category_performance = defaultdict(list)
        for product, data in product_performance.items():
            category = data["product_info"].get("category", "unknown")
            metrics = data.get("performance_metrics", {})
            category_performance[category].append({
                "product": product,
                "nps": metrics.get("avg_nps", 0),
                "sentiment": metrics.get("sentiment_score", 0)
            })

        portfolio_analysis["category_performance"] = dict(category_performance)

        return portfolio_analysis

    async def _generate_product_recommendations(
        self,
        product_performance: Dict[str, Dict[str, Any]],
        competitive_analysis: Dict[str, Any],
        portfolio_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate product-specific recommendations."""
        recommendations = []

        # Recommendations for underperforming products
        underperforming = portfolio_analysis.get("portfolio_health", {}).get("underperforming_products", [])

        for product in underperforming:
            performance_data = product_performance.get(product, {})
            metrics = performance_data.get("performance_metrics", {})

            rec = {
                "recommendation_id": f"product_improve_{product}",
                "product": product,
                "priority": "high",
                "type": "product_improvement",
                "title": f"改进{product}产品表现",
                "description": f"{product}的NPS和满意度表现不佳，需要重点改进",
                "current_nps": metrics.get("avg_nps", 0),
                "improvement_areas": self._identify_improvement_areas(performance_data),
                "suggested_actions": self._suggest_product_actions(product, performance_data),
                "expected_impact": "medium"
            }
            recommendations.append(rec)

        # Recommendations for leveraging top performers
        performing = portfolio_analysis.get("portfolio_health", {}).get("performing_products", [])

        for product in performing[:2]:  # Top 2 performers
            rec = {
                "recommendation_id": f"leverage_{product}",
                "product": product,
                "priority": "medium",
                "type": "leverage_success",
                "title": f"利用{product}成功经验",
                "description": f"{product}表现优秀，可将成功因素应用到其他产品",
                "success_factors": self._identify_success_factors(product_performance[product]),
                "expansion_opportunities": self._identify_expansion_opportunities(product),
                "expected_impact": "high"
            }
            recommendations.append(rec)

        # Enhanced recommendations with LLM
        if self.llm_client and recommendations:
            enhanced_recs = await self._enhance_product_recommendations(recommendations, competitive_analysis)
            if enhanced_recs:
                recommendations.extend(enhanced_recs)

        return recommendations[:10]  # Top 10 recommendations

    def _identify_improvement_areas(self, performance_data: Dict[str, Any]) -> List[str]:
        """Identify specific areas for product improvement."""
        areas = []
        themes = performance_data.get("key_themes", [])
        sentiment_dist = performance_data.get("sentiment_distribution", {})

        # If more negative sentiment, focus on quality issues
        if sentiment_dist.get("negative", 0) > sentiment_dist.get("positive", 0):
            areas.append("质量问题解决")

        # Based on common themes
        theme_counts = Counter(themes)
        for theme, count in theme_counts.most_common(3):
            if "问题" in theme or "差" in theme:
                areas.append(f"{theme}改进")

        return areas or ["整体用户体验提升"]

    def _suggest_product_actions(self, product: str, performance_data: Dict[str, Any]) -> List[str]:
        """Suggest specific actions for product improvement."""
        product_info = self.yili_products.get(product, {})
        category = product_info.get("category", "")

        actions = []
        if category == "premium_yogurt":
            actions = ["口味调研", "营养成分优化", "包装升级"]
        elif category == "premium_milk":
            actions = ["品质保证加强", "有机认证宣传", "价值传播"]
        elif category == "functional_milk":
            actions = ["功能性验证", "健康效果沟通", "目标人群扩展"]
        else:
            actions = ["消费者调研", "产品配方优化", "市场定位调整"]

        return actions

    def _identify_success_factors(self, product_data: Dict[str, Any]) -> List[str]:
        """Identify success factors for top-performing products."""
        factors = []
        themes = product_data.get("key_themes", [])
        metrics = product_data.get("performance_metrics", {})

        # High-frequency positive themes are success factors
        theme_counts = Counter(themes)
        for theme, count in theme_counts.most_common(3):
            if count >= 2:  # Mentioned multiple times
                factors.append(theme)

        # Add general success factors based on performance
        if metrics.get("sentiment_score", 0) > 0.5:
            factors.append("优秀的用户体验")

        if metrics.get("avg_nps", 0) > 8:
            factors.append("高客户满意度")

        return factors or ["品质优势", "品牌信任"]

    def _identify_expansion_opportunities(self, product: str) -> List[str]:
        """Identify expansion opportunities for successful products."""
        product_info = self.yili_products.get(product, {})
        opportunities = []

        # Based on product category
        category = product_info.get("category", "")
        if "premium" in category:
            opportunities = ["高端市场扩展", "新口味开发", "礼品市场"]
        elif "kids" in category:
            opportunities = ["年龄层扩展", "营养强化版本", "教育合作"]
        else:
            opportunities = ["地域扩展", "包装规格多样化", "场景应用拓展"]

        return opportunities

    def _generate_product_insights(
        self,
        product_performance: Dict[str, Dict[str, Any]],
        competitive_analysis: Dict[str, Any],
        cross_selling_opportunities: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate actionable product insights."""
        insights = []

        # Portfolio insights
        total_products = len(product_performance)
        insights.append(f"分析了{total_products}个伊利产品的市场表现")

        if product_performance:
            # Best performing product
            best_product = max(
                product_performance.items(),
                key=lambda x: x[1].get("performance_metrics", {}).get("avg_nps", 0)
            )
            insights.append(f"表现最佳产品：{best_product[0]}（平均NPS {best_product[1]['performance_metrics'].get('avg_nps', 0):.1f}）")

            # Category insights
            premium_products = [p for p, data in product_performance.items() if "premium" in data["product_info"].get("category", "")]
            if premium_products:
                premium_performance = [
                    product_performance[p]["performance_metrics"].get("avg_nps", 0) for p in premium_products
                ]
                avg_premium_nps = sum(premium_performance) / len(premium_performance)
                insights.append(f"高端产品线平均NPS {avg_premium_nps:.1f}，{'表现优异' if avg_premium_nps > 7.5 else '有待提升'}")

        # Competitive insights
        competitor_mentions = competitive_analysis.get("competitor_mentions", {})
        if competitor_mentions:
            most_mentioned = max(competitor_mentions.items(), key=lambda x: len(x[1]["mentions"]))
            insights.append(f"最受关注竞品：{most_mentioned[0]}（{len(most_mentioned[1]['mentions'])}次提及）")

        # Cross-selling insights
        if cross_selling_opportunities:
            top_opportunity = cross_selling_opportunities[0]
            insights.append(f"最大交叉销售机会：{top_opportunity['primary_product']}+{top_opportunity['cross_sell_product']}（预期提升{top_opportunity['expected_lift']:.1%}）")

        # Strategic insights
        brand_comparisons = competitive_analysis.get("brand_comparisons", [])
        if brand_comparisons:
            positive_comparisons = [c for c in brand_comparisons if c["sentiment"] == "positive"]
            comparison_ratio = len(positive_comparisons) / len(brand_comparisons)
            if comparison_ratio > 0.6:
                insights.append("消费者对比评价中，伊利产品整体占优")
            elif comparison_ratio < 0.4:
                insights.append("在消费者对比中处于劣势，需要加强竞争力")

        return insights

    async def _llm_competitive_analysis(self, tagged_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM for enhanced competitive analysis."""
        if not self.llm_client:
            return {}

        try:
            # Sample responses mentioning competitors
            competitor_texts = []
            for response in tagged_responses[:15]:  # Sample for LLM
                text = response.get("original_text", "")
                if any(competitor in text for competitor in self.competitor_brands.keys()):
                    competitor_texts.append(text)

            if not competitor_texts:
                return {}

            combined_text = "\n".join(f"反馈{i+1}: {text}" for i, text in enumerate(competitor_texts))

            prompt = f"""
分析以下包含竞品比较的消费者反馈，提供伊利的竞争分析：

{combined_text}

请分析：
1. 消费者如何看待伊利vs竞争对手
2. 伊利的竞争优势和劣势
3. 竞争对手的威胁和机会
4. 市场定位和品牌认知差异

以JSON格式返回：
{{
    "competitive_strengths": ["优势1", "优势2"],
    "competitive_weaknesses": ["劣势1", "劣势2"],
    "competitor_threats": [
        {{"competitor": "竞品名", "threat": "威胁描述", "severity": "high/medium/low"}}
    ],
    "market_opportunities": ["机会1", "机会2"],
    "positioning_insights": ["定位洞察1", "定位洞察2"]
}}
"""

            response = await self.llm_client.generate(prompt, temperature=0.3)

            import json
            return json.loads(response)

        except Exception as e:
            logger.debug(f"LLM competitive analysis failed: {e}")
            return {}

    async def _enhance_product_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        competitive_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Use LLM to enhance product recommendations."""
        if not self.llm_client:
            return []

        try:
            rec_summary = "\n".join([
                f"推荐{i+1}: {rec['title']} - {rec['type']}"
                for i, rec in enumerate(recommendations[:5])
            ])

            prompt = f"""
基于产品表现分析，提供战略性产品建议：

现有推荐：
{rec_summary}

请提供3个创新性产品战略建议：
1. 新产品开发机会
2. 现有产品升级方向
3. 市场扩展策略

以JSON格式返回：
[
    {{
        "title": "建议标题",
        "type": "new_product/product_upgrade/market_expansion",
        "description": "详细描述",
        "target_market": "目标市场",
        "competitive_advantage": "竞争优势",
        "implementation_timeline": "实施时间",
        "expected_roi": "预期回报"
    }}
]
"""

            response = await self.llm_client.generate(prompt, temperature=0.4)

            import json
            enhanced_data = json.loads(response)

            enhanced_recommendations = []
            for i, rec_data in enumerate(enhanced_data):
                enhanced_rec = {
                    "recommendation_id": f"product_strategy_{i}",
                    "priority": "strategic",
                    "type": rec_data.get("type", "strategic"),
                    "title": rec_data.get("title", ""),
                    "description": rec_data.get("description", ""),
                    "target_market": rec_data.get("target_market", ""),
                    "competitive_advantage": rec_data.get("competitive_advantage", ""),
                    "timeline": rec_data.get("implementation_timeline", "6-12个月"),
                    "expected_impact": "high",
                    "roi_estimate": rec_data.get("expected_roi", "medium")
                }
                enhanced_recommendations.append(enhanced_rec)

            return enhanced_recommendations

        except Exception as e:
            logger.debug(f"LLM product recommendation enhancement failed: {e}")
            return []