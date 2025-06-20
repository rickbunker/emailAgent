# Email Agent Knowledge Base

This directory contains the structured knowledge definitions that power the Email Agent's memory-based systems. These JSON files serve as the "source code" for the agent's knowledge, which is loaded into vector memory for runtime use.

## Knowledge Files

### Core Pattern Files

#### ✅ `spam_patterns.json` (COMPLETE)
**Purpose**: Spam detection and email classification patterns
**Memory Type**: Semantic Memory
**Status**: Fully migrated from hardcoded patterns
**Contains**:
- Spam keywords and phrases for content analysis
- Urgency indicators and financial scam patterns
- Credential harvesting attempt detection
- TLD-based suspicious domain patterns
- Content analysis thresholds and scoring rules

#### ✅ `contact_patterns.json` (COMPLETE)
**Purpose**: Contact extraction and human vs. automated system detection
**Memory Type**: Semantic Memory
**Status**: Fully migrated from hardcoded patterns
**Contains**:
- No-reply email address patterns
- Bulk email domain blacklists
- Personal vs. automated content indicators
- Local part indicators for system accounts
- Signature markers for email parsing
- Contact classification terms (family, business, vendor)
- Organization and job title extraction patterns
- Extraction configuration thresholds

#### ✅ `asset_types.json` (COMPLETE)
**Purpose**: Asset type definitions and document categorization
**Memory Type**: Semantic Memory
**Status**: Fully migrated from hardcoded enums
**Contains**:
- Private market asset type definitions
- Document category classifications with keywords
- File type validation rules (allowed/suspicious extensions)
- Asset identifier patterns for document routing

## Memory Type Guidelines

When creating or updating knowledge patterns, use these guidelines for memory type classification:

### Semantic Memory (Facts & Patterns)
- Asset types and their characteristics
- File type definitions and validation rules
- Spam detection keywords and patterns
- Contact extraction patterns
- Domain classifications
- General factual information that doesn't change based on user experience

### Procedural Memory (How-To Knowledge)
- Step-by-step processes and workflows
- Decision trees and routing logic
- General "how to do things" information
- Process templates and procedures

### Episodic Memory (Experience-Based Learning)
- Feedback from email processing operations
- Human review decisions and corrections
- User interaction history
- Context-specific learning that improves over time
- Fine-tuning data for other memory types

## Loading Patterns into Memory

### Production Usage
The Email Agent automatically loads patterns from memory during normal operation. Memory persists across restarts and continuously learns from user interactions.

### Development/Testing
Use the initialization scripts to load patterns:

```bash
# Load all patterns
python -m scripts.load_all_patterns

# Load specific pattern types
python -m scripts.load_spam_patterns
python -m scripts.load_contact_patterns
python -m scripts.load_asset_types

# Initialize fresh memory (⚠️ NEVER in production)
python -m scripts.initialize_memory
```

## Pattern File Structure

Each JSON file follows this structure:
```json
{
  "pattern_category": {
    "description": "Human-readable description",
    "patterns": [
      {
        "pattern": "actual_pattern_or_value",
        "confidence": 0.8,
        "description": "What this pattern detects"
      }
    ]
  }
}
```

## Migration Status

### ✅ Completed Migrations
- **Spam Detection**: All spam patterns migrated from hardcoded to memory-based
- **Contact Extraction**: Complete migration including signature markers, contact classification, and organization patterns
- **Asset Types**: Asset type enums and document categories migrated to memory
- **Infrastructure**: Memory loading and initialization framework established

### 🔄 Next Priority Areas
Based on business value assessment:

1. **Asset Service Business Rules**: Folder structure, organization rules, validation logic
2. **Email Processing Security**: Security patterns, compliance detection, suspicious activity rules
3. **Business Process Rules**: Document validation, classification thresholds, workflow rules

## Best Practices

1. **Version Control**: Treat JSON files as source code - commit all changes
2. **Testing**: Test pattern changes in development before production deployment
3. **Documentation**: Always include meaningful descriptions for new patterns
4. **Memory Persistence**: Remember that production memory learns and evolves - never reset without backup
5. **Incremental Updates**: Add new patterns incrementally rather than bulk replacements

## Architecture Notes

- **JSON Files**: Source code for knowledge (version controlled)
- **Memory Systems**: Runtime knowledge storage (persistent, learning)
- **Loading Scripts**: "Compilation" process from JSON to memory
- **Production Memory**: Never reset - contains valuable learned patterns and user feedback

