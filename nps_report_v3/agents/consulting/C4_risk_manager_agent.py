"""
C4 - Risk Manager Agent
Consulting Pass Agent for identifying business risks and mitigation strategies.
"""

import logging
from typing import Dict, Any, List, Optional
from collections import Counter
from datetime import datetime, timedelta

from ..base import ConsultingAgent, ConfidenceConstrainedAgent, AgentResult, AgentStatus
from ...llm import LLMClient

logger = logging.getLogger(__name__)


class RiskAssessment(dict):
    """Risk assessment structure"""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure required fields exist
        self.setdefault("risk_id", "")
        self.setdefault("risk_type", "")
        self.setdefault("title", "")
        self.setdefault("description", "")
        self.setdefault("severity", "medium")
        self.setdefault("probability", "medium")
        self.setdefault("impact_areas", [])
        self.setdefault("early_warning_signals", [])
        self.setdefault("mitigation_strategies", [])
        self.setdefault("contingency_plans", [])
        self.setdefault("monitoring_metrics", [])


class RiskManagerAgent(ConfidenceConstrainedAgent):
    """
    C4 - Risk Manager Agent

    Responsibilities:
    - Identify business risks from customer feedback and market signals
    - Assess risk severity and probability
    - Develop risk mitigation strategies
    - Create early warning systems
    - Provide contingency planning recommendations
    """

    def __init__(self, agent_id: str = "C4", agent_name: str = "Risk Manager Agent",
                 llm_client: Optional[LLMClient] = None, **kwargs):
        super().__init__(agent_id, agent_name, **kwargs)
        self.llm_client = llm_client
        self.min_confidence = 0.6  # Risk analysis requires reasonable confidence

        # Risk categories and classification
        self.risk_categories = {
            "customer_satisfaction": {
                "title": "客户满意度风险",
                "keywords": ["不满", "失望", "抱怨", "投诉", "差评"],
                "impact_areas": ["客户流失", "品牌声誉", "市场份额"],
                "severity_indicators": {
                    "high": ["大量投诉", "NPS显著下降", "媒体负面报道"],
                    "medium": ["满意度下降", "竞争加剧", "价格压力"],
                    "low": ["偶发问题", "局部不满", "轻微波动"]
                }
            },
            "product_quality": {
                "title": "产品质量风险",
                "keywords": ["质量", "变质", "安全", "标准", "缺陷"],
                "impact_areas": ["食品安全", "法律责任", "品牌信誉"],
                "severity_indicators": {
                    "high": ["安全事故", "监管处罚", "召回事件"],
                    "medium": ["质量投诉增加", "检验不合格", "客户警告"],
                    "low": ["个别质量问题", "轻微偏差", "改进建议"]
                }
            },
            "competitive_threat": {
                "title": "竞争威胁风险",
                "keywords": ["竞争", "对手", "替代", "价格战", "市场"],
                "impact_areas": ["市场份额", "定价能力", "利润率"],
                "severity_indicators": {
                    "high": ["新强劲竞争者", "颠覆性创新", "价格战"],
                    "medium": ["竞争加剧", "产品同质化", "营销对抗"],
                    "low": ["常规竞争", "局部竞争", "细分竞争"]
                }
            },
            "supply_chain": {
                "title": "供应链风险",
                "keywords": ["供应", "原料", "物流", "配送", "短缺"],
                "impact_areas": ["生产中断", "成本上升", "交付延迟"],
                "severity_indicators": {
                    "high": ["供应中断", "关键原料短缺", "物流瘫痪"],
                    "medium": ["供应紧张", "成本波动", "交付困难"],
                    "low": ["供应压力", "个别延迟", "成本微调"]
                }
            },
            "regulatory_compliance": {
                "title": "合规监管风险",
                "keywords": ["法规", "标准", "监管", "合规", "政策"],
                "impact_areas": ["法律责任", "运营许可", "市场准入"],
                "severity_indicators": {
                    "high": ["违规处罚", "许可吊销", "刑事责任"],
                    "medium": ["监管警告", "整改要求", "合规压力"],
                    "low": ["政策调整", "标准更新", "预防性合规"]
                }
            },
            "reputation": {
                "title": "品牌声誉风险",
                "keywords": ["声誉", "形象", "危机", "舆论", "负面"],
                "impact_areas": ["品牌价值", "客户信任", "投资信心"],
                "severity_indicators": {
                    "high": ["公关危机", "病毒传播", "媒体围攻"],
                    "medium": ["负面舆论", "信任下降", "形象受损"],
                    "low": ["个别负面", "局部争议", "传播风险"]
                }
            }
        }

        # Risk assessment matrix
        self.severity_levels = {
            "critical": {"score": 4, "description": "可能导致严重损失或业务中断"},
            "high": {"score": 3, "description": "显著影响业务表现或声誉"},
            "medium": {"score": 2, "description": "中等程度影响，需要关注"},
            "low": {"score": 1, "description": "轻微影响，可接受范围"}
        }

        self.probability_levels = {
            "very_high": {"score": 4, "description": "90%以上可能发生"},
            "high": {"score": 3, "description": "60-90%可能发生"},
            "medium": {"score": 2, "description": "30-60%可能发生"},
            "low": {"score": 1, "description": "30%以下可能发生"}
        }

    async def process(self, state: Dict[str, Any]) -> AgentResult:
        """
        Execute risk management analysis.

        Args:
            state: Current workflow state with all analysis results

        Returns:
            AgentResult with risk assessments and mitigation strategies
        """
        try:
            # Check confidence in risk-related data
            confidence_check = self._assess_risk_confidence(state)

            if confidence_check["confidence"] < self.min_confidence:
                logger.warning(f"Risk confidence {confidence_check['confidence']:.2f} below threshold {self.min_confidence}")
                return AgentResult(
                    agent_id=self.agent_id,
                    status=AgentStatus.FAILED,
                    errors=[f"Insufficient confidence in risk data: {confidence_check['issues']}"],
                    confidence_score=0.0
                )

            # Extract risk signals from analysis results
            risk_signals = await self._extract_risk_signals(state)

            # Identify and assess risks
            risk_assessments = await self._identify_and_assess_risks(risk_signals, state)

            # Prioritize risks by impact and probability
            prioritized_risks = self._prioritize_risks(risk_assessments)

            # Develop mitigation strategies
            mitigation_strategies = self._develop_mitigation_strategies(prioritized_risks, state)

            # Create early warning system
            early_warning_system = self._create_early_warning_system(prioritized_risks)

            # Generate contingency plans
            contingency_plans = self._generate_contingency_plans(prioritized_risks)

            # Create risk monitoring dashboard
            risk_dashboard = self._create_risk_dashboard(prioritized_risks, risk_signals)

            logger.info(f"Identified and assessed {len(prioritized_risks)} business risks")

            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.COMPLETED,
                data={
                    "risk_assessments": prioritized_risks,
                    "mitigation_strategies": mitigation_strategies,
                    "early_warning_system": early_warning_system,
                    "contingency_plans": contingency_plans,
                    "risk_dashboard": risk_dashboard,
                    "risk_signals": risk_signals,
                    "confidence": confidence_check["confidence"]
                },
                insights=[{"type": "risk", "count": len(prioritized_risks)}],
                confidence_score=confidence_check["confidence"]
            )

        except Exception as e:
            logger.error(f"Risk management analysis failed: {e}")
            return AgentResult(
                agent_id=self.agent_id,
                status=AgentStatus.FAILED,
                errors=[str(e)],
                confidence_score=0.0
            )

    def _assess_risk_confidence(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Assess confidence in risk analysis data.

        Args:
            state: Current workflow state

        Returns:
            Confidence assessment
        """
        confidence_factors = []
        issues = []

        # Check sample size for statistical significance
        nps_metrics = state.get("nps_metrics", {})
        sample_size = nps_metrics.get("sample_size", 0)

        if sample_size >= 100:
            confidence_factors.append(0.9)
        elif sample_size >= 50:
            confidence_factors.append(0.7)
        elif sample_size >= 20:
            confidence_factors.append(0.5)
        else:
            confidence_factors.append(0.3)
            issues.append("样本量较小，风险评估准确性有限")

        # Check feedback diversity
        tagged_responses = state.get("tagged_responses", [])
        sentiment_counts = Counter(r.get("sentiment", "neutral") for r in tagged_responses)

        if len(sentiment_counts) >= 3:  # Has positive, negative, and neutral
            confidence_factors.append(0.8)
        elif len(sentiment_counts) >= 2:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)
            issues.append("反馈情绪单一，风险识别范围受限")

        # Check detractor analysis availability
        nps_detractors = nps_metrics.get("detractors_count", 0)
        if nps_detractors >= 10:
            confidence_factors.append(0.8)
        elif nps_detractors >= 5:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.4)
            issues.append("不推荐者数量较少，风险信号有限")

        # Check technical requirements for operational risks
        tech_reqs = state.get("technical_requirements", [])
        critical_reqs = [req for req in tech_reqs if req.get("priority") in ["critical", "high"]]

        if len(critical_reqs) >= 3:
            confidence_factors.append(0.7)
        elif len(critical_reqs) >= 1:
            confidence_factors.append(0.6)
        else:
            confidence_factors.append(0.5)
            issues.append("缺乏高优先级技术需求，运营风险识别不足")

        overall_confidence = sum(confidence_factors) / len(confidence_factors) if confidence_factors else 0

        return {
            "confidence": overall_confidence,
            "factors": confidence_factors,
            "issues": issues
        }

    async def _extract_risk_signals(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract risk signals from various analysis results.

        Args:
            state: Current workflow state

        Returns:
            Risk signals by category
        """
        signals = {
            "nps_deterioration": {},
            "negative_sentiment_patterns": [],
            "quality_concerns": [],
            "competitive_threats": [],
            "operational_issues": [],
            "customer_churn_indicators": []
        }

        # Extract NPS deterioration signals
        nps_metrics = state.get("nps_metrics", {})
        if nps_metrics:
            nps_score = nps_metrics.get("nps_score", 0)
            detractors_pct = nps_metrics.get("detractors_percentage", 0)

            signals["nps_deterioration"] = {
                "current_nps": nps_score,
                "detractor_rate": detractors_pct,
                "risk_level": "high" if nps_score < 10 else "medium" if nps_score < 30 else "low",
                "critical_threshold": nps_score < 0,
                "warning_threshold": detractors_pct > 30
            }

        # Extract negative sentiment patterns
        tagged_responses = state.get("tagged_responses", [])
        negative_responses = [r for r in tagged_responses if r.get("sentiment") == "negative"]

        for response in negative_responses:
            comment = str(response.get("comment", "")).lower()

            # Categorize negative feedback by risk type
            for risk_type, config in self.risk_categories.items():
                if any(keyword in comment for keyword in config["keywords"]):
                    signals["negative_sentiment_patterns"].append({
                        "risk_type": risk_type,
                        "severity": self._assess_comment_severity(comment, config),
                        "content": response.get("comment", "")[:200],
                        "response_id": response.get("response_id")
                    })

        # Extract quality concerns
        clusters = state.get("semantic_clusters", [])
        quality_keywords = ["质量", "安全", "变质", "过期", "异味", "杂质"]

        for cluster in clusters:
            theme = cluster.get("theme", "").lower()
            if any(keyword in theme for keyword in quality_keywords):
                sentiment_dist = cluster.get("sentiment_distribution", {})
                if sentiment_dist.get("negative", 0) > 0.5:
                    signals["quality_concerns"].append({
                        "theme": cluster.get("theme"),
                        "frequency": cluster.get("size", 0),
                        "severity": "high" if sentiment_dist["negative"] > 0.8 else "medium",
                        "representative_quotes": cluster.get("representative_quotes", [])
                    })

        # Extract competitive threats
        competitive_keywords = ["蒙牛", "光明", "君乐宝", "竞争", "对手", "替代", "选择"]
        for response in tagged_responses:
            comment = str(response.get("comment", "")).lower()
            if any(keyword in comment for keyword in competitive_keywords):
                signals["competitive_threats"].append({
                    "sentiment": response.get("sentiment"),
                    "content": response.get("comment", "")[:200],
                    "threat_type": self._classify_competitive_threat(comment)
                })

        # Extract operational issues from technical requirements
        tech_reqs = state.get("technical_requirements", [])
        operational_categories = ["service", "logistics", "system", "process"]

        for req in tech_reqs:
            if req.get("category") in operational_categories and req.get("priority") in ["critical", "high"]:
                signals["operational_issues"].append({
                    "category": req.get("category"),
                    "description": req["description"],
                    "priority": req.get("priority"),
                    "impact": len(req.get("related_responses", [])),
                    "feasibility": req.get("feasibility", "unknown")
                })

        # Extract customer churn indicators
        if signals["nps_deterioration"]["detractor_rate"] > 25:
            signals["customer_churn_indicators"].append({
                "indicator": "高不推荐者比例",
                "value": signals["nps_deterioration"]["detractor_rate"],
                "threshold": 25,
                "risk_level": "high"
            })

        # Analyze detractor-specific risks
        detractor_analysis = state.get("detractor_analysis")
        if detractor_analysis:
            pain_points = detractor_analysis.get("pain_points", [])
            for pain_point in pain_points:
                if pain_point.get("severity_score", 0) >= 8:
                    signals["customer_churn_indicators"].append({
                        "indicator": pain_point.get("category", ""),
                        "description": pain_point.get("description", ""),
                        "severity": pain_point.get("severity_score"),
                        "risk_level": "high"
                    })

        return signals

    def _assess_comment_severity(self, comment: str, risk_config: Dict[str, Any]) -> str:
        """
        Assess severity of a comment based on risk category indicators.

        Args:
            comment: Comment text
            risk_config: Risk category configuration

        Returns:
            Severity level
        """
        severity_indicators = risk_config["severity_indicators"]

        # Check for high severity indicators
        for indicator in severity_indicators["high"]:
            if any(word in comment for word in indicator.split()):
                return "high"

        # Check for medium severity indicators
        for indicator in severity_indicators["medium"]:
            if any(word in comment for word in indicator.split()):
                return "medium"

        return "low"

    def _classify_competitive_threat(self, comment: str) -> str:
        """
        Classify type of competitive threat from comment.

        Args:
            comment: Comment text

        Returns:
            Threat type classification
        """
        if any(word in comment for word in ["价格", "便宜", "贵", "性价比"]):
            return "pricing_pressure"
        elif any(word in comment for word in ["质量", "口感", "更好"]):
            return "quality_comparison"
        elif any(word in comment for word in ["选择", "替代", "改用"]):
            return "switching_threat"
        elif any(word in comment for word in ["创新", "新品", "技术"]):
            return "innovation_gap"
        else:
            return "general_competition"

    async def _identify_and_assess_risks(
        self,
        risk_signals: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[RiskAssessment]:
        """
        Identify and assess specific business risks.

        Args:
            risk_signals: Extracted risk signals
            state: Current workflow state

        Returns:
            List of risk assessments
        """
        risk_assessments = []

        # Customer satisfaction risks
        nps_risk = risk_signals["nps_deterioration"]
        if nps_risk["risk_level"] in ["high", "medium"]:
            risk = RiskAssessment(
                risk_id="CUST_SAT_001",
                risk_type="customer_satisfaction",
                title="客户满意度下降风险",
                description=f"NPS得分{nps_risk['current_nps']:.1f}，不推荐者比例{nps_risk['detractor_rate']:.1f}%",
                severity="critical" if nps_risk["critical_threshold"] else "high" if nps_risk["risk_level"] == "high" else "medium",
                probability="high" if nps_risk["warning_threshold"] else "medium",
                impact_areas=["客户流失", "市场份额", "收入下降", "品牌声誉"],
                early_warning_signals=["NPS持续下降", "不推荐者比例增加", "负面评价增多"],
                monitoring_metrics=["月度NPS", "客户流失率", "负面反馈比例"]
            )
            risk_assessments.append(risk)

        # Product quality risks
        quality_concerns = risk_signals["quality_concerns"]
        if quality_concerns:
            high_severity_concerns = [c for c in quality_concerns if c["severity"] == "high"]
            if high_severity_concerns:
                risk = RiskAssessment(
                    risk_id="PROD_QUAL_001",
                    risk_type="product_quality",
                    title="产品质量安全风险",
                    description=f"发现{len(high_severity_concerns)}个高严重度质量问题",
                    severity="critical",
                    probability="medium",
                    impact_areas=["食品安全", "法律责任", "品牌信誉", "监管处罚"],
                    early_warning_signals=["质量投诉增加", "媒体关注", "监管询问"],
                    monitoring_metrics=["质量投诉率", "产品检验合格率", "召回事件数量"]
                )
                risk_assessments.append(risk)

        # Competitive threat risks
        competitive_threats = risk_signals["competitive_threats"]
        negative_competitive = [t for t in competitive_threats if t["sentiment"] == "negative"]

        if len(negative_competitive) >= 3:
            threat_types = Counter(t["threat_type"] for t in negative_competitive)
            main_threat = threat_types.most_common(1)[0][0]

            risk = RiskAssessment(
                risk_id="COMP_THREAT_001",
                risk_type="competitive_threat",
                title="竞争威胁风险",
                description=f"主要威胁类型：{main_threat}，负面对比{len(negative_competitive)}次",
                severity="medium",
                probability="high",
                impact_areas=["市场份额", "定价能力", "客户获取"],
                early_warning_signals=["竞争对比增加", "价格压力", "客户流向竞品"],
                monitoring_metrics=["市场份额变化", "价格竞争指数", "品牌提及率对比"]
            )
            risk_assessments.append(risk)

        # Operational risks
        operational_issues = risk_signals["operational_issues"]
        critical_operational = [i for i in operational_issues if i["priority"] == "critical"]

        if critical_operational:
            risk = RiskAssessment(
                risk_id="OPER_RISK_001",
                risk_type="supply_chain",
                title="运营流程风险",
                description=f"{len(critical_operational)}个关键运营问题需要解决",
                severity="high",
                probability="medium",
                impact_areas=["运营效率", "客户体验", "成本控制"],
                early_warning_signals=["流程中断", "客户投诉增加", "运营成本上升"],
                monitoring_metrics=["流程效率指标", "运营成本", "客户服务水平"]
            )
            risk_assessments.append(risk)

        # Customer churn risks
        churn_indicators = risk_signals["customer_churn_indicators"]
        high_churn_risk = [i for i in churn_indicators if i["risk_level"] == "high"]

        if high_churn_risk:
            risk = RiskAssessment(
                risk_id="CHURN_RISK_001",
                risk_type="customer_satisfaction",
                title="客户流失风险",
                description=f"识别出{len(high_churn_risk)}个高风险流失指标",
                severity="high",
                probability="high",
                impact_areas=["客户基数", "收入稳定性", "增长目标"],
                early_warning_signals=["活跃度下降", "复购率降低", "客服投诉增加"],
                monitoring_metrics=["月度流失率", "客户生命周期价值", "复购间隔"]
            )
            risk_assessments.append(risk)

        # LLM-enhanced risk identification
        if self.llm_client:
            llm_risks = await self._llm_identify_risks(risk_signals, state)
            risk_assessments.extend(llm_risks)

        return risk_assessments

    async def _llm_identify_risks(
        self,
        risk_signals: Dict[str, Any],
        state: Dict[str, Any]
    ) -> List[RiskAssessment]:
        """
        Use LLM to identify additional risks.

        Args:
            risk_signals: Risk signals
            state: Current workflow state

        Returns:
            LLM-identified risks
        """
        if not self.llm_client:
            return []

        try:
            nps_score = state.get("nps_metrics", {}).get("nps_score", 0)
            negative_patterns = [p["risk_type"] for p in risk_signals.get("negative_sentiment_patterns", [])]
            quality_issues = len(risk_signals.get("quality_concerns", []))

            prompt = f"""
作为伊利集团的风险管理专家，基于以下数据识别潜在业务风险：

NPS得分：{nps_score:.1f}
负面模式：{list(set(negative_patterns))[:5]}
质量问题数：{quality_issues}

请识别3-4个具体的业务风险，每个风险包括：
1. 风险标题
2. 风险描述
3. 风险类型（customer_satisfaction/product_quality/competitive_threat/supply_chain/regulatory_compliance/reputation）
4. 严重程度（critical/high/medium/low）
5. 发生概率（very_high/high/medium/low）
6. 影响领域
7. 预警信号
8. 监控指标

以JSON格式返回：
[
    {{
        "title": "风险标题",
        "description": "风险描述",
        "risk_type": "风险类型",
        "severity": "严重程度",
        "probability": "发生概率",
        "impact_areas": ["影响领域1", "影响领域2"],
        "early_warning_signals": ["预警信号1", "预警信号2"],
        "monitoring_metrics": ["监控指标1", "监控指标2"]
    }}
]
"""

            response = await self.llm_client.generate(prompt, temperature=0.2)

            # Parse JSON response
            import json
            risks_data = json.loads(response)

            risks = []
            for idx, risk_data in enumerate(risks_data):
                risk = RiskAssessment(
                    risk_id=f"LLM_RISK_{idx:03d}",
                    risk_type=risk_data.get("risk_type", "customer_satisfaction"),
                    title=risk_data.get("title", ""),
                    description=risk_data.get("description", ""),
                    severity=risk_data.get("severity", "medium"),
                    probability=risk_data.get("probability", "medium"),
                    impact_areas=risk_data.get("impact_areas", []),
                    early_warning_signals=risk_data.get("early_warning_signals", []),
                    monitoring_metrics=risk_data.get("monitoring_metrics", [])
                )
                risks.append(risk)

            return risks

        except Exception as e:
            logger.debug(f"LLM risk identification failed: {e}")
            return []

    def _prioritize_risks(self, risk_assessments: List[RiskAssessment]) -> List[RiskAssessment]:
        """
        Prioritize risks by impact and probability matrix.

        Args:
            risk_assessments: List of risk assessments

        Returns:
            Prioritized risk assessments
        """
        def calculate_risk_score(risk):
            severity_score = self.severity_levels.get(risk.get("severity", "medium"), {"score": 2})["score"]
            probability_score = self.probability_levels.get(risk.get("probability", "medium"), {"score": 2})["score"]
            return severity_score * probability_score

        # Sort by risk score (severity × probability)
        risk_assessments.sort(key=calculate_risk_score, reverse=True)

        return risk_assessments

    def _develop_mitigation_strategies(
        self,
        prioritized_risks: List[RiskAssessment],
        state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Develop mitigation strategies for prioritized risks.

        Args:
            prioritized_risks: Prioritized risk assessments
            state: Current workflow state

        Returns:
            Mitigation strategies by risk category
        """
        strategies = {
            "immediate_actions": [],
            "preventive_measures": [],
            "contingency_preparations": [],
            "monitoring_enhancements": []
        }

        for risk in prioritized_risks:
            risk_type = risk.get("risk_type", "")
            severity = risk.get("severity", "medium")

            # Immediate actions for critical/high severity risks
            if severity in ["critical", "high"]:
                if risk_type == "customer_satisfaction":
                    strategies["immediate_actions"].append({
                        "risk_id": risk["risk_id"],
                        "action": "启动客户满意度提升专项行动",
                        "timeline": "1-2周",
                        "responsibility": "客户服务部",
                        "resources": "客服团队加强、高管关注客户反馈"
                    })

                elif risk_type == "product_quality":
                    strategies["immediate_actions"].append({
                        "risk_id": risk["risk_id"],
                        "action": "产品质量紧急排查和整改",
                        "timeline": "立即",
                        "responsibility": "质量控制部",
                        "resources": "全面质量检查、可能产品召回"
                    })

            # Preventive measures
            strategies["preventive_measures"].extend(
                self._generate_preventive_measures(risk)
            )

            # Contingency preparations
            if severity == "critical":
                strategies["contingency_preparations"].extend(
                    self._generate_contingency_plans_for_risk(risk)
                )

        # Enhanced monitoring based on early warning signals
        all_warning_signals = []
        for risk in prioritized_risks:
            all_warning_signals.extend(risk.get("early_warning_signals", []))

        unique_signals = list(set(all_warning_signals))
        for signal in unique_signals[:5]:  # Top 5 signals
            strategies["monitoring_enhancements"].append({
                "signal": signal,
                "monitoring_frequency": "每日" if any(r.get("severity") == "critical" for r in prioritized_risks) else "每周",
                "alert_threshold": "偏离基线20%",
                "response_team": "风险管理小组"
            })

        return strategies

    def _generate_preventive_measures(self, risk: RiskAssessment) -> List[Dict[str, Any]]:
        """
        Generate preventive measures for a specific risk.

        Args:
            risk: Risk assessment

        Returns:
            List of preventive measures
        """
        measures = []
        risk_type = risk.get("risk_type", "")

        if risk_type == "customer_satisfaction":
            measures.append({
                "measure": "建立客户满意度监控系统",
                "description": "实时跟踪NPS变化和客户反馈",
                "timeline": "1个月",
                "investment": "中等"
            })

        elif risk_type == "product_quality":
            measures.append({
                "measure": "加强质量管理体系",
                "description": "提升质量检测频次和标准",
                "timeline": "2个月",
                "investment": "高"
            })

        elif risk_type == "competitive_threat":
            measures.append({
                "measure": "竞争情报收集系统",
                "description": "建立竞争对手监控和分析机制",
                "timeline": "6周",
                "investment": "中等"
            })

        return measures

    def _generate_contingency_plans_for_risk(self, risk: RiskAssessment) -> List[Dict[str, Any]]:
        """
        Generate contingency plans for critical risks.

        Args:
            risk: Risk assessment

        Returns:
            List of contingency plans
        """
        plans = []
        risk_type = risk.get("risk_type", "")

        if risk_type == "product_quality":
            plans.append({
                "scenario": "产品质量危机",
                "trigger": "媒体曝光或监管介入",
                "action_plan": "立即启动危机公关，产品召回，高管道歉",
                "communication": "24小时内发布官方声明",
                "resource_allocation": "危机公关预算，法务支持"
            })

        elif risk_type == "reputation":
            plans.append({
                "scenario": "品牌声誉危机",
                "trigger": "负面舆情大规模传播",
                "action_plan": "危机公关团队介入，澄清事实，品牌修复",
                "communication": "多渠道统一回应",
                "resource_allocation": "公关预算，高级管理层时间"
            })

        return plans

    def _create_early_warning_system(self, prioritized_risks: List[RiskAssessment]) -> Dict[str, Any]:
        """
        Create early warning system for risk monitoring.

        Args:
            prioritized_risks: Prioritized risk assessments

        Returns:
            Early warning system configuration
        """
        warning_system = {
            "monitoring_metrics": [],
            "alert_thresholds": {},
            "escalation_procedures": [],
            "reporting_frequency": {}
        }

        # Collect all monitoring metrics
        all_metrics = []
        for risk in prioritized_risks:
            all_metrics.extend(risk.get("monitoring_metrics", []))

        unique_metrics = list(set(all_metrics))

        for metric in unique_metrics:
            warning_system["monitoring_metrics"].append({
                "metric": metric,
                "data_source": self._identify_data_source(metric),
                "collection_frequency": "daily",
                "baseline_calculation": "3个月历史均值"
            })

        # Set alert thresholds based on risk severity
        for risk in prioritized_risks:
            severity = risk.get("severity", "medium")
            risk_id = risk["risk_id"]

            if severity == "critical":
                threshold = "偏离基线15%"
                escalation = "立即通知高级管理层"
            elif severity == "high":
                threshold = "偏离基线25%"
                escalation = "24小时内通知部门经理"
            else:
                threshold = "偏离基线40%"
                escalation = "每周报告中包含"

            warning_system["alert_thresholds"][risk_id] = threshold
            warning_system["escalation_procedures"].append({
                "risk_id": risk_id,
                "escalation": escalation
            })

        # Set reporting frequencies
        warning_system["reporting_frequency"] = {
            "executive_dashboard": "每周",
            "detailed_risk_report": "每月",
            "crisis_alert": "实时",
            "trend_analysis": "每季度"
        }

        return warning_system

    def _identify_data_source(self, metric: str) -> str:
        """
        Identify likely data source for a monitoring metric.

        Args:
            metric: Monitoring metric name

        Returns:
            Data source identification
        """
        metric_lower = metric.lower()

        if "nps" in metric_lower or "满意度" in metric_lower:
            return "客户反馈系统"
        elif "质量" in metric_lower or "合格率" in metric_lower:
            return "质量管理系统"
        elif "投诉" in metric_lower or "客服" in metric_lower:
            return "客服系统"
        elif "销售" in metric_lower or "份额" in metric_lower:
            return "销售数据系统"
        elif "成本" in metric_lower or "效率" in metric_lower:
            return "运营管理系统"
        else:
            return "业务数据系统"

    def _generate_contingency_plans(self, prioritized_risks: List[RiskAssessment]) -> List[Dict[str, Any]]:
        """
        Generate comprehensive contingency plans.

        Args:
            prioritized_risks: Prioritized risk assessments

        Returns:
            List of contingency plans
        """
        contingency_plans = []

        # Group risks by type for comprehensive planning
        risk_groups = {}
        for risk in prioritized_risks:
            risk_type = risk.get("risk_type", "general")
            if risk_type not in risk_groups:
                risk_groups[risk_type] = []
            risk_groups[risk_type].append(risk)

        # Create contingency plan for each risk type
        for risk_type, risks in risk_groups.items():
            high_severity_risks = [r for r in risks if r.get("severity") in ["critical", "high"]]

            if high_severity_risks:
                plan = {
                    "risk_category": risk_type,
                    "trigger_conditions": [],
                    "response_team": self._identify_response_team(risk_type),
                    "action_steps": self._generate_action_steps(risk_type),
                    "communication_plan": self._generate_communication_plan(risk_type),
                    "resource_requirements": self._estimate_resources(risk_type),
                    "success_criteria": self._define_success_criteria(risk_type)
                }

                # Aggregate trigger conditions
                for risk in high_severity_risks:
                    plan["trigger_conditions"].extend(risk.get("early_warning_signals", []))

                contingency_plans.append(plan)

        return contingency_plans

    def _identify_response_team(self, risk_type: str) -> Dict[str, str]:
        """Identify response team for risk type"""
        teams = {
            "customer_satisfaction": {"lead": "客户服务总监", "members": ["客服经理", "产品经理", "市场经理"]},
            "product_quality": {"lead": "质量总监", "members": ["质量经理", "生产经理", "法务顾问"]},
            "competitive_threat": {"lead": "市场总监", "members": ["品牌经理", "销售经理", "产品经理"]},
            "reputation": {"lead": "公关总监", "members": ["公关经理", "法务顾问", "高级管理层"]}
        }
        return teams.get(risk_type, {"lead": "风险管理经理", "members": ["相关部门经理"]})

    def _generate_action_steps(self, risk_type: str) -> List[str]:
        """Generate action steps for risk type"""
        steps = {
            "customer_satisfaction": [
                "立即分析客户反馈根本原因",
                "制定客户挽回计划",
                "实施服务改进措施",
                "加强客户沟通"
            ],
            "product_quality": [
                "立即停止相关产品销售",
                "启动产品召回程序",
                "调查质量问题根因",
                "实施整改措施",
                "恢复生产和销售"
            ],
            "reputation": [
                "启动危机公关程序",
                "发布官方回应声明",
                "加强媒体沟通",
                "实施品牌修复计划"
            ]
        }
        return steps.get(risk_type, ["评估风险影响", "制定应对措施", "实施解决方案", "监控效果"])

    def _generate_communication_plan(self, risk_type: str) -> Dict[str, Any]:
        """Generate communication plan for risk type"""
        return {
            "internal": ["管理层通报", "员工内部沟通", "部门协调会议"],
            "external": ["客户通知", "媒体声明", "监管汇报"] if risk_type in ["product_quality", "reputation"] else ["客户沟通"],
            "timeline": "24小时内启动" if risk_type in ["product_quality", "reputation"] else "72小时内启动"
        }

    def _estimate_resources(self, risk_type: str) -> Dict[str, str]:
        """Estimate resource requirements for risk type"""
        return {
            "budget": "高" if risk_type in ["product_quality", "reputation"] else "中等",
            "human_resources": "跨部门团队",
            "timeline": "1-4周",
            "external_support": "可能需要外部顾问" if risk_type == "reputation" else "内部处理"
        }

    def _define_success_criteria(self, risk_type: str) -> List[str]:
        """Define success criteria for risk type"""
        criteria = {
            "customer_satisfaction": ["NPS恢复到正常水平", "客户投诉量下降", "客户流失率控制"],
            "product_quality": ["质量问题彻底解决", "监管合规恢复", "品牌信任重建"],
            "reputation": ["负面舆情平息", "品牌形象恢复", "客户信心重建"]
        }
        return criteria.get(risk_type, ["风险得到有效控制", "业务影响最小化"])

    def _create_risk_dashboard(
        self,
        prioritized_risks: List[RiskAssessment],
        risk_signals: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Create risk monitoring dashboard structure.

        Args:
            prioritized_risks: Prioritized risk assessments
            risk_signals: Risk signals

        Returns:
            Risk dashboard configuration
        """
        dashboard = {
            "risk_summary": {
                "total_risks": len(prioritized_risks),
                "critical_risks": len([r for r in prioritized_risks if r.get("severity") == "critical"]),
                "high_risks": len([r for r in prioritized_risks if r.get("severity") == "high"]),
                "risk_trend": "increasing" if risk_signals["nps_deterioration"]["risk_level"] == "high" else "stable"
            },
            "key_indicators": [
                {
                    "name": "NPS风险指数",
                    "current_value": risk_signals["nps_deterioration"]["current_nps"],
                    "threshold": 30,
                    "status": "red" if risk_signals["nps_deterioration"]["current_nps"] < 10 else "yellow" if risk_signals["nps_deterioration"]["current_nps"] < 30 else "green"
                },
                {
                    "name": "质量问题数量",
                    "current_value": len(risk_signals.get("quality_concerns", [])),
                    "threshold": 2,
                    "status": "red" if len(risk_signals.get("quality_concerns", [])) >= 3 else "green"
                }
            ],
            "top_risks": [
                {
                    "title": risk["title"],
                    "severity": risk.get("severity", "medium"),
                    "probability": risk.get("probability", "medium"),
                    "status": "monitoring"
                }
                for risk in prioritized_risks[:5]
            ],
            "recommended_actions": [
                {
                    "priority": "immediate",
                    "count": len([r for r in prioritized_risks if r.get("severity") == "critical"]),
                    "description": "需要立即采取行动的关键风险"
                },
                {
                    "priority": "short_term",
                    "count": len([r for r in prioritized_risks if r.get("severity") == "high"]),
                    "description": "短期内需要重点关注的风险"
                }
            ]
        }

        return dashboard
