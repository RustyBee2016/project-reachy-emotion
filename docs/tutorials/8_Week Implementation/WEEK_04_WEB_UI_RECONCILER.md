# Week 4 Tutorial: Web UI Enhancement & Reconciler Agent

**Project**: Reachy Emotion Recognition  
**Duration**: 5 days  
**Prerequisites**: Week 3 complete, Streamlit environment configured

---

## Overview

This week focuses on enhancing the web UI with dataset management features and testing the Reconciler Agent workflow.

### Weekly Goals
- [ ] Add dataset curation UI to Streamlit (train/test visualization)
- [ ] Add training progress dashboard
- [ ] Test Reconciler Agent workflow
- [ ] Implement dry-run mode for all promotion operations

---

## Day 1: Dataset Curation UI - Overview Component

### Step 1.1: Create Dataset Overview Component

Create `apps/web/components/dataset_overview.py`:

```python
"""
Dataset Overview Component for Streamlit UI.

Displays current dataset statistics, class distribution,
and split information.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

# API configuration
API_BASE_URL = "http://10.0.4.140:8000/api"


async def fetch_dataset_stats() -> Dict:
    """Fetch dataset statistics from API."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(f"{API_BASE_URL}/videos/stats")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Failed to fetch stats: {e}")
            return {}


def render_dataset_overview():
    """Render the dataset overview section."""
    st.header("📊 Dataset Overview")
    
    # Fetch stats (using sync wrapper for Streamlit)
    stats = st.session_state.get("dataset_stats", {})
    
    if not stats:
        st.warning("Unable to load dataset statistics. Check API connection.")
        if st.button("Retry"):
            st.rerun()
        return
    
    # Summary metrics in columns
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Total Videos",
            stats.get("total_count", 0),
            delta=stats.get("new_today", 0),
            delta_color="normal"
        )
    
    with col2:
        st.metric(
            "Labeled",
            stats.get("labeled_count", 0),
            delta=f"{stats.get('label_rate', 0):.1%}"
        )
    
    with col3:
        st.metric(
            "In Training Set",
            stats.get("train_count", 0)
        )
    
    with col4:
        st.metric(
            "In Test Set",
            stats.get("test_count", 0)
        )
    
    st.divider()
    
    # Split distribution
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Split Distribution")
        split_data = stats.get("split_distribution", {})
        if split_data:
            fig = px.pie(
                names=list(split_data.keys()),
                values=list(split_data.values()),
                title="Videos by Split",
                color_discrete_sequence=px.colors.qualitative.Set2
            )
            fig.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("Class Distribution")
        class_data = stats.get("class_distribution", {})
        if class_data:
            fig = px.bar(
                x=list(class_data.keys()),
                y=list(class_data.values()),
                title="Videos by Emotion Class",
                color=list(class_data.keys()),
                color_discrete_sequence=px.colors.qualitative.Pastel
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)


def render_class_balance_indicator():
    """Render class balance indicator with warnings."""
    st.subheader("⚖️ Class Balance Status")
    
    stats = st.session_state.get("dataset_stats", {})
    class_counts = stats.get("class_distribution", {})
    
    if not class_counts:
        st.info("No labeled data available yet.")
        return
    
    # Calculate balance metrics
    counts = list(class_counts.values())
    min_count = min(counts)
    max_count = max(counts)
    
    if max_count == 0:
        st.info("No labeled data available yet.")
        return
    
    balance_ratio = min_count / max_count if max_count > 0 else 0
    
    # Display balance indicator
    if balance_ratio >= 0.8:
        st.success(f"✅ Classes are well-balanced (ratio: {balance_ratio:.2f})")
    elif balance_ratio >= 0.5:
        st.warning(f"⚠️ Moderate class imbalance (ratio: {balance_ratio:.2f})")
    else:
        st.error(f"❌ Severe class imbalance (ratio: {balance_ratio:.2f})")
    
    # Show per-class details
    with st.expander("View per-class counts"):
        df = pd.DataFrame({
            "Class": list(class_counts.keys()),
            "Count": list(class_counts.values()),
        })
        df["Percentage"] = df["Count"] / df["Count"].sum() * 100
        st.dataframe(df, use_container_width=True)
    
    # Recommendations
    if balance_ratio < 0.8:
        underrepresented = [
            cls for cls, count in class_counts.items()
            if count < max_count * 0.8
        ]
        st.info(f"💡 Consider adding more samples for: {', '.join(underrepresented)}")


def render_split_details(split: str):
    """Render detailed view of a specific split."""
    st.subheader(f"📁 {split.title()} Split Details")
    
    # Fetch videos for this split
    videos = st.session_state.get(f"videos_{split}", [])
    
    if not videos:
        st.info(f"No videos in {split} split.")
        return
    
    # Display as table
    df = pd.DataFrame(videos)
    
    # Select columns to display
    display_cols = ["video_id", "label", "duration_sec", "created_at"]
    available_cols = [c for c in display_cols if c in df.columns]
    
    st.dataframe(
        df[available_cols],
        use_container_width=True,
        hide_index=True
    )
    
    # Export option
    if st.button(f"Export {split} manifest"):
        csv = df.to_csv(index=False)
        st.download_button(
            label="Download CSV",
            data=csv,
            file_name=f"{split}_manifest.csv",
            mime="text/csv"
        )
```

