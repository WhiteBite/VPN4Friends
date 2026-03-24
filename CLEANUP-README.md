# 🧹 Git History Cleanup Guide

## Problem

Sensitive data was committed to `backup/3x-ui-config.json`:
- 3x-ui panel password
- WARP private keys  
- API secrets

## Solution

### Option 1: Using BFG Repo-Cleaner (Fastest - Recommended)

```bash
# Install BFG (requires Java)
# Windows: winget install bfg
# Mac: brew install bfg
# Linux: download from https://rtyley.github.io/bfg-repo-cleaner/

# Clone a fresh copy (cleaner to work with fresh clone)
git clone --mirror https://github.com/WhiteBite/VPN4Friends.git
cd VPN4Friends.git

# Remove sensitive files
bfg --delete-files 'backup/3x-ui-config.json'
bfg --delete-files '*.pem'
bfg --delete-files '*.key'

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push --force --all origin
git push --force --tags origin
```

### Option 2: Using git filter-branch (Slower, no extra tools)

```bash
# Run the cleanup script
chmod +x cleanup-secrets.sh
./cleanup-secrets.sh

# Or manually:
git filter-branch --force --index-filter \
  "git rm --cached --ignore-unmatch -r backup/" \
  --prune-empty --tag-name-filter cat -- --all

# Clean up
git reflog expire --expire=now --all
git gc --prune=now --aggressive

# Force push
git push --force --all origin
git push --force --tags origin
```

### Option 3: Nuclear Option (Delete & Reclone)

If the repo is small and you want a clean start:

```bash
# 1. Download current code (without git history)
curl -L https://github.com/WhiteBite/VPN4Friends/archive/master.zip -o vpn4friends.zip
unzip vpn4friends.zip
cd VPN4Friends-master

# 2. Remove any sensitive files
rm -rf backup/ *.pem *.key .env*

# 3. Create fresh repo
rm -rf .git
git init
git add .
git commit -m "Fresh start - secrets removed"

# 4. Force push to GitHub
git remote add origin https://github.com/WhiteBite/VPN4Friends.git
git push --force --all origin
```

## After Cleanup

### 1. Verify secrets are gone

```bash
# Check current HEAD
git ls-tree -r --name-only HEAD | grep -E 'backup|\.pem|\.key|\.env'

# Search history for passwords
git log --all --oneline --source --remotes -- '*.pem' '*.key' 'backup/*'
```

### 2. Tell team to re-clone

Everyone must run:
```bash
# Delete old clone
rm -rf VPN4Friends

# Fresh clone
git clone https://github.com/WhiteBite/VPN4Friends.git
```

Or if they want to keep local changes:
```bash
cd VPN4Friends
git fetch origin
git reset --hard origin/master
```

### 3. Rotate compromised secrets

**On server (62Yun):**
1. Change 3x-ui password: `http://62Yun:2053` → Settings
2. Regenerate WARP keys in 3x-ui
3. Update `.env` with new values

**On GitHub:**
1. Go to Settings → Secrets and variables → Actions
2. Check if any secrets need rotation
3. Update if compromised

## Prevention

### .gitignore (Already Updated)

```
# BACKUPS - NEVER COMMIT
backup/
backups/
*.backup
*.bak
*.old

# Secrets
secrets/
*.secret
credentials.json
```

### Pre-commit Hook

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
# Block commits with sensitive files

if git diff --cached --name-only | grep -qE 'backup/|\.pem$|\.key$|credentials\.json'; then
    echo "❌ Blocked: Attempt to commit sensitive files!"
    exit 1
fi
```

```bash
chmod +x .git/hooks/pre-commit
```

### GitHub Secret Scanning

Enable in GitHub repo settings:
- Settings → Code security and analysis
- Enable "Secret scanning"
- Enable "Push protection"

---

## Questions?

Contact: @WhiteBite (Telegram)
