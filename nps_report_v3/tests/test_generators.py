"""
Comprehensive tests for NPS V3 report generators.

Tests cover HTML report generation, dual output generation, template management,
and file handling with various scenarios and edge cases.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import the modules to test
from nps_report_v3.generators.html_report_generator import (
    HTMLReportGenerator,
    render_executive_dashboard,
    render_detailed_analysis,
    validate_report_quality
)
from nps_report_v3.generators.dual_output_generator import (
    DualOutputGenerator,
    generate_standard_reports,
    quick_executive_report
)
from nps_report_v3.templates.template_manager import TemplateManager
from nps_report_v3.models.response import (
    NPSAnalysisResponse,
    NPSMetrics,
    ExecutiveDashboard,
    AgentInsight,
    BusinessRecommendation,
    ConfidenceAssessment
)


class TestNPSDataFactory:
    """Factory for creating test NPS analysis data."""

    @staticmethod
    def create_nps_metrics(
        nps_score: int = 45,
        promoter_count: int = 30,
        passive_count: int = 40,
        detractor_count: int = 30
    ) -> NPSMetrics:
        """Create test NPS metrics."""
        total_responses = promoter_count + passive_count + detractor_count
        return NPSMetrics(
            nps_score=nps_score,
            promoter_count=promoter_count,
            passive_count=passive_count,
            detractor_count=detractor_count,
            sample_size=total_responses,
            statistical_significance=total_responses >= 100
        )

    @staticmethod
    def create_confidence_assessment(
        overall_score: float = 0.75,
        confidence_text: str = "中"
    ) -> ConfidenceAssessment:
        """Create test confidence assessment."""
        return ConfidenceAssessment(
            overall_confidence_score=overall_score,
            overall_confidence_text=confidence_text,
            data_quality_score=0.8,
            analysis_completeness_score=0.7,
            statistical_significance_score=0.75
        )

    @staticmethod
    def create_executive_dashboard() -> ExecutiveDashboard:
        """Create test executive dashboard."""
        return ExecutiveDashboard(
            executive_summary="整体客户满意度良好，NPS得分为45，存在提升空间。主要改进领域包括产品质量和服务体验。",
            top_recommendations=[
                BusinessRecommendation(
                    title="优化产品质量管控",
                    description="加强生产流程监管，提升产品一致性",
                    category="产品改进",
                    priority="高",
                    expected_impact="显著提升客户满意度",
                    confidence_score=0.85,
                    implementation_timeline="3-6个月内完成流程优化"
                ),
                BusinessRecommendation(
                    title="改进客户服务体验",
                    description="优化服务流程，提升响应速度",
                    category="服务改进",
                    priority="中",
                    expected_impact="改善客户体验",
                    confidence_score=0.72,
                    implementation_timeline="1-3个月内完成服务培训"
                )
            ],
            risk_alerts=[
                "部分产品质量不稳定，可能影响品牌声誉",
                "客服响应时间较长，客户满意度下降",
                "竞争对手推出新产品，市场份额面临挑战"
            ],
            key_performance_indicators={
                "客户满意度": "75%",
                "产品质量评分": "4.2/5.0",
                "服务响应时间": "24小时",
                "市场份额": "32%"
            }
        )

    @staticmethod
    def create_agent_insights() -> List[AgentInsight]:
        """Create test agent insights."""
        return [
            AgentInsight(
                agent_id="B1",
                title="技术需求分析",
                summary="客户对产品功能和性能的技术需求分析",
                content="分析显示客户主要关注产品的稳定性、易用性和创新功能。技术改进建议包括优化用户界面、提升系统性能、增加智能化功能。",
                category="技术分析",
                priority="高",
                confidence=0.82,
                impact_score=0.78,
                timestamp=datetime.now().isoformat()
            ),
            AgentInsight(
                agent_id="B2",
                title="被动客户转化分析",
                summary="7-8分被动客户的转化潜力和策略分析",
                content="被动客户群体占40%，主要关注性价比和服务质量。转化策略：提供个性化服务、优化产品定价、加强客户关系管理。",
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
                content="贬损客户占30%，主要问题集中在产品质量和售后服务。挽回策略：建立快速响应机制、提供补偿方案、持续跟进客户反馈。",
                category="风险管理",
                priority="高",
                confidence=0.79,
                impact_score=0.85,
                timestamp=datetime.now().isoformat()
            )
        ]

    @staticmethod
    def create_consulting_recommendations() -> List[BusinessRecommendation]:
        """Create test consulting recommendations."""
        return [
            BusinessRecommendation(
                title="建立客户体验管理体系",
                description="构建端到端的客户体验管理流程，包括数据收集、分析、改进和监控环节",
                category="战略建议",
                priority="高",
                expected_impact="全面提升客户满意度",
                confidence_score=0.88,
                implementation_timeline="6-12个月建立完整体系"
            ),
            BusinessRecommendation(
                title="产品创新与差异化策略",
                description="基于客户需求洞察，开发差异化产品功能，提升市场竞争力",
                category="产品策略",
                priority="中",
                expected_impact="增强市场地位",
                confidence_score=0.75,
                implementation_timeline="3-6个月完成产品规划"
            )
        ]

    @classmethod
    def create_complete_analysis_response(cls) -> NPSAnalysisResponse:
        """Create complete test analysis response."""
        return NPSAnalysisResponse(
            response_id="test_analysis_123",
            nps_metrics=cls.create_nps_metrics(),
            confidence_assessment=cls.create_confidence_assessment(),
            foundation_insights=[
                AgentInsight(
                    agent_id="A0",
                    title="数据清洗结果",
                    summary="数据质量良好，清洗完成",
                    content="原始数据100条，有效数据100条，数据质量评分：优秀",
                    category="数据处理",
                    priority="低",
                    confidence=0.95,
                    impact_score=0.85,
                    timestamp=datetime.now().isoformat()
                )
            ],
            analysis_insights=cls.create_agent_insights(),
            consulting_recommendations=cls.create_consulting_recommendations(),
            executive_dashboard=cls.create_executive_dashboard()
        )


class TestTemplateManager:
    """Test cases for TemplateManager."""

    @pytest.fixture
    def template_manager(self):
        """Create template manager for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Create test templates
            template_dir = Path(temp_dir)

            # Create executive dashboard template
            exec_template = template_dir / "test_executive.html"
            exec_template.write_text("""
<!DOCTYPE html>
<html>
<head><title>{{ company_name }} Test Report</title></head>
<body>
    <h1>NPS Score: {{ nps_score }}</h1>
    <p>Sample Size: {{ sample_size }}</p>
</body>
</html>
            """)

            yield TemplateManager(template_dir)

    def test_template_manager_initialization(self, template_manager):
        """Test template manager initialization."""
        assert template_manager is not None
        assert template_manager.template_dir.exists()

    def test_executive_context_preparation(self, template_manager):
        """Test executive context preparation."""
        analysis_response = TestNPSDataFactory.create_complete_analysis_response()
        context = template_manager._prepare_executive_context(analysis_response, "Test Company")

        assert context["company_name"] == "Test Company"
        assert context["nps_score"] == 45
        assert context["sample_size"] == 100
        assert "executive_recommendations" in context
        assert len(context["executive_recommendations"]) >= 2

    @patch('nps_report_v3.templates.template_manager.JINJA2_AVAILABLE', False)
    def test_fallback_template_rendering(self, template_manager):
        """Test fallback template rendering without Jinja2."""
        analysis_response = TestNPSDataFactory.create_complete_analysis_response()

        # This should use simple string replacement
        result = template_manager._render_simple_template(
            "test_executive.html",
            {"company_name": "Test Company", "nps_score": 45}
        )

        assert "Test Company" in result
        assert "45" in result


