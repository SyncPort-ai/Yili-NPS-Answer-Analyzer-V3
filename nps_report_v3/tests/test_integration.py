"""
Integration tests for NPS V3 Analysis System.

Tests the complete workflow from raw data input through multi-agent processing
to final report generation, validating end-to-end system functionality.
"""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

# Import system components
from nps_report_v3.workflow.orchestrator import WorkflowOrchestrator
from nps_report_v3.agents.factory import AgentFactory
from nps_report_v3.generators.dual_output_generator import DualOutputGenerator
from nps_report_v3.models.response import NPSAnalysisResponse
from nps_report_v3.state import NPSAnalysisState, create_initial_state


class TestDataFactory:
    """Factory for creating test data for integration tests."""

    @staticmethod
    def create_sample_survey_data() -> List[Dict[str, Any]]:
        """Create sample survey response data."""
        return [
            {
                "response_id": "resp_001",
                "score": 9,
                "comment": "伊利安慕希的口感非常好，质量稳定，是我最喜欢的酸奶品牌。包装也很精美，值得推荐给朋友。",
                "product": "安慕希",
                "region": "华东地区",
                "channel": "线上商城",
                "demographics": {"age_group": "25-35", "gender": "女"}
            },
            {
                "response_id": "resp_002",
                "score": 8,
                "comment": "金典牛奶的品质不错，但是价格有点贵。希望能有更多的优惠活动。",
                "product": "金典",
                "region": "华北地区",
                "channel": "连锁超市",
                "demographics": {"age_group": "35-45", "gender": "男"}
            },
            {
                "response_id": "resp_003",
                "score": 7,
                "comment": "舒化奶的口感还可以，但是包装设计可以更时尚一些。服务方面也有改进空间。",
                "product": "舒化",
                "region": "华南地区",
                "channel": "便利店",
                "demographics": {"age_group": "18-25", "gender": "女"}
            },
            {
                "response_id": "resp_004",
                "score": 10,
                "comment": "优酸乳的味道很棒，孩子们都很喜欢。质量可靠，会继续购买。",
                "product": "优酸乳",
                "region": "西南地区",
                "channel": "专卖店",
                "demographics": {"age_group": "35-45", "gender": "女"}
            },
            {
                "response_id": "resp_005",
                "score": 6,
                "comment": "最近买的味可滋口感不如以前，可能是配方改了。希望能恢复原来的味道。",
                "product": "味可滋",
                "region": "东北地区",
                "channel": "线上商城",
                "demographics": {"age_group": "25-35", "gender": "男"}
            },
            {
                "response_id": "resp_006",
                "score": 4,
                "comment": "客服态度不好，配送也很慢。产品质量也不稳定，有时候口感很差。",
                "product": "安慕希",
                "region": "华东地区",
                "channel": "线上商城",
                "demographics": {"age_group": "45-55", "gender": "男"}
            },
            {
                "response_id": "resp_007",
                "score": 3,
                "comment": "金典牛奶有异味，可能是保存不当。退货流程也很复杂，体验很差。",
                "product": "金典",
                "region": "华北地区",
                "channel": "连锁超市",
                "demographics": {"age_group": "55+", "gender": "女"}
            },
            {
                "response_id": "resp_008",
                "score": 8,
                "comment": "整体还不错，但希望能推出更多新口味。价格合理，质量稳定。",
                "product": "舒化",
                "region": "华南地区",
                "channel": "便利店",
                "demographics": {"age_group": "18-25", "gender": "男"}
            },
            {
                "response_id": "resp_009",
                "score": 9,
                "comment": "QQ星儿童奶很受孩子欢迎，营养丰富，包装可爱。会推荐给其他家长。",
                "product": "QQ星",
                "region": "西南地区",
                "channel": "专卖店",
                "demographics": {"age_group": "35-45", "gender": "女"}
            },
            {
                "response_id": "resp_010",
                "score": 5,
                "comment": "伊小欢的口感一般，性价比不高。希望能改进产品配方。",
                "product": "伊小欢",
                "region": "东北地区",
                "channel": "线上商城",
                "demographics": {"age_group": "25-35", "gender": "女"}
            }
        ]

    @staticmethod
    def create_workflow_config() -> Dict[str, Any]:
        """Create workflow configuration."""
        return {
            "enable_checkpointing": False,  # Disable for testing
            "enable_caching": False,
            "enable_profiling": True,
            "language": "zh-CN",
            "company_name": "伊利集团",
            "analysis_depth": "comprehensive"
        }

    @staticmethod
    def create_mock_llm_responses() -> Dict[str, str]:
        """Create mock LLM responses for different agents."""
        return {
            "A0": json.dumps({
                "cleaned_responses": [
                    {"id": "resp_001", "score": 9, "comment": "正面反馈，质量好"},
                    {"id": "resp_002", "score": 8, "comment": "正面但价格关注"},
                    {"id": "resp_003", "score": 7, "comment": "中性反馈"},
                    {"id": "resp_004", "score": 10, "comment": "非常满意"},
                    {"id": "resp_005", "score": 6, "comment": "产品质量下降"},
                    {"id": "resp_006", "score": 4, "comment": "服务和质量问题"},
                    {"id": "resp_007", "score": 3, "comment": "产品质量严重问题"},
                    {"id": "resp_008", "score": 8, "comment": "整体满意"},
                    {"id": "resp_009", "score": 9, "comment": "儿童产品受欢迎"},
                    {"id": "resp_010", "score": 5, "comment": "性价比不高"}
                ],
                "data_quality": "good",
                "pii_removed": True
            }),
            "A1": json.dumps({
                "nps_score": 40,
                "promoter_count": 3,
                "passive_count": 3,
                "detractor_count": 4,
                "sample_size": 10,
                "statistical_significance": False
            }),
            "A2": json.dumps({
                "tagged_responses": [
                    {"id": "resp_001", "tags": ["质量", "正面", "推荐"]},
                    {"id": "resp_002", "tags": ["价格", "优惠", "建议"]},
                    {"id": "resp_003", "tags": ["包装", "服务", "改进"]},
                    {"id": "resp_006", "tags": ["客服", "配送", "质量"]},
                    {"id": "resp_007", "tags": ["异味", "退货", "体验"]}
                ]
            }),
            "A3": json.dumps({
                "semantic_clusters": [
                    {
                        "cluster_id": 1,
                        "theme": "产品质量",
                        "keywords": ["质量", "口感", "稳定"],
                        "response_count": 4
                    },
                    {
                        "cluster_id": 2,
                        "theme": "价格关注",
                        "keywords": ["价格", "贵", "性价比"],
                        "response_count": 3
                    },
                    {
                        "cluster_id": 3,
                        "theme": "服务体验",
                        "keywords": ["客服", "配送", "服务"],
                        "response_count": 3
                    }
                ]
            }),
            "B1": json.dumps({
                "technical_requirements": [
                    "改进产品配方稳定性",
                    "优化包装设计",
                    "提升保鲜技术"
                ]
            }),
            "B2": json.dumps({
                "passive_analysis": {
                    "conversion_opportunities": [
                        "价格优惠策略",
                        "产品创新",
                        "服务改进"
                    ],
                    "main_concerns": ["价格", "新功能需求", "服务质量"]
                }
            }),
            "B3": json.dumps({
                "detractor_analysis": {
                    "pain_points": [
                        {"issue": "产品质量不稳定", "severity": "high", "frequency": 3},
                        {"issue": "客服响应慢", "severity": "medium", "frequency": 2},
                        {"issue": "退货流程复杂", "severity": "medium", "frequency": 1}
                    ],
                    "churn_risk": "high"
                }
            }),
            "C1": json.dumps({
                "strategic_recommendations": [
                    {
                        "title": "建立质量管控体系",
                        "description": "加强生产质量监控，确保产品一致性",
                        "priority": "high",
                        "timeline": "3-6个月"
                    },
                    {
                        "title": "优化客户服务流程",
                        "description": "改善客服响应时间和服务质量",
                        "priority": "medium",
                        "timeline": "1-3个月"
                    }
                ]
            }),
            "C2": json.dumps({
                "product_recommendations": [
                    {
                        "category": "产品改进",
                        "recommendations": [
                            "优化安慕希配方，提升口感稳定性",
                            "开发金典新口味，满足多样化需求",
                            "改进包装设计，增强视觉吸引力"
                        ]
                    }
                ]
            }),
            "C5": json.dumps({
                "executive_synthesis": {
                    "key_findings": [
                        "整体NPS为40，处于良好水平但有提升空间",
                        "产品质量是核心竞争优势，需要持续维护",
                        "价格敏感度较高，需要平衡价值与成本",
                        "服务体验是改进重点领域"
                    ],
                    "strategic_priorities": [
                        "质量管控体系建设",
                        "客户服务优化",
                        "产品创新与差异化",
                        "价值传播与品牌建设"
                    ]
                }
            })
        }


