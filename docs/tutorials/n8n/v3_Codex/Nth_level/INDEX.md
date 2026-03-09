# n8n V3 Nth-Level Script/Function Tutorials

This curriculum maps each n8n node in `n8n/workflows/ml-agentic-ai_v.3` to the exact backend scripts, functions, queries, and side effects that implement the behavior.

## Modules
- [AGENT_01_09_PARAMETER_MATRIX.md](./AGENT_01_09_PARAMETER_MATRIX.md)
- [MODULE_01_INGEST_AGENT_NTH_LEVEL.md](./MODULE_01_INGEST_AGENT_NTH_LEVEL.md)
- [MODULE_02_LABELING_AGENT_NTH_LEVEL.md](./MODULE_02_LABELING_AGENT_NTH_LEVEL.md)
- [MODULE_03_PROMOTION_AGENT_NTH_LEVEL.md](./MODULE_03_PROMOTION_AGENT_NTH_LEVEL.md)
- [MODULE_04_RECONCILER_AGENT_NTH_LEVEL.md](./MODULE_04_RECONCILER_AGENT_NTH_LEVEL.md)
- [MODULE_05_TRAINING_ORCHESTRATOR_NTH_LEVEL.md](./MODULE_05_TRAINING_ORCHESTRATOR_NTH_LEVEL.md)
- [MODULE_06_EVALUATION_AGENT_NTH_LEVEL.md](./MODULE_06_EVALUATION_AGENT_NTH_LEVEL.md)
- [MODULE_07_DEPLOYMENT_AGENT_NTH_LEVEL.md](./MODULE_07_DEPLOYMENT_AGENT_NTH_LEVEL.md)
- [MODULE_08_PRIVACY_AGENT_NTH_LEVEL.md](./MODULE_08_PRIVACY_AGENT_NTH_LEVEL.md)
- [MODULE_09_OBSERVABILITY_AGENT_NTH_LEVEL.md](./MODULE_09_OBSERVABILITY_AGENT_NTH_LEVEL.md)

## Cross-Cutting Script References
- `apps/api/app/routers/ingest.py`
- `apps/api/routers/media.py`
- `apps/api/routers/gateway.py`
- `apps/api/app/routers/gateway_upstream.py`
- `apps/api/app/fs/media_mover.py`
- `apps/api/app/db/models.py`
- `trainer/run_efficientnet_pipeline.py`
- `trainer/gate_a_validator.py`
- `trainer/fer_finetune/train_efficientnet.py`
- `trainer/fer_finetune/specs/efficientnet_b0_emotion_3cls.yaml`

## How To Use These Nth-Level Guides
1. Open the workflow JSON and the matching Nth-level module side-by-side.
2. Validate node name, node type, and node expression path exactly.
3. Follow the “Backend Binding” and “Essential Functions” sections to trace runtime behavior.
4. Verify SQL/HTTP/SSH side effects before changing any node expression.
