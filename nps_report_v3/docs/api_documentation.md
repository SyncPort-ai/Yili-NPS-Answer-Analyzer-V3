# NPS V3 Analysis System - API Documentation

## 概述 (Overview)

NPS V3 智能分析系统是一个基于多智能体架构的客户满意度分析平台，专为中国市场和中文内容优化。系统通过三层分析架构提供深度的客户洞察和战略建议。

### 核心特性

- **多智能体分析**: 14个专业智能体协同工作
- **三层架构**: Foundation → Analysis → Consulting 递进分析
- **中文优化**: 专门针对中文文本和中国商业环境优化
- **双格式输出**: JSON 数据 + 专业 HTML 报告
- **实时监控**: 工作流可视化和性能监控
- **企业级**: 错误处理、重试机制、降级策略

### 系统架构

```mermaid
graph TD
    A[客户调研数据] --> B[Foundation Pass A0-A3]
    B --> C[Analysis Pass B1-B9]
    C --> D[Consulting Pass C1-C5]
    D --> E[双格式输出]
    E --> F[JSON 报告]
    E --> G[HTML 仪表板]
```

## 快速开始 (Quick Start)

### 安装依赖

```bash
pip install -r requirements.txt
```

### 基础使用

```python
from nps_report_v3.workflow.orchestrator import WorkflowOrchestrator
from nps_report_v3.generators.dual_output_generator import generate_standard_reports

# 创建工作流实例
orchestrator = WorkflowOrchestrator()

# 执行分析
result = await orchestrator.execute(survey_data)

# 生成报告
reports = await generate_standard_reports(result, company_name="伊利集团")
```

## API 端点 (Endpoints)

### 1. 工作流执行 API

#### POST /api/v3/analyze

执行完整的 NPS 多智能体分析工作流。

**请求格式:**

```json
{
    "workflow_id": "optional-custom-id",
    "company_name": "伊利集团",
    "survey_responses": [
        {
            "response_id": "resp_001",
            "score": 9,
            "comment": "伊利安慕希的口感非常好，质量稳定，是我最喜欢的酸奶品牌。",
            "product": "安慕希",
            "region": "华东地区",
            "channel": "线上商城",
            "demographics": {
                "age_group": "25-35",
                "gender": "女",
                "income_level": "中高"
            }
        }
    ],
    "config": {
        "language": "zh-CN",
        "enable_detailed_analysis": true,
        "confidence_threshold": 0.7,
        "analysis_depth": "comprehensive"
    }
}
```

**响应格式:**

```json
{
    "response_id": "nps_v3_20240115_143022_8a9b2c3d",
    "status": "completed",
    "execution_time": 45.23,
    "nps_metrics": {
        "nps_score": 45,
        "promoter_count": 50,
        "passive_count": 30,
        "detractor_count": 20,
        "sample_size": 100,
        "statistical_significance": true
    },
    "confidence_assessment": {
        "overall_confidence_score": 0.82,
        "overall_confidence_text": "高",
        "data_quality_score": 0.85,
        "analysis_completeness_score": 0.78,
        "statistical_significance_score": 0.83
    },
    "foundation_insights": [
        {
            "agent_id": "A0",
            "title": "数据清洗与质量评估",
            "summary": "完成原始数据的清洗和质量评估",
            "content": "处理了100条原始响应数据，清洗后得到100条有效数据...",
            "category": "数据处理",
            "priority": "低",
            "confidence": 0.95,
            "impact_score": 0.85,
            "timestamp": "2024-01-15T14:30:22Z"
        }
    ],
    "analysis_insights": [
        {
            "agent_id": "B1",
            "title": "技术需求分析结果",
            "summary": "客户对产品技术功能的需求分析",
            "content": "通过分析客户反馈，识别出以下技术改进需求...",
            "category": "技术分析",
            "priority": "高",
            "confidence": 0.82,
            "impact_score": 0.78,
            "timestamp": "2024-01-15T14:32:15Z"
        }
    ],
    "consulting_recommendations": [
        {
            "title": "建立全面的客户体验管理体系",
            "description": "构建从数据收集、分析、改进到监控的完整客户体验管理流程...",
            "category": "战略建议",
            "priority": "高",
            "expected_impact": "全面提升客户满意度和品牌忠诚度",
            "confidence_score": 0.88,
            "implementation_timeline": "6-12个月内建立完整体系..."
        }
    ],
    "executive_dashboard": {
        "executive_summary": "整体客户满意度处于中等水平，NPS得分45分...",
        "top_recommendations": [...],
        "risk_alerts": [
            "产品质量不稳定性可能导致客户流失加剧",
            "客服响应时间过长影响客户体验"
        ],
        "key_performance_indicators": {
            "客户满意度": "75%",
            "产品质量评分": "4.2/5.0",
            "服务响应时间": "24小时"
        }
    }
}
```

