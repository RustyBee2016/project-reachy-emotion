# Next Steps — Action Plan for Phase 4
**Project**: Reachy_Local_08.4.2  
**Current Status**: Gateway Services Complete (Phase 3) ✅  
**Next Phase**: n8n Orchestration (Phase 4) ⏳

[MEMORY BANK: ACTIVE]

---

## 🎯 Phase 4 Objective

**Deploy and integrate the 9-agent agentic system using n8n workflows to orchestrate the complete video → label → train → evaluate → deploy pipeline.**

---

## 📋 Detailed Action Plan

### **Week 1: n8n Setup & Foundation**

#### Day 1-2: n8n Installation
**Goal**: Get n8n running on Ubuntu 1

```bash
# Option 1: Docker (Recommended)
docker run -d \
  --name n8n \
  -p 5678:5678 \
  -v ~/.n8n:/home/node/.n8n \
  -e N8N_BASIC_AUTH_ACTIVE=true \
  -e N8N_BASIC_AUTH_USER=admin \
  -e N8N_BASIC_AUTH_PASSWORD=<secure_password> \
  n8nio/n8n

# Option 2: npm
npm install -g n8n
n8n start --tunnel
```

**Tasks**:
- [ ] Install n8n on Ubuntu 1
- [ ] Configure to run on port 5678
- [ ] Set up basic authentication
- [ ] Test web UI access: `http://10.0.4.130:5678`
- [ ] Configure systemd service for auto-start
- [ ] Document credentials in secure location

**Verification**:
```bash
curl -u admin:<password> http://10.0.4.130:5678/healthz
```

#### Day 3: Environment Configuration
**Goal**: Configure n8n for the Reachy environment

**Tasks**:
- [ ] Set environment variables:
  ```bash
  export REACHY_VIDEOS_ROOT="/media/project_data/reachy_emotion/videos"
  export REACHY_DATABASE_URL="postgresql://user:pass@localhost:5432/reachy_emotion"
  export REACHY_API_BASE="http://10.0.4.140:8000"
  export REACHY_MEDIA_API="http://10.0.4.130:8081"
  ```
- [ ] Create n8n credentials for:
  - PostgreSQL database
  - FastAPI endpoints (Ubuntu 2)
  - Media Mover API (Ubuntu 1)
  - LM Studio API (Ubuntu 1)
- [ ] Test credential connections

**Verification**:
- n8n can connect to PostgreSQL
- n8n can reach FastAPI endpoints
- n8n can access Media Mover API

#### Day 4-5: Import Agent Workflows
**Goal**: Load all 9 agent workflows into n8n

**Tasks**:
- [ ] Import `01_ingest_agent.json`
- [ ] Import `02_labeling_agent.json`
- [ ] Import `03_promotion_agent.json`
- [ ] Import `04_reconciler_agent.json`
- [ ] Import `05_training_orchestrator.json`
- [ ] Import `06_evaluation_agent.json`
- [ ] Import `07_deployment_agent.json`
- [ ] Import `08_privacy_agent.json`
- [ ] Import `09_observability_agent.json`

**For Each Workflow**:
1. Import JSON file via n8n UI
2. Update credentials
3. Update endpoint URLs
4. Update file paths
5. Save and activate

**Verification**:
- All 9 workflows visible in n8n
- No credential errors
- All nodes properly configured

---

### **Week 2: Agent Testing & Integration**

#### Agent 1: Ingest Agent (Day 1)
**Goal**: Test video ingestion pipeline

**Test Scenario**:
```bash
# 1. Upload a test video to /videos/temp/
cp test_video.mp4 /media/project_data/reachy_emotion/videos/temp/

# 2. Trigger ingest workflow (manual or webhook)
curl -X POST http://10.0.4.130:5678/webhook/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path": "temp/test_video.mp4"}'

# 3. Verify results
# - SHA256 checksum computed
# - Metadata in PostgreSQL
# - Thumbnail generated in /thumbs/
# - ingest.completed event emitted
```

