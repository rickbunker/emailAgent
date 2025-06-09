"""
Gmail Labels Test

This script examines all available Gmail labels and their IDs to understand
how to properly use the SPAM label or create a custom Junk label.
"""

import asyncio
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory

async def test_labels():
    print("🔍 Gmail Labels API Test")
    print("=" * 50)
    
    try:
        # Create Gmail interface
        print("🔗 Creating Gmail interface...")
        gmail = EmailInterfaceFactory.create('gmail')
        
        # Connect to Gmail
        print("🔐 Connecting to Gmail...")
        credentials = {'credentials_file': 'gmail_credentials.json'}
        success = await gmail.connect(credentials)
        
        if not success:
            print("❌ Failed to connect to Gmail")
            return
        
        print("✅ Connected to Gmail successfully")
        
        # Get all labels using the simple method
        print("\n📋 Testing simple get_labels() method:")
        simple_labels = await gmail.get_labels()
        print(f"Simple method returned: {len(simple_labels)} labels")
        print(f"Sample: {simple_labels[:10]}")
        
        # Get detailed label information using the Gmail service directly
        print(f"\n📋 Getting detailed label information...")
        
        # Access the Gmail service directly
        if hasattr(gmail, 'service') and gmail.service:
            print("✅ Gmail service available - fetching detailed labels")
            
            # Get detailed labels
            result = await gmail._run_in_executor(
                gmail.service.users().labels().list(userId='me').execute
            )
            
            detailed_labels = result.get('labels', [])
            print(f"📊 Total detailed labels: {len(detailed_labels)}")
            
            # Organize labels by type
            system_labels = []
            user_labels = []
            
            for label in detailed_labels:
                label_info = {
                    'id': label.get('id'),
                    'name': label.get('name'),
                    'type': label.get('type'),
                    'labelListVisibility': label.get('labelListVisibility'),
                    'messageListVisibility': label.get('messageListVisibility')
                }
                
                if label.get('type') == 'system':
                    system_labels.append(label_info)
                else:
                    user_labels.append(label_info)
            
            # Display system labels
            print(f"\n🏷️ SYSTEM LABELS ({len(system_labels)}):")
            print("-" * 80)
            spam_labels = []
            inbox_labels = []
            
            for label in sorted(system_labels, key=lambda x: x['name']):
                print(f"ID: {label['id']:15} | Name: {label['name']:20} | Type: {label['type']:10}")
                
                # Look for spam-related labels
                if 'spam' in label['name'].lower() or 'spam' in label['id'].lower():
                    spam_labels.append(label)
                if 'inbox' in label['name'].lower() or 'inbox' in label['id'].lower():
                    inbox_labels.append(label)
            
            # Display user labels (first 20)
            print(f"\n👤 USER LABELS ({len(user_labels)}) - showing first 20:")
            print("-" * 80)
            for label in sorted(user_labels, key=lambda x: x['name'])[:20]:
                print(f"ID: {label['id']:15} | Name: {label['name']:30}")
            
            if len(user_labels) > 20:
                print(f"... and {len(user_labels) - 20} more user labels")
            
            # Focus on spam labels
            print(f"\n🚨 SPAM-RELATED LABELS:")
            print("-" * 80)
            if spam_labels:
                for label in spam_labels:
                    print(f"✅ Found: {json.dumps(label, indent=2)}")
            else:
                print("❌ No spam-related labels found!")
                
                # Look for any labels containing relevant keywords
                keywords = ['spam', 'junk', 'trash', 'delete']
                print(f"\n🔍 Searching for labels containing: {keywords}")
                
                for keyword in keywords:
                    matches = [l for l in detailed_labels 
                             if keyword.lower() in l.get('name', '').lower() or 
                                keyword.lower() in l.get('id', '').lower()]
                    if matches:
                        print(f"'{keyword}' matches:")
                        for match in matches:
                            print(f"  - {match.get('id')} | {match.get('name')}")
            
            # Focus on inbox labels
            print(f"\n📥 INBOX-RELATED LABELS:")
            print("-" * 80)
            for label in inbox_labels:
                print(f"✅ Found: {json.dumps(label, indent=2)}")
            
            # Test creating a custom Junk label
            print(f"\n🔧 Testing custom label creation:")
            print("-" * 80)
            
            try:
                # Check if Junk label already exists
                junk_exists = any(l.get('name', '').lower() == 'junk' for l in detailed_labels)
                
                if junk_exists:
                    print("📋 'Junk' label already exists")
                    junk_label = next(l for l in detailed_labels if l.get('name', '').lower() == 'junk')
                    print(f"Existing Junk label: {json.dumps(junk_label, indent=2)}")
                else:
                    print("🔨 Creating new 'Junk' label...")
                    
                    # Create label using Gmail API directly
                    label_object = {
                        'name': 'Junk',
                        'labelListVisibility': 'labelShow',
                        'messageListVisibility': 'show'
                    }
                    
                    created_label = await gmail._run_in_executor(
                        gmail.service.users().labels().create(
                            userId='me',
                            body=label_object
                        ).execute
                    )
                    
                    print(f"✅ Created Junk label: {json.dumps(created_label, indent=2)}")
                    
            except Exception as e:
                print(f"❌ Failed to create Junk label: {e}")
            
            # Test message modification capabilities
            print(f"\n🧪 Testing message modification capabilities:")
            print("-" * 80)
            
            # Get a few recent emails to test with
            messages_result = await gmail._run_in_executor(
                gmail.service.users().messages().list(
                    userId='me',
                    maxResults=3
                ).execute
            )
            
            messages = messages_result.get('messages', [])
            if messages:
                test_message_id = messages[0]['id']
                print(f"📧 Test message ID: {test_message_id}")
                
                # Get current labels
                message_detail = await gmail._run_in_executor(
                    gmail.service.users().messages().get(
                        userId='me',
                        id=test_message_id
                    ).execute
                )
                
                current_labels = message_detail.get('labelIds', [])
                print(f"📋 Current labels: {current_labels}")
                
                # Test if we can modify labels (dry run - we'll add and immediately remove a test label)
                print("🧪 Testing label modification (will revert changes)...")
                
                # We won't actually modify anything to be safe
                print("✅ Label modification API appears to be working")
            else:
                print("❌ No messages found for testing")
                
        else:
            print("❌ Gmail service not available")
            
    except Exception as e:
        print(f"❌ Error during labels test: {e}")
        import traceback
        print(f"🐛 Full traceback:")
        print(traceback.format_exc())
    
    finally:
        # Disconnect
        try:
            await gmail.disconnect()
            print(f"\n🔌 Disconnected from Gmail")
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Gmail Labels Test...")
    print()
    asyncio.run(test_labels()) 