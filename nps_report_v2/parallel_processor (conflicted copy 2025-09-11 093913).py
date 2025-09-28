"""
V1/V2并行处理管理器
负责协调V1和V2的并行执行，处理结果合并和降级策略
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from .input_data_processor import InputDataProcessor, ProcessedSurveyData
from .nps_data_processor import NPSDataProcessor, ProcessedNPSData
from .data_recorder import DataRecorder

# 导入V2本地副本的V1处理逻辑，避免与原始V1文件冲突
from .v1_legacy_analysis import v1_legacy_auto_analysis

# 配置详细日志
try:
    from .utils.logging_config import get_logger, log_function_call
    logger = get_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    # 如果没有详细日志系统，创建一个空装饰器
    def log_function_call():
        def decorator(func):
            return func
        return decorator

@dataclass
class ProcessingResult:
    """处理结果数据结构"""
    version: str  # "v1" or "v2"
    success: bool
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    processing_time: float
    timestamp: str

@dataclass
class ParallelProcessingResult:
    """并行处理结果"""
    request_id: str
    input_data: Dict[str, Any]
    v1_result: ProcessingResult
    v2_result: ProcessingResult
    merged_result: Dict[str, Any]
    comparison_analysis: Dict[str, Any]
    final_status: str  # "success", "v1_fallback", "failure"
    total_processing_time: float

class ParallelProcessor:
    """V1/V2并行处理器"""
    
    def __init__(self, enable_v2: bool = True, v2_timeout: float = 300.0):
        """
        初始化并行处理器
        
        Args:
            enable_v2: 是否启用V2处理
            v2_timeout: V2处理超时时间（秒）
        """
        self.enable_v2 = enable_v2
        self.v2_timeout = v2_timeout
        
        # 初始化处理器
        self.input_processor = InputDataProcessor()
        self.nps_processor = NPSDataProcessor()
        self.data_recorder = DataRecorder()
        
        # 线程池
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        logger.info(f"并行处理器初始化完成 - V2启用: {enable_v2}, 超时: {v2_timeout}s")
    
    @log_function_call()
    async def process_parallel(self, raw_input_data: Dict[str, Any], 
                             request_id: Optional[str] = None) -> ParallelProcessingResult:
        """
        并行处理主入口函数
        
        Args:
            raw_input_data: 原始输入数据
            request_id: 请求ID（可选）
            
        Returns:
            ParallelProcessingResult: 并行处理结果
        """
        start_time = time.time()
        
        if not request_id:
            request_id = f"req_{int(time.time() * 1000)}"
        
        logger.info(f"🚀 开始并行处理 - 请求ID: {request_id}")
        logger.debug(f"📥 原始输入数据键值: {list(raw_input_data.keys())}")
        logger.debug(f"⚙️ V2启用状态: {self.enable_v2}, 超时设置: {self.v2_timeout}s")
        
        try:
            # 记录输入数据
            await self.data_recorder.record_input(request_id, raw_input_data)
            
            # 创建处理任务
            tasks = []
            
            # V1处理任务
            v1_task = asyncio.create_task(
                self._process_v1(raw_input_data, request_id)
            )
            tasks.append(("v1", v1_task))
            
            # V2处理任务（如果启用）
            if self.enable_v2:
                v2_task = asyncio.create_task(
                    self._process_v2(raw_input_data, request_id)
                )
                tasks.append(("v2", v2_task))
            
            # 等待所有任务完成或超时
            v1_result = None
            v2_result = None
            
            for version, task in tasks:
                try:
                    if version == "v2":
                        result = await asyncio.wait_for(task, timeout=self.v2_timeout)
                    else:
                        result = await task
                    
                    if version == "v1":
                        v1_result = result
                    else:
                        v2_result = result
                        
                except asyncio.TimeoutError:
                    logger.warning(f"{version.upper()}处理超时")
                    if version == "v1":
                        v1_result = ProcessingResult(
                            version="v1",
                            success=False,
                            result=None,
                            error="处理超时",
                            processing_time=self.v2_timeout,
                            timestamp=datetime.now().isoformat()
                        )
                    else:
                        v2_result = ProcessingResult(
                            version="v2",
                            success=False,
                            result=None,
                            error="处理超时",
                            processing_time=self.v2_timeout,
                            timestamp=datetime.now().isoformat()
                        )
                except Exception as e:
                    logger.error(f"{version.upper()}处理出错: {e}")
                    if version == "v1":
                        v1_result = ProcessingResult(
                            version="v1",
                            success=False,
                            result=None,
                            error=str(e),
                            processing_time=time.time() - start_time,
                            timestamp=datetime.now().isoformat()
                        )
                    else:
                        v2_result = ProcessingResult(
                            version="v2",
                            success=False,
                            result=None,
                            error=str(e),
                            processing_time=time.time() - start_time,
                            timestamp=datetime.now().isoformat()
                        )
            
            # 如果V2未启用，创建默认V2结果
            if not self.enable_v2:
                v2_result = ProcessingResult(
                    version="v2",
                    success=False,
                    result=None,
                    error="V2处理未启用",
                    processing_time=0,
                    timestamp=datetime.now().isoformat()
                )
            
            # 合并结果和决定最终状态
            merged_result, final_status = self._merge_results(v1_result, v2_result)
            
            # 生成对比分析
            comparison_analysis = self._generate_comparison_analysis(v1_result, v2_result)
            
            # 创建最终结果
            parallel_result = ParallelProcessingResult(
                request_id=request_id,
                input_data=raw_input_data,
                v1_result=v1_result,
                v2_result=v2_result,
                merged_result=merged_result,
                comparison_analysis=comparison_analysis,
                final_status=final_status,
                total_processing_time=time.time() - start_time
            )
            
            # 记录处理结果
            await self.data_recorder.record_processing_result(request_id, parallel_result)
            
            logger.info(f"并行处理完成 - 请求ID: {request_id}, 状态: {final_status}, 耗时: {parallel_result.total_processing_time:.2f}s")
            
            return parallel_result
            
        except Exception as e:
            logger.error(f"并行处理失败 - 请求ID: {request_id}, 错误: {e}")
            logger.error(traceback.format_exc())
            
            # 创建失败结果
            return ParallelProcessingResult(
                request_id=request_id,
                input_data=raw_input_data,
                v1_result=ProcessingResult("v1", False, None, str(e), 0, datetime.now().isoformat()),
                v2_result=ProcessingResult("v2", False, None, str(e), 0, datetime.now().isoformat()),
                merged_result={"error": str(e)},
                comparison_analysis={"error": "处理失败，无法生成对比分析"},
                final_status="failure",
                total_processing_time=time.time() - start_time
            )
    
    async def _process_v1(self, input_data: Dict[str, Any], request_id: str) -> ProcessingResult:
        """执行V1处理逻辑"""
        start_time = time.time()
        
        try:
            logger.info(f"开始V1处理 - 请求ID: {request_id}")
            
            # 调用V1的auto_analysis函数
            # 需要将输入数据转换为V1期望的格式
            v1_input = self._convert_to_v1_format(input_data)
            
            # 调用V2本地副本的V1算法（已经是异步的）
            v1_result = await v1_legacy_auto_analysis(v1_input)
            
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                version="v1",
                success=True,
                result=v1_result,
                error=None,
                processing_time=processing_time,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"V1处理完成 - 请求ID: {request_id}, 耗时: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"V1处理失败 - 请求ID: {request_id}, 错误: {e}")
            
            return ProcessingResult(
                version="v1",
                success=False,
                result=None,
                error=str(e),
                processing_time=processing_time,
                timestamp=datetime.now().isoformat()
            )
    
    async def _process_v2(self, input_data: Dict[str, Any], request_id: str) -> ProcessingResult:
        """执行V2处理逻辑"""
        start_time = time.time()
        
        try:
            logger.info(f"开始V2处理 - 请求ID: {request_id}")
            
            # V2处理流程
            # 1. 输入数据处理
            processed_survey = self.input_processor.process_survey_data(input_data)
            
            # 2. NPS数据处理
            processed_nps = self.nps_processor.process_nps_data(processed_survey)
            
            # 3. 转换为返回格式
            v2_result = {
                "survey_analysis": asdict(processed_survey),
                "nps_analysis": asdict(processed_nps),
                "enhancement_type": "v2_multi_agent",
                "processing_metadata": {
                    "version": "2.0",
                    "agents_used": ["input_processor", "nps_processor"],
                    "processing_stages": 2
                }
            }
            
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                version="v2",
                success=True,
                result=v2_result,
                error=None,
                processing_time=processing_time,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"V2处理完成 - 请求ID: {request_id}, 耗时: {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"V2处理失败 - 请求ID: {request_id}, 错误: {e}")
            
            return ProcessingResult(
                version="v2",
                success=False,
                result=None,
                error=str(e),
                processing_time=processing_time,
                timestamp=datetime.now().isoformat()
            )
    
    def _convert_to_v1_format(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """将输入数据转换为V1期望的格式"""
        try:
            # 如果输入已经是V1格式，直接返回
            if 'wordInfos' in input_data:
                return input_data
            
            # 如果是V2格式，需要转换
            if 'survey_response_data' in input_data:
                survey_data = input_data['survey_response_data']
                responses = survey_data.get('response_data', [])
                
                # 提取文本信息创建wordInfos
                word_infos = []
                word_id = 1
                
                for response in responses:
                    # 提取开放性回答
                    open_responses = response.get('open_responses', {})
                    if 'specific_reasons' in open_responses:
                        reasons = open_responses['specific_reasons']
                        for key, text in reasons.items():
                            if text and text.strip():
                                word_infos.append({
                                    'ids': [word_id],
                                    'word': text.strip()
                                })
                                word_id += 1
                
                # 创建V1格式的数据
                v1_data = {
                    'emotionalType': 1,  # 默认情感类型
                    'taskType': 1,       # 默认任务类型
                    'questionId': 'nps_survey',
                    'wordInfos': word_infos
                }
                
                return v1_data
            
            # 如果格式不明，尝试直接使用
            return input_data
            
        except Exception as e:
            logger.warning(f"数据格式转换失败: {e}, 使用原始数据")
            return input_data
    
    def _merge_results(self, v1_result: ProcessingResult, v2_result: ProcessingResult) -> Tuple[Dict[str, Any], str]:
        """合并V1和V2的处理结果"""
        
        # 决定最终状态和使用哪个结果
        if v1_result.success and v2_result.success:
            # 两个都成功，合并结果
            merged_result = {
                "status": "success",
                "v1_analysis": v1_result.result,
                "v2_enhancement": v2_result.result,
                "primary_result": v2_result.result,  # V2为主要结果
                "fallback_result": v1_result.result,  # V1为备用结果
                "processing_info": {
                    "v1_processing_time": v1_result.processing_time,
                    "v2_processing_time": v2_result.processing_time,
                    "enhancement_applied": True
                }
            }
            final_status = "success"
            
        elif v1_result.success and not v2_result.success:
            # V1成功，V2失败，使用V1结果
            merged_result = {
                "status": "v1_fallback", 
                "analysis_result": v1_result.result,
                "v2_error": v2_result.error,
                "processing_info": {
                    "v1_processing_time": v1_result.processing_time,
                    "v2_error": v2_result.error,
                    "enhancement_applied": False,
                    "fallback_reason": "V2处理失败"
                }
            }
            final_status = "v1_fallback"
            
        elif not v1_result.success and v2_result.success:
            # V1失败，V2成功，使用V2结果
            merged_result = {
                "status": "v2_only",
                "analysis_result": v2_result.result,
                "v1_error": v1_result.error,
                "processing_info": {
                    "v1_error": v1_result.error,
                    "v2_processing_time": v2_result.processing_time,
                    "enhancement_applied": True,
                    "fallback_reason": "V1处理失败"
                }
            }
            final_status = "success"
            
        else:
            # 两个都失败
            merged_result = {
                "status": "failure",
                "v1_error": v1_result.error,
                "v2_error": v2_result.error,
                "processing_info": {
                    "v1_error": v1_result.error,
                    "v2_error": v2_result.error,
                    "enhancement_applied": False,
                    "fallback_reason": "所有处理管道都失败"
                }
            }
            final_status = "failure"
        
        return merged_result, final_status
    
    def _generate_comparison_analysis(self, v1_result: ProcessingResult, v2_result: ProcessingResult) -> Dict[str, Any]:
        """生成V1 vs V2对比分析"""
        
        comparison = {
            "processing_comparison": {
                "v1_success": v1_result.success,
                "v2_success": v2_result.success,
                "v1_processing_time": v1_result.processing_time,
                "v2_processing_time": v2_result.processing_time,
                "time_difference": abs(v1_result.processing_time - v2_result.processing_time),
                "faster_version": "v1" if v1_result.processing_time < v2_result.processing_time else "v2"
            },
            "quality_comparison": {},
            "feature_comparison": {
                "v1_features": ["基础文本分析", "情感分类", "关键词提取"],
                "v2_features": ["多Agent分析", "结构化数据处理", "NPS深度分析", "质量评估"]
            }
        }
        
        # 如果两个都成功，进行更详细的对比
        if v1_result.success and v2_result.success:
            try:
                v1_data = v1_result.result
                v2_data = v2_result.result
                
                # 比较分析结果的复杂度和深度
                v1_text_length = len(str(v1_data)) if v1_data else 0
                v2_text_length = len(str(v2_data)) if v2_data else 0
                
                comparison["quality_comparison"] = {
                    "result_complexity": {
                        "v1_result_size": v1_text_length,
                        "v2_result_size": v2_text_length,
                        "complexity_ratio": v2_text_length / v1_text_length if v1_text_length > 0 else 0
                    },
                    "analysis_depth": {
                        "v1_analysis_type": "基础分析",
                        "v2_analysis_type": "增强分析",
                        "enhancement_value": "提供更深入的NPS洞察和结构化数据"
                    }
                }
                
            except Exception as e:
                comparison["quality_comparison"]["error"] = f"对比分析生成失败: {e}"
        
        return comparison
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        return {
            "v2_enabled": self.enable_v2,
            "v2_timeout": self.v2_timeout,
            "processor_status": "active",
            "supported_features": {
                "parallel_processing": True,
                "automatic_fallback": True,
                "result_comparison": True,
                "data_recording": True
            }
        }

# 使用示例
async def main():
    """主函数示例"""
    processor = ParallelProcessor(enable_v2=True, v2_timeout=60.0)
    
    # 示例输入数据
    sample_input = {
        "survey_response_data": {
            "survey_metadata": {
                "survey_type": "product_nps",
                "survey_title": "测试调研"
            },
            "response_data": [
                {
                    "response_metadata": {"user_id": "1", "response_id": "test1"},
                    "nps_score": {"value": 8, "category": "passive"},
                    "open_responses": {
                        "specific_reasons": {
                            "positive": "产品质量不错",
                            "negative": ""
                        }
                    }
                }
            ]
        }
    }
    
    # 执行并行处理
    result = await processor.process_parallel(sample_input)
    
    print(f"处理状态: {result.final_status}")
    print(f"总耗时: {result.total_processing_time:.2f}秒")
    print(f"V1成功: {result.v1_result.success}")
    print(f"V2成功: {result.v2_result.success}")

if __name__ == "__main__":
    asyncio.run(main())