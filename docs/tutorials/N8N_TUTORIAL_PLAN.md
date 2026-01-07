# n8n Tutorial Plan for Reachy_Local_08.4.2

## Overview

This document outlines a comprehensive tutorial series to teach Russ how to develop n8n workflows while implementing the agentic AI system for Project Reachy_Local_08.4.2.

**Target Outcome:** Professional-level n8n development skills with hands-on experience building production-grade agentic workflows.

---

## Part 1: Screenshot Requirements for Tutorial Development

Before developing the tutorials, I need screenshots of the following n8n UI elements from your self-hosted instance. These will help me understand your specific n8n version and create accurate tutorials.

### 1.1 Core Node Configuration Panels

Please provide screenshots of the **full parameter panel** for each of these nodes:

| Node Type | Screenshot Needed | Purpose |
|-----------|-------------------|---------|
| **Webhook** | Full settings panel with all options expanded | Understand trigger configuration options |
| **HTTP Request** | All tabs (Parameters, Headers, Body, Options) | Critical for API integration |
| **Code** | Editor view + settings | JavaScript execution environment |
| **IF** | Condition builder interface | Branching logic |
| **Postgres** | Connection + Query panels | Database integration |
| **SSH** | All authentication options | Remote command execution |
| **Wait** | All timing options | Polling patterns |
| **Respond to Webhook** | Response configuration | Webhook response handling |

### 1.2 Workflow-Level Settings

| Setting Area | Screenshot Needed |
|--------------|-------------------|
| **Workflow Settings** | The gear icon menu showing execution order, error handling |
| **Credentials Manager** | List view + credential creation form |
| **Environment Variables** | Where/how to set `$env` variables |
| **Tags** | Tag management interface |
| **Execution History** | Execution list + detail view |

### 1.3 Canvas & Editor Features

| Feature | Screenshot Needed |
|---------|-------------------|
| **Node Palette** | Full list of available nodes |
| **Connection Drawing** | How to connect nodes (drag interface) |
| **Expression Editor** | The `={{ }}` expression builder |
| **Test Execution** | Manual execution controls |
| **Pinned Data** | How to pin test data |

---

## Part 2: Prerequisites & Functionality Testing

Before building tutorials, we must verify that all backend services the workflows depend on are operational.

### 2.1 Required API Endpoints

The n8n workflows call these endpoints. Each must be tested:

| Endpoint | Method | Used By | Status |
|----------|--------|---------|--------|
| `/api/media/pull` | POST | Ingest Agent | ⚠️ STUB |
| `/api/media/promote` | POST | Promotion Agent | ✅ Implemented |
| `/api/videos/list` | GET | Multiple agents | ✅ Implemented |
| `/api/events/ingest` | POST | Ingest Agent | ❓ Needs verification |
| `/api/events/training` | POST | Training Agent | ❓ Needs verification |
| `/api/events/deployment` | POST | Deployment Agent | ❓ Needs verification |
| `/api/events/pipeline` | POST | Pipeline Orchestrator | ❓ Needs verification |
| `/api/training/status/{id}` | GET | Pipeline Orchestrator | ❓ Needs verification |

### 2.2 Required Credentials

The workflows require these credentials configured in n8n:

| Credential Name | Type | Used For |
|-----------------|------|----------|
| `Media Mover Auth` | HTTP Header Auth | API authentication |
| `PostgreSQL - reachy_local` | PostgreSQL | Database queries |
| `SSH Ubuntu1` | SSH Password | Training server commands |
| `SSH Jetson` | SSH Password | Deployment commands |

### 2.3 Required Environment Variables

| Variable | Example Value | Used By |
|----------|---------------|---------|
| `MEDIA_MOVER_BASE_URL` | `https://10.0.4.130` | Ingest, Promotion |
| `GATEWAY_BASE_URL` | `https://10.0.4.130` | Event emission |
| `MLFLOW_URL` | `http://10.0.4.130:5000` | Training tracking |
| `MLFLOW_EXPERIMENT_ID` | `1` | MLflow runs |
| `N8N_HOST` | `http://localhost:5678` | Workflow triggers |
| `INGEST_TOKEN` | `<secret>` | Webhook auth |

---

## Part 3: Tutorial Curriculum

### Module 0: n8n Fundamentals (Foundation)

**Objective:** Build foundational understanding before tackling agentic workflows.

| Lesson | Topic | Duration |
|--------|-------|----------|
| 0.1 | n8n Architecture: Nodes, Connections, Executions | 30 min |
| 0.2 | Data Flow: Items, JSON, and the `$json` object | 45 min |
| 0.3 | Expressions: `={{ }}` syntax and JavaScript | 45 min |
| 0.4 | Credentials & Environment Variables | 30 min |
| 0.5 | Error Handling & Execution Modes | 30 min |
| 0.6 | **Lab:** Build a "Hello World" webhook workflow | 30 min |

### Module 1: Ingest Agent (Workflow 01)

**Objective:** Learn webhook triggers, HTTP requests, polling patterns, and database integration.

| Lesson | Topic | Key Concepts |
|--------|-------|--------------|
| 1.1 | Webhook Triggers | POST endpoints, response modes, authentication |
| 1.2 | IF Node Branching | Condition types, true/false paths |
| 1.3 | Code Node Basics | JavaScript execution, item manipulation |
| 1.4 | HTTP Request Node | Methods, headers, body, authentication |
| 1.5 | Polling Pattern | Wait + HTTP + IF loop |
| 1.6 | PostgreSQL Node | Query execution, parameterization |
| 1.7 | Event Emission | Emitting completion events |
| 1.8 | **Lab:** Wire the complete Ingest Agent |

### Module 2: Labeling & Promotion Agents (Workflows 02-03)

**Objective:** Learn database-driven workflows and state management.

