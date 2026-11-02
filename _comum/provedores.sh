#!/usr/bin/env bash
# Carrega o .env e decide quais provedores o gateway vai usar.
# Usado por iniciar_proxy.sh (pastas 04-06) e iniciar_gateway.sh (pasta 07).
#
# Os config.yaml das pastas 05, 06 e 07 falam em modelo PRINCIPAL e SECUNDÁRIO:
#   - ChatGPT e Gemini preenchidos → principal = ChatGPT, secundário = Gemini
#   - só um preenchido             → principal = secundário = esse provedor
# Assim os exemplos funcionam com qualquer uma das duas chaves.

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
set -a; source "$RAIZ/.env"; set +a

preenchido() { [ -n "${!1:-}" ] && [[ "${!1}" != COLE_* ]]; }

TEM_OPENAI=false; TEM_GEMINI=false
preenchido OPENAI_API_KEY && preenchido MODELO_OPENAI && TEM_OPENAI=true
preenchido GEMINI_API_KEY && preenchido MODELO_GEMINI && TEM_GEMINI=true

if ! $TEM_OPENAI && ! $TEM_GEMINI; then
  echo "❌ Preencha no .env a chave e o modelo do ChatGPT e/ou do Gemini."
  exit 1
fi

# Nomes com prefixo do provedor, como o LiteLLM exige.
export LITELLM_MODELO_OPENAI="openai/$MODELO_OPENAI"
export LITELLM_MODELO_GEMINI="gemini/$MODELO_GEMINI"

if $TEM_OPENAI; then
  export MODELO_PRINCIPAL="$LITELLM_MODELO_OPENAI" CHAVE_PRINCIPAL="$OPENAI_API_KEY"
else
  export MODELO_PRINCIPAL="$LITELLM_MODELO_GEMINI" CHAVE_PRINCIPAL="$GEMINI_API_KEY"
fi
if $TEM_GEMINI; then
  export MODELO_SECUNDARIO="$LITELLM_MODELO_GEMINI" CHAVE_SECUNDARIO="$GEMINI_API_KEY"
else
  export MODELO_SECUNDARIO="$LITELLM_MODELO_OPENAI" CHAVE_SECUNDARIO="$OPENAI_API_KEY"
fi

echo "🔌 Provedores: ChatGPT=$($TEM_OPENAI && echo sim || echo não) | Gemini=$($TEM_GEMINI && echo sim || echo não)"
echo "   modelo principal  → $MODELO_PRINCIPAL"
echo "   modelo secundário → $MODELO_SECUNDARIO"
