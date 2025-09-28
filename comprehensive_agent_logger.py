"""Comprehensive Agent Logger with LLM Call Interception

This module provides comprehensive logging for the V3 multi-agent workflow,
capturing every step, LLM call, prompt, and response for detailed debugging.
"""

import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import traceback
import functools
from agent_logger import get_agent_logger


class ComprehensiveAgentLogger:
    """Enhanced logger that captures every detail of agent execution."""

    def __init__(self, base_logger: Optional[Any] = None):
        """Initialize comprehensive logger.

        Args:
            base_logger: Base agent logger instance
        """
        self.base_logger = base_logger or get_agent_logger()
        self.current_agent_id = None
        self.llm_call_counter = {}
        self.step_counter = {}

    def set_current_agent(self, agent_id: str, agent_name: str):
        """Set the current agent being executed.

        Args:
            agent_id: Agent identifier
            agent_name: Human-readable agent name
        """
        self.current_agent_id = agent_id
        self.llm_call_counter[agent_id] = 0
        self.step_counter[agent_id] = 0

        self.base_logger.log_agent_start(agent_id, agent_name)

    def log_step(self, step_name: str, step_data: Any = None, level: str = "INFO"):
        """Log a step in the current agent's execution.

        Args:
            step_name: Name of the step
            step_data: Data associated with the step
            level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        if not self.current_agent_id:
            return

        self.step_counter[self.current_agent_id] += 1
        step_num = self.step_counter[self.current_agent_id]

        full_step_name = f"[{step_num:02d}] {step_name}"
        self.base_logger.log_agent_step(self.current_agent_id, full_step_name, step_data)

    def log_agent_complete(self, output_data: Any):
        """Log the completion of an agent.

        Args:
            output_data: The agent's output data
        """
        if not self.current_agent_id:
            return

        total_steps = self.step_counter.get(self.current_agent_id, 0)
        total_llm_calls = self.llm_call_counter.get(self.current_agent_id, 0)

        completion_summary = {
            "total_steps": total_steps,
            "total_llm_calls": total_llm_calls,
            "output_summary": self.base_logger._create_data_summary(output_data) if output_data else None
        }

        self.log_step("AGENT COMPLETION SUMMARY", completion_summary)
        self.base_logger.log_agent_output(self.current_agent_id, output_data, success=True)

    def log_error(self, error: Exception, context: str = ""):
        """Log an error with full context.

        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        if not self.current_agent_id:
            return

        error_data = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "context": context,
            "traceback": traceback.format_exc()
        }

        self.log_step("ERROR OCCURRED", error_data, "ERROR")
        self.base_logger.log_agent_output(
            self.current_agent_id,
            None,
            success=False,
            error=f"{context}: {str(error)}"
        )


# Global instance
_comprehensive_logger = None

def get_comprehensive_logger(reset: bool = False):
    """Get or create the global comprehensive logger.

    Args:
        reset: Whether to create a new logger instance

    Returns:
        ComprehensiveAgentLogger instance
    """
    global _comprehensive_logger

    if _comprehensive_logger is None or reset:
        _comprehensive_logger = ComprehensiveAgentLogger()

    return _comprehensive_logger