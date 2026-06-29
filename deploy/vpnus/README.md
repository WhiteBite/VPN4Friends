# VPNUS re-proxy (host-side)

Re-proxies an upstream VPNUS subscription as stable per-country exits, so users
connect to our own panel inbounds while traffic leaves via VPNUS servers. Upstream
rotation is handled here on the host and never touches the panel or disconnects users.

## How it works

```
user → 3x-ui inbound (our Reality keys, ports 8451-8456)
     → panel outbound vpnus_<cc> = socks 127.0.0.1:4001x   (static, never changes)
     → vpnus-xray (dedicated client) → current VPNUS server (<country>) → internet
```

- `refresh.py` fetches the VPNUS subscription, parses the VLESS servers, and rebuilds
  the dedicated client's `config.json` (one local SOCKS port per country). It restarts
  `vpnus-xray` only when the server set actually changes.
- `vpnus-refresh.timer` runs `refresh.py` every ~30 min (rotation-safe).
- The panel's `vpnus_*` outbounds point at the static local SOCKS ports, so the panel
  config never needs to change when upstream rotates.

Country → local SOCKS port: us=40010, uk=40011, fr=40012, nl=40013, tr=40014, kz=40015.

## Host install (one-time, as root)

```sh
mkdir -p /opt/vpnus-xray
cp deploy/vpnus/refresh.py /opt/vpnus-xray/refresh.py
cp /path/to/xray /opt/vpnus-xray/xray            # any recent xray-core binary
printf '%s\n' 'https://<vpnus-subscription-url>' > /opt/vpnus-xray/sub_url.txt
cp deploy/vpnus/vpnus-xray.service     /etc/systemd/system/
cp deploy/vpnus/vpnus-refresh.service  /etc/systemd/system/
cp deploy/vpnus/vpnus-refresh.timer    /etc/systemd/system/
systemctl daemon-reload
python3 /opt/vpnus-xray/refresh.py                # generates config + starts client
systemctl enable vpnus-xray
systemctl enable --now vpnus-refresh.timer
```

The subscription URL is a secret and lives only in `/opt/vpnus-xray/sub_url.txt`
(or the `VPNUS_SUB_URL` env var) — never commit it.

## Panel + bot wiring (one-time)

1. Panel `xrayTemplateConfig` (3x-ui DB `settings`): add socks outbounds
   `vpnus_us..vpnus_kz` → `127.0.0.1:40010..40015`, plus routing rules mapping each
   VPNUS user inbound tag → its `vpnus_<cc>` outbound. Restart the panel.
2. Bot `.env` `ENDPOINTS_CONFIG`: add one `vpnus_<cc>` endpoint per country
   (ports 8451-8456, our Reality keys, `sub_label` branded "🇺🇸 VPNUS — …").
   The bot provisions the inbounds and they appear in user subscriptions automatically.

## Notes

- Upstream labels may not match the real exit IP geo (e.g. their "UK" server can
  egress via a DE IP). That reflects VPNUS routing, not this pipeline.
- `refresh.py` preserves the last-known-good outbound for any country missing from a
  given refresh, so a transient upstream gap doesn't drop a location.
