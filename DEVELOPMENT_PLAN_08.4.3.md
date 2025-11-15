# Reachy Emotion Detection - Development Plan v0.08.4.3

**Date**: 2025-11-14  
**Current Version**: 0.08.4.3  
**Project Status**: Endpoint System Complete, Ready for Next Phase  
**Completion**: ~65% (Phases 1-3 complete, Phases 4-5 remaining)

---

## 📊 Project Status Overview

### Completed Phases ✅
1. **Phase 1**: Web UI & Foundation (100%)
2. **Phase 2**: ML Pipeline (100%)
3. **Phase 3**: Edge Deployment (100%)
4. **Endpoint Rewrite**: API System v1 (100%)

### Remaining Phases 🚧
4. **Phase 4**: n8n Orchestration & Agents (0%)
5. **Phase 5**: Production Hardening (0%)

---

## 🎯 Next Phase: n8n Orchestration & Agents

### Overview
Implement the 9-agent system using n8n workflows to automate the complete video → label → train → deploy pipeline.

### Agent Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     n8n Orchestration                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Agent 1: Ingest      →  Agent 2: Labeling                  │
│  Agent 3: Promotion   →  Agent 4: Reconciler                │
│  Agent 5: Training    →  Agent 6: Evaluation                │
│  Agent 7: Deployment  →  Agent 8: Privacy                   │
│  Agent 9: Observability                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Reference Documents
- `AGENTS_08.4.2.md` - Complete agent specifications
- `n8n/AGENTIC_SYSTEM_OVERVIEW.md` - System architecture
- `n8n/AGENT_SUMMARIES.md` - Individual agent details
- `n8n/workflows/*.json` - Existing workflow templates

---

## 📋 Phase 4: Detailed Task Groups

### Group 4.1: Agent Infrastructure Setup ⏱️ 2-3 hours

**Objective**: Establish foundation for agent workflows

#### Tasks
1. **n8n Environment Configuration**
   - Verify n8n installation (10.0.4.130:5678)
   - Configure environment variables
   - Set up webhook authentication
   - Test connectivity to API endpoints
   
2. **Workflow Templates**
   - Review existing workflows in `n8n/workflows/`
   - Update endpoint URLs to v1 API
   - Test basic webhook triggers
   - Document workflow patterns

3. **Database Schema Validation**
   - Verify agent-related tables exist
   - Check stored procedures for agent operations
   - Test idempotency key handling
   - Validate event logging

4. **API Integration Points**
   - Map agent actions to API endpoints
   - Document request/response formats
   - Create test payloads
   - Verify authentication

**Deliverables**:
- [ ] n8n connection verified
- [ ] Workflow templates updated
- [ ] Database schema validated
- [ ] API integration documented

**Testing**:
```bash
# Test n8n connectivity
curl http://10.0.4.130:5678/healthz

# Test webhook
curl -X POST http://10.0.4.130:5678/webhook/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Validate database
psql reachy_local -c "SELECT * FROM pg_tables WHERE schemaname='public';"
```

---

### Group 4.2: Core Agent Implementation ⏱️ 4-5 hours

**Objective**: Implement the 9 core agents

#### Agent 1: Ingest Agent
**Purpose**: Receive and register new videos

**Workflow Steps**:
1. Receive upload/generation event
2. Compute SHA256 checksum
3. Store video in `/videos/temp/`
4. Extract metadata (duration, fps, resolution)
5. Generate thumbnail
6. Persist to database
7. Emit `ingest.completed` event

**API Endpoints Used**:
- `POST /api/media/ingest` (Gateway)
- `POST /api/v1/media/register` (if needed)

**Implementation**:
- File: `n8n/workflows/01_ingest_agent.json`
- Test: Create test workflow
- Validate: Upload test video

---

#### Agent 2: Labeling Agent
**Purpose**: Manage user-assisted classification

**Workflow Steps**:
1. Listen for labeling requests from UI
2. Validate label (`happy`, `sad`, etc.)
3. Update database with label
4. Check class balance
5. Emit `labeling.completed` event

