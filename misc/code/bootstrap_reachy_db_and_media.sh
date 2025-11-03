#!/usr/bin/env bash
set -euo pipefail

# --- CONFIG (edit as needed) ---------------------------------------------------
PGVER="${PGVER:-15}"
DB_NAME="${DB_NAME:-reachy_local}"
DB_OWNER="${DB_OWNER:-reachy_owner}"
APP_ROLE="${APP_ROLE:-reachy_app}"
READ_ROLE="${READ_ROLE:-reachy_read}"
DB_HOST="${DB_HOST:-/var/run/postgresql}"
DB_PORT="${DB_PORT:-5432}"

# Canonical filesystem root (Ubuntu 1) and public base for Nginx/Proxy
VIDEOS_ROOT="${VIDEOS_ROOT:-/media/rusty_admin/project_data/reachy_emotion/videos}"
BASE_MEDIA_URL="${BASE_MEDIA_URL:-/videos}"    # what the web/app will prefix for mp4s
BASE_THUMBS_URL="${BASE_THUMBS_URL:-/thumbs}"  # what the web/app will prefix for jpgs

# Nginx site path (Ubuntu 1 local static server for thumbs)
NGINX_SITE="${NGINX_SITE:-/etc/nginx/sites-available/reachy_media.conf}"
NGINX_LINK="${NGINX_LINK:-/etc/nginx/sites-enabled/reachy_media.conf}"
NGINX_PORT="${NGINX_PORT:-8082}"  # set to 80 in production

# --- PRE-FLIGHT ----------------------------------------------------------------
echo "==> Preflight: verifying directories under VIDEOS_ROOT=${VIDEOS_ROOT}"
for d in temp train test thumbs manifests; do
  mkdir -p "${VIDEOS_ROOT}/${d}"
done

# Ensure /videos is visible to apps even if VIDEOS_ROOT is elsewhere
if [ ! -e /videos ]; then
  echo "==> Creating symlink: /videos -> ${VIDEOS_ROOT}"
  sudo ln -s "${VIDEOS_ROOT}" /videos
fi

echo "==> Preflight: psql connectivity"
export PGHOST="$DB_HOST" PGPORT="$DB_PORT" PGUSER="${PGUSER:-postgres}"
psql -v ON_ERROR_STOP=1 -Atqc "SELECT 'ok'"

# --- ROLES & DB (idempotent) ---------------------------------------------------
echo "==> Creating roles and database (idempotent)"
psql <<SQL
DO 
		req$$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${DB_OWNER}') THEN
    EXECUTE format('CREATE ROLE %I LOGIN', '${DB_OWNER}');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${APP_ROLE}') THEN
    EXECUTE format('CREATE ROLE %I LOGIN', '${APP_ROLE}');
  END IF;
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '${READ_ROLE}') THEN
    EXECUTE format('CREATE ROLE %I LOGIN', '${READ_ROLE}');
  END IF;
END
		req$$;
SQL

# Create database using client-side conditional (CREATE DATABASE is not allowed inside DO)
psql <<SQL
SELECT format('CREATE DATABASE %I OWNER %I', '${DB_NAME}', '${DB_OWNER}')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}')\gexec
SQL

# --- EXTENSIONS, SCHEMA, TABLES ------------------------------------------------
echo "==> Creating schema/objects in ${DB_NAME}"
psql -d "$DB_NAME" <<SQL
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA IF NOT EXISTS media AUTHORIZATION ${DB_OWNER};

