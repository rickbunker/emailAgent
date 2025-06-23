#!/usr/bin/env python3
"""
Test email processing with detailed debugging to see why attachments aren't being processed.
"""

# # Standard library imports
import asyncio
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Local application imports
from src.asset_management.processing.document_processor import DocumentProcessor
from src.asset_management.services.asset_service import AssetService
from src.email_interface.base import EmailSearchCriteria
from src.email_interface.factory import EmailInterfaceFactory
from src.utils.logging_system import get_logger

logger = get_logger(__name__)


async def test_email_processing_debug():
    """Test the exact email processing logic with detailed debugging."""
    print("=" * 60)
    print("Testing Email Processing Logic Debug")
    print("=" * 60)

    try:
        # Create Microsoft Graph interface
        email_interface = EmailInterfaceFactory.create(system_type="microsoft_graph")

        # Connect to Microsoft Graph
        print("Connecting to Microsoft Graph...")
        await email_interface.connect()
        print("✅ Connected to Microsoft Graph")

        # Create document processor and asset service
        document_processor = DocumentProcessor()
        asset_service = AssetService()

        # Get assets list
        assets = await asset_service.list_assets()
        print(f"📋 Found {len(assets)} assets in system")

        # Search for emails with attachments
        criteria = EmailSearchCriteria(
            has_attachments=True, date_after=datetime.now(UTC) - timedelta(hours=720)
        )

        print("\n🔍 Searching for emails with attachments (last 720 hours)...")
        emails = await email_interface.list_emails(criteria=criteria)
        print(f"Found {len(emails)} emails with attachments")

        if not emails:
            print("❌ No emails found - stopping test")
            return

        # Test the first email processing logic
        email = emails[0]
        print(f"\n📧 Testing email: {email.subject}")
        print(f"   From: {email.sender}")
        print(f"   Date: {email.sent_date}")
        print(f"   Initial attachments count: {len(email.attachments)}")

        # Simulate the reload logic from email processing
        if len(email.attachments) == 0:
            print(f"\n🔄 Reloading email {email.id} with attachment details...")
            try:
                reloaded_email = await email_interface.get_email(
                    email_id=email.id, include_attachments=True
                )
                print(
                    f"   Reloaded attachments count: {len(reloaded_email.attachments)}"
                )

                if len(reloaded_email.attachments) > 0:
                    email = reloaded_email  # Use the reloaded email
                    print(
                        f"   ✅ Using reloaded email with {len(email.attachments)} attachments"
                    )
                else:
                    print("   ❌ No attachments even after reload")
            except Exception as e:
                print(f"   ❌ Error reloading email: {e}")

        # Process each attachment
        for i, attachment in enumerate(email.attachments):
            print(f"\n📎 Processing attachment {i+1}: {attachment.filename}")
            print(f"   Content type: {attachment.content_type}")
            print(f"   Size: {attachment.size}")
            print(f"   Has content: {len(attachment.content or b'') > 0}")

            # Check if content needs to be downloaded
            if not attachment.content:
                print("   🔄 Downloading attachment content...")
                try:
                    downloaded_content = await email_interface.download_attachment(
                        email_id=email.id, attachment_id=attachment.id
                    )
                    attachment.content = downloaded_content
                    print(f"   ✅ Downloaded {len(downloaded_content)} bytes")
                except Exception as e:
                    print(f"   ❌ Error downloading: {e}")
                    continue

            # Test file type validation
            print("   🔒 Testing file type validation...")
            extension = Path(attachment.filename).suffix.lower().lstrip(".")

            # Simulate what the security service does
            # # Local application imports
            from src.memory.semantic import SemanticMemory

            semantic_memory = SemanticMemory()
            validation = await semantic_memory.get_file_type_validation(extension)
            print(f"   Extension: {extension}")
            print(f"   Validation result: {validation}")

            if validation:
                is_allowed = validation.get("is_allowed", False)
                print(f"   File type {'✅ ALLOWED' if is_allowed else '❌ BLOCKED'}")

                if is_allowed:
                    print("   🚀 Would process attachment with document processor")
                else:
                    print("   🚫 Attachment blocked by security validation")
            else:
                print("   ⚠️  No validation found - would be blocked by default")

        print(f"\n{'='*60}")
        print("✅ Email processing debug completed")
        print(f"{'='*60}")

    except Exception as e:
        print(f"❌ Failed to test email processing: {e}")
        # # Standard library imports
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_email_processing_debug())
