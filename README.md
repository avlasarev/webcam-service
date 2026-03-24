# webcam-service — homelab stack

A self-hosted surveillance, media, and AI service running on Ubuntu with Docker Compose, exposed via WireGuard VPN. Started as a single webcam container experiment and evolved into a multi-service homelab.

---

## What this is

A homelab stack covering containerisation, reverse proxying, network isolation, VPN access, and local AI inference. 

---

## Architecture

```
Internet (encrypted)
    │
    └── WireGuard VPN (UDP 51820) ── authenticated peers only
            │
            └── Ubuntu server (192.168.1.12)
                    │
                    └── Docker Compose — private_lan network
                            │
                            ├── NGINX (gateway, port 80) ── only public entry point
                            │       ├── /stream    → webcam_service:8000
                            │       ├── /music     → navidrome:4533
                            │       ├── /ollama    → ollama:11434
                            │       └── /health    → webcam_service:8000
                            │
                            ├── webcam_service  172.18.0.10  FastAPI MJPEG stream
                            ├── navidrome       172.18.0.11  Subsonic music server
                            ├── nginx_gateway   172.18.0.20  Reverse proxy
                            ├── wireguard       172.18.0.21  VPN gateway
                            ├── ollama          172.18.0.30  LLM inference engine
                            └── hollama         172.18.0.31  AI chat interface (port 4173)
```

All services use static Docker IPs. No service other than NGINX has an exposed port on the host. The webcam service and Navidrome are completely invisible to the host network — they only exist inside the Docker private LAN.

---

## Services

| Service | Purpose | Internal address | External access |
|---------|---------|-----------------|-----------------|
| webcam_service | MJPEG live stream via FastAPI | 172.18.0.10:8000 | /stream via NGINX |
| navidrome | Self-hosted music server (Subsonic API) | 172.18.0.11:4533 | /music via NGINX |
| nginx_gateway | Reverse proxy and sole gateway | 172.18.0.20:80 | port 80 on host |
| wireguard | VPN server, routes authenticated peers to NGINX | 172.18.0.21 | UDP 51820 on host |
| ollama | Local LLM inference (llama3.2:3b) | 172.18.0.30:11434 | /ollama via NGINX |
| hollama | Minimal Ollama web UI | 172.18.0.31:4173 | port 4173 on host |

---

## Security model

No service is directly reachable from the internet. The full traffic path for a remote client is:

```
Phone (mobile data)
    → WireGuard tunnel (Curve25519 + ChaCha20 encryption)
    → NGINX gateway (only HTTP entry point)
    → target service (invisible to everything outside Docker network)
```

WireGuard uses public/private keypairs for authentication — there is no login page to brute force. Unauthenticated packets are silently dropped. Only devices with a valid peer config can establish a tunnel.

NGINX enforces service boundaries. The webcam service has no awareness of the network topology around it — it reads from the camera and serves frames. All security decisions happen in infrastructure, not application code.

---

## Project structure

```
webcam-service/
├── app/
│   ├── camera.py          # CameraStream class — shared frame buffer, 15fps cap
│   ├── main.py            # FastAPI routes — /stream, /health
│   └── requirements.txt
├── nginx/
│   └── nginx.conf         # Reverse proxy config — all upstream routing
├── docs/
│   └── homelab.md         # Server reference — IPs, commands, known issues
├── Dockerfile             # python:3.11-slim + libgl1 + video group
├── docker-compose.yml     # Full stack definition with static IPs
└── .env                   # WIREGUARD_HOST=your_public_ip (not committed)
```

---

## How to run

Prerequisites: Ubuntu 22.04+, Docker, Git.

```bash
git clone https://github.com/avlasarev/webcam-service.git
cd webcam-service
cp .env.example .env
# edit .env and set WIREGUARD_HOST to your public IP
docker compose up -d
```

For WireGuard remote access, forward UDP port 51820 on your router to the server's LAN IP.

Get peer QR codes:
```bash
docker exec wireguard /app/show-peer phone
```

---

## After every server reboot

The server has a static netplan IP (`192.168.1.12`) but Internet provider's DHCP sometimes re-assigns the old lease. Remove it:

```bash
sudo ip addr del 192.168.1.21/24 dev enp4s0
```

Start the stack:
```bash
cd ~/webcam-service && docker compose up -d
```

Reapply WireGuard routing rules (not persistent across reboots yet):
```bash
sudo nft insert rule ip raw PREROUTING iifname "wg0" ip saddr 10.13.13.0/24 counter accept
sudo iptables -I FORWARD 1 -i wg0 -j ACCEPT
sudo iptables -I FORWARD 1 -o wg0 -j ACCEPT
sudo iptables -t nat -A POSTROUTING -o enp4s0 -j MASQUERADE
sudo iptables -t nat -A PREROUTING -i wg0 -p tcp --dport 80 -j DNAT --to-destination 172.18.0.20:80
```

---

## Local AI

The stack includes Ollama running `llama3.2:3b` for CPU-only inference on the server's AMD A8-3870. A custom model variant with a focused system prompt is available:

```bash
docker exec -it ollama bash
ollama create homelab-assistant -f /tmp/Modelfile
```

Access via Hollama at `http://192.168.1.12:4173` or `http://10.13.13.1:4173` over WireGuard.

Ollama API is proxied through NGINX at `/ollama/` for internal use.

---

## Deployment workflow

```
Edit in PyCharm (Windows)
    → git add . && git commit -m "message" && git push
        → ssh eker@192.168.1.12
            → cd ~/webcam-service && git pull
                → docker compose down && docker compose up -d
```


---

## Known issues and limitations

- DHCP lease for `192.168.1.21` returns after router restart — must be removed manually on each reboot. Permanent fix: configure router DHCP reservation or disable DHCP entirely on the interface.
- LLM inference is hardware intensive
- Local residential ISP uses CGNAT — required purchasing a static IP to enable port forwarding for WireGuard.

---

## Stack versions

| Component | Version |
|-----------|---------|
| Ubuntu | 24.04 LTS |
| Docker | latest |
| Python | 3.11-slim |
| FastAPI | latest |
| Navidrome | latest |
| NGINX | alpine |
| WireGuard | linuxserver/wireguard |
| Ollama | latest |
| Hollama | 0.35.4 |
| llama3.2 | 3b |
