"""
Comprehensive tests for NPS V3 Pydantic models.

Tests cover model validation, serialization, deserialization,
and edge cases for all response models.
"""

import pytest
from datetime import datetime
from typing import Dict, Any, List
from pydantic import ValidationError
import json

from nps_report_v3.models.response import (
    NPSMetrics,
    ConfidenceAssessment,
    AgentInsight,
    BusinessRecommendation,
    ExecutiveDashboard,
    NPSAnalysisResponse,
    build_analysis_response,
    create_minimal_response,
    validate_agent_insights
)


class TestNPSMetrics:
    """Test NPS metrics model."""

    def test_valid_nps_metrics(self):
        """Test creation of valid NPS metrics."""
        metrics = NPSMetrics(
            nps_score=45,
            promoter_count=50,
            passive_count=30,
            detractor_count=20,
            sample_size=100,
            statistical_significance=True
        )

        assert metrics.nps_score == 45
        assert metrics.promoter_count == 50
        assert metrics.passive_count == 30
        assert metrics.detractor_count == 20
        assert metrics.sample_size == 100
        assert metrics.statistical_significance is True

    def test_nps_score_validation(self):
        """Test NPS score validation."""
        # Valid NPS scores
        valid_scores = [-100, -50, 0, 25, 50, 75, 100]
        for score in valid_scores:
            metrics = NPSMetrics(
                nps_score=score,
                promoter_count=10,
                passive_count=10,
                detractor_count=10,
                sample_size=30
            )
            assert metrics.nps_score == score

        # Invalid NPS scores
        invalid_scores = [-101, 101, 150, -200]
        for score in invalid_scores:
            with pytest.raises(ValidationError):
                NPSMetrics(
                    nps_score=score,
                    promoter_count=10,
                    passive_count=10,
                    detractor_count=10,
                    sample_size=30
                )

    def test_count_validation(self):
        """Test count field validation."""
        # Negative counts should fail
        with pytest.raises(ValidationError):
            NPSMetrics(
                nps_score=0,
                promoter_count=-1,
                passive_count=10,
                detractor_count=10,
                sample_size=30
            )

    def test_sample_size_consistency(self):
        """Test sample size consistency validation."""
        # Sample size should be at least the sum of counts
        metrics = NPSMetrics(
            nps_score=0,
            promoter_count=10,
            passive_count=20,
            detractor_count=30,
            sample_size=60  # Equals sum
        )
        assert metrics.sample_size == 60

        # Sample size can be larger (some responses might not have scores)
        metrics = NPSMetrics(
            nps_score=0,
            promoter_count=10,
            passive_count=20,
            detractor_count=30,
            sample_size=80  # Larger than sum
        )
        assert metrics.sample_size == 80

    def test_nps_metrics_serialization(self):
        """Test NPS metrics JSON serialization."""
        metrics = NPSMetrics(
            nps_score=45,
            promoter_count=50,
            passive_count=30,
            detractor_count=20,
            sample_size=100,
            statistical_significance=True
        )

        # Test dict conversion
        metrics_dict = metrics.dict()
        assert metrics_dict["nps_score"] == 45
        assert metrics_dict["statistical_significance"] is True

        # Test JSON serialization
        json_str = metrics.json()
        parsed_data = json.loads(json_str)
        assert parsed_data["nps_score"] == 45

    def test_nps_classification_property(self):
        """Test NPS classification computed property."""
        # Excellent NPS
        excellent_metrics = NPSMetrics(
            nps_score=75, promoter_count=80, passive_count=10,
            detractor_count=5, sample_size=95
        )
        # Would need to implement classification property in model

        # Poor NPS
        poor_metrics = NPSMetrics(
            nps_score=-30, promoter_count=10, passive_count=20,
            detractor_count=70, sample_size=100
        )
        # Would need to implement classification property in model


