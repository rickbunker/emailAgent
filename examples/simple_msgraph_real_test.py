#!/usr/bin/env python3
"""
Test the exact Microsoft Graph filter combination we're using.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria

async def test_real_filters():
    """Test the exact filter combinations used in production."""
    print("🔍 Testing real Microsoft Graph filters...")
    
    # Initialize and connect
    msgraph = MicrosoftGraphInterface(credentials_path='msgraph_credentials.json')
    await msgraph.connect()
    
    print(f"✅ Connected to {msgraph.user_email}")
    
    # Test the actual filters used in the production workflow
    print("\n📧 Test 1: Attachments + Date range (production case)")
    try:
        # This is exactly what the workflow uses
        date_after = datetime.now() - timedelta(hours=168)  # 7 days ago
        date_before = datetime.now()
        
        criteria = EmailSearchCriteria(
            has_attachments=True,
            date_after=date_after,
            date_before=date_before,
            max_results=10
        )
        
        print(f"   Date range: {date_after} to {date_before}")
        emails = await msgraph.list_emails(criteria)
        print(f"✅ Success: Found {len(emails)} emails with attachments in date range")
        for email in emails[:3]:  # Show first 3
            print(f"   - {email.subject} (attachments: {len(email.attachments)})")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    # Test simpler case
    print("\n📧 Test 2: Attachments only (no date range)")
    try:
        criteria = EmailSearchCriteria(has_attachments=True, max_results=5)
        emails = await msgraph.list_emails(criteria)
        print(f"✅ Success: Found {len(emails)} emails with attachments")
        for email in emails[:3]:  # Show first 3
            print(f"   - {email.subject} (attachments: {len(email.attachments)})")
    except Exception as e:
        print(f"❌ Failed: {e}")
    
    await msgraph.disconnect()

if __name__ == "__main__":
    asyncio.run(test_real_filters()) 