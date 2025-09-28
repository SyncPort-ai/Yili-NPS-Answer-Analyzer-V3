"""
NPS Calculator
==============

Professional NPS calculation engine with statistical analysis.
Handles standard NPS methodology with Yili-specific business rules.
"""

from typing import Dict, List, Any, Union
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class NPSDistribution:
    """NPS distribution breakdown."""
    promoters: int
    passives: int  
    detractors: int
    total_responses: int
    nps_score: float
    distribution: Dict[str, int]  # Score 0-10 distribution
    
    @property
    def promoter_percentage(self) -> float:
        return (self.promoters / self.total_responses * 100) if self.total_responses > 0 else 0.0
    
    @property
    def passive_percentage(self) -> float:
        return (self.passives / self.total_responses * 100) if self.total_responses > 0 else 0.0
    
    @property
    def detractor_percentage(self) -> float:
        return (self.detractors / self.total_responses * 100) if self.total_responses > 0 else 0.0


class NPSCalculator:
    """
    Professional NPS calculation engine.
    
    Implements standard NPS methodology:
    - Promoters: 9-10 scores
    - Passives: 7-8 scores  
    - Detractors: 0-6 scores
    - NPS = (% Promoters) - (% Detractors)
    """
    
    def __init__(self):
        logger.info("NPSCalculator initialized")
    
    def calculate_from_scores(self, scores: List[int]) -> NPSDistribution:
        """
        Calculate NPS distribution from list of scores.
        
        Args:
            scores: List of NPS scores (0-10)
            
        Returns:
            NPSDistribution: Complete NPS breakdown
            
        Raises:
            ValueError: If scores contain invalid values
        """
        if not scores:
            raise ValueError("No scores provided")
        
        # Validate scores
        invalid_scores = [s for s in scores if not isinstance(s, int) or s < 0 or s > 10]
        if invalid_scores:
            raise ValueError(f"Invalid scores found: {invalid_scores[:5]}... (must be 0-10)")
        
        # Calculate distribution
        distribution = {str(i): scores.count(i) for i in range(11)}
        
        # Categorize responses
        promoters = sum(scores.count(i) for i in [9, 10])
        passives = sum(scores.count(i) for i in [7, 8])
        detractors = sum(scores.count(i) for i in range(7))
        
        total = len(scores)
        
        # Calculate NPS score
        nps_score = ((promoters - detractors) / total * 100) if total > 0 else 0.0
        
        logger.debug(
            "NPS calculated: Score=%.1f, Promoters=%d, Passives=%d, Detractors=%d, Total=%d",
            nps_score, promoters, passives, detractors, total
        )
        
        return NPSDistribution(
            promoters=promoters,
            passives=passives,
            detractors=detractors,
            total_responses=total,
            nps_score=nps_score,
            distribution=distribution
        )
    
    def calculate_from_responses(self, responses: List[Any]) -> Dict[str, Any]:
        """
        Calculate NPS from response objects with score attribute.
        
        Args:
            responses: List of objects with .score attribute
            
        Returns:
            Dict: NPS metrics in dictionary format for compatibility
        """
        scores = [r.score for r in responses]
        result = self.calculate_from_scores(scores)
        
        return {
            "nps_score": result.nps_score,
            "promoters": result.promoters,
            "passives": result.passives,
            "detractors": result.detractors,
            "total_responses": result.total_responses,
            "distribution": result.distribution,
            "percentages": {
                "promoters": result.promoter_percentage,
                "passives": result.passive_percentage,
                "detractors": result.detractor_percentage
            }
        }
    
    def calculate_from_distribution(self, distribution: Dict[Union[str, int], int]) -> NPSDistribution:
        """
        Calculate NPS from pre-aggregated score distribution.
        
        Args:
            distribution: Dict mapping scores to counts {0: 5, 1: 3, ..., 10: 20}
            
        Returns:
            NPSDistribution: Complete NPS breakdown
        """
        # Normalize keys to integers
        normalized_dist = {}
        for score, count in distribution.items():
            score_int = int(score)
            if 0 <= score_int <= 10:
                normalized_dist[score_int] = int(count)
        
        # Expand to score list for calculation
        scores = []
        for score, count in normalized_dist.items():
            scores.extend([score] * count)
        
        return self.calculate_from_scores(scores)
    
    def get_nps_interpretation(self, nps_score: float) -> Dict[str, str]:
        """
        Provide business interpretation of NPS score.
        
        Args:
            nps_score: NPS score (-100 to +100)
            
        Returns:
            Dict: Interpretation with level, description, and recommendations
        """
        if nps_score >= 70:
            level = "优秀"
            description = "客户忠诚度极高，品牌口碑优异"
            recommendation = "维持现有优势，继续提升客户体验"
        elif nps_score >= 50:
            level = "良好" 
            description = "客户满意度较高，有较强的推荐意愿"
            recommendation = "巩固优势，针对性改进痛点"
        elif nps_score >= 30:
            level = "中等"
            description = "客户满意度一般，推荐意愿有限"
            recommendation = "分析差评原因，重点改进产品和服务"
        elif nps_score >= 0:
            level = "较低"
            description = "客户满意度偏低，贬损者较多"
            recommendation = "紧急改进计划，解决核心问题"
        else:
            level = "需改进"
            description = "客户满意度很低，贬损者显著多于推荐者"
            recommendation = "全面质量提升，重新审视产品策略"
        
        return {
            "level": level,
            "description": description,
            "recommendation": recommendation,
            "industry_context": self._get_industry_context(nps_score)
        }
    
    def _get_industry_context(self, nps_score: float) -> str:
        """Get industry-specific context for NPS score."""
        # Yili dairy industry benchmarks
        if nps_score >= 60:
            return "在乳制品行业中表现优秀，超越行业平均水平"
        elif nps_score >= 40:
            return "达到乳制品行业良好水平，接近头部品牌表现"
        elif nps_score >= 20:
            return "处于乳制品行业平均水平，有提升空间"
        else:
            return "低于乳制品行业平均水平，需重点关注"