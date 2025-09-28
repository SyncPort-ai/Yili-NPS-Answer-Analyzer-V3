# 伊利API大模型接口技术规范文档

## 文档概览

**项目名称**: llm_inquiry_analyzer - 伊利NPS文本分析服务  
**分析版本**: v1.0 (基于代码快照)  
**文档创建日期**: 2025年01月10日  
**分析范围**: AI LLM调用方式、端点配置、模型参数、提示词工程

---

## 1. AI LLM 架构概览

### 1.1 双LLM服务架构

该系统采用**双LLM服务架构**，支持两种不同的AI模型调用方式：

1. **Azure OpenAI 直连服务** (`AzureChat`) - UAT环境
2. **伊利内部AI网关服务** (`AzureChatApp`) - 生产环境

### 1.2 服务选择逻辑

```python
# 服务模式选择 (opening_question_analysis.py:429-433)
if mode == 'uat':
    model = AzureChat()          # 测试环境 - Azure直连
else:
    model = AzureChatApp()       # 生产环境 - 伊利网关
```

---

## 2. Azure OpenAI 直连服务 (AzureChat)

### 2.1 服务端点配置

```python
class AzureChat():
    def __init__(self, 
                 GPT4V_KEY: str = "37ae2a35c80c4b42b9d6ff8793ce472b",
                 GPT4V_ENDPOINT: str = "https://gpt4-turbo-sweden.openai.azure.com/openai/deployments/only_for_yili_test_4o_240710/chat/completions?api-version=2024-02-15-preview")
```

**关键配置参数**:

| 参数 | 值 | 说明 |
|------|----|----|
| **端点地址** | `https://gpt4-turbo-sweden.openai.azure.com` | Azure OpenAI Sweden区域服务器 |
| **部署名称** | `only_for_yili_test_4o_240710` | 伊利专用GPT-4o模型部署 |
| **API版本** | `2024-02-15-preview` | Azure OpenAI API版本 |
| **API密钥** | `37ae2a35c80c4b42b9d6ff8793ce472b` | Azure服务认证密钥 |

### 2.2 模型参数配置

```python
payload = {
    "messages": [{
        "role": "system",
        "content": [{"type": "text", "text": prompt}]
    }],
    "temperature": 0.5,        # 生成多样性控制
    "top_p": 0.95,            # 采样概率阈值
    "max_tokens": 1800        # 最大输出长度
}
```

**模型参数说明**:

- **temperature: 0.5** - 中等创造性，保持结果一致性
- **top_p: 0.95** - 高概率token采样，保证输出质量
- **max_tokens: 1800** - 限制单次输出长度，适合分析任务

### 2.3 请求头配置

```python
headers = {
    "Content-Type": "application/json",
    "api-key": self.GPT4V_KEY
}
```

---

## 3. 伊利内部AI网关服务 (AzureChatApp)

### 3.1 服务端点配置

```python
class AzureChatApp():
    def __init__(self, 
                 url = 'https://ycsb-gw-pub.xapi.digitalyili.com/restcloud/yili-gpt-prod/v1/getTextToThird',
                 app_key = '649aa4671fa7b91962caa01d')
```

**关键配置参数**:

| 参数 | 值 | 说明 |
|------|----|----|
| **网关地址** | `https://ycsb-gw-pub.xapi.digitalyili.com` | 伊利企业AI网关 |
| **服务路径** | `/restcloud/yili-gpt-prod/v1/getTextToThird` | LLM文本处理接口 |
| **应用密钥** | `649aa4671fa7b91962caa01d` | 伊利内部应用认证 |

### 3.2 请求参数配置

```python
data = {
    "channelCode": "wvEO",                    # 渠道代码
    "tenantsCode": "Yun8457",                # 租户代码  
    "choiceModel": 1,                        # 模型选择
    "isMultiSession": 1,                     # 多轮对话支持
    "requestContent": prompt,                # 提示词内容
    "requestType": 1,                        # 请求类型
    "streamFlag": 0,                         # 流式输出关闭
    "userCode": "wvEO10047252",             # 用户代码
    "requestGroupCode": "1243112808144896"   # 请求组代码
}
```

### 3.3 企业级功能特性

```python
# 连接复用和超时控制
self.session = requests.Session()    # HTTP连接复用
self.timeout = 30                    # 30秒超时
self.max_retries = 3                 # 最大重试3次

# 指数退避重试机制
for attempt in range(self.max_retries):
    try:
        # API调用逻辑
    except requests.RequestException as e:
        if attempt == self.max_retries - 1:
            raise SystemExit(f"请求失败重试{self.max_retries}次: {e}")
        time.sleep(1)  # 重试间隔
```

