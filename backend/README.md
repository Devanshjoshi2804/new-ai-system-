# AI Logistics Integration Platform - Backend

Multi-tenant AI-powered logistics integration platform backend built with FastAPI, MongoDB, and advanced AI frameworks.

## Features

- **Multi-Tenant Architecture**: Complete data isolation using MongoDB collection-level tenancy
- **AI-Powered Documentation Parsing**: Automatically parse API documentation in any format
- **Dynamic Code Generation**: Generate API adapters and agents at runtime
- **Autonomous AI Operations**: AI agents that understand and execute logistics workflows
- **Real-time Processing**: WebSocket support for live updates
- **Secure Code Execution**: Sandboxed environment for generated code

## Tech Stack

- **Framework**: FastAPI 0.109+
- **Database**: MongoDB 7.0+
- **Cache**: Redis 7+
- **AI/ML**: LangChain, LangGraph, CrewAI, OpenAI GPT-4
- **Document Parsing**: PyPDF2, pdfplumber, pytesseract
- **Code Generation**: Jinja2, AST manipulation

## Project Structure

```
backend/
├── src/
│   ├── domain/              # Domain entities and business logic
│   ├── application/         # Use cases and AI orchestration
│   ├── infrastructure/      # External integrations and database
│   └── presentation/        # API endpoints (REST, GraphQL, WebSocket)
├── tests/                   # Test suite
├── requirements.txt         # Python dependencies
└── Dockerfile              # Container configuration
```

## Setup

### Prerequisites

- Python 3.11+
- MongoDB 7.0+
- Redis 7+
- OpenAI API Key

### Installation

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Copy environment file:
```bash
cp .env.example .env
```

4. Configure `.env`:
```env
MONGODB_URL=mongodb://localhost:27017
OPENAI_API_KEY=your_key_here
# ... other settings
```

5. Run application:
```bash
python src/main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload
```

### Using Docker Compose

```bash
docker-compose up -d
```

## API Documentation

Once running, access:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/api/health

## Architecture

### Multi-Tenant Data Isolation

Every request requires tenant context (via header, subdomain, or JWT):
```
X-Tenant-ID: partner-abc-123
```

MongoDB collections are automatically prefixed:
```
tenant_{tenant_id}_bookings
tenant_{tenant_id}_shipments
tenant_{tenant_id}_conversations
```

### AI-Powered Documentation Parsing

1. Upload API documentation (OpenAPI, PDF, text, etc.)
2. AI automatically detects format
3. Extracts API endpoints, schemas, and workflows
4. Generates code and agents dynamically
5. Ready to use in minutes

### Request Flow

```
User Request
    ↓
Tenant Middleware (extract tenant_id)
    ↓
TenantAwareClient (inject tenant filter)
    ↓
Use Case Layer
    ↓
Domain Layer
    ↓
MongoDB (tenant-specific collection)
```

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Format code
black src/

# Lint
pylint src/

# Type checking
mypy src/
```

## License

Proprietary - All rights reserved

