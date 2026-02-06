# Guide 12: n8n Orchestration Integration

**Duration**: 2-3 hours  
**Difficulty**: Intermediate  
**Prerequisites**: Guides 01-07 concepts, basic understanding of workflow automation

---

## Overview

This guide explains how the ML training pipeline integrates with **n8n**, the workflow automation platform that orchestrates the Reachy project's agent system. You'll learn:

1. How training fits into the overall agent architecture
2. The Training Orchestrator (Agent 5) workflow
3. How Gate A triggers deployment
4. Monitoring and alerting integration

**Understanding n8n integration helps you see how manual training connects to automated production workflows.**

---

## 1. Agent Architecture Overview

### 1.1 Where Training Fits

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    REACHY AGENT ARCHITECTURE                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Data Pipeline                    ML Pipeline                            │
│  ────────────                     ───────────                            │
│                                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Agent 1  │───▶│ Agent 2  │───▶│ Agent 3  │───▶│ Agent 5  │          │
│  │ Ingest   │    │ Labeling │    │ Promote  │    │ Training │          │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│       │              │               │               │                   │
│       │              │               │               ▼                   │
│       │              │               │         ┌──────────┐             │
│       │              │               │         │ Agent 6  │             │
│       │              │               │         │ Evaluate │             │
│       │              │               │         └──────────┘             │
│       │              │               │               │                   │
│       │              │               │               ▼                   │
│       ▼              ▼               ▼         ┌──────────┐             │
│  ┌─────────────────────────────────────────┐  │ Agent 7  │             │
│  │           PostgreSQL Database            │  │ Deploy   │             │
│  └─────────────────────────────────────────┘  └──────────┘             │
│                                                      │                   │
│                                                      ▼                   │
│                                               ┌──────────┐              │
│                                               │  Jetson  │              │
│                                               │Xavier NX │              │
│                                               └──────────┘              │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 Key Agents for ML Engineers

| Agent | Name | Role in ML Pipeline |
|-------|------|---------------------|
| **Agent 3** | Promotion/Curation | Triggers training when dataset ready |
| **Agent 5** | Training Orchestrator | Runs EfficientNet-B0 training |
| **Agent 6** | Evaluation | Validates Gate A metrics |
| **Agent 7** | Deployment | Deploys to Jetson after Gate A passes |

---

## 2. Training Orchestrator (Agent 5)

### 2.1 Workflow Location

```
n8n/workflows/ml-agentic-ai_v.1/
└── 05_training_orchestrator_efficientnet.json
```

### 2.2 Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│              AGENT 5: TRAINING ORCHESTRATOR WORKFLOW                     │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  TRIGGER                                                                 │
│  ───────                                                                 │
│  ┌──────────────────┐                                                   │
│  │ Webhook: POST    │  ← From Agent 3 (dataset ready)                   │
│  │ /training/start  │  ← From Web UI (manual trigger)                   │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  VALIDATION                                                              │
│  ──────────                                                              │
│  ┌──────────────────┐                                                   │
│  │ Check Dataset    │  Verify train/test splits exist                   │
│  │ Requirements     │  Verify class balance > 0.80                      │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ Check GPU        │  Verify GPU available                             │
│  │ Availability     │  Check no conflicting jobs                        │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  TRAINING                                                                │
│  ────────                                                                │
│  ┌──────────────────┐                                                   │
│  │ Execute Training │  python trainer/train_efficientnet.py             │
│  │ Script           │  --config efficientnet_b0_emotion_2cls.yaml       │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ Monitor Progress │  Track epochs, loss, metrics                      │
│  │ (polling)        │  Update database with status                      │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  COMPLETION                                                              │
│  ──────────                                                              │
│  ┌──────────────────┐                                                   │
│  │ Gate A Check     │──── PASS ───▶ Emit: training.completed            │
│  │                  │                      │                             │
│  │                  │──── FAIL ───▶ Emit: training.failed               │
│  └──────────────────┘                      │                             │
│                                            ▼                             │
│                                    ┌──────────────────┐                 │
│                                    │ Trigger Agent 6  │                 │
│                                    │ (Evaluation)     │                 │
│                                    └──────────────────┘                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 2.3 n8n Node Configuration

