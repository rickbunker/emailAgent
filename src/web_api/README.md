# Asset Management System - Web API

This is a modern FastAPI-based web application for managing private market investment documents.

## Features (Phase 1 - Core Asset Management)

✅ **Implemented:**
- Complete Asset CRUD operations (Create, Read, Update, Delete)
- Asset search and filtering by type
- RESTful API with OpenAPI documentation
- Simple demo UI with HTMX for dynamic behavior
- Health check and system status endpoints

🚧 **Coming Soon (from feature requirements):**
- Document processing and classification
- Email integration
- Sender mapping management
- Memory system dashboard
- Human review workflow
- File browsing and management

## Technology Stack

- **Backend**: FastAPI (async Python web framework)
- **Frontend**: HTMX + Bootstrap (lightweight, no SPA complexity)
- **Storage**: Qdrant (vector database) + File system
- **Services**: Modular asset management system

## Running the Application

### Prerequisites

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Ensure Qdrant is running (optional, but recommended):
```bash
docker run -p 6333:6333 qdrant/qdrant
```

### Start the Server

```bash
# From the project root
python -m src.web_api.main

# Or with uvicorn directly
uvicorn src.web_api.main:app --reload --host 0.0.0.0 --port 8000
```

### Access the Application

- **Web UI**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Alternative API Docs**: http://localhost:8000/api/redoc
- **Health Check**: http://localhost:8000/api/v1/system/health

## API Endpoints (Phase 1)

### System
- `GET /api/v1/system/health` - Basic health check
- `GET /api/v1/system/health/detailed` - Detailed service status
- `GET /api/v1/system/info` - System configuration info

### Assets
- `GET /api/v1/assets/` - List all assets (with filtering)
- `GET /api/v1/assets/stats` - Get asset statistics
- `GET /api/v1/assets/{asset_id}` - Get specific asset
- `POST /api/v1/assets/` - Create new asset
- `PUT /api/v1/assets/{asset_id}` - Update asset
- `DELETE /api/v1/assets/{asset_id}` - Delete asset

## Project Structure

```
src/web_api/
├── __init__.py
├── main.py              # FastAPI application setup
├── dependencies.py      # Service initialization and DI
├── routers/            # API route handlers
│   ├── __init__.py
│   ├── assets.py       # Asset CRUD endpoints
│   ├── health.py       # System health endpoints
│   └── ui.py           # UI routes for demo frontend
├── templates/          # Jinja2 HTML templates
│   ├── base.html       # Base template with HTMX
│   ├── dashboard.html  # Main dashboard
│   ├── assets.html     # Asset list view
│   ├── asset_form.html # Create/edit form
│   ├── asset_detail.html # Asset details
│   └── partials/       # HTMX partial responses
├── static/             # Static files (CSS, JS, images)
└── README.md           # This file
```

## Development Notes

### For the Full Dev Team

This is a **demonstration skeleton** designed to:
1. Show integration with the new modular asset management system
2. Provide a clean API-first architecture
3. Demonstrate all features from the old UI in a modern way
4. Be easy to extend or replace with a full SPA if desired

### Key Design Decisions

1. **FastAPI over Flask**: Modern async support, automatic OpenAPI docs, better type hints
2. **HTMX over full SPA**: Simpler to demo features without Angular/React complexity
3. **Bootstrap for UI**: Quick professional look, easy to customize
4. **Service-oriented**: All business logic in services, not in routes

### Next Steps for Production

1. Add authentication/authorization (JWT, OAuth2)
2. Implement remaining features from requirements doc
3. Add comprehensive error handling
4. Set up proper logging and monitoring
5. Add database migrations for Qdrant
6. Implement file upload/download for documents
7. Add WebSocket support for real-time updates
8. Consider replacing demo UI with full SPA if needed

## Configuration

The API uses the same configuration as the main application (`src/utils/config.py`). Key settings:

- `assets_base_path`: Where asset files are stored
- `qdrant_host/port`: Vector database connection
- Memory limits for various subsystems

## Testing

```bash
# Run API tests (to be implemented)
pytest tests/test_web_api/

# Test health endpoint
curl http://localhost:8000/api/v1/system/health

# Test asset creation via API
curl -X POST http://localhost:8000/api/v1/assets/ \
  -H "Content-Type: application/json" \
  -d '{
    "deal_name": "Test Asset",
    "asset_name": "Test Asset - Full Name",
    "asset_type": "commercial_real_estate",
    "identifiers": ["TEST001", "Test Building"]
  }'
```

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [HTMX Documentation](https://htmx.org/)
- [Bootstrap 5 Documentation](https://getbootstrap.com/)
- Project Requirements: `/docs/WEB_UI_FEATURE_REQUIREMENTS.md`
- API Design: `/docs/NEW_API_DESIGN.md`
