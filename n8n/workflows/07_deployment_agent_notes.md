# Agent 7 — Deployment Agent (Workflow `07_deployment_agent.json`)

Rusty, this note maps the deployment workflow so you can mirror it in n8n. It starts with an alphabetical node inventory, then walks through each node's inputs, key parameters (with JSON you can paste), and how the shadow → canary → rollout control flow works, including the health gate before full rollout.

## Alphabetical inventory of nodes (workflow scope)
- HTTP: check.jetson_health
- Postgres: log.deployment
- Respond: success
- SSH: deploy.canary
- SSH: deploy.rollout
- SSH: deploy.shadow
- Switch: deployment.stage
- Wait: 30min canary
- Webhook: deployment.promote

---

## Node-by-node flow details
The workflow accepts a deployment request, routes by `target_stage`, performs the appropriate SSH copy/restart, optionally waits and health-checks during canary, logs the action in Postgres, and responds to the caller with the outcome.

### Webhook node
**Webhook: deployment.promote** — External POST hook (`/agent/deployment/promote`) that starts the promotion. It expects a JSON body with at least `engine_path` (source of the TensorRT engine) and `target_stage` (`shadow`, `canary`, or `rollout`). That payload is forwarded to downstream nodes so they can reference the stage and engine path.

Parameters:
```json
{
  "httpMethod": "POST",
  "path": "agent/deployment/promote",
  "responseMode": "responseNode"
}
```

### Switch node
**Switch: deployment.stage** — Routes to the correct branch based on `target_stage`. Each rule emits a uniquely named output (shadow/canary/rollout) to simplify wiring.

Dynamic parameters:
```json
{
  "rules": {
    "values": [
      {"conditions": {"string": [{"value1": "={{$json.target_stage}}", "value2": "shadow"}]}, "renameOutput": true, "outputKey": "shadow"},
      {"conditions": {"string": [{"value1": "={{$json.target_stage}}", "value2": "canary"}]}, "renameOutput": true, "outputKey": "canary"},
      {"conditions": {"string": [{"value1": "={{$json.target_stage}}", "value2": "rollout"}]}, "renameOutput": true, "outputKey": "rollout"}
    ]
  }
}
```

### SSH nodes
**SSH: deploy.shadow** — Copies the engine to the Jetson shadow slot. It uses the inbound `engine_path` and leaves services untouched (no restart), letting you validate the file before canary.

Parameters:
```json
{
  "command": "scp {{$json.engine_path}} jetson@10.0.4.150:/opt/reachy/models/emotion_shadow.engine",
  "authentication": "password"
}
```

**SSH: deploy.canary** — Copies the engine to the canary slot and restarts the canary systemd service so the new engine is live for the soak period. The webhook payload is passed through unchanged for downstream logging.

Parameters:
```json
{
  "command": "scp {{$json.engine_path}} jetson@10.0.4.150:/opt/reachy/models/emotion_canary.engine && ssh jetson@10.0.4.150 'sudo systemctl restart reachy-emotion-canary'",
  "authentication": "password"
}
```

**SSH: deploy.rollout** — Promotes the canary engine to production by copying it into place and restarting the main service. This runs either directly from the rollout branch or after the canary health gate passes.

Parameters:
```json
{
  "command": "cp /opt/reachy/models/emotion_canary.engine /opt/reachy/models/emotion.engine && sudo systemctl restart reachy-emotion",
  "authentication": "password"
}
```

### Wait node
**Wait: 30min canary** — Introduces a 30-minute soak after the canary deploy to allow monitoring before final rollout.

Parameters:
```json
{ "amount": 30, "unit": "minutes" }
```

### HTTP node
**HTTP: check.jetson_health** — Queries the Jetson health endpoint after the canary wait to ensure the pipeline is responsive (HTTP 200) before rollout.

Parameters:
```json
{ "url": "http://10.0.4.150/healthz" }
```

### Postgres node
**Postgres: log.deployment** — Records the deployment attempt in `deployment_log` with the engine path, requested stage, timestamp, and status. It receives context from any branch (shadow, canary after health, or direct rollout) and writes a row.

Parameters:
```json
{
  "operation": "insert",
  "table": "deployment_log",
  "columns": "engine_path, target_stage, deployed_at, status"
}
```

### Respond node
**Respond: success** — Final webhook response that echoes back the target stage and engine path so the caller can confirm what was deployed.

Parameters:
```json
{
  "respondWith": "json",
  "responseBody": "={{  {\"status\": \"success\", \"stage\": $json.target_stage, \"engine\": $json.engine_path} }}"
}
```

### Flow wiring (inputs between nodes)
- **Webhook deployment.promote** → Switch deployment.stage (branches to shadow/canary/rollout).
- **Shadow branch**: SSH deploy.shadow → Postgres log.deployment → Respond success.
- **Canary branch**: SSH deploy.canary → Wait 30min canary → HTTP check.jetson_health → Postgres log.deployment → Respond success.
- **Rollout branch**: SSH deploy.rollout → Postgres log.deployment → Respond success.

This branching ensures each promotion stage has an explicit path: shadow copies the engine for preflight inspection, canary performs a timed soak with a health gate before rollout, and rollout copies the validated engine into production, with all actions logged and surfaced to the requester.
