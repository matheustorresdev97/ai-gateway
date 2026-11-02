#!/usr/bin/env bash
# Nota AI Gateways → "Na prática: chamar um LLM com e sem SDK" (versão curl)
# A mesma chamada do chamada_http.py, direto no terminal, para o ChatGPT (OpenAI).
set -euo pipefail
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
set -a; source "$RAIZ/.env"; set +a

curl https://api.openai.com/v1/chat/completions \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -H "content-type: application/json" \
  -d "{\"model\": \"$MODELO_OPENAI\", \"max_completion_tokens\": 2000,
       \"messages\": [{\"role\": \"user\", \"content\": \"Explique em duas frases o que é um AI gateway.\"}]}"
echo
