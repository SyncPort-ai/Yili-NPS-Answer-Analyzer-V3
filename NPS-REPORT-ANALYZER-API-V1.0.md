# NPS Report Analyzer – API v1.0

Full-state NPS analysis API using the integrated multi‑agent workflow (demo core). Returns the entire final state and an embedded HTML report by default. Persists results to the project folder.

- Base endpoint: `POST /nps-report-v1`
- Sample payload: `GET /api/v1/nps/sample` (reads `data/V1-sample-input.json`)
- Health: `GET /healthz`

## Request Body

- `survey_responses` (required): list of objects
  - `score` (int)
  - `comment` (string, optional)
  - `customer_id` (string, optional)
  - `timestamp` (string, optional)
  - `region` (string, optional)
  - `age_group` (string, optional)
- `metadata` (object, optional)
- `optional_data` (object, optional)
  - supports `yili_products_csv`: list of product rows
- `persist_outputs` (boolean, optional, default true)
  - Writes JSON to `outputs/results/v1_*.json`
  - Writes HTML to `outputs/reports/v1_*.html`

## Response (Full State)

- Full final state containing all intermediate and final results plus the HTML report string:
  - `raw_responses`, `clean_responses`
  - `nps_results`, `qual_results`, `context_results`
  - `final_output` (contains `executive_summary`, `quality_assessment`, `next_steps`, and `html_report_string`)
  - `errors` (if any), plus debug trace fields such as `route_log`, `step_counter` when present

Example (abridged):
```
{
  "nps_results": { ... },
  "qual_results": { ... },
  "context_results": { ... },
  "final_output": {
    "executive_summary": { ... },
    "quality_assessment": { ... },
    "next_steps": [ ... ],
    "html_report_string": "<!DOCTYPE html>..."
  }
}
```

## Examples

1) Full-state run (default) — pass JSON payload inline (no file upload)
```
curl -X POST http://localhost:7070/nps-report-v1 \
  -H 'Content-Type: application/json' \
  -d '{
    "survey_responses": [
      {"score": 9, "comment": "安慕希口感很好", "region": "华东"},
      {"score": 3, "comment": "金典有怪味", "region": "华北"},
      {"score": 8, "comment": "舒化奶帮助乳糖不耐", "region": "华南"}
    ]
  }'
```

Or, use the built‑in sample provider (still JSON payload; no file attachment):
```
curl -s http://localhost:7070/api/v1/nps/sample \
| curl -X POST http://localhost:7070/nps-report-v1 \
    -H 'Content-Type: application/json' \
    -d @-
```

2) Get the default sample
```
curl http://localhost:7070/api/v1/nps/sample
```

## HTML Report (Charts & Sections)

- Charts use CDN by default:
  - `<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>`
- To serve locally (optional), set `PUBLIC_BASE_URL` (e.g., `http://localhost:7070`) and place Chart.js at `static/thirdparty/chart.umd.min.js`.
- If Chart.js is unavailable, the report falls back to textual summaries under chart areas.

Sections included by default:
- Dashboard tiles (NPS score, sample count, data quality, business insights count)
- 🔍 执行摘要 (scope, NPS评估, 主要发现, 技术说明)
- 📊 关键指标一览 (promoters%, detractors%, quality score, theme count)
- 📊 NPS构成分析 (Chart.js doughnut)
- 🎯 关键主题分析 (top themes with mentions & sentiment)
- 💡 战略业务洞察 (up to 20 items; shows 建议行动; synthesized defaults added if none)
- 🧩 产品映射与表现 (table)
- 🧭 竞争情报 (summary; fixed competitor table: 蒙牛/光明/三元/君乐宝/飞鹤)
- 📈 市场趋势 (list)
- 🏁 区域NPS分布 (bar chart + table)
- 📋 质量评估报告 (grade, score, details line)

## Environment & Backends

- OpenAI as primary, Yili gateway as fallback (configurable via `.env`):
  - `PRIMARY_LLM`: `openai` (default) or `yili`
  - `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_TEMPERATURE`
  - `YILI_APP_KEY`, `YILI_GATEWAY_URL`
- Optional serving base for static assets:
  - `PUBLIC_BASE_URL` (e.g., `http://localhost:7070`)

## Persistence & Logs

- Persistence (default true):
  - JSON: `outputs/results/v1_*.json`
  - HTML: `outputs/reports/v1_*.html`
- Logs: `logs/app.log` (rotating) records AI calls and pipeline progress.

## Design Notes

- The workflow runs linearly (ingestion → quantitative → qualitative → context → report) to avoid recursive loops.
- A small, bounded critique/revision cycle runs iteratively (outside the graph) to improve quality without risking recursion.
- Qual and context outputs are normalized to stable shapes for downstream consumers.
- The report builder is robust: always returns an HTML string (falls back to a minimal HTML if enhanced generation encounters a data quirk).

## Troubleshooting

- Charts not visible offline? Use CDN (default) or set `PUBLIC_BASE_URL` and place Chart.js at `static/thirdparty/chart.umd.min.js`.
- Missing sections? The HTML includes synthesized defaults for strategic insights and chart fallbacks; ensure LLM backends are configured for richer content.
- If analysis appears thin, check `logs/app.log` for AI call status and `outputs/results/v1_*.json` for `errors` and trace fields.

## Sample Data (Example)

Input sample (used as Swagger example): `data/V1-sample-input.json` (copy content and pass as JSON payload; the API does not accept file uploads)

```
{ (abridged) 
  "survey_responses": [
    {
      "score": 9,
      "comment": "安慕希的口感很棒，浓稠香甜，包装也很精美。品质一如既往的好，会一直支持伊利！",
      "customer_id": "YL20240901001",
      "timestamp": "2024-09-01T10:30:00Z",
      "region": "华东",
      "age_group": "25-34"
    },
    {
      "score": 10,
      "comment": "金典牛奶是我们全家的选择，孩子特别爱喝。有机奶源，营养丰富，价格合理。强烈推荐给朋友们！",
      "customer_id": "YL20240901002",
      "timestamp": "2024-09-01T11:15:00Z",
      "region": "华北",
      "age_group": "35-44"
    },
    ...
  ]
}
```

Output sample (full-state JSON, abridged): `outputs/results/v1_20250911_042915.json`

```
{ (abridged)
  "raw_responses": [ ... ],
  "nps_results": { "nps_score": -13.33, "score_breakdown": { ... }, "regional_breakdown": { ... }, "total_responses": 15 },
  "qual_results": { "top_themes": [ ... ], "sentiment_overview": { ... }, "product_mentions": [ ... ], "emotions_detected": [ ... ], "comment_count": 6, "analysis_method": "yili_only" },
  "context_results": { "product_mapping": { ... }, "competitor_analysis": { ... }, "market_trends": [ ... ], "business_insights": [ ... ] },
  "final_output": {
    "executive_summary": { ... },
    "quality_assessment": { ... },
    "next_steps": [ ... ],
    "html_report_string": "<!DOCTYPE html>..."
  },
  "errors": [ ... ]
}
```
