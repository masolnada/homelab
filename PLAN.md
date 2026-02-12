Architecting an Immutable, Modular Homelab Stack
Objective
Implement a production-grade homelab using Docker Compose on Linux. The architecture must be modular, highly secure, and utilize remote storage (TrueNAS) for both media and backups.

Core Architectural Specifications
1. Global Infrastructure
Networking: Use a single, pre-existing external bridge network named proxy_net.

Immutability: Every image must be pinned using its SHA-256 Digest (not just version tags) to ensure build consistency and security.

Reverse Proxy: Deploy a standalone Caddy instance.

Custom Build: Multi-stage Dockerfile using caddy:builder to include the caddy-dns/cloudflare plugin.

TLS Strategy: Use Cloudflare DNS-01 challenges for all SSL certificates to allow internal-only services without opening port 80/443 to the public internet.

2. Service: Vaultwarden (Security Stack)
Data Persistence: Persistent volume for vault data.

Integrated Backup: Implement a "Sidecar" backup strategy using offen/docker-volume-backup.

Schedule: Daily at 03:00 AM.

Retention: 30 days of local/remote rotation.

Integrity: Use the docker.sock label system to pause/stop the Vaultwarden container during the backup window to prevent SQLite database corruption.

Destination: Backup to a TrueNAS SMB/CIFS share mounted as a Docker volume.

3. Service: Navidrome (Media Stack)
Music Library: Point the music folder to a remote TrueNAS server.

Mounting Method: Use the Docker local volume driver with cifs options (SMB) defined directly in the Compose file.

Access: Read-only access to the music library.

Scan Schedule: Library refresh set to every 1 hour.

4. Secret Management & Permissions
Separation of Concerns: Each stack (Gateway, Security, Media) must exist in its own directory with its own docker-compose.yml.

Environment Variables: Use .env files for all sensitive credentials (API tokens, NAS passwords, IPs).

Least Privilege: Assume the use of service-specific NAS users rather than a global administrator.

Requested Deliverables
Directory Structure: A clear Linux tree structure for ~/homelab/.

Dockerfile: The multi-stage build for the Caddy/Cloudflare image.

Caddyfile: Configured for DNS-01 challenges and reverse proxying by container name.

Docker-Compose Files: Separate files for Gateway, Security, and Media.

Environment Template: A master .env template containing all required keys for the stack.

Initialization Script: A list of CLI commands to create the network, folder structure, and set correct file permissions (chmod 600 for .env).
