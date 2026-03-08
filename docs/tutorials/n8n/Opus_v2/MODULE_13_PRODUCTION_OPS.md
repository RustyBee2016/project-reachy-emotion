# MODULE 13 -- Production Operations

**Duration:** ~2 hours
**Prerequisites:** MODULES 00-12 complete
**Outcome:** Operational procedures for running the Reachy agentic AI system in production, including backup/restore, monitoring, scaling, and maintenance

---

## 13.1 Production Readiness

Before going live, verify the entire system is production-ready using this checklist.

### Infrastructure Checklist

| Component | Host | Port | Status |
|-----------|------|------|--------|
| n8n | Ubuntu 1 (10.0.4.130) | 5678 | [ ] Running |
| PostgreSQL | Ubuntu 1 (10.0.4.130) | 5432 | [ ] Running |
| Media Mover API | Ubuntu 1 (10.0.4.130) | 8083 | [ ] Running |
| MLflow | Ubuntu 1 (10.0.4.130) | 5000 | [ ] Running |
| FastAPI Gateway | Ubuntu 2 (10.0.4.140) | 8000 | [ ] Running |
| DeepStream Pipeline | Jetson | -- | [ ] Running |
| Emotion Client | Jetson | -- | [ ] Connected |

### Workflow Activation Checklist

| # | Workflow | Active | Error Handler | Timeout |
|---|----------|--------|---------------|---------|
| 01 | Ingest Agent | [ ] | [ ] | 30 min |
| 02 | Labeling Agent | [ ] | [ ] | 30 min |
| 03 | Promotion Agent | [ ] | [ ] | 30 min |
| 04 | Reconciler Agent | [ ] | [ ] | 30 min |
| 05 | Privacy Agent | [ ] | [ ] | 30 min |
| 06 | Training Orchestrator | [ ] | [ ] | 120 min |
| 07 | Evaluation Agent | [ ] | [ ] | 30 min |
| 08 | Deployment Agent | [ ] | [ ] | 60 min |
| 09 | Observability Agent | [ ] | [ ] | 5 min |
| 10 | ML Pipeline Orchestrator | [ ] | [ ] | 240 min |
| -- | Error Handler (Global) | [ ] | N/A | 10 min |

---

## 13.2 Backup & Restore

### n8n Workflow Backup

n8n stores workflows in its own database. Export them regularly:

```bash
#!/bin/bash
# backup_n8n_workflows.sh
# Run daily via cron: 0 2 * * * /path/to/backup_n8n_workflows.sh

BACKUP_DIR="/home/reachy/backups/n8n/$(date +%Y-%m-%d)"
mkdir -p "$BACKUP_DIR"

# Export all workflows via CLI
n8n export:workflow --all --output="$BACKUP_DIR/"

# Export credentials (encrypted)
n8n export:credentials --all --output="$BACKUP_DIR/"

# Count exports
WF_COUNT=$(ls "$BACKUP_DIR"/*.json 2>/dev/null | wc -l)
echo "Backed up $WF_COUNT workflows to $BACKUP_DIR"

# Retain 30 days of backups
find /home/reachy/backups/n8n -maxdepth 1 -type d -mtime +30 -exec rm -rf {} \;
```

### PostgreSQL Backup

```bash
#!/bin/bash
# backup_postgres.sh
# Run daily via cron: 0 3 * * * /path/to/backup_postgres.sh

BACKUP_DIR="/home/reachy/backups/postgres"
mkdir -p "$BACKUP_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# Full database dump
pg_dump -h localhost -U reachy_dev -d reachy_emotion \
  --format=custom \
  --file="$BACKUP_DIR/reachy_emotion_${TIMESTAMP}.dump"

echo "Database backed up: reachy_emotion_${TIMESTAMP}.dump"

# Retain 14 days
find "$BACKUP_DIR" -name "*.dump" -mtime +14 -delete
```

### Restore Procedures

**Restore n8n workflows:**
```bash
# Import a single workflow
n8n import:workflow --input=/path/to/workflow.json

# Import all workflows from backup
n8n import:workflow --input=/home/reachy/backups/n8n/2026-03-01/
```

**Restore PostgreSQL:**
```bash
# Restore full database (WARNING: overwrites existing data)
pg_restore -h localhost -U reachy_dev -d reachy_emotion \
  --clean --if-exists \
  /home/reachy/backups/postgres/reachy_emotion_20260301_030000.dump
```

**Restore a single table:**
```bash
pg_restore -h localhost -U reachy_dev -d reachy_emotion \
  --table=video --clean --if-exists \
  /home/reachy/backups/postgres/reachy_emotion_20260301_030000.dump
```

---

## 13.3 Monitoring & Alerting

### Dashboard Queries

