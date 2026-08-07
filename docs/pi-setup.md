# Raspberry Pi Setup: Camera Server + Backup Target

Target: Raspberry Pi 4 Model B running Raspberry Pi OS Bookworm.

---

## Prerequisites

Confirm the following before starting:

- Pi is booted and reachable over SSH on the local network
- External HDD is physically connected via USB
- Camera module is physically connected via ribbon cable
- You have `sudo` access
- You have access to the Tailscale admin console to approve the new device

---

## Phase 1 — Tailscale

### 1.1 Install Tailscale

```bash
curl -fsSL https://tailscale.com/install.sh | sh
```

### 1.2 Authenticate and join the tailnet

```bash
sudo tailscale up
```

A URL will be printed. Open it in a browser and authenticate with your Tailscale account. Approve the device in the admin console if device approval is enabled.

### 1.3 Confirm the Pi is on the tailnet

```bash
tailscale ip -4
tailscale status
```

Note the Tailscale IP (e.g. `100.x.x.x`) or the MagicDNS hostname (e.g. `pi.tail1234.ts.net`). You will use this for the camera stream URL and the TrueNAS SSH connection.

---

## Phase 2 — External HDD

### 2.1 Identify the drive

```bash
lsblk
```

Expected: an entry like `/dev/sda` with no mount point. Confirm it is the external HDD by checking its size. If multiple drives appear, use the one without an OS partition.

### 2.2 Inspect existing partitions

```bash
sudo fdisk -l /dev/sda
```

If the drive already has an ext4 partition you want to reuse, skip to step 2.5.

### 2.3 Create a new partition table

```bash
sudo fdisk /dev/sda
```

Inside fdisk, type these commands in order:
- `o` — create new DOS partition table (this wipes the disk)
- `n` — new partition
- `p` — primary
- `1` — partition number
- Enter — accept default first sector
- Enter — accept default last sector (uses full disk)
- `w` — write and exit

### 2.4 Format as ext4

```bash
sudo mkfs.ext4 -L backup /dev/sda1
```

### 2.5 Create the mount point

```bash
sudo mkdir -p /mnt/backup
```

### 2.6 Get the partition UUID

```bash
sudo blkid /dev/sda1
```

Note the `UUID="..."` value. You will use it in the next step.

### 2.7 Add to /etc/fstab

```bash
echo 'UUID=<uuid-from-step-2.6>  /mnt/backup  ext4  defaults,nofail  0  2' | sudo tee -a /etc/fstab
```

Replace `<uuid-from-step-2.6>` with the actual UUID. The `nofail` option prevents a boot failure if the drive is ever unplugged.

### 2.8 Mount and verify

```bash
sudo mount -a
df -h /mnt/backup
```

Expected: `/dev/sda1` listed with the correct size and mounted at `/mnt/backup`.

### 2.9 Verify mount survives reboot

```bash
sudo reboot
```

After reconnecting:

```bash
df -h /mnt/backup
```

Expected: drive is mounted automatically without any manual intervention.

---

## Phase 3 — go2rtc Camera Server

### 3.1 Verify the camera is detected

```bash
libcamera-vid --list-cameras
```

Expected: at least one camera listed (e.g. `imx219` for Camera Module v2, `imx708` for v3). If nothing shows, check the ribbon cable connection and run `sudo raspi-config` → Interface Options → Camera to enable it, then reboot.

### 3.2 Determine OS architecture

```bash
uname -m
```

- `aarch64` → 64-bit OS, use `go2rtc_linux_arm64`
- `armv7l` → 32-bit OS, use `go2rtc_linux_arm`

### 3.3 Download the go2rtc binary

For 64-bit OS (`aarch64`):

```bash
wget https://github.com/AlexxIT/go2rtc/releases/latest/download/go2rtc_linux_arm64 -O go2rtc
```

For 32-bit OS (`armv7l`):

```bash
wget https://github.com/AlexxIT/go2rtc/releases/latest/download/go2rtc_linux_arm -O go2rtc
```

Then install:

```bash
chmod +x go2rtc
sudo mv go2rtc /usr/local/bin/
go2rtc --version
```

### 3.4 Create the config

```bash
sudo mkdir -p /etc/go2rtc

sudo tee /etc/go2rtc/go2rtc.yaml <<'EOF'
streams:
  picam:
    - exec:libcamera-vid --inline --nopreview -t 0 --codec h264 --width 1280 --height 720 --framerate 30 -o -
EOF
```

### 3.5 Test manually

```bash
go2rtc -config /etc/go2rtc/go2rtc.yaml
```

Open `http://<pi-tailscale-ip>:1984` in a browser. Click on `picam`. You should see a live WebRTC stream with sub-second latency. Press `Ctrl+C` to stop once confirmed.

If the stream lags, reduce `--framerate` to `15` or `--width` to `640` and `--height` to `480` in the config.

