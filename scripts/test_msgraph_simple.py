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

    # Check if credentials file exists
    creds_file = Path(config.msgraph_credentials_path)
    if not creds_file.exists():
        print(
            f"❌ Microsoft Graph credentials file not found: {config.msgraph_credentials_path}"
        )
        return False

    print(f"✅ Credentials file found: {config.msgraph_credentials_path}")

    # Test connection
    print("\n🔐 Testing Authentication...")
    interface = None

    try:
        interface = MicrosoftGraphInterface()
        success = await interface.connect()

        if success:
            print("✅ Authentication successful!")

            # Get user profile
            print("\n👤 Getting User Profile...")
            profile = await interface.get_profile()

            if profile:
                print(
                    f"✅ User: {profile.get('name', 'Unknown')} ({profile.get('email', 'No email')})"
                )
            else:
                print("⚠️ Could not retrieve user profile")

            # Quick email test
            print("\n📨 Testing Email Retrieval...")
            from src.email_interface.base import EmailSearchCriteria

            criteria = EmailSearchCriteria(max_results=1)
            emails = await interface.list_emails(criteria)

            if emails:
                print(f"✅ Email retrieval successful - found {len(emails)} email(s)")
                email = emails[0]
                print(f"📧 Latest: '{email.subject[:50]}...' from {email.sender}")
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