**API Endpoints Used**:
- `POST /api/v1/promote/stage` (with label)
- `GET /api/v1/media/list?split=dataset_all`

**Implementation**:
- File: `n8n/workflows/02_labeling_agent.json`
- Test: Label test videos
- Validate: Check database updates

---

#### Agent 3: Promotion/Curation Agent
**Purpose**: Move media between filesystem stages

**Workflow Steps**:
1. Receive promotion request
2. Validate destination split
3. Check class balance constraints
4. Execute filesystem move
5. Update database transactionally
6. Emit `promotion.completed` event

**API Endpoints Used**:
- `POST /api/v1/promote/stage` (temp → dataset_all)
- `POST /api/v1/promote/sample` (dataset_all → train/test)

**Implementation**:
- File: `n8n/workflows/03_promotion_agent.json`
- Test: Promote test videos
- Validate: Verify filesystem and DB

---

#### Agent 4: Reconciler/Audit Agent
**Purpose**: Ensure filesystem and database consistency

**Workflow Steps**:
1. Scan filesystem directories
2. Compute checksums
3. Compare with database
4. Detect orphans/duplicates
5. Rebuild manifests if needed
6. Emit `reconcile.report` event

**API Endpoints Used**:
- `GET /api/v1/media/list` (all splits)
- `POST /api/v1/promote/reset-manifest`

**Implementation**:
- File: `n8n/workflows/04_reconciler_agent.json`
- Schedule: Cron (daily at 2 AM)
- Test: Run manual reconciliation
- Validate: Check manifest files

---

#### Agent 5: Training Orchestrator
**Purpose**: Trigger EmotionNet fine-tuning

**Workflow Steps**:
1. Check dataset balance and size
2. Validate minimum thresholds
3. Generate training manifest
4. Launch TAO training container
5. Monitor training progress
6. Record metrics to MLflow
7. Emit `training.completed` event

**API Endpoints Used**:
- `GET /api/v1/media/list?split=train`
- Training script: `trainer/train_emotionnet.py`

**Implementation**:
- File: `n8n/workflows/05_training_agent.json`
- Trigger: Manual or scheduled
- Test: Run with small dataset
- Validate: Check MLflow artifacts

---

#### Agent 6: Evaluation Agent
**Purpose**: Run validation jobs

**Workflow Steps**:
1. Check test set balance
2. Load trained model
3. Run inference on test set
4. Compute metrics (accuracy, F1)
5. Generate confusion matrix
6. Record to MLflow
7. Emit `evaluation.completed` event

**API Endpoints Used**:
- `GET /api/v1/media/list?split=test`
- Evaluation script: `trainer/eval/evaluate_model.py`

**Implementation**:
- File: `n8n/workflows/06_evaluation_agent.json`
- Trigger: After training completion
- Test: Evaluate test model
- Validate: Check metrics

---

#### Agent 7: Deployment Agent
**Purpose**: Promote validated engines to Jetson

**Workflow Steps**:
1. Validate evaluation metrics (Gate A/B/C)
2. Export model to TensorRT
3. Copy engine to Jetson
4. Update DeepStream config
5. Restart Jetson service
6. Verify live metrics
7. Emit `deployment.completed` event

**API Endpoints Used**:
- Export script: `trainer/export_to_trt.py`
- Jetson deployment: `jetson/deploy.sh`

**Implementation**:
- File: `n8n/workflows/07_deployment_agent.json`
- Trigger: Manual approval after evaluation
- Test: Deploy to test Jetson
- Validate: Check FPS and latency

---

#### Agent 8: Privacy/Retention Agent
**Purpose**: Enforce local-first policy and TTLs

**Workflow Steps**:
1. Scan temp directory for old files
2. Check TTL (default: 7 days)
3. Delete expired videos
4. Update database
5. Log purge events
6. Emit `privacy.purged` event

**API Endpoints Used**:
- `POST /api/privacy/redact/{video_id}` (Gateway)
- `DELETE /api/v1/media/{video_id}` (if needed)

