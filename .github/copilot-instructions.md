<!-- Copilot / AI agent instructions for quick, productive edits in this repo -->
# Repo-specific guidance for AI coding assistants

This file gives compact, actionable guidance so an AI agent can be productive immediately.

1. Big picture
   - Monorepo with two primary apps: `backend/` (FastAPI + Python, DDD) and `frontend/` (React + TS + Vite).
   - `try and error api try/` contains standalone Node experiments — treat as sandbox; don't change core app behavior there.
   - AI logic and orchestration live under `backend/src/application/ai/` and `backend/src/infrastructure/ai/`.

2. Key entry points (read before editing behavior)
   - `backend/src/main.py` — app startup, middleware (tenant + CORS), router registration.
   - `backend/src/infrastructure/middleware/tenant_middleware.py` — tenant context extraction; all DB access must honor tenant context.
   - `backend/src/application/ai/agents/agent_factory.py` and `.../generators/adapter_generator.py` — where agents/tools and runtime adapters are produced.
   - Vector store: `backend/src/infrastructure/ai/vector_store/` (Chroma client and chunking). See `document_vector_store.py` and `document_chunker.py`.

3. Developer workflows & commands (use these exact commands)
   - Start backend (dev):
     cd backend; python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
   - Start frontend: cd frontend; npm run dev
   - Quick start (Windows): run `START.bat` from repository root.
   - Backend tests: cd backend; pytest tests/
   - Vector DB tests: cd backend; pytest tests/test_vector_db/
   - Create DB indexes / migrate vectors: cd backend; python scripts/create_indexes.py / python scripts/migrate_to_vector_db.py

4. Project-specific conventions (do not assume defaults)
   - Multi-tenant collection naming: use `tenant_{tenant_id}_*` prefix for tenant-specific collections.
   - Tenant context must be read from middleware helpers (do not parse headers manually). Use `TenantAwareRepository` pattern.
   - Generated adapters/tools live conceptually under `application/ai/generators/` and are cached in `infrastructure/ai/cache/` — prefer using generator APIs rather than editing generated output.
   - DEV_MODE behavior: if `DEV_MODE=True` the app bypasses auth and auto-assigns `test-tenant-001`. Avoid committing production auth changes.

5. AI & vector patterns to respect
   - Document parsing flow: `format_detector.py` → specific parser e.g. `parsers/openapi_parser.py` or `parsers/pdf_parser.py` → `workflow_analyzer.py` → `adapter_generator.py`.
   - Vector DB chunk size/overlap configured in `src/infrastructure/config/settings.py` (defaults: chunk_size≈1000, overlap≈200, top_k=3). Use these when querying.
   - Use `ChromaVectorStore` helper for similarity_search; prefer top_k=3 for quick answers.

6. Where to find environment keys & critical settings
   - `.env` / `backend/src/infrastructure/config/settings.py` define: `DEV_MODE`, `MONGODB_URL`, `VECTOR_DB_PERSIST_DIR`, `GOOGLE_GEMINI_API_KEY`, `MISTRAL_API_KEY`, and provider fallbacks.

7. Small, high-value editing rules (examples)
   - Adding a REST endpoint: create router in `presentation/rest/{feature}.py`, implement use case under `application/use_cases/{feature}`, register router in `src/main.py`.
   - Adding a parser: add class to `application/ai/parsers/` inheriting from `BaseParser` and register it in `format_detector.py`.
   - Access tenant id inside business logic via `get_tenant_context()` (do not access headers directly).

8. Agent and testing notes
   - Agents are produced by `agent_factory.py` and orchestrated by LangGraph (`application/ai/graphs/execution_graph.py`). When changing orchestration, check impacts on `application/ai/testing/` which depends on the same flows.
   - Autonomous testing utilities live in `application/ai/testing/` — changes to test generation/execution affect stored vectors and historical flow DB data.

9. Safety & non-goals
   - Do not remove tenant checks or disable DEV_MODE gating for production.
   - Generated code is sandboxed; prefer updating generator logic rather than directly patching generated adapters.

10. Helpful file examples to open first
   - `backend/src/main.py`, `backend/README.md`, `CLAUDE.md`, `backend/src/application/ai/understanding/comprehensive_api_analyzer.py`, and `backend/src/infrastructure/ai/vector_store/document_vector_store.py`.

If any section is unclear or you want more examples (e.g., exact code snippets for tenant helpers or vector queries), tell me which part to expand and I'll iterate.
