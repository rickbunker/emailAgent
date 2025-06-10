# Asset Document E-Mail Ingestion Agent

An email-driven document processing and filing agent for private market assets.

## Overview

This agent automatically processes email attachments and organizes them by asset and document type using AI classification and fuzzy matching.

## Key Features

- Automated document extraction from emails
- Asset-based organization using UUID identifiers
- ClamAV antivirus scanning
- SHA256 duplicate detection
- Confidence-based processing decisions
- Automated email confirmations
- Qdrant vector database integration

## Asset Types Supported

1. **Commercial Real Estate** - rent rolls, leases, financials
2. **Private Credit** - loan docs, compliance reports  
3. **Private Equity** - portfolio financials, presentations
4. **Infrastructure** - permits, engineering docs

## Processing Pipeline

1. Email received → Spam check → Attachment extraction
2. SHA256 hash → Duplicate check → AV scan
3. Sender lookup → Content analysis → Asset matching
4. Confidence scoring → Routing decision → File categorization & organization
5. Metadata storage → Email confirmation → Memory updates

## File Organization

```
./assets/
└── [deal_id]_[deal_name]/
    ├── rent_rolls/
    ├── financials/
    ├── legal/
    ├── to_be_categorized/
    └── quarantine/
```

## Confidence Thresholds

- **≥90%**: Auto-process
- **≥70%**: Process + confirm
- **≥50%**: Save uncategorized
- **<50%**: Human review

## Implementation Phases

- **Phase 0**: Documentation ✅
- **Phase 1**: Core infrastructure (next)
- **Phase 2**: Asset management
- **Phase 3**: Document classification
- **Phase 4**: Fuzzy matching
- **Phase 5**: File organization
- **Phase 6**: Communications
- **Phase 7**: Unknown senders
- **Phase 8**: Monitoring

## Technical Stack

- **Database**: Qdrant (vector search)
- **AV Scanner**: ClamAV
- **String Matching**: Damerau-Levenshtein
- **Email**: Gmail/Microsoft Graph APIs
- **Memory**: Procedural + Semantic

## Security Features

- Antivirus scanning all attachments
- SHA256 hash duplicate prevention
- File type whitelisting
- Quarantine system for threats
- Processing audit trails

## Agent Architecture

The agent integrates with existing email and memory systems to provide document management with minimal human intervention.

Ready for Phase 1 implementation. 