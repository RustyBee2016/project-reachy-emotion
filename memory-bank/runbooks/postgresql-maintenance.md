---
title: PostgreSQL 16 Service Maintenance (Ubuntu 1)
kind: runbook
owners: [rusty_admin]
related: [../requirements_08.4.2.md#15-database-schema-metadata, ../requirements_08.4.2.md#23-operations-playbooks]
created: 2025-11-03
updated: 2025-11-03
status: active
---

# PostgreSQL 16 Service Maintenance (Ubuntu 1)

## Context
Media Mover and promotion workflows depend on PostgreSQL 16 (`postgresql@16-main`) running on Ubuntu 1. This runbook documents routine service health checks, package/driver validation for async clients, role privilege audits, and remediation steps to avoid the regressions captured in "Postgres & Promotion Challenges and Resolutions".

## Decision / Content
### Service health monitoring
1. **Systemd status**
   ```bash
   sudo systemctl status postgresql@16-main
   sudo journalctl -u postgresql@16-main -n 200 --no-pager
   ```
   - Ensure `Active: active (running)`.
   - Investigate repeated restarts or crash loops.
2. **Port listener & connectivity**
   ```bash
   sudo ss -ltnp | grep 5432
   psql "postgresql://reachy_app@localhost:5432/reachy_local" -c 'SELECT 1'
   ```
3. **Prometheus scrape** (if enabled)
   - Endpoint: `http://localhost:9187/metrics` (postgres_exporter).
   - Metrics to alert on: `pg_up == 0`, `pg_stat_database_xact_rollback_total` spikes, `pg_locks` > threshold.

### Package / driver verification
- Deployment Python venv: `/opt/reachy/venvs/media-mover` (adjust if different).
- Ensure async driver `asyncpg` remains installed; fallback `psycopg[binary]` supported.
  ```bash
  source /opt/reachy/venvs/media-mover/bin/activate
  python - <<'PY'
  import importlib
  for pkg in ("asyncpg", "sqlalchemy", "psycopg");
      spec = importlib.util.find_spec(pkg)
      print(pkg, "ok" if spec else "missing")
  PY
  ```
- On failure, reinstall pinned versions from `requirements_08.4.2.md`:
  ```bash
  pip install "asyncpg>=0.29" "SQLAlchemy>=2.0" "psycopg[binary]>=3.1"
  deactivate
  ```
- Confirm Alembic compatibility: `alembic --version` matches toolchain.

### Role & privilege audit
1. List roles and attributes:
   ```bash
   psql -c "\du"
   ```
2. Inspect database grants:
   ```bash
   psql -d reachy_local -c "\dn+"
   psql -d reachy_local -c "\dp"
   ```
3. Validation checklist:
   - `reachy_app` role: `LOGIN`, `CONNECT` on `reachy_local`, `USAGE` on `public`, `SELECT/INSERT/UPDATE/DELETE` on application tables only.
   - `reachy_app` should **not** have `SUPERUSER` or `CREATEDB`.
   - `reachy_migrations` role (if present) holds `ALTER` privileges for Alembic migrations but is not used by runtime service.
4. Enforce security baseline:
   ```sql
   REVOKE ALL ON DATABASE reachy_local FROM PUBLIC;
   GRANT CONNECT ON DATABASE reachy_local TO reachy_app;
   ALTER ROLE reachy_app NOCREATEDB NOCREATEROLE NOSUPERUSER;
   ```

### Backups & retention
- Reference NAS backup runbook for filesystem-level backups; for DB dumps ensure weekly `pg_dump` stored under `/backups/postgres/`.
- Schedule `systemd` timer `pgdump-weekly.timer`:
  ```ini
  [Unit]
  Description=Weekly PostgreSQL logical backup

  [Timer]
  OnCalendar=Sun *-*-* 03:00:00
  Persistent=true

  [Install]
  WantedBy=timers.target
  ```
- Service script `pgdump-weekly.sh`:
  ```bash
  #!/bin/bash
  set -euo pipefail
  TARGET_DIR=/backups/postgres/$(date +%Y/%m/%d)
  mkdir -p "$TARGET_DIR"
  pg_dump reachy_local > "$TARGET_DIR/reachy_local.sql"
  ```

### Maintenance windows
- Quarterly vacuum/analyze:
  ```bash
  psql -d reachy_local -c 'VACUUM (ANALYZE);'
  ```
- Monitor autovacuum logs via `journalctl -u postgresql@16-main -g autovacuum`.
- Major version upgrades: follow Ubuntu PGDG instructions; take ZFS snapshot and DB dump beforehand.

### Incident response summary
1. Service down → check systemd status, restart: `sudo systemctl restart postgresql@16-main`.
2. Connection errors from app → verify driver modules, rotate service credentials if compromised.
3. Privilege drift detected → apply baseline SQL, log in incident tracker.
4. Performance regression → capture `pg_stat_activity`, evaluate slow queries, adjust indexes per requirements.

## Consequences
- Keeps PostgreSQL service reliable for promotions and reconciler.
- Ensures async drivers remain present to avoid runtime import errors.
- Reduces risk of privilege escalation or accidental data loss.

## Alternatives Considered
- Dockerized PostgreSQL (rejected: adds complexity, existing service manageable).
- Direct system cron for dumps (systemd timer chosen for better observability and persistence).

## Related
- `requirements_08.4.2.md` sections 15 & 23 for DB schema and operational policies.
- NAS backup runbook for storage redundancy.
- Incident reports referenced in `docs/gpt/2025-11-02-Postgres_and_Promotion_Challenges_and_Resolutions.txt`.

## Notes
- Document any schema changes via Alembic migrations; update runbook with new maintenance tasks.
- Add Prometheus alerting rules: `pg_up == 0`, `pg_checkpoint_write_time_seconds > 30`, `pg_stat_activity` waiting sessions.

---

**Last Updated**: 2025-11-03  
**Owner**: rusty_admin