### Step 1.2: Create API Endpoint for Stats

Add to `apps/api/routers/videos.py`:

```python
@router.get("/stats")
async def get_dataset_stats(db: Session = Depends(get_db)):
    """Get dataset statistics for UI dashboard."""
    
    # Total counts by split
    split_counts = db.execute(
        "SELECT split, COUNT(*) as count FROM video GROUP BY split"
    ).fetchall()
    
    # Class distribution (labeled only)
    class_counts = db.execute(
        "SELECT label, COUNT(*) as count FROM video "
        "WHERE label IS NOT NULL GROUP BY label"
    ).fetchall()
    
    # Recent activity
    new_today = db.execute(
        "SELECT COUNT(*) FROM video WHERE created_at > CURRENT_DATE"
    ).scalar()
    
    total = sum(row.count for row in split_counts)
    labeled = sum(row.count for row in class_counts)
    
    return {
        "total_count": total,
        "labeled_count": labeled,
        "label_rate": labeled / total if total > 0 else 0,
        "new_today": new_today,
        "train_count": next((r.count for r in split_counts if r.split == "train"), 0),
        "test_count": next((r.count for r in split_counts if r.split == "test"), 0),
        "split_distribution": {r.split: r.count for r in split_counts},
        "class_distribution": {r.label: r.count for r in class_counts},
    }
```

### Step 1.3: Integrate into Landing Page

Update `apps/web/landing_page.py` to include the overview:

```python
from components.dataset_overview import (
    render_dataset_overview,
    render_class_balance_indicator,
)

# In the main function, add a new tab or section:
tab1, tab2, tab3 = st.tabs(["Generate", "Label", "Dataset"])

with tab3:
    render_dataset_overview()
    render_class_balance_indicator()
```

### Checkpoint: Day 1 Complete
- [ ] Dataset overview component created
- [ ] Stats API endpoint added
- [ ] Integrated into landing page
- [ ] Charts rendering correctly

---

## Day 2: Training Progress Dashboard

### Step 2.1: Create Training Dashboard Component

Create `apps/web/components/training_dashboard.py`:

