#!/usr/bin/env python3
"""
Debug script to inspect a single email and its attachments in detail.
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
from src.email_interface.base import EmailSearchCriteria
from src.email_interface.factory import EmailInterfaceFactory


async def debug_single_email():
    """Debug a single email to see what's happening with attachments."""
    print("=" * 60)
    print("Debugging Single Email Attachment Processing")
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

        # Search for emails with attachments from last 30 days
        print("\nSearching for emails from last 30 days...")
        since_date = datetime.now(UTC) - timedelta(days=30)

        # First, search for ANY emails (not just those with attachments)
        all_criteria = EmailSearchCriteria(date_after=since_date, max_results=5)

        all_emails = await email_interface.list_emails(all_criteria)
        print(f"Found {len(all_emails)} total emails")

        # Now search specifically for emails with attachments
        attachment_criteria = EmailSearchCriteria(
            date_after=since_date, has_attachments=True, max_results=5
        )

        attachment_emails = await email_interface.list_emails(attachment_criteria)
        print(f"Found {len(attachment_emails)} emails with attachments")

        # Examine the first email in detail
        if all_emails:
            email = all_emails[0]
            print("\n--- First Email Details ---")
            print(f"Subject: {email.subject}")
            print(f"From: {email.sender.address}")
            print(f"Date: {email.received_date}")
            print(f"Attachments count: {len(email.attachments)}")
            print(f"Raw attachments list: {email.attachments}")

            # Check if email has attachments but they weren't loaded
            if hasattr(email, "raw_data") and email.raw_data:
                raw_attachments = email.raw_data.get("attachments", [])
                print(f"Raw data attachments: {len(raw_attachments)} items")
                if raw_attachments:
                    for i, att in enumerate(raw_attachments):
                        print(f"  Raw attachment {i+1}:")
                        print(f"    Name: {att.get('name', 'N/A')}")
                        print(f"    Size: {att.get('size', 'N/A')}")
                        print(f"    Type: {att.get('contentType', 'N/A')}")
                        print(f"    ID: {att.get('id', 'N/A')}")
                        print(f"    Has contentBytes: {'contentBytes' in att}")

            # If no attachments were loaded, try to get the email with explicit attachment expansion
            if len(email.attachments) == 0:
                print("\nTrying to get email with explicit attachment inclusion...")
                try:
                    email_with_attachments = await email_interface.get_email(
                        email.id, include_attachments=True
                    )
                    print(
                        f"Email with attachments: {len(email_with_attachments.attachments)} attachments"
                    )

                    for i, att in enumerate(email_with_attachments.attachments):
                        print(f"  Attachment {i+1}:")
                        print(f"    Filename: {att.filename}")
                        print(f"    Size: {att.size}")
                        print(f"    Content type: {att.content_type}")
                        print(f"    Attachment ID: {att.attachment_id}")
                        print(f"    Has content: {att.content is not None}")

                        # Try to download content if missing
                        if not att.content and att.attachment_id:
                            print("    Attempting to download content...")
                            try:
                                content = await email_interface.download_attachment(
                                    email.id, att.attachment_id
                                )
                                print(f"    Downloaded: {len(content)} bytes")
                            except Exception as e:
                                print(f"    Download failed: {e}")

                except Exception as e:
                    print(f"Failed to get email with attachments: {e}")

        print(f"\n{'='*60}")
        print("Summary:")
        print(f"- Total emails found: {len(all_emails)}")
        print(f"- Emails with attachments: {len(attachment_emails)}")

        if len(all_emails) == 0:
            print("🔍 No emails found in the last 30 days")
        elif len(attachment_emails) == 0:
            print("🔍 No emails with attachments found")
        else:
            print("🔍 Found emails with attachments - check processing logic")

    except Exception as e:
        print(f"❌ Debug failed: {e}")
        # # Standard library imports
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(debug_single_email())