#### POST /api/v3/analyze/async

异步执行分析，适用于大数据集。

**请求格式:** 同上

**响应格式:**

```json
{
    "workflow_id": "async_workflow_abc123",
    "status": "submitted",
    "estimated_completion_time": "2024-01-15T15:00:00Z",
    "status_endpoint": "/api/v3/status/async_workflow_abc123",
    "webhook_url": "https://your-app.com/webhook/nps-analysis"
}
```

### 2. 状态查询 API

#### GET /api/v3/status/{workflow_id}

查询工作流执行状态。

**响应格式:**

```json
{
    "workflow_id": "async_workflow_abc123",
    "status": "running",
    "current_phase": "analysis",
    "progress_percentage": 65,
    "completed_agents": ["A0", "A1", "A2", "A3", "B1", "B2", "B3"],
    "current_agents": ["B4", "B5"],
    "estimated_remaining_time": 120,
    "error_count": 0,
    "start_time": "2024-01-15T14:30:00Z",
    "last_update": "2024-01-15T14:35:22Z"
}
```

### 3. 报告生成 API

#### POST /api/v3/reports/generate

基于分析结果生成专业报告。

**请求格式:**

```json
{
    "analysis_response_id": "nps_v3_20240115_143022_8a9b2c3d",
    "report_types": ["executive_dashboard", "detailed_analysis"],
    "output_formats": ["html", "json"],
    "company_name": "伊利集团",
    "custom_branding": {
        "logo_url": "https://company.com/logo.png",
        "primary_color": "#1e3a8a",
        "company_description": "领先的乳制品企业"
    }
}
```

**响应格式:**

```json
{
    "report_package_id": "report_20240115_143522_def456",
    "generated_reports": {
        "executive_dashboard_html": "/reports/exec_dashboard_def456.html",
        "detailed_analysis_html": "/reports/detailed_analysis_def456.html",
        "analysis_data_json": "/reports/analysis_data_def456.json"
    },
    "download_links": {
        "executive_dashboard": "https://api.company.com/reports/download/exec_dashboard_def456.html?token=xyz",
        "detailed_analysis": "https://api.company.com/reports/download/detailed_analysis_def456.html?token=xyz"
    },
    "metadata": {
        "generation_time": "2024-01-15T14:35:22Z",
        "total_file_size_mb": 2.1,
        "report_validity_days": 30
    }
}
```

### 4. 配置管理 API

#### GET /api/v3/config

获取系统配置信息。

#### POST /api/v3/config

更新系统配置（需要管理员权限）。

### 5. 健康检查 API

#### GET /api/v3/health

系统健康状态检查。

**响应格式:**

```json
{
    "status": "healthy",
    "timestamp": "2024-01-15T14:30:00Z",
    "components": {
        "database": "healthy",
        "llm_service": "healthy",
        "workflow_engine": "healthy",
        "report_generator": "healthy"
    },
    "performance_metrics": {
        "avg_response_time_ms": 1250,
        "active_workflows": 3,
        "error_rate_1h": 0.02,
        "success_rate_24h": 99.8
    },
    "system_resources": {
        "cpu_usage_percent": 45,
        "memory_usage_percent": 62,
        "disk_space_available_gb": 128
    }
}
```

## 数据模型 (Data Models)

### 输入数据模型

#### SurveyResponse

