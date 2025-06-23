"""
Email Processing Graph using LangGraph.

This module implements a simple, effective email processing workflow using
LangGraph's graph-based architecture. Focuses on clarity and maintainability
over complexity.
"""

# # Standard library imports
from datetime import datetime
from typing import Literal, TypedDict

# # Third-party imports
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

# # Local application imports
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


# Define the state structure for our email processing graph
class EmailState(TypedDict):
    """State maintained throughout email processing workflow."""

    # Email information
    email_id: str
    subject: str
    sender: str
    body: str
    attachments: list[dict]
    received_date: datetime

    # Processing state
    classification: str  # spam/important/normal
    confidence: float
    asset_matches: list[dict]  # Matched assets for attachments
    document_categories: list[dict]  # Document type classifications

    # Decision tracking
    needs_human_review: bool
    processing_errors: list[str]
    processing_complete: bool

    # Actions taken
    actions: list[str]  # List of actions performed


class EmailProcessingGraph:
    """
    LangGraph-based email processing agent.

    Implements a simple workflow:
    1. Classify email (spam/important/normal)
    2. Extract and analyze attachments
    3. Match attachments to assets
    4. Categorize documents
    5. Route to appropriate folders
    6. Flag for human review if needed
    """

    def __init__(self):
        """Initialize the email processing graph."""
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Create the graph
        self.workflow = StateGraph(EmailState)

        # Add nodes
        self.workflow.add_node("classify_email", self.classify_email)
        self.workflow.add_node("process_attachments", self.process_attachments)
        self.workflow.add_node("match_assets", self.match_assets)
        self.workflow.add_node("categorize_documents", self.categorize_documents)
        self.workflow.add_node("route_documents", self.route_documents)
        self.workflow.add_node("human_review", self.flag_human_review)

        # Add edges
        self.workflow.add_edge("classify_email", "process_attachments")
        self.workflow.add_edge("process_attachments", "match_assets")
        self.workflow.add_edge("match_assets", "categorize_documents")

        # Conditional routing after categorization
        self.workflow.add_conditional_edges(
            "categorize_documents",
            self.should_review,
            {"review": "human_review", "route": "route_documents"},
        )

        # End states
        self.workflow.add_edge("route_documents", END)
        self.workflow.add_edge("human_review", END)

        # Set entry point
        self.workflow.set_entry_point("classify_email")

        # Compile with memory for persistence
        self.checkpointer = MemorySaver()
        self.app = self.workflow.compile(checkpointer=self.checkpointer)

        self.logger.info("Email processing graph initialized")

    @log_function()
    async def classify_email(self, state: EmailState) -> EmailState:
        """
        Classify email as spam, important, or normal.

        Simple keyword-based classification to start.
        """
        self.logger.info(f"Classifying email: {state['subject']}")

        # Simple classification logic
        subject_lower = state["subject"].lower()
        body_lower = state["body"].lower()
        combined = f"{subject_lower} {body_lower}"

        # Check for spam indicators
        spam_keywords = [
            "viagra",
            "lottery",
            "winner",
            "click here now",
            "limited time offer",
        ]
        if any(kw in combined for kw in spam_keywords):
            state["classification"] = "spam"
            state["confidence"] = 0.9
            state["actions"].append("Classified as spam")
            return state

        # Check for important indicators
        important_keywords = ["urgent", "deadline", "compliance", "regulatory", "audit"]
        if any(kw in combined for kw in important_keywords):
            state["classification"] = "important"
            state["confidence"] = 0.8
            state["actions"].append("Classified as important")
            return state

        # Default to normal
        state["classification"] = "normal"
        state["confidence"] = 0.7
        state["actions"].append("Classified as normal")

        return state

    @log_function()
    async def process_attachments(self, state: EmailState) -> EmailState:
        """Extract and validate attachments."""
        self.logger.info(f"Processing {len(state['attachments'])} attachments")

        # Skip if spam
        if state["classification"] == "spam":
            state["actions"].append("Skipped attachment processing (spam)")
            return state

        # Validate attachments
        valid_extensions = [".pdf", ".xlsx", ".docx", ".csv"]
        for attachment in state["attachments"]:
            filename = attachment.get("filename", "")
            ext = filename.lower().split(".")[-1] if "." in filename else ""

            if f".{ext}" in valid_extensions:
                attachment["valid"] = True
                attachment["file_type"] = ext
            else:
                attachment["valid"] = False
                state["processing_errors"].append(f"Invalid file type: {filename}")

        state["actions"].append(f"Processed {len(state['attachments'])} attachments")
        return state

    @log_function()
    async def match_assets(self, state: EmailState) -> EmailState:
        """Match attachments to known assets using simple pattern matching."""
        self.logger.info("Matching attachments to assets")

        # Simple asset matching based on filename patterns
        # In real implementation, this would query your asset database
        asset_patterns = {
            "FUND001": ["fund001", "alpha fund", "af_"],
            "FUND002": ["fund002", "beta fund", "bf_"],
            "RE001": ["re001", "property alpha", "pa_"],
        }

        matches = []
        for attachment in state["attachments"]:
            if not attachment.get("valid", False):
                continue

            filename_lower = attachment["filename"].lower()

            for asset_id, patterns in asset_patterns.items():
                if any(pattern in filename_lower for pattern in patterns):
                    matches.append(
                        {
                            "attachment": attachment["filename"],
                            "asset_id": asset_id,
                            "confidence": 0.8,
                        }
                    )
                    break

        state["asset_matches"] = matches
        state["actions"].append(f"Matched {len(matches)} attachments to assets")

        # Flag for review if no matches
        if state["attachments"] and not matches:
            state["needs_human_review"] = True

        return state

    @log_function()
    async def categorize_documents(self, state: EmailState) -> EmailState:
        """Categorize documents by type."""
        self.logger.info("Categorizing documents")

        # Simple document categorization based on keywords
        categories = []
        for attachment in state["attachments"]:
            if not attachment.get("valid", False):
                continue

            filename_lower = attachment["filename"].lower()

            # Simple pattern matching for document types
            if any(kw in filename_lower for kw in ["financial", "statement", "fs_"]):
                category = "financial_statements"
            elif any(kw in filename_lower for kw in ["compliance", "covenant"]):
                category = "compliance_documents"
            elif any(kw in filename_lower for kw in ["report", "update"]):
                category = "reports"
            else:
                category = "other"

            categories.append(
                {
                    "attachment": attachment["filename"],
                    "category": category,
                    "confidence": 0.7,
                }
            )

        state["document_categories"] = categories
        state["actions"].append(f"Categorized {len(categories)} documents")

        # Flag for review if low confidence
        if any(cat["confidence"] < 0.6 for cat in categories):
            state["needs_human_review"] = True

        return state

    def should_review(self, state: EmailState) -> Literal["review", "route"]:
        """Determine if human review is needed."""
        if state["needs_human_review"] or state["confidence"] < 0.6:
            return "review"
        return "route"

    @log_function()
    async def route_documents(self, state: EmailState) -> EmailState:
        """Route documents to appropriate folders."""
        self.logger.info("Routing documents to folders")

        # In real implementation, this would move files to asset folders
        routing_actions = []
        for match in state["asset_matches"]:
            for cat in state["document_categories"]:
                if match["attachment"] == cat["attachment"]:
                    routing_actions.append(
                        f"Route {match['attachment']} to "
                        f"{match['asset_id']}/{cat['category']}"
                    )

        state["actions"].extend(routing_actions)
        state["processing_complete"] = True

        return state

    @log_function()
    async def flag_human_review(self, state: EmailState) -> EmailState:
        """Flag email for human review."""
        self.logger.info("Flagging for human review")

        state["actions"].append("Flagged for human review")
        state["processing_complete"] = True

        return state

    async def process_email(self, email_data: dict) -> dict:
        """
        Process a single email through the graph.

        Args:
            email_data: Dictionary with email information

        Returns:
            Final state after processing
        """
        # Initialize state
        initial_state = EmailState(
            email_id=email_data.get("id", ""),
            subject=email_data.get("subject", ""),
            sender=email_data.get("sender", ""),
            body=email_data.get("body", ""),
            attachments=email_data.get("attachments", []),
            received_date=email_data.get("received_date", datetime.now()),
            classification="",
            confidence=0.0,
            asset_matches=[],
            document_categories=[],
            needs_human_review=False,
            processing_errors=[],
            processing_complete=False,
            actions=[],
        )

        # Run through the graph
        config = {"configurable": {"thread_id": email_data.get("id", "default")}}
        final_state = await self.app.ainvoke(initial_state, config)

        return final_state


def create_email_agent() -> EmailProcessingGraph:
    """Factory function to create an email processing agent."""
    return EmailProcessingGraph()
