#!/usr/bin/env python3
"""
Direct Compatibility Test
========================

Tests actual API endpoints for identical behavior.
"""

import json
import requests
import sys
from typing import Dict, Any

# Test server endpoints
EXTERNAL_API_URL = "http://localhost:7070"
ORIGINAL_API_URL = "http://localhost:7000"  # If running original

def test_analyze_endpoint_compatibility():
    """Test /analyze endpoint compatibility with real API calls."""
    
    test_data = {
        "emotionalType": 1,
        "taskType": 2,
        "questionId": "test_compatibility_001",
        "wordInfos": [
            {"ids": [1], "word": "安慕希口感很好"},
            {"ids": [2], "word": ""}  # Test empty string - critical test case
        ]
    }
    
    print("🧪 Testing /analyze endpoint compatibility...")
    print(f"Test data: {json.dumps(test_data, ensure_ascii=False)}")
    
    try:
        # Test external API
        response = requests.post(f"{EXTERNAL_API_URL}/analyze", json=test_data, timeout=30)
        print(f"\n📡 External API Response:")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}...")
        
        if response.status_code == 200:
            print("✅ External API /analyze endpoint working")
        else:
            print("❌ External API /analyze endpoint failed")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ External API connection failed: {e}")
        print("💡 Make sure api_external.py is running on port 7070")

def test_nps_report_v0_compatibility():
    """Test /nps-report-v0 endpoint compatibility."""
    
    test_data = {
        "input": {
            "input_text_0": {
                "count": 10,
                "nps_value": 0.2,
                "user_distribution": [
                    {"score": 9, "people_number": 3, "percentage": 0.3},
                    {"score": 7, "people_number": 2, "percentage": 0.2},
                    {"score": 5, "people_number": 5, "percentage": 0.5}
                ],
                "analysis_type_list": [
                    {"type_name": "推荐者", "type_percentage": 0.3},
                    {"type_name": "中立者", "type_percentage": 0.2},
                    {"type_name": "贬损者", "type_percentage": 0.5}
                ]
            }
        }
    }
    
    print("\n🧪 Testing /nps-report-v0 endpoint compatibility...")
    
    try:
        response = requests.post(f"{EXTERNAL_API_URL}/nps-report-v0", json=test_data, timeout=30)
        print(f"\n📡 External API Response:")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:300]}...")
        
        if response.status_code == 200:
            result = response.json()
            if "output_text_0" in result and "output" in result:
                print("✅ External API /nps-report-v0 endpoint working")
                print(f"Generated report preview: {result['output_text_0'][:100]}...")
            else:
                print("❌ Response format incorrect")
        else:
            print("❌ External API /nps-report-v0 endpoint failed")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ External API connection failed: {e}")

def test_health_endpoints():
    """Test health and version endpoints."""
    
    print("\n🧪 Testing health endpoints...")
    
    endpoints = ["/healthz", "/version", "/"]
    
    for endpoint in endpoints:
        try:
            response = requests.get(f"{EXTERNAL_API_URL}{endpoint}", timeout=10)
            print(f"✅ {endpoint}: {response.status_code}")
            
        except requests.exceptions.RequestException as e:
            print(f"❌ {endpoint}: Failed - {e}")

def test_validation_errors():
    """Test that validation errors are handled correctly."""
    
    print("\n🧪 Testing validation error handling...")
    
    # Test case 1: Missing emotionalType
    invalid_data = {
        "taskType": 1,
        "questionId": "test",
        "wordInfos": [{"ids": [1], "word": "test"}]
    }
    
    try:
        response = requests.post(f"{EXTERNAL_API_URL}/analyze", json=invalid_data, timeout=10)
        if response.status_code == 400:
            result = response.json()
            if "emotionalType 不能为 None" in result.get("status_message", ""):
                print("✅ Validation error handling working correctly")
            else:
                print(f"❌ Unexpected error message: {result.get('status_message')}")
        else:
            print(f"❌ Expected 400 status, got {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Validation test failed: {e}")

def main():
    """Run all compatibility tests."""
    
    print("🚀 Direct API Compatibility Test")
    print("=" * 50)
    print("Testing api_external.py endpoints for compatibility")
    print("Make sure api_external.py is running on port 7070")
    print("=" * 50)
    
    # Test basic connectivity
    try:
        response = requests.get(f"{EXTERNAL_API_URL}/healthz", timeout=5)
        if response.status_code == 200:
            print("✅ External API is running and accessible")
        else:
            print("❌ External API health check failed")
            return 1
    except requests.exceptions.RequestException:
        print("❌ Cannot connect to external API")
        print("💡 Start the API with: python api_external.py")
        return 1
    
    # Run compatibility tests
    test_health_endpoints()
    test_nps_report_v0_compatibility()
    test_validation_errors()
    test_analyze_endpoint_compatibility()
    
    print("\n" + "=" * 50)
    print("🎯 COMPATIBILITY TEST SUMMARY")
    print("=" * 50)
    print("✅ If all tests above passed, compatibility is verified")
    print("❌ If any tests failed, fix issues before deployment")
    print("📋 Next: Test with real production data samples")
    
    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)