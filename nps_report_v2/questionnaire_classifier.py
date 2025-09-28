"""
NPS报告分析系统V2 - 问卷类型智能识别器
基于伊利集团业务知识库的高精度问卷分类算法
"""

import re
import json
import pandas as pd
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class QuestionnaireCategory(Enum):
    """问卷主类别"""
    NPS_RESEARCH = "nps_research"
    CONCEPT_TEST = "concept_test"
    TASTE_TEST = "taste_test"
    PACKAGE_TEST = "package_test"
    BRAND_EVALUATION = "brand_evaluation"
    PRODUCT_COMPARISON = "product_comparison"
    MARKET_RESEARCH = "market_research"
    USER_EXPERIENCE = "user_experience"
    UNKNOWN = "unknown"


class BusinessUnit(Enum):
    """伊利集团事业部"""
    LIQUID_MILK = "液奶事业部"
    INFANT_NUTRITION = "婴幼儿营养品事业部"
    YOGURT = "酸奶事业部"
    ADULT_NUTRITION = "成人营养品事业部"
    ICE_CREAM = "冷饮事业部"
    CHEESE = "奶酪事业部"
    YIZHINIU = "伊知牛公司"
    KANGYIJIA = "康益佳公司"
    UNKNOWN = "未知事业部"


@dataclass
class ClassificationResult:
    """问卷分类结果"""
    category: QuestionnaireCategory
    business_unit: BusinessUnit
    target_products: List[str]
    confidence_score: float
    key_indicators: List[str]
    analysis_focus: List[str]
    recommended_tags: List[str]
    metadata: Dict[str, Any]


