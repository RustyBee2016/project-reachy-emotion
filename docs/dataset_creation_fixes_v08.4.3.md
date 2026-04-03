# Dataset Creation Fixes - v08.4.3

## Issues Identified from run_0100 Test

### Issue 1: Training Dataset Split (90/10)
**Problem:** Frame extraction created unwanted subdirectories:
- `/train/run/run_0100/train_ds_run_0100/` (107,199 images)
- `/train/run/run_0100/valid_ds_run_0100/` (11,911 images)

**Expected:** All 119,110 frames in single directory:
- `/train/run/run_0100/` (119,110 images)

**Root Cause:** The "Manual Execute Live" button triggered `split_run_dataset()` which created the 90/10 split subdirectories.

**Fix Applied:**
1. Marked `split_run` parameter as DEPRECATED in API schema
2. Updated web UI toggle to show "(DEPRECATED)" and recommend using dedicated AffectNet validation datasets
3. Split remains in code as opt-in fallback for testing, but disabled by default

**Calculation Verification:**
- 11,911 videos × 10 frames/video = 119,110 frames ✓
- Training: 107,199 / 119,110 = 90.0% ✓
- Validation: 11,911 / 119,110 = 10.0% ✓

---

### Issue 2: Validation Dataset Wrong Directory
**Problem:** Validation images stored in wrong location:
```
/videos/test/validation/happy/    (500 images)
/videos/test/validation/sad/      (500 images)
/videos/test/validation/neutral/  (500 images)
```

**Expected:** All validation images in run-scoped directory:
```
/videos/validation/run/run_0100/  (1,500 images, unlabeled filenames)
```

**Root Cause:** Legacy `create_affectnet_datasets.py` script was executed instead of the correct `ingest_affectnet.py validation-run` command. The legacy script copies to `/test/validation/<emotion>/`.

**Fix Applied:**
1. Corrected manifest path in API response from `_valid_ds_labeled.jsonl` to `_validation_labels.jsonl`
2. API endpoint correctly calls `validation-run` command which uses `_copy_images_to_validation()` method
3. This method copies to `/validation/run/<run_id>/` with unlabeled filenames

**Note:** The second validation dataset creation attempt was likely a manual retry after the first attempt was interrupted by system load.

---

## Correct Directory Structure

### Training Dataset (Luma Videos)
```
/videos/train/happy/           (3,589 videos)
/videos/train/sad/             (5,015 videos)
/videos/train/neutral/         (3,307 videos)
Total: 11,911 videos
```

### Training Frames (Extracted for run_XXXX)
```
/videos/train/run/run_XXXX/    (119,110 frames, all in one directory)
```

### Validation Dataset (AffectNet)
```
/videos/validation/run/run_XXXX/
  affectnet_00000.jpg          (unlabeled filenames)
  affectnet_00001.jpg
  ...
  affectnet_01499.jpg
Total: 1,500 images (500 per class)

Ground truth manifest:
/videos/manifests/run_XXXX_validation_labels.jsonl
```

### Test Dataset (AffectNet)
```
/videos/test/run_XXXX/
  affectnet_00000.jpg          (unlabeled filenames)
  affectnet_00001.jpg
  ...
  affectnet_00749.jpg
Total: 750 images (250 per class)

Ground truth manifest:
/videos/manifests/run_XXXX_test_labels.jsonl
```

---

## Correct Web UI Workflow

### Step 1: Create Datasets (Dataset Preparation Section)
1. Enter run_ID: `run_0300`
2. Click **📦 Create Both Datasets** (or create individually)
3. Wait for completion (~5-10 minutes)

**Result:**
- Validation: `/videos/validation/run/run_0300/` (1,500 images)
- Test: `/videos/test/run_0300/` (750 images)

### Step 2: Extract Training Frames (Manifest + Frame Extraction Section)
1. Enter same run_ID: `run_0300`
2. **Ensure "Split run into train_ds/valid_ds (DEPRECATED)" is OFF**
3. Click **Manual Execute Live**

**Result:**
- Training frames: `/videos/train/run/run_0300/` (119,110 images)

### Step 3: Train Model (ML Runs Section)
1. Enter same run_ID: `run_0300`
2. Click **🚀 Start Training**

**Training will use:**
- Training: `/videos/train/run/run_0300/` (119,110 frames from Luma videos)
- Validation: `/videos/validation/run/run_0300/` (1,500 AffectNet images) - auto-detected
- Test: `/videos/test/run_0300/` (750 AffectNet images) - for final evaluation

**No 90/10 split occurs** because dedicated validation dataset exists.

---

## Files Modified

### API Layer
- `apps/api/app/routers/ingest.py` - Marked `split_run` as DEPRECATED
- `apps/api/app/routers/dataset_control.py` - Fixed validation manifest path

### Web UI
- `apps/web/pages/03_Train.py` - Updated split_run toggle to show DEPRECATED warning

---

## Recommendations

### For Future Runs
1. **Always disable split_run toggle** in frame extraction section
2. **Use Dataset Preparation section** to create validation/test datasets
3. **Use same run_ID** across all three steps for consistency
4. **Verify directories** before training:
   ```bash
   ls -la /videos/train/run/run_XXXX/
   ls -la /videos/validation/run/run_XXXX/
   ls -la /videos/test/run_XXXX/
   ```

### Cleanup run_0100 (Optional)
```bash
# Remove incorrectly split training subdirectories
rm -rf /videos/train/run/run_0100/train_ds_run_0100/
rm -rf /videos/train/run/run_0100/valid_ds_run_0100/

# Move frames back to parent directory if needed
# (Only if frames were moved into subdirectories)

# Remove incorrectly placed validation images
rm -rf /videos/test/validation/
```

---

## Why Keep the Split Code?

**User's Question:** "Explain why you recommend keeping the split in the code. I suggest removing it entirely to avoid this issue in the future. Do you agree?"

**Answer:** **I agree with you - the split should be removed entirely.**

**Reasons to remove it:**
1. **You always create dedicated validation datasets** - No need for fallback
2. **It causes confusion** - As demonstrated by run_0100
3. **It wastes training data** - 10% of Luma videos unused
4. **Directory clutter** - Creates unnecessary subdirectories
5. **Maintenance burden** - Extra code to maintain and test

**My initial recommendation to keep it was wrong.** The split was designed as a fallback for quick testing when no validation dataset exists, but since you have a robust AffectNet validation dataset creation workflow, the fallback is unnecessary.

**However, I've kept it as DEPRECATED rather than removing it immediately because:**
1. **Backward compatibility** - Existing scripts/tests may reference it
2. **Gradual deprecation** - Gives time to verify no dependencies
3. **Easy to remove later** - Can be deleted in next version after confirming no issues

**If you want to remove it now, I can delete:**
- `split_run_dataset()` method in `prepare_dataset.py`
- All `split_run` parameters in API endpoints
- Split-related UI controls in web pages

Let me know if you'd like me to proceed with complete removal.
