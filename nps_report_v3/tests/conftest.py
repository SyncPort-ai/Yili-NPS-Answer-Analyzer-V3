"""
Pytest configuration and fixtures for NPS V3 testing.

Provides common fixtures, test configuration, and utilities
for comprehensive testing of the NPS analysis system.
"""

import pytest
import asyncio
import tempfile
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
from unittest.mock import Mock, AsyncMock

# Configure test logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import test dependencies
from nps_report_v3.models.response import (
    NPSAnalysisResponse,
    NPSMetrics,
    ExecutiveDashboard,
    AgentInsight,
    BusinessRecommendation,
    ConfidenceAssessment
)
from nps_report_v3.generators.dual_output_generator import DualOutputGenerator
from nps_report_v3.templates.template_manager import TemplateManager


# Pytest configuration
def pytest_configure(config):
    """Configure pytest settings."""
    # Add custom markers
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests (deselect with '-m \"not integration\"')"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_llm: marks tests that require LLM API access"
    )

    # Set test session configuration
    config.test_start_time = datetime.now()


def pytest_sessionstart(session):
    """Called after the Session object has been created."""
    print(f"\n{'='*60}")
    print("NPS V3 Analysis System Test Suite")
    print(f"Test session started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")


def pytest_sessionfinish(session, exitstatus):
    """Called after whole test run finished."""
    duration = datetime.now() - session.config.test_start_time
    print(f"\n{'='*60}")
    print(f"Test session completed in: {duration}")
    print(f"Exit status: {exitstatus}")
    print(f"{'='*60}\n")


