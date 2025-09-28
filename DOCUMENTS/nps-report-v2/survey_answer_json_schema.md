# Survey Answer JSON Schema Design Document

## 概述

本文档定义了NPS报告分析系统V2的问卷数据输入格式规范，支持系统平台和产品两种调研类型的统一JSON格式。

## 设计原则

1. **灵活性**: 架构适配不同调研类型，保持结构一致性
2. **完整性**: 所有原始信息均可从JSON完整重建
3. **扩展性**: 易于添加新的调研类型或问题格式
4. **标准兼容**: 使用一致的数据类型和ISO标准
5. **客户端定制**: 允许格式微调，保留核心数据结构

## 核心架构

### 顶层结构

```json
{
  "survey_metadata": {
    "survey_type": "system_platform" | "product_nps",
    "survey_title": "string",
    "data_source": "string",
    "export_timestamp": "ISO 8601 datetime",
    "version": "2.0.0"
  },
  "survey_config": {
    "nps_question": {
      "question_id": "Q1",
      "question_text": "string",
      "scale": {
        "min": 0,
        "max": 10,
        "format": "分值制"
      }
    },
    "factor_questions": {
      "negative_factors": {
        "question_id": "Q2",
        "question_text": "string",
        "factor_list": ["string array"]
      },
      "positive_factors": {
        "question_id": "Q4|Q6",
        "question_text": "string", 
        "factor_list": ["string array"]
      }
    },
    "open_ended_questions": [
      {
        "question_id": "string",
        "question_text": "string",
        "question_type": "expectation" | "suggestion" | "specific_reason"
      }
    ]
  },
  "response_data": [
    {
      "response_metadata": {
        "user_id": "string",
        "response_id": "string",
        "response_type": "正式" | "测试",
        "distribution_method": "string",
        "status": "已完成" | "进行中",
        "timing": {
          "start_time": "datetime",
          "submit_time": "datetime|null",
          "duration": "string"
        },
        "annotation": {
          "ai_status": "string",
          "ai_reason": "string",
          "manual_status": "string", 
          "manual_reason": "string"
        }
      },
      "nps_score": {
        "value": "integer|null",
        "raw_value": "string",
        "category": "promoter|passive|detractor|null"
      },
      "factor_responses": {
        "negative_factors": {
          "selected": ["string array"],
          "other_specified": "string|null"
        },
        "positive_factors": {
          "selected": ["string array"], 
          "other_specified": "string|null"
        }
      },
      "open_responses": {
        "expectations": "string|null",
        "suggestions": "string|null",
        "specific_reasons": {
          "negative": "string|null",
          "positive": "string|null"
        }
      }
    }
  ]
}
```

## 字段说明

### survey_metadata（调研元数据）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| survey_type | string | ✓ | 调研类型："system_platform" 或 "product_nps" |
| survey_title | string | ✓ | 调研标题 |
| data_source | string | ✓ | 数据来源文件名 |
| export_timestamp | string | ✓ | 导出时间（ISO 8601格式） |
| version | string | ✓ | 架构版本号 |

### survey_config（调研配置）
定义问卷的结构和问题配置

#### nps_question（NPS主问题）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question_id | string | ✓ | 问题编号 |
| question_text | string | ✓ | 问题文本 |
| scale | object | ✓ | 评分量表配置 |

#### factor_questions（因子问题）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| negative_factors | object | ✓ | 负面因子问题配置 |
| positive_factors | object | ✓ | 正面因子问题配置 |

#### open_ended_questions（开放性问题）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| question_id | string | ✓ | 问题编号 |
| question_text | string | ✓ | 问题文本 |
| question_type | string | ✓ | 问题类型：expectation/suggestion/specific_reason |

### response_data（响应数据）
包含所有受访者的回答数据

#### response_metadata（响应元数据）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| user_id | string | ✓ | 用户ID |
| response_id | string | ✓ | 作答ID |
| response_type | string | ✓ | 作答类型：正式/测试 |
| distribution_method | string | ✓ | 投放方式 |
| status | string | ✓ | 作答状态：已完成/进行中 |
| timing | object | ✓ | 时间信息 |
| annotation | object | ✓ | 标记信息 |

