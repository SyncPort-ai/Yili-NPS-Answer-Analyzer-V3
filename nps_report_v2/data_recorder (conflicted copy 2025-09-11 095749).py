"""
数据记录系统
负责完整记录输入、输出、结果和报告，便于对比分析和追踪
"""

import json
import logging
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, is_dataclass
from datetime import datetime
import hashlib
import pandas as pd
from pathlib import Path

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dataclass
class RecordMetadata:
    """记录元数据"""
    record_id: str
    request_id: str
    record_type: str  # "input", "v1_result", "v2_result", "merged_result", "comparison"
    timestamp: str
    file_path: str
    data_hash: str
    data_size: int

def serialize_data(data: Any, _seen: set = None) -> Any:
    """
    递归序列化数据，处理dataclass和其他不可序列化对象
    
    Args:
        data: 要序列化的数据
        _seen: 已处理的对象ID集合，防止循环引用
        
    Returns:
        可序列化的数据
    """
    if _seen is None:
        _seen = set()
    
    # 防止循环引用
    obj_id = id(data)
    if obj_id in _seen:
        return f"<circular_reference:{type(data).__name__}>"
    
    if data is None:
        return None
    elif isinstance(data, (str, int, float, bool)):
        return data
    elif is_dataclass(data):
        _seen.add(obj_id)
        try:
            result = asdict(data)
            _seen.remove(obj_id)
            return serialize_data(result, _seen)
        except:
            _seen.discard(obj_id)
            return f"<dataclass:{type(data).__name__}>"
    elif isinstance(data, dict):
        _seen.add(obj_id)
        try:
            result = {k: serialize_data(v, _seen) for k, v in data.items()}
            _seen.remove(obj_id)
            return result
        except:
            _seen.discard(obj_id)
            return f"<dict_error:{len(data)}>"
    elif isinstance(data, (list, tuple)):
        _seen.add(obj_id)
        try:
            result = [serialize_data(item, _seen) for item in data]
            _seen.remove(obj_id)
            return result
        except:
            _seen.discard(obj_id)
            return f"<list_error:{len(data)}>"
    elif hasattr(data, '__dict__'):
        _seen.add(obj_id)
        try:
            result = {k: serialize_data(v, _seen) for k, v in data.__dict__.items()}
            _seen.remove(obj_id)
            return result
        except:
            _seen.discard(obj_id)
            return f"<object:{type(data).__name__}>"
    else:
        # 其他类型转换为字符串
        return str(data)

