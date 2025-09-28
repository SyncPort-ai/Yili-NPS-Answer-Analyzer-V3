# 伊利NPS报告分析器 API V2 文档

## 概述

伊利NPS报告分析器V2是基于七智能体架构的高级NPS（Net Promoter Score）分析系统，为伊利集团提供深度客户洞察和商业智能分析。

> **🔥 伊调研系统重点提示**: 本API的核心价值在于每个智能体返回的 `insight_summary` 字段，这些字段包含直接可用的业务洞察、营销建议和战略指导，是伊调研系统的主要数据源。

---

## API 基本信息

**API 基础URL**: `http://ai-algorithm-ainps-report-dev.dcin-test.digitalyili.com`

**API 端点**: `/nps_report_v2`

**请求方法**: `POST`

**Content-Type**: `application/json`

**API版本**: `2.0`

---

## 接口说明

### POST /nps_report_v2

使用七智能体系统对伊利NPS调研数据进行全面分析，提供深度客户洞察和战略建议。

#### 功能特性
- ✅ 七智能体协同分析：NPS净值、分布、正面/负面因素、综合洞察
- ✅ AI驱动的深度洞察挖掘
- ✅ 商业智能和战略建议生成
- ✅ 支持产品NPS和系统平台NPS分析
- ✅ 中文优化的自然语言处理

---

## 请求参数

### 请求格式

```json
{
  "yili_survey_data_input": {
    "base_analysis_result": "string",
    "cross_analysis_result": "string | null",
    "kano_analysis_result": "string | null",
    "psm_analysis_result": "string | null", 
    "maxdiff_analysis_result": "string | null",
    "nps_analysis_result": "string",
    "data_list": [
      {
        "样本编码": "string",
        "作答类型": "string",
        "AI标记状态": "string",
        "AI标记原因": "string",
        "人工标记状态": "string",
        "人工标记原因": "string",
        "作答ID": "string",
        "投放方式": "string", 
        "作答状态": "string",
        "答题时间": "string",
        "提交时间": "string",
        "作答时长": "string",
        "Q1您向朋友或同事推荐我们的可能性多大？": "string",
        "Q2 您不愿意推荐我们的主要因素有哪些？": {
          "选项1": "string",
          "选项2": "string"
        },
        "Q3 您不愿意推荐我们的具体原因是什么？": "string",
        "Q4 您愿意推荐我们的主要因素有哪些？": {
          "选项1": "string", 
          "选项2": "string"
        },
        "Q5 您愿意推荐我们的具体原因是什么？": "string"
      }
    ]
  }
}
```

### 参数详细说明

#### 根级别参数

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `yili_survey_data_input` | Object | ✅ | 伊利问卷数据输入格式的根对象 |

#### yili_survey_data_input 对象参数

| 字段名 | 类型 | 必填 | 描述 |
|--------|------|------|------|
| `base_analysis_result` | String | ✅ | 基础分析结果，包含初步的NPS分析总结 |
| `cross_analysis_result` | String \| null | ❌ | 交叉分析结果，可为null |
| `kano_analysis_result` | String \| null | ❌ | Kano模型分析结果，可为null |
| `psm_analysis_result` | String \| null | ❌ | PSM价格敏感度分析结果，可为null |
| `maxdiff_analysis_result` | String \| null | ❌ | MaxDiff分析结果，可为null |
| `nps_analysis_result` | String | ✅ | NPS专项分析结果 |
| `data_list` | Array | ✅ | 问卷回答数据列表 |

#### data_list 数组元素参数

