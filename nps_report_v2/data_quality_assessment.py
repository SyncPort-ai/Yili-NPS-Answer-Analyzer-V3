"""
数据质量和可信度评估模块

该模块实现了全面的数据质量评估框架，包括：
- 数据完整性检验
- 统计显著性分析  
- 样本代表性评估
- 响应质量分析
- 可信度计算

所有输出都使用中文，但类名和变量使用英文。
"""

import math
import statistics
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
import logging

logger = logging.getLogger(__name__)

@dataclass
class DataQualityScore:
    """数据质量评分结构"""
    dimension: str
    score: float  # 0-100分值
    status: str   # "优秀", "良好", "一般", "需改进"
    issues: List[str]
    recommendations: List[str]

@dataclass  
class ReliabilityMetrics:
    """可信度指标结构"""
    overall_reliability: float  # 整体可信度 0-100
    data_quality_score: float   # 数据质量分数
    statistical_confidence: float  # 统计置信度
    response_quality: float     # 响应质量
    sample_representativeness: float  # 样本代表性
    temporal_consistency: float # 时间一致性
    
class DataQualityAssessment:
    """数据质量评估核心类"""
    
    def __init__(self):
        self.quality_thresholds = {
            "excellent": 85,    # 优秀
            "good": 70,         # 良好  
            "fair": 55,         # 一般
            "poor": 40          # 需改进
        }
        
        self.weight_config = {
            "completeness": 0.25,      # 完整性权重
            "validity": 0.20,          # 有效性权重
            "consistency": 0.20,       # 一致性权重
            "accuracy": 0.15,          # 准确性权重
            "timeliness": 0.10,        # 时效性权重
            "uniqueness": 0.10         # 唯一性权重
        }
    
    def assess_data_quality(self, data: Dict[str, Any]) -> Dict[str, DataQualityScore]:
        """
        综合评估数据质量的六个维度
        
        Args:
            data: 包含NPS调研数据的字典
            
        Returns:
            各维度质量评分的字典
        """
        quality_scores = {}
        
        # 1. 数据完整性评估
        quality_scores['completeness'] = self._assess_completeness(data)
        
        # 2. 数据有效性评估  
        quality_scores['validity'] = self._assess_validity(data)
        
        # 3. 数据一致性评估
        quality_scores['consistency'] = self._assess_consistency(data)
        
        # 4. 数据准确性评估
        quality_scores['accuracy'] = self._assess_accuracy(data)
        
        # 5. 数据时效性评估
        quality_scores['timeliness'] = self._assess_timeliness(data)
        
        # 6. 数据唯一性评估
        quality_scores['uniqueness'] = self._assess_uniqueness(data)
        
        return quality_scores
    
    def _assess_completeness(self, data: Dict) -> DataQualityScore:
        """评估数据完整性 - 必填字段完整率"""
        issues = []
        recommendations = []
        
        required_fields = ['score', 'comment', 'customer_id', 'timestamp']
        optional_fields = ['region', 'age_group', 'product_category']
        
        if 'raw_responses' not in data:
            return DataQualityScore("完整性", 0, "需改进", 
                                  ["缺少原始响应数据"], ["提供完整的调研数据"])
        
        responses = data['raw_responses']
        total_responses = len(responses)
        complete_responses = 0
        
        for response in responses:
            missing_required = [field for field in required_fields if field not in response or not response[field]]
            if not missing_required:
                complete_responses += 1
            else:
                issues.extend([f"缺少必填字段: {field}" for field in missing_required[:2]])  # 限制显示
        
        completeness_rate = (complete_responses / total_responses * 100) if total_responses > 0 else 0
        
        if completeness_rate < 60:
            recommendations.append("增加数据收集流程的必填字段验证")
            recommendations.append("对不完整记录进行数据清洗或补充")
        
        status = self._get_quality_status(completeness_rate)
        
        return DataQualityScore("完整性", completeness_rate, status, issues[:5], recommendations[:3])
    
    def _assess_validity(self, data: Dict) -> DataQualityScore:
        """评估数据有效性 - 数据格式和范围正确性"""
        issues = []
        recommendations = []
        
        if 'raw_responses' not in data:
            return DataQualityScore("有效性", 0, "需改进", 
                                  ["缺少原始响应数据"], ["提供有效的数据格式"])
        
        responses = data['raw_responses']
        total_responses = len(responses)
        valid_responses = 0
        
        for response in responses:
            response_valid = True
            
            # 检查NPS分数范围 (0-10)
            if 'score' in response:
                try:
                    score = float(response['score'])
                    if not (0 <= score <= 10):
                        issues.append(f"NPS分数 {score} 超出有效范围 [0-10]")
                        response_valid = False
                except (ValueError, TypeError):
                    issues.append("NPS分数格式无效")
                    response_valid = False
            
            # 检查评论内容质量
            if 'comment' in response:
                comment = str(response['comment']).strip()
                if len(comment) < 5:
                    issues.append("评论内容过短")
                    response_valid = False
                elif len(comment) > 1000:
                    issues.append("评论内容过长")
                    response_valid = False
            
            # 检查时间戳格式
            if 'timestamp' in response:
                try:
                    datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00'))
                except (ValueError, AttributeError):
                    issues.append("时间戳格式无效")
                    response_valid = False
            
            if response_valid:
                valid_responses += 1
        
        validity_rate = (valid_responses / total_responses * 100) if total_responses > 0 else 0
        
        if validity_rate < 80:
            recommendations.append("加强数据输入验证规则")
            recommendations.append("增加数据清洗流程")
        
        status = self._get_quality_status(validity_rate)
        
        return DataQualityScore("有效性", validity_rate, status, issues[:5], recommendations[:3])
    
    def _assess_consistency(self, data: Dict) -> DataQualityScore:
        """评估数据一致性 - 内部逻辑和格式一致性"""
        issues = []
        recommendations = []
        
        if 'raw_responses' not in data:
            return DataQualityScore("一致性", 0, "需改进", 
                                  ["缺少原始响应数据"], ["确保数据格式一致"])
        
        responses = data['raw_responses']
        consistency_score = 100
        
        # 检查评论与分数的一致性
        inconsistent_count = 0
        positive_words = ['喜欢', '好', '棒', '优秀', '推荐', '满意']
        negative_words = ['不好', '差', '失望', '问题', '糟糕', '不满']
        
        for response in responses:
            if 'score' in response and 'comment' in response:
                try:
                    score = float(response['score'])
                    comment = str(response['comment']).lower()
                    
                    # 高分但负面评论
                    if score >= 7 and any(word in comment for word in negative_words):
                        inconsistent_count += 1
                        issues.append(f"高分({score})但评论偏负面")
                    
                    # 低分但正面评论
                    elif score <= 4 and any(word in comment for word in positive_words):
                        inconsistent_count += 1
                        issues.append(f"低分({score})但评论偏正面")
                    
                except (ValueError, TypeError):
                    continue
        
        if inconsistent_count > 0:
            inconsistency_rate = (inconsistent_count / len(responses)) * 100
            consistency_score = max(0, 100 - inconsistency_rate * 2)  # 每个不一致项扣2分
            
            if inconsistency_rate > 20:
                recommendations.append("审查评分与评论的匹配性")
                recommendations.append("增加数据质量培训")
        
        status = self._get_quality_status(consistency_score)
        
        return DataQualityScore("一致性", consistency_score, status, issues[:5], recommendations[:3])
    
    def _assess_accuracy(self, data: Dict) -> DataQualityScore:
        """评估数据准确性 - 信息真实性和可验证性"""
        issues = []
        recommendations = []
        
        if 'raw_responses' not in data:
            return DataQualityScore("准确性", 0, "需改进", 
                                  ["缺少原始响应数据"], ["验证数据来源准确性"])
        
        responses = data['raw_responses']
        accuracy_score = 100
        accuracy_issues = 0
        
        # 检查异常模式
        for response in responses:
            if 'comment' in response:
                comment = str(response['comment'])
                
                # 检查是否包含PII信息（隐私泄露风险）
                if re.search(r'(\d{11}|\d{3}-\d{4}-\d{4})', comment):  # 手机号模式
                    accuracy_issues += 1
                    issues.append("评论中包含敏感个人信息")
                
                if re.search(r'\w+@\w+\.\w+', comment):  # 邮箱模式
                    accuracy_issues += 1
                    issues.append("评论中包含邮箱地址")
                
                # 检查明显虚假或测试内容
                test_patterns = ['测试', 'test', '假的', '随便写']
                if any(pattern in comment.lower() for pattern in test_patterns):
                    accuracy_issues += 1
                    issues.append("发现疑似测试或虚假内容")
        
        # 计算准确性分数
        if accuracy_issues > 0:
            accuracy_rate = (accuracy_issues / len(responses)) * 100
            accuracy_score = max(0, 100 - accuracy_rate * 5)  # 每个问题扣5分
            
            if accuracy_rate > 10:
                recommendations.append("加强数据来源验证")
                recommendations.append("实施PII自动检测和清洗")
                recommendations.append("建立数据真实性审核机制")
        
        status = self._get_quality_status(accuracy_score)
        
        return DataQualityScore("准确性", accuracy_score, status, issues[:5], recommendations[:3])
    
    def _assess_timeliness(self, data: Dict) -> DataQualityScore:
        """评估数据时效性 - 数据收集的时间跨度和新鲜度"""
        issues = []
        recommendations = []
        
        if 'raw_responses' not in data:
            return DataQualityScore("时效性", 0, "需改进", 
                                  ["缺少原始响应数据"], ["确保数据时效性"])
        
        responses = data['raw_responses']
        current_time = datetime.now()
        valid_timestamps = []
        
        for response in responses:
            if 'timestamp' in response:
                try:
                    ts = datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00'))
                    valid_timestamps.append(ts.replace(tzinfo=None))
                except (ValueError, AttributeError):
                    continue
        
        if not valid_timestamps:
            return DataQualityScore("时效性", 0, "需改进", 
                                  ["无有效时间戳"], ["添加有效的时间戳信息"])
        
        # 计算时间跨度和新鲜度
        oldest_time = min(valid_timestamps)
        newest_time = max(valid_timestamps)
        time_span = (newest_time - oldest_time).days
        data_age = (current_time - newest_time).days
        
        timeliness_score = 100
        
        # 评估数据新鲜度
        if data_age > 365:  # 超过1年
            timeliness_score -= 30
            issues.append(f"数据过于陈旧 ({data_age}天前)")
        elif data_age > 180:  # 超过6个月
            timeliness_score -= 15
            issues.append(f"数据较为陈旧 ({data_age}天前)")
        elif data_age > 90:   # 超过3个月
            timeliness_score -= 5
            issues.append(f"数据稍显陈旧 ({data_age}天前)")
        
        # 评估时间跨度合理性
        if time_span < 1:
            timeliness_score -= 10
            issues.append("数据收集时间过于集中")
            recommendations.append("增加数据收集的时间跨度")
        elif time_span > 365:
            timeliness_score -= 20
            issues.append(f"数据时间跨度过大 ({time_span}天)")
            recommendations.append("缩短数据分析的时间窗口")
        
        if timeliness_score < 70:
            recommendations.append("建立定期数据更新机制")
            recommendations.append("设置数据有效期管理")
        
        status = self._get_quality_status(timeliness_score)
        
        return DataQualityScore("时效性", timeliness_score, status, issues[:5], recommendations[:3])
    
    def _assess_uniqueness(self, data: Dict) -> DataQualityScore:
        """评估数据唯一性 - 重复记录检测"""
        issues = []
        recommendations = []
        
        if 'raw_responses' not in data:
            return DataQualityScore("唯一性", 0, "需改进", 
                                  ["缺少原始响应数据"], ["确保数据唯一性"])
        
        responses = data['raw_responses']
        total_responses = len(responses)
        
        # 检查customer_id重复
        customer_ids = [r.get('customer_id') for r in responses if r.get('customer_id')]
        unique_customers = len(set(customer_ids))
        customer_duplication_rate = ((len(customer_ids) - unique_customers) / len(customer_ids) * 100) if customer_ids else 0
        
        # 检查评论内容重复
        comments = [r.get('comment', '').strip() for r in responses if r.get('comment')]
        unique_comments = len(set(comments))
        comment_duplication_rate = ((len(comments) - unique_comments) / len(comments) * 100) if comments else 0
        
        uniqueness_score = 100
        
        if customer_duplication_rate > 5:
            uniqueness_score -= customer_duplication_rate
            issues.append(f"客户ID重复率: {customer_duplication_rate:.1f}%")
            recommendations.append("检查客户ID分配机制")
        
        if comment_duplication_rate > 10:
            uniqueness_score -= comment_duplication_rate / 2
            issues.append(f"评论内容重复率: {comment_duplication_rate:.1f}%")
            recommendations.append("增加评论内容多样性验证")
        
        # 检查完全相同的记录
        response_strings = [str(sorted(r.items())) for r in responses]
        unique_responses = len(set(response_strings))
        exact_duplication_rate = ((total_responses - unique_responses) / total_responses * 100) if total_responses > 0 else 0
        
        if exact_duplication_rate > 0:
            uniqueness_score -= exact_duplication_rate * 2
            issues.append(f"完全重复记录率: {exact_duplication_rate:.1f}%")
            recommendations.append("实施重复记录自动检测和清除")
        
        status = self._get_quality_status(uniqueness_score)
        
        return DataQualityScore("唯一性", uniqueness_score, status, issues[:5], recommendations[:3])
    
    def calculate_reliability_metrics(self, data: Dict[str, Any], 
                                    quality_scores: Dict[str, DataQualityScore]) -> ReliabilityMetrics:
        """
        计算综合可信度指标
        
        Args:
            data: 原始数据
            quality_scores: 数据质量评分
            
        Returns:
            可信度指标对象
        """
        # 计算加权数据质量分数
        data_quality_score = sum(
            quality_scores[dimension].score * self.weight_config[dimension]
            for dimension in quality_scores.keys()
            if dimension in self.weight_config
        )
        
        # 计算统计置信度
        statistical_confidence = self._calculate_statistical_confidence(data)
        
        # 计算响应质量
        response_quality = self._calculate_response_quality(data)
        
        # 计算样本代表性
        sample_representativeness = self._calculate_sample_representativeness(data)
        
        # 计算时间一致性
        temporal_consistency = self._calculate_temporal_consistency(data)
        
        # 计算整体可信度 (综合权重)
        reliability_weights = {
            'data_quality': 0.35,
            'statistical_confidence': 0.25,
            'response_quality': 0.20,
            'sample_representativeness': 0.15,
            'temporal_consistency': 0.05
        }
        
        overall_reliability = (
            data_quality_score * reliability_weights['data_quality'] +
            statistical_confidence * reliability_weights['statistical_confidence'] +
            response_quality * reliability_weights['response_quality'] +
            sample_representativeness * reliability_weights['sample_representativeness'] +
            temporal_consistency * reliability_weights['temporal_consistency']
        )
        
        return ReliabilityMetrics(
            overall_reliability=round(overall_reliability, 2),
            data_quality_score=round(data_quality_score, 2),
            statistical_confidence=round(statistical_confidence, 2),
            response_quality=round(response_quality, 2),
            sample_representativeness=round(sample_representativeness, 2),
            temporal_consistency=round(temporal_consistency, 2)
        )
    
    def _calculate_statistical_confidence(self, data: Dict) -> float:
        """计算统计置信度"""
        if 'raw_responses' not in data:
            return 0.0
        
        responses = data['raw_responses']
        sample_size = len(responses)
        
        # 基于样本量的置信度计算
        if sample_size >= 400:
            base_confidence = 95
        elif sample_size >= 100:
            base_confidence = 85
        elif sample_size >= 30:
            base_confidence = 75
        elif sample_size >= 10:
            base_confidence = 60
        else:
            base_confidence = 40
        
        # 考虑分数分布的方差
        scores = [float(r.get('score', 5)) for r in responses if 'score' in r]
        if len(scores) > 1:
            score_std = statistics.stdev(scores)
            # 标准差越大，置信度越低
            variance_penalty = min(score_std * 5, 20)  # 最多扣20分
            base_confidence -= variance_penalty
        
        return max(0, min(100, base_confidence))
    
    def _calculate_response_quality(self, data: Dict) -> float:
        """计算响应质量分数"""
        if 'raw_responses' not in data:
            return 0.0
        
        responses = data['raw_responses']
        total_responses = len(responses)
        quality_score = 100
        
        # 评估评论质量
        low_quality_count = 0
        for response in responses:
            comment = str(response.get('comment', '')).strip()
            
            # 评论长度评估
            if len(comment) < 10:
                low_quality_count += 1
            elif len(comment) > 200:
                # 长评论通常质量更高
                continue
            
            # 评估评论信息量
            words = comment.split()
            if len(words) < 3:
                low_quality_count += 1
        
        if total_responses > 0:
            low_quality_rate = (low_quality_count / total_responses) * 100
            quality_score = max(0, 100 - low_quality_rate)
        
        return quality_score
    
    def _calculate_sample_representativeness(self, data: Dict) -> float:
        """计算样本代表性分数"""
        if 'raw_responses' not in data:
            return 0.0
        
        responses = data['raw_responses']
        representativeness_score = 100
        
        # 检查地域分布
        regions = [r.get('region') for r in responses if r.get('region')]
        unique_regions = len(set(regions))
        if unique_regions < 3 and len(regions) > 5:
            representativeness_score -= 15
        
        # 检查年龄分布
        age_groups = [r.get('age_group') for r in responses if r.get('age_group')]
        unique_age_groups = len(set(age_groups))
        if unique_age_groups < 3 and len(age_groups) > 5:
            representativeness_score -= 15
        
        # 检查分数分布
        scores = [float(r.get('score', 5)) for r in responses if 'score' in r]
        if scores:
            score_range = max(scores) - min(scores)
            if score_range < 3:  # 分数过于集中
                representativeness_score -= 20
        
        return max(0, representativeness_score)
    
    def _calculate_temporal_consistency(self, data: Dict) -> float:
        """计算时间一致性分数"""
        if 'raw_responses' not in data:
            return 0.0
        
        responses = data['raw_responses']
        timestamps = []
        
        for response in responses:
            if 'timestamp' in response:
                try:
                    ts = datetime.fromisoformat(response['timestamp'].replace('Z', '+00:00'))
                    timestamps.append(ts)
                except (ValueError, AttributeError):
                    continue
        
        if len(timestamps) < 2:
            return 50  # 无法判断，给中等分
        
        # 计算时间分布的均匀性
        timestamps.sort()
        time_intervals = [(timestamps[i+1] - timestamps[i]).total_seconds() 
                         for i in range(len(timestamps)-1)]
        
        if time_intervals:
            avg_interval = statistics.mean(time_intervals)
            if avg_interval < 60:  # 间隔过短可能是批量生成
                return 60
            elif avg_interval > 86400 * 30:  # 间隔过长可能缺乏连续性
                return 70
            else:
                return 90
        
        return 75
    
    def _get_quality_status(self, score: float) -> str:
        """根据分数获取质量状态"""
        if score >= self.quality_thresholds["excellent"]:
            return "优秀"
        elif score >= self.quality_thresholds["good"]:
            return "良好"
        elif score >= self.quality_thresholds["fair"]:
            return "一般"
        else:
            return "需改进"
    
    def generate_quality_summary(self, quality_scores: Dict[str, DataQualityScore], 
                                reliability_metrics: ReliabilityMetrics) -> Dict[str, Any]:
        """
        生成数据质量和可信度总结报告
        
        Args:
            quality_scores: 质量评分字典
            reliability_metrics: 可信度指标
            
        Returns:
            质量总结报告
        """
        # 识别主要问题领域
        problem_areas = [
            dimension for dimension, score in quality_scores.items()
            if score.score < self.quality_thresholds["good"]
        ]
        
        # 生成改进建议
        all_recommendations = []
        for score in quality_scores.values():
            all_recommendations.extend(score.recommendations)
        
        # 去重并优先排序
        unique_recommendations = list(dict.fromkeys(all_recommendations))[:5]
        
        # 确定整体质量等级
        overall_score = reliability_metrics.overall_reliability
        overall_status = self._get_quality_status(overall_score)
        
        return {
            "整体质量等级": overall_status,
            "整体可信度分数": overall_score,
            "质量维度评分": {
                dimension: {
                    "分数": score.score,
                    "状态": score.status,
                    "主要问题数": len(score.issues)
                }
                for dimension, score in quality_scores.items()
            },
            "可信度细分指标": {
                "数据质量分数": reliability_metrics.data_quality_score,
                "统计置信度": reliability_metrics.statistical_confidence,
                "响应质量": reliability_metrics.response_quality,
                "样本代表性": reliability_metrics.sample_representativeness,
                "时间一致性": reliability_metrics.temporal_consistency
            },
            "重点关注领域": problem_areas,
            "改进建议": unique_recommendations,
            "质量风险提示": self._generate_risk_alerts(quality_scores, reliability_metrics)
        }
    
    def _generate_risk_alerts(self, quality_scores: Dict[str, DataQualityScore], 
                             reliability_metrics: ReliabilityMetrics) -> List[str]:
        """生成质量风险提示"""
        alerts = []
        
        if reliability_metrics.overall_reliability < 50:
            alerts.append("🔴 整体数据可信度低，建议谨慎使用分析结果")
        
        if reliability_metrics.statistical_confidence < 60:
            alerts.append("🟡 统计置信度不足，结论可能存在较大误差")
        
        if quality_scores.get('accuracy', DataQualityScore("", 100, "", [], [])).score < 70:
            alerts.append("🟡 数据准确性存疑，建议进行人工审核")
        
        if quality_scores.get('completeness', DataQualityScore("", 100, "", [], [])).score < 60:
            alerts.append("🟡 数据完整性不足，可能影响分析全面性")
        
        if reliability_metrics.sample_representativeness < 70:
            alerts.append("🟡 样本代表性有限，结论推广性可能受限")
        
        return alerts