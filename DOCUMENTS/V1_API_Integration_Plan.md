V1 API Integration – Multi‑Agent NPS Workflow

Purpose
- Expose the demo multi‑agent NPS analysis (YiLi_NPS_Insights_demo) as v1 API endpoints in nps-report-analyzer, so the UI can consume real computed insights instead of static mocks.

Endpoint
- POST `/api/v1/nps/workflow/analyze`
  - Runs the LangGraph-based multi‑agent workflow from the demo.
  - Dynamically loads `NPSAnalysisWorkflow` from `YiLi_NPS_Insights_demo/src/nps_analysis/workflow.py` if present in the repo.

Input Schema (JSON)
- `survey_responses` [required]:
  - Array of responses: `{ score: 0..10, comment?: string, customer_id?: string, timestamp?: string, region?: string, age_group?: string }`
- `metadata` [optional]: any object
- `optional_data` [optional]:
  - `yili_products_csv` [optional]: array of `{ product_name: string, category?: string, product_line?: string, variations?: string[] }`
- `include_html_report` [optional]: boolean; when true, includes `html_report_string` in the response (can be large).

Output (summary)
- `nps`: `{ score, breakdown, distribution, regional, total_responses }`
- `qual`: `{ analysis_method, comment_count, top_themes[], product_mentions{}, sentiment_overview{}, emotions_detected{} }`
- `context`: `{ product_mapping{}, competitor_analysis{}, market_trends[], business_insights[] }`
- `report`: `{ executive_summary, quality_report, html_report_string? }`
- `flags`: agent completion flags

Notes & Behavior
- If the demo workflow module is not found, returns 501 (not implemented) with guidance to place the demo at `YiLi_NPS_Insights_demo/`.
- The Qual agent prefers “Yili‑only” gateway by default (`YILI_ONLY_MODE=true`); in restricted environments, the agent falls back to an offline baseline analysis when gateway calls fail.
- No external network dependency is required for the quantitative and context steps.
- Dependencies (`langgraph`, `pandas`, etc.) are already present in `requirements.txt`.

Example Request
{
  "survey_responses": [
    { "score": 9, "comment": "安慕希口感好", "region": "北京", "age_group": "25-34" },
    { "score": 3, "comment": "金典偏贵", "region": "上海", "age_group": "35-44" },
    { "score": 8, "comment": "舒化奶适合乳糖不耐", "region": "广州", "age_group": "18-24" }
  ],
  "metadata": { "survey_date": "2024-01-15" },
  "optional_data": {
    "yili_products_csv": [
      { "product_name": "安慕希", "category": "酸奶", "product_line": "高端" },
      { "product_name": "金典", "category": "牛奶", "product_line": "高端" }
    ]
  }
}

Example Response (abridged)
{
  "nps": { "score": 33.33, "breakdown": { ... }, "regional": { ... } },
  "qual": { "analysis_method": "fallback|yili_ai_*", "top_themes": [ ... ], "product_mentions": { ... } },
  "context": { "business_insights": [ ... ] },
  "report": { "executive_summary": { ... } },
  "flags": { "ingestion_complete": true, "quant_complete": true, "qual_complete": true, "context_complete": true, "report_complete": true }
}

Operational Considerations
- To enable rich qualitative analysis via Yili gateway, set env vars: `YILI_APP_KEY` and `YILI_GATEWAY_URL`. Otherwise, fallback analysis is applied automatically.
- Large HTML report strings can be included by setting `include_html_report=true`, but prefer on-demand retrieval to keep payloads small.

Next Steps
- Wire frontend to call `/api/v1/nps/workflow/analyze` for Analytics and Reports tabs.
- If desired, add narrower endpoints (e.g., `/api/v1/nps/summary`, `/api/v1/nps/by-region`) that proxy fields from the workflow output for lightweight dashboards.

