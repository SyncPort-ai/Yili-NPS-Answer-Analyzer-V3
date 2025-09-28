#!/usr/bin/env python3
"""Debug the V2-to-V3 conversion to see what data format agents are receiving."""

import json
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from api_v3 import _convert_v2_to_v3_format

def debug_conversion():
    """Debug the conversion process step by step."""

    # Create sample rich feedback data
    sample_data = {
        "yili_survey_data_input": {
            "data_list": [
                {
                    "样本编码": "debug_001",
                    "作答ID": "debug_test_001",
                    "Q1您向朋友或同事推荐我们的可能性多大？": "9分",
                    "Q2 您不愿意推荐我们的主要因素有哪些？": {
                        "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）": "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）",
                        "产品价格太贵，性价比不高": "-",
                        "其他": "-"
                    },
                    "Q3 您不愿意推荐我们的具体原因是什么？": "包装设计确实需要改进，颜色搭配不够吸引人，而且材质感觉有点廉价。希望能设计得更高档一些。",
                    "Q4 您愿意推荐我们的主要因素有哪些？": {
                        "产品口味口感好": "产品口味口感好",
                        "饮用后体感舒适，无不良反应": "饮用后体感舒适，无不良反应",
                        "其他": "-"
                    },
                    "Q5 您愿意推荐我们的具体原因是什么？": "伊利安慕希的口感真的很棒，浓郁顺滑，而且蛋白质含量高，营养价值好。品质一直很稳定，所以很愿意推荐。"
                },
                {
                    "样本编码": "debug_002",
                    "作答ID": "debug_test_002",
                    "Q1您向朋友或同事推荐我们的可能性多大？": "3分",
                    "Q2 您不愿意推荐我们的主要因素有哪些？": {
                        "产品价格太贵，性价比不高": "产品价格太贵，性价比不高",
                        "产品口味口感不好": "产品口味口感不好",
                        "其他": "-"
                    },
                    "Q3 您不愿意推荐我们的具体原因是什么？": "价格确实太高了，比普通酸奶贵了一倍。而且口味有点过甜，不够天然。性价比不高。",
                    "Q4 您愿意推荐我们的主要因素有哪些？": {
                        "包装设计好（如醒目、美观，材质好，便携、方便打开等）": "包装设计好（如醒目、美观，材质好，便携、方便打开等）",
                        "其他": "-"
                    },
                    "Q5 您愿意推荐我们的具体原因是什么？": "包装设计还是不错的，看起来比较高档。"
                }
            ]
        }
    }

    print("🔍 Debugging V2-to-V3 Conversion")
    print("=" * 60)

    # Show original V2 data
    print("📥 Original V2 Data Structure:")
    data_list = sample_data["yili_survey_data_input"]["data_list"]
    for i, item in enumerate(data_list):
        print(f"  Response {i+1}:")
        print(f"    NPS Score: {item['Q1您向朋友或同事推荐我们的可能性多大？']}")
        print(f"    Q3 (negative): {item['Q3 您不愿意推荐我们的具体原因是什么？'][:50]}...")
        print(f"    Q5 (positive): {item['Q5 您愿意推荐我们的具体原因是什么？'][:50]}...")
        print()

    # Convert using the API function
    print("🔄 Converting V2 to V3...")
    try:
        v3_data = _convert_v2_to_v3_format(sample_data)
        print("✅ Conversion successful!")

        # Show converted V3 data structure
        print("\n📤 Converted V3 Data Structure:")
        survey_responses = v3_data["survey_data"]["survey_responses"]

        for i, response in enumerate(survey_responses):
            print(f"  Survey Response {i+1}:")
            print(f"    response_id: {response['response_id']}")
            print(f"    nps_score: {response['nps_score']}")
            print(f"    feedback_text: {response['feedback_text']}")
            print(f"    customer_data: {response.get('customer_data', {}).get('customer_id', 'N/A')}")
            print(f"    metadata keys: {list(response.get('metadata', {}).keys())}")
            print()

        # Show what agents will see
        print("🤖 What A2 Qualitative Agent Will See:")
        responses_with_comments = []
        for response in survey_responses:
            feedback = response.get('feedback_text', '')
            if feedback and feedback.strip() and not feedback.startswith("NPS评分"):
                responses_with_comments.append({
                    'id': response['response_id'],
                    'feedback': feedback[:100] + '...' if len(feedback) > 100 else feedback
                })

        if responses_with_comments:
            print(f"  ✅ Found {len(responses_with_comments)} responses with meaningful feedback:")
            for resp in responses_with_comments:
                print(f"    {resp['id']}: {resp['feedback']}")
        else:
            print("  ❌ No responses with meaningful feedback found")

        # Check why agents might not recognize the data
        print("\n🔍 Agent Data Recognition Analysis:")

        # Check what A2 looks for
        print("  A2 Qualitative Agent Requirements:")
        print("    - Must have 'feedback_text' field ✅")
        print("    - Must not be empty string ✅" if any(r.get('feedback_text', '').strip() for r in survey_responses) else "    - Must not be empty string ❌")
        print("    - Must not start with 'NPS评分' ✅" if any(not r.get('feedback_text', '').startswith('NPS评分') for r in survey_responses) else "    - Must not start with 'NPS评分' ❌")

        # Show raw JSON for debugging
        print("\n📋 Full V3 JSON Structure (first response):")
        if survey_responses:
            print(json.dumps(survey_responses[0], indent=2, ensure_ascii=False))

        return v3_data

    except Exception as e:
        print(f"❌ Conversion failed: {e}")
        import traceback
        traceback.print_exc()
        return None

