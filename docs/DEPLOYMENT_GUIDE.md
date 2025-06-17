# Asset Document Management System Deployment Guide

Comprehensive deployment guide for the **Memory-Driven Asset Document Processing Agent** production environment.

## 📋 **System Requirements**

### **Minimum Requirements**
- **CPU**: 4 cores (8 recommended for parallel processing)
- **RAM**: 8GB minimum (16GB recommended)
- **Storage**: 50GB+ for documents and vector database
- **Network**: Stable internet for email API access
- **OS**: Linux (Ubuntu 22.04 LTS recommended), macOS, or Windows

### **Production Requirements**
- **CPU**: 8+ cores for high-throughput processing
- **RAM**: 32GB+ for large-scale document processing
- **Storage**: 500GB+ SSD for optimal Qdrant performance
- **Network**: High-speed connection for email processing
- **Backup**: Automated backup strategy for assets and memory

### **Required Services**
- **Qdrant Vector Database** (required for memory-driven learning)
- **Gmail API** credentials (for Gmail processing)
- **Microsoft Graph API** credentials (for M365 processing)
- **ClamAV** (recommended for antivirus scanning)
- **Redis** (optional - for caching and job queues)

## 🚀 **Quick Start Deployment**

### **1. System Setup**
```bash
# Clone repository
git clone <your-repo-url> asset-document-agent
cd asset-document-agent

# Create virtual environment
python3 -m venv .emailagent
source .emailagent/bin/activate  # On Windows: .emailagent\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # For development
```

### **2. Vector Database Setup**
```bash
# Option 1: Docker (Recommended)
docker run -d \
  --name qdrant \
  -p 6333:6333 \
  -v qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Option 2: Docker Compose (Full stack)
docker-compose up -d qdrant

# Verify Qdrant is running
curl http://localhost:6333/health
```

### **3. Configuration**
```bash
# Copy configuration template
cp config/config.yaml.example config/config.yaml

# Edit configuration with your settings
nano config/config.yaml
```

### **4. Initialize System**
```bash
# Test configuration
python -c "from src.utils.config import config; print('✅ Configuration loaded')"

# Initialize Qdrant collections
python -c "
from src.agents.asset_document_agent import AssetDocumentAgent
import asyncio

async def init():
    agent = AssetDocumentAgent()
    await agent.initialize_collections()
    print('✅ Collections initialized')

asyncio.run(init())
"

# Start web interface
python -m src.web_ui.app
```

## 🔧 **Production Configuration**

### **config/config.yaml**
```yaml
# Production configuration
environment: production

# Email interface configuration
email_interface:
  gmail:
    credentials_file: "${GMAIL_CREDENTIALS_FILE}"
    token_file: "${GMAIL_TOKEN_FILE}"
    scopes:
      - "https://www.googleapis.com/auth/gmail.readonly"
      - "https://www.googleapis.com/auth/gmail.modify"

  msgraph:
    client_id: "${MSGRAPH_CLIENT_ID}"
    client_secret: "${MSGRAPH_CLIENT_SECRET}"
    tenant_id: "${MSGRAPH_TENANT_ID}"
    redirect_uri: "${MSGRAPH_REDIRECT_URI}"

# Asset processing configuration
asset_processing:
  base_assets_path: "/opt/asset-documents/assets"
  max_attachment_size_mb: 25
  allowed_extensions: [".pdf", ".xlsx", ".xls", ".doc", ".docx", ".pptx", ".jpg", ".png", ".dwg"]
  low_confidence_threshold: 0.4

  # Parallel processing for production
  max_concurrent_emails: 10
  max_concurrent_attachments: 20
  batch_size: 50

# Qdrant vector database
qdrant:
  host: "${QDRANT_HOST:localhost}"
  port: "${QDRANT_PORT:6333}"
  timeout: 30

# Memory system configuration
memory:
  auto_learning_threshold: 0.75
  similarity_threshold: 0.8
  pattern_retention_days: 365
  max_patterns_per_collection: 100000

# Security configuration
security:
  clamav_enabled: true
  quarantine_path: "/opt/asset-documents/quarantine"
  max_file_size_mb: 25

# Logging configuration
logging:
  level: "${LOG_LEVEL:INFO}"
  file: "/var/log/asset-document-agent/app.log"
  max_size_mb: 100
  backup_count: 10

# Web interface
web_ui:
  host: "0.0.0.0"
  port: 5000
  secret_key: "${FLASK_SECRET_KEY}"
  debug: false
```

