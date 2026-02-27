#!/usr/bin/env bash
set -euo pipefail

DIR="/media/rusty_admin/project_data/reachy_emotion/videos/train/happy"
PREFIX="happy_"

if [[ ! -d "$DIR" ]]; then
  echo "Directory not found: $DIR" >&2
  exit 1
fi

shopt -s nullglob
renamed=0
skipped=0
conflicts=0

for f in "$DIR"/*; do
  [[ -f "$f" ]] || continue
  case "${f,,}" in
    *.mp4|*.mov|*.avi|*.mkv|*.webm|*.m4v) ;;
    *) continue ;;
  esac
  base="$(basename "$f")"
  if [[ "$base" == "$PREFIX"* ]]; then
    skipped=$((skipped + 1))
    continue
  fi
  target="$DIR/$PREFIX$base"
  if [[ -e "$target" ]]; then
    echo "Conflict (target exists), skipping: $target" >&2
    conflicts=$((conflicts + 1))
    continue
  fi
  mv -- "$f" "$target"
  renamed=$((renamed + 1))
done

echo "happy rename complete: renamed=$renamed skipped_prefixed=$skipped conflicts=$conflicts"
