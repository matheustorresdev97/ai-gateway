"""
Nota AI Gateways → "Gatekeeping Interno do Proxy"

Aplicação (ex: OpenAI SDK) → Requisição HTTP → LiteLLM Proxy → Provedores

A aplicação usa o SDK da OpenAI, mas NÃO fala com a OpenAI: aponta para o
proxy (base_url). Com isso ela conversa com ChatGPT e Gemini pelo mesmo
cliente, sem conhecer nenhuma chave real de provedor.

Provedor sem chave no .env responde com erro 401: o script mostra e segue.

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import sys
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

client = OpenAI(
    base_url=f"{comum.URL_PROXY}/v1",               # ← o gateway, não a OpenAI
    api_key=comum.valor("LITELLM_MASTER_KEY"),      # ← Bearer Token do gateway
)

for modelo in ["chatgpt", "gemini"]:
    print("=" * 60 + f"\nmodel = \"{modelo}\"\n" + "=" * 60)
    try:
        # with_raw_response dá acesso aos headers que o proxy devolve.
        bruta = client.chat.completions.with_raw_response.create(
            model=modelo,
            messages=[{"role": "user", "content": comum.PERGUNTA}],
            max_tokens=4000,
        )
    except openai.APIConnectionError:
        raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
    except openai.APIStatusError as erro:
        print(f"❌ HTTP {erro.status_code}: {erro.message}\n")
        continue

    resposta = bruta.parse()
    print(f"modelo real (header do proxy): {bruta.headers.get('x-litellm-model-name')}")
    print(resposta.choices[0].message.content, "\n")