### **Environment Variables**
```bash
# Required environment variables
export GMAIL_CREDENTIALS_FILE="/opt/asset-documents/config/gmail_credentials.json"
export GMAIL_TOKEN_FILE="/opt/asset-documents/config/gmail_token.json"
export MSGRAPH_CLIENT_ID="your-msgraph-client-id"
export MSGRAPH_CLIENT_SECRET="your-msgraph-client-secret"
export MSGRAPH_TENANT_ID="your-tenant-id"
export MSGRAPH_REDIRECT_URI="https://your-domain.com/auth/callback"

# Security
export FLASK_SECRET_KEY="your-very-secure-secret-key-here"

# Optional
export QDRANT_HOST="localhost"
export QDRANT_PORT="6333"
export LOG_LEVEL="INFO"
```

## 🐳 **Docker Deployment**

### **Complete Docker Compose Stack**
```yaml
# docker-compose.yml
version: '3.8'

services:
  asset-document-agent:
    build:
      context: .
      dockerfile: Dockerfile.production
    ports:
      - "5000:5000"
    volumes:
      - ./config:/app/config:ro
      - ./assets:/app/assets
      - ./logs:/app/logs
      - quarantine_data:/app/quarantine
    environment:
      - FLASK_ENV=production
      - FLASK_SECRET_KEY=${FLASK_SECRET_KEY}
      - QDRANT_HOST=qdrant
      - QDRANT_PORT=6333
    depends_on:
      - qdrant
      - redis
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  qdrant:
    image: qdrant/qdrant:v1.7.4
    ports:
      - "6333:6333"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__HTTP_PORT=6333
      - QDRANT__SERVICE__GRPC_PORT=6334
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6333/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - asset-document-agent
    restart: unless-stopped

volumes:
  qdrant_data:
  redis_data:
  quarantine_data:
```

### **Production Dockerfile**
```dockerfile
# Dockerfile.production
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    clamav \
    clamav-daemon \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Update ClamAV signatures
RUN freshclam

# Create app user
RUN useradd --create-home --shell /bin/bash app

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt requirements-prod.txt ./
RUN pip install --no-cache-dir -r requirements-prod.txt

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p /app/assets /app/logs /app/quarantine \
    && chown -R app:app /app

# Switch to app user
USER app

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:5000/api/health || exit 1

# Start application
CMD ["python", "-m", "src.web_ui.app"]
```

## ☁️ **Cloud Deployment Options**

### **AWS EC2 Deployment**

#### **1. Launch EC2 Instance**
```bash
# Recommended instance type: t3.xlarge or m5.xlarge
# AMI: Ubuntu 22.04 LTS
# Storage: 100GB+ gp3 SSD
# Security groups: Allow 22 (SSH), 80 (HTTP), 443 (HTTPS)
```

#### **2. Instance Setup**
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install additional dependencies
sudo apt install -y nginx certbot python3-certbot-nginx
```

#### **3. Deploy Application**
```bash
# Clone and setup
git clone <repo-url> /opt/asset-document-agent
cd /opt/asset-document-agent

# Copy environment configuration
cp docker-compose.yml.production docker-compose.yml
cp .env.example .env

# Edit configuration
sudo nano .env

# Deploy with Docker Compose
docker-compose up -d

# Setup SSL with Let's Encrypt
sudo certbot --nginx -d your-domain.com
```

#### **4. Configure Auto-Startup**
```bash
# Create systemd service for docker-compose
sudo tee /etc/systemd/system/asset-document-agent.service << EOF
[Unit]
Description=Asset Document Management System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/asset-document-agent
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl enable asset-document-agent
sudo systemctl start asset-document-agent
```

### **Azure Container Instances**

```bash
# Create resource group
az group create --name AssetDocumentAgent --location eastus

# Create container registry
az acr create --resource-group AssetDocumentAgent \
  --name assetdocagentregistry --sku Basic

# Build and push image
az acr build --registry assetdocagentregistry \
  --image asset-document-agent:latest .

# Deploy container group
az container create \
  --resource-group AssetDocumentAgent \
  --name asset-document-agent \
  --image assetdocagentregistry.azurecr.io/asset-document-agent:latest \
  --cpu 4 --memory 8 \
  --ports 5000 \
  --environment-variables \
    FLASK_ENV=production \
    QDRANT_HOST=qdrant-server.eastus.azurecontainer.io
```

### **Google Cloud Run**

```bash
# Build and push to Google Container Registry
gcloud builds submit --tag gcr.io/PROJECT-ID/asset-document-agent

# Deploy to Cloud Run
gcloud run deploy asset-document-agent \
  --image gcr.io/PROJECT-ID/asset-document-agent \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --memory 4Gi \
  --cpu 2 \
  --set-env-vars FLASK_ENV=production
