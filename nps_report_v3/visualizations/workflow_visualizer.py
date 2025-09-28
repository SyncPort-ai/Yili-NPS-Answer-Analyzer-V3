"""
Workflow Visualization Tools for NPS V3 Analysis System

Provides comprehensive visualization capabilities for understanding and monitoring
the multi-agent workflow execution, including dependency graphs, performance metrics,
and real-time status monitoring.
"""

import asyncio
import json
import logging
from typing import Dict, Any, List, Optional, Tuple, Union
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# Try to import visualization libraries
try:
    import networkx as nx
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    from matplotlib.colors import ListedColormap
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    logging.warning("Matplotlib not available, using text-based visualization")

try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    import plotly.offline as pyo
    PLOTLY_AVAILABLE = True
except ImportError:
    PLOTLY_AVAILABLE = False
    logging.warning("Plotly not available, interactive visualizations disabled")

from ..state.state_definition import NPSAnalysisState
from ..workflow.orchestrator import WorkflowOrchestrator


logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class WorkflowPhase(Enum):
    """Workflow execution phases."""
    FOUNDATION = "foundation"
    ANALYSIS = "analysis"
    CONSULTING = "consulting"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentNode:
    """Represents an agent in the workflow graph."""
    agent_id: str
    agent_name: str
    phase: WorkflowPhase
    group: str
    status: AgentStatus = AgentStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    execution_time: Optional[float] = None
    error_message: Optional[str] = None
    confidence_score: Optional[float] = None
    output_size: Optional[int] = None
    dependencies: List[str] = None
    parallel_group: Optional[str] = None

    def __post_init__(self):
        """Initialize dependencies if not provided."""
        if self.dependencies is None:
            self.dependencies = []


