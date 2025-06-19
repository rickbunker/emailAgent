# New API Design Document

This document outlines the API structure for the new web interface, designed to leverage the modular `/src/asset_management` system while providing all features from the legacy UI.

## Design Principles

1. **RESTful Architecture** - Resources, HTTP verbs, stateless
2. **Service-Oriented** - Each module handles its domain
3. **Async-First** - Built for scalability with async/await
4. **OpenAPI Compatible** - Self-documenting with FastAPI
5. **Clean Separation** - API logic separate from business logic

---

## API Structure Overview

```
/api/v1/
├── /assets/              # Asset management
├── /senders/             # Sender mapping management  
├── /documents/           # Document processing & files
├── /email/               # Email processing
├── /review/              # Human review system
├── /memory/              # Memory system operations
├── /admin/               # Administrative functions
└── /system/              # System health & status
```

---

## 1. Asset Management API

### Service Integration
```python
# Uses: src.asset_management.services.AssetService
```

### Endpoints

#### List Assets
```
GET /api/v1/assets
Query Parameters:
  - asset_type: AssetType (optional) - Filter by type
  - search: string (optional) - Search in names/identifiers
  - limit: int (default: 100)
  - offset: int (default: 0)

Response: {
  "items": [Asset],
  "total": int,
  "limit": int,
  "offset": int
}
```

#### Get Asset
```
GET /api/v1/assets/{asset_id}

Response: Asset
```

#### Create Asset
```
POST /api/v1/assets
Body: {
  "deal_name": string,
  "asset_name": string,
  "asset_type": AssetType,
  "identifiers": [string],
  "metadata": object (optional)
}

Response: {
  "asset_id": string,
  "asset": Asset
}
```

#### Update Asset
```
PUT /api/v1/assets/{asset_id}
Body: {
  "deal_name": string (optional),
  "asset_name": string (optional),
  "asset_type": AssetType (optional),
  "identifiers": [string] (optional),
  "metadata": object (optional)
}

Response: Asset
```

#### Delete Asset
```
DELETE /api/v1/assets/{asset_id}
Query Parameters:
  - preserve_files: bool (default: true)

Response: {
  "deleted": bool,
  "message": string
}
```

#### Asset Statistics
```
GET /api/v1/assets/stats

Response: {
  "total_assets": int,
  "by_type": {
    "commercial_real_estate": int,
    "private_equity": int,
    "private_credit": int,
    "infrastructure": int
  },
  "recent_assets": [Asset]
}
```

---

## 2. Sender Mapping API

### Service Integration
```python
# Uses: src.asset_management.SenderMappingService
```

### Endpoints

#### List Mappings
```
GET /api/v1/senders
Query Parameters:
  - asset_id: string (optional) - Filter by asset
  - email: string (optional) - Filter by email domain
  - confidence_min: float (optional)

Response: {
  "items": [SenderMapping],
  "total": int
}
```

#### Get Mapping
```
GET /api/v1/senders/{mapping_id}

Response: SenderMapping
```

#### Create Mapping
```
POST /api/v1/senders
Body: {
  "sender_email": string,
  "asset_id": string,
  "confidence": float (0.0-1.0),
  "document_types": [string] (optional),
  "source": string (default: "manual")
}

Response: SenderMapping
```

#### Update Mapping
```
PUT /api/v1/senders/{mapping_id}
Body: {
  "confidence": float (optional),
  "document_types": [string] (optional),
  "asset_id": string (optional)
}

Response: SenderMapping
```

#### Delete Mapping
```
DELETE /api/v1/senders/{mapping_id}

Response: {
  "deleted": bool
}
```

---

## 3. Document Processing API

### Service Integration
```python
# Uses: src.asset_management.processing.DocumentProcessor
# Uses: src.asset_management.utils.StorageService
```

### Endpoints