class TestConfidenceAssessment:
    """Test confidence assessment model."""

    def test_valid_confidence_assessment(self):
        """Test creation of valid confidence assessment."""
        assessment = ConfidenceAssessment(
            overall_confidence_score=0.75,
            overall_confidence_text="中",
            data_quality_score=0.80,
            analysis_completeness_score=0.70,
            statistical_significance_score=0.75
        )

        assert assessment.overall_confidence_score == 0.75
        assert assessment.overall_confidence_text == "中"
        assert assessment.data_quality_score == 0.80

    def test_confidence_score_validation(self):
        """Test confidence score validation (0.0 to 1.0)."""
        # Valid scores
        valid_scores = [0.0, 0.5, 1.0, 0.75, 0.123]
        for score in valid_scores:
            assessment = ConfidenceAssessment(
                overall_confidence_score=score,
                overall_confidence_text="测试",
                data_quality_score=score,
                analysis_completeness_score=score,
                statistical_significance_score=score
            )
            assert assessment.overall_confidence_score == score

        # Invalid scores
        invalid_scores = [-0.1, 1.1, 2.0, -1.0]
        for score in invalid_scores:
            with pytest.raises(ValidationError):
                ConfidenceAssessment(
                    overall_confidence_score=score,
                    overall_confidence_text="测试",
                    data_quality_score=0.5,
                    analysis_completeness_score=0.5,
                    statistical_significance_score=0.5
                )

    def test_confidence_text_validation(self):
        """Test confidence text validation."""
        valid_texts = ["高", "中", "低", "excellent", "good", "poor"]
        for text in valid_texts:
            assessment = ConfidenceAssessment(
                overall_confidence_score=0.5,
                overall_confidence_text=text,
                data_quality_score=0.5,
                analysis_completeness_score=0.5,
                statistical_significance_score=0.5
            )
            assert assessment.overall_confidence_text == text

        # Empty text should fail
        with pytest.raises(ValidationError):
            ConfidenceAssessment(
                overall_confidence_score=0.5,
                overall_confidence_text="",
                data_quality_score=0.5,
                analysis_completeness_score=0.5,
                statistical_significance_score=0.5
            )


class TestAgentInsight:
    """Test agent insight model."""

    def test_valid_agent_insight(self):
        """Test creation of valid agent insight."""
        insight = AgentInsight(
            agent_id="B1",
            title="测试洞察",
            summary="测试摘要",
            content="详细的洞察内容，包含分析结果和建议。",
            category="技术分析",
            priority="高",
            confidence=0.85,
            impact_score=0.75,
            timestamp=datetime.now().isoformat()
        )

        assert insight.agent_id == "B1"
        assert insight.title == "测试洞察"
        assert insight.priority == "高"
        assert insight.confidence == 0.85

    def test_agent_id_validation(self):
        """Test agent ID validation."""
        valid_ids = ["A0", "A1", "B1", "B9", "C1", "C5"]
        for agent_id in valid_ids:
            insight = AgentInsight(
                agent_id=agent_id,
                title="测试",
                summary="测试",
                content="测试内容",
                category="测试",
                priority="中",
                confidence=0.5,
                impact_score=0.5
            )
            assert insight.agent_id == agent_id

        # Invalid agent IDs
        invalid_ids = ["", "X1", "A10", "invalid"]
        for agent_id in invalid_ids:
            with pytest.raises(ValidationError):
                AgentInsight(
                    agent_id=agent_id,
                    title="测试",
                    summary="测试",
                    content="测试内容",
                    category="测试",
                    priority="中",
                    confidence=0.5,
                    impact_score=0.5
                )

    def test_priority_validation(self):
        """Test priority validation."""
        valid_priorities = ["高", "中", "低", "high", "medium", "low"]
        for priority in valid_priorities:
            insight = AgentInsight(
                agent_id="B1",
                title="测试",
                summary="测试",
                content="测试内容",
                category="测试",
                priority=priority,
                confidence=0.5,
                impact_score=0.5
            )
            assert insight.priority == priority

        # Invalid priorities
        invalid_priorities = ["", "urgent", "critical", "无效"]
        for priority in invalid_priorities:
            with pytest.raises(ValidationError):
                AgentInsight(
                    agent_id="B1",
                    title="测试",
                    summary="测试",
                    content="测试内容",
                    category="测试",
                    priority=priority,
                    confidence=0.5,
                    impact_score=0.5
                )

    def test_content_length_validation(self):
        """Test content length validation."""
        # Very short content should fail
        with pytest.raises(ValidationError):
            AgentInsight(
                agent_id="B1",
                title="测试",
                summary="测试",
                content="短",  # Too short
                category="测试",
                priority="中",
                confidence=0.5,
                impact_score=0.5
            )

        # Normal content should pass
        insight = AgentInsight(
            agent_id="B1",
            title="测试",
            summary="测试",
            content="这是一个足够长的内容，包含了详细的分析和建议。",
            category="测试",
            priority="中",
            confidence=0.5,
            impact_score=0.5
        )
        assert len(insight.content) >= 10

    def test_timestamp_validation(self):
        """Test timestamp validation."""
        # Valid ISO timestamps
        valid_timestamps = [
            datetime.now().isoformat(),
            "2024-01-01T12:00:00",
            "2024-01-01T12:00:00.000Z"
        ]

        for timestamp in valid_timestamps:
            insight = AgentInsight(
                agent_id="B1",
                title="测试",
                summary="测试",
                content="测试内容详细信息",
                category="测试",
                priority="中",
                confidence=0.5,
                impact_score=0.5,
                timestamp=timestamp
            )
            assert insight.timestamp == timestamp


