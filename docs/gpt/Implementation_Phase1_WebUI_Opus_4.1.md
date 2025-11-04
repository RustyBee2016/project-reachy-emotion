# Phase 1: Web UI & Foundation Implementation
**Weeks 1-2 | Foundation Completion**

## Overview
Complete Web UI integration with Media Mover API, implement WebSocket support, finalize database schema.

## Components to Implement

### 1.1 Enhanced API Client (`apps/web/api_client_v2.py`)
- Exponential backoff retry logic with jitter
- Idempotency key generation
- Async batch operations
- Comprehensive error handling
- Connection pooling

### 1.2 WebSocket Client (`apps/web/websocket_client.py`)
- Auto-reconnection with backoff
- Event subscription system
- Thread-safe message queuing
- Heartbeat monitoring
- Real-time event handlers for:
  - Emotion events from Jetson
  - Promotion completion
  - Training status updates
  - Video generation completion

### 1.3 Main Streamlit Application (`apps/web/main_app.py`)
- Session state management
- Multi-page navigation
- Real-time status indicators
- WebSocket integration
- Custom CSS theming

### 1.4 Video Management Page (`apps/web/pages/video_management.py`)
- Video listing with filtering
- Upload interface
- Batch labeling
- Promotion workflow
- Thumbnail gallery view

### 1.5 Database Migrations (`alembic/versions/`)
- `training_run` table
- `training_selection` table  
- `promotion_log` table
- `user_session` table
- `generation_request` table
- `emotion_event` table
- Stored procedures for business logic

## Testing Strategy

### Unit Tests
```python
# tests/test_api_client.py
- test_exponential_backoff_retry
- test_idempotency_key_generation
- test_connection_error_handling
- test_batch_promote_async

# tests/test_websocket_client.py
- test_auto_reconnection
- test_event_subscription
- test_message_queuing
- test_heartbeat_timeout
```

### Integration Tests
```python
# tests/test_integration.py
- test_upload_label_promote_flow
- test_websocket_event_delivery
- test_database_transaction_rollback
- test_concurrent_promotions
```

## Implementation Order
1. Database migrations (foundation for everything)
2. API client with retry logic
3. WebSocket client
4. Streamlit main app structure
5. Individual page implementations

## Success Criteria
- [ ] All API calls have retry logic
- [ ] WebSocket maintains persistent connection
- [ ] UI updates in real-time with events
- [ ] Database schema supports all operations
- [ ] Tests pass with >80% coverage
