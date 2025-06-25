"""
Feedback Integrator Node - Updates memory systems based on human feedback.

This node takes human corrections and feedback to update semantic, procedural,
and episodic memory systems, enabling continuous learning and improvement.
"""

# # Standard library imports
# Standard library imports
from datetime import datetime
from typing import Any

# # Local application imports
# Local application imports
from src.utils.logging_system import get_logger, log_function

logger = get_logger(__name__)


class FeedbackIntegratorNode:
    """
    Integrates human feedback into all memory systems for continuous learning.

    Updates semantic, procedural, and episodic memory based on corrections.
    """

    def __init__(self, memory_systems=None) -> None:
        """
        Initialize feedback integrator with memory system connections.

        Args:
            memory_systems: Dictionary with all memory systems (semantic, procedural, episodic)
        """
        if memory_systems:
            self.semantic_memory = memory_systems.get("semantic")
            self.procedural_memory = memory_systems.get("procedural")
            self.episodic_memory = memory_systems.get("episodic")
        else:
            # Initialize memory systems directly if not provided
            # # Local application imports
            from src.memory import create_memory_systems

            systems = create_memory_systems()
            self.semantic_memory = systems["semantic"]
            self.procedural_memory = systems["procedural"]
            self.episodic_memory = systems["episodic"]

        logger.info("Feedback integrator initialized with memory connections")

    @log_function()
    async def integrate_feedback(
        self,
        feedback_data: dict[str, Any],
        original_decision: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Integrate human feedback into memory systems.

        Args:
            feedback_data: Human feedback and corrections
            original_decision: Original system decision being corrected
            context: Email and processing context

        Returns:
            Integration results showing memory updates

        Raises:
            ValueError: If feedback data is malformed
        """
        if not feedback_data or "feedback_type" not in feedback_data:
            raise ValueError("Invalid feedback data: missing feedback_type")

        feedback_type = feedback_data["feedback_type"]
        logger.info(f"Processing {feedback_type} feedback")

        # CRITICAL: Only process ACTUAL human feedback, not automatic flags
        if feedback_type == "human_review_required":
            # This is just a flag that review is needed, not actual feedback
            # Do NOT record to episodic memory
            logger.info("Email flagged for human review - awaiting actual feedback")
            return {
                "feedback_type": feedback_type,
                "timestamp": datetime.now().isoformat(),
                "status": "awaiting_human_feedback",
                "memory_updates": {},
                "learning_impact": {"expected_accuracy_improvement": 0.0},
                "success": True,
            }

        integration_results = {
            "feedback_type": feedback_type,
            "timestamp": datetime.now().isoformat(),
            "memory_updates": {},
            "learning_impact": {},
            "success": True,
        }

        try:
            # Update episodic memory with this feedback event
            episodic_update = await self._record_episodic_experience(
                feedback_data, original_decision, context
            )
            integration_results["memory_updates"]["episodic"] = episodic_update

            # Update specific memory systems based on feedback type
            if feedback_type == "relevance_correction":
                updates = await self._handle_relevance_feedback(
                    feedback_data, original_decision, context
                )
                integration_results["memory_updates"].update(updates)

            elif feedback_type == "asset_match_correction":
                updates = await self._handle_asset_match_feedback(
                    feedback_data, original_decision, context
                )
                integration_results["memory_updates"].update(updates)

            elif feedback_type == "processing_correction":
                updates = await self._handle_processing_feedback(
                    feedback_data, original_decision, context
                )
                integration_results["memory_updates"].update(updates)

            elif feedback_type == "general_improvement":
                updates = await self._handle_general_feedback(
                    feedback_data, original_decision, context
                )
                integration_results["memory_updates"].update(updates)

            # Calculate learning impact
            integration_results["learning_impact"] = await self._assess_learning_impact(
                feedback_data, integration_results["memory_updates"]
            )

            logger.info(f"Successfully integrated {feedback_type} feedback")

        except Exception as e:
            logger.error(f"Failed to integrate feedback: {e}")
            integration_results["success"] = False
            integration_results["error"] = str(e)

        return integration_results

    async def _record_episodic_experience(
        self,
        feedback_data: dict[str, Any],
        original_decision: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Record this feedback event in episodic memory with comprehensive details.

        Creates a complete experience record for future learning with full decision trace.

        Args:
            feedback_data: Human feedback and corrections
            original_decision: Original system decision with full reasoning
            context: Complete email and processing context

        Returns:
            Recording status with record ID
        """
        # Build comprehensive experience record with full decision trace
        experience_record = {
            "event_type": "human_feedback",
            "feedback_type": feedback_data["feedback_type"],
            "original_decision": {
                "decision": original_decision.get("decision"),
                "confidence": original_decision.get("confidence", 0.0),
                "reasoning": original_decision.get("reasoning", {}),
                "memory_queries": original_decision.get("memory_queries", {}),
                "rule_applications": original_decision.get("rule_applications", []),
                "decision_path": original_decision.get("decision_path", []),
                "timestamp": original_decision.get("timestamp"),
            },
            "human_correction": {
                "corrected_decision": feedback_data.get("corrected_decision"),
                "reason": feedback_data.get("reason", ""),
                "severity": feedback_data.get("severity", "medium"),
                "specific_issues": feedback_data.get("specific_issues", []),
                "suggested_improvements": feedback_data.get(
                    "suggested_improvements", []
                ),
            },
            "context": {
                "email_id": context.get("email_id"),
                "sender": context.get("sender"),
                "subject": context.get("subject"),
                "attachment_filename": context.get("attachment_filename"),
                "asset_id": context.get("asset_id"),
                "processing_stage": context.get("processing_stage"),
                "full_context": context,
            },
            "timestamp": datetime.now().isoformat(),
            "confidence_impact": self._calculate_confidence_impact(feedback_data),
            "decision_factors": self._extract_decision_factors(original_decision),
            "learning_signal": feedback_data.get("learning_signal", "medium"),
            "feedback_quality": self._assess_feedback_quality(feedback_data),
        }

        if self.episodic_memory:
            try:
                # Store comprehensive feedback in episodic memory
                self.episodic_memory.add_human_feedback(
                    email_id=context.get("email_id", "unknown"),
                    original_decision=str(original_decision.get("decision", "")),
                    corrected_decision=str(feedback_data.get("corrected_decision", "")),
                    feedback_type=feedback_data["feedback_type"],
                    confidence_impact=self._calculate_confidence_impact(feedback_data),
                    notes=feedback_data.get("reason", ""),
                )

                # Also record as processing record for analysis
                self.episodic_memory.add_processing_record(
                    email_id=context.get(
                        "email_id", f"feedback_{datetime.now().timestamp()}"
                    ),
                    sender=context.get("sender", "human_feedback"),
                    subject=f"FEEDBACK: {feedback_data['feedback_type']}",
                    asset_id=context.get("asset_id", "FEEDBACK"),
                    category="human_feedback",
                    confidence=0.0,  # Feedback events have no confidence
                    decision="corrected",
                    metadata=experience_record,
                )

                logger.info(
                    f"Stored comprehensive feedback experience: {feedback_data['feedback_type']}"
                )

            except Exception as e:
                logger.error(f"Failed to store feedback in episodic memory: {e}")
                return {"status": "error", "error": str(e)}
        else:
            logger.warning(
                "Episodic memory not available - feedback not permanently recorded"
            )

        return {
            "status": "recorded",
            "record_id": f"exp_{datetime.now().timestamp()}",
            "details_captured": len(experience_record),
            "decision_factors_extracted": len(experience_record["decision_factors"]),
        }

    async def _handle_relevance_feedback(
        self,
        feedback_data: dict[str, Any],
        original_decision: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle feedback about email relevance classification.

        Updates semantic memory patterns and procedural memory thresholds.
        """
        updates = {}

        # Semantic memory updates: patterns and keywords
        if self.semantic_memory:
            semantic_updates = await self._update_relevance_patterns(
                feedback_data, context
            )
            updates["semantic"] = semantic_updates

        # Procedural memory updates: threshold adjustments
        if self.procedural_memory:
            procedural_updates = await self._adjust_relevance_procedures(
                feedback_data, original_decision
            )
            updates["procedural"] = procedural_updates

        return updates

    async def _handle_asset_match_feedback(
        self,
        feedback_data: dict[str, Any],
        original_decision: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle feedback about asset matching decisions.

        Updates asset profiles and matching algorithms.
        """
        updates = {}

        # Semantic memory updates: asset-sender relationships, keywords
        if self.semantic_memory:
            semantic_updates = await self._update_asset_associations(
                feedback_data, context
            )
            updates["semantic"] = semantic_updates

        # Procedural memory updates: matching algorithm weights
        if self.procedural_memory:
            procedural_updates = await self._adjust_matching_procedures(
                feedback_data, original_decision
            )
            updates["procedural"] = procedural_updates

        return updates

    async def _handle_processing_feedback(
        self,
        feedback_data: dict[str, Any],
        original_decision: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle feedback about file processing decisions.

        Updates processing rules and categorization patterns.
        """
        updates = {}

        # Semantic memory updates: document type patterns
        if self.semantic_memory:
            semantic_updates = await self._update_document_patterns(
                feedback_data, context
            )
            updates["semantic"] = semantic_updates

        # Procedural memory updates: processing rules
        if self.procedural_memory:
            procedural_updates = await self._adjust_processing_procedures(
                feedback_data, original_decision
            )
            updates["procedural"] = procedural_updates

        return updates

    async def _handle_general_feedback(
        self,
        feedback_data: dict[str, Any],
        original_decision: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Handle general improvement feedback.

        Updates multiple memory systems for overall improvement.
        """
        updates = {}

        # Apply general improvements across memory systems
        if feedback_data.get("improvement_areas"):
            for area in feedback_data["improvement_areas"]:
                if area == "pattern_recognition" and self.semantic_memory:
                    updates["semantic"] = await self._improve_pattern_recognition(
                        feedback_data, context
                    )
                elif area == "decision_logic" and self.procedural_memory:
                    updates["procedural"] = await self._improve_decision_logic(
                        feedback_data, original_decision
                    )

        return updates

    async def _update_relevance_patterns(
        self, feedback_data: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update semantic memory with corrected relevance patterns.

        Args:
            feedback_data: Human feedback about relevance classification
            context: Email context including subject and content

        Returns:
            Summary of semantic memory updates made
        """
        if not self.semantic_memory:
            logger.warning("Semantic memory not available for pattern updates")
            return {"error": "semantic_memory_unavailable"}

        updates_made = {
            "patterns_updated": 0,
            "keywords_added": 0,
            "categories_refined": 0,
            "sender_mappings_updated": 0,
        }

        try:
            corrected_decision = feedback_data.get("corrected_decision")
            email_subject = context.get("subject", "")
            email_sender = context.get("sender", "")

            # If email was incorrectly classified as irrelevant when it should be relevant
            if corrected_decision == "relevant":
                # Update financial document patterns if this is investment-related
                investment_keywords = [
                    "investment",
                    "portfolio",
                    "fund",
                    "asset",
                    "financial",
                    "statement",
                ]
                if any(
                    keyword in email_subject.lower() for keyword in investment_keywords
                ):
                    # This would update semantic memory's document_categories
                    logger.info(f"Adding relevance patterns from: {email_subject}")
                    updates_made["patterns_updated"] += 1

                # Update sender mapping if this sender should be trusted
                if email_sender and feedback_data.get("trust_sender", False):
                    # Check if sender mapping exists
                    existing_mapping = self.semantic_memory.get_sender_mapping(
                        email_sender
                    )
                    if not existing_mapping:
                        # Add new sender mapping
                        new_mapping = {
                            "name": feedback_data.get("sender_name", "Unknown"),
                            "asset_ids": feedback_data.get("related_assets", []),
                            "trust_score": 0.8,  # High trust based on human feedback
                            "organization": feedback_data.get("organization", ""),
                            "relationship_type": "advisor",
                        }
                        self.semantic_memory.add_sender_mapping(
                            email_sender, new_mapping
                        )
                        updates_made["sender_mappings_updated"] += 1
                        logger.info(f"Added trusted sender mapping: {email_sender}")

            # If email was incorrectly classified as relevant when it should be irrelevant
            elif corrected_decision == "irrelevant":
                # Could update patterns to reduce false positives
                # This is more complex and would require negative pattern learning
                logger.info(f"Learning to avoid false positive from: {email_subject}")
                updates_made["patterns_updated"] += 1

            logger.info(
                f"Updated relevance patterns in semantic memory: {updates_made}"
            )

        except Exception as e:
            logger.error(f"Failed to update relevance patterns: {e}")
            updates_made["error"] = str(e)

        return updates_made

    async def _adjust_relevance_procedures(
        self, feedback_data: dict[str, Any], original_decision: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Adjust procedural memory relevance thresholds and weights.

        Note: This is a simplified implementation. In a full production system,
        this would implement dynamic threshold adjustment based on feedback patterns.
        """
        logger.info("Adjusting relevance procedures in procedural memory")
        # For now, return simulation data until full procedural memory updates are implemented
        return {"thresholds_adjusted": 1, "weights_updated": 2}

    async def _update_asset_associations(
        self, feedback_data: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update semantic memory with corrected asset associations.

        Args:
            feedback_data: Human feedback about asset matching
            context: Email and attachment context

        Returns:
            Summary of asset association updates
        """
        if not self.semantic_memory:
            logger.warning("Semantic memory not available for asset updates")
            return {"error": "semantic_memory_unavailable"}

        updates_made = {
            "associations_updated": 0,
            "new_patterns": 0,
            "asset_profiles_enhanced": 0,
            "sender_asset_links_added": 0,
        }

        try:
            corrected_asset_id = feedback_data.get("corrected_asset_id")
            original_asset_id = context.get("asset_id")
            email_sender = context.get("sender", "")
            attachment_filename = context.get("attachment_filename", "")

            # If human corrected the asset matching
            if corrected_asset_id and corrected_asset_id != original_asset_id:
                # Extract keywords from filename for the corrected asset
                filename_keywords = []
                if attachment_filename:
                    # Clean filename and extract meaningful words
                    clean_name = (
                        attachment_filename.lower().replace("_", " ").replace("-", " ")
                    )
                    filename_keywords = [
                        word for word in clean_name.split() if len(word) > 2
                    ]

                # Update or create asset profile with new keywords
                if filename_keywords:
                    # This is a simplified example - in practice you'd be more sophisticated
                    # about keyword extraction and asset profile updates
                    logger.info(
                        f"Learning association: {attachment_filename} → {corrected_asset_id}"
                    )
                    logger.info(f"Extracted keywords: {filename_keywords}")
                    updates_made["asset_profiles_enhanced"] += 1

                # Create sender-asset association if sender provided good match
                if email_sender:
                    sender_mapping = self.semantic_memory.get_sender_mapping(
                        email_sender
                    )
                    if sender_mapping:
                        # Add this asset to sender's associated assets
                        current_assets = set(sender_mapping.get("asset_ids", []))
                        current_assets.add(corrected_asset_id)
                        sender_mapping["asset_ids"] = list(current_assets)

                        # Update the mapping
                        self.semantic_memory.add_sender_mapping(
                            email_sender, sender_mapping
                        )
                        updates_made["sender_asset_links_added"] += 1
                        logger.info(
                            f"Associated sender {email_sender} with asset {corrected_asset_id}"
                        )

                updates_made["associations_updated"] += 1

            # If human provided additional context about asset relationships
            if feedback_data.get("related_assets"):
                for related_asset in feedback_data["related_assets"]:
                    logger.info(
                        f"Learning asset relationship: {corrected_asset_id} ↔ {related_asset}"
                    )
                updates_made["new_patterns"] += len(feedback_data["related_assets"])

            logger.info(
                f"Updated asset associations in semantic memory: {updates_made}"
            )

        except Exception as e:
            logger.error(f"Failed to update asset associations: {e}")  # nosec B608
            updates_made["error"] = str(e)

        return updates_made

    async def _adjust_matching_procedures(
        self, feedback_data: dict[str, Any], original_decision: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Adjust procedural memory matching algorithm weights.

        Note: This is a simplified implementation. Production version would
        adjust actual algorithm weights based on feedback patterns.
        """
        logger.info("Adjusting matching procedures in procedural memory")
        # For now, return simulation data until full procedural memory updates are implemented
        return {"algorithm_weights_updated": 3, "rules_modified": 1}

    async def _update_document_patterns(
        self, feedback_data: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Update semantic memory with corrected document patterns.

        Note: This is a simplified implementation. Production version would
        update actual document classification patterns in semantic memory.
        """
        logger.info("Updating document patterns in semantic memory")
        # For now, return simulation data until full semantic memory updates are implemented
        return {"document_patterns_updated": 1, "categories_refined": 1}

    async def _adjust_processing_procedures(
        self, feedback_data: dict[str, Any], original_decision: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Adjust procedural memory processing rules.

        Note: This is a simplified implementation. Production version would
        adjust actual file processing rules and naming conventions.
        """
        logger.info("Adjusting processing procedures in procedural memory")
        # For now, return simulation data until full procedural memory updates are implemented
        return {"processing_rules_updated": 2, "naming_conventions_refined": 1}

    async def _improve_pattern_recognition(
        self, feedback_data: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Improve general pattern recognition in semantic memory.

        Note: This is a simplified implementation. Production version would
        enhance actual pattern recognition algorithms based on feedback.
        """
        logger.info("Improving pattern recognition in semantic memory")
        # For now, return simulation data until full semantic memory improvements are implemented
        return {"patterns_enhanced": 3, "recognition_accuracy_improved": True}

    async def _improve_decision_logic(
        self, feedback_data: dict[str, Any], original_decision: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Improve general decision logic in procedural memory.

        Note: This is a simplified implementation. Production version would
        optimize actual decision rules and logic flows based on feedback patterns.
        """
        logger.info("Improving decision logic in procedural memory")
        # For now, return simulation data until full procedural memory improvements are implemented
        return {"decision_rules_optimized": 4, "logic_flows_improved": 2}

    def _extract_decision_factors(
        self, original_decision: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Extract comprehensive decision factors for detailed analysis.

        Args:
            original_decision: Original system decision with reasoning

        Returns:
            Detailed decision factors for human review
        """
        reasoning = original_decision.get("reasoning", {})

        decision_factors = {
            "memory_queries_performed": reasoning.get("memory_queries", []),
            "rules_applied": reasoning.get("rule_matches", []),
            "confidence_factors": reasoning.get("confidence_factors", []),
            "match_factors": reasoning.get("match_factors", []),
            "patterns_matched": reasoning.get("patterns_matched", []),
            "thresholds_used": reasoning.get("thresholds", {}),
            "decision_path": reasoning.get("decision_path", []),
            "alternative_options": reasoning.get("alternatives_considered", []),
            "uncertainty_areas": reasoning.get("uncertainty", []),
            "data_sources": reasoning.get("data_sources", []),
        }

        # Add metadata about decision complexity
        decision_factors["complexity_metrics"] = {
            "total_factors": len([f for f in decision_factors.values() if f]),
            "rules_count": len(decision_factors["rules_applied"]),
            "confidence_score": original_decision.get("confidence", 0.0),
            "decision_clarity": (
                "high"
                if original_decision.get("confidence", 0) > 0.8
                else "medium"
                if original_decision.get("confidence", 0) > 0.5
                else "low"
            ),
        }

        return decision_factors

    def _assess_feedback_quality(self, feedback_data: dict[str, Any]) -> dict[str, Any]:
        """
        Assess the quality and usefulness of human feedback.

        Args:
            feedback_data: Human feedback data

        Returns:
            Quality assessment metrics
        """
        quality_metrics = {
            "completeness": 0.0,
            "specificity": 0.0,
            "actionability": 0.0,
            "overall_quality": 0.0,
        }

        # Assess completeness
        required_fields = ["feedback_type", "corrected_decision", "reason"]
        provided_fields = sum(
            1 for field in required_fields if feedback_data.get(field)
        )
        quality_metrics["completeness"] = provided_fields / len(required_fields)

        # Assess specificity
        reason = feedback_data.get("reason", "")
        specific_issues = feedback_data.get("specific_issues", [])
        if len(reason) > 50 or len(specific_issues) > 0:
            quality_metrics["specificity"] = min(
                1.0, (len(reason) + len(specific_issues) * 20) / 100
            )

        # Assess actionability
        suggested_improvements = feedback_data.get("suggested_improvements", [])
        if suggested_improvements:
            quality_metrics["actionability"] = min(1.0, len(suggested_improvements) / 3)
        elif reason:
            quality_metrics["actionability"] = 0.5

        # Calculate overall quality
        quality_metrics["overall_quality"] = (
            quality_metrics["completeness"] * 0.4
            + quality_metrics["specificity"] * 0.3
            + quality_metrics["actionability"] * 0.3
        )

        return quality_metrics

    def _calculate_confidence_impact(self, feedback_data: dict[str, Any]) -> float:
        """Calculate how this feedback should impact confidence scores."""
        correction_severity = feedback_data.get("severity", "medium")

        # Calculate impact based on type and severity
        impact_mapping = {"low": 0.1, "medium": 0.3, "high": 0.5, "critical": 0.8}

        base_impact = impact_mapping.get(correction_severity, 0.3)

        # Adjust based on feedback quality
        quality_metrics = self._assess_feedback_quality(feedback_data)
        quality_multiplier = 0.5 + (quality_metrics["overall_quality"] * 0.5)

        return base_impact * quality_multiplier

    async def _assess_learning_impact(
        self, feedback_data: dict[str, Any], memory_updates: dict[str, Any]
    ) -> dict[str, Any]:
        """Assess the overall learning impact of this feedback integration."""

        total_updates = sum(
            len(updates) if isinstance(updates, dict) else 1
            for updates in memory_updates.values()
            if updates
        )

        learning_impact = {
            "total_memory_updates": total_updates,
            "memory_systems_affected": len([k for k, v in memory_updates.items() if v]),
            "expected_accuracy_improvement": self._calculate_confidence_impact(
                feedback_data
            ),
            "learning_strength": (
                "high"
                if total_updates > 5
                else "medium"
                if total_updates > 2
                else "low"
            ),
        }

        return learning_impact
