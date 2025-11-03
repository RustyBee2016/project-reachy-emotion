# /etc/nginx/sites-available/reachy_https.conf
server {
    listen 443 ssl http2;
    server_name 10.0.4.130 AORUSAI;

    ssl_certificate     /etc/ssl/localcerts/reachy.crt;
    ssl_certificate_key /etc/ssl/localcerts/reachy.key;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # (Optional) HSTS for strict HTTPS in browsers:
    # add_header Strict-Transport-Security "max-age=31536000" always;

    # Static media (adjust to your actual aliases)
    location /videos/ { alias /media/rusty_admin/project_data/reachy_emotion/videos/; autoindex off; }
    location /thumbs/ { alias /media/rusty_admin/project_data/reachy_emotion/thumbs/;  autoindex off; }

    # FastAPI Media Mover (leave your upstream HTTP on localhost)
    location /api/media/ {
        proxy_pass         http://127.0.0.1:8000/;   # or whatever Uvicorn is bound to
        proxy_set_header   Host              $host;
        proxy_set_header   X-Real-IP         $remote_addr;
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto https;
    }
}

# (Optional) redirect 80→443
server {
    listen 80;
    server_name 10.0.4.130 AORUSAI;
    return 301 https://$host$request_uri;
}
