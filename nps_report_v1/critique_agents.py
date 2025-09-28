"""
批评和修订系统 - NPS分析多智能体系统的质量保证层

该模块实现了四个专家评审智能体，用于评估和改进NPS分析结果：
- NPSExpertCritic：评估统计准确性和方法论
- LinguisticsExpertCritic：评估自然语言处理质量
- BusinessAnalystCritic：评估战略洞察价值
- ReportQualityCritic：评估报告专业性和可读性

按要求所有输出都使用中文，但类名和变量使用英文。
"""

import json
import re
from typing import Dict, List, Any, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)

@dataclass
class CritiqueResult:
    """批评结果的数据结构"""
    reviewer: str
    severity: str  # "低", "中", "高", "严重"
    overall_score: float  # 0-10分值
    issues: List[str]
    recommendations: List[str]
    specific_changes: List[Dict[str, str]]
    needs_revision: bool

class NPSExpertCritic:
    """NPS方法论和统计分析专家评审员"""
    
    def __init__(self):
        self.expertise_areas = [
            "NPS计算准确性",
            "统计显著性检验",
            "样本代表性分析", 
            "趋势分析方法论",
            "基准比较有效性",
            "客户分群逻辑"
        ]
    
    def review_nps_analysis(self, analysis_results: Dict) -> CritiqueResult:
        """评审NPS计算准确性和方法论"""
        issues = []
        recommendations = []
        changes = []
        
        # 检查NPS计算公式
        if 'nps_score' in analysis_results:
            nps_score = analysis_results['nps_score']
            if not (-100 <= nps_score <= 100):
                issues.append(f"NPS分数 {nps_score} 超出有效范围 [-100, 100]")
                recommendations.append("重新验证NPS计算公式：(推荐者% - 批评者%) × 100")
        
        # 对于小型演示数据集跳过样本量批评
        # 注意：根据用户请求，小型测试数据集禁用样本量验证
        if 'total_responses' in analysis_results:
            sample_size = analysis_results['total_responses']
            # 仅在样本量极小时（< 5）标记，以避免演示噪音
            if sample_size < 5:
                issues.append(f"样本量 {sample_size} 极小，仅适用于系统测试")
                recommendations.append("实际使用时建议样本量至少达到30份")
        
        # 检查分群逻辑
        if 'segments' in analysis_results:
            for segment_name, segment_data in analysis_results['segments'].items():
                if segment_data.get('count', 0) < 10:
                    issues.append(f"客户分群 '{segment_name}' 样本量过小 ({segment_data.get('count', 0)})")
                    recommendations.append(f"合并小样本分群或增加 '{segment_name}' 分群的样本收集")
        
        # 评估严重程度和分数
        severity = self._assess_severity(issues)
        score = self._calculate_score(issues, recommendations)
        
        return CritiqueResult(
            reviewer="NPS专家评审员",
            severity=severity,
            overall_score=score,
            issues=issues,
            recommendations=recommendations,
            specific_changes=changes,
            needs_revision=len(issues) > 0
        )
    
    def _assess_severity(self, issues: List[str]) -> str:
        """根据问题数量和类型评估严重程度"""
        critical_issues = [issue for issue in issues if any(keyword in issue for keyword in ["严重", "不可信", "超出范围"])]
        moderate_issues = [issue for issue in issues if any(keyword in issue for keyword in ["可能", "建议", "较低"])]
        
        if len(critical_issues) > 0:
            return "严重"
        elif len(moderate_issues) > 2:
            return "高"
        elif len(moderate_issues) > 0:
            return "中"
        else:
            return "低"
    
    def _calculate_score(self, issues: List[str], recommendations: List[str]) -> float:
        """计算0-10质量分数"""
        base_score = 10.0
        for issue in issues:
            if any(keyword in issue for keyword in ["严重", "不可信"]):
                base_score -= 3.0
            elif any(keyword in issue for keyword in ["可能", "较低"]):
                base_score -= 1.5
            else:
                base_score -= 1.0
        return max(0.0, min(10.0, base_score))