# Async test configuration
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Common fixtures
@pytest.fixture
def temp_directory():
    """Provide temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_nps_metrics():
    """Provide sample NPS metrics for testing."""
    return NPSMetrics(
        nps_score=45,
        promoter_count=50,
        passive_count=30,
        detractor_count=20,
        sample_size=100,
        statistical_significance=True
    )


@pytest.fixture
def sample_confidence_assessment():
    """Provide sample confidence assessment for testing."""
    return ConfidenceAssessment(
        overall_confidence_score=0.75,
        overall_confidence_text="中",
        data_quality_score=0.80,
        analysis_completeness_score=0.70,
        statistical_significance_score=0.75
    )


@pytest.fixture
def sample_agent_insights():
    """Provide sample agent insights for testing."""
    return [
        AgentInsight(
            agent_id="B1",
            title="技术需求分析结果",
            summary="客户对产品技术功能的需求分析",
            content="通过分析客户反馈，识别出以下技术改进需求：1）提升产品稳定性；2）优化用户界面设计；3）增加智能化功能。建议优先改进产品稳定性，这是客户最关注的技术问题。",
            category="技术分析",
            priority="高",
            confidence=0.82,
            impact_score=0.78,
            timestamp=datetime.now().isoformat()
        ),
        AgentInsight(
            agent_id="B2",
            title="被动客户转化分析",
            summary="7-8分被动客户的转化潜力分析",
            content="被动客户主要关注性价比和服务质量。转化策略建议：1）推出更多优惠活动；2）改善客户服务响应时间；3）提供个性化产品推荐。预计通过这些措施可以将30%的被动客户转化为推荐者。",
            category="客户分析",
            priority="中",
            confidence=0.75,
            impact_score=0.68,
            timestamp=datetime.now().isoformat()
        ),
        AgentInsight(
            agent_id="B3",
            title="贬损客户挽回分析",
            summary="0-6分贬损客户的问题识别和挽回策略",
            content="贬损客户的主要问题：1）产品质量不稳定（45%）；2）客服响应慢（30%）；3）价格偏高（25%）。挽回策略：建立快速响应机制、提供质量保证、制定挽回补偿方案。预计可以挽回40%的贬损客户。",
            category="风险管理",
            priority="高",
            confidence=0.79,
            impact_score=0.85,
            timestamp=datetime.now().isoformat()
        )
    ]


@pytest.fixture
def sample_business_recommendations():
    """Provide sample business recommendations for testing."""
    return [
        BusinessRecommendation(
            title="建立全面的客户体验管理体系",
            description="构建从数据收集、分析、改进到监控的完整客户体验管理流程，确保客户满意度的持续提升。",
            category="战略建议",
            priority="高",
            expected_impact="全面提升客户满意度和品牌忠诚度",
            confidence_score=0.88,
            implementation_timeline="6-12个月内建立完整体系，包括组织架构调整、流程优化、系统建设等关键环节。"
        ),
        BusinessRecommendation(
            title="产品创新与差异化发展策略",
            description="基于深度客户需求洞察，开发具有差异化竞争优势的产品功能和服务，提升市场竞争力。",
            category="产品策略",
            priority="中",
            expected_impact="增强市场竞争力，扩大市场份额",
            confidence_score=0.75,
            implementation_timeline="3-6个月完成产品创新规划，12-18个月实现市场化。"
        ),
        BusinessRecommendation(
            title="客户服务质量提升计划",
            description="通过服务流程优化、人员培训、技术升级等手段，全面提升客户服务质量和满意度。",
            category="服务改进",
            priority="高",
            expected_impact="显著改善客户服务体验，降低客户流失率",
            confidence_score=0.82,
            implementation_timeline="1-3个月完成培训和流程优化，持续监控和改进。"
        )
    ]


@pytest.fixture
def sample_executive_dashboard(sample_business_recommendations):
    """Provide sample executive dashboard for testing."""
    return ExecutiveDashboard(
        executive_summary="整体客户满意度处于中等水平，NPS得分45分，存在明显提升空间。推荐者占50%，被动客户30%，贬损客户20%。主要改进领域包括产品质量稳定性、客户服务响应速度、以及价格竞争力。通过系统性的客户体验管理和产品创新，预计可将NPS提升至60分以上。",
        top_recommendations=sample_business_recommendations,
        risk_alerts=[
            "产品质量不稳定性可能导致客户流失加剧，需要立即关注生产质量管控。",
            "客服响应时间过长影响客户体验，建议优化服务流程和增加人力投入。",
            "价格竞争压力增大，需要平衡成本控制与价值提升的策略。",
            "竞争对手推出新产品，市场份额可能受到冲击，需要加快产品创新步伐。"
        ],
        key_performance_indicators={
            "客户满意度": "75%",
            "产品质量评分": "4.2/5.0",
            "服务响应时间": "24小时",
            "市场份额": "32%",
            "客户留存率": "85%",
            "品牌知名度": "78%"
        }
    )


@pytest.fixture
def complete_nps_response(
    sample_nps_metrics,
    sample_confidence_assessment,
    sample_agent_insights,
    sample_business_recommendations,
    sample_executive_dashboard
):
    """Provide complete NPS analysis response for testing."""
    return NPSAnalysisResponse(
        response_id="test_analysis_complete_001",
        nps_metrics=sample_nps_metrics,
        confidence_assessment=sample_confidence_assessment,
        foundation_insights=[
            AgentInsight(
                agent_id="A0",
                title="数据清洗与质量评估",
                summary="完成原始数据的清洗和质量评估",
                content="处理了100条原始响应数据，清洗后得到100条有效数据。数据质量评估：完整性95%，准确性92%，一致性90%。已完成PII脱敏处理，数据符合隐私保护要求。",
                category="数据处理",
                priority="低",
                confidence=0.95,
                impact_score=0.85,
                timestamp=datetime.now().isoformat()
            ),
            AgentInsight(
                agent_id="A1",
                title="NPS基础计算结果",
                summary="完成NPS得分计算和统计分析",
                content="计算得出NPS得分为45分。推荐者（9-10分）50人，占50%；被动客户（7-8分）30人，占30%；贬损客户（0-6分）20人，占20%。样本量100，具有统计显著性。",
                category="统计分析",
                priority="中",
                confidence=0.92,
                impact_score=0.90,
                timestamp=datetime.now().isoformat()
            ),
            AgentInsight(
                agent_id="A2",
                title="响应内容标注结果",
                summary="完成客户反馈内容的智能标注",
                content="对客户反馈进行了多维度标注：情感极性（正面60%、中性25%、负面15%），主题分类（产品质量40%、服务体验35%、价格因素25%），关键词提取（质量、服务、价格、口感、包装等）。",
                category="文本分析",
                priority="中",
                confidence=0.88,
                impact_score=0.75,
                timestamp=datetime.now().isoformat()
            ),
            AgentInsight(
                agent_id="A3",
                title="语义聚类分析结果",
                summary="识别客户反馈的主要话题聚类",
                content="识别出5个主要话题聚类：1）产品质量与口感（30条）；2）服务体验与态度（25条）；3）价格与性价比（20条）；4）包装与外观（15条）；5）购买便利性（10条）。每个聚类都提取了核心关键词和典型评论。",
                category="话题分析",
                priority="中",
                confidence=0.85,
                impact_score=0.80,
                timestamp=datetime.now().isoformat()
            )
        ],
        analysis_insights=sample_agent_insights,
        consulting_recommendations=sample_business_recommendations,
        executive_dashboard=sample_executive_dashboard
    )


@pytest.fixture
def mock_llm_client():
    """Provide mock LLM client for testing."""
    mock_client = AsyncMock()

    async def mock_call_llm(prompt, **kwargs):
        """Mock LLM call that returns contextual responses."""
        if "数据清洗" in prompt or "data cleaning" in prompt:
            return """
            {
                "cleaned_responses": [
                    {"id": "001", "score": 9, "comment": "产品质量很好"},
                    {"id": "002", "score": 7, "comment": "服务还可以"}
                ],
                "data_quality": "good",
                "pii_removed": true
            }
            """
        elif "NPS" in prompt or "score" in prompt:
            return """
            {
                "nps_score": 45,
                "promoter_count": 50,
                "passive_count": 30,
                "detractor_count": 20,
                "sample_size": 100
            }
            """
        elif "推荐" in prompt or "recommendation" in prompt:
            return """
            {
                "recommendations": [
                    {"title": "提升产品质量", "priority": "高", "impact": "显著"}
                ]
            }
            """
        else:
            return """
            {
                "result": "mock_response",
                "status": "completed"
            }
            """

    mock_client.call_llm = mock_call_llm
    return mock_client


@pytest.fixture
def sample_survey_data():
    """Provide sample survey data for testing."""
    return [
        {
            "response_id": "test_001",
            "score": 9,
            "comment": "伊利安慕希酸奶的口感非常棒，质感丝滑，味道纯正。包装设计也很精美，是我经常购买的品牌。会推荐给朋友们。",
            "product": "安慕希",
            "region": "华东地区",
            "channel": "线上商城",
            "customer_type": "忠实用户",
            "purchase_frequency": "每周",
            "demographics": {
                "age_group": "25-35",
                "gender": "女",
                "income_level": "中高"
            }
        },
        {
            "response_id": "test_002",
            "score": 8,
            "comment": "金典牛奶品质不错，营养丰富，但是价格稍微有点贵。希望能有更多的促销活动。",
            "product": "金典",
            "region": "华北地区",
            "channel": "连锁超市",
            "customer_type": "普通用户",
            "purchase_frequency": "每月",
            "demographics": {
                "age_group": "35-45",
                "gender": "男",
                "income_level": "中等"
            }
        },
        {
            "response_id": "test_003",
            "score": 7,
            "comment": "舒化奶的口感还可以，适合乳糖不耐受的人群。但包装可以更现代化一些。",
            "product": "舒化",
            "region": "华南地区",
            "channel": "便利店",
            "customer_type": "新用户",
            "purchase_frequency": "偶尔",
            "demographics": {
                "age_group": "18-25",
                "gender": "女",
                "income_level": "中等"
            }
        },
        {
            "response_id": "test_004",
            "score": 10,
            "comment": "优酸乳是孩子们最喜欢的饮品，口味多样，营养均衡。质量一直很稳定，值得信赖。",
            "product": "优酸乳",
            "region": "西南地区",
            "channel": "专卖店",
            "customer_type": "家庭用户",
            "purchase_frequency": "每周",
            "demographics": {
                "age_group": "35-45",
                "gender": "女",
                "income_level": "中高"
            }
        },
        {
            "response_id": "test_005",
            "score": 6,
            "comment": "味可滋最近的口感不如以前了，可能是配方调整了。希望能够改回原来的味道。",
            "product": "味可滋",
            "region": "东北地区",
            "channel": "线上商城",
            "customer_type": "老用户",
            "purchase_frequency": "每月",
            "demographics": {
                "age_group": "25-35",
                "gender": "男",
                "income_level": "中等"
            }
        },
        {
            "response_id": "test_006",
            "score": 4,
            "comment": "客服态度不够好，配送也经常延迟。产品质量也不稳定，有时候会有异味。",
            "product": "安慕希",
            "region": "华东地区",
            "channel": "线上商城",
            "customer_type": "普通用户",
            "purchase_frequency": "很少",
            "demographics": {
                "age_group": "45-55",
                "gender": "男",
                "income_level": "中等"
            }
        },
        {
            "response_id": "test_007",
            "score": 3,
            "comment": "金典牛奶有酸味，可能是过期了或者储存不当。退货过程很麻烦，体验很差。",
            "product": "金典",
            "region": "华北地区",
            "channel": "连锁超市",
            "customer_type": "新用户",
            "purchase_frequency": "首次",
            "demographics": {
                "age_group": "55+",
                "gender": "女",
                "income_level": "中低"
            }
        },
        {
            "response_id": "test_008",
            "score": 8,
            "comment": "整体来说还是不错的产品，质量稳定，口感也好。希望能推出更多新口味。",
            "product": "舒化",
            "region": "华南地区",
            "channel": "便利店",
            "customer_type": "忠实用户",
            "purchase_frequency": "每周",
            "demographics": {
                "age_group": "18-25",
                "gender": "男",
                "income_level": "中等"
            }
        },
        {
            "response_id": "test_009",
            "score": 9,
            "comment": "QQ星儿童牛奶很受小朋友欢迎，营养成分丰富，包装也很可爱。会继续购买。",
            "product": "QQ星",
            "region": "西南地区",
            "channel": "专卖店",
            "customer_type": "家庭用户",
            "purchase_frequency": "每周",
            "demographics": {
                "age_group": "35-45",
                "gender": "女",
                "income_level": "中高"
            }
        },
        {
            "response_id": "test_010",
            "score": 5,
            "comment": "伊小欢的口感一般，价格也不便宜。性价比不高，可能不会再购买了。",
            "product": "伊小欢",
            "region": "东北地区",
            "channel": "线上商城",
            "customer_type": "普通用户",
            "purchase_frequency": "偶尔",
            "demographics": {
                "age_group": "25-35",
                "gender": "女",
                "income_level": "中等"
            }
        }
    ]


@pytest.fixture
def test_output_generator(temp_directory):
    """Provide test output generator."""
    return DualOutputGenerator(
        output_directory=temp_directory,
        company_name="伊利集团测试"
    )


@pytest.fixture
def test_template_manager(temp_directory):
    """Provide test template manager."""
    return TemplateManager(template_dir=temp_directory)


# Utility fixtures
@pytest.fixture
def capture_logs():
    """Capture logs during test execution."""
    import logging
    from io import StringIO

    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)

    # Get the root logger and add our handler
    logger = logging.getLogger('nps_report_v3')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    yield log_capture

    # Clean up
    logger.removeHandler(handler)


@pytest.fixture
def performance_monitor():
    """Monitor test performance."""
    import time
    import psutil
    import os

    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
            self.process = psutil.Process(os.getpid())

        def start(self):
            self.start_time = time.time()
            self.start_memory = self.process.memory_info().rss / 1024 / 1024  # MB

        def stop(self):
            end_time = time.time()
            end_memory = self.process.memory_info().rss / 1024 / 1024  # MB

            return {
                'duration': end_time - self.start_time,
                'memory_start_mb': self.start_memory,
                'memory_end_mb': end_memory,
                'memory_diff_mb': end_memory - self.start_memory
            }

    monitor = PerformanceMonitor()
    yield monitor


# Custom pytest markers and helpers
class TestHelpers:
    """Helper methods for tests."""

    @staticmethod
    def validate_nps_score(score):
        """Validate NPS score is in valid range."""
        return -100 <= score <= 100

    @staticmethod
    def validate_json_structure(json_data, required_fields):
        """Validate JSON data has required structure."""
        if not isinstance(json_data, dict):
            return False

        for field in required_fields:
            if field not in json_data:
                return False

        return True

    @staticmethod
    def count_chinese_chars(text):
        """Count Chinese characters in text."""
        return sum(1 for char in text if '\u4e00' <= char <= '\u9fff')

    @staticmethod
    def extract_nps_components(responses):
        """Extract NPS components from response list."""
        promoters = sum(1 for r in responses if r.get('score', 0) >= 9)
        passives = sum(1 for r in responses if 7 <= r.get('score', 0) <= 8)
        detractors = sum(1 for r in responses if r.get('score', 0) <= 6)

        return {
            'promoters': promoters,
            'passives': passives,
            'detractors': detractors,
            'total': len(responses)
        }


@pytest.fixture
def test_helpers():
    """Provide test helper methods."""
    return TestHelpers()


# Test data validation fixtures
@pytest.fixture
def data_validator():
    """Provide data validation utilities."""
    class DataValidator:
        @staticmethod
        def validate_nps_response(response):
            """Validate NPSAnalysisResponse structure."""
            required_fields = [
                'response_id', 'nps_metrics', 'executive_dashboard'
            ]

            for field in required_fields:
                if not hasattr(response, field):
                    return False, f"Missing required field: {field}"

            return True, "Valid"

        @staticmethod
        def validate_html_content(html_content):
            """Validate HTML content structure."""
            required_elements = [
                '<!DOCTYPE html>',
                '<html',
                '<head>',
                '<body>',
                '</html>'
            ]

            for element in required_elements:
                if element not in html_content:
                    return False, f"Missing HTML element: {element}"

            return True, "Valid HTML"

        @staticmethod
        def validate_json_report(json_data):
            """Validate JSON report structure."""
            required_sections = [
                'analysis_results',
                'report_metadata'
            ]

            if not isinstance(json_data, dict):
                return False, "JSON data must be a dictionary"

            for section in required_sections:
                if section not in json_data:
                    return False, f"Missing JSON section: {section}"

            return True, "Valid JSON report"

    return DataValidator()