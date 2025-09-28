#!/usr/bin/env python3
"""Comprehensive test for V3 API with detailed agent logging."""

import json
import requests
import time
from pathlib import Path
from datetime import datetime

# API endpoint
BASE_URL = "http://localhost:7070"
V3_ENDPOINT = f"{BASE_URL}/nps-report-v3"

def test_v3_with_comprehensive_logging():
    """Test V3 API with comprehensive agent logging to track every step."""
    print("=" * 80)
    print("🔬 COMPREHENSIVE AGENT LOGGING TEST - V3 API")
    print("=" * 80)
    print("This test will capture EVERY step, LLM call, prompt, and response")
    print("for detailed debugging of each agent in the multi-agent workflow.")
    print("")

    # Load test data
    test_data_file = Path("data/V2-sample-product-survey-input-100-yili-format.json")
    if not test_data_file.exists():
        print(f"❌ Test data file not found: {test_data_file}")
        return False

    with open(test_data_file, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    data_size = len(test_data.get('yili_survey_data_input', {}).get('data_list', []))
    print(f"✅ Loaded test data with {data_size} survey responses")
    print(f"📄 Data file: {test_data_file}")

    # Show what we're testing
    print(f"\n🎯 TEST OBJECTIVES:")
    print(f"   1. Track every agent execution (A0-A3, B1-B9, C1-C5)")
    print(f"   2. Log every LLM API call with prompts and responses")
    print(f"   3. Monitor each step within each agent")
    print(f"   4. Capture performance metrics and error details")
    print(f"   5. Generate comprehensive logs for debugging")

    # Make API request with timing
    print(f"\n📤 Sending request to V3 API with comprehensive logging...")
    print(f"🔗 Endpoint: {V3_ENDPOINT}")

    start_time = time.time()

    try:
        response = requests.post(
            V3_ENDPOINT,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=300  # 5 minute timeout for comprehensive logging
        )

        elapsed = time.time() - start_time
        print(f"⏱️  Response received in {elapsed:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            print("✅ V3 API request successful!")

            # Analyze comprehensive logging results
            analyze_comprehensive_results(result)

            return True

        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"📝 Response: {response.text[:1000]}")
            return False

    except requests.exceptions.Timeout:
        elapsed = time.time() - start_time
        print(f"⏰ Request timed out after {elapsed:.2f} seconds")
        print("   This might indicate agents are taking too long or getting stuck")
        return False
    except Exception as e:
        print(f"❌ Error during API call: {e}")
        return False

def analyze_comprehensive_results(result):
    """Analyze the comprehensive logging results."""
    print(f"\n" + "="*60)
    print(f"📊 COMPREHENSIVE LOGGING ANALYSIS")
    print(f"="*60)

    # Basic workflow info
    workflow_info = {
        "workflow_id": result.get("workflow_id"),
        "phase": result.get("workflow_phase"),
        "version": result.get("workflow_version"),
        "status": result.get("analysis_status", "unknown")
    }

    print(f"🔍 Workflow Information:")
    for key, value in workflow_info.items():
        print(f"   {key}: {value}")

    # Agent execution analysis
    agent_sequence = result.get("agent_sequence", [])
    agent_outputs = result.get("agent_outputs", {})

    print(f"\n🤖 Agent Execution Analysis:")
    print(f"   Total agents in sequence: {len(agent_sequence)}")
    print(f"   Agents with outputs: {len(agent_outputs)}")
    print(f"   Agent sequence: {agent_sequence}")

    # Performance metrics
    performance = {
        "total_tokens": result.get("total_tokens_used", 0),
        "llm_calls": result.get("total_llm_calls", 0),
        "processing_time_ms": result.get("total_processing_time_ms", 0),
        "memory_peak_mb": result.get("memory_peak_mb", 0.0)
    }

    print(f"\n📈 Performance Metrics:")
    for key, value in performance.items():
        print(f"   {key}: {value}")

    # Error and warning analysis
    errors = result.get("errors", [])
    warnings = result.get("warnings", [])
    failed_agents = result.get("failed_agents", [])

    print(f"\n⚠️  Issues Analysis:")
    print(f"   Errors: {len(errors)}")
    print(f"   Warnings: {len(warnings)}")
    print(f"   Failed agents: {len(failed_agents)}")

    if errors:
        print(f"   Error details:")
        for i, error in enumerate(errors[:3], 1):  # Show first 3 errors
            print(f"     {i}. {error}")

    if failed_agents:
        print(f"   Failed agent details: {failed_agents}")

    # Comprehensive logging specific info
    if result.get("comprehensive_logging"):
        print(f"\n🔬 Comprehensive Logging Details:")
        print(f"   Enhanced logging: ✅")
        print(f"   Detailed agent logs: {result.get('detailed_agent_logs', False)}")

        log_dir = result.get("agent_log_dir")
        if log_dir:
            print(f"   Log directory: {log_dir}")

        # Agent log summary
        log_summary = result.get("agent_log_summary", {})
        if log_summary:
            metadata = log_summary.get("metadata", {})
            agent_outputs_logged = log_summary.get("agent_outputs", {})

            print(f"   Session ID: {metadata.get('session_id')}")
            print(f"   Logged agents: {len(agent_outputs_logged)}")
            print(f"   Total execution time: {metadata.get('total_execution_time_ms', 0)}ms")

    # NPS results analysis
    nps_metrics = result.get("nps_metrics", {})
    if nps_metrics:
        print(f"\n📊 NPS Results Analysis:")
        print(f"   NPS Score: {nps_metrics.get('nps_score', 'N/A')}")
        print(f"   Sample Size: {nps_metrics.get('sample_size', 'N/A')}")
        print(f"   Promoters: {nps_metrics.get('promoters_percentage', 0):.1f}%")
        print(f"   Passives: {nps_metrics.get('passives_percentage', 0):.1f}%")
        print(f"   Detractors: {nps_metrics.get('detractors_percentage', 0):.1f}%")

    # Report generation analysis
    html_report = result.get("html_report", "")
    html_reports = result.get("html_reports", {})

    print(f"\n📄 Report Generation Analysis:")
    print(f"   Main HTML report length: {len(html_report)} characters")
    print(f"   Additional reports: {len(html_reports)}")

def check_detailed_logs():
    """Check the detailed log files that were generated."""
    print(f"\n" + "="*60)
    print(f"📁 DETAILED LOG FILE ANALYSIS")
    print(f"="*60)

    # Check for today's logs
    today = datetime.now().strftime("%Y%m%d")
    log_dir = Path(f"outputs/agent_logs/{today}")

    if not log_dir.exists():
        print(f"❌ No log directory found: {log_dir}")
        return

    print(f"✅ Log directory found: {log_dir}")

    # List all log files
    log_files = list(log_dir.glob("*.log"))
    json_files = list(log_dir.glob("*.json"))

    print(f"📄 Log files found:")
    print(f"   .log files: {len(log_files)}")
    print(f"   .json files: {len(json_files)}")

    # Show recent log files
    all_files = sorted(log_files + json_files, key=lambda f: f.stat().st_mtime, reverse=True)

    print(f"\n📋 Recent log files (most recent first):")
    for i, file in enumerate(all_files[:10], 1):  # Show top 10 most recent
        size = file.stat().st_size
        modified = datetime.fromtimestamp(file.stat().st_mtime).strftime("%H:%M:%S")
        print(f"   {i:2d}. {file.name} ({size} bytes, {modified})")

    # Analyze the most recent session
    if json_files:
        latest_json = max(json_files, key=lambda f: f.stat().st_mtime)
        print(f"\n🔍 Analyzing latest session file: {latest_json.name}")

        try:
            with open(latest_json, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            metadata = session_data.get("metadata", {})
            agent_outputs = session_data.get("agent_outputs", {})

            print(f"   Session agents: {len(agent_outputs)}")
            print(f"   Execution time: {metadata.get('total_execution_time_ms', 0)}ms")
            print(f"   Errors: {len(metadata.get('errors', []))}")
            print(f"   Warnings: {len(metadata.get('warnings', []))}")

            # Show agent details
            if agent_outputs:
                print(f"\n   Agent execution details:")
                for agent_id, agent_data in list(agent_outputs.items())[:5]:  # Show first 5
                    status = agent_data.get("status", "unknown")
                    exec_time = agent_data.get("execution_time_ms", 0)
                    steps = len(agent_data.get("steps", []))
                    llm_calls = len(agent_data.get("llm_calls", []))

                    print(f"     {agent_id}: {status} ({exec_time}ms, {steps} steps, {llm_calls} LLM calls)")

        except Exception as e:
            print(f"   ❌ Error reading session file: {e}")

def main():
    """Main test function."""
    print("\n🚀 Starting Comprehensive Agent Logging Tests")
    print(f"⏰ Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check if API is running
    try:
        health_response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        if health_response.status_code != 200:
            print("❌ API is not running. Please start the API server first.")
            print("   Command: uvicorn api:app --port 7070")
            return False
    except:
        print("❌ Cannot connect to API. Please start the API server first.")
        print("   Command: uvicorn api:app --port 7070")
        return False

    print("✅ API server is running")

    # Run the comprehensive test
    success = test_v3_with_comprehensive_logging()

    if success:
        # Wait a moment for logs to be written
        time.sleep(2)
        check_detailed_logs()

        print(f"\n🎉 Comprehensive Agent Logging Test Complete!")
        print(f"📋 Check the log files for detailed agent execution information.")
        print(f"🔍 Look for:")
        print(f"   - Agent start/end times")
        print(f"   - LLM API calls with prompts and responses")
        print(f"   - Step-by-step execution details")
        print(f"   - Error messages and stack traces")
        print(f"   - Performance metrics per agent")
    else:
        print(f"\n❌ Test failed. Check the API server and try again.")

    return success

if __name__ == "__main__":
    main()