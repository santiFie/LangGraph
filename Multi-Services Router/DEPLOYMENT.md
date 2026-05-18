# Deployment Guide - Multi-Services Router

## 🚀 Production Deployment

This guide covers deploying the Multi-Services Router to production environments.

### Prerequisites

- Docker & Docker Compose (v1.27+)
- Node.js 18+ (for MCP servers)
- Sufficient system resources:
  - **CPU**: 2+ cores
  - **RAM**: 4GB minimum
  - **Disk**: 10GB (including PDFs)

### Quick Start with Docker Compose

1. **Prepare environment**
```bash
cd "Multi-Services Router"
cp .env.example .env

# Edit .env with production values
# - Set ENVIRONMENT=production
# - Update all API keys
# - Configure WORKSPACE_PATH
```

2. **Deploy**
```bash
docker-compose up -d

# View logs
docker-compose logs -f app
```

3. **Verify deployment**
```bash
# Health check
curl http://localhost:8000/health

# API documentation
open http://localhost:8000/docs
```

### Environment Configuration for Production

Critical settings in `.env`:

```bash
# Security
ENVIRONMENT=production
DEBUG=false

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Database
CHECKPOINT_DB=/data/checkpoint.db
DATABASE_URL=sqlite+aiosqlite:////data/checkpoint.db

# Logging
LOG_LEVEL=INFO

# Limits
# Max concurrent requests (requires reverse proxy)
```

### Reverse Proxy Setup (Nginx)

```nginx
upstream app {
    server app:8000;
}

server {
    listen 80;
    server_name api.example.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;

    ssl_certificate /etc/ssl/certs/cert.pem;
    ssl_certificate_key /etc/ssl/private/key.pem;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=general:10m rate=100r/m;
    limit_req zone=general burst=20 nodelay;

    location / {
        proxy_pass http://app;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Stream support for FastAPI SSE
    location /supervisor/stream {
        proxy_pass http://app;
        proxy_buffering off;
        proxy_set_header Connection "";
        proxy_http_version 1.1;
    }
}
```

### Kubernetes Deployment

Example YAML for Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: multi-services-router
  labels:
    app: router
spec:
  replicas: 3
  selector:
    matchLabels:
      app: router
  template:
    metadata:
      labels:
        app: router
    spec:
      containers:
      - name: app
        image: multi-services-router:latest
        ports:
        - containerPort: 8000
        env:
        - name: ENVIRONMENT
          value: "production"
        - name: SERVER_HOST
          value: "0.0.0.0"
        - name: CHECKPOINT_DB
          value: "/data/checkpoint.db"
        volumeMounts:
        - name: data
          mountPath: /data
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 10
          periodSeconds: 5
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: router-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: multi-services-router
spec:
  selector:
    app: router
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Monitoring and Logging

#### Application Logs

Local:
```bash
docker-compose logs -f app
```

Production:
```bash
# View logs from container
docker logs -f multi-services-router

# Export logs
docker logs multi-services-router > app.log
```

#### Health Monitoring

```bash
# Set up monitoring with curl and cron
*/5 * * * * curl -f http://localhost:8000/health || send_alert
```

#### Database Maintenance

```bash
# Backup checkpoint database
docker exec multi-services-router cp /app/checkpoint.db /app/checkpoint.backup

# Restore
docker exec multi-services-router cp /app/checkpoint.backup /app/checkpoint.db
```

### Scaling Considerations

#### Horizontal Scaling

- Use load balancer (AWS ALB, GCP Load Balancer, etc.)
- Ensure each instance has independent checkpoint database
- Consider shared database backend for state management

```bash
# Example: Multiple instances with load balancer
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Scale to 3 instances
docker-compose up -d --scale app=3
```

#### Vertical Scaling

Adjust in Docker Compose:
```yaml
resources:
  limits:
    cpus: '2'
    memory: 4G
  reservations:
    cpus: '1'
    memory: 2G
```

### Security Best Practices

1. **Environment Variables**
   - Never commit `.env` to version control
   - Use secret management (AWS Secrets Manager, HashiCorp Vault)
   - Rotate API keys regularly

2. **Network Security**
   - Use HTTPS/TLS only
   - Implement rate limiting
   - Use VPN for private deployments
   - Restrict database access

3. **API Security**
   - Implement API key authentication
   - Use JWT tokens for session management
   - Enable CORS only for trusted domains
   - Add request validation

4. **Data Protection**
   - Encrypt data at rest (database)
   - Encrypt data in transit (TLS)
   - Regular backups
   - Monitor access logs

### Troubleshooting Deployment

**Container won't start**
```bash
docker-compose logs app
docker-compose logs --tail=50 app
```

**Permission denied errors**
```bash
# Check file permissions
docker exec multi-services-router ls -la /app

# Fix permissions
docker exec multi-services-router chmod 755 /app
```

**Out of memory**
```bash
# Monitor usage
docker stats multi-services-router

# Increase limits in docker-compose.yml
```

**Database locked**
```bash
# Restart application
docker-compose restart app

# Or remove and recreate
docker-compose down
docker-compose up -d
```

### Rollback Procedure

```bash
# Save current state
docker exec multi-services-router cp /app/checkpoint.db /backup/

# Restore previous version
docker-compose down
docker-compose pull  # Get previous tag
docker-compose up -d
```

### Performance Tuning

```bash
# Increase uvicorn workers
WORKERS=4 docker-compose up -d

# Enable HTTP/2
# Configure in docker-compose.yml environment
```

---

For more information, see [README.md](./README.md) and [Troubleshooting](#).
