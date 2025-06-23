#!/usr/bin/env python3
"""
Microsoft Graph Debug Utility

Comprehensive debugging tool for Microsoft Graph API connectivity,
authentication issues, and mailbox access problems.

Usage:
    python scripts/debug_msgraph.py [options]

Options:
    --test-auth     Test authentication only
    --test-mailbox  Test mailbox access
    --test-emails   Test email retrieval
    --verbose       Show detailed debug output
    --config-check  Validate configuration only
"""

# # Standard library imports
import argparse
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
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


class MicrosoftGraphDebugger:
    """Comprehensive Microsoft Graph debugging utility."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.interface = None
        self.errors = []
        self.warnings = []

    async def check_configuration(self) -> bool:
        """Validate Microsoft Graph configuration."""
        print("🔧 Checking Microsoft Graph Configuration...")

        # Check if credentials file exists
        creds_file = Path(config.msgraph_credentials_path)

        if not creds_file.exists():
            self.errors.append(
                f"❌ Microsoft Graph credentials file not found: {config.msgraph_credentials_path}"
            )
            return False

        print(f"✅ Credentials file found: {config.msgraph_credentials_path}")

        # Try to read the credentials file to check its contents
        try:
            # # Standard library imports
            import json

            with open(creds_file) as f:
                creds = json.load(f)

            required_fields = ["client_id", "client_secret", "tenant_id"]
            missing_fields = []

            for field in required_fields:
                if (
                    field not in creds
                    or not creds[field]
                    or creds[field] == "your_value_here"
                ):
                    missing_fields.append(field)
                else:
                    # Show masked version for security
                    value = str(creds[field])
                    masked = (
                        "*" * max(len(value) - 4, 4) + value[-4:]
                        if len(value) > 4
                        else "*" * len(value)
                    )
                    print(f"✅ {field}: {masked}")

            if missing_fields:
                for field in missing_fields:
                    self.errors.append(
                        f"❌ Missing or invalid {field} in credentials file"
                    )
                return False

            print("✅ All required credentials appear to be configured")
            return True

        except Exception as e:
            self.errors.append(f"❌ Error reading credentials file: {e}")
            return False

    async def test_authentication(self) -> bool:
        """Test Microsoft Graph authentication."""
        print("\n🔐 Testing Authentication...")

        try:
            self.interface = MicrosoftGraphInterface()

            # Test connection
            success = await self.interface.connect()

            if success:
                print("✅ Authentication successful")
                return True
            else:
                self.errors.append("❌ Authentication failed - check credentials")
                return False

        except Exception as e:
            self.errors.append(f"❌ Authentication error: {e}")
            return False

    async def test_mailbox_access(self) -> bool:
        """Test mailbox access and permissions."""
        print("\n📬 Testing Mailbox Access...")

        if not self.interface:
            self.errors.append("❌ No authenticated interface available")
            return False

        try:
            # Test mailbox listing
            mailboxes = await self.interface.list_mailboxes()

            if mailboxes:
                print(f"✅ Found {len(mailboxes)} accessible mailbox(es):")
                for mailbox in mailboxes[:3]:  # Show first 3
                    print(
                        f"   📧 {mailbox.get('displayName', 'Unknown')} ({mailbox.get('mail', 'No email')})"
                    )

                if len(mailboxes) > 3:
                    print(f"   ... and {len(mailboxes) - 3} more")

                return True
            else:
                self.warnings.append(
                    "⚠️ No accessible mailboxes found - check permissions"
                )
                return False

        except Exception as e:
            self.errors.append(f"❌ Mailbox access error: {e}")
            return False

    async def test_email_retrieval(self) -> bool:
        """Test email retrieval functionality."""
        print("\n📨 Testing Email Retrieval...")

        if not self.interface:
            self.errors.append("❌ No authenticated interface available")
            return False

        try:
            # Get recent emails from primary mailbox
            emails = await self.interface.get_emails(limit=5)

            if emails:
                print(f"✅ Successfully retrieved {len(emails)} recent email(s):")
                for email in emails[:3]:  # Show first 3
                    subject = email.get("subject", "No Subject")[:50]
                    sender = (
                        email.get("from", {})
                        .get("emailAddress", {})
                        .get("address", "Unknown")
                    )
                    print(f"   📧 '{subject}...' from {sender}")

                return True
            else:
                self.warnings.append("⚠️ No emails found in mailbox")
                return True  # Not necessarily an error

        except Exception as e:
            self.errors.append(f"❌ Email retrieval error: {e}")
            return False

    async def test_permissions(self) -> bool:
        """Test Microsoft Graph API permissions."""
        print("\n🔑 Testing API Permissions...")

        if not self.interface:
            self.errors.append("❌ No authenticated interface available")
            return False

        try:
            # Test different permission levels
            permissions_tests = [
                ("Mail.Read", "Reading emails"),
                ("Mail.ReadWrite", "Email management"),
                ("User.Read", "User profile access"),
            ]

            permissions_ok = True
            for permission, description in permissions_tests:
                try:
                    # Try a simple operation that requires this permission
                    if permission == "Mail.Read":
                        await self.interface.get_emails(limit=1)
                        print(f"✅ {permission}: {description}")
                    elif permission == "User.Read":
                        # Could add user profile test here
                        print(f"⚠️ {permission}: {description} (not tested)")
                    else:
                        print(f"⚠️ {permission}: {description} (not tested)")

                except Exception as e:
                    self.warnings.append(f"⚠️ {permission} may be missing: {e}")
                    permissions_ok = False

            return permissions_ok

        except Exception as e:
            self.errors.append(f"❌ Permission testing error: {e}")
            return False

    async def cleanup(self):
        """Clean up connections."""
        if self.interface:
            try:
                await self.interface.disconnect()
                print("\n🧹 Cleaned up connections")
            except Exception as e:
                if self.verbose:
                    print(f"⚠️ Cleanup warning: {e}")

    def print_summary(self):
        """Print diagnostic summary."""
        print("\n" + "=" * 60)
        print("📊 DIAGNOSTIC SUMMARY")
        print("=" * 60)

        if self.errors:
            print(f"\n❌ ERRORS ({len(self.errors)}):")
            for error in self.errors:
                print(f"  {error}")

        if self.warnings:
            print(f"\n⚠️ WARNINGS ({len(self.warnings)}):")
            for warning in self.warnings:
                print(f"  {warning}")

        if not self.errors and not self.warnings:
            print("\n🎉 All tests passed! Microsoft Graph is working correctly.")
        elif not self.errors:
            print("\n✅ No critical errors found. Check warnings above.")
        else:
            print(
                "\n❌ Critical errors found. Please resolve before using Microsoft Graph."
            )
            print("\n💡 Common solutions:")
            print("  - Verify credentials in config/environment")
            print("  - Check Azure app registration permissions")
            print("  - Ensure tenant admin consent is granted")
            print("  - Verify redirect URI matches Azure app registration")

        print("=" * 60)


async def main():
    """Main debugging function."""
    parser = argparse.ArgumentParser(description="Microsoft Graph Debug Utility")
    parser.add_argument(
        "--test-auth", action="store_true", help="Test authentication only"
    )
    parser.add_argument(
        "--test-mailbox", action="store_true", help="Test mailbox access"
    )
    parser.add_argument(
        "--test-emails", action="store_true", help="Test email retrieval"
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed output"
    )
    parser.add_argument(
        "--config-check", action="store_true", help="Validate configuration only"
    )

    args = parser.parse_args()

    debugger = MicrosoftGraphDebugger(verbose=args.verbose)

    print("🚀 Microsoft Graph Debug Utility")
    print("=" * 40)

    try:
        # Always check configuration first
        config_ok = await debugger.check_configuration()

        if args.config_check:
            debugger.print_summary()
            return

        if not config_ok:
            print("\n❌ Configuration issues found. Cannot proceed with testing.")
            debugger.print_summary()
            return

        # Run tests based on arguments
        if args.test_auth or not any([args.test_mailbox, args.test_emails]):
            await debugger.test_authentication()

        if args.test_mailbox or not any([args.test_auth, args.test_emails]):
            await debugger.test_mailbox_access()

        if args.test_emails or not any([args.test_auth, args.test_mailbox]):
            await debugger.test_email_retrieval()

        # Always test permissions if we have an interface
        if debugger.interface:
            await debugger.test_permissions()

    except KeyboardInterrupt:
        print("\n\n⏹️ Debug session interrupted by user")
    except Exception as e:
        debugger.errors.append(f"❌ Unexpected error: {e}")
    finally:
        await debugger.cleanup()
        debugger.print_summary()


if __name__ == "__main__":
    asyncio.run(main())
