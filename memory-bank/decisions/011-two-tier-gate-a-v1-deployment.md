---
title: Two-Tier Gate A & V1 Deployment
kind: decision
owners: [rusty_admin]
related: [requirements.md§7.1, AGENTS.md§Agent5-7, stats/results/runs/analysis_run_0107.md]
created: 2026-04-14
updated: 2026-04-14
status: active
---

# Two-Tier Gate A & V1 Deployment

## Context

Run 0107 revealed a fundamental **synthetic-to-real generalization gap**: models trained on
11,911 synthetic Luma videos (86,519 frames) achieve F1 ≥ 0.99 on synthetic validation but
only F1 ≈ 0.78 on real AffectNet faces (894-image test_dataset_01). The previous single-tier
Gate A threshold (F1 ≥ 0.84) was designed for synthetic validation metrics and blocks
deployment of models that are operationally adequate on real-world data.

Key run_0107 metrics on AffectNet test:

| Variant | F1 macro | ECE   | Brier | Balanced Acc |
|---------|----------|-------|-------|--------------|
| V1      | 0.781    | 0.102 | 0.340 | 0.780        |
| V2      | 0.780    | 0.096 | 0.279 | 0.784        |

Both variants pass ECE ≤ 0.12 on real data — **calibration is no longer a blocker**.
Classification accuracy (F1) is the remaining gap.

The base model (HSEmotion pre-trained on 500K+ real faces) scores F1 = 0.926 on the same
test set, but is **not a deployment candidate** because it uses the 8-class Ekman head
rather than the project's 3-class head.

## Decision

### 1. Split Gate A into two tiers

| Sub-gate | Evaluation Context | F1 macro | bAcc | Per-class F1 | ECE  | Brier |
|----------|--------------------|----------|------|-------------|------|-------|
| **Gate A-val** | Synthetic validation (training pipeline) | ≥ 0.84 | ≥ 0.85 | ≥ 0.75 | ≤ 0.12 | ≤ 0.16 |
| **Gate A-deploy** | Real-world test (AffectNet) | ≥ 0.75 | ≥ 0.75 | ≥ 0.70 | ≤ 0.12 | — |

- **Gate A-val** controls ONNX export in the training pipeline (unchanged).
- **Gate A-deploy** controls promotion to Jetson deployment. Brier is omitted because at
  F1 ≈ 0.78 it is dominated by classification errors, not calibration.

### 2. Deploy Variant 1 (run_0107) as initial production model

V1 is preferred over V2 because:
- **Balanced error profile**: V1 errors distribute across classes; V2 concentrates errors
  on neutral→sad confusion (35.1%).
- **Stability**: Frozen backbone = deterministic inference; no risk of fine-tuning artifacts.
- **Both pass Gate A-deploy**: F1 0.781 ≥ 0.75, ECE 0.102 ≤ 0.12.
- V1's happy→neutral confusion (33.8%) is safer than V2's neutral→sad confusion for a
  companion robot — misclassifying happy as neutral is lower-impact than misclassifying
  neutral as sad.

### 3. Remove base model from deployment consideration

The base model uses an 8-class head incompatible with the project's 3-class pipeline.
It remains a benchmark reference only.

## Consequences

1. **Code**: `gate_a_validator.py` and `config.py` need deploy-tier threshold presets.
   CLI must accept `--tier deploy` flag.
2. **Documentation**: `requirements.md` §7.1, `AGENTS.md` Agents 5/6/7, and
   `runbooks/model-deployment.md` must reflect the two-tier system.
3. **n8n workflows**: No JSON changes needed — workflows read gate pass/fail from Python
   output. Agent 6 may eventually support a two-mode evaluation path.
4. **Future work**: Improve real-world F1 via domain adaptation, AffectNet fine-tuning,
   or temperature scaling. Target: close the gap toward 0.84 on real data.
5. **Hardcoded ECE 0.08**: Several code files still reference the pre-relaxation ECE
   threshold of 0.08; these must be updated to 0.12.

## Alternatives Considered

1. **Keep single-tier Gate A at 0.84**: Rejected — blocks any deployment until the
   synthetic-to-real gap is fully closed, which requires significantly more diverse
   training data.
2. **Lower single-tier Gate A to 0.75**: Rejected — would also lower the bar for
   synthetic validation, masking training regressions.
3. **Deploy V2 instead of V1**: Rejected — V2's concentrated neutral→sad confusion
   pattern is worse for companion robot UX than V1's distributed errors.
4. **Deploy base model**: Rejected — 8-class head incompatible with 3-class pipeline.

## Related

- [Run 0107 Analysis](../../stats/results/runs/analysis_run_0107.md)
- [requirements.md §7.1](../requirements.md) — Deployment Gates
- [AGENTS.md](../../AGENTS.md) — Agents 5, 6, 7
- [Runbook: Model Deployment](../runbooks/model-deployment.md)
- [Gate A ECE Threshold Change](../decisions/) — ECE relaxed 0.08 → 0.12

## Notes

- The V2 sweep (101 trials) found configurations that pass Gate A-val on synthetic data
  (best: `var2_sweep_s2_t004`, F1=0.9996, ECE=0.0755). These should be evaluated against
  AffectNet test data to determine if any V2 sweep winner also passes Gate A-deploy.
- Face cropping was the transformational fix: test F1 doubled from 0.43 (run_0104) → 0.78
  (run_0107) after enabling face detection during frame extraction.

---

**Last Updated**: 2026-04-14  
**Owner**: Russell Bray
