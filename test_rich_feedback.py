#!/usr/bin/env python3
"""Test V3 API with rich feedback data to validate agent processing and LLM call logging."""

import json
import requests
import time
from datetime import datetime

# API endpoint
BASE_URL = "http://localhost:7070"
V3_ENDPOINT = f"{BASE_URL}/nps-report-v3"

def create_rich_test_data():
    """Create test data with meaningful free-text feedback to trigger agent processing."""
    return {
        "yili_survey_data_input": {
            "base_analysis_result": "测试数据，包含丰富的用户反馈内容",
            "cross_analysis_result": None,
            "kano_analysis_result": None,
            "psm_analysis_result": None,
            "maxdiff_analysis_result": None,
            "nps_analysis_result": "测试NPS分析结果",
            "data_list": [
                {
                    "样本编码": "test_001",
                    "作答类型": "正式",
                    "AI标记状态": "未标记",
                    "AI标记原因": "",
                    "人工标记状态": "未标记",
                    "人工标记原因": "",
                    "作答ID": "rich_test_001",
                    "投放方式": "链接二维码",
                    "作答状态": "已完成",
                    "答题时间": "2025-09-25 10:00:00",
                    "提交时间": "2025-09-25 10:05:00",
                    "作答时长": "5分钟",
                    "Q1您向朋友或同事推荐我们的可能性多大？": "9分",
                    "Q2 您不愿意推荐我们的主要因素有哪些？": {
                        "不喜欢品牌或代言人、赞助综艺等宣传内容": "-",
                        "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）": "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）",
                        "产品价格太贵，性价比不高": "-",
                        "促销活动不好（如对赠品、活动力度/规则等不满意）": "-",
                        "产品口味口感不好": "-",
                        "饮用后感觉不舒服（如身体有腹胀、腹泻等不良反应）": "-",
                        "产品品质不稳定性（如发生变质、有异物等）": "-",
                        "没有感知到产品宣传的功能": "-",
                        "物流配送、门店导购、售后等服务体验不好": "-",
                        "其他": "-"
                    },
                    "Q3 您不愿意推荐我们的具体原因是什么？": "包装设计确实需要改进，颜色搭配不够吸引人，而且材质感觉有点廉价。希望能设计得更高档一些，符合伊利品牌的定位。",
                    "Q4 您愿意推荐我们的主要因素有哪些？": {
                        "喜欢品牌或代言人、赞助综艺等宣传内容": "喜欢品牌或代言人、赞助综艺等宣传内容",
                        "包装设计好（如醒目、美观，材质好，便携、方便打开等）": "-",
                        "产品物有所值、性价比高": "产品物有所值、性价比高",
                        "对促销活动满意（如赠品、活动力度/规则等）": "-",
                        "产品口味口感好": "产品口味口感好",
                        "饮用后体感舒适，无不良反应": "饮用后体感舒适，无不良反应",
                        "满意产品宣传的功能（如促进消化、增强免疫、助睡眠等）": "-",
                        "物流配送、门店导购、售后等服务体验好": "-",
                        "其他": "-"
                    },
                    "Q5 您愿意推荐我们的具体原因是什么？": "伊利安慕希的口感真的很棒，浓郁顺滑，而且蛋白质含量高，营养价值好。杨幂代言的形象也很不错，感觉很有品质保证。价格虽然不算便宜，但是物有所值。我已经喝了两年多了，品质一直很稳定，所以很愿意推荐给朋友们。"
                },
                {
                    "样本编码": "test_002",
                    "作答类型": "正式",
                    "AI标记状态": "未标记",
                    "AI标记原因": "",
                    "人工标记状态": "未标记",
                    "人工标记原因": "",
                    "作答ID": "rich_test_002",
                    "投放方式": "链接二维码",
                    "作答状态": "已完成",
                    "答题时间": "2025-09-25 11:00:00",
                    "提交时间": "2025-09-25 11:03:00",
                    "作答时长": "3分钟",
                    "Q1您向朋友或同事推荐我们的可能性多大？": "3分",
                    "Q2 您不愿意推荐我们的主要因素有哪些？": {
                        "不喜欢品牌或代言人、赞助综艺等宣传内容": "-",
                        "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）": "-",
                        "产品价格太贵，性价比不高": "产品价格太贵，性价比不高",
                        "促销活动不好（如对赠品、活动力度/规则等不满意）": "-",
                        "产品口味口感不好": "产品口味口感不好",
                        "饮用后感觉不舒服（如身体有腹胀、腹泻等不良反应）": "-",
                        "产品品质不稳定性（如发生变质、有异物等）": "-",
                        "没有感知到产品宣传的功能": "没有感知到产品宣传的功能",
                        "物流配送、门店导购、售后等服务体验不好": "-",
                        "其他": "-"
                    },
                    "Q3 您不愿意推荐我们的具体原因是什么？": "价格确实太高了，一盒12支要30多块钱，比普通酸奶贵了一倍。而且口味有点过甜，不够天然。广告说的那些功能我也没感觉到，感觉就是普通的酸奶。性价比不高，不值得这个价钱。",
                    "Q4 您愿意推荐我们的主要因素有哪些？": {
                        "喜欢品牌或代言人、赞助综艺等宣传内容": "-",
                        "包装设计好（如醒目、美观，材质好，便携、方便打开等）": "包装设计好（如醒目、美观，材质好，便携、方便打开等）",
                        "产品物有所值、性价比高": "-",
                        "对促销活动满意（如赠品、活动力度/规则等）": "-",
                        "产品口味口感好": "-",
                        "饮用后体感舒适，无不良反应": "-",
                        "满意产品宣传的功能（如促进消化、增强免疫、助睡眠等）": "-",
                        "物流配送、门店导购、售后等服务体验好": "-",
                        "其他": "-"
                    },
                    "Q5 您愿意推荐我们的具体原因是什么？": "包装设计还是不错的，看起来比较高档，送人也拿得出手。"
                },
                {
                    "样本编码": "test_003",
                    "作答类型": "正式",
                    "AI标记状态": "未标记",
                    "AI标记原因": "",
                    "人工标记状态": "未标记",
                    "人工标记原因": "",
                    "作答ID": "rich_test_003",
                    "投放方式": "链接二维码",
                    "作答状态": "已完成",
                    "答题时间": "2025-09-25 12:00:00",
                    "提交时间": "2025-09-25 12:04:00",
                    "作答时长": "4分钟",
                    "Q1您向朋友或同事推荐我们的可能性多大？": "7分",
                    "Q2 您不愿意推荐我们的主要因素有哪些？": {
                        "不喜欢品牌或代言人、赞助综艺等宣传内容": "-",
                        "包装设计不好（如不够醒目、美观，材质不好，不便携、不方便打开等）": "-",
                        "产品价格太贵，性价比不高": "-",
                        "促销活动不好（如对赠品、活动力度/规则等不满意）": "促销活动不好（如对赠品、活动力度/规则等不满意）",
                        "产品口味口感不好": "-",
                        "饮用后感觉不舒服（如身体有腹胀、腹泻等不良反应）": "-",
                        "产品品质不稳定性（如发生变质、有异物等）": "-",
                        "没有感知到产品宣传的功能": "-",
                        "物流配送、门店导购、售后等服务体验不好": "物流配送、门店导购、售后等服务体验不好",
                        "其他": "-"
                    },
                    "Q3 您不愿意推荐我们的具体原因是什么？": "促销活动太少了，而且折扣力度不大。另外网购的时候物流有点慢，有一次还收到了过期的产品，售后处理也不够及时。希望能改善服务质量。",
                    "Q4 您愿意推荐我们的主要因素有哪些？": {
                        "喜欢品牌或代言人、赞助综艺等宣传内容": "-",
                        "包装设计好（如醒目、美观，材质好，便携、方便打开等）": "-",
                        "产品物有所值、性价比高": "-",
                        "对促销活动满意（如赠品、活动力度/规则等）": "-",
                        "产品口味口感好": "产品口味口感好",
                        "饮用后体感舒适，无不良反应": "饮用后体感舒适，无不良反应",
                        "满意产品宣传的功能（如促进消化、增强免疫、助睡眠等）": "满意产品宣传的功能（如促进消化、增强免疫、助睡眠等）",
                        "物流配送、门店导购、售后等服务体验好": "-",
                        "其他": "-"
                    },
                    "Q5 您愿意推荐我们的具体原因是什么？": "口感确实很好，比其他品牌的酸奶更浓稠，蛋白质含量也高。喝了之后确实感觉消化好了一些，可能是益生菌的作用。总体来说产品质量还是值得信赖的，就是服务需要提升。"
                }
            ]
        }
    }

