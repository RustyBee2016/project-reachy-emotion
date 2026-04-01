# Automatic Video Rename System Setup

**Project:** Reachy_Local_08.4.2  
**Date:** 2026-04-01  
**Purpose:** Automatically rename and move manually-generated videos when added to rename_prefix directories.

---

## Overview

This system automatically monitors the `rename_prefix` directories and triggers the renaming script whenever new video files are added.

### Monitored Directories
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/`
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/sad_rename/`
- `/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/neutral_rename/`

### Automatic Actions
When a video file (`.mp4`, `.avi`, `.mov`, `.mkv`, `.webm`) is added to any monitored directory:
1. **5-second delay** - Waits for file transfer to complete
2. **Triggers rename script** - Runs `rename_and_move_manual_videos.sh`
3. **Moves videos** - Renames and moves to `train/<emotion>/` directories
4. **Logs activity** - Records all actions to `/var/log/reachy_rename_watcher.log`

---

## Components

### 1. Rename Script: `scripts/rename_and_move_manual_videos.sh`
- Processes all three `*_rename` directories
- Extracts emotion from directory name
- Renames: `<emotion>_luma_YYYYMMDD_HHMMSS.mp4`
- **Moves** (not copies) videos to `train/<emotion>/`

### 2. Watcher Script: `scripts/watch_rename_prefix.sh`
- Uses `inotifywait` to monitor directories
- Detects CREATE and MOVED_TO events
- 10-second debounce to prevent rapid re-triggering
- Logs all activity

### 3. Systemd Service: `systemd/reachy-rename-watcher.service`
- Runs watcher script as background service
- Auto-starts on boot
- Auto-restarts on failure
- Logs to `/var/log/reachy_rename_watcher.log`

---

## Installation

### Step 1: Install inotify-tools

```bash
sudo apt-get update
sudo apt-get install inotify-tools
```

**Verify installation:**
```bash
which inotifywait
# Should output: /usr/bin/inotifywait
```

---

### Step 2: Create Log File

```bash
sudo touch /var/log/reachy_rename_watcher.log
sudo chown rusty_admin:rusty_admin /var/log/reachy_rename_watcher.log
sudo chmod 664 /var/log/reachy_rename_watcher.log
```

---

### Step 3: Install Systemd Service

```bash
cd /home/rusty_admin/projects/reachy_08.4.2

# Copy service file to systemd directory
sudo cp systemd/reachy-rename-watcher.service /etc/systemd/system/

# Reload systemd daemon
sudo systemctl daemon-reload

# Enable service (auto-start on boot)
sudo systemctl enable reachy-rename-watcher.service

# Start service
sudo systemctl start reachy-rename-watcher.service
```

---

### Step 4: Verify Service is Running

```bash
# Check service status
sudo systemctl status reachy-rename-watcher.service

# Should show:
# ● reachy-rename-watcher.service - Reachy Manual Video Rename Watcher
#    Loaded: loaded (/etc/systemd/system/reachy-rename-watcher.service; enabled)
#    Active: active (running) since ...
```

**Check logs:**
```bash
tail -f /var/log/reachy_rename_watcher.log
```

Expected output:
```
2026-04-01 08:30:00 - Starting rename_prefix watcher
Monitoring directories:
  - /media/.../rename_prefix/happy_rename/
  - /media/.../rename_prefix/sad_rename/
  - /media/.../rename_prefix/neutral_rename/

Setting up watches.
Watches established.
```

---

## Usage

### Automatic Mode (Recommended)

Simply copy or move video files to the appropriate `*_rename` directory:

```bash
# Copy videos to happy_rename directory
cp /path/to/my_videos/*.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/

# The watcher will automatically:
# 1. Detect the new files
# 2. Wait 5 seconds
# 3. Run rename script
# 4. Move videos to train/happy/ with proper naming
```

**Watch the logs in real-time:**
```bash
tail -f /var/log/reachy_rename_watcher.log
```

Expected log output:
```
2026-04-01 08:35:12 - Detected: CREATE video001.mp4 in .../happy_rename/
  Waiting 5 seconds for file transfer to complete...
  Triggering rename script...
============================================
Manual Video Rename and Move
============================================
Processing: happy (from happy_rename)
----------------------------------------
  Found 1 video files
  ✓ Moved: video001.mp4 → happy_luma_20260401_083517.mp4
  Summary for happy:
    Moved: 1
    Skipped: 0
    Destination: /media/.../videos/train/happy
  ✓ Rename script completed successfully
```

---

### Manual Mode (For Testing)

You can still run the rename script manually:

```bash
cd /home/rusty_admin/projects/reachy_08.4.2
./scripts/rename_and_move_manual_videos.sh
```

---

## Service Management

### Start Service
```bash
sudo systemctl start reachy-rename-watcher.service
```