class LinguisticsExpertCritic:
    """自然语言处理和中文文本分析专家评审员"""
    
    def __init__(self):
        self.expertise_areas = [
            "中文文本预处理质量",
            "情感分析准确性", 
            "主题提取合理性",
            "实体识别完整性",
            "语义相似度计算",
            "文本分类有效性"
        ]
    
    def review_text_processing_quality(self, analysis_results: Dict) -> CritiqueResult:
        """评审文本处理和NLP分析质量"""
        issues = []
        recommendations = []
        changes = []
        
        # 检查情感分析结果 - 改进的带类型安全逻辑
        if 'sentiment_analysis' in analysis_results:
            sentiment_analysis = analysis_results['sentiment_analysis']
            
            # 安全提取情感计数，处理数字和字典值
            def extract_sentiment_count(sentiment_data, key):
                value = sentiment_data.get(key, 0)
                if isinstance(value, dict):
                    # 如果是字典，尝试获取'count'字段或返回0
                    return value.get('count', 0)
                elif isinstance(value, (int, float)):
                    return value
                else:
                    return 0
            
            positive_count = extract_sentiment_count(sentiment_analysis, 'positive')
            negative_count = extract_sentiment_count(sentiment_analysis, 'negative')
            neutral_count = extract_sentiment_count(sentiment_analysis, 'neutral')
            total_count = positive_count + negative_count + neutral_count
            
            # 检查是否执行了情感分析（即使所有零对某些数据集都是有效的）
            if sentiment_analysis is None or (not isinstance(sentiment_analysis, dict)):
                issues.append("情感分析结果为空，可能存在文本预处理问题")
                recommendations.append("检查文本预处理流程和情感分析模型配置")
            elif total_count == 0:
                # 这对于某些数据集可能是有效的，所以设为低严重性问题
                issues.append("情感分析未产生分类结果，可能是中性文本或需要调整阈值")
                recommendations.append("检查情感分析阈值设置，确保能够识别细微情感倾向")
            
            # 检查情感分布合理性
            if neutral_count / max(total_count, 1) > 0.8:
                issues.append("中性情感比例过高 (>80%)，可能存在情感识别不准确问题")
                recommendations.append("调整情感分析阈值或使用更敏感的情感识别模型")
        
        # 检查主题提取质量 - 为小数据集改进
        if 'themes' in analysis_results:
            themes_list = analysis_results['themes']
            total_responses = analysis_results.get('total_responses', 10)  # 默认后备值
            
            # 根据数据集大小调整期望
            if total_responses <= 6:  # 小型演示数据集
                min_expected_themes = 1
            elif total_responses <= 20:
                min_expected_themes = 2  
            else:
                min_expected_themes = 3
                
            if len(themes_list) < min_expected_themes:
                issues.append(f"识别的主题数量为 {len(themes_list)} 个，期望至少 {min_expected_themes} 个主题")
                recommendations.append("调整主题提取参数以识别更多相关主题")
            elif len(themes_list) > 20:
                issues.append(f"识别的主题数量过多 ({len(themes_list)}个)，主题过于分散")
                recommendations.append("提高主题聚类的相似度阈值或合并相似主题")
        
        # 检查实体识别结果
        if 'entities' in analysis_results:
            entities_data = analysis_results['entities']
            product_entities = entities_data.get('products', [])
            yili_products = ['安慕希', '金典', '舒化', '味可滋', '奶粉', 'QQ星', 'JoyDay']
            
            identified_yili_products = [p for p in product_entities if any(brand in p for brand in yili_products)]
            if len(identified_yili_products) == 0:
                issues.append("未识别到伊利集团的主要产品实体")
                recommendations.append("增强产品实体识别词典，添加伊利品牌产品关键词")
        
        # Assess severity and score
        severity = self._assess_severity(issues)
        score = self._calculate_score(issues)
        
        return CritiqueResult(
            reviewer="语言学专家评审员",
            severity=severity,
            overall_score=score,
            issues=issues,
            recommendations=recommendations,
            specific_changes=changes,
            needs_revision=len(issues) > 0
        )
    
    def _assess_severity(self, issues: List[str]) -> str:
        """Assess text processing issue severity"""
        if any("为空" in issue or "未识别到" in issue for issue in issues):
            return "严重"
        elif len(issues) > 2:
            return "高"
        elif len(issues) > 0:
            return "中"
        else:
            return "低"
    
    def _calculate_score(self, issues: List[str]) -> float:
        """Calculate text processing quality score - improved scoring logic"""
        base_score = 10.0
        for issue in issues:
            if "为空" in issue and "文本预处理问题" in issue:
                base_score -= 4.0  # Severe technical issues
            elif "未识别到" in issue:
                base_score -= 2.5  # Missing entity recognition 
            elif "未产生分类结果" in issue or "需要调整阈值" in issue:
                base_score -= 1.5  # Configuration issues, less severe
            elif "过高" in issue or "过多" in issue or "数量为" in issue:
                base_score -= 2.0  # Distribution issues
            else:
                base_score -= 1.0  # General issues
        return max(0.0, min(10.0, base_score))