**Tasks**:
- [ ] Configure ingest webhook
- [ ] Test checksum computation
- [ ] Test metadata extraction
- [ ] Test thumbnail generation
- [ ] Test database insertion
- [ ] Test event emission
- [ ] Document any issues

**Success Criteria**:
- Video record in database
- Thumbnail exists
- Checksum matches
- Event emitted

#### Agent 2: Labeling Agent (Day 2)
**Goal**: Test user classification workflow

**Test Scenario**:
```bash
# 1. Label a video via API
curl -X PATCH http://10.0.4.140:8000/api/videos/{video_id}/label \
  -H "Content-Type: application/json" \
  -d '{"new_label": "happy"}'

# 2. Verify labeling agent processes it
# - Updates database
# - Checks class balance
# - Emits label.updated event
```

**Tasks**:
- [ ] Test label update workflow
- [ ] Test balance checking
- [ ] Test constraint enforcement
- [ ] Test event emission
- [ ] Document edge cases

**Success Criteria**:
- Label updated in database
- Balance metrics updated
- Constraints enforced

#### Agent 3: Promotion Agent (Day 3)
**Goal**: Test file promotion workflow

**Test Scenario**:
```bash
# 1. Promote video to dataset_all
curl -X POST http://10.0.4.140:8000/api/v1/promote/stage \
  -H "Content-Type: application/json" \
  -d '{"video_ids": ["<uuid>"], "label": "happy"}'

# 2. Verify promotion
# - File moved from temp/ to dataset_all/
# - Database updated
# - Manifest updated
# - promotion.completed event emitted
```

**Tasks**:
- [ ] Test temp → dataset_all promotion
- [ ] Test atomic file operations
- [ ] Test manifest updates
- [ ] Test rollback on error
- [ ] Document failure modes

**Success Criteria**:
- File physically moved
- Database split updated
- Manifest reflects change
- No orphaned files

#### Agent 4: Reconciler Agent (Day 4)
**Goal**: Test consistency checking

**Test Scenario**:
```bash
# 1. Manually create inconsistency
# - Add file without DB record
# - Add DB record without file
# - Modify file checksum

# 2. Run reconciler
curl -X POST http://10.0.4.130:5678/webhook/reconcile

# 3. Verify detection and reporting
```

**Tasks**:
- [ ] Test orphan file detection
- [ ] Test missing file detection
- [ ] Test checksum mismatch detection
- [ ] Test manifest rebuild
- [ ] Test reconciliation report

**Success Criteria**:
- All inconsistencies detected
- Report generated
- Manifests rebuilt
- Metrics emitted

#### Agent 5: Training Orchestrator (Day 5)
**Goal**: Test training trigger workflow

**Test Scenario**:
```bash
# 1. Ensure dataset ready (balanced, sufficient size)
# 2. Trigger training
curl -X POST http://10.0.4.130:5678/webhook/train \
  -H "Content-Type: application/json" \
  -d '{"run_id": "<uuid>", "dataset_hash": "<hash>"}'

# 3. Verify TAO container launch
# 4. Monitor training progress
# 5. Verify MLflow tracking
```

**Tasks**:
- [ ] Test dataset validation
- [ ] Test TAO container launch
- [ ] Test training monitoring
- [ ] Test MLflow integration
- [ ] Test checkpoint saving
- [ ] Document training parameters

**Success Criteria**:
- TAO training starts
- MLflow logs created
- Checkpoints saved
- training.completed event emitted

---

### **Week 3: Advanced Agent Testing**

#### Agent 6: Evaluation Agent (Day 1)
**Goal**: Test model validation workflow

**Test Scenario**:
```bash
# 1. After training completes
# 2. Trigger evaluation
curl -X POST http://10.0.4.130:5678/webhook/evaluate \
  -H "Content-Type: application/json" \
  -d '{"model_path": "<path>", "test_split": "test"}'

# 3. Verify metrics computation
# - Accuracy
# - Confusion matrix
# - Per-class metrics
```

