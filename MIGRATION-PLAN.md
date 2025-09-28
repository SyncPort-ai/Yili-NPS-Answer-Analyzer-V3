# Migration Plan

## Overview
This document captures the structure and workflow of the current Vite + React + Tailwind repository so that a Python-based implementation can mirror the same user experience and data-flows. The focus is on site navigation, shared layout patterns, feature modules, and the analytical data model used across the app.
目标实现保持全中文界面、Tailwind 风格与响应式体验，并采用 FastAPI 输出 HTML 页面与 JSON API。

## Navigation Tree
```
/
├─ / (NPS概览 Dashboard)
├─ /projects (项目管理)
├─ /surveys (问卷设计)
├─ /analytics (数据分析)
├─ /insights (专家洞察)
├─ /consumers (消费者档案)
├─ /calendar (调研日历)
├─ /reports
│  ├─ list view
│  └─ /reports/:reportId (Analytical Report detail)
├─ /settings (系统设置)
├─ /learn (学习中心)
└─ * → NotFound
```

## Menu → Page Map
| 侧边菜单 | 路由 | 核心能力 |
| --- | --- | --- |
| NPS概览 | `/` | 仪表盘：指标卡、项目一览、专家洞察 |
| 项目管理 | `/projects` | 项目进度、负责人、阶段追踪 |
| 问卷设计 | `/surveys` | 问卷模板库、AI生成、导入工具 |
| 数据分析 | `/analytics` | 多维度趋势、产品/区域对比图表 |
| 专家洞察 | `/insights` | 洞察卡片、行动建议、跨页跳转 |
| 消费者档案 | `/consumers` | Persona 画像、细分指标、数据导入 |
| 调研日历 | `/calendar` | 调研排期、提醒与创建入口 |
| 报告中心 | `/reports` | 报告列表、生成器、详情阅览 |
| 系统设置 | `/settings` | 账号与工作区配置 |
| 学习中心 | `/learn` | NPS 方法论教育与资源库 |

## Shared Layout & Providers
- `src/main.tsx` mounts the React tree with Tailwind styles applied globally.
- `src/App.tsx` wraps routing with `QueryClientProvider`, tooltip/toast providers, and declares the `BrowserRouter` routes.
- `src/components/layout/Layout.tsx` owns the chrome: collapsible sidebar, sticky header, main content slot.
- Header (`src/components/layout/Header.tsx`) exposes notifications, search, user menu, and the mobile drawer toggle.
- Sidebar (`src/components/layout/Sidebar.tsx`) defines the navigation items above; should be the single source of truth when porting routes.

## Feature Modules
- Dashboard widgets live in `src/components/dashboard/` (hero CTA, KPI cards, project cards, quick actions).
- Chart primitives in `src/components/charts/` wrap Recharts for trend, product, regional, and demographic visuals; they currently consume static arrays within each component.
- Report-specific UI (`src/components/reports/`) contains the detailed analytical report view and the modal-driven report generator workflow.
- Design system components (buttons, cards, tabs, inputs, etc.) reside in `src/components/ui/`; this can be replicated or mapped to the target Python front-end toolkit.
- Utility hooks (`src/hooks/use-toast.ts`, `src/hooks/use-mobile.tsx`) and helper functions (`src/lib/utils.ts`) support layout responsiveness and toasts.

## Page Specifications
- `/` (`src/pages/Index.tsx`): renders Dashboard module with hero, KPI metrics, project grid, quick actions, expert insights.
- `/projects` & `/surveys`: management tables with status chips, progress bars, action buttons linking to Reports and Analytics.
- `/analytics` (`src/pages/Analytics.tsx`): metrics tiles + tabbed charts + recommendation panels; relies on all chart modules.
- `/insights` & `/learn`: curated knowledge center cards, tags, and cross-links to reports/projects.
- `/consumers`: persona cards, segmentation stats, import CTA linking to surveys.
- `/calendar`: schedule tiles for upcoming research, quick filters.
- `/reports`: list dashboard of report stats, filterable cards, and a “Generate Report” modal. Navigates to `/reports/:reportId` to render `AnalyticalReport` detail.
- `/settings`: tabbed workspace/settings preferences.
- `NotFound`: fallback route for unmatched URLs.

## Data & Reports
- `src/data/mockReports.ts` defines the `AnalyticalReport` interface plus nested constructs for recommendations, insights, benchmarks, segment analysis, trend analysis, competitive intel, action plans, and risk assessments.
- Exports `mockAnalyticalReports`, `industryInsights`, and `competitiveAnalysis`, which power the Reports and Insights pages.
- The report list in `src/pages/Reports.tsx` contains metadata cards linking to mock IDs; ensure the Python backend serves equivalent structures.

