#!/usr/bin/env python3
"""
Debug script to examine exact Microsoft Graph API parameters.
"""

import asyncio
import sys
import os
import json
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria

async def debug_parameters():
    """Debug exact parameters being sent to Microsoft Graph."""
    print("🔍 Debugging Microsoft Graph API parameters...")
    
    # Initialize and connect
    msgraph = MicrosoftGraphInterface(credentials_path='msgraph_credentials.json')
    await msgraph.connect()
    
    print(f"✅ Connected to {msgraph.user_email}")
    
    # Patch the _make_request method to log parameters
    original_make_request = msgraph._make_request
    
    async def debug_make_request(method, endpoint, params=None, data=None, **kwargs):
        print(f"\n🔧 API Request Debug:")
        print(f"   Method: {method}")
        print(f"   Endpoint: {endpoint}")
        print(f"   Params: {json.dumps(params, indent=2, default=str) if params else None}")
        print(f"   Data: {json.dumps(data, indent=2, default=str) if data else None}")
        
        # Call original method
        return await original_make_request(method, endpoint, params, data, **kwargs)
    
    # Replace method temporarily
    msgraph._make_request = debug_make_request
    
    # Test 1: Simple query (should work)
    print("\n📧 Test 1: Simple query (no filters)")
    try:
        criteria = EmailSearchCriteria(max_results=5)
        emails = await msgraph.list_emails(criteria)
        print(f"✅ Success: Found {len(emails)} emails")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: With attachments filter (currently failing)
    print("\n📧 Test 2: With attachments filter")
    try:
        criteria = EmailSearchCriteria(has_attachments=True, max_results=5)
        emails = await msgraph.list_emails(criteria)
        print(f"✅ Success: Found {len(emails)} emails")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 3: Direct API call that we know works
    print("\n📧 Test 3: Direct API call (known working)")
    try:
        result = await msgraph._make_request(
            'GET', 
            'me/messages',
            params={
                '$filter': 'hasAttachments eq true',
                '$top': '5'
            }
        )
        emails = result.get('value', [])
        print(f"✅ Success: Found {len(emails)} emails")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    await msgraph.disconnect()

if __name__ == "__main__":
    asyncio.run(debug_parameters()) 