```python
{
    "response_id": str,           # 响应唯一标识
    "score": int,                 # NPS评分 (0-10)
    "comment": str,               # 客户评论
    "product": str,               # 产品名称
    "region": str,                # 地区
    "channel": str,               # 渠道
    "customer_type": str,         # 客户类型
    "purchase_frequency": str,    # 购买频率
    "demographics": {             # 人口统计信息
        "age_group": str,
        "gender": str,
        "income_level": str
    },
    "metadata": {                 # 可选元数据
        "survey_date": str,
        "survey_version": str,
        "source": str
    }
}
```

### 输出数据模型

#### NPSAnalysisResponse

完整的分析响应模型，包含所有分析结果和洞察。

#### NPSMetrics

```python
{
    "nps_score": int,                    # NPS得分 (-100 to 100)
    "promoter_count": int,               # 推荐者数量
    "passive_count": int,                # 被动者数量
    "detractor_count": int,              # 贬损者数量
    "sample_size": int,                  # 样本总数
    "statistical_significance": bool     # 统计显著性
}
```

#### AgentInsight

```python
{
    "agent_id": str,                     # 智能体ID (A0-A3, B1-B9, C1-C5)
    "title": str,                        # 洞察标题
    "summary": str,                      # 简要摘要
    "content": str,                      # 详细内容
    "category": str,                     # 分类
    "priority": str,                     # 优先级 (高/中/低)
    "confidence": float,                 # 置信度 (0.0-1.0)
    "impact_score": float,               # 影响评分 (0.0-1.0)
    "timestamp": str                     # ISO 8601 时间戳
}
```

#### BusinessRecommendation

```python
{
    "title": str,                        # 建议标题
    "description": str,                  # 详细描述
    "category": str,                     # 分类
    "priority": str,                     # 优先级
    "expected_impact": str,              # 预期影响
    "confidence_score": float,           # 置信度
    "implementation_timeline": str       # 实施时间线
}
```

## 错误处理 (Error Handling)

### 错误码分类

| 错误码 | 类型 | 描述 | 处理策略 |
|--------|------|------|----------|
| 400-499 | 客户端错误 | 请求格式错误、参数无效 | 检查请求格式 |
| 500-599 | 服务器错误 | 系统内部错误 | 重试或联系支持 |
| 1001-1099 | 工作流错误 | 工作流执行失败 | 检查数据或重试 |
| 2001-2099 | 智能体错误 | 特定智能体执行失败 | 降级处理 |
| 3001-3099 | LLM错误 | 大语言模型调用失败 | 重试或降级 |
| 4001-4099 | 数据错误 | 数据验证或处理失败 | 检查数据格式 |

### 标准错误响应格式

```json
{
    "error": {
        "code": 1001,
        "category": "workflow_error",
        "message": "工作流执行失败：数据验证错误",
        "details": {
            "component": "data_validator",
            "field": "survey_responses[0].score",
            "expected": "integer between 0 and 10",
            "received": "15"
        },
        "error_id": "err_20240115_143022_abc123",
        "timestamp": "2024-01-15T14:30:22Z",
        "retry_after": 5,
        "suggested_actions": [
            "检查评分数据格式",
            "确保分数在0-10范围内",
            "联系技术支持获取帮助"
        ]
    },
    "request_id": "req_20240115_143022_xyz789"
}
```

### 重试机制

系统实现了智能重试机制：

- **指数退避**: 重试间隔逐渐增加 (1s, 2s, 4s, 8s...)
- **熔断器**: 防止级联失败
- **降级策略**: 部分功能不可用时提供基本服务
- **最大重试次数**: 默认3次，可配置

## 认证与安全 (Authentication & Security)

