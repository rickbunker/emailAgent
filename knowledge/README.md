# Knowledge Base for Email Agent Memory System

This directory contains JSON files that serve as the knowledge base for the Email Agent's memory systems. These files are used to seed the semantic memory with essential patterns, rules, and configurations that the system needs to operate effectively.

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