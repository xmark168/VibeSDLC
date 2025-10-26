# Repository Guidelines

## Project Structure & Module Organization
- Services: `services/management-service` (FastAPI), `services/ai-agent-service` (FastAPI), `services/api-gateway`.
- Frontend: `frontend` (React + TypeScript). Static assets in `frontend/public/assets`.
- Tests: `services/management-service/tests`, `services/ai-agent-service/app/tests`, `frontend/tests`.
- Scripts: `scripts/*.sh` for local run, build, and deploy.

## Build, Test, and Development Commands
- Frontend: `cd frontend && npm install && npm run dev` (serve), `npm run build`, `npm run test:e2e`.
- Management Service: `bash services/management-service/scripts/test.sh` (pytest + coverage), `bash .../lint.sh` (mypy + ruff), `bash .../format.sh` (ruff fix + format).
- AI Agent Service: `cd services/ai-agent-service && pytest`; run API locally: `uvicorn app.api.main:app --reload --port 8001`.
- All services (convenience): `bash scripts/start-microservices.sh`. Individual: `bash scripts/run-frontend.sh`, `bash scripts/run-management-service.sh`, `bash scripts/run-ai-agent-service.sh`.

## Coding Style & Naming Conventions
- Python: format with `ruff format`; lint with `ruff check`; types via `mypy` (management-service). Snake_case for functions/modules; PascalCase for classes.
- TypeScript/React: `npm run lint` (Biome) and `npm run typecheck` (tsc). Components and files in PascalCase (e.g., `UserCard.tsx`).
- Tests: Python `test_*.py`; Playwright `*.spec.ts`.

## Testing Guidelines
- Python: `coverage run -m pytest` then `coverage report` (HTML via `coverage html`). Keep unit tests under each service’s `tests` folder.
- Frontend: Playwright E2E with `npm run test:e2e` (or `npm run test:e2e:ui`). Co-locate helpers under `frontend/tests/utils`.
- Prefer deterministic tests; name by feature or route (e.g., `tests/api/routes/test_users.py`).

## Commit & Pull Request Guidelines
- Commit messages: Conventional Commits (`feat:`, `fix:`, `chore:`, `test:`, `docs:`). Use imperative tone and scoped changes.
- PRs include description, linked issues, reproduction steps, expected behavior, and screenshots for UI.
- Ensure CI parity: typecheck, lint, build, and tests pass for changed areas.

## Security & Configuration Tips
- Use `.env` (see `README.md`). Do not commit secrets. Typical keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and Postgres/Kafka settings.
- Default dev ports: Frontend `5173`, Management `8000`, AI Agent `8001`. Adjust via `uvicorn` args or service configs if needed.