-- Core table (matches requirements)
CREATE TABLE IF NOT EXISTS media.video (
  video_id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  file_path    TEXT NOT NULL,   -- relative under videos/, e.g., videos/train/abc123.mp4
  split        TEXT NOT NULL CHECK (split IN ('temp','train','test')),
  label        TEXT,
  duration_sec NUMERIC,
  fps          NUMERIC,
  width        INT,
  height       INT,
  size_bytes   BIGINT,
  sha256       TEXT,
  zfs_snapshot TEXT,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT chk_file_path_format CHECK (
    file_path ~ '^videos/(temp|train|test)/[^/]+\.mp4$'
  )
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_video_sha ON media.video(sha256, size_bytes);
CREATE INDEX IF NOT EXISTS ix_video_split ON media.video(split);

-- Promotion audit log (append-only)
CREATE TABLE IF NOT EXISTS media.promotion_log (
  id             BIGSERIAL PRIMARY KEY,
  video_id       UUID NOT NULL,
  from_split     TEXT NOT NULL CHECK (from_split IN ('temp','train','test')),
  to_split       TEXT NOT NULL CHECK (to_split   IN ('temp','train','test')),
  label          TEXT,
  correlation_id TEXT,
  actor          TEXT DEFAULT current_user,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Config kv (for URLs, knobs)
CREATE TABLE IF NOT EXISTS media.config (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

-- Upsert base URLs so the view below can compute hrefs
INSERT INTO media.config(key, value) VALUES
  ('base_media_url',  '${BASE_MEDIA_URL}'),
  ('base_thumbs_url', '${BASE_THUMBS_URL}')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- Timestamps & path normalization
CREATE OR REPLACE FUNCTION media.touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = now(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_video_touch ON media.video;
CREATE TRIGGER trg_video_touch BEFORE UPDATE ON media.video
FOR EACH ROW EXECUTE FUNCTION media.touch_updated_at();

CREATE OR REPLACE FUNCTION media.normalize_path()
RETURNS TRIGGER AS $$
BEGIN
  -- force relative paths like 'videos/train/xyz.mp4'
  IF NEW.file_path ~* '^(?:/|\\)' THEN
    RAISE EXCEPTION 'file_path must be relative under videos/, got: %', NEW.file_path;
  END IF;
  IF position('videos/' IN NEW.file_path) <> 1 THEN
    NEW.file_path := 'videos/' || NEW.file_path;
  END IF;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_video_norm ON media.video;
CREATE TRIGGER trg_video_norm BEFORE INSERT OR UPDATE ON media.video
FOR EACH ROW EXECUTE FUNCTION media.normalize_path();

-- URL view: derive public URLs without storing them (thumbs without split)
CREATE OR REPLACE VIEW media.v_video_urls AS
SELECT
  v.video_id,
  v.split,
  v.label,
  v.file_path,
  (SELECT value FROM media.config WHERE key='base_media_url')
    || '/' || regexp_replace(v.file_path, '^videos/', '') AS video_url,
  (SELECT value FROM media.config WHERE key='base_thumbs_url')
    || '/' || regexp_replace(v.file_path, '.*/|\\.mp4$','') || '.jpg' AS thumb_url,
  v.size_bytes, v.sha256, v.created_at, v.updated_at
FROM media.video v;

-- Grants
GRANT USAGE ON SCHEMA media TO ${APP_ROLE}, ${READ_ROLE};
GRANT SELECT, INSERT, UPDATE, DELETE ON media.video TO ${APP_ROLE};
GRANT INSERT ON media.promotion_log TO ${APP_ROLE};
GRANT SELECT ON media.video, media.promotion_log, media.v_video_urls TO ${READ_ROLE};
GRANT SELECT, UPDATE ON media.config TO ${APP_ROLE};
SQL

# --- NGINX (thumbs/static) -----------------------------------------------------
echo "==> Writing nginx static site for /thumbs and /videos (read-only) on port ${NGINX_PORT}"
sudo tee "$NGINX_SITE" >/dev/null <<NGINX
# Reachy media (Ubuntu 1) — serves static thumbnails & optional video files
server {
  listen ${NGINX_PORT};
  server_name _;

  # Thumbnails
  location /thumbs/ {
    alias ${VIDEOS_ROOT}/thumbs/;
    autoindex off;
    add_header Cache-Control "public, max-age=3600";
    types { image/jpeg jpg; }
  }

  # (Optional) expose read-only raw videos inside LAN
  location /videos/ {
    alias ${VIDEOS_ROOT}/;
    autoindex off;
    add_header Cache-Control "public, max-age=60";
    types { video/mp4 mp4; }
    limit_rate_after 1m;
  }
}
NGINX

sudo ln -sf "$NGINX_SITE" "$NGINX_LINK"
sudo nginx -t && sudo systemctl reload nginx || {
  echo "!! nginx config test failed; leaving DB objects in place" >&2; exit 1;
}

# --- DONE ----------------------------------------------------------------------
echo "==> Complete. Notes:"
echo " DB:     ${DB_NAME} on ${DB_HOST}:${DB_PORT}"
echo " Roles:  owner=${DB_OWNER} app=${APP_ROLE} read=${READ_ROLE}"
echo " FS:     ${VIDEOS_ROOT}/{temp,train,test,thumbs,manifests} (symlink at /videos)"
echo " URLs:   media=${BASE_MEDIA_URL}  thumbs=${BASE_THUMBS_URL} (used by media.v_video_urls)"
echo " Nginx:  http://ubuntu1:${NGINX_PORT}/thumbs/…  and  /videos/…"
