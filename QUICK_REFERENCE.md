# Reachy Emotion Detection - Quick Reference

## 🎯 Project Structure

```
reachy_08.4.2/
├── apps/web/              # Streamlit Web UI
├── trainer/               # ML Training Pipeline
├── jetson/               # Edge Deployment
├── alembic/versions/     # Database Migrations
├── tests/                # Test Suite (151 tests)
├── memory-bank/          # Project Documentation
└── docs/gpt/             # Implementation Guides
```

## 🧪 Testing

```bash
# Run all tests
python -m pytest tests/ -v

# Run specific phase
python -m pytest tests/test_api_client_v2.py -v
python -m pytest tests/test_training_pipeline.py -v
python -m pytest tests/test_deployment.py -v

# With coverage
python -m pytest tests/ --cov=. --cov-report=html
```

## 🚀 Common Commands

### Web UI
```bash
streamlit run apps/web/main_app.py
```

### Training
```bash
# Setup TAO
cd trainer/tao && ./setup_tao_env.sh

# Train 2-class model
python trainer/train_emotionnet.py \
  --config trainer/tao/specs/emotionnet_2cls.yaml \
  --dataset /media/project_data/reachy_emotion/videos \
  --output trainer/tao/experiments

# Export to TensorRT
python trainer/export_to_trt.py \
  --model experiments/run_001/model.hdf5 \
  --output jetson/engines \
  --name emotionnet_v1 \
  --precision fp16
```

### Jetson Deployment
```bash
# Deploy
./jetson/deploy.sh

# Service management
sudo systemctl status reachy-emotion
sudo systemctl restart reachy-emotion
sudo journalctl -u reachy-emotion -f
```

## 📊 Test Results Summary

- **Phase 1**: 43 tests (Web UI & Foundation)
- **Phase 2**: 62 tests (ML Pipeline)
- **Phase 3**: 46 tests (Edge Deployment)
- **Total**: 151 tests, 137+ passing (90%+)

## 🔗 Key Endpoints

- **Web UI**: http://localhost:8501
- **API**: http://10.0.4.130/api/media
- **Gateway**: http://10.0.4.140:8000
- **MLflow**: http://localhost:5000 (if running)

## 📝 Important Files

### Configuration
- `trainer/tao/specs/emotionnet_2cls.yaml` - 2-class training config
- `jetson/deepstream/emotion_pipeline.txt` - DeepStream pipeline
- `jetson/systemd/reachy-emotion.service` - Systemd service

### Core Modules
- `apps/web/api_client_v2.py` - API client with retry logic
- `trainer/train_emotionnet.py` - Training orchestrator
- `jetson/emotion_main.py` - Jetson service main

### Tests
- `tests/test_api_client_v2.py` - API client tests (25)
- `tests/test_training_pipeline.py` - Training tests (15)
- `tests/test_deployment.py` - Deployment tests (16)

## 🐛 Troubleshooting

### Database Connection
```bash
# Check PostgreSQL
sudo systemctl status postgresql
psql -U reachy_app -d reachy_local -h localhost

# Reset database
psql reachy_local < alembic/versions/001_phase1_schema.sql
```

### TAO Training
```bash
# Check containers
docker ps | grep reachy-tao

# View logs
docker-compose -f trainer/tao/docker-compose-tao.yml logs -f

# Restart
docker-compose -f trainer/tao/docker-compose-tao.yml restart
```

### Jetson Service
```bash
# Check status
sudo systemctl status reachy-emotion

# View logs
sudo journalctl -u reachy-emotion -n 100 -f

# Restart
sudo systemctl restart reachy-emotion

# Check GPU
tegrastats
nvidia-smi
```

## 🔧 Environment Setup

```bash
# Python dependencies (if needed)
pip install -r requirements-phase1.txt
pip install -r requirements-phase2.txt

# Jetson dependencies
pip3 install python-socketio aiohttp psutil
```

## 📈 Performance Targets

- **Inference Latency**: <100ms (p95)
- **Throughput**: 30 FPS
- **GPU Temperature**: <75°C
- **Memory Usage**: <2GB
- **Model Accuracy**: F1 ≥ 0.84 (2-class), ≥ 0.75 (6-class)

## 🎓 Next Steps (Phase 4)

1. Review `/docs/gpt/Implementation_Phase4_Orchestration_Opus_4.1.md`
2. Implement n8n workflows
3. Setup agent coordination
4. Automate training triggers
5. Complete event-driven architecture

---

**For detailed information, see**: `IMPLEMENTATION_STATUS.md`
