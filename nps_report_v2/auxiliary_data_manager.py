"""
辅助信息管理模块 - V2版本核心增强

该模块负责管理和处理伊利集团的企业知识库、产品目录、业务标签体系等辅助信息，
为NPS分析提供丰富的上下文和业务洞察。

V2版本新增特性：
- 持久化知识存储和管理
- 动态知识更新机制
- 容错和降级处理
- 自动缓存和性能优化

所有输出都使用中文，但类名和变量使用英文。
"""

import json
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
import logging

from .persistent_knowledge_manager import PersistentKnowledgeManager

logger = logging.getLogger(__name__)

@dataclass
class BusinessContext:
    """业务上下文信息结构"""
    primary_products: List[str]
    business_units: List[str]
    channels: List[str]
    categories: List[str]
    confidence_score: float
    context_metadata: Dict[str, Any]

@dataclass
class TagAnalysisResult:
    """标签分析结果结构"""
    matched_tags: Dict[str, List[str]]  # domain -> matched_tags
    relevance_scores: Dict[str, Dict[str, float]]  # domain -> tag -> score
    insights: Dict[str, List[str]]  # domain -> insights
    total_matched_count: int
    analysis_metadata: Dict[str, Any]

class AuxiliaryDataManager:
    """辅助信息管理器 - V2版本"""
    
    def __init__(self, data_dir: Optional[str] = None, enable_auto_update: bool = True):
        """
        初始化辅助信息管理器
        
        Args:
            data_dir: 数据存储目录（可选，使用默认位置）
            enable_auto_update: 是否启用自动更新
        """
        # 初始化持久化知识管理器
        self.knowledge_manager = PersistentKnowledgeManager(
            data_dir=data_dir,
            enable_auto_update=enable_auto_update
        )
        
        # 运行时缓存
        self.context_cache = {}
        self.tag_cache = {}
        
        logger.info("辅助信息管理器V2初始化完成")
    
    def identify_business_context(self, 
                                data: Any, 
                                detected_products: Optional[List[str]] = None) -> BusinessContext:
        """
        从数据中识别业务上下文
        
        Args:
            data: 待分析的数据（可以是文本、DataFrame等）
            detected_products: 已检测到的产品列表
            
        Returns:
            识别出的业务上下文
        """
        try:
            # 提取文本内容
            text_content = self._extract_text_from_data(data)
            
            # 生成缓存键
            cache_key = hash(text_content + str(detected_products))
            
            # 检查缓存
            if cache_key in self.context_cache:
                return self.context_cache[cache_key]
            
            # 获取产品目录
            product_catalog = self.knowledge_manager.get_safe_knowledge(
                "yili_product_catalog", 
                fallback_category="product_catalog"
            )
            
            # 识别产品和业务单元
            identified_products = detected_products or self._detect_products_from_text(text_content, product_catalog)
            business_units = self._identify_business_units(identified_products, product_catalog)
            channels = self._identify_channels(identified_products, product_catalog)
            categories = self._identify_categories(identified_products, product_catalog)
            
            # 计算置信度
            confidence = self._calculate_context_confidence(
                identified_products, business_units, text_content
            )
            
            # 生成元数据
            metadata = {
                "detection_method": "persistent_knowledge",
                "text_length": len(text_content),
                "catalog_version": product_catalog.get('metadata', {}).get('version', 'unknown'),
                "timestamp": datetime.now().isoformat()
            }
            
            # 创建业务上下文
            context = BusinessContext(
                primary_products=identified_products[:5],  # 前5个主要产品
                business_units=business_units,
                channels=channels,
                categories=categories,
                confidence_score=confidence,
                context_metadata=metadata
            )
            
            # 缓存结果
            self.context_cache[cache_key] = context
            
            # 动态更新知识库
            self._update_knowledge_from_analysis(text_content, context)
            
            return context
            
        except Exception as e:
            logger.warning(f"业务上下文识别失败: {str(e)}")
            return self._get_fallback_context()

    def _extract_text_from_data(self, data: Any) -> str:
        """从各种数据类型中提取文本"""
        if isinstance(data, str):
            return data
        elif isinstance(data, dict):
            # 从字典中提取所有字符串值
            text_parts = []
            for value in data.values():
                if isinstance(value, str):
                    text_parts.append(value)
                elif isinstance(value, (list, tuple)):
                    for item in value:
                        if isinstance(item, str):
                            text_parts.append(item)
            return " ".join(text_parts)
        elif hasattr(data, 'to_string'):
            # DataFrame等
            return data.to_string()
        else:
            return str(data)

    def _detect_products_from_text(self, text: str, product_catalog: Dict[str, Any]) -> List[str]:
        """从文本中检测产品"""
        detected_products = []
        text_lower = text.lower()
        
        # 检查核心品牌
        for brand in product_catalog.get('key_brands', []):
            if brand in text or brand.lower() in text_lower:
                detected_products.append(brand)
        
        # 检查详细产品列表
        for business_unit in product_catalog.get('business_units', []):
            for product in business_unit.get('products', []):
                brand_name = product.get('brand_name', '')
                if brand_name and (brand_name in text or brand_name.lower() in text_lower):
                    if brand_name not in detected_products:
                        detected_products.append(brand_name)
        
        # 检查产品别名和变体
        brand_variants = self.knowledge_manager.get_knowledge("brand_variants", {})
        for brand, variants in brand_variants.items():
            if any(variant in text_lower for variant in variants):
                if brand not in detected_products:
                    detected_products.append(brand)
        
        return detected_products

    def _identify_business_units(self, products: List[str], product_catalog: Dict[str, Any]) -> List[str]:
        """识别业务单元"""
        business_units = set()
        
        for business_unit in product_catalog.get('business_units', []):
            unit_name = business_unit.get('name', '')
            unit_products = [p.get('brand_name', '') for p in business_unit.get('products', [])]
            
            # 检查是否有产品属于该业务单元
            if any(product in unit_products for product in products):
                business_units.add(unit_name)
        
        return list(business_units)

    def _identify_channels(self, products: List[str], product_catalog: Dict[str, Any]) -> List[str]:
        """识别渠道"""
        channels = set()
        
        for business_unit in product_catalog.get('business_units', []):
            for product in business_unit.get('products', []):
                if product.get('brand_name', '') in products:
                    channel_name = product.get('channel_name', '')
                    if channel_name:
                        channels.add(channel_name)
        
        return list(channels)

    def _identify_categories(self, products: List[str], product_catalog: Dict[str, Any]) -> List[str]:
        """识别产品类别"""
        categories = set()
        
        for business_unit in product_catalog.get('business_units', []):
            for product in business_unit.get('products', []):
                if product.get('brand_name', '') in products:
                    category = product.get('category', '')
                    if category:
                        categories.add(category)
        
        return list(categories)

    def _calculate_context_confidence(self, products: List[str], business_units: List[str], text: str) -> float:
        """计算上下文识别置信度"""
        confidence = 0.0
        
        # 产品识别得分 (50%)
        if products:
            product_score = min(len(products) / 3, 1.0)  # 最多3个产品得满分
            confidence += product_score * 0.5
        
        # 业务单元识别得分 (30%)
        if business_units:
            unit_score = min(len(business_units) / 2, 1.0)  # 最多2个单元得满分
            confidence += unit_score * 0.3
        
        # 文本丰富度得分 (20%)
        text_richness = min(len(text) / 1000, 1.0)  # 1000字符得满分
        confidence += text_richness * 0.2
        
        return round(confidence, 3)

    def _get_fallback_context(self) -> BusinessContext:
        """获取降级上下文"""
        return BusinessContext(
            primary_products=[],
            business_units=[],
            channels=[],
            categories=[],
            confidence_score=0.0,
            context_metadata={
                "fallback": True,
                "reason": "识别失败，使用降级上下文"
            }
        )

    def analyze_business_domain_tags(self, 
                                   text_content: str, 
                                   target_products: Optional[List[str]] = None) -> TagAnalysisResult:
        """
        分析文本中的三大业务域标签
        
        Args:
            text_content: 待分析的文本内容
            target_products: 目标产品列表（用于定向分析）
            
        Returns:
            业务域标签分析结果
        """
        try:
            # 检查缓存
            cache_key = hash(text_content + str(target_products))
            if cache_key in self.tag_cache:
                return self.tag_cache[cache_key]
            
            # 获取业务域标签体系
            domain_tags = self.knowledge_manager.get_safe_knowledge(
                "analysis_templates",
                fallback_category="analysis_templates"
            ).get("business_domain_tags", {})
            
            # 如果没有获取到，使用降级默认值
            if not domain_tags:
                domain_tags = self._get_fallback_domain_tags()
            
            # 分析各个业务域
            matched_tags = {}
            relevance_scores = {}
            insights = {}
            total_count = 0
            
            for domain, tags in domain_tags.items():
                domain_matched = []
                domain_scores = {}
                
                for tag in tags:
                    relevance = self._calculate_tag_relevance(text_content, tag, target_products)
                    if relevance > 0.5:  # 相关性阈值
                        domain_matched.append(tag)
                        domain_scores[tag] = relevance
                        total_count += 1
                
                matched_tags[domain] = domain_matched
                relevance_scores[domain] = domain_scores
                insights[domain] = self._generate_domain_insights(domain, domain_matched, text_content)
            
            # 生成元数据
            metadata = {
                "analysis_timestamp": datetime.now().isoformat(),
                "text_length": len(text_content),
                "target_products": target_products or [],
                "domains_analyzed": list(domain_tags.keys())
            }
            
            # 创建分析结果
            result = TagAnalysisResult(
                matched_tags=matched_tags,
                relevance_scores=relevance_scores,
                insights=insights,
                total_matched_count=total_count,
                analysis_metadata=metadata
            )
            
            # 缓存结果
            self.tag_cache[cache_key] = result
            
            # 动态更新知识库
            self._update_tag_knowledge(text_content, result)
            
            return result
            
        except Exception as e:
            logger.warning(f"业务域标签分析失败: {str(e)}")
            return self._get_fallback_tag_result()

    def _get_fallback_domain_tags(self) -> Dict[str, List[str]]:
        """获取降级业务域标签"""
        return {
            "概念设计": [
                "产品定位", "目标人群", "价值主张", "差异化优势", "市场机会",
                "健康", "营养", "高端", "品质", "创新"
            ],
            "口味设计": [
                "甜度", "酸度", "香味", "口感", "质地",
                "口味", "味道", "浓度", "层次", "回味"
            ],
            "包装设计": [
                "视觉", "美观", "设计", "颜色", "图案",
                "包装", "外观", "便利", "环保", "创意"
            ]
        }

    def _calculate_tag_relevance(self, text: str, tag: str, target_products: Optional[List[str]] = None) -> float:
        """计算标签与文本的相关性"""
        text_lower = text.lower()
        tag_lower = tag.lower()
        relevance = 0.0
        
        # 直接匹配 (最高权重)
        if tag in text or tag_lower in text_lower:
            relevance = 1.0
        else:
            # 获取标签关键词映射
            tag_keywords = self.knowledge_manager.get_knowledge("tag_keywords_mapping", {})
            
            if tag in tag_keywords:
                keywords = tag_keywords[tag]
                for keyword in keywords:
                    if keyword in text_lower:
                        relevance = max(relevance, 0.8)
            
            # 字符相似性匹配
            if len(tag) >= 2:
                for i in range(len(tag) - 1):
                    substring = tag[i:i+2]
                    if substring in text:
                        relevance = max(relevance, 0.3)
        
        # 产品相关性加权
        if target_products and relevance > 0:
            product_boost = any(product in text for product in target_products)
            if product_boost:
                relevance = min(relevance * 1.2, 1.0)
        
        return round(relevance, 3)

    def _generate_domain_insights(self, domain: str, matched_tags: List[str], text: str) -> List[str]:
        """为特定业务域生成洞察"""
        insights = []
        tag_count = len(matched_tags)
        
        if not matched_tags:
            insights.append(f"{domain}维度暂未识别到相关标签")
            return insights
        
        # 基于标签数量的通用洞察
        if tag_count >= 5:
            insights.append(f"{domain}维度表现丰富，涵盖{tag_count}个关键要素")
        elif tag_count >= 3:
            insights.append(f"{domain}维度关注度较高，涉及{tag_count}个要素")
        else:
            insights.append(f"{domain}维度有{tag_count}个要素被提及")
        
        # 领域特定洞察
        domain_insights = self.knowledge_manager.get_knowledge("domain_insights_templates", {})
        if domain in domain_insights:
            template_insights = domain_insights[domain]
            for insight_rule in template_insights:
                required_tags = insight_rule.get("required_tags", [])
                insight_text = insight_rule.get("insight", "")
                
                if all(tag in matched_tags for tag in required_tags):
                    insights.append(insight_text)
        
        return insights

    def _get_fallback_tag_result(self) -> TagAnalysisResult:
        """获取降级标签分析结果"""
        return TagAnalysisResult(
            matched_tags={"概念设计": [], "口味设计": [], "包装设计": []},
            relevance_scores={"概念设计": {}, "口味设计": {}, "包装设计": {}},
            insights={"概念设计": ["无法识别相关标签"], "口味设计": ["无法识别相关标签"], "包装设计": ["无法识别相关标签"]},
            total_matched_count=0,
            analysis_metadata={"fallback": True}
        )

    def _update_knowledge_from_analysis(self, text_content: str, context: BusinessContext):
        """从分析结果动态更新知识库"""
        try:
            # 准备更新数据
            analysis_data = {
                "text_content": text_content[:500],  # 限制长度
                "identified_products": context.primary_products,
                "business_units": context.business_units,
                "confidence": context.confidence_score
            }
            
            # 触发动态更新
            self.knowledge_manager.update_knowledge_dynamically(
                analysis_result=analysis_data
            )
            
        except Exception as e:
            logger.warning(f"动态知识更新失败: {str(e)}")

    def _update_tag_knowledge(self, text_content: str, tag_result: TagAnalysisResult):
        """从标签分析结果更新知识库"""
        try:
            # 收集高频标签
            high_frequency_tags = []
            for domain, tags in tag_result.matched_tags.items():
                for tag in tags:
                    score = tag_result.relevance_scores.get(domain, {}).get(tag, 0)
                    if score > 0.8:
                        high_frequency_tags.append(tag)
            
            if high_frequency_tags:
                # 更新标签频率统计
                tag_frequency = self.knowledge_manager.get_knowledge("tag_frequency", {})
                for tag in high_frequency_tags:
                    tag_frequency[tag] = tag_frequency.get(tag, 0) + 1
                
                self.knowledge_manager.store_knowledge(
                    key="tag_frequency",
                    category="analytics_meta",
                    content=tag_frequency,
                    source="dynamic_tag_analysis"
                )
            
        except Exception as e:
            logger.warning(f"标签知识更新失败: {str(e)}")

    def enrich_analysis_with_context(self, 
                                   analysis_results: Dict[str, Any],
                                   business_context: BusinessContext,
                                   tag_analysis: TagAnalysisResult) -> Dict[str, Any]:
        """
        使用业务上下文和标签分析丰富原有分析结果
        
        Args:
            analysis_results: 原始分析结果
            business_context: 业务上下文
            tag_analysis: 标签分析结果
            
        Returns:
            丰富后的分析结果
        """
        try:
            enriched_results = analysis_results.copy()
            
            # 添加业务上下文信息
            enriched_results["business_context_v2"] = {
                "主要产品": business_context.primary_products,
                "涉及事业部": business_context.business_units,
                "相关渠道": business_context.channels,
                "产品类别": business_context.categories,
                "识别置信度": business_context.confidence_score,
                "上下文元数据": business_context.context_metadata
            }
            
            # 添加业务域标签分析
            enriched_results["business_domain_analysis_v2"] = {
                "标签匹配情况": tag_analysis.matched_tags,
                "相关性分数": tag_analysis.relevance_scores,
                "业务洞察": tag_analysis.insights,
                "总匹配标签数": tag_analysis.total_matched_count,
                "分析元数据": tag_analysis.analysis_metadata
            }
            
            # 生成综合业务洞察
            enriched_results["comprehensive_business_insights_v2"] = self._generate_comprehensive_insights_v2(
                business_context, tag_analysis, analysis_results
            )
            
            # 更新元数据
            if "metadata" not in enriched_results:
                enriched_results["metadata"] = {}
            
            enriched_results["metadata"].update({
                "v2_enrichment_applied": True,
                "enrichment_timestamp": datetime.now().isoformat(),
                "knowledge_manager_version": "2.0.0",
                "persistent_knowledge_used": True
            })
            
            return enriched_results
            
        except Exception as e:
            logger.error(f"分析结果增强失败: {str(e)}")
            return analysis_results  # 返回原始结果

    def _generate_comprehensive_insights_v2(self, 
                                          business_context: BusinessContext,
                                          tag_analysis: TagAnalysisResult,
                                          original_analysis: Dict[str, Any]) -> List[str]:
        """生成综合业务洞察 V2版本"""
        insights = []
        
        # 业务上下文洞察
        if business_context.primary_products:
            products_str = "、".join(business_context.primary_products[:3])
            insights.append(f"本次分析主要涉及{products_str}等产品")
            
            if business_context.business_units:
                units_str = "、".join(business_context.business_units)
                insights.append(f"覆盖{units_str}等业务单元")
        
        # 标签分析洞察
        if tag_analysis.total_matched_count > 0:
            insights.append(f"三大业务域共识别{tag_analysis.total_matched_count}个相关标签")
            
            # 找出最突出的业务域
            domain_counts = {domain: len(tags) for domain, tags in tag_analysis.matched_tags.items()}
            if domain_counts:
                top_domain = max(domain_counts, key=domain_counts.get)
                top_count = domain_counts[top_domain]
                if top_count > 0:
                    insights.append(f"{top_domain}维度最为突出，涉及{top_count}个关键要素")
        
        # 基于置信度的质量评估
        if business_context.confidence_score >= 0.8:
            insights.append("业务上下文识别精确度高，分析结果可信度强")
        elif business_context.confidence_score >= 0.5:
            insights.append("业务上下文识别准确度中等，建议补充更多上下文信息")
        else:
            insights.append("业务上下文识别准确度较低，建议谨慎解读分析结果")
        
        return insights

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """获取知识库摘要信息"""
        try:
            # 获取产品目录信息
            product_catalog = self.knowledge_manager.get_knowledge("yili_product_catalog", {})
            
            # 获取业务域标签信息
            domain_tags = self.knowledge_manager.get_knowledge("analysis_templates", {}).get("business_domain_tags", {})
            
            # 统计信息
            summary = {
                "知识库版本": "2.0.0",
                "存储方式": "持久化SQLite数据库",
                "产品目录": {
                    "事业部数量": len(product_catalog.get('business_units', [])),
                    "核心品牌数": len(product_catalog.get('key_brands', [])),
                    "渠道数量": len(product_catalog.get('mini_program_channels', [])),
                    "数据版本": product_catalog.get('metadata', {}).get('version', 'unknown')
                },
                "业务域标签": {
                    "标签总数": sum(len(tags) for tags in domain_tags.values()),
                    "业务域数": len(domain_tags),
                    "各域标签数": {domain: len(tags) for domain, tags in domain_tags.items()}
                },
                "缓存状态": {
                    "上下文缓存数": len(self.context_cache),
                    "标签缓存数": len(self.tag_cache)
                },
                "动态更新": "已启用" if self.knowledge_manager.enable_auto_update else "已禁用"
            }
            
            return summary
            
        except Exception as e:
            logger.error(f"获取知识库摘要失败: {str(e)}")
            return {"error": str(e), "status": "获取失败"}

    def clear_cache(self):
        """清空运行时缓存"""
        self.context_cache.clear()
        self.tag_cache.clear()
        logger.info("运行时缓存已清空")

    def export_knowledge_backup(self, backup_path: Optional[str] = None) -> str:
        """导出知识库备份"""
        return self.knowledge_manager.export_knowledge_backup(backup_path)