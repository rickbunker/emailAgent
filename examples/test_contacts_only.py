"""
Gmail Contacts Test

This script tests only the Google Contacts API integration to see exactly
what contacts and email addresses we can fetch.
"""

import asyncio
import sys
import os
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory

async def test_contacts():
    print("🔍 Gmail Contacts API Test")
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
        
        # Test contacts fetching
        print("\n📱 Fetching Gmail contacts...")
        contacts = await gmail.get_contacts()
        
        print(f"📊 Total contacts found: {len(contacts)}")
        
        if not contacts:
            print("⚠️ No contacts returned - this might be the issue!")
            return
        
        # Display detailed contact information
        print(f"\n📋 First 10 contacts (detailed):")
        print("-" * 80)
        
        target_emails = ['david.stengle@gmail.com', 'alan@bassmancpa.com', 'abassman@bassmancpa.com']
        found_targets = []
        
        for i, contact in enumerate(contacts[:10]):
            name = contact.get('name', 'No Name')
            emails = contact.get('emails', [])
            
            print(f"Contact {i+1}:")
            print(f"  Name: {name}")
            print(f"  Emails: {emails}")
            print(f"  Raw data: {json.dumps(contact, indent=2)}")
            print()
            
            # Check if this is one of our target contacts
            for email in emails:
                if email.lower() in [t.lower() for t in target_emails]:
                    found_targets.append(f"{name} ({email})")
        
        # Search for specific target contacts in all contacts
        print(f"\n🎯 Searching for target contacts in all {len(contacts)} contacts:")
        print("-" * 80)
        
        all_found_targets = []
        david_contacts = []
        alan_contacts = []
        
        for contact in contacts:
            name = contact.get('name', 'No Name')
            emails = contact.get('emails', [])
            
            for email in emails:
                email_lower = email.lower()
                
                # Check for exact matches
                if email_lower in [t.lower() for t in target_emails]:
                    all_found_targets.append(f"{name} ({email})")
                
                # Check for David Stengle variations
                if 'david' in name.lower() and 'stengle' in name.lower():
                    david_contacts.append(f"{name} - {emails}")
                elif 'stengle' in email_lower or 'stengle' in name.lower():
                    david_contacts.append(f"{name} - {emails}")
                
                # Check for Alan/Bassman variations  
                if ('alan' in name.lower() and 'bassman' in name.lower()) or 'bassman' in email_lower:
                    alan_contacts.append(f"{name} - {emails}")
        
        if all_found_targets:
            print(f"✅ Found exact target matches:")
            for target in all_found_targets:
                print(f"   - {target}")
        else:
            print("❌ No exact target matches found")
        
        if david_contacts:
            print(f"\n🔍 Found David/Stengle related contacts:")
            for contact in david_contacts[:5]:  # Show first 5
                print(f"   - {contact}")
        else:
            print(f"\n❌ No David/Stengle contacts found")
        
        if alan_contacts:
            print(f"\n🔍 Found Alan/Bassman related contacts:")
            for contact in alan_contacts[:5]:  # Show first 5  
                print(f"   - {contact}")
        else:
            print(f"\n❌ No Alan/Bassman contacts found")
        
        # Show sample of all email addresses
        print(f"\n📧 Sample of all email addresses found:")
        print("-" * 80)
        all_emails = []
        for contact in contacts:
            all_emails.extend(contact.get('emails', []))
        
        unique_emails = sorted(list(set(all_emails)))
        print(f"Total unique email addresses: {len(unique_emails)}")
        
        # Show first 20 emails
        for i, email in enumerate(unique_emails[:20]):
            print(f"   {i+1:2d}. {email}")
        
        if len(unique_emails) > 20:
            print(f"   ... and {len(unique_emails) - 20} more")
        
        # Check for partial matches
        print(f"\n🔍 Searching for partial matches:")
        print("-" * 80)
        
        search_terms = ['stengle', 'bassman', 'david', 'alan']
        for term in search_terms:
            matches = [email for email in unique_emails if term.lower() in email.lower()]
            if matches:
                print(f"Emails containing '{term}': {matches[:5]}")
            else:
                print(f"No emails containing '{term}'")
        
    except Exception as e:
        print(f"❌ Error during contacts test: {e}")
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
    print("🚀 Starting Gmail Contacts Test...")
    print()
    asyncio.run(test_contacts()) 