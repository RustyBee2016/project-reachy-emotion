# Quick Start: Luma AI Video Generation

## 5-Minute Setup Guide

### 1. Add Your API Key to .env

```bash
cd /home/rusty_admin/projects/reachy_08.4.2/apps/web
cp .env.example .env
nano .env
```

Add this line with your actual API key:
```env
LUMAAI_API_KEY=luma-56be55b6-bb5f-4c9d-a3a1-417442d20a50-67f0b180-4b9f-4bfd-963f-74132bd60ef3
N8N_INGEST_TOKEN=your_secure_token_here
```

### 2. Install Dependencies

```bash
pip install lumaai>=1.0
```

### 3. Configure n8n Webhook

In n8n (http://10.0.4.130:5678):

1. Import workflow: `n8n/workflows/01_ingest_agent.json`
2. Set environment variable: `INGEST_TOKEN=your_secure_token_here`
3. Activate the workflow
4. Note the webhook URL: `http://10.0.4.130:5678/webhook/video_gen_hook`

### 4. Run the Web App

```bash
streamlit run landing_page.py
```

### 5. Generate Your First Video

1. Open: `http://10.0.4.140:8501`
2. Enter prompt: "a happy girl eating lunch"
3. Click "Generate Video"
4. Wait ~1-2 minutes
5. Video appears in player and is sent to n8n automatically

---

## How the n8n Webhook Trigger Works

### Webhook Configuration

**Path**: `/webhook/video_gen_hook`  
**Method**: POST  
**Authentication**: `x-ingest-key` header  
**Response**: 202 Accepted (immediate, non-blocking)

### Expected Payload

```json
{
  "source_url": "/media/rusty_admin/project_data/reachy_emotion/videos/temp/luma_20251110_220000.mp4",
  "label": "happy",
  "meta": {
    "generator": "luma",
    "timestamp": "2025-11-10T22:00:00Z"
  }
}
```

### What Happens Next

1. **Authentication Check**: Validates `x-ingest-key` header
2. **Payload Normalization**: Extracts video URL and metadata
3. **Media Pull**: Downloads video, computes checksum, extracts metadata
4. **Database Insert**: Stores video record in PostgreSQL
5. **Event Emission**: Notifies downstream agents (Agent 2 - Labeling)
6. **Success Response**: Returns video_id and correlation_id

### Workflow Execution Time

- **Total**: ~10-30 seconds
- **Media Pull**: ~5-15 seconds (depends on video size)
- **Database Insert**: <1 second
- **Event Emission**: <1 second

---

## Testing the Integration

### Test 1: Web App Generation

```bash
# Start web app
streamlit run landing_page.py

# Generate video via UI
# Prompt: "a happy girl eating lunch"
```

### Test 2: Direct Webhook Call

```bash
curl -X POST http://10.0.4.130:5678/webhook/video_gen_hook \
  -H "Content-Type: application/json" \
  -H "x-ingest-key: your_secure_token_here" \
  -d '{
    "source_url": "/media/rusty_admin/project_data/reachy_emotion/videos/temp/test.mp4",
    "label": "happy",
    "meta": {"generator": "test"}
  }'
```

Expected response:
```json
{"status": "accepted", "correlation_id": "uuid"}
```

### Test 3: Verify in Database

```sql
SELECT video_id, file_path, label, created_at 
FROM video 
WHERE split = 'temp' 
ORDER BY created_at DESC 
LIMIT 5;
```

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Luma AI client not configured" | Check `LUMAAI_API_KEY` in `.env` |
| "Failed to send to n8n" | Verify `N8N_INGEST_TOKEN` matches in both `.env` and n8n |
| "401 Unauthorized" | Check `x-ingest-key` header matches `INGEST_TOKEN` |
| Video not in database | Check n8n execution logs, verify Media Mover is running |

---

## Next Steps

1. ✅ Generate videos with Luma AI
2. ✅ Send to n8n Ingest Agent
3. 🔄 Configure Agent 2 - Labeling (next)
4. 🔄 Set up video promotion workflow (next)

---

For detailed documentation, see: `docs/LUMA_N8N_INTEGRATION_GUIDE.md`
