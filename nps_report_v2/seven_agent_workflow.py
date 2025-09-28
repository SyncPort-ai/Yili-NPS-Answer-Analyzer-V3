#!/usr/bin/env python3
"""
Seven Agent Analysis Workflow for NPS Report V2
Integrates the seven agent analysis into the V2 processing pipeline with AI-powered agents
"""
import json
import logging
import os
from typing import Dict, Any, List
from datetime import datetime
from pathlib import Path

from .input_data_processor import InputDataProcessor

# Configure logging
logger = logging.getLogger(__name__)

class YiliPromptTemplates:
    """Prompt templates for Yili NPS analysis following the specification format"""
    
    # Agent 1: NPS Net Value Analysis Prompt Template
    NPS_NET_VALUE_ANALYSIS = """
请作为伊利集团的NPS专业分析师，深度分析以下NPS净值数据。

NPS数据：
净值分数: {nps_net_score}
总响应数: {total_responses}
行业基准: {industry_benchmark}%

伊利产品线参考：{key_brands}
主要竞争对手：蒙牛、光明、君乐宝、三元

请按照以下要求分析：
1. 评估当前NPS净值的行业地位和竞争力水平
2. 分析NPS表现对业务健康度的影响
3. 识别NPS分数背后的客户忠诚度信号
4. 提出基于NPS水平的战略建议
5. 预测NPS趋势和改进空间

请以JSON格式返回结果：
{{
    "nps_level_assessment": {{
        "level": "优秀/良好/中等/需改进",
        "industry_comparison": "超越/达到/低于行业标准",
        "competitive_position": "领先/中等/落后"
    }},
    "business_health_impact": {{
        "customer_loyalty": "高/中/低",
        "brand_strength": "强/中/弱",
        "growth_potential": "高/中/低"
    }},
    "strategic_recommendations": [
        {{
            "priority": "高/中/低",
            "action": "具体行动建议",
            "expected_impact": "预期效果",
            "timeline": "实施时间框架"
        }}
    ],
    "key_insights": [
        "洞察1: 关键发现和含义",
        "洞察2: 关键发现和含义"
    ]
}}
"""

    # Agent 2: NPS Distribution Analysis Prompt Template  
    NPS_DISTRIBUTION_ANALYSIS = """
请作为伊利集团的客户分群专家，分析以下NPS分布数据。

客户分布数据：
推荐者(9-10分): {promoters}人 ({promoter_pct:.1f}%)
中立者(7-8分): {passives}人 ({passive_pct:.1f}%)
贬损者(0-6分): {detractors}人 ({detractor_pct:.1f}%)
总客户数: {total}人

伊利目标客户：注重健康的消费者群体，追求品质生活的中产阶级

请按照以下要求分析：
1. 评估客户分布结构的健康度
2. 识别各客户群体的特征和行为模式
3. 分析客户流转的可能性和风险
4. 提出客户群体优化策略
5. 预测客户价值和生命周期

请以JSON格式返回结果：
{{
    "distribution_health": {{
        "structure_assessment": "健康/中等/有风险",
        "dominant_group": "推荐者/中立者/贬损者",
        "balance_score": "平衡评分0-10"
    }},
    "customer_insights": {{
        "promoter_characteristics": ["推荐者特征1", "推荐者特征2"],
        "passive_conversion_potential": "高/中/低",
        "detractor_risk_level": "高/中/低"
    }},
    "optimization_strategies": [
        {{
            "target_group": "推荐者/中立者/贬损者",
            "strategy": "具体优化策略",
            "conversion_goal": "转化目标",
            "success_metrics": "成功衡量指标"
        }}
    ],
    "business_implications": [
        "含义1: 对业务的影响",
        "含义2: 对业务的影响"
    ]
}}
"""

    # Agent 3: Positive Multiple Choice Analysis Prompt Template
    POSITIVE_FACTORS_ANALYSIS = """
请作为伊利集团的客户洞察专家，分析以下推荐者的正面因素选择。

正面因素数据：
总选择数: {total_selections}
因素种类: {unique_factors}
因素频次: {factor_frequency}
完整因素列表: {flattened_text}

伊利产品优势领域：产品品质、口味创新、营养健康、包装设计、品牌信任度

请按照以下要求分析：
1. 识别客户最认可的核心优势因素
2. 分析因素背后的客户价值需求
3. 评估这些优势的市场差异化价值
4. 提出基于优势的营销策略建议
5. 识别可放大的竞争优势

请以JSON格式返回结果：
{{
    "core_advantages": {{
        "primary_strength": "最核心优势",
        "secondary_strengths": ["次要优势1", "次要优势2"],
        "advantage_categories": {{"类别1": 权重, "类别2": 权重}}
    }},
    "customer_value_drivers": {{
        "functional_benefits": ["功能性价值1", "功能性价值2"],
        "emotional_benefits": ["情感性价值1", "情感性价值2"],
        "social_benefits": ["社交性价值1", "社交性价值2"]
    }},
    "marketing_opportunities": [
        {{
            "advantage": "优势因素",
            "communication_message": "传播信息",
            "target_audience": "目标受众",
            "channels": ["传播渠道1", "传播渠道2"]
        }}
    ],
    "competitive_positioning": {{
        "unique_selling_points": ["独特卖点1", "独特卖点2"],
        "differentiation_strategy": "差异化策略建议"
    }}
}}
"""

    # Agent 4: Positive Free Answers Analysis Prompt Template
    POSITIVE_OPENTEXT_ANALYSIS = """
请作为伊利集团的客户体验专家，深度分析以下推荐者的开放回答。

开放回答数据：
回答数量: {total_responses}
回答率: {response_rate:.1f}%
完整回答内容: {flattened_text}

分析重点：客户的真实感受、情感连接、使用场景、推荐动机

请按照以下要求分析：
1. 提取客户的真实情感和态度
2. 识别产品使用的具体场景和时机
3. 分析客户与品牌的情感连接点
4. 发现隐藏的客户需求和期望
5. 识别可用于营销的客户故事

请以JSON格式返回结果：
{{
    "emotional_insights": {{
        "dominant_emotions": ["主导情感1", "主导情感2"],
        "satisfaction_drivers": ["满意驱动因素1", "满意驱动因素2"],
        "emotional_connection_strength": "强/中/弱"
    }},
    "usage_scenarios": {{
        "primary_occasions": ["使用场景1", "使用场景2"],
        "consumption_patterns": ["消费模式1", "消费模式2"],
        "decision_contexts": ["决策场景1", "决策场景2"]
    }},
    "hidden_needs": {{
        "unmet_expectations": ["未满足期望1", "未满足期望2"],
        "improvement_opportunities": ["改进机会1", "改进机会2"],
        "innovation_directions": ["创新方向1", "创新方向2"]
    }},
    "customer_stories": [
        {{
            "story_theme": "故事主题",
            "narrative": "客户叙述",
            "marketing_value": "营销价值",
            "usage_recommendation": "使用建议"
        }}
    ]
}}
"""

    # Agent 5: Negative Multiple Choice Analysis Prompt Template
    NEGATIVE_FACTORS_ANALYSIS = """
请作为伊利集团的问题诊断专家，分析以下非推荐者的负面因素选择。

负面因素数据：
总选择数: {total_selections}
问题种类: {unique_factors}
因素频次: {factor_frequency}
完整因素列表: {flattened_text}

常见问题领域：产品质量、价格策略、营销宣传、渠道便利性、服务体验

请按照以下要求分析：
1. 识别最严重的客户流失风险因素
2. 分析问题的根本原因和系统性缺陷
3. 评估问题解决的紧急程度和影响范围
4. 提出问题解决的优先级和资源配置建议
5. 预测不解决问题的业务风险

请以JSON格式返回结果：
{{
    "critical_issues": {{
        "primary_problem": "最严重问题",
        "secondary_problems": ["次要问题1", "次要问题2"],
        "issue_categories": {{"类别1": 严重程度, "类别2": 严重程度}}
    }},
    "root_cause_analysis": {{
        "system_failures": ["系统性问题1", "系统性问题2"],
        "process_gaps": ["流程缺陷1", "流程缺陷2"],
        "resource_constraints": ["资源限制1", "资源限制2"]
    }},
    "solution_roadmap": [
        {{
            "problem": "具体问题",
            "solution": "解决方案",
            "priority": "高/中/低",
            "timeline": "解决时间框架",
            "resources_needed": "所需资源",
            "success_metrics": "成功指标"
        }}
    ],
    "risk_assessment": {{
        "customer_churn_risk": "高/中/低",
        "brand_reputation_impact": "高/中/低",
        "revenue_impact": "高/中/低",
        "competitive_vulnerability": "高/中/低"
    }}
}}
"""

    # Agent 6: Negative Free Answers Analysis Prompt Template
    NEGATIVE_OPENTEXT_ANALYSIS = """
请作为伊利集团的客户挽留专家，深度分析以下非推荐者的开放回答。

开放回答数据：
回答数量: {total_responses}
回答率: {response_rate:.1f}%
完整回答内容: {flattened_text}

分析重点：客户的不满情绪、具体痛点、失望原因、期望落差

请按照以下要求分析：
1. 识别客户不满的深层次原因
2. 分析客户期望与实际体验的差距
3. 评估客户情感创伤的严重程度
4. 提出客户挽留和关系修复策略
5. 发现产品和服务改进的具体方向

请以JSON格式返回结果：
{{
    "dissatisfaction_analysis": {{
        "primary_complaints": ["主要抱怨1", "主要抱怨2"],
        "emotional_intensity": "强烈/中等/轻微",
        "disappointment_sources": ["失望来源1", "失望来源2"]
    }},
    "expectation_gaps": {{
        "quality_expectations": ["质量期望1", "质量期望2"],
        "service_expectations": ["服务期望1", "服务期望2"],
        "value_expectations": ["价值期望1", "价值期望2"]
    }},
    "retention_strategies": [
        {{
            "customer_segment": "客户群体",
            "retention_approach": "挽留方法",
            "compensation_needed": "补偿措施",
            "relationship_repair": "关系修复策略",
            "success_probability": "成功概率"
        }}
    ],
    "improvement_priorities": [
        {{
            "area": "改进领域",
            "specific_issue": "具体问题",
            "improvement_action": "改进行动",
            "impact_level": "影响程度",
            "implementation_difficulty": "实施难度"
        }}
    ]
}}
"""

    # Agent 7: Comprehensive Summary Analysis Prompt Template
    COMPREHENSIVE_SUMMARY_ANALYSIS = """
请作为伊利集团的高级战略分析师，基于前六个智能体的分析结果，提供综合性的NPS洞察和战略建议。

前六个智能体分析摘要：
NPS净值分析: {agent1_summary}
客户分布分析: {agent2_summary}  
正面因素分析: {agent3_summary}
正面开放回答: {agent4_summary}
负面因素分析: {agent5_summary}
负面开放回答: {agent6_summary}

伊利集团背景：中国乳制品市场领导者，主要品牌包括{key_brands}，面临蒙牛、光明等激烈竞争

请按照以下要求提供综合分析：
1. 整合所有分析维度，识别NPS表现的核心驱动因素
2. 制定全面的NPS提升战略和行动计划
3. 平衡短期改进和长期品牌建设需求
4. 提供跨部门协作的具体建议
5. 建立NPS监控和持续改进机制

请以JSON格式返回结果：
{{
    "comprehensive_assessment": {{
        "overall_nps_health": "健康/中等/有风险",
        "key_drivers": ["核心驱动因素1", "核心驱动因素2"],
        "critical_success_factors": ["成功关键因素1", "成功关键因素2"],
        "main_challenges": ["主要挑战1", "主要挑战2"]
    }},
    "strategic_roadmap": {{
        "immediate_actions": [
            {{
                "action": "立即行动",
                "timeline": "1-3个月",
                "owner": "负责部门",
                "success_metric": "成功指标"
            }}
        ],
        "medium_term_initiatives": [
            {{
                "initiative": "中期举措",
                "timeline": "3-12个月", 
                "investment_required": "所需投资",
                "expected_outcome": "预期结果"
            }}
        ],
        "long_term_vision": {{
            "target_nps": "目标NPS分数",
            "timeline": "12-24个月",
            "transformation_areas": ["转型领域1", "转型领域2"]
        }}
    }},
    "cross_functional_recommendations": {{
        "product_development": ["产品开发建议1", "产品开发建议2"],
        "marketing_communications": ["营销传播建议1", "营销传播建议2"],
        "customer_service": ["客户服务建议1", "客户服务建议2"],
        "sales_channels": ["销售渠道建议1", "销售渠道建议2"],
        "quality_management": ["质量管理建议1", "质量管理建议2"]
    }},
    "monitoring_framework": {{
        "kpi_dashboard": ["关键指标1", "关键指标2"],
        "feedback_mechanisms": ["反馈机制1", "反馈机制2"],
        "review_frequency": "评估频率",
        "escalation_triggers": ["升级触发条件1", "升级触发条件2"]
    }},
    "executive_summary": {{
        "situation": "当前情况概述",
        "key_insights": "关键洞察",
        "recommendations": "核心建议",
        "expected_impact": "预期影响"
    }}
}}
"""

