# Quick Start Guide - Phase 4 Implementation

**Version**: 0.08.4.3  
**Last Updated**: 2025-11-14  
**Estimated Time**: 25-35 hours over 3 weeks

---

## 🎯 Overview

Phase 4 implements the 9-agent orchestration system using n8n workflows to automate the complete video → label → train → deploy pipeline.

---

## ⚡ Prerequisites (30 minutes)

### 1. Configuration Setup

```bash
# Navigate to project
cd /home/rusty_admin/projects/reachy_08.4.2

# Create API .env
cp apps/api/.env.template apps/api/.env
nano apps/api/.env
# Verify: REACHY_VIDEOS_ROOT, REACHY_DATABASE_URL, REACHY_API_PORT

# Update Web UI .env (preserve API keys)
cp apps/web/.env apps/web/.env.backup
cp apps/web/.env.template apps/web/.env
grep "^LUMAAI_API_KEY=" apps/web/.env.backup >> apps/web/.env
grep "^N8N_INGEST_TOKEN=" apps/web/.env.backup >> apps/web/.env

# Validate configuration
python -c "from apps.api.app.config import load_and_validate_config; load_and_validate_config()"
# Expected: ✅ Configuration valid
```

### 2. Service Verification

```bash
# Start API service
./scripts/service-start.sh

# Check health
curl http://localhost:8083/api/v1/health
# Expected: {"status": "success", ...}

# Test video listing
curl "http://localhost:8083/api/v1/media/list?split=temp&limit=5"

# Check service status
./scripts/service-status.sh
# Expected: Active: active (running)
```

### 3. Run Tests

```bash
# Run endpoint tests
python -m pytest tests/test_config.py tests/test_v1_endpoints.py -v
# Expected: 40 passed

# Run integration tests
python -m pytest tests/test_integration_full.py -v
# Expected: 17 passed
```

**✅ Prerequisites Complete** - Ready to begin Phase 4

---

## 📅 Week 1: Foundation & Core Agents (10-12 hours)

### Day 1: n8n Setup (2-3 hours)

#### Task 1.1: Verify n8n Installation
```bash
# Test n8n connectivity
curl http://10.0.4.130:5678/healthz
# Expected: OK or 200 response

# Access n8n UI
# Browser: http://10.0.4.130:5678
# Login with credentials
```

#### Task 1.2: Configure n8n Environment
```bash
# SSH to n8n host
ssh admin@10.0.4.130

# Check n8n environment
cat ~/.n8n/.env
# Verify: N8N_INGEST_TOKEN, webhook settings

# Test webhook
curl -X POST http://10.0.4.130:5678/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

#### Task 1.3: Import Workflow Templates
```bash
# In n8n UI:
# 1. Go to Workflows
# 2. Click "Import from File"
# 3. Import each workflow from n8n/workflows/
# 4. Update credentials
# 5. Test each workflow
```

**Files to Import**:
- `01_ingest_agent.json`
- `02_labeling_agent.json`
- `03_promotion_agent.json`
- `04_reconciler_agent.json`
- `05_training_agent.json`
- `06_evaluation_agent.json`
- `07_deployment_agent.json`

**Deliverables**:
- [ ] n8n accessible
- [ ] Workflows imported
- [ ] Credentials configured
- [ ] Test webhook working

---

### Day 2: Ingest & Labeling Agents (3-4 hours)

#### Task 2.1: Update Ingest Agent Workflow

**Open**: `01_ingest_agent.json` in n8n UI

**Update Nodes**:
1. **Webhook Trigger**
   - Path: `/webhook/ingest`
   - Method: POST
   - Authentication: Header Auth (N8N_INGEST_TOKEN)

2. **HTTP Request: Store Video**
   - URL: `http://localhost:8083/api/v1/media/register`
   - Method: POST
   - Body: `{{ $json }}`

3. **Function: Extract Metadata**
   ```javascript
   const video = $input.item.json;
   return {
     video_id: video.video_id,
     duration: video.duration,
     fps: video.fps,
     resolution: video.resolution
   };
   ```

4. **HTTP Request: Generate Thumbnail**
   - URL: `http://localhost:8083/api/v1/media/{{ $json.video_id }}/thumb`
   - Method: POST

**Test**:
```bash
# Upload test video
curl -X POST http://10.0.4.130:5678/webhook/ingest \
  -H "Authorization: Bearer tkn3848" \
  -F "file=@test_video.mp4" \
  -F "correlation_id=test-123"

# Verify in database
psql reachy_local -c "SELECT * FROM video WHERE video_id='test_video';"

# Check filesystem
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/temp/
```

**Deliverables**:
- [ ] Workflow updated
- [ ] Test upload successful
- [ ] Database updated
- [ ] Thumbnail generated

---