#### nps_score（NPS得分）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| value | integer/null | ✓ | 数值分数（0-10） |
| raw_value | string | ✓ | 原始值（如"5分"） |
| category | string/null | ✓ | NPS分类：promoter/passive/detractor |

#### factor_responses（因子响应）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| negative_factors | object | ✓ | 负面因子选择 |
| positive_factors | object | ✓ | 正面因子选择 |

#### open_responses（开放回答）
| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| expectations | string/null | - | 期待内容 |
| suggestions | string/null | - | 建议内容 |
| specific_reasons | object | - | 具体原因 |

## 示例数据

### 系统平台调研示例

```json
{
  "survey_metadata": {
    "survey_type": "system_platform",
    "survey_title": "定量智能体-系统平台NPS调研模板",
    "data_source": "定量智能体-系统平台NPS调研模板_答案文本数据列表_202509101848.xlsx",
    "export_timestamp": "2025-09-10T18:48:00Z",
    "version": "2.0.0"
  },
  "survey_config": {
    "nps_question": {
      "question_id": "Q1",
      "question_text": "您向同事推荐XXXX的可能性多大？",
      "scale": {
        "min": 0,
        "max": 10,
        "format": "分值制"
      }
    },
    "factor_questions": {
      "negative_factors": {
        "question_id": "Q2",
        "question_text": "您不推荐XXX的原因有哪些？",
        "factor_list": [
          "操作复杂难上手",
          "界面内容不清晰", 
          "功能难找",
          "性能不稳定",
          "界面不好看",
          "性能不全",
          "内容没价值",
          "内容太有限",
          "内容更新滞后",
          "数据帮助不大",
          "应用与服务介绍不清晰",
          "活动单调",
          "其他"
        ]
      },
      "positive_factors": {
        "question_id": "Q6",
        "question_text": "您推荐XXX的原因有哪些？",
        "factor_list": [
          "容易上手",
          "界面清晰易理解",
          "能高效完成任务",
          "性能稳定", 
          "界面美观",
          "功能完善",
          "内容质量高",
          "内容时效性高",
          "数据有帮助",
          "内容很丰富",
          "应用与服务介绍清晰",
          "活动丰富",
          "其他"
        ]
      }
    },
    "open_ended_questions": [
      {
        "question_id": "Q5",
        "question_text": "您还期待XXX提供哪些方面的内容或数据？",
        "question_type": "expectation"
      },
      {
        "question_id": "Q3", 
        "question_text": "您对XXX还有哪些建议？",
        "question_type": "suggestion"
      }
    ]
  },
  "response_data": [
    {
      "response_metadata": {
        "user_id": "10",
        "response_id": "vb1oD4XQ",
        "response_type": "正式",
        "distribution_method": "链接二维码",
        "status": "已完成",
        "timing": {
          "start_time": "2025-09-01T16:51:47",
          "submit_time": "2025-09-01T16:52:20", 
          "duration": "33秒"
        },
        "annotation": {
          "ai_status": "未标记",
          "ai_reason": "",
          "manual_status": "未标记",
          "manual_reason": ""
        }
      },
      "nps_score": {
        "value": 5,
        "raw_value": "5分",
        "category": "detractor"
      },
      "factor_responses": {
        "negative_factors": {
          "selected": ["活动单调"],
          "other_specified": null
        },
        "positive_factors": {
          "selected": [],
          "other_specified": null
        }
      },
      "open_responses": {
        "expectations": "暂无",
        "suggestions": "没有",
        "specific_reasons": {
          "negative": null,
          "positive": null
        }
      }
    }
  ]
}
```

### 产品调研示例

