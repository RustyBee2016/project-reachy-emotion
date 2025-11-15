# n8n Quick Configuration Guide

**Date**: 2025-11-14  
**n8n**: http://10.0.4.130:5678  
**API**: http://10.0.4.130:8083

---

## 🚀 Quick Setup

### 1. Environment Variables (in n8n)

```bash
REACHY_API_BASE=http://10.0.4.130:8083
N8N_INGEST_TOKEN=tkn3848
```

### 2. Update Existing Workflows

**Key Changes for v1 API**:

**OLD**:
```
URL: /api/videos/list
Response: body.items
```

**NEW**:
```
URL: /api/v1/media/list
Response: body.data.items
```

---

## 📝 Common Node Patterns

### Webhook Node (Receive)
```javascript
{
  "httpMethod": "POST",
  "path": "webhook_name",
  "responseMode": "onReceived"
}
```

### HTTP Request (Call API)
```javascript
{
  "method": "POST",
  "url": "={{$env.REACHY_API_BASE}}/api/v1/media/list",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {"name": "X-Correlation-ID", "value": "={{$json.correlation_id}}"}
    ]
  }
}
```

### HTTP Request (Trigger Another Workflow)
```javascript
{
  "method": "POST",
  "url": "http://10.0.4.130:5678/webhook/target",
  "sendHeaders": true,
  "headerParameters": {
    "parameters": [
      {"name": "X-Ingest-Key", "value": "={{$env.N8N_INGEST_TOKEN}}"}
    ]
  },
  "sendBody": true,
  "specifyBody": "json",
  "jsonBody": "={{ JSON.stringify($json) }}"
}
```

### Code Node (Parse v1 Response)
```javascript
const response = $input.first().json;
const items = response.data.items;  // v1 format
return items.map(item => ({ json: item }));
```

---

## 🔄 Workflow Updates Needed

### Workflow 1: Ingest Agent
- ✅ Already configured
- Update if using old endpoints

### Workflow 2: Labeling Agent
**Update HTTP Request node**:
```
OLD: /api/media/promote
NEW: /api/v1/promote/stage
```

**Update response parsing**:
```javascript
// Direct response (not wrapped)
const response = $input.first().json;
return [{ json: {
  promoted_ids: response.promoted_ids,
  skipped_ids: response.skipped_ids
}}];
```

### Workflow 3: Promotion Agent
**Update HTTP Request node**:
```
OLD: /api/media/promote
NEW: /api/v1/promote/sample
```

### Workflow 4: Reconciler Agent
**Update HTTP Request node**:
```
OLD: /api/videos/list
NEW: /api/v1/media/list
```

**Update response parsing**:
```javascript
const response = $input.first().json;
const items = response.data.items;  // NEW
```

---

## 🧪 Testing

```bash
# Test webhook
curl -X POST http://10.0.4.130:5678/webhook/ingest \
  -H "X-Ingest-Key: tkn3848" \
  -d '{"test": "data"}'

# Test API
curl http://10.0.4.130:8083/api/v1/health
```

---

## 📚 Full Guide

See `N8N_WORKFLOW_CONFIGURATION_GUIDE.md` for complete details.
