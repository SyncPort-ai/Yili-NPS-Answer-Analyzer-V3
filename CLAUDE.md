# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# NPS Report Analyzer

一个基于 FastAPI 的 NPS 报告分析/生成服务，使用多智能体工作流为伊利集团提供深度客户洞察。

## Architecture Overview

### Dual Version System
- **V1 (nps_report_v1/)**: Multi-agent workflow using LangGraph with 5 specialized agents
- **V2 (nps_report_v2/)**: Enhanced architecture with persistent knowledge management and dual-input processing
- **Legacy API**: V0 compatibility layer for existing Flow API integration

### Core Components
- **FastAPI Service** (`api.py`): REST API server with health checks, web UI, and dual version support
- **Multi-Agent Workflow** (`nps_report_v1/workflow.py`): LangGraph-based analysis pipeline
- **Text Analysis Pipeline** (`opening_question_analysis.py`): Traditional cleaning-labeling-clustering workflow
- **LLM Integration** (`llm.py`): Azure OpenAI and Yili gateway support with failover
- **Knowledge Management** (`nps_report_v2/`): Persistent business knowledge and auxiliary data management

## Common Development Commands

### Local Development
```bash
# Install dependencies
make install

# Development server with hot reload
make dev PORT=7070

# Production-style run
make run

# Health check
curl http://localhost:7070/healthz

# Version info
curl http://localhost:7070/version

# V1 demo endpoint
curl http://localhost:7070/nps-report-v1/demo
```

### Testing
```bash
# Run test suite
pytest tests/ -v

# Specific test
pytest tests/test_v1_api.py::test_v1_demo_persist_outputs -v

# Interactive development and testing
jupyter notebook set_up.ipynb
```

### Docker Operations
```bash
# Build image (requires VPN for Yili registry)
make docker-build IMAGE=nps-report-analyzer TAG=v0.0.1

# Run container
make docker-run PORT=7070 IMAGE=nps-report-analyzer TAG=v0.0.1
```

## API Architecture

### V1 Endpoint: `/nps-report-v1`
Multi-agent workflow that processes NPS survey data through specialized agents:
- **Ingestion Agent**: Data cleaning and PII scrubbing
- **Quantitative Agent**: NPS calculation and statistical analysis
- **Qualitative Agent**: Text analysis and sentiment extraction
- **Context Agent**: Business intelligence integration
- **Report Agent**: Professional report generation

**Input**: Survey responses with scores, comments, and metadata
**Output**: Full state with HTML report string and structured insights

### V0 Compatibility: `/nps-report-v0`
Legacy endpoint for existing Flow API integration with identical input/output format.

### Web Interface
- `/`: NPS overview dashboard with KPI metrics
- `/analytics`: Product-line NPS comparison
- `/reports`: Report gallery with generated analyses

## Key Configuration

### Environment Variables
```bash
# Primary LLM selection
PRIMARY_LLM=openai  # or 'yili' for corporate gateway

# OpenAI Configuration
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4-turbo
OPENAI_TEMPERATURE=0.1
OPENAI_MAX_TOKENS=4000

# Azure OpenAI Configuration (Corporate)
AZURE_OPENAI_ENDPOINT=https://yili-openai.openai.azure.com/
AZURE_OPENAI_API_KEY=your-azure-key

# Yili Corporate Gateway
YILI_APP_KEY=your-app-key
YILI_GATEWAY_URL=http://ai-gateway.yili.com/v1/
OPENAI_BASE_URL_YL=http://ai-gateway.yili.com/v1/

# Optional overrides (see README for defaults)
```

### Corporate Infrastructure
- **Docker Registry**: `yldc-docker.pkg.coding.yili.com` (VPN required)
- **PyPI Mirror**: `https://mirrors.aliyun.com/pypi/simple`
- **Base Image**: `python-llmydy-3.11:v1.0.0`

## Development Patterns

### Multi-Agent Workflow Pattern
```python
# Linear pipeline to avoid recursion
workflow = StateGraph(dict)
workflow.add_node("ingestion", ingestion_agent)
workflow.add_node("quantitative", quant_agent)
workflow.add_node("qualitative", qual_agent)
workflow.add_node("context", context_agent)
workflow.add_node("report", report_agent)

# Sequential execution
workflow.add_edge("ingestion", "quantitative")
workflow.add_edge("quantitative", "qualitative")
# ... etc
```

### LLM Integration with Failover
```python
# Dual gateway support with automatic fallback
if PRIMARY_LLM == "yili":
    try:
        result = await yili_gateway_call(prompt)
    except Exception:
        result = await azure_openai_call(prompt)
else:
    result = await azure_openai_call(prompt)
```

### FastAPI Service Design Pattern
```python
# Single endpoint with comprehensive validation
@app.post("/analyze")
async def analyze_text(request: AnalysisRequest):
    async with request_semaphore:  # Concurrency control
        try:
            result = await auto_analysis(request.dict())
            return AnalysisResponse(**result)
        except (ModelCallError, LabelingError, EmbeddingError) as e:
            raise HTTPException(status_code=500, detail=str(e))

# Custom validation with Chinese text support
def validate_word(word):
    validate_not_none(word, 'word')
    if not isinstance(word, str) or not word.strip():
        raise CustomValidationError('word 不能为空字符串')
    return word
```

