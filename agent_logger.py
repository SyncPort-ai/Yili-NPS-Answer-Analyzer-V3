"""Agent Output Logging System for NPS V3 Multi-Agent Workflow.

This module provides comprehensive logging functionality to track and debug
the behavior of all agents in the V3 analysis workflow.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import traceback


class AgentOutputLogger:
    """Comprehensive logger for multi-agent system outputs."""

    def __init__(self,
                 log_dir: str = "outputs/agent_logs",
                 log_level: str = "DEBUG",
                 enable_console: bool = True,
                 enable_file: bool = True):
        """Initialize the agent output logger.

        Args:
            log_dir: Directory for agent log files
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
            enable_console: Whether to log to console
            enable_file: Whether to log to file
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_level = getattr(logging, log_level.upper())
        self.enable_console = enable_console
        self.enable_file = enable_file

        # Create timestamp for this session
        self.session_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Session metadata
        self.session_metadata = {
            "session_id": self.session_timestamp,
            "start_time": datetime.now().isoformat(),
            "agents_executed": [],
            "total_execution_time_ms": 0,
            "errors": [],
            "warnings": []
        }

        # Setup main logger
        self.logger = self._setup_logger("agent_output", "main")

        # Agent-specific loggers
        self.agent_loggers = {}

        # Detailed agent outputs storage
        self.agent_outputs = {}

        # Performance metrics
        self.performance_metrics = {}

    def _setup_logger(self, name: str, agent_id: str) -> logging.Logger:
        """Setup a logger for a specific agent.

        Args:
            name: Logger name
            agent_id: Agent identifier

        Returns:
            Configured logger instance
        """
        logger = logging.getLogger(f"{name}.{agent_id}")
        logger.setLevel(self.log_level)
        logger.handlers.clear()  # Clear existing handlers

        # Create formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s - [%(name)s] - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # Console handler
        if self.enable_console:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(detailed_formatter)
            console_handler.setLevel(self.log_level)
            logger.addHandler(console_handler)

        # File handler
        if self.enable_file:
            log_file = self.log_dir / f"{self.session_timestamp}_{agent_id}.log"
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(detailed_formatter)
            file_handler.setLevel(logging.DEBUG)  # Always log everything to file
            logger.addHandler(file_handler)

        return logger

    def log_agent_start(self, agent_id: str, agent_name: str,
                       input_data: Optional[Dict[str, Any]] = None):
        """Log the start of an agent execution.

        Args:
            agent_id: Unique agent identifier (e.g., 'A1', 'B2', 'C3')
            agent_name: Human-readable agent name
            input_data: Input data passed to the agent
        """
        # Create agent-specific logger if not exists
        if agent_id not in self.agent_loggers:
            self.agent_loggers[agent_id] = self._setup_logger("agent", agent_id)

        logger = self.agent_loggers[agent_id]

        # Log start
        logger.info(f"{'='*60}")
        logger.info(f"Starting agent: {agent_name} ({agent_id})")
        logger.info(f"Timestamp: {datetime.now().isoformat()}")

        # Log input data summary
        if input_data:
            logger.debug(f"Input data keys: {list(input_data.keys())}")

            # Log sample of input data for debugging
            try:
                input_summary = self._create_data_summary(input_data)
                logger.debug(f"Input summary: {json.dumps(input_summary, ensure_ascii=False, indent=2)}")
            except Exception as e:
                logger.warning(f"Could not serialize input data: {e}")

        # Track in session metadata
        self.session_metadata["agents_executed"].append({
            "agent_id": agent_id,
            "agent_name": agent_name,
            "start_time": datetime.now().isoformat()
        })

        # Initialize agent output storage
        self.agent_outputs[agent_id] = {
            "agent_name": agent_name,
            "start_time": datetime.now().isoformat(),
            "input_summary": self._create_data_summary(input_data) if input_data else None,
            "output": None,
            "end_time": None,
            "execution_time_ms": None,
            "status": "running",
            "errors": [],
            "warnings": []
        }

        # Initialize performance metrics
        self.performance_metrics[agent_id] = {
            "start_time": datetime.now()
        }

    def log_agent_output(self, agent_id: str, output_data: Any,
                        success: bool = True, error: Optional[str] = None):
        """Log the output of an agent execution.

        Args:
            agent_id: Unique agent identifier
            output_data: Output data from the agent
            success: Whether the agent execution was successful
            error: Error message if execution failed
        """
        if agent_id not in self.agent_loggers:
            self.logger.warning(f"Agent {agent_id} not initialized, creating logger")
            self.agent_loggers[agent_id] = self._setup_logger("agent", agent_id)

        logger = self.agent_loggers[agent_id]

        # Calculate execution time
        if agent_id in self.performance_metrics:
            start_time = self.performance_metrics[agent_id]["start_time"]
            execution_time_ms = int((datetime.now() - start_time).total_seconds() * 1000)
        else:
            execution_time_ms = 0

        # Log output
        if success:
            logger.info(f"Agent completed successfully in {execution_time_ms}ms")

            # Log output data
            try:
                output_summary = self._create_data_summary(output_data)
                logger.debug(f"Output summary: {json.dumps(output_summary, ensure_ascii=False, indent=2)}")

                # Store full output for analysis
                if agent_id in self.agent_outputs:
                    self.agent_outputs[agent_id]["output"] = output_summary
                    self.agent_outputs[agent_id]["status"] = "completed"
                    self.agent_outputs[agent_id]["end_time"] = datetime.now().isoformat()
                    self.agent_outputs[agent_id]["execution_time_ms"] = execution_time_ms

            except Exception as e:
                logger.warning(f"Could not serialize output data: {e}")
                if agent_id in self.agent_outputs:
                    self.agent_outputs[agent_id]["output"] = str(output_data)[:1000]
        else:
            logger.error(f"Agent failed after {execution_time_ms}ms")
            if error:
                logger.error(f"Error: {error}")
                logger.debug(f"Stack trace:\n{traceback.format_exc()}")

            # Update agent output storage
            if agent_id in self.agent_outputs:
                self.agent_outputs[agent_id]["status"] = "failed"
                self.agent_outputs[agent_id]["end_time"] = datetime.now().isoformat()
                self.agent_outputs[agent_id]["execution_time_ms"] = execution_time_ms
                self.agent_outputs[agent_id]["errors"].append(error or "Unknown error")

        logger.info(f"{'='*60}\n")

        # Update session metadata
        self.session_metadata["total_execution_time_ms"] += execution_time_ms
        if not success and error:
            self.session_metadata["errors"].append({
                "agent_id": agent_id,
                "error": error,
                "timestamp": datetime.now().isoformat()
            })

    def log_agent_warning(self, agent_id: str, warning: str):
        """Log a warning from an agent.

        Args:
            agent_id: Unique agent identifier
            warning: Warning message
        """
        if agent_id not in self.agent_loggers:
            self.agent_loggers[agent_id] = self._setup_logger("agent", agent_id)

        logger = self.agent_loggers[agent_id]
        logger.warning(warning)

        # Store warning
        if agent_id in self.agent_outputs:
            self.agent_outputs[agent_id]["warnings"].append(warning)

        self.session_metadata["warnings"].append({
            "agent_id": agent_id,
            "warning": warning,
            "timestamp": datetime.now().isoformat()
        })

    def log_workflow_summary(self, workflow_result: Optional[Dict[str, Any]] = None):
        """Log a summary of the entire workflow execution.

        Args:
            workflow_result: Final workflow result
        """
        self.logger.info("\n" + "="*80)
        self.logger.info("WORKFLOW EXECUTION SUMMARY")
        self.logger.info("="*80)

        # Session info
        self.logger.info(f"Session ID: {self.session_metadata['session_id']}")
        self.logger.info(f"Total agents executed: {len(self.session_metadata['agents_executed'])}")
        self.logger.info(f"Total execution time: {self.session_metadata['total_execution_time_ms']}ms")

        # Agent execution summary
        self.logger.info("\nAgent Execution Summary:")
        for agent_id, data in self.agent_outputs.items():
            status_emoji = "✅" if data["status"] == "completed" else "❌"
            execution_time = data.get("execution_time_ms", 0)
            self.logger.info(
                f"  {status_emoji} {agent_id}: {data['agent_name']} "
                f"- {data['status']} ({execution_time}ms)"
            )

        # Error summary
        if self.session_metadata["errors"]:
            self.logger.warning(f"\nErrors encountered: {len(self.session_metadata['errors'])}")
            for error_info in self.session_metadata["errors"]:
                self.logger.warning(f"  - {error_info['agent_id']}: {error_info['error']}")

        # Warning summary
        if self.session_metadata["warnings"]:
            self.logger.info(f"\nWarnings: {len(self.session_metadata['warnings'])}")
            for warning_info in self.session_metadata["warnings"]:
                self.logger.info(f"  - {warning_info['agent_id']}: {warning_info['warning']}")

        # Save complete session data to JSON
        if self.enable_file:
            session_file = self.log_dir / f"{self.session_timestamp}_session_summary.json"
            session_data = {
                "metadata": self.session_metadata,
                "agent_outputs": self.agent_outputs,
                "workflow_result_summary": self._create_data_summary(workflow_result) if workflow_result else None
            }

            try:
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
                self.logger.info(f"\nSession summary saved to: {session_file}")
            except Exception as e:
                self.logger.error(f"Failed to save session summary: {e}")

        self.logger.info("="*80 + "\n")

    def _create_data_summary(self, data: Any, max_depth: int = 3,
                            max_str_length: int = 500) -> Any:
        """Create a summarized version of data for logging.

        Args:
            data: Data to summarize
            max_depth: Maximum depth for nested structures
            max_str_length: Maximum string length to preserve

        Returns:
            Summarized data structure
        """
        if max_depth <= 0:
            return "..."

        if isinstance(data, dict):
            summary = {}
            for key, value in list(data.items())[:20]:  # Limit to 20 keys
                summary[key] = self._create_data_summary(value, max_depth - 1, max_str_length)
            if len(data) > 20:
                summary["..."] = f"({len(data) - 20} more items)"
            return summary

        elif isinstance(data, list):
            if len(data) <= 5:
                return [self._create_data_summary(item, max_depth - 1, max_str_length)
                       for item in data]
            else:
                summary = [self._create_data_summary(item, max_depth - 1, max_str_length)
                          for item in data[:3]]
                summary.append(f"... ({len(data) - 3} more items)")
                return summary

        elif isinstance(data, str):
            if len(data) > max_str_length:
                return data[:max_str_length] + f"... (truncated, {len(data)} chars total)"
            return data

        elif data is None:
            return None

        elif isinstance(data, (int, float, bool)):
            return data

        else:
            # Try to convert to string
            str_repr = str(data)
            if len(str_repr) > max_str_length:
                return str_repr[:max_str_length] + "..."
            return str_repr

    def get_agent_output(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get the stored output for a specific agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Agent output data or None if not found
        """
        return self.agent_outputs.get(agent_id)

    def get_session_summary(self) -> Dict[str, Any]:
        """Get a summary of the entire session.

        Returns:
            Session summary including metadata and all agent outputs
        """
        return {
            "metadata": self.session_metadata,
            "agent_outputs": self.agent_outputs
        }


# Global logger instance (can be initialized once and reused)
agent_logger = None

def get_agent_logger(log_dir: str = "outputs/agent_logs",
                    log_level: str = "DEBUG",
                    reset: bool = False) -> AgentOutputLogger:
    """Get or create the global agent logger instance.

    Args:
        log_dir: Directory for log files
        log_level: Logging level
        reset: Whether to create a new logger instance

    Returns:
        AgentOutputLogger instance
    """
    global agent_logger

    if agent_logger is None or reset:
        agent_logger = AgentOutputLogger(
            log_dir=log_dir,
            log_level=log_level,
            enable_console=True,
            enable_file=True
        )

    return agent_logger