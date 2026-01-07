# Next Steps - Prioritized Action Plan

**Date**: 2025-11-14  
**Version**: 0.08.4.3  
**Status**: Ready to Begin Phase 4

---

## 🎯 Immediate Actions (Before Starting Development)

### 1. Configuration Setup ⚠️ CRITICAL
**Time**: 15 minutes  
**Priority**: P0 - Must complete before any development

```bash
# Step 1: Create API service .env
cd /home/rusty_admin/projects/reachy_08.4.2
cp apps/api/.env.template apps/api/.env

# Step 2: Edit API .env (verify these values)
nano apps/api/.env
# Confirm:
# - REACHY_VIDEOS_ROOT=/media/rusty_admin/project_data/reachy_emotion/videos
# - REACHY_DATABASE_URL=postgresql+asyncpg://reachy_app:reachy_app@localhost:5432/reachy_local
# - REACHY_API_PORT=8083

# Step 3: Update Web UI .env
cp apps/web/.env apps/web/.env.backup
cp apps/web/.env.template apps/web/.env

# Step 4: Restore secrets from backup
grep "^LUMAAI_API_KEY=" apps/web/.env.backup >> apps/web/.env
grep "^N8N_INGEST_TOKEN=" apps/web/.env.backup >> apps/web/.env

# Step 5: Validate configuration
python -c "from apps.api.app.config import load_and_validate_config; load_and_validate_config()"
```

**Success Criteria**:
- ✅ Both .env files created
- ✅ Configuration validates without errors
- ✅ Secrets preserved

---

### 2. Service Verification ⚠️ CRITICAL
**Time**: 10 minutes  
**Priority**: P0 - Verify system operational

```bash
# Start API service
./scripts/service-start.sh

# Check health
curl http://localhost:8083/api/v1/health

# Expected response:
# {
#   "status": "success",
#   "data": {
#     "service": "media-mover",
#     "version": "0.08.4.3",
#     "status": "healthy"
#   }
# }

# Test video listing
curl "http://localhost:8083/api/v1/media/list?split=temp&limit=5"

# Check service status
./scripts/service-status.sh
```

**Success Criteria**:
- ✅ Service starts without errors
- ✅ Health check returns 200
- ✅ Video listing works
- ✅ Service status shows active

---

### 3. Run Test Suite ⚠️ CRITICAL
**Time**: 5 minutes  
**Priority**: P0 - Ensure no regressions

```bash
# Run endpoint tests
python -m pytest tests/test_config.py tests/test_v1_endpoints.py -v

# Expected: All tests passing

# Run integration tests
python -m pytest tests/test_integration_full.py -v

# Run client tests
python -m pytest tests/test_api_client_retry.py -v
```

**Success Criteria**:
- ✅ Config tests: 24/24 passing
- ✅ V1 endpoint tests: 16/16 passing
- ✅ Integration tests: 17/17 passing
- ✅ Client tests: 9/9 passing
- ✅ Total: 66+ tests passing

---

## 📋 Phase 4: n8n Orchestration - Task Priority

### Priority P1: Foundation (Week 1)

#### Task 4.1.1: n8n Environment Setup
**Time**: 1-2 hours  
**Dependencies**: None

**Actions**:
1. Verify n8n installation at 10.0.4.130:5678
2. Test n8n health endpoint
3. Configure webhook authentication
4. Update n8n environment variables
5. Test basic webhook trigger

**Files to Review**:
- `n8n/AGENTIC_SYSTEM_OVERVIEW.md`
- `n8n/workflows/01_ingest_agent.json`

**Testing**:
```bash
# Test n8n connectivity
curl http://10.0.4.130:5678/healthz

# Test webhook
curl -X POST http://10.0.4.130:5678/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```

**Deliverables**:
- [ ] n8n accessible
- [ ] Webhooks functional
- [ ] Environment configured
- [ ] Documentation updated

---

#### Task 4.1.2: Update Workflow Templates
**Time**: 1-2 hours  
**Dependencies**: 4.1.1

