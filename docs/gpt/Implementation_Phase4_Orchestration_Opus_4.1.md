# Phase 4: Orchestration & Automation Implementation
**Weeks 8-9 | n8n Agent Orchestration & Video Generation**

## Overview
Implement all 9 n8n agents, establish inter-agent communication, integrate video generation APIs, automate workflows.

## Components to Implement

### 4.1 n8n Agent Workflows (`n8n/workflows/`)

#### Core Agents
1. **Ingest Agent** (`01_ingest_agent.json`)
   - Webhook trigger for uploads
   - SHA256 hash computation
   - FFprobe metadata extraction
   - Thumbnail generation
   - Database insertion
   - Event emission

2. **Labeling Agent** (`02_labeling_agent.json`)
   - Label event reception
   - Validation rules
   - Class balance tracking
   - Database update
   - Promotion trigger

3. **Promotion Agent** (`03_promotion_agent.json`)
   - Atomic file movement
   - Database transaction
   - Manifest rebuild trigger
   - Notification dispatch
   - Rollback capability

4. **Training Orchestrator** (`04_training_orchestrator.json`)
   - Dataset readiness check
   - Training job launch
   - Progress monitoring
   - Gate validation
   - Model deployment trigger

5. **Evaluation Agent** (`05_evaluation_agent.json`)
   - Test set inference
   - Metric calculation
   - Confusion matrix generation
   - Report creation
   - Gate decision

6. **Deployment Agent** (`06_deployment_agent.json`)
   - Model version control
   - Canary deployment
   - Rollback mechanism
   - Health checking
   - Traffic shifting

7. **Privacy Agent** (`07_privacy_agent.json`)
   - TTL enforcement
   - Data redaction
   - Consent tracking
   - GDPR compliance
   - Audit logging

8. **Reconciler Agent** (`08_reconciler_agent.json`)
   - Consistency checking
   - Orphan cleanup
   - Database sync
   - File system validation
   - Alert generation

9. **Observability Agent** (`09_observability_agent.json`)
   - Metric aggregation
   - Alert routing
   - Dashboard updates
   - SLA tracking
   - Report generation

### 4.2 Video Generation Integration (`apps/generation/`)

#### Luma Integration (`luma_client.py`)
```python
class LumaClient:
    async def generate_video(prompt, emotion, duration)
    async def check_status(request_id)
    async def download_video(video_url)
```

#### Runway Integration (`runway_client.py`)
```python
class RunwayClient:
    async def generate_video(prompt, style, duration)
    async def apply_emotion_filter(video_id, emotion)
    async def export(video_id, format)
```

#### Generation Orchestrator (`generation_manager.py`)
- Provider selection (Luma vs Runway)
- Prompt template management
- Emotion-specific prompting
- Queue management
- Quota tracking
- Cost optimization

### 4.3 Agent Communication (`n8n/shared/`)

#### Message Bus (`message_bus.js`)
- Redis pub/sub implementation
- Event routing
- Message serialization
- Dead letter queue
- Retry logic

#### Common Functions (`utils.js`)
- Database helpers
- File operations
- Error handling
- Logging utilities
- Metric reporting

### 4.4 Scheduling & Triggers (`n8n/schedules/`)
- Cron expressions for periodic tasks
- Webhook endpoints
- Event listeners
- Queue consumers
- Health check endpoints

## Agent Interaction Flows

### Video Ingestion Flow
```
Upload → Ingest Agent → Hash/Metadata → Thumbnail → Database → Notification
```

### Promotion Flow
```
Label Event → Labeling Agent → Validation → Promotion Agent → File Move → Manifest Rebuild
```

### Training Flow
```
Schedule → Training Orchestrator → Dataset Check → Sample → Train → Evaluate → Deploy
```

### Generation Flow
```
Request → Generation Manager → Provider Selection → API Call → Poll Status → Download → Ingest
```

## Testing Strategy

### Unit Tests
```python
# tests/test_agents.py
- test_ingest_workflow
- test_promotion_logic
- test_training_trigger
- test_evaluation_gates

# tests/test_generation.py
- test_luma_api_integration
- test_runway_api_integration
- test_prompt_templating
- test_quota_management
```

### Integration Tests
```python
# tests/test_orchestration.py
- test_end_to_end_video_flow
- test_agent_communication
- test_error_recovery
- test_concurrent_workflows
```

### Load Tests
```python
# tests/test_load.py
- test_high_volume_ingestion (100 videos/min)
- test_concurrent_training_runs
- test_generation_queue_performance
- test_agent_scaling
```

## Implementation Order

1. **Week 8**:
   - Core agent workflows (Ingest, Label, Promote)
   - Message bus setup
   - Basic scheduling

2. **Week 9**:
   - Advanced agents (Training, Evaluation, Deploy)
   - Video generation integration
   - Inter-agent communication
   - Monitoring agents

## Success Criteria
- [ ] All 9 agents operational
- [ ] Video generation produces 50 clips/day
- [ ] Class balance maintained at 50/50 ±5%
- [ ] Automated training triggers work
- [ ] End-to-end pipeline <10 min/video
- [ ] Agent communication latency <1s
- [ ] Error recovery works correctly