| Lesson | Topic | Key Concepts |
|--------|-------|--------------|
| 2.1 | Database Queries | SELECT, UPDATE, transactions |
| 2.2 | Idempotency | Idempotency-Key headers, conflict handling |
| 2.3 | Multi-path Workflows | Complex branching logic |
| 2.4 | **Lab:** Wire Labeling + Promotion Agents |

### Module 3: Reconciler & Privacy Agents (Workflows 04, 08)

**Objective:** Learn scheduled triggers and batch processing.

| Lesson | Topic | Key Concepts |
|--------|-------|--------------|
| 3.1 | Cron Triggers | Scheduled execution |
| 3.2 | Batch Processing | Loop over items |
| 3.3 | File System Operations | SSH commands for file ops |
| 3.4 | **Lab:** Wire Reconciler + Privacy Agents |

### Module 4: Training Orchestrator (Workflow 05)

**Objective:** Learn long-running process orchestration.

| Lesson | Topic | Key Concepts |
|--------|-------|--------------|
| 4.1 | SSH Node | Remote command execution |
| 4.2 | Long Polling | Extended wait patterns |
| 4.3 | Result Parsing | JSON parsing in Code node |
| 4.4 | Quality Gates | Conditional logic for gates |
| 4.5 | MLflow Integration | API calls for experiment tracking |
| 4.6 | **Lab:** Wire Training Orchestrator |

### Module 5: Evaluation & Deployment Agents (Workflows 06-07)

**Objective:** Learn multi-system orchestration and rollback patterns.

| Lesson | Topic | Key Concepts |
|--------|-------|--------------|
| 5.1 | Cross-System Coordination | Ubuntu1 → Jetson |
| 5.2 | SCP File Transfer | SSH-based file copy |
| 5.3 | Service Management | systemctl via SSH |
| 5.4 | Rollback Patterns | Backup and restore |
| 5.5 | **Lab:** Wire Evaluation + Deployment Agents |

### Module 6: Pipeline Orchestrator (Workflow 10)

**Objective:** Learn workflow-to-workflow orchestration.

| Lesson | Topic | Key Concepts |
|--------|-------|--------------|
| 6.1 | Workflow Triggers | Calling webhooks from workflows |
| 6.2 | Pipeline State | Tracking multi-stage progress |
| 6.3 | Conditional Deployment | Auto-deploy logic |
| 6.4 | **Lab:** Wire ML Pipeline Orchestrator |

### Module 7: Observability Agent (Workflow 09)

**Objective:** Learn metrics collection and alerting.

| Lesson | Topic | Key Concepts |
|--------|-------|--------------|
| 7.1 | Metrics Collection | Aggregating from multiple sources |
| 7.2 | Prometheus Integration | Pushing metrics |
| 7.3 | Alert Conditions | Threshold-based alerts |
| 7.4 | **Lab:** Wire Observability Agent |

### Module 8: Advanced Topics

| Lesson | Topic |
|--------|-------|
| 8.1 | Error Workflows | Global error handling |
| 8.2 | Sub-workflows | Reusable workflow components |
| 8.3 | Versioning | Workflow version control |
| 8.4 | Testing Strategies | Manual testing, pinned data |
| 8.5 | Production Deployment | Backup, restore, monitoring |

---

## Part 4: Node Types Used Across All Workflows

| Node Type | Count | Workflows Using |
|-----------|-------|-----------------|
| `n8n-nodes-base.webhook` | 10 | All |
| `n8n-nodes-base.httpRequest` | 25+ | All |
| `n8n-nodes-base.code` | 15+ | All |
| `n8n-nodes-base.if` | 12+ | All |
| `n8n-nodes-base.postgres` | 8 | 01-06, 10 |
| `n8n-nodes-base.ssh` | 8 | 05, 07 |
| `n8n-nodes-base.wait` | 6 | 01, 05, 07, 10 |
| `n8n-nodes-base.respondToWebhook` | 4 | 01, 02, 03 |

---

## Part 5: Immediate Action Items

### For Russ:

1. **Provide Screenshots** (Section 1)
   - Capture the UI elements listed above from your self-hosted n8n
   - Save to `n8n/workflows/screenshots/` directory

2. **Verify n8n Version**
   - Check Settings → About → Version number
   - Different versions have different node options

3. **Test Credentials**
   - Verify PostgreSQL connection works
   - Verify SSH connections to Ubuntu1 and Jetson

### For Me (Cascade):

1. **Implement Missing Endpoints**
   - `/api/media/pull` - Currently a stub
   - `/api/events/*` - Need to verify/implement

2. **Create Test Fixtures**
   - Sample webhook payloads for each agent
   - Expected responses for validation

3. **Develop Tutorial Content**
   - Start with Module 0 (Fundamentals)
   - Progress through modules sequentially

---

## Part 6: Testing Checklist

Before each tutorial module, we must verify:

| Test | Command/Method | Expected Result |
|------|----------------|-----------------|
| PostgreSQL connectivity | Test query in n8n | Returns rows |
| Media API health | `curl https://10.0.4.130/media/health` | `ok` |
| SSH to Ubuntu1 | Test SSH node | Command output |
| SSH to Jetson | Test SSH node | Command output |
| Webhook reception | POST to webhook URL | 202 response |

---

## Next Steps

1. **Please provide the screenshots** listed in Part 1
2. **Confirm your n8n version** (e.g., 1.x.x)
3. **Let me know which module** you'd like to start with

Once I have the screenshots, I'll begin developing detailed, step-by-step tutorials with:
- Annotated screenshots
- Copy-paste code snippets
- Troubleshooting guides
- Practice exercises

---

*Document created: 2025-11-30*
*Project: Reachy_Local_08.4.2*
*Author: Cascade (AI Instructor)*