Use these SQL queries to build a monitoring dashboard or run them manually to check system health.

#### Data Pipeline Health

```sql
-- Ingestion rate (last 24 hours, by hour)
SELECT
  date_trunc('hour', created_at) AS hour,
  COUNT(*) AS ingested
FROM video
WHERE created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;

-- Current dataset split distribution
SELECT
  split,
  label,
  COUNT(*) AS count
FROM video
WHERE split IS NOT NULL
GROUP BY split, label
ORDER BY split, label;

-- Promotion backlog (labeled but not promoted)
SELECT COUNT(*) AS pending_promotion
FROM video
WHERE label IS NOT NULL
  AND split IS NULL;
```

#### ML Pipeline Health

```sql
-- Recent training runs
SELECT
  run_id,
  status,
  start_time,
  end_time,
  end_time - start_time AS duration
FROM mlflow_runs
ORDER BY start_time DESC
LIMIT 5;

-- Model deployment history
SELECT
  model_version,
  deployed_at,
  gate_b_passed,
  deployment_target
FROM deployment_log
ORDER BY deployed_at DESC
LIMIT 5;
```

#### Error Rates

```sql
-- Errors in last 24 hours by workflow
SELECT
  workflow_name,
  severity,
  COUNT(*) AS error_count
FROM error_log
WHERE ts > NOW() - INTERVAL '24 hours'
GROUP BY workflow_name, severity
ORDER BY error_count DESC;

-- Dead-letter queue status
SELECT
  status,
  COUNT(*) AS count
FROM dead_letter_queue
GROUP BY status;
```

#### Observability Metrics

```sql
-- Latest metrics by source
SELECT DISTINCT ON (src, metric)
  src,
  metric,
  value,
  ts
FROM obs_samples
ORDER BY src, metric, ts DESC;

-- n8n active executions over time
SELECT
  date_trunc('minute', ts) AS minute,
  AVG(value) AS avg_active
FROM obs_samples
WHERE metric = 'n8n_active_executions'
  AND ts > NOW() - INTERVAL '1 hour'
GROUP BY minute
ORDER BY minute;
```

### Alert Rules

Configure these alerts using the Error Handler workflow (Module 11) or an external monitoring tool:

| Alert | Condition | Severity |
|-------|-----------|----------|
| No ingestions | 0 ingestions in last 6 hours | Warning |
| Training stuck | MLflow run `RUNNING` > 3 hours | Critical |
| DLQ growing | > 10 pending items in dead_letter_queue | Warning |
| Deployment failure | Gate B failed | Critical |
| Database space | Disk usage > 80% | Warning |
| n8n down | Health endpoint unreachable | Critical |
| Observability gap | No obs_samples in last 5 minutes | Warning |

---

## 13.4 n8n Performance Tuning

### Execution Settings

Configure in n8n's Settings → **Workflow Settings** (per workflow):

| Setting | Production Value | Reason |
|---------|-----------------|--------|
| **Save Successful Executions** | `When Configured` | Reduce DB bloat |
| **Save Failed Executions** | `Always` | Keep for debugging |
| **Execution Order** | `v1 (FIFO)` | Predictable ordering |

For the **Observability Agent** (fires every 30 seconds), set:
- Save Successful Executions: **No** (saves ~2,880 execution records per day)

### Database Maintenance

n8n's execution history grows over time. Prune it regularly:

```bash
# n8n CLI: prune executions older than 30 days
n8n prune --days=30
```

Or configure auto-pruning in n8n's environment:

```bash
EXECUTIONS_DATA_PRUNE=true
EXECUTIONS_DATA_MAX_AGE=720  # hours (30 days)
```

### PostgreSQL Maintenance

```sql
-- Analyze tables for query optimizer
ANALYZE video;
ANALYZE obs_samples;
ANALYZE error_log;

-- Check table sizes
SELECT
  relname AS table_name,
  pg_size_pretty(pg_total_relation_size(relid)) AS total_size
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

-- Add index for common queries if not present
CREATE INDEX IF NOT EXISTS idx_video_split_label ON video(split, label);
CREATE INDEX IF NOT EXISTS idx_obs_samples_ts ON obs_samples(ts DESC);
CREATE INDEX IF NOT EXISTS idx_error_log_ts ON error_log(ts DESC);
```

---

## 13.5 Scaling Considerations

### Current Architecture Limits

| Component | Bottleneck | Limit |
|-----------|-----------|-------|
| n8n | Single-threaded main process | ~100 concurrent executions |
| PostgreSQL | Connection pool | Default 100 connections |
| Media Mover | Disk I/O | Depends on storage type |
| Training | GPU memory (Jetson/Ubuntu1) | 1 concurrent training run |
| DeepStream | Jetson GPU | 1 pipeline per GPU |

