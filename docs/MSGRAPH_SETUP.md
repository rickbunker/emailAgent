# Microsoft Graph API Setup Guide

This guide helps you configure Microsoft Graph API access for the **Asset Document Agent** to process emails containing private market investment documents from Microsoft 365/Outlook accounts.

## System Overview

The Asset Document Agent uses Microsoft Graph to:
- **Monitor asset-related emails** from fund managers, borrowers, and service providers
- **Extract and classify documents** (rent rolls, financial statements, loan documents, etc.)
- **Learn from patterns** to improve classification accuracy over time
- **Organize documents** into asset-specific folder structures
- **Enable human review** for low-confidence classifications

## Prerequisites

- Microsoft 365 account (Office 365, Outlook.com, etc.)
- Azure account (free tier is sufficient)
- Python environment with required dependencies
- Qdrant vector database running (for memory storage)

## Step 1: Create Azure App Registration

### Azure Portal Setup

1. **Access Azure Portal**:
   - Visit [https://portal.azure.com](https://portal.azure.com)
   - Sign in with your Microsoft account

2. **Navigate to App Registrations**:
   - Search for "App registrations" in the top search bar
   - Click on "App registrations"

3. **Create New Registration**:
   - Click "New registration"
   - Configure the application:
     - **Name**: "Asset Document Processing Agent"
     - **Supported account types**: "Accounts in any organizational directory and personal Microsoft accounts"
     - **Redirect URI**: Select "Public client/native (mobile & desktop)" and enter `http://localhost:8080`
   - Click "Register"

4. **Record Application Details**:
   After registration, copy these values from the **Overview** page:
   - **Application (client) ID**: Your `MSGRAPH_CLIENT_ID`
   - **Directory (tenant) ID**: Your `MSGRAPH_TENANT_ID`

## Step 2: Configure API Permissions

### Required Permissions for Document Processing

1. **Add Microsoft Graph Permissions**:
   - In your app registration, click "API permissions"
   - Click "Add a permission" → "Microsoft Graph" → "Delegated permissions"
   - Add these permissions:
     - `Mail.ReadWrite` - Read and write access to user mail
     - `Mail.Send` - Send notifications and confirmations
     - `User.Read` - Sign in and read user profile
     - `Contacts.Read` - Access contact information for sender identification
     - `Files.ReadWrite.All` - Access OneDrive/SharePoint for document storage (optional)

2. **Grant Admin Consent**:
   - Click "Grant admin consent for [your organization]"
   - Click "Yes" to confirm all permissions

### Permission Usage Details

- **Mail.ReadWrite**: Process incoming emails with attachments
- **Mail.Send**: Send processing confirmations and alerts
- **User.Read**: Identify the user and personalize the experience
- **Contacts.Read**: Match senders to known contacts and assets
- **Files.ReadWrite.All**: Optional - for SharePoint/OneDrive integration

## Step 3: Configure Authentication Settings

### Authentication Configuration

1. **Set Platform Configuration**:
   - Go to "Authentication" in the left sidebar
   - Ensure "Public client/native (mobile & desktop)" is configured with:
     - **Redirect URI**: `http://localhost:8080`

2. **Advanced Settings**:
   - Under "Advanced settings":
     - **Allow public client flows**: **Yes**
     - **Supported account types**: Leave as configured during registration

## Step 4: Update System Configuration

### Environment Configuration

1. **Update Configuration File**:
   Edit `config/config.yaml` or set environment variables:
   ```yaml
   email_interface:
     msgraph:
       client_id: "YOUR_APPLICATION_CLIENT_ID"      # From Step 1
       tenant_id: "YOUR_DIRECTORY_TENANT_ID"       # From Step 1
       redirect_uri: "http://localhost:8080"       # Must match Azure
       scopes:
         - "https://graph.microsoft.com/Mail.ReadWrite"
         - "https://graph.microsoft.com/Mail.Send"
         - "https://graph.microsoft.com/User.Read"
         - "https://graph.microsoft.com/Contacts.Read"

   # Asset processing configuration
   asset_processing:
     base_assets_path: "./assets"
     max_attachment_size_mb: 25
     allowed_extensions: [".pdf", ".xlsx", ".xls", ".doc", ".docx", ".pptx", ".jpg", ".png", ".dwg"]
     low_confidence_threshold: 0.4

   # Antivirus configuration
   security:
     clamav_enabled: true  # Set to false if ClamAV not installed
   ```

2. **Account Type Specific Settings**:

   **For Personal Microsoft Accounts** (outlook.com, hotmail.com, live.com):
   ```yaml
   email_interface:
     msgraph:
       tenant_id: "common"
   ```

   **For Organizational Accounts** (company/school):
   ```yaml
   email_interface:
     msgraph:
       tenant_id: "your-specific-tenant-id"  # From Azure portal
   ```

## Step 5: Test the Integration

### Initial Connection Test

1. **Start the System**:
   ```bash
   # Ensure Qdrant is running
   docker run -p 6333:6333 qdrant/qdrant

   # Start the web interface
   python -m src.web_ui.app
   ```

2. **Test Microsoft Graph Connection**:
   - Navigate to `http://localhost:5000`
   - Go to "Email Processing" section
   - Select "Microsoft Graph" as the email interface
   - Click "Test Connection"

3. **Complete Authentication Flow**:
   - Browser will open for Microsoft sign-in
   - Sign in with your Microsoft account
   - Grant permissions to the application
   - Browser redirects to localhost (expected behavior)
   - Connection status should show "Connected"

### Asset Processing Test

1. **Create Test Assets**:
   - Go to "Asset Management" in the web UI
   - Create a few test assets (e.g., "Test Property A", "Test Credit Fund B")
   - Add identifiers and keywords for each asset

2. **Process Test Emails**:
   - Send yourself an email with a PDF attachment
   - Include asset-related keywords in the subject/body
   - Use the web interface to process the mailbox
   - Verify documents are classified and organized correctly

## Step 6: Production Setup

### Automated Processing Configuration

1. **Configure Email Monitoring**:
   ```yaml
   email_processing:
     check_interval_minutes: 15
     batch_size: 20
     max_concurrent_emails: 5
     max_concurrent_attachments: 10

   # Human review settings
   human_review:
     very_low_confidence_threshold: 0.4
     auto_process_threshold: 0.85
     review_notification_email: "admin@yourcompany.com"
   ```

2. **Memory Learning Configuration**:
   ```yaml
   memory:
     auto_learning_threshold: 0.75
     pattern_retention_days: 365
     similarity_threshold: 0.8
   ```

## Troubleshooting

### Authentication Issues

**"AADSTS50011: Reply URL mismatch"**:
- Verify redirect URI matches exactly: `http://localhost:8080`
- Check for extra spaces or characters
- Ensure protocol is `http` not `https` for localhost

**"AADSTS65001: User has not consented"**:
- Return to Azure Portal → API permissions
- Click "Grant admin consent"
- Ensure all required permissions are checked

**"Invalid client"**:
- Verify `client_id` is copied correctly from Azure
- Confirm app registration is set as "Public client"

### Processing Issues

**Documents Not Being Classified**:
- Check if Qdrant is running and accessible
- Verify asset definitions include relevant identifiers
- Review logs for processing errors
- Use the human review interface to provide feedback

**Antivirus Scanning Failures**:
- Install ClamAV: `brew install clamav` (macOS) or appropriate package manager
- Update virus definitions: `freshclam`
- Or disable antivirus scanning in config if not needed

**Memory Learning Not Working**:
- Ensure Qdrant collections are initialized
- Check procedural memory logs for errors
- Verify sufficient confidence in training data

### Performance Optimization

**Slow Email Processing**:
- Adjust `max_concurrent_emails` and `max_concurrent_attachments`
- Consider disabling antivirus scanning for trusted sources
- Increase batch size for bulk processing

**High Memory Usage**:
- Reduce concurrent processing limits
- Clear old procedural memory patterns periodically
- Monitor Qdrant memory usage

## Security Considerations

### Data Protection
- All authentication uses OAuth 2.0 with PKCE
- No passwords stored - only temporary access tokens
- Tokens refreshed automatically
- Document content processed locally before vector storage

### Access Control
- Minimum required permissions requested
- Separate tenant configurations for different organizations
- Admin consent required for organizational deployments

### Compliance
- Document processing logs maintained for audit trails
- Human review system for sensitive classifications
- Configurable data retention policies

## Advanced Configuration

### Multi-Tenant Setup
For organizations managing multiple clients:
```yaml
multi_tenant:
  enabled: true
  tenant_configs:
    - name: "Client A"
      tenant_id: "client-a-tenant-id"
      asset_prefix: "CLNT_A"
    - name: "Client B"
      tenant_id: "client-b-tenant-id"
      asset_prefix: "CLNT_B"
```

### SharePoint Integration (Optional)
```yaml
sharepoint:
  enabled: true
  site_url: "https://yourcompany.sharepoint.com/sites/AssetManagement"
  document_library: "Asset Documents"
  sync_frequency_hours: 4
```

## Next Steps

After successful setup:

1. **Asset Configuration**: Define your real assets with proper identifiers
2. **Sender Mapping**: Create mappings between email senders and assets
3. **Training**: Process historical emails to build classification patterns
4. **Monitoring**: Set up regular email processing and human review workflows
5. **Integration**: Connect with existing document management systems

## Support Resources

- **Microsoft Graph Documentation**: [https://docs.microsoft.com/en-us/graph/](https://docs.microsoft.com/en-us/graph/)
- **Azure App Registration Guide**: [https://docs.microsoft.com/en-us/azure/active-directory/develop/](https://docs.microsoft.com/en-us/azure/active-directory/develop/)
- **System Architecture**: See `docs/EMAIL_INTERFACE_README.md`
- **Development Setup**: See `docs/DEVELOPMENT_SETUP.md`

For system-specific issues, check the application logs in the `logs/` directory or use the built-in diagnostics in the web interface.
