# MODULE 00 -- n8n Fundamentals

**Duration:** ~3 hours
**Prerequisite:** n8n running on Ubuntu 1 (http://10.0.4.130:5678)
**Outcome:** Understand n8n's architecture, data model, and core node types before wiring any agents

---

## 0.1 What Is n8n?

n8n is an open-source workflow automation platform. Think of it as a visual programming environment where you connect **nodes** (boxes) with **connections** (wires) to build automated pipelines.

In the Reachy system, n8n serves as the **orchestration layer** -- it coordinates nine specialized agents that handle everything from video ingestion to model deployment.

### Key Concepts

| Concept | Definition |
|---------|------------|
| **Workflow** | A complete automation consisting of connected nodes. Each agent is one workflow. |
| **Node** | A single operation (e.g., make an HTTP request, query a database, run JavaScript code). |
| **Connection** | A wire between two nodes that passes data from one to the next. |
| **Execution** | A single run of a workflow from trigger to completion. |
| **Item** | A unit of data flowing through the workflow. Each node receives items and outputs items. |
| **Expression** | A dynamic value reference using `{{ }}` syntax, e.g., `{{ $json.video_id }}`. |

---

## 0.2 The n8n UI

When you open n8n at `http://10.0.4.130:5678`, you'll see:

```
┌──────────────────────────────────────────────────────────────┐
│  n8n                                                [≡ Menu] │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐     ┌──────────────┐     ┌──────────────┐  │
│  │  Trigger     │────►│  Process      │────►│  Output      │  │
│  │  Node        │     │  Node         │     │  Node        │  │
│  └─────────────┘     └──────────────┘     └──────────────┘  │
│                                                              │
│                         CANVAS                               │
│                                                              │
├──────────────────────────────────────────────────────────────┤
│  [Execute Workflow]  [Save]  [Active: OFF]                   │
└──────────────────────────────────────────────────────────────┘
```

### Navigation

1. **Canvas** -- The main area where you drag and connect nodes
2. **Node Panel** -- Click the `+` button on the canvas to open the node selector
3. **Execution History** -- Click the clock icon to view past runs
4. **Settings** -- Access workflow settings via the `⚙` gear icon

---

## 0.3 Data Model -- Items and JSON

Every piece of data in n8n is a **JSON item**. When a node runs, it receives an array of items and outputs an array of items.

### Example: A Webhook receives a POST request

**Input to the Webhook node:**
```json
[
  {
    "json": {
      "source_url": "https://example.com/video.mp4",
      "label": "happy",
      "meta": { "camera": "front" }
    },
    "headers": {
      "x-ingest-key": "tkn3848",
      "content-type": "application/json"
    }
  }
]
```

**Key points:**
- `$json` references the current item's JSON data
- `$json.source_url` → `"https://example.com/video.mp4"`
- `$input.item.json.label` → `"happy"`
- Headers are available via `$json.headers` in the Webhook node

### Referencing Data Between Nodes

| Expression | Meaning |
|-----------|---------|
| `{{ $json.video_id }}` | Current item's `video_id` field |
| `{{ $('node_name').item.json.field }}` | A specific field from a named node's output |
| `{{ $env.VARIABLE_NAME }}` | An environment variable |
| `{{ $now.toISO() }}` | Current timestamp in ISO format |
| `{{ $runIndex }}` | Current execution index (useful in loops) |

### Lab Exercise 0.3a: Explore Data Flow

1. Create a new workflow named "Lab: Data Flow"
2. Add a **Manual Trigger** node (search for "Manual" in the node panel)
3. Add a **Set** node after it:
   - Click "Add Value" → String
   - Name: `greeting`
   - Value: `Hello from n8n`
4. Add a **Code** node after the Set node:
   ```javascript
   const input = $input.all();
   return input.map(item => ({
     json: {
       original_greeting: item.json.greeting,
       uppercase: item.json.greeting.toUpperCase(),
       timestamp: new Date().toISOString()
     }
   }));
   ```
5. Click **Execute Workflow**
6. Click each node to inspect the output data

---

## 0.4 Node Types Used in Reachy

The Reachy system uses 13 different node types. Here's what each one does:

### Trigger Nodes (Start a workflow)

| Node | Icon | Purpose | Used In |
|------|------|---------|---------|
| **Webhook** | 🔗 | Receives HTTP requests (POST/GET) | All agents |
| **Schedule Trigger** | ⏰ | Fires on a cron schedule | Agents 4, 8 |
| **Cron** | ⏱ | Fires at intervals (e.g., every 30s) | Agent 9 |

### Logic Nodes (Make decisions)

| Node | Purpose | Used In |
|------|---------|---------|
| **IF** | Binary true/false branching | Agents 1, 3-7, 10 |
| **Switch** | Multi-way branching (like a switch statement) | Agent 2 |

### Action Nodes (Do things)

| Node | Purpose | Used In |
|------|---------|---------|
| **HTTP Request** | Call external APIs | All agents |
| **Postgres** | Query/insert/update PostgreSQL | Agents 1, 2, 4-6, 8-10 |
| **SSH** | Run commands on remote servers | Agents 4-8 |
| **Code** | Run custom JavaScript | All agents |
| **Send Email** | Send email notifications | Agent 4 |

### Flow Control Nodes

| Node | Purpose | Used In |
|------|---------|---------|
| **Wait** | Pause execution for a duration | Agents 1, 5, 7, 10 |
| **Split In Batches** | Process items in groups | Agent 8 |
| **Respond to Webhook** | Send HTTP response back to caller | Agents 1-3, 6-7 |
| **Set** | Set/modify data fields | Agent 4 |

---

## 0.5 Credentials

Credentials store sensitive connection details (passwords, tokens, API keys) separately from workflows.

### Setting Up Credentials for Reachy

You need 4 credentials. Set them up before wiring any agents:

#### Credential 1: PostgreSQL -- reachy_local

1. Go to **Settings** → **Credentials** → **Add Credential**
2. Search for **Postgres**
3. Configure:
   - **Name:** `PostgreSQL - reachy_local`
   - **Host:** `localhost`
   - **Port:** `5432`
   - **Database:** `reachy_emotion`
   - **User:** `reachy_dev`
   - **Password:** *(your password)*
4. Click **Test Connection** to verify
5. Click **Save**

#### Credential 2: Media Mover Auth (HTTP Header)

1. Go to **Settings** → **Credentials** → **Add Credential**
2. Search for **Header Auth**
3. Configure:
   - **Name:** `Media Mover Auth`
   - **Header Name:** `Authorization`
   - **Header Value:** `Bearer <your-media-mover-token>`
4. Click **Save**

#### Credential 3: SSH Ubuntu1

1. Go to **Settings** → **Credentials** → **Add Credential**
2. Search for **SSH**
3. Configure:
   - **Name:** `SSH Ubuntu1`
   - **Host:** `10.0.4.130`
   - **Port:** `22`
   - **Username:** `rusty_admin`
   - **Authentication:** Password
   - **Password:** *(your password)*
4. Click **Save**

#### Credential 4: SSH Jetson

1. Go to **Settings** → **Credentials** → **Add Credential**
2. Search for **SSH**
3. Configure:
   - **Name:** `SSH Jetson`
   - **Host:** `10.0.4.150`
   - **Port:** `22`
   - **Username:** `jetson`
   - **Authentication:** Password
   - **Password:** *(your password)*
4. Click **Save**

---

## 0.6 Environment Variables

Environment variables let you store configuration values that all workflows share.

### Setting Up Environment Variables

1. Go to **Settings** → **Variables** (or set them in n8n's `.env` file)
2. Add the following:

| Variable | Value | Purpose |
|----------|-------|---------|
| `INGEST_TOKEN` | `tkn3848` | Auth token for ingest webhook |
| `MEDIA_MOVER_BASE_URL` | `http://10.0.4.130:8083` | Media Mover API base URL |
| `GATEWAY_BASE_URL` | `http://10.0.4.140:8000` | FastAPI Gateway base URL |
| `MLFLOW_URL` | `http://10.0.4.130:5000` | MLflow tracking server |

### Using Environment Variables in Nodes

Reference them with `{{ $env.VARIABLE_NAME }}`:

```
URL: {{ $env.MEDIA_MOVER_BASE_URL }}/api/media/pull
```

---

## 0.7 Workflow Settings

Each Reachy workflow uses these settings:

1. Open a workflow → click the `⚙` gear icon
2. Configure:
   - **Execution Order:** `v1` (nodes run in order they were connected)
   - **Save Manual Executions:** `Yes` (keeps test run data)
   - **Error Workflow:** Set to your error handler workflow (optional)
   - **Timeout:** Set a reasonable timeout per workflow

---

## 0.8 Common Patterns You'll See

### Pattern: Webhook → Auth → Process → Respond

Most Reachy agents follow this pattern:

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐
│ Webhook  │───►│ IF: Auth │───►│ Process  │───►│ Respond  │
│ (trigger)│    │ Check    │    │ (work)   │    │ (result) │
└──────────┘    └────┬─────┘    └──────────┘    └──────────┘
                     │
                     │ [fail]
                     ▼
                ┌──────────┐
                │ Respond  │
                │ 401      │
                └──────────┘
```

### Pattern: Poll Until Done

Used when waiting for a long-running operation:

```
┌───────┐    ┌───────┐    ┌──────────┐    ┌──────────┐
│ Start │───►│ Wait  │───►│ Check    │───►│ IF: Done?│
│ Job   │    │ 3-5s  │    │ Status   │    │          │
└───────┘    └───────┘    └──────────┘    └────┬─────┘
                  ▲                            │
                  │         [not done]         │
                  └────────────────────────────┘
                                  [done]       │
                                               ▼
                                          Continue...
```

### Lab Exercise 0.8a: Build a Polling Loop

1. Create a new workflow named "Lab: Polling"
2. Add a **Manual Trigger**
3. Add a **Set** node → add field `attempt` = `0`
4. Add a **Wait** node → set to 2 seconds
5. Add a **Code** node:
   ```javascript
   const attempt = $json.attempt + 1;
   return [{ json: { attempt, done: attempt >= 3 } }];
   ```
6. Add an **IF** node → condition: `{{ $json.done }}` equals `true`
7. Connect **IF** false output back to the **Wait** node (creating a loop)
8. Add a **Set** node on the IF true output → add field `result` = `Polling complete!`
9. Execute and watch the loop run 3 times

---

## 0.9 Error Handling

n8n provides several error handling mechanisms:

### Node-Level Error Handling

1. Click any node → **Settings** tab
2. **Continue On Fail:** When enabled, the workflow continues even if this node fails
3. **Retry On Fail:** Automatically retries the node (set count and wait time)

### Workflow-Level Error Handling

1. Create a dedicated error handler workflow
2. Set it as the **Error Workflow** in workflow settings
3. The error workflow receives details about what failed

### Try/Catch in Code Nodes

```javascript
try {
  const response = JSON.parse($json.body);
  return [{ json: { status: 'ok', data: response } }];
} catch (error) {
  return [{ json: { status: 'error', message: error.message } }];
}
```

---

## 0.10 Checklist: Ready for Module 01

Before proceeding to Module 01 (Ingest Agent), verify:

- [ ] n8n is accessible at `http://10.0.4.130:5678`
- [ ] PostgreSQL credential `reachy_local` is configured and tested
- [ ] Media Mover Auth credential is configured
- [ ] SSH Ubuntu1 credential is configured
- [ ] SSH Jetson credential is configured (can be done later for Module 08)
- [ ] Environment variables are set (INGEST_TOKEN, MEDIA_MOVER_BASE_URL, GATEWAY_BASE_URL, MLFLOW_URL)
- [ ] You completed Lab Exercise 0.3a (Data Flow)
- [ ] You completed Lab Exercise 0.8a (Polling Loop)
- [ ] You understand the difference between `$json`, `$('node_name')`, and `$env`

---

## Quick Reference Card

```
EXPRESSIONS
  {{ $json.field }}              Current item's field
  {{ $('NodeName').item.json }}  Another node's output
  {{ $env.VAR }}                 Environment variable
  {{ $now.toISO() }}             Current timestamp
  {{ $input.all() }}             All input items (Code node)

NODE TYPES
  Webhook         = HTTP endpoint (trigger)
  HTTP Request    = Call an API
  Postgres        = Database query
  Code            = Custom JavaScript
  IF              = True/false branch
  Switch          = Multi-branch
  Wait            = Pause execution
  SSH             = Remote command
  Set             = Set fields
  Respond         = Send HTTP response

KEYBOARD SHORTCUTS
  Ctrl+S          = Save workflow
  Ctrl+Enter      = Execute workflow
  Tab             = Open node panel
  Ctrl+Z          = Undo
  Space+Drag      = Pan canvas
  Scroll          = Zoom in/out
```

---

*Next: [MODULE 01 -- Ingest Agent](MODULE_01_INGEST_AGENT.md)*