class DataRecorder:
    """数据记录器"""
    
    def __init__(self, base_output_dir: str = "outputs"):
        """
        初始化数据记录器
        
        Args:
            base_output_dir: 基础输出目录
        """
        self.base_output_dir = Path(base_output_dir)
        self.setup_directories()
        self.records_index = []
        
        logger.info(f"数据记录器初始化完成 - 输出目录: {self.base_output_dir}")
    
    def setup_directories(self):
        """创建必要的目录结构"""
        directories = [
            self.base_output_dir,
            self.base_output_dir / "inputs",
            self.base_output_dir / "v1_results", 
            self.base_output_dir / "v2_results",
            self.base_output_dir / "merged_results",
            self.base_output_dir / "comparison_reports",
            self.base_output_dir / "recorded_data",
            self.base_output_dir / "logs"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
            
        logger.info("输出目录结构创建完成")
    
    def _generate_data_hash(self, data: Any) -> str:
        """生成数据哈希值"""
        try:
            data_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            return hashlib.md5(data_str.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.warning(f"生成数据哈希失败: {e}")
            return "unknown"
    
    def _get_data_size(self, data: Any) -> int:
        """获取数据大小（字节）"""
        try:
            data_str = json.dumps(data, ensure_ascii=False)
            return len(data_str.encode('utf-8'))
        except Exception as e:
            logger.warning(f"计算数据大小失败: {e}")
            return 0
    
    async def record_input(self, request_id: str, input_data: Dict[str, Any]) -> str:
        """
        记录输入数据
        
        Args:
            request_id: 请求ID
            input_data: 输入数据
            
        Returns:
            str: 记录ID
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            record_id = f"input_{request_id}_{timestamp}"
            
            # 保存输入数据
            file_path = self.base_output_dir / "inputs" / f"{record_id}.json"
            
            # 添加元数据
            enriched_data = {
                "record_metadata": {
                    "record_id": record_id,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "record_type": "input",
                    "data_hash": self._generate_data_hash(input_data),
                    "data_size": self._get_data_size(input_data)
                },
                "input_data": input_data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=2)
            
            # 记录到索引
            metadata = RecordMetadata(
                record_id=record_id,
                request_id=request_id,
                record_type="input",
                timestamp=datetime.now().isoformat(),
                file_path=str(file_path),
                data_hash=self._generate_data_hash(input_data),
                data_size=self._get_data_size(input_data)
            )
            self.records_index.append(metadata)
            
            logger.info(f"输入数据已记录 - 记录ID: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"记录输入数据失败: {e}")
            return ""
    
    async def record_v1_result(self, request_id: str, v1_result: Any) -> str:
        """记录V1处理结果"""
        return await self._record_result(request_id, v1_result, "v1_result", "v1_results")
    
    async def record_v2_result(self, request_id: str, v2_result: Any) -> str:
        """记录V2处理结果"""
        return await self._record_result(request_id, v2_result, "v2_result", "v2_results")
    
    async def record_merged_result(self, request_id: str, merged_result: Dict[str, Any]) -> str:
        """记录合并后的结果"""
        return await self._record_result(request_id, merged_result, "merged_result", "merged_results")
    
    async def _record_result(self, request_id: str, result_data: Any, 
                           record_type: str, subdirectory: str) -> str:
        """通用结果记录方法"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            record_id = f"{record_type}_{request_id}_{timestamp}"
            
            # 保存结果数据
            file_path = self.base_output_dir / subdirectory / f"{record_id}.json"
            
            # 序列化数据
            serialized_data = serialize_data(result_data)
            
            # 添加元数据
            enriched_data = {
                "record_metadata": {
                    "record_id": record_id,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "record_type": record_type,
                    "data_hash": self._generate_data_hash(serialized_data),
                    "data_size": self._get_data_size(serialized_data)
                },
                "result_data": serialized_data
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(enriched_data, f, ensure_ascii=False, indent=2)
            
            # 记录到索引
            metadata = RecordMetadata(
                record_id=record_id,
                request_id=request_id,
                record_type=record_type,
                timestamp=datetime.now().isoformat(),
                file_path=str(file_path),
                data_hash=self._generate_data_hash(serialized_data),
                data_size=self._get_data_size(serialized_data)
            )
            self.records_index.append(metadata)
            
            logger.info(f"{record_type}结果已记录 - 记录ID: {record_id}")
            return record_id
            
        except Exception as e:
            logger.error(f"记录{record_type}结果失败: {e}")
            return ""
    
    async def record_processing_result(self, request_id: str, parallel_result: Any) -> str:
        """
        记录完整的并行处理结果
        
        Args:
            request_id: 请求ID
            parallel_result: 并行处理结果对象
            
        Returns:
            str: 记录ID
        """
        try:
            # 转换为字典
            if hasattr(parallel_result, '__dict__'):
                result_dict = asdict(parallel_result)
            else:
                result_dict = parallel_result
            
            # 分别记录各部分结果
            record_ids = {}
            
            # 记录V1结果
            if hasattr(parallel_result, 'v1_result') and parallel_result.v1_result:
                v1_record_id = await self.record_v1_result(request_id, parallel_result.v1_result)
                record_ids['v1_result'] = v1_record_id
            
            # 记录V2结果
            if hasattr(parallel_result, 'v2_result') and parallel_result.v2_result:
                v2_record_id = await self.record_v2_result(request_id, parallel_result.v2_result)
                record_ids['v2_result'] = v2_record_id
            
            # 记录合并结果
            if hasattr(parallel_result, 'merged_result') and parallel_result.merged_result:
                merged_record_id = await self.record_merged_result(request_id, parallel_result.merged_result)
                record_ids['merged_result'] = merged_record_id
            
            # 记录对比分析
            if hasattr(parallel_result, 'comparison_analysis') and parallel_result.comparison_analysis:
                comparison_record_id = await self._record_comparison_analysis(request_id, parallel_result.comparison_analysis)
                record_ids['comparison_analysis'] = comparison_record_id
            
            # 记录完整结果
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            complete_record_id = f"complete_{request_id}_{timestamp}"
            
            file_path = self.base_output_dir / "recorded_data" / f"{complete_record_id}.json"
            
            complete_data = {
                "record_metadata": {
                    "record_id": complete_record_id,
                    "request_id": request_id,
                    "timestamp": datetime.now().isoformat(),
                    "record_type": "complete_processing_result",
                    "sub_record_ids": record_ids,
                    "data_hash": self._generate_data_hash(result_dict),
                    "data_size": self._get_data_size(result_dict)
                },
                "complete_result": result_dict
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(complete_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"完整处理结果已记录 - 记录ID: {complete_record_id}")
            return complete_record_id
            
        except Exception as e:
            logger.error(f"记录完整处理结果失败: {e}")
            return ""
    
    async def _record_comparison_analysis(self, request_id: str, comparison_data: Dict[str, Any]) -> str:
        """记录对比分析结果"""
        return await self._record_result(request_id, comparison_data, "comparison", "comparison_reports")
    
    def generate_processing_summary(self, request_id: str) -> Dict[str, Any]:
        """
        生成指定请求的处理摘要
        
        Args:
            request_id: 请求ID
            
        Returns:
            Dict: 处理摘要
        """
        try:
            # 查找相关记录
            related_records = [r for r in self.records_index if r.request_id == request_id]
            
            if not related_records:
                return {"error": f"未找到请求ID {request_id} 的相关记录"}
            
            # 按类型分组
            records_by_type = {}
            for record in related_records:
                if record.record_type not in records_by_type:
                    records_by_type[record.record_type] = []
                records_by_type[record.record_type].append(record)
            
            # 生成摘要
            summary = {
                "request_id": request_id,
                "total_records": len(related_records),
                "record_types": list(records_by_type.keys()),
                "processing_timeline": [],
                "data_statistics": {
                    "total_data_size": sum(r.data_size for r in related_records),
                    "records_by_type": {
                        record_type: len(records) 
                        for record_type, records in records_by_type.items()
                    }
                },
                "file_locations": {
                    record.record_type: record.file_path 
                    for record in related_records
                }
            }
            
            # 生成处理时间线
            sorted_records = sorted(related_records, key=lambda x: x.timestamp)
            for record in sorted_records:
                summary["processing_timeline"].append({
                    "timestamp": record.timestamp,
                    "record_type": record.record_type,
                    "record_id": record.record_id,
                    "data_size": record.data_size
                })
            
            return summary
            
        except Exception as e:
            logger.error(f"生成处理摘要失败: {e}")
            return {"error": str(e)}
    
    def export_records_index(self, output_file: Optional[str] = None) -> str:
        """
        导出记录索引到CSV文件
        
        Args:
            output_file: 输出文件路径（可选）
            
        Returns:
            str: 导出文件路径
        """
        try:
            if not output_file:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = self.base_output_dir / "logs" / f"records_index_{timestamp}.csv"
            
            # 转换为DataFrame
            records_data = [asdict(record) for record in self.records_index]
            df = pd.DataFrame(records_data)
            
            # 保存到CSV
            df.to_csv(output_file, index=False, encoding='utf-8')
            
            logger.info(f"记录索引已导出到: {output_file}")
            return str(output_file)
            
        except Exception as e:
            logger.error(f"导出记录索引失败: {e}")
            return ""
    
    def get_processing_statistics(self) -> Dict[str, Any]:
        """获取处理统计信息"""
        try:
            if not self.records_index:
                return {"message": "暂无处理记录"}
            
            # 按类型统计
            type_counts = {}
            total_data_size = 0
            unique_requests = set()
            
            for record in self.records_index:
                type_counts[record.record_type] = type_counts.get(record.record_type, 0) + 1
                total_data_size += record.data_size
                unique_requests.add(record.request_id)
            
            # 最近的记录
            recent_records = sorted(self.records_index, key=lambda x: x.timestamp, reverse=True)[:5]
            
            statistics = {
                "total_records": len(self.records_index),
                "unique_requests": len(unique_requests),
                "total_data_size_bytes": total_data_size,
                "total_data_size_mb": round(total_data_size / (1024 * 1024), 2),
                "records_by_type": type_counts,
                "recent_records": [
                    {
                        "record_id": r.record_id,
                        "request_id": r.request_id,
                        "record_type": r.record_type,
                        "timestamp": r.timestamp
                    }
                    for r in recent_records
                ],
                "directory_structure": {
                    "base_dir": str(self.base_output_dir),
                    "subdirectories": [
                        "inputs", "v1_results", "v2_results", 
                        "merged_results", "comparison_reports", 
                        "recorded_data", "logs"
                    ]
                }
            }
            
            return statistics
            
        except Exception as e:
            logger.error(f"获取处理统计信息失败: {e}")
            return {"error": str(e)}
    
    def cleanup_old_records(self, days_to_keep: int = 30) -> Dict[str, Any]:
        """
        清理旧记录
        
        Args:
            days_to_keep: 保留天数
            
        Returns:
            Dict: 清理结果
        """
        try:
            from datetime import timedelta
            
            cutoff_date = datetime.now() - timedelta(days=days_to_keep)
            
            files_deleted = 0
            space_freed = 0
            
            for record in self.records_index[:]:  # 复制列表以避免修改迭代器
                record_date = datetime.fromisoformat(record.timestamp.replace('Z', '+00:00').replace('+00:00', ''))
                
                if record_date < cutoff_date:
                    try:
                        # 删除文件
                        if os.path.exists(record.file_path):
                            file_size = os.path.getsize(record.file_path)
                            os.remove(record.file_path)
                            files_deleted += 1
                            space_freed += file_size
                        
                        # 从索引中移除
                        self.records_index.remove(record)
                        
                    except Exception as e:
                        logger.warning(f"删除记录文件失败: {record.file_path}, 错误: {e}")
            
            cleanup_result = {
                "files_deleted": files_deleted,
                "space_freed_bytes": space_freed,
                "space_freed_mb": round(space_freed / (1024 * 1024), 2),
                "cutoff_date": cutoff_date.isoformat(),
                "remaining_records": len(self.records_index)
            }
            
            logger.info(f"清理完成 - 删除文件: {files_deleted}, 释放空间: {cleanup_result['space_freed_mb']}MB")
            return cleanup_result
            
        except Exception as e:
            logger.error(f"清理旧记录失败: {e}")
            return {"error": str(e)}

# 使用示例
async def main():
    """主函数示例"""
    recorder = DataRecorder()
    
    # 示例记录
    sample_input = {"test": "data", "numbers": [1, 2, 3]}
    sample_result = {"analysis": "结果", "score": 85}
    
    request_id = "test_request_001"
    
    # 记录输入
    input_record_id = await recorder.record_input(request_id, sample_input)
    print(f"输入记录ID: {input_record_id}")
    
    # 记录结果
    result_record_id = await recorder.record_v1_result(request_id, sample_result)
    print(f"结果记录ID: {result_record_id}")
    
    # 生成摘要
    summary = recorder.generate_processing_summary(request_id)
    print(f"处理摘要: {summary}")
    
    # 获取统计信息
    stats = recorder.get_processing_statistics()
    print(f"统计信息: {stats}")

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())