---

## 4. 文本嵌入服务 (AzureEmbedding)

### 4.1 嵌入模型配置

```python
class AzureEmbedding():
    def __init__(self,
                 key="37ae2a35c80c4b42b9d6ff8793ce472b",
                 api_version="2024-06-01", 
                 endpoint="https://gpt4-turbo-sweden.openai.azure.com/",
                 model="text-embedding-ada-002")
```

**配置参数**:

| 参数 | 值 | 说明 |
|------|----|----|
| **嵌入模型** | `text-embedding-ada-002` | OpenAI标准嵌入模型 |
| **API版本** | `2024-06-01` | 最新嵌入API版本 |
| **向量维度** | 1536 | Ada-002模型输出维度 |

### 4.2 性能监控

```python
start_time = time.time()
response = self.client.embeddings.create(input=texts, model=self.model)
end_time = time.time()
print(f"文本数量（{len(response.data)}）向量维度（{len(response.data[0].embedding)}）调用embedding耗时{end_time-start_time}秒")
```

---

## 5. 提示词工程体系

### 5.1 核心提示词模板

系统使用**动态提示词生成**，基于业务场景构建专业的分析提示词：

```python
def prompt_create(question, theme, emotion, answers):
    theme_specific = f"对于这个新品的{theme}，你{emotion}的原因是什么？" if theme != "其他设计" else f"{question}"
    emotion_specific = f'只提炼{emotion}的点。' if theme != "其他设计" else ""
    aspect = f'<预设标签>：\n{aspect_dict[theme]}\n\n' if theme != "其他设计" else ""
```

### 5.2 业务领域标签体系

系统针对**三个核心业务领域**构建专业标签体系：

#### 5.2.1 概念设计标签

```python
'概念设计': '原料天然、奶源优质、目标群体、乳糖不耐、素食主义、健身、颗粒、蛋白、脂肪、0蔗糖、植物蛋白、植物、水果、口味口感、卡路里、益生菌、维生素、有机、功效性、独特性、接受度、高端、高品质、时尚潮流、天然无添加、年轻活力、安全信赖、营养价值感知、健康、专业先进、文案宣传、品牌关联、价格、容量、爱国、奥运、低碳环保、包装美观'
```

#### 5.2.2 口味设计标签

```python
'口味设计': '口味、酸味、甜味、奶香味、果味、苦味涩味、异味杂味、协调度、余味回味、口感、细腻度、顺滑度、清新度、浓稀度流动性、层次感、醇厚度、添加剂、颗粒口感、小料口感、营养价值感知'
```

#### 5.2.3 包装设计标签

```python
'包装设计': '字体美观度、字体大小、字体颜色、图案美观度、图案风格、色彩美观度、整体美观度、信息传达、文案内容、品牌认知、产品印象、情感共鸣、瓶体、瓶口瓶盖、配件、容量'
```

### 5.3 专业分析提示词模板

系统提示词采用**角色扮演+专业指导+输出规范**的结构：

```python
prompt = f"""作为伊利乳制品公司的资深市场分析师，你的任务是针对问卷题目"{theme_specific}"的多个消费者回答进行深入的观点提取与精准打标。这对公司的产品改进和市场策略至关重要。

要求：
1. 整体分析：将每个回答视为一个完整的观点单元，不要过度拆分。
2. 观点提炼：
    - {emotion_specific}
    - 要求语言极致精简。
    - 提炼核心主谓结构，可保留必要的宾语或关键修饰词。
    - 去除标点、程度词、非必要修饰词。
    - 确保明确突出。
3. 标签分配：
    - 优先从<预设标签>中选择最贴合的标签。
    - 标签应精准反映观点的核心评价维度。
    - 如果实在无法提取明确的观点或分配合适的标签，使用"（未知，未知）"。
4. 多维度分析：如果一个回答包含多个不同维度的观点，请分别列出所有相关的标签和观点对。
5. 语境理解：考虑产品类型和消费者可能的关注点，合理推断隐含的评价维度。

输出格式：
- 使用数字编号标识每个回答。
- 每个回答的观点和标签对使用"（标签，观点）"的格式。
- 同一回答的多个观点用"|"分隔。
- 不同回答用换行符分隔。
"""
```

### 5.4 主题生成提示词

```python
def create_prompt_title(theme, emotion, answer_list):
    prompt_title = f"""你是专业的市场研究人员。针对"对于这个新品的{theme}，你{emotion}的原因是什么？"的多个回答，已经进行了分类，以下的回答来自同一分类(不同回答用；隔开）：
"{answer_text}"
请为这些回答概括一个主题，要求语言精炼重点明确，此主题将用于撰写新品测试报告(请直接输出主题，不要输出其他内容，不需要标点）"""
```

