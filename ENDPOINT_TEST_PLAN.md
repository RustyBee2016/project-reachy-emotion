# Comprehensive Endpoint Test Plan — Reachy_Local_08.4.2

**Version**: 1.1.0  
**Last Updated**: 2025-11-17  
**Status**: Ready for Execution

---

## 1. Scope & Objectives

### Primary Goals
- Verify all FastAPI/WebSocket endpoints respond correctly with services running
- Validate emotion-conditioned dialogue generation via LM Studio integration
- Confirm legacy endpoint deprecation behavior
- Test WebSocket cue streaming for robot behavioral control
- Ensure proper error handling, correlation IDs, and response envelopes

### Services Required
- **Ubuntu 2 Gateway**: `http://10.0.4.140:8000` (FastAPI + Uvicorn)
- **Ubuntu 1 Media Mover**: `http://10.0.4.130:8081` (FastAPI behind Nginx `/api`)
- **Ubuntu 1 LM Studio**: `http://10.0.4.130:1234` (OpenAI-compatible API)
- **PostgreSQL**: `localhost:5432` (metadata storage)
- **Filesystem**: `/media/.../videos/{temp,dataset_all,train,test,thumbs,manifests}`

---

## 2. Test Phases & Hierarchy

### Phase A — Gateway (Ubuntu 2) Core Services
Test the highest-level entry points on the gateway service.

### Phase B — Media Mover v1 (Ubuntu 1) 
Test media management, promotion, and metadata endpoints.

### Phase C — LM Studio Dialogue Integration (NEW)
Test emotion-conditioned dialogue generation and WebSocket cue delivery.

### Phase D — Legacy Compatibility
Test deprecated endpoints and migration warnings.

### Phase E — Supporting Services
Test training, evaluation, deployment, privacy, and observability hooks.

### Phase F — Integration & End-to-End
Test complete workflows spanning multiple services.

---

## 3. Detailed Test Cases

### Phase A — Gateway (Ubuntu 2)

#### A.1 Liveness & Readiness
**Endpoints**: `GET /health`, `GET /ready`

| Test Case | Method | Endpoint | Expected Status | Expected Response | Notes |
|-----------|--------|----------|----------------|-------------------|-------|
| A.1.1 | GET | `/health` | 200 | `"ok"` (plain text) | Basic liveness probe |
| A.1.2 | GET | `/ready` | 200 | `"ready"` (plain text) | Readiness for traffic |

**Validation**:
- Response time < 50ms
- No dependencies checked (fast response)

#### A.2 Metrics Export
**Endpoint**: `GET /metrics`

| Test Case | Method | Endpoint | Expected Status | Expected Response | Notes |
|-----------|--------|----------|----------------|-------------------|-------|
| A.2.1 | GET | `/metrics` | 200 | Prometheus text format | Contains `# HELP` and `# TYPE` |

**Validation**:
- Content-Type: `text/plain; version=0.0.4`
- Contains emotion_event counters
- Contains http_request_duration histograms

#### A.3 Emotion Event Intake
**Endpoint**: `POST /api/events/emotion`

| Test Case | Method | Endpoint | Payload | Expected Status | Notes |
|-----------|--------|----------|---------|----------------|-------|
| A.3.1 | POST | `/api/events/emotion` | Valid emotion event | 202 | Accepted for processing |
| A.3.2 | POST | `/api/events/emotion` | Missing `emotion` field | 400 | Validation error |
| A.3.3 | POST | `/api/events/emotion` | Invalid emotion value | 400 | Must be in enum |
| A.3.4 | POST | `/api/events/emotion` | Confidence out of range | 400 | Must be 0.0-1.0 |
| A.3.5 | POST | `/api/events/emotion` | Missing `X-API-Version` | 400 | Header required |

**Sample Payload** (A.3.1):
```json
{
  "schema_version": "v1",
  "device_id": "reachy-mini-01",
  "ts": "2025-11-17T20:11:33Z",
  "emotion": "happy",
  "confidence": 0.87,
  "inference_ms": 92,
  "window": {"fps": 30, "size_s": 1.2, "hop_s": 0.5},
  "meta": {"model_version": "emotionnet-0.8.4-trt"},
  "correlation_id": "test-uuid-123"
}
```

