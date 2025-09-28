"""
State management for NPS Analysis Multi-Agent System
Simple dict-based state schema as defined in design document
"""

from typing import Dict, List, Any, Optional
from datetime import datetime


def create_initial_state(raw_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create initial state from raw JSON input.
    
    Args:
        raw_input: Raw JSON input containing survey responses
        
    Returns:
        Initial state dict for the workflow
    """
    return {
        # Input data
        "raw_responses": raw_input.get("survey_responses", []),
        "metadata": raw_input.get("metadata", {}),
        "optional_data": raw_input.get("optional_data", {}),
        "yili_products_csv": raw_input.get("optional_data", {}).get("yili_products_csv"),
        
        # Processing flags (for supervisor routing)
        "ingestion_complete": False,
        "quant_complete": False,
        "qual_complete": False,
        "context_complete": False,
        "report_complete": False,
        
        # Processed data (from IngestionAgent)
        "clean_responses": [],
        
        # Results from each agent
        "nps_results": {},
        "qual_results": {},
        "context_results": {},
        
        # Final comprehensive output
        "final_output": {},
        
        # Error tracking
        "errors": [],
        
        # Processing metadata
        "processing_started": datetime.now().isoformat(),
        "current_agent": None,
        # Debug/trace
        "route_log": [],
        "step_counter": 0
    }


def validate_state_structure(state: Dict[str, Any]) -> bool:
    """
    Validate that state contains all required keys.
    
    Args:
        state: State dictionary to validate
        
    Returns:
        True if state is valid, False otherwise
    """
    required_keys = [
        "raw_responses", "ingestion_complete", "quant_complete", 
        "qual_complete", "context_complete", "report_complete",
        "clean_responses", "nps_results", "qual_results", 
        "context_results", "final_output", "errors"
    ]
    
    return all(key in state for key in required_keys)


def get_completion_status(state: Dict[str, Any]) -> Dict[str, bool]:
    """
    Get completion status of all agents.
    
    Args:
        state: Current state dictionary
        
    Returns:
        Dictionary with completion status for each agent
    """
    return {
        "ingestion": state.get("ingestion_complete", False),
        "quantitative": state.get("quant_complete", False),
        "qualitative": state.get("qual_complete", False),
        "context": state.get("context_complete", False),
        "report": state.get("report_complete", False)
    }


def add_error(state: Dict[str, Any], error_msg: str, agent_name: str = None) -> None:
    """
    Add error to state error list.
    
    Args:
        state: Current state dictionary
        error_msg: Error message to add
        agent_name: Optional agent name where error occurred
    """
    error_entry = {
        "timestamp": datetime.now().isoformat(),
        "message": error_msg,
        "agent": agent_name
    }
    
    if "errors" not in state:
        state["errors"] = []
    
    state["errors"].append(error_entry)


def update_current_agent(state: Dict[str, Any], agent_name: str) -> None:
    """
    Update current agent in state for tracking.
    
    Args:
        state: Current state dictionary
        agent_name: Name of current agent
    """
    state["current_agent"] = agent_name
    state[f"{agent_name}_started"] = datetime.now().isoformat()


def is_workflow_complete(state: Dict[str, Any]) -> bool:
    """
    Check if entire workflow is complete.
    
    Args:
        state: Current state dictionary
        
    Returns:
        True if all agents have completed successfully
    """
    completion_status = get_completion_status(state)
    return all(completion_status.values())


def get_next_agent(state: Dict[str, Any]) -> Optional[str]:
    """
    Determine next agent to execute based on completion status.
    
    Args:
        state: Current state dictionary
        
    Returns:
        Name of next agent to execute, or None if workflow is complete
    """
    if not state.get("ingestion_complete", False):
        return "ingestion"
    elif not state.get("quant_complete", False):
        return "quantitative"
    elif not state.get("qual_complete", False):
        return "qualitative"
    elif not state.get("context_complete", False):
        return "context"
    elif not state.get("report_complete", False):
        return "report"
    else:
        return None  # Workflow complete
