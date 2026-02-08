# n8n Workflow Updates for 3-Class Emotion Model

**Date:** 2026-02-08  
**Change:** 2-class (happy, sad) → 3-class (happy, sad, neutral)

This guide documents the required updates to n8n workflows in `ml-agentic-ai_v.2/` to support the 3-class emotion classification model.

---

## Summary of Required Changes

| Workflow | Node | Current | Required Change |
|----------|------|---------|-----------------|
| `02_labeling_agent.json` | `db_class_balance` | Counts happy/sad only | Add neutral_count |
| `02_labeling_agent.json` | `respond_success` | Returns happy/sad balance | Add neutral to response |
| `05_training_orchestrator_efficientnet.json` | `db_check_balance` | `Math.min(happy, sad)` | Add neutral_train |
| `06_evaluation_agent_efficientnet.json` | `db_check_balance` | `Math.min(happy, sad)` | Add neutral_test |
| `10_ml_pipeline_orchestrator.json` | `db_dataset_stats` | Counts happy/sad only | Add neutral stats |
| `10_ml_pipeline_orchestrator.json` | `check_dataset` | Checks 2 classes | Check 3 classes |

---

## Detailed Updates

### 1. `02_labeling_agent.json`

#### Node: `db_class_balance` (Postgres)

**Current SQL:**
```sql
SELECT 
  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,
  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,
  COUNT(*) FILTER (WHERE split = 'train') AS total_train
FROM video;
```

**Updated SQL:**
```sql
SELECT 
  COUNT(CASE WHEN label = 'happy' AND split = 'train' THEN 1 END) AS happy_count,
  COUNT(CASE WHEN label = 'sad' AND split = 'train' THEN 1 END) AS sad_count,
  COUNT(CASE WHEN label = 'neutral' AND split = 'train' THEN 1 END) AS neutral_count,
  COUNT(*) FILTER (WHERE split = 'train') AS total_train
FROM video;
```

#### Node: `respond_success` (Respond to Webhook)

**Current Response:**
```javascript
{
  "class_balance": {
    "happy": $json.happy_count,
    "sad": $json.sad_count,
    "total_train": $json.total_train,
    "balanced": Math.abs($json.happy_count - $json.sad_count) <= 5
  }
}
```

**Updated Response:**
```javascript
{
  "class_balance": {
    "happy": $json.happy_count,
    "sad": $json.sad_count,
    "neutral": $json.neutral_count,
    "total_train": $json.total_train,
    "balanced": Math.max($json.happy_count, $json.sad_count, $json.neutral_count) - 
                Math.min($json.happy_count, $json.sad_count, $json.neutral_count) <= 10
  }
}
```

---

### 2. `05_training_orchestrator_efficientnet.json`

#### Node: `db_check_balance` (Postgres)

**Current SQL:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train, 
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train 
FROM video;
```

**Updated SQL:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train, 
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train,
  COUNT(*) FILTER (WHERE label='neutral' AND split='train') AS neutral_train
FROM video;
```

#### Node: `IF: balance_check` (IF Node)

**Current Condition:**
```javascript
={{Math.min($json.happy_train, $json.sad_train)}} >= 50
```

**Updated Condition:**
```javascript
={{Math.min($json.happy_train, $json.sad_train, $json.neutral_train)}} >= 50
```

---

### 3. `06_evaluation_agent_efficientnet.json`

#### Node: `db_check_balance` (Postgres)

**Current SQL:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test, 
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test 
FROM video;
```

**Updated SQL:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test, 
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test,
  COUNT(*) FILTER (WHERE label='neutral' AND split='test') AS neutral_test
FROM video;
```

#### Node: `IF: balance_check` (IF Node)

**Current Condition:**
```javascript
={{Math.min($json.happy_test, $json.sad_test)}} >= 20
```

**Updated Condition:**
```javascript
={{Math.min($json.happy_test, $json.sad_test, $json.neutral_test)}} >= 20
```

#### Node: `ssh_run_eval` (SSH Execute Command)

**Current Python Code:**
```python
model = load_pretrained_model('{{$json.checkpoint_path}}', num_classes=2)
results = evaluate_model(model, val_loader, class_names=['happy', 'sad'])
```