class TestHTMLReportGenerator:
    """Test cases for HTMLReportGenerator."""

    @pytest.fixture
    def html_generator(self):
        """Create HTML generator for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield HTMLReportGenerator(
                output_directory=temp_dir,
                company_name="测试公司"
            )

    @pytest.fixture
    def sample_analysis(self):
        """Create sample analysis response."""
        return TestNPSDataFactory.create_complete_analysis_response()

    @pytest.mark.asyncio
    async def test_html_generator_initialization(self, html_generator):
        """Test HTML generator initialization."""
        assert html_generator.company_name == "测试公司"
        assert html_generator.output_directory.exists()
        assert html_generator.template_manager is not None

    @pytest.mark.asyncio
    async def test_executive_dashboard_generation(self, html_generator, sample_analysis):
        """Test executive dashboard HTML generation."""
        html_path = await html_generator.generate_executive_dashboard(sample_analysis)

        assert html_path.exists()
        assert html_path.suffix == ".html"

        # Check content
        content = html_path.read_text(encoding='utf-8')
        assert "测试公司" in content
        assert "NPS" in content
        assert str(sample_analysis.nps_metrics.nps_score) in content

    @pytest.mark.asyncio
    async def test_detailed_analysis_generation(self, html_generator, sample_analysis):
        """Test detailed analysis HTML generation."""
        html_path = await html_generator.generate_detailed_analysis(sample_analysis)

        assert html_path.exists()
        assert html_path.suffix == ".html"

        # Check content
        content = html_path.read_text(encoding='utf-8')
        assert "测试公司" in content
        assert "详细分析" in content or "detailed" in content.lower()

    @pytest.mark.asyncio
    async def test_dual_format_report_generation(self, html_generator, sample_analysis):
        """Test dual format report generation."""
        report_package = await html_generator.generate_dual_format_report(sample_analysis)

        assert "report_id" in report_package
        assert "generation_time" in report_package
        assert "json_report" in report_package
        assert "html_reports" in report_package
        assert "metadata" in report_package

        # Check that files were created
        json_path = Path(report_package["json_report"])
        assert json_path.exists()

        html_reports = report_package["html_reports"]
        for html_path in html_reports.values():
            assert Path(html_path).exists()

    def test_report_quality_validation(self):
        """Test HTML report quality validation."""
        good_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Test Report</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body>
            <h1>伊利 NPS Report</h1>
            <canvas id="chart"></canvas>
        </body>
        </html>
        """

        validation_results = validate_report_quality(good_html)

        assert validation_results["overall_score"] > 80
        assert validation_results["checks"]["html_structure"]
        assert validation_results["checks"]["chinese_content"]
        assert validation_results["checks"]["responsive_design"]

    def test_report_quality_validation_poor(self):
        """Test HTML report quality validation with poor content."""
        poor_html = "<html><body>Simple report</body></html>"

        validation_results = validate_report_quality(poor_html)

        assert validation_results["overall_score"] < 80
        assert len(validation_results["recommendations"]) > 0


