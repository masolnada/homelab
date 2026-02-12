# 🏠 Homelab

Docker Compose homelab running behind Caddy (reverse proxy) and Tailscale (VPN). Backups and media are stored on TrueNAS via SMB/CIFS.

## 🏗️ Architecture

```mermaid
graph LR
    TS[Tailscale] --> Caddy

    subgraph VM["Proxmox VM"]
        subgraph proxy_net
            Caddy --> Vaultwarden
            Caddy --> Navidrome
            Vaultwarden -.- Backup[Backup Sidecar]
        end
    end

    subgraph NAS["TrueNAS (separate machine)"]
        backups["/backups (SMB)"]
        music["/music (SMB)"]
    end

    Backup -->|CIFS| backups
    Navidrome -->|CIFS read-only| music
```

- 🌐 **Gateway** — Caddy with Cloudflare DNS-01 TLS, exposed via Tailscale sidecar
- 🔐 **Security** — Vaultwarden with daily backup to TrueNAS
- 🎵 **Media** — Navidrome streaming from TrueNAS music share

## 📋 Prerequisites

- A Proxmox server
- A TrueNAS server with SMB shares configured
- A Cloudflare account managing your domain's DNS
- A Tailscale account

## 🖥️ VM Creation (from Proxmox host)

Run this from any machine with the repo cloned, via SSH to the Proxmox host:

```bash
ssh root@<proxmox-ip> 'bash -s' < create-vm.sh
```

Or with custom variables:

```bash
ssh root@<proxmox-ip> 'VMID=300 CORES=8 bash -s' < create-vm.sh
```

This downloads an Ubuntu 24.04 cloud image, creates the VM, and uses cloud-init to automatically install Docker, Tailscale, git, and cifs-utils, then clones the repo and runs `init.sh`.

Override defaults with environment variables:

| Variable | Default | Description |
|---|---|---|
| `VMID` | `200` | Proxmox VM ID |
| `VM_NAME` | `homelab` | VM name |
| `CORES` | `4` | CPU cores |
| `MEMORY` | `4096` | RAM in MB |
| `DISK_SIZE` | `32G` | Disk size |
| `STORAGE` | `local-lvm` | Proxmox storage pool |
| `BRIDGE` | `vmbr0` | Network bridge |
| `SSH_KEYS` | `~/.ssh/authorized_keys` | SSH public keys file |

```bash
# Example: custom VM ID with more resources
ssh root@<proxmox-ip> 'VMID=300 CORES=8 MEMORY=8192 bash -s' < create-vm.sh
```

## 🚀 Setup (inside the VM)

After the VM boots, SSH in and complete the remaining manual steps:

### 1. Authenticate Tailscale

```bash
tailscale up
```

### 2. Configure environment variables

Edit each stack's `.env` file in `/opt/homelab/` with your credentials:

**gateway/.env**

| Variable | Description |
|---|---|
| `DOMAIN` | Your base domain (e.g. `life.marcsolanadal.com`) |
| `CLOUDFLARE_API_TOKEN` | API token with DNS edit permissions for your zone |
| `TS_AUTHKEY` | Tailscale auth key (generate at Tailscale admin console > Settings > Keys) |

**security/.env**

| Variable | Description |
|---|---|
| `TZ` | Timezone (e.g. `Europe/Madrid`) |
| `VAULTWARDEN_ADMIN_TOKEN` | Admin panel token — generate with `openssl rand -base64 48` |
| `NAS_IP` | TrueNAS IP address |
| `NAS_BACKUP_SHARE` | SMB share name for backups |
| `NAS_BACKUP_USER` | NAS user for backup share |
| `NAS_BACKUP_PASSWORD` | NAS password for backup share |

**media/.env**

| Variable | Description |
|---|---|
| `TZ` | Timezone (e.g. `Europe/Madrid`) |
| `NAS_IP` | TrueNAS IP address |
| `NAS_MUSIC_SHARE` | SMB share name for music library |
| `NAS_MUSIC_USER` | NAS user for music share |
| `NAS_MUSIC_PASSWORD` | NAS password for music share |

### 3. DNS

A wildcard A record (`*.<DOMAIN>`) points directly to the server IP in Cloudflare. This avoids double-hopping through the Cloudflare proxy, which causes issues with Android clients. No per-service DNS changes needed — all subdomains resolve automatically.

### 4. Start the stacks

```bash
./start.sh
```

This starts gateway, security, and media in order.

### 5. ✅ Verify

```bash
# Check Caddy TLS certificates
docker compose -f gateway/docker-compose.yml logs caddy

# Check Tailscale connectivity
docker exec tailscale-gateway tailscale status

# Check all containers are running
docker ps
```

## 💾 TrueNAS Setup

Before starting the security and media stacks, make sure your TrueNAS server has:

1. **Two SMB shares** — one for Vaultwarden backups, one for the music library
2. **Dedicated users** — a backup user (read/write) and a music user (read-only)
3. **CIFS utils installed** on the VM: `sudo apt install cifs-utils`

## ➕ Adding a New Service

To expose a service running on a different Proxmox VM (e.g. `192.168.1.50:8080`), add a block to `gateway/Caddyfile`:

```
myapp.{$DOMAIN} {
    reverse_proxy 192.168.1.50:8080
    import cloudflare
}
```

Then reload Caddy:

```bash
docker exec caddy caddy reload --config /etc/caddy/Caddyfile
```

## 🔄 Backups

Vaultwarden is backed up daily at 03:00 AM to the TrueNAS SMB share. The backup sidecar:

- Pauses the Vaultwarden container during backup to prevent SQLite corruption
- Retains 30 days of backups with automatic rotation
- Stores backups as `vaultwarden-<timestamp>.tar.gz`

## 📁 File Structure

```
~/homelab/
├── create-vm.sh            # Creates and provisions the Proxmox VM
├── install.sh              # Installs Docker and Tailscale
├── init.sh                 # Creates network, dirs, and .env files
├── start.sh                # Starts all stacks in order
├── .env.template           # Master env template
├── gateway/
│   ├── docker-compose.yml  # Tailscale + Caddy
│   ├── Dockerfile          # Caddy with Cloudflare DNS plugin
│   ├── Caddyfile           # Reverse proxy config
│   └── .env
├── security/
│   ├── docker-compose.yml  # Vaultwarden + backup sidecar
│   └── .env
└── media/
    ├── docker-compose.yml  # Navidrome
    └── .env
```
