#!/usr/bin/env bash
set -euo pipefail

# ── Docker ────────────────────────────────────────────────────────────
install_docker() {
  if command -v docker &>/dev/null; then
    echo "==> Docker already installed: $(docker --version)"
    return
  fi

  echo "==> Installing Docker via official convenience script..."
  curl -fsSL https://get.docker.com | sh

  echo "==> Adding users to docker group..."
  sudo usermod -aG docker "$USER"
  # When running as root (e.g. cloud-init), also add the first non-root user
  NORMAL_USER=$(getent passwd 1000 | cut -d: -f1)
  if [ -n "$NORMAL_USER" ] && [ "$NORMAL_USER" != "$USER" ]; then
    sudo usermod -aG docker "$NORMAL_USER"
  fi

  echo "==> Enabling and starting Docker service..."
  sudo systemctl enable --now docker

  echo "==> Docker installed: $(docker --version)"
}

# ── Tailscale ─────────────────────────────────────────────────────────
install_tailscale() {
  if command -v tailscale &>/dev/null; then
    echo "==> Tailscale already installed: $(tailscale version | head -1)"
    return
  fi

  echo "==> Installing Tailscale..."
  curl -fsSL https://tailscale.com/install.sh | sh

  echo "==> Enabling and starting Tailscale service..."
  sudo systemctl enable --now tailscaled

  echo "==> Tailscale installed: $(tailscale version | head -1)"
}

# ── Lazydocker ───────────────────────────────────────────────────────
install_lazydocker() {
  if command -v lazydocker &>/dev/null; then
    echo "==> Lazydocker already installed"
    return
  fi

  echo "==> Installing Lazydocker..."
  curl -fsSL https://raw.githubusercontent.com/jesseduffield/lazydocker/master/scripts/install_update_linux.sh | sudo bash

  echo "==> Lazydocker installed"
}

# ── Main ──────────────────────────────────────────────────────────────
echo "Homelab dependency installer"
echo "============================"
echo ""

install_docker
echo ""
install_tailscale
echo ""
install_lazydocker

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Log out and back in for docker group membership to take effect"
echo "  2. Run: tailscale up"
echo "  3. Run: ./init.sh"
