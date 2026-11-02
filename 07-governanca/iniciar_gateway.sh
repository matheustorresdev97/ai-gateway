#!/usr/bin/env bash
# Sobe o gateway com banco (Docker). Uso: ./iniciar_gateway.sh
# Para parar:            docker compose down
# Para apagar o banco:   docker compose down -v
set -euo pipefail
cd "$(dirname "$0")"

source ../_comum/provedores.sh

echo "🌐 Chamadas REAIS aos provedores (geram custo conforme o seu plano)."
echo "🚪 Subindo gateway + banco em http://localhost:4000 (Ctrl+C para parar)"
exec docker compose up
