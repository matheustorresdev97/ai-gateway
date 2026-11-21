"""
Nota Cache → "Como OpenAI, Anthropic e Gemini tratam prompt caching"
             e "Arquitetura de prompts: estrutura e prefixos estáveis"

Aqui o cache é do PROVEDOR: a chamada acontece, mas o provedor reaproveita o
processamento do PREFIXO idêntico do prompt (acima de ~1.024 tokens). A resposta
traz quantos tokens vieram do cache em usage.prompt_tokens_details.cached_tokens.

Um manual de políticas longo (fixo) + a pergunta do usuário (variável):

  1. prefixo fixo + pergunta A        → grava o prefixo no cache do provedor
  2. prefixo fixo + pergunta B        → mesmo prefixo: tokens lidos do cache
  3. prefixo fixo + pergunta C        → idem
  4. HORA ATUAL no topo + pergunta B  → o prefixo mudou no 1º token: nada do cache
  5. HORA ATUAL no fim  + pergunta C  → o prefixo segue igual: cache volta a funcionar

O cache do provedor é "melhor esforço": às vezes a requisição cai numa máquina
sem o prefixo e o cached_tokens vem 0. Rode de novo se acontecer.

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import sys
import time
from datetime import datetime
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

client = OpenAI(base_url=f"{comum.URL_PROXY}/v1", api_key=comum.valor("LITELLM_MASTER_KEY"), max_retries=0)

TEMAS = ["cancelamento", "reembolso", "troca de plano", "cobrança em duplicidade", "pausa da assinatura",
         "compartilhamento de conta", "suporte em TV", "download offline", "perfis infantis", "promoções"]


def manual_de_politicas() -> str:
    """Texto FIXO e determinístico (~4.000 tokens): sempre igual, byte a byte."""
    linhas = ["Você é o assistente de atendimento da StreamFlix. Responda em português, em até duas frases,",
              "usando SOMENTE as políticas abaixo. Se a política não cobrir o caso, diga que vai encaminhar.", ""]
    for i in range(1, 61):
        tema = TEMAS[i % len(TEMAS)]
        linhas.append(
            f"Política {i:02d} ({tema}): o cliente pode solicitar {tema} pelo app ou site; o prazo de análise é de "
            f"{(i % 7) + 1} dias úteis; casos com valor acima de R$ {50 + i * 5},00 exigem confirmação por e-mail; "
            f"o protocolo deve ser informado no início da conversa e registrado no histórico do cliente."
        )
    return "\n".join(linhas)


MANUAL = manual_de_politicas()


def chamar(rotulo: str, system: str, pergunta: str) -> None:
    inicio = time.perf_counter()
    try:
        resposta = client.chat.completions.create(
            model="politicas",
            messages=[{"role": "system", "content": system}, {"role": "user", "content": pergunta}],
            max_tokens=80, temperature=0,
        )
    except openai.APIConnectionError:
        raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
    ms = (time.perf_counter() - inicio) * 1000
    uso = resposta.usage
    detalhes = getattr(uso, "prompt_tokens_details", None)
    cacheados = (getattr(detalhes, "cached_tokens", 0) or 0) if detalhes else 0
    print(f"{rotulo:<34} {uso.prompt_tokens:>8} {cacheados:>10} {cacheados / uso.prompt_tokens:>7.0%} {ms:>9.0f} ms")


agora = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"{'passo':<34} {'entrada':>8} {'do cache':>10} {'%':>7} {'tempo':>12}")
print("-" * 76)
chamar("1. prefixo fixo + pergunta A", MANUAL, "Quanto tempo leva a análise de um reembolso?")
chamar("2. prefixo fixo + pergunta B", MANUAL, "Posso pausar minha assinatura?")
chamar("3. prefixo fixo + pergunta C", MANUAL, "Como compartilho minha conta?")
chamar("4. hora atual NO TOPO + pergunta B", f"Data e hora atual: {agora}\n\n{MANUAL}", "Posso pausar minha assinatura?")
chamar("5. hora atual NO FIM + pergunta C", MANUAL, f"Data e hora atual: {agora}\n\nComo compartilho minha conta?")

print("""
Repare:
- A 1ª chamada grava o prefixo; as seguintes leem a maior parte da entrada do cache (cobrada com desconto).
- A resposta continua sendo gerada: o cache do provedor NÃO evita a chamada, só barateia a parte repetida.
- No passo 4, um único dado variável no começo muda o prefixo inteiro: zero do cache.
  Regra de ouro: do mais estático para o mais dinâmico (data, sessão e pergunta no FIM).""")
