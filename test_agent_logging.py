#!/usr/bin/env python3
"""Test script for agent logging functionality in V3 API."""

import json
import requests
from pathlib import Path
from datetime import datetime
import time

# API endpoint
BASE_URL = "http://localhost:7070"
V3_ENDPOINT = f"{BASE_URL}/nps-report-v3"

def test_v3_with_logging():
    """Test V3 API with agent logging."""
    print("=" * 60)
    print("Testing V3 API with Agent Logging")
    print("=" * 60)

    # Load test data
    test_data_file = Path("data/V2-sample-product-survey-input-100-yili-format.json")
    if not test_data_file.exists():
        print(f"❌ Test data file not found: {test_data_file}")
        return

    with open(test_data_file, 'r', encoding='utf-8') as f:
        test_data = json.load(f)

    print(f"✅ Loaded test data with {len(test_data.get('yili_survey_data_input', {}).get('data_list', []))} responses")

    # Make API request
    print("\n📤 Sending request to V3 API...")
    start_time = time.time()

    try:
        response = requests.post(
            V3_ENDPOINT,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=60
        )

        elapsed = time.time() - start_time
        print(f"⏱️  Response received in {elapsed:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            print("✅ V3 API request successful!")

            # Check for agent log information
            if "agent_log_dir" in result:
                print(f"\n📁 Agent logs saved to: {result['agent_log_dir']}")

            if "agent_log_summary" in result:
                summary = result["agent_log_summary"]
                metadata = summary.get("metadata", {})
                agent_outputs = summary.get("agent_outputs", {})

                print(f"\n📊 Agent Execution Summary:")
                print(f"   Session ID: {metadata.get('session_id', 'N/A')}")
                print(f"   Agents Executed: {len(metadata.get('agents_executed', []))}")
                print(f"   Total Time: {metadata.get('total_execution_time_ms', 0)}ms")
                print(f"   Errors: {len(metadata.get('errors', []))}")
                print(f"   Warnings: {len(metadata.get('warnings', []))}")

                print(f"\n🤖 Agent Details:")
                for agent_id, agent_data in agent_outputs.items():
                    status = agent_data.get("status", "unknown")
                    exec_time = agent_data.get("execution_time_ms", 0)
                    status_emoji = "✅" if status == "completed" else "❌"
                    print(f"   {status_emoji} {agent_id}: {agent_data.get('agent_name', 'Unknown')} - {status} ({exec_time}ms)")

        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"Response: {response.text[:500]}")

    except requests.exceptions.Timeout:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")

def test_agent_log_retrieval():
    """Test retrieving agent logs via API."""
    print("\n" + "=" * 60)
    print("Testing Agent Log Retrieval")
    print("=" * 60)

    # Get today's logs
    today = datetime.now().strftime("%Y%m%d")
    logs_url = f"{V3_ENDPOINT}/agent-logs"

    print(f"\n📋 Retrieving logs for date: {today}")

    try:
        # Get list of sessions
        response = requests.get(logs_url, params={"date": today})

        if response.status_code == 200:
            data = response.json()
            print(f"✅ Found {data['sessions_count']} sessions")

            if data['sessions']:
                # Get details of the first session
                first_session = data['sessions'][0]
                session_id = first_session['session_id']

                print(f"\n🔍 Getting details for session: {session_id}")
                detail_response = requests.get(logs_url, params={
                    "date": today,
                    "session_id": session_id
                })

                if detail_response.status_code == 200:
                    session_data = detail_response.json()
                    print("✅ Session details retrieved successfully")

                    # Display agent outputs
                    agent_outputs = session_data['data'].get('agent_outputs', {})
                    print(f"\n📊 Agents in session: {len(agent_outputs)}")

                    for agent_id in sorted(agent_outputs.keys()):
                        agent_info = agent_outputs[agent_id]
                        print(f"   - {agent_id}: {agent_info.get('agent_name', 'Unknown')} "
                              f"({agent_info.get('status', 'unknown')})")
        elif response.status_code == 404:
            print(f"ℹ️  No logs found for {today}")
            data = response.json()
            if "available_dates" in data:
                print(f"Available dates: {', '.join(data['available_dates'])}")
        else:
            print(f"❌ Failed to retrieve logs: {response.status_code}")

    except Exception as e:
        print(f"❌ Error retrieving logs: {e}")

def main():
    """Main test function."""
    print("\n🚀 Starting Agent Logging Tests\n")

    # Check if API is running
    try:
        health_response = requests.get(f"{BASE_URL}/healthz", timeout=2)
        if health_response.status_code != 200:
            print("❌ API is not running. Please start the API server first.")
            print("   Run: python api.py")
            return
    except:
        print("❌ Cannot connect to API. Please start the API server first.")
        print("   Run: python api.py")
        return

    # Run tests
    test_v3_with_logging()
    time.sleep(1)  # Small delay between tests
    test_agent_log_retrieval()

    print("\n✅ Agent Logging Tests Complete!\n")

if __name__ == "__main__":
    main()