# Requirements Document

## Introduction

This document outlines the requirements for implementing the NPS V3 API core functionality. The focus is on developing the 14-agent multi-layer analysis system that generates enhanced JSON and HTML reports as a clean, independent implementation.

**Core Scope:**
- Multi-agent analysis architecture (Foundation → Analysis → Consulting)
- Dynamic question recognition and processing
- Enhanced confidence grading system
- Dual-format output generation (JSON + HTML)
- Independent V3 development (no V2 constraints)
- Essential error handling and validation

**Out of Scope for V1:**
- Enterprise integrations, real-time processing, advanced security, cultural intelligence, and platform-level features will be addressed in future iterations after core API accuracy is validated.

## Requirements

### Requirement 1: Multi-Agent Architecture Implementation

**User Story:** As a system architect, I want to implement a 14-agent multi-layer architecture, so that the system can provide specialized, high-quality analysis across foundation, analysis, and consulting domains.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL create three distinct agent layers: Foundation (A0-A3), Analysis (B1-B9), and Consulting (C1-C5)
2. WHEN processing a request THEN Foundation agents SHALL execute sequentially: A0→A1→A2→A3
3. WHEN Foundation layer completes THEN Analysis agents B1-B8 SHALL execute in parallel with B9 coordinating results
4. WHEN Analysis layer completes THEN Consulting agents C1-C4 SHALL execute in parallel with C5 providing final coordination
5. WHEN any agent fails THEN the system SHALL log the error and continue with degraded functionality
6. WHEN token limits approach THEN the system SHALL implement LangGraph batch execution to prevent overflow

### Requirement 2: Dynamic Question Recognition and Processing

**User Story:** As a data analyst, I want the system to automatically recognize question types regardless of order, so that surveys with varying question sequences can be processed accurately.

#### Acceptance Criteria

1. WHEN receiving survey data THEN the system SHALL identify Q1 (NPS scoring) through numerical rating patterns (0-10 scale)
2. WHEN processing open-ended questions THEN the system SHALL classify them as positive/negative based on semantic analysis of question stems
3. WHEN question classification is uncertain THEN the system SHALL use statistical analysis of response patterns by score group
4. WHEN Q2/Q3/Q4/Q5 cannot be identified THEN the system SHALL log a warning and continue with available data
5. WHEN processing multi-choice questions THEN the system SHALL extract them for driving factor analysis

### Requirement 3: Enhanced Confidence Assessment System

**User Story:** As a business stakeholder, I want clear confidence indicators for all insights, so that I can make informed decisions based on data reliability.

#### Acceptance Criteria

1. WHEN sample size < 30 OR effective rate < 30% THEN the system SHALL assign confidence level "low"
2. WHEN sample size 30-99 OR (100-149 AND effective rate < 70%) THEN the system SHALL assign confidence level "medium"
3. WHEN sample size 100±20 AND effective rate ≥ 60% THEN the system SHALL assign confidence level "medium-high"
4. WHEN sample size ≥ 150 AND effective rate ≥ 70% THEN the system SHALL assign confidence level "high"
5. WHEN confidence is "low" THEN strategic insights SHALL be limited to data collection recommendations
6. WHEN distribution is > 90% concentrated in single score THEN the system SHALL generate SKEWED_DISTRIBUTION_WARNING

### Requirement 4: Comprehensive Input Validation and Error Handling

**User Story:** As a system administrator, I want robust input validation and error handling, so that the system provides clear feedback and graceful degradation.

#### Acceptance Criteria

1. WHEN required fields are missing THEN the system SHALL return INPUT_SCHEMA_ERROR with specific field details
2. WHEN sample size is insufficient THEN the system SHALL generate INSUFFICIENT_SAMPLE_WARNING
3. WHEN text quality is poor (>50% invalid responses) THEN the system SHALL generate TEXT_QUALITY_WARNING
4. WHEN dimensional data is missing THEN the system SHALL generate DIMENSION_DATA_GAP warning
5. WHEN benchmark data is unavailable THEN the system SHALL generate BENCHMARK_MISSING warning
6. WHEN any error occurs THEN error details SHALL be included in both JSON and HTML outputs

### Requirement 5: Agent-Specific Analysis Implementation

**User Story:** As an analysis expert, I want each agent to perform specialized analysis within its domain, so that insights are comprehensive and high-quality.

#### Acceptance Criteria

**Foundation Layer:**
1. WHEN A0 processes data THEN it SHALL standardize input format and identify invalid responses
2. WHEN A1 calculates NPS THEN it SHALL generate promoter/passive/detractor distributions with statistical confidence
3. WHEN A2 assesses confidence THEN it SHALL apply the enhanced 4-level grading system (low/medium/medium-high/high)
4. WHEN A3 monitors quality THEN it SHALL generate data completeness reports and gap identification

