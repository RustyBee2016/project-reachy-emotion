# Nine Agentic AI Workflows - Complete Summary

## Overview

This document provides a comprehensive summary of all 9 AI agents that power the Reachy_Local_08.4.2 emotion recognition system. Each agent is implemented as an n8n workflow that orchestrates specific responsibilities in the video processing → training → deployment pipeline.

---

## Agent 1: Ingest Agent

### Purpose
Receives video uploads or generation callbacks and atomically registers them in the system with full metadata.

### Key Responsibilities
- Accept webhook POST requests from web UI or video generation services
- Authenticate incoming requests via X-INGEST-KEY header
- Normalize payloads from various sources (Luma, Runway, direct upload)
- Call Media Mover API to pull video by URL (avoiding n8n data transfer)
- Poll Media Mover status until hash, ffprobe, and thumbnail complete
- Insert video metadata to PostgreSQL with deduplication (SHA256 + size_bytes)
- Emit `ingest.completed` event for downstream consumers

### Benefits to Project
- **Data Integrity**: Every video is hashed and validated before processing
- **Idempotency**: Duplicate uploads are prevented via unique constraints
- **Scalability**: n8n doesn't handle video bytes; Media Mover does the heavy lifting
- **Audit Trail**: Full correlation IDs and timestamps for every ingest
- **Error Recovery**: Retry logic with exponential backoff on transient failures

### Workflow File
`01_ingest_agent.json`

---

## Agent 2: Labeling Agent

### Purpose
Processes human labels from the web UI and maintains the single source of truth for video labels while enforcing class balance constraints.

### Key Responsibilities
- Receive label submissions via webhook (POST /label)
- Validate payload (video_id, label, action)
- Fetch existing video record from PostgreSQL
- Insert to `label_event` audit table (append-only)
- Update `video.label` field (source of truth)
- Branch on action: `label_only`, `promote_train`, `promote_test`, `discard`
- Call Media Mover `/api/relabel` or `/api/promote` as needed
- Query class balance stats (happy vs sad counts)
- Return updated balance status to UI

### Benefits to Project
- **Single Source of Truth**: DB is authoritative for labels; manifests are derived
- **Class Balance Enforcement**: Prevents imbalanced datasets (50/50 ± 5%)
- **Audit Trail**: `label_event` table tracks every labeling decision with rater_id
- **UI Responsiveness**: Immediate feedback on class distribution
- **Promotion Coordination**: Triggers Promotion Agent when user approves

### Workflow File
`02_labeling_agent.json`

---

## Agent 3: Promotion/Curation Agent

### Purpose
Safely moves videos from `temp` → `train`/`test` with dry-run preview, human approval, and manifest rebuild.

### Key Responsibilities
- Validate promotion request (video_id, label, target split)
- Generate stable idempotency key (SHA256 of video_id|target|label)
- Execute dry-run promotion via Media Mover
- Summarize plan (files to move, DB updates, conflicts)
- Wait for human approval via webhook or Slack
- If approved: execute real promotion (atomic FS move + DB update)
- Rebuild manifests for train/test splits
- Emit `promotion.completed` event with dataset_hash
- Log to metrics for Observability Agent

### Benefits to Project
- **Safety**: Dry-run prevents accidental data loss
- **Rollback**: Approval gate allows review before irreversible changes
- **Manifest Integrity**: Manifests always reflect current dataset state
- **Idempotency**: Retry-safe even if network fails mid-promotion
- **Observability**: Full correlation IDs for end-to-end trace

### Workflow File
`03_promotion_agent.json`

---

## Agent 4: Reconciler/Audit Agent

### Purpose
Detects filesystem ↔ database drift and enforces consistency without destructive actions by default.

### Key Responsibilities
- Triggered daily at 02:15 AM (also supports manual webhook)
- SSH to Ubuntu 1 and enumerate `/videos/{temp,train,test,dataset_all}`
- Parse JSONL output into structured items
- Query PostgreSQL for all `video` records
- Diff filesystem vs database to find:
  - **Orphans**: Files on disk but not in DB
  - **Missing**: DB records with no matching file
  - **Mismatches**: Size or split discrepancies
