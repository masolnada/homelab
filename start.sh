#!/usr/bin/env bash
set -euo pipefail

# Bring every stack up from the current checkout, without pulling git.
# For the normal deploy loop (pull, build missing app images, apply) use
# ./deploy.sh instead.

HOMELAB_DIR="$(cd "$(dirname "$0")" && pwd)"

exec "$HOMELAB_DIR/deploy.sh" --no-pull
