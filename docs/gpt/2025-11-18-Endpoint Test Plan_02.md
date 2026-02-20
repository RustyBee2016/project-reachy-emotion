**2025-11-18-Endpoint Test Plan_02**

**Endpoint Test Plan_02**

PROMPT:

Let\'s go through each of the next actions in order.

Restore Media Mover

Check service status on Ubuntu 1 (systemd unit, container, or uvicorn
process). Once live, rerun Phase B tests plus gateway proxy checks.

Clarify WebSocket authentication

Identify expected header/token (consult deployment config or
maintainer). Retest handshake, ping/pong, ack, and cue push after
enabling credentials.

Verify LM Studio

Confirm http://10.0.4.130:1234/v1/chat/completions responds. Then
execute full Phase C dialogue scenarios (sad/happy/low-confidence/etc.).

Re-run metrics check

After upstream services come online, confirm Prometheus exports include
real counters/histograms per plan.

\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Provide commands to accomplish each task.

======================================== =

RESPONSE

\[MEMORY BANK: ACTIVE\] Here are shell commands to address each action
in sequence. Run them from a shell on Ubuntu 1 unless noted otherwise.
Replace placeholder values (e.g., UUIDs, tokens) with real data as
needed.

**1. Restore Media Mover (fastapi-media.service)**

Service definition: fastapi-media.service launches Uvicorn on port 8083
and performs a post-start health probe, so systemd is the control point
\@systemd/fastapimedia.service#1-48.

1\. Check current status & last failures:

sudo systemctl status fastapi-media.service

2\. Attempt restart and watch logs:

sudo systemctl restart fastapi-media.service sudo journalctl -u
fastapi-media.service -n 50 \--no-pager

3\. Confirm it is listening:

ss -tnlp \| grep 8083

4\. Local health/readiness checks (direct to service on Ubuntu 1):

curl -i http://localhost:8083/api/v1/health curl -i
http://localhost:8083/api/v1/ready

(Both endpoints come from the v1 health router
\@apps/api/app/routers/health.py#13- 108.)

5\. Once healthy, rerun Phase B tests from any host on the LAN:

curl -i http://10.0.4.130:8081/api/v1/health curl -i
http://10.0.4.130:8081/api/v1/ready curl -i
\"http://10.0.4.130:8081/api/v1/media/list?split=temp&limit=20&offset=0\"
curl -i
\"http://10.0.4.130:8081/api/v1/media/list?split=train&limit=20&offset=0\"
curl -i http://10.0.4.130:8081/api/v1/media/YOUR_VIDEO_UUID curl -i
\"http://10.0.4.130:8081/api/v1/media/YOUR_VIDEO_UUID/thumb\"

curl -i -X POST http://10.0.4.130:8081/api/v1/promote/stage \\ -H
\'Content-Type: application/json\' \\ -d
\'{\"video_ids\":\[\"uuid-1\",\"uuid-2\"\],\"label\":\"happy\",\"dry_run\":true}\'
curl -i -X POST http://10.0.4.130:8081/api/v1/promote/sample \\ -H
\'Content-Type: application/json\' \\ -d
\'{\"run_id\":\"run-uuid\",\"dest_split\":\"train\",\"sample_fraction\":0.5,\"dry_run\":true}\'
curl -i -X POST http://10.0.4.130:8081/api/v1/promote/reset-manifest \\
-H \'Content-Type: application/json\' \\ -d
\'{\"run_id\":\"run-uuid\"}\'

6\. Verify gateway proxies now succeed:

curl -i
\"http://10.0.4.140:8000/api/v1/media/list?split=temp&limit=20&offset=0\"
curl -i \"http://10.0.4.140:8000/api/v1/promote/stage\" \\ -H
\'Content-Type: application/json\' \\ -H \'Idempotency-Key:
test-key-001\' \\ -d
\'{\"video_ids\":\[\"uuid-1\"\],\"label\":\"happy\",\"dry_run\":true}\'

**2. Clarify WebSocket authentication**

The WebSocket endpoint enforces device validation and expects a proper
handshake via /ws/cues/{device_id}
\@apps/api/app/routers/websocket_cues.py#163-256. Use these commands to
locate any required headers/tokens:

1\. Inspect gateway .env for auth-related variables: grep -nE
\'WS\|WEBSOCKET\|TOKEN\' apps/api/.env 2. Search codebase for custom
headers: rg \"extra_headers\" -n apps/api rg \"X-Device\" -n apps/api rg
\"WebSocket\" -n apps/api 3. If credentials are stored elsewhere (e.g.,
/etc/default/fastapi-media), check: sudo grep -nE
\'WS\|WEBSOCKET\|TOKEN\' /etc/systemd/system/fastapi-media.service.d/\*
2\>/dev/null

