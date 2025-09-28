"""
NPS V3 Analysis System Test Suite

Comprehensive testing framework for validating the NPS V3 multi-agent analysis system.
Includes unit tests, integration tests, performance tests, and end-to-end validation.

Test Categories:
- Unit Tests: Fast tests for individual components and models
- Integration Tests: Tests for component interactions and workflow orchestration
- Generator Tests: Tests for report generation and template rendering
- Performance Tests: Load testing and performance validation
- End-to-End Tests: Complete workflow validation from data input to report output

Usage:
    # Run all tests
    python -m pytest

    # Run specific test category
    python -m pytest -m unit
    python -m pytest -m integration

    # Run with coverage
    python -m pytest --cov=nps_report_v3

    # Use the comprehensive test runner
    cd tests && python run_tests.py --category full --coverage

Test Structure:
- conftest.py: Shared fixtures and test configuration
- test_models.py: Pydantic model validation tests
- test_generators.py: Report generator and template tests
- test_integration.py: End-to-end workflow integration tests
- run_tests.py: Comprehensive test runner with reporting
- pytest.ini: Pytest configuration and settings

Key Features:
- Async test support for workflow testing
- Mock LLM responses for reliable testing
- Coverage reporting with HTML output
- Performance monitoring and validation
- Chinese language content testing
- Comprehensive error handling validation
- Template rendering quality validation
- Data consistency verification through pipeline

Test Data:
- Sample survey responses with Chinese content
- Mock NPS analysis results
- Template test data with various scenarios
- Performance test datasets
- Edge case and error condition data

Quality Assurance:
- All tests include Chinese language validation
- Performance benchmarks for large datasets
- Memory usage monitoring
- Error recovery and resilience testing
- Data privacy and PII handling validation

CI/CD Integration:
- JUnit XML output for CI systems
- Coverage reporting compatible with standard tools
- Test result archival and trend analysis
- Environment validation before test execution
"""

import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

# Test suite metadata
__version__ = "3.0.0"
__author__ = "NPS V3 Development Team"

# Test configuration
TEST_CONFIG = {
    "default_timeout": 300,
    "performance_timeout": 600,
    "integration_timeout": 900,
    "coverage_threshold": 80,
    "performance_benchmark": {
        "max_response_time": 30.0,
        "max_memory_usage_mb": 512,
        "large_dataset_size": 1000
    },
    "supported_languages": ["zh-CN", "en-US"],
    "test_data_encoding": "utf-8"
}

# Export test utilities
__all__ = [
    "TEST_CONFIG"
]


def get_test_info():
    """Get information about the test suite."""
    return {
        "version": __version__,
        "test_files": [
            "test_models.py",
            "test_generators.py",
            "test_integration.py"
        ],
        "test_categories": [
            "unit",
            "integration",
            "generators",
            "performance",
            "smoke"
        ],
        "features": {
            "async_support": True,
            "coverage_reporting": True,
            "performance_monitoring": True,
            "chinese_language_support": True,
            "mock_llm_responses": True,
            "html_report_validation": True,
            "end_to_end_testing": True
        },
        "configuration": TEST_CONFIG
    }


def validate_test_environment():
    """Validate that the test environment is properly configured."""
    import importlib

    validation_results = {
        "is_valid": True,
        "missing_dependencies": [],
        "warnings": []
    }

    # Check required test dependencies
    required_packages = [
        "pytest",
        "pytest_asyncio",
        "pydantic",
        "pathlib",
        "datetime",
        "json",
        "tempfile",
        "unittest.mock"
    ]

    for package in required_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            validation_results["missing_dependencies"].append(package)
            validation_results["is_valid"] = False

    # Check optional dependencies
    optional_packages = [
        "pytest_cov",
        "pytest_xdist",
        "pytest_html",
        "pytest_timeout",
        "jinja2"
    ]

    for package in optional_packages:
        try:
            importlib.import_module(package)
        except ImportError:
            validation_results["warnings"].append(f"Optional package not available: {package}")

    # Check project structure
    required_modules = [
        "nps_report_v3.models.response",
        "nps_report_v3.generators.dual_output_generator",
        "nps_report_v3.templates.template_manager"
    ]

    for module in required_modules:
        try:
            importlib.import_module(module)
        except ImportError:
            validation_results["missing_dependencies"].append(f"Project module: {module}")
            validation_results["is_valid"] = False

    return validation_results