**Actions**:
1. Review existing workflows in `n8n/workflows/`
2. Update all endpoint URLs to v1 API
3. Update request/response parsing
4. Test each workflow individually
5. Document changes

**Files to Update**:
- `n8n/workflows/01_ingest_agent.json`
- `n8n/workflows/02_labeling_agent.json`
- `n8n/workflows/03_promotion_agent.json`
- `n8n/workflows/04_reconciler_agent.json`
- `n8n/workflows/05_training_agent.json`
- `n8n/workflows/06_evaluation_agent.json`
- `n8n/workflows/07_deployment_agent.json`

**Changes Required**:
```javascript
// Old
"url": "http://localhost:8083/api/videos/list"

// New
"url": "http://localhost:8083/api/v1/media/list"

// Update response parsing
// Old: body.items
// New: body.data.items
```

**Deliverables**:
- [ ] All workflows updated
- [ ] Endpoints tested
- [ ] Response parsing validated
- [ ] Changes documented

---

#### Task 4.1.3: Database Schema Validation
**Time**: 1 hour  
**Dependencies**: None

**Actions**:
1. Connect to PostgreSQL
2. Verify all required tables exist
3. Test stored procedures
4. Validate constraints
5. Check indexes

**SQL Validation**:
```sql
-- Check tables
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public';

-- Expected tables:
-- video, training_run, training_selection, promotion_log,
-- user_session, generation_request, emotion_event

-- Test stored procedure
SELECT * FROM promote_video_to_split('test_video', 'train', 'happy');

-- Check constraints
SELECT constraint_name, constraint_type 
FROM information_schema.table_constraints 
WHERE table_schema = 'public';
```

**Deliverables**:
- [ ] Schema validated
- [ ] Procedures tested
- [ ] Constraints verified
- [ ] Documentation updated

---

### Priority P2: Core Agents (Week 1-2)

#### Task 4.2.1: Implement Ingest Agent
**Time**: 2-3 hours  
**Dependencies**: 4.1.1, 4.1.2

**Workflow Steps**:
1. Receive upload/generation event
2. Compute SHA256 checksum
3. Store in `/videos/temp/`
4. Extract metadata
5. Generate thumbnail
6. Persist to database
7. Emit event

**Implementation**:
```javascript
// n8n workflow nodes:
1. Webhook Trigger
2. Function: Compute Checksum
3. HTTP Request: Store Video
4. Function: Extract Metadata
5. HTTP Request: Generate Thumbnail
6. HTTP Request: Save to Database
7. Webhook Response
```

**Testing**:
```bash
# Test ingest
curl -X POST http://10.0.4.130:5678/webhook/ingest \
  -F "file=@test_video.mp4" \
  -F "correlation_id=test-123"

# Verify in database
psql reachy_local -c "SELECT * FROM video WHERE video_id='test_video';"

# Check filesystem
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/temp/
```

**Deliverables**:
- [ ] Workflow created
- [ ] Checksum computed
- [ ] Metadata extracted
- [ ] Thumbnail generated
- [ ] Database updated
- [ ] Tests passing

---

#### Task 4.2.2: Implement Labeling Agent
**Time**: 1-2 hours  
**Dependencies**: 4.2.1

**Workflow Steps**:
1. Listen for labeling requests
2. Validate label
3. Update database
4. Check class balance
5. Emit event

**Implementation**:
```javascript
// n8n workflow nodes:
1. Webhook Trigger
2. Function: Validate Label
3. HTTP Request: POST /api/v1/promote/stage
4. Function: Check Balance
5. HTTP Request: Update Stats
6. Webhook Response
```

**Testing**:
```bash
# Test labeling
curl -X POST http://10.0.4.130:5678/webhook/label \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": ["test_video"],
    "label": "happy"
  }'

# Verify label
psql reachy_local -c "SELECT video_id, label FROM video WHERE video_id='test_video';"
```