sudo grep -nE \'WS\|WEBSOCKET\|TOKEN\' \~/.config/reachy/\*.env
2\>/dev/null

4\. After determining the required header, test the connection
(substitute actual

header name/value):

python3 - \<\<\'PY\' import asyncio, json, os import websockets headers
= { \"X-Device-Token\": os.environ\[\"REACHY_WS_TOKEN\"\] \# replace
with discovered name/value } async def main(): uri =
\"ws://10.0.4.140:8000/ws/cues/reachy-mini-01\" async with
websockets.connect(uri, extra_headers=headers) as ws:
print(\"WELCOME:\", await ws.recv()) await ws.send(json.dumps({\"type\":
\"ping\"})) print(\"PONG:\", await ws.recv()) asyncio.run(main()) PY

5\. To confirm cue delivery end-to-end, trigger a sample combined cue
once device is

connected:

python3 - \<\<\'PY\' import asyncio from
apps.api.app.routers.websocket_cues import create_cue_message from
apps.api.app.routers.websocket_cues import manager async def
send_test(): cue = create_cue_message( cue_type=\"combined\",
text=\"Diagnostic cue\", gesture_id=\"wave_enthusiastic\",
tone=\"warm_upbeat\", )

await manager.send_cue(\"reachy-mini-01\", cue) asyncio.run(send_test())
PY

(Run inside the API environment after authenticating to ensure the
manager sees the connection.)

**3. Verify LM Studio and execute dialogue scenarios**

Dialogue generation uses
http://{config.gateway_host}:1234/v1/chat/completions
\@apps/api/app/routers/dialogue.py#149-233.

1\. Liveness check against LM Studio (Ubuntu 1):

curl -i http://10.0.4.130:1234/v1/models

2\. Basic completion smoke test:

curl -i -X POST http://10.0.4.130:1234/v1/chat/completions \\ -H
\'Content-Type: application/json\' \\ -d
\'{\"model\":\"localmodel\",\"messages\":\[{\"role\":\"user\",\"content\":\"ping\"}\],\"max_tokens\":10}\'

3\. Gateway dialogue endpoint -- sad emotion:

curl -i -X POST http://10.0.4.140:8000/api/v1/dialogue/generate \\ -H
\'Content-Type: application/json\' \\ -d \'{ \"emotion\": \"sad\",
\"confidence\": 0.87, \"user_message\": \"I had a tough day.\",
\"device_id\": \"reachy-mini-01\" }\'

4\. Happy emotion scenario:

curl -i -X POST http://10.0.4.140:8000/api/v1/dialogue/generate \\ -H
\'Content-Type: application/json\' \\ -d \'{ \"emotion\": \"happy\",
\"confidence\": 0.92, \"user_message\": \"I just got great news!\",
\"device_id\": \"reachy-mini-01\" }\'

5\. Low-confidence fallback:

curl -i -X POST http://10.0.4.140:8000/api/v1/dialogue/generate \\ -H
\'Content-Type: application/json\' \\ -d \'{ \"emotion\": \"angry\",
\"confidence\": 0.42, \"user_message\": \"Not sure how I feel.\",
\"device_id\": \"reachy-mini-01\" }\'

6\. Conversation history case:

curl -i -X POST http://10.0.4.140:8000/api/v1/dialogue/generate \\ -H
\'Content-Type: application/json\' \\ -d \'{ \"emotion\": \"neutral\",
\"confidence\": 0.75, \"device_id\": \"reachy-mini-01\",
\"conversation_history\": \[ {\"role\": \"user\", \"content\": \"Hi
Reachy.\"}, {\"role\": \"assistant\", \"content\": \"Hello! How can I
help today?\"} \], \"user_message\": \"Can you give me a quick
summary?\" }\'

7\. Error-path validation (invalid emotion):

curl -i -X POST http://10.0.4.140:8000/api/v1/dialogue/generate \\ -H
\'Content-Type: application/json\' \\ -d \'{ \"emotion\": \"confused\",
\"confidence\": 0.7, \"user_message\": \"??\", \"device_id\":
\"reachy-mini-01\" }\'

**4. Re-run metrics checks**

Once all upstream services are running, confirm Prometheus exports show
detailed metrics rather than placeholders:

1\. Gateway metrics:

curl -s http://10.0.4.140:8000/metrics \| head -n 40

2\. Media Mover metrics (if router exposes them):

curl -s http://10.0.4.130:8081/api/v1/metrics \| head -n 40

3\. Optional: filter for emotion events or latency histogram:

curl -s http://10.0.4.140:8000/metrics \| rg \'emotion_event\' curl -s
http://10.0.4.130:8081/api/v1/metrics \| rg \'http_request_duration\'

Let me know when you've run these or if any commands need adjustment.