**Trigger Node (Webhook):**
```json
{
  "node": "Webhook",
  "parameters": {
    "httpMethod": "POST",
    "path": "training/start",
    "responseMode": "onReceived",
    "responseData": "firstEntryJson"
  }
}
```

**Training Execution Node:**
```json
{
  "node": "Execute Command",
  "parameters": {
    "command": "python trainer/train_efficientnet.py --config fer_finetune/specs/efficientnet_b0_emotion_2cls.yaml --run-id {{ $json.run_id }}",
    "cwd": "/path/to/reachy_emotion"
  }
}
```

---

## 3. How Training is Triggered

### 3.1 Automatic Trigger (from Agent 3)

When Agent 3 (Promotion Agent) detects the dataset meets requirements:

```
Agent 3 checks:
├── Train set: min 200 videos ✅
├── Test set: min 40 videos ✅
├── Train balance: ratio > 0.80 ✅
└── Test balance: ratio > 0.80 ✅

All conditions met → POST to /training/start
```

**Automatic trigger payload:**
```json
{
  "trigger_source": "agent_3_promotion",
  "run_id": "auto_20260205_143000",
  "config_file": "efficientnet_b0_emotion_2cls.yaml",
  "dataset_stats": {
    "train_total": 500,
    "train_happy": 250,
    "train_sad": 250,
    "test_total": 100
  }
}
```

### 3.2 Manual Trigger (from Web UI)

Users can trigger training from the Streamlit dashboard:

```python
# In Web UI (03_Train.py)
import requests

def trigger_training(run_id: str, config: str):
    response = requests.post(
        "http://10.0.4.130:5678/webhook/training/start",
        json={
            "trigger_source": "web_ui_manual",
            "run_id": run_id,
            "config_file": config,
        }
    )
    return response.json()
```

### 3.3 API Trigger (for automation)

```bash
# Direct API call to trigger training
curl -X POST "http://10.0.4.130:5678/webhook/training/start" \
  -H "Content-Type: application/json" \
  -d '{
    "trigger_source": "api_manual",
    "run_id": "manual_run_001",
    "config_file": "efficientnet_b0_emotion_2cls.yaml"
  }'
```

---

## 4. Training Status and Events

### 4.1 Event Flow

```
training.started
       │
       ▼
training.epoch_complete (×30)
       │
       ▼
training.completed ──────┬──── gate_a.passed ───▶ deployment.triggered
                         │
                         └──── gate_a.failed ───▶ alert.sent
```

### 4.2 Event Payloads

**training.started:**
```json
{
  "event": "training.started",
  "timestamp": "2026-02-05T14:30:00Z",
  "run_id": "production_run_20260205",
  "config": "efficientnet_b0_emotion_2cls.yaml",
  "dataset": {
    "train_samples": 500,
    "val_samples": 100
  }
}
```

**training.epoch_complete:**
```json
{
  "event": "training.epoch_complete",
  "timestamp": "2026-02-05T14:35:00Z",
  "run_id": "production_run_20260205",
  "epoch": 10,
  "total_epochs": 30,
  "metrics": {
    "train_loss": 0.2456,
    "val_loss": 0.2234,
    "val_f1": 0.8612,
    "val_balanced_accuracy": 0.8700
  }
}
```

**training.completed:**
```json
{
  "event": "training.completed",
  "timestamp": "2026-02-05T15:42:00Z",
  "run_id": "production_run_20260205",
  "success": true,
  "gate_a_passed": true,
  "final_metrics": {
    "macro_f1": 0.9089,
    "balanced_accuracy": 0.9100,
    "ece": 0.0534,
    "brier": 0.1123
  },
  "artifacts": {
    "checkpoint": "/workspace/checkpoints/best_model.pth",
    "onnx": "/workspace/exports/emotion_efficientnet.onnx"
  }
}
```