---

## 6. 并发控制与性能优化

### 6.1 API层并发控制

```python
# 全局信号量限制并发请求数
request_semaphore = asyncio.Semaphore(2)

@app.post("/analyze")
async def analyze(request: Request):
    async with request_semaphore:  # 最大2个并发请求
        # 分析逻辑
```

### 6.2 LLM调用并发控制

```python
# 文本标注并发控制
semaphore = asyncio.Semaphore(4)  # 最大4个并发LLM调用

# 标题生成并发控制  
semaphore = asyncio.Semaphore(4)  # 最大4个并发标题生成
```

### 6.3 批处理优化

```python
# 批量处理配置
batch_size = 20              # 每批20条数据
total_batches = (len(df) + batch_size - 1) // batch_size

# 异步批处理
tasks = [process_with_semaphore(i * batch_size) for i in range(total_batches)]
results = await asyncio.gather(*tasks)
```

### 6.4 重试机制

```python
# 指数退避重试
async def process_batch_with_retry(model, df, question, theme, emotion, start_num, step, max_retries=10):
    for attempt in range(max_retries):
        try:
            return await result_process(model, df, question, theme, emotion, start_num, step)
        except Exception as e:
            wait_time = min(2 ** attempt, 8)  # 指数退避，最大8秒
            await asyncio.sleep(wait_time)
```

---

## 7. 数据处理管道

### 7.1 文本预处理

```python
def list_process(answers):
    punctuation = f"[，。、,.;；：:/]"
    nonsence = f"(没有|无|追问|无追问|无已|已)"
    
    # 清洗规则：
    # 1. 移除追问标记
    # 2. 标准化分隔符
    # 3. 移除无意义内容
    # 4. 规范化标点符号
```

### 7.2 结果后处理

```python
# 结果分类处理
df_nonsense = df[df.opinion.isna()].copy()      # 无意义数据
df_unknown = df[df.opinion == '未知'].copy()     # 未知类别数据
df = df[(df.opinion.isna()==0) & (df.opinion != '未知')]  # 有效数据

# 聚类参数动态调整
if n_samples <= 40:
    cn = [2, max(min_cluster, 3)]
else:
    cn = [6, max(min_cluster, 7)]
```

---

## 8. 错误处理与异常管理

### 8.1 自定义异常类型

```python
class ModelCallError(Exception):
    """LLM调用错误"""
    def __init__(self, message, stage):
        self.message = message
        self.stage = stage

class LabelingError(Exception):
    """标注过程错误"""
    pass

class EmbeddingError(Exception):
    """嵌入过程错误"""
    pass
```

### 8.2 API错误响应

```python
# 模型调用错误 - 503服务不可用
{
    "status_code": 503,
    "status_message": "模型调用错误: labeling: 调用语言模型时出错: xxx",
    "result": None,
    "questionId": "xxx"
}

# 标注错误 - 500内部错误
{
    "status_code": 500,
    "status_message": "标注错误: xxx",
    "result": None,
    "questionId": "xxx"
}
```

---

## 9. 依赖管理与环境配置

### 9.1 核心依赖

```txt
# AI/ML核心依赖
openai==1.43.0              # OpenAI官方SDK
numpy==2.1.0                # 数值计算
pandas==2.2.2               # 数据处理
scikit-learn==1.5.1         # 机器学习（聚类）

# API服务依赖
fastapi==0.112.2            # Web API框架
uvicorn==0.30.6             # ASGI服务器
pydantic==2.8.2             # 数据验证

# HTTP客户端
requests==2.32.3            # HTTP请求
httpx==0.27.2               # 异步HTTP客户端
```

### 9.2 环境变量支持

```python
# Azure OpenAI环境变量
api_key = os.getenv("AZURE_OPENAI_API_KEY", key)
azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", endpoint)
```

---

## 10. API接口规范

### 10.1 请求格式

```json
{
    "emotionalType": 1,           // 情感类型: 0=其他, 1=喜欢, 2=不喜欢
    "taskType": 1,               // 任务类型: 0=其他设计, 1=概念设计, 2=口味设计, 3=包装设计
    "questionId": "test_001",    // 问题ID
    "question": "问题内容",      // 问题内容（taskType=0时必填）
    "wordInfos": [               // 文本数据数组
        {
            "ids": [1, 2, 3],    // 记录ID数组
            "word": "消费者反馈文本"  // 反馈内容
        }
    ]
}
```