class TestBusinessRecommendation:
    """Test business recommendation model."""

    def test_valid_business_recommendation(self):
        """Test creation of valid business recommendation."""
        recommendation = BusinessRecommendation(
            title="优化客户体验流程",
            description="通过改进服务流程和技术手段，提升整体客户体验质量。",
            category="客户体验",
            priority="高",
            expected_impact="显著提升客户满意度和忠诚度",
            confidence_score=0.85,
            implementation_timeline="3-6个月内完成主要改进措施"
        )

        assert recommendation.title == "优化客户体验流程"
        assert recommendation.priority == "高"
        assert recommendation.confidence_score == 0.85

    def test_required_fields(self):
        """Test required fields validation."""
        # Missing title should fail
        with pytest.raises(ValidationError):
            BusinessRecommendation(
                description="描述",
                category="类别",
                priority="中",
                confidence_score=0.5
            )

        # Missing description should fail
        with pytest.raises(ValidationError):
            BusinessRecommendation(
                title="标题",
                category="类别",
                priority="中",
                confidence_score=0.5
            )

    def test_optional_fields(self):
        """Test optional fields handling."""
        # Minimal recommendation
        recommendation = BusinessRecommendation(
            title="基础建议",
            description="基础描述内容",
            priority="中",
            confidence_score=0.5
        )

        assert recommendation.category is None
        assert recommendation.expected_impact is None
        assert recommendation.implementation_timeline is None

    def test_confidence_score_validation(self):
        """Test confidence score validation for recommendations."""
        # Valid confidence scores
        valid_scores = [0.0, 0.5, 1.0, 0.75]
        for score in valid_scores:
            recommendation = BusinessRecommendation(
                title="测试建议",
                description="测试描述",
                priority="中",
                confidence_score=score
            )
            assert recommendation.confidence_score == score

        # Invalid confidence scores
        invalid_scores = [-0.1, 1.1, 2.0]
        for score in invalid_scores:
            with pytest.raises(ValidationError):
                BusinessRecommendation(
                    title="测试建议",
                    description="测试描述",
                    priority="中",
                    confidence_score=score
                )


