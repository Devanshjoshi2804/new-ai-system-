# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**CargoDham AI** is a multi-tenant AI-powered logistics integration platform that enables logistics partners to onboard by uploading API documentation. The AI automatically parses docs, understands workflows, generates dynamic adapters, and creates partner-specific agents for autonomous operations (booking, tracking, etc.).

## Architecture

This is a monorepo with three main components:

### Backend (FastAPI + Python)
- **Framework**: FastAPI with async/await
- **Database**: MongoDB (multi-tenant with collection-level isolation)
- **AI Stack**: LangChain, LangGraph, CrewAI, Mem0, Google Gemini, Mistral AI
- **Vector Store**: ChromaDB (for document embeddings) and Pinecone
- **Architecture Pattern**: Domain-Driven Design (DDD)
  - `domain/` - Business entities and value objects
  - `application/` - Use cases and AI orchestration
  - `infrastructure/` - Database, AI providers, external services
  - `presentation/` - REST APIs (GraphQL planned)

### Frontend (React + TypeScript)
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS
- **State**: Zustand + React Query
- **GraphQL**: Apollo Client (ready, not fully integrated)
- **Features**: Partner onboarding wizard, chat interface, integration viewer, testing dashboard

### Experimental Directory
- `try and error api try/` - Standalone Node.js experiments and prototypes (not part of main app)

## Common Commands

### Development

**Start Backend:**
```bash
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Start Frontend:**
```bash
cd frontend
npm run dev
```

**Quick Start (Windows):**
```bash
# From root directory
START.bat
```

### Testing

**Backend Tests:**
```bash
cd backend
pytest tests/
pytest tests/test_cargodham_apis.py  # Specific test file
```

**Frontend Tests:**
```bash
cd frontend
npm test
npm run lint
```

### Database

**MongoDB Scripts:**
```bash
cd backend
python scripts/create_indexes.py          # Create database indexes
python scripts/migrate_to_vector_db.py    # Migrate data to vector store
python scripts/vector_db_monitor.py       # Monitor vector DB status
```

### Build

**Frontend Build:**
```bash
cd frontend
npm run build
```

**Backend Type Check:**
```bash
cd backend
mypy src/
```

## Key Architecture Patterns

### Multi-Tenant Data Isolation

MongoDB collections are prefixed with `tenant_{partner_id}_` for complete data isolation:
- Shared collections: `partners`, `users`, `api_documentation`, `integration_configurations`
- Tenant-specific collections: `tenant_{id}_bookings`, `tenant_{id}_shipments`, etc.

**Middleware (`src/infrastructure/middleware/tenant_middleware.py`)** automatically extracts tenant context from:
1. `X-Tenant-ID` header
2. Subdomain
3. JWT token

All repository classes inherit from `TenantAwareRepository` which enforces tenant isolation at the query level.

### AI-Powered Document Parsing Pipeline

The system accepts multiple document formats:

**Structured formats** (direct parsing):
- OpenAPI/Swagger specs → `application/ai/parsers/openapi_parser.py`
- Postman collections → Handled by multi-parser

**Unstructured formats** (AI-powered):
- PDFs → `application/ai/parsers/pdf_parser.py` (uses Mistral OCR)
- Images → `application/ai/parsers/image_parser.py` (uses Google Gemini Vision)
- Plain text/Markdown → `application/ai/parsers/multi_parser.py`

**Parsing Flow:**
1. `format_detector.py` identifies document type
2. Appropriate parser extracts API information
3. `understanding/workflow_analyzer.py` learns business logic
4. `generators/adapter_generator.py` creates API client code
5. `agents/agent_factory.py` generates partner-specific AI agents

### Dynamic Code Generation

Runtime API adapter generation happens in `application/ai/generators/`:
- `adapter_generator.py` - Creates Python API client classes
- `tool_generator.py` - Generates LangChain tools for agents
- Generated code is validated and cached in `infrastructure/ai/cache/`

### AI Agent System

**Multi-Agent Architecture (CrewAI):**
- Booking agents
- Tracking agents
- Customer service agents
- Each partner gets custom agents based on their API capabilities

**Agent Factory** (`application/ai/agents/agent_factory.py`):
- Dynamically creates agents at runtime
- Loads partner-specific workflows from memory
- Uses generated tools for API integration

**Execution Flow** (`application/ai/graphs/execution_graph.py`):
- LangGraph state machine orchestrates multi-step operations
- Intent analysis → workflow selection → agent execution → response

### Vector Database Usage

Two vector stores are used:

**ChromaDB** (`infrastructure/ai/embeddings/`):
- Stores API documentation embeddings
- Enables semantic search over partner APIs
- Collection prefix: `api_docs_{partner_id}`

**Flow DB** (`settings.flow_db_path`):
- Stores test execution history
- Enables sequential learning from past tests
- Used for autonomous testing improvements

## Configuration

### Environment Variables

Backend uses `.env` file (see `infrastructure/config/settings.py`):

**Critical settings:**
- `DEV_MODE=True` - Bypasses authentication for testing
- `BYPASS_TENANT_CHECK=True` - Auto-assigns test tenant
- `MONGODB_URL` - MongoDB connection string
- `GOOGLE_GEMINI_API_KEY` - For AI text generation
- `MISTRAL_API_KEY` - For OCR/document understanding
- `GROQ_API_KEY` - For ultra-fast LLM inference

**Vector DB settings:**
- `VECTOR_DB_PERSIST_DIR` - ChromaDB storage path
- `FLOW_DB_PATH` - Flow vector store path
- `SEQUENTIAL_LEARNING=True` - Enable progressive test learning

### CORS Configuration

Frontend runs on `localhost:5173`, backend on `localhost:8000`. CORS is configured in `src/main.py` middleware.

## Important Code Patterns

### Adding a New REST Endpoint

1. Create router in `src/presentation/rest/{feature}.py`
2. Implement use case in `src/application/use_cases/{feature}/`
3. Add domain entities if needed in `src/domain/entities/`
4. Register router in `src/main.py`

Example structure:
```python
# presentation/rest/partners.py
@router.post("/partners/register")
async def register_partner(data: PartnerCreate):
    use_case = RegisterPartnerUseCase()
    return await use_case.execute(data)

