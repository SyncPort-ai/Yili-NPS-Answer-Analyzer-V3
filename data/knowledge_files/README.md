# NPS报告分析系统V2 - 知识库文件说明

## 目录结构

本目录包含NPS报告分析系统V2所需的全部辅助信息文件，采用简单的文件目录管理方式。

## 文件清单

### 1. 产品目录信息
- **yili_products.json**: 伊利集团完整产品目录
  - 8个事业部
  - 79个产品品牌
  - 12个小程序渠道
  - 产品分类和渠道映射关系

### 2. 业务标签体系
- **business_tags.json**: 三大业务域标签体系
  - 概念设计标签 (28个)
  - 口味设计标签 (22个) 
  - 包装设计标签 (19个)

### 3. 业务规则配置
- **business_rules.json**: 分析业务规则
  - NPS评分规则
  - 数据质量阈值
  - 风险预警标准
  - 分析参数配置

### 4. 分析模板
- **analysis_templates.json**: 分析报告模板
  - NPS分析模板
  - 数据质量评估模板
  - 可信度评估模板
  - 业务域标签定义
  - 报告格式规范

### 5. 调研模板
- **survey_templates.json**: 问卷调研模板
  - 系统平台NPS模板
  - 产品NPS模板
  - 通用元数据字段

### 6. 标签关键词映射
- **tag_keywords_mapping.json**: 标签智能识别
  - 业务标签与关键词的映射关系
  - 支持模糊匹配和语义识别

### 7. 领域洞察模板
- **domain_insights_templates.json**: 业务洞察生成
  - 各业务域的洞察生成规则
  - 标签组合条件与洞察模板
  - 综合分析洞察规则

## 使用方式

### SimpleKnowledgeManager集成
所有文件将通过`SimpleKnowledgeManager`类自动加载和管理：

```python
from nps_report_v2.simple_knowledge_manager import SimpleKnowledgeManager

# 初始化知识管理器
km = SimpleKnowledgeManager()

# 获取产品信息
products = km.get_knowledge("yili_products.json")

# 获取业务标签
tags = km.get_knowledge("business_tags.json")
```

### 动态更新
- 文件修改后系统自动检测变化
- 支持热重载，无需重启服务
- 内存缓存优化性能

### 容错处理
- 文件不存在时提供降级默认值
- JSON格式错误时自动降级处理
- 支持部分文件缺失的场景

## 扩展指南

### 添加新知识文件
1. 在本目录创建新的JSON或TXT文件
2. 文件会被自动识别和加载
3. 通过`km.get_knowledge("filename")`访问

### 修改现有文件
1. 直接编辑JSON文件内容
2. 保存后系统自动重新加载
3. 建议先备份原文件

### 文件格式要求
- JSON文件: 必须是有效的JSON格式，使用UTF-8编码
- TXT文件: 纯文本格式，使用UTF-8编码
- 文件名: 建议使用描述性名称，避免特殊字符

## 版本控制

- **创建时间**: 2025-09-10
- **最后更新**: 2025-09-10
- **维护人员**: Claude Code
- **版本**: 2.0.0

## 数据来源

- 伊利集团官方产品目录
- 业务专家整理的标签体系
- 历史NPS调研经验总结
- 数据科学最佳实践

## 注意事项

1. **数据敏感性**: 产品信息属于商业敏感数据，请妥善保管
2. **更新频率**: 建议定期同步最新的产品目录和业务规则
3. **备份策略**: 重要修改前请做好文件备份
4. **编码格式**: 确保所有文件使用UTF-8编码，支持中文字符
5. **JSON格式**: 修改JSON文件时注意语法正确性，建议使用JSON验证工具

## 技术支持

如需添加新的辅助信息或修改现有配置，请参考：
- `simple_knowledge_manager.py` - 知识管理器实现
- `auxiliary_data_manager.py` - 辅助数据管理接口  
- `knowledge_management_guide.md` - 详细使用指南