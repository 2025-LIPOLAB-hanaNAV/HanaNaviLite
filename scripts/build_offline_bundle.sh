#!/usr/bin/env bash
set -euo pipefail

# Build both images (app and ollama) and produce an offline bundle tar.gz

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$ROOT_DIR/dist"
IMAGES_DIR="$DIST_DIR/images"
TS="$(date +%Y%m%d_%H%M%S)"
BUNDLE_NAME="hananavilite_offline_bundle_${TS}.tar.gz"

APP_IMAGE="hananavilite-app:offline"
OLLAMA_IMAGE="hananavilite-ollama:offline"

OLLAMA_MODELS_DEFAULT="gemma3:12b-it-qat llama3.1:8b-instruct"
PREFETCH_EMBEDDING_DEFAULT=1

echo "[+] Checking docker..."
command -v docker >/dev/null 2>&1 || { echo "docker not found"; exit 1; }

mkdir -p "$IMAGES_DIR"

echo "[+] Building app image ($APP_IMAGE)"
docker build \
  --build-arg PREFETCH_EMBEDDING=${PREFETCH_EMBEDDING:-$PREFETCH_EMBEDDING_DEFAULT} \
  -t "$APP_IMAGE" \
  -f "$ROOT_DIR/Dockerfile" "$ROOT_DIR"

echo "[+] Building ollama image ($OLLAMA_IMAGE) with pre-pulled models: ${OLLAMA_MODELS:-$OLLAMA_MODELS_DEFAULT}"
docker build \
  --build-arg OLLAMA_MODELS="${OLLAMA_MODELS:-$OLLAMA_MODELS_DEFAULT}" \
  -t "$OLLAMA_IMAGE" \
  -f "$ROOT_DIR/Dockerfile.ollama" "$ROOT_DIR"

echo "[+] Saving images to $IMAGES_DIR"
docker save "$APP_IMAGE" | gzip > "$IMAGES_DIR/app_${TS}.tar.gz"
docker save "$OLLAMA_IMAGE" | gzip > "$IMAGES_DIR/ollama_${TS}.tar.gz"

echo "[+] Staging bundle files"
STAGE_DIR="$DIST_DIR/bundle_${TS}"
mkdir -p "$STAGE_DIR"
cp "$ROOT_DIR/docker-compose.offline.yml" "$STAGE_DIR/"
cp "$ROOT_DIR/README_OFFLINE.md" "$STAGE_DIR/" 2>/dev/null || true
cp -r "$IMAGES_DIR" "$STAGE_DIR/"

cat > "$STAGE_DIR/load_offline.sh" <<'LOAD'
#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
echo "[+] Loading images from ./images"
for f in "$DIR"/images/*.tar.gz; do
  echo "  - loading $f"
  gunzip -c "$f" | docker load
done
echo "[+] Done. Now start with: docker compose -f docker-compose.offline.yml up -d"
LOAD
chmod +x "$STAGE_DIR/load_offline.sh"

echo "[+] Creating bundle archive $BUNDLE_NAME"
tar -C "$STAGE_DIR/.." -czf "$DIST_DIR/$BUNDLE_NAME" "$(basename "$STAGE_DIR")"

echo "[+] Bundle ready: $DIST_DIR/$BUNDLE_NAME"