### Scaling the Observability Agent

If metrics collection becomes a bottleneck (too many Prometheus endpoints):

1. Reduce polling frequency from 30s to 60s
2. Batch metrics into fewer, larger PostgreSQL inserts
3. Consider using TimescaleDB extension for better time-series performance:
   ```sql
   -- Convert obs_samples to a TimescaleDB hypertable
   CREATE EXTENSION IF NOT EXISTS timescaledb;
   SELECT create_hypertable('obs_samples', 'ts');
   ```

### Scaling the Data Pipeline

If ingestion volume exceeds n8n's capacity:

1. Add a message queue (Redis, RabbitMQ) between the Gateway and n8n
2. Process batches instead of individual items in the Labeling Agent
3. Use n8n's **Queue Mode** for multi-worker execution:
   ```bash
   # n8n environment variables for queue mode
   EXECUTIONS_MODE=queue
   QUEUE_BULL_REDIS_HOST=localhost
   QUEUE_BULL_REDIS_PORT=6379
   ```

---

## 13.6 Maintenance Procedures

### Weekly Maintenance

```bash
#!/bin/bash
# weekly_maintenance.sh

echo "=== Weekly Maintenance ==="

echo "1. Checking n8n execution count..."
psql -h localhost -U reachy_dev -d reachy_emotion -c \
  "SELECT COUNT(*) FROM execution_entity WHERE finished_at < NOW() - INTERVAL '7 days';"

echo "2. Checking obs_samples growth..."
psql -h localhost -U reachy_dev -d reachy_emotion -c \
  "SELECT COUNT(*) AS total, pg_size_pretty(pg_total_relation_size('obs_samples')) AS size FROM obs_samples;"

echo "3. Checking error_log..."
psql -h localhost -U reachy_dev -d reachy_emotion -c \
  "SELECT severity, COUNT(*) FROM error_log WHERE ts > NOW() - INTERVAL '7 days' GROUP BY severity;"

echo "4. Checking dead_letter_queue..."
psql -h localhost -U reachy_dev -d reachy_emotion -c \
  "SELECT status, COUNT(*) FROM dead_letter_queue GROUP BY status;"

echo "5. Database vacuum..."
psql -h localhost -U reachy_dev -d reachy_emotion -c "VACUUM ANALYZE;"

echo "=== Done ==="
```

### Monthly Maintenance

1. **Review and rotate logs**: Check n8n logs, PostgreSQL logs, system logs
2. **Update n8n**: Check for new versions at https://docs.n8n.io/hosting/updating/
3. **Review error patterns**: Query `error_log` for recurring issues
4. **Verify backups**: Test-restore a backup to confirm it works
5. **Update credentials**: Rotate API tokens, SSH keys if needed

### Quarterly Maintenance

1. **Capacity review**: Check database sizes, disk usage, execution volumes
2. **Performance review**: Are any workflows consistently slow?
3. **Security audit**: Review credentials, access patterns, audit logs
4. **Model performance review**: Is the deployed EmotionNet model still performing well?

---

## 13.7 Incident Response

### Workflow Down (Not Executing)

```
1. Check n8n is running:       curl http://10.0.4.130:5678/healthz
2. Check workflow is active:   Open n8n UI → workflow list → verify toggle
3. Check execution history:    Look for recent failures
4. Check error handler:        Did it fire?
5. Check logs:                 journalctl -u n8n -n 50  (or docker logs n8n)
```

### Database Connection Errors

```
1. Check PostgreSQL is running: systemctl status postgresql
2. Check connections:           psql -c "SELECT count(*) FROM pg_stat_activity;"
3. Check max connections:       psql -c "SHOW max_connections;"
4. If maxed out:                Kill idle connections or increase max_connections
5. Restart if needed:           systemctl restart postgresql
```

### Jetson Unreachable

```
1. Ping:                        ping 10.0.4.XXX
2. SSH:                         ssh jetson "hostname"
3. Check DeepStream:            ssh jetson "systemctl status deepstream-emotion"
4. Check emotion client:        ssh jetson "systemctl status emotion-client"
5. If down:                     ssh jetson "systemctl restart emotion-client"
```

### Training Stuck

```
1. Check MLflow:                curl http://10.0.4.130:5000/api/2.0/mlflow/runs/get?run_id=XXX
2. Check GPU:                   ssh ubuntu1 "nvidia-smi"
3. Check training process:      ssh ubuntu1 "ps aux | grep train"
4. If stuck, kill and re-run:   ssh ubuntu1 "kill -9 <PID>"
5. Update MLflow run status:    Mark as FAILED via MLflow API
6. Retry from Orchestrator:     Re-trigger Agent 10
```

---

## 13.8 Environment Variable Reference