## Pattern Structure

Each JSON file follows a consistent structure:

```json
{
    "metadata": {
        "description": "...",
        "version": "1.0.0",
        "created_date": "YYYY-MM-DD",
        "source": "...",
        "notes": "..."
    },
    "pattern_category": {
        "description": "...",
        "patterns": [...]
    }
}
```

## Version Control

These JSON files are under source control because they represent the base configuration of the system. Changes to these files should be carefully reviewed as they affect the fundamental behavior of the Email Agent.

## Human Feedback

While these files provide the initial patterns, the system learns and improves through human feedback stored in episodic memory. The patterns in these files serve as a baseline that can be enhanced over time through use.

## Overview

The Email Agent uses a memory-based architecture where all patterns, rules, and configurations are stored in semantic memory rather than being hardcoded. This approach provides several benefits:

- **Dynamic Updates**: Patterns can be modified without changing code
- **Learning Capability**: The system learns from user feedback to improve accuracy
- **Centralized Management**: All knowledge is in one place
- **Version Control**: Changes to patterns are tracked in git

## Knowledge Files

### 1. `spam_patterns.json`
Contains spam detection patterns including:
- **Spam Keywords**: Common spam words with confidence scores
- **Regex Patterns**: Suspicious content patterns
- **Phishing Indicators**: Patterns indicating phishing attempts
- **Blacklists**: DNS blacklist servers for reputation checking
- **Suspicious TLDs**: Top-level domains commonly used in spam
- **Learning Configuration**: Parameters for pattern effectiveness learning

### 2. `asset_data.json`
Contains asset management information including:
- Asset identifiers and metadata
- Deal names and relationships
- Business context information

## Loading Knowledge into Memory

To load knowledge from these JSON files into semantic memory, use the provided scripts:

```bash
# Load spam patterns
python scripts/load_spam_patterns.py

# Future: Load other knowledge types
# python scripts/load_asset_data.py
```

## How the System Works

### 1. Initial Loading
When the system starts, agents check if their required patterns are loaded in memory. If not, they operate with default/empty patterns.

### 2. Pattern Usage
Agents query semantic memory for patterns:
```python
patterns = await semantic_memory.search(
    query="spam pattern",
    limit=200,
    knowledge_type=KnowledgeType.PATTERN
)
```

### 3. Learning from Feedback
When users mark emails as spam/not spam, the system:
- Records the feedback
- Identifies which patterns matched
- Adjusts pattern confidence scores
- Stores the adjustments in memory

### 4. Pattern Effectiveness
Each pattern has:
- **Confidence Score**: How reliable the pattern is (0.0-1.0)
- **Weight**: How much it contributes to the overall score
- **Category**: Type of pattern (spam, phishing, etc.)

## Adding New Patterns

To add new patterns:

1. Edit the appropriate JSON file
2. Add your pattern with required fields:
   ```json
   {
       "word": "new_spam_word",
       "confidence": 0.7,
       "category": "promotional",
       "weight": 2.0
   }
   ```
3. Run the loading script to update memory
4. The system will automatically use the new patterns

## Pattern Evolution

The system tracks pattern effectiveness over time:
- Patterns that correctly identify spam get confidence boosts
- Patterns that cause false positives get confidence reductions
- Patterns below minimum confidence are eventually ignored
- New patterns can be discovered through user feedback

## Best Practices

1. **Conservative Confidence**: Start new patterns with lower confidence (0.5-0.7)
2. **Descriptive Categories**: Use clear category names for pattern grouping
3. **Regular Reviews**: Periodically review pattern effectiveness
4. **Backup Before Changes**: Always backup JSON files before major changes
5. **Test After Loading**: Verify patterns loaded correctly after updates

## Future Enhancements

- Automatic pattern discovery from user feedback
- Pattern effectiveness dashboards
- Automated pattern pruning for low-performing patterns
- Pattern versioning and rollback capabilities
- Cross-pattern correlation analysis

## Troubleshooting

### Patterns Not Loading
- Check Qdrant is running: `docker ps | grep qdrant`
- Verify JSON syntax: `python -m json.tool spam_patterns.json`
- Check logs: `tail -f logs/emailagent.log`

### Pattern Not Matching
- Verify pattern loaded: Use semantic memory search
- Check confidence threshold in agent code
- Review pattern syntax (especially regex escaping)

### Performance Issues
- Limit pattern count (keep under 500 per type)
- Optimize regex patterns for efficiency
- Consider pattern consolidation for similar matches
