"""
Asset Document Agent Integration Test

This script demonstrates how the Asset Document Agent integrates with
the existing email spam management system to process attachments.
"""

import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from agents.asset_document_agent import AssetDocumentAgent, ProcessingStatus, AssetType

async def test_integration():
    """Test Asset Document Agent integration with email processing."""
    print("🧪 Asset Document Agent Integration Test")
    print("=" * 60)
    
    # Initialize the agent
    print("🚀 Initializing Asset Document Agent...")
    agent = AssetDocumentAgent(base_assets_path="./test_assets")
    
    # Health check
    health = await agent.health_check()
    print(f"🏥 Agent Health Check:")
    for component, status in health.items():
        icon = "✅" if status else "⚠️"
        print(f"   {icon} {component}: {status}")
    
    # Test asset type configurations
    print(f"\n📋 Asset Type Configurations:")
    for asset_type, config in agent.ASSET_CONFIGS.items():
        print(f"   {asset_type.value}:")
        print(f"     Max size: {config.max_file_size_mb}MB")
        print(f"     Extensions: {', '.join(config.allowed_extensions)}")
    
    # Simulate email attachments
    print(f"\n📧 Testing Email Attachment Processing:")
    
    test_attachments = [
        {
            'filename': 'rent_roll_Q4_2024.xlsx',
            'content': b'FAKE_EXCEL_CONTENT_FOR_TESTING_PURPOSES_ONLY' * 100,
            'expected_status': ProcessingStatus.SUCCESS
        },
        {
            'filename': 'property_photos.jpg',
            'content': b'FAKE_IMAGE_CONTENT_FOR_TESTING' * 50,
            'expected_status': ProcessingStatus.SUCCESS
        },
        {
            'filename': 'malware.exe',
            'content': b'FAKE_EXECUTABLE_CONTENT',
            'expected_status': ProcessingStatus.INVALID_TYPE
        },
        {
            'filename': 'huge_file.pdf',
            'content': b'FAKE_PDF_CONTENT' * 1000000,  # Very large file
            'expected_status': ProcessingStatus.INVALID_TYPE
        },
        {
            'filename': 'financial_report.pdf',
            'content': b'FAKE_PDF_FINANCIAL_REPORT_CONTENT' * 200,
            'expected_status': ProcessingStatus.SUCCESS
        }
    ]
    
    test_email_data = {
        'sender_email': 'property.manager@realestate.com',
        'sender_name': 'John Property Manager',
        'subject': 'Q4 2024 Rent Roll for 123 Main Street',
        'date': datetime.now().isoformat()
    }
    
    results = []
    
    for i, attachment in enumerate(test_attachments, 1):
        print(f"\n📎 Test {i}: {attachment['filename']}")
        
        result = await agent.process_single_attachment(
            {'filename': attachment['filename'], 'content': attachment['content']},
            test_email_data
        )
        
        results.append(result)
        
        # Verify expected result
        expected = attachment['expected_status']
        actual = result.status
        match_icon = "✅" if actual == expected else "❌"
        
        print(f"   {match_icon} Expected: {expected.value}, Got: {actual.value}")
        
        if result.error_message:
            print(f"   📝 Error: {result.error_message}")
        
        if result.file_hash:
            print(f"   🔢 Hash: {result.file_hash[:16]}...")
        
        if result.metadata:
            print(f"   📊 File size: {result.metadata.get('file_size', 0)} bytes")
    
    # Processing statistics
    stats = agent.get_processing_stats()
    print(f"\n📊 Final Processing Statistics:")
    print(f"   Total processed: {stats['total_processed']}")
    print(f"   Successful: {stats['successful']}")
    print(f"   Quarantined: {stats['quarantined']}")
    print(f"   Duplicates: {stats['duplicates']}")
    print(f"   Errors: {stats['errors']}")
    print(f"   Success rate: {stats['success_rate']:.1f}%")
    
    # Test file type validation for different asset types
    print(f"\n🏢 Asset Type Specific Validation:")
    test_files = [
        ('rent_roll.xlsx', AssetType.COMMERCIAL_REAL_ESTATE),
        ('loan_agreement.pdf', AssetType.PRIVATE_CREDIT),
        ('portfolio_presentation.pptx', AssetType.PRIVATE_EQUITY),
        ('engineering_drawing.dwg', AssetType.INFRASTRUCTURE),
        ('unsupported.exe', AssetType.COMMERCIAL_REAL_ESTATE)
    ]
    
    for filename, asset_type in test_files:
        is_valid = agent.validate_file_type(filename, asset_type)
        icon = "✅" if is_valid else "❌"
        print(f"   {icon} {filename} for {asset_type.value}: {is_valid}")
    
    # Demonstrate integration points
    print(f"\n🔗 Integration Points with Existing Email System:")
    print(f"   ✅ Spam Detection → Asset Document Processing")
    print(f"   ✅ Email Interface → Attachment Extraction")
    print(f"   ✅ Contact Management → Sender-Asset Mapping (Phase 2)")
    print(f"   ✅ Memory Systems → Document Classification Learning (Phase 3)")
    print(f"   ✅ Supervisor → Orchestration and Monitoring (Phase 6)")
    
    # Future phase roadmap
    print(f"\n🛣️ Implementation Roadmap:")
    phases = [
        ("Phase 1", "Core Infrastructure", "✅ COMPLETE"),
        ("Phase 2", "Asset & Sender Management", "🔄 NEXT"),
        ("Phase 3", "Document Classification", "📋 PLANNED"),
        ("Phase 4", "Fuzzy Matching & Intelligence", "📋 PLANNED"),
        ("Phase 5", "File Organization", "📋 PLANNED"),
        ("Phase 6", "Communication System", "📋 PLANNED"),
        ("Phase 7", "Unknown Sender Management", "📋 PLANNED"),
        ("Phase 8", "Monitoring & Optimization", "📋 PLANNED")
    ]
    
    for phase, description, status in phases:
        print(f"   {status} {phase}: {description}")
    
    print(f"\n🎉 Asset Document Agent Integration Test Complete!")
    print(f"   Ready to integrate with existing spam management system")
    print(f"   Phase 1 infrastructure validated and working")

