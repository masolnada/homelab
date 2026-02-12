#!/usr/bin/env bash
set -euo pipefail

echo "This will remove ALL Docker containers, images, volumes, and networks."
read -rp "Are you sure? (y/N) " confirm
[[ "$confirm" =~ ^[Yy]$ ]] || exit 0

echo "Stopping all containers..."
docker stop $(docker ps -aq) 2>/dev/null || true

echo "Removing all containers..."
docker rm -f $(docker ps -aq) 2>/dev/null || true

echo "Removing all images..."
docker rmi -f $(docker images -aq) 2>/dev/null || true

echo "Removing all volumes..."
docker volume rm -f $(docker volume ls -q) 2>/dev/null || true

echo "Removing all networks (except default)..."
docker network rm $(docker network ls -q --filter type=custom) 2>/dev/null || true

echo "Running system prune..."
docker system prune -af --volumes

echo "Done. Docker is clean."