#### Process Document
```
POST /api/v1/documents/process
Body: {
  "filename": string,
  "content": base64_string,
  "email_context": {
    "sender_email": string,
    "subject": string,
    "body": string,
    "date": datetime
  }
}

Response: ProcessingResult
```

#### List Documents
```
GET /api/v1/documents
Query Parameters:
  - asset_id: string (optional)
  - category: DocumentCategory (optional)
  - date_from: datetime (optional)
  - date_to: datetime (optional)
  - needs_review: bool (optional)

Response: {
  "items": [DocumentInfo],
  "total": int
}
```

#### Get Document
```
GET /api/v1/documents/{document_id}

Response: {
  "info": DocumentInfo,
  "processing_details": ProcessingResult,
  "file_path": string
}
```

#### Download Document
```
GET /api/v1/documents/{document_id}/download

Response: Binary file
```

#### Preview Document
```
GET /api/v1/documents/{document_id}/preview

Response: {
  "content": string (text) or base64 (binary),
  "content_type": string
}
```

#### Reclassify Document
```
POST /api/v1/documents/{document_id}/reclassify
Body: {
  "new_asset_id": string (optional),
  "new_category": DocumentCategory (optional),
  "reason": string,
  "update_memory": bool (default: true)
}

Response: {
  "success": bool,
  "new_path": string,
  "processing_result": ProcessingResult
}
```

#### Inspect Classification
```
GET /api/v1/documents/{document_id}/classification

Response: {
  "asset_identification": {
    "result": AssetMatch,
    "reasoning": object,
    "memory_contributions": object
  },
  "document_classification": {
    "result": CategoryMatch,
    "reasoning": object,
    "memory_contributions": object
  },
  "confidence_analysis": object
}
```

---

## 4. Email Processing API

### Service Integration
```python
# Uses: src.email_interface
# Uses: src.asset_management.processing.DocumentProcessor
```

### Endpoints

#### List Mailboxes
```
GET /api/v1/email/mailboxes

Response: {
  "mailboxes": [{
    "id": string,
    "name": string,
    "type": "gmail" | "msgraph",
    "status": "active" | "error",
    "last_sync": datetime
  }]
}
```

#### Process Emails
```
POST /api/v1/email/process
Body: {
  "mailbox_ids": [string],
  "hours_back": int (default: 24),
  "force_reprocess": bool (default: false)
}

Response: {
  "run_id": string,
  "status": "started"
}
```

#### Get Processing Status
```
GET /api/v1/email/process/{run_id}

Response: {
  "run_id": string,
  "status": "running" | "completed" | "cancelled" | "error",
  "progress": {
    "total_emails": int,
    "processed_emails": int,
    "total_attachments": int,
    "processed_attachments": int
  },
  "results": object
}
```

#### Cancel Processing
```
POST /api/v1/email/process/{run_id}/cancel

Response: {
  "cancelled": bool
}
```

#### Processing History
```
GET /api/v1/email/history
Query Parameters:
  - limit: int (default: 50)
  - offset: int (default: 0)

Response: {
  "runs": [ProcessingRun],
  "total": int
}
```

---

## 5. Human Review API

### Service Integration
```python
# Uses: src.web_ui.human_review.review_queue
# Integrates with memory systems for feedback
```

### Endpoints

#### List Review Items
```
GET /api/v1/review
Query Parameters:
  - status: "pending" | "completed" | "all" (default: "pending")
  - asset_id: string (optional)
  - date_from: datetime (optional)
  - limit: int (default: 50)

Response: {
  "items": [ReviewItem],
  "total": int,
  "stats": {
    "pending": int,
    "completed": int,
    "avg_confidence": float
  }
}
```

#### Get Review Item
```
GET /api/v1/review/{review_id}

Response: ReviewItem with full details
```

#### Submit Review
```
POST /api/v1/review/{review_id}/submit
Body: {
  "asset_id": string,
  "document_category": DocumentCategory,
  "confidence": float,
  "notes": string (optional),
  "corrections": object (optional)
}

Response: {
  "success": bool,
  "file_moved": bool,
  "memory_updated": bool
}
```

