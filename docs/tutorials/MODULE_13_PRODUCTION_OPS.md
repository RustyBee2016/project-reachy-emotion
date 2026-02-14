# Module 13: Production Operations

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~2 hours  
**Prerequisites**: Completed Modules 0-12

---

## Learning Objectives

By the end of this module, you will:
1. Manage **workflow versioning** and backup
2. Understand **activation** best practices
3. **Monitor** production workflows
4. Handle **scaling** and performance
5. Plan for **disaster recovery**

---

## Part 1: Workflow Versioning

### Export Workflows

**Manual Export**:
1. Open workflow
2. Click "..." menu
3. Download → Download as File
4. Save JSON to version control

**API Export**:
```bash
# Get all workflows
curl http://localhost:5678/api/v1/workflows \
  -H "X-N8N-API-KEY: your-api-key" \
  | jq '.data[] | {id, name}' > workflow_list.json

# Export specific workflow
curl http://localhost:5678/api/v1/workflows/abc123 \
  -H "X-N8N-API-KEY: your-api-key" \
  > workflows/ingest_agent.json
```

### Version Control Strategy

```
n8n/workflows/
├── ml-agentic-ai_v.1/     # Archive
├── ml-agentic-ai_v.2/     # Current production
│   ├── 01_ingest_agent.json
│   ├── 02_labeling_agent.json
│   └── ...
└── ml-agentic-ai_v.3/     # Development
```

### Backup Script

```bash
#!/bin/bash
# backup_workflows.sh

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backup/n8n/$DATE"
API_KEY="your-api-key"
N8N_HOST="http://localhost:5678"

mkdir -p "$BACKUP_DIR"

# Get workflow list
WORKFLOWS=$(curl -s "$N8N_HOST/api/v1/workflows" \
  -H "X-N8N-API-KEY: $API_KEY" | jq -r '.data[].id')

# Export each workflow
for WF_ID in $WORKFLOWS; do
  curl -s "$N8N_HOST/api/v1/workflows/$WF_ID" \
    -H "X-N8N-API-KEY: $API_KEY" \
    > "$BACKUP_DIR/$WF_ID.json"
done

echo "Backed up $(echo $WORKFLOWS | wc -w) workflows to $BACKUP_DIR"
```

---

## Part 2: Activation Management

### Activation States

| State | Webhooks | Schedules | Manual |
|-------|----------|-----------|--------|
| **Inactive** | ❌ | ❌ | ✅ |
| **Active** | ✅ | ✅ | ✅ |

### Activation Checklist

Before activating:
- [ ] All credentials configured
- [ ] Environment variables set
- [ ] Backend services running
- [ ] Error workflow attached
- [ ] Manual test successful
- [ ] Pinned data removed (unless intentional)

### Bulk Activation

```bash
# Activate all agentic workflows
for WF_ID in abc123 def456 ghi789; do
  curl -X PATCH "http://localhost:5678/api/v1/workflows/$WF_ID" \
    -H "X-N8N-API-KEY: your-api-key" \
    -H "Content-Type: application/json" \
    -d '{"active": true}'
done
```

### Activation Order

For the agentic system, activate in dependency order:
1. Error Handler (global)
2. Observability Agent
3. Privacy Agent
4. Reconciler Agent
5. Ingest Agent
6. Labeling Agent
7. Promotion Agent
8. Training Orchestrator
9. Evaluation Agent
10. Deployment Agent
11. ML Pipeline Orchestrator (last)

---

## Part 3: Production Monitoring

### Key Metrics to Watch

| Metric | Source | Alert Threshold |
|--------|--------|-----------------|
| Active executions | n8n /metrics | > 50 |
| Error rate | n8n /metrics | > 5% |
| Queue depth | Custom | > 100 |
| Execution duration | Execution history | > expected × 2 |

### Monitoring Dashboard Query

```sql
-- Execution stats by workflow (last 24h)
SELECT 
  workflow_name,
  COUNT(*) as executions,
  COUNT(*) FILTER (WHERE status = 'error') as errors,
  AVG(duration_ms) as avg_duration_ms,
  MAX(duration_ms) as max_duration_ms
FROM workflow_executions
WHERE started_at > NOW() - INTERVAL '24 hours'
GROUP BY workflow_name
ORDER BY errors DESC;
```

### Health Check Endpoint

Create a simple health check workflow:

```
Webhook: /health
     │
     ▼
Code: check_status
     │
     ▼
Respond: OK
```

**Code: check_status**:
```javascript
const checks = {
  n8n: 'ok',
  timestamp: new Date().toISOString(),
  active_workflows: 10  // Update with actual count
};

return [{ json: checks }];
```

---

## Part 4: Scaling Considerations

### n8n Execution Modes

| Mode | Description | Use Case |
|------|-------------|----------|
| **Main** | Single process | Development, small loads |
| **Queue** | Worker-based | Production, parallel |

### Queue Mode Setup

```bash
# docker-compose.yml additions
services:
  n8n:
    environment:
      - EXECUTIONS_MODE=queue
      - QUEUE_BULL_REDIS_HOST=redis
      
  n8n-worker:
    image: n8nio/n8n
    command: worker
    environment:
      - EXECUTIONS_MODE=queue
      - QUEUE_BULL_REDIS_HOST=redis
    deploy:
      replicas: 3
```

### Performance Tips

1. **Limit concurrent executions**: Workflow settings → Max Concurrent
2. **Optimize Code nodes**: Avoid heavy computations
3. **Use pagination**: For large database queries
4. **Batch operations**: Split In Batches for bulk work
5. **Cache external calls**: Avoid redundant API calls

