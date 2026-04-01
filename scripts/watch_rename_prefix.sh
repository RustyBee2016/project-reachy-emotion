#!/bin/bash
# Watch rename_prefix directories and automatically trigger renaming script
# when new video files are added
#
# This script uses inotifywait to monitor:
#   /videos/train/rename_prefix/happy_rename/
#   /videos/train/rename_prefix/sad_rename/
#   /videos/train/rename_prefix/neutral_rename/
#
# When a video file is added (CREATE or MOVED_TO event), it triggers
# the rename_and_move_manual_videos.sh script after a 5-second delay
# to allow for file transfer completion.

set -e

RENAME_PREFIX_DIR="/media/rusty_admin/project_data/reachy_emotion/videos/train/rename_prefix"
SCRIPT_DIR="/home/rusty_admin/projects/reachy_08.4.2/scripts"
RENAME_SCRIPT="$SCRIPT_DIR/rename_and_move_manual_videos.sh"
LOGFILE="/var/log/reachy_rename_watcher.log"

# Check if inotify-tools is installed
if ! command -v inotifywait &> /dev/null; then
    echo "Error: inotify-tools not installed"
    echo "Install with: sudo apt-get install inotify-tools"
    exit 1
fi

# Check if rename_prefix directory exists
if [ ! -d "$RENAME_PREFIX_DIR" ]; then
    echo "Error: rename_prefix directory not found: $RENAME_PREFIX_DIR"
    exit 1
fi

# Create log file if it doesn't exist
sudo touch "$LOGFILE" 2>/dev/null || LOGFILE="/tmp/reachy_rename_watcher.log"
sudo chmod 666 "$LOGFILE" 2>/dev/null || true

echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting rename_prefix watcher" | tee -a "$LOGFILE"
echo "Monitoring directories:" | tee -a "$LOGFILE"
echo "  - $RENAME_PREFIX_DIR/happy_rename/" | tee -a "$LOGFILE"
echo "  - $RENAME_PREFIX_DIR/sad_rename/" | tee -a "$LOGFILE"
echo "  - $RENAME_PREFIX_DIR/neutral_rename/" | tee -a "$LOGFILE"
echo "" | tee -a "$LOGFILE"

# Track last execution time to prevent rapid re-triggering
LAST_EXECUTION=0
DEBOUNCE_SECONDS=10

# Monitor all three directories for video file additions
inotifywait -m -r -e create -e moved_to \
    --include '\.(mp4|avi|mov|mkv|webm)$' \
    "$RENAME_PREFIX_DIR/happy_rename" \
    "$RENAME_PREFIX_DIR/sad_rename" \
    "$RENAME_PREFIX_DIR/neutral_rename" \
    2>&1 | grep -v "^Setting up watches" | grep -v "^Watches established" | while read -r directory event filename; do
    
    CURRENT_TIME=$(date +%s)
    TIME_SINCE_LAST=$((CURRENT_TIME - LAST_EXECUTION))
    
    echo "$(date '+%Y-%m-%d %H:%M:%S') - Detected: $event $filename in $directory" | tee -a "$LOGFILE"
    
    # Debounce: only trigger if enough time has passed since last execution
    if [ $TIME_SINCE_LAST -lt $DEBOUNCE_SECONDS ]; then
        echo "  Debouncing... (${TIME_SINCE_LAST}s since last run, waiting ${DEBOUNCE_SECONDS}s)" | tee -a "$LOGFILE"
        continue
    fi
    
    # Wait 5 seconds to ensure file transfer is complete
    echo "  Waiting 5 seconds for file transfer to complete..." | tee -a "$LOGFILE"
    sleep 5
    
    # Execute rename script
    echo "  Triggering rename script..." | tee -a "$LOGFILE"
    if bash "$RENAME_SCRIPT" >> "$LOGFILE" 2>&1; then
        echo "  ✓ Rename script completed successfully" | tee -a "$LOGFILE"
        LAST_EXECUTION=$(date +%s)
    else
        echo "  ✗ Rename script failed (see log for details)" | tee -a "$LOGFILE"
    fi
    
    echo "" | tee -a "$LOGFILE"
done
