---
title: Ubuntu 1 Filesystem Operations & Cleanup
kind: runbook
owners: [rusty_admin]
related: [../requirements_08.4.2.md#14-data-storage--curation-workflow, ./rollback-procedure.md, ./promote-video-flow.md]
created: 2025-11-03
updated: 2025-11-03
status: active
---

# Ubuntu 1 Filesystem Operations & Cleanup

## Context
PromoteService persists media under `/videos/` on Ubuntu 1. Each promotion can create or move files across `temp/`, `dataset_all/`, and per-run splits (`train/<run_id>/`, `test/<run_id>/`). Operators need a single reference describing expected permissions, how to audit/repair them, how to recover after filesystem mishaps, and how to plan automated cleanup for aged per-run copies so storage stays predictable.

## Decision / Content
### Directory structure & permissions
- **Root**: `/videos` should exist on the ZFS dataset (`tank/videos`).
  - Ownership: `root:mediaops`
  - Mode: `0775`
  - Ensure recursive group write for automation: `sudo chown -R root:mediaops /videos && sudo chmod -R g+w /videos`
- **Subdirectories**:
  - `temp/`: ingest buffer. Mode `0775`. Set ACL to allow uploader service account (e.g., `reachy_app`):
    ```bash
    sudo setfacl -R -m u:reachy_app:rwx /videos/temp
    sudo setfacl -d -m u:reachy_app:rwx /videos/temp
    ```
  - `dataset_all/`: canonical labeled corpus. Mode `0775`, no default ACL. Only promotion service and reconciler should have write access (`mediaops` group).
  - `train/`, `test/`: per-run splits. Mode `0775` with default ACL granting `reachy_app` read-only (`r-x`) and `train_ops` write for evaluations:
    ```bash
    sudo setfacl -m u:reachy_app:rx /videos/train /videos/test
    sudo setfacl -m g:train_ops:rwx /videos/train /videos/test
    sudo setfacl -d -m g:train_ops:rwx /videos/train /videos/test
    ```
  - `manifests/`: JSONL artifacts. Mode `0755`. Owner `reachy_app:mediaops`.

**Verification checklist**
1. Confirm ownership: `sudo find /videos -maxdepth 1 -printf "%u:%g %p\n"`
2. Spot-check ACLs: `getfacl /videos/temp`
3. Verify new promotions inherit group write: promote a sample clip and run `ls -l`.

### Rollback and recovery references
- For full dataset rollbacks, use the **Rollback Procedure** runbook (`rollback-procedure.md`).
- For single-clip corrections, follow **Promote Video Flow** runbook section "Rollback".
- After any rollback, rerun manifest rebuild (`POST /promote/reset-manifest`) and reconciler dry run.

### Planned cleanup for per-run train/test copies
1. **Retention policy**
   - Keep per-run copies under `/videos/train/<run_id>/` and `/videos/test/<run_id>/` for 30 days unless run is marked `protected` in PostgreSQL (`training_runs.protected = true`).
2. **Staging script** `cleanup-train-test.sh` (store under `/usr/local/lib/reachy/`):
   ```bash
   #!/bin/bash
   set -euo pipefail

   RETENTION_DAYS=${RETENTION_DAYS:-30}
   TRAIN_ROOT="/videos/train"
   TEST_ROOT="/videos/test"

   prune_split() {
     local split_root=$1
     find "${split_root}" -mindepth 1 -maxdepth 1 -type d \
       -mtime +"${RETENTION_DAYS}" \
       -exec bash -c '
         run_id=$(basename "$1")
         protected=$(psql -XtAc "SELECT protected FROM training_runs WHERE run_id = \"$run_id\"" reachy_local | tr -d "\n \t")
         if [[ "$protected" != "t" ]]; then
           echo "Pruning $split_root/$run_id"
           rm -rf "$1"
         else
           echo "Skip protected run $run_id"
         fi
       ' bash {} \;
   }

   prune_split "$TRAIN_ROOT"
   prune_split "$TEST_ROOT"
   ```
   - Requires `psql` CLI and `reachy_local` connection access.
   - Execute as user in `mediaops` group.
3. **Systemd timer**
   - Unit file `/etc/systemd/system/cleanup-train-test.service`:
     ```ini
     [Unit]
     Description=Prune aged train/test run directories

     [Service]
     Type=oneshot
     ExecStart=/usr/local/lib/reachy/cleanup-train-test.sh
     User=reachy_app
     Group=mediaops
     ```
   - Timer `/etc/systemd/system/cleanup-train-test.timer`:
     ```ini
     [Unit]
     Description=Run train/test cleanup daily

     [Timer]
     OnCalendar=daily
     Persistent=true

     [Install]
     WantedBy=timers.target
     ```
   - Enable with:
     ```bash
     sudo systemctl daemon-reload
     sudo systemctl enable --now cleanup-train-test.timer
     ```
4. **Validation**
   - Dry run by setting `RETENTION_DAYS=0` env variable and invoking script manually.
   - Confirm pruning respects `protected` flag.
   - Audit logs: pipe script output to `/var/log/reachy/cleanup-train-test.log` via systemd `StandardOutput` directive if needed.

### Emergency rollback steps summary
1. Stop writers (`systemctl stop media-mover`, orchestrator, reconciler).
2. Snapshot or rollback via ZFS as per `rollback-procedure.md`.
3. Run `cleanup-train-test.sh` with `RETENTION_DAYS=0` to remove inconsistent per-run copies created post-event.
4. Trigger `/promote/reset-manifest` and reconciler reconciliation.
5. Restart services and document incident.

## Consequences
- Provides clear guidance for operators to maintain correct permissions.
- Prevents storage bloat via automated cleanup with safeguards for protected runs.
- Aligns rollback responses across runbooks.
- Requires keeping PostgreSQL accessible from cleanup script; add monitoring for script failures.

## Alternatives Considered
- Cron-based cleanup job (rejected in favor of systemd timer for reliability and persistent scheduling).
- Storing cleanup logic inside FastAPI background tasks (rejected to keep production API stateless and avoid cross-cutting file deletions).

## Related
- `requirements_08.4.2.md#14` for promotion storage policy.
- `runbooks/rollback-procedure.md` and `runbooks/promote-video-flow.md` for recovery sequences.
- Future work: integrate cleanup metrics into Prometheus (`cleanup_runs_pruned_total`).

## Notes
- Ensure `/usr/local/lib/reachy/cleanup-train-test.sh` has `0750` permissions and owned by `root:mediaops`.
- Update retention window if training cadence changes; log decision in ADR if >30 days.

---

**Last Updated**: 2025-11-03  
**Owner**: rusty_admin
