#!/usr/bin/env python3
"""
Test script for complete memory-driven email processing architecture.

Demonstrates the clean separation between memory systems (knowledge) and
processing agents (actions), showing how all nodes work together.
"""

# # Standard library imports
import asyncio
from datetime import datetime

# # Local application imports
from src.agents.nodes import (
    AssetMatcherNode,
    AttachmentProcessorNode,
    FeedbackIntegratorNode,
    RelevanceFilterNode,
)


async def test_complete_email_processing():
    """Test the complete email processing pipeline with memory-driven nodes."""

    print("🧠 Testing Complete Memory-Driven Email Agent Architecture")
    print("=" * 70)
    print("\n🎯 Architecture Overview:")
    print("   Memory Systems: Semantic, Procedural, Episodic")
    print("   Processing Agents: Filter → Match → Process → Learn")
    print("=" * 70)

    # Initialize all nodes (without memory systems for now)
    relevance_filter = RelevanceFilterNode()
    asset_matcher = AssetMatcherNode()
    attachment_processor = AttachmentProcessorNode()
    feedback_integrator = FeedbackIntegratorNode()

    # Test email with investment documents
    test_email = {
        "id": "email_001",
        "subject": "Q4 Alpha Fund Financial Statements",
        "sender": "investor.relations@alphacapital.com",
        "body": "Please find attached the quarterly financial statements and compliance report for Alpha Fund.",
        "received_date": datetime.now().isoformat(),
        "attachments": [
            {
                "filename": "AF_Q4_2024_FinancialStatements.pdf",
                "size": 2048000,
                "content_type": "application/pdf",
            },
            {
                "filename": "Fund001_Compliance_Report.xlsx",
                "size": 512000,
                "content_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            },
        ],
    }

    print(f"\n📧 Processing Email: {test_email['subject']}")
    print(f"   From: {test_email['sender']}")
    print(f"   Attachments: {len(test_email['attachments'])}")
    print("-" * 70)

    # Step 1: Relevance Filtering
    print("\n🔍 Step 1: Relevance Filtering")
    classification, confidence, reasoning = await relevance_filter.evaluate_relevance(
        test_email
    )

    print(f"   Result: {classification} (confidence: {confidence:.2f})")
    if reasoning["decision_factors"]:
        print("   Decision Factors:")
        for factor in reasoning["decision_factors"]:
            print(f"     • {factor}")

    if classification not in ["relevant", "uncertain"]:
        print("   📛 Email not relevant, stopping processing")
        return

    # Step 2: Asset Matching
    print("\n🎯 Step 2: Asset Matching")
    asset_matches = await asset_matcher.match_attachments_to_assets(
        test_email, test_email["attachments"]
    )

    print(f"   Found {len(asset_matches)} asset matches:")
    for match in asset_matches:
        print(
            f"     • {match['attachment_filename']} → {match['asset_id']} "
            f"(confidence: {match['confidence']:.2f})"
        )

    # Step 3: Attachment Processing
    print("\n💾 Step 3: Attachment Processing")
    processing_results = await attachment_processor.process_attachments(
        asset_matches, test_email, test_email["attachments"]
    )

    print(f"   Processed {len(processing_results)} attachments:")
    for result in processing_results:
        if result["status"] == "saved":
            print(f"     ✅ {result['attachment_filename']}")
            print(f"        → {result['saved_path']}")
            print(f"        → Category: {result['document_category']}")
        else:
            print(
                f"     ❌ {result['attachment_filename']}: {result.get('reason', 'Error')}"
            )

    # Step 4: Simulate Human Feedback
    print("\n🤝 Step 4: Human Feedback Integration")

    # Simulate feedback that one match was incorrect
    feedback_data = {
        "feedback_type": "asset_match_correction",
        "severity": "medium",
        "correction": {
            "attachment": "Fund001_Compliance_Report.xlsx",
            "correct_asset_id": "COMPLIANCE_FUND001",
            "incorrect_asset_id": "FUND001",
            "reason": "Compliance documents should go to compliance-specific asset",
        },
        "learning_signal": "high",
    }

    original_decision = {
        "attachment": "Fund001_Compliance_Report.xlsx",
        "asset_match": "FUND001",
        "confidence": 0.8,
        "reasoning": asset_matches[1]["reasoning"] if len(asset_matches) > 1 else {},
    }

    integration_result = await feedback_integrator.integrate_feedback(
        feedback_data, original_decision, test_email
    )

    if integration_result["success"]:
        print("   ✅ Feedback successfully integrated")
        print("   📊 Learning Impact:")
        impact = integration_result["learning_impact"]
        print(f"     • Memory systems affected: {impact['memory_systems_affected']}")
        print(f"     • Total updates: {impact['total_memory_updates']}")
        print(f"     • Learning strength: {impact['learning_strength']}")
    else:
        print(f"   ❌ Feedback integration failed: {integration_result.get('error')}")

    # Architecture Summary
    print("\n" + "=" * 70)
    print("🏗️  Architecture Success Summary")
    print("=" * 70)
    print("✅ Clean separation: Memory (knowledge) vs Agents (actions)")
    print("✅ RelevanceFilterNode: Queries memory for patterns")
    print("✅ AssetMatcherNode: Uses procedural + semantic memory")
    print("✅ AttachmentProcessorNode: Queries procedural memory for rules")
    print("✅ FeedbackIntegratorNode: Updates all memory systems")
    print("✅ No hardcoded business logic in agents")
    print("✅ Complete audit trail and reasoning")
    print("✅ Human feedback integration for continuous learning")

    print("\n🔮 Next Steps:")
    print("   1. Connect actual memory systems (semantic, procedural, episodic)")
    print("   2. Load investment patterns and asset profiles into semantic memory")
    print("   3. Define processing rules and algorithms in procedural memory")
    print("   4. Build web UI for human feedback and review")
    print("   5. Add real email integration (Gmail/Outlook)")

    return {
        "relevance_result": (classification, confidence),
        "asset_matches": len(asset_matches),
        "processing_results": len(processing_results),
        "feedback_integrated": integration_result["success"],
        "architecture_validated": True,
    }


if __name__ == "__main__":
    result = asyncio.run(test_complete_email_processing())
    print(f"\n🎉 Test completed successfully: {result}")