**Tasks**:
- [ ] Test model loading
- [ ] Test inference on test set
- [ ] Test metrics computation
- [ ] Test confusion matrix generation
- [ ] Test MLflow logging
- [ ] Document validation criteria

**Success Criteria**:
- Metrics computed
- Confusion matrix generated
- Results logged to MLflow
- evaluation.completed event emitted

#### Agent 7: Deployment Agent (Day 2-3)
**Goal**: Test staged deployment workflow

**Test Scenario**:
```bash
# 1. Export model to TensorRT
# 2. Deploy to shadow
curl -X POST http://10.0.4.130:5678/webhook/deploy \
  -d '{"stage": "shadow", "model_id": "<id>"}'

# 3. Test shadow deployment
# 4. Promote to canary (manual approval)
# 5. Promote to rollout (manual approval)
```

**Tasks**:
- [ ] Test TensorRT export
- [ ] Test shadow deployment
- [ ] Test canary deployment
- [ ] Test rollout deployment
- [ ] Test rollback procedure
- [ ] Test Jetson integration
- [ ] Document approval gates

**Success Criteria**:
- Model deployed to Jetson
- DeepStream pipeline updated
- Metrics show expected performance
- Rollback works

#### Agent 8: Privacy Agent (Day 4)
**Goal**: Test TTL and purge workflows

**Test Scenario**:
```bash
# 1. Create old videos in temp/
# 2. Run privacy agent
curl -X POST http://10.0.4.130:5678/webhook/privacy-check

# 3. Verify TTL enforcement
# - Videos > 7 days purged
# - Database records updated
# - Audit log created
```

**Tasks**:
- [ ] Test TTL calculation
- [ ] Test automatic purge
- [ ] Test manual purge
- [ ] Test audit logging
- [ ] Test privacy violation detection
- [ ] Document retention policies

**Success Criteria**:
- Old videos purged
- Database cleaned
- Audit trail complete
- No data leaks

#### Agent 9: Observability Agent (Day 5)
**Goal**: Test metrics and alerting

**Test Scenario**:
```bash
# 1. Generate various events
# 2. Run observability agent
curl -X POST http://10.0.4.130:5678/webhook/metrics

# 3. Verify metrics collection
# - Queue depth
# - Task latency
# - Success rate
# - Error budget
```

**Tasks**:
- [ ] Test metrics collection
- [ ] Test Prometheus export
- [ ] Test alert generation
- [ ] Test dashboard updates
- [ ] Test error budget tracking
- [ ] Document SLOs

**Success Criteria**:
- Metrics collected
- Prometheus scraping works
- Alerts fire correctly
- Dashboards updated

---

### **Week 4: End-to-End Testing**

#### Day 1-2: Full Pipeline Test
**Goal**: Run complete video → deploy workflow

**Scenario**:
1. Generate synthetic video (Luma AI)
2. Ingest → temp/
3. User labels via UI
4. Promote → dataset_all
5. Accumulate balanced dataset
6. Sample → train/test splits
7. Train EmotionNet
8. Evaluate on test set
9. Deploy to Jetson (shadow → canary → rollout)
10. Monitor live inference

**Tasks**:
- [ ] Execute full pipeline
- [ ] Monitor each agent handoff
- [ ] Verify data flow
- [ ] Test error recovery
- [ ] Test rollback at each stage
- [ ] Document timing and performance

**Success Criteria**:
- Complete pipeline executes
- Model deployed to Jetson
- Live inference working
- All metrics within SLOs

#### Day 3: Error Handling & Recovery
**Goal**: Test failure modes and recovery

**Test Scenarios**:
- [ ] Database connection failure
- [ ] File system full
- [ ] Network partition
- [ ] TAO training failure
- [ ] Deployment failure
- [ ] Corrupted video file
- [ ] Invalid label
- [ ] Checksum mismatch

