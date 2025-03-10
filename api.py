from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
import pandas as pd
from opening_question_analysis import auto_analysis, ModelCallError, LabelingError, EmbeddingError

app = FastAPI()

# 自定义验证错误类
class CustomValidationError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)

# 自定义验证错误处理器
@app.exception_handler(CustomValidationError)
async def custom_validation_exception_handler(request: Request, exc: CustomValidationError):
    return JSONResponse(
        status_code=400,
        content={"status_code": 400, "status_message": exc.message},
    )

# 验证值不为 None
def validate_not_none(value, field_name):
    if value is None:
        raise CustomValidationError(f'{field_name} 不能为 None')
    return value

# 验证值在有效列表中
def validate_in_list(value, field_name, valid_list):
    if value not in valid_list:
        raise CustomValidationError(f'{field_name} 必须是 {valid_list} 中的一个')
    return value

# 验证 ids 列表
def validate_ids(ids):
    validate_not_none(ids, 'ids')
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise CustomValidationError('ids需要是list[int]类型')
    if not ids:
        raise CustomValidationError('ids 不能为空列表')
    return ids

# 验证 word 字符串
def validate_word(word):
    validate_not_none(word, 'word')
    return word.strip() if word else word

@app.post("/analyze")
async def analyze(request: Request):
    try:
        # 从请求中读取 JSON 数据
        body = await request.json()
        
        # 读取并验证 emotionalType
        emotionalType = validate_not_none(body.get('emotionalType'), 'emotionalType')
        validate_in_list(emotionalType, 'emotionalType', [0, 1, 2])
        
        # 读取并验证 taskType
        taskType = validate_not_none(body.get('taskType'), 'taskType')
        validate_in_list(taskType, 'taskType', [0, 1, 2, 3])
        
        # 读取并验证 question
        question = body.get('question')
        if taskType == 0 and not question:
            raise CustomValidationError('当taskType为0时，question不能为空')
        
        # 读取并验证 wordInfos
        wordInfos = validate_not_none(body.get('wordInfos'), 'wordInfos')
        if not isinstance(wordInfos, list) or not wordInfos:
            raise CustomValidationError('wordInfos 不能为空')
        
        # 验证每个 wordInfo
        for wordInfo in wordInfos:
            ids = validate_ids(wordInfo.get('ids'))
            word = validate_word(wordInfo.get('word'))
        
        # 检查 ids 列是否有重复值
        ids_list = [wordInfo.get('ids') for wordInfo in wordInfos]
        flat_ids_list = [item for sublist in ids_list for item in sublist]
        if len(flat_ids_list) != len(set(flat_ids_list)):
            raise CustomValidationError("输入数据中的 'ids' 列存在重复值，请确保 'ids' 列中的值唯一。")
        
        # 将情感类型和任务类型转换为对应的字符串
        emotion_map = {0: "其他", 1: "喜欢", 2: "不喜欢"}
        emotion = emotion_map[emotionalType]
        theme_map = {0: "其他设计", 1: "概念设计", 2: "口味设计", 3: "包装设计"}
        theme = theme_map[taskType]

        # 将输入数据转换为 DataFrame
        data = [{"origion": word_info['word'], "mark": word_info['ids']} for word_info in wordInfos]
        df = pd.DataFrame(data)

        # 验证 DataFrame 是否包含必要的列
        required_columns = ['origion', 'mark']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"DataFrame 必须包含以下列: {', '.join(required_columns)}")
        
        # 调用 auto_analysis 函数
        result = auto_analysis(question, theme, emotion, df, mode='prod')
        
        # 将结果 DataFrame 转换为字典列表
        result_json = result.to_dict(orient='records')
        
        return JSONResponse(
            status_code=200,
            content={
                "status_code": 200,
                "status_message": "分析成功完成",
                "result": result_json
            }
        )
    except ModelCallError as e:
        return JSONResponse(
            status_code=503,
            content={
                "status_code": 503,
                "status_message": f"模型调用错误: {e.stage}: {str(e)}",
                "result": None
            }
        )
    except LabelingError as e:
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500,
                "status_message": f"标注错误: {str(e)}",
                "result": None
            }
        )
    except EmbeddingError as e:
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500,
                "status_message": f"嵌入错误: {str(e)}",
                "result": None
            }
        )
    except ValueError as e:
        return JSONResponse(
            status_code=400,
            content={
                "status_code": 400,
                "status_message": f"无效输入: {str(e)}",
                "result": None
            }
        )
    except CustomValidationError as e:
        return JSONResponse(
            status_code=400,
            content={
                "status_code": 400,
                "status_message": e.message,
                "result": None
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "status_code": 500,
                "status_message": f"意外错误: {str(e)}",
                "result": None
            }
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7000)

