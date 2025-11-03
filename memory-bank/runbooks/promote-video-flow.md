---
title: Promote Video Flow (temp → train/test)
kind: runbook
owners: [Russell Bray]
related: [requirements.md#14, decisions/001-hybrid-storage-architecture.md]
created: 2025-10-04
updated: 2025-10-04
status: active
---

# Runbook: Promote Video Flow

## Purpose
Step-by-step guide for promoting videos from `temp/` to `train/` or `test/` with atomic operations, integrity checks, and audit logging.

## Prerequisites
- Access to Ubuntu 1 (media-mover API)
- Valid JWT token with `promote:write` scope
- `video_id` of clip to promote (from UI or `GET /api/videos/list?split=temp`)

## Procedure

### 1. Dry-Run (Recommended)
Validate the promotion plan before executing.

```bash
curl -X POST http://ubuntu1:8081/api/promote \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "video_id": "abc123-def456-...",
    "dest_split": "train",
    "label": "happy",
    "dry_run": true
  }'
```

**Expected Response** (200 OK):
```json
{
  "status": "dry_run",
  "plan": {
    "source": "/videos/temp/clip_00123.mp4",
    "dest": "/videos/train/clip_00123.mp4",
    "label": "happy",
    "sha256": "a1b2c3...",
    "size_bytes": 1048576
  },
  "checks": {
    "sha256_match": true,
    "dest_exists": false,
    "disk_space_ok": true
  }
}
```

**Validation**:
- `checks.sha256_match` must be `true` (file integrity verified).
- `checks.dest_exists` must be `false` (no collision).
- `checks.disk_space_ok` must be `true` (sufficient space).

### 2. Execute Promotion
If dry-run passes, execute the promotion.

```bash
curl -X POST http://ubuntu1:8081/api/promote \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: $(uuidgen)" \
  -d '{
    "video_id": "abc123-def456-...",
    "dest_split": "train",
    "label": "happy",
    "dry_run": false
  }'
```

**Expected Response** (200 OK):
```json
{
  "status": "success",
  "video_id": "abc123-def456-...",
  "new_path": "/videos/train/clip_00123.mp4",
  "label": "happy",
  "promoted_at": "2025-10-04T12:34:56Z"
}
```

### 3. Verify Promotion
Check that the file moved and DB updated.

```bash
# List videos in train split
curl -X GET "http://ubuntu1:8081/api/videos/list?split=train&limit=10" \
  -H "Authorization: Bearer $JWT_TOKEN"

# Verify specific video
curl -X GET "http://ubuntu1:8081/api/videos/abc123-def456-..." \
  -H "Authorization: Bearer $JWT_TOKEN"
```

**Expected Response**:
```json
{
  "video_id": "abc123-def456-...",
  "file_path": "videos/train/clip_00123.mp4",
  "split": "train",
  "label": "happy",
  "size_bytes": 1048576,
  "sha256": "a1b2c3...",
  "updated_at": "2025-10-04T12:34:56Z"
}
```

### 4. Rebuild Manifests
After promoting a batch of videos, rebuild manifests for training.

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
  "dataset_hash": "sha256:d4e5f6...",
  "counts": {
    "train": 1234,
    "test": 456
  }
}
```

**Validation**:
- `dataset_hash` changes after promotion (indicates manifest updated).
- `counts.train` increments by number of promoted videos.

### 5. (Optional) Create ZFS Snapshot
If using ZFS, snapshot before training.

```bash
ssh ubuntu1
sudo zfs snapshot tank/videos@pre-train-$(date +%Y%m%d-%H%M%S)
sudo zfs list -t snapshot | grep videos
```

## Error Handling

### Error: `dest_exists: true`
**Cause**: File already exists at destination (collision).

**Resolution**:
1. Check if existing file is identical (same `sha256`).
2. If identical, skip promotion (already promoted).
3. If different, investigate collision (possible duplicate with different content).

### Error: `sha256_mismatch`
**Cause**: File corrupted or modified since ingestion.

**Resolution**:
1. Re-compute `sha256` on source file.
2. If mismatch persists, discard file (do not promote corrupted data).
3. Log incident for investigation.

### Error: `disk_space_insufficient`
**Cause**: Destination filesystem low on space.

**Resolution**:
1. Check disk usage: `df -h /videos`
2. Purge expired `temp/` files: `POST /api/purge?split=temp&ttl_days=7`
3. Archive old `train/test/` to NAS if needed.
4. Retry promotion.

### Error: `401 Unauthorized`
**Cause**: JWT token expired or invalid.

**Resolution**:
1. Refresh JWT token from auth service.
2. Retry with new token.

### Error: `409 Conflict` (Idempotency-Key collision)
**Cause**: Same `Idempotency-Key` used for different request.

**Resolution**:
1. Generate new `Idempotency-Key` (use `uuidgen` or similar).
2. Retry promotion.

## Rollback
If promotion was incorrect (wrong label, wrong split):

### Option 1: Relabel
```bash
curl -X POST http://ubuntu1:8081/api/relabel \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc123-def456-...",
    "label": "sad"
  }'
```

### Option 2: Demote to temp
```bash
curl -X POST http://ubuntu1:8081/api/promote \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "video_id": "abc123-def456-...",
    "dest_split": "temp",
    "label": null
  }'
```

### Option 3: Delete
```bash
curl -X DELETE http://ubuntu1:8081/api/videos/abc123-def456-... \
  -H "Authorization: Bearer $JWT_TOKEN" \
  -H "X-Reason: incorrect-label"
```

**Note**: Deletion is permanent; ensure audit log captures reason.

## Audit Log
All promotions are logged to `/var/log/media-mover/promotions.jsonl`:

```json
{
  "ts": "2025-10-04T12:34:56Z",
  "operator": "user@example.com",
  "video_id": "abc123-def456-...",
  "source": "/videos/temp/clip_00123.mp4",
  "dest": "/videos/train/clip_00123.mp4",
  "label": "happy",
  "idempotency_key": "uuid-...",
  "status": "success"
}
```

## Monitoring
- **Prometheus metrics**: `promotions_total`, `promotions_errors_total`, `promotion_duration_seconds`
- **Alerts**: Spike in errors, slow promotions (>5s), disk space <10%

## Related
- **[requirements.md §14](../requirements.md#14-data-storage--curation-workflow)**: Promotion workflow, dry-run, idempotency.
- **[requirements.md §16](../requirements.md#16-api-contract-minifastapi)**: API contract for `/api/promote`.
- **[Decision: Hybrid Storage](../decisions/001-hybrid-storage-architecture.md)**: Rationale for filesystem + PostgreSQL.

---

**Last Updated**: 2025-10-04  
**Owner**: Russell Bray