class QuestionnaireClassifier:
    """问卷类型智能识别器"""
    
    def __init__(self, auxiliary_data_path: Optional[str] = None):
        """
        初始化分类器
        
        Args:
            auxiliary_data_path: 辅助数据文件路径，包含伊利产品目录
        """
        self.auxiliary_data_path = auxiliary_data_path
        self.product_catalog = {}
        self.business_units_mapping = {}
        self.channel_mapping = {}
        
        # 加载辅助数据
        self._load_auxiliary_data()
        
        # 初始化分类规则
        self._initialize_classification_rules()
        
        # 初始化业务领域标签系统
        self._initialize_business_tags()

    def _load_auxiliary_data(self):
        """加载伊利集团产品目录等辅助数据"""
        if self.auxiliary_data_path and Path(self.auxiliary_data_path).exists():
            try:
                with open(self.auxiliary_data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 构建产品目录索引
                for business_unit in data.get('business_units', []):
                    unit_name = business_unit['name']
                    for product in business_unit.get('products', []):
                        brand_name = product['brand_name']
                        category = product['category']
                        
                        self.product_catalog[brand_name] = {
                            'business_unit': unit_name,
                            'category': category,
                            'examples': product.get('product_examples', ''),
                            'channel_code': product.get('channel_code', ''),
                            'channel_name': product.get('channel_name', '')
                        }
                        
                        # 构建事业部映射
                        if unit_name not in self.business_units_mapping:
                            self.business_units_mapping[unit_name] = []
                        self.business_units_mapping[unit_name].append(brand_name)
                
                # 构建渠道映射
                for channel in data.get('mini_program_channels', []):
                    self.channel_mapping[channel['channel_code']] = channel['channel_name']
                
                logger.info(f"成功加载 {len(self.product_catalog)} 个产品的辅助数据")
                
            except Exception as e:
                logger.warning(f"加载辅助数据失败: {str(e)}")
        else:
            logger.warning("未提供辅助数据路径或文件不存在，使用默认配置")

    def _initialize_classification_rules(self):
        """初始化问卷分类规则"""
        self.classification_rules = {
            QuestionnaireCategory.NPS_RESEARCH: {
                'keywords': [
                    '净推荐值', 'NPS', '推荐度', '推荐指数', '推荐分数',
                    '整体满意度', '综合评价', '总体印象', '品牌忠诚度'
                ],
                'question_patterns': [
                    r'您.*推荐.*给.*朋友',
                    r'推荐.*可能性.*分',
                    r'整体.*满意度.*评分',
                    r'总体.*评价.*分数'
                ],
                'indicators': ['推荐者', '中立者', '贬损者', 'NPS值']
            },
            
            QuestionnaireCategory.CONCEPT_TEST: {
                'keywords': [
                    '概念测试', '产品概念', '创意评估', '概念吸引力',
                    '产品创意', '概念描述', '产品理念', '设计概念'
                ],
                'question_patterns': [
                    r'概念.*吸引力.*评分',
                    r'产品.*概念.*喜欢程度',
                    r'创意.*独特性.*评价',
                    r'概念.*购买意愿'
                ],
                'indicators': ['概念吸引力', '独特性', '相关性', '可信度']
            },
            
            QuestionnaireCategory.TASTE_TEST: {
                'keywords': [
                    '口味测试', '味觉评估', '口感', '风味', '甜度', '酸度',
                    '香味', '质地', '口感层次', '余味', '浓度', '新鲜度'
                ],
                'question_patterns': [
                    r'口味.*喜欢程度',
                    r'甜度.*合适性',
                    r'口感.*满意度',
                    r'味道.*评分'
                ],
                'indicators': ['口感', '甜度', '酸度', '香味', '质地']
            },
            
            QuestionnaireCategory.PACKAGE_TEST: {
                'keywords': [
                    '包装测试', '包装设计', '外观评价', '包装吸引力',
                    '包装材质', '标签设计', '颜色搭配', '包装便利性'
                ],
                'question_patterns': [
                    r'包装.*吸引力.*评分',
                    r'外观.*设计.*喜欢',
                    r'包装.*便利性.*评价',
                    r'标签.*清晰度'
                ],
                'indicators': ['视觉吸引力', '信息清晰度', '便利性', '品质感']
            },
            
            QuestionnaireCategory.BRAND_EVALUATION: {
                'keywords': [
                    '品牌评估', '品牌形象', '品牌认知', '品牌偏好',
                    '品牌印象', '品牌联想', '品牌信任度', '品牌影响力'
                ],
                'question_patterns': [
                    r'品牌.*印象.*评价',
                    r'品牌.*信任度.*评分',
                    r'品牌.*偏好.*选择',
                    r'品牌.*形象.*描述'
                ],
                'indicators': ['品牌认知', '品牌偏好', '品牌信任', '品牌形象']
            },
            
            QuestionnaireCategory.PRODUCT_COMPARISON: {
                'keywords': [
                    '产品对比', '竞品分析', '产品比较', '优劣对比',
                    '竞争对手', '市场比较', '产品排名', '相对优势'
                ],
                'question_patterns': [
                    r'相比.*其他.*产品',
                    r'与.*竞品.*比较',
                    r'产品.*排名.*评价',
                    r'优势.*劣势.*分析'
                ],
                'indicators': ['相对优势', '竞争地位', '差异化', '市场表现']
            }
        }

    def _initialize_business_tags(self):
        """初始化业务领域标签系统"""
        self.business_domain_tags = {
            '概念设计': [
                '产品定位', '目标人群', '价值主张', '差异化优势', '市场机会',
                '产品特性', '功能创新', '使用场景', '消费需求', '产品理念',
                '创新点', '卖点提炼', '产品形态', '核心价值', '竞争优势',
                '市场缺口', '消费趋势', '产品概念', '设计理念', '品牌延伸',
                '产品组合', '价格策略'
            ],
            
            '口味设计': [
                '甜度调节', '酸度平衡', '香味层次', '口感质地', '风味组合',
                '新口味开发', '经典口味', '季节性口味', '地域口味', '功能性口味',
                '天然香料', '人工添加剂', '口感创新', '味觉体验', '口味偏好',
                '口味测试', '感官评价', '口味接受度', '口味记忆', '口味识别',
                '配方优化', '原料选择', '生产工艺'
            ],
            
            '包装设计': [
                '视觉设计', '包装材质', '结构设计', '便利性', '环保性',
                '货架展示', '品牌识别', '信息传达', '色彩搭配', '图案设计',
                '包装规格', '开启方式', '储存便利', '携带方便', '包装创新',
                '成本控制', '生产可行性', '法规合规', '消费者体验', '包装测试',
                '耐用性', '密封性', '防伪设计'
            ]
        }

    def classify_questionnaire(self, 
                             questionnaire_data: Dict[str, Any],
                             text_content: str = "") -> ClassificationResult:
        """
        智能分类问卷类型
        
        Args:
            questionnaire_data: 问卷数据字典
            text_content: 额外的文本内容用于分析
            
        Returns:
            ClassificationResult: 分类结果
        """
        try:
            # 提取问卷文本内容
            combined_text = self._extract_text_content(questionnaire_data, text_content)
            
            # 主类别分类
            category, category_confidence, category_indicators = self._classify_main_category(combined_text)
            
            # 业务单元识别
            business_unit, target_products = self._identify_business_unit(combined_text)
            
            # 分析焦点识别
            analysis_focus = self._identify_analysis_focus(combined_text, category)
            
            # 推荐标签生成
            recommended_tags = self._generate_recommended_tags(combined_text, category)
            
            # 计算综合置信度
            confidence_score = self._calculate_confidence_score(
                category_confidence, business_unit, target_products, analysis_focus
            )
            
            # 生成元数据
            metadata = self._generate_metadata(questionnaire_data, combined_text)
            
            return ClassificationResult(
                category=category,
                business_unit=business_unit,
                target_products=target_products,
                confidence_score=confidence_score,
                key_indicators=category_indicators,
                analysis_focus=analysis_focus,
                recommended_tags=recommended_tags,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"问卷分类失败: {str(e)}")
            return ClassificationResult(
                category=QuestionnaireCategory.UNKNOWN,
                business_unit=BusinessUnit.UNKNOWN,
                target_products=[],
                confidence_score=0.0,
                key_indicators=[],
                analysis_focus=[],
                recommended_tags=[],
                metadata={'error': str(e)}
            )

    def _extract_text_content(self, questionnaire_data: Dict[str, Any], additional_text: str = "") -> str:
        """提取问卷中的所有文本内容"""
        text_parts = [additional_text] if additional_text else []
        
        def extract_from_value(value):
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, (list, tuple)):
                for item in value:
                    extract_from_value(item)
            elif isinstance(value, dict):
                for v in value.values():
                    extract_from_value(v)
        
        extract_from_value(questionnaire_data)
        
        return " ".join(text_parts)

    def _classify_main_category(self, text_content: str) -> Tuple[QuestionnaireCategory, float, List[str]]:
        """分类主类别"""
        category_scores = {}
        detected_indicators = {}
        
        for category, rules in self.classification_rules.items():
            score = 0.0
            indicators = []
            
            # 关键词匹配 (40%)
            keyword_matches = 0
            for keyword in rules['keywords']:
                if keyword in text_content:
                    keyword_matches += 1
                    indicators.append(f"关键词: {keyword}")
            
            if rules['keywords']:
                score += (keyword_matches / len(rules['keywords'])) * 0.4
            
            # 问题模式匹配 (35%)
            pattern_matches = 0
            for pattern in rules['question_patterns']:
                if re.search(pattern, text_content):
                    pattern_matches += 1
                    indicators.append(f"模式: {pattern}")
            
            if rules['question_patterns']:
                score += (pattern_matches / len(rules['question_patterns'])) * 0.35
            
            # 指标词匹配 (25%)
            indicator_matches = 0
            for indicator in rules['indicators']:
                if indicator in text_content:
                    indicator_matches += 1
                    indicators.append(f"指标: {indicator}")
            
            if rules['indicators']:
                score += (indicator_matches / len(rules['indicators'])) * 0.25
            
            category_scores[category] = score
            detected_indicators[category] = indicators
        
        # 选择得分最高的类别
        best_category = max(category_scores, key=category_scores.get)
        best_score = category_scores[best_category]
        best_indicators = detected_indicators[best_category]
        
        # 如果得分过低，归类为未知
        if best_score < 0.3:
            best_category = QuestionnaireCategory.UNKNOWN
            best_score = 0.0
            best_indicators = []
        
        return best_category, best_score, best_indicators

    def _identify_business_unit(self, text_content: str) -> Tuple[BusinessUnit, List[str]]:
        """识别目标业务单元和产品"""
        unit_scores = {}
        identified_products = []
        
        # 产品品牌匹配
        for brand_name, product_info in self.product_catalog.items():
            if brand_name in text_content:
                business_unit = product_info['business_unit']
                if business_unit not in unit_scores:
                    unit_scores[business_unit] = 0
                unit_scores[business_unit] += 1
                identified_products.append(brand_name)
        
        # 事业部名称直接匹配
        for unit_name in self.business_units_mapping.keys():
            if unit_name in text_content:
                if unit_name not in unit_scores:
                    unit_scores[unit_name] = 0
                unit_scores[unit_name] += 2  # 直接匹配给更高权重
        
        # 产品类别匹配
        category_unit_mapping = {
            '常温白奶': '液奶事业部',
            '酸奶': '酸奶事业部',
            '婴儿奶粉': '婴幼儿营养品事业部',
            '冰淇淋': '冷饮事业部',
            '奶酪': '奶酪事业部'
        }
        
        for category, unit in category_unit_mapping.items():
            if category in text_content:
                if unit not in unit_scores:
                    unit_scores[unit] = 0
                unit_scores[unit] += 1
        
        # 确定最可能的业务单元
        if unit_scores:
            best_unit_name = max(unit_scores, key=unit_scores.get)
            # 映射到枚举值
            unit_mapping = {
                '液奶事业部': BusinessUnit.LIQUID_MILK,
                '婴幼儿营养品事业部': BusinessUnit.INFANT_NUTRITION,
                '酸奶事业部': BusinessUnit.YOGURT,
                '成人营养品事业部': BusinessUnit.ADULT_NUTRITION,
                '冷饮事业部': BusinessUnit.ICE_CREAM,
                '奶酪事业部': BusinessUnit.CHEESE,
                '伊知牛公司': BusinessUnit.YIZHINIU,
                '康益佳公司': BusinessUnit.KANGYIJIA
            }
            best_unit = unit_mapping.get(best_unit_name, BusinessUnit.UNKNOWN)
        else:
            best_unit = BusinessUnit.UNKNOWN
        
        return best_unit, identified_products

    def _identify_analysis_focus(self, text_content: str, category: QuestionnaireCategory) -> List[str]:
        """识别分析焦点"""
        focus_areas = []
        
        # 基于问卷类别的通用焦点
        category_focus_mapping = {
            QuestionnaireCategory.NPS_RESEARCH: [
                '推荐意愿分析', '满意度驱动因素', '忠诚度提升建议'
            ],
            QuestionnaireCategory.CONCEPT_TEST: [
                '概念吸引力评估', '独特性分析', '购买意愿预测'
            ],
            QuestionnaireCategory.TASTE_TEST: [
                '口味偏好分析', '感官体验评估', '配方优化建议'
            ],
            QuestionnaireCategory.PACKAGE_TEST: [
                '视觉吸引力评估', '功能性分析', '货架表现预测'
            ],
            QuestionnaireCategory.BRAND_EVALUATION: [
                '品牌形象分析', '竞争地位评估', '品牌价值提升'
            ],
            QuestionnaireCategory.PRODUCT_COMPARISON: [
                '竞争优劣势分析', '差异化机会识别', '市场定位建议'
            ]
        }
        
        focus_areas.extend(category_focus_mapping.get(category, []))
        
        # 基于文本内容的特定焦点
        specific_focus_keywords = {
            '价格': '价格敏感度分析',
            '渠道': '渠道偏好分析',
            '年龄': '年龄群体差异分析',
            '性别': '性别偏好差异分析',
            '地区': '地域差异分析',
            '收入': '收入水平影响分析',
            '购买': '购买行为分析',
            '使用': '使用习惯分析',
            '竞品': '竞品对比分析',
            '创新': '创新接受度分析'
        }
        
        for keyword, focus in specific_focus_keywords.items():
            if keyword in text_content and focus not in focus_areas:
                focus_areas.append(focus)
        
        return focus_areas

    def _generate_recommended_tags(self, text_content: str, category: QuestionnaireCategory) -> List[str]:
        """生成推荐的业务标签"""
        recommended_tags = []
        
        # 基于问卷类别映射到业务领域
        category_domain_mapping = {
            QuestionnaireCategory.CONCEPT_TEST: '概念设计',
            QuestionnaireCategory.TASTE_TEST: '口味设计',
            QuestionnaireCategory.PACKAGE_TEST: '包装设计'
        }
        
        target_domain = category_domain_mapping.get(category)
        if target_domain and target_domain in self.business_domain_tags:
            domain_tags = self.business_domain_tags[target_domain]
            
            # 根据文本内容匹配相关标签
            for tag in domain_tags:
                if any(keyword in text_content for keyword in tag.split()):
                    recommended_tags.append(tag)
                    if len(recommended_tags) >= 10:  # 限制推荐标签数量
                        break
        
        # 如果没有匹配到足够的标签，添加通用标签
        if len(recommended_tags) < 5:
            general_tags = [
                '消费者洞察', '市场研究', '产品优化', '用户体验',
                '品质提升', '创新开发', '竞争分析'
            ]
            for tag in general_tags:
                if tag not in recommended_tags:
                    recommended_tags.append(tag)
                    if len(recommended_tags) >= 5:
                        break
        
        return recommended_tags

    def _calculate_confidence_score(self, 
                                  category_confidence: float,
                                  business_unit: BusinessUnit,
                                  target_products: List[str],
                                  analysis_focus: List[str]) -> float:
        """计算综合置信度分数"""
        # 主类别置信度权重 50%
        confidence = category_confidence * 0.5
        
        # 业务单元识别准确性权重 25%
        if business_unit != BusinessUnit.UNKNOWN:
            confidence += 0.25
        
        # 产品识别数量权重 15%
        product_score = min(len(target_products) / 3, 1.0)  # 最多3个产品得满分
        confidence += product_score * 0.15
        
        # 分析焦点丰富度权重 10%
        focus_score = min(len(analysis_focus) / 5, 1.0)  # 最多5个焦点得满分
        confidence += focus_score * 0.1
        
        return round(confidence, 3)

    def _generate_metadata(self, questionnaire_data: Dict[str, Any], text_content: str) -> Dict[str, Any]:
        """生成分类元数据"""
        metadata = {
            'classification_time': pd.Timestamp.now().isoformat(),
            'text_length': len(text_content),
            'data_fields': list(questionnaire_data.keys()) if isinstance(questionnaire_data, dict) else [],
            'has_auxiliary_data': bool(self.product_catalog),
            'detected_brands': [],
            'detected_categories': []
        }
        
        # 检测到的品牌
        for brand_name in self.product_catalog.keys():
            if brand_name in text_content:
                metadata['detected_brands'].append(brand_name)
        
        # 检测到的产品类别
        categories_in_text = set()
        for product_info in self.product_catalog.values():
            if product_info['category'] in text_content:
                categories_in_text.add(product_info['category'])
        
        metadata['detected_categories'] = list(categories_in_text)
        
        return metadata

    def get_classification_suggestions(self, classification_result: ClassificationResult) -> Dict[str, Any]:
        """基于分类结果生成分析建议"""
        suggestions = {
            'analysis_approach': [],
            'key_metrics': [],
            'visualization_recommendations': [],
            'report_sections': []
        }
        
        category = classification_result.category
        business_unit = classification_result.business_unit
        
        # 基于问卷类别的建议
        if category == QuestionnaireCategory.NPS_RESEARCH:
            suggestions['analysis_approach'] = [
                '计算NPS值及其分布',
                '分析推荐者、中立者、贬损者的特征差异',
                '识别NPS驱动因素',
                '构建NPS改进路径'
            ]
            suggestions['key_metrics'] = ['NPS值', '推荐者比例', '中立者比例', '贬损者比例']
            suggestions['visualization_recommendations'] = ['NPS分布图', '驱动因素重要性图', '改进机会矩阵']
            
        elif category == QuestionnaireCategory.CONCEPT_TEST:
            suggestions['analysis_approach'] = [
                '评估概念吸引力各维度表现',
                '分析目标群体接受度差异',
                '识别概念优化机会',
                '预测市场成功概率'
            ]
            suggestions['key_metrics'] = ['总体吸引力', '独特性得分', '相关性得分', '可信度得分']
            
        elif category == QuestionnaireCategory.TASTE_TEST:
            suggestions['analysis_approach'] = [
                '分析各口味维度评分',
                '识别最佳配方组合',
                '评估口味接受度',
                '提供配方优化建议'
            ]
            suggestions['key_metrics'] = ['整体喜好度', '甜度评分', '口感评分', '香味评分']
        
        # 基于业务单元的建议
        if business_unit != BusinessUnit.UNKNOWN:
            unit_specific_suggestions = self._get_business_unit_suggestions(business_unit)
            suggestions.update(unit_specific_suggestions)
        
        return suggestions

    def _get_business_unit_suggestions(self, business_unit: BusinessUnit) -> Dict[str, List[str]]:
        """获取特定业务单元的分析建议"""
        unit_suggestions = {
            BusinessUnit.LIQUID_MILK: {
                'report_sections': ['液奶品类竞争分析', '营养成分偏好', '包装便利性评估'],
                'key_metrics': ['新鲜度感知', '营养价值认知', '品牌信任度']
            },
            BusinessUnit.YOGURT: {
                'report_sections': ['酸奶口味偏好', '功能性需求分析', '包装创新评估'],
                'key_metrics': ['口感层次', '益生菌认知', '便携性评价']
            },
            BusinessUnit.INFANT_NUTRITION: {
                'report_sections': ['婴幼儿营养需求', '家长购买决策因素', '产品安全性认知'],
                'key_metrics': ['营养全面性', '安全性信任', '易消化性']
            },
            BusinessUnit.ICE_CREAM: {
                'report_sections': ['季节性消费模式', '口味创新接受度', '价格敏感度分析'],
                'key_metrics': ['口感创新性', '价格合理性', '包装吸引力']
            }
        }
        
        return unit_suggestions.get(business_unit, {
            'report_sections': ['通用产品分析'],
            'key_metrics': ['整体满意度']
        })