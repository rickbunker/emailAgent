#!/usr/bin/env python3
"""
Real Microsoft Graph Email-to-Folder Workflow

Connects to actual Microsoft/Outlook account and processes emails with attachments 
from the last 24 hours, saving them to organized asset folders.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.msgraph import MicrosoftGraphInterface
from email_interface.base import EmailSearchCriteria
from agents.asset_document_agent import AssetDocumentAgent, AssetType
from utils.logging_system import get_logger, LogConfig, configure_logging

# Configure logging
config = LogConfig(
    level="INFO",
    log_to_file=True,
    log_to_stdout=True,
    log_file="logs/msgraph_real_workflow.log",
    log_arguments=False,
    log_return_values=False,
    log_execution_time=True
)
configure_logging(config)
logger = get_logger(__name__)

class RealMicrosoftGraphWorkflow:
    """Real Microsoft Graph email processing workflow."""
    
    def __init__(self):
        """Initialize the real Microsoft Graph workflow system."""
        self.msgraph_interface = None
        self.asset_agent = None
        self.stats = {
            'emails_found': 0,
            'emails_processed': 0,
            'attachments_found': 0,
            'attachments_saved': 0,
            'assets_matched': 0,
            'files_organized': 0,
            'errors': 0
        }
    
    async def setup_msgraph_connection(self) -> bool:
        """
        Setup real Microsoft Graph connection using OAuth credentials.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            logger.info("🔐 Setting up Microsoft Graph connection...")
            
            # Initialize Microsoft Graph interface with credentials
            credentials_path = 'msgraph_credentials.json'
            
            if not os.path.exists(credentials_path):
                logger.error(f"Microsoft Graph credentials not found at: {credentials_path}")
                logger.error("Please follow MSGRAPH_SETUP.md to set up credentials")
                return False
            
            self.msgraph_interface = MicrosoftGraphInterface(credentials_path=credentials_path)
            
            # Test connection (credentials are loaded automatically in constructor)
            await self.msgraph_interface.connect()
            
            logger.info("✅ Microsoft Graph connection established successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Microsoft Graph connection: {e}")
            return False
    
    async def setup_asset_agent(self) -> bool:
        """
        Setup the asset document agent with sample assets.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Initialize asset agent
            self.asset_agent = AssetDocumentAgent(base_assets_path="./msgraph_processed_attachments")
            
            # Create some sample assets for demonstration
            await self.create_sample_assets()
            
            logger.info("✅ Asset document agent initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup asset agent: {e}")
            return False
    
    async def create_sample_assets(self):
        """Create sample assets that might match email content."""
        
        # Real Estate Asset (common in email attachments)
        cre_asset_id = await self.asset_agent.create_asset(
            deal_name="Real_Estate_Portfolio",
            asset_name="Real Estate Investment Portfolio",
            asset_type=AssetType.COMMERCIAL_REAL_ESTATE,
            identifiers=["real estate", "property", "rent roll", "lease", "tenant"]
        )
        
        # Private Credit Asset 
        credit_asset_id = await self.asset_agent.create_asset(
            deal_name="Credit_Investments",
            asset_name="Private Credit Investment Portfolio",
            asset_type=AssetType.PRIVATE_CREDIT,
            identifiers=["loan", "credit", "borrower", "SBA", "finance", "lending"]
        )
        
        # Private Equity Asset
        pe_asset_id = await self.asset_agent.create_asset(
            deal_name="PE_Portfolio",
            asset_name="Private Equity Investment Portfolio", 
            asset_type=AssetType.PRIVATE_EQUITY,
            identifiers=["investment", "portfolio", "fund", "equity", "deal"]
        )
        
        logger.info(f"Created sample assets: RE={cre_asset_id[:8]}..., Credit={credit_asset_id[:8]}..., PE={pe_asset_id[:8]}...")
    
    async def find_recent_emails_with_attachments(self, hours_back: int = 24) -> list:
        """
        Find emails with attachments from the last N hours.
        
        Args:
            hours_back: Number of hours to look back
            
        Returns:
            List of emails with attachments
        """
        # Calculate date range with timezone awareness
        from datetime import timezone
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=hours_back)
        
        logger.info(f"🔍 Searching for emails with attachments from the last {hours_back} hours")
        logger.info(f"   Date range: {start_date.strftime('%Y-%m-%d %H:%M')} to {end_date.strftime('%Y-%m-%d %H:%M')}")
        
        # Create search criteria for emails with attachments
        criteria = EmailSearchCriteria(
            has_attachments=True,
            date_after=start_date,
            date_before=end_date,
            max_results=100  # Reasonable limit
        )
        
        try:
            # Get emails from Microsoft Graph
            emails = await self.msgraph_interface.list_emails(criteria)
            
        except Exception as e:
            logger.warning(f"Date filtering failed ({e}), falling back to basic attachment search...")
            # Fall back to basic attachment search without date filters
            fallback_criteria = EmailSearchCriteria(has_attachments=True, max_results=100)
            try:
                emails = await self.msgraph_interface.list_emails(fallback_criteria)
                logger.info(f"Found {len(emails)} emails with attachments (no date filter)")
                # Filter by date manually with timezone handling
                filtered_emails = []
                for email in emails:
                    if email.received_date:
                        # Ensure both dates are timezone-aware for comparison
                        email_date = email.received_date
                        if email_date.tzinfo is None:
                            email_date = email_date.replace(tzinfo=timezone.utc)
                        if start_date <= email_date <= end_date:
                            filtered_emails.append(email)
                emails = filtered_emails
                logger.info(f"After manual date filtering: {len(emails)} emails")
            except Exception as e2:
                logger.error(f"Fallback search also failed: {e2}")
                return []
        
        # Load full emails with attachments (Microsoft Graph search found these as having attachments)
        emails_with_attachments = []
        for email in emails:
            # Load the full email with attachments explicitly requested
            full_email = await self.msgraph_interface.get_email(email.id, include_attachments=True)
            if full_email.attachments:  # Check if attachments were actually loaded
                emails_with_attachments.append(full_email)
            else:
                logger.info(f"      ⚠️ Email {email.id} marked as having attachments but none found")
        
        self.stats['emails_found'] = len(emails_with_attachments)
        total_attachments = sum(len(email.attachments) for email in emails_with_attachments)
        
        logger.info(f"✅ Found {len(emails_with_attachments)} emails with {total_attachments} attachments")
        
        # Log some details about what we found
        for i, email in enumerate(emails_with_attachments[:5], 1):  # Show first 5
            logger.info(f"   📧 Email {i}: From {email.sender.address}")
            logger.info(f"      Subject: {email.subject[:60]}{'...' if len(email.subject) > 60 else ''}")
            logger.info(f"      Attachments: {len(email.attachments)}")
            for att in email.attachments:
                size_mb = att.size / (1024 * 1024) if att.size else 0
                logger.info(f"        📎 {att.filename} ({size_mb:.1f}MB)")
        
        if len(emails_with_attachments) > 5:
            logger.info(f"   ... and {len(emails_with_attachments) - 5} more emails")
        
        return emails_with_attachments
    
    async def process_real_email_attachments(self, emails: list) -> dict:
        """
        Process all attachments from the real Microsoft Graph emails.
        
        Args:
            emails: List of Email objects from Microsoft Graph
            
        Returns:
            Dictionary with processing results and statistics
        """
        results = {
            'processed_attachments': [],
            'saved_files': [],
            'asset_matches': [],
            'errors': []
        }
        
        logger.info(f"⚙️ Processing {len(emails)} emails with attachments...")
        
        for email in emails:
            self.stats['emails_processed'] += 1
            
            logger.info(f"\n📧 Processing email from {email.sender.address}")
            logger.info(f"   Subject: {email.subject}")
            logger.info(f"   Date: {email.received_date}")
            logger.info(f"   Attachments: {len(email.attachments)}")
            
            # Prepare email data for processing
            email_data = {
                'sender_email': email.sender.address,
                'sender_name': email.sender.name or email.sender.address,
                'subject': email.subject,
                'date': email.received_date.isoformat() if email.received_date else datetime.now().isoformat(),
                'body': email.body_text or email.body_html or ''
            }
            
            # Process all attachments in parallel for maximum performance
            if email.attachments:
                logger.info(f"   📎 Processing {len(email.attachments)} attachments in parallel...")
                
                # Prepare attachment data for parallel processing
                attachment_data_list = []
                for attachment in email.attachments:
                    self.stats['attachments_found'] += 1
                    
                    logger.info(f"      📄 {attachment.filename} ({attachment.size / (1024*1024):.1f}MB)")
                    
                    # Ensure attachment content is loaded
                    if not attachment.content:
                        logger.warning(f"      ⚠️ No content available for {attachment.filename}")
                        continue
                    
                    attachment_data_list.append({
                        'filename': attachment.filename,
                        'content': attachment.content
                    })
                
                # Process all attachments in parallel
                if attachment_data_list:
                    parallel_results = await self.asset_agent.process_attachments_parallel(
                        email_attachments=attachment_data_list,
                        email_data=email_data
                    )
                    
                    # Process results from parallel processing
                    for i, result in enumerate(parallel_results):
                        if i < len(email.attachments):
                            attachment = email.attachments[i]
                        else:
                            continue
                            
                        try:
                            # Record results
                            attachment_result = {
                                'email_id': email.id,
                                'email_sender': email.sender.address,
                                'email_subject': email.subject,
                                'email_date': str(email.received_date),
                                'filename': attachment.filename,
                                'file_size': attachment.size,
                                'content_type': attachment.content_type,
                                'status': result.status.value,
                                'file_path': str(result.file_path) if result.file_path else None,
                                'document_category': result.document_category.value if result.document_category else None,
                                'confidence_level': result.confidence_level.value if result.confidence_level else None,
                                'matched_asset_id': result.matched_asset_id,
                                'file_hash': result.file_hash,
                                'quarantine_reason': result.quarantine_reason,
                                'error_message': result.error_message
                            }
                            
                            results['processed_attachments'].append(attachment_result)
                            
                            # Update statistics
                            if result.file_path:
                                self.stats['attachments_saved'] += 1
                                self.stats['files_organized'] += 1
                                results['saved_files'].append(str(result.file_path))
                                
                            if result.matched_asset_id:
                                self.stats['assets_matched'] += 1
                                results['asset_matches'].append({
                                    'filename': attachment.filename,
                                    'asset_id': result.matched_asset_id,
                                    'confidence': result.asset_confidence
                                })
                            
                            # Log the outcome
                            if result.file_path:
                                logger.info(f"      ✅ Saved: {result.file_path}")
                                if result.document_category:
                                    logger.info(f"      📋 Category: {result.document_category.value}")
                                if result.matched_asset_id:
                                    logger.info(f"      🎯 Asset: {result.matched_asset_id[:8]}...")
                            elif result.status.value == "quarantined":
                                logger.warning(f"      🦠 Quarantined: {result.quarantine_reason}")
                            else:
                                logger.warning(f"      ⚠️ Not saved: {result.status.value}")
                                if result.error_message:
                                    logger.warning(f"         Error: {result.error_message}")
                        
                        except Exception as e:
                            self.stats['errors'] += 1
                            error_msg = f"Error processing attachment {i}: {e}"
                            logger.error(f"      ❌ {error_msg}")
                            results['errors'].append(error_msg)
        
        return results
    
    async def run_real_msgraph_workflow(self, hours_back: int = 24) -> bool:
        """
        Run the complete real Microsoft Graph workflow.
        
        Args:
            hours_back: Number of hours to look back for emails
            
        Returns:
            True if workflow completed successfully, False otherwise
        """
        logger.info("🚀 Starting Real Microsoft Graph Email-to-Folder Workflow")
        logger.info("=" * 60)
        
        # Step 1: Setup Microsoft Graph connection
        logger.info("📨 Step 1: Connecting to Microsoft Graph...")
        if not await self.setup_msgraph_connection():
            logger.error("Failed to connect to Microsoft Graph")
            return False
        
        # Step 2: Setup asset document agent
        logger.info("🏢 Step 2: Setting up asset document agent...")
        if not await self.setup_asset_agent():
            logger.error("Failed to setup asset agent")
            return False
        
        # Step 3: Find recent emails with attachments
        days = hours_back / 24
        logger.info(f"🔍 Step 3: Finding emails with attachments from last {hours_back} hours ({days:.1f} days)...")
        emails = await self.find_recent_emails_with_attachments(hours_back)
        
        if not emails:
            logger.info("No emails with attachments found in the specified time range")
            return True
        
        # Step 4: Process all attachments
        logger.info("⚙️ Step 4: Processing attachments and saving to folders...")
        results = await self.process_real_email_attachments(emails)
        
        # Step 5: Display results
        logger.info("\n📊 Step 5: Workflow Results")
        logger.info("-" * 40)
        
        logger.info(f"Emails found: {self.stats['emails_found']}")
        logger.info(f"Emails processed: {self.stats['emails_processed']}")
        logger.info(f"Attachments found: {self.stats['attachments_found']}")
        logger.info(f"Attachments saved: {self.stats['attachments_saved']}")
        logger.info(f"Assets matched: {self.stats['assets_matched']}")
        logger.info(f"Files organized: {self.stats['files_organized']}")
        logger.info(f"Errors: {self.stats['errors']}")
        
        if results['errors']:
            logger.warning(f"\nErrors encountered:")
            for error in results['errors']:
                logger.warning(f"  - {error}")
        
        # Show folder structure
        if self.stats['files_organized'] > 0:
            logger.info("\n📁 Created Folder Structure:")
            await self.show_folder_structure()
        
        # Save results to JSON file
        await self.save_results_to_file(results)
        
        logger.info("\n✅ Real Microsoft Graph workflow finished successfully!")
        return True
    
    async def show_folder_structure(self):
        """Display the created folder structure."""
        base_path = Path("./msgraph_processed_attachments")
        
        if base_path.exists():
            for root, dirs, files in os.walk(base_path):
                level = root.replace(str(base_path), '').count(os.sep)
                indent = '  ' * level
                folder_name = os.path.basename(root) or "msgraph_processed_attachments"
                logger.info(f"{indent}📁 {folder_name}/")
                
                # Show files in this folder
                sub_indent = '  ' * (level + 1)
                for file in files:
                    logger.info(f"{sub_indent}📄 {file}")
    
    async def save_results_to_file(self, results: dict):
        """Save processing results to JSON file."""
        import json
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"msgraph_attachment_processing_results_{timestamp}.json"
        
        # Add statistics to results
        results['statistics'] = self.stats
        results['timestamp'] = timestamp
        results['workflow_type'] = 'real_msgraph_workflow'
        
        try:
            with open(filename, 'w') as f:
                json.dump(results, f, indent=2)
            
            logger.info(f"📁 Results saved to: {filename}")
            
        except Exception as e:
            logger.error(f"Failed to save results: {e}")

async def main():
    """Main entry point for the real Microsoft Graph workflow."""
    workflow = RealMicrosoftGraphWorkflow()
    
    print("🚀 Real Microsoft Graph Email-to-Folder Workflow")
    print("=" * 60)
    print("This will:")
    print("1. Connect to your Microsoft/Outlook account")
    print("2. Find emails with attachments from the last 168 hours (7 days)")
    print("3. Process and classify attachments")
    print("4. Save files to organized folders")
    print("5. Generate processing report")
    print()
    
    try:
        success = await workflow.run_real_msgraph_workflow(hours_back=168)  # 7 days
        
        if success:
            print("\n🎉 Microsoft Graph workflow completed successfully!")
            print(f"\nStatistics:")
            print(f"  📧 Emails found: {workflow.stats['emails_found']}")
            print(f"  📎 Attachments found: {workflow.stats['attachments_found']}")
            print(f"  💾 Attachments saved: {workflow.stats['attachments_saved']}")
            print(f"  🎯 Assets matched: {workflow.stats['assets_matched']}")
            print(f"  📁 Files organized: {workflow.stats['files_organized']}")
            
            if workflow.stats['errors'] > 0:
                print(f"  ❌ Errors: {workflow.stats['errors']}")
            
            print(f"\n📂 Check the 'msgraph_processed_attachments' folder for saved files")
            
        else:
            print("\n❌ Microsoft Graph workflow failed - check logs for details")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Workflow interrupted by user")
        logger.info("Workflow interrupted by user")
        
    except Exception as e:
        logger.error(f"Workflow failed with exception: {e}")
        print(f"\n💥 Workflow crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 