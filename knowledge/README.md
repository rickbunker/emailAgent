# Email Agent Knowledge Base

This directory contains the extracted domain knowledge from the legacy hardcoded `asset_document_agent.py` system, converted into structured JSON files for use with the new memory-driven architecture.

## 📋 Knowledge Files

### Core Classification Knowledge
- **`classification_patterns.json`** - Document classification regex patterns (95 patterns)
- **`asset_keywords.json`** - Asset type identification keywords
- **`asset_configs.json`** - File validation rules and size limits by asset type
- **`business_rules.json`** - Confidence adjustments, routing logic, and business rules

## 🎯 Purpose

This knowledge base serves multiple critical functions:

1. **Procedural Memory Seeding** - Initialize the learning system with proven patterns
2. **Disaster Recovery** - Rebuild memory from known-good domain knowledge
3. **Version Control** - Track changes to business logic as source code
4. **Knowledge Transfer** - Move learned patterns between environments
5. **Compliance** - Maintain auditable decision logic

## 🔄 Usage Pattern

```python
# Load knowledge into procedural memory
await procedural_memory.seed_from_knowledge_base("./knowledge/")

# Verify seeding
stats = await procedural_memory.get_pattern_stats()
print(f"Loaded {stats['pattern_count']} classification patterns")
```

## 📊 Extraction Summary

**From Legacy System:**
- **2,788 lines** of hardcoded patterns and logic
- **100+ regex patterns** for document classification
- **48 asset keywords** for type identification
- **4 asset type configs** with validation rules
- **Complex business logic** for confidence and routing

**To Knowledge Base:**
- **4 structured JSON files** with metadata
- **Version-controlled** business rules
- **Searchable and maintainable** pattern library
- **Seeding system** for rapid deployment

## 🚀 Benefits

### Before: Hardcoded Anti-Patterns
- ❌ Business rules embedded in code
- ❌ Regex patterns scattered throughout
- ❌ Magic numbers and thresholds
- ❌ Code changes needed for new patterns
- ❌ No learning or adaptation

### After: Knowledge-Driven System
- ✅ Business rules as data
- ✅ Organized, searchable patterns
- ✅ Configurable thresholds
- ✅ Learning system that adapts
- ✅ Version-controlled domain knowledge

## 📈 Evolution Strategy

1. **Seed** procedural memory with this knowledge base
2. **Monitor** classification performance and accuracy
3. **Learn** from human corrections and successful processing
4. **Export** improved patterns back to knowledge base
5. **Version** the knowledge base as business rules evolve

## 🔧 Maintenance

- **Review patterns quarterly** for business relevance
- **Add new patterns** from successful classifications
- **Remove outdated patterns** that cause false positives
- **Update thresholds** based on performance metrics
- **Document changes** with business justification

---

**This knowledge base represents years of accumulated domain expertise in private market asset management, now preserved as maintainable, version-controlled source code.**