### Stop Service
```bash
sudo systemctl stop reachy-rename-watcher.service
```

### Restart Service
```bash
sudo systemctl restart reachy-rename-watcher.service
```

### Check Status
```bash
sudo systemctl status reachy-rename-watcher.service
```

### View Logs
```bash
# Real-time logs
tail -f /var/log/reachy_rename_watcher.log

# Last 50 lines
tail -n 50 /var/log/reachy_rename_watcher.log

# Full log
cat /var/log/reachy_rename_watcher.log
```

### Disable Auto-Start
```bash
sudo systemctl disable reachy-rename-watcher.service
```

### Enable Auto-Start
```bash
sudo systemctl enable reachy-rename-watcher.service
```

---

## Troubleshooting

### Service Won't Start

**Check service status:**
```bash
sudo systemctl status reachy-rename-watcher.service
```

**Check for errors:**
```bash
sudo journalctl -u reachy-rename-watcher.service -n 50
```

**Common issues:**
1. **inotify-tools not installed**
   ```bash
   sudo apt-get install inotify-tools
   ```

2. **Directories don't exist**
   ```bash
   mkdir -p /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/{happy_rename,sad_rename,neutral_rename}
   ```

3. **Permission issues**
   ```bash
   sudo chown -R rusty_admin:rusty_admin /media/rusty_admin/project_data/reachy_emotion/videos/
   ```

---

### Watcher Not Detecting Files

**Test inotifywait manually:**
```bash
inotifywait -m -e create /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/
```

Then in another terminal:
```bash
touch /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/test.mp4
```

You should see:
```
/media/.../happy_rename/ CREATE test.mp4
```

---

### Rename Script Fails

**Run script manually to see errors:**
```bash
cd /home/rusty_admin/projects/reachy_08.4.2
./scripts/rename_and_move_manual_videos.sh
```

**Check script permissions:**
```bash
ls -l scripts/rename_and_move_manual_videos.sh
# Should show: -rwxr-xr-x (executable)
```

**Make executable if needed:**
```bash
chmod +x scripts/rename_and_move_manual_videos.sh
```

---

## Configuration

### Debounce Time

The watcher waits 10 seconds between script executions to prevent rapid re-triggering. To change this:

Edit `scripts/watch_rename_prefix.sh`:
```bash
DEBOUNCE_SECONDS=10  # Change to desired seconds
```

Then restart the service:
```bash
sudo systemctl restart reachy-rename-watcher.service
```

---

### File Transfer Delay

The watcher waits 5 seconds after detecting a file to ensure transfer is complete. To change this:

Edit `scripts/watch_rename_prefix.sh`:
```bash
sleep 5  # Change to desired seconds (line ~60)
```

Then restart the service:
```bash
sudo systemctl restart reachy-rename-watcher.service
```

---

## Verification

### Test the Complete System

1. **Ensure service is running:**
   ```bash
   sudo systemctl status reachy-rename-watcher.service
   ```

2. **Open log viewer in one terminal:**
   ```bash
   tail -f /var/log/reachy_rename_watcher.log
   ```

3. **Copy a test video in another terminal:**
   ```bash
   cp /path/to/test_video.mp4 /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/
   ```

4. **Watch the logs** - You should see:
   - File detection
   - 5-second wait
   - Rename script execution
   - Success message

5. **Verify the result:**
   ```bash
   ls -lh /media/rusty_admin/project_data/reachy_emotion/videos/train/happy/
   # Should show: happy_luma_YYYYMMDD_HHMMSS.mp4
   
   ls /media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix/happy_rename/
   # Should be empty (file was moved, not copied)
   ```

---

## Summary

### Previous Configuration (ingest_manual_videos.sh)
- ❌ Required manual invocation with parameters
- ❌ No automatic directory detection
- ❌ Wrong naming convention (`manual_*` instead of `*_luma_*`)
- ❌ Copied files instead of moving

### New Configuration (rename_and_move_manual_videos.sh + watcher)
- ✅ Automatic triggering when files are added
- ✅ Extracts emotion from directory name
- ✅ Correct naming: `<emotion>_luma_<timestamp>.mp4`
- ✅ Moves files (not copies)
- ✅ Processes all three emotion classes
- ✅ Background service with auto-restart
- ✅ Comprehensive logging

---

## Next Steps

After videos are automatically renamed and moved:

1. **Verify videos are in place:**
   ```bash
   find /media/rusty_admin/project_data/reachy_emotion/videos/train/{happy,sad,neutral} -name "*_luma_*.mp4" | wc -l
   ```

2. **Continue with dataset creation workflow:**
   - Step 2: Ingest AffectNet training images
   - Step 3: Create consolidated training dataset
   - Step 4: Create validation dataset
   - Step 5: Create test dataset

See `docs/DATASET_CREATION_WORKFLOW.md` for complete workflow.
