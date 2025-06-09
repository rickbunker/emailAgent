"""
Email Interface Demonstration

This script demonstrates how to use the email interface layer
to connect to different email systems (Gmail and Microsoft Graph).

Before running:
1. For Gmail: Set up OAuth2 credentials at https://console.cloud.google.com/
2. For Microsoft Graph: Set up app registration at https://portal.azure.com/

Usage:
    python examples/email_demo.py --system gmail
    python examples/email_demo.py --system microsoft_graph
"""

import asyncio
import argparse
import os
import sys
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import (
    EmailInterfaceFactory,
    EmailSystemType,
    EmailSearchCriteria,
    EmailSendRequest,
    EmailAddress,
    EmailImportance
)

async def demo_gmail():
    """Demonstrate Gmail integration."""
    print("🔗 Setting up Gmail interface...")
    
    # Create Gmail interface
    gmail = EmailInterfaceFactory.create('gmail')
    
    # Set up credentials
    credentials = {
        'credentials_file': 'credentials.json',  # You need to create this
        'token_file': 'gmail_token.json'
    }
    
    try:
        # Connect
        print("🔐 Connecting to Gmail...")
        connected = await gmail.connect(credentials)
        
        if not connected:
            print("❌ Failed to connect to Gmail")
            return
        
        print("✅ Connected to Gmail!")
        
        # Get profile
        profile = await gmail.get_profile()
        print(f"📧 Connected as: {profile.get('name')} ({profile.get('email')})")
        print(f"📊 Total messages: {profile.get('messages_total', 'unknown')}")
        
        # List recent emails
        print("\n📬 Recent emails:")
        criteria = EmailSearchCriteria(
            max_results=5,
            is_unread=None  # Get both read and unread
        )
        
        emails = await gmail.list_emails(criteria)
        
        for i, email in enumerate(emails, 1):
            status = "📩" if email.is_read else "📧"
            importance = "⭐" if email.importance.value == "high" else ""
            print(f"{i}. {status} {importance} From: {email.sender.name or email.sender.address}")
            print(f"   Subject: {email.subject}")
            print(f"   Date: {email.sent_date}")
            print()
        
        # Get labels
        print("🏷️ Available labels:")
        labels = await gmail.get_labels()
        for label in labels[:10]:  # Show first 10
            print(f"   - {label}")
        
        # Search for emails
        print("\n🔍 Searching for emails containing 'meeting'...")
        search_criteria = EmailSearchCriteria(
            query="meeting",
            max_results=3
        )
        
        search_results = await gmail.list_emails(search_criteria)
        print(f"Found {len(search_results)} emails")
        
        for email in search_results:
            print(f"   - {email.subject} (from {email.sender.address})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await gmail.disconnect()
        print("🔌 Disconnected from Gmail")

async def demo_microsoft_graph():
    """Demonstrate Microsoft Graph integration."""
    print("🔗 Setting up Microsoft Graph interface...")
    
    # Create Microsoft Graph interface
    msgraph = EmailInterfaceFactory.create('microsoft_graph')
    
    # Set up credentials
    credentials = {
        'client_id': 'your-client-id',  # You need to set this
        'tenant_id': 'common',
        # 'client_secret': 'your-secret',  # Optional for public clients
    }
    
    try:
        # Connect
        print("🔐 Connecting to Microsoft Graph...")
        connected = await msgraph.connect(credentials)
        
        if not connected:
            print("❌ Failed to connect to Microsoft Graph")
            return
        
        print("✅ Connected to Microsoft Graph!")
        
        # Get profile
        profile = await msgraph.get_profile()
        print(f"📧 Connected as: {profile.get('name')} ({profile.get('email')})")
        print(f"🏢 Job Title: {profile.get('job_title', 'N/A')}")
        print(f"📍 Office: {profile.get('office_location', 'N/A')}")
        
        # List recent emails
        print("\n📬 Recent emails:")
        criteria = EmailSearchCriteria(
            max_results=5,
            is_unread=None  # Get both read and unread
        )
        
        emails = await msgraph.list_emails(criteria)
        
        for i, email in enumerate(emails, 1):
            status = "📩" if email.is_read else "📧"
            importance = "⭐" if email.importance.value == "high" else ""
            print(f"{i}. {status} {importance} From: {email.sender.name or email.sender.address}")
            print(f"   Subject: {email.subject}")
            print(f"   Date: {email.sent_date}")
            print()
        
        # Get folders
        print("📁 Available folders:")
        folders = await msgraph.get_labels()
        for folder in folders:
            print(f"   - {folder}")
        
        # Search for unread emails
        print("\n🔍 Searching for unread emails...")
        search_criteria = EmailSearchCriteria(
            is_unread=True,
            max_results=3
        )
        
        unread_emails = await msgraph.list_emails(search_criteria)
        print(f"Found {len(unread_emails)} unread emails")
        
        for email in unread_emails:
            print(f"   - {email.subject} (from {email.sender.address})")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    finally:
        await msgraph.disconnect()
        print("🔌 Disconnected from Microsoft Graph")

async def demo_factory():
    """Demonstrate email interface factory."""
    print("🏭 Email Interface Factory Demo")
    print("=" * 40)
    
    # Show supported types
    print("📋 Supported email system types:")
    for system_type in EmailInterfaceFactory.get_supported_types():
        print(f"   - {system_type}")
    
    # Show credential templates
    print("\n🔐 Gmail credentials template:")
    gmail_template = EmailInterfaceFactory.get_credentials_template('gmail')
    for field, info in gmail_template.items():
        required = "✅ Required" if info['required'] else "⚪ Optional"
        print(f"   {field}: {info['description']} ({required})")
    
    print("\n🔐 Microsoft Graph credentials template:")
    graph_template = EmailInterfaceFactory.get_credentials_template('microsoft_graph')
    for field, info in graph_template.items():
        required = "✅ Required" if info['required'] else "⚪ Optional"
        default = f" (default: {info.get('default', 'N/A')})" if 'default' in info else ""
        print(f"   {field}: {info['description']} ({required}){default}")
    
    # Show config-based creation
    print("\n⚙️ Interface creation examples:")
    
    print("✅ Creating Gmail interface...")
    try:
        gmail_interface = EmailInterfaceFactory.create('gmail')
        print(f"✅ Created Gmail interface: {type(gmail_interface).__name__}")
        print("   (Credentials would be passed to connect() method)")
    except Exception as e:
        print(f"❌ Gmail interface creation failed: {e}")
    
    print("\n✅ Creating Microsoft Graph interface...")
    try:
        msgraph_interface = EmailInterfaceFactory.create('microsoft_graph')
        print(f"✅ Created Microsoft Graph interface: {type(msgraph_interface).__name__}")
        print("   (Credentials would be passed to connect() method)")
    except Exception as e:
        print(f"❌ Microsoft Graph interface creation failed: {e}")
    
    print("\n💡 Correct usage pattern:")
    print("   1. interface = EmailInterfaceFactory.create('gmail')")
    print("   2. credentials = {'credentials_file': 'path/to/file.json'}")
    print("   3. await interface.connect(credentials)")
    print("   4. emails = await interface.list_emails(criteria)")
    print("   5. await interface.disconnect()")

def main():
    parser = argparse.ArgumentParser(description="Email Interface Demo")
    parser.add_argument(
        '--system',
        choices=['gmail', 'microsoft_graph', 'factory'],
        default='factory',
        help='Email system to demonstrate'
    )
    
    args = parser.parse_args()
    
    print("📧 Email Agent - Interface Layer Demo")
    print("=" * 50)
    
    if args.system == 'gmail':
        print("\n🟦 Gmail Integration Demo")
        print("Note: You need to set up OAuth2 credentials first!")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create a project and enable Gmail API")
        print("3. Create OAuth2 credentials")
        print("4. Download credentials.json")
        print()
        asyncio.run(demo_gmail())
    
    elif args.system == 'microsoft_graph':
        print("\n🟦 Microsoft Graph Integration Demo")
        print("Note: You need to set up Azure AD app registration first!")
        print("1. Go to https://portal.azure.com/")
        print("2. Register an application")
        print("3. Configure API permissions for Microsoft Graph")
        print("4. Get client ID and optionally client secret")
        print()
        asyncio.run(demo_microsoft_graph())
    
    else:
        asyncio.run(demo_factory())

if __name__ == "__main__":
    main() 