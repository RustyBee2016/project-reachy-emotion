# Reachy Database Training Curriculum

## Welcome

This curriculum teaches the PostgreSQL database system for the Reachy Emotion Detection project. It is designed for developers who are new to database management and PostgreSQL.

## Learning Path

```
Week 1                    Week 2                    Week 3
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Module 1       │      │  Module 3       │      │  Module 6       │
│  DB Fundamentals│─────▶│  Reachy Schema  │─────▶│  API Integration│
│  (4 hours)      │      │  (4 hours)      │      │  (4 hours)      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
        │                        │                        │
        ▼                        ▼                        ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│  Module 2       │      │  Module 4       │      │  Module 7       │
│  PostgreSQL     │─────▶│  Stored Procs   │─────▶│  Migrations     │
│  (4 hours)      │      │  (3 hours)      │      │  (3 hours)      │
└─────────────────┘      └─────────────────┘      └─────────────────┘
                                 │                        │
                                 ▼                        ▼
                         ┌─────────────────┐      ┌─────────────────┐
                         │  Module 5       │      │  Module 8       │
                         │  SQLAlchemy ORM │─────▶│  Troubleshooting│
                         │  (4 hours)      │      │  (2 hours)      │
                         └─────────────────┘      └─────────────────┘
```

**Total Time**: ~28 hours over 3 weeks

---

## Module Summary

| Module | Title | Duration | Prerequisites |
|--------|-------|----------|---------------|
| 1 | Database Fundamentals | 4 hours | None |
| 2 | PostgreSQL Essentials | 4 hours | Module 1 |
| 3 | Reachy Schema Deep Dive | 4 hours | Module 2 |
| 4 | Stored Procedures & Business Logic | 3 hours | Module 3 |
| 5 | Python ORM with SQLAlchemy | 4 hours | Module 2, Python basics |
| 6 | API Integration | 4 hours | Module 5 |
| 7 | Migrations & DevOps | 3 hours | Modules 3, 5 |
| 8 | Troubleshooting & Known Issues | 2 hours | All previous |

---

## What You'll Learn

### By End of Week 1
- Understand relational database concepts
- Write basic SQL queries (SELECT, INSERT, UPDATE, DELETE)
- Navigate PostgreSQL using `psql` command-line tool
- Understand transactions and ACID properties

### By End of Week 2
- Know all 9 tables in the Alembic-managed schema (plus 3 legacy-only tables)
- Understand the current video lifecycle (temp → train/<label> → run-specific frame datasets → purged)
- Use stored procedures for business operations
- Write Python code using SQLAlchemy ORM

### By End of Week 3
- Build API endpoints that interact with the database
- Manage database migrations with Alembic
- Understand how SQLAlchemy models translate to database tables
- Debug common database issues
- Deploy the database to development/production

---

## Required Software

Before starting, ensure you have:

| Software | Version | Installation |
|----------|---------|--------------|
| PostgreSQL | 15 or 16 | `sudo apt install postgresql-16` |
| Python | 3.10+ | Pre-installed on Ubuntu |
| psql | (with PostgreSQL) | Included with PostgreSQL |
| DBeaver (optional) | Latest | GUI tool for database exploration |

---

## Key Files Reference

Throughout this curriculum, you'll work with these files:

### Schema Definition (Authoritative)
```
apps/api/app/db/
├── models.py                  # SQLAlchemy ORM models — defines all 9 tables
├── enums.py                   # Enum definitions (split, emotion, target_split)
├── base.py                    # Base class and TimestampMixin
├── session.py                 # Database session factory
└── alembic/
    ├── alembic.ini            # Alembic configuration
    ├── env.py                 # Migration environment (imports Base.metadata)
    └── versions/
        └── 202510280000_initial_schema.py  # Initial migration (creates 4 core tables)
```

### Legacy SQL Files (Reference Only — DEPRECATED)
```
alembic/versions/
├── 001_phase1_schema.sql      # DEPRECATED — replaced by Alembic migration
├── 002_stored_procedures.sql  # Optional helper functions for ad-hoc queries
└── 003_missing_tables.sql     # DEPRECATED — tables now in models.py
```

### Application Layer
```
apps/api/app/
├── routers/promote.py         # Promotion API endpoints
├── services/promote_service.py # Business logic
└── repositories/video_repository.py # Data access layer
```

### Configuration
```
apps/api/app/config.py         # Database connection settings
misc/code/bootstrap_reachy_db_and_media.sh  # Setup script
```

---

## How to Use This Curriculum

### Self-Study
1. Read each module in order
2. Complete all exercises before moving on
3. Use the provided SQL files to practice
4. Ask questions in team Slack/Discord

### Instructor-Led
1. Schedule 2-hour sessions twice per week
2. Instructor demonstrates concepts
3. Students complete exercises during sessions
4. Review and Q&A at end of each session

### Assessment
Each module includes:
- **Knowledge Check**: Multiple-choice questions
- **Hands-On Exercise**: Practical coding tasks
- **Capstone Project**: Module 8 includes a final project

---

## Database Connection Quick Reference

### Development (Docker)
```bash
# Start PostgreSQL
docker run -d --name reachy_postgres \
  -e POSTGRES_DB=reachy_local \
  -e POSTGRES_USER=reachy_app \
  -e POSTGRES_PASSWORD=dev_password \
  -p 5432:5432 postgres:16

# Connect
psql -h localhost -U reachy_app -d reachy_local
```

### Development (Local)
```bash
# Connect to local PostgreSQL
psql -U reachy_app -d reachy_local
```

### Connection String (Python)
```python
DATABASE_URL = "postgresql+asyncpg://reachy_app:password@localhost:5432/reachy_local"
```

---

## Instructor Notes

### Preparing Lab Environment

Before each session:
1. Ensure PostgreSQL is running
2. Reset database to clean state if needed:
   ```bash
   psql -U postgres -c "DROP DATABASE IF EXISTS reachy_local;"
   psql -U postgres -c "CREATE DATABASE reachy_local OWNER reachy_app;"
   alembic -c apps/api/app/db/alembic/alembic.ini upgrade head
   ```
3. Have sample data ready (see exercises file)

### Common Student Issues
- Forgetting to start PostgreSQL service
- Connection string typos
- Not understanding async vs sync Python
- Confusing ORM models with database tables

---

## Getting Help

- **Documentation**: `docs/database/` folder
- **Known Issues**: `docs/database/07-KNOWN-ISSUES.md` (most issues now resolved)
- **Setup Guide**: `docs/database/08-SETUP-GUIDE.md`

---

## Let's Begin!

Start with [Module 1: Database Fundamentals](./01-MODULE-DATABASE-FUNDAMENTALS.md)