#### Bulk Review Actions
```
POST /api/v1/review/bulk
Body: {
  "review_ids": [string],
  "action": "approve" | "reject" | "defer",
  "asset_id": string (optional),
  "category": DocumentCategory (optional)
}

Response: {
  "processed": int,
  "errors": [object]
}
```

---

## 6. Memory System API

### Service Integration
```python
# Uses: src.memory.semantic.SemanticMemory
# Uses: src.memory.episodic.EpisodicMemory
# Uses: src.memory.procedural.ProceduralMemory
# Uses: src.memory.contact.ContactMemory
```

### Endpoints

#### Memory Overview
```
GET /api/v1/memory/stats

Response: {
  "semantic": MemoryStats,
  "episodic": MemoryStats,
  "procedural": MemoryStats,
  "contact": MemoryStats
}
```

#### Query Memory
```
POST /api/v1/memory/{memory_type}/query
Body: {
  "query": string,
  "filters": object (optional),
  "limit": int (default: 10)
}

Response: {
  "results": [MemoryItem],
  "total": int
}
```

#### Get Memory Item
```
GET /api/v1/memory/{memory_type}/{item_id}

Response: MemoryItem
```

#### Delete Memory Item
```
DELETE /api/v1/memory/{memory_type}/{item_id}

Response: {
  "deleted": bool
}
```

#### Clear Memory Type
```
POST /api/v1/memory/{memory_type}/clear
Body: {
  "confirm": bool
}

Response: {
  "cleared": int
}
```

#### Memory Conflicts
```
GET /api/v1/memory/conflicts

Response: {
  "conflicts": [MemoryConflict]
}
```

#### Resolve Conflict
```
POST /api/v1/memory/conflicts/{conflict_id}/resolve
Body: {
  "resolution": "keep_first" | "keep_second" | "merge",
  "merge_data": object (optional)
}

Response: {
  "resolved": bool
}
```

---

## 7. Administrative API

### Service Integration
```python
# Direct integration with various services
# Includes cleanup, maintenance, and system operations
```

### Endpoints

#### System Cleanup
```
POST /api/v1/admin/cleanup
Body: {
  "operations": [
    "processed_documents",
    "email_history",
    "processing_runs",
    "human_review",
    "attachment_files",
    "memory_collections"
  ],
  "confirm": bool
}

Response: {
  "results": {
    operation: {
      "success": bool,
      "removed_count": int,
      "message": string
    }
  }
}
```

#### Reload Knowledge Base
```
POST /api/v1/admin/knowledge/reload

Response: {
  "loaded": {
    "semantic": int,
    "procedural": int
  }
}
```

#### Export Data
```
POST /api/v1/admin/export
Body: {
  "include": ["assets", "mappings", "documents", "memory"],
  "format": "json" | "csv"
}

Response: {
  "export_id": string,
  "status": "started"
}
```

#### Import Data
```
POST /api/v1/admin/import
Body: {
  "data": object or file upload,
  "merge_strategy": "replace" | "merge" | "skip_existing"
}

Response: {
  "imported": {
    resource_type: int
  },
  "errors": [object]
}
```

---

## 8. System API

### Endpoints

#### Health Check
```
GET /api/v1/system/health

Response: {
  "status": "healthy" | "degraded" | "unhealthy",
  "services": {
    "qdrant": ServiceHealth,
    "memory": ServiceHealth,
    "storage": ServiceHealth,
    "email": ServiceHealth
  },
  "version": string,
  "uptime": int
}
```

#### System Info
```
GET /api/v1/system/info

Response: {
  "version": string,
  "environment": string,
  "config": {
    "assets_base_path": string,
    "memory_limits": object,
    "email_providers": [string]
  }
}
```

#### WebSocket Events
```
WS /api/v1/system/events

Events:
  - processing_progress
  - document_classified
  - review_submitted
  - memory_updated
```

---

## Data Models