### 10.2 响应格式

```json
{
    "status_code": 200,
    "status_message": "分析成功完成",
    "questionId": "test_001",
    "result": [
        {
            "origion": "原始文本",
            "ids": [1, 2, 3],
            "clean": "清洗后文本", 
            "aspect": "标签维度",
            "opinion": "观点提取",
            "aspect_opinion": "标签_观点",
            "topic": "主题分类"
        }
    ]
}
```

---

## 11. 性能指标与监控

### 11.1 处理性能

```python
# 性能日志输出
print(f"处理{len(df)}条耗时{end_time-start_time}秒，平均{(end_time-start_time)/len(df)*10}秒/10条")
print(f"文本数量（{len(response.data)}）向量维度（{len(response.data[0].embedding)}）调用embedding耗时{end_time-start_time}秒")
```

### 11.2 并发控制指标

- **API层并发限制**: 2个并发请求
- **LLM调用并发**: 4个并发调用
- **批处理大小**: 20条/批
- **重试次数**: 最大10次重试
- **超时设置**: 30秒API超时

---

## 12. 安全与认证

### 12.1 API密钥管理

```python
# Azure OpenAI密钥（硬编码 - 安全风险）
GPT4V_KEY = "37ae2a35c80c4b42b9d6ff8793ce472b"

# 伊利网关应用密钥（硬编码 - 安全风险）  
app_key = '649aa4671fa7b91962caa01d'
```

**⚠️ 安全建议**: 当前密钥硬编码存在安全风险，建议：
1. 使用环境变量管理敏感信息
2. 实施密钥轮换机制
3. 采用密钥管理服务(如Azure Key Vault)

### 12.2 输入验证

```python
# 严格的输入验证
def validate_not_none(value, field_name):
    if value is None:
        raise CustomValidationError(f'{field_name} 不能为 None')

def validate_in_list(value, field_name, valid_list):
    if value not in valid_list:
        raise CustomValidationError(f'{field_name} 必须是 {valid_list} 中的一个')
```

---

## 13. 部署与运维

### 13.1 容器化部署

```dockerfile
# Dockerfile配置
FROM python:3.11-slim
COPY requirements.txt /app/
RUN pip install -r requirements.txt
COPY . /app/
EXPOSE 7000
CMD ["uvicorn", "api:app", "--host", "0.0.0.0", "--port", "7000"]
```

### 13.2 服务启动

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)
```

---

## 14. 扩展性设计

### 14.1 模型切换机制

系统支持在UAT和生产环境间无缝切换：

```python
# 环境模式控制
mode = 'uat'    # 测试环境 - Azure直连
mode = 'prod'   # 生产环境 - 伊利网关
```

### 14.2 标签体系扩展

支持新业务场景的标签体系扩展：

```python
aspect_dict = {
    '概念设计': '现有标签...',
    '口味设计': '现有标签...',
    '包装设计': '现有标签...',
    '新业务场景': '新标签体系...'  # 扩展点
}
```

---

## 15. 最佳实践建议

### 15.1 生产环境优化

1. **密钥安全化**: 迁移至环境变量或密钥管理服务
2. **监控增强**: 添加详细的性能和错误监控
3. **日志系统**: 实施结构化日志记录
4. **配置外部化**: 将硬编码配置迁移至配置文件

### 15.2 性能优化

1. **连接池管理**: 优化HTTP连接复用
2. **缓存机制**: 对频繁调用的嵌入结果进行缓存
3. **批处理优化**: 根据实际负载调整批处理大小
4. **异步优化**: 进一步优化异步处理逻辑

### 15.3 可靠性提升

1. **健康检查**: 添加服务健康检查端点
2. **熔断机制**: 实施API调用熔断保护
3. **降级策略**: 制定LLM服务不可用时的降级方案
4. **数据备份**: 实施关键分析结果的备份机制

---

## 16. 技术债务与改进空间

### 16.1 已识别问题

1. **安全风险**: API密钥硬编码
2. **错误处理**: 部分异常处理不够细化
3. **配置管理**: 缺乏统一的配置管理机制
4. **测试覆盖**: 缺乏完整的单元测试和集成测试

### 16.2 优化建议

1. **引入配置管理**: 使用配置文件或配置中心
2. **增强测试**: 补充单元测试和集成测试
3. **监控完善**: 添加APM和业务指标监控
4. **文档完善**: 补充API文档和运维文档

---

**文档维护**: Claude Code  
**最后更新**: 2025年01月10日  
**版本**: v1.0 - 初始版本