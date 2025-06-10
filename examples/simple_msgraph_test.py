#!/usr/bin/env python3
"""
Simple Microsoft Graph test to debug the HTTP 400 issue.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria

async def simple_test():
    """Simple test of Microsoft Graph functionality."""
    print("🔍 Testing Microsoft Graph basic functionality...")
    
    # Initialize and connect
    msgraph = MicrosoftGraphInterface(credentials_path='msgraph_credentials.json')
    await msgraph.connect()
    
    print(f"✅ Connected to {msgraph.user_email}")
    
    # Test 1: Get all emails without any filters
    print("\n📧 Test 1: Getting recent emails (no filters)...")
    try:
        basic_criteria = EmailSearchCriteria(max_results=5)
        emails = await msgraph.list_emails(basic_criteria)
        print(f"✅ Found {len(emails)} emails")
        for i, email in enumerate(emails[:3], 1):
            print(f"  {i}. From: {email.sender.address}")
            print(f"     Subject: {email.subject[:50]}...")
            print(f"     Has attachments: {email.has_attachments}")
    except Exception as e:
        print(f"❌ Basic test failed: {e}")
        return
    
    # Test 2: Search for emails with attachments only
    print("\n📎 Test 2: Getting emails with attachments only...")
    try:
        attachment_criteria = EmailSearchCriteria(
            has_attachments=True,
            max_results=10
        )
        emails_with_attachments = await msgraph.list_emails(attachment_criteria)
        print(f"✅ Found {len(emails_with_attachments)} emails with attachments")
        
        for i, email in enumerate(emails_with_attachments[:5], 1):
            print(f"  {i}. From: {email.sender.address}")
            print(f"     Subject: {email.subject[:50]}...")
            print(f"     Date: {email.received_date}")
            
    except Exception as e:
        print(f"❌ Attachment test failed: {e}")
        return
    
    # Test 3: Get one email with attachments
    if emails_with_attachments:
        print(f"\n📎 Test 3: Getting full email with attachments...")
        try:
            email_id = emails_with_attachments[0].id
            full_email = await msgraph.get_email(email_id, include_attachments=True)
            print(f"✅ Loaded email with {len(full_email.attachments)} attachments")
            
            for i, att in enumerate(full_email.attachments[:3], 1):
                size_mb = att.size / (1024*1024) if att.size else 0
                print(f"  {i}. {att.filename} ({size_mb:.1f}MB)")
                
        except Exception as e:
            print(f"❌ Full email test failed: {e}")
    
    await msgraph.disconnect()
    print("\n🎉 Tests completed!")

if __name__ == "__main__":
    asyncio.run(simple_test()) 