**Deliverables**:
- [ ] Workflow created
- [ ] Label validation working
- [ ] Database updated
- [ ] Balance checked
- [ ] Tests passing

---

#### Task 4.2.3: Implement Promotion Agent
**Time**: 2-3 hours  
**Dependencies**: 4.2.2

**Workflow Steps**:
1. Receive promotion request
2. Validate destination
3. Check constraints
4. Execute filesystem move
5. Update database
6. Emit event

**Implementation**:
```javascript
// n8n workflow nodes:
1. Webhook Trigger
2. Function: Validate Request
3. HTTP Request: POST /api/v1/promote/stage
4. Function: Verify Move
5. HTTP Request: Update Database
6. Webhook Response
```

**Testing**:
```bash
# Test promotion
curl -X POST http://10.0.4.130:5678/webhook/promote \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": ["test_video"],
    "label": "happy",
    "dry_run": false
  }'

# Verify filesystem
ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/dataset_all/

# Verify database
psql reachy_local -c "SELECT video_id, split FROM video WHERE video_id='test_video';"
```

**Deliverables**:
- [ ] Workflow created
- [ ] Validation working
- [ ] Filesystem updated
- [ ] Database synced
- [ ] Tests passing

---

#### Task 4.2.4: Implement Reconciler Agent
**Time**: 2-3 hours  
**Dependencies**: 4.2.3

**Workflow Steps**:
1. Scan filesystem
2. Compute checksums
3. Compare with database
4. Detect issues
5. Rebuild manifests
6. Emit report

**Implementation**:
```javascript
// n8n workflow nodes:
1. Cron Trigger (daily 2 AM)
2. HTTP Request: GET /api/v1/media/list (all splits)
3. Function: Scan Filesystem
4. Function: Compare Checksums
5. Function: Detect Orphans
6. HTTP Request: POST /api/v1/promote/reset-manifest (if needed)
7. Function: Generate Report
8. Email: Send Report
```

**Testing**:
```bash
# Manual trigger
curl -X POST http://10.0.4.130:5678/webhook/reconcile

# Check manifests
cat /media/rusty_admin/project_data/reachy_emotion/videos/manifests/train_manifest.json
```

**Deliverables**:
- [ ] Workflow created
- [ ] Scanning working
- [ ] Comparison accurate
- [ ] Manifests rebuilt
- [ ] Reports generated
- [ ] Tests passing

---

#### Task 4.2.5: Implement Training Orchestrator
**Time**: 3-4 hours  
**Dependencies**: 4.2.4

**Workflow Steps**:
1. Check dataset balance
2. Validate thresholds
3. Generate manifest
4. Launch TAO training
5. Monitor progress
6. Record to MLflow
7. Emit event

**Implementation**:
```javascript
// n8n workflow nodes:
1. Webhook Trigger (manual)
2. HTTP Request: GET /api/v1/media/list?split=train
3. Function: Check Balance
4. Function: Generate Manifest
5. Execute Command: python trainer/train_emotionnet.py
6. Function: Monitor Progress
7. HTTP Request: Record to MLflow
8. Webhook Response
```

