# 伊利NPS调研报告分析API - V2需求文档

## 文档信息

**项目名称**: 伊利NPS调研报告分析API V2  
**客户**: 伊利集团  
**创建日期**: 2025年01月10日  
**文档状态**: 需求收集中  
**版本**: Draft v0.1

---

## 1. 项目背景

### 1.1 业务背景
伊利集团作为中国乳制品行业领导者，需要通过NPS (Net Promoter Score) 调研深入了解客户满意度，为产品改进和市场策略提供数据支撑。

### 1.2 业务流程
```
伊利设计NPS调研问卷 → 收集客户反馈 → 基本统计处理 → 调用AI分析API → 生成JSON分析数据 → 伊利生成最终报告
```

### 1.3 API职责范围
**我们负责的分析部分**:
- ✅ **NPS分布分析**: 推荐者/被动者/批评者分布统计
- ✅ **推荐原因分析**: 正面选项的统计和洞察
- ✅ **不推荐原因分析**: 负面选项的统计和问题识别
- ✅ **开放题分析**: 填空题的文本挖掘和主题提取
- ✅ **综合洞察生成**: 维度分析、趋势洞察、改进建议
- ✅ **JSON数据输出**: 结构化分析结果
- ✅ **HTML报告**: 可选的可视化报告

**伊利负责的部分**:
- ❌ 问卷设计和数据收集
- ❌ 基本统计预处理
- ❌ 最终报告的整合和发布

---

## 2. 特殊需求与约束

### 2.1 输出格式要求
- **JSON格式**: 类似V1的结构化JSON，支持程序化处理
- **HTML报告**: 包含图表和可视化，支持高管查看
- **格式一致性**: 与现有系统兼容，便于集成

### 2.2 部署约束
- **内网部署**: 必须在伊利内部网络运行
- **安全合规**: 符合企业数据安全政策
- **离线运行**: 可能需要支持离线或半离线模式

### 2.3 企业集成要求
- **API接口**: RESTful API，支持现有调用方式
- **认证授权**: 企业级身份验证
- **日志审计**: 完整的操作日志记录

---

## 3. NPS问卷类型与结构分析

### 3.1 两种核心问卷类型

伊利设计了两种NPS调研问卷模板，分别针对不同的评估目标：

#### 3.1.1 NPS-系统（系统平台调研）
**目标**: 评估伊利内部系统平台（如小程序、数字化工具）的用户体验

**核心问题结构**:
```
Q1: 您向同事推荐XXX的可能性多大？ (0-10分NPS评分)
└── ≤7分 → Q2: 不推荐的原因（多选）
    ├── 操作复杂难上手
    ├── 界面内容不清晰  
    ├── 功能难找
    ├── 性能不稳定
    ├── 界面不好看
    ├── 功能不全
    ├── 内容没价值
    ├── 内容太有限
    ├── 内容更新滞后
    ├── 数据帮助不大
    ├── 应用与服务介绍不清晰
    ├── 活动单调
    └── 其他

└── 8-9分 → Q5: 期待提供哪些内容或数据（开放题）

└── 10分 → Q6: 推荐的原因（多选）
    ├── 容易上手
    ├── 界面清晰易理解
    ├── 能高效完成任务
    ├── 性能稳定
    ├── 界面美观
    ├── 功能完善
    ├── 内容质量高
    ├── 内容时效性高
    ├── 数据有帮助
    ├── 内容很丰富
    ├── 应用与服务介绍清晰
    ├── 活动丰富
    └── 其他

Q3: 对XXX还有哪些建议？（开放题）
```

#### 3.1.2 NPS-产品（产品线调研）
**目标**: 评估伊利具体产品线（安慕希、金典、舒化等）的客户满意度

