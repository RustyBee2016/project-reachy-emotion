# Memory Bank Index

**Last Updated**: 2025-11-14

This index provides curated entry points to project context, decisions, and references. Start here to discover what's known and where to find it.

---

## Core Specifications
- **[requirements.md](./requirements.md)** — Comprehensive project requirements (v0.08.3.2): architecture, data flow, API contracts, deployment gates, storage, observability, and acceptance criteria.
- **[AGENTS.md](../AGENTS.md)** — Agent roles, contracts, orchestration policy, approval rules, security guardrails, and observability SLOs.
- **[MODEL_SPEC.md](../MODEL_SPEC.md)** *(if exists)* — Model architecture, training config, hyperparameters, and deployment gates.

---

## Key Design Decisions
- **[Decision: Endpoint System v1 Rewrite](./decisions/005-endpoint-system-v1.md)** — Centralized config, versioned API, standardized responses, retry logic (2025-11-14).
- **[Decision: EmotionNet TAO Toolchain](./decisions/004-emotionnet-tao-toolchain.md)** — Train with TAO 4.x; export with TAO 5.3.
- **[Decision: Hybrid Storage Architecture](./decisions/001-hybrid-storage-architecture.md)** — Local filesystem + PostgreSQL metadata over object storage.
- **[Decision: DeepStream-Only Runtime](./decisions/002-deepstream-only-runtime.md)** — Rationale for skipping Triton on Jetson in v0.8.3.
- **[Decision: Privacy-First Architecture](./decisions/003-privacy-first-architecture.md)** — Local-only video processing, no raw video egress by default.

---

## Runbooks & Operations
*(Add links to operational playbooks as they are created)*

- **[Runbook: Promote Video Flow](./runbooks/)** *(pending)* — Step-by-step guide for promoting videos from `temp/` to `train/test/`.
- **[Runbook: Rollback Procedure](./runbooks/)** *(pending)* — ZFS snapshot rollback and manifest rebuild.
- **[Runbook: NAS Backup & Restore](./runbooks/)** *(pending)* — Nightly rsync, quarterly restore test, hash verification.
- **[Runbook: Model Deployment](./runbooks/)** *(pending)* — Gate A/B/C validation, engine export, DeepStream config update.

---

## API & Integration References
- **[endpoints.md](../docs/endpoints.md)** — FastAPI gateway endpoints, schemas, and examples.
- **[API Contract: Media Mover](./requirements.md#16-api-contract-minifastapi)** — Mini-FastAPI endpoints for media listing, promotion, thumbnails, and manifest rebuild.
- **[Event Schemas](./requirements.md#13-apis--event-schemas)** — Jetson → Ubuntu 2 emotion events, LLM chat, WebSocket cues, error model.

---

## System Architecture
- **[Architecture Overview](./requirements.md#11-system-architecture-overview)** — Ubuntu 1 (model host), Ubuntu 2 (app gateway), Jetson (edge inference).
- **[Data Flow](./requirements.md#12-end-to-end-data-flow)** — End-to-end flow from Jetson detection → LLM inference → curation → training → deployment.
- **[Networking & Security](./requirements.md#17-networking-ports-and-security)** — Ports, mTLS/JWT, reverse proxy hardening, firewall rules.

### Repo Layout (08.3)
- API service under `apps/api/` with routers `gateway.py` and `media.py`.
- Web UI under `apps/web/`.
- Shared contracts placeholder under `shared/contracts/`.
- Legacy modules retained temporarily under `src/` pending full migration.

---

## Quality Gates & Metrics
- **[Deployment Gates](./requirements.md#7-model-deployment--quality-gates)** — Gate A (offline validation), Gate B (shadow mode), Gate C (limited rollout).
- **[Performance Targets](./requirements.md#63-performance-targets)** — Nginx latency, manifest rebuild time, training I/O throughput.
- **[Observability SLOs](./requirements.md#18-observability--operations)** — Latency histograms, F1 metrics, drift monitoring, alerts.

---

## Compliance & Privacy
- **[Ethical Guidelines](./requirements.md#81-ethical-guidelines)** — No demographic bias, clear capability statements, user consent.
- **[Data Governance](./requirements.md#83-data-governance)** — Retention policies, right to be forgotten, DSAR process.
- **[Privacy Guardrails](../AGENTS.md#security--privacy-guardrails)** — LLM agents must not access raw video; mTLS/JWT; secrets from vault only.

---

## Testing & CI
- **[Testing Strategy](./requirements.md#testing--ci-expectations)** — ruff, pyright, pytest, spec parser, benchmark recording.
- **[Acceptance Criteria](./requirements.md#24-acceptance-criteria)** — Media-mover endpoints, MLflow lineage, NAS sync, performance targets.

---

## Templates & Helpers
- **[Memory Template](./templates/memory_template.md)** — Template for creating new memory notes (decisions, runbooks, references).

---

## How to Contribute
1. **Add a new memory**: Copy `templates/memory_template.md`, fill it out, save under an appropriate subdirectory (e.g., `decisions/`, `runbooks/`), and link it here.
2. **Update existing memory**: Edit in place and bump the `updated` date in the frontmatter.
3. **Prune stale links**: Review this index quarterly and archive obsolete memories to `archive/`.

---

**Maintained by**: Russell Bray (rustybee255@gmail.com)  
**Next Review**: 2026-01-04
