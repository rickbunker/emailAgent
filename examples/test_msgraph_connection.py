"""
Microsoft Graph Connection Test

This script tests the basic Microsoft Graph connection and displays account information.
Use this to verify your setup before running the full spam detection system.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from email_interface import EmailInterfaceFactory

async def test_msgraph_connection():
    print("🧪 Testing Microsoft Graph Connection")
    print("=" * 50)
    
    try:
        # Create Microsoft Graph interface
        print("🔗 Creating Microsoft Graph interface...")
        msgraph = EmailInterfaceFactory.create('microsoft_graph')
        
        # Connect to Microsoft Graph
        print("🔐 Connecting to Microsoft Graph...")
        print("   (Browser will open for authentication)")
        
        # ⚠️ UPDATE THESE CREDENTIALS WITH YOUR AZURE APP REGISTRATION DETAILS
        credentials = {
            'client_id': 'YOUR_CLIENT_ID_HERE',     # Replace with your Application (client) ID
            'tenant_id': 'common',                  # Use 'common' for personal accounts, or your tenant ID
            'redirect_uri': 'http://localhost:8080' # Must match your Azure app registration
        }
        
        # Check if credentials are still default
        if credentials['client_id'] == 'YOUR_CLIENT_ID_HERE':
            print("❌ Error: Please update the credentials in this script")
            print("   1. Update 'client_id' with your Azure Application (client) ID")
            print("   2. Update 'tenant_id' if needed ('common' works for personal accounts)")
            print("   3. See MSGRAPH_SETUP.md for detailed setup instructions")
            return
        
        success = await msgraph.connect(credentials)
        
        if not success:
            print("❌ Failed to connect to Microsoft Graph")
            return
        
        print("✅ Connected to Microsoft Graph successfully!")
        
        # Get profile
        print(f"\n👤 Getting user profile...")
        profile = await msgraph.get_profile()
        print(f"   📧 Email: {profile.get('email')}")
        print(f"   👤 Name: {profile.get('name')}")
        print(f"   🏢 Job Title: {profile.get('job_title', 'Not specified')}")
        print(f"   🏟️ Office: {profile.get('office_location', 'Not specified')}")
        
        # Test folder access
        print(f"\n📁 Getting email folders...")
        folders = await msgraph.get_labels()  # get_labels() returns folder names for Microsoft Graph
        print(f"   ✅ Found {len(folders)} folders")
        
        if folders:
            print(f"   📋 Folders: {', '.join(folders[:10])}")
            if len(folders) > 10:
                print(f"   ... and {len(folders) - 10} more")
        
        # Test email access (get a few recent emails)
        print(f"\n📧 Testing email access...")
        from email_interface.base import EmailSearchCriteria
        
        criteria = EmailSearchCriteria(max_results=3)
        emails = await msgraph.list_emails(criteria)
        
        print(f"   ✅ Found {len(emails)} recent emails")
        
        if emails:
            print(f"   📋 Recent emails:")
            for i, email in enumerate(emails, 1):
                sender = email.sender.name or email.sender.address
                subject = email.subject[:50] + "..." if len(email.subject) > 50 else email.subject
                print(f"   {i}. From: {sender}")
                print(f"      Subject: {subject}")
                print(f"      Date: {email.sent_date}")
                print()
        
        # Test contacts access (if available)
        print(f"📱 Testing contacts access...")
        try:
            if hasattr(msgraph, 'session') and msgraph.session:
                url = f"{msgraph.GRAPH_ENDPOINT}/me/contacts?$top=5"
                async with msgraph.session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        contacts = data.get('value', [])
                        print(f"   ✅ Found {len(contacts)} sample contacts")
                        
                        if contacts:
                            for contact in contacts[:3]:
                                name = contact.get('displayName', 'No name')
                                emails = contact.get('emailAddresses', [])
                                email_str = emails[0].get('address', 'No email') if emails else 'No email'
                                print(f"   📋 {name} ({email_str})")
                    else:
                        print(f"   ⚠️ Contacts access returned HTTP {response.status}")
            else:
                print(f"   ⚠️ No session available for contacts test")
                
        except Exception as e:
            print(f"   ⚠️ Contacts test failed: {e}")
        
        print(f"\n🎉 Microsoft Graph Connection Test Complete!")
        print("=" * 60)
        print(f"✅ Connection: Working")
        print(f"✅ Authentication: Working") 
        print(f"✅ Profile Access: Working")
        print(f"✅ Folder Access: Working")
        print(f"✅ Email Access: Working")
        print(f"\n🚀 Ready to run full spam detection system!")
        print(f"   Next: Run 'python msgraph_spam_test.py' for spam management")
        
    except Exception as e:
        print(f"❌ Error during connection test: {e}")
        import traceback
        print(f"🐛 Full traceback:")
        print(traceback.format_exc())
        
        print(f"\n🔧 Troubleshooting Tips:")
        print(f"   1. Check your client_id and tenant_id are correct")
        print(f"   2. Ensure redirect URI matches Azure app registration")
        print(f"   3. Verify API permissions are granted in Azure portal")
        print(f"   4. See MSGRAPH_SETUP.md for detailed setup instructions")
    
    finally:
        # Disconnect
        try:
            await msgraph.disconnect()
            print(f"\n🔌 Disconnected from Microsoft Graph")
        except:
            pass

if __name__ == "__main__":
    print("🚀 Starting Microsoft Graph Connection Test...")
    print()
    asyncio.run(test_msgraph_connection()) 