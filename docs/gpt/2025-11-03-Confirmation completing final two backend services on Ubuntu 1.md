**2025-11-03-Confirmation completing final two backend services on
Ubuntu 1**

**Confirmation completing final two backend services on Ubuntu 1**

Final two steps:

1\. Operational polish: document filesystem permissions/rollbacks in
memory-bank

runbooks and plan cleanup jobs for per-run train/test copies, keeping
Ubuntu 1's

storage predictable.@docs/gpt/2025-11-01-

Promotion_System_Summary_of_steps_1-3.txt#82-85

2\. Monitor PostgreSQL long-term: maintain the postgresql@16-main
service, ensure

async drivers remain installed in the deployment venv, and periodically
validate role

privileges to avoid recurrence.@docs/gpt/2025-11-02-

Postgres_and_Promotion_Challenges_and_Resolutions.txt#3-36

\[MEMORY BANK: ACTIVE\]

Yes---those two items were the final backend tasks from "Current Status
and Next Steps," and they are now covered. I added two new runbooks:

• **Ubuntu 1 Filesystem Operations & Cleanup** documents directory
permissions,

ties rollback references together, and defines a systemd-timer cleanup
plan for perrun train/test folders so storage stays
tidy.@memory-bank/runbooks/filesystemoperations.md#1-142

• **PostgreSQL 16 Service Maintenance** captures routine service health
checks,

async driver validation, privilege audits, and backup guidance to keep
the DB stable

on Ubuntu 1.@memory-bank/runbooks/postgresql-maintenance.md#1-142

These satisfy the remaining operational polish and PostgreSQL monitoring
steps. Let me know if you'd like any follow-up actions or verification
runs.
