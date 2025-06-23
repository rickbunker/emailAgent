"""
Agent Nodes Package - Individual LangGraph node implementations.

This package contains the processing nodes that make up the email processing graph.
Each node follows clean architecture with proper separation between memory systems
(intelligence/knowledge) and processing agents (actions/operations).

## Memory Systems (What We Know)
- Semantic Memory: Asset profiles, keywords, patterns, relationships
- Procedural Memory: Rules, algorithms, procedures for HOW to do things
- Episodic Memory: Historical decisions, human feedback, experiences

## Processing Agents (What We Do)
- RelevanceFilterNode: Determines email relevance using memory-driven patterns
- AssetMatcherNode: Matches attachments to assets using procedural + semantic memory
- AttachmentProcessorNode: Saves files using procedural memory rules
- FeedbackIntegratorNode: Updates all memory systems based on human feedback
"""

from .asset_matcher import AssetMatcherNode
from .attachment_processor import AttachmentProcessorNode
from .feedback_integrator import FeedbackIntegratorNode
from .relevance_filter import RelevanceFilterNode

__all__ = [
    "RelevanceFilterNode",
    "AssetMatcherNode",
    "AttachmentProcessorNode",
    "FeedbackIntegratorNode",
]
