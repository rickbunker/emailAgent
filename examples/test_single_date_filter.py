#!/usr/bin/env python3
"""
Test individual date filters to isolate the Microsoft Graph issue.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria

async def test_individual_filters():
    """Test individual filter combinations."""
    print("🔍 Testing individual Microsoft Graph filters...")
    
    # Initialize and connect
    msgraph = MicrosoftGraphInterface(credentials_path='msgraph_credentials.json')
    await msgraph.connect()
    
    print(f"✅ Connected to {msgraph.user_email}")
    
    # Test 1: Only date_after filter
    print("\n📧 Test 1: Only date_after (ge) filter")
    try:
        date_after = datetime.now() - timedelta(days=7)
        criteria = EmailSearchCriteria(date_after=date_after, max_results=5)
        emails = await msgraph.list_emails(criteria)
        print(f"✅ Success: Found {len(emails)} emails after {date_after}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 2: Only date_before filter  
    print("\n📧 Test 2: Only date_before (le) filter")
    try:
        date_before = datetime.now()
        criteria = EmailSearchCriteria(date_before=date_before, max_results=5)
        emails = await msgraph.list_emails(criteria)
        print(f"✅ Success: Found {len(emails)} emails before {date_before}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 3: Attachments + date_after only
    print("\n📧 Test 3: Attachments + date_after only")
    try:
        date_after = datetime.now() - timedelta(days=7)
        criteria = EmailSearchCriteria(has_attachments=True, date_after=date_after, max_results=5)
        emails = await msgraph.list_emails(criteria)
        print(f"✅ Success: Found {len(emails)} emails with attachments after {date_after}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test 4: Attachments + date_before only
    print("\n📧 Test 4: Attachments + date_before only")
    try:
        date_before = datetime.now()
        criteria = EmailSearchCriteria(has_attachments=True, date_before=date_before, max_results=5)
        emails = await msgraph.list_emails(criteria)
        print(f"✅ Success: Found {len(emails)} emails with attachments before {date_before}")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    await msgraph.disconnect()

if __name__ == "__main__":
    asyncio.run(test_individual_filters()) 