## 页面布局模块图
```
首页 / (Dashboard)
├─ 顶部横幅（品牌CTA + 快捷按钮）
├─ 核心指标网格（NPS得分、推荐者比例等）
├─ 项目卡片栅格（状态、进度、报告链接）
├─ 快捷操作卡片（跳转 surveys / consumers / reports）
└─ 专家洞察列表（重点建议卡片）

项目管理 /projects
├─ 页面标题栏（筛选、创建按钮）
├─ 项目统计卡片（总数、活跃数等）
└─ 项目表格（项目名称、负责人、阶段、CTA）

问卷设计 /surveys
├─ 模板库网格（分类、标签、AI推荐）
├─ 问卷状态统计
└─ 行动栏（新建问卷、导入、AI生成）

数据分析 /analytics
├─ 指标概览卡片（整体NPS、推荐者等）
├─ Tab 切换
│  ├─ 趋势分析 → NPSTrendChart
│  ├─ 产品对比 → ProductNPSChart
│  ├─ 区域表现 → RegionalPerformanceChart
│  └─ 用户画像 → DemographicChart
└─ 下方双栏模块
   ├─ 驱动因子排行
   └─ 行动建议列表

专家洞察 /insights
├─ 顶部搜索/筛选区域
├─ 洞察卡片栅格（标签、影响度）
└─ 推荐行动区（链接至 reports / projects）

消费者档案 /consumers
├─ Persona 卡片
├─ 指标统计图（满意度、忠诚度）
└─ 数据操作区（导入、同步、跳转问卷）

调研日历 /calendar
├─ 视图切换（周/月）
├─ 事件日历（颜色区分项目类型）
└─ 快捷创建与提醒设置

报告中心 /reports
├─ 顶部操作栏（筛选、学习中心、生成报告）
├─ 指标卡片组（总报告、下载量等）
├─ 分类筛选块
├─ 报告卡片列表（含状态、下载、查看按钮）
└─ 报告详情 /reports/:reportId
   ├─ 报告抬头（标签、元数据、操作按钮）
   ├─ 执行摘要
   ├─ 关键发现
   ├─ 核心数据洞察（图表、数值）
   ├─ 商业建议 / 行动计划
   ├─ 行业对标 / 竞争情报
   ├─ 风险评估
   └─ 附录/下载链接

系统设置 /settings
├─ Tab 导航（个人、通知、团队、API 密钥）
└─ 配置表单模块

学习中心 /learn
├─ 顶部 Banner（课程 CTA）
├─ 分类标签
└─ 课程/文章卡片网格

NotFound
└─ 404 信息块 + 返回首页按钮
```

## Report Generator Dialog
- Triggered from `/reports` via `ReportGenerator` and must keep parity with the modal shown at `http://localhost:8080/reports`.
- Form fields: report title (placeholder `例如：2024年Q1伊利NPS综合分析报告`), description textarea, time-range select (`上月`, `上季度`, `近6个月`, `过去一年`, `年初至今`).
- Report types (radio-style buttons): `季度报告`, `品牌分析`, `产品测试`, `竞品分析`, `趋势分析`, `人群分析`. Treat these as report templates or AI agent roles.
- Content modules (checkboxes) define output sections: `NPS核心数据`, `人群细分`, `区域分析`, `产品表现`, `趋势分析`, `商业洞察`, `行业对标`, `改进建议`.
- Migration must persist this structure so downstream automation can map selections to the correct analytical service or agent pipeline.

## Migration Notes
1. Rebuild the layout shell (providers, header, sidebar) first to retain consistent navigation UX.
2. Port design-system primitives or map to a Python-friendly UI library before recreating higher-level widgets.
3. Externalize chart data to APIs while preserving the JSON shape expected by the current charts.
4. Migrate workflow-heavy modules one by one: Dashboard → Analytics → Reports → auxiliary pages.
5. Translate the analytical report data model directly; Python services should emit the same nested structures consumed by `AnalyticalReport.tsx`.
6. Replace toast/hooks functionality with framework equivalents (e.g., Django messages, HTMX events) while keeping trigger points intact.

## FastAPI 逻辑架构
- **展示层**：FastAPI + Jinja2/HTMX/前端组件，保持 Tailwind 样式与中文界面；可按需继续使用 Vite 前端，通过 API 获取数据。
- **路由层**：`APIRouter` 对应当前导航树，提供 HTML 页面与 JSON 接口（如 `/api/analytics/trend` 返回图表数据）。
- **业务层**：封装 NPS 问卷解析、指标计算、AI 洞察生成（调用 LLM 或规则引擎），输出符合现有 TypeScript 接口的结构。
- **数据层**：持久化调查结果、报告档案、教育内容与操作日志；建议 PostgreSQL + SQLModel/SQLAlchemy。
- **集成层**：支持文件上传（问卷 CSV）、任务队列（如 Celery）用于报告生成与异步分析。

## FastAPI 门户需求
- 首页即综合仪表盘：最近调查概览、跨调查对比、系统日志、重要通知与教育入口。
- 报告档案库：可按项目/时间/标签筛选，支持预览、下载、权限控制。
- API 核心职责：接收问卷回答数据与配置，返回分析 JSON + HTML 片段（报告、图表、洞察）。
- 日志与跨报告分析：展示处理历史、错误提示、对多个调查的趋势比较。
- NPS 方法论教育区：课程列表、文档下载、常见问题，便于新成员学习。
- 全站响应式与无障碍优化：移动端优先布局、ARIA 标签、键盘导航。