- Generate report (counts, details, timestamp)
- If `safe_fix=true`: update DB split for benign changes
- Email summary report to maintainer
- Never delete files automatically (respects safety policy)

### Benefits to Project
- **Data Integrity**: Catches orphaned uploads and missing files early
- **Troubleshooting**: Identifies drift before training failures occur
- **Compliance**: Audit reports support data governance requirements
- **Safety**: Read-only by default; fixes require explicit flag
- **Alerting**: Email notifications enable proactive maintenance

### Workflow File
`04_reconciler_agent.json`

---

## Agent 5: Training Orchestrator

### Purpose
Triggers TAO fine-tuning when dataset is ready, tracks lineage in MLflow, validates Gate A metrics, and exports TensorRT engines.

### Key Responsibilities
- Receive `dataset.promoted` webhook with dataset_hash and manifest_path
- Create MLflow run with tags (dataset_hash, correlation_id)
- SSH to Ubuntu 1 and launch TAO training (detached via nohup)
- Poll for `summary.json` every 5 minutes using Wait node
- Parse metrics: macro_f1, balanced_accuracy, ECE, Brier score, per-class F1
- Log params/metrics/artifacts to MLflow
- Validate **Gate A-val** thresholds (synthetic validation):
  - Macro F1 ≥ 0.84
  - Balanced accuracy ≥ 0.85
  - ECE ≤ 0.12, Brier ≤ 0.16
- **Gate A-deploy** (real-world test): F1 ≥ 0.75, ECE ≤ 0.12 (see ADR 011)
- If pass: export to TensorRT FP16, log .engine artifact
- If fail: mark run as failed, emit `training.failed` event
- Emit `training.completed` with engine_path for Evaluation Agent

### Benefits to Project
- **Quality Gates**: Prevents poor models from reaching deployment
- **Lineage Tracking**: MLflow ties models to exact dataset versions
- **Async Design**: Wait node offloads state; doesn't block n8n workers for hours
- **Reproducibility**: Optional ZFS snapshot support for exact dataset rollback
- **Automation**: Triggers automatically when dataset balance met

### Workflow File
`05_training_orchestrator.json`

---

## Agent 6: Evaluation Agent

### Purpose
Runs validation on the test set once balanced, produces confusion matrix and Gate B/C metrics for deployment decisions.

### Key Responsibilities
- Triggered by `evaluation.start` webhook (manual or post-training)
- Query PostgreSQL: verify `min(happy_test, sad_test) ≥ TEST_MIN_PER_CLASS`
- If balanced: SSH to Jetson and run DeepStream inference on `/videos/test/`
- Parse predictions from DeepStream output
- Compute metrics: accuracy, F1, confusion matrix
- Log to MLflow (test_accuracy, latency metrics)
- Validate **Gate B** thresholds:
  - On-device latency p95 ≤ 250ms
  - Macro F1 ≥ 0.80
- Emit `evaluation.completed` with gate decision (pass/fail)
- Never attaches labels to test videos internally (privacy constraint)

### Benefits to Project
- **Gate B Validation**: Ensures on-device performance before canary deploy
- **Privacy Preservation**: Test set remains unlabeled throughout inference
- **Real-World Metrics**: Jetson latency reflects actual robot conditions
- **MLflow Integration**: Evaluation metrics tied to training run
- **Decision Support**: Pass/fail status guides Deployment Agent

### Workflow File
`06_evaluation_agent.json`

---

## Agent 7: Deployment Agent

### Purpose
Promotes TRT engines through shadow → canary → rollout stages with health checks and instant rollback capability.

### Key Responsibilities
- Receive `deployment.promote` webhook with engine_path and target_stage
- Branch on stage:
  - **Shadow**: Copy .engine to Jetson shadow slot (no traffic routing)
  - **Canary**: Deploy to canary slot, restart canary service, wait 30 min
  - **Rollout**: Promote canary engine to production, restart main service
