# Web UI Feature Requirements Document

This document extracts all features from the old web UI (src/web_ui/app.py) to serve as requirements for the new API-first web interface.

## Overview
The web UI is a Flask application that provides a complete interface for managing private market investment documents. It includes asset management, document processing, email integration, and a comprehensive memory system dashboard.

---

## 1. Core Asset Management

### 1.1 Asset CRUD Operations
- **Dashboard** (`/`)
  - Display total assets count
  - Show assets grouped by type (CRE, PE, PC, Infrastructure)
  - List 5 most recent assets
  - Asset type distribution visualization

- **Asset List** (`/assets`)
  - List all assets with filtering
  - Show asset type, deal name, and identifiers
  - Quick links to view/edit each asset
  - Create new asset button

- **Create Asset** (`/assets/new`)
  - Form fields: deal_name, asset_name, asset_type, identifiers
  - Parse comma-separated identifiers (supports quoted strings)
  - Create folder structure on filesystem
  - Store in Qdrant vector database

- **View Asset** (`/assets/<deal_id>`)
  - Display all asset details
  - Show associated sender mappings
  - List document categories
  - Edit/delete actions

- **Edit Asset** (`/assets/<deal_id>/edit`)
  - Update deal_name, asset_name, asset_type, identifiers
  - Preserve folder structure
  - Update Qdrant storage

- **Delete Asset** (`/assets/<deal_id>/delete`)
  - Remove from Qdrant
  - Preserve folder (contains documents)
  - Confirmation required

### 1.2 Asset API Endpoints
- `GET /api/assets` - JSON list of all assets
- Asset health check integration

---

## 2. Sender Mapping Management

### 2.1 Sender Mapping CRUD
- **Sender List** (`/senders`)
  - List all sender-to-asset mappings
  - Show sender email, mapped asset, confidence
  - Display asset type and full name
  - Email count per sender

- **Create Mapping** (`/senders/new`)
  - Select asset from dropdown
  - Enter sender email
  - Set confidence level (0.0-1.0)
  - Optional document types

- **Edit Mapping** (`/senders/<mapping_id>/edit`)
  - Update confidence, document types
  - Change asset assignment

- **Delete Mapping** (`/senders/<mapping_id>/delete`)
  - Remove mapping from system

---

## 3. Email Processing

### 3.1 Email Processing Interface
- **Processing Dashboard** (`/email-processing`)
  - List configured mailboxes (Gmail, MS Graph)
  - Processing history summary
  - Start new processing run
  - Stop active processing

- **Process Emails** (`/api/process-emails`)
  - Select mailboxes to process
  - Set hours_back parameter
  - Force reprocess option
  - Parallel processing with progress tracking
  - Cancellation support

- **Processing Run Details** (`/email-processing/runs/<run_id>`)
  - Show complete run statistics
  - List processed emails with attachments
  - Error details
  - Processing timeline

### 3.2 Email Configuration
- **Mailbox Management** (`/api/mailboxes`)
  - Auto-detect Gmail/MS Graph credentials
  - List configured mailboxes
  - Mailbox health status

### 3.3 Processing History
- `GET /api/processing-history` - Recent processing summary
- `GET /api/processing-runs` - List all runs
- `POST /api/clear-history` - Clear processing history

---

## 4. Document Processing

### 4.1 Attachment Processing
- **Enhanced Processing Pipeline**
  - Antivirus scanning
  - File type validation
  - Duplicate detection (SHA-256)
  - Asset identification (4 memory types)
  - Document classification
  - Confidence scoring
  - Human review routing

### 4.2 Processing Results
- File storage in asset folders
- Category-based organization
- Needs review folder for low confidence
- Processing metadata storage

---

## 5. Human Review System

### 5.1 Review Queue Management
- **Review Queue** (`/human-review`)
  - List items needing review
  - Filter by status, asset, date
  - Bulk actions
  - Queue statistics

- **Review Item** (`/human-review/<review_id>`)
  - Display document preview
  - Show AI predictions
  - Manual asset selection
  - Category selection
  - Confidence adjustment
  - Add notes/corrections

- **Submit Review** (`/api/human-review/<review_id>/submit`)
  - Apply human corrections
  - Move file to correct location
  - Update memory systems
  - Learn from feedback

### 5.2 Review Statistics
- `GET /api/human-review/stats` - Queue metrics

---

## 6. File Management

### 6.1 File Browser
- **Browse Files** (`/files`)
  - Navigate asset folder structure
  - Search files by name/type
  - Preview documents
  - Download files
  - Reclassify documents
  - File count per folder

- **File Operations**
  - `GET /files/download/<path>` - Download file
  - `GET /files/view/<path>` - Preview file
  - `POST /files/reclassify/<path>` - Change classification

### 6.2 Classification Inspector
- **Inspect Classification** (`/files/inspect/<path>`)
  - Show AI reasoning for classification
  - Display all memory contributions
  - Confidence breakdown
  - Pattern matches
  - Decision flow visualization

