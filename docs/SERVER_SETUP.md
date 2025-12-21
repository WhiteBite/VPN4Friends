# VPN Server Setup & Backup

## Сервер
- **IP:** 185.232.205.172
- **OS:** Debian/Ubuntu
- **3X-UI Panel:** http://185.232.205.172:2053

## Текущая конфигурация (20.12.2025)

### VLESS-Reality Inbound (ID: 1)

```
Port: 443
Protocol: VLESS
Security: Reality
SNI: google.com
Fingerprint: chrome
```

**Reality Keys:**
```
Private Key: 8Dr80TJH-qfjFGd1PIgRTy0Pr8jlH_blcBbk7DKw8mo
Public Key:  4YJfGgy6y3zkWJfYyNECrlcFp25CYZ6oQAsmwKfDlA4
Short ID:    33189997caa12349
```

**Тестовый клиент:**
```
UUID:  caa5997e-5da1-4ca2-a37b-3ef227d510bb
Email: 1zrq2uo2
Flow:  xtls-rprx-vision
```

**VLESS URL:**
```
vless://caa5997e-5da1-4ca2-a37b-3ef227d510bb@185.232.205.172:443?type=tcp&encryption=none&security=reality&pbk=4YJfGgy6y3zkWJfYyNECrlcFp25CYZ6oQAsmwKfDlA4&fp=chrome&sni=google.com&sid=33189997caa12349&spx=%2F&flow=xtls-rprx-vision#VLESS-Reality-1zrq2uo2
```

---

## Оптимизация сети (sysctl.conf)

Добавлено в `/etc/sysctl.conf` для увеличения скорости VPN:

```bash
# === VPN Optimization (added by Kiro 18.12.2025) ===

# BBR congestion control (вместо cubic)
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr

# Увеличенные сетевые буферы (64MB вместо 212KB)
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.core.rmem_default = 1048576
net.core.wmem_default = 1048576
net.ipv4.tcp_rmem = 4096 1048576 67108864
net.ipv4.tcp_wmem = 4096 1048576 67108864

# Увеличенный backlog
net.core.netdev_max_backlog = 65536
net.core.somaxconn = 65535

# TCP оптимизации
net.ipv4.tcp_fastopen = 3
net.ipv4.tcp_slow_start_after_idle = 0
net.ipv4.tcp_mtu_probing = 1

# Connection tracking
net.netfilter.nf_conntrack_max = 1048576
```

**Результат оптимизации:**
- Download: 9 Mbps → **77 Mbps** (+720%)
- Upload: 7 Mbps → **61 Mbps** (+708%)
- Латентность: 327ms → **34ms** (-90%)

**Применение:**
```bash
sysctl -p
```

---

## Дополнительные оптимизации (rc.local)

Файл `/etc/rc.local` — выполняется при загрузке:

```bash
#!/bin/bash
# Network optimizations for VPN

# Увеличенные ring buffers (4096 вместо 1024)
ethtool -G ens192 rx 4096 tx 4096 2>/dev/null

# Qdisc fq для BBR (вместо pfifo_fast)
tc qdisc replace dev ens192 root fq 2>/dev/null

exit 0
```

**Активация:**
```bash
chmod +x /etc/rc.local
systemctl enable rc-local
systemctl start rc-local
```

---

## 3X-UI Inbound JSON (полный бэкап)

```json
{
  "id": 3,
  "remark": "VLESS-Reality",
  "enable": true,
  "port": 443,
  "protocol": "vless",
  "settings": {
    "clients": [
      {
        "id": "5f2dd4ad-3b92-46b5-b720-497ba7b0b35a",
        "email": "test-client",
        "enable": true,
        "flow": "xtls-rprx-vision",
        "limitIp": 0,
        "totalGB": 0,
        "expiryTime": 0
      }
    ],
    "decryption": "none",
    "fallbacks": []
  },
  "streamSettings": {
    "network": "tcp",
    "security": "reality",
    "realitySettings": {
      "show": false,
      "xver": 0,
      "dest": "www.google.com:443",
      "serverNames": ["www.google.com"],
      "privateKey": "4Okp7SF1PzivrWp4fUNHlM48HGv19Xtme5rwIXUDxXk",
      "shortIds": ["1f38d4f5"],
      "settings": {
        "publicKey": "YekDGkMaw9U8-WkptHVedz7X-ClHRogd6cxzo8ykll0",
        "fingerprint": "chrome",
        "spiderX": "/"
      }
    },
    "tcpSettings": {
      "acceptProxyProtocol": false,
      "header": {"type": "none"}
    }
  },
  "sniffing": {
    "enabled": true,
    "destOverride": ["http", "tls", "quic", "fakedns"]
  }
}
```

---

## Восстановление после сбоя

### 1. Установка 3X-UI
```bash
docker run -d \
  --name 3x-ui \
  --restart unless-stopped \
  --network host \
  -v /root/x-ui-data:/etc/x-ui \
  ghcr.io/mhsanaei/3x-ui:latest
```

### 2. Применение sysctl
```bash
# Скопировать настройки выше в /etc/sysctl.conf
sysctl -p
```

### 3. Создание inbound
Использовать JSON выше через панель или API.

---

## Важно

- **Private Key** хранить в секрете — с ним можно расшифровать трафик
- При смене ключей нужно обновить `.env` в проекте бота
- Volume 3X-UI: `/root/x-ui-data:/etc/x-ui` — бэкапить эту папку
