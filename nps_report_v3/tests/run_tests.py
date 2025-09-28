#!/usr/bin/env python3
"""
Comprehensive test runner for NPS V3 Analysis System.

Provides various test execution modes and comprehensive reporting
for validating the complete NPS analysis system functionality.
"""

import sys
import os
import argparse
import subprocess
import json
from pathlib import Path
from datetime import datetime
import logging

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class NPSTestRunner:
    """Comprehensive test runner for NPS V3 system."""

    def __init__(self):
        """Initialize test runner."""
        self.test_dir = Path(__file__).parent
        self.project_root = self.test_dir.parent
        self.results_dir = self.test_dir / "results"
        self.results_dir.mkdir(exist_ok=True)

        # Test categories
        self.test_categories = {
            "unit": {
                "description": "Fast unit tests for individual components",
                "markers": "unit",
                "files": ["test_models.py"],
                "timeout": 60
            },
            "integration": {
                "description": "Integration tests for component interactions",
                "markers": "integration",
                "files": ["test_integration.py"],
                "timeout": 300
            },
            "generators": {
                "description": "Report generator and template tests",
                "markers": None,
                "files": ["test_generators.py"],
                "timeout": 180
            },
            "full": {
                "description": "Complete test suite (all tests)",
                "markers": None,
                "files": ["test_models.py", "test_generators.py", "test_integration.py"],
                "timeout": 600
            }
        }

    def run_tests(
        self,
        category: str = "full",
        verbose: bool = True,
        coverage: bool = True,
        html_report: bool = True,
        parallel: bool = False,
        fail_fast: bool = False,
        capture_output: bool = False
    ) -> dict:
        """
        Run tests with specified configuration.

        Args:
            category: Test category to run
            verbose: Enable verbose output
            coverage: Enable coverage reporting
            html_report: Generate HTML coverage report
            parallel: Run tests in parallel
            fail_fast: Stop on first failure
            capture_output: Capture test output

        Returns:
            Test execution results
        """
        if category not in self.test_categories:
            raise ValueError(f"Unknown test category: {category}. Available: {list(self.test_categories.keys())}")

        logger.info(f"Running {category} tests for NPS V3 Analysis System")

        # Prepare pytest command
        pytest_cmd = ["python", "-m", "pytest"]

        # Add test files
        test_config = self.test_categories[category]
        if test_config["files"]:
            for test_file in test_config["files"]:
                test_path = self.test_dir / test_file
                if test_path.exists():
                    pytest_cmd.append(str(test_path))

        # Add markers
        if test_config["markers"]:
            pytest_cmd.extend(["-m", test_config["markers"]])

        # Verbosity
        if verbose:
            pytest_cmd.append("-v")
        else:
            pytest_cmd.append("-q")

        # Coverage
        if coverage:
            pytest_cmd.extend([
                "--cov=nps_report_v3",
                "--cov-report=term-missing",
                f"--cov-report=json:{self.results_dir}/coverage.json"
            ])

            if html_report:
                pytest_cmd.append(f"--cov-report=html:{self.results_dir}/htmlcov")

        # Parallel execution
        if parallel:
            try:
                import pytest_xdist
                pytest_cmd.extend(["-n", "auto"])
            except ImportError:
                logger.warning("pytest-xdist not available, running sequentially")

        # Fail fast
        if fail_fast:
            pytest_cmd.append("-x")

        # Output capture
        if capture_output:
            pytest_cmd.append("-s")
        else:
            pytest_cmd.append("--tb=short")

        # JUnit XML for CI
        junit_path = self.results_dir / f"junit_{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xml"
        pytest_cmd.extend(["--junit-xml", str(junit_path)])

        # Timeout
        pytest_cmd.extend(["--timeout", str(test_config["timeout"])])

        # Execute tests
        logger.info(f"Executing: {' '.join(pytest_cmd)}")
        start_time = datetime.now()

        try:
            result = subprocess.run(
                pytest_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=test_config["timeout"] + 60  # Add buffer to pytest timeout
            )

            end_time = datetime.now()
            duration = end_time - start_time

            # Process results
            test_results = {
                "category": category,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "duration_seconds": duration.total_seconds(),
                "return_code": result.returncode,
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "command": " ".join(pytest_cmd),
                "junit_report": str(junit_path) if junit_path.exists() else None
            }

            # Parse coverage if available
            coverage_file = self.results_dir / "coverage.json"
            if coverage and coverage_file.exists():
                try:
                    with open(coverage_file, 'r') as f:
                        coverage_data = json.load(f)
                    test_results["coverage"] = {
                        "total_coverage": coverage_data["totals"]["percent_covered"],
                        "lines_covered": coverage_data["totals"]["covered_lines"],
                        "lines_missing": coverage_data["totals"]["missing_lines"],
                        "files": len(coverage_data["files"])
                    }
                except Exception as e:
                    logger.warning(f"Could not parse coverage data: {e}")

            # Save results
            results_file = self.results_dir / f"test_results_{category}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(results_file, 'w') as f:
                json.dump(test_results, f, indent=2)

            # Log summary
            self._log_test_summary(test_results)

            return test_results

        except subprocess.TimeoutExpired:
            logger.error(f"Tests timed out after {test_config['timeout']} seconds")
            return {
                "category": category,
                "success": False,
                "error": "Test execution timed out",
                "timeout": test_config["timeout"]
            }

        except Exception as e:
            logger.error(f"Test execution failed: {e}")
            return {
                "category": category,
                "success": False,
                "error": str(e)
            }

    def _log_test_summary(self, results: dict) -> None:
        """Log test execution summary."""
        print(f"\n{'='*60}")
        print(f"NPS V3 Test Results Summary - {results['category'].title()}")
        print(f"{'='*60}")
        print(f"Status: {'✅ PASSED' if results['success'] else '❌ FAILED'}")
        print(f"Duration: {results['duration_seconds']:.2f} seconds")
        print(f"Start Time: {results['start_time']}")
        print(f"End Time: {results['end_time']}")

        if "coverage" in results:
            cov = results["coverage"]
            print(f"Coverage: {cov['total_coverage']:.1f}% ({cov['lines_covered']}/{cov['lines_covered'] + cov['lines_missing']} lines)")
            print(f"Files Tested: {cov['files']}")

        if not results['success']:
            print(f"\n❌ Error Details:")
            if results.get('stderr'):
                print(results['stderr'])

        print(f"{'='*60}\n")

    def run_smoke_tests(self) -> dict:
        """Run quick smoke tests to verify basic functionality."""
        logger.info("Running smoke tests...")

        smoke_cmd = [
            "python", "-m", "pytest",
            str(self.test_dir / "test_models.py::TestNPSMetrics::test_valid_nps_metrics"),
            str(self.test_dir / "test_generators.py::TestTemplateManager::test_template_manager_initialization"),
            "-v", "--tb=short", "--timeout=30"
        ]

        try:
            result = subprocess.run(
                smoke_cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=60
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "errors": result.stderr,
                "duration": "< 1 minute"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def validate_test_environment(self) -> dict:
        """Validate test environment and dependencies."""
        logger.info("Validating test environment...")

        validation_results = {
            "environment": "valid",
            "issues": [],
            "warnings": [],
            "dependencies": {}
        }

        # Check Python version
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        validation_results["python_version"] = python_version

        if sys.version_info < (3, 8):
            validation_results["issues"].append(f"Python {python_version} is too old, requires 3.8+")

        # Check required packages
        required_packages = [
            "pytest", "pytest-asyncio", "pytest-cov", "pydantic", "jinja2"
        ]

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                validation_results["dependencies"][package] = "✅ Available"
            except ImportError:
                validation_results["dependencies"][package] = "❌ Missing"
                validation_results["issues"].append(f"Missing required package: {package}")

        # Check optional packages
        optional_packages = ["pytest-xdist", "pytest-html", "pytest-timeout"]
        for package in optional_packages:
            try:
                __import__(package.replace("-", "_"))
                validation_results["dependencies"][package] = "✅ Available"
            except ImportError:
                validation_results["dependencies"][package] = "⚠️ Optional"
                validation_results["warnings"].append(f"Optional package not available: {package}")

        # Check project structure
        required_dirs = ["models", "generators", "templates", "agents", "workflows"]
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if not dir_path.exists():
                validation_results["issues"].append(f"Missing required directory: {dir_name}")

        # Check test files
        test_files = ["test_models.py", "test_generators.py", "test_integration.py", "conftest.py"]
        for test_file in test_files:
            test_path = self.test_dir / test_file
            if not test_path.exists():
                validation_results["issues"].append(f"Missing test file: {test_file}")

        # Overall validation status
        validation_results["environment"] = "invalid" if validation_results["issues"] else "valid"

        return validation_results

    def generate_test_report(self) -> str:
        """Generate comprehensive test report."""
        report_lines = []
        report_lines.append("# NPS V3 Analysis System - Test Report")
        report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report_lines.append("")

        # Environment validation
        env_validation = self.validate_test_environment()
        report_lines.append("## Environment Validation")
        report_lines.append(f"Status: {'✅ Valid' if env_validation['environment'] == 'valid' else '❌ Invalid'}")
        report_lines.append(f"Python Version: {env_validation['python_version']}")
        report_lines.append("")

        if env_validation["issues"]:
            report_lines.append("### Issues Found:")
            for issue in env_validation["issues"]:
                report_lines.append(f"- ❌ {issue}")
            report_lines.append("")

        if env_validation["warnings"]:
            report_lines.append("### Warnings:")
            for warning in env_validation["warnings"]:
                report_lines.append(f"- ⚠️ {warning}")
            report_lines.append("")

        # Dependencies
        report_lines.append("### Dependencies:")
        for dep, status in env_validation["dependencies"].items():
            report_lines.append(f"- {dep}: {status}")
        report_lines.append("")

        # Test categories
        report_lines.append("## Available Test Categories")
        for category, config in self.test_categories.items():
            report_lines.append(f"### {category.title()}")
            report_lines.append(f"Description: {config['description']}")
            report_lines.append(f"Files: {', '.join(config['files'])}")
            report_lines.append(f"Timeout: {config['timeout']} seconds")
            report_lines.append("")

        # Usage examples
        report_lines.append("## Usage Examples")
        report_lines.append("```bash")
        report_lines.append("# Run all tests")
        report_lines.append("python run_tests.py --category full")
        report_lines.append("")
        report_lines.append("# Run unit tests only")
        report_lines.append("python run_tests.py --category unit")
        report_lines.append("")
        report_lines.append("# Run with coverage")
        report_lines.append("python run_tests.py --coverage --html-report")
        report_lines.append("")
        report_lines.append("# Run smoke tests")
        report_lines.append("python run_tests.py --smoke-tests")
        report_lines.append("```")

        report_content = "\n".join(report_lines)

        # Save report
        report_file = self.results_dir / f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report_content)

        logger.info(f"Test report generated: {report_file}")
        return str(report_file)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="NPS V3 Analysis System Test Runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --category unit                    # Run unit tests
  %(prog)s --category integration             # Run integration tests
  %(prog)s --category full --coverage         # Run all tests with coverage
  %(prog)s --smoke-tests                      # Quick smoke tests
  %(prog)s --validate                         # Validate test environment
  %(prog)s --generate-report                  # Generate test report
        """
    )

    parser.add_argument(
        "--category", "-c",
        choices=["unit", "integration", "generators", "full"],
        default="full",
        help="Test category to run (default: full)"
    )

    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Enable coverage reporting"
    )

    parser.add_argument(
        "--html-report",
        action="store_true",
        help="Generate HTML coverage report"
    )

    parser.add_argument(
        "--parallel", "-p",
        action="store_true",
        help="Run tests in parallel (requires pytest-xdist)"
    )

    parser.add_argument(
        "--fail-fast", "-x",
        action="store_true",
        help="Stop on first failure"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=True,
        help="Enable verbose output (default: True)"
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Reduce output verbosity"
    )

    parser.add_argument(
        "--capture-output", "-s",
        action="store_true",
        help="Capture test output (don't suppress stdout/stderr)"
    )

    parser.add_argument(
        "--smoke-tests",
        action="store_true",
        help="Run quick smoke tests only"
    )

    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate test environment only"
    )

    parser.add_argument(
        "--generate-report",
        action="store_true",
        help="Generate comprehensive test report"
    )

    args = parser.parse_args()

    # Initialize test runner
    runner = NPSTestRunner()

    try:
        # Handle different modes
        if args.validate:
            validation = runner.validate_test_environment()
            print(json.dumps(validation, indent=2))
            return 0 if validation["environment"] == "valid" else 1

        elif args.generate_report:
            report_file = runner.generate_test_report()
            print(f"Test report generated: {report_file}")
            return 0

        elif args.smoke_tests:
            smoke_results = runner.run_smoke_tests()
            print(f"Smoke tests: {'✅ PASSED' if smoke_results['success'] else '❌ FAILED'}")
            if not smoke_results['success']:
                print(smoke_results.get('errors', ''))
            return 0 if smoke_results['success'] else 1

        else:
            # Run full tests
            verbose = args.verbose and not args.quiet

            results = runner.run_tests(
                category=args.category,
                verbose=verbose,
                coverage=args.coverage,
                html_report=args.html_report,
                parallel=args.parallel,
                fail_fast=args.fail_fast,
                capture_output=args.capture_output
            )

            return 0 if results["success"] else 1

    except KeyboardInterrupt:
        print("\n⚠️ Test execution interrupted by user")
        return 130

    except Exception as e:
        print(f"❌ Test runner failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())