### 4.3 Monitoring in n8n

The workflow includes monitoring nodes that:

1. **Poll training status** every 30 seconds
2. **Update database** with current epoch/metrics
3. **Send alerts** on failure or Gate A failure
4. **Trigger downstream agents** on success

---

## 5. Gate A Integration

### 5.1 Automatic Gate A Check

After training completes, the workflow automatically runs Gate A validation:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    GATE A VALIDATION IN N8N                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Training Complete                                                       │
│        │                                                                 │
│        ▼                                                                 │
│  ┌──────────────────┐                                                   │
│  │ Load Best Model  │                                                   │
│  │ from Checkpoint  │                                                   │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ Run Evaluation   │  Compute F1, Balanced Acc, ECE, Brier             │
│  │ on Test Set      │                                                   │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ Compare Against  │                                                   │
│  │ Gate A Thresholds│                                                   │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│     ┌─────┴─────┐                                                       │
│     ▼           ▼                                                       │
│  ┌──────┐   ┌──────┐                                                   │
│  │ PASS │   │ FAIL │                                                   │
│  └──┬───┘   └──┬───┘                                                   │
│     │          │                                                         │
│     ▼          ▼                                                         │
│  Export     Send Alert                                                   │
│  to ONNX    to Team                                                     │
│     │                                                                    │
│     ▼                                                                    │
│  Trigger                                                                 │
│  Agent 7                                                                 │
│  (Deploy)                                                                │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 5.2 Gate A Thresholds in Workflow

```json
{
  "node": "Gate A Check",
  "type": "If",
  "parameters": {
    "conditions": {
      "number": [
        {
          "value1": "={{ $json.metrics.macro_f1 }}",
          "operation": "largerEqual",
          "value2": 0.84
        },
        {
          "value1": "={{ $json.metrics.balanced_accuracy }}",
          "operation": "largerEqual",
          "value2": 0.85
        },
        {
          "value1": "={{ $json.metrics.ece }}",
          "operation": "smallerEqual",
          "value2": 0.08
        }
      ]
    }
  }
}
```

---

## 6. Deployment Trigger (Agent 7)

### 6.1 Automatic Deployment Flow

When Gate A passes, Agent 5 triggers Agent 7:

```bash
# Event emitted by Agent 5
POST /webhook/deployment/start
{
  "trigger_source": "agent_5_training",
  "model_path": "/workspace/exports/emotion_efficientnet.onnx",
  "gate_a_metrics": {
    "macro_f1": 0.9089,
    "balanced_accuracy": 0.9100
  },
  "approval_required": true  # Human-in-the-loop for production
}
```

### 6.2 Approval Workflow

For production deployments, human approval is required:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                    DEPLOYMENT APPROVAL FLOW                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Gate A Passed                                                           │
│        │                                                                 │
│        ▼                                                                 │
│  ┌──────────────────┐                                                   │
│  │ Send Approval    │  Slack/Email to ML team                           │
│  │ Request          │  "New model ready: F1=0.9089"                     │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│           ▼                                                              │
│  ┌──────────────────┐                                                   │
│  │ Wait for Human   │  Timeout: 24 hours                                │
│  │ Approval         │  Link to approve/reject                           │
│  └────────┬─────────┘                                                   │
│           │                                                              │
│     ┌─────┴─────┐                                                       │
│     ▼           ▼                                                       │
│  Approved    Rejected                                                    │
│     │           │                                                        │
│     ▼           ▼                                                        │
│  Agent 7     Log reason,                                                 │
│  Deploy      notify team                                                 │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 7. Alerts and Notifications

### 7.1 Alert Conditions

| Condition | Alert Type | Recipients |
|-----------|------------|------------|
| Training failed | Error | ML team |
| Gate A failed | Warning | ML team |
| Gate A passed | Info | ML team, PM |
| Deployment complete | Info | All stakeholders |