class TestExecutiveDashboard:
    """Test executive dashboard model."""

    def test_valid_executive_dashboard(self):
        """Test creation of valid executive dashboard."""
        recommendations = [
            BusinessRecommendation(
                title="建议1",
                description="建议描述1",
                priority="高",
                confidence_score=0.8
            ),
            BusinessRecommendation(
                title="建议2",
                description="建议描述2",
                priority="中",
                confidence_score=0.7
            )
        ]

        dashboard = ExecutiveDashboard(
            executive_summary="整体分析摘要，包含关键发现和建议。",
            top_recommendations=recommendations,
            risk_alerts=["风险提示1", "风险提示2"],
            key_performance_indicators={
                "客户满意度": "75%",
                "NPS得分": "45",
                "响应时间": "24小时"
            }
        )

        assert "整体分析摘要" in dashboard.executive_summary
        assert len(dashboard.top_recommendations) == 2
        assert len(dashboard.risk_alerts) == 2
        assert "客户满意度" in dashboard.key_performance_indicators

    def test_empty_collections(self):
        """Test handling of empty collections."""
        dashboard = ExecutiveDashboard(
            executive_summary="基础摘要",
            top_recommendations=[],
            risk_alerts=[],
            key_performance_indicators={}
        )

        assert dashboard.executive_summary == "基础摘要"
        assert len(dashboard.top_recommendations) == 0
        assert len(dashboard.risk_alerts) == 0
        assert len(dashboard.key_performance_indicators) == 0

    def test_kpi_validation(self):
        """Test KPI dictionary validation."""
        # Valid KPIs
        valid_kpis = {
            "metric1": "value1",
            "指标2": "数值2",
            "NPS": "45",
            "satisfaction_rate": "85%"
        }

        dashboard = ExecutiveDashboard(
            executive_summary="测试摘要",
            top_recommendations=[],
            risk_alerts=[],
            key_performance_indicators=valid_kpis
        )

        assert dashboard.key_performance_indicators == valid_kpis


