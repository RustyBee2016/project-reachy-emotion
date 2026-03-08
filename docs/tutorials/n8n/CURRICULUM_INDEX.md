# n8n Agentic AI Development Curriculum

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2
**Instructor**: Cascade (AI)
**Student**: Russ
**Total Duration**: ~40-50 hours
**Outcome**: Professional-level n8n development skills

---

## Course Overview

This curriculum teaches n8n workflow development through the practical implementation of the Reachy_Local_08.4.2 agentic AI system. By the end, you will have:

1. ✅ Mastered n8n fundamentals (nodes, expressions, credentials)
2. ✅ Wired all 10 agentic workflows from scratch
3. ✅ Understood advanced patterns (polling, orchestration, error handling)
4. ✅ Deployed a production-ready ML pipeline orchestration system

---

## Module Structure

Each module follows this pattern:

```
┌─────────────────────────────────────────────────────────────────┐
│  1. PRE-WIRING CHECKLIST                                        │
│     - Verify all backend functionalities                        │
│     - Test each endpoint/service the workflow depends on        │
│     - Mark items Complete before proceeding                     │
├─────────────────────────────────────────────────────────────────┤
│  2. CONCEPT EXPLANATION                                         │
│     - What does this agent do?                                  │
│     - How does it fit in the overall system?                    │
│     - Architecture diagram                                      │
├─────────────────────────────────────────────────────────────────┤
│  3. STEP-BY-STEP WIRING                                         │
│     - Node-by-node instructions                                 │
│     - Parameter-by-parameter configuration                      │
│     - Expression explanations                                   │
├─────────────────────────────────────────────────────────────────┤
│  4. TESTING & ACTIVATION                                        │
│     - Manual test procedures                                    │
│     - Edge case testing                                         │
│     - Production activation                                     │
├─────────────────────────────────────────────────────────────────┤
│  5. TROUBLESHOOTING                                             │
│     - Common problems and solutions                             │
│     - Debugging techniques                                      │
└─────────────────────────────────────────────────────────────────┘
```

---

## Curriculum Modules

### Foundation

| Module | Title | Duration | Status |
|--------|-------|----------|--------|
| **00** | [n8n Fundamentals](MODULE_00_N8N_FUNDAMENTALS.md) | 3 hours | ✅ Complete |

**Topics**: Architecture, data flow, expressions, node types, credentials, error handling

---

### Core Agents (Data Pipeline)

| Module | Title | Workflow | Duration | Status |
|--------|-------|----------|----------|--------|
| **01** | [Ingest Agent](MODULE_01_INGEST_AGENT.md) | `01_ingest_agent.json` | 4 hours | ✅ Complete |
| **02** | [Labeling Agent](MODULE_02_LABELING_AGENT.md) | `02_labeling_agent.json` | 3 hours | ✅ Complete |
| **03** | [Promotion Agent](MODULE_03_PROMOTION_AGENT.md) | `03_promotion_agent.json` | 4 hours | ✅ Complete |

**Topics**: Webhooks, authentication, polling, database operations, state management, idempotency

---

### Maintenance Agents

| Module | Title | Workflow | Duration | Status |
|--------|-------|----------|----------|--------|
| **04** | [Reconciler Agent](MODULE_04_RECONCILER_AGENT.md) | `04_reconciler_agent.json` | 3 hours | ✅ Complete |
| **05** | [Privacy Agent](MODULE_05_PRIVACY_AGENT.md) | `08_privacy_agent.json` | 2 hours | ✅ Complete |

**Topics**: Scheduled triggers, batch processing, SSH operations, compliance

---

### ML Pipeline Agents

| Module | Title | Workflow | Duration | Status |
|--------|-------|----------|----------|--------|
| **06** | [Training Orchestrator](MODULE_06_TRAINING_ORCHESTRATOR.md) | `05_training_orchestrator_efficientnet.json` | 5 hours | ✅ Complete |
| **07** | [Evaluation Agent](MODULE_07_EVALUATION_AGENT.md) | `06_evaluation_agent_efficientnet.json` | 3 hours | ✅ Complete |
| **08** | [Deployment Agent](MODULE_08_DEPLOYMENT_AGENT.md) | `07_deployment_agent_efficientnet.json` | 4 hours | ✅ Complete |

**Topics**: Long-running processes, MLflow integration, quality gates, SSH/SCP, rollback patterns

---

### Observability & Orchestration

| Module | Title | Workflow | Duration | Status |
|--------|-------|----------|----------|--------|
| **09** | [Observability Agent](MODULE_09_OBSERVABILITY_AGENT.md) | `09_observability_agent.json` | 3 hours | ✅ Complete |
| **10** | [ML Pipeline Orchestrator](MODULE_10_ML_PIPELINE_ORCHESTRATOR.md) | `10_ml_pipeline_orchestrator.json` | 5 hours | ✅ Complete |