class TestDualOutputGenerator:
    """Test cases for DualOutputGenerator."""

    @pytest.fixture
    def dual_generator(self):
        """Create dual output generator for testing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield DualOutputGenerator(
                output_directory=temp_dir,
                company_name="伊利集团"
            )

    @pytest.fixture
    def sample_analysis(self):
        """Create sample analysis response."""
        return TestNPSDataFactory.create_complete_analysis_response()

    @pytest.mark.asyncio
    async def test_dual_generator_initialization(self, dual_generator):
        """Test dual output generator initialization."""
        assert dual_generator.company_name == "伊利集团"
        assert dual_generator.output_directory.exists()
        assert dual_generator.json_dir.exists()
        assert dual_generator.html_dir.exists()

    @pytest.mark.asyncio
    async def test_complete_report_package_generation(self, dual_generator, sample_analysis):
        """Test complete report package generation."""
        report_package = await dual_generator.generate_complete_report_package(sample_analysis)

        # Verify package structure
        assert "package_info" in report_package
        assert "analysis_summary" in report_package
        assert "generated_outputs" in report_package
        assert "quality_assessment" in report_package
        assert "file_manifest" in report_package

        # Verify package info
        package_info = report_package["package_info"]
        assert package_info["company_name"] == "伊利集团"
        assert package_info["package_type"] == "dual_output"

        # Verify analysis summary
        analysis_summary = report_package["analysis_summary"]
        assert analysis_summary["nps_score"] == 45
        assert analysis_summary["sample_size"] == 100

    @pytest.mark.asyncio
    async def test_json_only_generation(self, dual_generator, sample_analysis):
        """Test JSON-only output generation."""
        json_path = await dual_generator.generate_json_only(sample_analysis)

        assert json_path.exists()
        assert json_path.suffix == ".json"

        # Verify JSON content
        with open(json_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)

        assert "analysis_results" in json_data
        assert "metadata" in json_data
        assert json_data["metadata"]["company_name"] == "伊利集团"

    @pytest.mark.asyncio
    async def test_html_only_generation(self, dual_generator, sample_analysis):
        """Test HTML-only output generation."""
        # Test executive report
        exec_path = await dual_generator.generate_html_only(
            sample_analysis,
            report_type="executive"
        )

        assert exec_path.exists()
        assert exec_path.suffix == ".html"

        # Test detailed report
        detail_path = await dual_generator.generate_html_only(
            sample_analysis,
            report_type="detailed"
        )

        assert detail_path.exists()
        assert detail_path.suffix == ".html"

    @pytest.mark.asyncio
    async def test_custom_output_generation(self, dual_generator, sample_analysis):
        """Test custom output generation."""
        template_config = {
            "custom_template.html": {
                "context": {"custom_field": "custom_value"}
            }
        }

        output_config = {
            "custom_json": {
                "fields": ["nps_metrics"],
                "filename": "custom_nps.json"
            }
        }

        # This test would require actual template files, so we'll mock the results
        with patch.object(dual_generator.html_generator, 'generate_custom_report', new_callable=AsyncMock) as mock_custom:
            mock_custom.return_value = Path("/tmp/custom.html")

            with patch.object(dual_generator, '_generate_custom_json', new_callable=AsyncMock) as mock_json:
                mock_json.return_value = Path("/tmp/custom.json")

                custom_results = await dual_generator.generate_custom_output(
                    sample_analysis,
                    template_config,
                    output_config
                )

                assert "report_id" in custom_results
                assert "outputs" in custom_results

    def test_state_to_response_conversion(self, dual_generator):
        """Test conversion from analysis state dict to response."""
        state_dict = {
            "workflow_id": "test_workflow",
            "nps_metrics": {
                "nps_score": 50,
                "promoter_count": 40,
                "passive_count": 35,
                "detractor_count": 25,
                "sample_size": 100,
                "statistical_significance": True
            }
        }

        response = dual_generator._ensure_response_format(state_dict)

        assert isinstance(response, NPSAnalysisResponse)
        assert response.response_id == "test_workflow"

    def test_analysis_validation(self, dual_generator, sample_analysis):
        """Test analysis results validation."""
        validation_results = dual_generator._validate_analysis_results(sample_analysis)

        assert "is_valid" in validation_results
        assert "quality_score" in validation_results
        assert validation_results["quality_score"] > 0

    def test_report_options_merging(self, dual_generator):
        """Test report options merging with defaults."""
        custom_options = {
            "generate_json": False,
            "custom_field": "custom_value"
        }

        merged_options = dual_generator._merge_report_options(custom_options)

        assert not merged_options["generate_json"]  # Custom override
        assert merged_options["generate_html"]      # Default
        assert merged_options["custom_field"] == "custom_value"  # Custom addition


class TestConvenienceFunctions:
    """Test convenience functions."""

    @pytest.fixture
    def sample_analysis(self):
        """Create sample analysis response."""
        return TestNPSDataFactory.create_complete_analysis_response()

    @pytest.mark.asyncio
    async def test_generate_standard_reports(self, sample_analysis):
        """Test generate_standard_reports convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            report_package = await generate_standard_reports(
                sample_analysis,
                output_directory=temp_dir,
                company_name="测试公司"
            )

            assert "package_info" in report_package
            assert report_package["package_info"]["company_name"] == "测试公司"

    @pytest.mark.asyncio
    async def test_quick_executive_report(self, sample_analysis):
        """Test quick_executive_report convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path, html_path = await quick_executive_report(
                sample_analysis,
                output_path=temp_dir
            )

            assert json_path.exists()
            assert html_path.exists()
            assert json_path.suffix == ".json"
            assert html_path.suffix == ".html"


class TestErrorHandling:
    """Test error handling scenarios."""

    @pytest.mark.asyncio
    async def test_invalid_analysis_data(self):
        """Test handling of invalid analysis data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = DualOutputGenerator(output_directory=temp_dir)

            # Test with None
            with pytest.raises(ValueError):
                await generator.generate_complete_report_package(None)

            # Test with empty dict
            with pytest.raises((ValueError, KeyError)):
                await generator.generate_complete_report_package({})

    @pytest.mark.asyncio
    async def test_file_system_errors(self):
        """Test file system error handling."""
        # Test with read-only directory
        with tempfile.TemporaryDirectory() as temp_dir:
            readonly_dir = Path(temp_dir) / "readonly"
            readonly_dir.mkdir()
            readonly_dir.chmod(0o444)  # Read-only

            generator = DualOutputGenerator(output_directory=readonly_dir)

            sample_analysis = TestNPSDataFactory.create_complete_analysis_response()

            # This should handle the permission error gracefully
            with pytest.raises((PermissionError, OSError)):
                await generator.generate_complete_report_package(sample_analysis)

    @pytest.mark.asyncio
    async def test_template_errors(self):
        """Test template rendering error handling."""
        with tempfile.TemporaryDirectory() as temp_dir:
            generator = HTMLReportGenerator(output_directory=temp_dir)

            # Test with malformed analysis data
            invalid_analysis = NPSAnalysisResponse(
                response_id="invalid",
                nps_metrics=None,  # This should cause issues
                executive_dashboard=None
            )

            # Should handle gracefully or raise appropriate error
            with pytest.raises((AttributeError, ValueError, TypeError)):
                await generator.generate_executive_dashboard(invalid_analysis)


