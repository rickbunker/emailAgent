#!/usr/bin/env python3
"""
Microsoft Graph Web Authentication Test

This uses authorization code flow with a local web server,
which is more reliable than device code flow.
"""

import asyncio
import sys
import os
import json
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs
import http.server
import socketserver
import threading
from datetime import datetime

# Add src to path (go up one directory from tests/)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import msal
import aiohttp

class AuthorizationHandler(http.server.SimpleHTTPRequestHandler):
    """Handle OAuth callback."""
    
    def do_GET(self):
        """Handle GET request with authorization code."""
        if self.path.startswith('/?code='):
            # Extract authorization code and state
            parsed = urlparse(self.path)
            query_params = parse_qs(parsed.query)
            
            if 'code' in query_params:
                self.server.auth_code = query_params['code'][0]
                self.server.state = query_params.get('state', [None])[0]
                
                # Send success response
                self.send_response(200)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                success_html = """
                <html>
                <head><title>Authentication Success</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: green;">✅ Authentication Successful!</h2>
                    <p>You can close this window and return to the terminal.</p>
                    <p>The email agent is now connecting to your Microsoft 365 account.</p>
                </body>
                </html>
                """
                self.wfile.write(success_html.encode())
            else:
                # Send error response
                self.send_response(400)
                self.send_header('Content-type', 'text/html')
                self.end_headers()
                
                error_html = """
                <html>
                <head><title>Authentication Error</title></head>
                <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                    <h2 style="color: red;">❌ Authentication Failed</h2>
                    <p>No authorization code received. Please try again.</p>
                </body>
                </html>
                """
                self.wfile.write(error_html.encode())
        else:
            # Default response
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            waiting_html = """
            <html>
            <head><title>Waiting for Authentication</title></head>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>🔄 Waiting for Microsoft 365 Authentication...</h2>
                <p>Please complete the authentication process in the other browser tab.</p>
            </body>
            </html>
            """
            self.wfile.write(waiting_html.encode())
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass

async def test_msgraph_web_auth():
    """Test Microsoft Graph with web-based authentication."""
    print("🧪 Microsoft Graph Web Authentication Test")
    print("="*60)
    
    try:
        # Load credentials (go up to project root, then to examples)
        creds_path = Path(os.path.join(os.path.dirname(__file__), '..', 'examples', 'msgraph_credentials.json'))
        if not creds_path.exists():
            print("❌ Credentials file not found")
            return
        
        with open(creds_path) as f:
            credentials = json.load(f)
        
        print(f"✅ Loaded credentials for: {credentials['application_name']}")
        
        # MSAL setup
        client_id = credentials['client_id']
        tenant_id = credentials['tenant_id']
        redirect_uri = "http://localhost:8080"
        
        authority = f"https://login.microsoftonline.com/{tenant_id}"
        scopes = [
            'https://graph.microsoft.com/Mail.ReadWrite',
            'https://graph.microsoft.com/Mail.Send',
            'https://graph.microsoft.com/User.Read'
        ]
        
        # Create public client app (better for desktop apps)
        app = msal.PublicClientApplication(
            client_id=client_id,
            authority=authority
        )
        
        print(f"\n🔗 Starting authentication flow...")
        
        # Check for cached token first
        accounts = app.get_accounts()
        token_result = None
        
        if accounts:
            print(f"   Found {len(accounts)} cached account(s)")
            token_result = app.acquire_token_silent(scopes, account=accounts[0])
        
        if not token_result:
            print("   No cached token found, starting interactive authentication...")
            
            # Start local server
            port = 8080
            server = socketserver.TCPServer(("", port), AuthorizationHandler)
            server.auth_code = None
            server.state = None
            
            # Start server in background thread
            server_thread = threading.Thread(target=server.serve_forever)
            server_thread.daemon = True
            server_thread.start()
            
            try:
                # Get authorization URL
                flow = app.initiate_auth_code_flow(
                    scopes=scopes,
                    redirect_uri=redirect_uri
                )
                
                if "auth_uri" not in flow:
                    raise Exception("Failed to create auth flow")
                
                auth_url = flow["auth_uri"]
                
                print(f"\n🌐 Opening browser for authentication...")
                print(f"   URL: {auth_url}")
                print(f"   Sign in as: rbunker@invconsult.com")
                print(f"   Waiting for authentication...")
                
                # Open browser
                webbrowser.open(auth_url)
                
                # Wait for authorization code
                timeout = 300  # 5 minutes
                elapsed = 0
                
                while server.auth_code is None and elapsed < timeout:
                    await asyncio.sleep(1)
                    elapsed += 1
                
                if server.auth_code is None:
                    raise Exception("Authentication timeout - no authorization code received")
                
                print(f"   ✅ Authorization code received!")
                
                # Exchange code for token - include the received state
                auth_response = {'code': server.auth_code}
                if server.state:
                    auth_response['state'] = server.state
                
                token_result = app.acquire_token_by_auth_code_flow(
                    flow,
                    auth_response
                )
                
            finally:
                server.shutdown()
                server.server_close()
        
        if "access_token" not in token_result:
            error = token_result.get("error_description", "Unknown authentication error")
            raise Exception(f"Failed to get access token: {error}")
        
        access_token = token_result["access_token"]
        print(f"✅ Successfully obtained access token!")
        
        # Test Microsoft Graph API
        print(f"\n📧 Testing Microsoft Graph API...")
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json'
        }
        
        async with aiohttp.ClientSession(headers=headers) as session:
            # Get user profile
            async with session.get('https://graph.microsoft.com/v1.0/me') as response:
                if response.status == 200:
                    profile = await response.json()
                    print(f"✅ Connected as: {profile.get('displayName')} ({profile.get('mail') or profile.get('userPrincipalName')})")
                    print(f"   Job Title: {profile.get('jobTitle', 'Not specified')}")
                    print(f"   Office: {profile.get('officeLocation', 'Not specified')}")
                else:
                    raise Exception(f"Failed to get profile: HTTP {response.status}")
            
            # Test fetching emails
            async with session.get('https://graph.microsoft.com/v1.0/me/messages?$top=5') as response:
                if response.status == 200:
                    data = await response.json()
                    messages = data.get('value', [])
                    print(f"\n📬 Fetched {len(messages)} recent emails:")
                    
                    for i, msg in enumerate(messages[:3], 1):
                        sender = msg.get('from', {}).get('emailAddress', {})
                        subject = msg.get('subject', '(no subject)')
                        received = msg.get('receivedDateTime', '')
                        attachments = len(msg.get('attachments', []))
                        
                        print(f"   {i}. From: {sender.get('address', 'Unknown')}")
                        print(f"      Subject: {subject[:50]}...")
                        print(f"      Date: {received}")
                        print(f"      Attachments: {attachments}")
                    
                    print(f"\n🎉 Microsoft Graph integration is working correctly!")
                    print(f"   Ready to process emails from rbunker@invconsult.com")
                    
                else:
                    raise Exception(f"Failed to list messages: HTTP {response.status}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        print(f"\n🔧 Troubleshooting tips:")
        print(f"   1. Check Azure app registration allows public client flows")
        print(f"   2. Ensure redirect URI http://localhost:8080 is registered")
        print(f"   3. Verify account rbunker@invconsult.com has necessary permissions")

if __name__ == "__main__":
    asyncio.run(test_msgraph_web_auth()) 