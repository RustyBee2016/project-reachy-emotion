---
title: Hybrid Storage Architecture (Filesystem + PostgreSQL)
kind: decision
owners: [Russell Bray]
related: [requirements.md#2, requirements.md#14]
created: 2025-09-20
updated: 2025-10-04
status: active
---

# Hybrid Storage Architecture (Filesystem + PostgreSQL)

## Context
The emotion recognition system requires storing video files, metadata, labels, and training artifacts. We evaluated three approaches:
1. **Object storage** (S3/MinIO/Supabase buckets)
2. **Database-only** (PostgreSQL with bytea/large objects)
3. **Hybrid** (filesystem for media + PostgreSQL for metadata)

Key constraints:
- Training I/O must sustain ≥1 GB/s sequential reads (NVMe SSD)
- Nginx must serve thumbnails with <30 ms median latency on LAN
- Atomic promotions from `temp/` → `train/test/` with ACID guarantees
- Simple backup/restore to Synology NAS via rsync
- Optional ZFS snapshots for rollback

## Decision
**Adopt hybrid storage**: local filesystem (ext4 or ZFS) for video files + PostgreSQL for metadata.

### Canonical Layout
```
/videos/
├── temp/           # Ingested clips awaiting curation (TTL 7-14 days)
├── train/          # Promoted training set
├── test/           # Promoted test set
├── thumbs/         # Pre-generated JPEG thumbnails
└── manifests/      # JSONL manifests (dataset_hash per rebuild)
```

### Responsibilities
- **Filesystem**: Stores `.mp4` files, `.jpg` thumbnails, `.jsonl` manifests.
- **PostgreSQL**: Stores metadata (`video_id`, `file_path`, `split`, `label`, `sha256`, `size_bytes`, `duration_sec`, `fps`, `width`, `height`, `zfs_snapshot`, timestamps).
- **mini-FastAPI**: Exposes `/api/videos/list`, `/api/promote`, `/api/relabel`, `/api/manifest/rebuild` with atomic operations.
- **Nginx**: Serves `/thumbs/` and `/videos/` directly (bypasses app layer for efficiency).

### Key Properties
- **Atomic promotions**: Same-filesystem `rename()` ensures ACID; DB update in transaction.
- **Deduplication**: Unique index on `(sha256, size_bytes)` prevents duplicate ingestion.
- **Integrity**: Nightly reconciler compares DB ↔ FS; Prometheus counters track drift.
- **Backup**: rsync to NAS mirrors `/videos/*` and `/mlruns`; quarterly restore test with hash verification.
- **Rollback**: ZFS snapshots before fine-tuning; `zfs rollback` + manifest rebuild on regression.

## Consequences
### Positive
- **Performance**: Direct filesystem I/O meets training throughput and Nginx latency targets.
- **Simplicity**: Standard POSIX operations; no object storage SDK dependencies.
- **Atomicity**: Same-FS `rename()` is atomic; no multi-phase commit complexity.
- **Backup**: rsync is simple, well-understood, and integrates with Synology NAS.
- **Flexibility**: Can layer ZFS (checksums, snapshots, compression) or stay on ext4.

### Negative
- **Single-machine**: Not distributed; scaling requires NFS/NAS (acceptable for current scope).
- **Manual reconciliation**: Requires nightly reconciler to detect FS/DB drift (mitigated by automation).
- **No built-in versioning**: Must use ZFS snapshots or manual copies (acceptable trade-off).

### Follow-Up Actions
- Implement nightly reconciler with Prometheus metrics (`videos_orphaned`, `videos_missing_db`).
- Document promotion dry-run flow in runbook.
- Add quarterly restore test to ops calendar.

## Alternatives Considered
### 1. Object Storage (S3/MinIO/Supabase)
- **Pros**: Distributed, versioned, scalable.
- **Cons**: Added latency for training I/O; SDK dependencies; complexity for atomic promotions; backup requires separate tooling.
- **Verdict**: Over-engineered for single-machine scope; revisit if multi-site deployment needed.

### 2. Database-Only (PostgreSQL bytea/large objects)
- **Pros**: Single source of truth; ACID guarantees.
- **Cons**: Poor I/O performance for large files; bloats DB size; complicates Nginx serving; backup/restore slower.
- **Verdict**: Unacceptable performance trade-offs for video workloads.

## Related
- **[requirements.md §2.1](../requirements.md#21-in-scope)**: Primary storage on local filesystem with canonical layout.
- **[requirements.md §14](../requirements.md#14-data-storage--curation-workflow)**: Directories, path conventions, dedup, promotion, integrity.
- **[requirements.md §15](../requirements.md#15-database-schema-metadata)**: PostgreSQL schema with `video` and `run_link` tables.
- **[requirements.md §16](../requirements.md#16-api-contract-minifastapi)**: mini-FastAPI endpoints for media operations.

## Notes
- ZFS is optional; ext4 is acceptable if ZFS overhead is undesirable.
- If multi-site deployment is required in future, consider MinIO with filesystem backend or NFS.
- Reconciler should run nightly and alert on drift >1% of total videos.

---

**Last Updated**: 2025-10-04  
**Owner**: Russell Bray