@dataclass
class WorkflowExecution:
    """Represents a complete workflow execution."""
    workflow_id: str
    start_time: datetime
    end_time: Optional[datetime] = None
    status: WorkflowPhase = WorkflowPhase.FOUNDATION
    agents: Dict[str, AgentNode] = None
    total_execution_time: Optional[float] = None
    input_data_size: int = 0
    output_data_size: int = 0
    error_count: int = 0
    performance_metrics: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize collections if not provided."""
        if self.agents is None:
            self.agents = {}
        if self.performance_metrics is None:
            self.performance_metrics = {}


class WorkflowVisualizer:
    """
    Comprehensive workflow visualization system.

    Provides multiple visualization modes:
    - Static workflow architecture diagrams
    - Real-time execution monitoring
    - Performance analysis charts
    - Error tracking and debugging views
    - Agent dependency graphs
    """

    def __init__(self, output_directory: Optional[Union[str, Path]] = None):
        """Initialize workflow visualizer."""
        self.output_directory = Path(output_directory or "outputs/visualizations")
        self.output_directory.mkdir(parents=True, exist_ok=True)

        self.workflow_definition = self._create_workflow_definition()
        self.executions: Dict[str, WorkflowExecution] = {}

        logger.info(f"Workflow visualizer initialized with output directory: {self.output_directory}")

    def _create_workflow_definition(self) -> Dict[str, AgentNode]:
        """Create the static workflow definition with all agents."""
        agents = {}

        # Foundation Pass (A0-A3)
        foundation_agents = [
            ("A0", "数据清洗代理", "data_cleaning"),
            ("A1", "NPS计算代理", "nps_calculation"),
            ("A2", "响应标注代理", "response_tagging"),
            ("A3", "语义聚类代理", "semantic_clustering")
        ]

        for i, (agent_id, name, group) in enumerate(foundation_agents):
            dependencies = [foundation_agents[j][0] for j in range(i)] if i > 0 else []
            agents[agent_id] = AgentNode(
                agent_id=agent_id,
                agent_name=name,
                phase=WorkflowPhase.FOUNDATION,
                group=group,
                dependencies=dependencies
            )

        # Analysis Pass (B1-B9) - with parallel groups
        analysis_groups = {
            "segment_analysis": [
                ("B1", "技术需求分析代理"),
                ("B2", "被动客户分析代理"),
                ("B3", "贬损客户分析代理")
            ],
            "advanced_analytics": [
                ("B4", "文本聚类代理"),
                ("B5", "驱动因子分析代理")
            ],
            "dimensional_analysis": [
                ("B6", "产品维度分析代理"),
                ("B7", "地域维度分析代理"),
                ("B8", "渠道维度分析代理")
            ],
            "synthesis": [
                ("B9", "分析协调代理")
            ]
        }

        prev_group_agents = ["A3"]  # B1-B3 depend on A3

        for group_name, group_agents in analysis_groups.items():
            current_group_ids = []
            for agent_id, agent_name in group_agents:
                agents[agent_id] = AgentNode(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    phase=WorkflowPhase.ANALYSIS,
                    group=group_name,
                    dependencies=prev_group_agents.copy(),
                    parallel_group=group_name if len(group_agents) > 1 else None
                )
                current_group_ids.append(agent_id)

            prev_group_agents = current_group_ids

        # Consulting Pass (C1-C5) - with confidence constraints
        consulting_groups = {
            "strategic_advisors": [
                ("C1", "战略建议代理"),
                ("C2", "产品顾问代理"),
                ("C3", "营销顾问代理"),
                ("C4", "风险管理代理")
            ],
            "executive_synthesis": [
                ("C5", "高管综合代理")
            ]
        }

        prev_group_agents = ["B9"]  # C1-C4 depend on B9

        for group_name, group_agents in consulting_groups.items():
            current_group_ids = []
            for agent_id, agent_name in group_agents:
                agents[agent_id] = AgentNode(
                    agent_id=agent_id,
                    agent_name=agent_name,
                    phase=WorkflowPhase.CONSULTING,
                    group=group_name,
                    dependencies=prev_group_agents.copy(),
                    parallel_group=group_name if len(group_agents) > 1 else None
                )
                current_group_ids.append(agent_id)

            prev_group_agents = current_group_ids

        return agents

    def create_architecture_diagram(
        self,
        output_file: Optional[str] = None,
        format: str = "png",
        style: str = "professional"
    ) -> Path:
        """
        Create static architecture diagram of the workflow.

        Args:
            output_file: Output filename (auto-generated if None)
            format: Output format (png, svg, html)
            style: Visualization style (professional, colorful, minimal)

        Returns:
            Path to generated diagram
        """
        logger.info("Creating workflow architecture diagram")

        if format == "html" and PLOTLY_AVAILABLE:
            return self._create_interactive_architecture(output_file, style)
        elif MATPLOTLIB_AVAILABLE:
            return self._create_static_architecture(output_file, format, style)
        else:
            return self._create_text_architecture(output_file)

    def _create_interactive_architecture(self, output_file: Optional[str], style: str) -> Path:
        """Create interactive architecture diagram with Plotly."""
        if not PLOTLY_AVAILABLE:
            raise ImportError("Plotly required for interactive diagrams")

        # Create network graph
        G = nx.DiGraph()

        # Add nodes with attributes
        for agent_id, agent in self.workflow_definition.items():
            G.add_node(
                agent_id,
                name=agent.agent_name,
                phase=agent.phase.value,
                group=agent.group,
                parallel_group=agent.parallel_group
            )

        # Add edges for dependencies
        for agent_id, agent in self.workflow_definition.items():
            for dep in agent.dependencies:
                if dep in G.nodes:
                    G.add_edge(dep, agent_id)

        # Use hierarchical layout
        pos = self._calculate_hierarchical_positions(G)

        # Create traces for nodes by phase
        phase_colors = {
            "foundation": "#3498db",
            "analysis": "#e74c3c",
            "consulting": "#2ecc71"
        }

        node_traces = {}
        for phase in phase_colors:
            node_traces[phase] = go.Scatter(
                x=[], y=[], text=[], mode="markers+text",
                marker=dict(size=20, color=phase_colors[phase]),
                textposition="middle center",
                name=f"{phase.title()} Pass",
                hovertemplate="<b>%{text}</b><br>Phase: " + phase + "<extra></extra>"
            )

        # Add node positions and labels
        for node_id, (x, y) in pos.items():
            agent = self.workflow_definition[node_id]
            phase = agent.phase.value

            node_traces[phase]["x"] += (x,)
            node_traces[phase]["y"] += (y,)
            node_traces[phase]["text"] += (agent_id,)

        # Create edge traces
        edge_trace = go.Scatter(
            x=[], y=[], mode="lines",
            line=dict(width=2, color="#999999"),
            hoverinfo="none", showlegend=False
        )

        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_trace["x"] += (x0, x1, None)
            edge_trace["y"] += (y0, y1, None)

        # Create figure
        fig = go.Figure()
        fig.add_trace(edge_trace)

        for trace in node_traces.values():
            fig.add_trace(trace)

        # Layout
        fig.update_layout(
            title=dict(
                text="NPS V3 多智能体工作流架构",
                x=0.5,
                font=dict(size=24)
            ),
            showlegend=True,
            hovermode="closest",
            margin=dict(b=20, l=5, r=5, t=40),
            annotations=[
                dict(
                    text="Foundation Pass → Analysis Pass → Consulting Pass",
                    showarrow=False,
                    xref="paper", yref="paper",
                    x=0.005, y=-0.002,
                    xanchor="left", yanchor="bottom",
                    font=dict(size=12, color="#666666")
                )
            ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            plot_bgcolor="white"
        )

        # Save file
        output_file = output_file or f"workflow_architecture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path = self.output_directory / output_file

        pyo.plot(fig, filename=str(output_path), auto_open=False)
        logger.info(f"Interactive architecture diagram saved: {output_path}")

        return output_path

    def _create_static_architecture(self, output_file: Optional[str], format: str, style: str) -> Path:
        """Create static architecture diagram with matplotlib."""
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("Matplotlib required for static diagrams")

        # Create figure
        plt.figure(figsize=(16, 12))

        # Create network graph
        G = nx.DiGraph()

        # Add nodes and edges
        for agent_id, agent in self.workflow_definition.items():
            G.add_node(agent_id, **asdict(agent))

        for agent_id, agent in self.workflow_definition.items():
            for dep in agent.dependencies:
                if dep in G.nodes:
                    G.add_edge(dep, agent_id)

        # Calculate positions
        pos = self._calculate_hierarchical_positions(G)

        # Color mapping by phase
        phase_colors = {
            "foundation": "#3498db",
            "analysis": "#e74c3c",
            "consulting": "#2ecc71"
        }

        node_colors = [phase_colors[self.workflow_definition[node].phase.value] for node in G.nodes()]

        # Draw the graph
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=1000, alpha=0.8)
        nx.draw_networkx_labels(G, pos, font_size=8, font_weight="bold")
        nx.draw_networkx_edges(G, pos, edge_color="gray", arrows=True, arrowsize=20, alpha=0.6)

        # Add phase labels and legend
        plt.title("NPS V3 多智能体工作流架构", fontsize=16, fontweight="bold", pad=20)

        # Create legend
        legend_elements = [
            mpatches.Patch(color=color, label=f"{phase.title()} Pass")
            for phase, color in phase_colors.items()
        ]
        plt.legend(handles=legend_elements, loc="upper right")

        plt.axis("off")
        plt.tight_layout()

        # Save file
        output_file = output_file or f"workflow_architecture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        output_path = self.output_directory / output_file

        plt.savefig(output_path, dpi=300, bbox_inches="tight")
        plt.close()

        logger.info(f"Static architecture diagram saved: {output_path}")
        return output_path

    def _create_text_architecture(self, output_file: Optional[str]) -> Path:
        """Create text-based architecture diagram."""
        lines = []
        lines.append("NPS V3 多智能体工作流架构")
        lines.append("=" * 40)
        lines.append("")

        # Group agents by phase
        phases = {
            WorkflowPhase.FOUNDATION: [],
            WorkflowPhase.ANALYSIS: [],
            WorkflowPhase.CONSULTING: []
        }

        for agent in self.workflow_definition.values():
            phases[agent.phase].append(agent)

        # Generate text representation
        for phase, agents in phases.items():
            lines.append(f"{phase.value.title()} Pass:")
            lines.append("-" * (len(phase.value) + 6))

            # Group by parallel groups
            groups = {}
            for agent in agents:
                group_key = agent.parallel_group or agent.group
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(agent)

            for group_name, group_agents in groups.items():
                if len(group_agents) > 1:
                    lines.append(f"  并行组: {group_name}")
                    for agent in group_agents:
                        lines.append(f"    ├─ {agent.agent_id}: {agent.agent_name}")
                else:
                    agent = group_agents[0]
                    lines.append(f"  {agent.agent_id}: {agent.agent_name}")
                    if agent.dependencies:
                        lines.append(f"    依赖: {', '.join(agent.dependencies)}")

            lines.append("")

        # Add flow description
        lines.append("执行流程:")
        lines.append("-" * 8)
        lines.append("1. Foundation Pass: 顺序执行 A0 → A1 → A2 → A3")
        lines.append("2. Analysis Pass: 并行组执行")
        lines.append("   - 段落分析组 (B1, B2, B3) 并行执行")
        lines.append("   - 高级分析组 (B4, B5) 并行执行")
        lines.append("   - 维度分析组 (B6, B7, B8) 并行执行")
        lines.append("   - 分析协调 (B9) 整合前面结果")
        lines.append("3. Consulting Pass: 置信度约束执行")
        lines.append("   - 战略顾问组 (C1, C2, C3, C4) 基于置信度并行执行")
        lines.append("   - 高管综合 (C5) 生成最终建议")

        # Save to file
        output_file = output_file or f"workflow_architecture_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        output_path = self.output_directory / output_file

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"Text architecture diagram saved: {output_path}")
        return output_path

    def _calculate_hierarchical_positions(self, G: nx.DiGraph) -> Dict[str, Tuple[float, float]]:
        """Calculate hierarchical positions for workflow visualization."""
        pos = {}

        # Define phase levels
        phase_levels = {
            WorkflowPhase.FOUNDATION: 0,
            WorkflowPhase.ANALYSIS: 1,
            WorkflowPhase.CONSULTING: 2
        }

        # Group nodes by phase
        phase_nodes = {phase: [] for phase in WorkflowPhase}
        for agent_id, agent in self.workflow_definition.items():
            phase_nodes[agent.phase].append(agent_id)

        # Position nodes
        for phase, nodes in phase_nodes.items():
            if not nodes:
                continue

            level = phase_levels[phase]
            y = -level * 2  # Negative Y to go top-to-bottom

            # Handle parallel groups within phase
            groups = {}
            for node_id in nodes:
                agent = self.workflow_definition[node_id]
                group_key = agent.parallel_group or agent.group
                if group_key not in groups:
                    groups[group_key] = []
                groups[group_key].append(node_id)

            # Position groups
            group_positions = list(range(len(groups)))
            group_width = max(len(groups) - 1, 1)

            for i, (group_name, group_nodes) in enumerate(groups.items()):
                if len(groups) == 1:
                    group_x = 0
                else:
                    group_x = (i - group_width/2) * 2  # Spread groups horizontally

                # Position nodes within group
                if len(group_nodes) == 1:
                    pos[group_nodes[0]] = (group_x, y)
                else:
                    node_width = len(group_nodes) - 1
                    for j, node_id in enumerate(group_nodes):
                        if node_width == 0:
                            node_x = group_x
                        else:
                            node_x = group_x + (j - node_width/2) * 0.8
                        pos[node_id] = (node_x, y)

        return pos

    async def monitor_execution(
        self,
        workflow_id: str,
        orchestrator: WorkflowOrchestrator,
        update_interval: float = 1.0
    ) -> WorkflowExecution:
        """
        Monitor real-time workflow execution.

        Args:
            workflow_id: Workflow identifier to monitor
            orchestrator: Workflow orchestrator instance
            update_interval: Update interval in seconds

        Returns:
            Complete workflow execution record
        """
        logger.info(f"Starting execution monitoring for workflow: {workflow_id}")

        # Initialize execution record
        execution = WorkflowExecution(
            workflow_id=workflow_id,
            start_time=datetime.now(),
            agents={agent_id: AgentNode(**asdict(agent)) for agent_id, agent in self.workflow_definition.items()}
        )

        self.executions[workflow_id] = execution

        # Start monitoring (this would integrate with actual orchestrator events)
        try:
            while execution.status != WorkflowPhase.COMPLETED and execution.status != WorkflowPhase.FAILED:
                await asyncio.sleep(update_interval)

                # Update execution status (this would come from orchestrator callbacks)
                # For now, simulate progress
                await self._update_execution_status(execution, orchestrator)

                # Generate real-time visualization
                if PLOTLY_AVAILABLE:
                    await self._generate_realtime_dashboard(execution)

            # Finalize execution record
            execution.end_time = datetime.now()
            execution.total_execution_time = (execution.end_time - execution.start_time).total_seconds()

            logger.info(f"Execution monitoring completed for workflow: {workflow_id}")
            return execution

        except Exception as e:
            logger.error(f"Error monitoring workflow {workflow_id}: {e}")
            execution.status = WorkflowPhase.FAILED
            raise

    async def _update_execution_status(self, execution: WorkflowExecution, orchestrator: WorkflowOrchestrator):
        """Update execution status from orchestrator."""
        # This would integrate with real orchestrator status
        # For now, simulate status updates

        current_time = datetime.now()
        elapsed = (current_time - execution.start_time).total_seconds()

        # Simulate phase progression
        if elapsed < 10:
            execution.status = WorkflowPhase.FOUNDATION
        elif elapsed < 30:
            execution.status = WorkflowPhase.ANALYSIS
        elif elapsed < 45:
            execution.status = WorkflowPhase.CONSULTING
        else:
            execution.status = WorkflowPhase.COMPLETED

    async def _generate_realtime_dashboard(self, execution: WorkflowExecution):
        """Generate real-time dashboard for execution monitoring."""
        if not PLOTLY_AVAILABLE:
            return

        # Create dashboard with multiple subplots
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=["执行进度", "代理状态", "性能指标", "错误跟踪"],
            specs=[[{"type": "scatter"}, {"type": "bar"}],
                   [{"type": "scatter"}, {"type": "scatter"}]]
        )

        # Execution progress
        phases = ["Foundation", "Analysis", "Consulting", "Completed"]
        current_phase_idx = list(WorkflowPhase).index(execution.status)
        progress = [1 if i <= current_phase_idx else 0 for i in range(len(phases))]

        fig.add_trace(
            go.Bar(x=phases, y=progress, marker_color="lightblue"),
            row=1, col=1
        )

        # Agent status
        status_counts = {"pending": 0, "running": 0, "completed": 0, "failed": 0}
        for agent in execution.agents.values():
            status_counts[agent.status.value] += 1

        fig.add_trace(
            go.Bar(x=list(status_counts.keys()), y=list(status_counts.values())),
            row=1, col=2
        )

        # Performance metrics (simulated)
        timestamps = [execution.start_time + timedelta(seconds=i) for i in range(10)]
        memory_usage = [50 + i * 2 + (i % 3) for i in range(10)]  # Simulated

        fig.add_trace(
            go.Scatter(x=timestamps, y=memory_usage, mode="lines", name="内存使用"),
            row=2, col=1
        )

        # Error tracking
        error_times = []
        error_counts = []
        cumulative_errors = 0

        for i, timestamp in enumerate(timestamps):
            if i % 4 == 0:  # Simulate occasional errors
                cumulative_errors += 1
            error_times.append(timestamp)
            error_counts.append(cumulative_errors)

        fig.add_trace(
            go.Scatter(x=error_times, y=error_counts, mode="lines+markers", name="累积错误"),
            row=2, col=2
        )

        # Update layout
        fig.update_layout(
            title=f"工作流实时监控 - {execution.workflow_id}",
            showlegend=False,
            height=600
        )

        # Save dashboard
        dashboard_path = self.output_directory / f"realtime_dashboard_{execution.workflow_id}.html"
        pyo.plot(fig, filename=str(dashboard_path), auto_open=False)

    def generate_performance_report(
        self,
        executions: Optional[List[str]] = None,
        output_file: Optional[str] = None
    ) -> Path:
        """
        Generate comprehensive performance analysis report.

        Args:
            executions: List of workflow IDs to analyze (all if None)
            output_file: Output filename

        Returns:
            Path to generated report
        """
        logger.info("Generating performance analysis report")

        if executions is None:
            executions = list(self.executions.keys())

        if not executions:
            raise ValueError("No workflow executions available for analysis")

        if PLOTLY_AVAILABLE:
            return self._generate_interactive_performance_report(executions, output_file)
        else:
            return self._generate_text_performance_report(executions, output_file)

    def _generate_interactive_performance_report(self, executions: List[str], output_file: Optional[str]) -> Path:
        """Generate interactive performance report with Plotly."""
        # Create multi-panel dashboard
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=[
                "执行时间分析", "代理性能对比",
                "错误率趋势", "资源使用情况",
                "成功率统计", "性能趋势"
            ],
            specs=[[{"type": "bar"}, {"type": "scatter"}],
                   [{"type": "scatter"}, {"type": "scatter"}],
                   [{"type": "pie"}, {"type": "scatter"}]]
        )

        # Analyze execution data
        execution_times = []
        success_rates = []
        error_counts = []
        timestamps = []

        for workflow_id in executions:
            if workflow_id in self.executions:
                exec_data = self.executions[workflow_id]
                if exec_data.total_execution_time:
                    execution_times.append(exec_data.total_execution_time)
                    success_rates.append(1 if exec_data.status == WorkflowPhase.COMPLETED else 0)
                    error_counts.append(exec_data.error_count)
                    timestamps.append(exec_data.start_time)

        # Execution time analysis
        if execution_times:
            fig.add_trace(
                go.Bar(x=executions[:len(execution_times)], y=execution_times, name="执行时间(秒)"),
                row=1, col=1
            )

        # Agent performance comparison (simulated)
        agent_ids = ["A0", "A1", "A2", "B1", "B2", "C1", "C2"]
        avg_times = [2.5, 1.8, 3.2, 4.1, 3.8, 5.2, 4.9]  # Simulated

        fig.add_trace(
            go.Scatter(x=agent_ids, y=avg_times, mode="markers+lines", name="平均执行时间"),
            row=1, col=2
        )

        # Error rate trends
        if timestamps and error_counts:
            fig.add_trace(
                go.Scatter(x=timestamps, y=error_counts, mode="lines+markers", name="错误数量"),
                row=2, col=1
            )

        # Success rate pie chart
        if success_rates:
            success_count = sum(success_rates)
            failure_count = len(success_rates) - success_count

            fig.add_trace(
                go.Pie(labels=["成功", "失败"], values=[success_count, failure_count]),
                row=3, col=1
            )

        # Update layout
        fig.update_layout(
            title="NPS V3 工作流性能分析报告",
            height=1200,
            showlegend=True
        )

        # Save report
        output_file = output_file or f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        output_path = self.output_directory / output_file

        pyo.plot(fig, filename=str(output_path), auto_open=False)
        logger.info(f"Interactive performance report saved: {output_path}")

        return output_path

    def _generate_text_performance_report(self, executions: List[str], output_file: Optional[str]) -> Path:
        """Generate text-based performance report."""
        lines = []
        lines.append("NPS V3 工作流性能分析报告")
        lines.append("=" * 35)
        lines.append(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append(f"分析执行数: {len(executions)}")
        lines.append("")

        # Analyze executions
        total_executions = len(executions)
        successful_executions = 0
        total_time = 0
        total_errors = 0

        for workflow_id in executions:
            if workflow_id in self.executions:
                exec_data = self.executions[workflow_id]
                if exec_data.status == WorkflowPhase.COMPLETED:
                    successful_executions += 1
                if exec_data.total_execution_time:
                    total_time += exec_data.total_execution_time
                total_errors += exec_data.error_count

        # Summary statistics
        lines.append("总体统计:")
        lines.append("-" * 10)
        lines.append(f"成功率: {successful_executions}/{total_executions} ({successful_executions/total_executions*100:.1f}%)")
        lines.append(f"平均执行时间: {total_time/total_executions:.2f} 秒")
        lines.append(f"总错误数: {total_errors}")
        lines.append("")

        # Individual execution details
        lines.append("执行详情:")
        lines.append("-" * 10)
        for workflow_id in executions:
            if workflow_id in self.executions:
                exec_data = self.executions[workflow_id]
                lines.append(f"工作流 {workflow_id}:")
                lines.append(f"  状态: {exec_data.status.value}")
                lines.append(f"  开始时间: {exec_data.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
                if exec_data.total_execution_time:
                    lines.append(f"  执行时间: {exec_data.total_execution_time:.2f} 秒")
                lines.append(f"  错误数: {exec_data.error_count}")
                lines.append("")

        # Save report
        output_file = output_file or f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        output_path = self.output_directory / output_file

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        logger.info(f"Text performance report saved: {output_path}")
        return output_path

    def export_execution_data(
        self,
        workflow_id: str,
        format: str = "json"
    ) -> Path:
        """
        Export execution data for external analysis.

        Args:
            workflow_id: Workflow to export
            format: Export format (json, csv, yaml)

        Returns:
            Path to exported file
        """
        if workflow_id not in self.executions:
            raise ValueError(f"Workflow {workflow_id} not found")

        execution = self.executions[workflow_id]

        # Convert to serializable format
        data = {
            "workflow_id": execution.workflow_id,
            "start_time": execution.start_time.isoformat(),
            "end_time": execution.end_time.isoformat() if execution.end_time else None,
            "status": execution.status.value,
            "total_execution_time": execution.total_execution_time,
            "input_data_size": execution.input_data_size,
            "output_data_size": execution.output_data_size,
            "error_count": execution.error_count,
            "performance_metrics": execution.performance_metrics,
            "agents": {
                agent_id: {
                    "agent_id": agent.agent_id,
                    "agent_name": agent.agent_name,
                    "phase": agent.phase.value,
                    "group": agent.group,
                    "status": agent.status.value,
                    "start_time": agent.start_time.isoformat() if agent.start_time else None,
                    "end_time": agent.end_time.isoformat() if agent.end_time else None,
                    "execution_time": agent.execution_time,
                    "error_message": agent.error_message,
                    "confidence_score": agent.confidence_score,
                    "output_size": agent.output_size
                }
                for agent_id, agent in execution.agents.items()
            }
        }

        # Export in requested format
        filename = f"execution_data_{workflow_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
        output_path = self.output_directory / filename

        if format == "json":
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        elif format == "yaml":
            try:
                import yaml
                with open(output_path, 'w', encoding='utf-8') as f:
                    yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            except ImportError:
                raise ImportError("PyYAML required for YAML export")

        elif format == "csv":
            import csv

            # Export agent data as CSV
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    "agent_id", "agent_name", "phase", "group", "status",
                    "execution_time", "confidence_score", "error_message"
                ])

                for agent in execution.agents.values():
                    writer.writerow([
                        agent.agent_id, agent.agent_name, agent.phase.value,
                        agent.group, agent.status.value, agent.execution_time,
                        agent.confidence_score, agent.error_message
                    ])

        else:
            raise ValueError(f"Unsupported export format: {format}")

        logger.info(f"Execution data exported: {output_path}")
        return output_path


# Convenience functions
def create_workflow_diagram(
    output_directory: Optional[Union[str, Path]] = None,
    style: str = "professional",
    format: str = "html"
) -> Path:
    """
    Create workflow architecture diagram.

    Args:
        output_directory: Output directory
        style: Visualization style
        format: Output format (html, png, svg)

    Returns:
        Path to generated diagram
    """
    visualizer = WorkflowVisualizer(output_directory)
    return visualizer.create_architecture_diagram(format=format, style=style)


async def monitor_workflow_execution(
    workflow_id: str,
    orchestrator: WorkflowOrchestrator,
    output_directory: Optional[Union[str, Path]] = None,
    update_interval: float = 1.0
) -> WorkflowExecution:
    """
    Monitor real-time workflow execution.

    Args:
        workflow_id: Workflow to monitor
        orchestrator: Orchestrator instance
        output_directory: Output directory
        update_interval: Update interval in seconds

    Returns:
        Complete execution record
    """
    visualizer = WorkflowVisualizer(output_directory)
    return await visualizer.monitor_execution(workflow_id, orchestrator, update_interval)


def generate_performance_analysis(
    execution_data: Dict[str, WorkflowExecution],
    output_directory: Optional[Union[str, Path]] = None
) -> Path:
    """
    Generate performance analysis report.

    Args:
        execution_data: Execution data to analyze
        output_directory: Output directory

    Returns:
        Path to generated report
    """
    visualizer = WorkflowVisualizer(output_directory)
    visualizer.executions.update(execution_data)
    return visualizer.generate_performance_report()