# Changelog

## v0.0.1 — Initial v0-compatible API

Release date: 2025-09-10

- feat(api): add v0-compatible endpoints `POST /nps-report-v0` and `/nps-report-v0/execute` that accept the wrapper payload `{ "input": { "input_text_0": "<JSON or object>" } }` and return Chinese bullet-point conclusions in `output_text_0`.
- docs: add `API_V0.md` documenting request/response, generation rules, and examples.
- ops: add health/meta endpoints `GET /healthz` and `GET /version`.
- ux: declare request body in FastAPI so Swagger UI (`/docs`) supports Try it out.
- chore: add `.gitignore` for caches and local env files.

Notes
- This release targets compatibility with existing API consumers without breaking changes.
- If port 7000 conflicts on macOS (ControlCenter/AirPlay), run with another port (e.g., 7070): `uvicorn api:app --reload --port 7070`.