def check_agent_expectations():
    """Check what format the V3 agents actually expect."""
    print("\n🎯 Checking V3 Agent Data Expectations:")
    print("=" * 60)

    # Read A2 agent code to see what it expects
    try:
        from nps_report_v3.agents.foundation.A2_qualitative_agent import QualitativeAnalysisAgent
        print("✅ Successfully imported A2 QualitativeAnalysisAgent")

        # Create instance and check its process method
        agent = QualitativeAnalysisAgent()
        print(f"  Agent class: {type(agent).__name__}")
        print(f"  Process method exists: {hasattr(agent, 'process')}")

        # Check the agent's source code or docstring
        if hasattr(agent, 'process'):
            import inspect
            source_lines = inspect.getsource(agent.process)
            print(f"  Process method source length: {len(source_lines)} characters")

            # Look for key patterns in the source
            if 'feedback_text' in source_lines:
                print("  ✅ Agent looks for 'feedback_text' field")
            if 'comment' in source_lines.lower():
                print("  📝 Agent references 'comment' field")
            if 'tagged' in source_lines.lower():
                print("  🏷️ Agent looks for 'tagged' responses")

    except ImportError as e:
        print(f"❌ Failed to import A2 agent: {e}")
    except Exception as e:
        print(f"❌ Error inspecting A2 agent: {e}")

def main():
    """Main debug function."""
    print("🔬 V2-to-V3 Conversion Debug Tool")
    print("=" * 60)

    # Debug the conversion
    v3_data = debug_conversion()

    if v3_data:
        # Check agent expectations
        check_agent_expectations()

        print("\n🎯 Debug Summary:")
        print("  1. V2 data has rich feedback in Q3 and Q5 ✅")
        print("  2. V3 conversion creates feedback_text field ✅")
        print("  3. Need to check why A2 agent doesn't recognize the data ⚠️")
        print("  4. LLM client issue: 'LLMClientWithFailover' object has no attribute 'call' ⚠️")

        print("\n📋 Next Steps:")
        print("  1. Check A2 agent's data filtering logic")
        print("  2. Fix LLM client call method")
        print("  3. Verify agent data format expectations")
    else:
        print("\n❌ Conversion failed - cannot proceed with agent analysis")

if __name__ == "__main__":
    main()