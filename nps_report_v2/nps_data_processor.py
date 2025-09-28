"""
NPS数据处理模块
负责处理问卷数据，包括题目信息提取、打标签、NPS分布计算
"""

import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from collections import Counter, defaultdict
from enum import Enum
import numpy as np

from .input_data_processor import ProcessedSurveyData, NPSCategory

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class QuestionType(Enum):
    """问题类型枚举"""
    NPS_SCORE = "nps_score"
    FACTOR_SELECTION = "factor_selection"
    OPEN_ENDED = "open_ended"
    SPECIFIC_REASON = "specific_reason"

class SentimentCategory(Enum):
    """情感分类枚举"""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

@dataclass
class QuestionInfo:
    """题目信息"""
    question_id: str
    question_text: str
    question_type: QuestionType
    options: Optional[List[str]] = None
    
@dataclass
class ResponseTag:
    """回答标签"""
    tag_id: str
    tag_name: str
    tag_category: str
    confidence: float
    keywords: List[str]
    
@dataclass
class NPSDistribution:
    """NPS分布统计"""
    promoters: int
    passives: int
    detractors: int
    total_responses: int
    nps_score: float
    promoter_percentage: float
    passive_percentage: float
    detractor_percentage: float
    score_distribution: Dict[int, int]
    
@dataclass
class FactorAnalysis:
    """因子分析结果"""
    factor_name: str
    positive_mentions: int
    negative_mentions: int
    total_mentions: int
    sentiment_ratio: float
    related_responses: List[str]
    
@dataclass
class QuestionAnalysis:
    """题目分析结果"""
    question_info: QuestionInfo
    response_count: int
    response_rate: float
    factor_analysis: Optional[List[FactorAnalysis]] = None
    common_themes: Optional[List[str]] = None
    sentiment_distribution: Optional[Dict[str, int]] = None
    
@dataclass
class ProcessedNPSData:
    """处理后的NPS数据"""
    survey_metadata: Dict[str, Any]
    question_analysis: List[QuestionAnalysis]
    nps_distribution: NPSDistribution
    response_tags: List[ResponseTag]
    quality_metrics: Dict[str, Any]
    processing_timestamp: str

