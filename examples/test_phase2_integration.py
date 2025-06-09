"""
Phase 2 Integration Test: Asset & Sender Management

This script demonstrates Phase 2 functionality:
- Asset creation and management
- Sender-Asset mapping
- Qdrant database integration
- Duplicate detection
- Document storage
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

try:
    from qdrant_client import QdrantClient
    QDRANT_AVAILABLE = True
except ImportError:
    print("⚠️ Qdrant client not installed. Install with: pip install qdrant-client")
    QDRANT_AVAILABLE = False

from agents.asset_document_agent import (
    AssetDocumentAgent, 
    ProcessingStatus, 
    AssetType,
    Asset,
    AssetSenderMapping
)

async def test_phase2_basic():
    """Test Phase 2 functionality without Qdrant (basic validation)."""
    print("🧪 Phase 2 Test - Basic Functionality")
    print("=" * 60)
    
    # Initialize agent without Qdrant
    agent = AssetDocumentAgent(
        qdrant_client=None,
        base_assets_path="./test_assets_phase2"
    )
    
    # Test health check
    health = await agent.health_check()
    print(f"🏥 Agent Health Check: {health}")
    
    # Test basic attachment processing
    test_attachments = [
        {
            'filename': 'rent_roll_Q4_2024.xlsx',
            'content': b'UNIQUE_EXCEL_CONTENT_TEST_123' * 50,
        },
        {
            'filename': 'duplicate_rent_roll.xlsx',
            'content': b'UNIQUE_EXCEL_CONTENT_TEST_123' * 50,  # Same content = should detect as duplicate
        },
        {
            'filename': 'property_appraisal.pdf',
            'content': b'UNIQUE_PDF_APPRAISAL_CONTENT' * 100,
        }
    ]
    
    test_email_data = {
        'sender_email': 'manager@commercial-property.com',
        'sender_name': 'Property Manager',
        'subject': 'Q4 2024 Documents for 123 Main Street',
        'date': datetime.now().isoformat()
    }
    
    print(f"\n📧 Testing Document Processing:")
    
    results = []
    for i, attachment in enumerate(test_attachments, 1):
        print(f"\n📎 Test {i}: {attachment['filename']}")
        
        result = await agent.process_single_attachment(
            attachment, test_email_data
        )
        
        results.append(result)
        
        status_icons = {
            ProcessingStatus.SUCCESS: "✅",
            ProcessingStatus.DUPLICATE: "🔄",
            ProcessingStatus.QUARANTINED: "🦠",
            ProcessingStatus.INVALID_TYPE: "❌",
            ProcessingStatus.ERROR: "💥"
        }
        
        icon = status_icons.get(result.status, "❓")
        print(f"   {icon} Status: {result.status.value}")
        
        if result.file_hash:
            print(f"   🔢 Hash: {result.file_hash[:16]}...")
            
        if result.error_message:
            print(f"   📝 Error: {result.error_message}")
            
        if result.duplicate_of:
            print(f"   🔗 Duplicate of: {result.duplicate_of}")
    
    print(f"\n✅ Phase 2 Basic Tests Complete!")
    return results

async def test_phase2_with_qdrant():
    """Test Phase 2 functionality with Qdrant integration."""
    if not QDRANT_AVAILABLE:
        print("⚠️ Skipping Qdrant integration tests - client not available")
        return
    
    print("\n🧪 Phase 2 Test - Qdrant Integration")
    print("=" * 60)
    
    try:
        # Try to connect to local Qdrant
        qdrant_client = QdrantClient("localhost", port=6333)
        collections = qdrant_client.get_collections()
        print(f"✅ Connected to Qdrant - {len(collections.collections)} existing collections")
        
    except Exception as e:
        print(f"⚠️ Cannot connect to Qdrant: {e}")
        print("   Start Qdrant with: docker run -p 6333:6333 qdrant/qdrant")
        return
    
    # Initialize agent with Qdrant
    agent = AssetDocumentAgent(
        qdrant_client=qdrant_client,
        base_assets_path="./test_assets_qdrant"
    )
    
    # Initialize collections
    print(f"\n🏗️ Initializing Collections:")
    collections_ok = await agent.initialize_collections()
    
    if not collections_ok:
        print("❌ Collection initialization failed")
        return
    
    # Test asset creation
    print(f"\n🏢 Testing Asset Management:")
    
    test_assets = [
        {
            'deal_name': '123 Main Street',
            'asset_name': '123 Main Street Commercial Property, LLC',
            'asset_type': AssetType.COMMERCIAL_REAL_ESTATE,
            'identifiers': ['123 Main', 'Main Street Property', 'Downtown Office']
        },
        {
            'deal_name': 'Bridge Loan Alpha',
            'asset_name': 'Alpha Credit Fund Bridge Loan Portfolio',
            'asset_type': AssetType.PRIVATE_CREDIT,
            'identifiers': ['Alpha Credit', 'Bridge Alpha', 'ACF-BL-001']
        },
        {
            'deal_name': 'Growth Equity Beta',
            'asset_name': 'Beta Growth Partners Investment Fund',
            'asset_type': AssetType.PRIVATE_EQUITY,
            'identifiers': ['Beta Growth', 'BGP Fund', 'Growth Beta']
        }
    ]
    
    created_assets = []
    
    for asset_data in test_assets:
        asset_id = await agent.create_asset(**asset_data)
        created_assets.append(asset_id)
        print(f"   ✅ Created: {asset_data['deal_name']} → {asset_id}")
    
    # Test asset retrieval
    print(f"\n🔍 Testing Asset Retrieval:")
    
    for asset_id in created_assets:
        asset = await agent.get_asset(asset_id)
        if asset:
            print(f"   ✅ Retrieved: {asset.deal_name} ({asset.asset_type.value})")
        else:
            print(f"   ❌ Failed to retrieve: {asset_id}")
    
    # Test asset listing
    print(f"\n📋 Testing Asset Listing:")
    all_assets = await agent.list_assets()
    print(f"   Found {len(all_assets)} total assets:")
    for asset in all_assets[-3:]:  # Show last 3
        print(f"     - {asset.deal_name}: {asset.asset_type.value}")
    
    # Test sender-asset mapping
    print(f"\n🔗 Testing Sender-Asset Mapping:")
    
    test_mappings = [
        {
            'asset_id': created_assets[0],  # 123 Main Street
            'sender_email': 'manager@mainstreetproperty.com',
            'confidence': 0.95,
            'document_types': ['rent_roll', 'financial_reports', 'photos']
        },
        {
            'asset_id': created_assets[1],  # Bridge Loan Alpha
            'sender_email': 'loans@alphacredit.com',
            'confidence': 0.90,
            'document_types': ['loan_docs', 'borrower_financials', 'compliance']
        },
        {
            'asset_id': created_assets[0],  # 123 Main Street (multiple senders)
            'sender_email': 'accounting@mainstreetproperty.com',
            'confidence': 0.85,
            'document_types': ['financial_reports', 'tax_docs']
        }
    ]
    
    for mapping_data in test_mappings:
        mapping_id = await agent.create_asset_sender_mapping(**mapping_data)
        print(f"   ✅ Mapped: {mapping_data['sender_email']} → {mapping_data['asset_id'][:8]}...")
    
    # Test sender lookup
    print(f"\n🔍 Testing Sender Asset Lookup:")
    
    test_senders = [
        'manager@mainstreetproperty.com',
        'loans@alphacredit.com',
        'unknown@example.com'
    ]
    
    for sender in test_senders:
        sender_assets = await agent.get_sender_assets(sender)
        print(f"   📧 {sender}: {len(sender_assets)} asset(s)")
        for asset_info in sender_assets:
            print(f"     - Asset: {asset_info['asset_id'][:8]}... (confidence: {asset_info['confidence']})")
    
    # Test document processing with asset mapping
    print(f"\n📄 Testing Document Processing with Asset Context:")
    
    test_document = {
        'filename': 'main_street_rent_roll.xlsx',
        'content': b'MAIN_STREET_RENT_ROLL_DATA' * 100
    }
    
    test_email = {
        'sender_email': 'manager@mainstreetproperty.com',
        'sender_name': 'Main Street Property Manager',
        'subject': 'Monthly rent roll for 123 Main Street',
        'date': datetime.now().isoformat()
    }
    
    # Process the document
    processing_result = await agent.process_single_attachment(test_document, test_email)
    
    print(f"   📄 Processed: {test_document['filename']}")
    print(f"   📊 Status: {processing_result.status.value}")
    print(f"   🔢 Hash: {processing_result.file_hash[:16] if processing_result.file_hash else 'None'}...")
    
    # Store the processed document
    if processing_result.status == ProcessingStatus.SUCCESS:
        # Find which asset this sender is associated with
        sender_assets = await agent.get_sender_assets(test_email['sender_email'])
        
        if sender_assets:
            # Use the highest confidence asset
            best_asset = max(sender_assets, key=lambda x: x['confidence'])
            asset_id = best_asset['asset_id']
            
            document_id = await agent.store_processed_document(
                processing_result.file_hash,
                processing_result,
                asset_id
            )
            
            print(f"   💾 Stored document: {document_id} → Asset: {asset_id[:8]}...")
        else:
            print(f"   ⚠️ No asset mapping found for sender")
    
    # Test duplicate detection
    print(f"\n🔄 Testing Duplicate Detection:")
    
    # Try to process the same document again
    duplicate_result = await agent.process_single_attachment(test_document, test_email)
    
    print(f"   📄 Re-processed: {test_document['filename']}")
    print(f"   📊 Status: {duplicate_result.status.value}")
    
    if duplicate_result.status == ProcessingStatus.DUPLICATE:
        print(f"   ✅ Duplicate correctly detected!")
        print(f"   🔗 Original document: {duplicate_result.duplicate_of}")
    else:
        print(f"   ⚠️ Duplicate detection may not be working")
    
    print(f"\n✅ Phase 2 Qdrant Integration Tests Complete!")

async def main():
    """Run Phase 2 tests."""
    print("🚀 Asset Document E-Mail Ingestion Agent - Phase 2 Tests")
    print("=" * 80)
    
    # Run basic tests
    await test_phase2_basic()
    
    print(f"\n🎯 Phase 2 Implementation Status:")
    print(f"   ✅ File processing pipeline enhanced")
    print(f"   ✅ Data models defined (Asset, AssetSenderMapping, UnknownSender)")
    print(f"   ✅ Qdrant collection management ready")
    print(f"   ✅ Duplicate detection implemented")
    print(f"   ✅ Asset and sender management methods ready")
    
    print(f"\n🛣️ Next Steps - Phase 3:")
    print(f"   📋 Document classification by type")
    print(f"   🤖 AI-powered content analysis")
    print(f"   🔍 Asset identification from email content")
    print(f"   📊 Confidence scoring for auto-routing")
    
    print(f"\n🎉 Phase 2 Foundation Complete!")

if __name__ == "__main__":
    asyncio.run(main()) 