# Web UI Landing Page - Implementation Summary

## Date: 2025-10-04

## Files Created

### 1. **landing_page.py** (`src/web_ui/landing_page.py`)
Main Streamlit application implementing the landing page with:

#### Features Implemented:
- ✅ **Element 1**: File uploader for existing videos
- ✅ **Element 2**: "Upload for Training" checkbox
- ✅ **Element 3**: "Upload Video" button
- ✅ **Element 4**: Text input for video generation prompts
- ✅ **Element 5**: "Generate Video" button
- ✅ **Element 6**: "Generate similar videos" button
- ✅ **Element 7**: "End Video Generation" button
- ✅ **Element 8**: Emotion type selector (6-class taxonomy)
- ✅ **Element 10**: "Incorrect" button to delete/reject videos
- ✅ Video player with placeholder when no video loaded
- ✅ Session state management for video queue
- ✅ Modern, minimalistic UI with custom CSS

#### Network Configuration:
- Ubuntu 1: `10.0.4.140` (Media Mover, LM Studio, storage)
- Ubuntu 2: `10.0.4.130` (Gateway API, Streamlit UI)
- Video storage: `videos/data_all` on Ubuntu 1

#### Emotion Taxonomy:
- neutral
- happy
- sad
- angry
- surprise
- fearful

### 2. **requirements.txt** (`src/web_ui/requirements.txt`)
Python dependencies:
- streamlit>=1.28.0
- requests>=2.31.0
- python-dotenv>=1.0.0

### 3. **README.md** (`src/web_ui/README.md`)
Documentation covering:
- Installation instructions
- Running the application
- Configuration options
- API integration points
- Privacy & security notes
- Next steps for full implementation

### 4. **endpoints.md** (`docs/endpoints.md`)
Comprehensive API documentation:
- Ubuntu 2 Gateway API endpoints
- Ubuntu 1 Media Mover API endpoints
- LM Studio API (OpenAI-compatible)
- Jetson WebSocket interface
- Error response formats
- Network configuration
- Authentication & idempotency
- Observability metrics

## Design Principles Applied

### 1. **Privacy-First Architecture**
- Local-first approach (no raw video transmission)
- Correlation IDs for request tracking
- Structured error handling
- Metadata-only API communication

### 2. **Modern UI/UX**
- Clean, minimalistic design
- Responsive layout using Streamlit columns
- Professional color scheme (#f8f9fa backgrounds, #1f1f1f text)
- Smooth button hover effects
- Emoji icons for visual clarity

### 3. **API Integration Ready**
- Placeholder endpoints for Gateway and Media Mover APIs
- Structured payloads matching schema requirements
- Error handling with user feedback
- Session state for workflow continuity

### 4. **Compliance with Requirements**
- Aligns with `requirements.md` v0.08.3.2
- Follows AGENTS.md orchestration policy
- Implements 6-class emotion taxonomy
- Supports train/test split promotion workflow

## TODO: Next Implementation Steps

### High Priority
1. **API Integration**
   - [ ] Connect to Gateway API (`POST /api/promote`)
   - [ ] Connect to Media Mover API (`POST /api/media/promote`)
   - [ ] Implement actual file upload to Ubuntu 1
   - [ ] Add authentication headers (JWT/Bearer)

2. **Video Generation**
   - [ ] Integrate with Luma/Runway/Flow API
   - [ ] Add prompt template support (Title, Goal, Scene, etc.)
   - [ ] Implement generation status polling
   - [ ] Handle synthetic video metadata logging

3. **Video Display**
   - [ ] Fetch videos from `/api/videos/list`
   - [ ] Display thumbnails from `/thumbs/{video_id}.jpg`
   - [ ] Stream videos from Ubuntu 1 Nginx
   - [ ] Add video metadata display (duration, fps, size)

### Medium Priority
4. **Database Integration**
   - [ ] Connect to PostgreSQL for metadata
   - [ ] Implement video labeling persistence
   - [ ] Add video history/queue display
   - [ ] Support relabeling workflow

5. **Real-time Updates**
   - [ ] WebSocket connection for Jetson events
   - [ ] Live classification results display
   - [ ] Real-time queue status updates

6. **Enhanced UX**
   - [ ] Add loading spinners
   - [ ] Implement toast notifications
   - [ ] Add keyboard shortcuts
   - [ ] Support batch operations

### Low Priority
7. **Advanced Features**
   - [ ] Video preview before upload
   - [ ] Drag-and-drop file upload
   - [ ] Export labeled dataset
   - [ ] Analytics dashboard
   - [ ] User preferences/settings

## Running the Application

```bash
# Install dependencies
cd src/web_ui
pip install -r requirements.txt

# Run Streamlit app
streamlit run landing_page.py

# Or specify custom port
streamlit run landing_page.py --server.port 8501
```

## Testing Checklist

- [ ] File upload functionality
- [ ] Video generation prompt submission
- [ ] Emotion classification workflow
- [ ] Video promotion to train/test splits
- [ ] Delete/reject video functionality
- [ ] Session state persistence
- [ ] Error handling and user feedback
- [ ] Responsive layout on different screen sizes
- [ ] API endpoint connectivity
- [ ] Authentication flow

## Notes

- All API calls currently use TODO placeholders
- Video storage paths assume Ubuntu 1 filesystem structure
- Authentication not yet implemented (requires JWT setup)
- WebSocket integration pending for real-time updates
- Thumbnail generation requires FFmpeg on Ubuntu 1

## Alignment with Project Requirements

✅ **FR-001**: Video generation & user classification interface  
✅ **FR-STOR-002**: Atomic promote workflow (UI ready)  
✅ **FR-STOR-003**: Thumbnail display support (pending API)  
✅ **Privacy-first**: No raw video transmission, local-first approach  
✅ **6-class taxonomy**: neutral, happy, sad, angry, surprise, fearful  
✅ **Modern UI**: Minimalistic design with Streamlit best practices
