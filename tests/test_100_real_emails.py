#!/usr/bin/env python3
"""
Comprehensive Real Email Processing Test

This script fetches 100 real emails from your Gmail account and processes them
through the complete Asset Document Agent pipeline including:

- Email interface connection
- Attachment extraction and validation
- File type and size validation
- ClamAV virus scanning
- Document classification
- Asset identification
- Confidence scoring
- Full processing pipeline

Setup Required:
1. Gmail API credentials (gmail_credentials.json) should already be set up
2. ClamAV should be installed and working
3. Virtual environment should be activated

Usage:
    python test_100_real_emails.py
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

@dataclass
class EmailProcessingResult:
    """Result of processing a single email through the agent."""
    email_id: str
    sender: str
    subject: str
    date: str
    attachment_count: int
    processing_results: List[Dict[str, Any]]
    total_processing_time: float
    has_spam_indicators: bool
    overall_status: str
    errors: List[str]

class RealEmailProcessor:
    """Processes real emails through the asset document agent."""
    
    def __init__(self):
        self.gmail = None
        self.agent = AssetDocumentAgent()
        self.results = []
        self.stats = {
            'total_emails': 0,
            'emails_with_attachments': 0,
            'total_attachments': 0,
            'clean_attachments': 0,
            'quarantined_attachments': 0,
            'invalid_type_attachments': 0,
            'duplicate_attachments': 0,
            'classified_documents': 0,
            'high_confidence_classifications': 0,
            'processing_errors': 0
        }
        
    async def connect_gmail(self):
        """Connect to Gmail using existing credentials."""
        print("🔗 Connecting to Gmail...")
        
        try:
            self.gmail = EmailInterfaceFactory.create('gmail')
            
            # Use the existing credentials from examples directory
            credentials_path = Path('examples/gmail_credentials.json')
            token_path = Path('examples/gmail_token.json')
            
            if not credentials_path.exists():
                raise FileNotFoundError("Gmail credentials not found. Run examples/gmail_spam_test.py first to set up authentication.")
            
            credentials = {
                'credentials_file': str(credentials_path),
                'token_file': str(token_path)
            }
            
            success = await self.gmail.connect(credentials)
            if not success:
                raise Exception("Failed to connect to Gmail")
            
            profile = await self.gmail.get_profile()
            print(f"✅ Connected to Gmail as: {profile.get('name', 'Unknown')} ({profile.get('email', 'Unknown')})")
            
        except Exception as e:
            print(f"❌ Failed to connect to Gmail: {e}")
            raise
    
    async def fetch_emails(self, count: int = 100) -> List:
        """Fetch recent emails from Gmail."""
        print(f"📧 Fetching {count} recent emails...")
        
        # Search for emails from the last 30 days with various criteria
        criteria = EmailSearchCriteria(
            max_results=count,
            date_after=datetime.now() - timedelta(days=30)
        )
        
        emails = await self.gmail.list_emails(criteria)
        print(f"📬 Fetched {len(emails)} emails")
        
        return emails
    
    async def process_single_email(self, email) -> EmailProcessingResult:
        """Process a single email through the complete pipeline."""
        start_time = datetime.now()
        
        print(f"\n📧 Processing: {email.subject[:50]}..." if email.subject else "📧 Processing: (no subject)")
        print(f"   From: {email.sender.address}")
        print(f"   Date: {email.sent_date}")
        print(f"   Attachments: {len(email.attachments)}")
        
        processing_results = []
        errors = []
        has_spam_indicators = False
        overall_status = "success"
        
        try:
            # Update statistics
            self.stats['total_emails'] += 1
            
            if email.attachments:
                self.stats['emails_with_attachments'] += 1
                self.stats['total_attachments'] += len(email.attachments)
                
                # Process each attachment
                for i, attachment in enumerate(email.attachments):
                    print(f"     📎 Attachment {i+1}: {attachment.filename}")
                    
                    try:
                        # Get full email with attachment content
                        full_email = await self.gmail.get_email(email.id, include_attachments=True)
                        full_attachment = full_email.attachments[i]
                        
                        if not full_attachment.content:
                            print(f"       ⚠️ No content available for {attachment.filename}")
                            continue
                        
                        # Prepare data for agent processing
                        attachment_data = {
                            'filename': full_attachment.filename,
                            'content': full_attachment.content
                        }
                        
                        email_data = {
                            'sender_email': email.sender.address,
                            'sender_name': email.sender.name or email.sender.address,
                            'subject': email.subject or '(no subject)',
                            'body': email.body_text or email.body_html or '',
                            'date': email.sent_date.isoformat() if email.sent_date else datetime.now().isoformat()
                        }
                        
                        # Process through enhanced pipeline (Phase 3)
                        result = await self.agent.enhanced_process_attachment(attachment_data, email_data)
                        
                        # Update statistics based on result
                        if result.status == ProcessingStatus.SUCCESS:
                            self.stats['clean_attachments'] += 1
                            if result.document_category:
                                self.stats['classified_documents'] += 1
                                if result.confidence_level == ConfidenceLevel.HIGH:
                                    self.stats['high_confidence_classifications'] += 1
                        elif result.status == ProcessingStatus.QUARANTINED:
                            self.stats['quarantined_attachments'] += 1
                        elif result.status == ProcessingStatus.INVALID_TYPE:
                            self.stats['invalid_type_attachments'] += 1
                        elif result.status == ProcessingStatus.DUPLICATE:
                            self.stats['duplicate_attachments'] += 1
                        
                        # Convert result to dict for storage
                        result_dict = {
                            'filename': attachment.filename,
                            'status': result.status.value,
                            'file_hash': result.file_hash,
                            'confidence': result.confidence,
                            'document_category': result.document_category.value if result.document_category else None,
                            'confidence_level': result.confidence_level.value if result.confidence_level else None,
                            'matched_asset_id': result.matched_asset_id,
                            'asset_confidence': result.asset_confidence,
                            'error_message': result.error_message,
                            'quarantine_reason': result.quarantine_reason
                        }
                        
                        processing_results.append(result_dict)
                        
                        # Log detailed results
                        if result.status == ProcessingStatus.SUCCESS:
                            print(f"       ✅ Processed successfully")
                            if result.document_category:
                                print(f"       📋 Category: {result.document_category.value}")
                                print(f"       🎯 Confidence: {result.confidence_level.value}")
                        elif result.status == ProcessingStatus.QUARANTINED:
                            print(f"       🦠 Quarantined: {result.quarantine_reason}")
                            has_spam_indicators = True
                        elif result.status == ProcessingStatus.DUPLICATE:
                            print(f"       🔄 Duplicate detected")
                        else:
                            print(f"       ⚠️ Status: {result.status.value}")
                            if result.error_message:
                                print(f"       ❌ Error: {result.error_message}")
                        
                    except Exception as e:
                        error_msg = f"Attachment processing error: {str(e)}"
                        errors.append(error_msg)
                        print(f"       ❌ {error_msg}")
                        self.stats['processing_errors'] += 1
            
            else:
                print("     📝 No attachments to process")
        
        except Exception as e:
            error_msg = f"Email processing error: {str(e)}"
            errors.append(error_msg)
            overall_status = "error"
            print(f"   ❌ {error_msg}")
            self.stats['processing_errors'] += 1
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Create result
        result = EmailProcessingResult(
            email_id=email.id,
            sender=email.sender.address,
            subject=email.subject or '(no subject)',
            date=email.sent_date.isoformat() if email.sent_date else '',
            attachment_count=len(email.attachments),
            processing_results=processing_results,
            total_processing_time=processing_time,
            has_spam_indicators=has_spam_indicators,
            overall_status=overall_status,
            errors=errors
        )
        
        self.results.append(result)
        return result
    
    def save_results(self):
        """Save processing results to CSV and JSON files."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save detailed results to JSON
        json_file = f"email_processing_results_{timestamp}.json"
        with open(json_file, 'w') as f:
            # Convert results to serializable format
            serializable_results = []
            for result in self.results:
                result_dict = asdict(result)
                serializable_results.append(result_dict)
            
            json.dump({
                'test_metadata': {
                    'timestamp': timestamp,
                    'total_emails_processed': len(self.results),
                    'agent_version': 'Phase 3',
                    'test_type': 'real_email_processing'
                },
                'statistics': self.stats,
                'results': serializable_results
            }, f, indent=2)
        
        # Save summary to CSV
        csv_file = f"email_processing_summary_{timestamp}.csv"
        with open(csv_file, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Email ID', 'Sender', 'Subject', 'Date', 'Attachment Count', 
                'Processing Time (s)', 'Has Spam Indicators', 'Overall Status', 'Error Count'
            ])
            
            for result in self.results:
                writer.writerow([
                    result.email_id,
                    result.sender,
                    result.subject[:100],  # Truncate long subjects
                    result.date,
                    result.attachment_count,
                    f"{result.total_processing_time:.2f}",
                    result.has_spam_indicators,
                    result.overall_status,
                    len(result.errors)
                ])
        
        print(f"\n💾 Results saved:")
        print(f"   📊 Detailed results: {json_file}")
        print(f"   📋 Summary CSV: {csv_file}")
        
        return json_file, csv_file
    
    def print_statistics(self):
        """Print comprehensive processing statistics."""
        print("\n" + "="*80)
        print("📊 EMAIL PROCESSING STATISTICS")
        print("="*80)
        
        print(f"\n📧 EMAIL OVERVIEW:")
        print(f"   Total Emails Processed: {self.stats['total_emails']}")
        print(f"   Emails with Attachments: {self.stats['emails_with_attachments']}")
        print(f"   Total Attachments: {self.stats['total_attachments']}")
        
        if self.stats['total_attachments'] > 0:
            print(f"\n📎 ATTACHMENT PROCESSING:")
            print(f"   ✅ Clean Attachments: {self.stats['clean_attachments']} ({self.stats['clean_attachments']/self.stats['total_attachments']*100:.1f}%)")
            print(f"   🦠 Quarantined (Virus): {self.stats['quarantined_attachments']} ({self.stats['quarantined_attachments']/self.stats['total_attachments']*100:.1f}%)")
            print(f"   🔄 Duplicates: {self.stats['duplicate_attachments']} ({self.stats['duplicate_attachments']/self.stats['total_attachments']*100:.1f}%)")
            print(f"   ❌ Invalid Types: {self.stats['invalid_type_attachments']} ({self.stats['invalid_type_attachments']/self.stats['total_attachments']*100:.1f}%)")
            
            print(f"\n🧠 DOCUMENT CLASSIFICATION:")
            print(f"   📋 Successfully Classified: {self.stats['classified_documents']} ({self.stats['classified_documents']/self.stats['total_attachments']*100:.1f}%)")
            print(f"   🎯 High Confidence Classifications: {self.stats['high_confidence_classifications']} ({self.stats['high_confidence_classifications']/self.stats['total_attachments']*100:.1f}%)")
        
        print(f"\n⚠️ ERRORS:")
        print(f"   Processing Errors: {self.stats['processing_errors']}")
        
        # Print some sample results
        print(f"\n📋 SAMPLE RESULTS:")
        successful_attachments = [r for r in self.results if r.processing_results and any(pr['status'] == 'success' for pr in r.processing_results)]
        
        if successful_attachments:
            print("   ✅ Successfully Processed Attachments:")
            for i, result in enumerate(successful_attachments[:5]):  # Show first 5
                for pr in result.processing_results:
                    if pr['status'] == 'success':
                        print(f"      {i+1}. {pr['filename']} - {pr.get('document_category', 'unclassified')} (confidence: {pr.get('confidence_level', 'unknown')})")
        
        quarantined_attachments = [r for r in self.results if r.processing_results and any(pr['status'] == 'quarantined' for pr in r.processing_results)]
        if quarantined_attachments:
            print("   🦠 Quarantined Attachments:")
            for i, result in enumerate(quarantined_attachments[:3]):  # Show first 3
                for pr in result.processing_results:
                    if pr['status'] == 'quarantined':
                        print(f"      {i+1}. {pr['filename']} - {pr.get('quarantine_reason', 'unknown reason')}")

async def main():
    """Main function to run the comprehensive email processing test."""
    print("🧪 COMPREHENSIVE REAL EMAIL PROCESSING TEST")
    print("="*80)
    print("Testing 100 real emails through the complete Asset Document Agent pipeline")
    print("="*80)
    
    processor = RealEmailProcessor()
    
    try:
        # Connect to Gmail
        await processor.connect_gmail()
        
        # Fetch emails
        emails = await processor.fetch_emails(100)
        
        if not emails:
            print("❌ No emails found to process")
            return
        
        print(f"\n🚀 Processing {len(emails)} emails through the asset document agent...")
        
        # Process each email
        for i, email in enumerate(emails, 1):
            print(f"\n📧 [{i}/{len(emails)}] ", end="")
            await processor.process_single_email(email)
        
        # Print statistics
        processor.print_statistics()
        
        # Save results
        processor.save_results()
        
        print(f"\n🎉 Processing complete! Processed {len(emails)} emails through the full pipeline.")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        print(f"🐛 Traceback: {traceback.format_exc()}")
    
    finally:
        # Cleanup
        if processor.gmail:
            await processor.gmail.disconnect()
        print("\n🔒 Disconnected from Gmail")

if __name__ == "__main__":
    asyncio.run(main()) 