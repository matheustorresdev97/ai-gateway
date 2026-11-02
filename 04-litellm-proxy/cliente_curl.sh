#!/usr/bin/env bash
# Nota AI Gateways → "LiteLLM Proxy - Fluxo de Requisição"
# APLICAÇÃO → Bearer Token (HTTP) → PROXY → PROVIDER
#
# Compare com o 01-sem-sdk/chamada_curl.sh: aqui a URL é a do gateway, a chave
# é a do gateway e o formato é o da OpenAI, para QUALQUER provedor.
# Uso: ./cliente_curl.sh [chatgpt|gemini]
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
set -a; source "$RAIZ/.env"; set +a
MODELO="${1:-chatgpt}"

curl -s http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer $LITELLM_MASTER_KEY" \
  -H "content-type: application/json" \
  -d "{\"model\": \"$MODELO\",
       \"messages\": [{\"role\": \"user\", \"content\": \"Explique em duas frases o que é um AI gateway.\"}]}"
echo
