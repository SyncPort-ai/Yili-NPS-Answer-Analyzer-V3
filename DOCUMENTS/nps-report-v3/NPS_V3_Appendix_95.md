# 附录 9.5 《开放文本分析接口文档》

## 1. 接口基本信息
- **框架**：FastAPI  
- **请求方法**：POST  
- **开发环境**：`http://ai-algorithm-llmydy-dev.dcin-test.digitalyili.com/analyze`  
- **生产环境**：`http://ai-algorithm-llmydy.dcin.digitalyili.com/analyze`  

## 2. 请求参数

示例：
```json
{
  "questionId": "Q3",
  "question": "请问您不推荐的原因是什么？",
  "emotionalType": 2,
  "taskType": 1,
  "wordInfos": [
    {"ids": [1], "word": "价格太贵了"},
    {"ids": [2], "word": "包装不方便"}
  ]
}
```

字段说明：
- **questionId**：题号 (必填)。  
- **question**：题目文本 (必填)。  
- **emotionalType**：情感类型 (1=喜欢, 2=不喜欢, 0=其他)。  
- **taskType**：任务类型 (1 概念, 2 口味, 3 包装, 0 其他)。  
- **wordInfos**：原始回答列表。  

## 3. 响应结果

示例：
```json
{
  "status_code": 200,
  "status_message": "分析成功完成",
  "result": [
    {
      "origion": "价格太贵了",
      "clean": "价格太贵了",
      "aspect": "价格",
      "opinion": "价格太贵",
      "topic": "价格过高",
      "questionId": "Q3"
    }
  ]
}
```

字段说明：
- **aspect**：主题 (如“价格/包装/口感/界面”)。  
- **opinion**：用户观点。  
- **topic**：主题聚合标签。  
- **无效回答**：当 opinion=“无意义/未知”时，可判定为无效样本。  

---

**应用场景**：  
- 聚类主题 (aspect/topic)。  
- 标注情感 (emotionalType)。  
- 过滤无效回答。  