**Topics**: Metrics collection, alerting, workflow-to-workflow calls, end-to-end orchestration

---

### Advanced Topics

| Module | Title | Duration | Status |
|--------|-------|----------|--------|
| **11** | [Error Handling & Recovery](MODULE_11_ERROR_HANDLING.md) | 2 hours | ✅ Complete |
| **12** | [Testing & Debugging Strategies](MODULE_12_TESTING_DEBUGGING.md) | 2 hours | ✅ Complete |
| **13** | [Production Operations](MODULE_13_PRODUCTION_OPS.md) | 2 hours | ✅ Complete |

**Topics**: Error workflows, sub-workflows, versioning, monitoring, backup/restore

---

### Reference Documents

| Document | Description |
|----------|-------------|
| [Node Reference -- All Agents](NODE_REFERENCE_ALL_AGENTS.md) | Comprehensive node-by-node reference for all 10 workflows (118 nodes total). Includes node types, parameters, connections, credentials, environment variables, and architecture patterns extracted directly from the v.2 workflow JSON files. |

---

## Learning Path

```
                                    START HERE
                                        │
                                        ▼
                            ┌───────────────────────┐
                            │  Module 00            │
                            │  n8n Fundamentals     │
                            │  (3 hours)            │
                            └───────────┬───────────┘
                                        │
                    ┌───────────────────┴───────────────────┐
                    │           CORE DATA PIPELINE          │
                    │                                       │
                    ▼                                       │
        ┌───────────────────────┐                          │
        │  Module 01            │                          │
        │  Ingest Agent         │                          │
        │  (4 hours)            │                          │
        └───────────┬───────────┘                          │
                    │                                       │
                    ▼                                       │
        ┌───────────────────────┐                          │
        │  Module 02            │                          │
        │  Labeling Agent       │                          │
        │  (3 hours)            │                          │
        └───────────┬───────────┘                          │
                    │                                       │
                    ▼                                       │
        ┌───────────────────────┐                          │
        │  Module 03            │                          │
        │  Promotion Agent      │                          │
        │  (4 hours)            │                          │
        └───────────┬───────────┘                          │
                    │                                       │
    ┌───────────────┴───────────────┐                      │
    │                               │                      │
    ▼                               ▼                      │
┌───────────────┐           ┌───────────────┐              │
│ Module 04     │           │ Module 06     │              │
│ Reconciler    │           │ Training      │              │
│ (3 hours)     │           │ Orchestrator  │              │
└───────┬───────┘           │ (5 hours)     │              │
        │                   └───────┬───────┘              │
        ▼                           │                      │
┌───────────────┐                   ▼                      │
│ Module 05     │           ┌───────────────┐              │
│ Privacy Agent │           │ Module 07     │              │
│ (2 hours)     │           │ Evaluation    │              │
└───────────────┘           │ (3 hours)     │              │
                            └───────┬───────┘              │
                                    │                      │
                                    ▼                      │
                            ┌───────────────┐              │
                            │ Module 08     │              │
                            │ Deployment    │              │
                            │ (4 hours)     │              │
                            └───────┬───────┘              │
                                    │                      │
                    ┌───────────────┴───────────────┐      │
                    │                               │      │
                    ▼                               ▼      │
            ┌───────────────┐               ┌───────────────┐
            │ Module 09     │               │ Module 10     │
            │ Observability │               │ ML Pipeline   │
            │ (3 hours)     │               │ Orchestrator  │
            └───────────────┘               │ (5 hours)     │
                                            └───────┬───────┘
                                                    │
                                    ┌───────────────┴───────────────┐
                                    │       ADVANCED TOPICS         │
                                    ▼                               │
                            ┌───────────────┐                       │
                            │ Modules 11-13 │                       │
                            │ (6 hours)     │                       │
                            └───────────────┘                       │
                                    │                               │
                                    ▼                               │
                            ┌───────────────┐                       │
                            │   COMPLETE!   │                       │
                            │ Professional  │                       │
                            │ n8n Developer │                       │
                            └───────────────┘                       │
```

---

## Prerequisites Checklist

Before starting, ensure you have:

### Environment

- [ ] n8n v1.120.0+ running on Ubuntu 1 (10.0.4.130:5678)
- [ ] PostgreSQL 16+ with `reachy_emotion` database
- [ ] Media Mover API running on port 8083
- [ ] FastAPI Gateway running on Ubuntu 2 (10.0.4.140:8000)
- [ ] SSH access to Ubuntu 1 and Jetson (when available)

### Credentials (in n8n)

