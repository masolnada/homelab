# Phase 1 — OPNsense Config Documentation

Reference for ER605 migration. Extracted from OPNsense config export.

---

## System

| Setting | Value |
|---|---|
| Hostname | thewall |
| Domain | home.lab |
| Timezone | Europe/Andorra |

---

## WAN

| Setting | Value |
|---|---|
| Interface | igb0 |
| Type | DHCP (dynamic IP from ISP) |

---

## VLANs & Interfaces

| VLAN ID | Name | Subnet | Gateway | DHCP Range |
|---|---|---|---|---|
| — | LAN (Management) | 192.168.1.0/24 | 192.168.1.1 | .100 – .200 |
| 30 | STAFF | 192.168.30.0/24 | 192.168.30.1 | .100 – .200 |
| 20 | IOT | 10.0.20.0/24 | 10.0.20.1 | .100 – .200 |
| 10 | EXTERNAL | 192.168.10.0/24 | 192.168.10.1 | .100 – .200 |

All VLANs are tagged on igb1 (LAN physical port).

---

## DHCP Static Leases

### Management (LAN — 192.168.1.x)

| Hostname | IP | MAC |
|---|---|---|
| switch-pis | 192.168.1.2 | d8:44:89:2b:10:0c |
| ap-pis | 192.168.1.3 | f0:09:0d:3a:60:68 |
| switch-baixos | 192.168.1.4 | 3c:64:cf:da:6c:69 |
| ap-baixos | 192.168.1.5 | ec:75:0c:18:a6:e2 |
| proxmox | 192.168.1.10 | f0:2f:74:c3:d2:f8 |
| omada-controller | 192.168.1.20 | bc:24:11:2c:47:ea |
| ajax-alarm | 192.168.1.50 | 9c:75:6e:12:8f:29 |
| nas | 192.168.1.71 | 74:d0:2b:90:95:54 |

### IOT (VLAN 20 — 10.0.20.x)

| Hostname | IP | MAC | Notes |
|---|---|---|---|
| zb-coord-pis | 10.0.20.5 | 30:83:98:16:68:f7 | |
| zb-coord-baixos | 10.0.20.6 | 20:43:a8:51:75:03 | |
| solar-energy-meter | 10.0.20.15 | 00:d0:93:50:a4:2c | |
| solar-inverter | 10.0.20.16 | fc:c2:3d:1c:d0:b4 | |
| gordi | 10.0.20.20 | bc:24:11:80:53:9e | |
| pis | 10.0.20.21 | bc:24:11:6b:3e:97 | |
| manscave | 10.0.20.22 | bc:24:11:e9:e6:69 | |
| persiana-marc-nord | 10.0.20.25 | — | no MAC |
| ring-intercom | 10.0.20.40 | 34:3e:a4:b1:df:b8 | |
| brother-printer | 10.0.20.172 | 00:80:92:8c:67:12 | Brother MFC-J5910DW |
| selphy-printer | 10.0.20.173 | 40:f8:df:eb:d8:fd | |

### STAFF (VLAN 30 — 192.168.30.x)

| Hostname | IP | MAC |
|---|---|---|
| pixel-9a | 192.168.30.220 | 5a:29:36:ff:51:6f |
| macmini | 192.168.30.221 | 1e:8f:ea:d9:4a:3c |

### EXTERNAL (VLAN 10 — 192.168.10.x)

| Hostname | IP | MAC |
|---|---|---|
| laia-laptop | 192.168.10.50 | 98:3b:8f:71:4c:ce |
| pixel-7a-laia | 192.168.10.51 | ea:e0:ad:7a:07:e6 |

---

## Firewall Rules

### LAN (Management)
| Action | Protocol | Source | Destination | Port | Notes |
|---|---|---|---|---|---|
| pass | any | LAN net | any | any | Default allow LAN → any (IPv4) |
| pass | any | LAN net | any | any | Default allow LAN → any (IPv6) |
| pass | tcp/udp | 192.168.1.10/32 | IOT net | 22 | Proxmox SSH → IoT |