### API 密钥认证

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     https://api.company.com/api/v3/analyze
```

### 安全特性

- **HTTPS 强制**: 所有API调用必须使用HTTPS
- **数据脱敏**: 自动识别和脱敏PII信息
- **访问控制**: 基于角色的访问控制(RBAC)
- **审计日志**: 完整的API调用日志
- **速率限制**: 防止API滥用

### 权限级别

| 权限级别 | 功能范围 | 速率限制 |
|----------|----------|----------|
| 基础 | 基本分析、状态查询 | 100 请求/小时 |
| 标准 | 完整分析、报告生成 | 500 请求/小时 |
| 高级 | 自定义配置、批量处理 | 2000 请求/小时 |
| 企业 | 所有功能、优先支持 | 10000 请求/小时 |

## 性能与限制 (Performance & Limits)

### 处理能力

- **单次分析**: 最多10,000条调研响应
- **并发处理**: 最多50个并发工作流
- **响应时间**: 平均30-120秒（取决于数据量）
- **数据保留**: 分析结果保留90天

### 输入限制

| 字段 | 限制 |
|------|------|
| survey_responses | 最多10,000条 |
| comment | 最长5,000字符 |
| workflow_id | 最长50字符 |
| 文件上传 | 最大100MB |

### 速率限制

```http
X-RateLimit-Limit: 500
X-RateLimit-Remaining: 487
X-RateLimit-Reset: 1642248000
X-RateLimit-Window: 3600
```

## SDK 与集成示例 (SDK & Integration Examples)

### Python SDK

```python
from nps_v3_client import NPSAnalysisClient

# 初始化客户端
client = NPSAnalysisClient(
    api_key="your_api_key",
    base_url="https://api.company.com"
)

# 执行分析
result = await client.analyze(
    survey_responses=survey_data,
    company_name="伊利集团",
    config={
        "language": "zh-CN",
        "analysis_depth": "comprehensive"
    }
)

# 生成报告
reports = await client.generate_reports(
    analysis_id=result.response_id,
    report_types=["executive_dashboard"],
    output_formats=["html"]
)

# 下载报告
report_content = await client.download_report(
    reports.download_links["executive_dashboard"]
)
```

### JavaScript SDK

```javascript
import { NPSAnalysisClient } from 'nps-v3-client';

const client = new NPSAnalysisClient({
    apiKey: 'your_api_key',
    baseUrl: 'https://api.company.com'
});

// 异步分析
const analysis = await client.analyzeAsync({
    surveyResponses: surveyData,
    companyName: '伊利集团',
    webhookUrl: 'https://your-app.com/webhook/nps-analysis'
});

// 监听状态变化
client.onStatusUpdate(analysis.workflowId, (status) => {
    console.log(`Analysis progress: ${status.progressPercentage}%`);
});
```

### REST API 直接调用

```bash
# 提交分析任务
curl -X POST https://api.company.com/api/v3/analyze \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d @survey_data.json

# 查询状态
curl -X GET https://api.company.com/api/v3/status/workflow_123 \
  -H "Authorization: Bearer YOUR_API_KEY"

# 生成报告
curl -X POST https://api.company.com/api/v3/reports/generate \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_response_id": "nps_v3_20240115_143022",
    "report_types": ["executive_dashboard"],
    "company_name": "伊利集团"
  }'
```

## 部署与配置 (Deployment & Configuration)

### 环境变量配置

```bash
# 核心配置
NPS_V3_API_KEY=your_secure_api_key
NPS_V3_DATABASE_URL=postgresql://user:pass@localhost:5432/nps_v3
NPS_V3_REDIS_URL=redis://localhost:6379/0

# LLM 配置
OPENAI_API_KEY=your_openai_key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your_azure_key

# 伊利企业网关配置
YILI_APP_KEY=your_yili_app_key
YILI_GATEWAY_URL=http://ai-gateway.yili.com/v1/