**Headers**: `X-API-Version: v1`

**Validation**:
- Returns 202 immediately
- Correlation ID logged
- Event appears in metrics

#### A.4 Proxy Endpoints
**Endpoints**: `/api/videos/*`, `/api/promote`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| A.4.1 | GET | `/api/videos/list?split=temp` | 200 or 404 | Proxies to Media Mover |
| A.4.2 | POST | `/api/promote` | 200 or 400 | Requires `Idempotency-Key` |

**Validation**:
- Requests forwarded to `http://10.0.4.130:8081`
- Response matches upstream format
- Deprecation headers present if legacy enabled

---

### Phase B — Media Mover v1 (Ubuntu 1)

#### B.1 Service Health
**Endpoints**: `GET /api/v1/health`, `GET /api/v1/ready`

| Test Case | Method | Endpoint | Expected Status | Expected Response | Notes |
|-----------|--------|----------|----------------|-------------------|-------|
| B.1.1 | GET | `/api/v1/health` | 200 | JSON with `status: "healthy"` | Includes directory checks |
| B.1.2 | GET | `/api/v1/ready` | 200 | JSON with `status: "healthy"` | Same as health for now |

**Validation**:
- `checks.videos_root.status` = "ok"
- `checks.directories.accessible` = 6 (temp, dataset_all, train, test, thumbs, manifests)

#### B.2 Media Listing
**Endpoint**: `GET /api/v1/media/list`

| Test Case | Method | Endpoint | Query Params | Expected Status | Notes |
|-----------|--------|----------|--------------|----------------|-------|
| B.2.1 | GET | `/api/v1/media/list` | `split=temp&limit=50&offset=0` | 200 | Returns paginated list |
| B.2.2 | GET | `/api/v1/media/list` | `split=dataset_all` | 200 | Empty if no files |
| B.2.3 | GET | `/api/v1/media/list` | `split=invalid` | 400 | Validation error |
| B.2.4 | GET | `/api/v1/media/list` | `split=train&limit=1000` | 200 | Max limit enforced |

**Validation**:
- Response envelope: `{status, data: {items[], pagination: {total, limit, offset}}}`
- Each item has: `video_id`, `file_path`, `size_bytes`, `mtime`, `split`
- Correlation ID in response

#### B.3 Video Metadata
**Endpoint**: `GET /api/v1/media/{video_id}`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| B.3.1 | GET | `/api/v1/media/test-video-123` | 200 or 404 | Returns metadata if found |
| B.3.2 | GET | `/api/v1/media/nonexistent` | 404 | Structured error response |

**Validation**:
- 200: Returns `VideoMetadata` with all fields
- 404: Returns `{error, message, correlation_id}`

#### B.4 Thumbnail Fetch
**Endpoint**: `GET /api/v1/media/{video_id}/thumb`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| B.4.1 | GET | `/api/v1/media/test-video-123/thumb` | 200 or 404 | Returns thumbnail URL |
| B.4.2 | GET | `/api/v1/media/nonexistent/thumb` | 404 | Thumbnail not found |

**Validation**:
- Returns `{thumbnail_url}` pointing to Nginx
- URL format: `http://10.0.4.130:8082/thumbs/{video_id}.jpg`

#### B.5 Promotion Suite
**Endpoints**: `/api/v1/promote/stage`, `/api/v1/promote/sample`, `/api/v1/promote/reset-manifest`

| Test Case | Method | Endpoint | Payload | Expected Status | Notes |
|-----------|--------|----------|---------|----------------|-------|
| B.5.1 | POST | `/api/v1/promote/stage` | Dry-run stage request | 202 | Preview counts |
| B.5.2 | POST | `/api/v1/promote/stage` | Actual stage (dry_run=false) | 202 | Moves files |
| B.5.3 | POST | `/api/v1/promote/stage` | Duplicate video_id | 409 | Conflict error |
| B.5.4 | POST | `/api/v1/promote/sample` | Dry-run sample request | 202 | Preview selection |
| B.5.5 | POST | `/api/v1/promote/sample` | Actual sample | 202 | Copies to train/test |
| B.5.6 | POST | `/api/v1/promote/reset-manifest` | Reset request | 202 | Clears manifest state |