class TestPerformance:
    """Performance and stress tests."""

    @pytest.mark.asyncio
    async def test_large_dataset_handling(self):
        """Test handling of large datasets."""
        # Create large analysis response
        large_insights = []
        for i in range(100):  # 100 insights
            large_insights.append(AgentInsight(
                agent_id=f"B{i}",
                title=f"Insight {i}",
                summary=f"Summary for insight {i}",
                content=f"Detailed content for insight {i} " * 50,  # Long content
                category="Test",
                priority="中",
                confidence=0.75,
                impact_score=0.5,
                timestamp=datetime.now().isoformat()
            ))

        large_analysis = NPSAnalysisResponse(
            response_id="large_test",
            nps_metrics=TestNPSDataFactory.create_nps_metrics(),
            confidence_assessment=TestNPSDataFactory.create_confidence_assessment(),
            foundation_insights=large_insights[:10],
            analysis_insights=large_insights[10:60],
            consulting_recommendations=TestNPSDataFactory.create_consulting_recommendations() * 10,
            executive_dashboard=TestNPSDataFactory.create_executive_dashboard()
        )

        with tempfile.TemporaryDirectory() as temp_dir:
            generator = DualOutputGenerator(output_directory=temp_dir)

            # This should complete within reasonable time
            import time
            start_time = time.time()

            report_package = await generator.generate_complete_report_package(large_analysis)

            end_time = time.time()
            generation_time = end_time - start_time

            assert generation_time < 30  # Should complete within 30 seconds
            assert report_package["analysis_summary"]["total_insights"] == 50
            assert report_package["analysis_summary"]["total_recommendations"] == 20

    @pytest.mark.asyncio
    async def test_concurrent_generation(self):
        """Test concurrent report generation."""
        analyses = [
            TestNPSDataFactory.create_complete_analysis_response()
            for _ in range(5)
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            # Create multiple generators
            generators = [
                DualOutputGenerator(output_directory=Path(temp_dir) / f"gen_{i}")
                for i in range(5)
            ]

            # Generate reports concurrently
            tasks = [
                gen.generate_complete_report_package(analysis)
                for gen, analysis in zip(generators, analyses)
            ]

            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check that all succeeded
            for result in results:
                assert not isinstance(result, Exception)
                assert "report_id" in result


# Integration tests
class TestIntegration:
    """Integration tests for the complete system."""

    @pytest.mark.asyncio
    async def test_end_to_end_report_generation(self):
        """Test complete end-to-end report generation."""
        # Create complete analysis response
        analysis_response = TestNPSDataFactory.create_complete_analysis_response()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate reports using the convenience function
            report_package = await generate_standard_reports(
                analysis_response,
                output_directory=temp_dir,
                company_name="伊利集团测试"
            )

            # Verify complete package
            assert report_package["package_info"]["company_name"] == "伊利集团测试"
            assert report_package["analysis_summary"]["nps_score"] == 45
            assert report_package["generated_outputs"]["total_files"] > 0

            # Verify files exist and have content
            for file_path in report_package["generated_outputs"]["json_files"].values():
                path = Path(file_path)
                assert path.exists()
                assert path.stat().st_size > 0

            for file_path in report_package["generated_outputs"]["html_files"].values():
                path = Path(file_path)
                assert path.exists()
                assert path.stat().st_size > 0

                # Verify HTML content is valid
                content = path.read_text(encoding='utf-8')
                assert "<!DOCTYPE html>" in content
                assert "伊利集团测试" in content

            # Verify manifest
            manifest = report_package["file_manifest"]
            assert len(manifest) > 0
            for item in manifest:
                assert "type" in item
                assert "path" in item
                assert "size_mb" in item


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])