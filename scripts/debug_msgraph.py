#!/usr/bin/env python3
"""
Debug script for Microsoft Graph email retrieval
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria

async def debug_msgraph():
    """Debug Microsoft Graph email retrieval"""
    
    print("🔍 Debugging Microsoft Graph Email Retrieval")
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
        
        # Get profile
        profile = await msgraph.get_profile()
        print(f"📧 User: {profile.get('displayName')} ({profile.get('mail')})")
        
        # Test 1: Get all emails (no filters)
        print("\n🔍 Test 1: Getting all emails (no filters)")
        criteria1 = EmailSearchCriteria(max_results=5)
        emails1 = await msgraph.list_emails(criteria1)
        print(f"Found {len(emails1)} emails")
        
        # Test 2: Get unread emails only
        print("\n🔍 Test 2: Getting unread emails only")
        criteria2 = EmailSearchCriteria(max_results=5, is_unread=True)
        emails2 = await msgraph.list_emails(criteria2)
        print(f"Found {len(emails2)} unread emails")
        
        # Test 3: Get read emails only
        print("\n🔍 Test 3: Getting read emails only")
        criteria3 = EmailSearchCriteria(max_results=5, is_unread=False)
        emails3 = await msgraph.list_emails(criteria3)
        print(f"Found {len(emails3)} read emails")
        
        # Test 4: Get emails with attachments
        print("\n🔍 Test 4: Getting emails with attachments")
        criteria4 = EmailSearchCriteria(max_results=5, has_attachments=True)
        emails4 = await msgraph.list_emails(criteria4)
        print(f"Found {len(emails4)} emails with attachments")
        
        # Show details of first few emails from Test 1
        if emails1:
            print(f"\n📋 Details of first {min(3, len(emails1))} emails:")
            for i, email in enumerate(emails1[:3], 1):
                print(f"  {i}. From: {email.sender}")
                print(f"     Subject: {email.subject}")
                print(f"     Date: {email.received_date}")
                print(f"     Read: {email.is_read}")
                print(f"     Attachments: {len(email.attachments)}")
                print()
        
        # Test detailed retrieval with attachments
        if emails4:
            print(f"\n🔍 Test 5: Getting detailed email with attachments")
            detailed_email = await msgraph.get_email(emails4[0].id, include_attachments=True)
            print(f"Email ID: {detailed_email.id}")
            print(f"Subject: {detailed_email.subject}")
            print(f"Attachments: {len(detailed_email.attachments)}")
            
            for i, att in enumerate(detailed_email.attachments, 1):
                print(f"  {i}. {att.filename} ({att.size} bytes, {att.content_type})")
                print(f"     Content loaded: {att.is_loaded}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await msgraph.disconnect()
        print("\n🔌 Disconnected from Microsoft Graph")

if __name__ == "__main__":
    asyncio.run(debug_msgraph()) 