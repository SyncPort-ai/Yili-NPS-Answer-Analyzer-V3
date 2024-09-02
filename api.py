from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import BaseModel, field_validator, Field
from typing import List, Dict, Optional
import pandas as pd
from opening_question_analysis import auto_analysis, ModelCallError, LabelingError, EmbeddingError

app = FastAPI()

class ValidationError(Exception):
    def __init__(self, message: str):
        self.message = message

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=400,
        content={"status_code": 400, "status_message": exc.message},
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"status_code": 422, "status_message": "Validation error", "details": exc.errors()},
    )

class WordInfo(BaseModel):
    ids: List[int]
    word: str

    @field_validator('ids')
    @classmethod
    def validate_ids(cls, v):
        if not v:
            raise ValidationError('ids 不能为空列表')
        return v

    @field_validator('word')
    @classmethod
    def validate_word(cls, v):
        if v is None:
            raise ValidationError('word 不能为 None')
        return v.strip()

class RequestBody(BaseModel):
    emotionalType: int
    taskType: int
    wordInfos: List[WordInfo]

    @field_validator('emotionalType')
    @classmethod
    def validate_emotional_type(cls, v):
        if v is None:
            raise ValidationError('emotionalType must not be None')
        if v not in [0, 1, 2]:
            raise ValidationError('emotionalType must be 0 (other), 1 (like), or 2 (dislike)')
        return v

    @field_validator('taskType')
    @classmethod
    def validate_task_type(cls, v):
        if v is None:
            raise ValidationError('taskType must not be None')
        if v not in [0, 1, 2, 3]:
            raise ValidationError('taskType must be 0 (other), 1 (concept), 2 (taste), or 3 (packaging)')
        return v

    @field_validator('wordInfos')
    @classmethod
    def validate_word_infos(cls, v):
        if not v:
            raise ValidationError('wordInfos 不能为空')
        return v

class ResponseBody(BaseModel):
    status_code: int
    status_message: str
    result: List[Dict] = None

@app.post("/analyze", response_model=ResponseBody)
async def analyze(request: RequestBody):
    try:
        # 将情感类型和任务类型转换为对应的字符串
        emotion_map = {0: "其他", 1: "喜欢", 2: "不喜欢"}
        emotion = emotion_map[request.emotionalType]
        theme_map = {0: "其他设计", 1: "概念设计", 2: "口味设计", 3: "包装设计"}
        theme = theme_map[request.taskType]

        # 将输入数据转换为DataFrame
        data = [{"origion": word_info.word, "mark": word_info.ids} for word_info in request.wordInfos]
        df = pd.DataFrame(data)

        # 验证DataFrame是否包含必要的列
        required_columns = ['origion', 'mark']
        if not all(col in df.columns for col in required_columns):
            raise ValueError(f"DataFrame must contain columns: {', '.join(required_columns)}")
        
        # 调用auto_analysis函数
        result = auto_analysis(theme, emotion, df, mode='uat')
        
        # 将结果DataFrame转换为字典列表
        result_json = result.to_dict(orient='records')
        
        return ResponseBody(
            status_code=200,
            status_message="Analysis completed successfully",
            result=result_json
        )
    except ModelCallError as e:
        return ResponseBody(
            status_code=503, 
            status_message=f"Model call error during {e.stage}: {str(e)}"
        )
    except LabelingError as e:
        return ResponseBody(status_code=500, status_message=f"Labeling error: {str(e)}")
    except EmbeddingError as e:
        return ResponseBody(status_code=500, status_message=f"Embedding error: {str(e)}")
    except ValueError as e:
        return ResponseBody(status_code=400, status_message=f"Invalid input: {str(e)}")
    except Exception as e:
        return ResponseBody(status_code=500, status_message=f"Unexpected error: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