**Sample Payload** (B.5.1):
```json
{
  "video_ids": ["uuid-1", "uuid-2"],
  "label": "happy",
  "dry_run": true
}
```

**Validation**:
- Returns `{status, staged_count, skipped_count, errors[]}`
- Correlation ID in response header
- 422 for validation errors
- 409 for conflicts

---

### Phase C — LM Studio Dialogue Integration (NEW)

#### C.1 Dialogue Generation
**Endpoint**: `POST /api/v1/dialogue/generate`

| Test Case | Method | Endpoint | Payload | Expected Status | Notes |
|-----------|--------|----------|---------|----------------|-------|
| C.1.1 | POST | `/api/v1/dialogue/generate` | Sad emotion request | 200 | Returns empathetic response |
| C.1.2 | POST | `/api/v1/dialogue/generate` | Happy emotion request | 200 | Returns enthusiastic response |
| C.1.3 | POST | `/api/v1/dialogue/generate` | Low confidence emotion | 200 | Returns neutral fallback |
| C.1.4 | POST | `/api/v1/dialogue/generate` | With conversation history | 200 | Includes context |
| C.1.5 | POST | `/api/v1/dialogue/generate` | Invalid emotion | 422 | Validation error |
| C.1.6 | POST | `/api/v1/dialogue/generate` | Confidence out of range | 422 | Must be 0.0-1.0 |
| C.1.7 | POST | `/api/v1/dialogue/generate` | LM Studio timeout | 504 | Gateway timeout |
| C.1.8 | POST | `/api/v1/dialogue/generate` | LM Studio error | 502 | Bad gateway |

**Sample Payload** (C.1.1):
```json
{
  "emotion": "sad",
  "confidence": 0.87,
  "user_message": "I'm having a rough day.",
  "device_id": "reachy-mini-01"
}
```

**Expected Response** (C.1.1):
```json
{
  "status": "success",
  "data": {
    "text": "I'm here with you. How's your day going? I noticed you might be feeling a little down. Want to talk about it?",
    "gesture": "head_tilt_sympathetic",
    "tone": "gentle_supportive",
    "emotion": "sad",
    "confidence": 0.87
  },
  "meta": {
    "correlation_id": "uuid-here",
    "timestamp": "2025-11-17T20:15:00Z"
  }
}
```

**Validation**:
- Response includes `text`, `gesture`, `tone`, `emotion`, `confidence`
- Gesture matches emotion (sad → head_tilt_sympathetic, happy → wave_enthusiastic)
- Tone matches emotion (sad → gentle_supportive, happy → warm_upbeat)
- Low confidence (<0.6) → neutral gesture/tone
- Correlation ID in response header
- LM Studio called with emotion-conditioned prompt

**Emotion-Gesture-Tone Mapping**:
| Emotion | Gesture | Tone |
|---------|---------|------|
| happy | wave_enthusiastic | warm_upbeat |
| sad | head_tilt_sympathetic | gentle_supportive |
| angry | calm_hands | calm_understanding |
| neutral | neutral_stance | neutral |
| surprise | head_tilt_curious | curious_engaged |
| fearful | open_hands_reassuring | reassuring_calm |

#### C.2 Dialogue Health Check
**Endpoint**: `GET /api/v1/dialogue/health`

| Test Case | Method | Endpoint | Expected Status | Expected Response | Notes |
|-----------|--------|----------|----------------|-------------------|-------|
| C.2.1 | GET | `/api/v1/dialogue/health` | 200 | `{status: "ok", service: "dialogue"}` | Service health |

#### C.3 WebSocket Cue Streaming
**Endpoint**: `WS /ws/cues/{device_id}`

| Test Case | Protocol | Endpoint | Action | Expected Behavior | Notes |
|-----------|----------|----------|--------|-------------------|-------|
| C.3.1 | WS | `/ws/cues/reachy-mini-01` | Connect | Receives welcome message | Connection established |
| C.3.2 | WS | `/ws/cues/reachy-mini-01` | Send ping | Receives pong | Heartbeat mechanism |
| C.3.3 | WS | `/ws/cues/reachy-mini-01` | Receive cue | Server pushes dialogue cue | Combined text+gesture+tone |
| C.3.4 | WS | `/ws/cues/reachy-mini-01` | Send ack | Server logs acknowledgment | Cue confirmation |
| C.3.5 | WS | `/ws/cues/reachy-mini-01` | Send error | Server logs client error | Error reporting |
| C.3.6 | WS | `/ws/cues/` | Connect (empty ID) | Rejects connection | Invalid device_id |
| C.3.7 | WS | `/ws/cues/x{200}` | Connect (long ID) | Rejects connection | Device ID too long |

