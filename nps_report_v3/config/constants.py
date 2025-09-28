"""Constants for NPS V3 API"""

# API Version
API_VERSION = "3.0.0"

# Agent IDs
FOUNDATION_AGENTS = {
    "A0": "Data Preprocessor",
    "A1": "NPS Calculator",
    "A2": "Confidence Assessor",
    "A3": "Quality Monitor"
}

ANALYSIS_AGENTS = {
    "B1": "Promoter Analyst",
    "B2": "Passive Analyst",
    "B3": "Detractor Analyst",
    "B4": "Text Clustering Agent",
    "B5": "Driver Analysis Agent",
    "B6": "Product Dimension Agent",
    "B7": "Geographic Dimension Agent",
    "B8": "Channel Dimension Agent",
    "B9": "Analysis Coordinator"
}

CONSULTING_AGENTS = {
    "C1": "Strategic Advisor",
    "C2": "Product Consultant",
    "C3": "Marketing Advisor",
    "C4": "Risk Manager",
    "C5": "Executive Synthesizer"
}

# NPS Score Boundaries
NPS_BOUNDARIES = {
    "PROMOTER_MIN": 9,
    "PASSIVE_MIN": 7,
    "PASSIVE_MAX": 8,
    "DETRACTOR_MAX": 6
}

# Confidence Levels
CONFIDENCE_LEVELS = {
    "HIGH": "high",
    "MEDIUM_HIGH": "medium-high",
    "MEDIUM": "medium",
    "LOW": "low"
}

# Confidence Thresholds
CONFIDENCE_THRESHOLDS = {
    "HIGH_MIN_SAMPLES": 150,
    "HIGH_MIN_EFFECTIVE_RATE": 0.7,
    "MEDIUM_HIGH_MIN_SAMPLES": 80,
    "MEDIUM_HIGH_MAX_SAMPLES": 120,
    "MEDIUM_HIGH_MIN_EFFECTIVE_RATE": 0.6,
    "MEDIUM_MIN_SAMPLES": 30,
    "LOW_MAX_SAMPLES": 30,
    "LOW_MAX_EFFECTIVE_RATE": 0.3
}

# Memory Limits (in MB)
MEMORY_LIMITS = {
    "PASS1_FOUNDATION": 512,
    "PASS2_ANALYSIS": 1024,
    "PASS3_CONSULTING": 768,
    "LARGE_DATASET_THRESHOLD": 1000,
    "CHUNK_SIZE": 200
}

# Timeout Settings (in seconds)
TIMEOUTS = {
    "AGENT_DEFAULT": 60,
    "WORKFLOW_TOTAL": 300,
    "LLM_CALL": 30,
    "CHECKPOINT_SAVE": 10
}

# Retry Settings
RETRY_SETTINGS = {
    "MAX_RETRIES": 3,
    "INITIAL_DELAY": 2,
    "EXPONENTIAL_BASE": 2,
    "MAX_DELAY": 60
}

# Chinese Invalid Response Patterns
INVALID_RESPONSE_PATTERNS = [
    r'^无$', r'^没有$', r'^不知道$', r'^没意见$',
    r'^无所谓$', r'^随便$', r'^一般$', r'^说不清$',
    r'^\s*无\s*$', r'^\s*没有\s*$', r'^\s*不知道\s*$',
    r'^(.)\1{3,}$',  # Same character repeated 4+ times
    r'^[a-zA-Z]{1,3}$',  # Single letters
    r'^\d+$'  # Pure numbers without context
]

# Dairy Industry Keywords (Chinese)
DAIRY_KEYWORDS = [
    "牛奶", "酸奶", "奶粉", "奶酪", "黄油", "奶油",
    "伊利", "金典", "安慕希", "舒化", "优酸乳", "味可滋",
    "蒙牛", "光明", "君乐宝", "三元",
    "口感", "营养", "品质", "新鲜", "健康", "有机"
]

# Product Categories
YILI_PRODUCTS = [
    "安慕希", "金典", "舒化", "优酸乳",
    "味可滋", "QQ星", "伊小欢", "巧乐兹"
]

COMPETITOR_BRANDS = [
    "蒙牛", "光明", "君乐宝", "三元"
]

# Report Sections
REPORT_SECTIONS = [
    "executive_summary",
    "nps_metrics",
    "confidence_assessment",
    "segment_analysis",
    "text_insights",
    "driver_analysis",
    "dimensional_analysis",
    "strategic_recommendations",
    "risk_assessment",
    "action_plan"
]

# Insight Limits
INSIGHT_LIMITS = {
    "B1_PROMOTER": 4,
    "B2_PASSIVE": 3,
    "B3_DETRACTOR": 3,
    "B6_B7_B8_DIMENSION": 3,
    "C1_STRATEGIC": 3,
    "C2_PRODUCT": 4,
    "C3_MARKETING": 3,
    "C4_RISK": 3,
    "C5_EXECUTIVE_SUMMARY": 7
}