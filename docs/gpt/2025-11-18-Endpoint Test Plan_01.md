**2025-11-18-Endpoint Test Plan_01**

**Endpoint Test Plan_01**

\[MEMORY BANK: ACTIVE\]

I agree that starting at the highest-level gateway endpoints and
iteratively probing deeper services matches the documented hierarchy
\@docs/endpoints.md #9-120.

**1. Scope & Objectives**

• Confirm every published FastAPI/WS endpoint responds as expected while
services

(gateway on Ubuntu 2, Media Mover on Ubuntu 1, LM Studio, telemetry) are
all

running.

• Validate legacy paths are either disabled or return the documented
deprecation

envelope when enabled \@apps/api/app/main.py#63-77,

\@apps/api/app/routers/legacy.py#37-210.

**2. Assumptions & Test Harness**

• FastAPI gateway reachable at http://10.0.4.140:8000; (Ubuntu 2); Media
Mover at

http://10.0.4.130:8081 (Ubuntu 1) behind /api prefix \@docs/endpoints.md
#9-101.

• Postgres seeded; filesystem splits exist or respond gracefully when
empty

\@apps/api/app/routers/media_v1.py#70-118.

• Tools:

o curl/HTTPie for REST probes.

o wscat (or Python websocket client) for /ws/cues/{device_id}.

o Optional pytest -k v1 or httpx script for automation

(tests/test_v1_endpoints.py covers core flows).

• Shared headers: Accept: application/json, optional X-Correlation-ID
override. Auth

not yet enforced for read-only routes; bearer tokens required once
enabled (flag to

note).

**3. Test Phases & Cases**

**Phase A --- Gateway (Ubuntu 2)**

1\. **Liveness & Readiness**

a\. GET /health, GET /ready, expect 200, status ok/ready

\@docs/endpoints.md#15-22.

2\. **Metrics Export**

a\. GET /metrics, confirm Prometheus text payload.

3\. **WebSocket Availability**

a\. Connect ws://10.0.4.140:8000/ws/cues/test-device; verify handshake,
send

ping, expect server ack or close reason.

4\. **Event Intake**

a\. POST /api/events/emotion sample payload; assert 202/200 and
correlation

ID logged.

5\. **Proxy Mapping Sanity**

a\. GET /api/videos/list?split=temp should forward to Media Mover legacy
stub;

confirm deprecation headers (if legacy enabled) or 404 if disabled.

**Phase B --- Media Mover v1 (Ubuntu 1, /api/v1)**

1\. **Service Health**

a\. GET /api/v1/health, GET /api/v1/ready; expect status healthy with
directory

checks \@apps/api/app/routers/health.py#23-107.

2\. **Media Listing**

a\. GET /api/v1/media/list across temp, dataset_all, train, test; verify
pagination

envelope and empty split handling \@apps/api/app/routers/media_v1.py#32-

118\.

3\. **Metadata Lookup**

a\. GET /api/v1/media/{video_id} for known ID; expect metadata or
structured

404\.

4\. **Thumbnail Fetch**

a\. GET /api/v1/media/{video_id}/thumb; confirm URL referencing Nginx
proxy

\@apps/api/app/routers/media_v1.py#184-222.

5\. **Promotion Suite**

a\. POST /api/v1/promote/stage dry-run with sample UUIDs; expect 202 and

staged counts \@apps/api/app/routers/promote.py#41-87.

b\. POST /api/v1/promote/sample dry-run train/test redistribution,
handle

422/409 edge cases.

c\. POST /api/v1/promote/reset-manifest basic request; expect
confirmation

echo.

6\. **Metrics Endpoint**

a\. GET /api/v1/metrics (if exposed via router metrics) to confirm

instrumentation.

**Phase C --- Legacy Compatibility (if enabled)**

1\. GET /api/videos/list & /api/media/videos/list expect legacy JSON and
deprecation

headers \@apps/api/app/routers/legacy.py#37-116.

2\. POST /api/media/promote returns stub warning

\@apps/api/app/routers/legacy.py#119-154.

3\. GET /api/media and /media/health respond with deprecation banner

\@apps/api/app/routers/legacy.py#156-210.

**Phase D --- Supporting Services**

1\. **Training/Eval/Deployment Hooks**

a\. POST /api/train/start & GET /api/train/runs (may be stubbed; verify
schema).

b\. POST /api/eval/run, GET /api/eval/metrics/{run_id}.

c\. POST /api/deploy/promote, GET /api/deploy/status, POST

/api/deploy/rollback. Focus on reachable responses; flag if 501.

2\. **Privacy Agent**

a\. DELETE /api/privacy/purge/temp dry-run (ensure safe mode), GET

/api/privacy/logs.

3\. **Observability Agent**

a\. GET /api/obs/metrics, GET /api/obs/snapshot, POST /api/obs/alert
with test

payload.

4\. **Generation Sub-Agent**

a\. POST /api/gen/request with target mix; assert accepted.

b\. GET /api/gen/stats returns counters.

**Phase E --- External Integrations**

1\. **LM Studio Proxy**

a\. POST /api/llm/chat via gateway; expect downstream LM Studio response
or

error mapping \@docs/endpoints.md#24-28, 104-106.

2\. **Telemetry Consistency**

a\. Confirm /api/v1/metrics and gateway /metrics export align (labeling,

correlation IDs).

3\. **Database Side Effects**

a\. For non-dry-run promote/test cases, validate Postgres rows updated

(optional SQL spot-check).

**4. Validation Criteria**

• Every endpoint returns documented HTTP status, JSON schema, and
correlation

header when applicable \@apps/api/app/routers/promote.py#41-138.

• Error paths produce structured envelope (error, message,
correlation_id)

\@apps/api/app/routers/promote.py#37-145.

• Legacy endpoints emit X-API-Deprecated headers when enabled

\@apps/api/app/routers/legacy.py#30-116.

• No unhandled exceptions in logs; services stay healthy across tests.

**5. Reporting & Follow-up**

• Capture command transcripts per phase; highlight failures with
endpoint + payload.

• Escalate missing implementations (501) or mismatched schemas for
prioritization.

• Optionally automate Phases A--D via pytest/httpx suite for CI once
baseline passes.

Next natural steps: execute Phase A manually or script it, then proceed
down the stack while capturing results.
