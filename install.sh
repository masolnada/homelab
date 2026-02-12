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

  echo "==> Adding current user to docker group..."
  sudo usermod -aG docker "$USER"

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

# ── Main ──────────────────────────────────────────────────────────────
echo "Homelab dependency installer"
echo "============================"
echo ""

install_docker
echo ""
install_tailscale

echo ""
echo "Installation complete!"
echo ""
echo "Next steps:"
echo "  1. Log out and back in for docker group membership to take effect"
echo "  2. Run: tailscale up"
echo "  3. Run: ./init.sh"
