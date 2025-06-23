#!/usr/bin/env python3
"""
Load business rules from knowledge base into semantic memory.

This script loads comprehensive business rules including:
- Asset folder structure rules
- Confidence thresholds
- Classification fallback rules
- File processing rules
- Memory learning rules
- Data validation rules
- Integration rules
"""

# # Standard library imports
import asyncio
import json
import sys
from pathlib import Path

# Add src to Python path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# # Local application imports
from src.memory.semantic import KnowledgeConfidence, KnowledgeType, SemanticMemory
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


async def load_business_rules():
    """Load business rules from knowledge base into semantic memory."""
    logger.info("Loading business rules into semantic memory...")

    # Load business rules data
    rules_file = Path(__file__).parent.parent / "knowledge" / "business_rules.json"

    if not rules_file.exists():
        logger.error(f"Business rules file not found: {rules_file}")
        return False

    try:
        with open(rules_file, encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load business rules file: {e}")
        return False

    # Initialize semantic memory
    memory = SemanticMemory()
    rules_loaded = 0

    # Load asset folder structure rules
    if "asset_folder_structure" in data["business_rules"]:
        folder_rules = data["business_rules"]["asset_folder_structure"]

        for rule_set in folder_rules["rules"]:
            if rule_set["rule_type"] == "standard_folders":
                # Load standard folder requirements
                for folder_info in rule_set["folders"]:
                    await memory.add(
                        content=f"Asset folder: {folder_info['name']} - {folder_info['description']}",
                        metadata={
                            "type": "business_rule",
                            "rule_category": "asset_folder_structure",
                            "rule_type": "standard_folder",
                            "folder_name": folder_info["name"],
                            "description": folder_info["description"],
                            "required": folder_info["required"],
                            "priority": folder_info["priority"],
                            "source": "knowledge_base",
                        },
                        knowledge_type=KnowledgeType.RULE,
                        confidence=KnowledgeConfidence.HIGH,
                    )
                    rules_loaded += 1

            elif rule_set["rule_type"] == "asset_type_specific":
                # Load asset type specific folder structures
                for asset_type, folders in rule_set.items():
                    if asset_type == "rule_type":
                        continue

                    await memory.add(
                        content=f"Asset type {asset_type} folder structure",
                        metadata={
                            "type": "business_rule",
                            "rule_category": "asset_folder_structure",
                            "rule_type": "asset_type_specific",
                            "asset_type": asset_type,
                            "folders": folders,
                            "source": "knowledge_base",
                        },
                        knowledge_type=KnowledgeType.RULE,
                        confidence=KnowledgeConfidence.HIGH,
                    )
                    rules_loaded += 1

    # Load confidence thresholds
    if "confidence_thresholds" in data["business_rules"]:
        thresholds = data["business_rules"]["confidence_thresholds"]

        for category, threshold_data in thresholds.items():
            if category == "description":
                continue

            await memory.add(
                content=f"Confidence thresholds for {category}",
                metadata={
                    "type": "business_rule",
                    "rule_category": "confidence_thresholds",
                    "threshold_category": category,
                    "thresholds": threshold_data,
                    "source": "knowledge_base",
                },
                knowledge_type=KnowledgeType.RULE,
                confidence=KnowledgeConfidence.HIGH,
            )
            rules_loaded += 1

    # Load classification fallback rules
    if "classification_fallback_rules" in data["business_rules"]:
        fallback_rules = data["business_rules"]["classification_fallback_rules"]

        for rule in fallback_rules["rules"]:
            await memory.add(
                content=f"Classification fallback: {rule['condition']} -> {rule['action']}",
                metadata={
                    "type": "business_rule",
                    "rule_category": "classification_fallback",
                    "condition": rule["condition"],
                    "action": rule["action"],
                    "rule_details": rule,
                    "source": "knowledge_base",
                },
                knowledge_type=KnowledgeType.RULE,
                confidence=KnowledgeConfidence.HIGH,
            )
            rules_loaded += 1

    # Load file processing rules
    if "file_processing_rules" in data["business_rules"]:
        file_rules = data["business_rules"]["file_processing_rules"]

        # Load allowed extensions
        await memory.add(
            content="File processing: allowed extensions",
            metadata={
                "type": "business_rule",
                "rule_category": "file_processing",
                "rule_type": "allowed_extensions",
                "extensions": file_rules["allowed_extensions"],
                "source": "knowledge_base",
            },
            knowledge_type=KnowledgeType.RULE,
            confidence=KnowledgeConfidence.HIGH,
        )
        rules_loaded += 1

        # Load suspicious extensions
        await memory.add(
            content="File processing: suspicious extensions",
            metadata={
                "type": "business_rule",
                "rule_category": "file_processing",
                "rule_type": "suspicious_extensions",
                "extensions": file_rules["suspicious_extensions"],
                "source": "knowledge_base",
            },
            knowledge_type=KnowledgeType.RULE,
            confidence=KnowledgeConfidence.HIGH,
        )
        rules_loaded += 1

        # Load size limits
        await memory.add(
            content="File processing: size limits",
            metadata={
                "type": "business_rule",
                "rule_category": "file_processing",
                "rule_type": "size_limits",
                "limits": file_rules["size_limits"],
                "source": "knowledge_base",
            },
            knowledge_type=KnowledgeType.RULE,
            confidence=KnowledgeConfidence.HIGH,
        )
        rules_loaded += 1

        # Load processing priorities
        await memory.add(
            content="File processing: priority keywords and patterns",
            metadata={
                "type": "business_rule",
                "rule_category": "file_processing",
                "rule_type": "processing_priorities",
                "priorities": file_rules["processing_priorities"],
                "source": "knowledge_base",
            },
            knowledge_type=KnowledgeType.RULE,
            confidence=KnowledgeConfidence.HIGH,
        )
        rules_loaded += 1

    # Load memory learning rules
    if "memory_learning_rules" in data["business_rules"]:
        learning_rules = data["business_rules"]["memory_learning_rules"]

        for rule_type, rule_data in learning_rules.items():
            if rule_type == "description":
                continue

            await memory.add(
                content=f"Memory learning: {rule_type}",
                metadata={
                    "type": "business_rule",
                    "rule_category": "memory_learning",
                    "rule_type": rule_type,
                    "rule_data": rule_data,
                    "source": "knowledge_base",
                },
                knowledge_type=KnowledgeType.RULE,
                confidence=KnowledgeConfidence.HIGH,
            )
            rules_loaded += 1

    # Load data validation rules
    if "data_validation_rules" in data["business_rules"]:
        validation_rules = data["business_rules"]["data_validation_rules"]

        for rule_type, rule_data in validation_rules.items():
            if rule_type == "description":
                continue

            await memory.add(
                content=f"Data validation: {rule_type}",
                metadata={
                    "type": "business_rule",
                    "rule_category": "data_validation",
                    "rule_type": rule_type,
                    "validation_rules": rule_data,
                    "source": "knowledge_base",
                },
                knowledge_type=KnowledgeType.RULE,
                confidence=KnowledgeConfidence.HIGH,
            )
            rules_loaded += 1

    # Load integration rules
    if "integration_rules" in data["business_rules"]:
        integration_rules = data["business_rules"]["integration_rules"]

        for rule_type, rule_data in integration_rules.items():
            if rule_type == "description":
                continue

            await memory.add(
                content=f"Integration rules: {rule_type}",
                metadata={
                    "type": "business_rule",
                    "rule_category": "integration",
                    "rule_type": rule_type,
                    "integration_config": rule_data,
                    "source": "knowledge_base",
                },
                knowledge_type=KnowledgeType.RULE,
                confidence=KnowledgeConfidence.HIGH,
            )
            rules_loaded += 1

    logger.info(
        f"Successfully loaded {rules_loaded} business rules into semantic memory"
    )
    return True


if __name__ == "__main__":
    print("📋 Loading Business Rules into Memory")
    print("====================================")
    print()
    print("⚠️  This will add business rules to semantic memory.")
    print("   Only run this when:")
    print("   - Setting up a new system")
    print("   - Updating business rules")
    print("   - Resetting after testing")
    print()

    response = input("Continue? (y/N): ").strip().lower()
    if response != "y":
        print("❌ Operation cancelled")
        sys.exit(0)

    try:
        success = asyncio.run(load_business_rules())
        if success:
            print("✅ Business rules loaded successfully!")
        else:
            print("❌ Failed to load business rules")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Error loading business rules: {e}")
        sys.exit(1)
