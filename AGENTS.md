# Repository Guidelines

## Project Structure & Module Organization
- `api.py`: FastAPI entrypoint and route definitions; exposes UI at `/` and docs at `/docs`.
- `nps_report_v1/`: multi-agent workflow orchestrations (`workflow.py`, `agents.py`, `state.py`).
- `nps_report_v2/`: dual-input processors for raw/preprocessed surveys plus knowledge managers.
- Core analysis modules: `opening_question_analysis.py`, `cluster.py`, `llm.py`, `prompts.py`.
- UI & assets: `templates/`, `static/`; data & outputs: `data/`, `outputs/`, `logs/`; tests in `tests/`.
- Reference artifacts: `demo_v1.py`, `README.md`, `NPS-REPORT-ANALYZER-API-V1.0.md`.

## Build, Test, and Development Commands
- `make install`: install Python dependencies from `requirements.txt`.
- `make dev PORT=7070`: launch FastAPI app with autoreload at the given port.
- `make run` or `uvicorn api:app --reload --port 7070`: run server manually.
- `pytest -q`: execute automated test suite with FastAPI `TestClient`.
- `make docker-build IMAGE=nps-report-analyzer TAG=v0.0.1` + `make docker-run PORT=7070`: build/run containerized service.

## Coding Style & Naming Conventions
- Target Python 3.10+, 4-space indentation, ≤100 char lines, UTF-8.
- Use `snake_case` for modules/functions, `PascalCase` for classes, `UPPER_SNAKE_CASE` constants.
- Prefer explicit FastAPI models and JSON-serializable responses; add docstrings for public APIs.
- Keep workflows modular and avoid circular imports; inject dependencies for external clients.

## Testing Guidelines
- Tests live under `tests/test_*.py`; name cases `test_*` and rely on `pytest`.
- Use `fastapi.testclient.TestClient` for route coverage; avoid real external calls.
- For deterministic assertions pass `{"response_mode": "demo"}` in request payloads.
- Add regression tests whenever modifying agents, clustering, or prompt logic.

## Commit & Pull Request Guidelines
- Follow Conventional Commits (`feat:`, `fix:`, `docs:`, `chore:`) in imperative mood.
- PRs should list purpose/scope, linked issues, testing commands, and screenshots for UI changes.
- Mention new env vars or config adjustments; ensure `pytest` passes before requesting review.

## Security & Configuration Tips
- Copy `.env.example` to `.env`; never commit keys (e.g., `PRIMARY_LLM`, `OPENAI_API_KEY`, `YILI_*`).
- Logs flow to `logs/app.log`; avoid logging sensitive survey data.
- Persist generated artifacts in `outputs/` and sanitize free-text inputs before clustering.
