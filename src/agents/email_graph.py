"""
Email Processing Graph using LangGraph with Memory-Driven Architecture.

This module implements a sophisticated, memory-driven email processing workflow
using LangGraph's graph-based architecture with our advanced memory systems.
All business logic is stored in memory rather than hardcoded.
"""

# # Standard library imports
from datetime import datetime
from typing import Literal, TypedDict

# # Third-party imports
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

# # Local application imports
from src.agents.nodes.asset_matcher import AssetMatcherNode
from src.agents.nodes.attachment_processor import AttachmentProcessorNode
from src.agents.nodes.feedback_integrator import FeedbackIntegratorNode
from src.agents.nodes.relevance_filter import RelevanceFilterNode
from src.memory import create_memory_systems
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

    # Memory-driven processing results
    relevance_result: dict  # From RelevanceFilterNode
    asset_matches: list[dict]  # From AssetMatcherNode
    processing_results: list[dict]  # From AttachmentProcessorNode

    # Decision tracking (complete audit trail for human review)
    decision_factors: list[dict]  # Detailed decision reasoning
    memory_queries: list[dict]  # Memory system queries made
    rule_applications: list[dict]  # Procedural rules applied
    confidence_factors: list[dict]  # Confidence calculations

    # Processing state
    needs_human_review: bool
    processing_errors: list[str]
    processing_complete: bool

    # Human feedback integration
    feedback_updates: list[dict]  # Memory updates from human corrections
    learning_impact: dict  # Quantified improvement from feedback

    # Actions taken
    actions: list[str]  # List of actions performed