```json
{
  "survey_metadata": {
    "survey_type": "product_nps",
    "survey_title": "定量智能体-产品NPS调研模板", 
    "data_source": "定量智能体-产品NPS调研模板_答案文本数据列表_202509101906.xlsx",
    "export_timestamp": "2025-09-10T19:06:00Z",
    "version": "2.0.0"
  },
  "survey_config": {
    "nps_question": {
      "question_id": "Q1",
      "question_text": "您向朋友或同事推荐我们的可能性多大？",
      "scale": {
        "min": 0,
        "max": 10,
        "format": "分值制"
      }
    },
    "factor_questions": {
      "negative_factors": {
        "question_id": "Q2",
        "question_text": "您不愿意推荐我们的主要因素有哪些？",
        "factor_list": [
          "不喜欢品牌或代言人、赞助综艺等宣传内容",
          "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）",
          "产品价格太贵，性价比不高",
          "促销活动不好（如对赠品、活动力度/规则等不满意）",
          "产品口味口感不好",
          "饮用后感觉不舒服（如身体有腹胀、腹泻等不良反应）",
          "产品品质不稳定性（如发生变质、有异物等）",
          "没有感知到产品宣传的功能",
          "物流配送、门店导购、售后等服务体验不好",
          "其他"
        ]
      },
      "positive_factors": {
        "question_id": "Q4",
        "question_text": "您愿意推荐我们的主要因素有哪些？",
        "factor_list": [
          "喜欢品牌或代言人、赞助综艺等宣传内容",
          "包装设计好（如醒目、美观，材质好，便携、方便打开等）",
          "产品物有所值、性价比高",
          "对促销活动满意（如赠品、活动力度/规则等）",
          "产品口味口感好",
          "饮用后体感舒适，无不良反应",
          "满意产品宣传的功能（如促进消化、增强免疫、助睡眠等）",
          "物流配送、门店导购、售后等服务体验好",
          "其他"
        ]
      }
    },
    "open_ended_questions": [
      {
        "question_id": "Q3",
        "question_text": "您不愿意推荐我们的具体原因是什么？",
        "question_type": "specific_reason"
      },
      {
        "question_id": "Q5",
        "question_text": "您愿意推荐我们的具体原因是什么？", 
        "question_type": "specific_reason"
      }
    ]
  },
  "response_data": [
    {
      "response_metadata": {
        "user_id": "6",
        "response_id": "GkMbEwKa",
        "response_type": "正式",
        "distribution_method": "链接二维码",
        "status": "已完成",
        "timing": {
          "start_time": "2025-09-01T15:53:34",
          "submit_time": "2025-09-01T15:55:50",
          "duration": "2分钟15秒"
        },
        "annotation": {
          "ai_status": "未标记",
          "ai_reason": "",
          "manual_status": "未标记", 
          "manual_reason": ""
        }
      },
      "nps_score": {
        "value": 10,
        "raw_value": "10分",
        "category": "promoter"
      },
      "factor_responses": {
        "negative_factors": {
          "selected": [],
          "other_specified": null
        },
        "positive_factors": {
          "selected": ["产品物有所值、性价比高"],
          "other_specified": null
        }
      },
      "open_responses": {
        "expectations": null,
        "suggestions": null,
        "specific_reasons": {
          "negative": "",
          "positive": "口味比较多，选择很多"
        }
      }
    }
  ]
}
```

## NPS分类规则

### 分数分类
- **推荐者 (Promoter)**: 9-10分
- **中立者 (Passive)**: 7-8分  
- **贬损者 (Detractor)**: 0-6分

### 计算公式
```
NPS = (推荐者数量 - 贬损者数量) / 总响应数量 × 100
```

## 数据验证规则

### 必填字段验证
- survey_metadata中所有字段必填
- response_metadata中的关键字段必填
- nps_score.value必须为0-10范围内的整数

### 数据一致性验证
- NPS分数与category必须匹配
- 选中的因子必须存在于factor_list中
- 时间字段必须符合ISO 8601格式

### 业务逻辑验证
- 已完成状态的响应必须有submit_time
- 进行中状态的响应submit_time可为null
- 测试类型数据可单独标识和过滤

## 扩展指南

### 添加新调研类型
1. 在survey_type枚举中添加新类型
2. 在survey_config中定义对应的问题结构
3. 更新response_data结构以适配新问题类型

### 添加新字段
1. 在相应层级添加新字段定义
2. 更新验证规则
3. 确保向后兼容性

### 客户端定制
- 可修改question_text内容
- 可调整factor_list项目
- 可添加额外的metadata字段
- 必须保持核心结构不变

## 版本历史

- **v2.0.0** (2025-09-10): 初始版本，支持系统平台和产品NPS调研