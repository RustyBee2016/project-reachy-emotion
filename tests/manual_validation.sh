#!/bin/bash
# Manual validation script for metadata persistence
# Run this after classifying videos through the UI

set -e

echo "================================================"
echo "Metadata Persistence Validation Script"
echo "================================================"
echo ""

# Configuration
DB_USER="${DB_USER:-reachy_app}"
DB_NAME="${DB_NAME:-reachy_local}"
VIDEOS_ROOT="${VIDEOS_ROOT:-/media/rusty_admin/project_data/reachy_emotion/videos}"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "1️⃣  Checking FastAPI service status..."
if curl -s http://localhost:8083/health > /dev/null 2>&1; then
    echo -e "${GREEN}✅ FastAPI service is running on port 8083${NC}"
else
    echo -e "${RED}❌ FastAPI service is NOT running${NC}"
    echo "   Start it with: ./start_media_api.sh"
    exit 1
fi

echo ""
echo "2️⃣  Checking PostgreSQL connection..."
if psql -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✅ PostgreSQL is accessible${NC}"
else
    echo -e "${RED}❌ Cannot connect to PostgreSQL${NC}"
    echo "   Check connection: psql -U $DB_USER -d $DB_NAME"
    exit 1
fi

echo ""
echo "3️⃣  Checking video directories..."
for split in temp train test; do
    dir="$VIDEOS_ROOT/$split"
    if [ -d "$dir" ]; then
        count=$(find "$dir" -type f -name "*.mp4" 2>/dev/null | wc -l)
        echo -e "${GREEN}✅ $split/: $count videos${NC}"
    else
        echo -e "${YELLOW}⚠️  $split/ directory not found${NC}"
    fi
done

echo ""
echo "4️⃣  Querying database for recent videos..."
echo "   Recent videos in train:"
psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT
    video_id::text AS id,
    split,
    label,
    size_bytes,
    created_at
FROM video
WHERE split = 'train'
ORDER BY created_at DESC
LIMIT 5;
" 2>/dev/null || echo -e "${RED}❌ Query failed${NC}"

echo ""
echo "5️⃣  Checking promotion logs..."
echo "   Recent promotions:"
psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    promotion_id,
    video_id::text AS video,
    from_split,
    to_split,
    intended_label,
    actor,
    success,
    created_at
FROM promotion_log
ORDER BY created_at DESC
LIMIT 5;
" 2>/dev/null || echo -e "${RED}❌ Query failed${NC}"

echo ""
echo "6️⃣  Emotion label distribution..."
psql -U "$DB_USER" -d "$DB_NAME" -c "
SELECT 
    label,
    COUNT(*) as count
FROM video
WHERE split = 'train' AND label IS NOT NULL
GROUP BY label
ORDER BY count DESC;
" 2>/dev/null || echo -e "${RED}❌ Query failed${NC}"

echo ""
echo "7️⃣  Filesystem vs Database consistency check..."
# Count files in train (all label subdirectories)
fs_count=$(find "$VIDEOS_ROOT/train" -type f -name "*.mp4" 2>/dev/null | wc -l)
db_count=$(psql -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT COUNT(*) FROM video WHERE split = 'train';" 2>/dev/null | xargs)

echo "   Filesystem: $fs_count videos"
echo "   Database:   $db_count records"

if [ "$fs_count" -eq "$db_count" ]; then
    echo -e "${GREEN}✅ Counts match!${NC}"
else
    echo -e "${YELLOW}⚠️  Mismatch detected - may need reconciliation${NC}"
fi

echo ""
echo "================================================"
echo "Validation Complete!"
echo "================================================"
echo ""
echo "Next steps:"
echo "1. Generate a video in the UI"
echo "2. Classify it with an emotion"
echo "3. Run this script again to verify persistence"
echo ""
echo "To query specific video:"
echo "  psql -U $DB_USER -d $DB_NAME -c \"SELECT * FROM video WHERE video_id = '<uuid>';\""
echo ""
