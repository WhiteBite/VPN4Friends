# 3X-UI Configuration Backup

> Дата: 21.12.2025
> Сервер: 185.232.205.172

## Быстрое восстановление

```bash
# 1. Установить Docker
curl -fsSL https://get.docker.com | sh

# 2. Создать директории
mkdir -p /opt/3x-ui/db /opt/3x-ui/cert
cd /opt/3x-ui

# 3. Создать docker-compose.yml (см. ниже)

# 4. Запустить
docker compose up -d

# 5. Применить sysctl оптимизации
cat >> /etc/sysctl.conf << 'EOF'
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.rmem_max = 67108864
net.core.wmem_max = 67108864
net.ipv4.tcp_fastopen = 3
EOF
sysctl -p
```

## docker-compose.yml

```yaml
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

## Panel

```
URL:      http://185.232.205.172:2053/panel/
Username: admin
Password: admin
```

## VLESS-Reality Inbound (порт 443)

- Protocol: `vless`
- Port: `443`
- Security: `reality`
- Flow: `xtls-rprx-vision`
- SNI: `google.com`
- Fingerprint: `chrome`

**Reality Keys:**
```
Public Key: 4YJfGgy6y3zkWJfYyNECrlcFp25CYZ6oQAsmwKfDlA4
Short ID:   33189997caa12349
```

## Оптимизации сети

Применены на сервере:
- BBR congestion control
- 64MB сетевые буферы  
- TCP Fast Open
- Fair Queue (fq) scheduler
- Ring buffers 4096

Результат: ~85 Mbps через VPN (92% от прямого подключения)

## Файлы

- `sysctl.conf` — настройки ядра
- `3x-ui-config.json` — экспорт настроек панели