def test_rich_feedback_analysis():
    """Test V3 API with rich feedback data."""
    print("🔬 Testing V3 API with Rich Feedback Data")
    print("=" * 60)

    test_data = create_rich_test_data()
    print(f"✅ Created test data with {len(test_data['yili_survey_data_input']['data_list'])} rich feedback responses")

    # Show sample feedback
    sample = test_data["yili_survey_data_input"]["data_list"][0]
    print(f"\n📝 Sample feedback content:")
    print(f"   Q3: {sample['Q3 您不愿意推荐我们的具体原因是什么？'][:50]}...")
    print(f"   Q5: {sample['Q5 您愿意推荐我们的具体原因是什么？'][:50]}...")

    # Make API request
    print(f"\n📤 Sending request to V3 API...")
    start_time = time.time()

    try:
        response = requests.post(
            V3_ENDPOINT,
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=300
        )

        elapsed = time.time() - start_time
        print(f"⏱️  Response received in {elapsed:.2f} seconds")

        if response.status_code == 200:
            result = response.json()
            print("✅ V3 API request successful!")

            # Analyze results
            analyze_rich_feedback_results(result)
            return True
        else:
            print(f"❌ API request failed with status {response.status_code}")
            print(f"📝 Response: {response.text[:1000]}")
            return False

    except Exception as e:
        print(f"❌ Error during API call: {e}")
        return False