| 字段名 | 类型 | 必填 | 描述 | 示例 |
|--------|------|------|------|------|
| `样本编码` | String | ✅ | 样本的唯一标识码 | "8" |
| `作答类型` | String | ✅ | 作答类型 | "正式" |
| `AI标记状态` | String | ✅ | AI自动标记状态 | "未标记" |
| `AI标记原因` | String | ❌ | AI标记的原因说明 | "" |
| `人工标记状态` | String | ✅ | 人工标记状态 | "未标记" |
| `人工标记原因` | String | ❌ | 人工标记的原因说明 | "" |
| `作答ID` | String | ✅ | 作答的唯一标识 | "8Gwk7wzV" |
| `投放方式` | String | ✅ | 问卷的投放方式 | "链接二维码" |
| `作答状态` | String | ✅ | 作答完成状态 | "已完成" |
| `答题时间` | String | ✅ | 开始答题的时间 | "2025-09-01 16:49:34" |
| `提交时间` | String | ✅ | 提交答案的时间 | "2025-09-01 16:51:19" |
| `作答时长` | String | ✅ | 完成问卷的时长 | "1分钟45秒" |
| `Q1您向朋友或同事推荐我们的可能性多大？` | String | ✅ | NPS核心问题，评分0-10分 | "5分" |
| `Q2 您不愿意推荐我们的主要因素有哪些？` | Object | ❌ | 负面因素多选题 | 详见下方说明 |
| `Q3 您不愿意推荐我们的具体原因是什么？` | String | ❌ | 负面因素开放回答 | "不了解产品" |
| `Q4 您愿意推荐我们的主要因素有哪些？` | Object | ❌ | 正面因素多选题 | 详见下方说明 |
| `Q5 您愿意推荐我们的具体原因是什么？` | String | ❌ | 正面因素开放回答 | "口感好" |

#### Q2/Q4 多选题对象格式

多选题对象的每个字段代表一个选项，值为选项文本（选中）或"-"（未选中）：

```json
{
  "不喜欢品牌或代言人、赞助综艺等宣传内容": "不喜欢品牌或代言人、赞助综艺等宣传内容",
  "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）": "-",
  "产品价格太贵，性价比不高": "-",
  "促销活动不好（如对赠品、活动力度/规则等不满意）": "-",
  "产品口味口感不好": "-",
  "饮用后感觉不舒服（如身体有腹胀、腹泻等不良反应）": "-",
  "产品品质不稳定性（如发生变质、有异物等）": "-",
  "没有感知到产品宣传的功能": "-",
  "物流配送、门店导购、售后等服务体验不好": "-",
  "其他": "-"
}
```

---

## 请求示例

### cURL 请求示例

```bash
curl -X POST "http://ai-algorithm-ainps-report-dev.dcin-test.digitalyili.com/nps_report_v2" \
  -H "Content-Type: application/json" \
  -d '{
    "yili_survey_data_input": {
      "base_analysis_result": "基于样本的分析结果：1. NPS值为-25%，用户满意度较低。2. 推荐者占比25%，中立者占比25%，贬损者占比50%。",
      "cross_analysis_result": null,
      "kano_analysis_result": null,
      "psm_analysis_result": null,
      "maxdiff_analysis_result": null,
      "nps_analysis_result": "1. NPS值为-25%，表明用户整体满意度较低。2. 贬损者占比50%，需优先解决核心问题。",
      "data_list": [
        {
          "样本编码": "8",
          "作答类型": "正式",
          "AI标记状态": "未标记",
          "AI标记原因": "",
          "人工标记状态": "未标记",
          "人工标记原因": "",
          "作答ID": "8Gwk7wzV",
          "投放方式": "链接二维码",
          "作答状态": "已完成",
          "答题时间": "2025-09-01 16:49:34",
          "提交时间": "2025-09-01 16:51:19", 
          "作答时长": "1分钟45秒",
          "Q1您向朋友或同事推荐我们的可能性多大？": "5分",
          "Q2 您不愿意推荐我们的主要因素有哪些？": {
            "不喜欢品牌或代言人、赞助综艺等宣传内容": "不喜欢品牌或代言人、赞助综艺等宣传内容",
            "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）": "-"
          },
          "Q3 您不愿意推荐我们的具体原因是什么？": "不了解产品",
          "Q4 您愿意推荐我们的主要因素有哪些？": {
            "喜欢品牌或代言人、赞助综艺等宣传内容": "-",
            "产品物有所值、性价比高": "产品物有所值、性价比高"
          },
          "Q5 您愿意推荐我们的具体原因是什么？": ""
        }
      ]
    }
  }'
```

### Python 请求示例

