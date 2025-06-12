# Microsoft Graph API Setup Guide

This guide will help you set up Microsoft Graph API access for the email agent to work with Microsoft 365/Outlook accounts.

## Prerequisites

- Microsoft 365 account (Office 365, Outlook.com, etc.)
- Azure account (free tier is sufficient)
- Python environment with required dependencies

## Step 1: Create Azure App Registration

1. **Go to Azure Portal**:
   - Visit [https://portal.azure.com](https://portal.azure.com)
   - Sign in with your Microsoft account

2. **Navigate to App Registrations**:
   - Search for "App registrations" in the top search bar
   - Click on "App registrations"

3. **Create New Registration**:
   - Click "New registration"
   - Fill in the details:
     - **Name**: "Email Agent Spam Manager" (or any name you prefer)
     - **Supported account types**: "Accounts in any organizational directory and personal Microsoft accounts"
     - **Redirect URI**: Select "Public client/native (mobile & desktop)" and enter `http://localhost:8080`
   - Click "Register"

4. **Note Your Application Details**:
   - After registration, you'll see the **Overview** page
   - Copy and save these values:
     - **Application (client) ID**: This is your `client_id`
     - **Directory (tenant) ID**: This is your `tenant_id`

## Step 2: Configure API Permissions

1. **Add Required Permissions**:
   - In your app registration, click "API permissions" in the left sidebar
   - Click "Add a permission"
   - Select "Microsoft Graph"
   - Choose "Delegated permissions"
   - Add these permissions:
     - `Mail.ReadWrite` - Read and write access to user mail
     - `Mail.Send` - Send mail as a user
     - `User.Read` - Sign in and read user profile
     - `Contacts.Read` - Read user contacts

2. **Grant Admin Consent** (if required):
   - If you see yellow warning triangles, click "Grant admin consent for [your organization]"
   - Click "Yes" to confirm

## Step 3: Configure Authentication

1. **Set Redirect URIs**:
   - Go to "Authentication" in the left sidebar
   - Under "Platform configurations", ensure you have:
     - **Public client/native (mobile & desktop)** with redirect URI: `http://localhost:8080`
   - Under "settings":
     - Enable "Allow public client flows": **Yes**

## Step 4: Update Email Agent Configuration

1. **Update the Microsoft Graph spam test script**:
   ```python
   # In msgraph_spam_test.py, update the credentials section:
   credentials = {
       'client_id': 'YOUR_APPLICATION_CLIENT_ID',  # From Step 1
       'tenant_id': 'YOUR_DIRECTORY_TENANT_ID',   # From Step 1 (or 'common' for personal accounts)
       'redirect_uri': 'http://localhost:8080'     # Must match Azure app registration
   }
   ```

2. **For Personal Microsoft Accounts** (outlook.com, hotmail.com, live.com):
   - Use `tenant_id: 'common'`

3. **For Organizational Accounts** (company/school):
   - Use your specific tenant ID from the Azure portal

## Step 5: Test the Connection

1. **Run the Test Script**:
   ```bash
   cd examples
   python msgraph_spam_test.py
   ```

2. **Complete Authentication**:
   - The script will open a browser window
   - Sign in with your Microsoft account
   - Grant permissions to the application
   - The browser will redirect to localhost (this is expected)

3. **Verify Connection**:
   - The script should display your profile information
   - You should see your email address and folder structure

## Troubleshooting

### Common Issues:

1. **"AADSTS50011: The reply URL specified in the request does not match"**:
   - Ensure the redirect URI in your code matches exactly what's configured in Azure
   - Check for typos in `http://localhost:8080`

2. **"AADSTS65001: The user or administrator has not consented"**:
   - Go back to API permissions in Azure and grant admin consent
   - Make sure all required permissions are added

3. **"Invalid client"**:
   - Verify your client_id is correct
   - Ensure the app registration is configured as a public client

4. **"Insufficient privileges"**:
   - Check that all required Graph API permissions are granted
   - Try signing in with an admin account if in an organization

### Permission Details:

- **Mail.ReadWrite**: Required to read emails and move them to junk folders
- **Mail.Send**: Required if the agent needs to send emails (optional for spam detection)
- **User.Read**: Required to get user profile information
- **Contacts.Read**: Required to load contacts for whitelist protection

## Security Notes

- The email agent uses OAuth 2.0 with PKCE for secure authentication
- No passwords are stored - only temporary access tokens
- Tokens are refreshed automatically
- The app only requests minimum required permissions

## Next Steps

Once setup is complete, you can:
1. Run spam detection on your Microsoft 365 emails
2. Configure whitelists for trusted domains
3. Set up automated spam management
4. Review detailed logs and reports

For questions or issues, refer to the [Microsoft Graph documentation](https://docs.microsoft.com/en-us/graph/) or the main project README.
