"""
Gmail Spam Management System

This script connects to your Gmail account and runs complete spam detection
and management on your emails. It can:

- Detect spam using SpamAssassin with whitelisting
- Automatically unsubscribe from unwanted mailing lists  
- Move spam emails to junk folder
- Process large batches of emails (up to 2000)
- Provide detailed reporting and progress tracking

Setup Required:
1. Go to https://console.cloud.google.com/
2. Create a new project or select existing one
3. Enable the Gmail API
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Desktop application"
6. Download the JSON file as "gmail_credentials.json"
7. Place it in the same directory as this script

Usage:
    python examples/gmail_spam_test.py
"""

import asyncio
import sys
import os
import subprocess
import re
import aiohttp
import csv
import json
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Optional
from urllib.parse import urlparse

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory, EmailSearchCriteria

@dataclass
class SimpleSpamResult:
    """Simple spam detection result."""
    is_spam: bool
    score: float
    triggered_rules: List[str]
    confidence_factors: str

class SimpleSpamDetector:
    """Simplified spam detector using SpamAssassin directly."""
    
    def __init__(self, threshold: float = 5.0, gmail_interface=None):
        self.threshold = threshold
        self.gmail_interface = gmail_interface
        self.contacts_cache = {}  # Cache for contacts
        # Define trusted domains for whitelisting
        self.trusted_domains = {
            'gov': -5.0,      # Government domains get -5 points
            'edu': -2.0,      # Educational institutions get -2 points
            'mil': -3.0,      # Military domains get -3 points
        }
        self.trusted_senders = {
            'chase.com': -2.0,
            'bankofamerica.com': -2.0,
            'wellsfargo.com': -2.0,
            'usaa.com': -2.0,
            'navyfederal.org': -2.0,
            'nytimes.com': -3.0,      # Increased from -1.0 to -3.0
            'wsj.com': -3.0,          # Increased from -1.0 to -3.0
            'washingtonpost.com': -3.0,
            'reuters.com': -3.0,
            'bbc.com': -3.0,
            'cnn.com': -2.0,
            'npr.org': -3.0,
            'linkedin.com': -1.0,
            'microsoft.com': -1.0,
            'notificationmail.microsoft.com': -1.0,
            'google.com': -1.0,
            'accounts.google.com': -1.0,
            'apple.com': -1.0,
            'paypal.com': -1.0
        }
        # Personal/contacts that should NEVER be spam
        self.trusted_personal_contacts = {
            'alan@bassmancpa.com': -10.0,     # Alan Bassman - Accountant
            'abassman@bassmancpa.com': -10.0,  # Alternative email
            'bassmancpa.com': -10.0,          # Entire domain
            'david.stengle@gmail.com': -10.0,  # David Stengle - Friend
            'dstengle@gmail.com': -10.0,      # Alternative email
            # Add more personal contacts here as needed
        }
    
    async def load_contacts(self):
        """Load Gmail contacts and add them to trusted contacts."""
        if not self.gmail_interface:
            print("   ⚠️ No Gmail interface provided - skipping contacts loading")
            return
        
        try:
            print("   📱 Loading Gmail contacts...")
            contacts = await self.gmail_interface.get_contacts()
            print(f"   🔍 Raw contacts fetched: {len(contacts)}")
            
            contacts_loaded = 0
            sample_contacts = []
            
            for contact in contacts:
                name = contact.get('name', 'Unknown')
                emails = contact.get('emails', [])
                
                # Debug: Show first few contacts
                if len(sample_contacts) < 5 and emails:
                    sample_contacts.append(f"{name} ({', '.join(emails)})")
                
                for email in emails:
                    # Add each contact email with high protection
                    self.contacts_cache[email.lower()] = {
                        'name': name,
                        'protection_score': -10.0
                    }
                    contacts_loaded += 1
            
            print(f"   ✅ Loaded {contacts_loaded} contact emails")
            if sample_contacts:
                print(f"   📋 Sample contacts: {'; '.join(sample_contacts[:3])}...")
            
            # Check for specific contacts we're looking for
            target_contacts = ['david.stengle@gmail.com', 'alan@bassmancpa.com', 'abassman@bassmancpa.com']
            found_contacts = []
            for target in target_contacts:
                if target.lower() in self.contacts_cache:
                    contact_info = self.contacts_cache[target.lower()]
                    found_contacts.append(f"{contact_info['name']} ({target})")
            
            if found_contacts:
                print(f"   🎯 Found target contacts: {'; '.join(found_contacts)}")
            else:
                print(f"   ⚠️ Target contacts not found in Gmail contacts")
                print(f"   📝 Using manual trusted_personal_contacts instead")
            
            print(f"   🛡️ All contacts automatically protected from spam detection")
            
        except Exception as e:
            print(f"   ❌ Could not load contacts: {e}")
            print("   📝 Using manual trusted_personal_contacts instead")
            import traceback
            print(f"   🐛 Debug traceback: {traceback.format_exc()}")
    
    def _get_whitelist_adjustment(self, sender_email: str) -> float:
        """Get whitelist score adjustment for a sender email."""
        if not sender_email or '@' not in sender_email:
            return 0.0
        
        domain = sender_email.split('@')[-1].lower()
        sender_email_lower = sender_email.lower()
        
        # Check Gmail contacts first (highest priority)
        if sender_email_lower in self.contacts_cache:
            contact = self.contacts_cache[sender_email_lower]
            return contact['protection_score']
        
        # Check personal/contacts second
        if sender_email_lower in self.trusted_personal_contacts:
            return self.trusted_personal_contacts[sender_email_lower]
        
        if domain in self.trusted_personal_contacts:
            return self.trusted_personal_contacts[domain]
        
        # Check exact domain matches
        if domain in self.trusted_senders:
            return self.trusted_senders[domain]
        
        # Check TLD-based rules
        for tld, adjustment in self.trusted_domains.items():
            if domain.endswith(f'.{tld}'):
                return adjustment
        
        return 0.0
    
    def is_whitelisted_domain(self, sender_email: str) -> bool:
        """Check if sender is from a whitelisted domain or contact."""
        return self._get_whitelist_adjustment(sender_email) < 0
    
    def get_protection_reason(self, sender_email: str) -> str:
        """Get the reason why an email is protected."""
        if not sender_email or '@' not in sender_email:
            return ""
        
        sender_email_lower = sender_email.lower()
        
        # Check Gmail contacts
        if sender_email_lower in self.contacts_cache:
            contact = self.contacts_cache[sender_email_lower]
            return f"Gmail contact: {contact['name']}"
        
        # Check personal contacts
        if sender_email_lower in self.trusted_personal_contacts:
            return "Personal/contact"
        
        domain = sender_email.split('@')[-1].lower()
        if domain in self.trusted_personal_contacts:
            return f"Trusted domain: {domain}"
        
        # Check other whitelists
        adjustment = self._get_whitelist_adjustment(sender_email)
        if adjustment < 0:
            return f"Trusted domain: {domain}"
        
        return ""
    
    async def analyze_email(self, email_content: str, sender_email: str = None) -> SimpleSpamResult:
        """Analyze email content for spam using SpamAssassin."""
        try:
            # Run spamassassin command with full path and custom config
            cmd = ['/opt/homebrew/Cellar/perl/5.40.2/bin/spamassassin', '-D', '-t']
            
            result = subprocess.run(
                cmd,
                input=email_content,
                text=True,
                capture_output=True,
                timeout=30
            )
            
            if result.returncode != 0:
                print(f"   ⚠️ SpamAssassin error: {result.stderr}")
                return SimpleSpamResult(False, 0.0, [], "SpamAssassin unavailable")
            
            # Parse output
            output = result.stdout
            score = 0.0
            triggered_rules = []
            
            # Extract score from X-Spam-Status header
            for line in output.split('\n'):
                if line.startswith('X-Spam-Status:'):
                    # Parse score from line like: X-Spam-Status: Yes, score=15.2 required=5.0
                    score_match = re.search(r'score=([\d.-]+)', line)
                    if score_match:
                        score = float(score_match.group(1))
                    
                    # Extract triggered rules
                    tests_match = re.search(r'tests=([^\s]+)', line)
                    if tests_match:
                        triggered_rules = tests_match.group(1).split(',')
                        triggered_rules = [rule.strip() for rule in triggered_rules if rule.strip()]
                    break
            
            # Apply whitelist adjustment
            adjustment = 0.0
            if sender_email:
                adjustment = self._get_whitelist_adjustment(sender_email)
                score += adjustment
            
            is_spam = score >= self.threshold
            confidence = "High" if score > 10 else "Medium" if score > 2 else "Low"
            
            # Add adjustment info to triggered rules if whitelist was applied
            if adjustment < 0:
                domain = sender_email.split('@')[-1] if '@' in sender_email else sender_email
                triggered_rules.append(f"WHITELIST_ADJUSTMENT_{domain.upper().replace('.', '_')}")
            
            return SimpleSpamResult(
                is_spam=is_spam,
                score=score,
                triggered_rules=triggered_rules,
                confidence_factors=f"{confidence} confidence (threshold: {self.threshold})"
            )
            
        except subprocess.TimeoutExpired:
            return SimpleSpamResult(False, 0.0, [], "SpamAssassin timeout")
        except FileNotFoundError:
            return SimpleSpamResult(False, 0.0, [], "SpamAssassin not installed")
        except Exception as e:
            return SimpleSpamResult(False, 0.0, [], f"Error: {e}")
    
    def cleanup(self):
        """Clean up any resources."""
        pass

