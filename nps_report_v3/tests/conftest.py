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
from .test_generators import TestNPSDataFactory


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
    return TestNPSDataFactory.create_nps_metrics()


@pytest.fixture
def sample_confidence_assessment():
    """Provide sample confidence assessment for testing."""
    return TestNPSDataFactory.create_confidence_assessment()


@pytest.fixture
def sample_agent_insights():
    """Provide sample agent insights for testing."""
    return TestNPSDataFactory.create_agent_insights()


@pytest.fixture
def sample_business_recommendations():
    """Provide sample business recommendations for testing."""
    return TestNPSDataFactory.create_consulting_recommendations()


@pytest.fixture
def sample_executive_dashboard(sample_business_recommendations):
    """Provide sample executive dashboard for testing."""
    return TestNPSDataFactory.create_executive_dashboard()


@pytest.fixture
def complete_nps_response(
    sample_nps_metrics,
    sample_confidence_assessment,
    sample_agent_insights,
    sample_business_recommendations,
    sample_executive_dashboard
):
    """Provide complete NPS analysis response for testing."""
    return TestNPSDataFactory.create_complete_analysis_response()


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
