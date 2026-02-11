# Nginx HTTPS Setup for Reachy Project

## Overview

This configuration implements the security requirements from `memory-bank/requirements.md` §17:
- **TLS 1.3 only** with strong cipher suites
- **HTTPS on port 443** (HTTP on port 80 redirects to HTTPS)
- **Reverse proxy** for FastAPI gateway at `/api/*`
- **Static file serving** for videos and thumbnails
- **Security headers** (HSTS, X-Frame-Options, etc.)

## Step 1: Generate SSL Certificate

For development/testing, generate a self-signed certificate:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
chmod +x generate_ssl_cert.sh
./generate_ssl_cert.sh
```

This creates:
- `/etc/ssl/reachy/reachy.crt` - Certificate
- `/etc/ssl/reachy/reachy.key` - Private key

**For production:** Replace with CA-signed certificates (Let's Encrypt, etc.)

## Step 2: Install Nginx Configuration

```bash
# Copy the HTTPS configuration
sudo cp nginx_reachy_https.conf /etc/nginx/sites-available/reachy

# Enable the site
sudo ln -sf /etc/nginx/sites-available/reachy /etc/nginx/sites-enabled/reachy

# Disable the default site
sudo rm -f /etc/nginx/sites-enabled/default

# Test configuration
sudo nginx -t
```

Expected output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

## Step 3: Reload Nginx

```bash
sudo systemctl reload nginx
```

## Step 4: Verify HTTPS is Working

### Test health endpoint
```bash
curl -sk https://10.0.4.140/healthz
# Should return: ok

curl -sk https://localhost/healthz
# Should return: ok
```

### Test HTTP redirect
```bash
curl -I http://10.0.4.140/healthz
# Should return: 301 Moved Permanently
# Location: https://10.0.4.140/healthz
```

### Test API proxy
```bash
curl -sk https://10.0.4.140/api/health
# Should return: ok (from FastAPI gateway)
```

### Test video serving
```bash
curl -sk https://10.0.4.140/videos/temp/
# Should list videos in temp directory
```

### Test TLS version
```bash
openssl s_client -connect 10.0.4.140:443 -tls1_3 < /dev/null 2>&1 | grep "Protocol"
# Should show: Protocol  : TLSv1.3
```

## Configuration Details

### Port Mapping

| Port | Protocol | Purpose |
|------|----------|---------|
| 80   | HTTP     | Redirect to HTTPS |
| 443  | HTTPS    | Main entry point |
| 8000 | HTTP     | FastAPI gateway (internal, proxied) |
| 8501 | HTTP     | Streamlit UI (internal) |

### URL Routing

| URL Path | Backend | Purpose |
|----------|---------|---------|
| `https://10.0.4.140/healthz` | nginx | Health check |
| `https://10.0.4.140/api/*` | `http://127.0.0.1:8000` | FastAPI gateway proxy |
| `https://10.0.4.140/videos/*` | `/media/.../videos/` | Video files (static) |
| `https://10.0.4.140/thumbs/*` | `/media/.../thumbs/` | Thumbnails (static) |

### TLS Configuration

- **Protocol:** TLS 1.3 only
- **Ciphers:** 
  - `TLS_AES_256_GCM_SHA384`
  - `TLS_CHACHA20_POLY1305_SHA256`
  - `TLS_AES_128_GCM_SHA256`
- **Session cache:** 10MB shared cache
- **Session timeout:** 10 minutes
- **Session tickets:** Disabled (for forward secrecy)

### Security Headers

```
Strict-Transport-Security: max-age=31536000; includeSubDomains
X-Frame-Options: SAMEORIGIN
X-Content-Type-Options: nosniff
X-XSS-Protection: 1; mode=block
```

## Troubleshooting

### Certificate Errors

If you get certificate warnings in the browser:
- **Self-signed cert:** This is expected. Click "Advanced" → "Proceed anyway"
- **For production:** Use Let's Encrypt or a proper CA

### Permission Denied

```bash
sudo chmod 600 /etc/ssl/reachy/reachy.key
sudo chmod 644 /etc/ssl/reachy/reachy.crt
sudo chown root:root /etc/ssl/reachy/*
```

### Port 443 Already in Use

```bash
# Check what's using port 443
sudo ss -tlnp | grep :443

# If another service is using it, stop it first
sudo systemctl stop <service-name>
```

### Nginx Won't Start

```bash
# Check error logs
sudo tail -50 /var/log/nginx/error.log

# Check nginx status
sudo systemctl status nginx

# Test configuration
sudo nginx -t
```

### API Proxy Not Working

Verify FastAPI gateway is running:
```bash
curl http://localhost:8000/health
# Should return: ok

# Check gateway service
sudo systemctl status reachy-gateway.service
```

## Update Web App Configuration

The web app needs to use HTTPS URLs. Update `apps/web/.env`:

```bash
# Old (HTTP)
REACHY_GATEWAY_BASE=http://10.0.4.140:8000

# New (HTTPS via nginx)
REACHY_GATEWAY_BASE=https://10.0.4.140
```

The web app will now access:
- API: `https://10.0.4.140/api/*` (proxied to gateway)
- Videos: `https://10.0.4.140/videos/*` (served by nginx)
- Thumbnails: `https://10.0.4.140/thumbs/*` (served by nginx)

## Firewall Configuration

If using UFW:

```bash
# Allow HTTPS
sudo ufw allow 443/tcp

# Allow HTTP (for redirect)
sudo ufw allow 80/tcp

# Reload firewall
sudo ufw reload
```

## Production Considerations

### 1. Use CA-Signed Certificates

Replace self-signed cert with Let's Encrypt:

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### 2. Enable OCSP Stapling

Uncomment in nginx config:
```nginx
ssl_stapling on;
ssl_stapling_verify on;
ssl_trusted_certificate /etc/ssl/reachy/chain.pem;
```

### 3. Rate Limiting

Add to nginx config:
```nginx
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

location /api/ {
    limit_req zone=api_limit burst=20 nodelay;
    # ... rest of config
}
```

### 4. Access Logging

Enable access logs for monitoring:
```nginx
access_log /var/log/nginx/reachy_access.log combined;
error_log /var/log/nginx/reachy_error.log warn;
```

## Compliance Checklist

- ✅ TLS 1.3 only (no TLS 1.2 or earlier)
- ✅ Strong cipher suites
- ✅ HSTS header with 1-year max-age
- ✅ HTTP redirects to HTTPS
- ✅ API gateway behind reverse proxy
- ✅ Security headers (X-Frame-Options, etc.)
- ✅ Session tickets disabled
- ✅ Forward secrecy enabled

This configuration meets the requirements specified in `memory-bank/requirements.md` §17.