```python
import requests
import json

url = "http://ai-algorithm-ainps-report-dev.dcin-test.digitalyili.com/nps_report_v2"
headers = {
    "Content-Type": "application/json"
}

payload = {
    "yili_survey_data_input": {
        "base_analysis_result": "基于样本的分析结果：1. NPS值为-25%，用户满意度较低。",
        "cross_analysis_result": None,
        "kano_analysis_result": None,
        "psm_analysis_result": None, 
        "maxdiff_analysis_result": None,
        "nps_analysis_result": "1. NPS值为-25%，表明用户整体满意度较低。",
        "data_list": [
            {
                "样本编码": "8",
                "作答类型": "正式",
                "AI标记状态": "未标记",
                "作答ID": "8Gwk7wzV",
                "投放方式": "链接二维码",
                "作答状态": "已完成",
                "答题时间": "2025-09-01 16:49:34",
                "提交时间": "2025-09-01 16:51:19",
                "作答时长": "1分钟45秒",
                "Q1您向朋友或同事推荐我们的可能性多大？": "5分"
            }
        ]
    }
}

response = requests.post(url, headers=headers, data=json.dumps(payload))
print(response.json())
```

---

## 响应格式

### 成功响应

**状态码**: `200 OK`

**Content-Type**: `application/json`

### 响应结构

```json
{
  "status": "string",
  "message": "string", 
  "analysis_type": "string",
  "timestamp": "string",
  "data": {
    "timestamp": "string",
    "analysis_type": "string",
    "original_input": {
      "data_source": "string",
      "processed_responses": "number",
      "valid_responses": "number",
      "survey_metadata": {
        "survey_type": "string",
        "survey_title": "string",
        "data_source": "string",
        "analysis_results": {
          "base_analysis": "string",
          "nps_analysis": "string",
          "cross_analysis": "string | null",
          "kano_analysis": "string | null",
          "psm_analysis": "string | null",
          "maxdiff_analysis": "string | null"
        }
      }
    },
    "agent_analysis_results": [
      {
        "agent_name": "string",
        "question_context": "string",
        "input_data": {},
        "ai_analysis": {},
        "business_questions": ["string"],
        "insight_summary": ["string"],
        "summary_text": "string"
      }
    ],
    "supporting_data": {},
    "summary_statistics": {}
  }
}
```

### 响应参数详细说明

#### 根级别响应参数

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `status` | String | 请求处理状态，通常为"success" |
| `message` | String | 处理结果消息 |
| `analysis_type` | String | 分析类型标识 |
| `timestamp` | String | 响应时间戳 |
| `data` | Object | 详细的分析结果数据 |

#### data 对象参数

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `timestamp` | String | 分析时间戳 |
| `analysis_type` | String | 分析系统类型 |
| `original_input` | Object | 原始输入数据的处理摘要 |
| `agent_analysis_results` | Array | 七个智能体的分析结果 |
| `supporting_data` | Object | 支撑数据 |
| `summary_statistics` | Object | 汇总统计信息 |

#### agent_analysis_results 数组元素 (七智能体)

每个智能体结果包含：

| 字段名 | 类型 | 描述 |
|--------|------|------|
| `agent_name` | String | 智能体名称 |
| `question_context` | String | 分析的问题上下文 |
| `input_data` | Object | 输入数据摘要 |
| `ai_analysis` | Object | AI分析结果，包含详细洞察 |
| `business_questions` | Array | 生成的商业问题 |
| `insight_summary` | **Array** | **🎯 核心洞察总结（伊调研系统主要使用字段）** |
| `summary_text` | String | 分析结果摘要 |

> **💡 重要提示**: `insight_summary` 字段是伊调研系统的核心需求，包含每个智能体的关键业务洞察。

#### 七智能体与insight_summary详细说明

##### 智能体1: NPS净值分析智能体
- **功能**: 分析NPS净值和行业对标，提供客户忠诚度和品牌健康度评估
- **insight_summary示例**:
  ```json
  [
    "洞察1: 当前NPS净值显著低于行业基准，表明客户满意度和忠诚度存在严重问题，需要立即采取行动",
    "洞察2: 与主要竞争对手相比，伊利在客户体验和品牌感知方面存在明显劣势，亟需提升核心竞争力"
  ]
  ```

