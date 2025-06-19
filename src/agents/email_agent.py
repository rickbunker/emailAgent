"""This module has been deprecated.

The old monolithic AssetDocumentAgent has been replaced with a modular
asset management system. Please update your imports to use:

- src.asset_management.processing.document_processor.DocumentProcessor
- src.asset_management.identification.asset_identifier.AssetIdentifier
- src.asset_management.classification.document_classifier.DocumentClassifier

For migration guidance, see docs/ASSET_MANAGEMENT_REWRITE_PROGRESS.md
"""

raise ImportError(
    "The email_agent module has been deprecated. "
    "Please use the new modular asset management system instead."
)