### Critical Dependencies
- **FastAPI Services**: `fastapi==0.112.2`, `openai==1.43.0`, `scikit-learn==1.5.1`, `pydantic==2.8.2`
- **Concurrency Control**: Semaphore-limited (2 concurrent requests) for resource management
- **Data Processing**: `pandas`, `numpy`, `scikit-learn` for clustering and statistical analysis

### Chinese Text Processing
All prompts and analysis are optimized for Mandarin Chinese:
- Domain-specific product knowledge (安慕希, 金典, 舒化, etc.)
- Competitive analysis (蒙牛, 光明, 君乐宝)
- Sentiment analysis with Chinese cultural context
- Business terminology and dairy industry specifics

## Data Management

### Input Formats
- **V1**: `survey_responses` with `score`, `comment`, optional metadata
- **V2**: Dual input modes - raw questionnaires or preprocessed responses
- **Knowledge**: Persistent business rules, product catalogs, tag mappings

### Output Persistence
Results automatically saved to:
- `outputs/results/v1_*.json`: Structured analysis data
- `outputs/reports/v1_*.html`: Interactive HTML reports
- `logs/app.log`: Rotating application logs (2MB, 3 backups)

### V2 Knowledge System
```python
# Persistent knowledge with automatic updates
knowledge_manager = PersistentKnowledgeManager("data/knowledge_files/")
business_context = knowledge_manager.get_business_context()
product_catalog = knowledge_manager.get_product_catalog()
```

## Quality Assurance

### Logging and Monitoring
- Structured logging with correlation IDs
- Request/response persistence for audit
- Error handling with business-friendly messages
- Performance metrics and LLM call tracking

### Testing Strategy
- FastAPI TestClient for API integration tests
- Sample data in `data/` directory with Chinese examples
- Jupyter notebooks for interactive experimentation
- Docker-based deployment testing

## Business Context

### Yili Group Integration
- **Industry**: Chinese dairy market leader
- **Products**: 安慕希 (Ambpoial), 金典 (Jindian), 舒化 (SHUHUA), 优酸乳, 味可滋
- **Competitors**: 蒙牛, 光明, 君乐宝, 三元
- **Analysis Focus**: Product development insights, market positioning, customer satisfaction

### Domain-Specific Processing
```python
TASK_TYPES = {
    1: "概念设计分析",    # Concept design analysis
    2: "口味设计分析",    # Taste design analysis  
    3: "包装设计分析"     # Package design analysis
}

YILI_PRODUCTS = [
    "安慕希", "金典", "舒化", "优酸乳", "味可滋", "QQ星", "伊小欢", "巧乐兹"
]
```

## Strategic Development Path

### Business Intelligence Transformation
**Target**: Transform from basic analyzer to strategic analysis platform
- **Multi-dimensional Analysis**: Temporal, demographic, product-specific insights
- **Advanced Statistical Modeling**: Trend analysis, market intelligence
- **Executive Reporting**: Automated business intelligence dashboard integration
- **Competitive Analysis**: Integration with market intelligence data
- **Performance Optimization**: Caching strategies, horizontal scaling with load balancing

### V1 → V2 Enhancement
- V1: Stable multi-agent workflow for production use
- V2: Enhanced with persistent knowledge, improved validation, dual-input support
- Maintain backward compatibility while adding enterprise features

### Current State Analysis
All three analyzer services (llm_inquiry_analyzer, nps-answer-analyzer, nps-report-analyzer) are currently identical with 38 dependencies and identical APIs. Development should differentiate nps-report-analyzer according to business intelligence specialization.

### Production Deployment Considerations
- **Scalability**: Horizontal scaling with load balancing, semaphore-controlled concurrency
- **Performance**: Vectorization for statistical analysis, parallel processing for clustering
- **Caching**: Redis for LLM response caching, database for analysis results persistence
- **Quality Gates**: Automated scoring system with revision loops, business impact measurement

### Integration Points
- Corporate VPN required for internal registry access
- Dual LLM gateway configuration for resilience
- Chinese language optimization throughout pipeline
- Business intelligence integration with existing Yili systems

## Development Philosophy

### FAIL-FAST Approach
**Critical**: Use FAIL-FAST development approach instead of defensive coding:
- **Fail early and loudly** when errors occur
- **Bomb immediately** with detailed error information 
- **No silent failures** or error swallowing
- **Comprehensive error details** in exceptions and logs
- **Assert conditions aggressively** rather than checking defensively

This approach enables Claude to catch all errors in the development path quickly and precisely.

### Error Handling Pattern
```python
# ❌ DON'T: Defensive coding that hides errors
try:
    result = process_data(data)
    return result if result else {}
except Exception:
    return {}  # Silent failure!

# ✅ DO: Fail-fast with detailed error information
def process_data(data):
    if not data:
        raise ValueError(f"Invalid input data: {data} - expected non-empty data structure")
    
    if 'required_field' not in data:
        raise KeyError(f"Missing required field 'required_field' in data. Available fields: {list(data.keys())}")
    
    result = expensive_operation(data)
    if not result:
        raise RuntimeError(f"Processing failed for data: {data[:100]}... - operation returned empty result")
    
    return result
```

### Smoke Testing
Use the comprehensive smoke test for validation:
```bash
# Run complete V2 workflow smoke test
python smoke_test_v2.py --verbose

# Debug mode with detailed logging
python smoke_test_v2.py --debug
```

## Python Compatibility
All code maintains Python 3.11+ compatibility with minimal memory footprint and maximum compatibility for enterprise deployment.