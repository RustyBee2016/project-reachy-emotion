# Reachy Emotion Recognition - Web UI

## Landing Page (Streamlit)

Modern, minimalistic web interface for video generation, upload, and emotion labeling.

### Features

- **Video Upload**: Upload existing videos from local filesystem
- **Synthetic Generation**: Generate emotion videos using text prompts
- **Emotion Classification**: Label videos with 6-class emotion taxonomy
- **Video Promotion**: Move classified videos to train/test splits
- **Queue Management**: Track video generation status

### Installation

```bash
pip install -r requirements.txt
```

### Running the Application

```bash
streamlit run landing_page.py
```

Or specify custom port:

```bash
streamlit run landing_page.py --server.port 8501
```

### Configuration

Update the following constants in `landing_page.py`:

- `UBUNTU1_HOST`: Ubuntu 1 network address (default: 10.0.4.140)
- `UBUNTU2_HOST`: Ubuntu 2 network address (default: 10.0.4.130)
- `GATEWAY_URL`: FastAPI gateway endpoint
- `MEDIA_MOVER_URL`: Media mover API endpoint

### API Integration

The landing page integrates with:

1. **Gateway API (Ubuntu 2)**: Emotion events and promotion requests
2. **Media Mover API (Ubuntu 1)**: Video file operations
3. **Video Generation API**: Synthetic video creation (Luma/Runway/Flow)

### Emotion Taxonomy

Supported emotion classes:
- neutral
- happy
- sad
- angry
- surprise
- fearful

### Privacy & Security

- Local-first approach (no raw video transmission)
- Correlation IDs for request tracking
- Structured error handling
- Session state management

### Next Steps

1. Implement actual API calls (currently using TODO placeholders)
2. Add authentication (JWT/Bearer tokens)
3. Integrate WebSocket for real-time updates
4. Add thumbnail display from `/thumbs/`
5. Connect to PostgreSQL for metadata
