#!/usr/bin/env python3
"""
Debug script to test Microsoft Graph filter combinations.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria

async def debug_filters():
    """Debug different filter combinations."""
    print("🔍 Debugging Microsoft Graph filter combinations...")
    
    # Initialize and connect
    msgraph = MicrosoftGraphInterface(credentials_path='msgraph_credentials.json')
    await msgraph.connect()
    
    print(f"✅ Connected to {msgraph.user_email}")
    
    # Test 1: Date filter only
    print("\n📅 Test 1: Date filter only (last 7 days)...")
    try:
        date_after = datetime.now() - timedelta(days=7)
        date_criteria = EmailSearchCriteria(
            date_after=date_after,
            max_results=10
        )
        emails = await msgraph.list_emails(date_criteria)
        print(f"✅ Found {len(emails)} emails with date filter")
    except Exception as e:
        print(f"❌ Date filter failed: {e}")
    
    # Test 2: Subject filter only
    print("\n📝 Test 2: Subject filter only...")
    try:
        subject_criteria = EmailSearchCriteria(
            subject="asset",
            max_results=10
        )
        emails = await msgraph.list_emails(subject_criteria)
        print(f"✅ Found {len(emails)} emails with subject filter")
    except Exception as e:
        print(f"❌ Subject filter failed: {e}")
    
    # Test 3: hasAttachments filter only
    print("\n📎 Test 3: hasAttachments filter only...")
    try:
        attachment_criteria = EmailSearchCriteria(
            has_attachments=True,
            max_results=10
        )
        emails = await msgraph.list_emails(attachment_criteria)
        print(f"✅ Found {len(emails)} emails with hasAttachments filter")
    except Exception as e:
        print(f"❌ hasAttachments filter failed: {e}")
    
    # Test 4: Raw API call to test hasAttachments directly
    print("\n🔧 Test 4: Raw API call with hasAttachments filter...")
    try:
        url = f"{msgraph.GRAPH_ENDPOINT}/me/messages"
        params = {
            '$filter': 'hasAttachments eq true',
            '$top': '5'
        }
        
        async with msgraph.session.get(url, params=params) as response:
            if response.status == 200:
                data = await response.json()
                print(f"✅ Raw API call succeeded: found {len(data.get('value', []))} messages")
            else:
                error_text = await response.text()
                print(f"❌ Raw API call failed: HTTP {response.status}")
                print(f"Error details: {error_text}")
    except Exception as e:
        print(f"❌ Raw API call exception: {e}")
    
    await msgraph.disconnect()
    print("\n🎉 Debug tests completed!")

if __name__ == "__main__":
    asyncio.run(debug_filters()) 