All environment variables used across the 10 workflows:

| Variable | Value | Used By |
|----------|-------|---------|
| `MEDIA_MOVER_BASE_URL` | `http://10.0.4.130:8083` | Agents 1, 3, 4 |
| `GATEWAY_BASE_URL` | `http://10.0.4.140:8000` | Agents 8, 10 |
| `INGEST_TOKEN` | *(secret)* | Agent 1 |
| `MLFLOW_URL` | `http://10.0.4.130:5000` | Agents 6, 7 |
| `ALERT_WEBHOOK_URL` | *(your Slack/email webhook)* | Error Handler |
| `N8N_METRICS` | `true` | Agent 9 |
| `EXECUTIONS_DATA_PRUNE` | `true` | n8n system |
| `EXECUTIONS_DATA_MAX_AGE` | `720` | n8n system |

---

## 13.9 Credential Reference

| Credential Name | Type | Used By |
|-----------------|------|---------|
| `PostgreSQL - reachy_local` | PostgreSQL | Agents 1-6, 9-10, Error Handler |
| `Media Mover Auth` | HTTP Header Auth | Agents 1, 3 |
| `SSH Ubuntu1` | SSH Key | Agents 4, 6-8 |
| `SSH Jetson` | SSH Key | Agents 4, 8 |

---

## 13.10 Final Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRODUCTION SYSTEM                            │
│                                                                     │
│  UBUNTU 1 (10.0.4.130)                                             │
│  ┌─────────┐  ┌──────────┐  ┌─────────┐  ┌──────────┐             │
│  │  n8n    │  │PostgreSQL│  │Media    │  │ MLflow   │             │
│  │ :5678   │  │ :5432    │  │Mover    │  │ :5000    │             │
│  │         │  │          │  │ :8083   │  │          │             │
│  │ 10 wkfl │  │reachy_   │  │         │  │          │             │
│  │ + error │  │emotion   │  │         │  │          │             │
│  └────┬────┘  └─────┬────┘  └────┬────┘  └────┬─────┘             │
│       │             │            │             │                    │
│       └─────────────┴────────────┴─────────────┘                    │
│                          │                                          │
│  UBUNTU 2 (10.0.4.140)  │                                          │
│  ┌──────────────┐        │                                          │
│  │ FastAPI      │◄───────┘                                          │
│  │ Gateway      │                                                   │
│  │ :8000        │◄──────────────────────┐                           │
│  └──────────────┘                       │                           │
│                                         │                           │
│  JETSON                                 │                           │
│  ┌──────────────┐  ┌──────────────┐     │                           │
│  │ DeepStream   │─►│ Emotion      │─────┘                           │
│  │ Pipeline     │  │ Client       │                                 │
│  │ (EmotionNet) │  │ (WebSocket)  │                                 │
│  └──────────────┘  └──────────────┘                                 │
│                                                                     │
│  MONITORING                                                         │
│  ┌──────────────────────────────────────────────┐                   │
│  │ Observability Agent (30s polling)             │                   │
│  │ Error Handler (real-time alerts)              │                   │
│  │ DLQ Retry (15 min cycle)                      │                   │
│  │ Backups (daily at 2am/3am)                    │                   │
│  │ Maintenance (weekly/monthly/quarterly)        │                   │
│  └──────────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 13.11 Congratulations -- Curriculum Complete!

You have now completed all 13 modules of the n8n Agentic AI Development Curriculum:

| Phase | Modules | What You Learned |
|-------|---------|------------------|
| **Foundation** | 00 | n8n fundamentals, data flow, expressions |
| **Core Data Pipeline** | 01-03 | Webhooks, auth, polling, DB ops, idempotency |
| **Maintenance** | 04-05 | Scheduling, SSH, batch processing, compliance |
| **ML Pipeline** | 06-08 | Training, evaluation, deployment, quality gates |
| **Observability** | 09-10 | Metrics, orchestration, workflow-to-workflow |
| **Advanced** | 11-13 | Error handling, testing, production operations |

### Your Capabilities

You can now:

- Wire any n8n workflow from scratch using 12+ node types
- Build multi-agent orchestration systems
- Implement robust error handling with dead-letter queues
- Test workflows at unit, integration, and end-to-end levels
- Operate a production ML pipeline with proper monitoring and maintenance
- Debug failed executions systematically

### Next Steps

1. **Monitor** the system daily for the first week
2. **Iterate** on alert thresholds based on real usage patterns
3. **Extend** the system with new agents as needed
4. **Document** any custom procedures specific to your environment

---

*Previous: [MODULE 12 -- Testing & Debugging Strategies](MODULE_12_TESTING_DEBUGGING.md)*
*Back to: [Curriculum Index](../CURRICULUM_INDEX.md)*
