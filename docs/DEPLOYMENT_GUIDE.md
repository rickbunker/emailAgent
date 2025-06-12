# Email Agent Deployment Guide

This guide covers deploying the Email Agent system for production use.

## 📋 Prerequisites

### System Requirements
- **Python 3.8+** (3.11 recommended)
- **4GB+ RAM** (for AI processing)
- **Storage**: 10GB+ for processing artifacts
- **Network**: Stable internet for email API access

### Required Services
- **Gmail API** credentials (for Gmail processing)
- **Microsoft Graph API** credentials (for M365 processing)
- **Qdrant** (optional - for enhanced document matching)

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <your-repo-url> emailAgent
cd emailAgent

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
# Copy environment template
cp config/environment.template .env

# Edit .env with your settings
nano .env
```

### 3. Setup Credentials
```bash
# Place your credential files in config/
# - config/gmail_credentials.json
# - config/msgraph_credentials.json
```

### 4. Initialize and Run
```bash
# Test configuration
python -c "from src.utils.config import config; print('✅ Configuration loaded successfully')"

# Run the application
python app.py
```

## 🔧 Configuration

### Environment Variables

**Required:**
- `GMAIL_CREDENTIALS_PATH` - Path to Gmail OAuth credentials
- `MSGRAPH_CREDENTIALS_PATH` - Path to Microsoft Graph credentials
- `FLASK_SECRET_KEY` - Strong secret key for Flask sessions

**Optional (with defaults):**
- `FLASK_PORT=5000` - Web interface port
- `LOG_LEVEL=INFO` - Logging level
- `DEFAULT_HOURS_BACK=24` - Email processing window

See `config/environment.template` for full list.

### Credential Setup

#### Gmail API
1. Create project in [Google Cloud Console](https://console.cloud.google.com/)
2. Enable Gmail API
3. Create OAuth 2.0 credentials
4. Download as `config/gmail_credentials.json`
5. Run first-time authentication to generate token

#### Microsoft Graph API
1. Register app in [Azure Portal](https://portal.azure.com/)
2. Configure Mail.Read permissions
3. Create client secret
4. Save credentials as `config/msgraph_credentials.json`:
```json
{
    "client_id": "your-client-id",
    "client_secret": "your-client-secret",
    "tenant_id": "your-tenant-id"
}
```

## 🐳 Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 5000

CMD ["python", "app.py"]
```

### Docker Compose
```yaml
version: '3.8'
services:
  email-agent:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs
      - ./assets:/app/assets
    environment:
      - FLASK_ENV=production
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
    depends_on:
      - qdrant

  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage

volumes:
  qdrant_data:
```

## ☁️ Cloud Deployment

### AWS EC2 / DigitalOcean / VPS

1. **Launch Instance**
   - Ubuntu 22.04 LTS
   - 4GB+ RAM recommended
   - Open ports 80, 443, 5000

2. **Install Dependencies**
   ```bash
   sudo apt update
   sudo apt install python3 python3-pip python3-venv nginx
   ```

3. **Deploy Application**
   ```bash
   git clone <repo> /opt/emailAgent
   cd /opt/emailAgent
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

4. **Configure Systemd Service**
   ```bash
   sudo tee /etc/systemd/system/email-agent.service << EOF
   [Unit]
   Description=Email Agent Service
   After=network.target

   [Service]
   Type=simple
   User=ubuntu
   WorkingDirectory=/opt/emailAgent
   Environment=PATH=/opt/emailAgent/.venv/bin
   ExecStart=/opt/emailAgent/.venv/bin/python app.py
   Restart=always

   [Install]
   WantedBy=multi-user.target
   EOF

   sudo systemctl enable email-agent
   sudo systemctl start email-agent
   ```

5. **Configure Nginx**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://127.0.0.1:5000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

### Heroku Deployment

1. **Create Heroku App**
   ```bash
   heroku create your-email-agent
   ```

2. **Configure Environment**
   ```bash
   heroku config:set FLASK_ENV=production
   heroku config:set FLASK_SECRET_KEY=your-secret-key
   ```

3. **Deploy**
   ```bash
   git push heroku main
   ```

## 🔒 Security Considerations

### Production Security
- **Change default secret key** in production
- **Use HTTPS** for web interface
- **Restrict file uploads** by size and type
- **Enable virus scanning** if ClamAV available
- **Regular credential rotation**

### Network Security
- **Firewall configuration** (only necessary ports)
- **VPN access** for admin interface
- **Rate limiting** on API endpoints

### Data Protection
- **Encrypt credential files** at rest
- **Secure backup strategy** for processed documents
- **Log rotation** and secure storage
- **Regular security updates**

## 📊 Monitoring & Maintenance

### Health Checks
```bash
# Check service status
curl http://localhost:5000/api/health

# Check logs
tail -f logs/email_agent.log

# Check processing history
curl http://localhost:5000/api/processing-history
```

### Backup Strategy
```bash
# Backup credentials
tar -czf backup-$(date +%Y%m%d).tar.gz config/ assets/

# Backup processed documents
rsync -av processed_attachments/ backup/processed_attachments/
```

### Updates
```bash
# Update application
git pull origin main
pip install -r requirements.txt

# Restart service
sudo systemctl restart email-agent
```

## 🐛 Troubleshooting

### Common Issues

**Authentication Errors:**
- Check credential file paths in `.env`
- Verify API permissions in cloud consoles
- Check token expiration

**Processing Failures:**
- Check log files for detailed errors
- Verify Qdrant connection (if used)
- Check disk space for attachments

**Performance Issues:**
- Monitor RAM usage during processing
- Adjust `MAX_EMAILS_PER_BATCH` if needed
- Consider adding more storage

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
export DEBUG=true

# Run with verbose output
python app.py
```

## 📞 Support

For issues and questions:
1. Check logs: `logs/email_agent.log`
2. Review configuration: `src/utils/config.py`
3. Test credentials: `tests/test_msgraph_connection.py`

---

**🎉 Your Email Agent is now production-ready!**