# application/use_cases/partners/register_partner.py
class RegisterPartnerUseCase:
    async def execute(self, data: PartnerCreate):
        # Business logic here
        pass
```

### Adding a New AI Parser

1. Create parser class in `src/application/ai/parsers/`
2. Inherit from `BaseParser`
3. Implement `parse()` method returning `APISpecification`
4. Register in `format_detector.py`

### Working with Tenant Context

Always access tenant context via middleware:
```python
from src.infrastructure.middleware.tenant_middleware import get_tenant_context

async def my_function():
    tenant_ctx = get_tenant_context()
    tenant_id = tenant_ctx.tenant_id
    # Use tenant_id for data isolation
```

### Vector Store Queries

ChromaDB semantic search pattern:
```python
from src.infrastructure.ai.embeddings.chroma_client import ChromaVectorStore

vector_store = ChromaVectorStore(partner_id="partner_123")
results = await vector_store.similarity_search(
    query="How to create a booking?",
    k=3
)
```

## Frontend Architecture

### Feature-Based Organization

Each feature lives in `frontend/src/features/{feature}/`:
- `components/` - React components
- `hooks/` - Custom hooks
- `types/` - TypeScript types

**Main features:**
- `onboarding/` - Partner onboarding wizard (9 steps)
- `chat/` - AI chat interface with streaming
- `integration/` - View generated integrations
- `dashboard/` - Partner management dashboard
- `ocr/` - OCR document viewer

### API Client Pattern

API calls are centralized in `frontend/src/lib/api/`:
```typescript
// lib/api/partners.ts
export async function registerPartner(data: PartnerData) {
  return axios.post(`${API_BASE_URL}/api/partners/register`, data);
}
```

### State Management

- **Zustand** for global state (not heavily used yet)
- **React Query** for server state and caching
- **Local state** via `useState` for component-specific state

## Testing Strategy

### Backend Testing

Tests are in `backend/tests/`:
- `conftest.py` - Pytest fixtures (MongoDB, test client)
- `test_cargodham_apis.py` - Integration tests for main APIs

Run with tenant context in test mode:
```python
@pytest.fixture
def test_tenant_context():
    from src.infrastructure.middleware.tenant_middleware import tenant_context
    ctx = TenantContext(tenant_id="test-tenant-001")
    token = tenant_context.set(ctx)
    yield ctx
    tenant_context.reset(token)