**核心问题结构**:
```
Q1: 您向朋友或同事推荐我们的可能性多大？ (0-10分NPS评分)
└── ≤7分 → Q2: 不愿意推荐的主要因素（多选）
    ├── 不喜欢品牌或代言人、赞助综艺等宣传内容
    ├── 包装设计不好（不够醒目、美观，材质不好，不便携、不方便打开等）
    ├── 产品价格太贵，性价比不高
    ├── 促销活动不好（对赠品、活动力度/规则等不满意）
    ├── 产品口味口感不好
    ├── 饮用后感觉不舒服（身体有腹胀、腹泻等不良反应）
    ├── 产品品质不稳定性（发生变质、有异物等）
    ├── 没有感知到产品宣传的功能
    ├── 物流配送、门店导购、售后等服务体验不好
    └── 其他
    
    Q3: 不愿意推荐的具体原因是什么？（开放题）

└── ≥8分 → Q4: 愿意推荐的主要因素（多选）
    ├── 喜欢品牌或代言人、赞助综艺等宣传内容
    ├── 包装设计好（醒目、美观，材质好，便携、方便打开等）
    ├── 产品物有所值、性价比高
    ├── 对促销活动满意（赠品、活动力度/规则等）
    ├── 产品口味口感好
    ├── 饮用后体感舒适，无不良反应
    ├── 满意产品宣传的功能（促进消化、增强免疫、助睡眠等）
    ├── 物流配送、门店导购、售后等服务体验好
    └── 其他
    
    Q5: 愿意推荐的具体原因是什么？（开放题）
```

### 3.2 问卷变化与智能生成

**动态调整特点**:
- **目标导向**: 根据具体调研目标（系统vs产品）调整问题
- **AI智能生成**: 可能根据产品特性智能调整选项内容
- **条件跳转**: 基于NPS评分的智能问题路径
- **本土化设计**: 完全针对中国乳制品市场设计

### 3.3 分项报告需求明确

基于问卷结构，分项报告应包括：

#### 3.3.1 系统平台NPS报告
- **用户体验维度**: 操作便利性、界面设计、功能完整性
- **性能维度**: 系统稳定性、响应速度
- **内容维度**: 内容质量、时效性、丰富度
- **服务维度**: 应用介绍、活动设计

#### 3.3.2 产品NPS报告  
- **产品维度**: 口味口感、品质稳定性、功能感知
- **包装维度**: 设计美观、材质、便携性
- **品牌维度**: 品牌认知、代言人、营销活动
- **价格维度**: 性价比、促销满意度
- **服务维度**: 物流配送、售后服务

## 4. 数据输入与处理要求

### 4.1 输入数据格式

基于两种问卷类型，API需要处理的数据结构：

#### 4.1.1 NPS-系统数据格式
```json
{
  "survey_type": "system",
  "system_name": "伊利数字化平台XXX",
  "responses": [
    {
      "response_id": "unique_id",
      "Q1_nps_score": 8,
      "Q2_negative_reasons": ["操作复杂难上手", "界面内容不清晰"],
      "Q5_expectations": "希望增加数据可视化功能",
      "Q6_positive_reasons": ["界面清晰易理解", "功能完善"],
      "Q3_suggestions": "建议优化搜索功能"
    }
  ]
}
```

#### 4.1.2 NPS-产品数据格式
```json
{
  "survey_type": "product",
  "product_line": "安慕希",
  "responses": [
    {
      "response_id": "unique_id", 
      "Q1_nps_score": 9,
      "Q2_negative_factors": ["产品价格太贵，性价比不高"],
      "Q3_negative_details": "感觉比同类产品贵很多",
      "Q4_positive_factors": ["产品口味口感好", "包装设计好"],
      "Q5_positive_details": "口感丰富，包装方便携带"
    }
  ]
}
```

### 4.2 数据处理边界

**已确定的处理范围**:
- ✅ **输入**: 伊利已完成基本统计的结构化数据
- ✅ **NPS计算**: API负责重新计算和验证NPS分数
- ✅ **数据清洗**: API进行二次数据清洗和验证
- ✅ **智能分析**: 基于问卷结构进行深度AI分析

**待确认的处理细节**:
1. **数据质量验证**
   - [ ] 异常评分处理规则？
   - [ ] 缺失数据补全策略？
   - [ ] 数据一致性检查？

2. **分析深度要求**
   - [ ] 是否需要跨时间对比？
   - [ ] 是否需要细分人群分析？
   - [ ] 是否需要与行业基准对比？

### 4.3 分析组件详细定义

#### 4.3.1 NPS分布分析组件
```
输入: Q1评分数据 (0-10分)
输出:
- NPS总分计算 (推荐者% - 批评者%)
- 三类客户分布 (推荐者9-10分、被动者7-8分、批评者0-6分)
- 分布统计和可视化数据
- NPS等级评估 (优秀/良好/需改进)
```

