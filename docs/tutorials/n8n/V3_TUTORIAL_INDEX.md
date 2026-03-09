# n8n Tutorials v3 (Reachy_Local_08.4.2)

Last updated: 2026-03-07

## Scope
This v3 tutorial set supersedes older n8n tutorial modules for Agent 1 through Agent 9 in:
- `n8n/workflows/ml-agentic-ai_v.2/*.json`
- `apps/api/app/*`
- `apps/api/routers/*`
- `apps/gateway/*`

## Why v3 exists
The legacy tutorial modules were written before major API and orchestration changes. The v3 docs are built from:
1. Actual n8n workflow JSON currently in repo.
2. Current gateway/media/training router implementations in code.
3. Official n8n docs and templates.

## Official n8n references used
- Advanced AI examples and concepts: https://docs.n8n.io/advanced-ai/examples/introduction/
- Workflow templates library: https://n8n.io/workflows/
- Webhook node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.webhook/
- Respond to Webhook node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.respondtowebhook/
- Code node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.code/
- HTTP Request node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.httprequest/
- If node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.if/
- Switch node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.switch/
- Wait node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.wait/
- Postgres node: https://docs.n8n.io/integrations/builtin/app-nodes/n8n-nodes-base.postgres/
- Schedule Trigger node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger/
- Split In Batches node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.splitinbatches/
- SSH node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.ssh/
- Set (Edit Fields) node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.set/
- Send Email node: https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.sendemail/

## Agent tutorial files (v3)
- [V3_AGENT_NODE_REFERENCE.md](./V3_AGENT_NODE_REFERENCE.md)
- [V3_ENDPOINT_ALIGNMENT.md](./V3_ENDPOINT_ALIGNMENT.md)

## Template-driven build guidance
Use templates as starting patterns, then adapt for Reachy contracts and idempotency requirements.

Recommended template categories to seed workflow redesigns:
- Approval and human-in-the-loop flows: https://n8n.io/workflows/?categories=IT+Ops
- Monitoring and scheduled telemetry: https://n8n.io/workflows/?categories=IT+Ops
- AI routing/fallback concepts: https://docs.n8n.io/advanced-ai/examples/introduction/

Example templates to study before editing Reachy workflows:
- Human-in-the-loop tool approval pattern: https://n8n.io/workflows/2819-build-an-mcp-server-with-human-in-the-loop-approval-for-executing-tools/
- AI + human approval security pattern: https://n8n.io/workflows/3365-streamline-tool-approval-with-ai-and-human-in-the-loop-for-secure-workflow-automation/
- AI routing/orchestration pattern: https://n8n.io/workflows/3049-use-ai-to-auto-tag-support-tickets-and-route-to-teams/

## Source-of-truth policy for this repo
When docs conflict:
1. `n8n/workflows/ml-agentic-ai_v.2/*.json` is the runtime truth for current node graph.
2. `apps/api/app/main.py`, `apps/api/app/routers/*`, `apps/api/routers/gateway.py`, and `apps/gateway/main.py` define actual endpoint behavior.
3. Legacy tutorial modules are historical context only unless explicitly updated.

## Important note about Agent count
This v3 pack documents the nine core n8n agents (Agents 1-9) exactly as requested. Agent 10 (ML pipeline orchestrator) is intentionally excluded from the node reference in this update.
