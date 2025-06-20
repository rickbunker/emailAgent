# Knowledge Base Directory

This directory contains JSON files that store base rule sets and patterns for the Email Agent's memory systems. These files serve as the foundation for initializing the memory systems and can be used to reset or re-seed the memory when needed.

## Memory Type Guidelines

- **Semantic Memory**: Facts about asset types, file types, spam keywords, and other general factual information
- **Procedural Memory**: General "how to do things" information and processes
- **Episodic Memory**: Feedback from processing, primarily from human interaction, used to fine-tune the combination of procedural and semantic memory

## Pattern Files

### spam_patterns.json
- **Memory Type**: Semantic (factual patterns about spam)
- **Description**: Spam detection patterns including keywords, regex patterns, phishing indicators, blacklists, and suspicious TLDs
- **Load Script**: `scripts/load_spam_patterns.py`
- **Used By**: `src/agents/spam_detector.py`

### contact_patterns.json
- **Memory Type**: Semantic (factual patterns about contacts)
- **Description**: Contact extraction patterns for identifying real humans vs. automated systems, including no-reply patterns, bulk domains, and personal/automated indicators
- **Load Script**: `scripts/load_contact_patterns.py`
- **Used By**: `src/agents/contact_extractor.py`

### asset_types.json
- **Memory Type**: Semantic (facts about asset types and categories)
- **Description**: Asset types, document categories, and file validation rules for the private market asset management system
- **Load Script**: `scripts/load_asset_types.py`
- **Used By**: Asset management system components

## Loading Patterns

To load all patterns into memory:

```bash
# Load spam patterns
python scripts/load_spam_patterns.py

# Load contact patterns
python scripts/load_contact_patterns.py

# Load asset types
python scripts/load_asset_types.py
```

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