##### 智能体2: NPS分布分析智能体
- **功能**: 分析推荐者、中立者、贬损者分布，识别客户群体特征和转化机会
- **insight_summary示例**:
  ```json
  [
    "贬损者比例高可能导致市场份额流失，需优先处理",
    "强化推荐者忠诚度可提升品牌形象和口碑传播"
  ]
  ```

##### 智能体3: 正面多选题分析智能体
- **功能**: 分析正面因素选择模式，识别营销机会和产品优势
- **insight_summary示例**:
  ```json
  [
    "营销机会: 产品口味口感好 - 享受每一口的极致口感，伊利带给您无与伦比的味觉体验",
    "营销机会: 产品物有所值、性价比高 - 高品质，合理价格，伊利是您明智的选择",
    "营销机会: 喜欢品牌或代言人、赞助综艺等宣传内容 - 与您喜爱的明星一起，选择伊利，选择健康生活"
  ]
  ```

##### 智能体4: 正面填空题分析智能体
- **功能**: 分析正面开放回答，提取客户推荐的具体原因
- **insight_summary示例**:
  ```json
  [
    "数据缺失：推荐者未提供开放回答"
  ]
  ```

##### 智能体5: 负面多选题分析智能体
- **功能**: 分析负面因素分布，制定问题解决方案和优先级
- **insight_summary示例**:
  ```json
  [
    "解决方案: 产品价格太贵，性价比不高 - 优先级: 高",
    "解决方案: 没有感知到产品宣传的功能 - 优先级: 中",
    "解决方案: 不喜欢品牌或代言人、赞助综艺等宣传内容 - 优先级: 低"
  ]
  ```

##### 智能体6: 负面填空题分析智能体
- **功能**: 分析负面开放回答，识别客户不满的根本原因
- **insight_summary示例**:
  ```json
  [
    "数据缺失：非推荐者未提供开放回答"
  ]
  ```

##### 智能体7: 综合总结分析智能体
- **功能**: 整合前六个智能体的分析结果，提供战略建议和行动计划
- **insight_summary示例**:
  ```json
  [
    "战略洞察: 客户体验和品牌感知是NPS表现的核心驱动因素，亟需提升产品质量和优化客户服务",
    "核心建议: 短期内通过调研和优化服务流程解决问题，中期推出新产品并加强品牌营销，长期目标是提升NPS至50分",
    "预期影响: 通过实施上述措施，预计在12-24个月内显著提升客户满意度和品牌忠诚度，增强市场竞争力"
  ]
  ```

### Python 获取insight_summary案例代码

