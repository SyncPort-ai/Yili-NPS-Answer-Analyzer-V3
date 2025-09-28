#!/usr/bin/env python3
"""
NPS Statistics Analysis for Chinese Format Data
Calculate NPS net value and comprehensive statistics
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from collections import Counter
import statistics

# Add project root to path
sys.path.append('.')

from nps_report_v2.input_data_processor import InputDataProcessor

def calculate_nps_statistics(processed_data):
    """Calculate comprehensive NPS statistics"""
    
    # Extract NPS scores
    nps_scores = []
    categories = []
    
    for response in processed_data.response_data:
        score = response.nps_score.value
        category = response.nps_score.category.value
        nps_scores.append(score)
        categories.append(category)
    
    # Count categories
    category_counts = Counter(categories)
    total_responses = len(nps_scores)
    
    # Calculate percentages
    promoters = category_counts.get('promoter', 0)
    passives = category_counts.get('passive', 0)  
    detractors = category_counts.get('detractor', 0)
    
    promoter_percentage = (promoters / total_responses * 100) if total_responses > 0 else 0
    passive_percentage = (passives / total_responses * 100) if total_responses > 0 else 0
    detractor_percentage = (detractors / total_responses * 100) if total_responses > 0 else 0
    
    # Calculate NPS Net Value
    nps_net_value = promoter_percentage - detractor_percentage
    
    # Score distribution
    score_distribution = Counter(nps_scores)
    
    # Basic statistics
    mean_score = statistics.mean(nps_scores) if nps_scores else 0
    median_score = statistics.median(nps_scores) if nps_scores else 0
    mode_scores = statistics.multimode(nps_scores) if nps_scores else []
    
    # Score range analysis
    score_ranges = {
        "0-3 (Very Unsatisfied)": sum(1 for s in nps_scores if 0 <= s <= 3),
        "4-6 (Unsatisfied)": sum(1 for s in nps_scores if 4 <= s <= 6),
        "7-8 (Neutral/Passive)": sum(1 for s in nps_scores if 7 <= s <= 8),
        "9-10 (Satisfied/Promoter)": sum(1 for s in nps_scores if 9 <= s <= 10)
    }
    
    return {
        "nps_net_value": round(nps_net_value, 2),
        "total_responses": total_responses,
        "category_breakdown": {
            "promoters": {"count": promoters, "percentage": round(promoter_percentage, 2)},
            "passives": {"count": passives, "percentage": round(passive_percentage, 2)},
            "detractors": {"count": detractors, "percentage": round(detractor_percentage, 2)}
        },
        "score_distribution": dict(score_distribution),
        "statistical_measures": {
            "mean": round(mean_score, 2),
            "median": median_score,
            "mode": mode_scores,
            "min": min(nps_scores) if nps_scores else 0,
            "max": max(nps_scores) if nps_scores else 0
        },
        "score_ranges": score_ranges,
        "raw_scores": nps_scores
    }

def analyze_factor_responses(processed_data):
    """Analyze factor selection patterns"""
    
    negative_factors = Counter()
    positive_factors = Counter()
    
    for response in processed_data.response_data:
        # Negative factors
        neg_factors = response.factor_responses.get('negative_factors')
        if neg_factors and neg_factors.selected:
            for factor in neg_factors.selected:
                negative_factors[factor] += 1
        
        # Positive factors  
        pos_factors = response.factor_responses.get('positive_factors')
        if pos_factors and pos_factors.selected:
            for factor in pos_factors.selected:
                positive_factors[factor] += 1
    
    return {
        "negative_factors": dict(negative_factors),
        "positive_factors": dict(positive_factors),
        "top_negative_factors": negative_factors.most_common(5),
        "top_positive_factors": positive_factors.most_common(5)
    }

def analyze_open_responses(processed_data):
    """Analyze open-ended responses"""
    
    negative_responses = []
    positive_responses = []
    
    for response in processed_data.response_data:
        specific_reasons = response.open_responses.specific_reasons
        
        if 'negative' in specific_reasons and specific_reasons['negative']:
            negative_responses.append(specific_reasons['negative'])
            
        if 'positive' in specific_reasons and specific_reasons['positive']:
            positive_responses.append(specific_reasons['positive'])
    
    return {
        "negative_responses": negative_responses,
        "positive_responses": positive_responses,
        "negative_count": len(negative_responses),
        "positive_count": len(positive_responses)
    }

def interpret_nps_score(nps_value):
    """Interpret NPS score according to industry standards"""
    if nps_value >= 70:
        return "World Class (Excellent)"
    elif nps_value >= 50:
        return "Excellent"
    elif nps_value >= 30:
        return "Great"
    elif nps_value >= 10:
        return "Good"
    elif nps_value >= 0:
        return "Okay"
    elif nps_value >= -10:
        return "Needs Improvement"
    else:
        return "Critical - Immediate Action Required"

def main():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    
    print("=" * 60)
    print("NPS Statistics Analysis")
    print(f"Timestamp: {timestamp}")
    print("=" * 60)
    
    # Load and process the Chinese format data
    input_file = Path("data/V2-中文-sample-product-survey-input.json")
    
    with open(input_file, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
    
    # Process the data
    processor = InputDataProcessor()
    processed_data = processor.process_survey_data(raw_data)
    
    print(f"Data loaded: {processed_data.total_responses} total responses, {processed_data.valid_responses} valid responses")
    
    # Calculate NPS statistics
    nps_stats = calculate_nps_statistics(processed_data)
    factor_analysis = analyze_factor_responses(processed_data)
    open_analysis = analyze_open_responses(processed_data)
    
    # Display results
    print("\n" + "=" * 40)
    print("NPS NET VALUE & BREAKDOWN")
    print("=" * 40)
    
    print(f"NPS Net Value: {nps_stats['nps_net_value']}%")
    print(f"Interpretation: {interpret_nps_score(nps_stats['nps_net_value'])}")
    print()
    
    print("Category Breakdown:")
    for category, data in nps_stats['category_breakdown'].items():
        print(f"  {category.capitalize()}: {data['count']} ({data['percentage']}%)")
    
    print(f"\nTotal Responses: {nps_stats['total_responses']}")
    
    print("\n" + "=" * 40)
    print("SCORE DISTRIBUTION")
    print("=" * 40)
    
    for score in sorted(nps_stats['score_distribution'].keys()):
        count = nps_stats['score_distribution'][score]
        percentage = (count / nps_stats['total_responses'] * 100)
        print(f"Score {score}: {count} responses ({percentage:.1f}%)")
    
    print("\n" + "=" * 40)
    print("STATISTICAL MEASURES")
    print("=" * 40)
    
    stats = nps_stats['statistical_measures']
    print(f"Mean Score: {stats['mean']}")
    print(f"Median Score: {stats['median']}")
    print(f"Mode Score(s): {stats['mode']}")
    print(f"Score Range: {stats['min']} - {stats['max']}")
    
    print("\n" + "=" * 40)
    print("SCORE RANGE ANALYSIS")
    print("=" * 40)
    
    for range_name, count in nps_stats['score_ranges'].items():
        percentage = (count / nps_stats['total_responses'] * 100) if nps_stats['total_responses'] > 0 else 0
        print(f"{range_name}: {count} ({percentage:.1f}%)")
    
    print("\n" + "=" * 40)
    print("FACTOR ANALYSIS")
    print("=" * 40)
    
    print("Top Negative Factors:")
    for factor, count in factor_analysis['top_negative_factors']:
        print(f"  • {factor}: {count} mentions")
    
    print("\nTop Positive Factors:")
    for factor, count in factor_analysis['top_positive_factors']:
        print(f"  • {factor}: {count} mentions")
    
    print("\n" + "=" * 40)
    print("OPEN RESPONSE ANALYSIS")
    print("=" * 40)
    
    print(f"Negative responses: {open_analysis['negative_count']}")
    print(f"Positive responses: {open_analysis['positive_count']}")
    
    if open_analysis['negative_responses']:
        print("\nNegative Response Examples:")
        for i, response in enumerate(open_analysis['negative_responses'][:3], 1):
            print(f"  {i}. {response}")
    
    if open_analysis['positive_responses']:
        print("\nPositive Response Examples:")
        for i, response in enumerate(open_analysis['positive_responses'][:3], 1):
            print(f"  {i}. {response}")
    
    # Save comprehensive results
    output_file = Path("outputs/logs") / f"nps_statistics_{timestamp}.json"
    
    comprehensive_results = {
        "timestamp": timestamp,
        "data_source": str(input_file),
        "nps_statistics": nps_stats,
        "factor_analysis": factor_analysis,
        "open_response_analysis": open_analysis,
        "interpretation": interpret_nps_score(nps_stats['nps_net_value']),
        "survey_metadata": {
            "total_responses": processed_data.total_responses,
            "valid_responses": processed_data.valid_responses,
            "survey_type": processed_data.survey_metadata.get('survey_type'),
            "pre_analysis_available": bool(processed_data.survey_metadata.get('analysis_results', {}).get('base_analysis'))
        }
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(comprehensive_results, f, ensure_ascii=False, indent=2)
    
    print(f"\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    print(f"• NPS Net Value: {nps_stats['nps_net_value']}% ({interpret_nps_score(nps_stats['nps_net_value'])})")
    print(f"• Sample Size: {nps_stats['total_responses']} responses")
    print(f"• Mean Score: {stats['mean']}/10")
    print(f"• Distribution: {nps_stats['category_breakdown']['promoters']['percentage']}% Promoters, {nps_stats['category_breakdown']['passives']['percentage']}% Passives, {nps_stats['category_breakdown']['detractors']['percentage']}% Detractors")
    
    print(f"\nDetailed results saved to: {output_file}")
    print("=" * 60)

if __name__ == "__main__":
    main()