class TestNPSAnalysisResponse:
    """Test complete NPS analysis response model."""

    def create_complete_response(self) -> NPSAnalysisResponse:
        """Create complete test response."""
        return NPSAnalysisResponse(
            response_id="test_response_123",
            nps_metrics=NPSMetrics(
                nps_score=45,
                promoter_count=50,
                passive_count=30,
                detractor_count=20,
                sample_size=100,
                statistical_significance=True
            ),
            confidence_assessment=ConfidenceAssessment(
                overall_confidence_score=0.75,
                overall_confidence_text="中",
                data_quality_score=0.80,
                analysis_completeness_score=0.70,
                statistical_significance_score=0.75
            ),
            foundation_insights=[
                AgentInsight(
                    agent_id="A0",
                    title="数据清洗结果",
                    summary="数据质量良好",
                    content="完成数据清洗和预处理，数据质量评估结果良好。",
                    category="数据处理",
                    priority="低",
                    confidence=0.95,
                    impact_score=0.85
                )
            ],
            analysis_insights=[
                AgentInsight(
                    agent_id="B1",
                    title="技术需求分析",
                    summary="客户技术需求分析",
                    content="分析客户对产品技术功能的需求和期望，识别改进机会。",
                    category="技术分析",
                    priority="高",
                    confidence=0.82,
                    impact_score=0.78
                )
            ],
            consulting_recommendations=[
                BusinessRecommendation(
                    title="优化产品技术架构",
                    description="基于客户需求分析，优化产品技术架构和功能设计。",
                    category="技术改进",
                    priority="高",
                    expected_impact="提升用户体验",
                    confidence_score=0.85,
                    implementation_timeline="3-6个月"
                )
            ],
            executive_dashboard=ExecutiveDashboard(
                executive_summary="整体客户满意度中等，存在明显改进空间。",
                top_recommendations=[
                    BusinessRecommendation(
                        title="建立客户反馈机制",
                        description="建立系统性的客户反馈收集和处理机制。",
                        priority="中",
                        confidence_score=0.75
                    )
                ],
                risk_alerts=["客户流失风险增加"],
                key_performance_indicators={"NPS": "45", "满意度": "75%"}
            )
        )

    def test_valid_complete_response(self):
        """Test creation of valid complete response."""
        response = self.create_complete_response()

        assert response.response_id == "test_response_123"
        assert response.nps_metrics.nps_score == 45
        assert len(response.foundation_insights) == 1
        assert len(response.analysis_insights) == 1
        assert len(response.consulting_recommendations) == 1

    def test_response_serialization(self):
        """Test response serialization to dict and JSON."""
        response = self.create_complete_response()

        # Test dict conversion
        response_dict = response.dict()
        assert response_dict["response_id"] == "test_response_123"
        assert response_dict["nps_metrics"]["nps_score"] == 45
        assert isinstance(response_dict["foundation_insights"], list)

        # Test JSON serialization
        json_str = response.json()
        parsed_data = json.loads(json_str)
        assert parsed_data["response_id"] == "test_response_123"
        assert parsed_data["nps_metrics"]["nps_score"] == 45

    def test_response_deserialization(self):
        """Test response deserialization from dict and JSON."""
        original_response = self.create_complete_response()
        response_dict = original_response.dict()

        # Test dict deserialization
        deserialized_response = NPSAnalysisResponse(**response_dict)
        assert deserialized_response.response_id == original_response.response_id
        assert deserialized_response.nps_metrics.nps_score == original_response.nps_metrics.nps_score

        # Test JSON deserialization
        json_str = original_response.json()
        parsed_dict = json.loads(json_str)
        json_deserialized_response = NPSAnalysisResponse(**parsed_dict)
        assert json_deserialized_response.response_id == original_response.response_id

    def test_minimal_response_creation(self):
        """Test creation of minimal response with required fields only."""
        minimal_response = NPSAnalysisResponse(
            response_id="minimal_123",
            nps_metrics=NPSMetrics(
                nps_score=0,
                promoter_count=0,
                passive_count=0,
                detractor_count=0,
                sample_size=0
            ),
            executive_dashboard=ExecutiveDashboard(
                executive_summary="最小摘要",
                top_recommendations=[],
                risk_alerts=[],
                key_performance_indicators={}
            )
        )

        assert minimal_response.response_id == "minimal_123"
        assert minimal_response.confidence_assessment is None  # Optional field
        assert len(minimal_response.foundation_insights) == 0  # Default empty list