**Analysis Layer:**
5. WHEN B1-B3 analyze segments THEN they SHALL generate insights for promoters/passives/detractors respectively
6. WHEN B4 processes text THEN it SHALL perform topic clustering and sentiment analysis with Chinese language support
7. WHEN B5 analyzes drivers THEN it SHALL create importance vs satisfaction matrix from multi-choice questions
8. WHEN B6-B8 process dimensions THEN they SHALL analyze product/geographic/channel/demographic differences
9. WHEN B9 coordinates THEN it SHALL synthesize and prioritize insights from B1-B8

**Consulting Layer:**
10. WHEN C1-C4 generate recommendations THEN they SHALL provide strategic, product, marketing, and risk guidance respectively
11. WHEN C5 synthesizes THEN it SHALL create executive summary with 5-7 prioritized recommendations

### Requirement 6: Dual-Format Output Generation

**User Story:** As an end user, I want reports in both structured JSON and visual HTML formats, so that I can integrate data programmatically and share results visually.

#### Acceptance Criteria

1. WHEN analysis completes successfully THEN the system SHALL generate structured JSON with all agent outputs
2. WHEN generating JSON THEN it SHALL include metadata: confidence level, sample stats, processing timestamps, warnings
3. WHEN analysis completes successfully THEN the system SHALL generate single-file HTML report using Tailwind CSS
4. WHEN generating HTML THEN it SHALL include: executive summary, NPS metrics, confidence indicators, key insights, and agent-specific sections
5. WHEN confidence is below "high" THEN both outputs SHALL include prominent confidence warnings
6. WHEN errors occur THEN both formats SHALL include error details and partial results where available

### Requirement 7: V2 Code Preservation and V3 Independent Development

**User Story:** As a system maintainer, I want V3 to be developed independently without breaking existing V2 functionality, so that legacy clients continue working while new clients benefit from V3 improvements.

#### Acceptance Criteria

1. WHEN V3 development occurs THEN no existing V2 code SHALL be modified or removed
2. WHEN V3 is deployed THEN all existing V2 endpoints SHALL continue to function exactly as before
3. WHEN V3 implements new features THEN they SHALL be designed optimally without V2 format constraints
4. WHEN routing requests THEN V2 and V3 SHALL use completely separate endpoints (e.g., `/nps-report-v2` vs `/nps-report-v3`)
5. WHEN V3 uses different input/output formats THEN it SHALL be designed for optimal usability without legacy compatibility requirements
6. WHEN V3 has issues THEN they SHALL not impact V2 functionality in any way

### Requirement 8: Performance and Reliability Requirements

**User Story:** As a performance engineer, I want the system to handle requests efficiently and reliably, so that response times remain acceptable.

#### Acceptance Criteria

1. WHEN processing standard requests THEN response time SHALL be < 30 seconds for 95% of requests
2. WHEN multiple agents execute THEN the system SHALL implement proper concurrency controls
3. WHEN LLM calls are made THEN the system SHALL implement timeout (60s) and retry (3 attempts) mechanisms
4. WHEN system resources are constrained THEN the system SHALL implement graceful degradation
5. WHEN errors occur THEN the system SHALL maintain detailed logs for debugging
6. WHEN processing large datasets (>1000 responses) THEN the system SHALL handle them without memory issues

### Requirement 9: Chinese Language Processing Support

**User Story:** As a business analyst, I want the system to understand Chinese language nuances and dairy industry context, so that insights are relevant and accurate.

#### Acceptance Criteria

1. WHEN analyzing Chinese text THEN the system SHALL handle sentiment analysis with appropriate cultural context
2. WHEN processing dairy product feedback THEN it SHALL map topics to relevant categories: 口感, 包装, 价格, 健康, 创新, 服务
3. WHEN generating insights THEN they SHALL reference appropriate product lines: 金典, 安慕希, 舒化, etc.
4. WHEN detecting invalid responses THEN it SHALL recognize Chinese patterns: "无", "不知道", "没有"
5. WHEN creating word clouds THEN it SHALL use Chinese text segmentation and meaningful terms
6. WHEN generating recommendations THEN they SHALL consider Chinese market context and business terminology

### Requirement 10: Testing and Quality Assurance

**User Story:** As a QA engineer, I want comprehensive test coverage to ensure system reliability and accuracy.

#### Acceptance Criteria

1. WHEN running unit tests THEN coverage SHALL be ≥ 80% across all agent implementations
2. WHEN testing with sample data THEN the system SHALL handle edge cases: empty responses, single scores, extreme distributions
3. WHEN testing integration THEN both V2 and V3 pathways SHALL be validated with identical inputs
4. WHEN testing Chinese text THEN validation SHALL include mixed content, empty fields, and standard responses
5. WHEN testing performance THEN the system SHALL meet response time requirements under simulated load
6. WHEN deploying changes THEN automated smoke tests SHALL verify core agent functionality