```python
"""
Training Progress Dashboard for Streamlit UI.

Displays active training runs, metrics, and Gate A status.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Optional
from datetime import datetime
import httpx
import mlflow

# MLflow configuration
MLFLOW_TRACKING_URI = "http://10.0.4.130:5000"


def get_recent_runs(experiment_name: str = "reachy_emotion", limit: int = 10) -> List[Dict]:
    """Fetch recent training runs from MLflow."""
    try:
        mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)
        experiment = mlflow.get_experiment_by_name(experiment_name)
        
        if not experiment:
            return []
        
        runs = mlflow.search_runs(
            experiment_ids=[experiment.experiment_id],
            max_results=limit,
            order_by=["start_time DESC"]
        )
        
        return runs.to_dict('records')
    except Exception as e:
        st.error(f"Failed to fetch MLflow runs: {e}")
        return []


def render_training_dashboard():
    """Render the training progress dashboard."""
    st.header("🏋️ Training Dashboard")
    
    # Fetch recent runs
    runs = get_recent_runs()
    
    if not runs:
        st.info("No training runs found. Start a training job to see progress here.")
        return
    
    # Active runs
    active_runs = [r for r in runs if r.get("status") == "RUNNING"]
    
    if active_runs:
        st.subheader("🔄 Active Training Runs")
        for run in active_runs:
            render_active_run(run)
    
    # Recent completed runs
    st.subheader("📋 Recent Runs")
    render_runs_table(runs)
    
    # Metrics comparison
    st.subheader("📈 Metrics Comparison")
    render_metrics_comparison(runs)


def render_active_run(run: Dict):
    """Render an active training run with progress."""
    with st.container():
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.write(f"**Run ID:** {run.get('run_id', 'N/A')[:8]}...")
            st.write(f"**Started:** {run.get('start_time', 'N/A')}")
        
        with col2:
            current_epoch = run.get("metrics.epoch", 0)
            total_epochs = run.get("params.epochs", 10)
            progress = current_epoch / total_epochs if total_epochs > 0 else 0
            st.progress(progress, text=f"Epoch {current_epoch}/{total_epochs}")
        
        with col3:
            current_f1 = run.get("metrics.val_f1", 0)
            st.metric("Val F1", f"{current_f1:.4f}")


def render_runs_table(runs: List[Dict]):
    """Render table of training runs."""
    if not runs:
        return
    
    # Prepare data
    table_data = []
    for run in runs[:10]:
        table_data.append({
            "Run ID": run.get("run_id", "")[:8],
            "Status": run.get("status", "UNKNOWN"),
            "Macro F1": run.get("metrics.macro_f1", 0),
            "Balanced Acc": run.get("metrics.balanced_accuracy", 0),
            "Gate A": "✅" if run.get("metrics.gate_a_passed", 0) == 1 else "❌",
            "Started": run.get("start_time", ""),
        })
    
    df = pd.DataFrame(table_data)
    
    # Style the dataframe
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Macro F1": st.column_config.NumberColumn(format="%.4f"),
            "Balanced Acc": st.column_config.NumberColumn(format="%.4f"),
        }
    )


def render_metrics_comparison(runs: List[Dict]):
    """Render metrics comparison chart."""
    if len(runs) < 2:
        st.info("Need at least 2 runs for comparison.")
        return
    
    # Extract metrics
    metrics_data = []
    for run in runs[:10]:
        metrics_data.append({
            "Run": run.get("run_id", "")[:8],
            "Macro F1": run.get("metrics.macro_f1", 0),
            "Balanced Accuracy": run.get("metrics.balanced_accuracy", 0),
            "F1 Neutral": run.get("metrics.f1_neutral", 0),
        })
    
    df = pd.DataFrame(metrics_data)
    
    # Create grouped bar chart
    fig = go.Figure()
    
    for metric in ["Macro F1", "Balanced Accuracy", "F1 Neutral"]:
        fig.add_trace(go.Bar(
            name=metric,
            x=df["Run"],
            y=df[metric],
        ))
    
    fig.update_layout(
        barmode='group',
        title="Metrics Across Recent Runs",
        xaxis_title="Run ID",
        yaxis_title="Score",
        yaxis_range=[0, 1],
    )
    
    # Add Gate A threshold lines
    fig.add_hline(y=0.84, line_dash="dash", line_color="red", 
                  annotation_text="Macro F1 threshold (0.84)")
    fig.add_hline(y=0.82, line_dash="dash", line_color="orange",
                  annotation_text="Balanced Acc threshold (0.82)")
    
    st.plotly_chart(fig, use_container_width=True)


def render_gate_a_status(run: Dict):
    """Render Gate A validation status for a run."""
    st.subheader("🚦 Gate A Status")
    
    gates = {
        "Macro F1 ≥ 0.84": run.get("metrics.macro_f1", 0) >= 0.84,
        "Balanced Acc ≥ 0.85": run.get("metrics.balanced_accuracy", 0) >= 0.85,
        "ECE ≤ 0.08": run.get("metrics.ece", 1) <= 0.08,
        "Brier ≤ 0.16": run.get("metrics.brier", 1) <= 0.16,
    }
    
    all_passed = all(gates.values())
    
    if all_passed:
        st.success("✅ All Gate A requirements met!")
    else:
        st.error("❌ Gate A requirements not met")
    
    # Show individual gates
    cols = st.columns(len(gates))
    for i, (gate, passed) in enumerate(gates.items()):
        with cols[i]:
            if passed:
                st.success(f"✅ {gate}")
            else:
                st.error(f"❌ {gate}")
```

