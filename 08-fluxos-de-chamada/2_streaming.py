"""
Nota Fluxos de Chamada → "Streaming e latência percebida"

A MESMA explicação pedida duas vezes:

  1) síncrona: a tela fica parada até a resposta inteira chegar;
  2) streaming: o texto aparece aos poucos, a partir do primeiro token.

Compare no final: a latência TOTAL é parecida, mas o TTFT (tempo até o
primeiro trecho visível) do streaming é muito menor. Streaming melhora a
latência PERCEBIDA, não a total.

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import sys
import time
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

client = OpenAI(base_url=f"{comum.URL_PROXY}/v1", api_key=comum.valor("LITELLM_MASTER_KEY"), max_retries=0)

MENSAGENS = [{
    "role": "user",
    "content": "Explique de forma didática, em uns 4 parágrafos, a diferença entre "
               "chamada síncrona, streaming e processamento assíncrono em apps com IA.",
}]

try:
    # ---------- 1) síncrono ----------
    print("=" * 60 + "\n1) SÍNCRONO: aguardando a resposta completa...\n" + "=" * 60, flush=True)
    inicio = time.perf_counter()
    resposta = client.chat.completions.create(model="explicacao", messages=MENSAGENS, max_tokens=4000)
    total_sinc = time.perf_counter() - inicio
    print(resposta.choices[0].message.content)
    print(f"\n⏱️  primeiro texto visível: {total_sinc:.1f}s | total: {total_sinc:.1f}s\n")

    # ---------- 2) streaming ----------
    print("=" * 60 + "\n2) STREAMING: o texto chega em pedaços\n" + "=" * 60, flush=True)
    inicio = time.perf_counter()
    ttft = None
    pedacos = 0
    stream = client.chat.completions.create(
        model="explicacao", messages=MENSAGENS, max_tokens=4000, stream=True,
    )
    for chunk in stream:
        if not chunk.choices:
            continue
        trecho = chunk.choices[0].delta.content
        if trecho:
            if ttft is None:
                ttft = time.perf_counter() - inicio
            pedacos += 1
            print(trecho, end="", flush=True)   # num app web: enviar ao front via SSE
    total_stream = time.perf_counter() - inicio
except openai.APIConnectionError:
    raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
except openai.APIStatusError as erro:
    raise SystemExit(f"❌ HTTP {erro.status_code}: {erro.message}")

print(f"\n\n⏱️  primeiro texto visível (TTFT): {ttft or 0:.1f}s | total: {total_stream:.1f}s | {pedacos} pedaços\n")

print("=" * 60 + "\nRESUMO\n" + "=" * 60)
print(f"{'':12}{'1º texto visível':>18}{'total':>10}")
print(f"{'síncrono':12}{total_sinc:>17.1f}s{total_sinc:>9.1f}s")
print(f"{'streaming':12}{(ttft or 0):>17.1f}s{total_stream:>9.1f}s")
print("\nO total é parecido; o que muda é quanto tempo o usuário fica olhando uma tela parada.")