---

## Part 5: Disaster Recovery

### Recovery Scenarios

| Scenario | Impact | Recovery |
|----------|--------|----------|
| Workflow deleted | Lost configuration | Restore from backup |
| Database down | Workflows can't execute | Fix DB, retry queue |
| n8n crash | Interrupted executions | Restart, check queue |
| Credential expired | Auth failures | Renew credentials |

### Recovery Procedures

**Restore Workflow from Backup**:
```bash
curl -X POST "http://localhost:5678/api/v1/workflows" \
  -H "X-N8N-API-KEY: your-api-key" \
  -H "Content-Type: application/json" \
  -d @backup/ingest_agent.json
```

**Clear Stuck Executions**:
```bash
# In n8n database
UPDATE execution
SET status = 'crashed', stoppedAt = NOW()
WHERE status = 'running' AND startedAt < NOW() - INTERVAL '1 hour';
```

**Reset Webhook Registration**:
1. Deactivate workflow
2. Clear webhook cache (restart n8n)
3. Reactivate workflow

---

## Part 6: Operational Runbook

### Daily Operations

| Task | Frequency | Action |
|------|-----------|--------|
| Check execution errors | Daily | Review execution history |
| Verify scheduled runs | Daily | Check cron workflows executed |
| Review DLQ | Daily | Process failed tasks |
| Check disk space | Daily | n8n logs, database |

### Weekly Operations

| Task | Action |
|------|--------|
| Backup workflows | Export to version control |
| Review metrics | Check SLO compliance |
| Update credentials | Renew expiring tokens |
| Clean old executions | Prune history |

### Monthly Operations

| Task | Action |
|------|--------|
| Dependency updates | Check n8n version |
| Performance review | Optimize slow workflows |
| Security audit | Review credentials, access |
| Disaster recovery test | Restore from backup |

---

## Part 7: Production Checklist

### Pre-Deployment

- [ ] Workflows exported and committed to git
- [ ] All tests passing
- [ ] Error workflow configured
- [ ] Credentials in production vault
- [ ] Environment variables set
- [ ] Monitoring configured
- [ ] Alerting configured
- [ ] Rollback plan documented

### Post-Deployment

- [ ] All workflows activated
- [ ] Health check passing
- [ ] Webhooks responding
- [ ] Scheduled triggers firing
- [ ] Metrics flowing
- [ ] No errors in logs

### Rollback Procedure

1. Deactivate failing workflow(s)
2. Export current (broken) state for debugging
3. Import previous working version
4. Reactivate workflow
5. Verify functionality
6. Investigate root cause

---

## Part 8: The Agentic System in Production

### System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REACHY AGENTIC AI SYSTEM                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │   Ingest    │  │   Label     │  │  Promote    │  DATA PIPELINE       │
│  │   Agent     │──│   Agent     │──│   Agent     │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐                                       │
│  │ Reconciler  │  │  Privacy    │  MAINTENANCE                          │
│  │   Agent     │  │   Agent     │                                       │
│  └─────────────┘  └─────────────┘                                       │
│                                                                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐                      │
│  │  Training   │  │ Evaluation  │  │ Deployment  │  ML PIPELINE         │
│  │   Agent     │──│   Agent     │──│   Agent     │                      │
│  └─────────────┘  └─────────────┘  └─────────────┘                      │
│                                                                         │
│  ┌─────────────┐  ┌─────────────────────────────┐                       │
│  │Observability│  │   ML Pipeline Orchestrator  │  ORCHESTRATION        │
│  │   Agent     │  │                             │                       │
│  └─────────────┘  └─────────────────────────────┘                       │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Key Operational Notes

| Agent | Schedule | Dependencies |
|-------|----------|--------------|
| Ingest | Webhook | Media Mover API |
| Labeling | Webhook | PostgreSQL |
| Promotion | Webhook | Media Mover, human approval |
| Reconciler | 02:15 daily | SSH, PostgreSQL |
| Privacy | 03:00 daily | SSH, PostgreSQL |
| Training | Webhook | SSH, MLflow |
| Evaluation | Webhook | SSH, MLflow |
| Deployment | Webhook | SSH to Jetson |
| Observability | Every 30s | PostgreSQL |
| Orchestrator | Webhook | All agents |

---

## Congratulations! 🎉

You've completed the entire n8n Agentic AI Development curriculum for Reachy_Local_08.4.2.

### What You've Mastered

1. **n8n Fundamentals** — Nodes, expressions, data flow
2. **Webhook Patterns** — Triggers, responses, polling
3. **Database Operations** — SQL, CTEs, idempotency
4. **Multi-Path Routing** — Switch, IF, parallel execution
5. **SSH Operations** — Remote commands, file transfer
6. **Error Handling** — Try-catch, retry, dead letters
7. **ML Pipeline** — Training, evaluation, deployment
8. **Orchestration** — Workflow-to-workflow coordination
9. **Production Ops** — Monitoring, scaling, recovery

### Your Certification Path

To demonstrate proficiency:
1. Wire all 10 agentic workflows from scratch
2. Test each workflow end-to-end
3. Run a complete ML pipeline (training → deployment)
4. Handle a simulated failure scenario
5. Document your operational procedures

### Next Steps

1. **Practice** — Wire the workflows without looking at tutorials
2. **Extend** — Add new features (Slack alerts, custom metrics)
3. **Optimize** — Improve performance, reduce errors
4. **Share** — Document what you've learned

---

*Curriculum Complete — You are now a Professional n8n Developer!*
