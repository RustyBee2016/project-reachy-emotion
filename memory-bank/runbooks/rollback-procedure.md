---
title: Rollback Procedure (ZFS Snapshot + Manifest Rebuild)
kind: runbook
owners: [Russell Bray]
related: [requirements.md#23, decisions/001-hybrid-storage-architecture.md]
created: 2025-10-04
updated: 2025-10-04
status: active
---

# Runbook: Rollback Procedure

## Purpose
Step-by-step guide for rolling back to a previous dataset state using ZFS snapshots and rebuilding manifests after a failed training run or data corruption.

## Prerequisites
- ZFS filesystem on Ubuntu 1 (`tank/videos`)
- Valid ZFS snapshot (created before training or promotion)
- Access to Ubuntu 1 with `sudo` privileges
- Training/inference pipelines stopped

## When to Rollback
- **Model regression**: New model performs worse than baseline (accuracy drop >5%).
- **Data corruption**: Manifests or video files corrupted (sha256 mismatch, missing files).
- **Incorrect promotions**: Batch of videos promoted with wrong labels or split.
- **Training failure**: TAO training crashes due to bad data.

## Procedure

### 1. Identify Snapshot
List available snapshots and select the target.

```bash
ssh ubuntu1
sudo zfs list -t snapshot | grep tank/videos
```

**Example Output**:
```
tank/videos@pre-train-20251004-120000  0B  -  1.2T  -
tank/videos@pre-train-20251003-180000  512M  -  1.1T  -
tank/videos@pre-train-20251002-140000  1.5G  -  1.0T  -
```

**Selection Criteria**:
- Choose snapshot before the problematic change.
- Verify snapshot timestamp matches expected state.
- Check snapshot size (larger = more changes since snapshot).

### 2. Stop Writers
Stop all services that write to `/videos/` to prevent data loss.

```bash
# Stop media-mover API
sudo systemctl stop media-mover

# Stop training jobs (if running)
docker ps | grep tao
docker stop <tao-container-id>

# Stop reconciler (if running)
sudo systemctl stop reconciler
```

**Validation**:
```bash
sudo lsof +D /videos | grep -v "^COMMAND"
# Should return empty (no processes accessing /videos)
```

### 3. Rollback Filesystem
Revert `/videos/` to the selected snapshot.

```bash
sudo zfs rollback tank/videos@pre-train-20251004-120000
```

**Warning**: This is **destructive**. All changes after the snapshot are lost.

**Validation**:
```bash
# Check current snapshot
sudo zfs list -t snapshot | grep tank/videos | tail -1

# Verify file timestamps
ls -lh /videos/train/ | head -10
# Timestamps should match snapshot time
```

### 4. Rebuild Manifests
Regenerate JSONL manifests to match rolled-back filesystem.

```bash
curl -X POST http://ubuntu1:8081/api/manifest/rebuild \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Idempotency-Key: $(uuidgen)"
```

**Expected Response** (200 OK):
```json
{
  "status": "success",
  "manifests": {
    "train": "/videos/manifests/train_2025-10-04.jsonl",
    "test": "/videos/manifests/test_2025-10-04.jsonl"
  },
  "dataset_hash": "sha256:a1b2c3...",
  "counts": {
    "train": 1200,
    "test": 450
  }
}
```

**Validation**:
- `dataset_hash` matches expected value (from MLflow run before rollback).
- `counts` match expected dataset size.

### 5. Reconcile Database
Update PostgreSQL to match rolled-back filesystem.

```bash
# Run reconciler in dry-run mode
curl -X POST http://ubuntu1:8081/api/reconcile \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"dry_run": true}'
```

**Expected Response**:
```json
{
  "status": "dry_run",
  "orphaned_db_rows": 15,  # DB rows with no file
  "orphaned_files": 3,      # Files with no DB row
  "sha256_mismatches": 0
}
```

**Resolution**:
- **Orphaned DB rows**: Delete from DB (files no longer exist after rollback).
- **Orphaned files**: Add to DB or delete (depends on intent).
- **SHA256 mismatches**: Investigate corruption; re-ingest or delete.

```bash
# Execute reconciliation
curl -X POST http://ubuntu1:8081/api/reconcile \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"dry_run": false, "fix_orphans": true}'
```

### 6. Restart Services
Restart stopped services.

```bash
# Start media-mover API
sudo systemctl start media-mover

# Start reconciler
sudo systemctl start reconciler

# Verify services healthy
curl http://ubuntu1:8081/healthz
```

### 7. Re-Evaluate Model
If rollback was due to model regression, re-run evaluation on rolled-back dataset.

```bash
# Load baseline model
curl -X POST http://ubuntu1:8081/api/load-classifier \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"engine_path": "/opt/models/baseline-0.8.2.engine"}'

# Run evaluation
curl -X POST http://ubuntu1:8081/api/evaluate \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -d '{"manifest": "/videos/manifests/test_2025-10-04.jsonl"}'
```

**Expected Metrics**:
- Macro F1 ≥ 0.84
- Per-class F1 ≥ 0.75
- Calibration ECE ≤ 0.08

### 8. Document Incident
Log rollback in incident tracker.

**Template**:
```markdown
## Incident: Rollback to pre-train-20251004-120000

**Date**: 2025-10-04  
**Operator**: Russell Bray  
**Reason**: Model regression (macro F1 dropped from 0.86 to 0.78)  
**Snapshot**: tank/videos@pre-train-20251004-120000  
**Dataset Hash**: sha256:a1b2c3...  
**Actions**:
1. Stopped writers (media-mover, TAO, reconciler)
2. Rolled back to snapshot
3. Rebuilt manifests (dataset_hash: a1b2c3...)
4. Reconciled DB (deleted 15 orphaned rows)
5. Restarted services
6. Re-evaluated baseline model (macro F1: 0.86)

**Root Cause**: Bad batch of synthetic videos with incorrect labels  
**Prevention**: Add label validation step before promotion  
**Status**: Resolved
```

## Error Handling

### Error: `cannot rollback to 'tank/videos@...': more recent snapshots exist`
**Cause**: ZFS requires rolling back to the most recent snapshot first.

**Resolution**:
```bash
# List snapshots in reverse order
sudo zfs list -t snapshot -o name,creation -s creation | grep tank/videos | tail -5

# Rollback to most recent first, then target
sudo zfs rollback tank/videos@pre-train-20251004-140000
sudo zfs rollback tank/videos@pre-train-20251004-120000
```

### Error: `dataset is busy`
**Cause**: Processes still accessing `/videos/`.

**Resolution**:
```bash
# Find processes
sudo lsof +D /videos

# Kill processes
sudo kill -9 <pid>

# Retry rollback
sudo zfs rollback tank/videos@pre-train-20251004-120000
```

### Error: `snapshot does not exist`
**Cause**: Snapshot was deleted or never created.

**Resolution**:
1. Check snapshot naming convention (should be `pre-train-YYYYMMDD-HHMMSS`).
2. If no snapshot exists, rollback not possible; must manually fix data.
3. Going forward, enforce snapshot creation before training (add to CI).

## Monitoring
- **Prometheus metrics**: `rollbacks_total`, `reconcile_orphans_total`, `reconcile_duration_seconds`
- **Alerts**: Rollback executed (notify team), reconcile errors >10

## Related
- **[requirements.md §23](../requirements.md#23-operations-playbooks)**: Rollback playbook with ZFS snapshot.
- **[Decision: Hybrid Storage](../decisions/001-hybrid-storage-architecture.md)**: ZFS snapshots for rollback.
- **[Runbook: Promote Video Flow](./promote-video-flow.md)**: Promotion workflow that should precede snapshot.

---

**Last Updated**: 2025-10-04  
**Owner**: Russell Bray