def analyze_rich_feedback_results(result):
    """Analyze the results from rich feedback test."""
    print(f"\n🔍 Rich Feedback Analysis Results:")
    print(f"=" * 50)

    # Agent execution analysis
    agent_sequence = result.get("agent_sequence", [])
    performance = {
        "total_tokens": result.get("total_tokens_used", 0),
        "llm_calls": result.get("total_llm_calls", 0),
        "processing_time_ms": result.get("total_processing_time_ms", 0)
    }

    print(f"🤖 Agent Execution:")
    print(f"   Agents executed: {len(agent_sequence)}")
    print(f"   Agent sequence: {agent_sequence}")

    print(f"\n📊 LLM Performance:")
    print(f"   Total LLM calls: {performance['llm_calls']}")
    print(f"   Total tokens used: {performance['total_tokens']}")
    print(f"   Processing time: {performance['processing_time_ms']}ms")

    # Check if we got meaningful analysis
    nps_metrics = result.get("nps_metrics", {})
    if nps_metrics:
        print(f"\n📈 NPS Analysis:")
        print(f"   NPS Score: {nps_metrics.get('nps_score', 'N/A')}")
        print(f"   Sample Size: {nps_metrics.get('sample_size', 'N/A')}")
        print(f"   Promoters: {nps_metrics.get('promoters_percentage', 0):.1f}%")
        print(f"   Detractors: {nps_metrics.get('detractors_percentage', 0):.1f}%")

    # Check HTML report
    html_report = result.get("html_report", "")
    print(f"\n📄 Report Generation:")
    print(f"   HTML report length: {len(html_report)} characters")

    # Success indicators
    success_indicators = []
    if performance['llm_calls'] > 0:
        success_indicators.append("✅ LLM calls were made")
    else:
        success_indicators.append("❌ No LLM calls detected")

    if len(agent_sequence) > 0:
        success_indicators.append("✅ Agents were executed")
    else:
        success_indicators.append("❌ No agents in sequence")

    if len(html_report) > 1000:
        success_indicators.append("✅ Meaningful report generated")
    else:
        success_indicators.append("❌ Report too short")

    print(f"\n🎯 Test Success Indicators:")
    for indicator in success_indicators:
        print(f"   {indicator}")

def main():
    """Main test function."""
    print(f"🚀 Rich Feedback V3 API Test")
    print(f"⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check API availability
    try:
        health_response = requests.get(f"{BASE_URL}/healthz", timeout=5)
        if health_response.status_code != 200:
            print("❌ API server not available")
            return False
    except:
        print("❌ Cannot connect to API server")
        return False

    print("✅ API server is available")

    # Run rich feedback test
    success = test_rich_feedback_analysis()

    if success:
        print(f"\n🎉 Rich Feedback Test Complete!")
        print(f"📋 This test should have triggered:")
        print(f"   - Meaningful agent processing with text analysis")
        print(f"   - LLM API calls for qualitative analysis")
        print(f"   - Comprehensive logging of all interactions")
    else:
        print(f"\n❌ Rich Feedback Test Failed")

    return success

if __name__ == "__main__":
    main()