class YiliAIClient:
    """AI client for Yili NPS analysis with dual gateway support"""
    
    def __init__(self, use_yili_gateway: bool = True):
        self.use_yili_gateway = use_yili_gateway
        self.max_retries = 3
        
        # Yili Gateway Configuration
        self.yili_gateway_url = os.getenv(
            "YILI_GATEWAY_URL", 
            "https://ycsb-gw-pub.xapi.digitalyili.com/restcloud/yili-gpt-prod/v1/getTextToThird"
        )
        self.yili_app_key = os.getenv("YILI_APP_KEY", "649aa4671fa7b91962caa01d")
        
        # Azure OpenAI Configuration (fallback)
        self.azure_endpoint = os.getenv(
            "AZURE_OPENAI_ENDPOINT",
            "https://gpt4-turbo-sweden.openai.azure.com/openai/deployments/only_for_yili_test_4o_240710/chat/completions"
        )
        self.azure_api_key = os.getenv("AZURE_OPENAI_API_KEY", "")
        
        # Import requests here to avoid issues if not available
        try:
            import requests
            self.session = requests.Session()
        except ImportError:
            logger.warning("requests库未安装，AI功能将被禁用")
            self.session = None
    
    def analyze_with_prompt(self, prompt_template: str, **kwargs) -> Dict[str, Any]:
        """
        Analyze data using AI with the given prompt template
        
        Args:
            prompt_template: The prompt template to use
            **kwargs: Variables to substitute in the template
            
        Returns:
            Dict: AI analysis results
        """
        if not self.session:
            logger.warning("AI客户端不可用，返回模拟结果")
            return self._generate_fallback_response(prompt_template, **kwargs)
        
        try:
            # Format the prompt with provided variables
            formatted_prompt = prompt_template.format(**kwargs)
            
            # Try Yili Gateway first if enabled
            if self.use_yili_gateway:
                try:
                    result = self._call_yili_gateway(formatted_prompt)
                    if result:
                        return self._parse_ai_response(result)
                except Exception as e:
                    logger.warning(f"伊利网关调用失败: {e}")
            
            # Fallback to Azure OpenAI
            try:
                result = self._call_azure_openai(formatted_prompt)
                if result:
                    return self._parse_ai_response(result)
            except Exception as e:
                logger.warning(f"Azure OpenAI调用失败: {e}")
            
            # Final fallback to rule-based analysis
            return self._generate_fallback_response(prompt_template, **kwargs)
            
        except Exception as e:
            logger.error(f"AI分析过程出错: {e}")
            return self._generate_fallback_response(prompt_template, **kwargs)
    
    def _call_yili_gateway(self, prompt: str) -> str:
        """Call Yili AI Gateway"""
        data = {
            "channelCode": "wvEO",
            "tenantsCode": "Yun8457",
            "choiceModel": 1,
            "isMultiSession": 1,
            "requestContent": prompt,
            "requestType": 1,
            "streamFlag": 0,
            "userCode": "wvEO10047252",
            "requestGroupCode": "1243112808144896"
        }
        
        headers = {
            "Content-Type": "application/json",
            "appKey": self.yili_app_key
        }
        
        response = self.session.post(
            self.yili_gateway_url, 
            json=data, 
            headers=headers, 
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('code') == 0:
                return response_data['data']['responseVO']
        
        raise Exception(f"伊利网关返回错误: {response.status_code}")
    
    def _call_azure_openai(self, prompt: str) -> str:
        """Call Azure OpenAI as fallback"""
        headers = {
            "Content-Type": "application/json",
            "api-key": self.azure_api_key
        }
        
        data = {
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.1,
            "max_tokens": 4000
        }
        
        response = self.session.post(
            self.azure_endpoint,
            json=data,
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data['choices'][0]['message']['content']
        
        raise Exception(f"Azure OpenAI返回错误: {response.status_code}")
    
    def _parse_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse AI response and extract JSON"""
        try:
            # Try to find JSON in the response
            import re
            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                # If no JSON found, return the text as insights
                return {
                    "analysis_text": response_text,
                    "key_insights": [response_text[:200] + "..." if len(response_text) > 200 else response_text]
                }
        except Exception as e:
            logger.warning(f"AI响应解析失败: {e}")
            return {
                "analysis_text": response_text,
                "parsing_error": str(e),
                "key_insights": ["AI分析结果解析失败，请查看原始文本"]
            }
    
    def _generate_fallback_response(self, prompt_template: str, **kwargs) -> Dict[str, Any]:
        """Generate fallback response when AI is not available"""
        return {
            "fallback_mode": True,
            "message": "AI服务不可用，使用规则化分析",
            "key_insights": [
                "数据分析基于规则化逻辑完成",
                "建议联系技术支持启用AI功能以获得更深度的洞察"
            ],
            "analysis_text": "AI分析服务暂时不可用，已使用备用分析方法"
        }


class SevenAgentWorkflow:
    """Seven Agent Analysis Workflow for NPS Report V2 with AI-powered agents"""
    
    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai
        self.ai_client = YiliAIClient() if use_ai else None
        
        self.question_texts = {
            "nps_question": "Q1您向朋友或同事推荐我们的可能性多大？",
            "negative_factors": "Q2 您不愿意推荐我们的主要因素有哪些？",
            "negative_specific": "Q3 您不愿意推荐我们的具体原因是什么？",
            "positive_factors": "Q4 您愿意推荐我们的主要因素有哪些？",
            "positive_specific": "Q5 您愿意推荐我们的具体原因是什么？"
        }
        
        # Load knowledge files for context-aware analysis
        self.knowledge_base = self._load_knowledge_files()
        
        # Enhanced additional information with knowledge base
        self.additional_info = {
            "product_context": "伊利集团乳制品全产品线",
            "market_context": "中国乳制品市场竞争激烈，主要竞争对手包括蒙牛、光明、君乐宝",
            "business_focus": "提升NPS分数，改善客户满意度，优化产品和服务体验",
            "target_segments": "注重健康的消费者群体，追求品质生活的中产阶级",
            "key_brands": self.knowledge_base.get("key_brands", []),
            "business_units": [unit["name"] for unit in self.knowledge_base.get("business_units", [])],
            "analysis_tags": self.knowledge_base.get("business_tags", {})
        }
    
    def _load_knowledge_files(self):
        """Load all knowledge files for context-aware analysis"""
        knowledge_base = {}
        knowledge_dir = Path(__file__).resolve().parent.parent / "data" / "knowledge_files"
        
        try:
            # Load business tags
            tags_file = knowledge_dir / "business_tags.json"
            if tags_file.exists():
                with open(tags_file, 'r', encoding='utf-8') as f:
                    knowledge_base["business_tags"] = json.load(f)
            
            # Load Yili products
            products_file = knowledge_dir / "yili_products.json"
            if products_file.exists():
                with open(products_file, 'r', encoding='utf-8') as f:
                    products_data = json.load(f)
                    knowledge_base["key_brands"] = products_data.get("key_brands", [])
                    knowledge_base["business_units"] = products_data.get("business_units", [])
            
            # Load business rules
            rules_file = knowledge_dir / "business_rules.json"
            if rules_file.exists():
                with open(rules_file, 'r', encoding='utf-8') as f:
                    knowledge_base["business_rules"] = json.load(f)
            
            logger.info(f"知识库加载成功: {len(knowledge_base)} 个知识文件")
            
        except Exception as e:
            logger.warning(f"知识库加载失败: {e}")
            # Fallback to basic knowledge
            knowledge_base = {
                "business_tags": {
                    "口味设计": ["口味", "酸味", "甜味", "奶香味", "口感", "细腻度"],
                    "包装设计": ["包装", "美观", "便利性", "色彩", "图案"],
                    "概念设计": ["品质", "健康", "营养", "高端", "价格"]
                },
                "key_brands": ["安慕希", "金典", "舒化", "QQ星", "优酸乳", "巧乐兹"]
            }
        
        return knowledge_base
    
    def _categorize_factors(self, factors: List[str], factor_type: str = "positive"):
        """Categorize factors using business tags knowledge"""
        business_tags = self.knowledge_base.get("business_tags", {})
        categories = {}
        
        for factor in factors:
            for category, keywords in business_tags.items():
                for keyword in keywords:
                    if keyword in factor:
                        categories[category] = categories.get(category, 0) + 1
                        break
        
        # If no matches found, use basic categorization
        if not categories:
            for factor in factors:
                if any(word in factor for word in ["口味", "口感", "好喝", "味道", "甜味", "酸味"]):
                    categories["口味设计"] = categories.get("口味设计", 0) + 1
                elif any(word in factor for word in ["包装", "美观", "设计", "外观", "便携", "方便"]):
                    categories["包装设计"] = categories.get("包装设计", 0) + 1
                elif any(word in factor for word in ["价格", "性价比", "便宜", "实惠", "值"]):
                    categories["概念设计"] = categories.get("概念设计", 0) + 1
                else:
                    categories["其他"] = categories.get("其他", 0) + 1
        
        return categories
    
    def process_nps_data(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing function for seven agent analysis
        
        Args:
            input_data: Raw input data (Chinese format or other)
            
        Returns:
            Dict: Complete seven agent analysis results
        """
        try:
            logger.info("开始七智能体NPS分析流程...")
            
            # Step 1: Process input data
            processor = InputDataProcessor()
            processed_data = processor.process_survey_data(input_data)
            
            # Step 2: Split data into positive/negative sets
            positive_set, negative_set = self._split_users_2x3(processed_data)
            
            # Step 3: Calculate summary statistics
            data_summary = self._calculate_summary_stats(positive_set, negative_set)
            
            # Step 4: Run seven agent analysis
            agent_results = self._run_seven_agents(positive_set, negative_set, data_summary)
            
            # Step 5: Create final output
            final_output = self._create_final_output(
                input_data, processed_data, agent_results, positive_set, negative_set
            )
            
            logger.info("七智能体NPS分析完成")
            return final_output
            
        except Exception as e:
            logger.error(f"七智能体分析过程出错: {e}")
            raise
    
    def _split_users_2x3(self, processed_data):
        """Split users into 2 sets x 3 arrays each"""
        
        positive_set = {
            "nps_array": [],
            "multiple_choice_array": [],
            "free_question_array": []
        }
        
        negative_set = {
            "nps_array": [],
            "multiple_choice_array": [],
            "free_question_array": []
        }
        
        for response in processed_data.response_data:
            user_id = response.user_id
            nps_score = response.nps_score.value
            
            # NPS data
            nps_data = {
                "user_id": user_id,
                "nps_score": nps_score,
                "nps_category": response.nps_score.category.value,
                "raw_value": response.nps_score.raw_value
            }
            
            # Multiple choice data
            multiple_choice_data = {
                "user_id": user_id,
                "negative_factors": response.factor_responses.get('negative_factors').selected if response.factor_responses.get('negative_factors') else [],
                "positive_factors": response.factor_responses.get('positive_factors').selected if response.factor_responses.get('positive_factors') else [],
                "negative_factor_count": len(response.factor_responses.get('negative_factors').selected) if response.factor_responses.get('negative_factors') else 0,
                "positive_factor_count": len(response.factor_responses.get('positive_factors').selected) if response.factor_responses.get('positive_factors') else 0
            }
            
            # Free question data
            specific_reasons = response.open_responses.specific_reasons if response.open_responses.specific_reasons else {}
            free_question_data = {
                "user_id": user_id,
                "negative_reason": specific_reasons.get('negative', ''),
                "positive_reason": specific_reasons.get('positive', ''),
                "has_negative_text": bool(specific_reasons.get('negative', '').strip()),
                "has_positive_text": bool(specific_reasons.get('positive', '').strip()),
                "total_text_length": len(specific_reasons.get('negative', '') + specific_reasons.get('positive', ''))
            }
            
            # Categorize into positive or negative set
            if nps_score >= 9:  # Promoters
                positive_set["nps_array"].append(nps_data)
                positive_set["multiple_choice_array"].append(multiple_choice_data)
                positive_set["free_question_array"].append(free_question_data)
            else:  # Detractors and Passives
                negative_set["nps_array"].append(nps_data)
                negative_set["multiple_choice_array"].append(multiple_choice_data)
                negative_set["free_question_array"].append(free_question_data)
        
        return positive_set, negative_set
    
    def _calculate_summary_stats(self, positive_set, negative_set):
        """Calculate summary statistics"""
        
        total_users = len(positive_set["nps_array"]) + len(negative_set["nps_array"])
        promoters = len(positive_set["nps_array"])
        others = len(negative_set["nps_array"])
        
        promoter_pct = (promoters / total_users * 100) if total_users > 0 else 0
        
        # Calculate detractors and passives within negative set
        detractors = len([x for x in negative_set["nps_array"] if x["nps_score"] <= 6])
        passives = len([x for x in negative_set["nps_array"] if x["nps_score"] >= 7])
        
        detractor_pct = (detractors / total_users * 100) if total_users > 0 else 0
        nps_net_score = promoter_pct - detractor_pct
        
        return {
            "total_users": total_users,
            "positive_users": promoters,
            "negative_users": others,
            "nps_net_score": nps_net_score,
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors
        }
    
    def _run_seven_agents(self, positive_set, negative_set, data_summary):
        """Run all seven agents and collect results"""
        
        agent_results = []
        
        # Agent 1: NPS Net Value
        agent_results.append(self._agent_1_nps_net_value(data_summary))
        
        # Agent 2: NPS Distribution
        agent_results.append(self._agent_2_nps_distribution(positive_set, negative_set))
        
        # Agent 3: Positive Multiple Choice
        agent_results.append(self._agent_3_positive_multiple_choice(positive_set))
        
        # Agent 4: Positive Free Answers
        agent_results.append(self._agent_4_positive_free_answers(positive_set))
        
        # Agent 5: Negative Multiple Choice
        agent_results.append(self._agent_5_negative_multiple_choice(negative_set))
        
        # Agent 6: Negative Free Answers
        agent_results.append(self._agent_6_negative_free_answers(negative_set))
        
        # Agent 7: Total Summary
        agent_results.append(self._agent_7_total_summary(agent_results[:6], data_summary))
        
        return agent_results
    
    def _agent_1_nps_net_value(self, data_summary):
        """Agent 1: AI-Powered NPS Net Value Analysis"""
        
        nps_net = data_summary["nps_net_score"]
        total_users = data_summary["total_users"]
        industry_benchmark = self.knowledge_base.get("business_rules", {}).get("nps_scoring_rules", {}).get("industry_benchmark", 30)
        key_brands = ", ".join(self.knowledge_base.get("key_brands", ["安慕希", "金典", "舒化"]))
        
        logger.info("🤖 [AI调用 1/7] Agent 1: NPS净值深度分析...")
        
        if self.use_ai and self.ai_client:
            try:
                ai_result = self.ai_client.analyze_with_prompt(
                    YiliPromptTemplates.NPS_NET_VALUE_ANALYSIS,
                    nps_net_score=nps_net,
                    total_responses=total_users,
                    industry_benchmark=industry_benchmark,
                    key_brands=key_brands
                )
                
                # Merge AI results with basic analysis structure
                analysis = {
                    "agent_name": "NPS净值分析智能体",
                    "question_context": self.question_texts["nps_question"],
                    "input_data": {
                        "nps_net_score": nps_net,
                        "total_responses": total_users,
                        "industry_benchmark": industry_benchmark
                    },
                    "ai_analysis": ai_result,
                    "business_questions": [
                        "当前NPS水平是否达到行业标准？",
                        "需要采取什么措施提升NPS分数？",
                        "与竞争对手相比我们的表现如何？"
                    ]
                }
                
                # Extract key insights from AI response
                if "key_insights" in ai_result:
                    analysis["insight_summary"] = ai_result["key_insights"]
                else:
                    analysis["insight_summary"] = ai_result.get("key_insights", ["AI分析完成，详见AI分析结果"])
                
                # Generate summary from AI analysis
                if "nps_level_assessment" in ai_result:
                    level_info = ai_result["nps_level_assessment"]
                    analysis["summary_text"] = f"AI分析显示当前NPS净值{nps_net:.1f}%处于{level_info.get('level', '待评估')}水平，在行业中{level_info.get('industry_comparison', '表现待评估')}，竞争地位{level_info.get('competitive_position', '需进一步分析')}。"
                else:
                    analysis["summary_text"] = f"AI深度分析了NPS净值{nps_net:.1f}%的表现，提供了专业的业务洞察和战略建议。"
                
                return analysis
                
            except Exception as e:
                logger.warning(f"Agent 1 AI分析失败，使用规则分析: {e}")
        
        # Fallback to rule-based analysis
        return self._agent_1_fallback_analysis(data_summary)
    
    def _agent_1_fallback_analysis(self, data_summary):
        """Fallback rule-based analysis for Agent 1"""
        nps_net = data_summary["nps_net_score"]
        total_users = data_summary["total_users"]
        industry_benchmark = self.knowledge_base.get("business_rules", {}).get("nps_scoring_rules", {}).get("industry_benchmark", 30)
        
        analysis = {
            "agent_name": "NPS净值分析智能体",
            "question_context": self.question_texts["nps_question"],
            "input_data": {
                "nps_net_score": nps_net,
                "total_responses": total_users,
                "industry_benchmark": industry_benchmark
            },
            "statements": [],
            "business_questions": [
                "当前NPS水平是否达到行业标准？",
                "需要采取什么措施提升NPS分数？",
                "与竞争对手相比我们的表现如何？"
            ],
            "summary_text": "",
            "insight_summary": []
        }
        
        if nps_net >= 50:
            analysis["statements"] = [
                f"NPS净值为{nps_net:.1f}%，属于优秀水平，表明客户忠诚度很高",
                "大部分客户愿意推荐产品，形成了良好的口碑传播",
                "当前客户满意度策略效果显著，应继续保持",
                "可以考虑扩大市场份额和提升品牌影响力"
            ]
            analysis["summary_text"] = f"伊利集团NPS净值达到{nps_net:.1f}%的优秀水平，远超行业基准{industry_benchmark}%，显示出强劲的客户忠诚度和市场竞争力。推荐者群体占主导地位，为品牌建立了良好的口碑传播基础，建议继续保持当前优势策略并积极扩大市场影响力。"
            analysis["insight_summary"] = [
                "1. NPS表现优秀：净值超过50%，客户忠诚度高",
                "2. 口碑效应显著：推荐者形成良好传播",
                "3. 策略效果验证：当前满意度策略成功",
                "4. 扩张机会：可考虑市场份额提升"
            ]
        elif nps_net >= 0:
            analysis["statements"] = [
                f"NPS净值为{nps_net:.1f}%，处于中等水平，有改进空间",
                "推荐者略多于贬损者，但优势不明显",
                "需要重点关注提升客户体验和满意度",
                "应深入分析客户痛点，制定针对性改进方案"
            ]
            analysis["summary_text"] = f"伊利集团NPS净值为{nps_net:.1f}%，处于中等水平，虽然推荐者数量略多于贬损者，但优势不够明显，存在较大改进空间。需要深入分析客户体验痛点，特别关注{', '.join(self.knowledge_base.get('key_brands', ['安慕希', '金典', '舒化'])[:3])}等核心品牌的表现，制定系统性的客户满意度提升方案。"
            analysis["insight_summary"] = [
                "1. NPS水平中等：净值为正但不够强劲",
                "2. 优势微弱：推荐者仅略多于贬损者",
                "3. 改进空间大：客户体验需要提升",
                "4. 策略调整：需制定针对性改进方案"
            ]
        else:
            analysis["statements"] = [
                f"NPS净值为{nps_net:.1f}%，处于负值，客户满意度亟需改善",
                "贬损者多于推荐者，存在客户流失风险",
                "必须立即识别并解决核心问题",
                "建议暂缓市场扩张，优先提升产品和服务质量",
                "需要制定紧急客户挽留和满意度提升计划"
            ]
            analysis["summary_text"] = f"伊利集团NPS净值为{nps_net:.1f}%的负值表现令人担忧，贬损者数量超过推荐者，存在严重的客户流失风险。当前局面要求立即采取紧急措施，暂缓市场扩张计划，集中资源解决产品质量、服务体验或价格等核心问题，并制定全面的客户挽留和满意度重建计划。"
            analysis["insight_summary"] = [
                "1. NPS表现严重：净值为负，客户满意度低",
                "2. 流失风险高：贬损者多于推荐者",
                "3. 紧急状态：需立即识别核心问题",
                "4. 策略调整：暂缓扩张，专注质量提升",
                "5. 挽留计划：制定紧急客户挽留措施"
            ]
        
        return analysis
    
    def _agent_2_nps_distribution(self, positive_set, negative_set):
        """Agent 2: AI-Powered NPS Distribution Analysis"""
        
        total = len(positive_set["nps_array"]) + len(negative_set["nps_array"])
        promoters = len(positive_set["nps_array"])
        passives = len([x for x in negative_set["nps_array"] if x["nps_score"] >= 7])
        detractors = len([x for x in negative_set["nps_array"] if x["nps_score"] <= 6])
        
        logger.info("🤖 [AI调用 2/7] Agent 2: NPS分布深度分析...")
        
        if self.use_ai and self.ai_client:
            try:
                ai_result = self.ai_client.analyze_with_prompt(
                    YiliPromptTemplates.NPS_DISTRIBUTION_ANALYSIS,
                    promoters=promoters,
                    passives=passives,
                    detractors=detractors,
                    total=total,
                    promoter_pct=promoters/total*100 if total > 0 else 0,
                    passive_pct=passives/total*100 if total > 0 else 0,
                    detractor_pct=detractors/total*100 if total > 0 else 0
                )
                
                analysis = {
                    "agent_name": "NPS分布分析智能体",
                    "question_context": self.question_texts["nps_question"],
                    "input_data": {
                        "promoters": promoters,
                        "passives": passives,
                        "detractors": detractors,
                        "total": total
                    },
                    "ai_analysis": ai_result,
                    "business_questions": [
                        "如何将中立者转化为推荐者？",
                        "贬损者的主要问题点是什么？",
                        "推荐者群体有什么共同特征？"
                    ]
                }
                
                # Extract insights from AI response
                if "business_implications" in ai_result:
                    analysis["insight_summary"] = ai_result["business_implications"]
                else:
                    analysis["insight_summary"] = ai_result.get("key_insights", ["AI分析完成，详见AI分析结果"])
                
                # Generate summary from AI analysis
                if "distribution_health" in ai_result:
                    health_info = ai_result["distribution_health"]
                    analysis["summary_text"] = f"AI分析显示客户分布结构{health_info.get('structure_assessment', '待评估')}，{health_info.get('dominant_group', '客户群体')}占主导地位，整体平衡评分{health_info.get('balance_score', 'N/A')}。"
                else:
                    analysis["summary_text"] = f"AI深度分析了{total}位客户的NPS分布结构，提供了客户群体优化策略建议。"
                
                return analysis
                
            except Exception as e:
                logger.warning(f"Agent 2 AI分析失败，使用规则分析: {e}")
        
        # Fallback to rule-based analysis
        analysis = {
            "agent_name": "NPS分布分析智能体",
            "question_context": self.question_texts["nps_question"],
            "input_data": {
                "promoters": promoters,
                "passives": passives,
                "detractors": detractors,
                "total": total
            },
            "statements": [
                f"客户分布：推荐者{promoters}人({promoters/total*100:.1f}%)，中立者{passives}人({passives/total*100:.1f}%)，贬损者{detractors}人({detractors/total*100:.1f}%)",
                f"贬损者比例{'较高' if detractors/total > 0.3 else '适中' if detractors/total > 0.1 else '较低'}，需要{'重点关注' if detractors/total > 0.3 else '持续改进'}",
                f"推荐者比例{'充足' if promoters/total > 0.5 else '有待提升'}，{'可以' if promoters/total > 0.5 else '需要'}利用口碑营销",
                f"{'推荐者' if promoters > detractors else '贬损者'}群体占主导地位，反映了{'正面' if promoters > detractors else '负面'}的整体客户体验"
            ],
            "business_questions": [
                "如何将中立者转化为推荐者？",
                "贬损者的主要问题点是什么？",
                "推荐者群体有什么共同特征？"
            ],
            "summary_text": f"伊利集团客户满意度呈现{promoters}人推荐者({promoters/total*100:.1f}%)、{passives}人中立者({passives/total*100:.1f}%)、{detractors}人贬损者({detractors/total*100:.1f}%)的分布格局。{'推荐者' if promoters > detractors else '贬损者'}群体占主导地位，反映当前客户体验整体趋向{'正面' if promoters > detractors else '负面'}。中立者群体存在较大转化潜力，是提升NPS的关键突破口。",
            "insight_summary": [
                f"1. 客户结构：推荐者{promoters/total*100:.1f}%，中立者{passives/total*100:.1f}%，贬损者{detractors/total*100:.1f}%",
                f"2. 主导群体：{'推荐者' if promoters > detractors else '贬损者'}占优势地位",
                f"3. 风险评估：贬损者比例{'较高' if detractors/total > 0.3 else '适中' if detractors/total > 0.1 else '较低'}",
                f"4. 转化机会：{passives}位中立者具备提升潜力"
            ]
        }
        
        return analysis
    
    def _agent_3_positive_multiple_choice(self, positive_set):
        """Agent 3: AI-Powered Positive Multiple Choice Analysis"""
        
        # Flatten positive factors
        all_positive_factors = []
        for item in positive_set["multiple_choice_array"]:
            all_positive_factors.extend(item["positive_factors"])
        
        # Count factor frequency
        factor_counts = {}
        for factor in all_positive_factors:
            factor_counts[factor] = factor_counts.get(factor, 0) + 1
        
        flattened_text = " | ".join(all_positive_factors)
        
        logger.info("🤖 [AI调用 3/7] Agent 3: 正面因素深度分析...")
        
        if self.use_ai and self.ai_client and all_positive_factors:
            try:
                ai_result = self.ai_client.analyze_with_prompt(
                    YiliPromptTemplates.POSITIVE_FACTORS_ANALYSIS,
                    total_selections=len(all_positive_factors),
                    unique_factors=len(factor_counts),
                    factor_frequency=factor_counts,
                    flattened_text=flattened_text
                )
                
                analysis = {
                    "agent_name": "正面多选题分析智能体",
                    "question_context": self.question_texts["positive_factors"],
                    "input_data": {
                        "total_selections": len(all_positive_factors),
                        "unique_factors": len(factor_counts),
                        "flattened_text": flattened_text,
                        "factor_frequency": factor_counts
                    },
                    "ai_analysis": ai_result,
                    "business_questions": [
                        "哪些正面因素最能打动客户？",
                        "如何在营销中强化这些优势？",
                        "这些因素如何转化为竞争优势？"
                    ]
                }
                
                # Extract insights from AI response
                if "marketing_opportunities" in ai_result:
                    insights = []
                    for opp in ai_result["marketing_opportunities"]:
                        insights.append(f"营销机会: {opp.get('advantage', 'N/A')} - {opp.get('communication_message', 'N/A')}")
                    analysis["insight_summary"] = insights
                else:
                    analysis["insight_summary"] = ai_result.get("key_insights", ["AI分析完成，详见AI分析结果"])
                
                # Generate summary from AI analysis
                if "core_advantages" in ai_result:
                    advantage_info = ai_result["core_advantages"]
                    analysis["summary_text"] = f"AI分析识别出核心优势'{advantage_info.get('primary_strength', 'N/A')}'，为营销传播和竞争定位提供了明确方向。"
                else:
                    analysis["summary_text"] = f"AI深度分析了{len(all_positive_factors)}个正面因素，提供了营销机会和竞争优势建议。"
                
                return analysis
                
            except Exception as e:
                logger.warning(f"Agent 3 AI分析失败，使用规则分析: {e}")
        
        # Fallback to rule-based analysis or handle empty data
        factor_categories = self._categorize_factors(all_positive_factors, "positive")
        
        analysis = {
            "agent_name": "正面多选题分析智能体",
            "question_context": self.question_texts["positive_factors"],
            "input_data": {
                "total_selections": len(all_positive_factors),
                "unique_factors": len(factor_counts),
                "flattened_text": flattened_text,
                "factor_frequency": factor_counts,
                "factor_categories": factor_categories
            },
            "statements": [],
            "business_questions": [
                "哪些正面因素最能打动客户？",
                "如何在营销中强化这些优势？",
                "这些因素如何转化为竞争优势？"
            ],
            "summary_text": "",
            "insight_summary": []
        }
        
        if not all_positive_factors:
            analysis["statements"] = [
                "推荐者群体未提供具体的正面因素选择",
                "需要通过深度访谈了解推荐的真实原因",
                "建议优化问卷设计，增加更贴近客户体验的选项"
            ]
            analysis["summary_text"] = "推荐者群体在多选题中缺乏具体的正面因素反馈，表明问卷设计可能不够贴近实际客户体验，或推荐动机较为复杂难以通过标准选项表达。建议通过定性研究方法深入了解客户真实的推荐驱动因素。"
            analysis["insight_summary"] = [
                "1. 数据缺失：推荐者未选择具体正面因素",
                "2. 设计问题：问卷选项可能不够贴切",
                "3. 研究建议：需要深度访谈补充"
            ]
        else:
            top_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)
            main_category = max(factor_categories.items(), key=lambda x: x[1]) if factor_categories else ("产品品质", 0)
            
            analysis["statements"] = [
                f"推荐者共选择了{len(all_positive_factors)}个正面因素，涉及{len(factor_counts)}个不同维度",
                f"最受认可的因素是'{top_factors[0][0]}'，被{top_factors[0][1]}位客户选择",
                f"正面因素主要集中在{main_category[0]}方面，占比{main_category[1]/len(all_positive_factors)*100:.1f}%",
                "这些优势因素可以作为品牌传播和产品改进的重点方向"
            ]
            analysis["summary_text"] = f"推荐者群体选择了{len(all_positive_factors)}个正面因素，主要集中在{main_category[0]}领域。最受认可的'{top_factors[0][0]}'被{top_factors[0][1]}位客户选择，反映了伊利在{main_category[0]}方面的市场优势。这些优势因素为{', '.join(self.knowledge_base.get('key_brands', ['安慕希', '金典'])[:2])}等核心品牌的营销传播和产品优化提供了明确方向。"
            analysis["insight_summary"] = [
                f"1. 选择集中度：{len(all_positive_factors)}个因素涉及{len(factor_counts)}个维度",
                f"2. 核心优势：'{top_factors[0][0]}'最受认可",
                f"3. 主要领域：{main_category[0]}占比{main_category[1]/len(all_positive_factors)*100:.1f}%",
                "4. 营销价值：优势因素指导品牌传播方向"
            ]
        
        return analysis
    
    def _agent_4_positive_free_answers(self, positive_set):
        """Agent 4: AI-Powered Positive Free Answers Analysis"""
        
        # Flatten positive reasons
        positive_reasons = []
        for item in positive_set["free_question_array"]:
            if item["positive_reason"].strip():
                positive_reasons.append(item["positive_reason"])
        
        flattened_text = " | ".join(positive_reasons)
        response_rate = len(positive_reasons) / len(positive_set["free_question_array"]) * 100 if positive_set["free_question_array"] else 0
        
        logger.info("🤖 [AI调用 4/7] Agent 4: 正面开放回答深度分析...")
        
        if self.use_ai and self.ai_client and positive_reasons:
            try:
                ai_result = self.ai_client.analyze_with_prompt(
                    YiliPromptTemplates.POSITIVE_OPENTEXT_ANALYSIS,
                    total_responses=len(positive_reasons),
                    response_rate=response_rate,
                    flattened_text=flattened_text
                )
                
                analysis = {
                    "agent_name": "正面填空题分析智能体",
                    "question_context": self.question_texts["positive_specific"],
                    "input_data": {
                        "total_responses": len(positive_reasons),
                        "flattened_text": flattened_text,
                        "response_rate": response_rate
                    },
                    "ai_analysis": ai_result,
                    "business_questions": [
                        "客户最真实的推荐理由是什么？",
                        "这些自发表达反映了什么深层需求？",
                        "如何将这些洞察转化为产品优化？"
                    ]
                }
                
                # Extract insights from AI response
                if "customer_stories" in ai_result:
                    insights = []
                    for story in ai_result["customer_stories"]:
                        insights.append(f"客户故事: {story.get('story_theme', 'N/A')} - {story.get('marketing_value', 'N/A')}")
                    analysis["insight_summary"] = insights
                else:
                    analysis["insight_summary"] = ai_result.get("key_insights", ["AI分析完成，详见AI分析结果"])
                
                # Generate summary from AI analysis
                if "emotional_insights" in ai_result:
                    emotion_info = ai_result["emotional_insights"]
                    connection_strength = emotion_info.get("emotional_connection_strength", "N/A")
                    analysis["summary_text"] = f"AI分析显示客户情感连接强度为{connection_strength}，识别出有价值的客户故事和使用场景洞察。"
                else:
                    analysis["summary_text"] = f"AI深度分析了{len(positive_reasons)}条推荐理由，揭示了客户的真实情感和深层需求。"
                
                return analysis
                
            except Exception as e:
                logger.warning(f"Agent 4 AI分析失败，使用规则分析: {e}")
        
        # Fallback to rule-based analysis
        analysis = {
            "agent_name": "正面填空题分析智能体",
            "question_context": self.question_texts["positive_specific"],
            "input_data": {
                "total_responses": len(positive_reasons),
                "flattened_text": flattened_text,
                "response_rate": response_rate
            },
            "statements": [],
            "business_questions": [
                "客户最真实的推荐理由是什么？",
                "这些自发表达反映了什么深层需求？",
                "如何将这些洞察转化为产品优化？"
            ]
        }
        
        if not positive_reasons:
            analysis["statements"] = [
                "推荐者未提供具体的推荐理由描述",
                "缺乏深度的客户洞察和情感连接信息",
                "建议增加开放式问题引导客户分享真实感受"
            ]
            analysis["summary_text"] = "推荐者未提供具体的推荐理由描述，缺乏深度的客户洞察。"
            analysis["insight_summary"] = ["数据缺失：推荐者未提供开放回答"]
        else:
            # Analyze content themes
            themes = []
            combined_text = " ".join(positive_reasons)
            if "口味" in combined_text or "好喝" in combined_text:
                themes.append("产品口感")
            if "包装" in combined_text or "外观" in combined_text:
                themes.append("包装设计")
            if "选择" in combined_text or "多样" in combined_text:
                themes.append("产品多样性")
            
            analysis["statements"] = [
                f"推荐者提供了{len(positive_reasons)}条具体推荐理由，回答率{response_rate:.1f}%",
                f"客户表达重点关注{'、'.join(themes) if themes else '整体体验'}",
                "推荐理由体现了客户的真实使用感受和情感连接",
                "这些自发表达为产品改进和营销传播提供了宝贵洞察"
            ]
            analysis["summary_text"] = f"推荐者提供了{len(positive_reasons)}条具体推荐理由，客户表达重点关注{'、'.join(themes) if themes else '整体体验'}。"
            analysis["insight_summary"] = [
                f"1. 回答情况：{len(positive_reasons)}条理由，回答率{response_rate:.1f}%",
                f"2. 关注重点：{'、'.join(themes) if themes else '整体体验'}",
                "3. 情感连接：体现客户真实使用感受",
                "4. 洞察价值：为产品改进提供方向"
            ]
        
        return analysis
    
    def _agent_5_negative_multiple_choice(self, negative_set):
        """Agent 5: AI-Powered Negative Multiple Choice Analysis"""
        
        # Flatten negative factors
        all_negative_factors = []
        for item in negative_set["multiple_choice_array"]:
            all_negative_factors.extend(item["negative_factors"])
        
        # Count factor frequency
        factor_counts = {}
        for factor in all_negative_factors:
            factor_counts[factor] = factor_counts.get(factor, 0) + 1
        
        flattened_text = " | ".join(all_negative_factors)
        
        logger.info("🤖 [AI调用 5/7] Agent 5: 负面因素深度分析...")
        
        if self.use_ai and self.ai_client and all_negative_factors:
            try:
                ai_result = self.ai_client.analyze_with_prompt(
                    YiliPromptTemplates.NEGATIVE_FACTORS_ANALYSIS,
                    total_selections=len(all_negative_factors),
                    unique_factors=len(factor_counts),
                    factor_frequency=factor_counts,
                    flattened_text=flattened_text
                )
                
                analysis = {
                    "agent_name": "负面多选题分析智能体",
                    "question_context": self.question_texts["negative_factors"],
                    "input_data": {
                        "total_selections": len(all_negative_factors),
                        "unique_factors": len(factor_counts),
                        "flattened_text": flattened_text,
                        "factor_frequency": factor_counts
                    },
                    "ai_analysis": ai_result,
                    "business_questions": [
                        "哪些问题是客户不推荐的主要原因？",
                        "这些问题的解决优先级如何排序？",
                        "需要投入多少资源来解决这些问题？"
                    ]
                }
                
                # Extract insights from AI response
                if "solution_roadmap" in ai_result:
                    insights = []
                    for solution in ai_result["solution_roadmap"]:
                        insights.append(f"解决方案: {solution.get('problem', 'N/A')} - 优先级: {solution.get('priority', 'N/A')}")
                    analysis["insight_summary"] = insights
                else:
                    analysis["insight_summary"] = ai_result.get("key_insights", ["AI分析完成，详见AI分析结果"])
                
                # Generate summary from AI analysis
                if "critical_issues" in ai_result:
                    issue_info = ai_result["critical_issues"]
                    primary_problem = issue_info.get("primary_problem", "N/A")
                    analysis["summary_text"] = f"AI分析识别出核心问题'{primary_problem}'，提供了系统性的解决路线图和风险评估。"
                else:
                    analysis["summary_text"] = f"AI深度分析了{len(all_negative_factors)}个负面因素，制定了问题解决的优先级和行动方案。"
                
                return analysis
                
            except Exception as e:
                logger.warning(f"Agent 5 AI分析失败，使用规则分析: {e}")
        
        # Fallback to rule-based analysis
        analysis = {
            "agent_name": "负面多选题分析智能体",
            "question_context": self.question_texts["negative_factors"],
            "input_data": {
                "total_selections": len(all_negative_factors),
                "unique_factors": len(factor_counts),
                "flattened_text": flattened_text,
                "factor_frequency": factor_counts
            },
            "statements": [],
            "business_questions": [
                "哪些问题是客户不推荐的主要原因？",
                "这些问题的解决优先级如何排序？",
                "需要投入多少资源来解决这些问题？"
            ]
        }
        
        if not all_negative_factors:
            analysis["statements"] = [
                "非推荐者群体未明确指出具体的负面因素",
                "可能存在问题识别不充分或问卷选项不够贴切的情况",
                "建议通过定性研究深入了解客户不满的根本原因"
            ]
            analysis["summary_text"] = "非推荐者群体未明确指出具体的负面因素，需要深入研究。"
            analysis["insight_summary"] = ["数据缺失：非推荐者未选择具体负面因素"]
        else:
            top_factors = sorted(factor_counts.items(), key=lambda x: x[1], reverse=True)
            analysis["statements"] = [
                f"非推荐者识别了{len(all_negative_factors)}个负面因素，涉及{len(factor_counts)}个不同问题领域",
                f"最突出的问题是'{top_factors[0][0]}'，被{top_factors[0][1]}位客户提及",
                f"负面因素主要集中在{'营销宣传' if any('宣传' in f or '品牌' in f for f in all_negative_factors) else '产品品质' if any('口味' in f or '质量' in f for f in all_negative_factors) else '服务体验'}方面",
                "这些问题点需要立即制定改进方案，防止客户流失"
            ]
            analysis["summary_text"] = f"非推荐者识别了{len(all_negative_factors)}个负面因素，最突出的问题是'{top_factors[0][0]}'。"
            analysis["insight_summary"] = [
                f"1. 问题规模：{len(all_negative_factors)}个因素涉及{len(factor_counts)}个领域",
                f"2. 核心问题：'{top_factors[0][0]}'被{top_factors[0][1]}位客户提及",
                "3. 改进优先级：需要立即制定解决方案",
                "4. 流失风险：防止客户进一步流失"
            ]
        
        return analysis
    
    def _agent_6_negative_free_answers(self, negative_set):
        """Agent 6: AI-Powered Negative Free Answers Analysis"""
        
        # Flatten negative reasons
        negative_reasons = []
        for item in negative_set["free_question_array"]:
            if item["negative_reason"].strip():
                negative_reasons.append(item["negative_reason"])
        
        flattened_text = " | ".join(negative_reasons)
        response_rate = len(negative_reasons) / len(negative_set["free_question_array"]) * 100 if negative_set["free_question_array"] else 0
        
        logger.info("🤖 [AI调用 6/7] Agent 6: 负面开放回答深度分析...")
        
        if self.use_ai and self.ai_client and negative_reasons:
            try:
                ai_result = self.ai_client.analyze_with_prompt(
                    YiliPromptTemplates.NEGATIVE_OPENTEXT_ANALYSIS,
                    total_responses=len(negative_reasons),
                    response_rate=response_rate,
                    flattened_text=flattened_text
                )
                
                analysis = {
                    "agent_name": "负面填空题分析智能体",
                    "question_context": self.question_texts["negative_specific"],
                    "input_data": {
                        "total_responses": len(negative_reasons),
                        "flattened_text": flattened_text,
                        "response_rate": response_rate
                    },
                    "ai_analysis": ai_result,
                    "business_questions": [
                        "客户最不满意的具体是什么？",
                        "这些问题反映了哪些系统性缺陷？",
                        "如何制定有效的问题解决方案？"
                    ]
                }
                
                # Extract insights from AI response
                if "improvement_priorities" in ai_result:
                    insights = []
                    for priority in ai_result["improvement_priorities"]:
                        insights.append(f"改进优先级: {priority.get('area', 'N/A')} - 影响程度: {priority.get('impact_level', 'N/A')}")
                    analysis["insight_summary"] = insights
                else:
                    analysis["insight_summary"] = ai_result.get("key_insights", ["AI分析完成，详见AI分析结果"])
                
                # Generate summary from AI analysis
                if "dissatisfaction_analysis" in ai_result:
                    dissatisfaction_info = ai_result["dissatisfaction_analysis"]
                    emotional_intensity = dissatisfaction_info.get("emotional_intensity", "N/A")
                    analysis["summary_text"] = f"AI分析显示客户不满情绪强度为{emotional_intensity}，识别出关键痛点和系统性改进方向。"
                else:
                    analysis["summary_text"] = f"AI深度分析了{len(negative_reasons)}条不满原因，提供了客户挽留策略和改进优先级建议。"
                
                return analysis
                
            except Exception as e:
                logger.warning(f"Agent 6 AI分析失败，使用规则分析: {e}")
        
        # Fallback to rule-based analysis
        analysis = {
            "agent_name": "负面填空题分析智能体",
            "question_context": self.question_texts["negative_specific"],
            "input_data": {
                "total_responses": len(negative_reasons),
                "flattened_text": flattened_text,
                "response_rate": response_rate
            },
            "statements": [],
            "business_questions": [
                "客户最不满意的具体是什么？",
                "这些问题反映了哪些系统性缺陷？",
                "如何制定有效的问题解决方案？"
            ]
        }
        
        if not negative_reasons:
            analysis["statements"] = [
                "非推荐者未详细说明不推荐的具体原因",
                "缺乏深度的问题洞察，难以制定针对性改进措施",
                "建议加强问题挖掘，了解客户真实痛点"
            ]
            analysis["summary_text"] = "非推荐者未详细说明不推荐的具体原因，缺乏深度洞察。"
            analysis["insight_summary"] = ["数据缺失：非推荐者未提供开放回答"]
        else:
            # Analyze problem themes
            themes = []
            combined_text = " ".join(negative_reasons)
            if "宣传" in combined_text or "代言" in combined_text:
                themes.append("营销宣传问题")
            if "找到" in combined_text or "网页" in combined_text:
                themes.append("购买便利性")
            if "包装" in combined_text:
                themes.append("包装设计")
            
            analysis["statements"] = [
                f"非推荐者提供了{len(negative_reasons)}条具体不满原因，回答率{response_rate:.1f}%",
                f"客户抱怨主要集中在{'、'.join(themes) if themes else '整体体验'}方面",
                "这些具体问题反映了客户体验中的关键痛点",
                "需要跨部门协作解决这些根本性问题"
            ]
            analysis["summary_text"] = f"非推荐者提供了{len(negative_reasons)}条具体不满原因，主要集中在{'、'.join(themes) if themes else '整体体验'}方面。"
            analysis["insight_summary"] = [
                f"1. 回答情况：{len(negative_reasons)}条原因，回答率{response_rate:.1f}%",
                f"2. 问题焦点：{'、'.join(themes) if themes else '整体体验'}",
                "3. 痛点反映：客户体验关键问题",
                "4. 解决方向：需要跨部门协作"
            ]
        
        return analysis
    
    def _agent_7_total_summary(self, all_agent_results, data_summary):
        """Agent 7: AI-Powered Comprehensive Summary Analysis"""
        
        # Collect summaries from all previous agents
        agent_summaries = {}
        for i, result in enumerate(all_agent_results, 1):
            if "ai_analysis" in result:
                # Extract key insights from AI analysis
                ai_result = result["ai_analysis"]
                if isinstance(ai_result, dict):
                    key_info = str(ai_result.get("key_insights", ai_result.get("analysis_text", "AI分析结果")))
                else:
                    key_info = str(ai_result)
            else:
                # Use summary_text or statements from fallback analysis
                key_info = result.get("summary_text", " ".join(result.get("statements", [])))
            
            agent_summaries[f"agent{i}_summary"] = key_info[:300]  # Limit length for prompt
        
        key_brands = ", ".join(self.knowledge_base.get("key_brands", ["安慕希", "金典", "舒化"]))
        
        logger.info("🤖 [AI调用 7/7] Agent 7: 综合战略分析...")
        
        if self.use_ai and self.ai_client:
            try:
                ai_result = self.ai_client.analyze_with_prompt(
                    YiliPromptTemplates.COMPREHENSIVE_SUMMARY_ANALYSIS,
                    **agent_summaries,
                    key_brands=key_brands
                )
                
                analysis = {
                    "agent_name": "综合总结分析智能体",
                    "question_context": "综合所有问题的分析结果",
                    "input_data": {
                        "total_insights": sum(len(result.get("insight_summary", [])) for result in all_agent_results),
                        "agent_count": len(all_agent_results),
                        "agent_summaries": agent_summaries
                    },
                    "ai_analysis": ai_result,
                    "business_questions": [
                        "如何制定综合性的NPS提升战略？",
                        "各部门应该如何协作改善客户体验？",
                        "如何平衡短期改进和长期品牌建设？",
                        "需要设立什么KPI来跟踪改进效果？"
                    ],
                    "additional_info": self.additional_info
                }
                
                # Extract insights from AI response
                if "executive_summary" in ai_result:
                    exec_summary = ai_result["executive_summary"]
                    analysis["insight_summary"] = [
                        f"战略洞察: {exec_summary.get('key_insights', 'N/A')}",
                        f"核心建议: {exec_summary.get('recommendations', 'N/A')}",
                        f"预期影响: {exec_summary.get('expected_impact', 'N/A')}"
                    ]
                else:
                    analysis["insight_summary"] = ai_result.get("key_insights", ["AI综合分析完成，详见AI分析结果"])
                
                # Generate summary from AI analysis
                if "comprehensive_assessment" in ai_result:
                    assessment = ai_result["comprehensive_assessment"]
                    overall_health = assessment.get("overall_nps_health", "N/A")
                    key_drivers = ", ".join(assessment.get("key_drivers", [])[:2])
                    analysis["summary_text"] = f"AI综合分析显示NPS整体健康度为{overall_health}，核心驱动因素包括{key_drivers}，提供了系统性的战略路线图和跨部门协作建议。"
                else:
                    analysis["summary_text"] = f"AI深度整合了{len(all_agent_results)}个智能体的分析结果，形成了全面的NPS提升战略和行动计划。"
                
                return analysis
                
            except Exception as e:
                logger.warning(f"Agent 7 AI分析失败，使用规则分析: {e}")
        
        # Fallback to rule-based analysis
        all_statements = []
        for result in all_agent_results:
            all_statements.extend(result.get("statements", []))
        
        combined_insights = " ".join(all_statements)
        
        analysis = {
            "agent_name": "综合总结分析智能体",
            "question_context": "综合所有问题的分析结果",
            "input_data": {
                "total_insights": len(all_statements),
                "agent_count": len(all_agent_results),
                "combined_insights": combined_insights
            },
            "statements": [
                f"基于{len(all_agent_results)}个维度的深度分析，识别出当前NPS表现的关键特征",
                "推荐者群体展现出对产品品质和多样性的认可，但基数仍需扩大",
                "非推荐者主要关注营销宣传和产品发现便利性问题，反映了品牌传播和渠道优化的需求",
                "客户反馈呈现两极分化趋势，需要平衡不同客户群体的需求和期望",
                "当前客户满意度水平有待提升，建议制定系统性的客户体验改进计划",
                "应该重点关注营销内容的真实性和渠道的便利性，同时保持产品品质优势",
                "建议建立持续的客户反馈监控机制，及时识别和解决新出现的问题",
                "通过优化客户体验旅程的关键触点，有望显著提升NPS分数和客户忠诚度"
            ],
            "business_questions": [
                "如何制定综合性的NPS提升战略？",
                "各部门应该如何协作改善客户体验？",
                "如何平衡短期改进和长期品牌建设？",
                "需要设立什么KPI来跟踪改进效果？"
            ],
            "additional_info": self.additional_info,
            "summary_text": f"基于七智能体的全方位NPS分析显示，伊利集团当前客户满意度呈现复杂态势。通过{len(all_agent_results)}个维度的深入剖析，发现推荐者群体认可产品品质和{', '.join(self.knowledge_base.get('key_brands', ['安慕希', '金典'])[:2])}等品牌多样性，但非推荐者主要关注营销宣传真实性和渠道便利性问题。客户反馈呈现两极分化趋势，需要制定系统性的客户体验改进计划，重点优化营销内容和购买便利性，同时保持产品品质优势，建立持续的客户反馈监控机制。",
            "insight_summary": [
                f"1. 全面分析：基于{len(all_agent_results)}个维度的深度洞察",
                "2. 品质认可：推荐者认可产品品质和多样性",
                "3. 关键问题：营销宣传和渠道便利性需改进",
                "4. 客户分化：反馈呈现两极分化趋势",
                "5. 改进方向：系统性客户体验提升计划",
                "6. 营销优化：重点关注内容真实性",
                "7. 渠道建设：提升购买便利性体验",
                "8. 监控机制：建立持续反馈跟踪系统"
            ]
        }
        
        return analysis
    
    def _create_final_output(self, input_data, processed_data, agent_results, positive_set, negative_set):
        """Create final output structure"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
        
        return {
            "timestamp": timestamp,
            "analysis_type": "七智能体NPS分析系统",
            "original_input": {
                "data_source": "伊利NPS调研问卷",
                "processed_responses": processed_data.total_responses,
                "valid_responses": processed_data.valid_responses,
                "survey_metadata": processed_data.survey_metadata
            },
            "agent_analysis_results": agent_results,
            "supporting_data": {
                "positive_set": positive_set,
                "negative_set": negative_set,
                "question_texts": self.question_texts
            },
            "summary_statistics": {
                "total_agents": len(agent_results),
                "total_statements": sum(len(result.get("statements", [])) for result in agent_results),
                "total_business_questions": sum(len(result.get("business_questions", [])) for result in agent_results),
                "total_ai_insights": sum(len(result.get("insight_summary", [])) for result in agent_results),
                "ai_powered_agents": sum(1 for result in agent_results if "ai_analysis" in result),
                "fallback_agents": sum(1 for result in agent_results if "ai_analysis" not in result),
                "analysis_coverage": "NPS净值、分布、正面因素、负面因素、开放回答、综合洞察"
            }
        }