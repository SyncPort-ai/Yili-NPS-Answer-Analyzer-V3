"""
输入数据处理模块
负责接收和标准化不同格式的问卷数据，保存为结构化数据
"""

import json
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import pandas as pd
from enum import Enum

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NPSCategory(Enum):
    """NPS分类枚举"""
    PROMOTER = "promoter"      # 推荐者 (9-10分)
    PASSIVE = "passive"        # 中立者 (7-8分)
    DETRACTOR = "detractor"    # 贬损者 (0-6分)

@dataclass
class ProcessedNPSScore:
    """处理后的NPS评分数据"""
    value: int
    raw_value: str
    category: NPSCategory
    
@dataclass
class ProcessedFactorResponse:
    """处理后的因子问题回答"""
    selected: List[str]
    other_specified: Optional[str]
    
@dataclass
class ProcessedOpenResponse:
    """处理后的开放性问题回答"""
    expectations: Optional[str]
    suggestions: Optional[str]
    specific_reasons: Dict[str, str]
    
@dataclass
class ProcessedResponseData:
    """处理后的单个回答数据"""
    user_id: str
    response_id: str
    response_type: str
    distribution_method: str
    status: str
    timing: Dict[str, Any]
    annotation: Dict[str, Any]
    nps_score: ProcessedNPSScore
    factor_responses: Dict[str, ProcessedFactorResponse]
    open_responses: ProcessedOpenResponse
    
@dataclass
class ProcessedSurveyData:
    """处理后的问卷数据"""
    survey_metadata: Dict[str, Any]
    survey_config: Dict[str, Any]
    response_data: List[ProcessedResponseData]
    total_responses: int
    valid_responses: int
    timestamp: str

