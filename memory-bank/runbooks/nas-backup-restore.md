---
title: NAS Backup & Restore (Synology Redundancy)
kind: runbook
owners: [Russell Bray]
related: [requirements.md#5.4, requirements.md#23]
created: 2025-10-04
updated: 2025-10-04
status: active
---

# Runbook: NAS Backup & Restore

## Purpose
Step-by-step guide for nightly backup of `/videos/` and `/mlruns` to Synology NAS, quarterly restore testing, and disaster recovery.

## Prerequisites
- Synology NAS accessible via NFS or SMB
- rsync installed on Ubuntu 1
- SSH key-based auth to NAS (if using rsync over SSH)
- Cron job configured for nightly backup

## Architecture
- **Source**: Ubuntu 1 (`/videos/`, `/mlruns`)
- **Destination**: Synology NAS (`/volume1/reachy-backup/videos/`, `/volume1/reachy-backup/mlruns/`)
- **Method**: rsync with `--archive`, `--delete`, `--checksum`
- **Schedule**: Nightly at 02:00 UTC (low-traffic window)
- **Retention**: Keep 7 daily snapshots on NAS (via Synology Snapshot Replication)

## Backup Procedure

### 1. Manual Backup (Testing)
Run backup manually to verify configuration.

```bash
ssh ubuntu1

# Backup /videos/
rsync -avz --delete --checksum \
  /videos/ \
  nas.local:/volume1/reachy-backup/videos/ \
  --log-file=/var/log/rsync/videos-$(date +%Y%m%d-%H%M%S).log

# Backup /mlruns
rsync -avz --delete --checksum \
  /mlruns/ \
  nas.local:/volume1/reachy-backup/mlruns/ \
  --log-file=/var/log/rsync/mlruns-$(date +%Y%m%d-%H%M%S).log
```

**Flags**:
- `-a`: Archive mode (preserves permissions, timestamps, symlinks)
- `-v`: Verbose
- `-z`: Compress during transfer
- `--delete`: Remove files on destination that no longer exist on source
- `--checksum`: Verify files by checksum (slower but safer)

**Validation**:
```bash
# Check exit code (0 = success)
echo $?

# Verify file count
ssh nas.local "find /volume1/reachy-backup/videos -type f | wc -l"
# Should match source: find /videos -type f | wc -l

# Verify total size
ssh nas.local "du -sh /volume1/reachy-backup/videos"
du -sh /videos
```

### 2. Automated Backup (Cron)
Configure cron job for nightly backup.

```bash
# Edit crontab
crontab -e

# Add entry (runs at 02:00 UTC daily)
0 2 * * * /usr/local/bin/backup-to-nas.sh >> /var/log/rsync/cron.log 2>&1
```

**Script**: `/usr/local/bin/backup-to-nas.sh`
```bash
#!/bin/bash
set -euo pipefail

LOG_DIR="/var/log/rsync"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# Backup /videos/
rsync -avz --delete --checksum \
  /videos/ \
  nas.local:/volume1/reachy-backup/videos/ \
  --log-file="${LOG_DIR}/videos-${TIMESTAMP}.log"

VIDEOS_EXIT=$?

# Backup /mlruns
rsync -avz --delete --checksum \
  /mlruns/ \
  nas.local:/volume1/reachy-backup/mlruns/ \
  --log-file="${LOG_DIR}/mlruns-${TIMESTAMP}.log"

MLRUNS_EXIT=$?

# Emit Prometheus metrics
echo "backup_videos_exit_code ${VIDEOS_EXIT}" | curl --data-binary @- http://localhost:9091/metrics/job/backup/instance/videos
echo "backup_mlruns_exit_code ${MLRUNS_EXIT}" | curl --data-binary @- http://localhost:9091/metrics/job/backup/instance/mlruns

# Alert on failure
if [ $VIDEOS_EXIT -ne 0 ] || [ $MLRUNS_EXIT -ne 0 ]; then
  echo "Backup failed: videos=$VIDEOS_EXIT, mlruns=$MLRUNS_EXIT" | mail -s "NAS Backup Failure" rustybee255@gmail.com
  exit 1
fi

echo "Backup completed successfully at ${TIMESTAMP}"
```

**Permissions**:
```bash
sudo chmod +x /usr/local/bin/backup-to-nas.sh
```

### 3. Monitor Backup Health
Check rsync logs and Prometheus metrics.

```bash
# Check latest log
tail -50 /var/log/rsync/videos-*.log | grep -E "total size|speedup"

# Check Prometheus metrics
curl http://localhost:9091/metrics | grep backup_exit_code
```

**Expected Metrics**:
- `backup_videos_exit_code 0`
- `backup_mlruns_exit_code 0`

**Alerts**:
- Exit code ≠ 0 → immediate page
- Backup duration >60 min → investigate
- Backup size delta >20% → investigate

## Restore Procedure

### 1. Quarterly Restore Test
Verify backup integrity by restoring to a test directory.

```bash
ssh ubuntu1

# Create test directory
sudo mkdir -p /tmp/restore-test/videos /tmp/restore-test/mlruns

# Restore /videos/
rsync -avz --checksum \
  nas.local:/volume1/reachy-backup/videos/ \
  /tmp/restore-test/videos/ \
  --log-file=/var/log/rsync/restore-test-$(date +%Y%m%d-%H%M%S).log

# Restore /mlruns
rsync -avz --checksum \
  nas.local:/volume1/reachy-backup/mlruns/ \
  /tmp/restore-test/mlruns/ \
  --log-file=/var/log/rsync/restore-test-$(date +%Y%m%d-%H%M%S).log
```

**Validation**:
```bash
# Compare file counts
diff <(find /videos -type f | sort) <(find /tmp/restore-test/videos -type f | sort)
# Should be empty (no differences)

# Compare checksums (sample 100 files)
find /videos -type f | shuf -n 100 | while read f; do
  sha256sum "$f"
  sha256sum "/tmp/restore-test/${f#/}"
done | sort | uniq -c | grep -v "^ *2 "
# Should be empty (all files have 2 identical checksums)

# Cleanup
sudo rm -rf /tmp/restore-test
```

**Document Results**:
```markdown
## Quarterly Restore Test — 2025-10-04

**Operator**: Russell Bray  
**Backup Date**: 2025-10-03 02:00 UTC  
**Restore Duration**: 45 minutes  
**Files Restored**: 1,234 videos, 56 MLflow runs  
**Checksum Validation**: 100/100 sampled files matched  
**Status**: ✅ PASS

**Next Test**: 2026-01-04
```

### 2. Disaster Recovery (Full Restore)
Restore `/videos/` and `/mlruns` after data loss or hardware failure.

**Scenario**: Ubuntu 1 SSD failed; replaced with new drive.

```bash
# Mount new SSD
sudo mkfs.ext4 /dev/nvme0n1p1
sudo mount /dev/nvme0n1p1 /mnt/new-ssd

# Restore /videos/
rsync -avz --checksum \
  nas.local:/volume1/reachy-backup/videos/ \
  /mnt/new-ssd/videos/ \
  --log-file=/var/log/rsync/disaster-restore-videos-$(date +%Y%m%d-%H%M%S).log

# Restore /mlruns
rsync -avz --checksum \
  nas.local:/volume1/reachy-backup/mlruns/ \
  /mnt/new-ssd/mlruns/ \
  --log-file=/var/log/rsync/disaster-restore-mlruns-$(date +%Y%m%d-%H%M%S).log

# Verify checksums (sample)
find /mnt/new-ssd/videos -type f | shuf -n 100 | xargs sha256sum > /tmp/checksums-restored.txt
# Compare against known-good checksums from DB or previous backup

# Update fstab and reboot
sudo nano /etc/fstab
# Add: /dev/nvme0n1p1 /videos ext4 defaults 0 2
sudo reboot
```

**Post-Restore**:
1. Reconcile DB with restored files: `POST /api/reconcile`
2. Rebuild manifests: `POST /api/manifest/rebuild`
3. Verify training pipeline: run eval on test set
4. Resume normal operations

## Error Handling

### Error: `rsync: connection refused`
**Cause**: NAS unreachable or SSH service down.

**Resolution**:
1. Ping NAS: `ping nas.local`
2. Check SSH: `ssh nas.local "echo ok"`
3. Verify NAS is powered on and network connected.
4. Check firewall rules on NAS.

### Error: `rsync: permission denied`
**Cause**: SSH key not authorized or incorrect permissions.

**Resolution**:
1. Verify SSH key: `ssh-add -l`
2. Copy public key to NAS: `ssh-copy-id nas.local`
3. Check NAS user permissions on `/volume1/reachy-backup/`.

### Error: `rsync: disk full`
**Cause**: NAS out of space.

**Resolution**:
1. Check NAS disk usage: `ssh nas.local "df -h /volume1"`
2. Delete old snapshots or expand storage.
3. Retry backup.

### Error: Checksum mismatch during restore
**Cause**: Data corruption on NAS or during transfer.

**Resolution**:
1. Re-run rsync with `--checksum` to re-transfer corrupted files.
2. If corruption persists, check NAS SMART status: `ssh nas.local "smartctl -a /dev/sda"`
3. If drive failing, replace and restore from older snapshot.

## Monitoring
- **Prometheus metrics**: `backup_exit_code`, `backup_duration_seconds`, `backup_size_bytes`
- **Alerts**:
  - Backup exit code ≠ 0 → immediate page
  - Backup not run in 25 hours → warning
  - NAS disk usage >90% → warning
  - Restore test overdue (>95 days) → reminder

## Related
- **[requirements.md §5.4](../requirements.md#54-redundancy--backup)**: NAS mirror, quarterly restore test.
- **[requirements.md §23](../requirements.md#23-operations-playbooks)**: Backup/restore playbook with hash verification.
- **[Decision: Hybrid Storage](../decisions/001-hybrid-storage-architecture.md)**: rsync to NAS for redundancy.

---

**Last Updated**: 2025-10-04  
**Owner**: Russell Bray
