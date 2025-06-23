#!/usr/bin/env python3
"""
Test script to debug attachment detection in Microsoft Graph.
"""

# # Standard library imports
import asyncio
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# # Standard library imports
from datetime import UTC, datetime, timedelta

# # Local application imports
from src.email_interface.base import EmailSearchCriteria
from src.email_interface.factory import EmailInterfaceFactory


async def test_attachments():
    """Test attachment detection and loading."""
    print("=" * 60)
    print("Testing Microsoft Graph Attachment Detection")
    print("=" * 60)

    try:
        # Create Microsoft Graph interface
        email_interface = EmailInterfaceFactory.create(
            system_type="microsoft_graph",
            credentials_path="config/msgraph_credentials.json",
        )

        # Connect
        print("Connecting to Microsoft Graph...")
        connected = await email_interface.connect()
        if not connected:
            print("❌ Failed to connect to Microsoft Graph")
            return

        print("✅ Connected to Microsoft Graph")

        # Search for emails with attachments from last 7 days
        print("\nSearching for emails with attachments...")
        since_date = datetime.now(UTC) - timedelta(days=7)

        criteria = EmailSearchCriteria(
            date_after=since_date, has_attachments=True, limit=3  # Just test a few
        )

        emails = await email_interface.list_emails(criteria)
        print(f"Found {len(emails)} emails with attachments")

        # Examine each email in detail
        for i, email in enumerate(emails[:3]):
            print(f"\n--- Email {i+1} ---")
            print(f"Subject: {email.subject}")
            print(f"From: {email.sender.address}")
            print(f"Attachments count: {len(email.attachments)}")

            for j, attachment in enumerate(email.attachments):
                print(f"  Attachment {j+1}:")
                print(f"    Filename: {attachment.filename}")
                print(f"    Size: {attachment.size} bytes")
                print(f"    Content type: {attachment.content_type}")
                print(f"    Has content: {attachment.content is not None}")
                print(
                    f"    Content length: {len(attachment.content) if attachment.content else 0}"
                )

        print("\n" + "=" * 60)
        print("Summary:")
        print(f"- Found {len(emails)} emails")
        total_attachments = sum(len(email.attachments) for email in emails)
        attachments_with_content = sum(
            1
            for email in emails
            for att in email.attachments
            if att.content is not None
        )
        print(f"- Total attachments: {total_attachments}")
        print(f"- Attachments with content: {attachments_with_content}")

        if total_attachments == 0:
            print("\n🔍 No attachments found. This suggests:")
            print("1. Emails don't actually have attachments, or")
            print("2. Microsoft Graph $expand=attachments isn't working, or")
            print("3. Attachment parsing logic has an issue")

        elif attachments_with_content == 0:
            print("\n🔍 Attachments found but no content loaded. This suggests:")
            print("1. Microsoft Graph doesn't include contentBytes in $expand, or")
            print("2. Attachments need to be downloaded separately, or")
            print("3. Content decoding is failing")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        # # Standard library imports
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_attachments())