```

### Autonomous Testing System

**Feature**: AI automatically tests API integrations

Located in `application/ai/testing/`:
- `autonomous_tester.py` - Executes tests based on documentation
- `test_sequence_executor.py` - Sequential test execution with learning
- Results stored in vector DB for improvement

Frontend viewer: `features/integration/components/TestingReportViewer.tsx`

## Development Mode

The system runs in development mode by default (`DEV_MODE=True`):

**What this means:**
- No authentication required
- Auto-assigns tenant ID `test-tenant-001`
- All API endpoints accessible without login
- Detailed debug logging enabled

**Access points:**
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- GraphQL: http://localhost:8000/graphql (planned)

## Common Issues & Solutions

### MongoDB Connection Issues
Check MongoDB is running on `localhost:27017`. Verify `MONGODB_URL` in `.env`.

### Vector DB Initialization
ChromaDB persists to `./vector_db_data`. Delete this directory to reset. Flow DB is at `./data/flow_chroma_db`.

### Large File Uploads
Max upload size is 50MB (`max_upload_size` in settings). PDF processing can be slow for large files - uses OCR with Mistral.

### CORS Errors
Ensure frontend origin is in `allowed_origins` setting. Default is `http://localhost:3000,http://localhost:5173`.

### AI Rate Limits
System uses multiple AI providers with fallback:
- Primary: Google Gemini (generous limits)
- OCR: Mistral AI (pixtral-large-latest)
- Fast inference: Groq

Fallback logic in `infrastructure/ai/resilience/`.

## Code Style Guidelines

### Backend (Python)
- Follow PEP 8
- Use async/await for I/O operations
- Type hints required (`mypy` checking planned)
- Docstrings for public classes/methods
- Domain entities must be immutable value objects when possible

### Frontend (TypeScript)
- Functional components only
- TypeScript strict mode
- Use custom hooks for logic reuse
- Props interfaces named `{Component}Props`
- Export components as default, types as named exports

## Critical Files to Understand

**Backend:**
- `src/main.py` - Application entry point, middleware setup
- `src/infrastructure/middleware/tenant_middleware.py` - Tenant isolation
- `src/application/ai/parsers/multi_parser.py` - Document parsing orchestrator
- `src/application/ai/execution/autonomous_executor.py` - AI execution engine
- `src/infrastructure/database/mongodb/connection.py` - DB connection management

**Frontend:**
- `src/App.tsx` - Main routing and layout
- `src/features/onboarding/components/OnboardingWizard.tsx` - Partner onboarding flow
- `src/features/chat/components/ChatContainer.tsx` - AI chat interface
- `src/lib/api/*.ts` - API client layer

## Performance Considerations

### Database Queries
- All queries automatically filtered by `tenant_id` via repository pattern
- Indexes created by `scripts/create_indexes.py` for common queries
- Use projection to limit returned fields for large documents

### AI Operations
- Document parsing is async and can take 30-60s for large PDFs
- Use WebSocket subscriptions for real-time progress updates
- Vector search limited to top-k=3 by default (configurable)

### Frontend
- Code splitting by route (Vite handles automatically)
- Large components lazy-loaded
- API responses cached via React Query (5min default)

## Extension Points

### Adding New AI Models
Implement provider in `infrastructure/ai/providers/{provider}_provider.py` and register in `provider_factory.py`.

### Adding New Document Formats
Create parser in `application/ai/parsers/` and update `format_detector.py`.

### Adding New Agent Types
Extend `application/ai/agents/agent_factory.py` with new agent roles and capabilities.

### Multi-Tenant Features
All new collections must use `tenant_{id}_` prefix pattern. Use `TenantAwareRepository` base class.

## Security Notes

- **Code Execution**: Generated adapters run in restricted sandbox (not fully implemented - use caution)
- **API Keys**: Partner API keys encrypted at rest in MongoDB
- **Tenant Isolation**: Critical - never bypass tenant context checks in production
- **File Uploads**: Validated for type and size, scanned for malicious content (basic checks only)

## Deployment

Production deployment not yet configured. Current setup is development only.

**Required for production:**
- Set `DEV_MODE=False`
- Implement proper authentication/authorization
- Configure production MongoDB cluster
- Set up Redis cluster
- Add rate limiting per tenant
- Enable HTTPS
- Configure monitoring (Sentry planned)

## Resources

- **Docs Directory**: `docs/` contains additional architecture notes
- **Plan Files**: `.cursor/plans/` has detailed architecture plans
- **Guide**: `guide.md` - Implementation guide
- **Plan**: `plan.md` - Phase-wise roadmap and team structure
