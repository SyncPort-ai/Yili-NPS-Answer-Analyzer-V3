"""
简单文件知识管理器 - FastAPI轻量级方案
只使用文件目录，支持JSON和文本文件，自动加载和缓存
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional
import time
import logging

logger = logging.getLogger(__name__)


class SimpleKnowledgeManager:
    """简单的文件知识管理器"""
    
    def __init__(self, knowledge_dir: Optional[str] = None):
        """
        初始化知识管理器
        
        Args:
            knowledge_dir: 知识文件目录，默认为 data/knowledge_files
        """
        self.knowledge_dir = Path(knowledge_dir or "data/knowledge_files")
        self.knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        # 内存缓存
        self._cache = {}
        self._file_timestamps = {}
        
        # 创建默认文件
        self._create_default_files()
        
        logger.info(f"知识管理器初始化完成，目录: {self.knowledge_dir}")

    def _create_default_files(self):
        """创建默认知识文件"""
        
        # 1. 产品目录文件
        product_file = self.knowledge_dir / "yili_products.json"
        if not product_file.exists():
            default_products = {
                "key_brands": ["金典", "安慕希", "舒化", "QQ星", "优酸乳", "谷粒多", "味可滋", "巧乐兹"],
                "business_units": {
                    "液奶事业部": ["金典", "安慕希", "舒化", "QQ星", "优酸乳"],
                    "冷饮事业部": ["巧乐兹", "甄稀", "须尽欢"],
                    "酸奶事业部": ["畅轻", "大果粒", "每益添"]
                }
            }
            with open(product_file, 'w', encoding='utf-8') as f:
                json.dump(default_products, f, ensure_ascii=False, indent=2)
        
        # 2. 业务标签文件
        tags_file = self.knowledge_dir / "business_tags.json"
        if not tags_file.exists():
            default_tags = {
                "概念设计": ["健康", "营养", "高端", "品质", "创新", "天然", "有机", "功能性"],
                "口味设计": ["甜度", "酸度", "香味", "口感", "质地", "层次", "醇厚", "清香"],
                "包装设计": ["美观", "设计", "颜色", "便利", "环保", "创意", "识别", "吸引力"]
            }
            with open(tags_file, 'w', encoding='utf-8') as f:
                json.dump(default_tags, f, ensure_ascii=False, indent=2)
        
        # 3. 业务规则文件
        rules_file = self.knowledge_dir / "business_rules.json"
        if not rules_file.exists():
            default_rules = {
                "nps_thresholds": {
                    "excellent": 50,
                    "good": 0,
                    "poor": -50
                },
                "quality_standards": {
                    "min_sample_size": 30,
                    "min_completeness": 0.8,
                    "min_reliability": 0.7
                }
            }
            with open(rules_file, 'w', encoding='utf-8') as f:
                json.dump(default_rules, f, ensure_ascii=False, indent=2)

    def get_knowledge(self, filename: str, default: Any = None) -> Any:
        """
        获取知识文件内容
        
        Args:
            filename: 文件名 (支持 .json 和 .txt)
            default: 默认值
            
        Returns:
            文件内容
        """
        file_path = self.knowledge_dir / filename
        
        # 检查文件是否存在
        if not file_path.exists():
            logger.warning(f"知识文件不存在: {filename}")
            return default
        
        # 检查是否需要重新加载
        current_mtime = file_path.stat().st_mtime
        cache_key = str(file_path)
        
        if (cache_key in self._cache and 
            cache_key in self._file_timestamps and 
            self._file_timestamps[cache_key] == current_mtime):
            return self._cache[cache_key]
        
        # 加载文件
        try:
            if filename.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = json.load(f)
            elif filename.endswith('.txt'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            else:
                # 尝试作为JSON加载，失败则作为文本
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = json.load(f)
                except json.JSONDecodeError:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
            
            # 更新缓存
            self._cache[cache_key] = content
            self._file_timestamps[cache_key] = current_mtime
            
            return content
            
        except Exception as e:
            logger.error(f"加载知识文件失败 {filename}: {str(e)}")
            return default

    def save_knowledge(self, filename: str, content: Any, format_type: str = "auto") -> bool:
        """
        保存知识文件
        
        Args:
            filename: 文件名
            content: 内容
            format_type: 格式类型 ("json", "text", "auto")
            
        Returns:
            是否成功
        """
        try:
            file_path = self.knowledge_dir / filename
            
            # 自动判断格式
            if format_type == "auto":
                if filename.endswith('.json') or isinstance(content, (dict, list)):
                    format_type = "json"
                else:
                    format_type = "text"
            
            # 保存文件
            if format_type == "json":
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(content, f, ensure_ascii=False, indent=2)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(str(content))
            
            # 清除缓存
            cache_key = str(file_path)
            if cache_key in self._cache:
                del self._cache[cache_key]
            if cache_key in self._file_timestamps:
                del self._file_timestamps[cache_key]
            
            logger.info(f"知识文件已保存: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"保存知识文件失败 {filename}: {str(e)}")
            return False

    def list_knowledge_files(self) -> List[str]:
        """列出所有知识文件"""
        try:
            files = []
            for file_path in self.knowledge_dir.iterdir():
                if file_path.is_file():
                    files.append(file_path.name)
            return sorted(files)
        except Exception as e:
            logger.error(f"列出知识文件失败: {str(e)}")
            return []

    def get_products(self) -> Dict[str, Any]:
        """获取产品信息"""
        return self.get_knowledge("yili_products.json", {})

    def get_business_tags(self) -> Dict[str, List[str]]:
        """获取业务标签"""
        return self.get_knowledge("business_tags.json", {})

    def get_business_rules(self) -> Dict[str, Any]:
        """获取业务规则"""
        return self.get_knowledge("business_rules.json", {})

    def add_custom_knowledge(self, filename: str, content: Any) -> bool:
        """添加自定义知识文件"""
        return self.save_knowledge(filename, content)

    def update_products(self, new_products: Dict[str, Any]) -> bool:
        """更新产品信息"""
        return self.save_knowledge("yili_products.json", new_products)

    def update_business_tags(self, new_tags: Dict[str, List[str]]) -> bool:
        """更新业务标签"""
        return self.save_knowledge("business_tags.json", new_tags)

    def get_knowledge_summary(self) -> Dict[str, Any]:
        """获取知识库摘要"""
        files = self.list_knowledge_files()
        
        summary = {
            "knowledge_directory": str(self.knowledge_dir),
            "total_files": len(files),
            "files": files,
            "cached_items": len(self._cache),
            "products": len(self.get_products().get("key_brands", [])),
            "business_tags": {
                domain: len(tags) for domain, tags in self.get_business_tags().items()
            }
        }
        
        return summary

    def clear_cache(self):
        """清空缓存"""
        self._cache.clear()
        self._file_timestamps.clear()
        logger.info("知识缓存已清空")

    def reload_all(self):
        """重新加载所有文件"""
        self.clear_cache()
        # 预加载核心文件
        self.get_products()
        self.get_business_tags()
        self.get_business_rules()
        logger.info("所有知识文件已重新加载")


# 全局实例，供FastAPI使用
knowledge_manager = SimpleKnowledgeManager()


def get_knowledge_manager() -> SimpleKnowledgeManager:
    """获取知识管理器实例"""
    return knowledge_manager