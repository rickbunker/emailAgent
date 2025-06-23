#!/usr/bin/env python3
"""
Load file type validation rules into semantic memory.

This script adds file type validation rules to allow common business document types
that are essential for asset management workflows.
"""

# # Standard library imports
import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Local application imports
from src.memory.semantic import KnowledgeConfidence, SemanticMemory
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


async def load_file_type_validation():
    """Load file type validation rules into semantic memory."""
    print("=" * 60)
    print("Loading File Type Validation Rules")
    print("=" * 60)

    try:
        # Initialize semantic memory
        semantic_memory = SemanticMemory()

        # Define allowed file types for asset management
        file_type_rules = {
            # Document formats - ESSENTIAL for asset management
            "pdf": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Portable Document Format - primary document type for asset management",
                "document_categories": [
                    "loan_documents",
                    "financial_statements",
                    "compliance_certificates",
                ],
            },
            "doc": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Microsoft Word document",
                "document_categories": ["correspondence", "agreements", "amendments"],
            },
            "docx": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Microsoft Word document (newer format)",
                "document_categories": ["correspondence", "agreements", "amendments"],
            },
            # Spreadsheet formats - ESSENTIAL for financial data
            "xlsx": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Microsoft Excel spreadsheet",
                "document_categories": [
                    "borrower_financials",
                    "rent_rolls",
                    "cash_flow",
                ],
            },
            "xls": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Microsoft Excel spreadsheet (older format)",
                "document_categories": [
                    "borrower_financials",
                    "rent_rolls",
                    "cash_flow",
                ],
            },
            "csv": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Comma-separated values file",
                "document_categories": [
                    "data_exports",
                    "transaction_lists",
                    "reporting",
                ],
            },
            # Presentation formats - for investor materials
            "ppt": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Microsoft PowerPoint presentation",
                "document_categories": ["investor_materials", "asset_summaries"],
            },
            "pptx": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Microsoft PowerPoint presentation (newer format)",
                "document_categories": ["investor_materials", "asset_summaries"],
            },
            # Text formats - for correspondence and notes
            "txt": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Plain text file",
                "document_categories": ["correspondence", "notes", "data_files"],
            },
            "rtf": {
                "is_allowed": True,
                "security_level": "safe",
                "description": "Rich Text Format",
                "document_categories": ["correspondence", "formatted_documents"],
            },
            # Image formats - LIMITED use for diagrams/scans
            "png": {
                "is_allowed": True,
                "security_level": "standard",
                "description": "Portable Network Graphics image",
                "document_categories": ["document_scans", "diagrams", "screenshots"],
            },
            "jpg": {
                "is_allowed": True,
                "security_level": "standard",
                "description": "JPEG image format",
                "document_categories": ["document_scans", "property_photos"],
            },
            "jpeg": {
                "is_allowed": True,
                "security_level": "standard",
                "description": "JPEG image format",
                "document_categories": ["document_scans", "property_photos"],
            },
            # Archive formats - BLOCKED for security
            "zip": {
                "is_allowed": False,
                "security_level": "dangerous",
                "description": "ZIP archive - blocked for security",
                "document_categories": [],
            },
            "rar": {
                "is_allowed": False,
                "security_level": "dangerous",
                "description": "RAR archive - blocked for security",
                "document_categories": [],
            },
            # Executable formats - BLOCKED for security
            "exe": {
                "is_allowed": False,
                "security_level": "dangerous",
                "description": "Executable file - blocked for security",
                "document_categories": [],
            },
            "bat": {
                "is_allowed": False,
                "security_level": "dangerous",
                "description": "Batch file - blocked for security",
                "document_categories": [],
            },
            "scr": {
                "is_allowed": False,
                "security_level": "dangerous",
                "description": "Screen saver file - blocked for security",
                "document_categories": [],
            },
        }

        # Load each file type rule into semantic memory using the existing method
        loaded_count = 0
        for extension, rules in file_type_rules.items():
            try:
                # Use the existing add_file_type_knowledge method
                await semantic_memory.add_file_type_knowledge(
                    file_extension=extension,
                    content=rules["description"],
                    is_allowed=rules["is_allowed"],
                    asset_types=["private_credit"],  # Default asset type
                    document_categories=rules["document_categories"],
                    security_level=rules["security_level"],
                    confidence=KnowledgeConfidence.HIGH,
                )

                loaded_count += 1
                status = "✅ ALLOWED" if rules["is_allowed"] else "❌ BLOCKED"
                print(f"{status} .{extension:<6} - {rules['description']}")

            except Exception as e:
                print(f"❌ ERROR loading .{extension}: {e}")

        print(f"\n{'='*60}")
        print(f"✅ Successfully loaded {loaded_count} file type validation rules")
        print("📋 Key allowed types: PDF, DOCX, XLSX (essential for asset management)")
        print("🔒 Blocked types: EXE, ZIP, RAR (security risks)")
        print(f"{'='*60}")

    except Exception as e:
        print(f"❌ Failed to load file type validation rules: {e}")
        # # Standard library imports
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(load_file_type_validation())