**Testing**:
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
```

**Deliverables**:
- [ ] Workflow created
- [ ] Balance checked
- [ ] Training launched
- [ ] Progress monitored
- [ ] MLflow updated
- [ ] Tests passing

---

### Priority P3: Supporting Agents (Week 2)

#### Task 4.2.6: Implement Evaluation Agent
**Time**: 2-3 hours  
**Dependencies**: 4.2.5

#### Task 4.2.7: Implement Deployment Agent
**Time**: 2-3 hours  
**Dependencies**: 4.2.6

#### Task 4.2.8: Implement Privacy Agent
**Time**: 1-2 hours  
**Dependencies**: None (independent)

#### Task 4.2.9: Implement Observability Agent
**Time**: 2-3 hours  
**Dependencies**: All other agents

---

### Priority P4: Integration (Week 3)

#### Task 4.3.1: Event-Driven Architecture
**Time**: 2-3 hours  
**Dependencies**: All core agents

#### Task 4.4.1: Workflow Orchestration
**Time**: 2-3 hours  
**Dependencies**: 4.3.1

#### Task 4.4.2: End-to-End Testing
**Time**: 2-3 hours  
**Dependencies**: 4.4.1

---

## 📊 Time Estimates

### Phase 4 Total: 25-35 hours

| Priority | Tasks | Time |
|----------|-------|------|
| P0 (Critical) | Configuration & Verification | 0.5 hours |
| P1 (Foundation) | n8n Setup & Templates | 3-5 hours |
| P2 (Core Agents) | Agents 1-5 | 10-15 hours |
| P3 (Supporting) | Agents 6-9 | 7-10 hours |
| P4 (Integration) | Events & Orchestration | 6-9 hours |

### Weekly Breakdown

**Week 1** (10-12 hours):
- Day 1: Configuration + n8n Setup (2-3 hours)
- Day 2: Ingest + Labeling Agents (3-4 hours)
- Day 3: Promotion + Reconciler Agents (4-5 hours)

**Week 2** (10-12 hours):
- Day 1: Training Orchestrator (3-4 hours)
- Day 2: Evaluation + Deployment Agents (4-6 hours)
- Day 3: Privacy + Observability Agents (3-4 hours)

**Week 3** (8-10 hours):
- Day 1: Event Architecture (2-3 hours)
- Day 2: Workflow Orchestration (2-3 hours)
- Day 3: End-to-End Testing (2-3 hours)
- Day 4: Documentation + Cleanup (2-3 hours)

---

## 🎯 Success Metrics

### Phase 4 Completion Criteria

**Functional**:
- [ ] All 9 agents operational
- [ ] End-to-end pipeline works
- [ ] Events flowing correctly
- [ ] Database consistent

**Quality**:
- [ ] Tests passing (>90%)
- [ ] No critical bugs
- [ ] Performance acceptable
- [ ] Documentation complete

**Operational**:
- [ ] Workflows deployed
- [ ] Monitoring active
- [ ] Alerts configured
- [ ] Runbooks created

---

## 🚀 Getting Started

### Today's Tasks (2-3 hours)

1. **Complete Configuration** (30 min)
   - Create .env files
   - Validate settings
   - Test services

2. **Verify System** (30 min)
   - Run test suite
   - Check endpoints
   - Validate database

3. **n8n Setup** (1-2 hours)
   - Access n8n UI
   - Test webhooks
   - Import workflows

### Tomorrow's Tasks (3-4 hours)

1. **Update Workflows** (2 hours)
   - Update endpoint URLs
   - Fix response parsing
   - Test individually

2. **Implement Ingest Agent** (2 hours)
   - Create workflow
   - Test upload
   - Validate database

---

## 📚 Reference Checklist

Before starting each task, review:

- [ ] `DEVELOPMENT_PLAN_08.4.3.md` - Full plan
- [ ] `AGENTS_08.4.2.md` - Agent specifications
- [ ] `API_ENDPOINT_REFERENCE.md` - API documentation
- [ ] `CONFIG_UPDATE_GUIDE.md` - Configuration help
- [ ] `n8n/AGENTIC_SYSTEM_OVERVIEW.md` - n8n architecture

---

## 🔧 Quick Commands Reference

```bash
# Configuration
cp apps/api/.env.template apps/api/.env
cp apps/web/.env.template apps/web/.env

# Service Management
./scripts/service-start.sh
./scripts/service-status.sh
./scripts/service-restart.sh

# Testing
python -m pytest tests/ -v
python -m pytest tests/test_config.py -v

# Health Checks
curl http://localhost:8083/api/v1/health
curl http://10.0.4.130:5678/healthz

# Database
psql reachy_local -c "SELECT * FROM video LIMIT 5;"

# Logs
journalctl -u fastapi-media.service -f
```

---

**Last Updated**: 2025-11-14  
**Status**: Ready to Begin ✅  
**Next Action**: Complete configuration setup (30 minutes)