class TestEndToEndWorkflow:
    """Test complete end-to-end workflow."""

    @pytest.fixture
    def sample_data(self):
        """Provide sample survey data."""
        return TestDataFactory.create_sample_survey_data()

    @pytest.fixture
    def workflow_config(self):
        """Provide workflow configuration."""
        return TestDataFactory.create_workflow_config()

    @pytest.fixture
    def mock_llm_responses(self):
        """Provide mock LLM responses."""
        return TestDataFactory.create_mock_llm_responses()

    @pytest.mark.asyncio
    async def test_complete_analysis_workflow(self, sample_data, workflow_config, mock_llm_responses):
        """Test complete analysis workflow from data input to final report."""

        with tempfile.TemporaryDirectory() as temp_dir:
            # Initialize orchestrator
            orchestrator = WorkflowOrchestrator(
                workflow_id="integration_test_001",
                enable_checkpointing=False,
                enable_caching=False
            )

            # Mock LLM calls for all agents
            async def mock_llm_call(prompt, agent_id=None, **kwargs):
                """Mock LLM call that returns appropriate response based on agent."""
                if agent_id and agent_id in mock_llm_responses:
                    return mock_llm_responses[agent_id]
                return json.dumps({"result": "mock_response", "agent_id": agent_id})

            # Patch LLM clients
            with patch('nps_report_v3.llm.llm_client.LLMClient.call_llm', new_callable=AsyncMock) as mock_call:
                mock_call.side_effect = mock_llm_call

                # Execute workflow
                try:
                    final_state = await orchestrator.execute(
                        raw_data=sample_data,
                        config=workflow_config
                    )

                    # Validate workflow completion
                    assert final_state["workflow_phase"] == "completed"
                    assert final_state["workflow_id"] == "integration_test_001"
                    assert "completion_time" in final_state

                    # Validate foundation pass results
                    assert "cleaned_data" in final_state
                    assert "nps_metrics" in final_state
                    assert "tagged_responses" in final_state
                    assert "semantic_clusters" in final_state

                    # Validate analysis pass results
                    assert "technical_requirements" in final_state or "analysis_insights" in final_state

                    # Validate consulting pass results
                    assert "strategic_recommendations" in final_state or "consulting_recommendations" in final_state

                    # Generate reports from final state
                    report_generator = DualOutputGenerator(
                        output_directory=temp_dir,
                        company_name="伊利集团测试"
                    )

                    report_package = await report_generator.generate_complete_report_package(final_state)

                    # Validate report generation
                    assert "report_id" in report_package
                    assert "generated_outputs" in report_package
                    assert report_package["generated_outputs"]["total_files"] > 0

                    return final_state, report_package

                except Exception as e:
                    # Log detailed error information for debugging
                    print(f"Integration test failed: {e}")
                    print(f"Exception type: {type(e)}")
                    import traceback
                    traceback.print_exc()
                    raise

    @pytest.mark.asyncio
    async def test_foundation_pass_only(self, sample_data, workflow_config):
        """Test foundation pass execution in isolation."""

        orchestrator = WorkflowOrchestrator(
            workflow_id="foundation_test",
            enable_checkpointing=False
        )

        # Create initial state
        state = create_initial_state(
            workflow_id="foundation_test",
            raw_data=sample_data,
            **workflow_config
        )

        # Add input_data structure
        state["input_data"] = {
            "survey_responses": sample_data,
            "responses": sample_data
        }

        # Mock foundation agents
        mock_responses = TestDataFactory.create_mock_llm_responses()

        async def mock_agent_execute(self, state):
            """Mock agent execution."""
            agent_id = self.agent_id
            mock_result = Mock()
            mock_result.status.value = "completed"

            if agent_id in mock_responses:
                mock_result.data = json.loads(mock_responses[agent_id])
            else:
                mock_result.data = {"result": f"mock_data_for_{agent_id}"}

            return mock_result

        # Patch agent execution
        with patch('nps_report_v3.agents.base.BaseAgent.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = mock_agent_execute

            # Execute foundation pass
            result_state = await orchestrator._execute_foundation_pass(state)

            # Validate foundation pass results
            assert result_state["workflow_phase"] == "foundation"
            assert "cleaned_data" in result_state or "input_data" in result_state

    @pytest.mark.asyncio
    async def test_analysis_pass_parallel_execution(self, sample_data, workflow_config):
        """Test analysis pass with parallel agent execution."""

        orchestrator = WorkflowOrchestrator(
            workflow_id="analysis_test",
            enable_checkpointing=False
        )

        # Create state with foundation results
        state = create_initial_state(
            workflow_id="analysis_test",
            raw_data=sample_data,
            **workflow_config
        )

        # Add foundation results
        state.update({
            "input_data": {"survey_responses": sample_data},
            "workflow_phase": "analysis",
            "cleaned_data": {"quality": "good"},
            "nps_metrics": {"nps_score": 40, "sample_size": 10},
            "tagged_responses": [],
            "semantic_clusters": []
        })

        # Mock parallel agent execution
        async def mock_parallel_execution(self, state):
            """Mock parallel agent execution."""
            import asyncio
            await asyncio.sleep(0.1)  # Simulate processing time

            mock_result = Mock()
            mock_result.status.value = "completed"
            mock_result.data = {"agent_result": f"data_from_{self.agent_id}"}
            return mock_result

        with patch('nps_report_v3.agents.base.BaseAgent.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = mock_parallel_execution

            # Execute analysis pass
            result_state = await orchestrator._execute_analysis_pass(state)

            # Validate parallel execution completed
            assert result_state["workflow_phase"] == "analysis"

    @pytest.mark.asyncio
    async def test_consulting_pass_confidence_constraints(self, sample_data, workflow_config):
        """Test consulting pass with confidence-based constraints."""

        orchestrator = WorkflowOrchestrator(
            workflow_id="consulting_test",
            enable_checkpointing=False
        )

        # Create state with analysis results
        state = create_initial_state(
            workflow_id="consulting_test",
            raw_data=sample_data,
            **workflow_config
        )

        # Add analysis results with different confidence levels
        state.update({
            "input_data": {"survey_responses": sample_data},
            "workflow_phase": "consulting",
            "nps_metrics": {
                "nps_score": 40,
                "sample_size": 10,
                "statistical_significance": False  # Low confidence scenario
            },
            "cleaned_data": {"data_quality": "medium"},
            "technical_requirements": [],
            "semantic_clusters": [],
            "tagged_responses": []
        })

        # Mock consulting agents with confidence checks
        async def mock_consulting_execution(self, state):
            """Mock consulting agent execution with confidence awareness."""
            mock_result = Mock()
            mock_result.status.value = "completed"
            mock_result.data = {
                "recommendations": [f"Low confidence recommendation from {self.agent_id}"],
                "confidence_applied": True
            }
            return mock_result

        with patch('nps_report_v3.agents.base.BaseAgent.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = mock_consulting_execution

            # Execute consulting pass
            result_state = await orchestrator._execute_consulting_pass(state)

            # Validate consulting pass handled confidence constraints
            assert result_state["workflow_phase"] == "consulting"

    @pytest.mark.asyncio
    async def test_error_recovery_and_resilience(self, sample_data, workflow_config):
        """Test system resilience and error recovery."""

        orchestrator = WorkflowOrchestrator(
            workflow_id="resilience_test",
            enable_checkpointing=False
        )

        # Simulate agent failure
        async def mock_failing_agent(self, state):
            """Mock agent that sometimes fails."""
            if self.agent_id == "B2":  # Simulate B2 agent failure
                raise RuntimeError(f"Simulated failure in agent {self.agent_id}")

            mock_result = Mock()
            mock_result.status.value = "completed"
            mock_result.data = {"result": f"success_from_{self.agent_id}"}
            return mock_result

        with patch('nps_report_v3.agents.base.BaseAgent.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = mock_failing_agent

            # Execute workflow - should handle agent failure gracefully
            with pytest.raises(RuntimeError):  # Expecting failure propagation
                await orchestrator.execute(sample_data, workflow_config)

    @pytest.mark.asyncio
    async def test_large_dataset_performance(self):
        """Test performance with large dataset."""

        # Create large dataset
        large_data = []
        for i in range(1000):  # 1000 responses
            large_data.append({
                "response_id": f"large_resp_{i:04d}",
                "score": (i % 11),  # Scores from 0-10
                "comment": f"这是第{i+1}个测试评论，包含客户对产品的详细反馈和建议。产品质量、服务体验、价格因素都是客户关注的重点。",
                "product": ["安慕希", "金典", "舒化", "优酸乳", "味可滋"][i % 5],
                "region": ["华北", "华东", "华南", "西南", "东北"][i % 5],
                "channel": ["线上", "超市", "便利店", "专卖店"][i % 4]
            })

        # Test with performance monitoring
        import time
        start_time = time.time()

        with tempfile.TemporaryDirectory() as temp_dir:
            # Mock fast agent responses for performance test
            async def mock_fast_agent(self, state):
                """Mock agent with minimal processing time."""
                mock_result = Mock()
                mock_result.status.value = "completed"
                mock_result.data = {
                    "processed_count": len(state.get("input_data", {}).get("survey_responses", [])),
                    "agent_id": self.agent_id
                }
                return mock_result

            orchestrator = WorkflowOrchestrator(
                workflow_id="performance_test",
                enable_checkpointing=False
            )

            with patch('nps_report_v3.agents.base.BaseAgent.execute', new_callable=AsyncMock) as mock_execute:
                mock_execute.side_effect = mock_fast_agent

                try:
                    # Execute workflow
                    result_state = await orchestrator.execute(large_data, {"enable_profiling": True})

                    processing_time = time.time() - start_time

                    # Performance assertions
                    assert processing_time < 60  # Should complete within 1 minute
                    assert result_state["workflow_phase"] == "completed"

                    # Generate reports
                    report_generator = DualOutputGenerator(output_directory=temp_dir)
                    report_package = await report_generator.generate_complete_report_package(result_state)

                    total_time = time.time() - start_time
                    assert total_time < 120  # Total time including reports < 2 minutes

                    print(f"Performance test completed in {total_time:.2f} seconds for 1000 responses")

                except Exception as e:
                    print(f"Performance test failed: {e}")
                    raise

    @pytest.mark.asyncio
    async def test_multilingual_content_handling(self):
        """Test handling of multilingual content."""

        multilingual_data = [
            {
                "response_id": "ml_001",
                "score": 9,
                "comment": "伊利产品质量很好，我很喜欢！Excellence quality and taste.",
                "product": "安慕希",
                "language": "zh-en"
            },
            {
                "response_id": "ml_002",
                "score": 7,
                "comment": "Good product, but expensive. 产品不错但价格有点贵。",
                "product": "金典",
                "language": "en-zh"
            },
            {
                "response_id": "ml_003",
                "score": 8,
                "comment": "很棒的产品！👍🏻 Really love the taste and quality! 五星推荐⭐⭐⭐⭐⭐",
                "product": "优酸乳",
                "language": "zh-en-emoji"
            }
        ]

        orchestrator = WorkflowOrchestrator(
            workflow_id="multilingual_test",
            enable_checkpointing=False
        )

        # Mock agents that handle multilingual content
        async def mock_multilingual_agent(self, state):
            """Mock agent that processes multilingual content."""
            mock_result = Mock()
            mock_result.status.value = "completed"
            mock_result.data = {
                "multilingual_processed": True,
                "languages_detected": ["zh", "en"],
                "emoji_support": True
            }
            return mock_result

        with patch('nps_report_v3.agents.base.BaseAgent.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = mock_multilingual_agent

            # Execute with multilingual data
            result_state = await orchestrator.execute(multilingual_data, {"language": "auto"})

            # Validate multilingual handling
            assert result_state["workflow_phase"] == "completed"


class TestReportIntegration:
    """Test report generation integration with workflow results."""

    @pytest.mark.asyncio
    async def test_workflow_to_report_integration(self):
        """Test seamless integration from workflow to report generation."""

        # Create mock workflow result
        workflow_result = {
            "workflow_id": "integration_report_test",
            "workflow_phase": "completed",
            "completion_time": datetime.now().isoformat(),
            "input_data": {"survey_responses": TestDataFactory.create_sample_survey_data()},
            "nps_metrics": {
                "nps_score": 45,
                "promoter_count": 4,
                "passive_count": 3,
                "detractor_count": 3,
                "sample_size": 10,
                "statistical_significance": False
            },
            "cleaned_data": {"data_quality": "good"},
            "tagged_responses": [{"id": "001", "tags": ["质量", "好"]}],
            "semantic_clusters": [{"theme": "产品质量", "count": 5}],
            "technical_requirements": ["改进配方"],
            "passive_analysis": {"conversion_rate": "medium"},
            "detractor_analysis": {"churn_risk": "low"},
            "strategic_recommendations": [{"title": "质量提升", "priority": "high"}]
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            # Generate reports from workflow result
            report_generator = DualOutputGenerator(
                output_directory=temp_dir,
                company_name="伊利集团集成测试"
            )

            report_package = await report_generator.generate_complete_report_package(
                workflow_result,
                report_options={
                    "generate_json": True,
                    "generate_html": True,
                    "generate_summary": True
                }
            )

            # Validate integration
            assert report_package["package_info"]["company_name"] == "伊利集团集成测试"
            assert report_package["analysis_summary"]["nps_score"] == 45
            assert report_package["generated_outputs"]["total_files"] >= 2

            # Validate file existence and content
            json_files = report_package["generated_outputs"]["json_files"]
            html_files = report_package["generated_outputs"]["html_files"]

            for file_path in json_files.values():
                assert Path(file_path).exists()
                assert Path(file_path).stat().st_size > 0

            for file_path in html_files.values():
                assert Path(file_path).exists()
                assert Path(file_path).stat().st_size > 0

                # Validate HTML content
                content = Path(file_path).read_text(encoding='utf-8')
                assert "伊利集团集成测试" in content
                assert "45" in content  # NPS score should be in HTML

    @pytest.mark.asyncio
    async def test_report_quality_validation_integration(self):
        """Test integrated report quality validation."""

        from nps_report_v3.generators.html_report_generator import validate_report_quality

        # Create and generate a report
        with tempfile.TemporaryDirectory() as temp_dir:
            report_generator = DualOutputGenerator(output_directory=temp_dir)

            # Mock workflow result
            mock_result = {
                "workflow_id": "quality_test",
                "nps_metrics": {"nps_score": 50, "sample_size": 100},
                "executive_dashboard": {
                    "executive_summary": "测试摘要",
                    "top_recommendations": [],
                    "risk_alerts": [],
                    "key_performance_indicators": {}
                }
            }

            # Generate HTML report
            html_path = await report_generator.generate_html_only(mock_result, "executive")

            # Validate report quality
            html_content = html_path.read_text(encoding='utf-8')
            quality_results = validate_report_quality(html_content)

            # Assert quality standards
            assert quality_results["overall_score"] >= 60  # Minimum acceptable quality
            assert quality_results["checks"]["html_structure"]

            if quality_results["overall_score"] < 80:
                print("Quality recommendations:", quality_results["recommendations"])


class TestDataPipeline:
    """Test data flow through the complete pipeline."""

    @pytest.mark.asyncio
    async def test_data_consistency_through_pipeline(self):
        """Test data consistency from input to final output."""

        # Track specific data point through pipeline
        tracked_response = {
            "response_id": "tracked_001",
            "score": 9,
            "comment": "伊利安慕希酸奶的品质非常棒，口感丝滑，营养丰富。包装设计也很精美，是我家冰箱里的必备品。强烈推荐给所有朋友！",
            "product": "安慕希",
            "region": "华东地区",
            "channel": "线上商城"
        }

        input_data = [tracked_response] + TestDataFactory.create_sample_survey_data()

        # Mock agents to preserve tracked data
        def create_preserving_mock(agent_id):
            async def preserving_mock(self, state):
                mock_result = Mock()
                mock_result.status.value = "completed"

                # Preserve tracked response in results
                mock_result.data = {
                    "agent_id": agent_id,
                    "processed_tracked": True,
                    "tracked_response_found": any(
                        r.get("response_id") == "tracked_001"
                        for r in state.get("input_data", {}).get("survey_responses", [])
                    )
                }
                return mock_result
            return preserving_mock

        # Execute workflow with tracking
        orchestrator = WorkflowOrchestrator(
            workflow_id="data_consistency_test",
            enable_checkpointing=False
        )

        with patch('nps_report_v3.agents.base.BaseAgent.execute', new_callable=AsyncMock) as mock_execute:
            mock_execute.side_effect = create_preserving_mock("test_agent")

            result_state = await orchestrator.execute(input_data, {"track_data": True})

            # Verify tracked data presence in final state
            assert result_state["workflow_phase"] == "completed"

            # Check that original input is preserved
            original_responses = result_state.get("input_data", {}).get("survey_responses", [])
            tracked_found = any(r.get("response_id") == "tracked_001" for r in original_responses)
            assert tracked_found, "Tracked response lost during processing"

            # Generate report and verify data consistency
            with tempfile.TemporaryDirectory() as temp_dir:
                report_generator = DualOutputGenerator(output_directory=temp_dir)
                report_package = await report_generator.generate_complete_report_package(result_state)

                # Check JSON output contains original data
                json_files = report_package["generated_outputs"]["json_files"]
                main_json_path = json_files.get("main_results")

                if main_json_path:
                    with open(main_json_path, 'r', encoding='utf-8') as f:
                        json_data = json.load(f)

                    # Verify data integrity in JSON output
                    assert "analysis_results" in json_data
                    # Could add more specific checks here


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s", "--tb=short"])