```python
import requests
import json
from typing import Dict, List, Any

class YiliNPSInsightExtractor:
    """伊利NPS洞察提取器 - 专门用于获取七智能体的insight_summary"""
    
    def __init__(self, api_url: str = "http://ai-algorithm-ainps-report-dev.dcin-test.digitalyili.com/nps_report_v2"):
        self.api_url = api_url
        self.headers = {"Content-Type": "application/json"}
    
    def call_nps_api(self, yili_survey_data: Dict[str, Any]) -> Dict[str, Any]:
        """调用NPS分析API"""
        try:
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                data=json.dumps(yili_survey_data),
                timeout=60
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise Exception(f"API调用失败: {e}")
    
    def extract_all_insights(self, api_response: Dict[str, Any]) -> Dict[str, List[str]]:
        """提取所有智能体的insight_summary"""
        insights = {}
        
        if api_response.get("status") != "success":
            raise Exception(f"API返回错误: {api_response.get('message', 'Unknown error')}")
        
        agent_results = api_response.get("data", {}).get("agent_analysis_results", [])
        
        for agent in agent_results:
            agent_name = agent.get("agent_name", "Unknown Agent")
            insight_summary = agent.get("insight_summary", [])
            insights[agent_name] = insight_summary
            
        return insights
    
    def extract_insights_by_type(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """按智能体类型分类提取insight_summary"""
        all_insights = self.extract_all_insights(api_response)
        
        categorized_insights = {
            "战略分析洞察": {
                "NPS净值分析": all_insights.get("NPS净值分析智能体", []),
                "NPS分布分析": all_insights.get("NPS分布分析智能体", [])
            },
            "营销洞察": {
                "正面因素营销机会": all_insights.get("正面多选题分析智能体", []),
                "正面开放回答": all_insights.get("正面填空题分析智能体", [])
            },
            "问题解决洞察": {
                "负面因素解决方案": all_insights.get("负面多选题分析智能体", []),
                "负面开放回答": all_insights.get("负面填空题分析智能体", [])
            },
            "综合战略洞察": {
                "总结建议": all_insights.get("综合总结分析智能体", [])
            }
        }
        
        return categorized_insights
    
    def format_insights_for_yidiaoyan(self, api_response: Dict[str, Any]) -> Dict[str, Any]:
        """格式化洞察数据，适配伊调研系统需求"""
        categorized = self.extract_insights_by_type(api_response)
        
        # 伊调研系统专用格式
        yidiaoyan_format = {
            "analysis_timestamp": api_response.get("timestamp", ""),
            "total_agents": len(api_response.get("data", {}).get("agent_analysis_results", [])),
            "strategic_insights": [],      # 战略级洞察
            "marketing_opportunities": [], # 营销机会
            "priority_solutions": [],      # 优先解决方案
            "comprehensive_plan": []       # 综合规划
        }
        
        # 战略级洞察
        for insight in categorized["战略分析洞察"]["NPS净值分析"]:
            yidiaoyan_format["strategic_insights"].append({
                "type": "NPS净值分析",
                "insight": insight
            })
        
        for insight in categorized["战略分析洞察"]["NPS分布分析"]:
            yidiaoyan_format["strategic_insights"].append({
                "type": "NPS分布分析", 
                "insight": insight
            })
        
        # 营销机会
        for insight in categorized["营销洞察"]["正面因素营销机会"]:
            if "营销机会" in insight:
                yidiaoyan_format["marketing_opportunities"].append({
                    "opportunity": insight.split(" - ")[0].replace("营销机会: ", ""),
                    "suggested_message": insight.split(" - ")[1] if " - " in insight else ""
                })
        
        # 优先解决方案
        for insight in categorized["问题解决洞察"]["负面因素解决方案"]:
            if "解决方案" in insight and "优先级" in insight:
                parts = insight.split(" - ")
                solution = parts[0].replace("解决方案: ", "")
                priority = parts[1].replace("优先级: ", "") if len(parts) > 1 else "中"
                yidiaoyan_format["priority_solutions"].append({
                    "solution": solution,
                    "priority": priority
                })
        
        # 综合规划
        for insight in categorized["综合战略洞察"]["总结建议"]:
            yidiaoyan_format["comprehensive_plan"].append({
                "plan_type": insight.split(":")[0] if ":" in insight else "综合建议",
                "content": insight.split(":")[1].strip() if ":" in insight else insight
            })
        
        return yidiaoyan_format

# 使用示例
def main():
    """完整使用示例"""
    
    # 初始化提取器
    extractor = YiliNPSInsightExtractor()
    
    # 准备请求数据 (简化示例)
    sample_request = {
        "yili_survey_data_input": {
            "base_analysis_result": "基于样本的分析结果...",
            "nps_analysis_result": "NPS分析结果...",
            "cross_analysis_result": None,
            "kano_analysis_result": None,
            "psm_analysis_result": None,
            "maxdiff_analysis_result": None,
            "data_list": [
                {
                    "样本编码": "1",
                    "作答类型": "正式",
                    "Q1您向朋友或同事推荐我们的可能性多大？": "8分"
                    # ... 其他字段
                }
            ]
        }
    }
    
    try:
        # 1. 调用API获取分析结果
        print("🔄 调用伊利NPS分析API...")
        api_response = extractor.call_nps_api(sample_request)
        print("✅ API调用成功")
        
        # 2. 提取所有insight_summary
        print("\n📊 提取所有智能体洞察...")
        all_insights = extractor.extract_all_insights(api_response)
        
        for agent_name, insights in all_insights.items():
            print(f"\n🤖 {agent_name}:")
            for i, insight in enumerate(insights, 1):
                print(f"   {i}. {insight}")
        
        # 3. 按类型分类提取
        print("\n📋 按类型分类洞察...")
        categorized = extractor.extract_insights_by_type(api_response)
        
        for category, subcategories in categorized.items():
            print(f"\n📂 {category}:")
            for subcat, insights in subcategories.items():
                if insights:
                    print(f"  └── {subcat}: {len(insights)}条洞察")
        
        # 4. 格式化为伊调研系统格式
        print("\n🎯 格式化为伊调研系统专用格式...")
        yidiaoyan_format = extractor.format_insights_for_yidiaoyan(api_response)
        
        print(f"战略洞察: {len(yidiaoyan_format['strategic_insights'])}条")
        print(f"营销机会: {len(yidiaoyan_format['marketing_opportunities'])}条")
        print(f"解决方案: {len(yidiaoyan_format['priority_solutions'])}条") 
        print(f"综合规划: {len(yidiaoyan_format['comprehensive_plan'])}条")
        
        # 5. 保存结果
        with open("yili_nps_insights.json", "w", encoding="utf-8") as f:
            json.dump(yidiaoyan_format, f, ensure_ascii=False, indent=2)
        print("\n💾 洞察结果已保存到 yili_nps_insights.json")
        
        return yidiaoyan_format
        
    except Exception as e:
        print(f"❌ 处理失败: {e}")
        return None

# 快速提取函数
def quick_extract_insights(api_response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """快速提取所有insight_summary的简化函数"""
    insights = []
    
    agent_results = api_response.get("data", {}).get("agent_analysis_results", [])
    
    for agent in agent_results:
        insights.append({
            "agent": agent.get("agent_name", "Unknown"),
            "insights": agent.get("insight_summary", [])
        })
    
    return insights

if __name__ == "__main__":
    main()
```

