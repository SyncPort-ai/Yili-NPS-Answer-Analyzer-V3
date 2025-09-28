"""
NPS V3 Report Generators

This module provides comprehensive report generation capabilities for the NPS V3 analysis system,
including dual-format output (JSON + HTML) with professional styling and interactive features.

Key Components:
- HTMLReportGenerator: Professional HTML report generation with TailwindCSS styling
- DualOutputGenerator: Orchestrates both JSON and HTML output generation
- Template management with Jinja2 support and fallback rendering
- Executive dashboards and detailed analysis reports
- Automated file organization and quality validation

Usage Examples:

    # Generate complete dual-format report package
    from nps_report_v3.generators import generate_standard_reports

    report_package = await generate_standard_reports(
        analysis_result,
        output_directory="outputs/reports",
        company_name="
)��"
    )

    # Generate executive report only
    from nps_report_v3.generators import quick_executive_report

    json_path, html_path = await quick_executive_report(analysis_result)

    # Generate custom HTML report
    from nps_report_v3.generators import HTMLReportGenerator

    generator = HTMLReportGenerator(company_name="
)��")
    html_path = await generator.generate_executive_dashboard(analysis_response)

Report Types:
- Executive Dashboard: High-level KPI metrics and strategic recommendations
- Detailed Analysis: Comprehensive multi-agent analysis with tabbed interface
- Custom Reports: Template-based reports with flexible configurations
- JSON Exports: Structured data for system integration and data analysis

Features:
- Professional styling with TailwindCSS and Chart.js
- Responsive design for desktop and mobile viewing
- Print-friendly formatting
- Interactive charts and visualizations
- Quality validation and error handling
- Automated file management and organization
- Comprehensive metadata and summaries
"""

from .html_report_generator import (
    HTMLReportGenerator,
    render_executive_dashboard,
    render_detailed_analysis,
    validate_report_quality
)

from .dual_output_generator import (
    DualOutputGenerator,
    generate_standard_reports,
    quick_executive_report
)

# Version and metadata
__version__ = "3.0.0"
__author__ = "NPS V3 Development Team"

# Exported classes and functions
__all__ = [
    # Main generator classes
    "HTMLReportGenerator",
    "DualOutputGenerator",

    # Convenience functions
    "render_executive_dashboard",
    "render_detailed_analysis",
    "generate_standard_reports",
    "quick_executive_report",

    # Validation utilities
    "validate_report_quality",
]

# Default configuration for generators
DEFAULT_CONFIG = {
    "company_name": "伊利集团",
    "output_directory": "outputs/reports",
    "include_charts": True,
    "include_metadata": True,
    "responsive_design": True,
    "print_friendly": True,
    "quality_validation": True,
    "file_organization": "by_type"
}

# Supported output formats
SUPPORTED_FORMATS = {
    "html": {
        "extensions": [".html", ".htm"],
        "mime_type": "text/html",
        "description": "Interactive HTML reports with charts and styling"
    },
    "json": {
        "extensions": [".json"],
        "mime_type": "application/json",
        "description": "Structured JSON data for system integration"
    }
}

# Template types available
TEMPLATE_TYPES = {
    "executive_dashboard": {
        "description": "High-level executive dashboard with KPI metrics",
        "target_audience": "Executives and senior management",
        "features": ["NPS metrics", "Risk alerts", "Strategic recommendations"]
    },
    "detailed_analysis": {
        "description": "Comprehensive multi-agent analysis report",
        "target_audience": "Analysts and product teams",
        "features": ["Agent insights", "Dimensional analysis", "Tabbed interface"]
    },
    "base_template": {
        "description": "Base template with common styling and functionality",
        "target_audience": "Template developers",
        "features": ["Common CSS", "JavaScript utilities", "Responsive layout"]
    }
}


def get_generator_info() -> dict:
    """
    Get information about available generators and their capabilities.

    Returns:
        Dictionary with generator information
    """
    return {
        "version": __version__,
        "supported_formats": SUPPORTED_FORMATS,
        "template_types": TEMPLATE_TYPES,
        "default_config": DEFAULT_CONFIG,
        "features": {
            "dual_output": True,
            "interactive_charts": True,
            "responsive_design": True,
            "print_support": True,
            "chinese_localization": True,
            "quality_validation": True,
            "custom_templates": True,
            "metadata_generation": True
        }
    }


def validate_generator_environment() -> dict:
    """
    Validate that the generator environment is properly configured.

    Returns:
        Validation results with any issues found
    """
    validation = {
        "is_valid": True,
        "issues": [],
        "warnings": [],
        "dependencies": {}
    }

    # Check for Jinja2
    try:
        import jinja2
        validation["dependencies"]["jinja2"] = jinja2.__version__
    except ImportError:
        validation["warnings"].append("Jinja2 not available, using fallback templating")
        validation["dependencies"]["jinja2"] = "not installed"

    # Check for required modules
    required_modules = ["pathlib", "datetime", "json", "uuid", "asyncio"]
    for module in required_modules:
        try:
            __import__(module)
            validation["dependencies"][module] = "available"
        except ImportError:
            validation["issues"].append(f"Required module not available: {module}")
            validation["is_valid"] = False

    return validation


# Initialize logging for the generators module
import logging

logger = logging.getLogger(__name__)
logger.info(f"NPS V3 Report Generators module loaded (version {__version__})")

# Validate environment on import
env_validation = validate_generator_environment()
if not env_validation["is_valid"]:
    logger.error(f"Generator environment validation failed: {env_validation['issues']}")
elif env_validation["warnings"]:
    for warning in env_validation["warnings"]:
        logger.warning(warning)