#### Task 2.2: Update Labeling Agent Workflow

**Open**: `02_labeling_agent.json` in n8n UI

**Update Nodes**:
1. **Webhook Trigger**
   - Path: `/webhook/label`
   - Method: POST

2. **Function: Validate Label**
   ```javascript
   const labels = ['happy', 'sad', 'angry', 'surprise', 'fear', 'neutral'];
   const label = $input.item.json.label;
   
   if (!labels.includes(label)) {
     throw new Error(`Invalid label: ${label}`);
   }
   
   return $input.item.json;
   ```

3. **HTTP Request: Stage Videos**
   - URL: `http://localhost:8083/api/v1/promote/stage`
   - Method: POST
   - Body:
     ```json
     {
       "video_ids": "{{ $json.video_ids }}",
       "label": "{{ $json.label }}",
       "dry_run": false
     }
     ```

4. **HTTP Request: Check Balance**
   - URL: `http://localhost:8083/api/v1/media/list?split=dataset_all`
   - Method: GET

**Test**:
```bash
# Label test video
curl -X POST http://10.0.4.130:5678/webhook/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": ["test_video"],
    "label": "happy"
  }'

# Verify label
psql reachy_local -c "SELECT video_id, label, split FROM video WHERE video_id='test_video';"
```

**Deliverables**:
- [ ] Workflow updated
- [ ] Label validation working
- [ ] Videos staged
- [ ] Balance checked

---

### Day 3: Promotion & Reconciler Agents (4-5 hours)

#### Task 3.1: Update Promotion Agent Workflow

**Open**: `03_promotion_agent.json` in n8n UI

**Update Nodes**:
1. **Webhook Trigger**
   - Path: `/webhook/promote`
   - Method: POST

2. **HTTP Request: Sample to Train/Test**
   - URL: `http://localhost:8083/api/v1/promote/sample`
   - Method: POST
   - Body:
     ```json
     {
       "train_fraction": 0.8,
       "test_fraction": 0.2,
       "stratify_by_label": true,
       "dry_run": false
     }
     ```

3. **Function: Verify Move**
   ```javascript
   const response = $input.item.json;
   return {
     train_count: response.train_ids.length,
     test_count: response.test_ids.length,
     skipped_count: response.skipped_ids.length
   };
   ```

**Test**:
```bash
# Promote videos to train/test
curl -X POST http://10.0.4.130:5678/webhook/promote \
  -H "Content-Type: application/json" \
  -d '{
    "train_fraction": 0.8,
    "test_fraction": 0.2
  }'

# Verify filesystem
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/train/
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/test/

# Verify database
psql reachy_local -c "SELECT split, COUNT(*) FROM video GROUP BY split;"
```

**Deliverables**:
- [ ] Workflow updated
- [ ] Sampling working
- [ ] Filesystem updated
- [ ] Database synced

---

#### Task 3.2: Update Reconciler Agent Workflow

**Open**: `04_reconciler_agent.json` in n8n UI

**Update Nodes**:
1. **Cron Trigger**
   - Schedule: `0 2 * * *` (daily at 2 AM)

2. **HTTP Request: List All Videos**
   - URL: `http://localhost:8083/api/v1/media/list?split=temp&limit=1000`
   - Method: GET

3. **Function: Scan Filesystem**
   ```javascript
   const fs = require('fs');
   const path = require('path');
   
   const videosRoot = '/media/rusty_admin/project_data/reachy_emotion/videos';
   const splits = ['temp', 'dataset_all', 'train', 'test'];
   
   let filesystemVideos = [];
   for (const split of splits) {
     const dir = path.join(videosRoot, split);
     const files = fs.readdirSync(dir);
     filesystemVideos = filesystemVideos.concat(
       files.map(f => ({ split, filename: f }))
     );
   }
   
   return { filesystemVideos };
   ```

4. **Function: Compare & Detect Issues**
   ```javascript
   const dbVideos = $node["HTTP Request"].json.data.items;
   const fsVideos = $input.item.json.filesystemVideos;
   
   // Detect orphans (in FS but not in DB)
   const orphans = fsVideos.filter(fv => 
     !dbVideos.some(dv => dv.file_path.includes(fv.filename))
   );
   
   // Detect missing (in DB but not in FS)
   const missing = dbVideos.filter(dv =>
     !fsVideos.some(fv => dv.file_path.includes(fv.filename))
   );
   
   return { orphans, missing, total_issues: orphans.length + missing.length };
   ```

5. **If: Issues Found**
   - Condition: `{{ $json.total_issues > 0 }}`

6. **HTTP Request: Rebuild Manifest**
   - URL: `http://localhost:8083/api/v1/promote/reset-manifest`
   - Method: POST

