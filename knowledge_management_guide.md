# 知识库管理指南

## 📍 存储位置

### 主要文件位置
```
nps-report-analyzer/
├── data/洞察智能体品类品牌渠道清单.json    # 🔄 产品目录 (可直接编辑)
├── nps_report_v2/data/knowledge_base.db    # 💾 SQLite知识库 (系统管理)
└── modify_knowledge_example.py             # 🛠️ 修改示例脚本
```

## 🛠️ 修改方法

### 方法1: 直接编辑JSON文件 ⭐ 推荐
**最简单的方式，适合大部分修改需求**

1. **编辑产品目录**
   ```bash
   # 直接编辑这个文件
   vi data/洞察智能体品类品牌渠道清单.json
   ```

2. **系统自动同步**
   - 系统每分钟检查文件变化
   - 检测到更新后自动同步到知识库
   - 无需重启服务

3. **可修改的内容**
   - 添加/删除产品品牌
   - 修改事业部信息
   - 更新渠道信息
   - 调整产品分类

### 方法2: 程序化API修改
**适合批量修改和自动化场景**

```python
from nps_report_v2 import PersistentKnowledgeManager

# 初始化管理器
km = PersistentKnowledgeManager()

# 修改业务规则
new_rules = {
    "nps_scoring_rules": {
        "excellent_threshold": 60,  # 优秀阈值
        "industry_benchmark": 35    # 行业基准
    }
}

km.store_knowledge(
    key="business_rules",
    category="business_logic",
    content=new_rules
)
```

### 方法3: 通过Web界面 (未来功能)
**计划中的功能，将提供图形界面**

## 📋 知识库结构

### 核心知识项
| 知识项 | 类别 | 描述 | 修改方式 |
|--------|------|------|----------|
| `yili_product_catalog` | 产品目录 | 伊利产品和事业部信息 | JSON文件 |
| `business_rules` | 业务规则 | NPS评分标准、质量阈值 | API修改 |
| `analysis_templates` | 分析模板 | 三大业务域标签体系 | API修改 |
| `product_mention_frequency` | 动态学习 | 产品提及频率统计 | 自动更新 |
| `problem_patterns` | 动态学习 | 问题模式识别 | 自动更新 |

### 业务域标签体系
```json
{
  "概念设计": [
    "原料天然", "奶源优质", "目标群体", "健康", "营养价值感知", 
    "高端", "高品质", "时尚潮流", "安全信赖", "价格", "包装美观"
  ],
  "口味设计": [
    "口味", "酸味", "甜味", "奶香味", "口感", "细腻度", 
    "顺滑度", "层次感", "醇厚度", "营养价值感知"
  ],
  "包装设计": [
    "字体美观度", "图案美观度", "色彩美观度", "整体美观度",
    "信息传达", "品牌认知", "产品印象", "情感共鸣"
  ]
}
```

## 🔧 常用修改场景

### 1. 添加新产品
**编辑JSON文件，在对应事业部添加:**
```json
{
  "brand_id": 100,
  "brand_name": "新产品名称",
  "category": "产品类别",
  "product_examples": "具体产品示例",
  "channel_code": "YILI_APP_XX",
  "channel_name": "对应小程序名称"
}
```

### 2. 调整NPS评分标准
**使用API修改:**
```python
km.store_knowledge("business_rules", "business_logic", {
    "nps_scoring_rules": {
        "promoter_range": [9, 10],
        "excellent_threshold": 50,  # 调整阈值
        "industry_benchmark": 30    # 调整基准
    }
})
```

### 3. 扩展业务标签
**添加新的分析标签:**
```python
templates = km.get_knowledge("analysis_templates")
templates["business_domain_tags"]["概念设计"].extend([
    "可持续发展", "智能包装", "个性化定制"
])
km.store_knowledge("analysis_templates", "analysis_templates", templates)
```

### 4. 查看知识库状态
```python
from nps_report_v2 import AuxiliaryDataManager

aux = AuxiliaryDataManager()
summary = aux.get_knowledge_summary()
print(summary)
```

## 📊 监控和备份

### 自动监控
- 系统每分钟检查文件变化
- 自动同步更新到知识库
- 记录变更历史和版本

### 手动备份
```python
# 导出完整备份
aux = AuxiliaryDataManager()
backup_path = aux.export_knowledge_backup()
print(f"备份已保存到: {backup_path}")
```

### 缓存管理
```python
# 清空缓存，强制重新加载
aux = AuxiliaryDataManager()
aux.clear_cache()
```

## ⚠️ 注意事项

1. **JSON格式**：确保编辑后的JSON格式正确
2. **中文编码**：使用UTF-8编码保存文件
3. **备份习惯**：重要修改前先导出备份
4. **测试验证**：修改后运行系统验证功能正常
5. **版本控制**：系统自动记录版本，但建议外部也做版本管理

## 🚀 快速开始

1. **查看当前状态**
   ```bash
   python modify_knowledge_example.py
   # 选择选项4查看状态
   ```

2. **进行简单修改**
   ```bash
   # 编辑产品目录
   vi data/洞察智能体品类品牌渠道清单.json
   # 系统会自动同步
   ```

3. **验证修改结果**
   ```python
   from nps_report_v2 import AuxiliaryDataManager
   aux = AuxiliaryDataManager()
   print(aux.get_knowledge_summary())
   ```

现在您可以轻松管理和修改系统的辅助信息了！