**Welcome Message** (C.3.1):
```json
{
  "type": "connection_established",
  "device_id": "reachy-mini-01",
  "timestamp": "2025-11-17T20:20:00Z",
  "server_version": "0.08.4.3"
}
```

**Cue Message Format** (C.3.3):
```json
{
  "type": "combined",
  "text": "I'm here to help!",
  "gesture_id": "open_hands_reassuring",
  "tone": "reassuring_calm",
  "correlation_id": "dialogue-uuid-123",
  "expires_at": "2025-11-17T20:20:30Z",
  "timestamp": "2025-11-17T20:20:00Z"
}
```

**Client Acknowledgment** (C.3.4):
```json
{
  "type": "ack",
  "correlation_id": "dialogue-uuid-123"
}
```

**Validation**:
- WebSocket handshake succeeds
- Welcome message received immediately
- Ping/pong works (heartbeat every 30s)
- Server can push cues to specific device
- Client acks are logged
- Connection survives idle periods
- Disconnection handled gracefully

---

### Phase D — Legacy Compatibility

#### D.1 Legacy Endpoints (if enabled)
**Endpoints**: `/api/videos/list`, `/api/media/videos/list`, `/api/media/promote`, `/api/media`, `/media/health`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| D.1.1 | GET | `/api/videos/list?split=temp` | 200 | Returns legacy format |
| D.1.2 | GET | `/api/media/videos/list?split=temp` | 200 | Alternate legacy path |
| D.1.3 | POST | `/api/media/promote` | 200 | Stub response |
| D.1.4 | GET | `/api/media` | 200 | Service info |
| D.1.5 | GET | `/media/health` | 200 | Health stub |

**Validation**:
- All responses include deprecation headers:
  - `X-API-Deprecated: true`
  - `X-API-Deprecation-Message: <warning>`
  - `X-API-Sunset: 2026-01-01`
- Legacy format unwraps envelope (no `status`/`data` wrapper)
- Promote endpoint returns stub warning

#### D.2 Legacy Disabled
**Config**: `REACHY_ENABLE_LEGACY_ENDPOINTS=false`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| D.2.1 | GET | `/api/videos/list` | 404 | Not found |
| D.2.2 | POST | `/api/media/promote` | 404 | Not found |

---

### Phase E — Supporting Services

#### E.1 Training Orchestrator
**Endpoints**: `POST /api/train/start`, `GET /api/train/status/{run_id}`, `GET /api/train/runs`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| E.1.1 | POST | `/api/train/start` | 202 or 501 | Accepted or not implemented |
| E.1.2 | GET | `/api/train/status/run-123` | 200 or 404 | Returns run state |
| E.1.3 | GET | `/api/train/runs` | 200 | Lists recent runs |

**Validation**:
- If implemented: returns MLflow run ID and status
- If stub: returns 501 with clear message

#### E.2 Evaluation Agent
**Endpoints**: `POST /api/eval/run`, `GET /api/eval/metrics/{run_id}`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| E.2.1 | POST | `/api/eval/run` | 202 or 501 | Triggers validation |
| E.2.2 | GET | `/api/eval/metrics/run-123` | 200 or 404 | Returns confusion matrix |

#### E.3 Deployment Agent
**Endpoints**: `POST /api/deploy/promote`, `GET /api/deploy/status`, `POST /api/deploy/rollback`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| E.3.1 | POST | `/api/deploy/promote` | 202 or 501 | Deploys engine |
| E.3.2 | GET | `/api/deploy/status` | 200 | Active engine version |
| E.3.3 | POST | `/api/deploy/rollback` | 202 or 501 | Reverts to previous |

