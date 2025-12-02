# Module 0: n8n Fundamentals

**Course**: n8n Agentic AI Development for Reachy_Local_08.4.2  
**Instructor**: Cascade (AI)  
**Student**: Russ  
**Duration**: ~3 hours  
**Prerequisites**: Basic programming knowledge, familiarity with JSON and APIs

---

## Learning Objectives

By the end of this module, you will:
1. Understand n8n's architecture and execution model
2. Master data flow concepts: items, JSON, and expressions
3. Configure credentials and environment variables securely
4. Build and debug simple workflows
5. Be prepared to wire the 10 agentic workflows in Reachy_Local_08.4.2

---

## Lesson 0.1: n8n Architecture Overview

### What is n8n?

**n8n** (pronounced "n-eight-n") is an **extendable workflow automation tool** that connects apps and services to automate tasks. Unlike Zapier or Make, n8n is:

- **Self-hosted** — You control your data (critical for Reachy's privacy requirements)
- **Code-capable** — JavaScript/Python in Code nodes for custom logic
- **Open-source** — Community edition is free; Enterprise adds features

### Core Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        n8n Architecture                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐       │
│  │ Trigger │───▶│  Node 1 │───▶│  Node 2 │───▶│  Node 3 │       │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘       │
│       │              │              │              │             │
│       ▼              ▼              ▼              ▼             │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │              Data Items (JSON Array)                     │    │
│  │  [{"name": "video1"}, {"name": "video2"}, ...]          │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │ Credentials │  │ Env Vars    │  │ Expressions │              │
│  │ (Encrypted) │  │ ($env.*)    │  │ ={{ }}      │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

### Your n8n Environment (Reachy_Local_08.4.2)

| Component | Location | Purpose |
|-----------|----------|---------|
| n8n Instance | Ubuntu 1 (10.0.4.130:5678) | Workflow execution |
| PostgreSQL | Ubuntu 1 (10.0.4.130:5432) | Metadata storage |
| Media Mover API | Ubuntu 1 (10.0.4.130:8081) | File operations |
| FastAPI Gateway | Ubuntu 2 (10.0.4.140:8000) | Web app backend |

### Exercise 0.1.1: Access Your n8n Instance

1. Open your browser and navigate to: `http://10.0.4.130:5678`
2. Log in with your configured credentials
3. Observe the main canvas area — this is where you'll build workflows

**Screenshot Reference**: See `n8n/workflows/screenshots/Execution History View.png` for the UI layout.

---

## Lesson 0.2: Data Flow — Items, JSON, and $json

### The Fundamental Unit: Items

In n8n, **every piece of data is an "item"**. An item is a JSON object:

```json
{
  "json": {
    "video_id": "abc123",
    "label": "happy",
    "file_path": "temp/abc123.mp4"
  }
}
```

### How Data Flows Between Nodes

When a node executes, it receives items from the previous node and outputs items to the next node:

```
┌────────────────┐         ┌────────────────┐         ┌────────────────┐
│   Webhook      │  ───▶   │   Code Node    │  ───▶   │   HTTP Request │
│                │         │                │         │                │
│ Output:        │         │ Input:         │         │ Input:         │
│ [item1, item2] │         │ [item1, item2] │         │ [item3, item4] │
└────────────────┘         │ Output:        │         └────────────────┘
                           │ [item3, item4] │
                           └────────────────┘
```

### Accessing Data: The $json Object

Inside any node, you access the current item's data using `$json`:

| Expression | What it Returns |
|------------|-----------------|
| `$json` | The entire JSON object of the current item |
| `$json.video_id` | The value of `video_id` field |
| `$json.ffprobe.duration` | Nested property access |
| `$json.headers['x-ingest-key']` | Bracket notation for special characters |

### Example: Ingest Agent Data Flow

Let's trace data through the first 3 nodes of the Ingest Agent:

**Node 1: Webhook receives POST request**
```json
// Output item
{
  "headers": { "x-ingest-key": "secret123" },
  "body": { "source_url": "https://example.com/video.mp4", "label": "happy" }
}
```

**Node 2: Code node normalizes payload**
```javascript
// Access input data
const body = $json.body;
const sourceUrl = body.source_url;

// Return new item
return [{
  json: {
    source_url: sourceUrl,
    label: body.label,
    timestamp: new Date().toISOString()
  }
}];
```

**Node 3: HTTP Request uses the normalized data**
```
URL: ={{$env.MEDIA_MOVER_BASE_URL}}/api/media/pull
Body Parameter: source_url = ={{$json.source_url}}
```

### Exercise 0.2.1: Trace Data Flow

Open the Ingest Agent workflow (`01_ingest_agent.json`) in your n8n instance:
1. Click on the **Webhook: ingest.video** node
2. Examine the **Output** tab to see what data it produces
3. Click on **Code: normalize.payload** and trace how it transforms the data

---

## Lesson 0.3: Expressions — The ={{ }} Syntax

### What Are Expressions?

Expressions let you **dynamically insert values** into node parameters. They're enclosed in `={{ }}`:

```
Static value:  https://10.0.4.130/api/media/pull
Expression:    ={{$env.MEDIA_MOVER_BASE_URL}}/api/media/pull
```

### Expression Syntax Rules

1. **Must start with `={{`** — This tells n8n to evaluate the contents
2. **Must end with `}}`** — Closes the expression
3. **Uses JavaScript** — Any valid JS expression works
4. **Has special variables** — `$json`, `$env`, `$node`, etc.

### Common Expression Patterns

| Pattern | Example | Result |
|---------|---------|--------|
| Simple property | `={{$json.video_id}}` | `"abc123"` |
| Environment var | `={{$env.INGEST_TOKEN}}` | `"secret-token"` |
| Concatenation | `={{$json.path + "/" + $json.filename}}` | `"temp/video.mp4"` |
| Conditional | `={{$json.label ?? "unknown"}}` | Uses label or "unknown" |
| Template literal | `={{"Status: " + $json.status}}` | `"Status: done"` |
| Object literal | `={{ {"key": $json.value} }}` | `{"key": "..."}`  |

### The Expression Editor

When you click on an input field, you can:
1. Type directly for static values
2. Click the `=` icon to switch to expression mode
3. Use the expression editor for autocomplete

**Screenshot Reference**: See the `=` toggle in `n8n/workflows/screenshots/HTTP Request node_Parameters_part 1.png`

### Exercise 0.3.1: Write Expressions

Practice these expressions in a Code node (use the expression tester):

```javascript
// 1. Access a nested property
$json.ffprobe?.duration  // Safe navigation

// 2. Fallback value
$json.label ?? "unlabeled"

// 3. String template
`Video ${$json.video_id} is ${$json.status}`

// 4. Conditional expression
$json.status === "done" ? "Complete" : "In Progress"
```

---

## Lesson 0.4: Node Types Used in Reachy Workflows

### Overview of Key Nodes

The 10 agentic workflows use these primary node types:

| Node Type | Count | Purpose | Workflows |
|-----------|-------|---------|-----------|
| **Webhook** | 13 | Entry points for HTTP requests | All |
| **HTTP Request** | 25 | Call external APIs | All |
| **Code** | 15 | JavaScript transformation | All |
| **IF** | 13 | Conditional branching | All |
| **Postgres** | 14 | Database queries | 01-06, 10 |
| **SSH** | 10 | Remote command execution | 05, 07 |
| **Wait** | 5 | Delays and polling loops | 01, 05, 07, 10 |
| **Respond to Webhook** | 6 | Return HTTP responses | 01, 02, 03 |

### Node 1: Webhook (Trigger)

**Purpose**: Creates an HTTP endpoint that starts the workflow when called.

**Key Parameters** (from `Webhook node_Parameters.png`):
- **HTTP Method**: GET, POST, PUT, DELETE
- **Path**: URL path (e.g., `video_gen_hook` → `/webhook/video_gen_hook`)
- **Response Mode**: 
  - `onReceived` — Respond immediately, process async (return 202)
  - `lastNode` — Wait for workflow to complete before responding
- **Authentication**: None, Basic Auth, Header Auth, JWT

**Reachy Usage**: Every agent starts with a Webhook trigger for external systems to invoke it.

```json
// Example from Ingest Agent
{
  "httpMethod": "POST",
  "path": "video_gen_hook",
  "responseMode": "onReceived",
  "options": { "responseCode": 202 }
}
```

### Node 2: HTTP Request

**Purpose**: Makes HTTP calls to external APIs (Media Mover, Gateway, MLflow).

**Key Parameters** (from `HTTP Request node_Parameters_part 1.png`, `part 2.png`, `part 3.png`):
- **URL**: The endpoint to call (use expressions for dynamic URLs)
- **Method**: GET, POST, PUT, DELETE, PATCH
- **Authentication**: None, Predefined Credential Type, Generic Credential
- **Send Headers**: Add custom headers (Idempotency-Key, X-Correlation-ID)
- **Send Body**: Include request body (JSON, form data)
- **Options**: Timeout, follow redirects, ignore SSL errors

**Reachy Usage**: Calling Media Mover (`/api/media/pull`), Gateway (`/api/events/ingest`), etc.

```json
// Example: Call Media Mover
{
  "url": "={{$env.MEDIA_MOVER_BASE_URL}}/api/media/pull",
  "authentication": "genericCredentialType",
  "genericAuthType": "httpHeaderAuth",
  "sendBody": true,
  "bodyParameters": {
    "parameters": [
      { "name": "source_url", "value": "={{$json.source_url}}" }
    ]
  }
}
```

### Node 3: Code

**Purpose**: Execute JavaScript for complex transformations, validations, or logic.

**Key Parameters** (from `Code node_Parameters.png`):
- **Mode**: 
  - `runOnceForEachItem` — Execute code for each input item separately
  - `runOnceForAllItems` — Execute once with access to all items
- **JavaScript**: Your custom code

**Reachy Usage**: Payload normalization, metrics calculation, polling logic.

```javascript
// Example: Normalize payload (from Ingest Agent)
const body = $json.body ?? $json;
const sourceUrl = body.source_url ?? body.url ?? body.asset?.url;

if (!sourceUrl) {
  throw new Error('Missing source_url in request body');
}

return [{
  json: {
    source_url: sourceUrl,
    label: body.label ?? null,
    correlation_id: $json.headers?.['x-correlation-id'] ?? `ingest-${Date.now()}`
  }
}];
```

### Node 4: IF (Conditional)

**Purpose**: Branch workflow based on conditions.

**Key Parameters** (from `If node_Parameters.png`):
- **Conditions**: Define comparison rules
  - Value 1: Expression (e.g., `={{$json.status}}`)
  - Operation: equals, not equals, contains, greater than, etc.
  - Value 2: Comparison value (e.g., `done`)

**Outputs**:
- **True branch** (index 0): Condition matched
- **False branch** (index 1): Condition not matched

**Reachy Usage**: Authentication checks, status polling, gate validation.

```json
// Example: Check if processing is done
{
  "conditions": {
    "string": [{
      "value1": "={{$json.status}}",
      "operation": "equals",
      "value2": "done"
    }]
  }
}
```

### Node 5: Postgres

**Purpose**: Execute SQL queries against the PostgreSQL database.

**Key Parameters** (from `Postgres node_Parameters.png`):
- **Operation**: Execute Query, Insert, Update, Select
- **Query**: SQL statement (use `{{$json.field}}` for parameterization)

**Reachy Usage**: Insert video metadata, query label counts, update splits.

```sql
-- Example: Insert video metadata
INSERT INTO video (video_id, file_path, split, label, sha256, size_bytes)
VALUES (
  '{{$json.video_id}}',
  '{{$json.file_path}}',
  'temp',
  '{{$json.label}}',
  '{{$json.sha256}}',
  {{$json.size_bytes}}
)
ON CONFLICT (sha256, size_bytes) DO NOTHING
RETURNING video_id;
```

### Node 6: SSH

**Purpose**: Execute commands on remote servers via SSH.

**Key Parameters** (from `SSH node_Execute a command_Parameters.png`):
- **Operation**: Execute Command, Upload File, Download File
- **Command**: Shell command to run
- **Credential**: SSH key or password authentication

**Reachy Usage**: Launch training jobs, deploy models to Jetson, check system status.

```json
// Example: Run training script
{
  "operation": "executeCommand",
  "command": "cd /opt/reachy && ./train.sh --config emotion_2cls.yaml"
}
```

### Node 7: Wait

**Purpose**: Pause execution for a specified duration or until a condition.

**Key Parameters** (from `Wait node_Parameters.png`):
- **Resume**: After Time Interval, On Webhook Call, At Specified Time
- **Amount**: Duration value
- **Unit**: Seconds, Minutes, Hours

**Reachy Usage**: Polling loops (wait 3s, check status, repeat).

```json
// Example: Poll every 3 seconds
{
  "amount": 3,
  "unit": "seconds"
}
```

### Exercise 0.4.1: Identify Nodes in Ingest Agent

Open `01_ingest_agent.json` and identify:
1. How many Webhook nodes are there? (Answer: 1 — the trigger)
2. How many HTTP Request nodes? (Answer: 3 — pull, check status, emit event)
3. What does the IF node check? (Answer: `status === "done"`)

---

## Lesson 0.5: Credentials and Environment Variables

### Credentials: Secure Storage for Sensitive Data

Credentials store API keys, passwords, and tokens **encrypted** in the n8n database.

**Screenshot Reference**: `n8n/workflows/screenshots/Credentials Manager.png`

#### Creating Credentials

1. Go to **Settings → Credentials**
2. Click **Add Credential**
3. Select credential type (e.g., "HTTP Header Auth")
4. Fill in the values
5. Save with a descriptive name

#### Credentials in Reachy_Local_08.4.2

| Credential Name | Type | Used For |
|-----------------|------|----------|
| `Media Mover Auth` | HTTP Header Auth | Authenticating to Media Mover API |
| `PostgreSQL - reachy_local` | PostgreSQL | Database connection |
| `SSH Ubuntu1` | SSH Password/Key | Training server access |
| `SSH Jetson` | SSH Password/Key | Deployment server access |

#### Using Credentials in Nodes

When configuring an HTTP Request node:
1. Set **Authentication** to "Predefined Credential Type" or "Generic Credential Type"
2. Select the credential from the dropdown
3. n8n automatically includes the authentication headers

### Environment Variables: Configuration Without Hardcoding

Environment variables let you configure workflows without editing node parameters.

#### Setting Environment Variables

For Docker-based n8n (your setup), set env vars in `docker-compose.yml` or `.env`:

```yaml
# docker-compose.yml excerpt
services:
  n8n:
    environment:
      - MEDIA_MOVER_BASE_URL=http://10.0.4.130:8081
      - GATEWAY_BASE_URL=http://10.0.4.140:8000
      - INGEST_TOKEN=your-secret-token
```

#### Environment Variables in Reachy_Local_08.4.2

| Variable | Purpose | Example Value |
|----------|---------|---------------|
| `MEDIA_MOVER_BASE_URL` | Base URL for Media Mover API | `http://10.0.4.130:8081` |
| `GATEWAY_BASE_URL` | Base URL for FastAPI Gateway | `http://10.0.4.140:8000` |
| `INGEST_TOKEN` | Authentication token for webhooks | `secret-token-123` |
| `MLFLOW_URL` | MLflow tracking server | `http://10.0.4.130:5000` |

#### Accessing Environment Variables in Expressions

Use `$env.VARIABLE_NAME`:

```
URL: ={{$env.MEDIA_MOVER_BASE_URL}}/api/media/pull
```

### Exercise 0.5.1: Verify Credentials

1. Open n8n Settings → Credentials
2. Confirm these credentials exist:
   - [ ] PostgreSQL - reachy_local
   - [ ] Media Mover Auth
   - [ ] SSH Ubuntu1
   - [ ] SSH Jetson
3. Test the PostgreSQL credential:
   - Create a new workflow
   - Add a Postgres node
   - Select the credential
   - Run a simple query: `SELECT 1`

---

## Lesson 0.6: Error Handling and Execution Modes

### Execution Modes

n8n workflows can run in different modes:

| Mode | Description | Use Case |
|------|-------------|----------|
| **Manual** | Triggered by clicking "Execute Workflow" | Testing |
| **Active (Webhook)** | Triggered by HTTP requests | Production APIs |
| **Active (Schedule)** | Triggered by cron schedules | Nightly jobs |

### Error Handling Strategies

#### Strategy 1: Try-Catch in Code Nodes

```javascript
try {
  const result = JSON.parse($json.data);
  return [{ json: { parsed: result } }];
} catch (error) {
  return [{ json: { error: error.message, original: $json.data } }];
}
```

#### Strategy 2: Error Workflow

Configure a global error handler that runs when any workflow fails:

1. Create an "Error Handler" workflow
2. In workflow settings, set **Error Workflow** to point to it
3. The error workflow receives execution details

**Reachy Usage**: All agents set `"errorWorkflow": "error_handler"` in settings.

#### Strategy 3: Retry Logic

For transient failures (network timeouts), implement retry patterns:

```javascript
// Example: Polling with max attempts
const maxAttempts = 20;
const currentAttempt = $json.attempt ?? 1;

if (currentAttempt >= maxAttempts) {
  throw new Error('Max polling attempts reached');
}

return [{
  json: {
    ...items[0].json,
    attempt: currentAttempt + 1
  }
}];
```

### Viewing Execution History

**Screenshot Reference**: `n8n/workflows/screenshots/Execution History View.png`

The Execution History shows:
- **Status**: Success, Error, Running
- **Started At**: Timestamp
- **Execution Time**: Duration
- **Data**: Input/output for each node

### Exercise 0.6.1: Trigger an Error

1. Create a test workflow with a Code node
2. Add this code: `throw new Error("Test error");`
3. Execute the workflow
4. View the execution in History
5. Examine the error details

---

## Lesson 0.7: Lab — Build Your First Webhook Workflow

### Objective

Build a "Hello World" webhook workflow that:
1. Receives a POST request with a `name` parameter
2. Returns a greeting message

### Step-by-Step Instructions

#### Step 1: Create New Workflow

1. Click **+ New Workflow** in n8n
2. Name it "Hello World Test"

#### Step 2: Add Webhook Trigger

1. Click **+** to add a node
2. Search for "Webhook" and add it
3. Configure:
   - **HTTP Method**: POST
   - **Path**: `hello`
   - **Response Mode**: `lastNode`

#### Step 3: Add Code Node

1. Click **+** after the Webhook
2. Add a **Code** node
3. Configure:
   - **Mode**: `runOnceForAllItems`
   - **Code**:
```javascript
const name = $json.body?.name ?? "World";
const greeting = `Hello, ${name}! Welcome to n8n.`;

return [{
  json: {
    message: greeting,
    timestamp: new Date().toISOString()
  }
}];
```

#### Step 4: Add Respond to Webhook

1. Click **+** after the Code node
2. Add **Respond to Webhook** node
3. Configure:
   - **Respond With**: JSON
   - **Response Body**: `={{ $json }}`

#### Step 5: Connect and Test

1. Connect: Webhook → Code → Respond to Webhook
2. Click **Execute Workflow**
3. The Webhook shows a test URL (e.g., `http://localhost:5678/webhook-test/hello`)
4. In a terminal:
```bash
curl -X POST http://localhost:5678/webhook-test/hello \
  -H "Content-Type: application/json" \
  -d '{"name": "Russ"}'
```

Expected response:
```json
{
  "message": "Hello, Russ! Welcome to n8n.",
  "timestamp": "2025-12-02T06:00:00.000Z"
}
```

### Congratulations!

You've built your first n8n workflow. This pattern (Webhook → Process → Respond) is the foundation of all Reachy agents.

---

## Module 0 Summary

| Concept | Key Takeaway |
|---------|--------------|
| **Architecture** | n8n is self-hosted, node-based, with encrypted credentials |
| **Data Flow** | Items are JSON objects; use `$json` to access data |
| **Expressions** | `={{ }}` evaluates JavaScript; `$env.VAR` for environment variables |
| **Key Nodes** | Webhook, HTTP Request, Code, IF, Postgres, SSH, Wait |
| **Credentials** | Store secrets encrypted; reference by name in nodes |
| **Error Handling** | Use try-catch, error workflows, and retry patterns |

### Next Steps

You're now ready for **Module 1: Ingest Agent** where you'll wire the first real agentic workflow!

---

## Quick Reference Card

```
┌────────────────────────────────────────────────────────────────┐
│                   n8n QUICK REFERENCE                          │
├────────────────────────────────────────────────────────────────┤
│ Access current item:     $json                                 │
│ Access property:         $json.video_id                        │
│ Access nested:           $json.ffprobe.duration                │
│ Access header:           $json.headers['x-ingest-key']         │
│ Environment variable:    $env.MEDIA_MOVER_BASE_URL             │
│ Fallback/default:        $json.label ?? "unknown"              │
│ Conditional:             $json.status === "done" ? "Y" : "N"   │
│ Template string:         `Video ${$json.video_id} ready`       │
│ Return from Code node:   return [{ json: { ... } }]            │
└────────────────────────────────────────────────────────────────┘
```

---

*Module 0 Complete — Proceed to Module 1: Ingest Agent*