**Updated Python Code:**
```python
model = load_pretrained_model('{{$json.checkpoint_path}}', num_classes=3)
results = evaluate_model(model, val_loader, class_names=['happy', 'sad', 'neutral'])
```

---

### 4. `10_ml_pipeline_orchestrator.json`

#### Node: `db_dataset_stats` (Postgres)

**Current SQL:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train, 
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train, 
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test, 
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test 
FROM video;
```

**Updated SQL:**
```sql
SELECT 
  COUNT(*) FILTER (WHERE label='happy' AND split='train') AS happy_train, 
  COUNT(*) FILTER (WHERE label='sad' AND split='train') AS sad_train,
  COUNT(*) FILTER (WHERE label='neutral' AND split='train') AS neutral_train,
  COUNT(*) FILTER (WHERE label='happy' AND split='test') AS happy_test, 
  COUNT(*) FILTER (WHERE label='sad' AND split='test') AS sad_test,
  COUNT(*) FILTER (WHERE label='neutral' AND split='test') AS neutral_test
FROM video;
```

#### Node: `check_dataset` (Code Node)

**Current Logic:**
```javascript
const trainReady = Math.min(stats.happy_train, stats.sad_train) >= minTrainPerClass;
const testReady = Math.min(stats.happy_test, stats.sad_test) >= minTestPerClass;
const balanced = Math.abs(stats.happy_train - stats.sad_train) / 
                 Math.max(stats.happy_train, stats.sad_train) < 0.2;
```

**Updated Logic:**
```javascript
const trainReady = Math.min(stats.happy_train, stats.sad_train, stats.neutral_train) >= minTrainPerClass;
const testReady = Math.min(stats.happy_test, stats.sad_test, stats.neutral_test) >= minTestPerClass;
const maxTrain = Math.max(stats.happy_train, stats.sad_train, stats.neutral_train);
const minTrain = Math.min(stats.happy_train, stats.sad_train, stats.neutral_train);
const balanced = (maxTrain - minTrain) / maxTrain < 0.2;
```

#### Node: `HTTP: trigger.training` (HTTP Request)

**Current Dataset Hash:**
```javascript
dataset_hash: $json.dataset_stats.happy_train + '_' + $json.dataset_stats.sad_train
```

**Updated Dataset Hash:**
```javascript
dataset_hash: $json.dataset_stats.happy_train + '_' + $json.dataset_stats.sad_train + '_' + $json.dataset_stats.neutral_train
```

---

## Tutorial Documentation Updates

The following tutorial files in `docs/tutorials/` reference 2-class configurations and should be updated:

| File | Priority | Changes Needed |
|------|----------|----------------|
| `MODULE_02_LABELING_AGENT.md` | High | Update SQL examples, balance checks |
| `MODULE_06_TRAINING_ORCHESTRATOR.md` | High | Update class count references |
| `MODULE_07_EVALUATION_AGENT.md` | High | Update num_classes, class_names |
| `MODULE_10_ML_PIPELINE_ORCHESTRATOR.md` | High | Update dataset stats examples |
| `fine_tuning/01_WHAT_IS_FINE_TUNING.md` | Medium | Update class count examples |
| `fine_tuning/03_DATA_PREPARATION.md` | Medium | Update directory structure |
| `fine_tuning/08_QUICK_START_HANDS_ON.md` | Medium | Update config examples |

---

## Testing After Updates

After updating the workflows, test with:

1. **Labeling Agent**: Submit a video with label "neutral" and verify class_balance response includes neutral_count
2. **Training Orchestrator**: Verify balance check passes only when all 3 classes have ≥50 samples
3. **Evaluation Agent**: Verify balance check passes only when all 3 classes have ≥20 test samples
4. **ML Pipeline Orchestrator**: Verify dataset_hash includes all 3 class counts

---

## Rollback Plan

If issues arise, the original 2-class workflows are preserved in `ml-agentic-ai_v.1/`. To rollback:

1. Deactivate v.2 workflows
2. Activate corresponding v.1 workflows
3. Revert Python code changes (num_classes=2)