- After each stage: poll Jetson `/healthz` endpoint
- Check GPU temperature via `tegrastats` (optional)
- If health checks fail: rollback to prior engine (automatic or manual)
- Log deployment metadata to `deployment_log` table
- Emit `deployment.completed` or `deployment.rolled_back` event

### Benefits to Project
- **Gradual Rollout**: Shadow validates engine loading; canary tests 10% traffic
- **Risk Mitigation**: 30-min canary soak detects regressions before full rollout
- **Instant Rollback**: Copy operation restores prior engine in seconds
- **Observability**: Health checks and metrics inform rollback decisions
- **Approval Gates**: Two-stage human approval (shadow→canary, canary→rollout)

### Workflow File
`07_deployment_agent.json`

---

## Agent 8: Privacy/Retention Agent

### Purpose
Enforces TTL policies on temp videos, supports GDPR deletion requests, and maintains audit logs for compliance.

### Key Responsibilities
- Triggered daily at 03:00 AM (also supports manual webhook for GDPR)
- Query PostgreSQL: find videos in `temp` older than TTL_DAYS_TEMP (default 14)
- Batch process deletions (50 videos per batch)
- SSH to Ubuntu 1 and `rm -f` each file
- Update PostgreSQL: set `split='purged'` (soft delete, not hard delete)
- Insert to `audit_log` table with action, video_id, reason, timestamp
- Emit `privacy.purged` event with count
- Support manual deletion requests (pass video_id in webhook payload)

### Benefits to Project
- **Compliance**: GDPR "right to be forgotten" support
- **Storage Management**: Prevents temp folder bloat
- **Audit Trail**: Every deletion logged with reason and operator
- **Safety**: Soft delete in DB allows recovery if needed
- **Automation**: Daily cleanup runs unattended

### Workflow File
`08_privacy_agent.json`

---

## Agent 9: Observability/Telemetry Agent

### Purpose
Aggregates metrics from all services, detects SLA breaches, and routes alerts to maintainers.

