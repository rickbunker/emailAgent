# Email Agent - AI-Powered Document Processing System

## 🚧 Under Active Refactoring

We are currently refactoring from a monolithic Flask application to a modern FastAPI + HTMX architecture. See [REFACTORING_PROGRESS.md](docs/REFACTORING_PROGRESS.md) for details.

## 🎯 Project Overview

The Email Agent is an intelligent document processing system that:
- Processes emails from Gmail and Microsoft 365
- Classifies documents using AI and memory systems
- Routes attachments to appropriate asset folders
- Learns from human feedback to improve accuracy

## 🏗️ New Architecture (In Progress)

```
src/
├── web_api/          # New FastAPI backend (active development)
│   ├── routers/      # API endpoints
│   └── templates/    # HTMX-powered UI
├── asset_management/ # Modular asset services
├── memory/          # Four-layer memory system
├── email_interface/ # Email provider integrations
└── agents/          # AI processing agents
```

## 🚀 Quick Start

### Current (New) System
```bash
# Start the FastAPI server
python -m src.web_api.main

# Access at http://localhost:8000
```

### Services Required
```bash
# Start Qdrant vector database
docker run -p 6333:6333 qdrant/qdrant
```

## 📍 Current Status

### ✅ Working Features
- Asset Management (CRUD operations)
- Sender Mappings (email to asset routing)
- Health Dashboard
- API Documentation at `/api/docs`

### 🚧 In Development
- Email Processing UI
- Human Review Queue
- Document Browser
- Memory System Dashboard

## 📚 Documentation

### Current Documentation
- [REFACTORING_PROGRESS.md](docs/REFACTORING_PROGRESS.md) - Detailed refactoring status
- [NEW_API_DESIGN.md](docs/NEW_API_DESIGN.md) - New API architecture
- [CODING_STANDARDS.md](docs/CODING_STANDARDS.md) - Development guidelines
- [MEMORY_SYSTEM_OVERHAUL_PLAN.md](docs/MEMORY_SYSTEM_OVERHAUL_PLAN.md) - Memory system improvements

### Setup Guides
- [GMAIL_SETUP.md](docs/GMAIL_SETUP.md) - Gmail OAuth configuration
- [MSGRAPH_SETUP.md](docs/MSGRAPH_SETUP.md) - Microsoft 365 setup

## 🛠️ Technology Stack

- **Backend**: FastAPI (Python 3.11+)
- **Frontend**: HTMX + Bootstrap 5
- **Database**: Qdrant Vector Database
- **Email**: Gmail API, Microsoft Graph API
- **AI/ML**: Sentence Transformers, Custom Memory Systems

## 🤝 Contributing

Please follow the guidelines in [CODING_STANDARDS.md](docs/CODING_STANDARDS.md).

## 📄 License

Copyright 2025 Inveniam Capital Partners, LLC and Rick Bunker
Internal use only

---

**Note**: Archived documentation from the old system can be found in the `archive/` directory.