**Implementation**:
- File: `n8n/workflows/08_privacy_agent.json`
- Schedule: Cron (daily at 3 AM)
- Test: Create old test files
- Validate: Check deletion logs

---

#### Agent 9: Observability/Telemetry Agent
**Purpose**: Aggregate metrics and raise alerts

**Workflow Steps**:
1. Collect metrics from all agents
2. Compute aggregates (queue depth, latency, success rate)
3. Check SLO thresholds
4. Publish to Prometheus
5. Emit alerts if thresholds breached
6. Update Grafana dashboards

**API Endpoints Used**:
- `GET /api/v1/health` (all services)
- Prometheus push gateway

**Implementation**:
- File: `n8n/workflows/09_observability_agent.json`
- Schedule: Cron (every 5 minutes)
- Test: Generate test metrics
- Validate: Check Prometheus

---

**Deliverables**:
- [ ] All 9 agents implemented
- [ ] Workflows tested individually
- [ ] End-to-end flow validated
- [ ] Documentation updated

**Testing Strategy**:
1. Unit test each agent workflow
2. Integration test agent chains
3. End-to-end test full pipeline
4. Load test with multiple videos

---

### Group 4.3: Event-Driven Architecture ⏱️ 2-3 hours

**Objective**: Implement event bus and message routing

#### Tasks
1. **Event Schema Definition**
   - Define event types and payloads
   - Create JSON schemas
   - Document event flows
   - Implement validation

2. **Message Queue Setup**
   - Configure n8n queue settings
   - Set up retry policies
   - Implement dead letter queue
   - Test message persistence

3. **Event Routing**
   - Map events to agent triggers
   - Implement correlation IDs
   - Set up event logging
   - Test event propagation

4. **Idempotency Handling**
   - Implement idempotency keys
   - Create deduplication logic
   - Test retry scenarios
   - Validate database constraints

**Deliverables**:
- [ ] Event schemas defined
- [ ] Message queue configured
- [ ] Event routing tested
- [ ] Idempotency validated

---

### Group 4.4: Workflow Orchestration ⏱️ 2-3 hours

**Objective**: Connect agents into cohesive workflows

#### Tasks
1. **Pipeline Coordination**
   - Define workflow sequences
   - Implement approval gates
   - Set up human-in-the-loop
   - Test pipeline execution

2. **Error Handling**
   - Implement retry logic
   - Set up circuit breakers
   - Create error notifications
   - Test failure scenarios

3. **Monitoring Integration**
   - Add workflow metrics
   - Implement progress tracking
   - Create status dashboards
   - Test observability

4. **Documentation**
   - Document workflow patterns
   - Create runbooks
   - Write troubleshooting guides
   - Update agent specs

**Deliverables**:
- [ ] Workflows orchestrated
- [ ] Error handling tested
- [ ] Monitoring integrated
- [ ] Documentation complete

---

## 📋 Phase 5: Production Hardening

### Group 5.1: Comprehensive Monitoring ⏱️ 3-4 hours

**Objective**: Full observability stack

#### Tasks
1. **Prometheus Setup**
   - Install Prometheus
   - Configure scrape targets
   - Set up service discovery
   - Test metric collection

2. **Grafana Dashboards**
   - Create system overview dashboard
   - Add agent-specific dashboards
   - Implement alerting rules
   - Test visualization

3. **Logging Infrastructure**
   - Centralize logs (ELK/Loki)
   - Implement structured logging
   - Set up log rotation
   - Test log aggregation

4. **Alerting**
   - Define alert rules
   - Configure notification channels
   - Test alert delivery
   - Document escalation

**Deliverables**:
- [ ] Prometheus operational
- [ ] Grafana dashboards created
- [ ] Logging centralized
- [ ] Alerting configured

---

### Group 5.2: Backup & Recovery ⏱️ 2-3 hours

**Objective**: Data protection and disaster recovery

#### Tasks
1. **Database Backups**
   - Implement automated backups
   - Set up backup retention
   - Test restore procedures
   - Document recovery steps