#### E.4 Privacy Agent
**Endpoints**: `DELETE /api/privacy/purge/temp`, `POST /api/privacy/redact/{video_id}`, `GET /api/privacy/logs`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| E.4.1 | DELETE | `/api/privacy/purge/temp` | 202 | Removes expired temp videos |
| E.4.2 | POST | `/api/privacy/redact/video-123` | 202 | Manual purge |
| E.4.3 | GET | `/api/privacy/logs` | 200 | Returns purge logs |

#### E.5 Observability Agent
**Endpoints**: `GET /api/obs/metrics`, `GET /api/obs/snapshot`, `POST /api/obs/alert`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| E.5.1 | GET | `/api/obs/metrics` | 200 | Prometheus metrics |
| E.5.2 | GET | `/api/obs/snapshot` | 200 | Live agent status |
| E.5.3 | POST | `/api/obs/alert` | 202 | Test alert trigger |

#### E.6 Generation Balancer
**Endpoints**: `POST /api/gen/request`, `GET /api/gen/stats`

| Test Case | Method | Endpoint | Expected Status | Notes |
|-----------|--------|----------|----------------|-------|
| E.6.1 | POST | `/api/gen/request` | 202 or 501 | Request synthetic videos |
| E.6.2 | GET | `/api/gen/stats` | 200 | Generation totals per class |

---

### Phase F — Integration & End-to-End

#### F.1 Emotion → Dialogue → Cue Flow
**Complete workflow from Jetson emotion event to robot cue delivery**

**Steps**:
1. Jetson sends emotion event to Gateway (`POST /api/events/emotion`)
2. Gateway logs event and triggers dialogue generation
3. Dialogue service calls LM Studio (`POST /api/v1/dialogue/generate`)
4. LM Studio returns emotion-conditioned response
5. Dialogue service sends cue via WebSocket (`/ws/cues/{device_id}`)
6. Jetson receives cue and acknowledges

**Validation**:
- End-to-end latency < 2 seconds
- Correlation ID propagates through all steps
- Cue matches emotion (sad → sympathetic, happy → enthusiastic)
- WebSocket delivery succeeds
- Acknowledgment logged

#### F.2 Video Promotion → Manifest Rebuild → Training
**Complete workflow from temp video to training dataset**

**Steps**:
1. Upload video to `/videos/temp/`
2. Label via UI
3. Promote to `dataset_all` (`POST /api/v1/promote/stage`)
4. Sample into `train`/`test` (`POST /api/v1/promote/sample`)
5. Rebuild manifest (`POST /api/v1/promote/reset-manifest`)
6. Trigger training (`POST /api/train/start`)

**Validation**:
- Files moved atomically
- Database updated correctly
- Manifests generated
- Training job started
- MLflow run created

#### F.3 Multi-Device WebSocket Management
**Multiple robots connected simultaneously**

**Steps**:
1. Connect 3 devices: `reachy-mini-01`, `reachy-mini-02`, `reachy-mini-03`
2. Send emotion events from each
3. Generate dialogue for each
4. Push cues to specific devices
5. Broadcast cue to all devices
6. Disconnect one device
7. Verify others unaffected

**Validation**:
- All devices receive welcome
- Targeted cues reach correct device
- Broadcast reaches all connected
- Disconnection doesn't affect others
- Connection manager tracks all devices

---

## 4. Test Execution Tools

### Manual Testing
```bash
# Health checks
curl http://10.0.4.140:8000/health
curl http://10.0.4.130:8081/api/v1/health

# Emotion event
curl -X POST http://10.0.4.140:8000/api/events/emotion \
  -H "Content-Type: application/json" \
  -H "X-API-Version: v1" \
  -d '{"schema_version":"v1","device_id":"test","ts":"2025-11-17T20:00:00Z","emotion":"happy","confidence":0.85,"inference_ms":90,"window":{"fps":30,"size_s":1.2,"hop_s":0.5},"meta":{},"correlation_id":"test-123"}'

# Dialogue generation
curl -X POST http://10.0.4.130:8081/api/v1/dialogue/generate \
  -H "Content-Type: application/json" \
  -d '{"emotion":"sad","confidence":0.87,"user_message":"I'\''m having a rough day."}'

# WebSocket connection (using wscat)
wscat -c ws://10.0.4.130:8081/ws/cues/reachy-mini-test
# Send: {"type":"ping"}
# Expect: {"type":"pong","timestamp":"..."}
```

