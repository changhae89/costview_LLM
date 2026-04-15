#!/usr/bin/env bash
set -euo pipefail

# Ubuntu 24.04 EC2 bootstrap for CostView PRD deployment.
# This script prepares:
# - git / docker runtime
# - passwordless docker for the current user
# - GitHub deploy key for private repo access
# - application directory and .env template

APP_DIR="${HOME}/costview-prd"
DEPLOY_KEY_PATH="${HOME}/.ssh/costview_github_deploy"
REPO_SSH_URL="git@github.com:changhae89/costview_LLM.git"
BRANCH_NAME="main"

echo "[1/8] Install base packages"
sudo apt-get update
sudo apt-get install -y git docker.io ca-certificates curl

echo "[2/8] Enable Docker"
sudo systemctl enable --now docker

echo "[3/8] Allow current user to run docker without sudo"
sudo groupadd docker 2>/dev/null || true
sudo usermod -aG docker "$USER"

echo "[4/8] Prepare SSH directory"
mkdir -p "${HOME}/.ssh"
chmod 700 "${HOME}/.ssh"

echo "[5/8] Generate GitHub deploy key if missing"
if [ ! -f "${DEPLOY_KEY_PATH}" ]; then
  ssh-keygen -t ed25519 -C "costview-ec2-deploy-key" -f "${DEPLOY_KEY_PATH}" -N ""
fi
chmod 600 "${DEPLOY_KEY_PATH}"
chmod 644 "${DEPLOY_KEY_PATH}.pub"

echo "[6/8] Configure SSH for GitHub"
if ! grep -q "Host github.com" "${HOME}/.ssh/config" 2>/dev/null; then
  cat <<EOF >> "${HOME}/.ssh/config"
Host github.com
  HostName github.com
  User git
  IdentityFile ${DEPLOY_KEY_PATH}
  IdentitiesOnly yes
  StrictHostKeyChecking accept-new
EOF
fi
chmod 600 "${HOME}/.ssh/config"

echo "[7/8] Prepare application directory and env file template"
mkdir -p "${APP_DIR}"
chmod 700 "${APP_DIR}"

if [ ! -f "${APP_DIR}/.env" ]; then
  cat <<'EOF' > "${APP_DIR}/.env"
APP_ENV=production
GEMINI_API_KEY=replace_me
GEMINI_MODEL=gemini-2.5-flash
SUPABASE_URL=https://replace-me.supabase.co
SUPABASE_SERVICE_ROLE_KEY=replace_me
PRD_MAX_BATCH=1
EOF
  chmod 600 "${APP_DIR}/.env"
fi

echo "[8/8] Clone repository if missing"
if [ ! -d "${APP_DIR}/.git" ]; then
  rm -rf "${APP_DIR}"
  git clone --branch "${BRANCH_NAME}" "${REPO_SSH_URL}" "${APP_DIR}"
fi

echo ""
echo "Bootstrap complete."
echo ""
echo "Next steps:"
echo "1. Register this deploy key in GitHub Deploy Keys:"
echo "   ${DEPLOY_KEY_PATH}.pub"
echo ""
echo "2. Test GitHub SSH access:"
echo "   ssh -T git@github.com"
echo ""
echo "3. Re-login so docker group membership applies, then verify:"
echo "   docker ps"

