#!/usr/bin/env bash
# Sobe o LiteLLM Proxy com o config.yaml da pasta que chamou este script.
# Uso (de dentro de uma pasta 04, 05 ou 06):  ./iniciar_proxy.sh
set -euo pipefail

CONFIG="${1:-$PWD/config.yaml}"

if ! command -v litellm >/dev/null; then
  RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
  echo "❌ Comando 'litellm' não encontrado. Ative o ambiente virtual:"
  echo "   source \"$RAIZ/.venv/bin/activate\""
  exit 1
fi

source "$(dirname "$0")/provedores.sh"

echo "🌐 Chamadas REAIS aos provedores (geram custo conforme o seu plano)."
echo "🚪 Gateway em http://localhost:4000  (Ctrl+C para parar)"
exec litellm --config "$CONFIG" --port 4000