- [ ] `PostgreSQL - reachy_local` — Database connection
- [ ] `Media Mover Auth` — HTTP Header Auth for Media Mover API
- [ ] `SSH Ubuntu1` — SSH access to training server
- [ ] `SSH Jetson` — SSH access to robot (can configure later)

### Environment Variables (in n8n)

- [ ] `MEDIA_MOVER_BASE_URL` = `http://10.0.4.130:8083`
- [ ] `GATEWAY_BASE_URL` = `http://10.0.4.140:8000`
- [ ] `INGEST_TOKEN` = Your secret token
- [ ] `MLFLOW_URL` = `http://10.0.4.130:5000`

### Reference Materials

- [ ] Screenshots in `n8n/workflows/screenshots/`
- [ ] Workflow specs in `n8n/workflows/ml-agentic-ai_v.2/detail_parameters_by_function/`
- [ ] JSON templates in `n8n/workflows/ml-agentic-ai_v.2/`
- [ ] [Node Reference -- All Agents](NODE_REFERENCE_ALL_AGENTS.md) — Complete node inventory for all workflows

---

## Node Type Mastery Tracker

Track your proficiency with each node type:

| Node Type | Module Introduced | Practiced In | Proficiency |
|-----------|-------------------|--------------|-------------|
| Webhook | 00, 01 | All | ⬜ ⬜ ⬜ |
| HTTP Request | 00, 01 | All | ⬜ ⬜ ⬜ |
| Code | 00, 01 | All | ⬜ ⬜ ⬜ |
| IF | 00, 01 | 01-03, 05-08 | ⬜ ⬜ ⬜ |
| Postgres | 01 | 01-06, 09-10 | ⬜ ⬜ ⬜ |
| Wait | 01 | 01, 06-08, 10 | ⬜ ⬜ ⬜ |
| Respond to Webhook | 01 | 01-03 | ⬜ ⬜ ⬜ |
| SSH | 06 | 04, 06-08 | ⬜ ⬜ ⬜ |
| Schedule Trigger | 04 | 04, 05, 09 | ⬜ ⬜ ⬜ |
| Switch | 02 | 02, 03 | ⬜ ⬜ ⬜ |
| Split In Batches | 04 | 04, 05 | ⬜ ⬜ ⬜ |
| Email Send | 04 | 04 | ⬜ ⬜ ⬜ |

**Legend**: ⬜ Not started | 🟡 Learning | 🟢 Proficient

---

## Quick Reference: Workflow → Module Mapping

| Workflow File | Module | Agent Name |
|---------------|--------|------------|
| `01_ingest_agent.json` | 01 | Ingest Agent |
| `02_labeling_agent.json` | 02 | Labeling Agent |
| `03_promotion_agent.json` | 03 | Promotion Agent |
| `04_reconciler_agent.json` | 04 | Reconciler Agent |
| `05_training_orchestrator_efficientnet.json` | 06 | Training Orchestrator |
| `06_evaluation_agent_efficientnet.json` | 07 | Evaluation Agent |
| `07_deployment_agent_efficientnet.json` | 08 | Deployment Agent |
| `08_privacy_agent.json` | 05 | Privacy Agent |
| `09_observability_agent.json` | 09 | Observability Agent |
| `10_ml_pipeline_orchestrator.json` | 10 | ML Pipeline Orchestrator |

---

## How to Use This Curriculum

### Recommended Approach

1. **Complete Module 00 first** — Even if you know n8n basics, this establishes common terminology
2. **Follow the learning path** — Modules build on each other
3. **Complete the pre-wiring checklist** — Never skip this; it prevents frustration
4. **Wire each workflow yourself** — Don't just import the JSON; build it node-by-node
5. **Test thoroughly** — Use the test procedures provided
6. **Keep notes** — Document any issues and solutions

### Time Management

- **Ideal pace**: 1-2 modules per week
- **Intensive pace**: 1 module per day
- **Total time**: 40-50 hours over 4-8 weeks

### Getting Help

If you get stuck:
1. Check the Troubleshooting section in each module
2. Review the n8n documentation: https://docs.n8n.io
3. Check workflow execution history for error details
4. Verify backend services are running

---

## Completion Checklist

Track your progress through the curriculum:

| Module | Started | Checklist Done | Wiring Done | Testing Done | Activated |
|--------|---------|----------------|-------------|--------------|-----------|
| 00 | ⬜ | N/A | ⬜ Lab | N/A | N/A |
| 01 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 02 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 03 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 04 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 05 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 06 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 07 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 08 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 09 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 10 | ⬜ | ⬜ | ⬜ | ⬜ | ⬜ |
| 11-13 | ⬜ | N/A | ⬜ | N/A | N/A |

---

*Curriculum Version 1.1 — Last Updated: 2026-03-08*
