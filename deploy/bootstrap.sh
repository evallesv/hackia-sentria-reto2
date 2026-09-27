#!/usr/bin/env bash
# bootstrap.sh — Setup completo del VPS sentria desde cero
# Uso: bash bootstrap.sh GEMINI_API_KEY GEMINI_MODEL DEMO_DOMAIN ACME_EMAIL
# Ejemplo: bash bootstrap.sh <GEMINI_API_KEY> gemini-2.5-flash-lite sentria-d2.evalle.dev admin@evalle.dev
set -euo pipefail

GEMINI_API_KEY="${1:?Falta GEMINI_API_KEY}"
GEMINI_MODEL="${2:?Falta GEMINI_MODEL (ej: gemini-1.5-flash)}"
DEMO_DOMAIN="${3:?Falta DEMO_DOMAIN (ej: sentria-d2.evalle.dev)}"
ACME_EMAIL="${4:?Falta ACME_EMAIL}"

echo "==> [1/6] Actualizando sistema e instalando Docker..."
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl gnupg

# Docker (oficial ARM64)
if ! command -v docker &>/dev/null; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
    | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker "$USER"
fi
echo "Docker: $(docker --version)"

echo "==> [2/6] Abriendo puertos en firewall del SO (iptables/ufw)..."
# Ubuntu Oracle tiene iptables por defecto — abrir 80, 443
sudo iptables -I INPUT -p tcp --dport 80 -j ACCEPT  2>/dev/null || true
sudo iptables -I INPUT -p tcp --dport 443 -j ACCEPT 2>/dev/null || true
sudo iptables -I INPUT -p udp --dport 443 -j ACCEPT 2>/dev/null || true
# Persistir si netfilter-persistent está disponible
sudo netfilter-persistent save 2>/dev/null || true

echo "==> [3/6] Clonando repositorio..."
REPO_DIR="/opt/sentria"
if [ -d "$REPO_DIR/.git" ]; then
  cd "$REPO_DIR" && git pull
else
  sudo git clone https://github.com/evallesv/hackia-sentria-reto2.git "$REPO_DIR"
  sudo chown -R "$USER:$USER" "$REPO_DIR"
fi
cd "$REPO_DIR"

echo "==> [4/6] Configurando .env..."
cat > .env <<EOF
AI_MODE=gemini
GEMINI_API_KEY=${GEMINI_API_KEY}
GEMINI_MODEL=${GEMINI_MODEL}
DEMO_DOMAIN=${DEMO_DOMAIN}
ACME_EMAIL=${ACME_EMAIL}
ENABLE_CUSTOM_INPUT=false
LLM_MAX_CALLS_PER_PROCESS=20
EOF
chmod 600 .env
echo ".env configurado (sin volcar valores)"

echo "==> [5/6] Validando compose y construyendo imagen..."
docker compose --env-file .env -f compose.oracle.yaml config --quiet
docker compose --env-file .env -f compose.oracle.yaml build

echo "==> [6/6] Arrancando servicios..."
docker compose --env-file .env -f compose.oracle.yaml up -d

echo ""
echo "======================================"
echo "  sentria desplegado en https://${DEMO_DOMAIN}"
echo "  Verifica: curl -sk https://${DEMO_DOMAIN}/healthz"
echo "======================================"
echo "Siguiente: actualizar DNS A → $(curl -s ifconfig.me) si cambió la IP"
