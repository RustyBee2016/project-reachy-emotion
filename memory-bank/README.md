# Memory Bank

## Purpose
The Memory Bank is a lightweight, repo-native knowledge base that preserves critical project context across chat sessions, team handoffs, and long-horizon development cycles. It serves as the **canonical source of truth** for decisions, runbooks, references, and design rationale.

## Scope
- **In Scope**: Design decisions, architecture rationale, runbooks, policy references, links to specs (`requirements.md`, `AGENTS.md`, `MODEL_SPEC.md`), acceptance criteria, and cross-cutting concerns.
- **Out of Scope**: Raw video files, secrets, PII, temporary notes, or chat transcripts. Use relative references and hashes only.

## Structure
```
memory-bank/
├── README.md              ← You are here
├── index.md               ← Curated entry points to all memories
├── requirements.md        ← Comprehensive project requirements (v0.08.3.2)
├── templates/
│   └── memory_template.md ← Template for new memory notes
└── decisions/             ← (future) Decision records
```

## How to Use
1. **Discover context**: Start with `index.md` for curated links to key docs and decisions.
2. **Add new memory**: Copy `templates/memory_template.md`, fill it out, save under an appropriate subdirectory (e.g., `decisions/`, `runbooks/`), and link it from `index.md`.
3. **Update existing memory**: Edit in place and bump the `updated` date in the frontmatter.
4. **Cross-reference**: Link to `AGENTS.md`, `MODEL_SPEC.md`, or other repo files to maintain a single source of truth.

## Governance
- **Format**: Markdown with minimal YAML frontmatter (see template).
- **Ownership**: Each memory must list `owners` (GitHub handles or team names).
- **Update Rule**: Non-trivial changes (architecture, policy, deployment gates) should create or update a memory and link it from `index.md`.
- **Privacy**: No secrets, raw media, or PII. Use references (e.g., `video_id`, `sha256`, file paths) only.
- **Alignment**: Keep `memory-bank/requirements.md`, `AGENTS.md`, and `MODEL_SPEC.md` consistent. If conflicts arise, escalate to project owner (Russ).

## Maintenance
- Review `index.md` quarterly to prune stale links and consolidate redundant memories.
- Archive obsolete memories to `archive/` with a note in the frontmatter.
- CI (optional future): Lint frontmatter schema and check for broken internal links.

## Related Files
- **`requirements.md`**: Comprehensive project requirements (v0.08.3.2).
- **`AGENTS.md`**: Agent roles, contracts, orchestration policy, approval rules.
- **`MODEL_SPEC.md`**: Model architecture, training config, deployment gates (if exists).
- **`.windsurfrules`**: Cascade AI agent instructions and memory integration rules.

---

**Last Updated**: 2025-10-04  
**Owner**: Russell Bray (rustybee255@gmail.com)
