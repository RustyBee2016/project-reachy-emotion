# Tutorial 12: Batch Video Operations

> **Priority**: MEDIUM — Completes Video Management UI
> **Time estimate**: 6-8 hours
> **Difficulty**: Moderate
> **Prerequisites**: Streamlit, API endpoints understood

---

## Why This Matters

The Video Management page (`apps/web/pages/05_Video_Management.py`) has
two stubbed functions with TODO comments:

```python
def perform_batch_labeling(label: str):
    st.info(f"Labeling {len(st.session_state.selected_videos)} videos as '{label}'")
    # TODO: Implement relabel API call

def perform_batch_delete():
    st.warning(f"Would delete {len(st.session_state.selected_videos)} videos")
    # TODO: Implement delete API call
```

---

## What You'll Build

Working implementations that:
1. Call the API to relabel selected videos
2. Call the API to delete/purge selected videos
3. Show confirmation dialogs before destructive actions
4. Update the UI after operations complete

---

## Step 1: Implement Batch Labeling

Find `perform_batch_labeling` in `apps/web/pages/05_Video_Management.py`
and replace it:

```python
def perform_batch_labeling(label: str):
    """Apply a label to all selected videos via the API."""
    selected = st.session_state.get("selected_videos", [])
    if not selected:
        st.warning("No videos selected.")
        return

    success_count = 0
    fail_count = 0

    progress = st.progress(0, text="Labeling videos...")

    for i, video_id in enumerate(selected):
        try:
            resp = requests.patch(
                f"{GATEWAY_URL}/api/v1/media/{video_id}/label",
                json={"label": label},
                timeout=10,
            )
            if resp.ok:
                success_count += 1
            else:
                fail_count += 1
                st.error(f"Failed to label {video_id}: {resp.status_code}")
        except requests.RequestException as e:
            fail_count += 1
            st.error(f"Error labeling {video_id}: {e}")

        progress.progress((i + 1) / len(selected))

    if success_count > 0:
        st.success(f"Labeled {success_count} videos as '{label}'")
    if fail_count > 0:
        st.warning(f"Failed to label {fail_count} videos")

    # Clear selection
    st.session_state.selected_videos = []
```

---

## Step 2: Implement Batch Delete with Confirmation

Replace `perform_batch_delete`:

```python
def perform_batch_delete():
    """Delete selected videos after confirmation."""
    selected = st.session_state.get("selected_videos", [])
    if not selected:
        st.warning("No videos selected.")
        return

    # Require explicit confirmation
    confirm_key = f"confirm_delete_{len(selected)}"
    confirmed = st.checkbox(
        f"I confirm deletion of {len(selected)} video(s). This cannot be undone.",
        key=confirm_key,
    )

    if not confirmed:
        st.info("Check the confirmation box to proceed with deletion.")
        return

    if st.button("Delete Now", type="primary", key="delete_now"):
        success_count = 0
        fail_count = 0

        for video_id in selected:
            try:
                resp = requests.delete(
                    f"{GATEWAY_URL}/api/v1/media/{video_id}",
                    timeout=10,
                )
                if resp.ok or resp.status_code == 404:
                    success_count += 1
                else:
                    fail_count += 1
            except requests.RequestException:
                fail_count += 1

        if success_count > 0:
            st.success(f"Deleted {success_count} videos")
        if fail_count > 0:
            st.warning(f"Failed to delete {fail_count} videos")

        st.session_state.selected_videos = []
```

---

## Step 3: Add the Import

Make sure `requests` is imported at the top of the file:

```python
import requests
```

And that `GATEWAY_URL` is defined:

```python
GATEWAY_URL = st.session_state.get(
    "gateway_url", "http://10.0.4.140:8000"
)
```

---

## Checklist

- [ ] `perform_batch_labeling()` calls the API
- [ ] `perform_batch_delete()` has confirmation dialog
- [ ] TODO comments removed
- [ ] Page loads without errors
- [ ] Operations update the UI after completion

---

## MEDIUM Priority Complete!

You've completed all 6 MEDIUM priority tutorials:

7. CI/CD pipeline with GitHub Actions
8. Train page with configuration form
9. Generate page with simulated data
10. Shared API contracts centralized
11. Test documentation and markers
12. Batch video operations implemented

Move on to LOW priority tutorials when ready, or begin collecting
real training data for a production Gate A run.