### Key Responsibilities
- Cron trigger every 30 seconds
- HTTP GET `/metrics` from:
  - n8n (http://n8n:5678/metrics)
  - Media Mover (http://10.0.4.130:9101/metrics)
  - Gateway (http://10.0.4.140:9100/metrics)
- Parse Prometheus exposition format (text)
- Extract key metrics:
  - `n8n_active_executions`, `n8n_workflow_errors_total`
  - `media_mover_promote_total`, `media_mover_promote_errors_total`
  - `gateway_ws_active`, `gateway_queue_depth`
- Store to `obs_samples` PostgreSQL table
- Companion workflows (9B, 9C) handle:
  - **Error → Incident**: Catch workflow failures, create incident records, notify Slack
  - **SLO Watchdog**: Evaluate thresholds every 5 min, trigger safe mode on breach

### Benefits to Project
- **Real-Time Visibility**: Metrics updated every 30s for dashboards
- **Proactive Alerting**: SLO watchdog detects issues before outages
- **Incident Management**: Error Trigger auto-creates tickets with correlation IDs
- **Performance Tuning**: Historical metrics enable capacity planning
- **Integration**: Prometheus format allows Grafana dashboards

### Workflow Files
- `09_observability_agent.json` (metrics collector)
- Additional workflows for error handling and SLO monitoring (create as needed)

---

## Cross-Agent Benefits

### Event-Driven Architecture
- Agents communicate via webhooks and events (not tight coupling)
- Correlation IDs propagate through entire pipeline for end-to-end tracing
- Enables async workflows (e.g., Training Orchestrator doesn't block Promotion)

### Idempotency Everywhere
- All mutating operations use idempotency keys (SHA256-based or client-provided)
- Database constraints prevent duplicate writes
- Retry-safe: network failures don't corrupt data

### Observability Built-In
- Every agent emits events to Observability Agent
- Metrics, logs, and traces available for every operation
- Correlation IDs link events across agent boundaries

### Human-in-the-Loop
- Approval gates for critical operations (Promotion, Deployment)
- Dry-run previews before irreversible changes
- Email/Slack notifications for anomalies

### Privacy-First
- No raw video passes through n8n workflows
- Test set remains unlabeled (Agent 6 respects this)
- Privacy Agent enforces TTL and GDPR compliance
- Audit logs for every deletion

### Deployment Safety
- Multi-stage rollout (shadow → canary → rollout)
- Health checks at every stage
- Instant rollback capability
- Gate A/B/C validation prevents bad models from reaching production

---

## Integration with Claude Sonnet 4.5

### How Claude Powers the Agents

1. **Workflow Design**: Claude analyzes requirements and generates optimal node graphs
2. **Error Handling**: Thinking model reasons about failure modes and retry strategies
3. **Validation**: Claude validates workflows against project constraints before deployment
4. **Optimization**: Suggests performance improvements based on execution patterns
5. **Documentation**: Auto-generates runbooks and troubleshooting guides

### n8n MCP Server Enables

1. **Programmatic Deployment**: Create/update workflows via API
2. **Validation**: Pre-flight checks before activating workflows
3. **Monitoring**: Query execution history and performance metrics
4. **Template Discovery**: Find community patterns for common tasks
5. **Schema Exploration**: Get node configurations and examples dynamically

---

## Deployment Checklist

- [ ] Import all 9 workflow JSON files to n8n
- [ ] Configure credentials:
  - PostgreSQL connection (reachy_local database)
  - SSH keys for Ubuntu 1 and Jetson
  - HTTP auth for Media Mover API
  - Email/Slack for notifications
- [ ] Set environment variables:
  - `MEDIA_MOVER_BASE_URL=http://10.0.4.130:8081/api`
  - `GATEWAY_BASE_URL=http://10.0.4.140:8000`
  - `MLFLOW_URL=http://10.0.4.130:5000`
  - `INGEST_TOKEN=<secure_token>`
- [ ] Create database tables:
  - `label_event`, `reconcile_report`, `deployment_log`, `audit_log`, `obs_samples`
- [ ] Activate workflows in n8n UI
- [ ] Test each webhook endpoint
- [ ] Verify metrics collection (Agent 9)
- [ ] Run manual reconciler audit (Agent 4)

---

## Monitoring & Maintenance

### Daily Checks
- Review Agent 4 (Reconciler) email reports for drift
- Check Agent 9 (Observability) dashboards for SLA breaches
- Verify Agent 8 (Privacy) purge logs for compliance

### Weekly Checks
- Audit Agent 7 (Deployment) logs for rollbacks
- Review Agent 5 (Training) MLflow runs for quality trends
- Inspect Agent 2 (Labeling) class balance stats

### Monthly Checks
- Agent 1 (Ingest) deduplication rate (high rate may indicate upstream issue)
- Agent 3 (Promotion) approval delays (long delays may indicate UX problem)
- Agent 6 (Evaluation) Gate B pass rate (low rate may indicate model drift)

---

## Future Enhancements

1. **Agent 10: Generation Balancer** (optional)
   - Monitors class ratios
   - Biases synthetic video generation toward underrepresented classes
   - Integrates with Luma/Runway APIs

2. **Advanced Claude Integration**
   - Code nodes calling Claude API for adaptive thresholds
   - Anomaly detection in Reconciler Agent
   - Automated workflow optimization

3. **Distributed Tracing**
   - OpenTelemetry export from n8n
   - Jaeger UI for end-to-end visualization

4. **Multi-Tenancy**
   - Per-user workflows with isolated credentials
   - Row-level security in PostgreSQL

---

**Version**: 1.0.0  
**Last Updated**: 2025-11-07  
**Maintainer**: Russell Bray (rustybee255@gmail.com)  
**Total Workflows**: 9  
**Total Nodes**: ~120 across all workflows  
**Lines of Configuration**: ~2000 JSON lines