### Step 2.2: Add Training Dashboard to UI

Update `apps/web/landing_page.py`:

```python
from components.training_dashboard import render_training_dashboard

# Add to tabs
tab1, tab2, tab3, tab4 = st.tabs(["Generate", "Label", "Dataset", "Training"])

with tab4:
    render_training_dashboard()
```

### Checkpoint: Day 2 Complete
- [ ] Training dashboard component created
- [ ] MLflow integration working
- [ ] Metrics comparison chart
- [ ] Gate A status display

---

## Day 3: Reconciler Agent Testing

### Step 3.1: Import Reconciler Agent Workflow

1. Import `n8n/workflows/ml-agentic-ai_v.2/04_reconciler_agent.json`
2. Review workflow nodes

### Step 3.2: Understand Reconciler Agent Flow

The Reconciler Agent performs:
1. **Trigger**: Scheduled (cron) or manual trigger
2. **Scan Filesystem**: List all files in video directories
3. **Query Database**: Get all video records
4. **Compare**: Find orphaned files, missing files, hash mismatches
5. **Report**: Generate reconciliation report
6. **Fix** (optional): Auto-fix minor issues
7. **Rebuild Manifests**: If drift detected
8. **Emit Metrics**: Publish to Prometheus

### Step 3.3: Create Test Scenarios

Set up test scenarios for reconciliation:

```bash
# Scenario 1: Orphaned file (file exists, no DB record)
touch /media/project_data/reachy_emotion/videos/temp/orphan_test.mp4

# Scenario 2: Missing file (DB record, no file)
# Insert a fake record in DB
psql -h 10.0.4.130 -U reachy_dev -d reachy_emotion -c "
INSERT INTO video (video_id, file_path, split, sha256)
VALUES ('00000000-0000-0000-0000-000000000001', 'videos/temp/missing.mp4', 'temp', 'fakehash');
"

# Scenario 3: Hash mismatch (modify a file after ingest)
echo "modified" >> /media/project_data/reachy_emotion/videos/temp/test_ingest_001.mp4
```

### Step 3.4: Run Reconciler Agent

1. Open Reconciler Agent workflow in n8n
2. Execute manually
3. Review output for each scenario

### Step 3.5: Verify Reconciliation Report

Check the reconciliation report includes:
- [ ] Orphaned files count and list
- [ ] Missing files count and list
- [ ] Hash mismatches count and list
- [ ] Recommendations

### Step 3.6: Test Auto-Fix Mode

Configure Reconciler to auto-fix:

```json
{
  "mode": "auto_fix",
  "fix_orphans": true,
  "fix_missing": false,
  "rebuild_manifests": true
}
```

Run and verify:
- [ ] Orphaned files registered in DB
- [ ] Manifests rebuilt
- [ ] Report shows fixes applied

### Step 3.7: Verify Prometheus Metrics

Check metrics are published:

```bash
curl http://10.0.4.130:9101/metrics | grep reconcile
```

Expected metrics:
- `reconcile_orphaned_files_total`
- `reconcile_missing_files_total`
- `reconcile_hash_mismatches_total`
- `reconcile_last_run_timestamp`

### Checkpoint: Day 3 Complete
- [ ] Reconciler Agent imported
- [ ] Test scenarios created
- [ ] Orphaned files detected
- [ ] Missing files detected
- [ ] Hash mismatches detected
- [ ] Auto-fix mode tested
- [ ] Metrics published

---

## Day 4: Dry-Run Mode Implementation

