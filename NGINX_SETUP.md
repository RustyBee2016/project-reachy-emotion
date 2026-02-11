# Nginx Setup for Reachy Project

## Current Status
- ✅ Nginx installed and running on port 80
- ✅ 13 worker processes active
- ❌ Not configured for Reachy project (serving default page)

## Configuration Steps

### 1. Copy the Reachy nginx configuration

```bash
sudo cp /home/rusty_admin/projects/reachy_08.4.2/nginx_reachy.conf /etc/nginx/sites-available/reachy
```

### 2. Create symbolic link to enable the site

```bash
sudo ln -sf /etc/nginx/sites-available/reachy /etc/nginx/sites-enabled/reachy
```

### 3. (Optional) Disable the default site

```bash
sudo rm /etc/nginx/sites-enabled/default
```

### 4. Test the configuration

```bash
sudo nginx -t
```

Should output:
```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

### 5. Reload nginx

```bash
sudo systemctl reload nginx
```

### 6. Verify it's working

```bash
# Test nginx health
curl http://localhost/nginx-health

# Test video directory listing
curl http://localhost/videos/temp/

# Test thumbnail access (if any exist)
curl -I http://localhost/thumbs/
```

## What This Configuration Does

### Video Files (`/videos/*`)
- **Path:** `http://10.0.4.140/videos/temp/`, `/videos/train/`, etc.
- **Serves from:** `/media/rusty_admin/project_data/reachy_emotion/videos/`
- **Features:**
  - Range requests enabled (for video streaming)
  - CORS headers for cross-origin access
  - Directory listing enabled (for debugging)
  - 1-hour cache

### Thumbnails (`/thumbs/*`)
- **Path:** `http://10.0.4.140/thumbs/video_id.jpg`
- **Serves from:** `/media/rusty_admin/project_data/reachy_emotion/videos/thumbs/`
- **Features:**
  - CORS headers
  - 7-day cache (thumbnails don't change)

### Health Check
- **Path:** `http://10.0.4.140/nginx-health`
- **Returns:** "nginx ok"

## Troubleshooting

### Permission Issues

If you get 403 Forbidden errors:

```bash
# Check directory permissions
ls -la /media/rusty_admin/project_data/reachy_emotion/videos/

# Ensure nginx user (www-data) can read the directories
sudo chmod 755 /media/rusty_admin/project_data/reachy_emotion/videos/
sudo chmod 755 /media/rusty_admin/project_data/reachy_emotion/videos/temp/
sudo chmod 755 /media/rusty_admin/project_data/reachy_emotion/videos/thumbs/

# Ensure nginx user can read the files
sudo chmod 644 /media/rusty_admin/project_data/reachy_emotion/videos/temp/*.mp4
```

### Check Nginx Error Logs

```bash
sudo tail -f /var/log/nginx/error.log
```

### Verify Nginx is Serving Files

```bash
# List videos via nginx
curl http://localhost/videos/temp/

# Get a specific video (first 100 bytes)
curl -r 0-99 http://localhost/videos/temp/some_video.mp4 | xxd | head
```

## Integration with Web App

The web app (`apps/web/landing_page.py`) is configured to use:

```python
MEDIA_MOVER_URL = "http://10.0.4.130:8083"  # Ubuntu 1 - API
# Videos served via nginx on Ubuntu 2 (this machine)
```

Videos are accessed via:
- **API metadata:** `http://10.0.4.130:8083/api/v1/media/list`
- **Video files:** `http://10.0.4.140/videos/temp/video.mp4` (nginx)
- **Thumbnails:** `http://10.0.4.140/thumbs/video_id.jpg` (nginx)

## Port Summary

- **Port 80** - Nginx (serving videos/thumbnails)
- **Port 8000** - Gateway API (FastAPI)
- **Port 8501** - Streamlit Web UI
- **Port 8083** - Media Mover API (on Ubuntu 1)