**For Each Scenario**:
1. Trigger failure
2. Verify agent detection
3. Verify error handling
4. Verify recovery/rollback
5. Verify alerting
6. Document resolution

#### Day 4: Performance Testing
**Goal**: Validate performance under load

**Tests**:
- [ ] Concurrent video ingestion (10 videos)
- [ ] Rapid labeling (100 labels)
- [ ] Large dataset promotion (1000 videos)
- [ ] Training with large dataset
- [ ] High-frequency inference requests

**Metrics to Collect**:
- Ingest throughput (videos/sec)
- Label update latency (ms)
- Promotion time (sec)
- Training time (min)
- Inference latency (ms)
- Memory usage (MB)
- CPU usage (%)

#### Day 5: Documentation & Handoff
**Goal**: Document everything for production

**Tasks**:
- [ ] Create n8n setup guide
- [ ] Document each agent workflow
- [ ] Create troubleshooting runbook
- [ ] Document common issues
- [ ] Create monitoring dashboard guide
- [ ] Update memory-bank with learnings
- [ ] Create deployment checklist

---

## 📊 Success Metrics (Phase 4)

### Agent Performance
- ✅ All 9 agents operational
- ✅ < 2s average task latency
- ✅ > 99% success rate per agent
- ✅ < 1% weekly error budget

### Pipeline Performance
- ✅ End-to-end pipeline < 30 min (excluding training)
- ✅ Training time < 2 hours (depends on dataset size)
- ✅ Deployment time < 5 min
- ✅ Zero data loss

### Reliability
- ✅ Automatic recovery from transient failures
- ✅ Manual intervention < 1% of operations
- ✅ Rollback success rate 100%
- ✅ Audit trail complete

---

## 🚨 Risk Mitigation

### High Risk Items
1. **n8n Learning Curve**
   - Mitigation: Start with simple workflows, iterate
   - Fallback: Manual orchestration scripts

2. **TAO Training Failures**
   - Mitigation: Validate dataset before training
   - Fallback: Use last known good model

3. **Jetson Deployment Issues**
   - Mitigation: Test in shadow mode first
   - Fallback: Rollback to previous engine

4. **Network Reliability**
   - Mitigation: Retry logic with exponential backoff
   - Fallback: Queue operations for later

### Medium Risk Items
1. **Database Performance**
   - Mitigation: Index optimization, connection pooling
   
2. **File System Space**
   - Mitigation: Monitoring, automatic cleanup
   
3. **Agent Coordination**
   - Mitigation: Clear event contracts, idempotency

---

## 📝 Deliverables

### Week 1
- [ ] n8n installation guide
- [ ] Environment configuration document
- [ ] All 9 workflows imported and configured

### Week 2
- [ ] Individual agent test reports (1-5)
- [ ] Integration issues log
- [ ] Agent configuration updates

### Week 3
- [ ] Individual agent test reports (6-9)
- [ ] Performance benchmarks
- [ ] Troubleshooting guide

### Week 4
- [ ] End-to-end test report
- [ ] Error handling documentation
- [ ] Production readiness checklist
- [ ] Updated memory-bank

---

## 🎯 Definition of Done (Phase 4)

Phase 4 is complete when:

- ✅ All 9 agents deployed and tested
- ✅ Full pipeline executes successfully
- ✅ Error handling verified
- ✅ Performance meets SLOs
- ✅ Documentation complete
- ✅ Monitoring in place
- ✅ Team trained on operations

---

## 📞 Support & Resources

**n8n Documentation**: https://docs.n8n.io/  
**Agent Specs**: `AGENTS_08.4.2.md`  
**Requirements**: `memory-bank/requirements.md`  
**Workflow Files**: `n8n/workflows/*.json`  
**Memory Bank**: `memory-bank/` directory

---

**Next Session**: Start with n8n installation on Ubuntu 1