### 3.6 Install as a systemd service (disabled by default)

```bash
sudo tee /etc/systemd/system/go2rtc.service <<'EOF'
[Unit]
Description=go2rtc camera server
After=network.target

[Service]
ExecStart=/usr/local/bin/go2rtc -config /etc/go2rtc/go2rtc.yaml
Restart=always
User=root

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
```

The service is intentionally **not enabled**. Start and stop it manually when the camera is needed:

```bash
sudo systemctl start go2rtc
sudo systemctl stop go2rtc
```

---

## Phase 4 — Rsync Backup Target

### 4.1 Create directories and a dedicated backup user

```bash
sudo mkdir -p /mnt/backup/data
sudo useradd -m -d /mnt/backup/home -s /bin/bash backup
sudo chown -R backup:backup /mnt/backup/home
sudo chown backup:backup /mnt/backup/data
```

### 4.2 Disable password login

```bash
sudo passwd -l backup
```

This forces SSH key-only authentication for the `backup` user.

### 4.3 Set up the SSH authorized_keys file

```bash
sudo mkdir -p /mnt/backup/home/.ssh
sudo chmod 700 /mnt/backup/home/.ssh
sudo touch /mnt/backup/home/.ssh/authorized_keys
sudo chmod 600 /mnt/backup/home/.ssh/authorized_keys
sudo chown -R backup:backup /mnt/backup/home/.ssh
```

### 4.4 Add TrueNAS's SSH public key

On TrueNAS, navigate to **Credentials → Backup Credentials → SSH Keypairs** and copy the public key for the keypair you will use for backups.

Then on the Pi:

```bash
echo "<truenas-public-key>" | sudo tee -a /mnt/backup/home/.ssh/authorized_keys
```

### 4.5 (Optional hardening) Restrict the user to rsync only

This prevents the `backup` user from ever opening a shell. First install `rrsync`:

```bash
sudo apt install -y rsync
find /usr -name rrsync 2>/dev/null
```

If the result is a `.gz` file, extract it:

```bash
sudo gunzip /usr/share/doc/rsync/scripts/rrsync.gz
sudo cp /usr/share/doc/rsync/scripts/rrsync /usr/local/bin/rrsync
sudo chmod +x /usr/local/bin/rrsync
```

Edit `/mnt/backup/home/.ssh/authorized_keys` and prepend the following to the key line (all on one line):

```
command="/usr/local/bin/rrsync /mnt/backup/data",no-port-forwarding,no-X11-forwarding,no-agent-forwarding,no-pty <truenas-public-key>
```

### 4.6 Verify SSH access from TrueNAS

From TrueNAS shell or any machine with the corresponding private key:

```bash
ssh backup@<pi-tailscale-ip>
```

Expected: connection accepted and immediately closed (if `rrsync` hardening is applied, this is correct — the shell is restricted). If hardening was skipped, you will get a bash prompt.

### 4.7 Test rsync end-to-end

From TrueNAS or a test machine:

```bash
rsync -avz --progress /path/to/test/file backup@<pi-tailscale-ip>:/mnt/backup/data/
```

Verify on the Pi:

```bash
ls /mnt/backup/data/
```

---

## Phase 5 — TrueNAS Rsync Task

### 5.1 Add the Pi as an SSH connection

1. Go to **Credentials → Backup Credentials → SSH Connections → Add**
2. Name: `pi-backup`
3. Host: Pi's Tailscale IP or MagicDNS hostname
4. Port: `22`
5. Username: `backup`
6. Private Key: select the keypair whose public key you added in Phase 4

Click **Verify** — it should return a success message.

### 5.2 Create a Rsync Task

1. Go to **Data Protection → Rsync Tasks → Add**
2. Path: dataset to back up (e.g. `/mnt/tank/important`)
3. Remote Host: Pi's Tailscale IP or MagicDNS hostname
4. Remote SSH Port: `22`
5. Remote Module/Path: `/mnt/backup/data`
6. Direction: Push
7. SSH Connection: `pi-backup`
8. Schedule: your preferred cron (e.g. daily at 02:00)
9. Enabled: checked

### 5.3 Run manually to verify

Click **Run Now** and watch the task log. Expected: completes with no errors and files appear under `/mnt/backup/data/` on the Pi.

---

## Quick Reference

| Task | Command |
|---|---|
| Start camera stream | `sudo systemctl start go2rtc` |
| Stop camera stream | `sudo systemctl stop go2rtc` |
| View camera stream | `http://<pi-tailscale-ip>:1984` |
| View go2rtc logs | `sudo journalctl -u go2rtc -f` |
| Check backup disk usage | `df -h /mnt/backup` |
| List backup files | `ls /mnt/backup/data/` |
| Check Tailscale status | `tailscale status` |
