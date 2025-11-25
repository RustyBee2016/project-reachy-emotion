# Reachy Gateway

The Gateway service runs on **Ubuntu 2** and provides a unified API surface for:
- The Streamlit UI (also on Ubuntu 2)
- External clients (future: mobile apps, web dashboards)
- The Jetson device (emotion events, video promotion requests)

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         Ubuntu 2                            │
│                                                             │
│  ┌──────────────┐         ┌──────────────────────────┐    │
│  │ Streamlit UI │────────▶│  Gateway (port 8000)     │    │
│  │ (port 8501)  │         │  apps/gateway/main.py    │    │
│  └──────────────┘         └──────────┬───────────────┘    │
│                                       │                     │
└───────────────────────────────────────┼─────────────────────┘
                                        │
                                        │ HTTP proxy
                                        ▼
┌─────────────────────────────────────────────────────────────┐
│                         Ubuntu 1                            │
│                                                             │
│  ┌──────────────────────────┐    ┌──────────────────────┐ │
│  │  Media Mover (port 8083) │    │  Nginx (port 8082)   │ │
│  │  apps/api/app/main.py    │    │  (static files)      │ │
│  └──────────────────────────┘    └──────────────────────┘ │
│                                                             │
│  ┌──────────────────────────┐                              │
│  │  PostgreSQL (port 5432)  │                              │
│  └──────────────────────────┘                              │
└─────────────────────────────────────────────────────────────┘
```

## Key Differences from Media Mover

| Feature | Media Mover (Ubuntu 1) | Gateway (Ubuntu 2) |
|---------|------------------------|-------------------|
| **Purpose** | Direct file operations | API proxy |
| **Storage** | `/mnt/videos` (NFS mount) | None (proxies to Ubuntu 1) |
| **Port** | 8083 | 8000 |
| **Entry Point** | `apps/api/app/main.py` | `apps/gateway/main.py` |
| **Dependencies** | Filesystem, thumbnails, DB | HTTP client only |
| **Routers** | `media_v1`, `promote`, `dialogue`, etc. | `gateway` only |

## Configuration

Configuration is loaded from environment variables with the `GATEWAY_` prefix.

### Environment Variables

See `apps/gateway/.env.template` for all available options. Key variables:

```bash
# Upstream services (Ubuntu 1)
GATEWAY_MEDIA_MOVER_URL=http://10.0.4.130:8083
GATEWAY_NGINX_MEDIA_URL=http://10.0.4.130:8082
GATEWAY_DATABASE_URL=postgresql+asyncpg://reachy_app:reachy_app@10.0.4.130:5432/reachy_local

# Gateway API
GATEWAY_API_HOST=0.0.0.0
GATEWAY_API_PORT=8000

# CORS
GATEWAY_ENABLE_CORS=true
GATEWAY_UI_ORIGINS=http://localhost:8501,http://10.0.4.140:8501
```

## Running the Gateway

### Manual Start (for testing)

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
source venv/bin/activate
./start_gateway.sh
```

### As a systemd service (production)

1. **Copy the environment template:**
   ```bash
   cp apps/gateway/.env.template apps/gateway/.env
   # Edit apps/gateway/.env with your values
   ```

2. **Install the systemd unit:**
   ```bash
   sudo cp systemd/reachy-gateway.service /etc/systemd/system/
   sudo systemctl daemon-reload
   ```

3. **Enable and start:**
   ```bash
   sudo systemctl enable reachy-gateway.service
   sudo systemctl start reachy-gateway.service
   ```

4. **Check status:**
   ```bash
   sudo systemctl status reachy-gateway.service
   sudo journalctl -u reachy-gateway.service -f
   ```

## API Endpoints

The gateway exposes the following endpoints:

### Health & Monitoring
- `GET /health` - Health check (returns "ok")
- `GET /ready` - Readiness check (returns "ready")
- `GET /metrics` - Prometheus metrics

### Emotion Events (from Jetson)
- `POST /api/events/emotion` - Receive emotion inference events
  - Requires `X-API-Version: v1` header
  - Validates against JSON schema
  - Logs events for observability

### Video Promotion (from UI or Jetson)
- `POST /api/promote` - Promote video to train/test split
  - Requires `X-API-Version: v1` and `Idempotency-Key` headers
  - Proxies to Media Mover on Ubuntu 1

### Video Operations (proxied to Media Mover)
- `GET /api/videos/{video_id}` - Get video metadata
- `GET /api/videos/{video_id}/thumb` - Get video thumbnail
- `POST /api/relabel` - Relabel a video
- `POST /api/manifest/rebuild` - Rebuild dataset manifest

## Testing

Run gateway-specific tests:

```bash
pytest tests/test_gateway_app.py -v
```

Run all tests including gateway router tests:

```bash
pytest tests/test_gateway.py tests/test_gateway_app.py -v
```

## Troubleshooting

### Gateway won't start

1. **Check configuration:**
   ```bash
   python3 -c "from apps.gateway.config import load_config; c = load_config(); print(c.log_configuration())"
   ```

2. **Check connectivity to Ubuntu 1:**
   ```bash
   curl http://10.0.4.130:8083/api/v1/healthz
   curl http://10.0.4.130:8082/
   ```

3. **Check logs:**
   ```bash
   sudo journalctl -u reachy-gateway.service -n 100 --no-pager
   ```

### Gateway returns 502/503 errors

This means the gateway is running but can't reach the Media Mover on Ubuntu 1.

1. **Verify Media Mover is running:**
   ```bash
   ssh rusty_admin@10.0.4.130 "sudo systemctl status fastapi-media.service"
   ```

2. **Check network connectivity:**
   ```bash
   ping 10.0.4.130
   telnet 10.0.4.130 8083
   ```

3. **Check firewall rules:**
   ```bash
   ssh rusty_admin@10.0.4.130 "sudo ufw status"
   ```

### CORS errors in browser

If the Streamlit UI can't reach the gateway due to CORS:

1. **Verify CORS is enabled:**
   ```bash
   grep GATEWAY_ENABLE_CORS apps/gateway/.env
   ```

2. **Verify UI origin is allowed:**
   ```bash
   grep GATEWAY_UI_ORIGINS apps/gateway/.env
   ```

3. **Restart gateway after config changes:**
   ```bash
   sudo systemctl restart reachy-gateway.service
   ```

## Development

To add new gateway endpoints:

1. Add the endpoint to `apps/api/routers/gateway.py`
2. Import and register the router in `apps/gateway/main.py` (already done)
3. Add tests to `tests/test_gateway_app.py`
4. Restart the gateway service

## Next Steps

After the gateway is running:

1. **Deploy the Streamlit UI** on Ubuntu 2 (see `apps/web/README.md`)
2. **Configure Nginx** as a reverse proxy (optional but recommended for production)
3. **Set up monitoring** (Prometheus + Grafana to scrape `/metrics`)
4. **Configure the Jetson** to send emotion events to `http://10.0.4.140:8000/api/events/emotion`
