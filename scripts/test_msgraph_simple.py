#!/usr/bin/env python3
"""
Simple Microsoft Graph Connection Test

Quick and minimal test to verify Microsoft Graph connectivity.
Useful for basic validation during setup and troubleshooting.

Usage:
    python scripts/test_msgraph_simple.py
"""

# # Standard library imports
import asyncio
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Local application imports
# Local imports
from src.email_interface.msgraph import MicrosoftGraphInterface
from src.utils.config import config


async def simple_test():
    """Simple Microsoft Graph connection test."""
    print("🚀 Simple Microsoft Graph Connection Test")
    print("=" * 45)

    # Check basic configuration
    print("🔧 Configuration Check:")
    if not config.client_id or config.client_id == "your_value_here":
        print("❌ CLIENT_ID not configured")
        return False

    if not config.tenant_id or config.tenant_id == "your_value_here":
        print("❌ TENANT_ID not configured")
        return False

    print("✅ Basic configuration appears valid")

    # Test connection
    print("\n🔐 Testing Authentication...")
    interface = None

    try:
        interface = MicrosoftGraphInterface()
        success = await interface.connect()

        if success:
            print("✅ Authentication successful!")

            # Quick mailbox test
            print("\n📬 Testing Mailbox Access...")
            mailboxes = await interface.list_mailboxes()

            if mailboxes:
                print(f"✅ Found {len(mailboxes)} accessible mailbox(es)")
                print(f"📧 Primary: {mailboxes[0].get('displayName', 'Unknown')}")
            else:
                print("⚠️ No mailboxes found")

            # Quick email test
            print("\n📨 Testing Email Retrieval...")
            emails = await interface.get_emails(limit=1)

            if emails:
                print("✅ Email retrieval successful")
            else:
                print("⚠️ No emails found (this may be normal)")

            print("\n🎉 Microsoft Graph is working correctly!")
            return True

        else:
            print("❌ Authentication failed")
            return False

    except Exception as e:
        print(f"❌ Error: {e}")
        return False

    finally:
        if interface:
            try:
                await interface.disconnect()
            except Exception:
                pass  # Ignore cleanup errors in simple test


async def main():
    """Main entry point."""
    try:
        success = await simple_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