### Automated Testing
```bash
# Run all endpoint tests
pytest tests/test_dialogue_endpoints.py -v
pytest tests/test_websocket_cues.py -v
pytest tests/test_v1_endpoints.py -v

# Run with coverage
pytest --cov=apps.api.app.routers --cov-report=html

# Run specific test class
pytest tests/test_dialogue_endpoints.py::TestDialogueGeneration -v
```

### Load Testing
```bash
# k6 script for dialogue endpoint
k6 run scripts/load_test_dialogue.js

# Locust for WebSocket connections
locust -f scripts/websocket_load.py --host=ws://10.0.4.130:8081
```

---

## 5. Success Criteria

### Functional Requirements
- ✅ All Phase A-E endpoints return documented status codes
- ✅ Dialogue generation produces emotion-appropriate responses
- ✅ WebSocket connections stable for >5 minutes
- ✅ Correlation IDs propagate through all services
- ✅ Error responses follow standard envelope format
- ✅ Legacy endpoints emit deprecation headers

### Performance Requirements
- ✅ Health checks: p50 < 50ms, p95 < 100ms
- ✅ Dialogue generation: p50 < 1.5s, p95 < 3s (includes LM Studio)
- ✅ WebSocket message delivery: < 100ms
- ✅ Media listing: p50 < 200ms for 1000 videos
- ✅ Promotion dry-run: < 500ms for 100 videos

### Reliability Requirements
- ✅ No unhandled exceptions in logs
- ✅ Services remain healthy after 100 requests
- ✅ WebSocket reconnection works after disconnect
- ✅ LM Studio timeout handled gracefully
- ✅ Database connection pool stable

---

## 6. Test Reporting

### Report Format
For each phase, capture:
- **Test ID**: e.g., C.1.1
- **Endpoint**: e.g., `POST /api/v1/dialogue/generate`
- **Status**: PASS / FAIL / SKIP
- **Response Time**: e.g., 1.2s
- **Notes**: Any issues or observations

### Example Report Entry
```
C.1.1 | POST /api/v1/dialogue/generate | PASS | 1.35s | Sad emotion → sympathetic response
C.1.2 | POST /api/v1/dialogue/generate | PASS | 1.28s | Happy emotion → enthusiastic response
C.1.7 | POST /api/v1/dialogue/generate | PASS | 10.1s | Timeout handled correctly (504)
C.3.1 | WS /ws/cues/reachy-mini-01 | PASS | 45ms | Connection established, welcome received
```

### Failure Escalation
- **Critical**: Dialogue generation fails, WebSocket crashes
- **High**: Wrong emotion-gesture mapping, missing correlation IDs
- **Medium**: Slow response times, deprecation headers missing
- **Low**: Minor logging issues, cosmetic response differences

---

## 7. Next Steps

1. **Execute Phase A-B**: Verify core gateway and media mover endpoints (baseline)
2. **Execute Phase C**: Test new LM Studio dialogue integration thoroughly
3. **Execute Phase D-E**: Validate legacy and supporting services
4. **Execute Phase F**: Run end-to-end integration tests
5. **Document Results**: Capture all test outcomes in report
6. **Fix Failures**: Address critical and high-priority issues
7. **Automate**: Convert manual tests to pytest/k6 scripts for CI

---

## 8. References

- **Endpoint Documentation**: `/home/rusty_admin/projects/reachy_08.4.2/docs/endpoints.md`
- **Requirements**: `/home/rusty_admin/projects/reachy_08.4.2/memory-bank/requirements_08.4.2.md`
- **Agent Contracts**: `/home/rusty_admin/projects/reachy_08.4.2/AGENTS_08.4.2.md`
- **LM Studio Integration**: `/home/rusty_admin/projects/reachy_08.4.2/docs/gpt/2025-11-17-LM Studio-Customized Interaction.pdf`
- **Test Code**: `/home/rusty_admin/projects/reachy_08.4.2/tests/test_dialogue_endpoints.py`
- **WebSocket Tests**: `/home/rusty_admin/projects/reachy_08.4.2/tests/test_websocket_cues.py`

---

**Maintained by**: Russell Bray (rustybee255@gmail.com)  
**Test Plan Version**: 1.1.0  
**Next Review**: 2025-11-24
