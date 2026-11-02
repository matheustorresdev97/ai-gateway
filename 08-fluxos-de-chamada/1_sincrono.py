"""
Nota Fluxos de Chamada → "Quando uma chamada síncrona ainda faz sentido"
                         "Por que usar IA síncrona para tudo é um problema"

Dois pedidos pelo MESMO fluxo síncrono (a aplicação segura a conexão até
a resposta chegar), com o mesmo timeout de cliente:

  A) Classificar um ticket: resposta curta e estruturada → síncrono é o certo.
  B) Gerar um relatório longo: a conexão fica presa até estourar o timeout,
     o usuário não recebe NADA e o provedor pode ter gerado (e cobrado) tokens.

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import sys
import time
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

TIMEOUT_CLIENTE = 8  # segundos que a aplicação aceita segurar a conexão

client = OpenAI(
    base_url=f"{comum.URL_PROXY}/v1",
    api_key=comum.valor("LITELLM_MASTER_KEY"),
    timeout=TIMEOUT_CLIENTE,   # timeout explícito: nunca esperar indefinidamente
    max_retries=0,             # retry é do gateway, não do cliente (ver pasta 06)
)

PEDIDOS = [
    (
        "A) classificar ticket (curto e estruturado)",
        "classificacao",
        "Classifique o ticket em BUG, DUVIDA ou PEDIDO. Responda só a palavra.\n\n"
        "Ticket: 'O botão de exportar PDF não faz nada quando clico.'",
    ),
    (
        "B) relatório longo (aberto e demorado)",
        "analise",
        "Escreva um relatório técnico detalhado, com pelo menos 1500 palavras, sobre "
        "os riscos de arquitetura ao integrar LLMs em um sistema bancário. "
        "Inclua seções, exemplos e recomendações.",
    ),
]

for titulo, capacidade, prompt in PEDIDOS:
    print("=" * 60 + f"\n{titulo}  →  model=\"{capacidade}\"\n" + "=" * 60)
    inicio = time.perf_counter()
    try:
        resposta = client.chat.completions.create(
            model=capacidade,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=6000,
        )
    except openai.APITimeoutError:
        espera = time.perf_counter() - inicio
        print(f"⏱️  TIMEOUT após {espera:.1f}s: a conexão ficou presa e o usuário não recebeu nada.")
        print("   O provedor pode ter continuado gerando (e cobrando) do outro lado.")
        print("   → Candidato a streaming (se o parcial ajuda) ou job assíncrono (3_job_assincrono.py).\n")
        continue
    except openai.APIConnectionError:
        raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
    except openai.APIStatusError as erro:
        print(f"❌ HTTP {erro.status_code}: {erro.message}\n")
        continue

    espera = time.perf_counter() - inicio
    texto = resposta.choices[0].message.content or ""
    print(f"✅ {espera:.1f}s, {len(texto)} caracteres")
    print(texto if len(texto) < 300 else texto[:300] + " [...]")
    if capacidade == "analise":
        print(f"\n   Voltou dentro de {TIMEOUT_CLIENTE}s desta vez, mas o tempo varia a cada chamada:")
        print("   o usuário ficou olhando um loading o tempo todo. Rode de novo ou reduza TIMEOUT_CLIENTE.")
    print()
