# 3X-UI Full Configuration Backup

> Дата бэкапа: 19.12.2025
> Сервер: 193.17.182.116

## Быстрое восстановление

```bash
# 1. Установить Docker
curl -fsSL https://get.docker.com | sh

# 2. Создать директории
mkdir -p /opt/3x-ui/db /opt/3x-ui/cert
cd /opt/3x-ui

# 3. Скопировать x-ui.db из бэкапа (если есть)
# или настроить вручную по инструкции ниже

# 4. Создать docker-compose.yml (см. ниже)

# 5. Запустить
docker compose up -d

# 6. Применить sysctl
# Скопировать настройки из раздела "Оптимизация сети"
sysctl -p
```

---

## docker-compose.yml

```yaml
version: '3.8'

services:
  3x-ui:
    image: ghcr.io/mhsanaei/3x-ui:latest
    container_name: 3x-ui
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./db/:/etc/x-ui/
      - ./cert/:/root/cert/
    environment:
      - XRAY_VMESS_AEAD_FORCED=false
    tty: true
```

---

## Panel Credentials

```
URL:      http://YOUR_IP:2053/panel/
Username: admin-dan
Password: spe~.4va+tw_)@4msfc4@i&~;6ukcf0(]m2
```

---

## VLESS-Reality Inbound (порт 443)

**Основные настройки:**
- Remark: `VLESS-REALITY-Vision`
- Protocol: `vless`
- Port: `443`
- Enable: ✓

**Reality Settings:**
- Security: `reality`
- Target (dest): `www.asus.com:443`
- Server Names: `www.asus.com`
- Fingerprint: `chrome`
- SpiderX: `/`

**Reality Keys (СЕКРЕТНО!):**
```
Private Key: uOOn9B861RQ78DILrivkrPDC_kGmSjfQfTiuHqjXX0M
Public Key:  pJ3eZ4U58pv7L6Zg_ud2zhQqLoeoIXZ6bxyVNXOL9Co
Short ID:    3d0dc523
```

**Client Settings:**
- Flow: `xtls-rprx-vision`

**Sniffing:**
- Enabled: ✓
- destOverride: `http, tls, quic, fakedns`
- routeOnly: ✓

---

## Клиенты (VPN пользователи)

| Email | UUID | Comment |
|-------|------|---------|
| vy8passs | 691fd156-80d0-4cee-b7b4-bb2ccdb3a248 | test-client |
| user_5683814147_9557 | 314aa362-e660-4c50-ae72-be7cce6ba73e | |
| user_267945352_2312 | 8a097b65-ed08-4281-a033-b2b76729b7ee | |

---

## WARP Outbound (Cloudflare)

Настроен как outbound для обхода блокировок.

```json
{
  "access_token": "ab766de2-5a18-49a3-8ac3-3f6b56ca13fc",
  "device_id": "63edc1fb-c8cb-4024-a22f-c709595bb411",
  "license_key": "E80X3iS1-8m467FUk-5ld2Hm61",
  "private_key": "EF6lI8fVCdXoywunCm/VOT9fTCC8pLce7mTpUeBFBkc="
}
```

**WireGuard Settings:**
- Endpoint: `engage.cloudflareclient.com:2408`
- Address: `172.16.0.2/32`
- Reserved: `[8, 177, 3]`

---

## Xray Template Config

**DNS Servers:**
- 1.1.1.1
- 1.0.0.1
- 2606:4700:4700::1111
- 2606:4700:4700::1001

**Routing Rules:**
- Block: `geoip:private`
- Block: `bittorrent`

**Panel Secret:** `JxGwxgyWOm8yY3vqYgTui2FWH6TXGrRy`

---

## Оптимизация сети (sysctl.conf)

```bash
# === VPN Optimization ===
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# Network buffers (16MB для VDS с 1GB RAM)
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.ipv4.tcp_rmem = 4096 1048576 16777216
net.ipv4.tcp_wmem = 4096 1048576 16777216

# Backlog
net.core.netdev_max_backlog = 65536
net.core.somaxconn = 65535

# TCP optimizations
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_mtu_probing = 1
```

---

## Файлы бэкапа

- `3x-ui-config.json` — полный JSON со всеми настройками
- `docker-compose.yml` — конфиг Docker
- `sysctl.conf` — настройки ядра
- `x-ui.db` — база данных (если нужно восстановить клиентов)
