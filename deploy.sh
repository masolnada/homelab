#!/usr/bin/env bash
set -euo pipefail

# Reconcile the running homelab with this git checkout.
#
#   1. pull the homelab repo (unless --no-pull)
#   2. build any app image referenced by a stack but missing from the local
#      registry, from the app's own git repo at that tag
#   3. docker compose up -d every stack
#
# Nothing outside the network ever pushes here: the VM pulls both code and
# sources, builds locally, and stores images in the local zot registry.
#
# Usage:
#   ./deploy.sh                 # pull, build what's missing, apply all stacks
#   ./deploy.sh --no-pull       # apply the current checkout as-is
#   ./deploy.sh automation      # only the given stacks (still builds for them)

HOMELAB_DIR="$(cd "$(dirname "$0")" && pwd)"
REGISTRY="localhost:5000"
APPS_CONF="$HOMELAB_DIR/registry/apps.conf"
BUILD_CACHE="/var/tmp/homelab-build"

ALL_STACKS=(registry gateway security media contacts notes agent cpa automation dashboard)

PULL=1
STACKS=()
for arg in "$@"; do
  case "$arg" in
    --no-pull) PULL=0 ;;
    -*) echo "unknown option: $arg" >&2; exit 2 ;;
    *) STACKS+=("$arg") ;;
  esac
done
[ ${#STACKS[@]} -eq 0 ] && STACKS=("${ALL_STACKS[@]}")

log() { echo "==> $*"; }

# ── 1. Sync the desired state ─────────────────────────────────────────
if [ "$PULL" -eq 1 ]; then
  log "Pulling homelab repo..."
  git -C "$HOMELAB_DIR" pull --ff-only
fi

# ── 2. Build missing app images ───────────────────────────────────────
# Every image reference of the form localhost:5000/<name>:<tag> found in the
# selected compose files is a build request. The tag is a git ref in the app
# repo listed in registry/apps.conf. An image already in the registry is never
# rebuilt, so this is a no-op on every run but the first after a version bump.

app_repo() {
  awk -v name="$1" '$1 == name { print $2; exit }' "$APPS_CONF"
}

image_exists() {
  curl -sfo /dev/null "http://$REGISTRY/v2/$1/manifests/$2" \
    -H 'Accept: application/vnd.oci.image.manifest.v1+json' \
    -H 'Accept: application/vnd.docker.distribution.manifest.v2+json'
}

build_app() {
  local name="$1" ref="$2" repo src
  repo="$(app_repo "$name")"
  if [ -z "$repo" ]; then
    echo "no git url for '$name' in registry/apps.conf" >&2
    exit 1
  fi

  src="$BUILD_CACHE/$name"
  if [ -d "$src/.git" ]; then
    git -C "$src" fetch --tags --prune --force origin
  else
    mkdir -p "$BUILD_CACHE"
    git clone "$repo" "$src"
  fi

  if ! git -C "$src" rev-parse --verify --quiet "$ref^{commit}" >/dev/null; then
    echo "$name: no such git ref '$ref' in $repo" >&2
    exit 1
  fi
  git -C "$src" checkout --detach --force "$ref"
  git -C "$src" clean -fdx

  log "Building $name:$ref"
  docker build -t "$REGISTRY/$name:$ref" "$src"
  docker push "$REGISTRY/$name:$ref"
}

required_images() {
  local stack
  for stack in "${STACKS[@]}"; do
    [ -f "$HOMELAB_DIR/$stack/docker-compose.yml" ] || continue
    grep -oE "image:[[:space:]]*$REGISTRY/[^[:space:]]+" \
      "$HOMELAB_DIR/$stack/docker-compose.yml" || true
  done | awk '{ print $2 }' | sed "s|^$REGISTRY/||" | sort -u
}

mapfile -t WANTED < <(required_images)

if [ ${#WANTED[@]} -gt 0 ]; then
  if ! curl -sfo /dev/null "http://$REGISTRY/v2/"; then
    log "Starting registry (needed to build app images)..."
    docker compose -f "$HOMELAB_DIR/registry/docker-compose.yml" up -d
    until curl -sfo /dev/null "http://$REGISTRY/v2/"; do sleep 1; done
  fi

  for image in "${WANTED[@]}"; do
    name="${image%:*}"
    ref="${image##*:}"
    if image_exists "$name" "$ref"; then
      log "$name:$ref already in registry"
    else
      build_app "$name" "$ref"
    fi
  done
fi

# ── 3. Apply ──────────────────────────────────────────────────────────
for stack in "${STACKS[@]}"; do
  if [ ! -f "$HOMELAB_DIR/$stack/docker-compose.yml" ]; then
    echo "no such stack: $stack" >&2
    exit 1
  fi
  log "Applying $stack..."
  docker compose -f "$HOMELAB_DIR/$stack/docker-compose.yml" up -d --remove-orphans
done

log "Deploy complete."
