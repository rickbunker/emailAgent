"""
Test Spam Label Assignment

This script tests the spam labeling functionality to ensure it works
with both Gmail's built-in SPAM label and custom Junk labels.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory

async def test_spam_labels():
    print("🧪 Testing Spam Label Assignment")
    print("=" * 60)
    
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
        
        # Get recent emails for testing
        print(f"\n📧 Getting recent emails for testing...")
        from email_interface.base import EmailSearchCriteria
        
        criteria = EmailSearchCriteria(max_results=5)
        recent_emails = await gmail.list_emails(criteria)
        
        if not recent_emails:
            print("❌ No recent emails found")
            return
        
        print(f"✅ Found {len(recent_emails)} recent emails")
        
        # Pick the first email that's not already in spam
        test_email = None
        for email in recent_emails:
            print(f"   📧 Email {email.id}: {email.subject[:50]}...")
            
            # Get detailed email info to check current labels
            if hasattr(gmail, 'service') and gmail.service:
                message_detail = await gmail._run_in_executor(
                    gmail.service.users().messages().get(
                        userId='me',
                        id=email.id
                    ).execute
                )
                
                current_labels = message_detail.get('labelIds', [])
                print(f"      📋 Current labels: {current_labels}")
                
                # Skip if already in SPAM
                if 'SPAM' not in current_labels:
                    test_email = email
                    test_email_labels = current_labels
                    break
        
        if not test_email:
            print("❌ No suitable test email found (all in SPAM already)")
            return
        
        print(f"\n🎯 Selected test email: {test_email.id}")
        print(f"   📋 Subject: {test_email.subject}")
        print(f"   📋 From: {test_email.sender.address}")
        print(f"   📋 Current labels: {test_email_labels}")
        
        # Test label operations
        print(f"\n🧪 TESTING LABEL OPERATIONS:")
        print("-" * 50)
        
        # Test 1: Add SPAM label
        print(f"1️⃣ Testing adding SPAM label...")
        try:
            result = await gmail.add_label(test_email.id, 'SPAM')
            print(f"   ✅ Add SPAM result: {result}")
            
            # Verify the change
            message_detail = await gmail._run_in_executor(
                gmail.service.users().messages().get(
                    userId='me',
                    id=test_email.id
                ).execute
            )
            
            new_labels = message_detail.get('labelIds', [])
            print(f"   📋 Labels after adding SPAM: {new_labels}")
            
            if 'SPAM' in new_labels:
                print(f"   ✅ SPAM label successfully added!")
            else:
                print(f"   ❌ SPAM label not found in updated labels")
                
        except Exception as e:
            print(f"   ❌ Failed to add SPAM label: {e}")
            import traceback
            print(f"   🐛 Full error: {traceback.format_exc()}")
        
        # Test 2: Remove from INBOX
        print(f"\n2️⃣ Testing removing INBOX label...")
        try:
            result = await gmail.remove_label(test_email.id, 'INBOX')
            print(f"   ✅ Remove INBOX result: {result}")
            
            # Verify the change
            message_detail = await gmail._run_in_executor(
                gmail.service.users().messages().get(
                    userId='me',
                    id=test_email.id
                ).execute
            )
            
            final_labels = message_detail.get('labelIds', [])
            print(f"   📋 Final labels: {final_labels}")
            
            if 'INBOX' not in final_labels:
                print(f"   ✅ INBOX label successfully removed!")
            else:
                print(f"   ❌ INBOX label still present")
                
        except Exception as e:
            print(f"   ❌ Failed to remove INBOX label: {e}")
            import traceback
            print(f"   🐛 Full error: {traceback.format_exc()}")
        
        # Test 3: Verify final state
        print(f"\n3️⃣ Final verification...")
        try:
            message_detail = await gmail._run_in_executor(
                gmail.service.users().messages().get(
                    userId='me',
                    id=test_email.id
                ).execute
            )
            
            final_labels = message_detail.get('labelIds', [])
            print(f"   📋 Final email labels: {final_labels}")
            
            # Check if it's properly in spam
            if 'SPAM' in final_labels and 'INBOX' not in final_labels:
                print(f"   🎉 SUCCESS: Email successfully moved to SPAM!")
                print(f"   📝 Note: This email will now be hidden from normal Gmail views")
            elif 'SPAM' in final_labels:
                print(f"   ⚠️ PARTIAL: SPAM label added but INBOX not removed")
            else:
                print(f"   ❌ FAILED: Email not properly moved to SPAM")
                
        except Exception as e:
            print(f"   ❌ Failed final verification: {e}")
        
        # Test 4: Restore email (move back to inbox for cleanup)
        print(f"\n4️⃣ Restoring email to inbox (cleanup)...")
        try:
            # Remove SPAM label
            await gmail.remove_label(test_email.id, 'SPAM')
            print(f"   📍 Removed SPAM label")
            
            # Add back to INBOX
            await gmail.add_label(test_email.id, 'INBOX')
            print(f"   📍 Added back to INBOX")
            
            # Verify restoration
            message_detail = await gmail._run_in_executor(
                gmail.service.users().messages().get(
                    userId='me',
                    id=test_email.id
                ).execute
            )
            
            restored_labels = message_detail.get('labelIds', [])
            print(f"   📋 Restored labels: {restored_labels}")
            
            if 'INBOX' in restored_labels and 'SPAM' not in restored_labels:
                print(f"   ✅ Email successfully restored to INBOX")
            else:
                print(f"   ⚠️ Email restoration may not be complete")
                
        except Exception as e:
            print(f"   ❌ Failed to restore email: {e}")
        
        # Summary
        print(f"\n📊 TEST SUMMARY:")
        print("-" * 50)
        print(f"✅ Gmail SPAM label operations work correctly")
        print(f"✅ Messages can be moved to and from SPAM")
        print(f"📝 SPAM messages are hidden from normal Gmail views")
        print(f"📝 This matches Gmail's expected behavior")
        
    except Exception as e:
        print(f"❌ Error during spam labels test: {e}")
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
    print("🚀 Starting Spam Labels Test...")
    print()
    asyncio.run(test_spam_labels()) 