"""
NPS报告分析系统V2 - 持久化知识管理器
负责管理系统内部保存的辅助信息，支持动态更新和容错处理
"""

import json
import os
import sqlite3
import threading
import time
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import logging
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class KnowledgeVersion:
    """知识版本信息"""
    version: str
    created_at: str
    updated_at: str
    hash_signature: str
    size: int
    source: str


@dataclass
class KnowledgeItem:
    """知识项"""
    key: str
    category: str
    content: Dict[str, Any]
    version: str
    created_at: str
    updated_at: str
    priority: int = 1  # 1=高, 2=中, 3=低
    is_active: bool = True


class PersistentKnowledgeManager:
    """持久化知识管理器"""
    
    def __init__(self, 
                 data_dir: Optional[str] = None,
                 enable_auto_update: bool = True,
                 cache_ttl: int = 3600):  # 缓存1小时
        """
        初始化知识管理器
        
        Args:
            data_dir: 数据存储目录
            enable_auto_update: 是否启用自动更新
            cache_ttl: 缓存有效期（秒）
        """
        self.data_dir = Path(data_dir or os.path.join(os.path.dirname(__file__), "../data"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        self.db_path = self.data_dir / "knowledge_base.db"
        self.files_dir = self.data_dir / "knowledge_files"
        self.files_dir.mkdir(parents=True, exist_ok=True)
        
        self.enable_auto_update = enable_auto_update
        self.cache_ttl = cache_ttl
        
        # 内存缓存
        self._cache = {}
        self._cache_timestamps = {}
        self._cache_lock = threading.RLock()
        
        # 初始化数据库
        self._init_database()
        
        # 加载默认知识
        self._load_default_knowledge()
        
        # 启动自动更新监控
        if enable_auto_update:
            self._start_auto_update_monitor()

    def _init_database(self):
        """初始化数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge_items (
                        key TEXT PRIMARY KEY,
                        category TEXT NOT NULL,
                        content TEXT NOT NULL,
                        version TEXT NOT NULL,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        priority INTEGER DEFAULT 1,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS knowledge_versions (
                        version TEXT PRIMARY KEY,
                        created_at TEXT NOT NULL,
                        updated_at TEXT NOT NULL,
                        hash_signature TEXT NOT NULL,
                        size INTEGER NOT NULL,
                        source TEXT NOT NULL
                    )
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_category ON knowledge_items(category)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_priority ON knowledge_items(priority)
                ''')
                
                conn.commit()
                
        except Exception as e:
            logger.error(f"数据库初始化失败: {str(e)}")

    def _load_default_knowledge(self):
        """加载默认知识库"""
        # 检查是否已有数据
        if self._get_knowledge_count() > 0:
            logger.info("知识库已存在，跳过默认数据加载")
            return
        
        try:
            # 加载伊利产品目录
            product_catalog_path = self.data_dir.parent / "洞察智能体品类品牌渠道清单.json"
            if product_catalog_path.exists():
                self._import_product_catalog(product_catalog_path)
            
            # 加载默认业务规则
            self._load_default_business_rules()
            
            # 加载默认分析模板
            self._load_default_analysis_templates()
            
            logger.info("默认知识库加载完成")
            
        except Exception as e:
            logger.warning(f"默认知识库加载失败: {str(e)}")

    def _import_product_catalog(self, file_path: Path):
        """导入产品目录"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 存储产品目录
            self.store_knowledge(
                key="yili_product_catalog",
                category="product_catalog",
                content=data,
                source=f"file:{file_path.name}"
            )
            
            # 存储业务单元映射
            business_units = {}
            for unit in data.get('business_units', []):
                unit_name = unit['name']
                products = [p['brand_name'] for p in unit.get('products', [])]
                business_units[unit_name] = {
                    'categories': unit.get('categories', []),
                    'products': products
                }
            
            self.store_knowledge(
                key="business_units_mapping",
                category="business_mapping",
                content=business_units,
                source="derived_from_catalog"
            )
            
            # 存储渠道映射
            channels = {ch['channel_code']: ch['channel_name'] 
                       for ch in data.get('mini_program_channels', [])}
            
            self.store_knowledge(
                key="channel_mapping",
                category="channel_mapping",
                content=channels,
                source="derived_from_catalog"
            )
            
            logger.info(f"产品目录导入成功: {len(data.get('business_units', []))} 个业务单元")
            
        except Exception as e:
            logger.error(f"产品目录导入失败: {str(e)}")

    def _load_default_business_rules(self):
        """加载默认业务规则"""
        business_rules = {
            "nps_scoring_rules": {
                "promoter_range": [9, 10],
                "passive_range": [7, 8],
                "detractor_range": [0, 6],
                "excellent_threshold": 50,
                "good_threshold": 0,
                "industry_benchmark": 30
            },
            "quality_thresholds": {
                "data_completeness_min": 0.8,
                "sample_size_min": 30,
                "reliability_min": 0.7,
                "consistency_min": 0.75
            },
            "risk_alerts": {
                "nps_critical": -20,
                "nps_warning": 0,
                "detractor_rate_critical": 30,
                "detractor_rate_warning": 20
            }
        }
        
        self.store_knowledge(
            key="business_rules",
            category="business_logic",
            content=business_rules,
            source="system_default"
        )

    def _load_default_analysis_templates(self):
        """加载默认分析模板"""
        analysis_templates = {
            "nps_analysis_template": {
                "sections": [
                    "NPS得分分析",
                    "用户群体分布",
                    "推荐驱动因素",
                    "改进建议"
                ],
                "metrics": ["NPS值", "推荐者比例", "中立者比例", "贬损者比例"],
                "visualizations": ["NPS分布图", "趋势图", "驱动因素分析"]
            },
            "business_domain_tags": {
                "概念设计": [
                    "产品定位", "目标人群", "价值主张", "差异化优势", "市场机会",
                    "产品特性", "功能创新", "使用场景", "消费需求", "产品理念"
                ],
                "口味设计": [
                    "甜度调节", "酸度平衡", "香味层次", "口感质地", "风味组合",
                    "新口味开发", "经典口味", "季节性口味", "地域口味", "功能性口味"
                ],
                "包装设计": [
                    "视觉设计", "包装材质", "结构设计", "便利性", "环保性",
                    "货架展示", "品牌识别", "信息传达", "色彩搭配", "图案设计"
                ]
            }
        }
        
        self.store_knowledge(
            key="analysis_templates",
            category="analysis_templates",
            content=analysis_templates,
            source="system_default"
        )

    def store_knowledge(self, 
                       key: str,
                       category: str,
                       content: Dict[str, Any],
                       source: str = "manual",
                       priority: int = 1) -> bool:
        """
        存储知识项
        
        Args:
            key: 知识项键
            category: 类别
            content: 内容
            source: 来源
            priority: 优先级
            
        Returns:
            bool: 是否成功
        """
        try:
            content_str = json.dumps(content, ensure_ascii=False, indent=2)
            content_hash = hashlib.md5(content_str.encode()).hexdigest()
            timestamp = datetime.now().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                # 检查是否已存在
                existing = conn.execute(
                    'SELECT version FROM knowledge_items WHERE key = ?', (key,)
                ).fetchone()
                
                if existing:
                    # 更新现有项
                    conn.execute('''
                        UPDATE knowledge_items 
                        SET content = ?, updated_at = ?, priority = ?
                        WHERE key = ?
                    ''', (content_str, timestamp, priority, key))
                else:
                    # 插入新项
                    conn.execute('''
                        INSERT INTO knowledge_items 
                        (key, category, content, version, created_at, updated_at, priority)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (key, category, content_str, content_hash[:8], timestamp, timestamp, priority))
                
                # 记录版本信息
                conn.execute('''
                    INSERT OR REPLACE INTO knowledge_versions
                    (version, created_at, updated_at, hash_signature, size, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (content_hash[:8], timestamp, timestamp, content_hash, len(content_str), source))
                
                conn.commit()
            
            # 清除相关缓存
            self._invalidate_cache(key, category)
            
            logger.info(f"知识项存储成功: {key} ({category})")
            return True
            
        except Exception as e:
            logger.error(f"知识项存储失败: {str(e)}")
            return False

    def get_knowledge(self, 
                     key: str,
                     default: Optional[Dict[str, Any]] = None,
                     use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        获取知识项
        
        Args:
            key: 知识项键
            default: 默认值
            use_cache: 是否使用缓存
            
        Returns:
            Dict: 知识项内容
        """
        try:
            # 检查缓存
            if use_cache and self._is_cache_valid(key):
                return self._cache.get(key, default)
            
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    'SELECT content FROM knowledge_items WHERE key = ? AND is_active = 1',
                    (key,)
                ).fetchone()
                
                if result:
                    content = json.loads(result[0])
                    
                    # 更新缓存
                    if use_cache:
                        self._update_cache(key, content)
                    
                    return content
                else:
                    return default
                    
        except Exception as e:
            logger.warning(f"获取知识项失败: {key}, 错误: {str(e)}")
            return default

    def get_knowledge_by_category(self, 
                                 category: str,
                                 priority_filter: Optional[int] = None,
                                 use_cache: bool = True) -> List[Dict[str, Any]]:
        """
        按类别获取知识项
        
        Args:
            category: 类别
            priority_filter: 优先级过滤
            use_cache: 是否使用缓存
            
        Returns:
            List[Dict]: 知识项列表
        """
        try:
            cache_key = f"category:{category}:{priority_filter}"
            
            # 检查缓存
            if use_cache and self._is_cache_valid(cache_key):
                return self._cache.get(cache_key, [])
            
            query = 'SELECT key, content FROM knowledge_items WHERE category = ? AND is_active = 1'
            params = [category]
            
            if priority_filter:
                query += ' AND priority <= ?'
                params.append(priority_filter)
            
            query += ' ORDER BY priority, updated_at DESC'
            
            with sqlite3.connect(self.db_path) as conn:
                results = conn.execute(query, params).fetchall()
                
                items = []
                for key, content_str in results:
                    try:
                        content = json.loads(content_str)
                        content['_key'] = key
                        items.append(content)
                    except json.JSONDecodeError:
                        logger.warning(f"知识项内容解析失败: {key}")
                
                # 更新缓存
                if use_cache:
                    self._update_cache(cache_key, items)
                
                return items
                
        except Exception as e:
            logger.warning(f"按类别获取知识项失败: {category}, 错误: {str(e)}")
            return []

    def update_knowledge_dynamically(self, 
                                   analysis_result: Dict[str, Any],
                                   feedback_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        基于分析结果动态更新知识库
        
        Args:
            analysis_result: 分析结果
            feedback_data: 反馈数据
            
        Returns:
            bool: 是否有更新
        """
        try:
            has_updates = False
            
            # 1. 更新产品提及频率
            if self._update_product_frequency(analysis_result):
                has_updates = True
            
            # 2. 更新问题模式
            if self._update_problem_patterns(analysis_result):
                has_updates = True
            
            # 3. 更新改进建议模板
            if self._update_improvement_templates(analysis_result):
                has_updates = True
            
            # 4. 处理用户反馈
            if feedback_data and self._process_user_feedback(feedback_data):
                has_updates = True
            
            if has_updates:
                logger.info("知识库动态更新完成")
            
            return has_updates
            
        except Exception as e:
            logger.error(f"动态更新知识库失败: {str(e)}")
            return False

    def _update_product_frequency(self, analysis_result: Dict[str, Any]) -> bool:
        """更新产品提及频率"""
        try:
            text_content = " ".join(str(v) for v in analysis_result.values() if isinstance(v, str))
            
            # 获取当前产品频率数据
            freq_data = self.get_knowledge("product_mention_frequency", {})
            
            # 更新频率
            product_catalog = self.get_knowledge("yili_product_catalog", {})
            if not product_catalog:
                return False
            
            updated = False
            for business_unit in product_catalog.get('business_units', []):
                for product in business_unit.get('products', []):
                    brand_name = product['brand_name']
                    if brand_name in text_content:
                        if brand_name not in freq_data:
                            freq_data[brand_name] = 0
                        freq_data[brand_name] += 1
                        updated = True
            
            if updated:
                self.store_knowledge(
                    key="product_mention_frequency",
                    category="analytics_meta",
                    content=freq_data,
                    source="dynamic_update"
                )
            
            return updated
            
        except Exception as e:
            logger.warning(f"更新产品频率失败: {str(e)}")
            return False

    def _update_problem_patterns(self, analysis_result: Dict[str, Any]) -> bool:
        """更新问题模式"""
        try:
            # 提取问题关键词
            problem_keywords = []
            for key, value in analysis_result.items():
                if isinstance(value, str) and ('问题' in value or '不满' in value or '建议' in value):
                    # 简单的关键词提取
                    import re
                    keywords = re.findall(r'[\u4e00-\u9fff]{2,6}', value)
                    problem_keywords.extend(keywords)
            
            if not problem_keywords:
                return False
            
            # 获取当前问题模式
            patterns = self.get_knowledge("problem_patterns", {})
            
            # 更新模式频率
            updated = False
            for keyword in problem_keywords:
                if len(keyword) >= 2:  # 过滤太短的词
                    if keyword not in patterns:
                        patterns[keyword] = 0
                    patterns[keyword] += 1
                    updated = True
            
            if updated:
                self.store_knowledge(
                    key="problem_patterns",
                    category="analytics_meta",
                    content=patterns,
                    source="dynamic_update"
                )
            
            return updated
            
        except Exception as e:
            logger.warning(f"更新问题模式失败: {str(e)}")
            return False

    def _update_improvement_templates(self, analysis_result: Dict[str, Any]) -> bool:
        """更新改进建议模板"""
        # 这里可以根据分析结果的模式来学习和优化建议模板
        # 暂时返回False，表示没有更新
        return False

    def _process_user_feedback(self, feedback_data: Dict[str, Any]) -> bool:
        """处理用户反馈"""
        try:
            # 存储用户反馈以供后续分析
            feedback_key = f"user_feedback_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            self.store_knowledge(
                key=feedback_key,
                category="user_feedback",
                content=feedback_data,
                source="user_input",
                priority=2
            )
            
            return True
            
        except Exception as e:
            logger.warning(f"处理用户反馈失败: {str(e)}")
            return False

    def _get_knowledge_count(self) -> int:
        """获取知识项数量"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                result = conn.execute(
                    'SELECT COUNT(*) FROM knowledge_items WHERE is_active = 1'
                ).fetchone()
                return result[0] if result else 0
        except Exception:
            return 0

    def _is_cache_valid(self, key: str) -> bool:
        """检查缓存是否有效"""
        with self._cache_lock:
            if key not in self._cache_timestamps:
                return False
            
            age = time.time() - self._cache_timestamps[key]
            return age < self.cache_ttl

    def _update_cache(self, key: str, value: Any):
        """更新缓存"""
        with self._cache_lock:
            self._cache[key] = value
            self._cache_timestamps[key] = time.time()

    def _invalidate_cache(self, key: str, category: str):
        """失效缓存"""
        with self._cache_lock:
            # 失效特定键
            if key in self._cache:
                del self._cache[key]
                del self._cache_timestamps[key]
            
            # 失效类别缓存
            category_keys = [k for k in self._cache.keys() if k.startswith(f"category:{category}")]
            for cache_key in category_keys:
                if cache_key in self._cache:
                    del self._cache[cache_key]
                    del self._cache_timestamps[cache_key]

    def _start_auto_update_monitor(self):
        """启动自动更新监控"""
        def monitor_files():
            """监控文件变化"""
            last_check = {}
            
            while True:
                try:
                    # 检查数据目录中的JSON文件
                    for json_file in self.data_dir.glob("*.json"):
                        mtime = json_file.stat().st_mtime
                        
                        if json_file.name not in last_check or last_check[json_file.name] < mtime:
                            logger.info(f"检测到文件更新: {json_file.name}")
                            
                            # 重新导入更新的文件
                            if "品类品牌渠道清单" in json_file.name:
                                self._import_product_catalog(json_file)
                            
                            last_check[json_file.name] = mtime
                    
                    time.sleep(60)  # 每分钟检查一次
                    
                except Exception as e:
                    logger.error(f"文件监控错误: {str(e)}")
                    time.sleep(300)  # 出错后等待5分钟
        
        # 在后台线程中运行监控
        monitor_thread = threading.Thread(target=monitor_files, daemon=True)
        monitor_thread.start()
        logger.info("自动更新监控已启动")

    def get_safe_knowledge(self, 
                          key: str,
                          fallback_category: Optional[str] = None) -> Dict[str, Any]:
        """
        安全获取知识项，如果不存在则返回降级默认值
        
        Args:
            key: 知识项键
            fallback_category: 降级类别
            
        Returns:
            Dict: 知识内容或降级默认值
        """
        # 尝试获取指定知识项
        result = self.get_knowledge(key)
        if result is not None:
            return result
        
        # 如果指定了降级类别，尝试获取该类别的任一项
        if fallback_category:
            items = self.get_knowledge_by_category(fallback_category, priority_filter=1)
            if items:
                return items[0]
        
        # 返回空的降级默认值
        return self._get_fallback_defaults(key)

    def _get_fallback_defaults(self, key: str) -> Dict[str, Any]:
        """获取降级默认值"""
        defaults = {
            "yili_product_catalog": {
                "business_units": [],
                "key_brands": ["伊利", "安慕希", "金典", "舒化"],
                "usage_scenarios": ["产品NPS调研", "产品概念测试"]
            },
            "business_rules": {
                "nps_scoring_rules": {
                    "promoter_range": [9, 10],
                    "passive_range": [7, 8],
                    "detractor_range": [0, 6]
                }
            },
            "analysis_templates": {
                "nps_analysis_template": {
                    "sections": ["NPS得分分析", "改进建议"],
                    "metrics": ["NPS值", "推荐者比例"]
                }
            }
        }
        
        return defaults.get(key, {})

    def export_knowledge_backup(self, backup_path: Optional[str] = None) -> str:
        """导出知识库备份"""
        if not backup_path:
            backup_path = self.data_dir / f"knowledge_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                items = conn.execute('''
                    SELECT key, category, content, version, created_at, updated_at, priority
                    FROM knowledge_items WHERE is_active = 1
                ''').fetchall()
                
                backup_data = {
                    "exported_at": datetime.now().isoformat(),
                    "version": "2.0.0",
                    "item_count": len(items),
                    "items": []
                }
                
                for item in items:
                    backup_data["items"].append({
                        "key": item[0],
                        "category": item[1],
                        "content": json.loads(item[2]),
                        "version": item[3],
                        "created_at": item[4],
                        "updated_at": item[5],
                        "priority": item[6]
                    })
                
                with open(backup_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data, f, ensure_ascii=False, indent=2)
                
                logger.info(f"知识库备份导出成功: {backup_path}")
                return str(backup_path)
                
        except Exception as e:
            logger.error(f"知识库备份导出失败: {str(e)}")
            raise