class BusinessAnalystCritic:
    """Business intelligence and strategic analysis expert reviewer"""
    
    def __init__(self):
        self.expertise_areas = [
            "Competitor analysis depth",
            "Market trend insight accuracy",
            "Product portfolio analysis completeness", 
            "Customer value analysis reasonableness",
            "Action recommendation feasibility",
            "Business impact assessment accuracy"
        ]
        
        self.yili_product_lines = {
            'Ambpoial': '安慕希',
            'Satine': '金典', 
            'Jinlinguan': '金领冠',
            'JoyDay': 'JoyDay',
            'SHUHUA': '舒化',
            'Cute Star': 'QQ星',
            'Chocliz': '巧乐兹'
        }
        
        self.main_competitors = ['蒙牛', '光明', '三元', '君乐宝', '飞鹤']
    
    def review_business_insights_quality(self, analysis_results: Dict) -> CritiqueResult:
        """Review business analysis depth and strategic value"""
        issues = []
        recommendations = []
        changes = []
        
        # Check competitor analysis
        if 'competitive_analysis' in analysis_results:
            competitive_analysis = analysis_results['competitive_analysis']
            mentioned_competitors = []
            
            for competitor in self.main_competitors:
                if any(competitor in str(v) for v in competitive_analysis.values()):
                    mentioned_competitors.append(competitor)
            
            if len(mentioned_competitors) == 0:
                issues.append("缺乏竞争对手分析，未提及主要竞争品牌")
                recommendations.append("增加与蒙牛、光明等主要竞争对手的对比分析")
            elif len(mentioned_competitors) < 2:
                issues.append("竞争对手分析深度不足，覆盖范围有限")
                recommendations.append("扩展竞争对手分析，包含至少3个主要竞争品牌")
        
        # Check product portfolio analysis
        if 'product_analysis' in analysis_results:
            product_analysis = analysis_results['product_analysis']
            covered_product_lines = []
            
            for english_name, chinese_name in self.yili_product_lines.items():
                if any(name in str(product_analysis) for name in [english_name, chinese_name]):
                    covered_product_lines.append(chinese_name)
            
            if len(covered_product_lines) < 3:
                issues.append(f"产品组合分析覆盖不全，仅涉及 {len(covered_product_lines)} 个产品线")
                recommendations.append("扩展产品分析，包含安慕希、金典、舒化等主要产品线")
        
        # Check action recommendation quality
        if 'recommendations' in analysis_results:
            recommendations_content = analysis_results['recommendations']
            if isinstance(recommendations_content, list) and len(recommendations_content) == 0:
                issues.append("缺乏具体的行动建议")
                recommendations.append("基于NPS分析结果提供具体、可执行的业务改进建议")
            elif isinstance(recommendations_content, list):
                # Handle both string and dict recommendations
                vague_recommendations = []
                for r in recommendations_content:
                    if isinstance(r, str):
                        # String recommendation
                        if len(r) < 20:
                            vague_recommendations.append(r)
                    elif isinstance(r, dict):
                        # Dict recommendation with category and action
                        if not r.get('action') or len(r.get('action', '')) < 10:
                            vague_recommendations.append(json.dumps(r, ensure_ascii=False))
                if vague_recommendations:
                    issues.append("部分行动建议过于笼统，缺乏具体执行路径")
                    recommendations.append("细化建议，明确具体实施步骤、负责人和时间节点")
        
        # Check market trends analysis completeness
        if 'market_trends' in analysis_results:
            market_trends = analysis_results['market_trends']
            if isinstance(market_trends, list) and len(market_trends) < 2:
                issues.append("市场趋势分析覆盖面有限")
                recommendations.append("拓展市场趋势分析，包含健康消费、价格敏感度、区域差异等维度")
        
        severity = self._assess_severity(issues)
        score = self._calculate_score(issues)
        
        return CritiqueResult(
            reviewer="商业分析专家评审员",
            severity=severity,
            overall_score=score,
            issues=issues,
            recommendations=recommendations,
            specific_changes=changes,
            needs_revision=len(issues) > 0
        )
    
    def _assess_severity(self, issues: List[str]) -> str:
        if len(issues) > 3:
            return "高"
        elif len(issues) > 0:
            return "中"
        else:
            return "低"
    
    def _calculate_score(self, issues: List[str]) -> float:
        base_score = 10.0
        for issue in issues:
            if any(k in issue for k in ["缺乏", "覆盖不全", "有限"]):
                base_score -= 2.0
            else:
                base_score -= 1.0
        return max(0.0, min(10.0, base_score))