### STAFF (VLAN 30)
| Action | Protocol | Source | Destination | Port | Notes |
|---|---|---|---|---|---|
| pass | any | STAFF net | printers alias | any | Allow STAFF → Printers |
| pass | tcp/udp | STAFF net | firewall | 53 | Allow STAFF → DNS |
| pass | any | STAFF net | internet | any | Allow STAFF → Internet |
| block | any | STAFF net | IOT, EXTERNAL | any | Block STAFF → other VLANs |

### IOT (VLAN 20)
| Action | Protocol | Source | Destination | Port | Notes |
|---|---|---|---|---|---|
| pass | tcp/udp | IOT net | firewall | 53 | Allow IoT → DNS |
| pass | any | IOT net | internet | any | Allow IoT → Internet |
| block | any | IOT net | LAN, STAFF, EXTERNAL | any | Block IoT → all VLANs |

**NAT redirect:** IoT DNS (port 53) is force-redirected to 10.0.20.1 (firewall Unbound) — prevents devices bypassing DNS.

### EXTERNAL (VLAN 10)
| Action | Protocol | Source | Destination | Port | Notes |
|---|---|---|---|---|---|
| pass | any | allowed_nas_devices | 192.168.1.70/32 | any | Laia Laptop → NAS |
| pass | any | EXTERNAL net | printers alias | any | Allow EXTERNAL → Printers |
| pass | tcp/udp | EXTERNAL net | firewall | 53 | Allow EXTERNAL → DNS |
| pass | any | EXTERNAL net | internet | any | Allow EXTERNAL → Internet |
| block | any | EXTERNAL net | LAN, STAFF, IOT | any | Block EXTERNAL → all VLANs |

---

## Aliases

| Name | Type | Values | Notes |
|---|---|---|---|
| staff_devices | host | 192.168.30.220, 192.168.30.221 | Admin hosts |
| allowed_nas_devices | host | 192.168.10.50 | Devices allowed to reach NAS from EXTERNAL |
| printers | host | 10.0.20.172, 10.0.20.173 | Printers in IoT network |
| printer_ports | port | 9100, 631, 515, 161, 54925, 54926 | Brother print + discovery ports |
| dopamine_sites | host | thepiratebay.org, nyaa.si, youtube.com, m.youtube.com, primevideo.com, subsplease.org | DNS block on STAFF + WAN |

---

## DNS (Unbound local hosts)

| Hostname | Domain | IP |
|---|---|---|
| pve | home.lab | 192.168.1.10 |
| nas | home.lab | 192.168.1.71 |
| gordi | home.lab | 10.0.20.20 |
| pis | home.lab | 10.0.20.21 |
| manscave | home.lab | 10.0.20.22 |
| zb-coord-pis | home.lab | 10.0.20.5 |
| zb-coord-baixos | home.lab | 10.0.20.6 |
| printer | home.lab | 10.0.20.172 |
| ollama | home.lab | 10.0.20.61 |
| n8n | home.lab | 10.0.20.60 |
| gateway | infra | 10.0.20.1 |
| smartphone | lan | 192.168.30.220 |
| macmini | lan | 192.168.30.221 |
| edpuzzle-macbook | lan | 192.168.30.222 |

---

## Notes for ER605 Migration

- **NAS IP discrepancy**: DHCP lease says `192.168.1.71`, DNS record says `192.168.1.71`, but the `allowed_nas_devices` alias points to `192.168.1.70/32` — verify which is correct before migrating.
- **Dopamine sites block**: OPNsense handles this via Unbound DNSBL. ER605/Omada doesn't have a direct equivalent — will need URL filtering or a Pi-hole/Adguard to replicate.
- **Force IoT DNS**: The NAT redirect rule (force port 53 to firewall) is not natively available on ER605. Replicate using Omada's DNS redirect feature or by setting IoT gateway DNS to the ER605's IOT interface IP only.
- **persiana-marc-nord**: No MAC address in the lease — cannot migrate as a static reservation without it.
- **WAN is DHCP**: No PPPoE credentials needed.
