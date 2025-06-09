# Gmail API Setup Guide

Follow these steps to set up Gmail API access for spam detection testing.

## 📋 **Step-by-Step Setup**

### 1. **Google Cloud Console Setup**

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Sign in with your Google account
3. **Create a new project** or select an existing one:
   - Click the project dropdown at the top
   - Click "New Project"
   - Name it something like "Email Agent Gmail"
   - Click "Create"

### 2. **Enable Gmail API**

1. In your project, go to **APIs & Services** → **Library**
2. Search for "Gmail API"
3. Click on **Gmail API**
4. Click **Enable**

### 3. **Create OAuth 2.0 Credentials**

1. Go to **APIs & Services** → **Credentials**
2. Click **+ Create Credentials** → **OAuth 2.0 Client IDs**
3. If prompted, configure the OAuth consent screen first:
   - Choose **External** (unless you have a Google Workspace account)
   - Fill in the required fields:
     - App name: "Email Agent"
     - User support email: Your email
     - Developer contact: Your email
   - Click **Save and Continue**
   - Add scopes: You can skip this for now
   - Add test users: Add your own email address
   - Click **Save and Continue**

4. Create the OAuth 2.0 Client ID:
   - Application type: **Desktop application**
   - Name: "Email Agent Desktop"
   - Click **Create**

### 4. **Download Credentials**

1. After creating, you'll see a popup with your credentials
2. Click **Download JSON**
3. Save the file as `gmail_credentials.json` in the `examples/` directory of your project

### 5. **Test the Setup**

Run the test script:

```bash
cd /Users/richardbunker/python/emailAgent
python examples/gmail_spam_test.py
```

## 🔐 **First-Time Authentication**

When you run the script for the first time:

1. **Browser will open automatically** showing Google's OAuth consent screen
2. **Sign in** with your Gmail account
3. **Grant permissions** for the Email Agent to access your Gmail
4. The browser will show "The authentication flow has completed"
5. You can close the browser - the script will continue automatically

A `gmail_token.json` file will be created to store your authentication token for future use.

## 🔍 **What the Test Script Does**

The spam detection test script will:

1. ✅ Connect to your Gmail account (read-only)
2. 📬 Fetch your 20 most recent emails from the last 30 days
3. 🛡️ Run each email through SpamAssassin spam detection
4. 📊 Show results for each email:
   - Sender and subject
   - Spam score
   - Whether it's classified as spam
   - Which spam rules were triggered
5. 📈 Provide a summary with spam detection statistics

**🚨 Important**: The script is **READ-ONLY** - it will not modify, delete, or mark any emails.

## 🛠️ **Troubleshooting**

### **"credentials.json not found"**
- Make sure you downloaded the OAuth credentials JSON file
- Rename it to exactly `gmail_credentials.json`
- Place it in the `examples/` directory

### **"Access blocked: This app's request is invalid"**
- Make sure you enabled the Gmail API in your project
- Check that you created OAuth 2.0 credentials (not API key or service account)
- Ensure you selected "Desktop application" as the application type

### **"This app isn't verified"**
- This is normal for development - click "Advanced" then "Go to Email Agent (unsafe)"
- For production use, you'd need to verify your app with Google

### **"insufficient authentication scopes"**
- The script requests the minimum required scopes automatically
- If this persists, delete `gmail_token.json` and re-authenticate

### **"SpamAssassin not found"**
- Make sure SpamAssassin is installed: `brew install spamassassin` (macOS)
- Or follow the installation guide in the main README

## 📁 **Files Created**

After setup, you'll have:
- `examples/gmail_credentials.json` - Your OAuth credentials (keep private!)
- `examples/gmail_token.json` - Authentication token (auto-generated)

## 🔒 **Security Notes**

- **Never commit** `gmail_credentials.json` or `gmail_token.json` to version control
- The credentials file contains your OAuth client secret
- The token file allows access to your Gmail account
- Both files should be kept secure and private

---

Ready to test spam detection on your real Gmail account! 🚀 