class InputDataProcessor:
    """输入数据处理器"""
    
    def __init__(self):
        self.supported_formats = ['json', 'excel', 'csv']
        
    def categorize_nps_score(self, score: int) -> NPSCategory:
        """根据NPS评分进行分类"""
        if score >= 9:
            return NPSCategory.PROMOTER
        elif score >= 7:
            return NPSCategory.PASSIVE
        else:
            return NPSCategory.DETRACTOR
    
    def process_survey_data(self, data: Dict[str, Any]) -> ProcessedSurveyData:
        """
        处理问卷数据的主入口函数
        
        Args:
            data: 原始问卷数据字典
            
        Returns:
            ProcessedSurveyData: 处理后的结构化数据
        """
        try:
            logger.info("开始处理问卷数据...")
            
            # 支持三种数据格式：
            # 1. 原始格式: survey_response_data.response_data (从JSON文件)
            # 2. V2 API格式: survey_responses (从V2工作流)
            # 3. 中文扁平格式: survey_data_input.data_list (从新的中文数据源)
            if 'survey_response_data' in data:
                # 原始格式
                survey_response_data = data.get('survey_response_data', {})
                survey_metadata = survey_response_data.get('survey_metadata', {})
                survey_config = survey_response_data.get('survey_config', {})
                raw_responses = survey_response_data.get('response_data', [])
                logger.debug(f"使用原始格式，found {len(raw_responses)} responses")
            elif 'survey_responses' in data:
                # V2 API格式 - 简化的survey_responses列表
                survey_metadata = data.get('metadata', {})
                survey_config = data.get('optional_data', {}).get('survey_config', {})
                raw_responses = data.get('survey_responses', [])
                logger.debug(f"使用V2 API格式，found {len(raw_responses)} responses")
                
                # 转换V2格式到内部格式
                converted_responses = []
                for i, response in enumerate(raw_responses):
                    converted_response = {
                        "response_metadata": {
                            "user_id": response.get("customer_id", f"user_{i}"),
                            "response_id": f"resp_{i}",
                            "response_type": "正式",
                            "status": "已完成",
                            "timing": {
                                "submit_time": response.get("timestamp", "")
                            }
                        },
                        "nps_score": {
                            "value": response.get("score", 0)
                        },
                        "open_responses": {
                            "specific_reasons": {
                                "general": response.get("comment", "")
                            }
                        },
                        "demographic_info": {
                            "region": response.get("region", "unknown"),
                            "age_group": response.get("age_group", "unknown")
                        }
                    }
                    converted_responses.append(converted_response)
                raw_responses = converted_responses
                logger.debug(f"转换后的响应数: {len(raw_responses)}")
            elif 'yili_survey_data_input' in data:
                # 中文扁平格式 - yili_survey_data_input.data_list
                survey_data_input = data.get('yili_survey_data_input', {})
                data_list = survey_data_input.get('data_list', [])
                logger.debug(f"使用中文扁平格式，found {len(data_list)} responses")
                
                # 构建元数据
                survey_metadata = {
                    "survey_type": "product_nps",
                    "survey_title": "Chinese NPS Survey",
                    "data_source": "survey_data_input",
                    "analysis_results": {
                        "base_analysis": survey_data_input.get("base_analysis_result"),
                        "nps_analysis": survey_data_input.get("nps_analysis_result"),
                        "cross_analysis": survey_data_input.get("cross_analysis_result"),
                        "kano_analysis": survey_data_input.get("kano_analysis_result"),
                        "psm_analysis": survey_data_input.get("psm_analysis_result"),
                        "maxdiff_analysis": survey_data_input.get("maxdiff_analysis_result")
                    }
                }
                survey_config = {}
                
                # 转换中文扁平格式到内部格式
                converted_responses = []
                for data_item in data_list:
                    converted_response = self._convert_chinese_flat_format(data_item)
                    if converted_response:  # 只添加成功转换的响应
                        converted_responses.append(converted_response)
                
                raw_responses = converted_responses
                logger.debug(f"中文格式转换后的响应数: {len(raw_responses)}")
            else:
                # 无效格式
                logger.warning("输入数据格式无效：缺少 survey_response_data, survey_responses 或 yili_survey_data_input")
                survey_metadata = {}
                survey_config = {}
                raw_responses = []
            
            # 处理每个回答
            processed_responses = []
            valid_count = 0
            
            for raw_response in raw_responses:
                try:
                    processed_response = self._process_single_response(raw_response)
                    processed_responses.append(processed_response)
                    
                    # 计算有效回答数（状态为已完成的正式回答）
                    if (processed_response.status == "已完成" and 
                        processed_response.response_type == "正式"):
                        valid_count += 1
                        
                except Exception as e:
                    logger.warning(f"处理单个回答时出错: {e}")
                    continue
            
            # 创建处理后的数据结构
            processed_data = ProcessedSurveyData(
                survey_metadata=survey_metadata,
                survey_config=survey_config,
                response_data=processed_responses,
                total_responses=len(processed_responses),
                valid_responses=valid_count,
                timestamp=datetime.now().isoformat()
            )
            
            logger.info(f"数据处理完成: 总回答数 {len(processed_responses)}, 有效回答数 {valid_count}")
            return processed_data
            
        except Exception as e:
            logger.error(f"处理问卷数据时出错: {e}")
            raise
    
    def _process_single_response(self, raw_response: Dict[str, Any]) -> ProcessedResponseData:
        """处理单个回答数据"""
        
        # 处理元数据
        metadata = raw_response.get('response_metadata', {})
        
        # 处理NPS评分
        nps_data = raw_response.get('nps_score', {})
        nps_score = ProcessedNPSScore(
            value=nps_data.get('value', 0),
            raw_value=nps_data.get('raw_value', ''),
            category=NPSCategory(nps_data.get('category', 'detractor'))
        )
        
        # 处理因子回答
        factor_data = raw_response.get('factor_responses', {})
        factor_responses = {}
        
        for factor_type in ['negative_factors', 'positive_factors']:
            factor_info = factor_data.get(factor_type, {})
            factor_responses[factor_type] = ProcessedFactorResponse(
                selected=factor_info.get('selected', []),
                other_specified=factor_info.get('other_specified')
            )
        
        # 处理开放性回答
        open_data = raw_response.get('open_responses', {})
        open_responses = ProcessedOpenResponse(
            expectations=open_data.get('expectations'),
            suggestions=open_data.get('suggestions'),
            specific_reasons=open_data.get('specific_reasons', {})
        )
        
        return ProcessedResponseData(
            user_id=metadata.get('user_id', ''),
            response_id=metadata.get('response_id', ''),
            response_type=metadata.get('response_type', ''),
            distribution_method=metadata.get('distribution_method', ''),
            status=metadata.get('status', ''),
            timing=metadata.get('timing', {}),
            annotation=metadata.get('annotation', {}),
            nps_score=nps_score,
            factor_responses=factor_responses,
            open_responses=open_responses
        )
    
    def save_processed_data(self, processed_data: ProcessedSurveyData, 
                          output_path: str) -> bool:
        """
        保存处理后的数据到文件
        
        Args:
            processed_data: 处理后的数据
            output_path: 输出文件路径
            
        Returns:
            bool: 保存是否成功
        """
        try:
            # 将数据转换为可序列化的字典
            data_dict = asdict(processed_data)
            
            # 处理枚举类型
            for response in data_dict['response_data']:
                if 'nps_score' in response and 'category' in response['nps_score']:
                    response['nps_score']['category'] = response['nps_score']['category'].value
            
            # 保存到JSON文件
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data_dict, f, ensure_ascii=False, indent=2)
            
            logger.info(f"处理后的数据已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存数据时出错: {e}")
            return False
    
    def load_from_file(self, file_path: str) -> Dict[str, Any]:
        """
        从文件加载原始数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            Dict: 加载的数据
        """
        try:
            if file_path.endswith('.json'):
                with open(file_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            elif file_path.endswith(('.xlsx', '.xls')):
                # 处理Excel文件
                return self._process_excel_file(file_path)
            elif file_path.endswith('.csv'):
                # 处理CSV文件
                return self._process_csv_file(file_path)
            else:
                raise ValueError(f"不支持的文件格式: {file_path}")
                
        except Exception as e:
            logger.error(f"加载文件时出错: {e}")
            raise
    
    def _process_excel_file(self, file_path: str) -> Dict[str, Any]:
        """处理Excel文件"""
        # TODO: 实现Excel文件处理逻辑
        logger.warning("Excel文件处理功能待实现")
        return {}
    
    def _process_csv_file(self, file_path: str) -> Dict[str, Any]:
        """处理CSV文件"""
        # TODO: 实现CSV文件处理逻辑
        logger.warning("CSV文件处理功能待实现")
        return {}
    
    def _detect_question_types(self, data_item: Dict[str, Any]) -> Dict[str, str]:
        """
        基于内容检测问题类型，避免依赖硬编码的问题编号
        
        Args:
            data_item: 单个回答数据项
            
        Returns:
            Dict: 问题类型映射 {'nps_score': '字段名', 'negative_factors': '字段名', ...}
        """
        question_mapping = {}
        
        # 检测NPS评分问题：通常包含"推荐"和"可能性"
        for key in data_item.keys():
            if isinstance(key, str):
                if ('推荐' in key and '可能性' in key) or ('推荐' in key and '朋友' in key):
                    question_mapping['nps_score'] = key
                    break
        
        # 检测负面因素问题：通常包含"不愿意推荐"和"因素"
        for key in data_item.keys():
            if isinstance(key, str):
                if ('不愿意推荐' in key and '因素' in key) or ('不愿意推荐' in key and '主要' in key):
                    question_mapping['negative_factors'] = key
                    break
        
        # 检测负面具体原因：通常包含"不愿意推荐"和"具体原因" (但排除"因素")
        for key in data_item.keys():
            if isinstance(key, str):
                if ('不愿意推荐' in key and '具体原因' in key) or ('不愿意推荐' in key and '原因' in key and '因素' not in key):
                    question_mapping['negative_specific'] = key
                    break
        
        # 检测正面因素问题：通常包含"愿意推荐"和"因素" (注意排除"不愿意")
        for key in data_item.keys():
            if isinstance(key, str):
                if ('愿意推荐' in key and '因素' in key and '不愿意' not in key) or ('愿意推荐' in key and '主要' in key and '不愿意' not in key):
                    question_mapping['positive_factors'] = key
                    break
        
        # 检测正面具体原因：通常包含"愿意推荐"和"具体原因" (注意排除"不愿意")
        for key in data_item.keys():
            if isinstance(key, str):
                if ('愿意推荐' in key and '具体原因' in key and '不愿意' not in key) or ('愿意推荐' in key and '原因' in key and '因素' not in key and '不愿意' not in key):
                    question_mapping['positive_specific'] = key
                    break
        
        return question_mapping
    
    def _convert_chinese_flat_format(self, data_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        将中文扁平格式转换为内部标准格式
        
        Args:
            data_item: 中文扁平格式的单个数据项
            
        Returns:
            Dict: 转换后的标准格式，如果转换失败返回None
        """
        try:
            # 检测问题类型映射
            question_mapping = self._detect_question_types(data_item)
            
            # 提取基本信息
            response_metadata = {
                "user_id": data_item.get("样本编码", ""),
                "response_id": data_item.get("作答ID", ""),
                "response_type": data_item.get("作答类型", "正式"),
                "distribution_method": data_item.get("投放方式", ""),
                "status": data_item.get("作答状态", "已完成"),
                "timing": {
                    "start_time": data_item.get("答题时间", ""),
                    "submit_time": data_item.get("提交时间", ""),
                    "duration": data_item.get("作答时长", "")
                },
                "annotation": {
                    "ai_status": data_item.get("AI标记状态", "未标记"),
                    "ai_reason": data_item.get("AI标记原因", ""),
                    "manual_status": data_item.get("人工标记状态", "未标记"),
                    "manual_reason": data_item.get("人工标记原因", "")
                }
            }
            
            # 处理NPS评分
            nps_score_data = {}
            if 'nps_score' in question_mapping:
                nps_field = question_mapping['nps_score']
                raw_score = data_item.get(nps_field, "0分")
                # 提取数字部分
                score_value = 0
                if isinstance(raw_score, str):
                    import re
                    score_match = re.search(r'(\d+)', raw_score)
                    if score_match:
                        score_value = int(score_match.group(1))
                elif isinstance(raw_score, (int, float)):
                    score_value = int(raw_score)
                
                # 确定NPS分类
                if score_value >= 9:
                    category = "promoter"
                elif score_value >= 7:
                    category = "passive"
                else:
                    category = "detractor"
                
                nps_score_data = {
                    "value": score_value,
                    "raw_value": raw_score,
                    "category": category
                }
            
            # 处理因素选择
            factor_responses = {}
            
            # 处理负面因素
            if 'negative_factors' in question_mapping:
                negative_field = question_mapping['negative_factors']
                negative_data = data_item.get(negative_field, {})
                selected_negative = []
                
                if isinstance(negative_data, dict):
                    for factor, value in negative_data.items():
                        if value and value != "-":
                            selected_negative.append(factor)
                
                factor_responses['negative_factors'] = {
                    "selected": selected_negative,
                    "other_specified": None
                }
            
            # 处理正面因素
            if 'positive_factors' in question_mapping:
                positive_field = question_mapping['positive_factors']
                positive_data = data_item.get(positive_field, {})
                selected_positive = []
                
                if isinstance(positive_data, dict):
                    for factor, value in positive_data.items():
                        if value and value != "-":
                            selected_positive.append(factor)
                
                factor_responses['positive_factors'] = {
                    "selected": selected_positive,
                    "other_specified": None
                }
            
            # 处理开放性回答
            open_responses = {
                "expectations": None,
                "suggestions": None,
                "specific_reasons": {}
            }
            
            if 'negative_specific' in question_mapping:
                negative_specific_field = question_mapping['negative_specific']
                negative_reason = data_item.get(negative_specific_field, "")
                if negative_reason and negative_reason.strip():
                    open_responses['specific_reasons']['negative'] = negative_reason.strip()
            
            if 'positive_specific' in question_mapping:
                positive_specific_field = question_mapping['positive_specific']
                positive_reason = data_item.get(positive_specific_field, "")
                if positive_reason and positive_reason.strip():
                    open_responses['specific_reasons']['positive'] = positive_reason.strip()
            
            # 构造完整的转换结果
            converted_response = {
                "response_metadata": response_metadata,
                "nps_score": nps_score_data,
                "factor_responses": factor_responses,
                "open_responses": open_responses
            }
            
            return converted_response
            
        except Exception as e:
            logger.warning(f"转换中文扁平格式数据时出错: {e}")
            return None
    
    def validate_data_integrity(self, processed_data: ProcessedSurveyData) -> Dict[str, Any]:
        """
        验证数据完整性
        
        Args:
            processed_data: 处理后的数据
            
        Returns:
            Dict: 验证结果
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'stats': {}
        }
        
        try:
            # 基本统计
            total_responses = processed_data.total_responses
            valid_responses = processed_data.valid_responses
            
            validation_result['stats'] = {
                'total_responses': total_responses,
                'valid_responses': valid_responses,
                'completion_rate': valid_responses / total_responses if total_responses > 0 else 0
            }
            
            # 验证必要字段
            for i, response in enumerate(processed_data.response_data):
                if not response.user_id:
                    validation_result['errors'].append(f"回答 {i+1}: 缺少用户ID")
                
                if not response.response_id:
                    validation_result['errors'].append(f"回答 {i+1}: 缺少回答ID")
                
                if response.nps_score.value < 0 or response.nps_score.value > 10:
                    validation_result['errors'].append(f"回答 {i+1}: NPS评分超出范围 (0-10)")
            
            # 检查数据一致性
            if len(validation_result['errors']) > 0:
                validation_result['is_valid'] = False
            
            return validation_result
            
        except Exception as e:
            logger.error(f"数据验证时出错: {e}")
            validation_result['is_valid'] = False
            validation_result['errors'].append(f"验证过程出错: {e}")
            return validation_result

# 使用示例
def main():
    """主函数示例"""
    processor = InputDataProcessor()
    
    # 加载数据
    input_file = "/path/to/survey_data.json"
    try:
        raw_data = processor.load_from_file(input_file)
        
        # 处理数据
        processed_data = processor.process_survey_data(raw_data)
        
        # 验证数据
        validation_result = processor.validate_data_integrity(processed_data)
        if not validation_result['is_valid']:
            logger.error(f"数据验证失败: {validation_result['errors']}")
            return
        
        # 保存处理后的数据
        output_file = "/path/to/processed_survey_data.json"
        success = processor.save_processed_data(processed_data, output_file)
        
        if success:
            logger.info("数据处理完成")
        else:
            logger.error("数据保存失败")
            
    except Exception as e:
        logger.error(f"处理过程出错: {e}")

if __name__ == "__main__":
    main()