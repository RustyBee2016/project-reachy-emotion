# Project Reachy — PM Cheat Sheet

**Print this page for quick reference**

---

## 🎯 Project in One Sentence

> Reachy is a companion robot that detects human emotions (happy/sad) via camera and responds with speech and gestures.

---

## 📊 Quality Gates

| Gate  | Pass Criteria                              | Status         |
| ----- | ------------------------------------------ | -------------- |
| **A** | F1 ≥ 0.84, Balanced Acc ≥ 0.85, ECE ≤ 0.08 | After training |
| **B** | Latency ≤ 120ms, Memory ≤ 2.5GB            | On Jetson      |
| **C** | Real-world user feedback                   | PM approval    |

---

## 🔧 Three Machines

| Machine      | IP         | Role                         |
| ------------ | ---------- | ---------------------------- |
| **Ubuntu 1** | 10.0.4.130 | Backend (training, database) |
| **Ubuntu 2** | 10.0.4.140 | Frontend (web UI, API)       |
| **Jetson**   | 10.0.4.150 | Robot (camera, inference)    |

---

## 📁 Key Files — Where to Look

| Need                   | Location                                                        |
| ---------------------- | --------------------------------------------------------------- |
| **Project overview**   | `docs/research_papers/Comprehensive_Overview_Project_Reachy.md` |
| **Requirements**       | `memory-bank/requirements.md`                                   |
| **Agent definitions**  | `AGENTS.md`                                                     |
| **8-week plan**        | `docs/tutorials/TUTORIAL_INDEX.md`                              |
| **n8n curriculum**     | `docs/tutorials/CURRICULUM_INDEX.md`                            |
| **ML training guides** | `docs/tutorials/fine_tuning/`                                   |
| **Web app curriculum** | `docs/tutorials/webapp/WEBAPP_CURRICULUM_INDEX.md`              |
| **Stats analysis**     | `docs/research_papers/Phase_1_Statistical_Analysis.md`          |
| **PM full guide**      | `docs/PM_ONBOARDING_GUIDE.md`                                   |

---

## 🤖 The 10 Agents

| #   | Agent         | One-liner            |
| --- | ------------- | -------------------- |
| 1   | Ingest        | Receives videos      |
| 2   | Labeling      | Human classification |
| 3   | Promotion     | Moves to dataset     |
| 4   | Reconciler    | Data integrity       |
| 5   | Training      | Triggers training    |
| 6   | Evaluation    | Quality checks       |
| 7   | Deployment    | Pushes to robot      |
| 8   | Privacy       | Data retention       |
| 9   | Observability | Monitoring           |
| 10  | Gesture       | Robot movements      |

---

## 📈 Phase Summary

| Phase | Focus                  | Key Output               |
| ----- | ---------------------- | ------------------------ |
| **1** | Offline ML             | Web app + trained model  |
| **2** | Emotional Intelligence | 8 emotions + calibration |
| **3** | Robotics               | Real-time + gestures     |

---

## 🔗 Quick Links

| Service | URL                     |
| ------- | ----------------------- |
| Web UI  | https://10.0.4.140:8501 |
| MLflow  | http://10.0.4.130:5000  |
| n8n     | http://10.0.4.130:5678  |

---

## 📖 Glossary (Top 10)

| Term                | Meaning                     |
| ------------------- | --------------------------- |
| **EfficientNet-B0** | Neural network architecture |
| **HSEmotion**       | Pre-trained emotion weights |
| **Gate A/B/C**      | Quality checkpoints         |
| **n8n**             | Workflow automation         |
| **MLflow**          | Experiment tracker          |
| **Macro F1**        | Accuracy metric (≥0.84)     |
| **ECE**             | Calibration error (≤0.08)   |
| **Fine-tuning**     | Training on our data        |
| **Jetson**          | Robot's computer            |
| **ONNX**            | Model export format         |

---

## ✅ PM Reading Priority

1. ✅ `PM_ONBOARDING_GUIDE.md` ← Start here
2. ⬜ `Comprehensive_Overview_Project_Reachy.md` (45 min)
3. ⬜ `memory-bank/requirements.md` (30 min)
4. ⬜ `AGENTS.md` (15 min)

---

## 🆘 Who to Ask

| Question About | Ask           |
| -------------- | ------------- |
| ML/Training    | ML Lead       |
| n8n/Workflows  | DevOps        |
| Database       | Backend Lead  |
| Robot/Jetson   | Embedded Lead |
| Statistics     | Data Science  |

---

*Last updated: 2026-01-31*