#### 4.3.2 推荐原因分析组件 (正面反馈)
```
输入: Q4/Q6正面选项数据 + Q5正面开放题
分析内容:
- 选项频次统计和排序
- 维度归类 (产品/服务/品牌/价格等)
- 开放题主题提取和情感分析
- 优势识别和强化建议
```

#### 4.3.3 不推荐原因分析组件 (负面反馈)
```
输入: Q2负面选项数据 + Q3负面开放题  
分析内容:
- 问题频次统计和优先级排序
- 问题根因分析和分类
- 开放题痛点挖掘和情感分析
- 改进建议和行动计划
```

#### 4.3.4 开放题深度分析组件
```
输入: 所有填空题文本数据
AI分析技术:
- 中文NLP文本预处理
- 主题聚类和关键词提取
- 情感分析和意图识别
- 业务洞察和趋势发现
```

#### 4.3.5 综合洞察生成组件
```
整合分析:
- 跨维度关联分析
- 问题和优势的对比洞察
- 业务改进优先级排序
- 战略建议和具体行动计划
```

### 4.4 输出JSON结构定义

#### 4.4.1 系统平台NPS分析输出
- **用户体验分析**: 操作便利性、界面设计、功能易用性
- **系统性能分析**: 稳定性、响应速度、功能完整性  
- **内容价值分析**: 内容质量、时效性、丰富度
- **改进建议**: 基于用户反馈的系统优化建议

#### 4.4.2 产品NPS分析输出
- **产品核心分析**: 口味口感、品质稳定性、功能感知
- **包装体验分析**: 设计美观、材质品质、便携性
- **品牌营销分析**: 品牌认知、代言人效果、营销活动
- **价格价值分析**: 性价比、促销满意度、竞争力
- **服务体验分析**: 物流配送、售后服务、购买体验

### 4.4 性能与规模要求

**待确认的规模参数**:
1. **处理规模**
   - [ ] 单次分析问卷数量：100份？1000份？10000份？
   - [ ] 并发处理能力要求？
   - [ ] 响应时间要求：30秒？2分钟？

2. **调用模式**
   - [ ] 批量处理还是实时分析？
   - [ ] 日调用频率预估？
   - [ ] 高峰期并发需求？

---

## 5. 技术需求（基于V1分析）

### 5.1 架构优化方向
- **并行处理**: 解决V1线性架构效率问题
- **AI调用优化**: 减少不必要的LLM调用
- **配置外部化**: 支持业务规则灵活调整

### 5.2 AI能力要求
- **中文NLP**: 优化中文文本分析能力
- **业务理解**: 深入理解乳制品行业特点
- **竞争分析**: 识别和分析竞争对手提及

### 5.3 集成能力
- **数据格式适配**: 支持多种输入格式
- **API兼容性**: 与现有调用方式兼容
- **扩展性**: 支持未来功能扩展

---

## 6. JSON输出格式规范