class NPSDataProcessor:
    """NPS数据处理器"""
    
    def __init__(self):
        self.factor_keywords = self._load_factor_keywords()
        self.business_rules = self._load_business_rules()
        
    def _load_factor_keywords(self) -> Dict[str, List[str]]:
        """加载因子关键词映射"""
        return {
            "品牌宣传": ["品牌", "代言人", "宣传", "综艺", "广告", "营销"],
            "包装设计": ["包装", "设计", "外观", "材质", "便携", "打开"],
            "价格性价比": ["价格", "性价比", "便宜", "贵", "物有所值"],
            "促销活动": ["促销", "活动", "赠品", "优惠", "折扣"],
            "口味口感": ["口味", "口感", "味道", "好喝", "难喝"],
            "产品品质": ["品质", "质量", "变质", "异物", "新鲜"],
            "健康功能": ["健康", "功能", "营养", "消化", "免疫"],
            "服务体验": ["服务", "配送", "导购", "售后", "客服"]
        }
    
    def _load_business_rules(self) -> Dict[str, Any]:
        """加载业务规则"""
        return {
            "nps_thresholds": {
                "excellent": 50,
                "good": 20,
                "acceptable": 0,
                "poor": -20
            },
            "quality_thresholds": {
                "min_response_rate": 0.1,
                "min_completion_time": 5,  # 秒
                "max_completion_time": 3600  # 秒
            }
        }
    
    def process_nps_data(self, processed_survey: ProcessedSurveyData) -> ProcessedNPSData:
        """
        处理NPS数据的主入口函数
        
        Args:
            processed_survey: 预处理的问卷数据
            
        Returns:
            ProcessedNPSData: 处理后的NPS数据
        """
        try:
            logger.info("开始处理NPS数据...")
            
            # 1. 提取题目信息
            question_analysis = self._analyze_questions(processed_survey)
            
            # 2. 计算NPS分布
            nps_distribution = self._calculate_nps_distribution(processed_survey)
            
            # 3. 生成回答标签
            response_tags = self._generate_response_tags(processed_survey)
            
            # 4. 计算质量指标
            quality_metrics = self._calculate_quality_metrics(processed_survey)
            
            # 创建处理结果
            processed_nps_data = ProcessedNPSData(
                survey_metadata=processed_survey.survey_metadata,
                question_analysis=question_analysis,
                nps_distribution=nps_distribution,
                response_tags=response_tags,
                quality_metrics=quality_metrics,
                processing_timestamp=processed_survey.timestamp
            )
            
            logger.info("NPS数据处理完成")
            return processed_nps_data
            
        except Exception as e:
            logger.error(f"处理NPS数据时出错: {e}")
            raise
    
    def _analyze_questions(self, processed_survey: ProcessedSurveyData) -> List[QuestionAnalysis]:
        """分析问题结构和回答情况"""
        question_analysis = []
        
        try:
            survey_config = processed_survey.survey_config
            responses = processed_survey.response_data
            total_responses = len(responses)
            
            # 分析NPS问题
            nps_question = survey_config.get('nps_question', {})
            if nps_question:
                nps_analysis = self._analyze_nps_question(nps_question, responses, total_responses)
                question_analysis.append(nps_analysis)
            
            # 分析因子问题
            factor_questions = survey_config.get('factor_questions', {})
            for factor_type, factor_config in factor_questions.items():
                factor_analysis = self._analyze_factor_question(
                    factor_config, responses, total_responses, factor_type
                )
                question_analysis.append(factor_analysis)
            
            # 分析开放性问题
            open_questions = survey_config.get('open_ended_questions', [])
            for question_config in open_questions:
                open_analysis = self._analyze_open_question(
                    question_config, responses, total_responses
                )
                question_analysis.append(open_analysis)
            
            return question_analysis
            
        except Exception as e:
            logger.error(f"分析问题时出错: {e}")
            return []
    
    def _analyze_nps_question(self, nps_config: Dict, responses: List, 
                            total_responses: int) -> QuestionAnalysis:
        """分析NPS评分问题"""
        
        question_info = QuestionInfo(
            question_id=nps_config.get('question_id', 'Q1'),
            question_text=nps_config.get('question_text', ''),
            question_type=QuestionType.NPS_SCORE,
            options=[str(i) for i in range(11)]  # 0-10分
        )
        
        # 统计评分分布
        score_distribution = defaultdict(int)
        valid_responses = 0
        
        for response in responses:
            if response.nps_score.value is not None:
                score_distribution[response.nps_score.value] += 1
                valid_responses += 1
        
        response_rate = valid_responses / total_responses if total_responses > 0 else 0
        
        return QuestionAnalysis(
            question_info=question_info,
            response_count=valid_responses,
            response_rate=response_rate,
            sentiment_distribution=dict(score_distribution)
        )
    
    def _analyze_factor_question(self, factor_config: Dict, responses: List, 
                               total_responses: int, factor_type: str) -> QuestionAnalysis:
        """分析因子选择问题"""
        
        question_info = QuestionInfo(
            question_id=factor_config.get('question_id', ''),
            question_text=factor_config.get('question_text', ''),
            question_type=QuestionType.FACTOR_SELECTION,
            options=factor_config.get('factor_list', [])
        )
        
        # 统计因子选择情况
        factor_counts = defaultdict(int)
        valid_responses = 0
        factor_analysis = []
        
        for response in responses:
            factor_response = response.factor_responses.get(factor_type, None)
            if factor_response and factor_response.selected:
                valid_responses += 1
                for selected_factor in factor_response.selected:
                    factor_counts[selected_factor] += 1
        
        # 生成因子分析
        for factor_name, count in factor_counts.items():
            factor_analysis.append(FactorAnalysis(
                factor_name=factor_name,
                positive_mentions=count if 'positive' in factor_type else 0,
                negative_mentions=count if 'negative' in factor_type else 0,
                total_mentions=count,
                sentiment_ratio=1.0 if 'positive' in factor_type else -1.0,
                related_responses=[]
            ))
        
        response_rate = valid_responses / total_responses if total_responses > 0 else 0
        
        return QuestionAnalysis(
            question_info=question_info,
            response_count=valid_responses,
            response_rate=response_rate,
            factor_analysis=factor_analysis
        )
    
    def _analyze_open_question(self, question_config: Dict, responses: List,
                             total_responses: int) -> QuestionAnalysis:
        """分析开放性问题"""
        
        question_info = QuestionInfo(
            question_id=question_config.get('question_id', ''),
            question_text=question_config.get('question_text', ''),
            question_type=QuestionType.OPEN_ENDED
        )
        
        # 收集文本回答
        text_responses = []
        valid_responses = 0
        
        for response in responses:
            open_responses = response.open_responses
            if hasattr(open_responses, 'specific_reasons'):
                reasons = open_responses.specific_reasons
                if isinstance(reasons, dict):
                    for key, text in reasons.items():
                        if text and text.strip():
                            text_responses.append(text.strip())
                            valid_responses += 1
        
        # 提取主题
        common_themes = self._extract_themes(text_responses)
        
        response_rate = valid_responses / total_responses if total_responses > 0 else 0
        
        return QuestionAnalysis(
            question_info=question_info,
            response_count=valid_responses,
            response_rate=response_rate,
            common_themes=common_themes
        )
    
    def _calculate_nps_distribution(self, processed_survey: ProcessedSurveyData) -> NPSDistribution:
        """计算NPS分布统计"""
        
        responses = processed_survey.response_data
        
        # 统计各类别数量
        promoters = 0
        passives = 0
        detractors = 0
        score_distribution = defaultdict(int)
        
        for response in responses:
            score = response.nps_score.value
            category = response.nps_score.category
            
            score_distribution[score] += 1
            
            if category == NPSCategory.PROMOTER:
                promoters += 1
            elif category == NPSCategory.PASSIVE:
                passives += 1
            elif category == NPSCategory.DETRACTOR:
                detractors += 1
        
        total_responses = len(responses)
        
        # 计算百分比和NPS分数
        promoter_percentage = (promoters / total_responses * 100) if total_responses > 0 else 0
        passive_percentage = (passives / total_responses * 100) if total_responses > 0 else 0
        detractor_percentage = (detractors / total_responses * 100) if total_responses > 0 else 0
        
        nps_score = promoter_percentage - detractor_percentage
        
        return NPSDistribution(
            promoters=promoters,
            passives=passives,
            detractors=detractors,
            total_responses=total_responses,
            nps_score=nps_score,
            promoter_percentage=promoter_percentage,
            passive_percentage=passive_percentage,
            detractor_percentage=detractor_percentage,
            score_distribution=dict(score_distribution)
        )
    
    def _generate_response_tags(self, processed_survey: ProcessedSurveyData) -> List[ResponseTag]:
        """生成回答标签"""
        
        tags = []
        responses = processed_survey.response_data
        
        # 基于关键词生成标签
        for category, keywords in self.factor_keywords.items():
            tag_count = 0
            related_responses = []
            
            for response in responses:
                # 检查开放性回答中的关键词
                open_responses = response.open_responses
                if hasattr(open_responses, 'specific_reasons'):
                    reasons = open_responses.specific_reasons
                    if isinstance(reasons, dict):
                        for text in reasons.values():
                            if text and any(keyword in text for keyword in keywords):
                                tag_count += 1
                                related_responses.append(text)
                                break
            
            if tag_count > 0:
                confidence = min(tag_count / len(responses), 1.0)
                tags.append(ResponseTag(
                    tag_id=f"tag_{category}",
                    tag_name=category,
                    tag_category="factor_analysis",
                    confidence=confidence,
                    keywords=keywords
                ))
        
        return tags
    
    def _calculate_quality_metrics(self, processed_survey: ProcessedSurveyData) -> Dict[str, Any]:
        """计算数据质量指标"""
        
        responses = processed_survey.response_data
        total_responses = len(responses)
        
        # 基本质量指标
        valid_responses = 0
        complete_responses = 0
        response_times = []
        
        for response in responses:
            if response.status == "已完成":
                complete_responses += 1
                
            if response.response_type == "正式":
                valid_responses += 1
                
            # 计算回答时间
            timing = response.timing
            if 'duration' in timing and timing['duration']:
                try:
                    duration_str = timing['duration']
                    # 解析时间格式 (如 "1分钟45秒")
                    if '分钟' in duration_str and '秒' in duration_str:
                        parts = duration_str.split('分钟')
                        minutes = int(parts[0])
                        seconds = int(parts[1].replace('秒', ''))
                        total_seconds = minutes * 60 + seconds
                        response_times.append(total_seconds)
                    elif '秒' in duration_str:
                        seconds = int(duration_str.replace('秒', ''))
                        response_times.append(seconds)
                except:
                    pass
        
        # 计算统计指标
        completion_rate = complete_responses / total_responses if total_responses > 0 else 0
        validity_rate = valid_responses / total_responses if total_responses > 0 else 0
        
        avg_response_time = np.mean(response_times) if response_times else 0
        median_response_time = np.median(response_times) if response_times else 0
        
        return {
            'total_responses': total_responses,
            'valid_responses': valid_responses,
            'complete_responses': complete_responses,
            'completion_rate': completion_rate,
            'validity_rate': validity_rate,
            'response_time_stats': {
                'mean': avg_response_time,
                'median': median_response_time,
                'min': min(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0
            }
        }
    
    def _extract_themes(self, text_responses: List[str]) -> List[str]:
        """从文本回答中提取主题"""
        
        if not text_responses:
            return []
        
        # 简单的主题提取：基于关键词频率
        word_counts = defaultdict(int)
        
        for text in text_responses:
            # 基于因子关键词进行主题识别
            for category, keywords in self.factor_keywords.items():
                if any(keyword in text for keyword in keywords):
                    word_counts[category] += 1
        
        # 返回前5个最常见的主题
        common_themes = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        return [theme[0] for theme in common_themes]
    
    def save_nps_data(self, processed_nps_data: ProcessedNPSData, 
                     output_path: str) -> bool:
        """
        保存处理后的NPS数据
        
        Args:
            processed_nps_data: 处理后的NPS数据
            output_path: 输出文件路径
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 将数据转换为可序列化的字典
            data_dict = asdict(processed_nps_data)
            
            # 处理枚举类型
            for question in data_dict['question_analysis']:
                if 'question_info' in question and 'question_type' in question['question_info']:
                    question['question_info']['question_type'] = question['question_info']['question_type'].value
            
            # 保存到JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"NPS数据已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存NPS数据时出错: {e}")
            return False

# 使用示例
def main():
    """主函数示例"""
    from .input_data_processor import InputDataProcessor
    
    # 加载和预处理数据
    input_processor = InputDataProcessor()
    raw_data = input_processor.load_from_file("/path/to/survey_data.json")
    processed_survey = input_processor.process_survey_data(raw_data)
    
    # 处理NPS数据
    nps_processor = NPSDataProcessor()
    processed_nps_data = nps_processor.process_nps_data(processed_survey)
    
    # 保存结果
    success = nps_processor.save_nps_data(processed_nps_data, "/path/to/nps_analysis.json")
    
    if success:
        logger.info("NPS数据处理完成")
        print(f"NPS分数: {processed_nps_data.nps_distribution.nps_score:.1f}")
        print(f"推荐者: {processed_nps_data.nps_distribution.promoter_percentage:.1f}%")
        print(f"中立者: {processed_nps_data.nps_distribution.passive_percentage:.1f}%")
        print(f"贬损者: {processed_nps_data.nps_distribution.detractor_percentage:.1f}%")

if __name__ == "__main__":
    main()