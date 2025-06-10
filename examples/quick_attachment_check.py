#!/usr/bin/env python3
"""
Quick check for emails with attachments in Gmail account.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.gmail import GmailInterface
from email_interface.base import EmailSearchCriteria

async def quick_check():
    """Check for any emails with attachments."""
    print("🔍 Checking for emails with attachments...")
    
    gmail = GmailInterface()
    credentials = {
        'credentials_file': 'gmail_credentials.json', 
        'token_file': 'gmail_token.json'
    }
    await gmail.connect(credentials)
    
    # Check for any emails with attachments (all time, limited to 10)
    criteria = EmailSearchCriteria(has_attachments=True, max_results=10)
    emails = await gmail.list_emails(criteria)
    
    print(f"✅ Found {len(emails)} emails with attachments (all time)")
    
    if emails:
        print("\n📧 Recent emails with attachments:")
        for i, email in enumerate(emails[:5], 1):
            print(f"  {i}. From: {email.sender.address}")
            print(f"     Subject: {email.subject[:60]}{'...' if len(email.subject) > 60 else ''}")
            print(f"     Date: {email.received_date}")
            print(f"     Has attachments: {email.has_attachments}")
            print()
    else:
        print("\n📭 No emails with attachments found in your Gmail account.")
        print("This could mean:")
        print("  - Your Gmail account doesn't have many emails with attachments")
        print("  - Attachments are stored in a specific folder/label")
        print("  - The Gmail API search might be filtering differently")

if __name__ == "__main__":
    asyncio.run(quick_check()) 