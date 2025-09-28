"""
题组分析智能体
负责分析推荐/不推荐题组的选择题和自由题，提取关键主题和模式
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
from collections import Counter, defaultdict
import asyncio
import re

# 导入相关数据结构
from ..nps_calculator import QuestionGroupClassification, QuestionGroupType
from ..input_data_processor import ProcessedSurveyData, ProcessedResponseData

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass 
class QuestionGroupInsight:
    """题组洞察结果"""
    question_type: str  # "choice" or "open_ended"
    group_type: str     # "promoter" or "detractor" 
    total_responses: int
    key_themes: List[Dict[str, Any]]
    sentiment_analysis: Dict[str, Any]
    frequency_analysis: Dict[str, Any]
    correlation_patterns: List[Dict[str, Any]]
    actionable_insights: List[str]
    confidence_score: float

@dataclass
class QuestionGroupAnalysisResult:
    """题组分析完整结果"""
    promoter_choice_insights: QuestionGroupInsight
    promoter_open_insights: QuestionGroupInsight
    detractor_choice_insights: QuestionGroupInsight
    detractor_open_insights: QuestionGroupInsight
    cross_group_comparison: Dict[str, Any]
    priority_actions: List[Dict[str, Any]]
    analysis_metadata: Dict[str, Any]

class QuestionGroupAgent:
    """题组分析智能体"""
    
    def __init__(self):
        """初始化题组分析智能体"""
        
        # 预定义关键词映射
        self.positive_keywords = {
            "产品质量": ["质量好", "品质", "新鲜", "口感", "味道", "香甜", "醇厚", "浓郁"],
            "品牌信任": ["品牌", "伊利", "信任", "放心", "安全", "可靠", "知名"],
            "营养价值": ["营养", "健康", "蛋白质", "维生素", "益生菌", "钙", "有机"],
            "包装设计": ["包装", "外观", "设计", "颜值", "方便", "便携"],
            "性价比": ["价格", "实惠", "划算", "性价比", "优惠", "便宜"],
            "购买便利": ["方便", "容易买", "随处可见", "渠道", "超市", "网购"]
        }
        
        self.negative_keywords = {
            "产品质量": ["质量差", "变质", "过期", "口感差", "味道怪", "太甜", "太酸", "稀薄"],
            "价格问题": ["太贵", "涨价", "价格高", "不值", "性价比低"],
            "包装问题": ["包装差", "漏液", "不便", "设计丑", "包装破损"],
            "购买困难": ["买不到", "断货", "渠道少", "不方便"],
            "健康担忧": ["添加剂", "防腐剂", "不健康", "糖分高", "脂肪多"],
            "服务问题": ["服务差", "态度不好", "售后差", "配送慢"]
        }
        
        # 情感强度词汇
        self.intensity_modifiers = {
            "极强": ["非常", "极其", "特别", "超级", "太", "很", "超"],
            "中等": ["比较", "还", "挺", "蛮", "相对"],
            "轻微": ["有点", "稍微", "略", "一般", "还行"]
        }
        
        logger.info("题组分析智能体初始化完成")
    
    async def analyze_question_groups(self, 
                                    processed_survey_data: ProcessedSurveyData,
                                    question_group_classification: QuestionGroupClassification) -> QuestionGroupAnalysisResult:
        """
        分析题组主入口函数
        
        Args:
            processed_survey_data: 处理后的调研数据
            question_group_classification: 题组分类结果
            
        Returns:
            QuestionGroupAnalysisResult: 完整分析结果
        """
        logger.info("开始题组分析")
        
        try:
            # 1. 分别分析推荐组和批评组的选择题
            promoter_choice_insights = await self._analyze_choice_questions(
                processed_survey_data, "promoter"
            )
            
            detractor_choice_insights = await self._analyze_choice_questions(
                processed_survey_data, "detractor"
            )
            
            # 2. 分别分析推荐组和批评组的开放题
            promoter_open_insights = await self._analyze_open_questions(
                processed_survey_data, "promoter"
            )
            
            detractor_open_insights = await self._analyze_open_questions(
                processed_survey_data, "detractor"
            )
            
            # 3. 跨组对比分析
            cross_group_comparison = await self._compare_across_groups(
                promoter_choice_insights, promoter_open_insights,
                detractor_choice_insights, detractor_open_insights
            )
            
            # 4. 生成优先行动建议
            priority_actions = await self._generate_priority_actions(
                promoter_choice_insights, promoter_open_insights,
                detractor_choice_insights, detractor_open_insights,
                cross_group_comparison
            )
            
            # 5. 构建分析结果
            result = QuestionGroupAnalysisResult(
                promoter_choice_insights=promoter_choice_insights,
                promoter_open_insights=promoter_open_insights,
                detractor_choice_insights=detractor_choice_insights,
                detractor_open_insights=detractor_open_insights,
                cross_group_comparison=cross_group_comparison,
                priority_actions=priority_actions,
                analysis_metadata={
                    "analysis_timestamp": datetime.now().isoformat(),
                    "agent_version": "question_group_v2.0",
                    "total_responses_analyzed": len(processed_survey_data.response_data),
                    "analysis_depth": "comprehensive"
                }
            )
            
            logger.info("题组分析完成")
            return result
            
        except Exception as e:
            logger.error(f"题组分析失败: {e}")
            raise
    
    async def _analyze_choice_questions(self, 
                                      survey_data: ProcessedSurveyData, 
                                      group_type: str) -> QuestionGroupInsight:
        """分析选择题"""
        
        # 根据NPS分数筛选对应群体
        if group_type == "promoter":
            target_responses = [r for r in survey_data.response_data if r.nps_score.value >= 9]
        else:  # detractor
            target_responses = [r for r in survey_data.response_data if r.nps_score.value <= 6]
        
        if not target_responses:
            return self._create_empty_insight("choice", group_type)
        
        # 收集选择题回答
        choice_responses = []
        for response in target_responses:
            if hasattr(response, 'choice_responses') and response.choice_responses:
                choice_responses.extend(response.choice_responses.values())
        
        # 频次分析
        frequency_analysis = self._analyze_choice_frequency(choice_responses)
        
        # 主题提取
        key_themes = self._extract_choice_themes(choice_responses, group_type)
        
        # 情感分析（对选择题选项进行情感倾向分析）
        sentiment_analysis = self._analyze_choice_sentiment(choice_responses, group_type)
        
        # 关联模式分析
        correlation_patterns = self._find_choice_correlations(target_responses)
        
        # 生成洞察
        actionable_insights = self._generate_choice_insights(
            frequency_analysis, key_themes, sentiment_analysis, group_type
        )
        
        # 计算置信度
        confidence_score = self._calculate_choice_confidence(choice_responses, target_responses)
        
        return QuestionGroupInsight(
            question_type="choice",
            group_type=group_type,
            total_responses=len(target_responses),
            key_themes=key_themes,
            sentiment_analysis=sentiment_analysis,
            frequency_analysis=frequency_analysis,
            correlation_patterns=correlation_patterns,
            actionable_insights=actionable_insights,
            confidence_score=confidence_score
        )
    
    async def _analyze_open_questions(self, 
                                    survey_data: ProcessedSurveyData,
                                    group_type: str) -> QuestionGroupInsight:
        """分析开放题"""
        
        # 根据NPS分数筛选对应群体
        if group_type == "promoter":
            target_responses = [r for r in survey_data.response_data if r.nps_score.value >= 9]
        else:  # detractor
            target_responses = [r for r in survey_data.response_data if r.nps_score.value <= 6]
        
        if not target_responses:
            return self._create_empty_insight("open_ended", group_type)
        
        # 收集开放题回答
        open_responses = []
        for response in target_responses:
            if hasattr(response, 'open_responses') and response.open_responses:
                # 将所有开放题回答合并
                for question, answer in response.open_responses.items():
                    if answer and answer.strip():
                        open_responses.append({
                            'question': question,
                            'answer': answer.strip(),
                            'response_id': response.response_metadata.response_id
                        })
        
        # 文本主题提取
        key_themes = await self._extract_text_themes(open_responses, group_type)
        
        # 情感分析
        sentiment_analysis = await self._analyze_text_sentiment(open_responses, group_type)
        
        # 频次分析
        frequency_analysis = self._analyze_text_frequency(open_responses)
        
        # 关联模式分析
        correlation_patterns = await self._find_text_correlations(open_responses, target_responses)
        
        # 生成洞察
        actionable_insights = self._generate_text_insights(
            key_themes, sentiment_analysis, frequency_analysis, group_type
        )
        
        # 计算置信度
        confidence_score = self._calculate_text_confidence(open_responses, target_responses)
        
        return QuestionGroupInsight(
            question_type="open_ended",
            group_type=group_type,
            total_responses=len(target_responses),
            key_themes=key_themes,
            sentiment_analysis=sentiment_analysis,
            frequency_analysis=frequency_analysis,
            correlation_patterns=correlation_patterns,
            actionable_insights=actionable_insights,
            confidence_score=confidence_score
        )
    
    def _analyze_choice_frequency(self, choice_responses: List[str]) -> Dict[str, Any]:
        """分析选择题频次"""
        
        if not choice_responses:
            return {"top_choices": [], "distribution": {}, "total_count": 0}
        
        # 统计选项频次
        choice_counter = Counter(choice_responses)
        total_count = len(choice_responses)
        
        # 计算分布
        distribution = {}
        for choice, count in choice_counter.items():
            distribution[choice] = {
                "count": count,
                "percentage": (count / total_count) * 100
            }
        
        # 获取前5个最frequent选项
        top_choices = [
            {
                "choice": choice,
                "count": count,
                "percentage": (count / total_count) * 100
            }
            for choice, count in choice_counter.most_common(5)
        ]
        
        return {
            "top_choices": top_choices,
            "distribution": distribution,
            "total_count": total_count,
            "unique_choices": len(choice_counter)
        }
    
    def _extract_choice_themes(self, choice_responses: List[str], group_type: str) -> List[Dict[str, Any]]:
        """提取选择题主题"""
        
        themes = []
        keyword_dict = self.positive_keywords if group_type == "promoter" else self.negative_keywords
        
        # 统计每个主题类别的提及次数
        theme_counts = defaultdict(int)
        theme_examples = defaultdict(list)
        
        for response in choice_responses:
            response_lower = response.lower()
            for theme, keywords in keyword_dict.items():
                for keyword in keywords:
                    if keyword in response_lower:
                        theme_counts[theme] += 1
                        if response not in theme_examples[theme]:
                            theme_examples[theme].append(response)
                        break  # 避免重复计数
        
        # 构建主题结果
        total_responses = len(choice_responses)
        for theme, count in sorted(theme_counts.items(), key=lambda x: x[1], reverse=True):
            themes.append({
                "theme": theme,
                "mention_count": count,
                "percentage": (count / total_responses) * 100,
                "examples": theme_examples[theme][:3],  # 最多3个例子
                "importance": "high" if count >= total_responses * 0.3 else 
                             "medium" if count >= total_responses * 0.1 else "low"
            })
        
        return themes[:10]  # 返回最重要的10个主题
    
    def _analyze_choice_sentiment(self, choice_responses: List[str], group_type: str) -> Dict[str, Any]:
        """分析选择题情感倾向"""
        
        sentiment_scores = []
        intensity_distribution = {"极强": 0, "中等": 0, "轻微": 0, "中性": 0}
        
        for response in choice_responses:
            response_lower = response.lower()
            
            # 计算情感强度
            intensity = "中性"
            for level, modifiers in self.intensity_modifiers.items():
                if any(modifier in response_lower for modifier in modifiers):
                    intensity = level
                    break
            
            intensity_distribution[intensity] += 1
            
            # 基础情感得分（推荐组为正，批评组为负）
            base_score = 1.0 if group_type == "promoter" else -1.0
            
            # 根据强度调整得分
            if intensity == "极强":
                score = base_score * 1.5
            elif intensity == "中等":
                score = base_score * 1.0
            elif intensity == "轻微":
                score = base_score * 0.5
            else:
                score = 0.0
            
            sentiment_scores.append(score)
        
        # 计算平均情感得分
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        return {
            "average_sentiment": avg_sentiment,
            "sentiment_distribution": {
                "positive": len([s for s in sentiment_scores if s > 0]),
                "neutral": len([s for s in sentiment_scores if s == 0]),
                "negative": len([s for s in sentiment_scores if s < 0])
            },
            "intensity_distribution": intensity_distribution,
            "emotional_strength": "strong" if abs(avg_sentiment) >= 1.0 else 
                                "moderate" if abs(avg_sentiment) >= 0.5 else "weak"
        }
    
    def _find_choice_correlations(self, target_responses: List[ProcessedResponseData]) -> List[Dict[str, Any]]:
        """查找选择题关联模式"""
        
        correlations = []
        
        # 寻找选择题之间的关联
        choice_combinations = defaultdict(int)
        
        for response in target_responses:
            if hasattr(response, 'choice_responses') and response.choice_responses:
                choices = list(response.choice_responses.values())
                # 分析两两组合
                for i in range(len(choices)):
                    for j in range(i+1, len(choices)):
                        combination = tuple(sorted([choices[i], choices[j]]))
                        choice_combinations[combination] += 1
        
        # 筛选出现频次较高的组合
        total_responses = len(target_responses)
        for combination, count in choice_combinations.items():
            if count >= max(2, total_responses * 0.1):  # 至少2次或10%的响应
                correlations.append({
                    "combination": list(combination),
                    "frequency": count,
                    "percentage": (count / total_responses) * 100,
                    "correlation_strength": "strong" if count >= total_responses * 0.3 else 
                                          "medium" if count >= total_responses * 0.2 else "weak"
                })
        
        return sorted(correlations, key=lambda x: x["frequency"], reverse=True)[:5]
    
    async def _extract_text_themes(self, open_responses: List[Dict[str, Any]], group_type: str) -> List[Dict[str, Any]]:
        """提取开放题文本主题"""
        
        themes = []
        keyword_dict = self.positive_keywords if group_type == "promoter" else self.negative_keywords
        
        # 主题统计
        theme_mentions = defaultdict(int)
        theme_examples = defaultdict(list)
        theme_questions = defaultdict(set)
        
        for response_data in open_responses:
            answer = response_data['answer'].lower()
            question = response_data['question']
            
            for theme, keywords in keyword_dict.items():
                for keyword in keywords:
                    if keyword in answer:
                        theme_mentions[theme] += 1
                        theme_examples[theme].append(response_data['answer'])
                        theme_questions[theme].add(question)
                        break
        
        # 构建主题分析结果
        total_responses = len(open_responses)
        for theme, count in sorted(theme_mentions.items(), key=lambda x: x[1], reverse=True):
            themes.append({
                "theme": theme,
                "mention_count": count,
                "percentage": (count / total_responses) * 100,
                "examples": theme_examples[theme][:3],
                "related_questions": list(theme_questions[theme]),
                "sentiment": "positive" if group_type == "promoter" else "negative",
                "importance": "high" if count >= total_responses * 0.2 else 
                             "medium" if count >= total_responses * 0.1 else "low"
            })
        
        return themes[:10]
    
    async def _analyze_text_sentiment(self, open_responses: List[Dict[str, Any]], group_type: str) -> Dict[str, Any]:
        """分析开放题文本情感"""
        
        sentiment_details = []
        emotion_words = []
        
        for response_data in open_responses:
            answer = response_data['answer']
            answer_lower = answer.lower()
            
            # 提取情感词汇
            for intensity_level, modifiers in self.intensity_modifiers.items():
                for modifier in modifiers:
                    if modifier in answer_lower:
                        emotion_words.append({
                            "word": modifier,
                            "intensity": intensity_level,
                            "context": answer
                        })
            
            # 计算句子级别的情感得分
            sentence_sentiment = self._calculate_sentence_sentiment(answer, group_type)
            sentiment_details.append({
                "response_id": response_data.get('response_id'),
                "sentiment_score": sentence_sentiment,
                "text_snippet": answer[:100] + "..." if len(answer) > 100 else answer
            })
        
        # 聚合情感分析
        sentiment_scores = [item["sentiment_score"] for item in sentiment_details]
        avg_sentiment = sum(sentiment_scores) / len(sentiment_scores) if sentiment_scores else 0
        
        # 情感分布
        positive_count = len([s for s in sentiment_scores if s > 0.2])
        neutral_count = len([s for s in sentiment_scores if -0.2 <= s <= 0.2])
        negative_count = len([s for s in sentiment_scores if s < -0.2])
        
        return {
            "average_sentiment": avg_sentiment,
            "sentiment_distribution": {
                "positive": positive_count,
                "neutral": neutral_count,
                "negative": negative_count
            },
            "emotion_words": emotion_words[:10],  # 前10个情感词
            "sentiment_details": sentiment_details[:5],  # 前5个详细分析
            "overall_tone": "very_positive" if avg_sentiment > 0.5 else
                          "positive" if avg_sentiment > 0.2 else
                          "neutral" if avg_sentiment >= -0.2 else
                          "negative" if avg_sentiment >= -0.5 else "very_negative"
        }
    
    def _calculate_sentence_sentiment(self, text: str, group_type: str) -> float:
        """计算句子情感得分"""
        
        text_lower = text.lower()
        base_sentiment = 1.0 if group_type == "promoter" else -1.0
        
        # 检查强度修饰词
        intensity_multiplier = 1.0
        for level, modifiers in self.intensity_modifiers.items():
            if any(modifier in text_lower for modifier in modifiers):
                if level == "极强":
                    intensity_multiplier = 1.5
                elif level == "中等":
                    intensity_multiplier = 1.0
                elif level == "轻微":
                    intensity_multiplier = 0.5
                break
        
        # 检查否定词
        negation_words = ["不", "没", "非", "无", "别", "莫"]
        has_negation = any(neg in text_lower for neg in negation_words)
        if has_negation:
            base_sentiment *= -0.5  # 否定降低情感强度并可能反转
        
        return base_sentiment * intensity_multiplier
    
    def _analyze_text_frequency(self, open_responses: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析开放题文本频次"""
        
        # 词频分析
        all_words = []
        for response_data in open_responses:
            # 简单的中文分词（按标点和空格分割）
            words = re.findall(r'[\u4e00-\u9fff]+', response_data['answer'])
            all_words.extend([word for word in words if len(word) >= 2])  # 过滤单字符
        
        word_counter = Counter(all_words)
        
        # 问题类型分布
        question_types = Counter([resp['question'] for resp in open_responses])
        
        return {
            "top_words": [
                {"word": word, "count": count, "percentage": (count / len(all_words)) * 100}
                for word, count in word_counter.most_common(20)
            ],
            "question_distribution": {
                question: {"count": count, "percentage": (count / len(open_responses)) * 100}
                for question, count in question_types.items()
            },
            "total_words": len(all_words),
            "unique_words": len(word_counter),
            "average_response_length": sum(len(resp['answer']) for resp in open_responses) / len(open_responses) if open_responses else 0
        }
    
    async def _find_text_correlations(self, open_responses: List[Dict[str, Any]], 
                                    target_responses: List[ProcessedResponseData]) -> List[Dict[str, Any]]:
        """查找文本关联模式"""
        
        correlations = []
        
        # 创建响应ID到文本的映射
        response_texts = {}
        for response_data in open_responses:
            response_id = response_data.get('response_id')
            if response_id:
                if response_id not in response_texts:
                    response_texts[response_id] = []
                response_texts[response_id].append(response_data['answer'])
        
        # 寻找共现的关键词
        keyword_cooccurrence = defaultdict(int)
        all_keywords = set()
        
        # 收集所有关键词
        for keyword_list in [*self.positive_keywords.values(), *self.negative_keywords.values()]:
            all_keywords.update(keyword_list)
        
        # 分析共现
        for response_id, texts in response_texts.items():
            combined_text = " ".join(texts).lower()
            found_keywords = [kw for kw in all_keywords if kw in combined_text]
            
            # 计算关键词两两共现
            for i in range(len(found_keywords)):
                for j in range(i+1, len(found_keywords)):
                    pair = tuple(sorted([found_keywords[i], found_keywords[j]]))
                    keyword_cooccurrence[pair] += 1
        
        # 构建关联结果
        total_responses = len(response_texts)
        for (kw1, kw2), count in keyword_cooccurrence.items():
            if count >= max(2, total_responses * 0.1):
                correlations.append({
                    "keywords": [kw1, kw2],
                    "cooccurrence_count": count,
                    "percentage": (count / total_responses) * 100,
                    "strength": "strong" if count >= total_responses * 0.3 else
                              "medium" if count >= total_responses * 0.2 else "weak"
                })
        
        return sorted(correlations, key=lambda x: x["cooccurrence_count"], reverse=True)[:5]
    
    def _generate_choice_insights(self, frequency_analysis: Dict[str, Any], 
                                key_themes: List[Dict[str, Any]], 
                                sentiment_analysis: Dict[str, Any],
                                group_type: str) -> List[str]:
        """生成选择题洞察"""
        
        insights = []
        
        # 基于频次的洞察
        if frequency_analysis["top_choices"]:
            top_choice = frequency_analysis["top_choices"][0]
            insights.append(
                f"{'推荐者' if group_type == 'promoter' else '批评者'}最常选择的是"{top_choice['choice']}"，"
                f"占比{top_choice['percentage']:.1f}%"
            )
        
        # 基于主题的洞察
        if key_themes:
            top_theme = key_themes[0]
            insights.append(
                f"最重要的关注点是{top_theme['theme']}，在{top_theme['percentage']:.1f}%的回答中被提及"
            )
        
        # 基于情感的洞察
        emotion_strength = sentiment_analysis.get("emotional_strength", "weak")
        if emotion_strength == "strong":
            insights.append(
                f"{'推荐者' if group_type == 'promoter' else '批评者'}的情感表达非常强烈，"
                f"显示出{'高度认同' if group_type == 'promoter' else '强烈不满'}"
            )
        
        # 分布多样性洞察
        unique_choices = frequency_analysis.get("unique_choices", 0)
        total_count = frequency_analysis.get("total_count", 0)
        if total_count > 0:
            diversity = unique_choices / total_count
            if diversity > 0.7:
                insights.append("回答多样性很高，显示关注点较为分散")
            elif diversity < 0.3:
                insights.append("回答集中度很高，显示存在共同的关注焦点")
        
        return insights
    
    def _generate_text_insights(self, key_themes: List[Dict[str, Any]],
                              sentiment_analysis: Dict[str, Any],
                              frequency_analysis: Dict[str, Any],
                              group_type: str) -> List[str]:
        """生成开放题洞察"""
        
        insights = []
        
        # 主题洞察
        if key_themes:
            high_importance_themes = [t for t in key_themes if t.get("importance") == "high"]
            if high_importance_themes:
                theme_names = [t["theme"] for t in high_importance_themes]
                insights.append(
                    f"{'推荐者' if group_type == 'promoter' else '批评者'}的核心关注点包括：{', '.join(theme_names)}"
                )
        
        # 情感强度洞察
        overall_tone = sentiment_analysis.get("overall_tone", "neutral")
        if overall_tone in ["very_positive", "very_negative"]:
            insights.append(
                f"整体情感倾向非常明确，显示{'高度满意' if 'positive' in overall_tone else '严重不满'}"
            )
        
        # 表达丰富度洞察
        avg_length = frequency_analysis.get("average_response_length", 0)
        if avg_length > 50:
            insights.append("回答普遍较为详细，显示出强烈的表达意愿")
        elif avg_length < 20:
            insights.append("回答较为简短，可能反映出有限的参与度")
        
        # 词汇使用洞察
        top_words = frequency_analysis.get("top_words", [])
        if top_words:
            most_frequent = top_words[0]["word"]
            insights.append(f"最常使用的词汇是"{most_frequent}"，反映了核心关注点")
        
        return insights
    
    def _calculate_choice_confidence(self, choice_responses: List[str], 
                                   target_responses: List[ProcessedResponseData]) -> float:
        """计算选择题分析置信度"""
        
        if not choice_responses or not target_responses:
            return 0.0
        
        # 样本量因子
        sample_factor = min(1.0, len(target_responses) / 50)  # 50个样本为满分
        
        # 回答覆盖率因子
        coverage_factor = len(choice_responses) / len(target_responses)
        
        # 多样性因子
        unique_responses = len(set(choice_responses))
        diversity_factor = min(1.0, unique_responses / max(1, len(choice_responses) * 0.5))
        
        # 加权平均
        confidence = (sample_factor * 0.4 + coverage_factor * 0.4 + diversity_factor * 0.2)
        
        return round(confidence, 3)
    
    def _calculate_text_confidence(self, open_responses: List[Dict[str, Any]], 
                                 target_responses: List[ProcessedResponseData]) -> float:
        """计算开放题分析置信度"""
        
        if not open_responses or not target_responses:
            return 0.0
        
        # 样本量因子
        sample_factor = min(1.0, len(target_responses) / 30)  # 30个样本为满分
        
        # 文本质量因子（基于平均长度）
        avg_length = sum(len(resp['answer']) for resp in open_responses) / len(open_responses)
        quality_factor = min(1.0, avg_length / 50)  # 50个字符为满分
        
        # 回答覆盖率因子
        coverage_factor = len(open_responses) / len(target_responses)
        
        # 加权平均
        confidence = (sample_factor * 0.4 + quality_factor * 0.3 + coverage_factor * 0.3)
        
        return round(confidence, 3)
    
    def _create_empty_insight(self, question_type: str, group_type: str) -> QuestionGroupInsight:
        """创建空的洞察结果"""
        
        return QuestionGroupInsight(
            question_type=question_type,
            group_type=group_type,
            total_responses=0,
            key_themes=[],
            sentiment_analysis={},
            frequency_analysis={},
            correlation_patterns=[],
            actionable_insights=["样本量不足，无法进行有意义的分析"],
            confidence_score=0.0
        )
    
    async def _compare_across_groups(self, promoter_choice: QuestionGroupInsight,
                                   promoter_open: QuestionGroupInsight,
                                   detractor_choice: QuestionGroupInsight,
                                   detractor_open: QuestionGroupInsight) -> Dict[str, Any]:
        """跨组对比分析"""
        
        comparison = {
            "sample_size_comparison": {
                "promoter_total": promoter_choice.total_responses,
                "detractor_total": detractor_choice.total_responses,
                "balance_ratio": (
                    min(promoter_choice.total_responses, detractor_choice.total_responses) /
                    max(promoter_choice.total_responses, detractor_choice.total_responses)
                    if max(promoter_choice.total_responses, detractor_choice.total_responses) > 0 else 0
                )
            },
            "theme_contrast": [],
            "sentiment_gap": {},
            "expression_patterns": {}
        }
        
        # 主题对比
        promoter_themes = {theme["theme"] for theme in promoter_choice.key_themes + promoter_open.key_themes}
        detractor_themes = {theme["theme"] for theme in detractor_choice.key_themes + detractor_open.key_themes}
        
        common_themes = promoter_themes.intersection(detractor_themes)
        unique_promoter = promoter_themes - detractor_themes
        unique_detractor = detractor_themes - promoter_themes
        
        comparison["theme_contrast"] = {
            "common_themes": list(common_themes),
            "promoter_unique": list(unique_promoter),
            "detractor_unique": list(unique_detractor),
            "polarization_level": "high" if len(common_themes) < 2 else "medium" if len(common_themes) < 4 else "low"
        }
        
        # 情感差距分析
        promoter_sentiment = promoter_open.sentiment_analysis.get("average_sentiment", 0)
        detractor_sentiment = detractor_open.sentiment_analysis.get("average_sentiment", 0)
        
        comparison["sentiment_gap"] = {
            "promoter_sentiment": promoter_sentiment,
            "detractor_sentiment": detractor_sentiment,
            "sentiment_spread": abs(promoter_sentiment - detractor_sentiment),
            "polarization": "extreme" if abs(promoter_sentiment - detractor_sentiment) > 1.5 else
                          "high" if abs(promoter_sentiment - detractor_sentiment) > 1.0 else
                          "moderate" if abs(promoter_sentiment - detractor_sentiment) > 0.5 else "low"
        }
        
        return comparison
    
    async def _generate_priority_actions(self, promoter_choice: QuestionGroupInsight,
                                       promoter_open: QuestionGroupInsight,
                                       detractor_choice: QuestionGroupInsight,
                                       detractor_open: QuestionGroupInsight,
                                       comparison: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成优先行动建议"""
        
        actions = []
        
        # 基于批评者反馈的紧急行动
        if detractor_choice.total_responses > 0 or detractor_open.total_responses > 0:
            detractor_themes = detractor_choice.key_themes + detractor_open.key_themes
            if detractor_themes:
                top_issue = detractor_themes[0]
                actions.append({
                    "priority": "urgent",
                    "category": "issue_resolution",
                    "title": f"解决{top_issue['theme']}问题",
                    "description": f"批评者中{top_issue['percentage']:.1f}%提到此问题，需要立即关注",
                    "target_group": "detractor",
                    "expected_impact": "减少客户流失，提升整体NPS"
                })
        
        # 基于推荐者反馈的优势放大
        if promoter_choice.total_responses > 0 or promoter_open.total_responses > 0:
            promoter_themes = promoter_choice.key_themes + promoter_open.key_themes
            if promoter_themes:
                top_strength = promoter_themes[0]
                actions.append({
                    "priority": "high",
                    "category": "strength_amplification",
                    "title": f"强化{top_strength['theme']}优势",
                    "description": f"推荐者中{top_strength['percentage']:.1f}%认可此优势，应进一步放大",
                    "target_group": "promoter",
                    "expected_impact": "提升客户忠诚度，增强口碑传播"
                })
        
        # 基于跨组对比的平衡行动
        if comparison["theme_contrast"]["common_themes"]:
            common_theme = comparison["theme_contrast"]["common_themes"][0]
            actions.append({
                "priority": "medium",
                "category": "balanced_improvement",
                "title": f"平衡改进{common_theme}",
                "description": "此主题同时被推荐者和批评者提及，需要细致平衡",
                "target_group": "all",
                "expected_impact": "避免改进措施产生负面影响"
            })
        
        # 基于样本平衡度的数据收集行动
        balance_ratio = comparison["sample_size_comparison"]["balance_ratio"]
        if balance_ratio < 0.5:
            actions.append({
                "priority": "low",
                "category": "data_collection",
                "title": "平衡样本收集",
                "description": "推荐者和批评者样本量不平衡，需要补充数据",
                "target_group": "research",
                "expected_impact": "提高分析准确性和可靠性"
            })
        
        return actions

# 使用示例
async def main():
    """主函数示例"""
    agent = QuestionGroupAgent()
    print("题组分析智能体初始化完成")

if __name__ == "__main__":
    asyncio.run(main())