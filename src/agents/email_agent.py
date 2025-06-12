"""Legacy compatibility wrapper for tests and scripts that still import EmailAgent.

Provides `EmailAgent` as an alias for `AssetDocumentAgent` so that legacy
code (e.g. old test suites) continues to work without modification.
"""

from .asset_document_agent import AssetDocumentAgent as EmailAgent

__all__: list[str] = ["EmailAgent"]
