# 🔒 Security Guidelines for VPN4Friends

## ⚠️ CRITICAL: Never Commit Secrets

### Files That Should NEVER Be Committed:

- `.env` - Environment variables with passwords
- `backup/*.json` - Backup configs with credentials
- `*.pem`, `*.key` - SSH/TLS private keys
- `credentials.json` - Service account keys
- `id_rsa`, `id_ed25519` - SSH private keys
- `opencode.json` - May contain API keys

### What Happened (March 2026)

Sensitive data was accidentally committed to `backup/3x-ui-config.json`:
- 3x-ui panel password
- WARP private keys
- API secrets

**Status:** ✅ Cleaned from repository, ⚠️ Still in git history until `git push --force`

---

## 🛡️ Best Practices

### 1. Use GitHub Secrets for CI/CD

Our GitHub Actions pipeline uses secrets:
- `SERVER_HOST` - Server IP
- `SERVER_USER` - SSH username (root)
- `SSH_KEY` - Private SSH key for deployment

**Never** hardcode these in workflow files!

### 2. Environment Variables

Create `.env` from `.env.example`:
```bash
cp .env.example .env
# Edit .env with real values (NEVER COMMIT!)
```

### 3. Backup Configs Securely

For 3x-ui backups:
```bash
# On server
docker exec 3x-ui cp /etc/x-ui/x-ui.db /root/backup-$(date +%Y%m%d).db

# Download locally (NOT to repo!)
scp root@server:/root/backup-*.db ./local-backups/
```

### 4. Rotate Compromised Secrets

If you accidentally commit secrets:

1. **Immediately change** the compromised credentials
2. **Clean git history** (see `cleanup-secrets.sh`)
3. **Force push**: `git push --force --all origin`
4. **Notify team** to re-clone

---

## 📋 Current Secrets Status

| Secret | Location | Status |
|--------|----------|--------|
| 3x-ui password | Server `.env` | ✅ Safe |
| WARP keys | Server config | ✅ Safe |
| Bot token | GitHub Secrets | ✅ Safe |
| SSH key | GitHub Secrets | ✅ Safe |
| Database | Server only | ✅ Safe |

---

## 🚨 If You Find Secrets in Repo

1. **Don't panic** - but act fast
2. **Rotate immediately** - change the compromised secret
3. **Report** - tell the team
4. **Clean** - run `cleanup-secrets.sh`
5. **Learn** - review what went wrong

---

## 🔐 Generating Secure Passwords

```bash
# Random 32-char password
openssl rand -base64 32

# Hex secret (64 chars)
openssl rand -hex 32

# UUID
uuidgen
```

---

## 📞 Emergency Contacts

- Admin: @WhiteBite (Telegram)
- Server: 62Yun (62YUN-1 MCP)
