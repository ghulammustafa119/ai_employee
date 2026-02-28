#!/bin/bash
# Initialize vault sync: bare repo + cloud/local working copies
# Usage: bash scripts/init_vault_sync.sh

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

BARE_REPO="vault_sync.git"
CLOUD_DIR="vault_cloud"
LOCAL_DIR="vault_local"

if [ -d "$BARE_REPO" ]; then
    echo "Vault sync already initialized. Delete vault_sync.git/ to reinitialize."
    exit 0
fi

echo "=== Initializing Vault Sync ==="

# 1. Create bare repo
echo "[1/5] Creating bare repo: $BARE_REPO"
git init --bare "$BARE_REPO"

# 2. Create cloud working copy
echo "[2/5] Creating cloud vault: $CLOUD_DIR"
git clone "$BARE_REPO" "$CLOUD_DIR"

# 3. Copy existing vault contents into cloud
echo "[3/5] Copying vault structure to cloud..."
cp -r vault/. "$CLOUD_DIR/" 2>/dev/null || true

# 4. Set up .gitignore in cloud
cat > "$CLOUD_DIR/.gitignore" << 'GITIGNORE'
.env
token.json
credentials.json
.whatsapp_session/
__pycache__/
*.pyc
node_modules/
package-lock.json
GITIGNORE

# 5. Initial commit + push from cloud
cd "$CLOUD_DIR"
git add -A
git commit -m "init: vault structure for platinum tier" 2>/dev/null || echo "Nothing to commit"
git push origin main 2>/dev/null || git push origin master 2>/dev/null || true
cd "$PROJECT_DIR"

# 6. Create local working copy
echo "[4/5] Creating local vault: $LOCAL_DIR"
git clone "$BARE_REPO" "$LOCAL_DIR"

echo "[5/5] Done!"
echo ""
echo "=== Vault Sync Ready ==="
echo "Bare repo:   $BARE_REPO"
echo "Cloud vault:  $CLOUD_DIR"
echo "Local vault:  $LOCAL_DIR"
echo ""
echo "Start Platinum tier with: bash scripts/start_platinum.sh"
