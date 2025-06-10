#!/usr/bin/env python3
"""
Complete Email-to-Folder Workflow Example

Demonstrates the complete pipeline:
1. Reading emails from Gmail/Microsoft Graph
2. Finding emails with attachments 
3. Processing attachments through AI classification
4. Saving files to organized asset folders

This is the core business workflow of the EmailAgent system.
"""

import asyncio
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface.gmail import GmailInterface
from email_interface.msgraph import MicrosoftGraphInterface  
from email_interface.base import EmailSearchCriteria
from agents.asset_document_agent import AssetDocumentAgent, AssetType
from utils.logging_system import get_logger, LogConfig, configure_logging

# Configure logging
config = LogConfig(
    level="INFO",
    log_to_file=True,
    log_to_stdout=True,
    log_file="logs/complete_workflow_example.log",
    log_arguments=False,
    log_return_values=False,
    log_execution_time=True
)
configure_logging(config)
logger = get_logger(__name__)

class CompleteEmailWorkflow:
    """Complete email processing workflow demonstration."""
    
    def __init__(self):
        """Initialize the complete workflow system."""
        self.email_interface = None
        self.asset_agent = None
        self.stats = {
            'emails_processed': 0,
            'attachments_found': 0,
            'attachments_saved': 0,
            'assets_matched': 0,
            'files_organized': 0
        }
    
    async def setup_email_interface(self, use_gmail: bool = True) -> bool:
        """
        Setup email interface (Gmail or Microsoft Graph).
        
        Args:
            use_gmail: True for Gmail, False for Microsoft Graph
            
        Returns:
            True if setup successful, False otherwise
        """
        try:
            if use_gmail:
                self.email_interface = GmailInterface()
                logger.info("Attempting Gmail connection...")
                
                # Try to connect (would normally use real credentials)
                # For demo, we'll simulate connection
                logger.info("✅ Gmail interface initialized (demo mode)")
                return True
            else:
                self.email_interface = MicrosoftGraphInterface()
                logger.info("Attempting Microsoft Graph connection...")
                
                # Try to connect (would normally use real credentials)
                # For demo, we'll simulate connection
                logger.info("✅ Microsoft Graph interface initialized (demo mode)")
                return True
                
        except Exception as e:
            logger.error(f"Failed to setup email interface: {e}")
            return False
    
    async def setup_asset_agent(self) -> bool:
        """
        Setup the asset document agent with initial assets.
        
        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Initialize asset agent
            self.asset_agent = AssetDocumentAgent(base_assets_path="./processed_attachments")
            
            # Create some sample assets for demonstration
            await self.create_sample_assets()
            
            logger.info("✅ Asset document agent initialized")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup asset agent: {e}")
            return False
    
    async def create_sample_assets(self):
        """Create sample assets for demonstration."""
        
        # Commercial Real Estate Asset
        cre_asset_id = await self.asset_agent.create_asset(
            deal_name="Main_Street_Plaza",
            asset_name="Main Street Plaza Commercial Complex",
            asset_type=AssetType.COMMERCIAL_REAL_ESTATE,
            identifiers=["123 Main Street", "Main Street Plaza", "MSP Commercial"]
        )
        
        # Create asset-sender mapping
        await self.asset_agent.create_asset_sender_mapping(
            asset_id=cre_asset_id,
            sender_email="property.manager@realestate.com", 
            confidence=0.95,
            document_types=["rent_roll", "financial_statements", "lease_documents"]
        )
        
        # Private Credit Asset
        credit_asset_id = await self.asset_agent.create_asset(
            deal_name="TechCorp_Term_Loan",
            asset_name="TechCorp Senior Term Loan Facility",
            asset_type=AssetType.PRIVATE_CREDIT,
            identifiers=["TechCorp", "Term Loan", "SBA Loan #3010259108"]
        )
        
        # Create asset-sender mapping
        await self.asset_agent.create_asset_sender_mapping(
            asset_id=credit_asset_id,
            sender_email="alan@bassman.com",
            confidence=0.90,
            document_types=["loan_documents", "borrower_financials", "covenant_compliance"]
        )
        
        logger.info(f"Created sample assets: CRE={cre_asset_id[:8]}..., Credit={credit_asset_id[:8]}...")
    
    async def find_emails_with_attachments(self, days_back: int = 7) -> list:
        """
        Find emails with attachments from the last N days.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of emails with attachments
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Create search criteria for emails with attachments
        criteria = EmailSearchCriteria(
            has_attachments=True,
            date_after=start_date,
            date_before=end_date,
            max_results=50  # Limit for demo
        )
        
        logger.info(f"Searching for emails with attachments from {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}")
        
        # For demo purposes, simulate email results
        # In real implementation, this would be:
        # emails = await self.email_interface.list_emails(criteria)
        
        # Simulate finding emails with attachments
        simulated_emails = [
            {
                'id': 'email_001',
                'sender': 'property.manager@realestate.com',
                'sender_name': 'John Property Manager',
                'subject': 'Q4 2024 Rent Roll for Main Street Plaza',
                'received_date': datetime.now() - timedelta(days=2),
                'attachments': [
                    {
                        'filename': 'rent_roll_Q4_2024.xlsx',
                        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'size': 2048576,
                        'content': b'MOCK_EXCEL_RENT_ROLL_CONTENT' * 500  # Simulated Excel content
                    },
                    {
                        'filename': 'tenant_photos.jpg', 
                        'content_type': 'image/jpeg',
                        'size': 1048576,
                        'content': b'MOCK_JPEG_IMAGE_CONTENT' * 300  # Simulated image content
                    }
                ]
            },
            {
                'id': 'email_002',
                'sender': 'alan@bassman.com',
                'sender_name': 'Alan Bassman',
                'subject': 'RE: SBA Loan #3010259108 Quarterly Financials',
                'received_date': datetime.now() - timedelta(days=1),
                'attachments': [
                    {
                        'filename': 'borrower_financials_Q4.pdf',
                        'content_type': 'application/pdf', 
                        'size': 3145728,
                        'content': b'MOCK_PDF_FINANCIAL_CONTENT' * 700  # Simulated PDF content
                    },
                    {
                        'filename': 'covenant_compliance_report.xlsx',
                        'content_type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                        'size': 1572864,
                        'content': b'MOCK_EXCEL_COMPLIANCE_CONTENT' * 400  # Simulated Excel content
                    }
                ]
            },
            {
                'id': 'email_003', 
                'sender': 'unknown.sender@somecompany.com',
                'sender_name': 'Unknown Sender',
                'subject': 'Investment Opportunity Documentation',
                'received_date': datetime.now() - timedelta(hours=6),
                'attachments': [
                    {
                        'filename': 'investment_memo.pdf',
                        'content_type': 'application/pdf',
                        'size': 4194304,
                        'content': b'MOCK_PDF_INVESTMENT_MEMO_CONTENT' * 800  # Simulated PDF content
                    }
                ]
            }
        ]
        
        logger.info(f"Found {len(simulated_emails)} emails with {sum(len(e['attachments']) for e in simulated_emails)} attachments")
        return simulated_emails
    
    async def process_email_attachments(self, emails: list) -> dict:
        """
        Process all attachments from the provided emails.
        
        Args:
            emails: List of email dictionaries with attachment data
            
        Returns:
            Dictionary with processing results and statistics
        """
        results = {
            'processed_attachments': [],
            'saved_files': [],
            'asset_matches': [],
            'errors': []
        }
        
        for email in emails:
            self.stats['emails_processed'] += 1
            
            logger.info(f"\n📧 Processing email from {email['sender']}")
            logger.info(f"   Subject: {email['subject']}")
            logger.info(f"   Attachments: {len(email['attachments'])}")
            
            # Prepare email data for processing
            email_data = {
                'sender_email': email['sender'],
                'sender_name': email['sender_name'],
                'subject': email['subject'],
                'date': email['received_date'].isoformat(),
                'body': ''  # Would contain email body in real implementation
            }
            
            # Process each attachment
            for attachment in email['attachments']:
                self.stats['attachments_found'] += 1
                
                logger.info(f"   📎 Processing: {attachment['filename']}")
                
                try:
                    # Process attachment through complete pipeline
                    result = await self.asset_agent.process_and_save_attachment(
                        attachment_data={
                            'filename': attachment['filename'],
                            'content': attachment['content']
                        },
                        email_data=email_data,
                        save_to_disk=True  # Actually save the files
                    )
                    
                    # Record results
                    attachment_result = {
                        'email_sender': email['sender'],
                        'email_subject': email['subject'],
                        'filename': attachment['filename'],
                        'status': result.status.value,
                        'file_path': str(result.file_path) if result.file_path else None,
                        'document_category': result.document_category.value if result.document_category else None,
                        'confidence_level': result.confidence_level.value if result.confidence_level else None,
                        'matched_asset_id': result.matched_asset_id,
                        'file_hash': result.file_hash
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
                            'filename': attachment['filename'],
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
                    else:
                        logger.warning(f"      ⚠️ Not saved: {result.status.value}")
                
                except Exception as e:
                    error_msg = f"Error processing {attachment['filename']}: {e}"
                    logger.error(f"      ❌ {error_msg}")
                    results['errors'].append(error_msg)
        
        return results
    
    async def run_complete_workflow(self) -> bool:
        """
        Run the complete email-to-folder workflow.
        
        Returns:
            True if workflow completed successfully, False otherwise
        """
        logger.info("🚀 Starting Complete Email-to-Folder Workflow")
        logger.info("=" * 60)
        
        # Step 1: Setup email interface
        logger.info("📨 Step 1: Setting up email interface...")
        if not await self.setup_email_interface(use_gmail=True):
            logger.error("Failed to setup email interface")
            return False
        
        # Step 2: Setup asset document agent
        logger.info("🏢 Step 2: Setting up asset document agent...")
        if not await self.setup_asset_agent():
            logger.error("Failed to setup asset agent")
            return False
        
        # Step 3: Find emails with attachments
        logger.info("🔍 Step 3: Finding emails with attachments...")
        emails = await self.find_emails_with_attachments(days_back=7)
        
        if not emails:
            logger.info("No emails with attachments found")
            return True
        
        # Step 4: Process all attachments
        logger.info("⚙️ Step 4: Processing attachments and saving to folders...")
        results = await self.process_email_attachments(emails)
        
        # Step 5: Display results
        logger.info("📊 Step 5: Workflow Results")
        logger.info("-" * 40)
        
        logger.info(f"Emails processed: {self.stats['emails_processed']}")
        logger.info(f"Attachments found: {self.stats['attachments_found']}")
        logger.info(f"Attachments saved: {self.stats['attachments_saved']}")
        logger.info(f"Assets matched: {self.stats['assets_matched']}")
        logger.info(f"Files organized: {self.stats['files_organized']}")
        
        if results['errors']:
            logger.warning(f"Errors encountered: {len(results['errors'])}")
            for error in results['errors']:
                logger.warning(f"  - {error}")
        
        # Show folder structure
        logger.info("\n📁 Created Folder Structure:")
        await self.show_folder_structure()
        
        logger.info("\n✅ Complete workflow finished successfully!")
        return True
    
    async def show_folder_structure(self):
        """Display the created folder structure."""
        base_path = Path("./processed_attachments")
        
        if base_path.exists():
            for root, dirs, files in os.walk(base_path):
                level = root.replace(str(base_path), '').count(os.sep)
                indent = '  ' * level
                folder_name = os.path.basename(root) or "processed_attachments"
                logger.info(f"{indent}📁 {folder_name}/")
                
                # Show files in this folder
                sub_indent = '  ' * (level + 1)
                for file in files:
                    logger.info(f"{sub_indent}📄 {file}")

async def main():
    """Main entry point for the complete workflow example."""
    workflow = CompleteEmailWorkflow()
    
    try:
        success = await workflow.run_complete_workflow()
        
        if success:
            print("\n🎉 Workflow completed successfully!")
            print("\nNext steps:")
            print("1. Connect real email credentials for Gmail/Microsoft Graph")
            print("2. Set up Qdrant vector database for production")
            print("3. Configure ClamAV for virus scanning")
            print("4. Create additional assets and sender mappings")
            print("5. Integrate with the email supervisor for automation")
        else:
            print("\n❌ Workflow failed - check logs for details")
            
    except Exception as e:
        logger.error(f"Workflow failed with exception: {e}")
        print(f"\n💥 Workflow crashed: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 