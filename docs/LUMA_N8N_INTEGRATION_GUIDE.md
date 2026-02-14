# Luma AI & n8n Integration Guide
## Reachy Emotion Recognition Project (v08.4.2)

**Last Updated**: 2025-11-10  
**Author**: Russell Bray

---

## Overview

This guide explains how to integrate Luma AI video generation with the Reachy web app and configure the n8n Agent 1 - Ingest workflow to process generated videos.

### Architecture Flow

```
Web App (Ubuntu 2) → Luma AI API → Download to /videos/temp/ → n8n Webhook → Agent 1 Ingest
```

1. **User enters prompt** in web app landing page
2. **Web app calls Luma AI** Dream Machine API (Ray 2 model)
3. **Video is generated** and polled until complete (~1-2 minutes)
4. **Video is downloaded** to `/media/rusty_admin/project_data/reachy_emotion/videos/temp/`
5. **HTTP POST sent** to n8n webhook with video path
6. **Agent 1 - Ingest** processes the video (checksum, metadata, database insert)

---

## Prerequisites

- **Luma AI API Key**: Get from [https://lumalabs.ai/dream-machine/api/keys](https://lumalabs.ai/dream-machine/api/keys)
- **n8n Instance**: Running on Ubuntu 1 (10.0.4.130:5678)
- **Agent 1 - Ingest Workflow**: Imported and activated in n8n
- **Python Environment**: Python 3.10+ with required packages

---

## Part 1: Web App Configuration

### Step 1: Install Dependencies

Navigate to the web app directory and install the Luma AI SDK:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2/apps/web
pip install lumaai>=1.0
```

Or install all requirements:

```bash
pip install -r requirements.txt
```

### Step 2: Configure Environment Variables

Create a `.env` file in `/home/rusty_admin/projects/reachy_08.4.2/apps/web/`:

```bash
cp .env.example .env
nano .env
```

Add your API keys and configuration:

```env
# Luma AI Configuration
LUMAAI_API_KEY=luma-56be55b6-bb5f-4c9d-a3a1-417442d20a50-67f0b180-4b9f-4bfd-963f-74132bd60ef3

# n8n Configuration
N8N_HOST=10.0.4.130
N8N_PORT=5678
N8N_INGEST_TOKEN=your_secure_token_here
```

**Security Note**: 
- The `.env` file is gitignored and will not be committed
- Store sensitive keys securely
- Use different tokens for development and production

### Step 3: Verify Directory Permissions

Ensure the web app can write to the temp directory:

```bash
sudo mkdir -p /media/rusty_admin/project_data/reachy_emotion/videos/temp
sudo chown -R rusty_admin:rusty_admin /media/rusty_admin/project_data/reachy_emotion/videos/
sudo chmod -R 755 /media/rusty_admin/project_data/reachy_emotion/videos/
```

### Step 4: Test the Web App

Run the Streamlit app:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2/apps/web
streamlit run landing_page.py
```

Access at: `http://10.0.4.140:8501`

---

## Part 2: n8n Webhook Configuration

### Understanding Agent 1 - Ingest Workflow

The workflow starts with a **Webhook Trigger** node that accepts HTTP POST requests.

#### Webhook Node Configuration

From the workflow JSON (`01_ingest_agent.json`):

```json
{
  "name": "Webhook: ingest.video",
  "type": "n8n-nodes-base.webhook",
  "parameters": {
    "httpMethod": "POST",
    "path": "video_gen_hook",
    "responseMode": "onReceived",
    "options": {
      "responseCode": 202
    }
  }
}
```

**Key Details**:
- **Path**: `video_gen_hook`
- **Method**: POST
- **Response**: 202 Accepted (immediate response)
- **Authentication**: `x-ingest-key` header

### Step 1: Import the Workflow

1. Open n8n at `http://10.0.4.130:5678`
2. Click **Workflows** → **Import from File**
3. Select `/home/rusty_admin/projects/reachy_08.4.2/n8n/workflows/01_ingest_agent.json`
4. Click **Import**

### Step 2: Configure Environment Variables in n8n

The workflow uses these environment variables:

```bash
# In n8n settings or docker-compose.yml
INGEST_TOKEN=your_secure_token_here
MEDIA_MOVER_BASE_URL=http://10.0.4.130:8083
GATEWAY_BASE_URL=http://10.0.4.140:8000
```

**To set in docker-compose.yml**:

```yaml
services:
  n8n:
    environment:
      - INGEST_TOKEN=your_secure_token_here
      - MEDIA_MOVER_BASE_URL=http://10.0.4.130:8083
      - GATEWAY_BASE_URL=http://10.0.4.140:8000
```

### Step 3: Configure Credentials

The workflow requires two credentials:

#### 1. HTTP Header Auth (Media Mover)
- **Name**: `Media Mover Auth`
- **Type**: HTTP Header Auth
- **Header Name**: `Authorization`
- **Value**: `Bearer your_media_mover_token`

#### 2. PostgreSQL Connection
- **Name**: `PostgreSQL - reachy_local`
- **Host**: `10.0.4.130`
- **Database**: `reachy_emotion`
- **User**: `reachy_user`
- **Password**: `your_db_password`
- **Port**: `5432`

### Step 4: Activate the Workflow

1. Open the **Agent 1 — Ingest Agent (Reachy 08.4.2)** workflow
2. Click the **Inactive** toggle to activate
3. Verify the webhook URL appears: `http://10.0.4.130:5678/webhook/video_gen_hook`

### Step 5: Test the Webhook

Test with curl:

```bash
curl -X POST http://10.0.4.130:5678/webhook/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "x-ingest-key: your_secure_token_here" \
  -d '{
    "source_url": "/media/rusty_admin/project_data/reachy_emotion/videos/temp/test_video.mp4",
    "label": "happy",
    "meta": {
      "generator": "luma",
      "timestamp": "2025-11-10T22:00:00Z"
    }
  }'
```

Expected response:
```json
{
  "status": "accepted",
  "message": "Video ingestion started"
}
```

---

## Part 3: How the Webhook Trigger Works

### Workflow Execution Flow

1. **Webhook Receives POST**
   - Path: `/webhook/video_gen_hook`
   - Returns 202 immediately (non-blocking)

2. **Authentication Check** (`IF: auth.check`)
   - Validates `x-ingest-key` header matches `$env.INGEST_TOKEN`
   - If invalid → Returns 401 Unauthorized
   - If valid → Continues to normalization

3. **Payload Normalization** (`Code: normalize.payload`)
   - Extracts `source_url`, `label`, `meta` from request body
   - Generates `correlation_id` and `idempotency_key`
   - Standardizes payload format

4. **Media Pull** (`HTTP: media.pull`)
   - Calls Media Mover API: `POST /api/media/pull`
   - Downloads video from `source_url`
   - Computes checksum, extracts metadata (ffprobe)
   - Generates thumbnail
   - Stores in `/videos/temp/`

5. **Polling Loop** (`Wait: 3s` → `HTTP: check.status`)
   - Polls status URL every 3 seconds
   - Max 20 attempts (60 seconds total)
   - Checks if `status == "done"`

6. **Database Insert** (`Postgres: insert.video`)
   - Inserts video metadata into `video` table
   - Fields: `video_id`, `file_path`, `split`, `label`, `duration_sec`, `fps`, `width`, `height`, `size_bytes`, `sha256`
   - Uses `ON CONFLICT DO NOTHING` for idempotency

7. **Event Emission** (`HTTP: emit.completed`)
   - Sends `ingest.completed` event to Gateway API
   - Notifies downstream agents (Agent 2 - Labeling)

8. **Success Response** (`Respond: success`)
   - Returns final status with `video_id` and `correlation_id`

### Payload Schema

**Request Payload**:
```json
{
  "source_url": "string (required)",
  "label": "string (optional: happy, sad)",
  "meta": {
    "generator": "string",
    "timestamp": "ISO8601 datetime"
  }
}
```

**Headers**:
```
Content-Type: application/json
x-ingest-key: <INGEST_TOKEN>
x-correlation-id: <UUID> (optional)
```

**Response (202 Accepted)**:
```json
{
  "status": "accepted",
  "correlation_id": "uuid"
}
```

**Response (Success - after processing)**:
```json
{
  "status": "success",
  "video_id": "uuid",
  "correlation_id": "uuid"
}
```

---

## Part 4: Luma AI Video Generation

### Luma Client Usage

The `luma_client.py` module provides a Python interface to Luma AI:

```python
from luma_client import LumaVideoGenerator
from pathlib import Path

# Initialize client
client = LumaVideoGenerator(api_key="luma-...")

# Generate and download video
video_path, metadata = client.generate_and_download(
    prompt="a happy girl eating lunch",
    output_path=Path("/media/rusty_admin/project_data/reachy_emotion/videos/temp"),
    model="ray-2",
    resolution="720p",
    duration="5s",
    aspect_ratio="16:9"
)

print(f"Video saved to: {video_path}")
print(f"Generation ID: {metadata['id']}")
```

### Supported Models

| Model Name | Model Param | Speed | Quality |
|------------|-------------|-------|---------|
| Ray 2 Flash | `ray-flash-2` | Fast | Good |
| Ray 2 | `ray-2` | Medium | Best |
| Ray 1.6 | `ray-1-6` | Medium | Good |

**Recommended**: `ray-2` for best quality

### Generation Parameters

```python
{
    "prompt": "a happy girl eating lunch",
    "model": "ray-2",
    "resolution": "720p",  # Options: 540p, 720p, 1080p, 4k
    "duration": "5s",      # Currently only 5s supported
    "aspect_ratio": "16:9", # Options: 16:9, 3:4, 9:16, etc.
    "loop": False          # Whether video should loop
}
```

### Generation Time

- **Ray 2**: ~60-120 seconds
- **Ray 2 Flash**: ~30-60 seconds

The web app polls every 3 seconds until complete.

---

## Part 5: Integration Testing

### End-to-End Test

1. **Start the web app**:
   ```bash
   cd /home/rusty_admin/projects/reachy_08.4.2/apps/web
   streamlit run landing_page.py
   ```

2. **Open browser**: `http://10.0.4.140:8501`

3. **Enter a prompt**: "a happy girl eating lunch"

4. **Click "Generate Video"**

5. **Monitor progress**:
   - Web app shows "Generating video... This may take 1-2 minutes"
   - Video downloads to `/videos/temp/`
   - n8n webhook is triggered
   - Success message appears

6. **Verify in n8n**:
   - Open n8n: `http://10.0.4.130:5678`
   - Check **Executions** tab
   - Find the latest execution of "Agent 1 — Ingest Agent"
   - Verify all nodes completed successfully

7. **Verify in database**:
   ```sql
   SELECT video_id, file_path, label, created_at 
   FROM video 
   WHERE split = 'temp' 
   ORDER BY created_at DESC 
   LIMIT 5;
   ```

8. **Verify file exists**:
   ```bash
   ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/temp/
   ```

### Troubleshooting

#### Issue: "Luma AI client not configured"
**Solution**: Check `.env` file has `LUMAAI_API_KEY` set correctly

#### Issue: "Failed to send to n8n"
**Solutions**:
- Verify n8n is running: `curl http://10.0.4.130:5678/healthz`
- Check `N8N_INGEST_TOKEN` matches in both `.env` and n8n environment
- Verify workflow is activated in n8n

#### Issue: "Generation failed"
**Solutions**:
- Check Luma API key is valid
- Verify internet connectivity
- Check Luma API status: [https://status.lumalabs.ai](https://status.lumalabs.ai)

#### Issue: "401 Unauthorized" from n8n
**Solution**: Ensure `x-ingest-key` header matches `INGEST_TOKEN` in n8n

#### Issue: Video not appearing in database
**Solutions**:
- Check Media Mover service is running on Ubuntu 1
- Verify PostgreSQL connection in n8n credentials
- Check n8n execution logs for errors

---

## Part 6: Docker Bind Mount Configuration

### n8n Docker Compose

To allow n8n to access the `/videos/temp/` directory, add a bind mount:

```yaml
services:
  n8n:
    image: n8nio/n8n:latest
    ports:
      - "5678:5678"
    environment:
      - N8N_BASIC_AUTH_ACTIVE=true
      - N8N_BASIC_AUTH_USER=admin
      - N8N_BASIC_AUTH_PASSWORD=your_password
      - INGEST_TOKEN=your_secure_token_here
      - MEDIA_MOVER_BASE_URL=http://10.0.4.130:8081
      - GATEWAY_BASE_URL=http://10.0.4.140:8000
    volumes:
      - n8n_data:/home/node/.n8n
      - /media/rusty_admin/project_data/reachy_emotion/videos:/videos:ro
    restart: unless-stopped

volumes:
  n8n_data:
```

**Key Points**:
- Mount `/videos` as read-only (`:ro`) for security
- n8n can access files but cannot modify them
- Media Mover service handles all file writes

### Restart n8n After Configuration

```bash
cd /path/to/n8n/docker-compose
docker-compose down
docker-compose up -d
docker-compose logs -f n8n
```

---

## Part 7: Security Considerations

### API Key Management

1. **Never commit `.env` files** to version control
2. **Use different tokens** for dev/staging/production
3. **Rotate tokens regularly** (every 90 days)
4. **Store in secrets manager** for production (e.g., HashiCorp Vault)

### n8n Webhook Security

1. **Always use authentication** (`x-ingest-key` header)
2. **Use HTTPS in production** (not HTTP)
3. **Rate limit webhook endpoints** to prevent abuse
4. **Log all webhook requests** for audit trail

### File System Security

1. **Restrict directory permissions**:
   ```bash
   chmod 755 /media/rusty_admin/project_data/reachy_emotion/videos/
   chmod 644 /media/rusty_admin/project_data/reachy_emotion/videos/temp/*.mp4
   ```

2. **Use read-only mounts** where possible
3. **Implement file size limits** to prevent disk exhaustion
4. **Scan uploaded files** for malware (future enhancement)

---

## Part 8: Monitoring & Observability

### n8n Execution Monitoring

1. **View executions**: n8n UI → Executions tab
2. **Filter by workflow**: "Agent 1 — Ingest Agent"
3. **Check execution time**: Should complete in < 30 seconds
4. **Monitor error rate**: Alert if > 5% failures

### Metrics to Track

- **Video generation time**: Luma API response time
- **Webhook success rate**: % of successful n8n triggers
- **Database insert rate**: Videos/hour ingested
- **Storage usage**: `/videos/temp/` disk space

### Logging

Enable detailed logging in the web app:

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

Check logs:
```bash
tail -f /var/log/streamlit/app.log
```

---

## Part 9: Next Steps

After successful integration:

1. **Agent 2 - Labeling**: Configure to receive `ingest.completed` events
2. **Agent 3 - Promotion**: Set up video promotion workflow (`temp → train/test`)
3. **Web UI Enhancement**: Add video preview before sending to n8n
4. **Batch Generation**: Support generating multiple videos from a list of prompts
5. **Quality Filters**: Reject low-quality generations automatically

---

## Appendix A: Complete .env Template

```env
# Streamlit Web App Environment
# Copy to .env and adjust for your environment

# Base URL for the Media Mover API
REACHY_API_BASE=https://10.0.4.130/api/media

# Optional bearer token for mutate endpoints
REACHY_API_TOKEN=Rb2552#!#

# Luma AI Configuration
# Get your API key from: https://lumalabs.ai/dream-machine/api/keys
LUMAAI_API_KEY=luma-56be55b6-bb5f-4c9d-a3a1-417442d20a50-67f0b180-4b9f-4bfd-963f-74132bd60ef3

# n8n Configuration
# n8n webhook endpoint for Agent 1 - Ingest
N8N_HOST=10.0.4.130
N8N_PORT=5678
# Authentication token for n8n webhook (x-ingest-key header)
N8N_INGEST_TOKEN=your_n8n_ingest_token_here
```

---

## Appendix B: Quick Reference Commands

```bash
# Install dependencies
pip install -r /home/rusty_admin/projects/reachy_08.4.2/apps/web/requirements.txt

# Run web app
streamlit run /home/rusty_admin/projects/reachy_08.4.2/apps/web/landing_page.py

# Test n8n webhook
curl -X POST http://10.0.4.130:5678/webhook/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "x-ingest-key: your_token" \
  -d '{"source_url": "/videos/temp/test.mp4"}'

# Check n8n logs
docker logs -f n8n

# Check video directory
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/temp/

# Query recent videos
psql -U reachy_user -d reachy_emotion -c \
  "SELECT video_id, file_path, created_at FROM video WHERE split='temp' ORDER BY created_at DESC LIMIT 10;"
```

---

## Support

For issues or questions:
- **Email**: rustybee255@gmail.com
- **Project**: Reachy Emotion Recognition v08.4.2
- **Documentation**: `/home/rusty_admin/projects/reachy_08.4.2/docs/`

---

**Document Version**: 1.0  
**Last Reviewed**: 2025-11-10
