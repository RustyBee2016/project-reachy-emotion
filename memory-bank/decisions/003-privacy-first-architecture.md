---
title: Privacy-First Architecture (Local-Only Video Processing)
kind: decision
owners: [Russell Bray]
related: [requirements.md#8, AGENTS.md#security--privacy-guardrails]
created: 2025-09-20
updated: 2025-10-04
status: active
---

# Privacy-First Architecture (Local-Only Video Processing)

## Context
The emotion recognition system processes video of human faces, which is sensitive personal data. We must balance functionality (training, debugging, user feedback) with privacy obligations (GDPR, COPPA, ethical AI guidelines).

Key concerns:
- **Raw video**: Contains identifiable faces, expressions, and potentially background context.
- **Training data**: Requires labeled video clips for fine-tuning ActionRecognitionNet.
- **Debugging**: May need to inspect misclassified clips.
- **User consent**: End-users interacting with Reachy may not expect video to leave the device.
- **Regulatory**: GDPR (right to be forgotten, data minimization), COPPA (parental consent for minors).

## Decision
**Adopt privacy-first architecture with local-only video processing by default.**

### Core Principles
1. **No raw video egress by default**: Jetson emits JSON emotion events only (emotion, confidence, latency, metadata); no video frames sent to Ubuntu 1/2 or cloud.
2. **On-device inference**: TensorRT engine runs on Jetson; no video streaming to remote inference servers.
3. **Explicit override for training**: Synthetic video generation (Luma/Veo/Flow) requires explicit flag and operator confirmation in UI; logged with metadata.
4. **Minimal retention**: `temp/` clips have TTL 7-14 days; purged on expiry or low-disk; promoted clips retained only as long as needed for training.
5. **User consent**: End-users must consent to video capture; opt-out available; DSAR process documented.
6. **Access controls**: LLM agents must NOT access raw video; only derived labels/confidence. Service-to-service auth via mTLS/JWT.

### Architecture Implications
- **Jetson → Ubuntu 2**: JSON events only (emotion, confidence, inference_ms, window, meta). No video frames.
- **Ubuntu 2 → Ubuntu 1**: LLM chat requests (text prompts), media promotion requests (video_id, not raw bytes). No video streaming.
- **Training data**: Stored on Ubuntu 1 filesystem (`/videos/train/`, `/videos/test/`); access restricted to training jobs and authorized operators.
- **Synthetic generation**: External APIs (Luma/Veo/Flow) used only when `synthetic=true` flag set; UI badges cloud-generated content; logs generator + version.
- **Debugging**: Misclassified clips flagged in DB; operators access via secure UI with audit log; no bulk export.

### Privacy Controls
- **Data minimization**: Store only necessary metadata (emotion, confidence, timestamps); no background audio or extraneous frames.
- **Retention policy**: `temp/` TTL 7-14 days; `train/test/` retained until model superseded + grace period; purge-on-request available.
- **Right to be forgotten**: DSAR process deletes video files, DB rows, and MLflow artifacts; logs redacted.
- **Consent flows**: UI presents clear consent prompt; opt-out stops video capture; parental consent for minors (COPPA).
- **Audit logs**: All video access logged with operator, timestamp, reason; append-only; monitored for anomalies.

## Consequences
### Positive
- **Regulatory compliance**: Meets GDPR data minimization, purpose limitation, and user rights requirements.
- **User trust**: Clear privacy stance builds confidence in human-robot interaction.
- **Reduced attack surface**: No video streaming reduces risk of interception or unauthorized access.
- **Ethical AI**: Aligns with OpenAI Model Spec and responsible AI guidelines.

### Negative
- **Debugging complexity**: Cannot inspect raw video remotely; must access Jetson or Ubuntu 1 directly (acceptable trade-off).
- **Training data sourcing**: Relies on synthetic generation or explicit user consent for real-world clips (mitigated by high-quality synthetic data).
- **Ops overhead**: Must maintain secure access controls, audit logs, and DSAR process (necessary for compliance).

### Follow-Up Actions
- Document DSAR process in runbook (request → verification → deletion → confirmation).
- Implement audit log for video access (operator, timestamp, reason, video_id).
- Add consent flow to UI with clear language and opt-out button.
- Train operators on privacy protocols and escalation procedures.

## Alternatives Considered
### 1. Cloud-Based Inference
- **Pros**: Centralized model updates, easier debugging, no Jetson compute constraints.
- **Cons**: Raw video egress violates privacy-first principle; latency overhead; regulatory risk.
- **Verdict**: Unacceptable privacy trade-off; on-device inference is non-negotiable.

### 2. Federated Learning
- **Pros**: Train on distributed data without centralizing raw video.
- **Cons**: Complex infrastructure; requires many devices; not needed for current scope.
- **Verdict**: Defer until multi-site deployment with many Reachy units.

### 3. Differential Privacy
- **Pros**: Adds noise to training data to protect individual privacy.
- **Cons**: May degrade model accuracy; complex to implement correctly.
- **Verdict**: Consider for future if real-world training data is used at scale.

## Related
- **[requirements.md §8](../requirements.md#8-compliance--ethics)**: Ethical guidelines, regulatory compliance, data governance.
- **[AGENTS.md §Security & Privacy Guardrails](../AGENTS.md#security--privacy-guardrails)**: LLM agents must not access raw video; mTLS/JWT; secrets from vault only.
- **[requirements.md §13.7](../requirements.md#137-authnauthz--transport)**: mTLS or short-lived JWTs for service calls; strict CORS; TLS 1.3.

## Notes
- Synthetic video generation is acceptable for training if properly labeled and logged.
- If real-world training data is needed, implement explicit consent flow with clear purpose statement.
- Monitor for privacy incidents; escalate to legal/compliance team immediately.
- Review privacy controls quarterly and update as regulations evolve.

---

**Last Updated**: 2025-10-04  
**Owner**: Russell Bray