### 快速获取insight_summary的简化代码

如果您只需要快速获取insight_summary，可以使用以下简化代码：

```python
def extract_insights_simple(api_response):
    """简化版本 - 直接提取所有insight_summary"""
    insights = {}
    
    for agent in api_response['data']['agent_analysis_results']:
        agent_name = agent['agent_name']
        insight_summary = agent['insight_summary']
        insights[agent_name] = insight_summary
    
    return insights

# 使用示例
# response = requests.post(api_url, json=request_data)
# insights = extract_insights_simple(response.json())
# 
# for agent_name, insights_list in insights.items():
#     print(f"{agent_name}: {insights_list}")
```

---

## 响应示例

### 成功响应示例

```json
{
  "status": "success",
  "message": "七智能体NPS分析完成",
  "analysis_type": "七智能体NPS分析系统",
  "timestamp": "20250911_083656_238",
  "data": {
    "timestamp": "20250911_083656_238",
    "analysis_type": "七智能体NPS分析系统",
    "original_input": {
      "data_source": "伊利NPS调研问卷",
      "processed_responses": 10,
      "valid_responses": 10,
      "survey_metadata": {
        "survey_type": "product_nps",
        "survey_title": "Chinese NPS Survey",
        "data_source": "survey_data_input"
      }
    },
    "agent_analysis_results": [
      {
        "agent_name": "NPS净值分析智能体",
        "question_context": "Q1您向朋友或同事推荐我们的可能性多大？",
        "input_data": {
          "nps_net_score": -20,
          "total_responses": 10,
          "industry_benchmark": 30
        },
        "ai_analysis": {
          "nps_level_assessment": {
            "level": "需改进",
            "industry_comparison": "低于行业标准",
            "competitive_position": "落后"
          },
          "business_health_impact": {
            "customer_loyalty": "低",
            "brand_strength": "弱", 
            "growth_potential": "低"
          },
          "strategic_recommendations": [
            {
              "priority": "高",
              "action": "深入分析NPS低分原因，通过客户调研收集具体不满点",
              "expected_impact": "提升客户满意度，改善NPS分数",
              "timeline": "3-6个月"
            }
          ],
          "key_insights": [
            "洞察1: 当前NPS分数显著低于行业基准，客户满意度和忠诚度存在较大问题",
            "洞察2: 低NPS分数可能影响品牌声誉和市场竞争力"
          ]
        },
        "business_questions": [
          "当前NPS水平是否达到行业标准？",
          "需要采取什么措施提升NPS分数？",
          "与竞争对手相比我们的表现如何？"
        ],
        "insight_summary": [
          "洞察1: 当前NPS分数显著低于行业基准，表明客户满意度和忠诚度存在较大问题，需立即采取行动。",
          "洞察2: 低NPS分数可能影响品牌声誉和市场竞争力，需通过多方面的改进措施来挽回客户信任。"
        ],
        "summary_text": "AI分析显示当前NPS净值-20.0%处于需改进水平，在行业中低于行业标准，竞争地位落后。"
      }
    ],
    "supporting_data": {
      "positive_set": [],
      "negative_set": [],
      "question_texts": {}
    },
    "summary_statistics": {
      "total_agents": 7,
      "total_statements": 45,
      "total_business_questions": 21,
      "total_ai_insights": 42,
      "ai_powered_agents": 7,
      "fallback_agents": 0,
      "analysis_coverage": "NPS净值、分布、正面因素、负面因素、开放回答、综合洞察"
    }
  }
}
```

