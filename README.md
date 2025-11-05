# 🚀 CargoDham AI - Multi-Tenant Logistics Integration Platform

> **AI-Powered Platform**: Upload any logistics partner's API documentation and let AI automatically create integrations, understand workflows, and perform autonomous operations.

![Status](https://img.shields.io/badge/status-active-success.svg)
![Python](https://img.shields.io/badge/python-3.12-blue.svg)
![React](https://img.shields.io/badge/react-18-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115-green.svg)

## 🎯 What Makes This Special?

- **📄 Upload Documentation → ✨ Get Working Integration**: Just upload API docs (OpenAPI, PDF, Markdown, etc.)
- **🤖 AI Understands Everything**: Parses docs, learns workflows, generates code automatically
- **🏢 Multi-Tenant Architecture**: Each partner gets isolated workspace with MongoDB
- **🧠 Autonomous Operations**: AI performs bookings, tracking, etc. without manual coding
- **🔌 Dynamic Adapters**: Runtime API client generation for any partner

## 🏗️ Architecture

```
┌─────────────────┐
│   Frontend      │  React 18 + TypeScript + Tailwind
│   (Port 5173)   │  Partner Onboarding Wizard
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Backend API   │  FastAPI + MongoDB + Redis
│   (Port 8000)   │  AI Orchestration Layer
└────────┬────────┘
         │
         ↓
┌─────────────────────────────────────────────┐
│  AI Engine (Integrated)                     │
│  • Google Gemini (Text Generation)          │
│  • Mistral OCR (Document Understanding)     │
│  • LangChain + LangGraph (Orchestration)    │
│  • CrewAI (Multi-Agent System)              │
│  • Mem0 (AI Memory)                         │
│  • Pinecone (Vector Store)                  │
└─────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **MongoDB** (running on `localhost:27017`)
- **Redis** (optional, for caching)

### 1. Clone & Setup

```bash
git clone https://github.com/Devanshjoshi2804/cargodham-ai.git
cd cargodham-ai
```

### 2. Backend Setup

```bash
cd backend

# Install dependencies (already done if you followed installation)
pip install --user -r requirements-clean.txt

# Environment is already configured in .env
# Backend will run in DEV_MODE (bypasses auth for testing)
```

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies (already done)
npm install

# TypeScript types are configured
```

### 4. Start Everything

**Option A: Use the startup script (Windows)**
```bash
START.bat
```

**Option B: Manual start**

Terminal 1 - Backend:
```bash
cd backend
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Terminal 2 - Frontend:
```bash
cd frontend
npm run dev
```

### 5. Access the Platform

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **GraphQL Playground**: http://localhost:8000/graphql

## 🎨 Features Implemented

### ✅ Core Platform
- [x] Multi-tenant MongoDB architecture
- [x] Tenant context middleware
- [x] Development mode (bypasses auth for testing)
- [x] Dynamic collection management
- [x] FastAPI + Strawberry GraphQL
- [x] React 18 + TypeScript frontend

### ✅ AI Integration
- [x] Google Gemini integration
- [x] Mistral OCR for document parsing
- [x] LangChain orchestration
- [x] LangGraph state machines
- [x] CrewAI multi-agent system
- [x] Mem0 AI memory
- [x] Pinecone vector store

### ✅ Partner Onboarding
- [x] 5-step onboarding wizard
- [x] Document upload (drag & drop)
- [x] Format detection (OpenAPI, PDF, etc.)
- [x] Real-time parsing progress
- [x] Integration review UI
- [x] Partner activation

### ✅ Document Parsing
- [x] OpenAPI/Swagger parser
- [x] PDF parser (Mistral OCR)
- [x] Markdown parser
- [x] Text parser
- [x] AI-powered workflow analyzer

### ✅ Dynamic Integration
- [x] API adapter generator
- [x] Schema generator
- [x] Agent factory
- [x] Code execution sandbox
- [x] Workflow orchestration

### ✅ UI Components
- [x] Partner dashboard
- [x] Integration viewer
- [x] Chat interface
- [x] Document uploader
- [x] Progress indicators

## 🧪 Testing Mode

The system is configured in **DEV_MODE** for easy testing:

- ✅ **No Authentication Required**: All auth checks bypassed
- ✅ **Auto-Tenant Assignment**: Automatically assigns `test-tenant-001`
- ✅ **Full API Access**: All endpoints accessible without login
- ✅ **Detailed Logging**: Debug mode enabled

### Test the API

```bash
# Health check
curl http://localhost:8000/health

# Register a partner (dev mode)
curl -X POST http://localhost:8000/api/v1/partners/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Logistics",
    "email": "test@example.com",
    "contact_name": "John Doe",
    "contact_email": "john@example.com"
  }'

# Upload documentation
curl -X POST http://localhost:8000/api/v1/partners/{partner_id}/documentation \
  -F "file=@test-openapi.json"
```

## 📁 Project Structure

```
cargodham-ai/
├── backend/
│   ├── src/
│   │   ├── domain/              # Business entities
│   │   ├── application/         # Use cases & AI
│   │   ├── infrastructure/      # DB, AI providers
│   │   └── presentation/        # REST & GraphQL APIs
│   ├── requirements-clean.txt   # Python dependencies
│   └── .env                     # Configuration
│
├── frontend/
│   ├── src/
│   │   ├── features/            # Feature modules
│   │   ├── shared/              # Shared components
│   │   └── lib/                 # Utilities
│   └── package.json
│
├── START.bat                    # Quick start script
└── README.md                    # This file
```

## 🔑 API Keys Configured

The following AI services are integrated:

- ✅ **Google Gemini**: `[REDACTED]`
- ✅ **Mistral AI**: `[REDACTED]`
- ✅ **Context7 MCP**: `[REDACTED]`

## 🎯 Next Steps

### Immediate Testing
1. Open http://localhost:5173
2. Go through the onboarding wizard
3. Upload a sample API documentation file
4. Watch AI parse and understand the API
5. Review the generated integration
6. Test the chat interface

### Production Preparation
- [ ] Set `DEV_MODE=False` in `.env`
- [ ] Implement proper authentication
- [ ] Add rate limiting
- [ ] Set up monitoring
- [ ] Configure production MongoDB
- [ ] Add your own API keys
- [ ] Deploy to cloud

## 🛠️ Technology Stack

### Backend
- **FastAPI** - High-performance async API framework
- **MongoDB** - Multi-tenant database with Beanie ODM
- **Redis** - Caching and queue management
- **Pydantic** - Data validation and settings

### AI/ML
- **Google Gemini** - Text generation and understanding
- **Mistral OCR** - World's best document understanding
- **LangChain** - AI orchestration framework
- **LangGraph** - State machine for workflows
- **CrewAI** - Multi-agent collaboration
- **Mem0** - Advanced AI memory with graphs
- **Pinecone** - Vector database for semantic search

### Frontend
- **React 18** - Modern UI framework
- **TypeScript** - Type-safe development
- **Tailwind CSS** - Utility-first styling
- **Framer Motion** - Smooth animations
- **Apollo Client** - GraphQL client
- **React Query** - Data fetching and caching

## 📚 Documentation

- **API Docs**: http://localhost:8000/docs (Swagger UI)
- **GraphQL Playground**: http://localhost:8000/graphql
- **Architecture Plan**: See `cargodham-ai-architecture.plan.md`
- **Testing Guide**: See `TESTING_GUIDE.md`

## 🤝 Contributing

This is a private project. For questions or issues, contact the development team.

## 📄 License

Proprietary - All rights reserved

## 🎉 Status

**✅ FULLY OPERATIONAL** - All core features implemented and tested!

---

Made with ❤️ for the future of logistics automation