**Test**:
```bash
# Manual trigger
curl -X POST http://10.0.4.130:5678/webhook/reconcile

# Check manifests
cat /media/rusty_admin/project_data/reachy_emotion/videos/manifests/train_manifest.json
cat /media/rusty_admin/project_data/reachy_emotion/videos/manifests/test_manifest.json
```

**Deliverables**:
- [ ] Workflow updated
- [ ] Scanning working
- [ ] Issues detected
- [ ] Manifests rebuilt

---

## 📅 Week 2: Training & Evaluation (10-12 hours)

### Day 1: Training Orchestrator (3-4 hours)

#### Task 4.1: Update Training Agent Workflow

**Open**: `05_training_agent.json` in n8n UI

**Update Nodes**:
1. **Webhook Trigger**
   - Path: `/webhook/train`
   - Method: POST

2. **HTTP Request: Check Dataset Balance**
   - URL: `http://localhost:8083/api/v1/media/list?split=train`
   - Method: GET

3. **Function: Validate Thresholds**
   ```javascript
   const videos = $input.item.json.data.items;
   const minPerClass = 50;
   
   // Count by label
   const counts = {};
   videos.forEach(v => {
     counts[v.label] = (counts[v.label] || 0) + 1;
   });
   
   // Check minimums
   for (const [label, count] of Object.entries(counts)) {
     if (count < minPerClass) {
       throw new Error(`Insufficient ${label} videos: ${count} < ${minPerClass}`);
     }
   }
   
   return { counts, ready: true };
   ```

4. **Execute Command: Launch Training**
   ```bash
   python /home/rusty_admin/projects/reachy_08.4.2/trainer/train_emotionnet.py \
     --config /home/rusty_admin/projects/reachy_08.4.2/trainer/tao/specs/emotionnet_2cls.yaml \
     --dataset /media/rusty_admin/project_data/reachy_emotion/videos \
     --output /home/rusty_admin/projects/reachy_08.4.2/trainer/tao/experiments \
     --train-fraction 0.8 \
     --seed 42
   ```

5. **Function: Monitor Progress**
   - Poll MLflow for metrics
   - Check training logs
   - Emit progress events

**Test**:
```bash
# Test training (small dataset)
curl -X POST http://10.0.4.130:5678/webhook/train \
  -H "Content-Type: application/json" \
  -d '{
    "config": "emotionnet_2cls.yaml",
    "epochs": 5
  }'

# Check MLflow
curl http://localhost:5000/api/2.0/mlflow/experiments/list

# Check training output
ls -lh trainer/tao/experiments/
```

**Deliverables**:
- [ ] Workflow updated
- [ ] Balance checked
- [ ] Training launched
- [ ] Progress monitored
- [ ] MLflow updated

---

### Day 2-3: Evaluation & Deployment Agents (4-6 hours)

Similar pattern for Agents 6 & 7...

---

## 📅 Week 3: Integration & Testing (8-10 hours)

### Event Architecture & Orchestration

Details in `DEVELOPMENT_PLAN_08.4.3.md`...

---

## 🎯 Success Checklist

### Week 1
- [ ] n8n configured and accessible
- [ ] All workflows imported
- [ ] Ingest agent working
- [ ] Labeling agent working
- [ ] Promotion agent working
- [ ] Reconciler agent working

### Week 2
- [ ] Training orchestrator working
- [ ] Evaluation agent working
- [ ] Deployment agent working
- [ ] Privacy agent working
- [ ] Observability agent working

### Week 3
- [ ] Event architecture implemented
- [ ] Workflows orchestrated
- [ ] End-to-end pipeline tested
- [ ] Documentation updated

---

## 📚 Key References

- **Full Plan**: `DEVELOPMENT_PLAN_08.4.3.md`
- **Prioritized Tasks**: `NEXT_STEPS_PRIORITIZED.md`
- **Agent Specs**: `AGENTS_08.4.2.md`
- **API Docs**: `API_ENDPOINT_REFERENCE.md`
- **n8n Overview**: `n8n/AGENTIC_SYSTEM_OVERVIEW.md`

---

## 🆘 Troubleshooting

### n8n Not Accessible
```bash
# Check n8n service
ssh admin@10.0.4.130
sudo systemctl status n8n
sudo systemctl restart n8n
```

### Webhook Not Working
```bash
# Check webhook path
curl -v http://10.0.4.130:5678/webhook/test

# Check authentication
curl -v -H "Authorization: Bearer tkn3848" http://10.0.4.130:5678/webhook/test
```

### Database Connection Issues
```bash
# Test connection
psql -h localhost -U reachy_app -d reachy_local -c "SELECT 1;"

# Check service
sudo systemctl status postgresql
```

---

**Ready to Begin**: Complete prerequisites, then start Week 1 Day 1! 🚀
