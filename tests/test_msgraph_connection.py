#!/usr/bin/env python3
"""
Test Microsoft Graph Connection with New Credentials
"""

import asyncio
import sys
import os
import json
from pathlib import Path

# Add src to path (go up one directory from tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory

async def test_msgraph_connection():
    print("🧪 Testing Microsoft Graph Connection")
    print("="*50)
    
    try:
        # Load credentials
        creds_path = Path('examples/msgraph_credentials.json')
        if not creds_path.exists():
            print("❌ Credentials file not found")
            return
        
        with open(creds_path) as f:
            credentials = json.load(f)
        
        print(f"✅ Loaded credentials for: {credentials['application_name']}")
        print(f"   Client ID: {credentials['client_id']}")
        print(f"   Tenant ID: {credentials['tenant_id']}")
        
        # Create Microsoft Graph interface
        msgraph = EmailInterfaceFactory.create('microsoft_graph')
        
        print("\n🔗 Connecting to Microsoft Graph...")
        success = await msgraph.connect(credentials)
        
        if success:
            print("✅ Successfully connected to Microsoft Graph!")
            
            # Get profile
            profile = await msgraph.get_profile()
            print(f"📧 Connected as: {profile.get('name', 'Unknown')} ({profile.get('email', 'Unknown')})")
            
            # Test fetching a few emails
            print("\n📧 Testing email fetch...")
            from email_interface import EmailSearchCriteria
            
            criteria = EmailSearchCriteria(max_results=5)
            emails = await msgraph.list_emails(criteria)
            
            print(f"✅ Fetched {len(emails)} emails successfully")
            
            for i, email in enumerate(emails[:3], 1):
                print(f"   {i}. From: {email.sender.address}")
                print(f"      Subject: {email.subject[:50]}...")
                print(f"      Attachments: {len(email.attachments)}")
            
            # Disconnect
            await msgraph.disconnect()
            print("\n🔒 Disconnected from Microsoft Graph")
            print("🎉 Microsoft Graph setup is working correctly!")
            
        else:
            print("❌ Failed to connect to Microsoft Graph")
            print("   Check your credentials and permissions")
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"🐛 Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    asyncio.run(test_msgraph_connection()) 