class TestUtilityFunctions:
    """Test utility functions for model creation and validation."""

    def test_build_analysis_response(self):
        """Test build_analysis_response utility function."""
        # Test data
        response_data = {
            "response_id": "built_response",
            "nps_score": 60,
            "promoter_count": 70,
            "passive_count": 20,
            "detractor_count": 10,
            "sample_size": 100,
            "executive_summary": "良好的客户满意度表现",
            "insights": [
                {
                    "agent_id": "B1",
                    "title": "客户满意度分析",
                    "summary": "客户整体满意度较高",
                    "content": "详细的客户满意度分析结果和建议措施。",
                    "category": "客户分析",
                    "priority": "中",
                    "confidence": 0.8,
                    "impact_score": 0.7
                }
            ],
            "recommendations": [
                {
                    "title": "维护客户关系",
                    "description": "继续维护现有的良好客户关系",
                    "priority": "中",
                    "confidence_score": 0.75
                }
            ]
        }

        response = build_analysis_response(response_data)

        assert response.response_id == "built_response"
        assert response.nps_metrics.nps_score == 60
        assert len(response.analysis_insights) == 1
        assert len(response.consulting_recommendations) == 1

    def test_create_minimal_response(self):
        """Test create_minimal_response utility function."""
        minimal = create_minimal_response(
            response_id="minimal_test",
            nps_score=25,
            summary="最小响应测试"
        )

        assert minimal.response_id == "minimal_test"
        assert minimal.nps_metrics.nps_score == 25
        assert "最小响应测试" in minimal.executive_dashboard.executive_summary

    def test_validate_agent_insights(self):
        """Test validate_agent_insights utility function."""
        # Valid insights
        valid_insights = [
            AgentInsight(
                agent_id="B1",
                title="洞察1",
                summary="摘要1",
                content="详细内容1，包含足够的分析信息。",
                category="分析",
                priority="高",
                confidence=0.8,
                impact_score=0.7
            ),
            AgentInsight(
                agent_id="B2",
                title="洞察2",
                summary="摘要2",
                content="详细内容2，包含足够的分析信息。",
                category="分析",
                priority="中",
                confidence=0.7,
                impact_score=0.6
            )
        ]

        validation_result = validate_agent_insights(valid_insights)
        assert validation_result["is_valid"]
        assert validation_result["total_insights"] == 2
        assert len(validation_result["issues"]) == 0

        # Invalid insights (duplicate agent IDs)
        invalid_insights = [
            AgentInsight(
                agent_id="B1",  # Duplicate
                title="洞察1",
                summary="摘要1",
                content="详细内容1，包含足够的分析信息。",
                category="分析",
                priority="高",
                confidence=0.8,
                impact_score=0.7
            ),
            AgentInsight(
                agent_id="B1",  # Duplicate
                title="洞察2",
                summary="摘要2",
                content="详细内容2，包含足够的分析信息。",
                category="分析",
                priority="中",
                confidence=0.7,
                impact_score=0.6
            )
        ]

        validation_result = validate_agent_insights(invalid_insights)
        assert not validation_result["is_valid"]
        assert len(validation_result["issues"]) > 0


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_unicode_content(self):
        """Test handling of Unicode content."""
        insight = AgentInsight(
            agent_id="B1",
            title="Unicode测试🚀",
            summary="包含emoji和特殊字符的摘要📊",
            content="详细内容包含各种字符：中文、English、数字123、符号@#$%、emoji🎯📈💡",
            category="特殊测试",
            priority="中",
            confidence=0.5,
            impact_score=0.5
        )

        # Should handle Unicode properly
        assert "🚀" in insight.title
        assert "📊" in insight.summary
        assert "💡" in insight.content

    def test_very_long_content(self):
        """Test handling of very long content."""
        long_content = "这是一个非常长的内容。" * 1000  # Very long string

        insight = AgentInsight(
            agent_id="B1",
            title="长内容测试",
            summary="测试长内容处理",
            content=long_content,
            category="测试",
            priority="低",
            confidence=0.5,
            impact_score=0.5
        )

        assert len(insight.content) > 10000
        # Should not cause validation errors

    def test_boundary_values(self):
        """Test boundary values for numeric fields."""
        # Test minimum values
        min_metrics = NPSMetrics(
            nps_score=-100,  # Minimum NPS
            promoter_count=0,
            passive_count=0,
            detractor_count=0,
            sample_size=0
        )
        assert min_metrics.nps_score == -100

        # Test maximum values
        max_metrics = NPSMetrics(
            nps_score=100,  # Maximum NPS
            promoter_count=1000000,
            passive_count=1000000,
            detractor_count=1000000,
            sample_size=3000000
        )
        assert max_metrics.nps_score == 100

    def test_none_values(self):
        """Test handling of None values in optional fields."""
        # Response with minimal data and None values
        response = NPSAnalysisResponse(
            response_id="none_test",
            nps_metrics=NPSMetrics(
                nps_score=0,
                promoter_count=0,
                passive_count=0,
                detractor_count=0,
                sample_size=0
            ),
            confidence_assessment=None,  # Optional
            foundation_insights=[],
            analysis_insights=[],
            consulting_recommendations=[],
            executive_dashboard=ExecutiveDashboard(
                executive_summary="基础摘要",
                top_recommendations=[],
                risk_alerts=[],
                key_performance_indicators={}
            )
        )

        assert response.confidence_assessment is None
        assert len(response.foundation_insights) == 0


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])