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

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        logger.info(f"开始并行处理 - 请求ID: {request_id}")
        
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
            
            # 3. 生成并保存HTML报告
            try:
                html_report = self._generate_simple_html_report(processed_survey, processed_nps, request_id)
                # 保存HTML报告到文件系统 - FAIL-FAST方式
                html_file_path = await self._save_html_report(html_report, request_id)
                logger.info(f"V2 HTML报告生成并保存成功 - 请求ID: {request_id}, 文件: {html_file_path}")
            except Exception as e:
                logger.error(f"V2 HTML报告生成失败 - 请求ID: {request_id}, 错误: {e}")
                html_report = f"<h1>报告生成失败</h1><p>错误: {str(e)}</p>"
                html_file_path = None
            
            # 4. 转换为返回格式
            v2_result = {
                "survey_analysis": asdict(processed_survey),
                "nps_analysis": asdict(processed_nps),
                "enhancement_type": "v2_multi_agent",
                "processing_metadata": {
                    "version": "2.0",
                    "agents_used": ["input_processor", "nps_processor", "report_generator"],
                    "processing_stages": 3
                },
                "v2_output": {
                    "html_report": html_report,
                    "html_file_path": html_file_path,
                    "report_generated": html_file_path is not None,
                    "report_timestamp": datetime.now().isoformat()
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
    
    def _generate_simple_html_report(self, survey_data: ProcessedSurveyData, nps_data: ProcessedNPSData, request_id: str) -> str:
        """生成简单的HTML报告"""
        
        try:
            # 安全提取关键数据 - FAIL-FAST方式，避免递归访问
            # 直接访问dataclass字段而不用getattr避免递归
            nps_distribution = nps_data.nps_distribution if hasattr(nps_data, 'nps_distribution') else None
            quality_metrics = nps_data.quality_metrics if hasattr(nps_data, 'quality_metrics') else None
            response_tags = nps_data.response_tags[:5] if hasattr(nps_data, 'response_tags') and nps_data.response_tags else []
            
            # 调试输出数据结构
            logger.info(f"nps_distribution type: {type(nps_distribution)}")
            logger.info(f"quality_metrics type: {type(quality_metrics)}")
            if quality_metrics:
                logger.info(f"quality_metrics keys: {list(quality_metrics.keys()) if isinstance(quality_metrics, dict) else 'not dict'}")
            
            if not nps_distribution:
                # 使用简化的fallback数据避免复杂访问
                logger.warning(f"Missing nps_distribution, using fallback data")
                return self._generate_fallback_html_report(request_id, "缺少NPS分布数据")
            if not quality_metrics:
                logger.warning(f"Missing quality_metrics, using fallback data")  
                return self._generate_fallback_html_report(request_id, "缺少质量指标数据")
                
        except Exception as e:
            logger.error(f"Failed to extract data for HTML report: {e}")
            return self._generate_fallback_html_report(request_id, f"数据提取失败: {str(e)}")
        
        # 生成HTML报告
        html_report = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NPS分析报告 - V2增强版</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 3px solid #4CAF50; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: #2E7D32; margin: 0; }}
        .header p {{ color: #666; margin: 5px 0; }}
        .section {{ margin-bottom: 30px; }}
        .section h2 {{ color: #1976D2; border-left: 4px solid #1976D2; padding-left: 15px; }}
        .nps-score {{ font-size: 48px; font-weight: bold; text-align: center; padding: 20px; border-radius: 10px; margin: 20px 0; }}
        .nps-negative {{ background-color: #ffebee; color: #c62828; }}
        .nps-neutral {{ background-color: #fff3e0; color: #ef6c00; }}
        .nps-positive {{ background-color: #e8f5e8; color: #2e7d32; }}
        .distribution {{ display: flex; justify-content: space-around; margin: 20px 0; }}
        .distribution-item {{ text-align: center; padding: 15px; border-radius: 8px; min-width: 120px; }}
        .promoters {{ background-color: #e8f5e8; color: #2e7d32; }}
        .passives {{ background-color: #fff3e0; color: #ef6c00; }}
        .detractors {{ background-color: #ffebee; color: #c62828; }}
        .metric-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .metric-card {{ background-color: #f8f9fa; padding: 15px; border-radius: 8px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #1976D2; }}
        .metric-label {{ color: #666; margin-top: 5px; }}
        .tags {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 15px 0; }}
        .tag {{ background-color: #e3f2fd; color: #1565c0; padding: 8px 12px; border-radius: 20px; font-size: 14px; }}
        .tag-confidence {{ font-size: 12px; opacity: 0.8; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
        .score-distribution {{ margin: 20px 0; }}
        .score-bar {{ display: flex; align-items: center; margin: 10px 0; }}
        .score-label {{ width: 80px; font-weight: bold; }}
        .score-fill {{ height: 25px; background-color: #2196F3; margin-right: 10px; border-radius: 3px; }}
        .response-sample {{ background-color: #f9f9f9; padding: 15px; border-radius: 8px; margin: 10px 0; }}
        .response-sample h4 {{ margin: 0 0 10px 0; color: #1976D2; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NPS客户满意度分析报告</h1>
            <p>V2多智能体增强分析 | 请求ID: {request_id}</p>
            <p>生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>

        <div class="section">
            <h2>📊 NPS得分概览</h2>
            <div class="nps-score {'nps-negative' if nps_distribution.nps_score < 0 else 'nps-neutral' if nps_distribution.nps_score < 50 else 'nps-positive'}">
                {nps_distribution.nps_score:.1f}
            </div>
            <p style="text-align: center; color: #666; margin-top: 10px;">
                基于 {nps_distribution.total_responses} 个有效回答的NPS得分
            </p>
        </div>

        <div class="section">
            <h2>👥 用户分布分析</h2>
            <div class="distribution">
                <div class="distribution-item promoters">
                    <div style="font-size: 24px; font-weight: bold;">{nps_distribution.promoters}</div>
                    <div>推荐者 ({nps_distribution.promoter_percentage:.1f}%)</div>
                    <div style="font-size: 12px; margin-top: 5px;">9-10分</div>
                </div>
                <div class="distribution-item passives">
                    <div style="font-size: 24px; font-weight: bold;">{nps_distribution.passives}</div>
                    <div>中立者 ({nps_distribution.passive_percentage:.1f}%)</div>
                    <div style="font-size: 12px; margin-top: 5px;">7-8分</div>
                </div>
                <div class="distribution-item detractors">
                    <div style="font-size: 24px; font-weight: bold;">{nps_distribution.detractors}</div>
                    <div>贬损者 ({nps_distribution.detractor_percentage:.1f}%)</div>
                    <div style="font-size: 12px; margin-top: 5px;">0-6分</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>📈 评分分布详情</h2>
            <div class="score-distribution">
"""
        
        # 添加评分分布条形图 - 安全访问避免递归
        try:
            score_dist = getattr(nps_distribution, 'score_distribution', {})
            if score_dist and isinstance(score_dist, dict):
                max_count = max(score_dist.values()) if score_dist else 1
                for score, count in sorted(score_dist.items()):
                    width_percent = (count / max_count) * 100
                    html_report += f"""
                    <div class="score-bar">
                        <div class="score-label">{score}分:</div>
                        <div class="score-fill" style="width: {width_percent}%;"></div>
                        <span>{count} 人</span>
                    </div>
"""
            else:
                html_report += "<p>评分分布数据不可用</p>"
        except Exception as e:
            logger.warning(f"评分分布生成失败: {e}")
            html_report += f"<p>评分分布数据加载失败: {str(e)}</p>"
        
        html_report += f"""
            </div>
        </div>

"""
        
        # 添加数据质量指标 - 安全访问dict结构
        try:
            if isinstance(quality_metrics, dict):
                total_resp = quality_metrics.get('total_responses', 0)
                valid_resp = quality_metrics.get('valid_responses', 0)
                completion_rate = quality_metrics.get('completion_rate', 0.0)
                validity_rate = quality_metrics.get('validity_rate', 0.0)
                
                html_report += f"""
        <div class="section">
            <h2>📋 数据质量指标</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value">{total_resp}</div>
                    <div class="metric-label">总回答数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{valid_resp}</div>
                    <div class="metric-label">有效回答数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{completion_rate:.1%}</div>
                    <div class="metric-label">完成率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{validity_rate:.1%}</div>
                    <div class="metric-label">有效率</div>
                </div>
            </div>
        </div>
"""
            elif hasattr(quality_metrics, 'total_responses'):
                # 如果是对象而不是字典
                html_report += f"""
        <div class="section">
            <h2>📋 数据质量指标</h2>
            <div class="metric-grid">
                <div class="metric-card">
                    <div class="metric-value">{getattr(quality_metrics, 'total_responses', 0)}</div>
                    <div class="metric-label">总回答数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{getattr(quality_metrics, 'valid_responses', 0)}</div>
                    <div class="metric-label">有效回答数</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{getattr(quality_metrics, 'completion_rate', 0.0):.1%}</div>
                    <div class="metric-label">完成率</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{getattr(quality_metrics, 'validity_rate', 0.0):.1%}</div>
                    <div class="metric-label">有效率</div>
                </div>
            </div>
        </div>
"""
            else:
                html_report += """
        <div class="section">
            <h2>📋 数据质量指标</h2>
            <p>质量指标数据格式不匹配</p>
        </div>
"""
        except Exception as e:
            logger.warning(f"质量指标生成失败: {e}")
            html_report += f"""
        <div class="section">
            <h2>📋 数据质量指标</h2>
            <p>质量指标数据加载失败: {str(e)}</p>
        </div>
"""
        
        # 添加响应标签分析 - 安全访问避免递归
        try:
            if response_tags and len(response_tags) > 0:
                html_report += f"""
        <div class="section">
            <h2>🏷️ 关键主题标签</h2>
            <div class="tags">
"""
                for tag in response_tags:
                    try:
                        tag_name = getattr(tag, 'tag_name', '未知标签')
                        confidence = getattr(tag, 'confidence', 0.0)
                        confidence_percent = confidence * 100
                        html_report += f"""
                        <div class="tag">
                            {tag_name} 
                            <span class="tag-confidence">({confidence_percent:.1f}%)</span>
                        </div>
"""
                    except Exception as tag_e:
                        logger.warning(f"标签处理失败: {tag_e}")
                        continue
                html_report += """
            </div>
        </div>
"""
            else:
                html_report += """
        <div class="section">
            <h2>🏷️ 关键主题标签</h2>
            <p>暂无标签数据</p>
        </div>
"""
        except Exception as e:
            logger.warning(f"标签分析生成失败: {e}")
            html_report += f"""
        <div class="section">
            <h2>🏷️ 关键主题标签</h2>
            <p>标签数据加载失败: {str(e)}</p>
        </div>
"""
        
        # 添加样本回答（如果有的话）- 安全访问避免递归
        try:
            response_data = getattr(survey_data, 'response_data', [])
            if response_data and len(response_data) > 0:
                sample_responses = response_data[:3]  # 取前3个回答作为样本
                html_report += """
        <div class="section">
            <h2>💬 客户反馈样本</h2>
"""
                for i, response in enumerate(sample_responses, 1):
                    try:
                        # 安全获取NPS分数
                        nps_score = "未知"
                        if hasattr(response, 'nps_score'):
                            score_obj = getattr(response, 'nps_score', None)
                            if hasattr(score_obj, 'value'):
                                nps_score = getattr(score_obj, 'value', '未知')
                            else:
                                nps_score = score_obj if score_obj is not None else '未知'
                        
                        # 安全获取评论
                        general_comment = "暂无具体反馈"
                        if hasattr(response, 'open_responses'):
                            open_resp = getattr(response, 'open_responses', None)
                            if open_resp and hasattr(open_resp, 'specific_reasons'):
                                reasons = getattr(open_resp, 'specific_reasons', {})
                                if isinstance(reasons, dict):
                                    general_comment = reasons.get('general', '暂无具体反馈')
                        
                        html_report += f"""
            <div class="response-sample">
                <h4>客户{i} (NPS: {nps_score}分)</h4>
                <p>{general_comment}</p>
            </div>
"""
                    except Exception as resp_e:
                        logger.warning(f"客户反馈{i}处理失败: {resp_e}")
                        html_report += f"""
            <div class="response-sample">
                <h4>客户{i}</h4>
                <p>反馈数据处理失败</p>
            </div>
"""
                html_report += """
        </div>
"""
            else:
                html_report += """
        <div class="section">
            <h2>💬 客户反馈样本</h2>
            <p>暂无客户反馈数据</p>
        </div>
"""
        except Exception as e:
            logger.warning(f"客户反馈样本生成失败: {e}")
            html_report += f"""
        <div class="section">
            <h2>💬 客户反馈样本</h2>
            <p>客户反馈数据加载失败: {str(e)}</p>
        </div>
"""
        
        # 完成HTML
        html_report += f"""
        <div class="footer">
            <p>本报告由V2多智能体NPS分析系统生成</p>
            <p>分析引擎: input_processor + nps_processor + report_generator</p>
            <p>© 2025 伊利集团NPS智能分析平台</p>
        </div>
    </div>
</body>
</html>
"""
        
        return html_report
    
    def _generate_fallback_html_report(self, request_id: str, error_message: str) -> str:
        """生成简化的fallback HTML报告"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NPS分析报告 - V2增强版</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; border-bottom: 3px solid #ff9800; padding-bottom: 20px; margin-bottom: 30px; }}
        .header h1 {{ color: #e65100; margin: 0; }}
        .error {{ background-color: #ffebee; padding: 20px; border-radius: 8px; border-left: 4px solid #f44336; }}
        .footer {{ text-align: center; margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; color: #666; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>NPS客户满意度分析报告</h1>
            <p>V2多智能体增强分析 | 请求ID: {request_id}</p>
            <p>生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}</p>
        </div>
        
        <div class="error">
            <h2>🚧 报告生成部分失败</h2>
            <p><strong>错误信息:</strong> {error_message}</p>
            <p>系统已记录此问题，请联系技术支持。</p>
        </div>
        
        <div class="footer">
            <p>本报告由V2多智能体NPS分析系统生成</p>
            <p>© 2025 伊利集团NPS智能分析平台</p>
        </div>
    </div>
</body>
</html>
"""
    
    async def _save_html_report(self, html_content: str, request_id: str) -> str:
        """保存HTML报告到文件系统 - FAIL-FAST方式"""
        try:
            import os
            
            # 确保输出目录存在
            output_dir = "outputs/v2_reports"
            os.makedirs(output_dir, exist_ok=True)
            
            # 生成文件名
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"v2_nps_report_{timestamp}_{request_id}.html"
            file_path = os.path.join(output_dir, filename)
            
            # 同步写入HTML文件 - FAIL-FAST
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # 验证文件是否成功写入
            if not os.path.exists(file_path):
                raise FileNotFoundError(f"HTML报告文件未能成功创建: {file_path}")
            
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                raise ValueError(f"HTML报告文件为空: {file_path}")
            
            logger.info(f"HTML报告已保存: {file_path} ({file_size} bytes)")
            return file_path
            
        except Exception as e:
            logger.error(f"保存HTML报告失败 - 请求ID: {request_id}, 错误: {e}")
            raise  # FAIL-FAST - 重新抛出异常
    
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