### Step 4.1: Update Promotion API for Dry-Run

Ensure all promotion endpoints support dry-run:

```python
# In apps/api/routers/promote.py

@router.post("/stage")
async def stage_videos(
    request: StageRequest,
    db: Session = Depends(get_db)
):
    """Stage videos from temp to dataset_all."""
    
    if request.dry_run:
        # Preview mode - don't make changes
        preview = await preview_stage_operation(
            db, request.video_ids, request.label
        )
        return {
            "dry_run": True,
            "would_stage": len(preview["valid"]),
            "would_skip": len(preview["invalid"]),
            "details": preview,
        }
    
    # Actual staging
    result = await perform_stage_operation(
        db, request.video_ids, request.label
    )
    return result


async def preview_stage_operation(
    db: Session,
    video_ids: List[str],
    label: str
) -> Dict:
    """Preview what would happen in a stage operation."""
    valid = []
    invalid = []
    
    for video_id in video_ids:
        video = db.query(Video).filter(Video.video_id == video_id).first()
        
        if not video:
            invalid.append({"video_id": video_id, "reason": "not_found"})
        elif video.split != "temp":
            invalid.append({"video_id": video_id, "reason": "wrong_split"})
        elif not label:
            invalid.append({"video_id": video_id, "reason": "no_label"})
        else:
            valid.append({
                "video_id": video_id,
                "current_path": video.file_path,
                "target_path": f"videos/dataset_all/{video_id}.mp4",
                "label": label,
            })
    
    return {"valid": valid, "invalid": invalid}
```

### Step 4.2: Update UI for Dry-Run Preview

Add dry-run preview to the labeling UI:

```python
# In apps/web/landing_page.py

def render_promotion_preview():
    """Show preview of what will be promoted."""
    st.subheader("Preview Promotion")
    
    selected_videos = st.session_state.get("selected_for_promotion", [])
    
    if not selected_videos:
        st.info("No videos selected for promotion.")
        return
    
    # Fetch dry-run preview
    if st.button("Preview Changes"):
        with st.spinner("Fetching preview..."):
            response = requests.post(
                f"{API_BASE_URL}/v1/promote/stage",
                json={
                    "video_ids": selected_videos,
                    "label": st.session_state.get("selected_label"),
                    "dry_run": True,
                }
            )
            
            if response.ok:
                preview = response.json()
                
                st.write(f"**Would stage:** {preview['would_stage']} videos")
                st.write(f"**Would skip:** {preview['would_skip']} videos")
                
                if preview["details"]["valid"]:
                    st.success("Valid videos:")
                    for v in preview["details"]["valid"]:
                        st.write(f"  - {v['video_id'][:8]}... → {v['target_path']}")
                
                if preview["details"]["invalid"]:
                    st.warning("Invalid videos:")
                    for v in preview["details"]["invalid"]:
                        st.write(f"  - {v['video_id'][:8]}...: {v['reason']}")
                
                # Confirm button
                if st.button("Confirm Promotion"):
                    perform_actual_promotion(selected_videos)
```

### Step 4.3: Add Dry-Run to n8n Workflows

Update each n8n workflow to check for dry_run flag:

```javascript
// In n8n Function node
const dryRun = $input.item.json.dry_run || false;

if (dryRun) {
  return {
    json: {
      dry_run: true,
      would_perform: "stage_to_dataset_all",
      video_id: $input.item.json.video_id,
      preview: {
        source: "/videos/temp/...",
        destination: "/videos/dataset_all/...",
      }
    }
  };
}

// Continue with actual operation...
```

### Step 4.4: Test Dry-Run Across All Operations

```bash
# Test stage dry-run
curl -X POST http://10.0.4.140:8000/api/v1/promote/stage \
  -H "Content-Type: application/json" \
  -d '{
    "video_ids": ["<video_id>"],
    "label": "happy",
    "dry_run": true
  }'

# Test sample dry-run
curl -X POST http://10.0.4.140:8000/api/v1/promote/sample \
  -H "Content-Type: application/json" \
  -d '{
    "run_id": "test-run",
    "target_split": "train",
    "sample_fraction": 0.7,
    "dry_run": true
  }'
```