class SpamActionHandler:
    """Handles actions to take on spam emails like unsubscribing and moving to junk."""
    
    def __init__(self, gmail_interface, spam_detector, dry_run=True):
        self.gmail = gmail_interface
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
    
    async def _get_or_create_junk_label(self):
        """Get the SPAM label or create a custom Junk label as backup."""
        try:
            # First try to use Gmail's built-in SPAM label
            if hasattr(self.gmail, 'service') and self.gmail.service:
                print(f"      🔍 Getting detailed label information...")
                
                # Get all labels with full details
                result = await self.gmail._run_in_executor(
                    self.gmail.service.users().labels().list(userId='me').execute
                )
                
                detailed_labels = result.get('labels', [])
                
                # Look for SPAM label
                spam_label = None
                junk_label = None
                
                for label in detailed_labels:
                    if label.get('id') == 'SPAM':
                        spam_label = label
                        print(f"      ✅ Found Gmail SPAM label: {label.get('id')}")
                    elif label.get('name', '').lower() == 'junk':
                        junk_label = label
                        print(f"      📋 Found custom Junk label: {label.get('id')}")
                
                # Prefer SPAM label, fall back to Junk
                if spam_label:
                    return {
                        'id': spam_label['id'], 
                        'name': spam_label['name'],
                        'type': 'system_spam'
                    }
                elif junk_label:
                    return {
                        'id': junk_label['id'], 
                        'name': junk_label['name'],
                        'type': 'custom_junk'
                    }
                else:
                    # Create custom Junk label if neither exists
                    print(f"      🔨 Creating custom Junk label...")
                    label_object = {
                        'name': 'Junk',
                        'labelListVisibility': 'labelShow',
                        'messageListVisibility': 'show'
                    }
                    
                    created_label = await self.gmail._run_in_executor(
                        self.gmail.service.users().labels().create(
                            userId='me',
                            body=label_object
                        ).execute
                    )
                    
                    return {
                        'id': created_label['id'], 
                        'name': created_label['name'],
                        'type': 'custom_junk'
                    }
            
            # Fallback to simple method
            print(f"      ⚠️ Using fallback method for SPAM label")
            return {'id': 'SPAM', 'name': 'Spam', 'type': 'system_spam'}
            
        except Exception as e:
            print(f"      ❌ Error accessing labels: {e}")
            # Last resort fallback
            return {'id': 'SPAM', 'name': 'Spam', 'type': 'system_spam'}
    
    def cleanup(self):
        """Clean up any resources."""
        pass

    async def handle_spam_email(self, email_id: str, email_obj, sender_address: str) -> dict:
        """Handle a spam email: try to unsubscribe and move to junk."""
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
                    # Create or get junk label
                    junk_label = await self._get_or_create_junk_label()
                    if junk_label:
                        label_type = junk_label.get('type', 'unknown')
                        print(f"      📧 Moving email {email_id} to {junk_label['name']} folder ({label_type})...")
                        
                        # For system SPAM label, we need to be more careful
                        if label_type == 'system_spam':
                            print(f"      🏷️ Using Gmail's built-in SPAM label (messages will be hidden from normal views)")
                            
                            # Add SPAM label first
                            add_result = await self.gmail.add_label(email_id, junk_label['id'])
                            print(f"      📍 Add SPAM label result: {add_result}")
                            
                            # Remove from INBOX
                            remove_result = await self.gmail.remove_label(email_id, 'INBOX')
                            print(f"      📍 Remove INBOX label result: {remove_result}")
                            
                            # Note: SPAM messages are automatically hidden in Gmail UI
                            print(f"      ✅ Successfully moved to SPAM (hidden from normal view)")
                            
                        else:
                            print(f"      🏷️ Using custom Junk label (messages will remain visible)")
                            
                            # Add junk label and remove from inbox  
                            add_result = await self.gmail.add_label(email_id, junk_label['id'])
                            print(f"      📍 Add Junk label result: {add_result}")
                            
                            remove_result = await self.gmail.remove_label(email_id, 'INBOX')
                            print(f"      📍 Remove INBOX label result: {remove_result}")
                            
                            print(f"      ✅ Successfully moved to {junk_label['name']}")
                        
                        results['moved_to_junk'] = True
                        print(f"      📁 Moved to junk: {sender_address}")
                    else:
                        print(f"      ❌ Could not get junk label")
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
        self.csv_filename = f"spam_processing_log_{self.timestamp}.csv"
        self.summary_filename = f"spam_processing_summary_{self.timestamp}.json"
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
        print(f"   📁 Location: {os.getcwd()}")
        
        # Show first few entries as preview
        if os.path.exists(self.csv_filename):
            print(f"\n📝 Preview of {self.csv_filename}:")
            with open(self.csv_filename, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                headers = next(reader)
                print(f"   Headers: {', '.join(headers[:5])}...")
                
                count = 0
                for row in reader:
                    if count < 3:  # Show first 3 data rows
                        print(f"   Row {count+1}: {row[1][:30]}... | {row[2][:30]}... | Score: {row[6]} | Spam: {row[7]}")
                        count += 1
                    else:
                        break

async def main():
    print("🔍 Gmail Spam Detection Test")
    print("=" * 50)
    
    # Check for credentials file
    credentials_file = os.path.join(os.path.dirname(__file__), 'gmail_credentials.json')
    if not os.path.exists(credentials_file):
        print("❌ Gmail credentials not found!")
        print(f"Please download your OAuth 2.0 credentials as: {credentials_file}")
        print("\n📋 Setup Instructions:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create/select a project")
        print("3. Enable Gmail API")
        print("4. Create OAuth 2.0 credentials (Desktop application)")
        print("5. Download JSON file as 'gmail_credentials.json'")
        print("6. Place it in the examples/ directory")
        return
    
    # Check if SpamAssassin is available  
    try:
        subprocess.run(['/opt/homebrew/Cellar/perl/5.40.2/bin/spamassassin', '--version'], capture_output=True, timeout=5)
        print("✅ SpamAssassin detected and ready")
    except (FileNotFoundError, subprocess.TimeoutExpired):
        print("⚠️ SpamAssassin not found at expected path")
        print("   Checking if it's available in PATH...")
        try:
            subprocess.run(['spamassassin', '--version'], capture_output=True, timeout=5)
            # If this works, update the command in the analyzer
            print("✅ SpamAssassin found in PATH")
        except:
            print("   SpamAssassin not accessible - continuing anyway...")
    
    # Create Gmail interface
    print("🔗 Creating Gmail interface...")
    gmail = EmailInterfaceFactory.create('gmail')
    
    # Set up credentials
    token_file = os.path.join(os.path.dirname(__file__), 'gmail_token.json')
    credentials = {
        'credentials_file': credentials_file,
        'token_file': token_file
    }
    
    try:
        # Connect to Gmail
        print("🔐 Connecting to Gmail...")
        print("   (Browser will open for first-time authentication)")
        connected = await gmail.connect(credentials)
        
        if not connected:
            print("❌ Failed to connect to Gmail")
            return
        
        print("✅ Connected to Gmail!")
        
        # Get profile
        profile = await gmail.get_profile()
        print(f"📧 Account: {profile.get('name')} ({profile.get('email')})")
        print(f"📊 Total messages: {profile.get('messages_total', 'unknown')}")
        
        # Create spam detector
        print("\n🛡️ Initializing spam detector...")
        print("   📋 Whitelist: .gov (-5), .edu (-2), .mil (-3), banks (-2), news (-3)")
        print("   👤 Personal contacts: Alan Bassman, David Stengle (-10) - NEVER spam")
        spam_detector = SimpleSpamDetector(gmail_interface=gmail)
        
        # Load Gmail contacts for automatic protection
        await spam_detector.load_contacts()
        
        # Initialize email processing logger
        logger = EmailProcessingLogger()
        print(f"📝 Logging enabled: {logger.csv_filename}")
        
        # Ask user about spam actions
        print("\n🎯 Spam Action Options:")
        print("   1. Detect only (read-only)")
        print("   2. Detect + simulate actions (show what would be done)")
        print("   3. Detect + take real actions (unsubscribe + move to junk)")
        
        while True:
            try:
                choice = input("\nSelect option (1-3): ").strip()
                if choice in ['1', '2', '3']:
                    break
                print("Please enter 1, 2, or 3")
            except KeyboardInterrupt:
                print("\n\n👋 Cancelled by user")
                return
        
        # Initialize spam action handler
        if choice == '1':
            spam_actions = None
            print("✅ Read-only mode: Only detecting spam, no actions will be taken")
        elif choice == '2':
            spam_actions = SpamActionHandler(gmail, spam_detector, dry_run=True)
            print("✅ Simulation mode: Will show what actions would be taken")
        else:
            spam_actions = SpamActionHandler(gmail, spam_detector, dry_run=False)
            print("⚠️ Action mode: Will actually unsubscribe and move emails to junk")
            confirm = input("Are you sure? Type 'yes' to confirm: ").strip().lower()
            if confirm != 'yes':
                print("Cancelled - switching to simulation mode")
                spam_actions = SpamActionHandler(gmail, spam_detector, dry_run=True)
        
        # Search for recent emails to test
        print("\n📬 Searching for emails...")
        criteria = EmailSearchCriteria(
            max_results=2000,  # Process 2000 emails for complete cleanup
            date_after=datetime.now() - timedelta(days=180)  # Last 6 months
        )
        
        emails = await gmail.list_emails(criteria)
        print(f"Found {len(emails)} emails to analyze")
        
        if not emails:
            print("ℹ️ No emails found in the specified time range")
            return
        
        # Final confirmation for large batch processing
        if len(emails) > 100 and spam_actions and not spam_actions.dry_run:
            print(f"\n⚠️ IMPORTANT: You're about to process {len(emails)} emails in ACTION MODE")
            print("   This will:")
            print("   • Actually unsubscribe from spam mailing lists")
            print("   • Move spam emails to your junk folder")
            print("   • These actions cannot be easily undone")
            
            final_confirm = input(f"\nType 'PROCESS {len(emails)} EMAILS' to confirm: ").strip()
            expected = f"PROCESS {len(emails)} EMAILS"
            if final_confirm != expected:
                print("❌ Confirmation failed - exiting for safety")
                return
            
            print("✅ Confirmed - starting large-scale spam processing...")
        
        # Process emails in batches for better progress reporting
        batch_size = 50
        total_batches = (len(emails) + batch_size - 1) // batch_size
        
        # Analyze emails for spam
        print(f"\n🔍 Analyzing {len(emails)} emails for spam...")
        print("-" * 80)
        
        spam_count = 0
        clean_count = 0
        error_count = 0
        action_results = {
            'unsubscribe_attempts': 0,
            'successful_unsubscribes': 0,
            'moves_to_junk': 0,
            'unsubscribe_links_found': 0
        }
        
        # Process emails in batches
        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(emails))
            batch_emails = emails[start_idx:end_idx]
            
            print(f"\n📦 Processing batch {batch_num + 1}/{total_batches} ({len(batch_emails)} emails)")
            
            for i, email in enumerate(batch_emails):
                global_idx = start_idx + i + 1
                print(f"\n📧 Email {global_idx}/{len(emails)}")
                print(f"   From: {email.sender.name or email.sender.address}")
                print(f"   Subject: {email.subject[:60]}{'...' if len(email.subject) > 60 else ''}")
                print(f"   Date: {email.sent_date}")
                print(f"   Read: {'Yes' if email.is_read else 'No'}")
                
                # Get full email content for spam analysis
                try:
                    full_email = await gmail.get_email(email.id, include_attachments=False)
                    
                    # Prepare email content for spam analysis
                    email_content = f"""From: {full_email.sender.address}
To: {', '.join([addr.address for addr in full_email.recipients])}
Subject: {full_email.subject}
Date: {full_email.sent_date}

{full_email.body_text or full_email.body_html or ''}"""
                    
                    # Run spam detection
                    spam_result = await spam_detector.analyze_email(email_content, full_email.sender.address)
                    
                    # Display results
                    if "Error" in spam_result.confidence_factors or "unavailable" in spam_result.confidence_factors:
                        print(f"   ❌ {spam_result.confidence_factors}")
                        error_count += 1
                        # Log error
                        logger.log_email(email, spam_result, error_msg=spam_result.confidence_factors)
                    else:
                        status = "🚨 SPAM" if spam_result.is_spam else "✅ CLEAN"
                        print(f"   Result: {status} (Score: {spam_result.score:.1f})")
                        
                        # Show whitelist adjustments
                        whitelist_rules = [rule for rule in spam_result.triggered_rules if rule.startswith('WHITELIST_ADJUSTMENT_')]
                        if whitelist_rules:
                            domain = whitelist_rules[0].replace('WHITELIST_ADJUSTMENT_', '').replace('_', '.').lower()
                            print(f"   📝 Whitelist applied: {domain} domain trusted")
                        
                        # Show specific protection reason if available
                        protection_reason = spam_detector.get_protection_reason(full_email.sender.address)
                        if protection_reason and not whitelist_rules:
                            print(f"   🛡️ Protected: {protection_reason}")
                        
                        action_result = None
                        if spam_result.is_spam:
                            spam_count += 1
                            regular_rules = [rule for rule in spam_result.triggered_rules if not rule.startswith('WHITELIST_ADJUSTMENT_')]
                            if regular_rules:
                                print(f"   Triggered rules: {', '.join(regular_rules[:5])}")
                            
                            # Handle spam actions if enabled
                            if spam_actions:
                                print(f"   🎯 Taking spam actions...")
                                action_result = await spam_actions.handle_spam_email(
                                    email.id, full_email, full_email.sender.address
                                )
                                
                                # Update action statistics
                                action_results['unsubscribe_links_found'] += action_result['unsubscribe_links']
                                if action_result['unsubscribe_links'] > 0:
                                    action_results['unsubscribe_attempts'] += 1
                                if action_result['unsubscribed']:
                                    action_results['successful_unsubscribes'] += 1
                                if action_result['moved_to_junk']:
                                    action_results['moves_to_junk'] += 1
                        else:
                            clean_count += 1
                        
                        # Log successful processing
                        logger.log_email(email, spam_result, action_result)
                        
                        # Show confidence details (only for spam to reduce output)
                        if spam_result.is_spam and spam_result.confidence_factors:
                            print(f"   {spam_result.confidence_factors}")
                    
                    # Rate limiting for large-scale processing
                    if global_idx % 10 == 0:
                        print(f"   ⏸️ Brief pause to avoid rate limits...")
                        await asyncio.sleep(1)
                    
                except Exception as e:
                    print(f"   ❌ Error analyzing email: {e}")
                    error_count += 1
                    # Log processing error with minimal email info
                    try:
                        dummy_result = SimpleSpamResult(False, 0.0, [], f"Processing error: {e}")
                        logger.log_email(email, dummy_result, error_msg=str(e))
                    except:
                        pass  # Don't let logging errors break the main process
                    continue
            
            # Batch completion summary
            current_spam = spam_count
            current_clean = clean_count
            current_errors = error_count
            print(f"\n📊 Batch {batch_num + 1} complete: {current_spam} spam, {current_clean} clean, {current_errors} errors")
            
            # Longer pause between batches
            if batch_num < total_batches - 1:
                print("   ⏸️ Pausing between batches...")
                await asyncio.sleep(3)
        
        # Summary
        print("\n" + "=" * 80)
        print("📊 SPAM DETECTION SUMMARY")
        print("=" * 80)
        print(f"   Total emails analyzed: {len(emails)}")
        print(f"   🚨 Spam detected: {spam_count}")
        print(f"   ✅ Clean emails: {clean_count}")
        if error_count > 0:
            print(f"   ❌ Analysis errors: {error_count}")
        if spam_count + clean_count > 0:
            print(f"   📈 Spam rate: {spam_count/(spam_count + clean_count)*100:.1f}%")
        
        # Spam action summary
        if spam_actions and spam_count > 0:
            print("\n" + "=" * 80)
            print("🎯 SPAM ACTION SUMMARY")
            print("=" * 80)
            print(f"   📧 Spam emails processed: {spam_count}")
            print(f"   🔗 Unsubscribe links found: {action_results['unsubscribe_links_found']}")
            print(f"   📤 Unsubscribe attempts: {action_results['unsubscribe_attempts']}")
            print(f"   ✅ Successful unsubscribes: {action_results['successful_unsubscribes']}")
            print(f"   📁 Moved to junk: {action_results['moves_to_junk']}")
            print()
            if not spam_actions.dry_run:
                print("   💡 Real actions taken - check your junk folder!")
            else:
                print("   💡 Simulation mode - no real actions taken")
        
        # Generate detailed summary report
        summary = logger.generate_summary(len(emails), spam_count, clean_count, error_count, action_results)
        
        # Show where detailed logs are saved
        logger.print_file_locations()
        
        # Clean up
        spam_detector.cleanup()
        if spam_actions:
            spam_actions.cleanup()
        
        if spam_count > 0:
            print(f"\n💡 Found {spam_count} potential spam emails!")
            if spam_actions and not spam_actions.dry_run:
                print("   Actions taken as configured above.")
            else:
                print("   Run again with action mode to unsubscribe and move to junk.")
        
        if error_count > 0:
            print(f"\n⚠️ {error_count} emails couldn't be analyzed")
            print("   This might be due to SpamAssassin not being installed or configured")
            print(f"   Check the detailed log ({logger.csv_filename}) for specific errors")
        
        print("\n🔌 Disconnected from Gmail")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        if "credentials" in str(e).lower():
            print("\n💡 Tip: Make sure you've downloaded the correct credentials file")
            print("   from Google Cloud Console and placed it as 'gmail_credentials.json'")
    
    finally:
        # Disconnect
        try:
            await gmail.disconnect()
            print("\n🔌 Disconnected from Gmail")
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Gmail Spam Management System...")
    print("📝 Note: This system can detect, unsubscribe, and move spam emails")
    print()
    
    asyncio.run(main()) 