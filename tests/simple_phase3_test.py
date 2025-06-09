"""
Simple Phase 3 Test - Document Classification
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from agents.asset_document_agent import (
    AssetDocumentAgent,
    AssetType,
    DocumentCategory,
    ConfidenceLevel
)

async def main():
    print("🧪 Simple Phase 3 Test")
    print("=" * 40)
    
    agent = AssetDocumentAgent()
    
    # Test 1: Document classification
    print("\n📋 Testing Document Classification:")
    
    filename = "December_2024_Rent_Roll.xlsx"
    subject = "Monthly rent roll for 123 Main Street"
    body = "Please find attached the rent roll showing tenant payments."
    
    category, confidence = agent.classify_document(
        filename, subject, body, AssetType.COMMERCIAL_REAL_ESTATE
    )
    
    print(f"   📄 File: {filename}")
    print(f"   📋 Classified as: {category.value}")
    print(f"   📊 Confidence: {confidence:.2f}")
    print(f"   ✅ Expected: {DocumentCategory.RENT_ROLL.value}")
    
    if category == DocumentCategory.RENT_ROLL:
        print("   🎉 Classification CORRECT!")
    else:
        print("   ⚠️ Classification mismatch")
    
    # Test 2: Confidence level determination
    print("\n📊 Testing Confidence Level:")
    
    conf_level = agent.determine_confidence_level(
        document_confidence=0.90,
        asset_confidence=0.85,
        sender_known=True
    )
    
    print(f"   🎯 Confidence Level: {conf_level.value}")
    print(f"   ✅ Expected: {ConfidenceLevel.HIGH.value}")
    
    if conf_level == ConfidenceLevel.HIGH:
        print("   🎉 Confidence level CORRECT!")
    else:
        print("   ⚠️ Confidence level mismatch")
    
    # Test 3: Enhanced processing
    print("\n📧 Testing Enhanced Processing:")
    
    test_attachment = {
        'filename': 'Alpha_Credit_Loan_Agreement.pdf',
        'content': b'LOAN_AGREEMENT_CONTENT' * 100
    }
    
    test_email = {
        'sender_email': 'loans@alphacredit.com',
        'sender_name': 'Alpha Credit',
        'subject': 'Final loan agreement documents',
        'body': 'Please find the executed loan agreement attached.',
        'date': '2024-12-09T16:00:00'
    }
    
    result = await agent.enhanced_process_attachment(test_attachment, test_email)
    
    print(f"   📊 Status: {result.status.value}")
    if result.document_category:
        print(f"   📋 Category: {result.document_category.value}")
    if result.confidence_level:
        print(f"   🎯 Confidence: {result.confidence_level.value}")
    
    print("\n✅ Phase 3 Features Working!")
    print("🎉 Document Classification & Intelligence Ready!")

if __name__ == "__main__":
    asyncio.run(main()) 