class ReportQualityCritic:
    """Report quality expert reviewer for professional presentation and clarity"""
    
    def __init__(self):
        self.required_sections = [
            "executive_summary",
            "detailed_analysis",
            "recommendations",
            "appendix"
        ]
    
    def review_report_quality(self, analysis_results: Dict) -> CritiqueResult:
        issues = []
        recommendations = []
        changes: List[Dict[str, str]] = []
        
        # Check required sections presence
        for section in self.required_sections:
            if section not in analysis_results or not analysis_results.get(section):
                issues.append(f"报告缺少必要部分：{section}")
                recommendations.append(f"补充报告的{section}部分，确保报告结构完整")
        
        # Check executive summary quality
        if 'executive_summary' in analysis_results:
            summary_content = analysis_results['executive_summary']
            if isinstance(summary_content, str) and len(summary_content) < 100:
                issues.append("执行摘要过于简短，缺乏足够的信息密度")
                recommendations.append("扩展执行摘要，包含关键发现、主要结论和核心建议")
            elif isinstance(summary_content, str) and len(summary_content) > 1000:
                issues.append("执行摘要过于冗长，失去摘要作用")
                recommendations.append("精简执行摘要，突出最核心的3-5个关键点")
        
        # Check data visualization
        if 'charts' in analysis_results:
            charts_data = analysis_results['charts']
            if len(charts_data) == 0:
                issues.append("缺乏数据可视化图表，报告可读性差")
                recommendations.append("增加关键指标的可视化图表，如NPS趋势图、分布图等")
            else:
                for i, chart in enumerate(charts_data):
                    if 'title' not in chart or not chart['title']:
                        issues.append(f"图表 {i+1} 缺少标题")
                        recommendations.append(f"为图表 {i+1} 添加清晰的中文标题")
        
        # Check Chinese expression standardization
        if 'detailed_analysis' in analysis_results:
            analysis_content = str(analysis_results['detailed_analysis'])
            
            # Check if too many English terms
            english_words = len(re.findall(r'[a-zA-Z]+', analysis_content))
            chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', analysis_content))
            
            if english_words > chinese_chars * 0.1:  # English words > 10% of Chinese characters
                issues.append("报告中英文术语过多，不符合中文本地化要求")
                recommendations.append("将英文术语翻译为中文，或在首次出现时提供中文解释")
        
        # Check HTML format
        if 'html_report' in analysis_results:
            html_content = analysis_results['html_report']
            if not isinstance(html_content, str) or len(html_content) < 500:
                issues.append("HTML报告内容过少或格式不正确")
                recommendations.append("生成完整的HTML报告，包含样式和交互功能")
            
            # Check basic HTML tags
            required_tags = ['<html>', '<head>', '<body>', '<title>']
            missing_tags = [tag for tag in required_tags if tag not in html_content]
            if missing_tags:
                issues.append(f"HTML格式不规范，缺少标签：{', '.join(missing_tags)}")
                recommendations.append("使用标准HTML5格式生成报告")
        
        # Assess severity and score
        severity = self._assess_severity(issues)
        score = self._calculate_score(issues, analysis_results)
        
        return CritiqueResult(
            reviewer="报告质量专家评审员",
            severity=severity,
            overall_score=score,
            issues=issues,
            recommendations=recommendations,
            specific_changes=changes,
            needs_revision=len(issues) > 0
        )
    
    def _assess_severity(self, issues: List[str]) -> str:
        """Assess report quality issue severity"""
        structure_issues = [issue for issue in issues if "结构" in issue or "缺少" in issue]
        format_issues = [issue for issue in issues if "格式" in issue or "HTML" in issue]
        content_issues = [issue for issue in issues if "过于" in issue or "缺乏" in issue]
        
        if len(structure_issues) > 0:
            return "严重"
        elif len(format_issues) > 1 or len(content_issues) > 2:
            return "高"
        elif len(format_issues) > 0 or len(content_issues) > 0:
            return "中"
        else:
            return "低"
    
    def _calculate_score(self, issues: List[str], analysis_results: Dict) -> float:
        """Calculate report quality score"""
        base_score = 10.0
        
        # Deduct points based on issue type
        for issue in issues:
            if "结构" in issue or "缺少" in issue:
                base_score -= 4.0
            elif "格式" in issue or "HTML" in issue:
                base_score -= 2.5
            elif "过于" in issue or "缺乏" in issue:
                base_score -= 1.5
            else:
                base_score -= 1.0
        
        # Adjust score based on report completeness
        completeness = sum(1 for section in self.required_sections if section in analysis_results) / len(self.required_sections)
        base_score *= (0.5 + 0.5 * completeness)  # Completeness affects 50% of score
        
        return max(0.0, min(10.0, base_score))

