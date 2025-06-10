#!/usr/bin/env python3
"""
Simple test to process Microsoft Graph email with attachments
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria
from agents.asset_document_agent import AssetDocumentAgent, AssetType

async def test_msgraph_simple():
    """Simple test to process Microsoft Graph email with attachments"""
    
    print("🔍 Simple Microsoft Graph Email Processing Test")
    print("=" * 50)
    
    # Initialize interface
    msgraph = MicrosoftGraphInterface()
    
    try:
        # Connect
        print("Connecting to Microsoft Graph...")
        connected = await msgraph.connect()
        
        if not connected:
            print("❌ Failed to connect to Microsoft Graph")
            return
        
        print("✅ Connected to Microsoft Graph")
        
        # Get emails with attachments (no date filtering)
        print("\n🔍 Getting emails with attachments...")
        criteria = EmailSearchCriteria(has_attachments=True, max_results=5)
        emails = await msgraph.list_emails(criteria)
        print(f"Found {len(emails)} emails with attachments")
        
        if not emails:
            print("❌ No emails with attachments found")
            return
        
        # Process the first email with attachments
        email = emails[0]
        print(f"\n📧 Processing email: {email.subject}")
        print(f"From: {email.sender}")
        print(f"Date: {email.received_date}")
        print(f"Attachments: {len(email.attachments)}")
        
        # Get full email with attachments
        full_email = await msgraph.get_email(email.id, include_attachments=True)
        print(f"Full email loaded with {len(full_email.attachments)} attachments")
        
        # Initialize asset agent
        print("\n🏢 Initializing asset agent...")
        asset_agent = AssetDocumentAgent(base_assets_path="./msgraph_processed_attachments")
        
        # Create a sample asset
        asset_id = await asset_agent.create_asset(
            deal_name="Test_Asset",
            asset_name="Test Asset for Processing",
            asset_type=AssetType.COMMERCIAL_REAL_ESTATE,
            identifiers=["test", "asset", "document"]
        )
        print(f"Created test asset: {asset_id[:8]}...")
        
        # Process each attachment
        print(f"\n📎 Processing {len(full_email.attachments)} attachments...")
        
        for i, attachment in enumerate(full_email.attachments, 1):
            print(f"\n  {i}. {attachment.filename}")
            print(f"     Size: {attachment.size / (1024*1024):.1f}MB")
            print(f"     Type: {attachment.content_type}")
            print(f"     Content loaded: {attachment.is_loaded}")
            
            if attachment.content:
                # Prepare email data
                email_data = {
                    'sender_email': full_email.sender.address,
                    'sender_name': full_email.sender.name or full_email.sender.address,
                    'subject': full_email.subject,
                    'date': full_email.received_date.isoformat() if full_email.received_date else '',
                    'body': full_email.body_text or full_email.body_html or ''
                }
                
                # Process attachment
                result = await asset_agent.process_and_save_attachment(
                    attachment_data={
                        'filename': attachment.filename,
                        'content': attachment.content
                    },
                    email_data=email_data,
                    save_to_disk=True
                )
                
                print(f"     Status: {result.status.value}")
                if result.file_path:
                    print(f"     Saved to: {result.file_path}")
                if result.document_category:
                    print(f"     Category: {result.document_category.value}")
                if result.matched_asset_id:
                    print(f"     Asset: {result.matched_asset_id[:8]}...")
                if result.error_message:
                    print(f"     Error: {result.error_message}")
            else:
                print(f"     ❌ No content available")
        
        print(f"\n✅ Processing complete!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await msgraph.disconnect()
        print("\n🔌 Disconnected from Microsoft Graph")

if __name__ == "__main__":
    asyncio.run(test_msgraph_simple()) 