### 6.1 分离式正负反馈分析结构
```json
{
  "metadata": {
    "report_id": "NPS-2025-01-10-1430",
    "analysis_timestamp": "2025-01-10T14:30:00Z",
    "survey_type": "system|product", 
    "target_name": "伊利数字化平台/安慕希",
    "total_responses": 1250,
    "api_version": "v2.0",
    "processing_time_seconds": 45.6,
    "system_version": "2.0.0",
    "analysis_scope": "comprehensive_nps_analysis"
  },
  
  "executive_summary": {
    "overall_nps_score": 32.5,
    "nps_grade": "良好",
    "key_findings": [
      "产品口味获得高度认可，82%满意度",
      "价格敏感度是主要痛点，影响37.5%不推荐用户",
      "包装设计存在两极化反馈"
    ],
    "strategic_impact": "中等积极，有明确改进方向",
    "business_health_assessment": "总体健康，需关注价格策略"
  },
  
  "quantitative_analysis": {
    "nps_metrics": {
      "overall_nps_score": 32.5,
      "nps_grade": "良好",
      "promoters": {"count": 412, "percentage": 33.0, "score_range": "9-10"},
      "passives": {"count": 481, "percentage": 38.5, "score_range": "7-8"},
      "detractors": {"count": 357, "percentage": 28.5, "score_range": "0-6"}
    },
    "statistical_confidence": {
      "confidence_level": "中等",
      "margin_of_error": "±5%",
      "sample_size": 1250
    },
    "regional_breakdown": {
      "华东": {"count": 456, "nps": 35.2},
      "华北": {"count": 378, "nps": 29.8},
      "华南": {"count": 416, "nps": 34.1}
    }
  },
  
  "positive_insights_analysis": {
    "satisfaction_drivers": {
      "multiple_choice_analysis": {
        "top_reasons": [
          {
            "reason": "产品口味口感好",
            "count": 189,
            "percentage": 45.9,
            "dimension": "产品核心",
            "satisfaction_impact": 0.89
          },
          {
            "reason": "包装设计好",
            "count": 127,
            "percentage": 30.8,
            "dimension": "包装体验",
            "satisfaction_impact": 0.76
          }
        ],
        "dimension_performance": {
          "产品核心": {"mentions": 256, "satisfaction": 0.85, "strength_level": "高"},
          "包装体验": {"mentions": 189, "satisfaction": 0.78, "strength_level": "中高"},
          "品牌营销": {"mentions": 145, "satisfaction": 0.71, "strength_level": "中"}
        }
      }
    },
    "positive_open_text_analysis": {
      "source_questions": ["Q5: 您愿意推荐我们的具体原因是什么？", "Q6推荐原因开放题"],
      "themes_extraction": [
        {
          "theme": "口感层次丰富",
          "mentions": 78,
          "sentiment_score": 0.92,
          "key_phrases": ["层次感强", "口感丰富", "味道醇厚", "香浓顺滑"],
          "representative_quotes": [
            "口感很棒，有很好的层次感，每一口都有惊喜",
            "味道丰富不单调，比其他品牌更有特色",
            "入口顺滑，奶香浓郁，回味悠长"
          ],
          "business_implications": ["强化口感差异化优势", "在营销中突出层次感"]
        },
        {
          "theme": "包装美观便携",
          "mentions": 56,
          "sentiment_score": 0.85,
          "key_phrases": ["设计精美", "方便携带", "高端感", "颜值很高"],
          "representative_quotes": [
            "包装很精美，拿得出手，送人也很体面",
            "便携性很好，出门带着方便",
            "包装设计有档次，看起来就很高端"
          ],
          "business_implications": ["继续投资包装设计", "强化高端品牌形象"]
        },
        {
          "theme": "品质信赖感",
          "mentions": 43,
          "sentiment_score": 0.88,
          "key_phrases": ["质量可靠", "大品牌", "安全放心", "值得信赖"],
          "representative_quotes": [
            "伊利是大品牌，质量有保障，喝着放心",
            "一直信赖伊利的品质，从小就喝",
            "品质稳定，每次购买都很满意"
          ],
          "business_implications": ["强化品牌信赖度传播", "突出历史底蕴"]
        }
      ],
      "emotional_intensity_analysis": {
        "high_advocacy": {
          "count": 89,
          "typical_expressions": ["强烈推荐", "一定要试试", "必买产品"],
          "loyalty_indicators": ["长期购买", "家人都在喝", "不会换品牌"]
        },
        "moderate_satisfaction": {
          "count": 156,
          "typical_expressions": ["还不错", "比较满意", "会考虑回购"],
          "improvement_areas": ["希望更多口味", "价格更优惠一些"]
        }
      },
      "word_frequency_analysis": {
        "top_positive_keywords": [
          {"word": "好喝", "frequency": 124, "sentiment": 0.91},
          {"word": "香浓", "frequency": 89, "sentiment": 0.88},
          {"word": "顺滑", "frequency": 76, "sentiment": 0.85},
          {"word": "高端", "frequency": 67, "sentiment": 0.83}
        ]
      }
    },
    "competitive_advantages": [
      {
        "advantage": "口味差异化优势",
        "evidence": "78次开放题提及口感层次",
        "vs_competitors": "相比蒙牛产品口感更有层次感",
        "market_position": "领先",
        "sustainability": "高"
      },
      {
        "advantage": "品牌信赖度",
        "evidence": "43次提及品质信赖",
        "vs_competitors": "品牌历史和信赖度明显领先",
        "market_position": "领先",
        "sustainability": "高"
      }
    ]
  },
  
  "negative_insights_analysis": {
    "dissatisfaction_drivers": {
      "multiple_choice_analysis": {
        "top_issues": [
          {
            "issue": "产品价格太贵，性价比不高",
            "count": 134,
            "percentage": 37.5,
            "severity": "高",
            "dimension": "价格价值",
            "churn_risk": 0.85
          },
          {
            "issue": "包装设计不好",
            "count": 78,
            "percentage": 21.8,
            "severity": "中",
            "dimension": "包装体验",
            "churn_risk": 0.45
          },
          {
            "issue": "产品口味口感不好",
            "count": 56,
            "percentage": 15.7,
            "severity": "高",
            "dimension": "产品核心",
            "churn_risk": 0.78
          }
        ],
        "dimension_weaknesses": {
          "价格价值": {"mentions": 198, "dissatisfaction": 0.82, "urgency": "高"},
          "促销活动": {"mentions": 89, "dissatisfaction": 0.67, "urgency": "中"},
          "购买渠道": {"mentions": 56, "dissatisfaction": 0.54, "urgency": "中"}
        }
      }
    },
    "negative_open_text_analysis": {
      "source_questions": ["Q3: 您不愿意推荐我们的具体原因是什么？", "Q3建议开放题"],
      "pain_points_extraction": [
        {
          "pain_point": "价格偏高缺乏性价比",
          "mentions": 89,
          "impact_score": 0.94,
          "sentiment_intensity": -0.85,
          "key_phrases": ["太贵了", "性价比不高", "价格偏高", "比XX贵很多"],
          "representative_quotes": [
            "比同类产品贵太多，性价比真的不高",
            "一盒要XX元，感觉不值这个价",
            "希望能便宜一些，现在真的买不起",
            "蒙牛的类似产品便宜好几块，效果差不多"
          ],
          "root_cause_analysis": [
            "与竞品价格对比悬殊",
            "促销活动覆盖面不够",
            "消费者价值感知不强",
            "经济环境影响购买力"
          ],
          "business_implications": ["重新评估定价策略", "加强价值传播", "增加促销频次"]
        },
        {
          "pain_point": "口味不符合个人偏好",
          "mentions": 67,
          "impact_score": 0.76,
          "sentiment_intensity": -0.72,
          "key_phrases": ["太甜了", "口感不好", "不喜欢这个味道", "有异味"],
          "representative_quotes": [
            "太甜了，喝不习惯，感觉齁得慌",
            "口感有点粘稠，不如以前的顺滑",
            "有股奇怪的味道，可能是添加剂的问题",
            "和广告宣传的不一样，失望"
          ],
          "root_cause_analysis": [
            "口味偏好地域差异",
            "配方调整引起争议",
            "质量控制不够稳定",
            "消费者期望与实际差距"
          ],
          "business_implications": ["口味本地化调研", "质量控制加强", "配方优化"]
        },
        {
          "pain_point": "包装环保和实用性问题",
          "mentions": 45,
          "impact_score": 0.63,
          "sentiment_intensity": -0.58,
          "key_phrases": ["不环保", "难打开", "包装浪费", "不方便"],
          "representative_quotes": [
            "包装太复杂，撕开很困难，设计不人性化",
            "过度包装，不够环保，现在都提倡绿色消费",
            "包装容易破损，运输过程中经常漏",
            "希望使用可回收材料，更环保一些"
          ],
          "root_cause_analysis": [
            "包装设计用户体验不佳",
            "环保意识提升但产品未跟上",
            "包装结构设计缺陷",
            "材质选择考虑不全面"
          ],
          "business_implications": ["包装结构优化", "环保材料升级", "用户体验改进"]
        }
      ],
      "emotional_intensity_analysis": {
        "high_frustration": {
          "count": 67,
          "typical_expressions": ["太失望了", "再也不买了", "浪费钱"],
          "churn_indicators": ["已经换品牌", "不会推荐", "后悔购买"]
        },
        "moderate_dissatisfaction": {
          "count": 134,
          "typical_expressions": ["不太满意", "有待改进", "希望更好"],
          "retention_possibility": ["如果改进会考虑", "期待新产品", "价格合适会买"]
        }
      },
      "competitor_comparison_mentions": [
        {
          "competitor": "蒙牛",
          "comparison_context": "价格更便宜",
          "mentions": 34,
          "typical_quotes": ["蒙牛的XX产品便宜3块钱", "蒙牛促销更多"]
        },
        {
          "competitor": "光明",
          "comparison_context": "口感更好",
          "mentions": 23,
          "typical_quotes": ["光明的口感更自然", "光明没有添加剂味道"]
        }
      ],
      "word_frequency_analysis": {
        "top_negative_keywords": [
          {"word": "贵", "frequency": 89, "sentiment": -0.88},
          {"word": "甜", "frequency": 45, "sentiment": -0.72},
          {"word": "失望", "frequency": 34, "sentiment": -0.91},
          {"word": "不值", "frequency": 28, "sentiment": -0.85}
        ]
      }
    },
    "improvement_priorities": [
      {
        "area": "价格策略优化",
        "urgency": "高",
        "estimated_impact": "可提升NPS 8-12分",
        "implementation_complexity": "中等",
        "timeline": "1-3个月",
        "evidence": "89次开放题痛点提及"
      },
      {
        "area": "口味配方调整",
        "urgency": "中高", 
        "estimated_impact": "可提升NPS 4-6分",
        "implementation_complexity": "高",
        "timeline": "3-6个月",
        "evidence": "67次口味相关负面反馈"
      },
      {
        "area": "包装用户体验",
        "urgency": "中",
        "estimated_impact": "可提升NPS 2-4分",
        "implementation_complexity": "低",
        "timeline": "1-2个月",
        "evidence": "45次包装问题反馈"
      }
    ]
  },
  
  "business_intelligence": {
    "product_mapping": {
      "mention_mapping": [
        {
          "mentioned_name": "安慕希",
          "official_product": "安慕希希腊风味酸奶",
          "product_category": "酸奶",
          "product_line": "高端",
          "mention_data": {"mentions": 156, "sentiment": "正面"},
          "confidence": 1.0
        }
      ]
    },
    "competitor_analysis": {
      "total_competitor_mentions": 89,
      "unique_competitors": 4,
      "competitor_threats": {
        "蒙牛": {"mentions": 34, "threat_level": "中等", "context": "价格对比"},
        "光明": {"mentions": 23, "threat_level": "低", "context": "产品对比"}
      },
      "competitive_pressure": "中等"
    },
    "market_trends": [
      {
        "trend_id": "health_wellness",
        "trend_name": "健康意识趋势",
        "description": "消费者更关注营养价值和健康功能",
        "evidence": "67次提及无糖、低脂、营养、健康",
        "business_impact": "高",
        "strength": "强"
      },
      {
        "trend_id": "price_sensitivity",
        "trend_name": "价格敏感度上升",
        "description": "消费者对价格更加敏感，关注性价比",
        "evidence": "134次价格相关负面反馈",
        "business_impact": "高",
        "strength": "强"
      }
    ]
  },
  
  "integrated_strategic_insights": {
    "strengths_vs_weaknesses": {
      "core_strengths": [
        {"strength": "产品品质优势", "evidence": "口味满意度85%", "可持续性": "高"},
        {"strength": "品牌认知度", "evidence": "品牌提及率78%", "可持续性": "中高"}
      ],
      "critical_weaknesses": [
        {"weakness": "价格竞争力", "impact": "影响37.5%客户", "紧急程度": "高"},
        {"weakness": "促销策略", "impact": "影响21%客户", "紧急程度": "中"}
      ]
    },
    "risk_opportunities_matrix": {
      "high_impact_opportunities": [
        {"opportunity": "健康功能强化", "市场潜力": "大", "实施难度": "中"},
        {"opportunity": "价值传播优化", "市场潜力": "大", "实施难度": "低"}
      ],
      "major_risks": [
        {"risk": "价格敏感客户流失", "概率": "中高", "影响": "高"},
        {"risk": "竞争对手价格战", "概率": "中", "影响": "中高"}
      ]
    },
    "strategic_recommendations": {
      "immediate_actions": [
        {
          "action": "启动价格策略评估",
          "timeline": "1-2周",
          "priority": "高",
          "expected_outcome": "缓解价格压力，提升性价比认知"
        }
      ],
      "medium_term_plans": [
        {
          "plan": "差异化产品线布局",
          "timeline": "2-4月",
          "investment": "中等",
          "success_metrics": "NPS提升5-8分，市场份额增长2%"
        }
      ],
      "long_term_strategy": [
        {
          "strategy": "品牌价值重塑",
          "timeline": "6-12月",
          "focus_areas": ["健康价值强化", "情感连接深化", "价格价值平衡"]
        }
      ]
    }
  },
  
  "data_quality_assessment": {
    "overall_quality_metrics": {
      "overall_quality_score": 8.5,
      "quality_grade": "优秀",
      "reliability_index": 0.89,
      "confidence_level": "高",
      "analysis_completeness": 0.92
    },
    "data_integrity_analysis": {
      "raw_data_quality": {
        "total_collected_responses": 1450,
        "valid_responses_after_cleaning": 1250,
        "data_completeness_rate": 0.86,
        "invalid_data_filtered": 200,
        "key_data_loss_reasons": [
          {"reason": "NPS评分超出范围", "count": 89},
          {"reason": "开放题回答无效", "count": 67},
          {"reason": "重复提交", "count": 44}
        ]
      },
      "response_quality_indicators": {
        "meaningful_text_responses": 0.78,
        "average_text_length": 45.6,
        "detailed_responses_ratio": 0.65,
        "generic_responses_ratio": 0.22,
        "spam_or_invalid_ratio": 0.13
      },
      "statistical_significance": {
        "sample_size_adequacy": "充足",
        "margin_of_error": "±3.2%",
        "confidence_interval": "95%",
        "statistical_power": 0.85,
        "effect_size_detectability": "中等以上"
      }
    },
    "analysis_credibility_assessment": {
      "methodology_validation": {
        "nps_calculation_accuracy": "标准",
        "text_analysis_methodology": "AI+专家验证",
        "sentiment_analysis_accuracy": 0.87,
        "theme_extraction_reliability": 0.82,
        "bias_detection_score": 0.91
      },
      "ai_analysis_confidence": {
        "overall_ai_confidence": 0.85,
        "positive_analysis_confidence": 0.89,
        "negative_analysis_confidence": 0.88,
        "neutral_analysis_confidence": 0.78,
        "cross_validation_consistency": 0.84
      },
      "expert_validation_results": {
        "nps_expert_score": 8.7,
        "linguistics_expert_score": 8.3,
        "business_expert_score": 8.9,
        "report_quality_expert_score": 8.6,
        "average_expert_validation": 8.6,
        "validation_consensus": "高度一致"
      }
    },
    "reliability_factors": {
      "temporal_consistency": {
        "analysis_timeframe": "2024年12月-2025年1月",
        "seasonal_bias_consideration": "已考虑节假日影响",
        "data_freshness": "最新30天数据",
        "trend_stability": "稳定"
      },
      "demographic_representation": {
        "age_distribution_balance": 0.78,
        "geographic_coverage": "全国主要城市",
        "income_level_representation": 0.82,
        "gender_balance": 0.85,
        "sampling_bias_score": 0.12
      },
      "contextual_validity": {
        "market_environment_consideration": "已纳入当前市场环境",
        "competitive_landscape_accuracy": "反映真实竞争态势",
        "economic_factors_impact": "已考虑消费环境变化",
        "external_events_influence": "已排除特殊事件影响"
      }
    },
    "limitation_disclosures": {
      "known_limitations": [
        {
          "limitation": "样本地域分布不均",
          "impact_level": "中等",
          "affected_analysis": "区域性洞察准确性",
          "mitigation": "增加权重调整"
        },
        {
          "limitation": "高收入群体样本偏少",
          "impact_level": "低",
          "affected_analysis": "价格敏感度分析",
          "mitigation": "补充定向调研"
        }
      ],
      "data_collection_constraints": [
        "在线问卷可能存在自选择偏差",
        "开放题回答质量参差不齐",
        "部分用户可能存在社会期望偏差"
      ],
      "analytical_assumptions": [
        "假设用户回答真实反映内心想法",
        "假设NPS评分与实际推荐行为正相关",
        "假设文本分析能准确捕捉情感倾向"
      ]
    },
    "quality_improvement_recommendations": [
      {
        "area": "数据收集质量",
        "current_score": 7.8,
        "target_score": 8.5,
        "improvement_actions": [
          "优化问卷设计降低无效回答",
          "增加数据验证规则",
          "引入多渠道数据收集"
        ]
      },
      {
        "area": "分析准确性",
        "current_score": 8.5,
        "target_score": 9.0,
        "improvement_actions": [
          "增加人工标注样本",
          "优化AI模型参数",
          "建立分析结果验证机制"
        ]
      }
    ],
    "report_usage_guidelines": {
      "high_confidence_findings": [
        "整体NPS得分及分布",
        "主要满意度驱动因素",
        "核心不满意原因",
        "价格敏感度趋势"
      ],
      "moderate_confidence_findings": [
        "细分人群差异分析",
        "竞争对手比较洞察",
        "新兴市场趋势预测"
      ],
      "usage_precautions": [
        "建议结合其他数据源验证关键发现",
        "重要决策前建议进行补充调研",
        "注意时效性，建议定期更新分析"
      ],
      "decision_support_level": {
        "strategic_decisions": "中高支撑度",
        "tactical_adjustments": "高支撑度", 
        "operational_changes": "高支撑度",
        "investment_decisions": "中等支撑度，需补充数据"
      }
    }
  }
}
```

