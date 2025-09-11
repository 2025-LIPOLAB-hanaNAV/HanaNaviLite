#!/usr/bin/env bash
set -euo pipefail

if [ $# -lt 1 ]; then
  echo "Usage: $0 <bundle_tar_gz>"
  exit 1
fi

BUNDLE="$1"
if [ ! -f "$BUNDLE" ]; then
  echo "Bundle not found: $BUNDLE"
  exit 1
fi

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "[+] Extracting bundle to $WORKDIR"
tar -C "$WORKDIR" -xzf "$BUNDLE"

SUBDIR="$(find "$WORKDIR" -maxdepth 1 -mindepth 1 -type d | head -n1)"
if [ -z "$SUBDIR" ]; then
  echo "No bundle directory found in archive"
  exit 1
fi

echo "[+] Loading images"
for f in "$SUBDIR"/images/*.tar.gz; do
  echo "  - loading $f"
  gunzip -c "$f" | docker load
done

echo "[+] Copying compose and helper files to current directory"
cp "$SUBDIR"/docker-compose.offline.yml .
cp "$SUBDIR"/README_OFFLINE.md . 2>/dev/null || true
echo "[i] Start services with: docker compose -f docker-compose.offline.yml up -d"

