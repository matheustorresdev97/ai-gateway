"""
Nota AI Gateways → "Árvore de fallback"

REQUISIÇÃO → TENTATIVA PRINCIPAL → sucesso? → RESPOSTA
                     └── falhou → FALLBACK TÉCNICO (outro modelo/deployment/provider) → RESPOSTA

O cliente só pede "atendimento" ou "analise-longa" e recebe uma resposta.
Ele não sabe que a tentativa principal falhou: quem resolveu foi o gateway.
Os headers x-litellm-* mostram o que aconteceu por dentro.

Lembrete da nota: no fallback a RESPOSTA PODE MUDAR (qualidade, formato,
estilo, comportamento), porque é outro modelo respondendo.

Antes de rodar, em terminais separados:
  1. python provedor_simulado.py
  2. ./iniciar_proxy.sh
"""

import sys
import time
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

# max_retries=0: o retry é responsabilidade do GATEWAY, não do cliente.
client = OpenAI(
    base_url=f"{comum.URL_PROXY}/v1",
    api_key=comum.valor("LITELLM_MASTER_KEY"),
    max_retries=0,
    timeout=300,
)

CENARIOS = [
    ("atendimento", "Provedor principal LENTO → estoura o timeout de 5s"),
    ("analise-longa", "Provedor principal FORA DO AR → falha de conexão"),
]

for capacidade, cenario in CENARIOS:
    print("=" * 60 + f"\n{capacidade}: {cenario}\n" + "=" * 60)
    inicio = time.perf_counter()
    try:
        bruta = client.chat.completions.with_raw_response.create(
            model=capacidade,
            messages=[{"role": "user", "content": comum.PERGUNTA}],
            max_tokens=4000,
        )
    except openai.APIConnectionError:
        raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
    except openai.APIStatusError as erro:
        print(f"❌ Nem o fallback salvou: HTTP {erro.status_code}: {erro.message}\n")
        continue

    duracao = time.perf_counter() - inicio
    h = bruta.headers
    print(f"tempo total            : {duracao:.1f}s")
    print(f"grupo que respondeu    : {h.get('x-litellm-model-group')}")
    print(f"modelo físico          : {h.get('x-litellm-model-name')}")
    print(f"fallbacks tentados     : {h.get('x-litellm-attempted-fallbacks')}")
    print(f"resposta               : {bruta.parse().choices[0].message.content}\n")