### 6.2 具体字段需求
**待客户确认**:
- [ ] 需要哪些一级字段？
- [ ] 数据结构深度要求？
- [ ] 是否需要与现有系统字段对应？
- [ ] 特殊业务字段需求？

---

## 7. HTML报告需求

### 7.1 基本要求
- **可视化图表**: NPS分布、趋势分析、对比图表
- **中文界面**: 完全中文化的报告界面
- **打印友好**: 支持打印和PDF导出
- **响应式设计**: 支持不同设备查看

### 7.2 内容结构
- **执行摘要**: 关键指标和核心发现
- **详细分析**: 分项分析结果
- **业务洞察**: AI生成的战略建议
- **附录**: 技术说明和数据来源

---

## 8. 部署和运维需求

### 8.1 部署环境
- **操作系统**: Linux/Docker支持
- **网络环境**: 伊利内网，可能需要VPN访问
- **资源要求**: CPU/内存/存储需求待评估

### 8.2 监控和维护
- **健康检查**: API健康状态监控
- **性能监控**: 响应时间、成功率监控
- **日志管理**: 完整的审计日志
- **错误处理**: 详细的错误信息和恢复机制

---

## 9. 风险和约束

### 9.1 技术风险
- **AI模型依赖**: 对外部AI服务的依赖风险
- **数据安全**: 客户数据保护要求
- **性能瓶颈**: 大数据量处理能力

