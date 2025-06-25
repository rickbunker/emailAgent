# Email Agent Memory System

This directory contains all memory files for the Email Agent system. The memory system consists of three types of memory, each serving different purposes in the email processing workflow.

## Memory Types

### 1. Semantic Memory (`semantic_memory.json`)
**Purpose**: Stores factual knowledge, asset profiles, and sender mappings.

**Contents**:
- `asset_profiles`: Definitions of assets with keywords for matching
- `file_type_rules`: Rules for handling different file types
- `sender_mappings`: Maps email addresses to trusted senders and their associated assets
- `organization_contacts`: Organization-level contact information

**Baseline**: `semantic_memory_baseline.json` contains the initial state

### 2. Procedural Memory (`procedural_memory.json`)
**Purpose**: Stores business rules, processing procedures, and algorithms.

**Contents**:
- `relevance_rules`: Rules for determining email relevance
- `asset_matching_rules`: Rules for matching attachments to assets
- `file_processing_rules`: Rules for processing different file types
- `thresholds`: Configuration thresholds for decision-making

**Baseline**: `procedural_memory_baseline.json` contains the initial state

### 3. Episodic Memory (`episodic_memory.db`)
**Purpose**: Stores processing history and learning experiences.

**Contents** (SQLite database):
- `processing_history`: Records of email processing decisions
- `human_feedback`: Human corrections and feedback for learning

**Baseline**: `episodic_memory_baseline.json` contains initial patterns
**Export**: `episodic_memory_export.json` contains a JSON export for version control

## File Overview

| File | Type | Purpose | Version Controlled |
|------|------|---------|-------------------|
| `semantic_memory.json` | Runtime | Current semantic knowledge | ✅ Yes |
| `semantic_memory_baseline.json` | Baseline | Initial semantic state | ✅ Yes |
| `procedural_memory.json` | Runtime | Current business rules | ✅ Yes |
| `procedural_memory_baseline.json` | Baseline | Initial business rules | ✅ Yes |
| `episodic_memory.db` | Runtime | SQLite database with history | ✅ Yes |
| `episodic_memory_baseline.json` | Baseline | Initial learning patterns | ✅ Yes |
| `episodic_memory_export.json` | Export | JSON export of episodic data | ✅ Yes |
| `memory_status.json` | Status | Current system status | ✅ Yes |
| `backups/` | Backups | Runtime backups | ❌ No |

## Management Operations

### Using the CLI Tool

The memory system can be managed using the CLI tool:

```bash
# Show current status
python scripts/memory_management.py status

# Create a backup
python scripts/memory_management.py backup --name "before_major_change"

# Export for GitHub (formats files consistently)
python scripts/memory_management.py export

# Reset to baseline state
python scripts/memory_management.py reset

# Restore from backup
python scripts/memory_management.py restore backup_name
```

### Programmatic Access

```python
from src.memory.simple_memory import (
    create_memory_backup,
    restore_memory_from_backup,
    export_all_memory_to_github_format,
    reset_all_memory_to_baseline,
    create_memory_systems
)

# Create backup
backup_paths = create_memory_backup("my_backup")

# Export for GitHub
export_paths = export_all_memory_to_github_format()

# Create memory system instances
memory_systems = create_memory_systems()
```

## Version Control Strategy

### What's Tracked in Git:
- ✅ **Current runtime files**: `*_memory.json`, `episodic_memory.db`
- ✅ **Baseline files**: `*_baseline.json`
- ✅ **Export files**: `episodic_memory_export.json`, `memory_status.json`

### What's Excluded:
- ❌ **Backup directories**: `backups/` (excluded via `.gitignore`)
- ❌ **Temporary files**: Any processing artifacts

### Before Committing to Git:
1. Run the export command to ensure consistent formatting:
   ```bash
   python scripts/memory_management.py export
   ```
2. Check the status to ensure all files are present:
   ```bash
   python scripts/memory_management.py status
   ```

## Backup Strategy

### Automatic Backups
- Backups are created with timestamp names by default
- Each backup includes all memory types and a manifest
- Backups are stored in `backups/` (not version controlled)

### Manual Backups
```bash
# Create named backup
python scripts/memory_management.py backup --name "before_production_deployment"

# List available backups
python scripts/memory_management.py restore

# Restore specific backup
python scripts/memory_management.py restore "before_production_deployment"
```

## File Formats

### JSON Files (Semantic & Procedural)
- Human-readable JSON with 2-space indentation
- Sorted keys for consistent diffs
- Comments via `_metadata` fields where appropriate

### SQLite Database (Episodic)
- Compact binary format for runtime efficiency
- Exported to JSON for version control
- Schema automatically created on first use

## Recovery Procedures

### Complete System Reset
```bash
python scripts/memory_management.py reset --confirm
```

### Partial Recovery
```python
# Reset specific memory type
semantic = SimpleSemanticMemory()
semantic.reset_to_base_state()
```

### Backup Recovery
```bash
# List backups
python scripts/memory_management.py restore

# Restore from backup
python scripts/memory_management.py restore "backup_name"
```

## Development Guidelines

1. **Always backup before major changes**:
   ```bash
   python scripts/memory_management.py backup --name "before_$(date +%Y%m%d_%H%M)"
   ```

2. **Test changes with reset capability**:
   ```bash
   # Make changes, test, then reset if needed
   python scripts/memory_management.py reset
   ```

3. **Export before committing**:
   ```bash
   python scripts/memory_management.py export
   git add data/memory/
   ```

4. **Monitor memory growth**:
   ```bash
   python scripts/memory_management.py status
   ```

## Troubleshooting

### File Not Found Errors
- Check if baseline files exist
- Run export to recreate missing files
- Use status command to identify missing files

### Corruption Recovery
1. Stop the email agent
2. Restore from a known good backup
3. Or reset to baseline and rebuild

### Performance Issues
- Check database size with status command
- Consider cleanup of old episodic records
- Monitor memory usage during processing

## Integration Points

### Application Startup
- Memory systems are automatically initialized
- Baseline files are used if current files are missing
- Database schema is created automatically

### Runtime Operations
- Semantic memory: Asset matching, sender lookup
- Procedural memory: Rule evaluation, thresholds
- Episodic memory: Learning from feedback, pattern recognition

### Shutdown/Cleanup
- All changes are automatically persisted
- SQLite database is safely closed
- JSON files are written atomically