```

## 🔒 **Security Hardening**

### **Application Security**
```bash
# Create secure credential storage
sudo mkdir -p /opt/asset-documents/config
sudo chmod 600 /opt/asset-documents/config
sudo chown app:app /opt/asset-documents/config

# Setup SSL/TLS
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com

# Configure firewall
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw enable
```

### **Nginx Security Configuration**
```nginx
# /etc/nginx/sites-available/asset-document-agent
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL configuration
    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;

    # Security headers
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options DENY;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload";

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;

    # File upload limits
    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # API rate limiting
    location /api/ {
        limit_req zone=api burst=10 nodelay;
        proxy_pass http://127.0.0.1:5000;
        # ... other proxy settings
    }
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}
```

### **Database Security**
```yaml
# Qdrant security configuration
# qdrant-config.yaml
storage:
  storage_path: "/qdrant/storage"

service:
  http_port: 6333
  grpc_port: 6334
  enable_cors: false

# Enable authentication in production
cluster:
  enabled: false

# Production optimizations
optimizer:
  deleted_threshold: 0.2
  vacuum_min_vector_number: 1000
  default_segment_number: 0
```

## 📊 **Monitoring and Observability**

### **Health Monitoring**
```bash
# Application health check endpoint
curl https://your-domain.com/api/health

# Detailed system status
curl https://your-domain.com/api/system-status

# Processing statistics
curl https://your-domain.com/api/processing-stats
```

### **Logging Configuration**
```python
# Enhanced logging configuration
# config/logging.yaml
version: 1
disable_existing_loggers: False

formatters:
  detailed:
    format: '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
  json:
    '()': 'src.utils.logging_system.JSONFormatter'

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: detailed
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: INFO
    formatter: json
    filename: /var/log/asset-document-agent/app.log
    maxBytes: 104857600  # 100MB
    backupCount: 10

  error_file:
    class: logging.handlers.RotatingFileHandler
    level: ERROR
    formatter: detailed
    filename: /var/log/asset-document-agent/error.log
    maxBytes: 10485760  # 10MB
    backupCount: 5

loggers:
  src:
    level: INFO
    handlers: [console, file]
    propagate: no

  src.agents.asset_document_agent:
    level: DEBUG
    handlers: [file, error_file]
    propagate: no

root:
  level: INFO
  handlers: [console, file]
```

### **Prometheus Metrics (Optional)**
```python
# Add to src/web_ui/app.py
from prometheus_client import Counter, Histogram, generate_latest

# Metrics
emails_processed = Counter('emails_processed_total', 'Total emails processed')
processing_time = Histogram('processing_time_seconds', 'Time spent processing emails')
classification_confidence = Histogram('classification_confidence', 'Classification confidence scores')

@app.route('/metrics')
def metrics():
    return generate_latest()
```

## 🗄️ **Backup and Disaster Recovery**

### **Automated Backup Strategy**
```bash
#!/bin/bash
# backup.sh - Daily backup script

BACKUP_DIR="/opt/backups/asset-document-agent"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_PATH="$BACKUP_DIR/$DATE"

mkdir -p "$BACKUP_PATH"

# Backup Qdrant data
docker exec qdrant tar -czf - /qdrant/storage > "$BACKUP_PATH/qdrant_$DATE.tar.gz"

# Backup application configuration
tar -czf "$BACKUP_PATH/config_$DATE.tar.gz" /opt/asset-documents/config/

# Backup processed assets
rsync -av /opt/asset-documents/assets/ "$BACKUP_PATH/assets/"

# Backup application logs
tar -czf "$BACKUP_PATH/logs_$DATE.tar.gz" /var/log/asset-document-agent/

# Upload to cloud storage (AWS S3 example)
aws s3 sync "$BACKUP_PATH" "s3://your-backup-bucket/asset-document-agent/$DATE/"

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -type d -mtime +30 -exec rm -rf {} \;

echo "Backup completed: $BACKUP_PATH"
```

### **Crontab Configuration**
```bash
# Add to crontab
crontab -e

# Daily backup at 2 AM
0 2 * * * /opt/asset-documents/scripts/backup.sh

# Weekly Qdrant optimization
0 3 * * 0 curl -X POST http://localhost:6333/collections/asset_management_assets/optimize

# Monthly log rotation
0 1 1 * * find /var/log/asset-document-agent -name "*.log" -mtime +30 -delete
```

### **Disaster Recovery Plan**
```bash
#!/bin/bash
# restore.sh - Disaster recovery script

BACKUP_DATE=$1
BACKUP_PATH="/opt/backups/asset-document-agent/$BACKUP_DATE"

if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 <backup_date>"
    exit 1
fi

# Stop services
docker-compose down