# 性能配置
MAX_CONCURRENT_WORKFLOWS=50
DEFAULT_TIMEOUT_SECONDS=300
MAX_RETRY_ATTEMPTS=3

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=INFO
```

### Docker 部署

```yaml
# docker-compose.yml
version: '3.8'
services:
  nps-v3-api:
    image: nps-v3:latest
    ports:
      - "8000:8000"
    environment:
      - NPS_V3_API_KEY=${NPS_V3_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
    depends_on:
      - postgres
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs

  postgres:
    image: postgres:13
    environment:
      POSTGRES_DB: nps_v3
      POSTGRES_USER: nps_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:6-alpine
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes 部署

```yaml
# k8s-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: nps-v3-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: nps-v3-api
  template:
    metadata:
      labels:
        app: nps-v3-api
    spec:
      containers:
      - name: nps-v3-api
        image: nps-v3:latest
        ports:
        - containerPort: 8000
        env:
        - name: NPS_V3_API_KEY
          valueFrom:
            secretKeyRef:
              name: nps-v3-secrets
              key: api-key
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
        livenessProbe:
          httpGet:
            path: /api/v3/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v3/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
```

## 监控与运维 (Monitoring & Operations)

### 指标监控

系统提供丰富的监控指标：

- **业务指标**: 分析完成率、平均处理时间、错误率
- **技术指标**: CPU使用率、内存使用率、响应时间
- **LLM指标**: API调用成功率、令牌使用量、费用统计

### 日志格式

```json
{
    "timestamp": "2024-01-15T14:30:22.123Z",
    "level": "INFO",
    "component": "workflow_orchestrator",
    "workflow_id": "workflow_abc123",
    "agent_id": "B1",
    "message": "Agent B1 execution completed successfully",
    "execution_time_ms": 1250,
    "metadata": {
        "input_size": 100,
        "output_size": 1024,
        "confidence_score": 0.85
    },
    "trace_id": "trace_xyz789"
}
```

### 运维命令

```bash
# 健康检查
curl https://api.company.com/api/v3/health

# 查看系统指标
curl https://api.company.com/api/v3/metrics

# 导出错误日志
curl -H "Authorization: Bearer ADMIN_KEY" \
     https://api.company.com/api/v3/admin/export-errors

# 清理过期数据
curl -X POST -H "Authorization: Bearer ADMIN_KEY" \
     https://api.company.com/api/v3/admin/cleanup
```

## 故障排查 (Troubleshooting)

### 常见问题

#### 1. 分析执行超时

**症状**: 请求超时，状态显示"running"但长时间无进展

**可能原因**:
- 输入数据过大
- LLM API响应慢
- 系统资源不足

**解决方案**:
```bash
# 检查系统资源
curl https://api.company.com/api/v3/health

# 查看具体工作流状态
curl https://api.company.com/api/v3/status/workflow_id

# 使用异步API处理大数据
curl -X POST https://api.company.com/api/v3/analyze/async
```

#### 2. LLM API调用失败

**症状**: 错误码3001-3099，提示LLM服务不可用

**解决方案**:
- 检查API密钥配置
- 验证网络连接
- 查看速率限制状态
- 使用备用LLM服务

#### 3. 数据验证错误

**症状**: 错误码4001-4099，数据格式不正确

**解决方案**:
```python
# 数据验证示例
from nps_v3_client.validators import validate_survey_data

validation_result = validate_survey_data(your_data)
if not validation_result.is_valid:
    print("Validation errors:", validation_result.errors)
```

### 调试工具

```python
# 启用调试模式
import logging
logging.basicConfig(level=logging.DEBUG)

# 使用详细错误报告
client = NPSAnalysisClient(
    api_key="your_key",
    debug=True,
    verbose_errors=True
)
```

## 更新日志 (Changelog)

### v3.0.0 (2024-01-15)

**新功能**:
- ✨ 全新多智能体架构
- ✨ 三层分析工作流 (Foundation → Analysis → Consulting)
- ✨ 专业HTML报告生成
- ✨ 实时工作流监控
- ✨ 中文内容深度优化

**改进**:
- 🚀 性能提升50%
- 🛡️ 增强错误处理和重试机制
- 📊 丰富的可视化图表
- 🔒 企业级安全特性

**修复**:
- 🐛 修复大数据集处理问题
- 🐛 优化内存使用
- 🐛 改进并发处理稳定性

### 支持与联系

- **技术文档**: https://docs.company.com/nps-v3
- **API参考**: https://api-docs.company.com/nps-v3
- **技术支持**: support@company.com
- **企业合作**: enterprise@company.com
- **GitHub**: https://github.com/company/nps-v3

---

*最后更新: 2024年1月15日*
*文档版本: v3.0.0*