### Checkpoint: Day 4 Complete
- [ ] Dry-run implemented in API
- [ ] Preview UI component added
- [ ] n8n workflows support dry-run
- [ ] All operations tested

---

## Day 5: Integration Testing & Documentation

### Step 5.1: End-to-End UI Test

Perform complete workflow through UI:

1. **Generate video** → Verify appears in temp
2. **Label video** → Verify label applied
3. **Preview promotion** → Verify dry-run works
4. **Promote video** → Verify moved to dataset_all
5. **Check dataset overview** → Verify stats updated
6. **Trigger reconciler** → Verify no issues

### Step 5.2: Create UI Tests

Create `tests/test_streamlit_components.py`:

```python
"""Tests for Streamlit UI components."""

import pytest
from unittest.mock import patch, MagicMock


def test_dataset_overview_renders():
    """Test dataset overview component renders without errors."""
    from apps.web.components.dataset_overview import render_dataset_overview
    
    with patch("streamlit.header") as mock_header:
        with patch("streamlit.session_state", {"dataset_stats": {
            "total_count": 100,
            "labeled_count": 80,
            "train_count": 50,
            "test_count": 20,
        }}):
            # Should not raise
            render_dataset_overview()
            mock_header.assert_called()


def test_class_balance_indicator():
    """Test class balance indicator shows correct status."""
    from apps.web.components.dataset_overview import render_class_balance_indicator
    
    # Test balanced case
    with patch("streamlit.session_state", {"dataset_stats": {
        "class_distribution": {"happy": 50, "sad": 48}
    }}):
        with patch("streamlit.success") as mock_success:
            render_class_balance_indicator()
            # Should show success for balanced classes
            assert mock_success.called


def test_training_dashboard_no_runs():
    """Test training dashboard handles no runs gracefully."""
    from apps.web.components.training_dashboard import render_training_dashboard
    
    with patch("apps.web.components.training_dashboard.get_recent_runs", return_value=[]):
        with patch("streamlit.info") as mock_info:
            render_training_dashboard()
            mock_info.assert_called()
```

### Step 5.3: Run All Tests

```bash
# Run UI component tests
pytest tests/test_streamlit_components.py -v

# Run webhook tests
pytest tests/test_webhooks.py -v

# Run full test suite
pytest tests/ -v --ignore=tests/manual_*
```

### Step 5.4: Update Documentation

Create `docs/WEB_UI_GUIDE.md`:

```markdown
# Web UI User Guide

## Overview
The Reachy Emotion Recognition web UI provides tools for:
- Generating synthetic emotion videos
- Labeling videos with emotion classes
- Managing the training dataset
- Monitoring training progress

## Tabs

### Generate Tab
- Create new synthetic videos using Luma AI
- Configure emotion type and parameters
- Preview generated videos

### Label Tab
- View videos pending labeling
- Assign emotion labels
- Accept or reject videos

### Dataset Tab
- View dataset statistics
- Check class balance
- Export manifests

### Training Tab
- Monitor active training runs
- View metrics history
- Check Gate A status

## Dry-Run Mode
All promotion operations support dry-run mode:
1. Select videos for promotion
2. Click "Preview Changes"
3. Review what will happen
4. Confirm or cancel
```

### Checkpoint: Day 5 Complete
- [ ] E2E UI test completed
- [ ] Component tests created
- [ ] All tests passing
- [ ] Documentation updated

---

## Week 4 Deliverables Summary

| Deliverable | Status | Location |
|-------------|--------|----------|
| Dataset overview component | ✅ | `apps/web/components/dataset_overview.py` |
| Training dashboard | ✅ | `apps/web/components/training_dashboard.py` |
| Reconciler Agent tested | ✅ | n8n workflow |
| Dry-run mode | ✅ | API + UI + n8n |
| UI tests | ✅ | `tests/test_streamlit_components.py` |
| Documentation | ✅ | `docs/WEB_UI_GUIDE.md` |

---

## Next Steps

Proceed to [Week 5: Jetson Deployment Automation](WEEK_05_JETSON_DEPLOYMENT.md).
