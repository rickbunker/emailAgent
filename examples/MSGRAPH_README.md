# Microsoft Graph Spam Management System

This directory contains a complete spam detection and management system for Microsoft 365/Outlook accounts using Microsoft Graph API.

## 🎯 Features

### **Spam Detection**
- **SpamAssassin Integration**: spam analysis with customizable rules
- **Multi-level Whitelisting**: Automatic protection for trusted sources
- **Contact Integration**: Automatic protection for Microsoft Graph contacts
- **False Positive Prevention**: Complete safeguards against legitimate email removal

### **Automated Actions**
- **Unsubscribe**: Safely attempts to unsubscribe from legitimate mailing lists
- **Folder Management**: Moves spam to Junk Email folder or creates custom Spam folder
- **Batch Processing**: Efficient handling of large email volumes
- **Rate Limiting**: Respects Microsoft Graph API limits

### **Detailed Logging**
- **CSV Reports**: Complete processing logs for review
- **JSON Summaries**: Statistical analysis and top spam triggers
- **Real-time Feedback**: Live progress monitoring during processing

## 📁 Files Overview

### **Core Scripts**
- `msgraph_spam_test.py` - Main spam detection and management system
- `test_msgraph_connection.py` - Simple connection test to verify setup

### **Documentation**
- `MSGRAPH_SETUP.md` - Detailed Azure app registration setup guide
- `MSGRAPH_README.md` - This file

### **Generated Logs** (after running)
- `msgraph_spam_log_YYYYMMDD_HHMMSS.csv` - Detailed processing logs
- `msgraph_spam_summary_YYYYMMDD_HHMMSS.json` - Statistical summaries

## 🚀 Quick Start

### 1. **Setup Azure App Registration**
Follow the detailed guide in `MSGRAPH_SETUP.md` to:
- Create Azure app registration
- Configure API permissions
- Get your client ID and tenant ID

### 2. **Test Connection**
```bash
# Update credentials in test_msgraph_connection.py first
python test_msgraph_connection.py
```

### 3. **Run Spam Detection**
```bash
# Update credentials in msgraph_spam_test.py first
python msgraph_spam_test.py
```

## 🛡️ Protection Levels

The system applies multiple layers of protection to prevent false positives:

### **Automatic Contact Protection (-10 points)**
- All Microsoft Graph contacts automatically protected
- Domain-based protection for contact domains

### **Government/Educational (-5 to -2 points)**
- `.gov` domains: -5 points
- `.edu` domains: -2 points
- `.mil` domains: -3 points

### **Financial Institutions (-2 points)**
- Major banks and credit unions
- Investment platforms
- Payment services

### **News Organizations (-3 points)**
- Major newspapers and news sites
- Trusted journalism sources

### **Trusted Services (-1 point)**
- Major technology platforms
- Common business services

### **Manual Protection (-10 points)**
- Specific email addresses manually configured
- Highest protection level

## ⚙️ Configuration Options

### **Operating Modes**
1. **Read-only**: Detect spam without taking actions
2. **Simulation**: Show what actions would be taken
3. **Action**: Actually unsubscribe and move emails

### **Spam Threshold**
- Default: 5.0 points
- Adjustable in `SimpleSpamDetector(threshold=X.X)`

### **Batch Processing**
- Default: 50 emails per batch
- Automatic rate limiting and pausing

## 📊 Sample Output

