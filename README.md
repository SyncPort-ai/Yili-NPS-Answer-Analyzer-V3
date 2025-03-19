# llm_inquiry_analyzer

一个基于大语言模型的开放题答案分析工具，实现对开放题答案的清洗-打标-聚类-总结流程。每次调用处理单道题的所有答案。

## 项目结构

### 核心文件
- `api.py`: FastAPI 服务器实现，提供 REST API 接口，处理请求验证和错误处理
- `opening_question_analysis.py`: 核心分析逻辑实现，包括数据清洗、打标、聚类和主题生成
- `llm.py`: 大语言模型接口封装，包括 Azure OpenAI 的聊天和嵌入模型调用
- `prompts.py`: 提示词模板管理，用于生成标注和主题提取的提示词
- `cluster.py`: 文本聚类实现，使用 PCA 降维和 K-means 聚类

### 测试文件
- `set_up.ipynb`: 测试脚本，包含基本功能测试、并发测试和负载测试