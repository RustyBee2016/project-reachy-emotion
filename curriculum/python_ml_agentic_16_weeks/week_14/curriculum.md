# Week 14 — Security, Privacy, and Compliance-by-Design

## Weekly Objective
Implement secure coding practices for local-first ML platforms.

## Core Python Topics
- Authn/authz patterns in services
- Secrets/config hardening
- Privacy-first logging strategies

## Codebase Review Targets
- Review auth/config boundaries in `apps/api/app/auth.py` and `apps/api/app/vault_config.py`.
- Trace privacy expectations from AGENTS policy into code touchpoints.
- Inspect metadata handling and logging paths for minimization opportunities.

## Hands-On Build Tasks
1. **Read & Explain:** Produce a detailed logic + control-flow walkthrough for one selected module.
2. **Modify:** Implement one scoped code improvement aligned to this week’s objective.
3. **Validate:** Add or update tests proving correctness.
4. **Reflect:** Write a short engineering note on tradeoffs and architecture impact.

## Checkpoints (end of week)
- Can Rusty explain each important function in plain English and pseudocode?
- Can Rusty justify chosen control flow and data structures?
- Can Rusty map syntax-level details to system-level behavior?
- Are tests and documentation updated with the change?

## Deliverable
- Produce a threat model and remediation plan for one subsystem.

## Stretch Goal (optional)
- Pair this week’s work with a small observability improvement (metric, log, or trace annotation).
