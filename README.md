# NPS Analysis System

专业的NPS分析系统，采用**库优先**架构设计：

## 🚀 推荐用法：直接函数调用（内部使用）

```python
# 导入核心库 - 快速、类型安全、无HTTP开销
from nps_analysis import NPSAnalyzer

analyzer = NPSAnalyzer()
result = analyzer.analyze_survey_responses(survey_data)1
print(f"NPS得分: {result.nps_score}")
```

**优势：比API调用快10倍，更好的错误处理，完整的IDE支持**

## 📡 API接口：仅供外部集成

- `POST /analyze` - V0兼容文本分析接口（Flow系统集成）
- `POST /nps-report-v0` - V0兼容NPS报告接口
- `GET /healthz` - 健康检查
- 详见：`api_external.py`（最小化API，仅核心端点）

## 快速开始

### 依赖安装
```bash
# 安装Python依赖
make install
# 或直接使用pip
pip install -r requirements.txt
```

### 启动API服务器

#### 开发模式（推荐）
```bash
# 使用make启动（热重载）
make dev PORT=7070

# 或直接使用uvicorn
uvicorn api:app --reload --host 0.0.0.0 --port 7070
```

#### 生产模式
```bash
# 使用make启动
make run

# 或直接使用uvicorn
uvicorn api:app --host 0.0.0.0 --port 7000
```

#### 直接Python启动
```bash
# api.py内置服务器启动器
python api.py
```

### 测试服务器
```bash
# 健康检查
curl http://localhost:7070/healthz

# 版本信息
curl http://localhost:7070/version

# V1工作流演示
curl http://localhost:7070/nps-report-v1/demo

# V2工作流演示  
curl http://localhost:7070/nps-report-v2/demo

# Web界面
open http://localhost:7070

# API文档
open http://localhost:7070/docs
```

### Chrome MCP 浏览器测试
```bash
# 启动本地 MCP 服务器
python -m mcp_servers.chrome_testing_server --headless --slow-mo-ms 150
```

要点：
- 启动前若未安装依赖，可运行 `pip install model-context-protocol pyppeteer`.
- 工具命名以 `chrome.*` 开头，覆盖 `launch`、`navigate`、`evaluate`、`screenshot`、`status`、`close`
- 支持环境变量 `CHROME_MCP_HEADLESS`、`CHROME_MCP_EXECUTABLE`、`CHROME_MCP_ARGS`、`CHROME_MCP_SLOWMO_MS`
- 底层使用 pyppeteer，首次运行会自动下载 Chromium；如需复用系统 Chrome，可设置 `CHROME_MCP_EXECUTABLE=/path/to/chrome`

### 环境配置

#### 前置要求
1. **LLM API密钥**: OpenAI API Key 或伊利网关配置
2. **环境变量**: 参考 `.env.example` 或 `.env.yili`

#### 主要环境变量（优先级：环境 > .env）
```bash
# LLM配置
PRIMARY_LLM=openai              # openai 或 yili
OPENAI_API_KEY=your-key-here    # OpenAI API密钥
OPENAI_MODEL=gpt-4-turbo        # 模型名称
OPENAI_TEMPERATURE=0.1          # 温度参数
OPENAI_MAX_TOKENS=4000          # 最大token数

# 伊利网关配置（备选）
YILI_APP_KEY=your-app-key       # 伊利应用密钥  
YILI_GATEWAY_URL=http://ai-gateway.yili.com/v1/
AZURE_OPENAI_ENDPOINT=https://yili-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-key
```

日志与输出
- 运行时日志写入：`logs/app.log`（支持轮转）
- API 结果持久化（默认开启）：
  - JSON：`outputs/results/v1_*.json`
  - HTML 报告：`outputs/reports/v1_*.html`（若生成）

v0 兼容接口示例
```
curl -X POST http://localhost:7070/nps-report-v0 \
  -H 'Content-Type: application/json' \
  -d '{
    "input": {
      "input_text_0": {
        "count": 35,
        "nps_value": -0.3714,
        "user_distribution": [
          { "score": 0, "people_number": 3, "percentage": 0.09 },
          { "score": 10, "people_number": 6, "percentage": 0.17 }
        ],
        "analysis_type_list": [
          { "type_name": "推荐者", "type_percentage": 0.23 },
          { "type_name": "中立者", "type_percentage": 0.17 },
          { "type_name": "贬损者", "type_percentage": 0.60 }
        ]
      }
    }
  }'
```

Docker
- 构建：`make docker-build IMAGE=nps-report-analyzer TAG=v0.0.1`
- 运行：`make docker-run PORT=7070 IMAGE=nps-report-analyzer TAG=v0.0.1`

页面与路由
- `/` 概览：NPS 核心指标与品牌表现（示例数据，可对接 `/api/kpi/*`）
- `/analytics` 数据分析：产品线 NPS 对比与说明
- `/reports` 报告中心：示例报告卡片

简单 KPI API（演示）
- `GET /api/kpi/overview` → `{ overall_nps, promoters, detractors, passives }`
- `GET /api/kpi/brands` → `[{ brand, nps, trend }]`

## v1 接口说明（/nps-report-v1）

- 请求体：
  - `survey_responses`（必填）：列表，每项包含 `score: int`，可选 `comment, customer_id, timestamp, region, age_group`
  - `metadata`（可选）：对象
  - `optional_data`（可选）：对象，支持 `yili_products_csv`
- 返回：始终为完整状态（demo 风格），包含 `final_output.html_report_string`。
- 详见：`NPS-REPORT-ANALYZER-API-V1.0.md`（包含请求/响应示例与说明）

## 项目结构

### 核心文件
- `api.py`: FastAPI 服务器实现，提供 REST API 接口，处理请求验证和错误处理
- `opening_question_analysis.py`: 核心分析逻辑实现，包括数据清洗、打标、聚类和主题生成
- `llm.py`: 大语言模型接口封装，包括 Azure OpenAI 的聊天和嵌入模型调用
- `prompts.py`: 提示词模板管理，用于生成标注和主题提取的提示词
- `cluster.py`: 文本聚类实现，使用 PCA 降维和 K-means 聚类

### 测试文件
- `set_up.ipynb`: 测试脚本，包含基本功能测试、并发测试和负载测试
