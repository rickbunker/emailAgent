#!/usr/bin/env python3
"""
Targeted Test: Emails with Attachments

This script specifically searches for emails with attachments and processes them
through the complete Asset Document Agent pipeline.

Usage:
    python test_emails_with_attachments.py
"""

import asyncio
import sys
import os
import json
import csv
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path

# Add src to path (go up one directory from tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory, EmailSearchCriteria
from agents.asset_document_agent import (
    AssetDocumentAgent, 
    ProcessingStatus, 
    DocumentCategory, 
    ConfidenceLevel,
    AssetType
)

async def main():
    """Find and process emails with attachments."""
    print("🧪 TARGETED TEST: EMAILS WITH ATTACHMENTS")
    print("="*80)
    print("Searching for emails with attachments to test the asset document agent")
    print("="*80)
    
    # Initialize
    gmail = EmailInterfaceFactory.create('gmail')
    agent = AssetDocumentAgent()
    
    try:
        # Connect to Gmail
        print("🔗 Connecting to Gmail...")
        credentials_path = Path('examples/gmail_credentials.json')
        token_path = Path('examples/gmail_token.json')
        
        credentials = {
            'credentials_file': str(credentials_path),
            'token_file': str(token_path)
        }
        
        success = await gmail.connect(credentials)
        if not success:
            raise Exception("Failed to connect to Gmail")
        
        profile = await gmail.get_profile()
        print(f"✅ Connected to Gmail as: {profile.get('name', 'Unknown')} ({profile.get('email', 'Unknown')})")
        
        # Search for emails with attachments from the last 90 days
        print("\n📎 Searching for emails with attachments (last 90 days)...")
        
        criteria = EmailSearchCriteria(
            has_attachments=True,
            date_after=datetime.now() - timedelta(days=90),
            max_results=50
        )
        
        emails = await gmail.list_emails(criteria)
        print(f"📧 Found {len(emails)} emails with attachments")
        
        if not emails:
            print("❌ No emails with attachments found in the last 90 days")
            print("   Try expanding the search criteria or checking older emails")
            return
        
        # Show some examples first
        print(f"\n📋 Sample emails with attachments:")
        for i, email in enumerate(emails[:5]):
            print(f"   {i+1}. From: {email.sender.address}")
            print(f"      Subject: {email.subject[:60]}...")
            print(f"      Attachments: {len(email.attachments)}")
            for j, att in enumerate(email.attachments):
                print(f"         {j+1}. {att.filename} ({att.content_type})")
        
        # Ask user to continue
        if len(emails) > 5:
            response = input(f"\n🤔 Process all {len(emails)} emails? (y/n): ").lower()
            if response != 'y':
                emails = emails[:5]
                print(f"📧 Processing first 5 emails only")
        
        # Process each email
        print(f"\n🚀 Processing {len(emails)} emails through the asset document agent...")
        
        results = []
        stats = {
            'total_emails': 0,
            'total_attachments': 0,
            'clean_attachments': 0,
            'quarantined_attachments': 0,
            'invalid_type_attachments': 0,
            'duplicate_attachments': 0,
            'classified_documents': 0,
            'high_confidence_classifications': 0,
            'processing_errors': 0
        }
        
        for i, email in enumerate(emails, 1):
            print(f"\n📧 [{i}/{len(emails)}] Processing: {email.subject[:50]}...")
            print(f"   From: {email.sender.address}")
            print(f"   Attachments: {len(email.attachments)}")
            
            stats['total_emails'] += 1
            stats['total_attachments'] += len(email.attachments)
            
            try:
                # Get full email with attachment content
                full_email = await gmail.get_email(email.id, include_attachments=True)
                
                for j, attachment in enumerate(full_email.attachments):
                    print(f"     📎 Attachment {j+1}: {attachment.filename}")
                    
                    if not attachment.content:
                        print(f"       ⚠️ No content available")
                        continue
                    
                    # Prepare data for agent processing
                    attachment_data = {
                        'filename': attachment.filename,
                        'content': attachment.content
                    }
                    
                    email_data = {
                        'sender_email': email.sender.address,
                        'sender_name': email.sender.name or email.sender.address,
                        'subject': email.subject or '(no subject)',
                        'body': full_email.body_text or full_email.body_html or '',
                        'date': email.sent_date.isoformat() if email.sent_date else datetime.now().isoformat()
                    }
                    
                    # Process through enhanced pipeline (Phase 3)
                    result = await agent.enhanced_process_attachment(attachment_data, email_data)
                    
                    # Update statistics
                    if result.status == ProcessingStatus.SUCCESS:
                        stats['clean_attachments'] += 1
                        if result.document_category:
                            stats['classified_documents'] += 1
                            if result.confidence_level == ConfidenceLevel.HIGH:
                                stats['high_confidence_classifications'] += 1
                    elif result.status == ProcessingStatus.QUARANTINED:
                        stats['quarantined_attachments'] += 1
                    elif result.status == ProcessingStatus.INVALID_TYPE:
                        stats['invalid_type_attachments'] += 1
                    elif result.status == ProcessingStatus.DUPLICATE:
                        stats['duplicate_attachments'] += 1
                    
                    # Log results
                    if result.status == ProcessingStatus.SUCCESS:
                        print(f"       ✅ Processed successfully")
                        if result.document_category:
                            print(f"       📋 Category: {result.document_category.value}")
                            print(f"       🎯 Confidence: {result.confidence_level.value}")
                            if result.matched_asset_id:
                                print(f"       🏢 Asset Match: {result.matched_asset_id} (confidence: {result.asset_confidence:.2f})")
                    elif result.status == ProcessingStatus.QUARANTINED:
                        print(f"       🦠 Quarantined: {result.quarantine_reason}")
                    elif result.status == ProcessingStatus.DUPLICATE:
                        print(f"       🔄 Duplicate of: {result.duplicate_of}")
                    elif result.status == ProcessingStatus.INVALID_TYPE:
                        print(f"       ❌ Invalid file type: {Path(attachment.filename).suffix}")
                    else:
                        print(f"       ⚠️ Status: {result.status.value}")
                        if result.error_message:
                            print(f"       Error: {result.error_message}")
                    
                    # Store result
                    results.append({
                        'email_sender': email.sender.address,
                        'email_subject': email.subject,
                        'attachment_filename': attachment.filename,
                        'status': result.status.value,
                        'document_category': result.document_category.value if result.document_category else None,
                        'confidence_level': result.confidence_level.value if result.confidence_level else None,
                        'file_hash': result.file_hash,
                        'quarantine_reason': result.quarantine_reason,
                        'error_message': result.error_message
                    })
            
            except Exception as e:
                print(f"   ❌ Error processing email: {e}")
                stats['processing_errors'] += 1
        
        # Print statistics
        print("\n" + "="*80)
        print("📊 ATTACHMENT PROCESSING STATISTICS")
        print("="*80)
        
        print(f"\n📧 EMAIL OVERVIEW:")
        print(f"   Total Emails Processed: {stats['total_emails']}")
        print(f"   Total Attachments: {stats['total_attachments']}")
        
        if stats['total_attachments'] > 0:
            print(f"\n📎 ATTACHMENT PROCESSING:")
            print(f"   ✅ Clean Attachments: {stats['clean_attachments']} ({stats['clean_attachments']/stats['total_attachments']*100:.1f}%)")
            print(f"   🦠 Quarantined (Virus): {stats['quarantined_attachments']} ({stats['quarantined_attachments']/stats['total_attachments']*100:.1f}%)")
            print(f"   🔄 Duplicates: {stats['duplicate_attachments']} ({stats['duplicate_attachments']/stats['total_attachments']*100:.1f}%)")
            print(f"   ❌ Invalid Types: {stats['invalid_type_attachments']} ({stats['invalid_type_attachments']/stats['total_attachments']*100:.1f}%)")
            
            print(f"\n🧠 DOCUMENT CLASSIFICATION:")
            print(f"   📋 Successfully Classified: {stats['classified_documents']} ({stats['classified_documents']/stats['total_attachments']*100:.1f}%)")
            print(f"   🎯 High Confidence Classifications: {stats['high_confidence_classifications']} ({stats['high_confidence_classifications']/stats['total_attachments']*100:.1f}%)")
        
        print(f"\n⚠️ ERRORS:")
        print(f"   Processing Errors: {stats['processing_errors']}")
        
        # Save results
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        results_file = f"attachment_processing_results_{timestamp}.json"
        
        with open(results_file, 'w') as f:
            json.dump({
                'test_metadata': {
                    'timestamp': timestamp,
                    'test_type': 'attachment_processing',
                    'agent_version': 'Phase 3'
                },
                'statistics': stats,
                'results': results
            }, f, indent=2)
        
        print(f"\n💾 Results saved to: {results_file}")
        print(f"🎉 Processing complete! Processed {stats['total_attachments']} attachments from {stats['total_emails']} emails.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"🐛 Traceback: {traceback.format_exc()}")
    
    finally:
        # Cleanup
        if gmail:
            await gmail.disconnect()
        print("\n🔒 Disconnected from Gmail")

if __name__ == "__main__":
    asyncio.run(main()) 