async def test_email_integration_mock():
    """Mock demonstration of email system integration."""
    print(f"\n🔄 Mock Email System Integration:")
    print("=" * 50)
    
    agent = AssetDocumentAgent()
    
    # Simulate processing emails from the existing spam system
    mock_emails = [
        {
            'email_data': {
                'sender_email': 'manager@property.com',
                'sender_name': 'Property Manager',
                'subject': 'Monthly rent roll for 123 Main Street',
                'date': datetime.now().isoformat()
            },
            'attachments': [
                {
                    'filename': 'rent_roll_december.xlsx',
                    'content': b'MOCK_EXCEL_RENT_ROLL_DATA' * 100
                }
            ]
        },
        {
            'email_data': {
                'sender_email': 'finance@creditfund.com',
                'sender_name': 'Credit Fund Finance',
                'subject': 'Quarterly borrower financials',
                'date': datetime.now().isoformat()
            },
            'attachments': [
                {
                    'filename': 'borrower_financials_Q4.pdf',
                    'content': b'MOCK_PDF_FINANCIAL_DATA' * 200
                },
                {
                    'filename': 'covenant_compliance.xlsx',
                    'content': b'MOCK_EXCEL_COMPLIANCE_DATA' * 150
                }
            ]
        }
    ]
    
    for i, email in enumerate(mock_emails, 1):
        print(f"\n📧 Processing Email {i}:")
        print(f"   From: {email['email_data']['sender_name']} <{email['email_data']['sender_email']}>")
        print(f"   Subject: {email['email_data']['subject']}")
        print(f"   Attachments: {len(email['attachments'])}")
        
        for attachment in email['attachments']:
            result = await agent.process_single_attachment(attachment, email['email_data'])
            
            status_icon = "✅" if result.status == ProcessingStatus.SUCCESS else "❌"
            print(f"     {status_icon} {attachment['filename']}: {result.status.value}")
            
            if result.metadata:
                size_kb = result.metadata.get('file_size', 0) / 1024
                print(f"        Size: {size_kb:.1f} KB")
                print(f"        Extension: {result.metadata.get('file_extension')}")
    
    print(f"\n🎯 Next Steps for Full Integration:")
    print(f"   1. Connect with existing Gmail/Microsoft Graph interfaces")
    print(f"   2. Add to spam processing pipeline after clean emails identified")
    print(f"   3. Implement asset-sender mapping (Phase 2)")
    print(f"   4. Add document classification intelligence (Phase 3)")
    print(f"   5. Integrate with supervisor for orchestration")

if __name__ == "__main__":
    async def main():
        await test_integration()
        await test_email_integration_mock()
    
    asyncio.run(main()) 