2. **Filesystem Backups**
   - Configure NAS rsync
   - Set up snapshot schedule
   - Test file recovery
   - Validate checksums

3. **Model Versioning**
   - Implement model registry
   - Track model lineage
   - Enable rollback capability
   - Test version switching

4. **Disaster Recovery Plan**
   - Document recovery procedures
   - Create runbooks
   - Test DR scenarios
   - Update documentation

**Deliverables**:
- [ ] Backups automated
- [ ] Recovery tested
- [ ] Model versioning implemented
- [ ] DR plan documented

---

### Group 5.3: Performance Optimization ⏱️ 2-3 hours

**Objective**: Optimize system performance

#### Tasks
1. **API Performance**
   - Profile endpoint latency
   - Optimize database queries
   - Implement caching
   - Test under load

2. **Jetson Optimization**
   - Tune DeepStream pipeline
   - Optimize TensorRT engine
   - Reduce memory usage
   - Test FPS and latency

3. **Training Optimization**
   - Optimize data loading
   - Tune batch sizes
   - Implement mixed precision
   - Test training speed

4. **Benchmarking**
   - Create performance tests
   - Establish baselines
   - Document targets
   - Monitor regressions

**Deliverables**:
- [ ] API optimized
- [ ] Jetson tuned
- [ ] Training accelerated
- [ ] Benchmarks established

---

### Group 5.4: Security Hardening ⏱️ 2-3 hours

**Objective**: Secure the system

#### Tasks
1. **Authentication & Authorization**
   - Implement JWT tokens
   - Set up RBAC
   - Secure API endpoints
   - Test access control

2. **Network Security**
   - Configure firewall rules
   - Set up mTLS
   - Implement rate limiting
   - Test security

3. **Secrets Management**
   - Use environment variables
   - Implement secrets vault
   - Rotate credentials
   - Audit access

4. **Security Audit**
   - Run vulnerability scan
   - Review code for issues
   - Test penetration
   - Document findings

**Deliverables**:
- [ ] Authentication implemented
- [ ] Network secured
- [ ] Secrets managed
- [ ] Security audited

---

### Group 5.5: Documentation & Training ⏱️ 2-3 hours

**Objective**: Complete documentation

#### Tasks
1. **User Documentation**
   - Write user guides
   - Create video tutorials
   - Document workflows
   - Test with users

2. **Developer Documentation**
   - API documentation
   - Architecture diagrams
   - Code comments
   - Contributing guide

3. **Operations Documentation**
   - Deployment guide
   - Runbooks
   - Troubleshooting guide
   - Maintenance procedures

4. **Training Materials**
   - Create training deck
   - Record demos
   - Write FAQs
   - Conduct training

**Deliverables**:
- [ ] User docs complete
- [ ] Developer docs complete
- [ ] Operations docs complete
- [ ] Training conducted

---

## 🎯 Implementation Strategy

### Approach: Iterative Development

1. **Group Tasks Logically** ✅
   - Related functionality grouped
   - Dependencies identified
   - Priorities assigned

2. **Recommend Related Code**
   - Identify relevant files
   - Review existing implementations
   - Document patterns

3. **Test Recommended Code**
   - Write unit tests
   - Run integration tests
   - Validate functionality

4. **Implement After Testing**
   - Only implement tested code
   - Follow test-driven approach
   - Maintain quality

5. **Summarize Completed Groups**
   - Document what was done
   - Update status
   - Monitor token usage

6. **Continue Forward**
   - Move to next group
   - Maintain momentum
   - Track progress

---

## 📊 Progress Tracking

### Phase 4: n8n Orchestration (0%)
- [ ] Group 4.1: Agent Infrastructure (0%)
- [ ] Group 4.2: Core Agents (0%)
- [ ] Group 4.3: Event Architecture (0%)
- [ ] Group 4.4: Workflow Orchestration (0%)

### Phase 5: Production Hardening (0%)
- [ ] Group 5.1: Monitoring (0%)
- [ ] Group 5.2: Backup & Recovery (0%)
- [ ] Group 5.3: Performance (0%)
- [ ] Group 5.4: Security (0%)
- [ ] Group 5.5: Documentation (0%)

