#!/bin/bash
# ============================================
# Git History Secrets Cleanup Script
# For VPN4Friends repository
# ============================================

set -e

echo "=== Git Secrets Cleanup ==="
echo ""
echo "⚠️  WARNING: This will REWRITE git history!"
echo "    After running, you MUST: git push --force"
echo "    All developers must: git pull --force"
echo ""

# Check if we're in the right directory
if [ ! -f ".gitignore" ]; then
    echo "Error: Not in repository root"
    exit 1
fi

# Files to remove from history
FILES_TO_REMOVE=(
    "backup/3x-ui-config.json"
    "*.pem"
    "*.key"
    "id_rsa"
    "id_ed25519"
    ".env"
    ".env.local"
    "credentials.json"
)

echo "Files to remove from history:"
for file in "${FILES_TO_REMOVE[@]}"; do
    echo "  - $file"
done
echo ""

# Method 1: Using BFG Repo-Cleaner (faster, recommended)
if command -v bfg &> /dev/null; then
    echo "Using BFG Repo-Cleaner..."
    bfg --delete-files "${FILES_TO_REMOVE[@]}" .
    echo ""
    echo "BFG cleanup complete!"
else
    echo "BFG not found. Using git filter-branch (slower)..."
    echo ""
    
    # Remove specific files
    git filter-branch --force --index-filter \
        "git rm --cached --ignore-unmatch -r backup/" \
        --prune-empty --tag-name-filter cat -- --all
    
    # Also remove any .pem, .key files
    git filter-branch --force --index-filter \
        "git rm --cached --ignore-unmatch -- '*.pem' '*.key'" \
        --prune-empty --tag-name-filter cat -- --all
    
    echo ""
    echo "Git filter-branch complete!"
fi

# Clean up reflog and garbage
echo "Cleaning up reflog and garbage..."
git reflog expire --expire=now --all
git gc --prune=now --aggressive

echo ""
echo "=== Cleanup Complete ==="
echo ""
echo "Next steps:"
echo "1. Verify: git log --all --oneline | head -10"
echo "2. Check: git ls-tree -r --name-only HEAD | grep -E 'backup|\.pem|\.key'"
echo "3. Force push: git push --force --all origin"
echo "4. Force push tags: git push --force --tags origin"
echo ""
echo "⚠️  Tell all developers to run:"
echo "   git fetch origin"
echo "   git reset --hard origin/master"
echo ""