```
🚀 Starting Microsoft Graph Spam Management System...

🔍 Microsoft Graph Spam Detection Test
==================================================
✅ SpamAssassin detected and ready
🔗 Creating Microsoft Graph interface...
🔐 Connecting to Microsoft Graph...
✅ Connected to Microsoft Graph!
📧 Account: John Doe (john.doe@company.com)

🛡️ Initializing spam detector...
   📋 Whitelist: .gov (-5), .edu (-2), .mil (-3), banks (-2), news (-3)
   👤 Personal contacts: Protected contacts (-10) - NEVER spam
   📱 Loading Microsoft Graph contacts...
   ✅ Loaded 1234 contact emails
   🛡️ All contacts automatically protected from spam detection

📬 Searching for emails...
Found 500 emails to analyze

📊 Processing 500 emails...
📧 Email 1/500
   From: newsletter@company.com
   Subject: Weekly Newsletter - Important Updates
   Result: 🚨 SPAM (Score: 6.2)
   🔍 Found 1 unsubscribe link(s)
   ✅ Unsubscribe successful
   📧 Moving email to Junk Email folder
   ✅ Successfully moved to Junk Email

📧 Email 2/500
   From: John Smith <john.smith@company.com>
   Subject: Meeting tomorrow at 2 PM
   Result: ✅ CLEAN (Score: -8.5)
   📝 Whitelist applied: Microsoft Graph contact

🎉 MICROSOFT GRAPH SPAM PROCESSING COMPLETE!
📊 Final Statistics:
   📧 Total emails processed: 500
   🚨 Spam detected: 23
   ✅ Clean emails: 477
   📈 Spam rate: 4.6%

🎯 Actions Taken:
   📧 Unsubscribe attempts: 15
   📁 Emails moved to junk: 23
```

## 🔧 Configuration

### **Custom Whitelist Domains**
Add domains to protection lists in `SimpleSpamDetector.__init__()`:

```python
self.financial_domains.add('yourbank.com')
self.trusted_services.add('yourservice.com')
```

### **Manual Contact Protection**
Add specific email addresses:

```python
self.manual_contacts.add('important@example.com')
```

### **SpamAssassin Tuning**
Adjust spam detection sensitivity:

```python
spam_detector = SimpleSpamDetector(threshold=4.0)  # More sensitive
spam_detector = SimpleSpamDetector(threshold=6.0)  # Less sensitive
```

## 🚨 Microsoft Graph vs Gmail Differences

### **Folder Structure**
- **Microsoft Graph**: Uses folders (Inbox, Junk Email, Custom folders)
- **Gmail**: Uses labels (INBOX, SPAM, custom labels)

### **Junk Handling**
- **Microsoft Graph**: Moves emails to "Junk Email" folder or creates "Spam" folder
- **Gmail**: Adds "SPAM" label and removes "INBOX" label

### **API Permissions**
- **Microsoft Graph**: Requires Azure app registration and specific Graph permissions
- **Gmail**: Uses Google OAuth with Gmail-specific scopes

### **Rate Limits**
- **Microsoft Graph**: 10,000 requests per 10 minutes per app per tenant
- **Gmail**: 1 billion quota units per day

## 🛟 Troubleshooting

### **Common Issues**

1. **Authentication Errors**
   - Verify client_id and tenant_id are correct
   - Check redirect URI matches Azure configuration
   - Ensure API permissions are granted

2. **Permission Errors**
   - Grant admin consent in Azure portal
   - Verify all required Graph permissions are added
   - Check user has appropriate mailbox access

3. **Rate Limiting**
   - System automatically handles rate limits
   - Reduce batch size if needed
   - Add longer pauses between operations

4. **Spam Detection Issues**
   - Install SpamAssassin for best results
   - Check whitelist configuration
   - Review spam threshold setting

### **Getting Help**
- Check Azure portal for app registration issues
- Review Microsoft Graph documentation
- Examine generated CSV logs for detailed error information
- Verify network connectivity and firewall settings

## 🔒 Security & Privacy

- **OAuth 2.0**: Secure authentication without storing passwords
- **Minimum Permissions**: Only requests necessary Graph API access
- **Local Processing**: All spam analysis done locally
- **Token Management**: Automatic token refresh and secure storage
- **Audit Trail**: Complete logging of all actions taken

## 📈 Future Enhancements

Potential improvements for the Microsoft Graph implementation:
- Machine learning spam classification
- Integration with Microsoft Defender
- Automatic rule learning from user actions
- phishing detection
- Integration with Microsoft Purview
- Shared mailbox support
- Exchange Online features

---

For detailed setup instructions, see `MSGRAPH_SETUP.md`.
For questions or issues, refer to the main project documentation.
