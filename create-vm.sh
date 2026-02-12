#!/usr/bin/env bash
set -euo pipefail

# ── Configuration ─────────────────────────────────────────────────────
VMID=${VMID:-200}
VM_NAME=${VM_NAME:-homelab}
CORES=${CORES:-2}
MEMORY=${MEMORY:-2048}
DISK_SIZE=${DISK_SIZE:-32G}
STORAGE=${STORAGE:-local-lvm}
BRIDGE=${BRIDGE:-vmbr0}
SSH_KEYS=${SSH_KEYS:-~/.ssh/authorized_keys}
CLOUD_IMAGE_URL="https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img"
CLOUD_IMAGE="/var/lib/vz/template/iso/ubuntu-24.04-cloudimg-amd64.img"
REPO_URL=${REPO_URL:-https://github.com/masolnada/homelab.git}

# ── Download cloud image ──────────────────────────────────────────────
if [ ! -f "$CLOUD_IMAGE" ]; then
  echo "==> Downloading Ubuntu 24.04 cloud image..."
  wget -O "$CLOUD_IMAGE" "$CLOUD_IMAGE_URL"
else
  echo "==> Cloud image already exists, skipping download"
fi

# ── Create VM ─────────────────────────────────────────────────────────
echo "==> Creating VM $VMID ($VM_NAME)..."
qm create "$VMID" \
  --name "$VM_NAME" \
  --ostype l26 \
  --cores "$CORES" \
  --memory "$MEMORY" \
  --net0 "virtio,bridge=$BRIDGE" \
  --agent enabled=1 \
  --scsihw virtio-scsi-single

# ── Disk setup ────────────────────────────────────────────────────────
echo "==> Importing cloud image as disk..."
qm set "$VMID" --scsi0 "$STORAGE:0,import-from=$CLOUD_IMAGE"
qm disk resize "$VMID" scsi0 "$DISK_SIZE"

# ── Cloud-init ────────────────────────────────────────────────────────
echo "==> Configuring cloud-init..."
qm set "$VMID" --ide2 "$STORAGE:cloudinit"
qm set "$VMID" --boot order=scsi0
qm set "$VMID" --serial0 socket --vga serial0
qm set "$VMID" --ipconfig0 ip=dhcp

if [ -f "$SSH_KEYS" ]; then
  qm set "$VMID" --sshkeys "$SSH_KEYS"
  echo "    SSH keys loaded from $SSH_KEYS"
else
  echo "    ⚠️  No SSH keys found at $SSH_KEYS — you may need to set a password"
fi

# ── Cloud-init user data (post-boot provisioning) ─────────────────────
SNIPPET_DIR="/var/lib/vz/snippets"
SNIPPET_FILE="$SNIPPET_DIR/homelab-cloud-init.yml"
mkdir -p "$SNIPPET_DIR"

cat > "$SNIPPET_FILE" <<EOF
#cloud-config
package_update: true
packages:
  - git
  - cifs-utils

runcmd:
  - git clone $REPO_URL /opt/homelab
  - chmod +x /opt/homelab/install.sh /opt/homelab/init.sh /opt/homelab/start.sh
  - /opt/homelab/install.sh
  - /opt/homelab/init.sh
EOF

qm set "$VMID" --cicustom "vendor=local:snippets/homelab-cloud-init.yml"

# ── Start VM ──────────────────────────────────────────────────────────
echo "==> Starting VM $VMID..."
qm start "$VMID"

echo ""
echo "✅ VM $VMID ($VM_NAME) created and starting!"
echo ""
echo "Cloud-init will automatically:"
echo "  1. Install git and cifs-utils"
echo "  2. Clone the homelab repo to /opt/homelab"
echo "  3. Run install.sh (Docker + Tailscale)"
echo "  4. Run init.sh (Docker network + .env files)"
echo ""
echo "Next steps after VM boots:"
echo "  1. SSH into the VM: ssh ubuntu@<vm-ip>"
echo "  2. Authenticate Tailscale: tailscale up"
echo "  3. Configure .env files in /opt/homelab/*/  "
echo "  4. Start the stacks: /opt/homelab/start.sh"