---

## 🔧 Prerequisites

### Before Starting Phase 4

1. **Configuration Updated** ⚠️
   - [ ] Create `apps/api/.env`
   - [ ] Update `apps/web/.env`
   - [ ] Validate configuration
   - [ ] Test endpoints

2. **Services Running**
   - [ ] API service (port 8083)
   - [ ] Nginx (port 8082)
   - [ ] PostgreSQL (port 5432)
   - [ ] n8n (port 5678)

3. **Database Ready**
   - [ ] Schema migrated
   - [ ] Stored procedures created
   - [ ] Test data loaded

4. **n8n Configured**
   - [ ] n8n installed
   - [ ] Credentials configured
   - [ ] Webhooks tested

---

## 📈 Success Metrics

### Phase 4 Completion Criteria
- ✅ All 9 agents implemented
- ✅ End-to-end pipeline functional
- ✅ Events flowing correctly
- ✅ Tests passing (>90%)
- ✅ Documentation updated

### Phase 5 Completion Criteria
- ✅ Monitoring operational
- ✅ Backups automated
- ✅ Performance optimized
- ✅ Security hardened
- ✅ Documentation complete

---

## 🚀 Quick Start Commands

### Configuration Setup
```bash
# Create API .env
cp apps/api/.env.template apps/api/.env
nano apps/api/.env

# Update Web .env
cp apps/web/.env apps/web/.env.backup
cp apps/web/.env.template apps/web/.env
# Restore API keys from backup

# Validate
python -c "from apps.api.app.config import load_and_validate_config; load_and_validate_config()"
```

### Service Management
```bash
# Start services
./scripts/service-start.sh

# Check status
./scripts/service-status.sh

# View logs
journalctl -u fastapi-media.service -f
```

### Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Run specific phase tests
python -m pytest tests/test_config.py -v
python -m pytest tests/test_v1_endpoints.py -v
python -m pytest tests/test_integration_full.py -v
```

---

## 📚 Reference Documents

### Core Documentation
- `AGENTS_08.4.2.md` - Agent specifications
- `API_ENDPOINT_REFERENCE.md` - API documentation
- `ENDPOINT_REWRITE_PROJECT_COMPLETE.md` - Endpoint system
- `IMPLEMENTATION_STATUS.md` - Current status
- `CONFIG_UPDATE_GUIDE.md` - Configuration guide

### n8n Documentation
- `n8n/AGENTIC_SYSTEM_OVERVIEW.md` - System overview
- `n8n/AGENT_SUMMARIES.md` - Agent details
- `n8n/DELIVERY_SUMMARY.md` - Delivery status
- `n8n/workflows/*.json` - Workflow templates

### Memory Bank
- `memory-bank/index.md` - Entry point
- `memory-bank/decisions/` - Design decisions
- `memory-bank/runbooks/` - Operations guides

---

## 🎓 Development Principles

1. **Test-Driven Development**
   - Write tests first
   - Implement to pass tests
   - Refactor with confidence

2. **Incremental Progress**
   - Small, focused changes
   - Frequent commits
   - Regular testing

3. **Documentation First**
   - Document before implementing
   - Keep docs updated
   - Write clear comments

4. **Quality Over Speed**
   - Maintain test coverage
   - Follow best practices
   - Review code carefully

5. **Token Management**
   - Monitor usage
   - Summarize regularly
   - Stay within limits

---

## 📞 Support & Resources

### Project Information
- **Project Root**: `/home/rusty_admin/projects/reachy_08.4.2`
- **Python Version**: 3.12
- **Test Framework**: pytest
- **Workflow Engine**: n8n

### Key Contacts
- **Project Owner**: Russell Bray (rustybee255@gmail.com)
- **Repository**: (if applicable)

---

**Last Updated**: 2025-11-14  
**Version**: 0.08.4.3  
**Status**: Ready for Phase 4 Implementation 🚀  
**Estimated Time**: Phase 4: 10-14 hours, Phase 5: 11-16 hours