---

## 7. Memory System Dashboards

### 7.1 Memory Overview
- **Memory Dashboard** (`/memory`)
  - Summary of all 4 memory types
  - Item counts
  - Storage usage
  - Collection health

### 7.2 Individual Memory Views
- **Semantic Memory** (`/memory/semantic`)
  - Asset knowledge
  - Human feedback
  - Classification hints
  - Search interface

- **Episodic Memory** (`/memory/episodic`)
  - Past experiences
  - Decision outcomes
  - Pattern recognition
  - Success/failure tracking

- **Procedural Memory** (`/memory/procedural`)
  - Business rules
  - Classification patterns
  - Asset matching rules
  - No dynamic learning

- **Contact Memory** (`/memory/contact`)
  - Sender profiles
  - Trust scores
  - Communication patterns
  - Organization relationships

### 7.3 Memory Operations
- View individual items
- Delete items
- Resolve conflicts
- Clear collections
- Reload from knowledge base

---

## 8. Knowledge Base Management

### 8.1 Knowledge Base Viewer
- **Knowledge Files** (`/memory/knowledge`)
  - List JSON knowledge files
  - View file contents
  - Validation status
  - Last loaded timestamp

- **Serve Knowledge** (`/memory/knowledge/<filename>`)
  - Download knowledge files
  - Pretty JSON display

---

## 9. Administrative Tools

### 9.1 Testing & Cleanup
- **Cleanup Dashboard** (`/testing/cleanup`)
  - Granular data cleanup options
  - System statistics
  - Batch operations
  - Confirmation required

### 9.2 Cleanup Operations (`/api/testing/cleanup`)
- Clear processed documents
- Reset email history
- Delete processing runs
- Clear human review
- Remove attachment files
- Reset memory collections
- Smart memory reset (preserve knowledge)
- Clear sender mappings
- Delete assets
- Reload knowledge base
- Reset file validation

### 9.3 System Health
- **Health Check** (`/api/health`)
  - Asset system status
  - Memory system health
  - Qdrant connectivity
  - Storage availability

---

## 10. Advanced Features

### 10.1 Memory Conflict Resolution
- `GET /api/memory/conflicts` - List conflicts
- `POST /api/memory/conflicts/<id>/resolve` - Resolve conflict

### 10.2 Direct Memory Access
- `GET /api/memory/<type>/<collection>/<item_id>` - View item
- `DELETE /api/memory/<type>/<collection>/<item_id>` - Delete item
- `POST /api/memory/<type>/clear` - Clear memory type

### 10.3 Processing Controls
- `POST /api/stop-processing` - Cancel active processing
- Parallel processing with semaphores
- Progress tracking
- Error recovery

---

## 11. UI/UX Features

### 11.1 User Feedback
- Flash messages for all operations
- Success/error notifications
- Progress indicators
- Confirmation dialogs

### 11.2 Navigation
- Consistent header/navigation
- Breadcrumbs
- Back to list links
- Quick actions

### 11.3 Data Display
- Sortable tables
- Pagination for large lists
- Search/filter capabilities
- Export options

---

## 12. Security & Validation

### 12.1 Input Validation
- Form field validation
- File type restrictions
- Size limits
- Path traversal prevention

### 12.2 Authentication
- Flask session management
- API authentication (planned)

---

## 13. Performance Features

### 13.1 Async Processing
- Email processing in parallel
- Batch operations
- Background tasks
- Progress tracking

### 13.2 Caching
- Memory query results
- Asset lists
- Configuration caching

---

## 14. Error Handling

### 14.1 User-Friendly Errors
- Custom 404 pages
- Custom 500 pages
- Detailed error messages
- Recovery suggestions

### 14.2 Logging
- Comprehensive operation logging
- Error tracking
- Performance metrics
- Audit trail

---

## Implementation Priority

### Phase 1: Core Functionality
1. Asset CRUD operations
2. Basic document processing
3. File storage management
4. Simple API endpoints

### Phase 2: Processing Pipeline
1. Email integration
2. Document classification
3. Asset identification
4. Confidence scoring

### Phase 3: Human Interface
1. Human review queue
2. File browser
3. Reclassification
4. Classification inspector

### Phase 4: Memory Systems
1. Memory dashboards
2. Knowledge base viewer
3. Conflict resolution
4. Memory management

### Phase 5: Advanced Features
1. Bulk operations
2. Administrative tools
3. Performance optimization
4. Advanced search

---

## Technical Requirements

### Backend
- FastAPI or Flask with Blueprints
- Async/await support
- RESTful API design
- OpenAPI documentation

### Frontend
- Modern responsive design
- AJAX for dynamic updates
- Progress indicators
- Keyboard shortcuts

### Storage
- Qdrant vector database
- File system organization
- JSON configuration
- SQLite for metadata (optional)

### Integration
- Gmail API
- MS Graph API
- Antivirus integration
- Memory system APIs
