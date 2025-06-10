"""
Microsoft Graph Spam Management System

This script provides complete spam detection and management for Microsoft 365/Outlook
using Microsoft Graph API. It integrates SpamAssassin for spam detection with automated
actions like unsubscribing and moving emails to junk folders.

Features:
- SpamAssassin integration for spam detection
- Multi-level whitelist protection (government, financial, news, personal contacts)
- Microsoft Graph contacts integration for automatic protection
- Automated unsubscribe attempts for legitimate senders
- Detailed logging and reporting
- Outlook folder-based spam management
"""

import asyncio
import sys
import os
import re
import csv
import json
import aiohttp
import subprocess
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urlparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory

# SpamAssassin detection result
@dataclass
class SimpleSpamResult:
    """Simple spam detection result."""
    is_spam: bool
    score: float
    triggered_rules: List[str]
    confidence_factors: str

class SimpleSpamDetector:
    """Simplified spam detector using SpamAssassin."""
    
    def __init__(self, threshold: float = 5.0, msgraph_interface=None):
        self.threshold = threshold
        self.msgraph = msgraph_interface
        self.spamassassin_available = False
        self.contact_emails = set()
        self.contact_domains = set()
        
        # Pre-defined whitelists
        self.government_domains = {'.gov', '.mil'}
        self.edu_domains = {'.edu'}
        self.financial_domains = {
            'bankofamerica.com', 'chase.com', 'wellsfargo.com', 'citibank.com', 
            'usaa.com', 'americanexpress.com', 'discover.com', 'capitalone.com',
            'navyfederal.org', 'usbank.com', 'pnc.com', 'tdbank.com',
            'schwab.com', 'fidelity.com', 'vanguard.com', 'etrade.com'
        }
        self.news_domains = {
            'nytimes.com', 'wsj.com', 'reuters.com', 'bloomberg.com',
            'cnn.com', 'bbc.com', 'npr.org', 'pbs.org', 'apnews.com'
        }
        
        # Manual personal contact protection
        self.manual_contacts = {
            'alan@bassmancpa.com', 'abassman@bassmancpa.com', 'alan@bassman.com',
            'beth@bassman.com', 'donna@bassman.com', 'joan@bassman.com', 'nancy@bassman.com',
            'david.stengle@gmail.com'
        }
        
        # Check SpamAssassin
        self._check_spamassassin()
    
    def _check_spamassassin(self):
        """Check if SpamAssassin is available."""
        try:
            result = subprocess.run(['spamassassin', '--version'], 
                                  capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                self.spamassassin_available = True
                print("✅ SpamAssassin detected and ready")
            else:
                print("⚠️ SpamAssassin not available - using simplified detection")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            print("⚠️ SpamAssassin not available - using simplified detection")
    
    async def load_contacts(self):
        """Load contacts from Microsoft Graph."""
        if not self.msgraph:
            print("   ⚠️ No Microsoft Graph interface provided")
            return
        
        try:
            print("   📱 Loading Microsoft Graph contacts...")
            contacts = await self._get_msgraph_contacts()
            
            print(f"   🔍 Raw contacts fetched: {len(contacts)}")
            
            # Process contacts
            total_emails = 0
            for contact in contacts:
                for email in contact['emails']:
                    self.contact_emails.add(email.lower())
                    domain = email.split('@')[1].lower() if '@' in email else ''
                    if domain:
                        self.contact_domains.add(domain)
                    total_emails += 1
            
            print(f"   ✅ Loaded {total_emails} contact emails")
            if contacts:
                sample_contacts = '; '.join([f"{c['name']} ({c['emails'][0]})" if c['emails'] else f"{c['name']} (no email)" 
                                           for c in contacts[:3]])
                print(f"   📋 Sample contacts: {sample_contacts}...")
            
            # Look for specific target contacts
            target_contacts = []
            for email in ['david.stengle@gmail.com', 'alan@bassman.com']:
                if email in self.contact_emails:
                    contact_name = next((c['name'] for c in contacts if email in c['emails']), 'Unknown')
                    target_contacts.append(f"{contact_name} ({email})")
            
            if target_contacts:
                print(f"   🎯 Found target contacts: {', '.join(target_contacts)}")
            
            print(f"   🛡️ All contacts automatically protected from spam detection")
            
        except Exception as e:
            print(f"   ⚠️ Failed to load contacts: {e}")
    
    async def _get_msgraph_contacts(self) -> List[Dict[str, Any]]:
        """Get contacts from Microsoft Graph."""
        if not self.msgraph or not hasattr(self.msgraph, 'session') or not self.msgraph.session:
            return []
        
        try:
            contacts = []
            url = f"{self.msgraph.GRAPH_ENDPOINT}/me/contacts"
            
            while url:
                async with self.msgraph.session.get(url) as response:
                    if response.status != 200:
                        print(f"      Warning: Failed to fetch contacts (HTTP {response.status})")
                        break
                    
                    data = await response.json()
                    
                    for contact in data.get('value', []):
                        contact_info = {
                            'name': contact.get('displayName', ''),
                            'emails': []
                        }
                        
                        # Get email addresses
                        for email_addr in contact.get('emailAddresses', []):
                            email = email_addr.get('address', '').lower()
                            if email:
                                contact_info['emails'].append(email)
                        
                        if contact_info['emails']:
                            contacts.append(contact_info)
                    
                    # Check for next page
                    url = data.get('@odata.nextLink')
            
            return contacts
            
        except Exception as e:
            print(f"      Error fetching Microsoft Graph contacts: {e}")
            return []
    
    def _get_whitelist_adjustment(self, sender_email: str) -> float:
        """Get whitelist adjustment score for sender."""
        sender_lower = sender_email.lower()
        domain = sender_lower.split('@')[1] if '@' in sender_lower else ''
        
        # Personal contacts (highest priority)
        if sender_lower in self.contact_emails or sender_lower in self.manual_contacts:
            return -10.0
        
        # Domain-based contacts  
        if domain in self.contact_domains:
            return -10.0
        
        # Government domains (.gov, .mil)
        if any(domain.endswith(gov_domain) for gov_domain in self.government_domains):
            return -5.0
        
        # Educational domains (.edu)
        if any(domain.endswith(edu_domain) for edu_domain in self.edu_domains):
            return -2.0
        
        # Financial institutions
        if domain in self.financial_domains:
            return -2.0
        
        # News organizations
        if domain in self.news_domains:
            return -3.0
        
        # Trusted services
        trusted_services = {
            'amazon.com', 'ebay.com', 'paypal.com', 'linkedin.com', 
            'microsoft.com', 'apple.com', 'google.com', 'github.com'
        }
        if domain in trusted_services:
            return -1.0
        
        return 0.0
    
    def is_whitelisted_domain(self, sender_email: str) -> bool:
        """Check if sender is from a whitelisted domain."""
        return self._get_whitelist_adjustment(sender_email) < 0
    
    def get_protection_reason(self, sender_email: str) -> str:
        """Get the reason why this sender is protected."""
        sender_lower = sender_email.lower()
        domain = sender_lower.split('@')[1] if '@' in sender_lower else ''
        
        if sender_lower in self.contact_emails:
            return "Microsoft Graph contact"
        if sender_lower in self.manual_contacts:
            return "Manual personal contact"
        if domain in self.contact_domains:
            return f"Contact domain ({domain})"
        if any(domain.endswith(gov_domain) for gov_domain in self.government_domains):
            return f"Government domain ({domain})"
        if any(domain.endswith(edu_domain) for edu_domain in self.edu_domains):
            return f"Educational domain ({domain})"
        if domain in self.financial_domains:
            return f"Financial institution ({domain})"
        if domain in self.news_domains:
            return f"News organization ({domain})"
        
        return f"Trusted domain ({domain})"
    
    async def analyze_email(self, email_content: str, sender_email: str = None) -> SimpleSpamResult:
        """Analyze email for spam using SpamAssassin with whitelist adjustments."""
        base_score = 0.0
        triggered_rules = []
        confidence = "High"
        
        try:
            if self.spamassassin_available and email_content:
                # Run SpamAssassin
                process = await asyncio.create_subprocess_exec(
                    'spamassassin', '--test-mode',
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                stdout, stderr = await process.communicate(email_content.encode('utf-8', errors='ignore'))
                
                if process.returncode == 0:
                    output = stdout.decode('utf-8', errors='ignore')
                    
                    # Parse SpamAssassin output
                    for line in output.split('\n'):
                        if line.startswith('X-Spam-Status:'):
                            # Extract score from "score=X.X"
                            import re
                            score_match = re.search(r'score=(-?\d+\.?\d*)', line)
                            if score_match:
                                base_score = float(score_match.group(1))
                        
                        elif line.strip().startswith('*') and 'points' in line:
                            # Extract rule name
                            rule_match = re.search(r'\* (-?\d+\.?\d*) (\w+)', line)
                            if rule_match:
                                triggered_rules.append(rule_match.group(2))
                else:
                    confidence = f"Error: SpamAssassin exit code {process.returncode}"
            
            else:
                # Simplified detection without SpamAssassin
                if email_content:
                    content_lower = email_content.lower()
                    spam_indicators = [
                        'viagra', 'cialis', 'pharmacy', 'weight loss', 'lottery',
                        'winner', 'congratulations', 'urgent', 'act now',
                        'limited time', 'free money', 'make money fast'
                    ]
                    
                    for indicator in spam_indicators:
                        if indicator in content_lower:
                            base_score += 2.0
                            triggered_rules.append(f"CONTENT_{indicator.replace(' ', '_').upper()}")
                
                confidence = "Medium (no SpamAssassin)"
            
            # Apply whitelist adjustments
            if sender_email:
                whitelist_adjustment = self._get_whitelist_adjustment(sender_email)
                if whitelist_adjustment < 0:
                    base_score += whitelist_adjustment
                    domain = sender_email.split('@')[1] if '@' in sender_email else ''
                    triggered_rules.append(f"WHITELIST_ADJUSTMENT_{domain.replace('.', '_').upper()}")
            
            final_score = base_score
            is_spam = final_score >= self.threshold
            
            return SimpleSpamResult(
                is_spam=is_spam,
                score=final_score,
                triggered_rules=triggered_rules,
                confidence_factors=confidence
            )
            
        except Exception as e:
            return SimpleSpamResult(
                is_spam=False,
                score=0.0,
                triggered_rules=[],
                confidence_factors=f"Error: {str(e)}"
            )

    def cleanup(self):
        """Clean up any resources."""
        pass

class SpamActionHandler:
    """Handles actions to take on spam emails like unsubscribing and moving to junk folder."""
    
    def __init__(self, msgraph_interface, spam_detector, dry_run=True):
        self.msgraph = msgraph_interface
        self.spam_detector = spam_detector
        self.dry_run = dry_run
        self.unsubscribe_attempts = 0
        self.moves_to_junk = 0
    
    def _extract_unsubscribe_links(self, email_body: str) -> List[str]:
        """Extract potential unsubscribe links from email body."""
        if not email_body:
            return []
        
        # Common unsubscribe patterns
        patterns = [
            r'href=["\']([^"\']*(?:unsubscribe|optout|remove|stop)[^"\']*)["\']',
            r'https?://[^\s<>"\']+(?:unsubscribe|optout|remove|stop)[^\s<>"\']*',
        ]
        
        links = []
        for pattern in patterns:
            matches = re.findall(pattern, email_body, re.IGNORECASE)
            links.extend(matches)
        
        # Filter for legitimate domains (avoid suspicious/phishing links)
        safe_links = []
        for link in links:
            try:
                parsed = urlparse(link)
                # Only allow HTTPS links from legitimate domains
                if (parsed.scheme == 'https' and 
                    parsed.netloc and 
                    not any(suspicious in parsed.netloc.lower() for suspicious in ['bit.ly', 'tinyurl', 'shorturl'])):
                    safe_links.append(link)
            except:
                continue
        
        return list(set(safe_links))  # Remove duplicates
    
    async def _attempt_unsubscribe(self, link: str) -> bool:
        """Attempt to unsubscribe using a link."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(link, timeout=10) as response:
                    return response.status == 200
        except:
            return False
    
    async def _get_or_create_junk_folder(self):
        """Get the Junk Email folder or create a custom Spam folder."""
        try:
            # Get all folders
            if hasattr(self.msgraph, 'session') and self.msgraph.session:
                print(f"      🔍 Getting Microsoft Graph folders...")
                
                url = f"{self.msgraph.GRAPH_ENDPOINT}/me/mailFolders"
                async with self.msgraph.session.get(url) as response:
                    if response.status != 200:
                        print(f"      ❌ Failed to get folders: HTTP {response.status}")
                        return None
                    
                    data = await response.json()
                    folders = data.get('value', [])
                    
                    # Look for standard junk folder names
                    junk_folder = None
                    spam_folder = None
                    
                    for folder in folders:
                        folder_name = folder.get('displayName', '').lower()
                        folder_id = folder.get('id')
                        
                        if folder_name in ['junk email', 'junk', 'spam', 'junk e-mail']:
                            junk_folder = folder
                            print(f"      ✅ Found junk folder: {folder.get('displayName')} ({folder_id})")
                            break
                        elif 'spam' in folder_name:
                            spam_folder = folder
                    
                    # Prefer standard junk folder
                    if junk_folder:
                        return {
                            'id': junk_folder['id'],
                            'name': junk_folder['displayName'],
                            'type': 'system_junk'
                        }
                    elif spam_folder:
                        return {
                            'id': spam_folder['id'],
                            'name': spam_folder['displayName'],
                            'type': 'custom_spam'
                        }
                    else:
                        # Create custom Spam folder
                        print(f"      🔨 Creating custom Spam folder...")
                        
                        create_url = f"{self.msgraph.GRAPH_ENDPOINT}/me/mailFolders"
                        folder_data = {
                            'displayName': 'Spam',
                            'isHidden': False
                        }
                        
                        async with self.msgraph.session.post(create_url, json=folder_data) as create_response:
                            if create_response.status in [200, 201]:
                                created_folder = await create_response.json()
                                print(f"      ✅ Created Spam folder: {created_folder.get('id')}")
                                return {
                                    'id': created_folder['id'],
                                    'name': created_folder['displayName'],
                                    'type': 'custom_spam'
                                }
                            else:
                                print(f"      ❌ Failed to create Spam folder: HTTP {create_response.status}")
                                return None
            
            return None
            
        except Exception as e:
            print(f"      ❌ Error accessing folders: {e}")
            return None
    
    def cleanup(self):
        """Clean up any resources."""
        pass

    async def handle_spam_email(self, email_id: str, email_obj, sender_address: str) -> dict:
        """Handle a spam email: try to unsubscribe and move to junk folder."""
        results = {
            'unsubscribe_links': 0,
            'unsubscribed': False,
            'moved_to_junk': False
        }
        
        # Check if this is a whitelisted domain
        is_whitelisted = self.spam_detector.is_whitelisted_domain(sender_address)
        
        if is_whitelisted:
            protection_reason = self.spam_detector.get_protection_reason(sender_address)
            print(f"      ⚠️ WARNING: Email from protected source: {protection_reason}")
            print(f"      🛡️ PROTECTION: Will NOT move to junk (likely false positive)")
        
        # Try to unsubscribe if not from a whitelisted domain
        if not is_whitelisted:
            email_body = email_obj.body_html or email_obj.body_text or ""
            unsubscribe_links = self._extract_unsubscribe_links(email_body)
            results['unsubscribe_links'] = len(unsubscribe_links)
            
            if unsubscribe_links:
                print(f"      🔍 Found {len(unsubscribe_links)} unsubscribe link(s)")
                
                if not self.dry_run:
                    # Try to unsubscribe using the first valid link
                    for link in unsubscribe_links[:2]:  # Try first 2 links max
                        try:
                            success = await self._attempt_unsubscribe(link)
                            if success:
                                results['unsubscribed'] = True
                                print(f"      ✅ Unsubscribe successful: {sender_address}")
                                break
                        except Exception as e:
                            print(f"      ❌ Unsubscribe failed: {e}")
                            continue
                else:
                    print(f"      🔍 Would attempt unsubscribe from: {sender_address}")
        
        # Move to junk folder (only if not whitelisted)
        if not is_whitelisted:
            if not self.dry_run:
                try:
                    # Get or create junk folder
                    junk_folder = await self._get_or_create_junk_folder()
                    if junk_folder:
                        folder_type = junk_folder.get('type', 'unknown')
                        print(f"      📧 Moving email {email_id} to {junk_folder['name']} folder ({folder_type})...")
                        
                        # Move to junk folder using Microsoft Graph
                        url = f"{self.msgraph.GRAPH_ENDPOINT}/me/messages/{email_id}/move"
                        payload = {'destinationId': junk_folder['id']}
                        
                        async with self.msgraph.session.post(url, json=payload) as response:
                            if response.status in [200, 201]:
                                print(f"      ✅ Successfully moved to {junk_folder['name']}")
                                results['moved_to_junk'] = True
                            else:
                                error_text = await response.text()
                                print(f"      ❌ Failed to move email: HTTP {response.status}")
                                print(f"      🐛 Error details: {error_text}")
                        
                        print(f"      📁 Moved to junk: {sender_address}")
                    else:
                        print(f"      ❌ Could not get junk folder")
                except Exception as e:
                    print(f"      ❌ Failed to move to junk: {e}")
                    import traceback
                    print(f"      🐛 Full error: {traceback.format_exc()}")
            else:
                print(f"      📁 Would move to junk: {sender_address}")
                results['moved_to_junk'] = True  # For simulation statistics
        else:
            print(f"      🛡️ Whitelisted domain - NOT moving to junk")
            
        return results

class EmailProcessingLogger:
    """Logs all email processing results for detailed review."""
    
    def __init__(self):
        self.timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.csv_filename = f"msgraph_spam_log_{self.timestamp}.csv"
        self.summary_filename = f"msgraph_spam_summary_{self.timestamp}.json"
        self.processed_emails = []
        
        # Initialize CSV file with headers
        with open(self.csv_filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                'Email_ID', 'From_Name', 'From_Address', 'Subject', 'Date', 
                'Is_Read', 'Spam_Score', 'Is_Spam', 'Confidence', 
                'Triggered_Rules', 'Whitelist_Applied', 'Unsubscribe_Links_Found',
                'Unsubscribe_Successful', 'Moved_To_Junk', 'Processing_Status'
            ])
    
    def log_email(self, email, spam_result, action_result=None, error_msg=None):
        """Log a processed email with all details."""
        # Extract whitelist info
        whitelist_rules = [rule for rule in spam_result.triggered_rules if rule.startswith('WHITELIST_ADJUSTMENT_')]
        whitelist_applied = ', '.join([rule.replace('WHITELIST_ADJUSTMENT_', '').replace('_', '.').lower() 
                                     for rule in whitelist_rules]) if whitelist_rules else 'None'
        
        # Extract non-whitelist rules
        regular_rules = [rule for rule in spam_result.triggered_rules if not rule.startswith('WHITELIST_ADJUSTMENT_')]
        triggered_rules = ', '.join(regular_rules) if regular_rules else 'None'
        
        # Action results
        unsubscribe_links = action_result['unsubscribe_links'] if action_result else 0
        unsubscribe_success = action_result['unsubscribed'] if action_result else False
        moved_to_junk = action_result['moved_to_junk'] if action_result else False
        
        # Processing status
        if error_msg:
            status = f"ERROR: {error_msg}"
        elif "Error" in spam_result.confidence_factors:
            status = f"ANALYSIS_ERROR: {spam_result.confidence_factors}"
        else:
            status = "SUCCESS"
        
        # Create email record
        email_record = {
            'email_id': email.id,
            'from_name': email.sender.name or '',
            'from_address': email.sender.address,
            'subject': email.subject,
            'date': str(email.sent_date),
            'is_read': email.is_read,
            'spam_score': spam_result.score,
            'is_spam': spam_result.is_spam,
            'confidence': spam_result.confidence_factors,
            'triggered_rules': triggered_rules,
            'whitelist_applied': whitelist_applied,
            'unsubscribe_links_found': unsubscribe_links,
            'unsubscribe_successful': unsubscribe_success,
            'moved_to_junk': moved_to_junk,
            'processing_status': status
        }
        
        self.processed_emails.append(email_record)
        
        # Write to CSV immediately
        with open(self.csv_filename, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                email.id, email.sender.name or '', email.sender.address,
                email.subject, email.sent_date, email.is_read,
                spam_result.score, spam_result.is_spam, spam_result.confidence_factors,
                triggered_rules, whitelist_applied, unsubscribe_links,
                unsubscribe_success, moved_to_junk, status
            ])
    
    def generate_summary(self, total_emails, spam_count, clean_count, error_count, action_results):
        """Generate a complete summary report."""
        # Calculate statistics
        spam_rate = (spam_count / (spam_count + clean_count) * 100) if (spam_count + clean_count) > 0 else 0
        
        # Top spam triggers
        all_rules = []
        for email in self.processed_emails:
            if email['triggered_rules'] != 'None':
                all_rules.extend(email['triggered_rules'].split(', '))
        
        rule_counts = {}
        for rule in all_rules:
            rule_counts[rule] = rule_counts.get(rule, 0) + 1
        
        top_spam_rules = sorted(rule_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Whitelist applications  
        whitelist_applications = {}
        for email in self.processed_emails:
            if email['whitelist_applied'] != 'None':
                domains = email['whitelist_applied'].split(', ')
                for domain in domains:
                    whitelist_applications[domain] = whitelist_applications.get(domain, 0) + 1
        
        # Summary data
        summary = {
            'processing_timestamp': self.timestamp,
            'total_emails_processed': total_emails,
            'statistics': {
                'spam_detected': spam_count,
                'clean_emails': clean_count,
                'analysis_errors': error_count,
                'spam_rate_percent': round(spam_rate, 1)
            },
            'actions_taken': action_results,
            'top_spam_rules': top_spam_rules,
            'whitelist_applications': whitelist_applications,
            'files_generated': {
                'detailed_log': self.csv_filename,
                'summary_report': self.summary_filename
            }
        }
        
        # Write summary to JSON
        with open(self.summary_filename, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2, default=str)
        
        return summary
    
    def print_file_locations(self):
        """Print where the log files are saved."""
        print(f"\n📋 DETAILED LOGS SAVED:")
        print(f"   📊 CSV Log: {self.csv_filename}")
        print(f"   📈 Summary: {self.summary_filename}")

async def main():
    """Main function to run Microsoft Graph spam detection."""
    print("🚀 Starting Microsoft Graph Spam Management System...")
    print("📝 Note: This system can detect, unsubscribe, and move spam emails")
    
    print(f"\n🔍 Microsoft Graph Spam Detection Test")
    print("=" * 50)
    
    # Initialize spam detector
    spam_detector = SimpleSpamDetector(threshold=5.0)
    
    try:
        # Create Microsoft Graph interface
        print("🔗 Creating Microsoft Graph interface...")
        msgraph = EmailInterfaceFactory.create('microsoft_graph')
        
        # Connect to Microsoft Graph
        print("🔐 Connecting to Microsoft Graph...")
        print("   (Browser will open for authentication)")
        
        # You'll need to set up these credentials
        credentials = {
            'client_id': 'YOUR_CLIENT_ID',  # Replace with your actual client ID
            'tenant_id': 'common',  # or your specific tenant ID
            # 'client_secret': 'YOUR_CLIENT_SECRET',  # Only for confidential clients
            'redirect_uri': 'http://localhost:8080'
        }
        
        success = await msgraph.connect(credentials)
        
        if not success:
            print("❌ Failed to connect to Microsoft Graph")
            return
        
        print("✅ Connected to Microsoft Graph!")
        
        # Get profile
        profile = await msgraph.get_profile()
        print(f"📧 Account: {profile.get('name')} ({profile.get('email')})")
        
        # Initialize spam detector with msgraph interface for contacts
        spam_detector.msgraph = msgraph
        
        print(f"\n🛡️ Initializing spam detector...")
        print(f"   📋 Whitelist: .gov (-5), .edu (-2), .mil (-3), banks (-2), news (-3)")
        print(f"   👤 Personal contacts: Alan Bassman, David Stengle (-10) - NEVER spam")
        
        # Load contacts
        await spam_detector.load_contacts()
        
        # Initialize logger
        logger = EmailProcessingLogger()
        print(f"📝 Logging enabled: {logger.csv_filename}")
        
        # Choose action mode
        print(f"\n🎯 Spam Action Options:")
        print(f"   1. Detect only (read-only)")
        print(f"   2. Detect + simulate actions (show what would be done)")
        print(f"   3. Detect + take real actions (unsubscribe + move to junk)")
        print()
        
        while True:
            try:
                choice = input("Select option (1-3): ").strip()
                if choice in ['1', '2', '3']:
                    break
                print("Please enter 1, 2, or 3")
            except (EOFError, KeyboardInterrupt):
                print("\n❌ Error: EOF when reading a line")
                return
        
        # Configure based on choice
        take_action = False
        dry_run = True
        
        if choice == '1':
            print("📖 Read-only mode: Will only detect spam")
        elif choice == '2':
            print("🎭 Simulation mode: Will show what actions would be taken")
        elif choice == '3':
            print("⚠️ Action mode: Will actually unsubscribe and move emails to junk")
            confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
            if confirm != 'yes':
                print("❌ Cancelled")
                return
            take_action = True
            dry_run = False
        
        # Initialize action handler
        action_handler = SpamActionHandler(msgraph, spam_detector, dry_run=dry_run)
        
        # Get emails to process
        print(f"\n📬 Searching for emails...")
        from email_interface.base import EmailSearchCriteria
        
        criteria = EmailSearchCriteria(max_results=500)
        emails = await msgraph.list_emails(criteria)
        
        if not emails:
            print("❌ No emails found")
            return
        
        print(f"Found {len(emails)} emails to analyze")
        
        if take_action:
            print(f"\n⚠️ IMPORTANT: You're about to process {len(emails)} emails in ACTION MODE")
            print(f"   This will:")
            print(f"   • Actually unsubscribe from spam mailing lists")
            print(f"   • Move spam emails to your junk folder")
            print(f"   • These actions cannot be easily undone")
            print()
            
            final_confirm = input(f"Type 'PROCESS {len(emails)} EMAILS' to confirm: ").strip()
            if final_confirm != f'PROCESS {len(emails)} EMAILS':
                print("❌ Cancelled - confirmation text didn't match")
                return
        
        # Process emails
        print(f"\n📊 Processing {len(emails)} emails...")
        print("=" * 60)
        
        # Counters
        spam_count = 0
        clean_count = 0
        error_count = 0
        total_unsubscribes = 0
        total_moved = 0
        
        # Process in batches
        batch_size = 50
        total_batches = (len(emails) + batch_size - 1) // batch_size
        
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(emails))
            batch_emails = emails[start_idx:end_idx]
            
            print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch_emails)} emails)")
            print()
            
            for i, email in enumerate(batch_emails):
                global_idx = start_idx + i + 1
                print(f"📧 Email {global_idx}/{len(emails)}")
                print(f"   From: {email.sender.name or email.sender.address}")
                print(f"   Subject: {email.subject[:60]}{'...' if len(email.subject) > 60 else ''}")
                print(f"   Date: {email.sent_date}")
                print(f"   Read: {'Yes' if email.is_read else 'No'}")
                
                try:
                    # Get full email content for analysis
                    full_email = await msgraph.get_email(email.id, include_attachments=False)
                    email_content = full_email.body_html or full_email.body_text or ""
                    
                    # Analyze for spam
                    spam_result = await spam_detector.analyze_email(email_content, email.sender.address)
                    
                    # Display result
                    if spam_result.is_spam:
                        print(f"   Result: 🚨 SPAM (Score: {spam_result.score})")
                        spam_count += 1
                        
                        # Handle spam actions
                        if take_action or choice == '2':
                            action_result = await action_handler.handle_spam_email(
                                email.id, full_email, email.sender.address
                            )
                            
                            total_unsubscribes += 1 if action_result['unsubscribed'] else 0
                            total_moved += 1 if action_result['moved_to_junk'] else 0
                            
                            logger.log_email(email, spam_result, action_result)
                        else:
                            logger.log_email(email, spam_result)
                    else:
                        print(f"   Result: ✅ CLEAN (Score: {spam_result.score})")
                        clean_count += 1
                        
                        # Check if whitelist was applied
                        whitelist_rules = [rule for rule in spam_result.triggered_rules 
                                         if rule.startswith('WHITELIST_ADJUSTMENT_')]
                        if whitelist_rules:
                            domains = [rule.replace('WHITELIST_ADJUSTMENT_', '').replace('_', '.').lower() 
                                     for rule in whitelist_rules]
                            print(f"   📝 Whitelist applied: {', '.join(domains)} domain trusted")
                        
                        logger.log_email(email, spam_result)
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    error_count += 1
                    continue
                
                # Rate limiting
                if global_idx % 10 == 0:
                    print(f"   ⏸️ Brief pause to avoid rate limits...")
                    await asyncio.sleep(1)
            
            print(f"\n📊 Batch {batch_num + 1} complete: {spam_count} spam, {clean_count} clean, {error_count} errors")
            
            # Pause between batches
            if batch_num < total_batches - 1:
                print(f"   ⏸️ Pausing between batches...")
                await asyncio.sleep(2)
        
        # Final results
        action_results = {
            'emails_unsubscribed': total_unsubscribes,
            'emails_moved_to_junk': total_moved
        }
        
        # Generate summary
        summary = logger.generate_summary(
            len(emails), spam_count, clean_count, error_count, action_results
        )
        
        print(f"\n🎉 MICROSOFT GRAPH SPAM PROCESSING COMPLETE!")
        print("=" * 60)
        print(f"📊 Final Statistics:")
        print(f"   📧 Total emails processed: {len(emails)}")
        print(f"   🚨 Spam detected: {spam_count}")
        print(f"   ✅ Clean emails: {clean_count}")
        print(f"   ❌ Processing errors: {error_count}")
        print(f"   📈 Spam rate: {summary['statistics']['spam_rate_percent']}%")
        
        if take_action:
            print(f"\n🎯 Actions Taken:")
            print(f"   📧 Unsubscribe attempts: {total_unsubscribes}")
            print(f"   📁 Emails moved to junk: {total_moved}")
        
        logger.print_file_locations()
        
    except Exception as e:
        print(f"❌ Error during processing: {e}")
        import traceback
        print(f"🐛 Full traceback:")
        print(traceback.format_exc())
    
    finally:
        # Cleanup
        try:
            spam_detector.cleanup()
            await msgraph.disconnect()
            print(f"\n🔌 Disconnected from Microsoft Graph")
        except:
            pass

if __name__ == "__main__":
    asyncio.run(main()) 