class EmailProcessingGraph:
    """
    Memory-driven LangGraph email processing agent.

    Implements a sophisticated workflow powered by semantic, procedural, and
    episodic memory systems. All business logic is stored in memory rather
    than hardcoded, enabling continuous learning and adaptation.

    Workflow:
    1. Evaluate email relevance (RelevanceFilterNode with memory)
    2. Match attachments to assets (AssetMatcherNode with memory + learning)
    3. Process and categorize attachments (AttachmentProcessorNode with memory)
    4. Integrate human feedback (FeedbackIntegratorNode for continuous improvement)
    """

    def __init__(self):
        """Initialize the memory-driven email processing graph."""
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")

        # Initialize memory systems
        self.logger.info("Initializing memory systems for email processing")
        memory_systems = create_memory_systems()
        self.semantic_memory = memory_systems["semantic"]
        self.procedural_memory = memory_systems["procedural"]
        self.episodic_memory = memory_systems["episodic"]

        # Initialize memory-driven agent nodes
        self.relevance_filter = RelevanceFilterNode(memory_systems=memory_systems)

        self.asset_matcher = AssetMatcherNode(memory_systems=memory_systems)

        self.attachment_processor = AttachmentProcessorNode(
            memory_systems=memory_systems
        )

        self.feedback_integrator = FeedbackIntegratorNode(memory_systems=memory_systems)

        # Create the graph
        self.workflow = StateGraph(EmailState)

        # Add memory-driven nodes
        self.workflow.add_node("evaluate_relevance", self.evaluate_relevance)
        self.workflow.add_node("match_assets", self.match_assets)
        self.workflow.add_node("process_attachments", self.process_attachments)
        self.workflow.add_node("integrate_feedback", self.integrate_feedback)

        # Add edges
        self.workflow.add_edge("evaluate_relevance", "match_assets")
        self.workflow.add_edge("match_assets", "process_attachments")

        # Conditional routing after processing
        self.workflow.add_conditional_edges(
            "process_attachments",
            self.should_integrate_feedback,
            {"feedback": "integrate_feedback", "complete": END},
        )

        # End states
        self.workflow.add_edge("integrate_feedback", END)

        # Set entry point
        self.workflow.set_entry_point("evaluate_relevance")

        # Compile with memory for persistence
        self.checkpointer = MemorySaver()
        self.app = self.workflow.compile(checkpointer=self.checkpointer)

        self.logger.info("Memory-driven email processing graph initialized")

    @log_function()
    async def evaluate_relevance(self, state: EmailState) -> EmailState:
        """
        Evaluate email relevance using memory-driven RelevanceFilterNode.

        Leverages semantic memory patterns and procedural memory rules
        to determine if the email is relevant to our investment focus.
        """
        self.logger.info(f"Evaluating relevance for email: {state['subject']}")

        try:
            # Prepare email data for relevance evaluation
            email_data = {
                "subject": state["subject"],
                "sender": state["sender"],
                "body": state["body"],
                "attachments": state["attachments"],
                "received_date": state["received_date"],
            }

            # Use memory-driven relevance evaluation
            (
                classification,
                confidence,
                reasoning,
            ) = await self.relevance_filter.evaluate_relevance(email_data)

            # Package results in expected format
            relevance_result = {
                "relevance": classification,
                "confidence": confidence,
                "reasoning": reasoning,
                "decision_factors": reasoning.get("decision_factors", []),
                "confidence_factors": reasoning.get("confidence_factors", []),
                "memory_queries": [],  # Would be populated in more advanced implementation
                "rule_applications": [],  # Would be populated in more advanced implementation
            }

            # Store detailed results
            state["relevance_result"] = relevance_result
            state["decision_factors"].extend(relevance_result["decision_factors"])
            state["memory_queries"].extend(relevance_result["memory_queries"])
            state["rule_applications"].extend(relevance_result["rule_applications"])
            state["confidence_factors"].extend(relevance_result["confidence_factors"])

            # Add processing action
            state["actions"].append(
                f"Memory-driven relevance evaluation: {classification} (confidence: {confidence:.2f})"
            )

            # Flag for review if low confidence
            if confidence < 0.6:  # This could be stored in procedural memory
                state["needs_human_review"] = True
                state["actions"].append(
                    "Flagged for human review due to low confidence"
                )

            return state

        except Exception as e:
            self.logger.error(f"Relevance evaluation failed: {e}")
            state["processing_errors"].append(f"Relevance evaluation error: {e}")
            state["needs_human_review"] = True
            return state

    @log_function()
    async def match_assets(self, state: EmailState) -> EmailState:
        """
        Match attachments to assets using memory-driven AssetMatcherNode.

        Uses semantic memory asset profiles, procedural memory matching rules,
        and episodic memory for learning from past successful matches.
        """
        self.logger.info(f"Matching assets for {len(state['attachments'])} attachments")

        try:
            # Skip if not relevant
            if state["relevance_result"].get("relevance") == "irrelevant":
                state["actions"].append("Skipped asset matching (email not relevant)")
                state["asset_matches"] = []
                return state

            # Prepare attachment data for matching
            email_context = {
                "subject": state["subject"],
                "sender": state["sender"],
                "body": state["body"],
                "received_date": state["received_date"],
            }

            # Use memory-driven asset matching
            matching_result = await self.asset_matcher.match_attachments_to_assets(
                email_context, state["attachments"]
            )

            # Store detailed results
            state["asset_matches"] = matching_result.get("matches", [])
            state["decision_factors"].extend(
                matching_result.get("decision_factors", [])
            )
            state["memory_queries"].extend(matching_result.get("memory_queries", []))
            state["rule_applications"].extend(
                matching_result.get("rule_applications", [])
            )
            state["confidence_factors"].extend(
                matching_result.get("confidence_factors", [])
            )

            # Add processing action
            match_count = len(state["asset_matches"])
            state["actions"].append(
                f"Memory-driven asset matching: {match_count} matches found"
            )

            # Flag for review if no matches found for attachments
            if state["attachments"] and not state["asset_matches"]:
                state["needs_human_review"] = True
                state["actions"].append(
                    "Flagged for human review - no asset matches found"
                )

            return state

        except Exception as e:
            self.logger.error(f"Asset matching failed: {e}")
            state["processing_errors"].append(f"Asset matching error: {e}")
            state["needs_human_review"] = True
            return state

    @log_function()
    async def process_attachments(self, state: EmailState) -> EmailState:
        """
        Process attachments using memory-driven AttachmentProcessorNode.

        Uses semantic memory for document categorization and procedural
        memory for file processing rules, security checks, and organization.
        """
        self.logger.info(f"Processing {len(state['attachments'])} attachments")

        try:
            # Skip if no attachments
            if not state["attachments"]:
                state["actions"].append("No attachments to process")
                state["processing_results"] = []
                state["processing_complete"] = True
                return state

            # Prepare context for processing
            email_context = {
                "subject": state["subject"],
                "sender": state["sender"],
                "body": state["body"],
                "received_date": state["received_date"],
            }

            # Use memory-driven attachment processing
            processing_result = await self.attachment_processor.process_attachments(
                state["asset_matches"], email_context, state["attachments"]
            )

            # Store detailed results
            state["processing_results"] = processing_result.get("results", [])
            state["decision_factors"].extend(
                processing_result.get("decision_factors", [])
            )
            state["memory_queries"].extend(processing_result.get("memory_queries", []))
            state["rule_applications"].extend(
                processing_result.get("rule_applications", [])
            )
            state["confidence_factors"].extend(
                processing_result.get("confidence_factors", [])
            )

            # Add processing actions
            processed_count = len(
                [r for r in state["processing_results"] if r.get("status") == "saved"]
            )
            failed_count = len(
                [
                    r
                    for r in state["processing_results"]
                    if r.get("status") in ["error", "blocked"]
                ]
            )
            state["actions"].append(
                f"Memory-driven attachment processing: {processed_count} processed, {failed_count} failed"
            )

            # Flag for review if processing errors
            if failed_count > 0:
                state["needs_human_review"] = True
                state["actions"].append(
                    "Flagged for human review due to processing failures"
                )

            # Check if processing complete
            state["processing_complete"] = True

            return state

        except Exception as e:
            self.logger.error(f"Attachment processing failed: {e}")
            state["processing_errors"].append(f"Attachment processing error: {e}")
            state["needs_human_review"] = True
            return state

    def should_integrate_feedback(
        self, state: EmailState
    ) -> Literal["feedback", "complete"]:
        """
        Determine if feedback integration is needed.

        Triggers feedback integration for human review cases to capture
        corrections and integrate them into memory systems for learning.
        """
        if state["needs_human_review"]:
            return "feedback"
        return "complete"

    @log_function()
    async def integrate_feedback(self, state: EmailState) -> EmailState:
        """
        Integrate human feedback using FeedbackIntegratorNode.

        Captures human corrections and updates memory systems to improve
        future decision-making through continuous learning.
        """
        self.logger.info("Integrating human feedback for continuous learning")

        try:
            # Prepare comprehensive decision context for feedback
            decision_context = {
                "email_data": {
                    "subject": state["subject"],
                    "sender": state["sender"],
                    "body": state["body"],
                    "attachments": state["attachments"],
                    "received_date": state["received_date"],
                },
                "relevance_result": state["relevance_result"],
                "asset_matches": state["asset_matches"],
                "processing_results": state["processing_results"],
                "decision_factors": state["decision_factors"],
                "memory_queries": state["memory_queries"],
                "rule_applications": state["rule_applications"],
                "confidence_factors": state["confidence_factors"],
            }

            # Note: In a real implementation, human feedback would be collected
            # through a web interface. For now, we prepare for feedback integration.
            feedback_data = {
                "requires_human_input": True,
                "decision_context": decision_context,
                "feedback_type": "human_review_required",
            }

            # Integrate feedback (this will record the need for human review)
            feedback_result = await self.feedback_integrator.integrate_feedback(
                feedback_data, decision_context, decision_context
            )

            # Store feedback integration results
            state["feedback_updates"] = feedback_result.get("memory_updates", [])
            state["learning_impact"] = feedback_result.get("learning_impact", {})

            # Add processing action
            state["actions"].append("Prepared for human feedback integration")

            return state

        except Exception as e:
            self.logger.error(f"Feedback integration failed: {e}")
            state["processing_errors"].append(f"Feedback integration error: {e}")
            return state

    async def process_email(self, email_data: dict) -> dict:
        """
        Process a single email through the memory-driven graph.

        Args:
            email_data: Dictionary with email information

        Returns:
            Final state after processing with complete decision audit trail
        """
        # Initialize state with memory-driven architecture
        initial_state = EmailState(
            email_id=email_data.get("id", ""),
            subject=email_data.get("subject", ""),
            sender=email_data.get("sender", ""),
            body=email_data.get("body", ""),
            attachments=email_data.get("attachments", []),
            received_date=email_data.get("received_date", datetime.now()),
            # Memory-driven results (will be populated)
            relevance_result={},
            asset_matches=[],
            processing_results=[],
            # Decision tracking for human review
            decision_factors=[],
            memory_queries=[],
            rule_applications=[],
            confidence_factors=[],
            # Processing state
            needs_human_review=False,
            processing_errors=[],
            processing_complete=False,
            # Feedback integration
            feedback_updates=[],
            learning_impact={},
            # Actions taken
            actions=[],
        )

        # Run through the memory-driven graph
        config = {"configurable": {"thread_id": email_data.get("id", "default")}}
        final_state = await self.app.ainvoke(initial_state, config)

        return final_state


def create_email_agent() -> EmailProcessingGraph:
    """Factory function to create a memory-driven email processing agent."""
    return EmailProcessingGraph()