def run_all_critics(analysis_results: Dict) -> Dict[str, CritiqueResult]:
    """Run all critic experts and return comprehensive critique results"""
    logger.info("开始运行批评和修订系统...")
    
    critique_results = {}
    
    try:
        # Run NPS expert review
        logger.info("准备运行NPS专家评审...")
        nps_expert = NPSExpertCritic()
        critique_results['nps_expert'] = nps_expert.review_nps_analysis(analysis_results)
        logger.info("NPS专家评审完成")
        
        # Run linguistics expert review  
        logger.info("准备运行语言学专家评审...")
        linguistics_expert = LinguisticsExpertCritic()
        critique_results['linguistics_expert'] = linguistics_expert.review_text_processing_quality(analysis_results)
        logger.info("语言学专家评审完成")
        
        # Run business analyst expert review
        logger.info("准备运行商业分析专家评审...")
        logger.info(f"检查recommendations数据类型: {type(analysis_results.get('recommendations', []))}")
        if 'recommendations' in analysis_results:
            logger.info(f"recommendations内容: {analysis_results['recommendations']}")
        business_expert = BusinessAnalystCritic()
        critique_results['business_expert'] = business_expert.review_business_insights_quality(analysis_results)
        logger.info("商业分析专家评审完成")
        
        # Run report quality expert review
        logger.info("准备运行报告质量专家评审...")
        report_expert = ReportQualityCritic()
        critique_results['report_expert'] = report_expert.review_report_quality(analysis_results)
        logger.info("报告质量专家评审完成")
        
    except Exception as e:
        logger.error(f"评审过程中出现错误: {str(e)}")
        import traceback
        logger.error(f"完整错误堆栈: {traceback.format_exc()}")
        raise
    
    logger.info("所有专家评审完成")
    return critique_results

def generate_revision_summary(critique_results: Dict[str, CritiqueResult]) -> Dict[str, Any]:
    """Generate comprehensive revision recommendation summary"""
    
    overall_score = sum(result.overall_score for result in critique_results.values()) / len(critique_results)
    
    revision_needed_areas = [result.reviewer for result in critique_results.values() if result.needs_revision]
    
    critical_issues_count = sum(1 for result in critique_results.values() if result.severity in ["高", "严重"])
    
    all_recommendations = []
    for result in critique_results.values():
        all_recommendations.extend(result.recommendations)
    
    revision_priority = "高" if critical_issues_count > 2 else "中" if critical_issues_count > 0 else "低"
    
    revision_summary = {
        "总体质量评分": round(overall_score, 2),
        "修订优先级": revision_priority,
        "需要修订的专业领域": revision_needed_areas,
        "严重问题数量": critical_issues_count,
        "综合改进建议": all_recommendations[:10],  # Show only first 10 recommendations
        "专家评审详情": {
            result.reviewer: {
                "评分": result.overall_score,
                "严重程度": result.severity,
                "主要问题": result.issues[:3],  # Show only first 3 issues
                "核心建议": result.recommendations[:3]   # Show only first 3 recommendations
            }
            for result in critique_results.values()
        }
    }
    
    return revision_summary

