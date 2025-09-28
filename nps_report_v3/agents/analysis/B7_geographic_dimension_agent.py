"""
B7 - Geographic Dimension Agent
Analysis Pass Agent for regional and demographic analysis.
"""

import logging
from typing import Dict, Any, List, Optional
from collections import defaultdict, Counter

from ..base import AnalysisAgent, AgentResult, AgentStatus
from ...llm import LLMClient

logger = logging.getLogger(__name__)


class GeographicDimensionAgent(AnalysisAgent):
    """
    B7 - Geographic Dimension Agent

    Responsibilities:
    - Analyze regional patterns and geographic distribution of feedback
    - Implement demographic segmentation and city-tier analysis
    - Create regional performance comparisons and market insights
    - Generate location-specific recommendations and expansion strategies
    """

    def __init__(self, agent_id: str = "B7", agent_name: str = "Geographic Dimension Agent",
                 llm_client: Optional[LLMClient] = None, **kwargs):
        super().__init__(agent_id, agent_name, **kwargs)
        self.llm_client = llm_client

        # Chinese geographic regions and city tiers
        self.geographic_regions = {
            "华北": {
                "provinces": ["北京", "天津", "河北", "山西", "内蒙古"],
                "characteristics": ["寒冷气候", "重工业", "消费习惯偏传统"],
                "dairy_preferences": ["纯奶偏好", "品牌忠诚度高", "营养价值重视"]
            },
            "华东": {
                "provinces": ["上海", "江苏", "浙江", "安徽", "福建", "江西", "山东"],
                "characteristics": ["经济发达", "消费升级", "健康意识强"],
                "dairy_preferences": ["有机产品", "高端消费", "口感品质要求高"]
            },
            "华南": {
                "provinces": ["广东", "广西", "海南", "香港", "澳门"],
                "characteristics": ["炎热气候", "开放文化", "国际化程度高"],
                "dairy_preferences": ["冷饮需求大", "口味多样化", "便携性重要"]
            },
            "华中": {
                "provinces": ["河南", "湖北", "湖南"],
                "characteristics": ["人口密集", "农业传统", "价格敏感"],
                "dairy_preferences": ["性价比重视", "家庭装偏好", "传统口味"]
            },
            "西南": {
                "provinces": ["重庆", "四川", "贵州", "云南", "西藏"],
                "characteristics": ["地形复杂", "口味偏辣", "物流挑战"],
                "dairy_preferences": ["口味适应性", "保质期要求", "包装耐运输"]
            },
            "西北": {
                "provinces": ["陕西", "甘肃", "青海", "宁夏", "新疆"],
                "characteristics": ["干燥气候", "民族多样", "经济待发展"],
                "dairy_preferences": ["营养需求高", "传统饮食习惯", "价格敏感度高"]
            },
            "东北": {
                "provinces": ["辽宁", "吉林", "黑龙江"],
                "characteristics": ["工业基础", "人口外流", "消费保守"],
                "dairy_preferences": ["品牌信任度", "量大实惠", "传统产品"]
            }
        }

        # City tier classification
        self.city_tiers = {
            "tier1": {
                "cities": ["北京", "上海", "广州", "深圳"],
                "characteristics": ["消费力强", "国际化", "品牌意识强", "创新接受度高"],
                "consumption_patterns": ["高端产品", "便利性需求", "品牌溢价接受度高"]
            },
            "tier2": {
                "cities": ["成都", "杭州", "武汉", "西安", "苏州", "天津", "南京", "长沙", "沈阳", "青岛"],
                "characteristics": ["快速发展", "中产阶级", "消费升级", "品质要求提升"],
                "consumption_patterns": ["性价比关注", "品质追求", "品牌选择理性"]
            },
            "tier3": {
                "cities": ["温州", "佛山", "无锡", "烟台", "太原", "合肥", "南昌", "贵阳", "石家庄"],
                "characteristics": ["经济增长", "消费潜力", "价格敏感", "品牌教育需要"],
                "consumption_patterns": ["实用导向", "口碑影响", "促销响应度高"]
            },
            "tier4_below": {
                "characteristics": ["县市及以下", "农村市场", "价格主导", "渠道下沉"],
                "consumption_patterns": ["基础需求", "量大优惠", "本土品牌接受度"]
            }
        }

        # Demographic segments
        self.demographic_segments = {
            "age_groups": {
                "gen_z": {"age": "18-25", "characteristics": ["数字原生", "个性化", "社交驱动"]},
                "millennials": {"age": "26-35", "characteristics": ["消费主力", "品质追求", "便利需求"]},
                "gen_x": {"age": "36-45", "characteristics": ["家庭责任", "理性消费", "品牌忠诚"]},
                "boomers": {"age": "46+", "characteristics": ["传统观念", "健康关注", "价格敏感"]}
            },
            "income_levels": {
                "high": {"threshold": "月收入15000+", "behavior": ["品牌偏好", "品质优先", "便利付费"]},
                "middle": {"threshold": "月收入8000-15000", "behavior": ["性价比平衡", "品牌选择", "促销关注"]},
                "lower": {"threshold": "月收入8000以下", "behavior": ["价格导向", "基础需求", "促销敏感"]}
            }
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Process geographic dimension analysis.

        Args:
            state: Current workflow state

        Returns:
            AgentResult with geographic and demographic insights
        """
        try:
            # Get data from state
            tagged_responses = state.get("tagged_responses", [])
            nps_results = state.get("nps_results", {})

            if not tagged_responses:
                logger.warning("No responses available for geographic dimension analysis")
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.COMPLETED,
                    data={
                        "geographic_dimension": {
                            "total_responses": 0,
                            "regional_analysis": {},
                            "city_tier_analysis": {},
                            "demographic_analysis": {},
                            "geographic_recommendations": []
                        }
                    },
                    insights=["No responses available for geographic dimension analysis"],
                    confidence_score=1.0
                )

            # Perform regional analysis
            regional_analysis = self._analyze_regional_patterns(tagged_responses, nps_results)

            # Perform city tier analysis
            city_tier_analysis = self._analyze_city_tiers(tagged_responses, regional_analysis)

            # Perform demographic analysis
            demographic_analysis = await self._analyze_demographics(tagged_responses)

            # Generate geographic insights
            geographic_insights = self._generate_geographic_insights(
                regional_analysis, city_tier_analysis, demographic_analysis
            )

            # Generate expansion opportunities
            expansion_opportunities = self._identify_expansion_opportunities(
                regional_analysis, city_tier_analysis
            )

            # Generate recommendations
            recommendations = await self._generate_geographic_recommendations(
                regional_analysis, city_tier_analysis, demographic_analysis, expansion_opportunities
            )

            logger.info(f"Analyzed {len(tagged_responses)} responses across geographic dimensions")

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "geographic_dimension": {
                        "total_responses": len(tagged_responses),
                        "regional_analysis": regional_analysis,
                        "city_tier_analysis": city_tier_analysis,
                        "demographic_analysis": demographic_analysis,
                        "expansion_opportunities": expansion_opportunities,
                        "geographic_recommendations": recommendations,
                        "geographic_insights": geographic_insights
                    }
                },
                insights=geographic_insights,
                confidence_score=0.75
            )

        except Exception as e:
            logger.error(f"Geographic dimension analysis failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                data={},
                errors=[str(e)],
                confidence_score=0.0
            )

    def _analyze_regional_patterns(
        self,
        tagged_responses: List[Dict[str, Any]],
        nps_results: Dict[str, Any]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze patterns across different geographic regions.

        Args:
            tagged_responses: Tagged responses
            nps_results: NPS results

        Returns:
            Regional analysis results
        """
        regional_analysis = {}

        # Initialize regional data
        for region_name, region_info in self.geographic_regions.items():
            regional_analysis[region_name] = {
                "region_info": region_info,
                "responses": [],
                "nps_scores": [],
                "sentiment_distribution": {"positive": 0, "negative": 0, "neutral": 0},
                "key_themes": [],
                "performance_metrics": {}
            }

        # Classify responses by region
        for response in tagged_responses:
            text = response.get("original_text", "")
            location_info = response.get("location", {})  # Assume location data available
            nps_score = response.get("nps_score")

            # Identify region from text or metadata
            identified_regions = self._identify_regions_from_text(text, location_info)

            for region in identified_regions:
                if region in regional_analysis:
                    regional_analysis[region]["responses"].append(response.get("response_id", ""))

                    if nps_score is not None:
                        regional_analysis[region]["nps_scores"].append(nps_score)

                    # Analyze sentiment
                    sentiment = self._analyze_regional_sentiment(text, region)
                    regional_analysis[region]["sentiment_distribution"][sentiment] += 1

                    # Extract regional themes
                    themes = self._extract_regional_themes(text, region)
                    regional_analysis[region]["key_themes"].extend(themes)

        # Calculate regional performance metrics
        for region, data in regional_analysis.items():
            if data["responses"]:  # Only analyze regions with data
                metrics = self._calculate_regional_metrics(data)
                regional_analysis[region]["performance_metrics"] = metrics
            else:
                # Remove regions with no data
                regional_analysis[region] = None

        # Filter out empty regions
        regional_analysis = {k: v for k, v in regional_analysis.items() if v is not None}

        return regional_analysis

    def _identify_regions_from_text(
        self,
        text: str,
        location_info: Dict[str, Any]
    ) -> List[str]:
        """Identify geographic regions from text and location metadata."""
        identified_regions = []

        # First try metadata
        if location_info:
            province = location_info.get("province", "")
            city = location_info.get("city", "")

            # Map province to region
            for region_name, region_data in self.geographic_regions.items():
                if province in region_data["provinces"] or city in region_data["provinces"]:
                    identified_regions.append(region_name)

        # Then try text analysis
        if not identified_regions:
            for region_name, region_data in self.geographic_regions.items():
                # Check for province/city mentions
                for province in region_data["provinces"]:
                    if province in text:
                        identified_regions.append(region_name)
                        break

        # Default region assignment based on content patterns
        if not identified_regions:
            inferred_region = self._infer_region_from_content(text)
            if inferred_region:
                identified_regions.append(inferred_region)

        return identified_regions or ["华东"]  # Default to most common region

    def _infer_region_from_content(self, text: str) -> Optional[str]:
        """Infer region from content patterns and preferences."""
        # Climate-based inference
        if any(word in text for word in ["热", "夏天", "冷饮", "冰"]):
            return "华南"  # Hot climate preferences
        elif any(word in text for word in ["冷", "冬天", "保温", "热饮"]):
            return "东北"  # Cold climate preferences

        # Economic patterns
        if any(word in text for word in ["便宜", "实惠", "省钱", "划算"]):
            return "华中"  # Price-sensitive regions
        elif any(word in text for word in ["高端", "品质", "进口", "有机"]):
            return "华东"  # Premium consumption

        # Cultural patterns
        if any(word in text for word in ["辣", "麻", "火锅", "川味"]):
            return "西南"  # Spicy food culture
        elif any(word in text for word in ["清淡", "养生", "健康", "营养"]):
            return "华东"  # Health-conscious

        return None

    def _analyze_regional_sentiment(self, text: str, region: str) -> str:
        """Analyze sentiment with regional context."""
        # Basic sentiment analysis
        positive_words = ["好", "喜欢", "满意", "不错", "推荐"]
        negative_words = ["差", "不好", "失望", "贵", "难喝"]

        # Regional adjustment factors
        region_characteristics = self.geographic_regions.get(region, {})
        if "价格敏感" in str(region_characteristics.get("characteristics", [])):
            # More weight to price-related sentiment
            if any(word in text for word in ["贵", "便宜", "实惠", "划算"]):
                if "贵" in text:
                    return "negative"
                elif any(word in text for word in ["便宜", "实惠", "划算"]):
                    return "positive"

        # Standard sentiment analysis
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"

    def _extract_regional_themes(self, text: str, region: str) -> List[str]:
        """Extract themes specific to regional preferences."""
        themes = []
        region_prefs = self.geographic_regions.get(region, {}).get("dairy_preferences", [])

        # Check for regional preference themes
        for pref in region_prefs:
            if any(keyword in text for keyword in pref.split()):
                themes.append(pref)

        # Climate-based themes
        if region in ["华南", "西南"] and any(word in text for word in ["热", "冷饮", "冰镇"]):
            themes.append("气候适应")
        elif region in ["东北", "华北"] and any(word in text for word in ["保质", "储存", "冷藏"]):
            themes.append("储存便利")

        # Economic themes
        if region in ["华中", "西北"] and any(word in text for word in ["性价比", "实惠", "经济"]):
            themes.append("经济实用")
        elif region in ["华东", "华南"] and any(word in text for word in ["品质", "高端", "进口"]):
            themes.append("品质追求")

        return themes

    def _calculate_regional_metrics(self, regional_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance metrics for a region."""
        responses = regional_data["responses"]
        nps_scores = regional_data["nps_scores"]
        sentiment_dist = regional_data["sentiment_distribution"]
        themes = regional_data["key_themes"]

        metrics = {
            "response_count": len(responses),
            "avg_nps": sum(nps_scores) / len(nps_scores) if nps_scores else 0,
            "nps_distribution": self._calculate_nps_distribution(nps_scores),
            "sentiment_score": self._calculate_sentiment_score(sentiment_dist),
            "theme_diversity": len(set(themes)),
            "regional_engagement": self._assess_regional_engagement(responses, themes)
        }

        return metrics

    def _calculate_nps_distribution(self, nps_scores: List[int]) -> Dict[str, float]:
        """Calculate NPS distribution."""
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

    def _assess_regional_engagement(self, responses: List[str], themes: List[str]) -> str:
        """Assess engagement level for region."""
        response_count = len(responses)
        theme_diversity = len(set(themes))

        if response_count >= 20 and theme_diversity >= 5:
            return "high"
        elif response_count >= 10 and theme_diversity >= 3:
            return "medium"
        else:
            return "low"

    def _analyze_city_tiers(
        self,
        tagged_responses: List[Dict[str, Any]],
        regional_analysis: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """Analyze patterns across city tiers."""
        city_tier_analysis = {}

        # Initialize city tier data
        for tier, tier_info in self.city_tiers.items():
            city_tier_analysis[tier] = {
                "tier_info": tier_info,
                "responses": [],
                "nps_scores": [],
                "consumption_patterns": [],
                "performance_metrics": {}
            }

        # Classify responses by city tier
        for response in tagged_responses:
            text = response.get("original_text", "")
            location_info = response.get("location", {})
            nps_score = response.get("nps_score")

            # Identify city tier
            identified_tier = self._identify_city_tier(text, location_info)

            if identified_tier and identified_tier in city_tier_analysis:
                city_tier_analysis[identified_tier]["responses"].append(response.get("response_id", ""))

                if nps_score is not None:
                    city_tier_analysis[identified_tier]["nps_scores"].append(nps_score)

                # Extract consumption patterns
                patterns = self._extract_consumption_patterns(text, identified_tier)
                city_tier_analysis[identified_tier]["consumption_patterns"].extend(patterns)

        # Calculate city tier metrics
        for tier, data in city_tier_analysis.items():
            if data["responses"]:
                metrics = self._calculate_city_tier_metrics(data)
                city_tier_analysis[tier]["performance_metrics"] = metrics

        return city_tier_analysis

    def _identify_city_tier(self, text: str, location_info: Dict[str, Any]) -> Optional[str]:
        """Identify city tier from text and location."""
        # Check metadata first
        city = location_info.get("city", "")
        if city:
            for tier, tier_data in self.city_tiers.items():
                if tier != "tier4_below" and city in tier_data.get("cities", []):
                    return tier

        # Check text mentions
        for tier, tier_data in self.city_tiers.items():
            if tier != "tier4_below":
                for city in tier_data.get("cities", []):
                    if city in text:
                        return tier

        # Infer from consumption patterns
        if any(word in text for word in ["高端", "进口", "品牌", "便利"]):
            return "tier1"
        elif any(word in text for word in ["性价比", "品质", "选择"]):
            return "tier2"
        elif any(word in text for word in ["实惠", "便宜", "促销", "打折"]):
            return "tier3"
        else:
            return "tier4_below"

    def _extract_consumption_patterns(self, text: str, tier: str) -> List[str]:
        """Extract consumption patterns based on city tier."""
        patterns = []
        tier_info = self.city_tiers.get(tier, {})
        expected_patterns = tier_info.get("consumption_patterns", [])

        # Check for expected patterns
        for pattern in expected_patterns:
            if any(keyword in text for keyword in pattern.split()):
                patterns.append(pattern)

        # Tier-specific pattern detection
        if tier == "tier1":
            if any(word in text for word in ["品牌", "进口", "高端", "便利"]):
                patterns.append("高端消费")
        elif tier == "tier2":
            if any(word in text for word in ["性价比", "品质", "理性"]):
                patterns.append("理性消费")
        elif tier in ["tier3", "tier4_below"]:
            if any(word in text for word in ["便宜", "实惠", "促销"]):
                patterns.append("价格导向")

        return patterns

    def _calculate_city_tier_metrics(self, tier_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate metrics for city tier."""
        responses = tier_data["responses"]
        nps_scores = tier_data["nps_scores"]
        patterns = tier_data["consumption_patterns"]

        metrics = {
            "response_count": len(responses),
            "avg_nps": sum(nps_scores) / len(nps_scores) if nps_scores else 0,
            "pattern_frequency": Counter(patterns),
            "market_penetration": self._assess_market_penetration(len(responses)),
            "consumption_sophistication": self._assess_consumption_sophistication(patterns)
        }

        return metrics

    def _assess_market_penetration(self, response_count: int) -> str:
        """Assess market penetration level."""
        if response_count >= 30:
            return "high"
        elif response_count >= 15:
            return "medium"
        else:
            return "low"

    def _assess_consumption_sophistication(self, patterns: List[str]) -> str:
        """Assess consumption sophistication level."""
        sophisticated_patterns = ["高端消费", "品质追求", "品牌偏好", "创新接受"]
        basic_patterns = ["价格导向", "基础需求", "实用导向"]

        sophisticated_count = sum(1 for p in patterns if any(sp in p for sp in sophisticated_patterns))
        basic_count = sum(1 for p in patterns if any(bp in p for bp in basic_patterns))

        if sophisticated_count > basic_count:
            return "high"
        elif basic_count > sophisticated_count:
            return "low"
        else:
            return "medium"

    async def _analyze_demographics(self, tagged_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze demographic patterns in responses."""
        demographic_analysis = {
            "age_group_analysis": {},
            "income_level_analysis": {},
            "lifestyle_segments": {},
            "demographic_insights": []
        }

        # Initialize demographic categories
        for age_group, info in self.demographic_segments["age_groups"].items():
            demographic_analysis["age_group_analysis"][age_group] = {
                "info": info,
                "responses": [],
                "preferences": [],
                "nps_scores": []
            }

        # Analyze responses for demographic indicators
        for response in tagged_responses:
            text = response.get("original_text", "")
            demographic_info = response.get("demographics", {})
            nps_score = response.get("nps_score")

            # Identify age group
            age_group = self._identify_age_group(text, demographic_info)
            if age_group:
                demographic_analysis["age_group_analysis"][age_group]["responses"].append(response.get("response_id", ""))
                if nps_score is not None:
                    demographic_analysis["age_group_analysis"][age_group]["nps_scores"].append(nps_score)

                # Extract preferences
                preferences = self._extract_demographic_preferences(text, age_group)
                demographic_analysis["age_group_analysis"][age_group]["preferences"].extend(preferences)

        # Enhanced demographic analysis with LLM
        if self.llm_client:
            llm_insights = await self._llm_demographic_analysis(tagged_responses[:20])
            demographic_analysis["llm_insights"] = llm_insights

        return demographic_analysis

    def _identify_age_group(self, text: str, demographic_info: Dict[str, Any]) -> Optional[str]:
        """Identify age group from text and metadata."""
        # Check metadata first
        age = demographic_info.get("age")
        if age:
            if 18 <= age <= 25:
                return "gen_z"
            elif 26 <= age <= 35:
                return "millennials"
            elif 36 <= age <= 45:
                return "gen_x"
            elif age >= 46:
                return "boomers"

        # Infer from text patterns
        if any(word in text for word in ["学生", "大学", "刚毕业", "年轻", "90后", "00后"]):
            return "gen_z"
        elif any(word in text for word in ["工作", "职场", "买房", "结婚", "80后"]):
            return "millennials"
        elif any(word in text for word in ["家庭", "孩子", "中年", "事业", "70后"]):
            return "gen_x"
        elif any(word in text for word in ["退休", "老人", "养生", "健康", "60后"]):
            return "boomers"

        return None

    def _extract_demographic_preferences(self, text: str, age_group: str) -> List[str]:
        """Extract preferences based on demographic group."""
        preferences = []

        # Age-specific preference patterns
        if age_group == "gen_z":
            if any(word in text for word in ["个性", "潮流", "社交", "分享"]):
                preferences.append("个性化需求")
            if any(word in text for word in ["网红", "直播", "种草", "推荐"]):
                preferences.append("社交影响")
        elif age_group == "millennials":
            if any(word in text for word in ["品质", "体验", "便利", "效率"]):
                preferences.append("品质生活")
            if any(word in text for word in ["工作", "忙碌", "方便", "快捷"]):
                preferences.append("便利需求")
        elif age_group == "gen_x":
            if any(word in text for word in ["家庭", "孩子", "营养", "健康"]):
                preferences.append("家庭关怀")
            if any(word in text for word in ["稳定", "可靠", "信任", "品牌"]):
                preferences.append("品牌忠诚")
        elif age_group == "boomers":
            if any(word in text for word in ["健康", "养生", "营养", "安全"]):
                preferences.append("健康关注")
            if any(word in text for word in ["传统", "经典", "熟悉", "习惯"]):
                preferences.append("传统偏好")

        return preferences

    def _identify_expansion_opportunities(
        self,
        regional_analysis: Dict[str, Dict[str, Any]],
        city_tier_analysis: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Identify geographic expansion opportunities."""
        opportunities = []

        # Regional expansion opportunities
        for region, data in regional_analysis.items():
            metrics = data.get("performance_metrics", {})
            response_count = metrics.get("response_count", 0)
            avg_nps = metrics.get("avg_nps", 0)

            # High NPS but low response count indicates expansion opportunity
            if avg_nps > 7.5 and response_count < 15:
                opportunity = {
                    "type": "regional_expansion",
                    "target": region,
                    "opportunity_score": avg_nps - (response_count / 10),
                    "rationale": f"{region}地区NPS表现优秀但市场渗透率低",
                    "potential_market": data["region_info"]["characteristics"],
                    "expansion_strategy": self._suggest_regional_strategy(region, data)
                }
                opportunities.append(opportunity)

        # City tier expansion opportunities
        for tier, data in city_tier_analysis.items():
            metrics = data.get("performance_metrics", {})
            penetration = metrics.get("market_penetration", "low")

            if penetration == "low" and tier in ["tier2", "tier3"]:
                opportunity = {
                    "type": "city_tier_expansion",
                    "target": tier,
                    "opportunity_score": 0.7 if tier == "tier2" else 0.6,
                    "rationale": f"{tier}城市市场渗透率低但增长潜力大",
                    "target_characteristics": data["tier_info"]["characteristics"],
                    "expansion_strategy": self._suggest_tier_strategy(tier, data)
                }
                opportunities.append(opportunity)

        # Sort by opportunity score
        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)

        return opportunities[:5]  # Top 5 opportunities

    def _suggest_regional_strategy(self, region: str, data: Dict[str, Any]) -> List[str]:
        """Suggest expansion strategy for region."""
        region_chars = data["region_info"]["characteristics"]
        dairy_prefs = data["region_info"]["dairy_preferences"]

        strategies = []

        if "价格敏感" in str(region_chars):
            strategies.append("性价比产品推广")
            strategies.append("促销活动加强")
        if "消费升级" in str(region_chars):
            strategies.append("高端产品导入")
            strategies.append("品质宣传重点")
        if "物流挑战" in str(region_chars):
            strategies.append("渠道网络建设")
            strategies.append("保质期优化")

        return strategies or ["市场教育", "渠道建设", "品牌推广"]

    def _suggest_tier_strategy(self, tier: str, data: Dict[str, Any]) -> List[str]:
        """Suggest expansion strategy for city tier."""
        tier_chars = data["tier_info"]["characteristics"]

        strategies = []
        if tier == "tier2":
            strategies = ["品质差异化", "中高端定位", "渠道下沉", "本地化营销"]
        elif tier == "tier3":
            strategies = ["性价比突出", "渠道密集化", "口碑营销", "促销活动"]
        elif tier == "tier4_below":
            strategies = ["基础产品线", "价格竞争力", "农村渠道", "量贩包装"]

        return strategies

    def _generate_geographic_insights(
        self,
        regional_analysis: Dict[str, Dict[str, Any]],
        city_tier_analysis: Dict[str, Dict[str, Any]],
        demographic_analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate geographic and demographic insights."""
        insights = []

        # Regional insights
        if regional_analysis:
            # Best performing region
            best_region = max(
                regional_analysis.items(),
                key=lambda x: x[1].get("performance_metrics", {}).get("avg_nps", 0)
            )
            insights.append(f"表现最佳区域：{best_region[0]}（平均NPS {best_region[1]['performance_metrics'].get('avg_nps', 0):.1f}）")

            # Regional coverage
            coverage_count = len([r for r in regional_analysis.values() if r["performance_metrics"].get("response_count", 0) > 10])
            insights.append(f"在{coverage_count}个主要区域有较好市场表现")

        # City tier insights
        if city_tier_analysis:
            tier1_performance = city_tier_analysis.get("tier1", {}).get("performance_metrics", {})
            if tier1_performance:
                insights.append(f"一线城市平均NPS {tier1_performance.get('avg_nps', 0):.1f}，市场基础稳固")

        # Demographic insights
        age_analysis = demographic_analysis.get("age_group_analysis", {})
        if age_analysis:
            # Find most engaged age group
            most_engaged = max(
                age_analysis.items(),
                key=lambda x: len(x[1].get("responses", []))
            )
            insights.append(f"最活跃用户群体：{most_engaged[0]}（{len(most_engaged[1]['responses'])}条反馈）")

        # Cross-dimensional insights
        insights.append("不同地域和人群呈现差异化消费特征，需要精准化营销策略")

        return insights

    async def _generate_geographic_recommendations(
        self,
        regional_analysis: Dict[str, Dict[str, Any]],
        city_tier_analysis: Dict[str, Dict[str, Any]],
        demographic_analysis: Dict[str, Any],
        expansion_opportunities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Generate geographic-specific recommendations."""
        recommendations = []

        # Regional recommendations
        for region, data in regional_analysis.items():
            metrics = data.get("performance_metrics", {})
            if metrics.get("avg_nps", 0) < 6.5:  # Underperforming regions
                rec = {
                    "recommendation_id": f"regional_{region}",
                    "type": "regional_improvement",
                    "target": region,
                    "priority": "high",
                    "title": f"改善{region}地区市场表现",
                    "description": f"{region}地区NPS低于平均水平，需要针对性改进",
                    "specific_actions": self._suggest_regional_strategy(region, data),
                    "target_characteristics": data["region_info"]["characteristics"]
                }
                recommendations.append(rec)

        # Expansion recommendations
        for opportunity in expansion_opportunities[:3]:  # Top 3 opportunities
            rec = {
                "recommendation_id": f"expansion_{opportunity['target']}",
                "type": "market_expansion",
                "target": opportunity["target"],
                "priority": "medium",
                "title": f"拓展{opportunity['target']}市场",
                "description": opportunity["rationale"],
                "expansion_strategy": opportunity["expansion_strategy"],
                "opportunity_score": opportunity["opportunity_score"]
            }
            recommendations.append(rec)

        # Enhanced recommendations with LLM
        if self.llm_client and recommendations:
            enhanced_recs = await self._enhance_geographic_recommendations(recommendations, regional_analysis)
            if enhanced_recs:
                recommendations.extend(enhanced_recs)

        return recommendations[:8]  # Top 8 recommendations

    async def _llm_demographic_analysis(self, tagged_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM for enhanced demographic analysis."""
        if not self.llm_client:
            return {}

        try:
            sample_texts = [resp.get("original_text", "") for resp in tagged_responses]
            combined_text = "\n".join(f"反馈{i+1}: {text}" for i, text in enumerate(sample_texts) if text)

            prompt = f"""
分析以下消费者反馈的人群特征和地域特色：

{combined_text}

请识别：
1. 主要用户群体特征（年龄、收入、生活方式）
2. 地域消费差异和偏好
3. 人群细分和定位机会
4. 跨地域的共同趋势

以JSON格式返回：
{{
    "user_segments": [
        {{"segment": "群体名称", "characteristics": ["特征1", "特征2"], "preferences": ["偏好1", "偏好2"]}}
    ],
    "regional_differences": [
        {{"aspect": "差异方面", "pattern": "差异模式描述"}}
    ],
    "targeting_opportunities": ["机会1", "机会2"],
    "common_trends": ["趋势1", "趋势2"]
}}
"""

            response = await self.llm_client.generate(prompt, temperature=0.3)

            import json
            return json.loads(response)

        except Exception as e:
            logger.debug(f"LLM demographic analysis failed: {e}")
            return {}

    async def _enhance_geographic_recommendations(
        self,
        recommendations: List[Dict[str, Any]],
        regional_analysis: Dict[str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Use LLM to enhance geographic recommendations."""
        if not self.llm_client:
            return []

        try:
            rec_summary = "\n".join([
                f"推荐{i+1}: {rec['title']} - {rec['target']}"
                for i, rec in enumerate(recommendations[:5])
            ])

            regional_summary = "\n".join([
                f"{region}: NPS {data['performance_metrics'].get('avg_nps', 0):.1f}"
                for region, data in regional_analysis.items()
                if data.get('performance_metrics')
            ])

            prompt = f"""
基于地域分析结果，提供地域营销战略建议：

现有推荐：
{rec_summary}

区域表现：
{regional_summary}

请提供3个创新地域策略：
1. 跨区域协同策略
2. 本土化深度策略
3. 数字化地域精准营销

以JSON格式返回：
[
    {{
        "title": "策略标题",
        "type": "cross_regional/localization/digital_targeting",
        "description": "详细描述",
        "target_regions": ["目标区域"],
        "implementation_approach": "实施方法",
        "expected_outcome": "预期结果"
    }}
]
"""

            response = await self.llm_client.generate(prompt, temperature=0.4)

            import json
            enhanced_data = json.loads(response)

            enhanced_recommendations = []
            for i, rec_data in enumerate(enhanced_data):
                enhanced_rec = {
                    "recommendation_id": f"geo_strategy_{i}",
                    "type": rec_data.get("type", "geographic_strategy"),
                    "priority": "strategic",
                    "title": rec_data.get("title", ""),
                    "description": rec_data.get("description", ""),
                    "target_regions": rec_data.get("target_regions", []),
                    "implementation": rec_data.get("implementation_approach", ""),
                    "expected_outcome": rec_data.get("expected_outcome", "")
                }
                enhanced_recommendations.append(enhanced_rec)

            return enhanced_recommendations

        except Exception as e:
            logger.debug(f"LLM geographic recommendation enhancement failed: {e}")
            return []