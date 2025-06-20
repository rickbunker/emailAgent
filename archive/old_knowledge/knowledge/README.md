# Email Agent Knowledge Base

This directory contains the extracted domain knowledge from the legacy hardcoded `asset_document_agent.py` system, converted into structured JSON files for use with the new memory-driven architecture.

## 📋 Knowledge Files

### Core Classification Knowledge
- **`classification_patterns.json`** - Document classification regex patterns (95 patterns)
- **`asset_keywords.json`** - Asset type identification keywords
- **`asset_configs.json`** - File validation rules and size limits by asset type
- **`business_rules.json`** - Confidence adjustments, routing logic, and business rules

### Adaptive Security Knowledge
- **`file_type_validation.json`** - File type validation rules with learning patterns - replaces hardcoded file extensions with adaptive semantic memory-driven validation

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

## 📊 Expected Seeding Results

When running Smart Memory Reset, expect these pattern counts:
- **Classification patterns**: 24 pattern groups (4 asset types × 6 categories avg)
- **Asset keywords**: 4 keyword sets
- **Business rules**: 9 rules (4 confidence + 5 routing)
- **Asset configs**: 4 configurations
- **Total**: ~41 patterns loaded into procedural memory

## 🔍 Knowledge Base Validation

### Quick Validation Commands
```bash
# Count classification patterns
cat knowledge/classification_patterns.json | jq '.classification_patterns | to_entries | map(.value | to_entries | map(.value | length)) | flatten | add'

# Count asset keywords
cat knowledge/asset_keywords.json | jq '.asset_keywords | keys | length'

# Count business rules
cat knowledge/business_rules.json | jq '(.confidence_adjustments | keys | length) + (.routing_decisions | keys | length)'

# Count asset configs
cat knowledge/asset_configs.json | jq '.asset_configs | keys | length'
```

### Expected Counts
- Classification patterns: **112 regex patterns**
- Asset keywords: **4 asset types**
- Business rules: **9 rules**
- Asset configs: **4 configurations**
- **Total items**: 129

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

## ⚠️ Critical Notes

- **This knowledge base IS the source code** for the learning system
- **Changes should be tested** before committing to production
- **Smart Memory Reset** relies on these files being complete and valid
- **Backup before major changes** - this enables disaster recovery
- **Version control is essential** - track all business rule changes

---

**This knowledge base represents years of accumulated domain expertise in private market asset management, now preserved as maintainable, version-controlled source code.**