### Common Models

```python
class Asset:
    deal_id: str
    deal_name: str
    asset_name: str
    asset_type: AssetType
    folder_path: str
    identifiers: List[str]
    created_date: datetime
    last_updated: datetime
    metadata: Optional[Dict[str, Any]]

class ProcessingResult:
    status: ProcessingStatus
    file_hash: str
    file_path: Optional[str]
    confidence: float
    matched_asset_id: Optional[str]
    asset_confidence: float
    document_category: Optional[DocumentCategory]
    confidence_level: Optional[ConfidenceLevel]
    metadata: Dict[str, Any]

class SenderMapping:
    mapping_id: str
    asset_id: str
    sender_email: str
    confidence: float
    document_types: List[str]
    created_date: datetime
    last_activity: datetime
    email_count: int

class ReviewItem:
    review_id: str
    document_id: str
    filename: str
    predicted_asset: Optional[Asset]
    predicted_category: Optional[DocumentCategory]
    confidence: float
    status: str
    created_date: datetime
    email_context: Dict[str, Any]
```

---

## Error Handling

### Standard Error Response
```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Asset not found",
    "details": {
      "asset_id": "uuid-here"
    }
  },
  "request_id": "req-uuid"
}
```

### Error Codes
- `VALIDATION_ERROR` - Invalid input
- `RESOURCE_NOT_FOUND` - Resource doesn't exist
- `CONFLICT` - Resource conflict
- `PROCESSING_ERROR` - Processing failed
- `AUTHENTICATION_ERROR` - Auth required
- `PERMISSION_DENIED` - Insufficient permissions
- `RATE_LIMITED` - Too many requests
- `SERVICE_UNAVAILABLE` - Service down

---

## Authentication & Authorization

### API Key Authentication
```
Header: X-API-Key: your-api-key
```

### JWT Bearer Token
```
Header: Authorization: Bearer <token>
```

### Permissions Model
- `read:assets` - View assets
- `write:assets` - Create/update/delete assets
- `read:documents` - View documents
- `write:documents` - Process/reclassify documents
- `admin:system` - System administration

---

## Implementation Notes

### FastAPI Structure
```python
from fastapi import FastAPI, APIRouter

# Main app
app = FastAPI(title="Asset Management API", version="1.0.0")

# Routers
asset_router = APIRouter(prefix="/api/v1/assets", tags=["assets"])
sender_router = APIRouter(prefix="/api/v1/senders", tags=["senders"])
document_router = APIRouter(prefix="/api/v1/documents", tags=["documents"])
# ... etc

# Include routers
app.include_router(asset_router)
app.include_router(sender_router)
# ... etc
```

### Dependency Injection
```python
from fastapi import Depends

async def get_asset_service() -> AssetService:
    return asset_service_instance

@asset_router.get("/")
async def list_assets(
    service: AssetService = Depends(get_asset_service),
    limit: int = 100,
    offset: int = 0
):
    return await service.list_assets(limit=limit, offset=offset)
```

### Background Tasks
```python
from fastapi import BackgroundTasks

@email_router.post("/process")
async def process_emails(
    request: ProcessEmailRequest,
    background_tasks: BackgroundTasks
):
    run_id = str(uuid.uuid4())
    background_tasks.add_task(
        process_emails_task,
        run_id,
        request.mailbox_ids,
        request.hours_back
    )
    return {"run_id": run_id, "status": "started"}
```

### WebSocket Support
```python
@app.websocket("/api/v1/system/events")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await event_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        event_manager.disconnect(websocket)
```

---

## Migration Strategy

### Phase 1: Core APIs
1. Asset CRUD operations
2. Basic document endpoints
3. Health check

### Phase 2: Processing
1. Document processing
2. Email integration
3. Sender mappings

### Phase 3: Advanced Features
1. Human review
2. Memory system
3. Administrative tools

### Phase 4: Real-time
1. WebSocket events
2. Progress tracking
3. Live updates 