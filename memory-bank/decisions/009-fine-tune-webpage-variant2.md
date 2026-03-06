---
title: Fine-Tune Webpage for Variant 2 (EfficientNet-B0 HSEmotion)
kind: decision
owners: [RussellBray]
related: [apps/web/pages/07_Fine_Tune.py, apps/web/api_client.py, apps/api/app/routers/training_control.py]
created: 2026-03-06
updated: 2026-03-06
status: active
---

# Fine-Tune Webpage for Variant 2 (EfficientNet-B0 HSEmotion)

## Context

The ML experiment involves three model variants:
1. **Base** — Pre-trained HSEmotion model with default weights, no synthetic data.
2. **Variant 1** — Pre-trained HSEmotion model + Luma-generated synthetic videos (Train page, 03_Train.py).
3. **Variant 2** — Pre-trained AND fine-tuned HSEmotion model + Luma synthetic videos (Fine-Tune page, 07_Fine_Tune.py).

All three variants are evaluated against the same fixed test dataset at
`videos/test/affectnet_test_dataset`.

A dedicated Fine-Tune page was needed to expose all relevant hyperparameters
for EfficientNet-B0 fine-tuning with user-friendly slider/toggle/select
interfaces, following the patterns established by the Train page.

## Decision / Content

Created `apps/web/pages/07_Fine_Tune.py` with 10 parameter groups, 25+ individual
tuneable hyperparameters, and inline documentation for each:

1. **Backbone Freezing Strategy** — freeze_backbone_epochs (slider), unfreeze_layers (multiselect)
2. **Learning Rate & Schedule** — learning_rate (log select_slider), min_lr, lr_scheduler, warmup_epochs
3. **Regularization** — weight_decay, dropout_rate, label_smoothing, gradient_clip_norm
4. **Data Augmentation** — mixup_alpha, mixup_probability
5. **Training Configuration** — batch_size, num_epochs, mixed_precision
6. **Early Stopping** — enabled toggle, patience, min_delta, monitor_metric
7. **Class Balance** — use_class_weights, class_weight_power
8. **Input & Frame Sampling** — input_size, frame_sampling, frames_per_video
9. **Post-Inference Smoothing** — smoothing_window_k (preview only, for deployment)
10. **Reproducibility** — seed, deterministic

Backend changes:
- `api_client.py` — Added `launch_finetune_run()` with `config_overrides` parameter.
- `training_control.py` — Added `config_overrides` to `TrainingLaunchRequest`,
  plus `_deep_merge()` and `_write_run_config()` to merge overrides into the base
  YAML and write a run-specific config at `trainer/fer_finetune/specs/runs/<run_id>_finetune.yaml`.

### Parameter Assessment vs. Conversation Recommendations

Parameters from the conversation that were **included** (directly applicable to
EfficientNet-B0 frame-level classification):
- Backbone freezing, differential learning rates, weight decay, batch size, epochs,
  label smoothing, dropout, mixup, LR scheduler, warmup, early stopping, class weights,
  input resolution, frame sampling.

Parameters that were **adjusted** for this architecture:
- **Smoothing kernel** — Correctly identified as a post-inference parameter, not a
  training parameter. Included as a deployment preview note only.
- **Temporal Head (TCN)** — Not applicable. EmotiEffLib/HSEmotion uses single-frame
  EfficientNet-B0; no temporal head exists in this codebase. Frame sampling strategy
  exposed instead.
- **Top-K frame sampling** — Not implemented in the trainer; omitted.
- **Face cropping margin** — Already on the Train page (dataset prep); not a
  fine-tuning parameter.

## Consequences

- Users can configure and launch fine-tuning runs entirely from the web UI.
- Run-specific YAML configs are preserved at `specs/runs/` for reproducibility.
- The same `/api/v1/training/launch` endpoint serves both Train and Fine-Tune pages.
- Test runs use the fixed AffectNet test dataset for all three model variants.

## Related

- `apps/web/pages/03_Train.py` — Variant 1 training page (template)
- `trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml` — Base config
- `trainer/fer_finetune/train_efficientnet.py` — EfficientNetTrainer
- `trainer/fer_finetune/config.py` — TrainingConfig dataclass
- `AGENTS.md` — Agent 5 (Training Orchestrator)

## Notes

- The _meta.smoothing_window_k field is stored in config overrides for later use
  by the Deployment Agent when configuring the DeepStream inference pipeline.
- Future work: add real-time training progress via WebSocket updates on this page.

---

**Last Updated**: 2026-03-06
**Owner**: Russell Bray