# Restore Qdrant data
docker run --rm -v qdrant_data:/qdrant/storage -v "$BACKUP_PATH":/backup \
    ubuntu tar -xzf /backup/qdrant_$BACKUP_DATE.tar.gz -C /

# Restore configuration
tar -xzf "$BACKUP_PATH/config_$BACKUP_DATE.tar.gz" -C /

# Restore assets
rsync -av "$BACKUP_PATH/assets/" /opt/asset-documents/assets/

# Start services
docker-compose up -d

echo "Restore completed from backup: $BACKUP_DATE"
```

## ⚡ **Performance Optimization**

### **Production Tuning**
```yaml
# High-performance configuration
asset_processing:
  max_concurrent_emails: 20
  max_concurrent_attachments: 40
  batch_size: 100

  # Memory optimization
  max_memory_per_process: "2GB"
  gc_threshold: 1000

# Qdrant optimization
qdrant:
  # Connection pooling
  max_connections: 20
  connection_timeout: 30

  # Performance settings
  max_search_limit: 10000
  default_segment_number: 8
```

### **System Monitoring**
```bash
# Monitor system resources
htop

# Monitor Qdrant performance
curl http://localhost:6333/metrics

# Monitor application memory
docker stats asset-document-agent

# Monitor processing queue
curl https://your-domain.com/api/processing-queue-status
```

## 🐛 **Troubleshooting**

### **Common Issues and Solutions**

#### **Qdrant Connection Issues**
```bash
# Check Qdrant health
curl http://localhost:6333/health

# Check collections
curl http://localhost:6333/collections

# Restart Qdrant
docker restart qdrant

# Check logs
docker logs qdrant
```

#### **Email Authentication Issues**
```bash
# Test Gmail connection
python -c "
from src.email_interface.gmail import GmailInterface
import asyncio

async def test():
    interface = GmailInterface()
    try:
        await interface.connect({'credentials_file': 'config/gmail_credentials.json'})
        print('✅ Gmail connection successful')
    except Exception as e:
        print(f'❌ Gmail connection failed: {e}')

asyncio.run(test())
"

# Test Microsoft Graph connection
python -c "
from src.email_interface.msgraph import MicrosoftGraphInterface
import asyncio

async def test():
    interface = MicrosoftGraphInterface()
    creds = {
        'client_id': 'your-client-id',
        'tenant_id': 'your-tenant-id'
    }
    try:
        await interface.connect(creds)
        print('✅ Microsoft Graph connection successful')
    except Exception as e:
        print(f'❌ Microsoft Graph connection failed: {e}')

asyncio.run(test())
"
```

#### **Memory Issues**
```bash
# Check memory usage
free -h

# Check for memory leaks
python -m memory_profiler src/web_ui/app.py

# Restart services if needed
docker-compose restart asset-document-agent
```

#### **Storage Issues**
```bash
# Check disk space
df -h

# Check asset storage usage
du -sh /opt/asset-documents/assets/

# Clean up old logs
find /var/log/asset-document-agent -name "*.log.*" -mtime +7 -delete

# Optimize Qdrant storage
curl -X POST http://localhost:6333/collections/asset_management_assets/optimize
```

### **Debug Mode Deployment**
```bash
# Enable debug mode temporarily
export LOG_LEVEL=DEBUG
export FLASK_DEBUG=true

# Restart with debug logging
docker-compose restart asset-document-agent

# View real-time logs
docker-compose logs -f asset-document-agent
```

## 📞 **Production Support**

### **Monitoring Checklist**
- [ ] Application health endpoint responding
- [ ] Qdrant database accessible and optimized
- [ ] Email authentication working
- [ ] Processing queue not backed up
- [ ] Disk space sufficient (>20% free)
- [ ] Memory usage within limits (<80%)
- [ ] SSL certificate valid
- [ ] Backups completing successfully
- [ ] Log rotation working
- [ ] Security updates applied

### **Support Contacts**
- **Application Logs**: `/var/log/asset-document-agent/app.log`
- **Error Logs**: `/var/log/asset-document-agent/error.log`
- **System Status**: `https://your-domain.com/api/system-status`
- **Documentation**: `https://your-domain.com/docs`

### **Emergency Procedures**
```bash
# Emergency shutdown
docker-compose down

# Emergency backup
./backup.sh

# Emergency restore
./restore.sh BACKUP_DATE

# Reset learning system (if needed)
python -c "
from src.memory.procedural import ProceduralMemory
import asyncio

async def reset():
    memory = ProceduralMemory()
    await memory.reset_all_patterns()
    print('Memory system reset complete')

asyncio.run(reset())
"
```

---

**🎉 Your Asset Document Management System is now production-ready!**

The system is designed for high availability, scalability, and reliable document processing with comprehensive monitoring and disaster recovery capabilities.