### 7.2 Slack Integration

```json
{
  "node": "Slack",
  "parameters": {
    "channel": "#reachy-ml-alerts",
    "text": "🎯 Training Complete!\n\nRun: {{ $json.run_id }}\nMacro F1: {{ $json.metrics.macro_f1 }}\nGate A: {{ $json.gate_a_passed ? '✅ PASSED' : '❌ FAILED' }}"
  }
}
```

---

## 8. Database Integration

### 8.1 Training Runs Table

```sql
-- PostgreSQL schema for tracking training runs
CREATE TABLE training_runs (
    id SERIAL PRIMARY KEY,
    run_id VARCHAR(100) UNIQUE NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, running, completed, failed
    trigger_source VARCHAR(50),
    config_file VARCHAR(200),
    
    -- Dataset info
    train_samples INTEGER,
    val_samples INTEGER,
    
    -- Progress
    current_epoch INTEGER DEFAULT 0,
    total_epochs INTEGER,
    
    -- Metrics (updated during training)
    best_val_f1 DECIMAL(6,4),
    best_val_loss DECIMAL(8,6),
    
    -- Gate A results
    gate_a_passed BOOLEAN,
    gate_a_macro_f1 DECIMAL(6,4),
    gate_a_balanced_accuracy DECIMAL(6,4),
    gate_a_ece DECIMAL(6,4),
    
    -- Artifacts
    checkpoint_path VARCHAR(500),
    onnx_path VARCHAR(500),
    
    -- Timestamps
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 8.2 Querying Training Status

```sql
-- Get latest training run status
SELECT 
    run_id,
    status,
    current_epoch || '/' || total_epochs as progress,
    best_val_f1,
    gate_a_passed,
    started_at,
    completed_at
FROM training_runs
ORDER BY created_at DESC
LIMIT 1;
```

---

## 9. Manual Intervention Points

### 9.1 When to Intervene

| Scenario | Action |
|----------|--------|
| Training stuck (no progress) | Check GPU, restart training |
| Gate A failed narrowly | Review metrics, consider adjustments |
| Unexpected low metrics | Check data quality |
| Deployment blocked | Review approval request |

### 9.2 Manual Override Commands

```bash
# Cancel running training
curl -X POST "http://10.0.4.130:5678/webhook/training/cancel" \
  -d '{"run_id": "production_run_20260205"}'

# Force Gate A re-evaluation
curl -X POST "http://10.0.4.130:5678/webhook/gate-a/evaluate" \
  -d '{"checkpoint_path": "/workspace/checkpoints/best_model.pth"}'

# Skip approval and deploy (emergency only)
curl -X POST "http://10.0.4.130:5678/webhook/deployment/force" \
  -d '{"model_path": "/workspace/exports/model.onnx", "reason": "Emergency hotfix"}'
```

---

## 10. Summary

### What You Learned

1. ✅ Training integrates with n8n via Agent 5 (Training Orchestrator)
2. ✅ Training can be triggered automatically or manually
3. ✅ Gate A validation happens automatically after training
4. ✅ Successful training triggers Agent 7 for deployment
5. ✅ Human approval is required for production deployments
6. ✅ All training runs are tracked in PostgreSQL

### Key Integration Points

| Component | URL/Endpoint |
|-----------|--------------|
| Training trigger | POST /webhook/training/start |
| Training status | GET /api/training/status/{run_id} |
| Gate A results | GET /api/gate-a/results/{run_id} |
| Deployment trigger | POST /webhook/deployment/start |

### n8n Workflow Files

```
n8n/workflows/ml-agentic-ai_v.1/
├── 05_training_orchestrator_efficientnet.json
├── 06_evaluation_agent_efficientnet.json
└── 07_deployment_agent_efficientnet.json
```

---

*This completes the ML training pipeline tutorial series. Return to [Guide Index](00_FINE_TUNING_INDEX.md) for the full curriculum.*