### 9.2 业务约束
- **时间要求**: 项目交付时间限制
- **预算约束**: 开发和部署成本控制
- **合规要求**: 企业数据处理合规性

---

## 10. 待确认问题清单

### 10.1 高优先级问题
1. **分项报告的具体维度定义**
2. **输入数据的处理状态和格式**
3. **JSON输出的详细字段要求**
4. **处理规模和性能要求**
5. **部署环境的具体配置**

### 10.2 中优先级问题
1. **HTML报告的具体内容要求**
2. **与现有系统的集成方式**
3. **用户权限和访问控制**
4. **数据备份和恢复策略**

### 10.3 低优先级问题
1. **未来功能扩展规划**
2. **多语言支持需求**
3. **第三方系统集成**
4. **高级分析功能需求**

---

## 11. 下一步行动

### 11.1 需求澄清会议
- **参与方**: 伊利业务方、技术方、开发团队
- **议题**: 确认高优先级问题
- **输出**: 明确的功能规格说明

### 11.2 技术调研
- **数据格式分析**: 分析伊利现有数据格式
- **性能基准测试**: 确定性能目标
- **架构设计**: 基于V1优化的V2架构

### 11.3 原型开发
- **MVP功能**: 核心分析功能
- **接口设计**: API接口定义
- **演示准备**: 功能演示和验证

---

**文档状态**: 🔄 持续更新中  
**负责人**: 开发团队  
**审核**: 待客户确认  
**下次更新**: 需求澄清会议后