---

## 错误处理

### 错误响应格式

**状态码**: `400/422/500`

```json
{
  "status": "error",
  "message": "错误描述信息",
  "error_type": "错误类型",
  "timestamp": "20250911_083656_238"
}
```

### 常见错误类型

| 状态码 | 错误类型 | 描述 | 解决方案 |
|--------|----------|------|----------|
| `400` | `invalid_request` | 请求格式错误 | 检查JSON格式和必填字段 |
| `422` | `validation_error` | 参数验证失败 | 检查参数类型和值范围 |
| `500` | `processing_error` | 服务器处理错误 | 联系技术支持 |
| `500` | `ai_analysis_error` | AI分析失败 | 检查数据质量，重试请求 |

### 错误示例

```json
{
  "status": "error",
  "message": "缺少必填字段 'yili_survey_data_input'",
  "error_type": "validation_error",
  "timestamp": "20250911_083656_238"
}
```

---

## 使用指南

### 最佳实践

1. **数据质量**
   - 确保NPS评分数据完整（Q1问题）
   - 提供充足的样本量（建议≥30）
   - 包含多选题和开放题的完整回答

2. **请求优化**
   - 单次请求建议不超过1000个样本
   - 超大数据集建议分批处理
   - 设置合理的超时时间（建议60秒）

3. **结果解读**
   - **🎯 重点关注**: 七个智能体的`insight_summary`字段（伊调研系统主要需求）
   - 参考`ai_analysis`中的战略建议
   - 结合`summary_statistics`评估分析覆盖度

### 伊调研系统专用指南

**insight_summary字段解读**：

1. **智能体1-2**: 战略级洞察，包含竞争分析和客户群体风险评估
2. **智能体3**: 营销机会洞察，提供可直接使用的营销文案建议
3. **智能体4-6**: 数据质量洞察和具体问题解决方案，包含优先级指导
4. **智能体7**: 综合战略规划，包含短期/中期/长期行动建议

**数据提取示例**：
```python
# 从API响应中提取所有insight_summary
all_insights = []
for agent in response['data']['agent_analysis_results']:
    agent_insights = {
        'agent_name': agent['agent_name'],
        'insights': agent['insight_summary']
    }
    all_insights.append(agent_insights)
```

### 性能说明

- **响应时间**: 通常10-30秒（取决于数据量）
- **并发限制**: 建议不超过5个并发请求
- **数据限制**: 单次请求最大1000个样本

### 技术支持

如遇到问题，请联系：
- **技术支持邮箱**: ai-support@yili.com  
- **API状态页面**: http://status.digitalyili.com
- **文档版本**: v2.0.0
- **最后更新**: 2025-09-11

---

**© 2025 伊利集团 - AI算法团队**