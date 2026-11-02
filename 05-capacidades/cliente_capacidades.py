"""
Nota AI Gateways → "GATEWAY TÉCNICO: a aplicação pede uma CAPACIDADE, não um provider"

A aplicação só conhece nomes de capacidade. Quem decide o modelo físico é o
gateway (config.yaml). O header x-litellm-model-name mostra qual modelo real
atendeu: a aplicação não precisa saber, mas aqui imprimimos para você ver.

Lembrete da nota: a abstração protege a aplicação, mas NÃO elimina o modelo
físico. Em algum momento existe um modelo concreto sendo chamado por baixo.

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import sys
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

client = OpenAI(base_url=f"{comum.URL_PROXY}/v1", api_key=comum.valor("LITELLM_MASTER_KEY"))

# O que cada funcionalidade da aplicação pede: capacidade + tarefa.
PEDIDOS = [
    ("classificador-simples", "Classifique a intenção: 'quero cancelar meu plano'. Responda só a categoria."),
    ("resposta-suporte", "Como faço para trocar minha senha?"),
    ("resposta-suporte", "Qual o horário de atendimento?"),
    ("resposta-suporte", "Vocês emitem nota fiscal?"),
    ("extracao-documento", "Extraia nome e CPF: 'Contrato de Maria Silva, CPF 123.456.789-00'."),
    ("analise-profunda", "Analise os riscos de depender de um único provedor de IA."),
]

for capacidade, tarefa in PEDIDOS:
    try:
        bruta = client.chat.completions.with_raw_response.create(
            model=capacidade,                                # ← nome lógico
            messages=[{"role": "user", "content": tarefa}],
            max_tokens=4000,
        )
    except openai.APIConnectionError:
        raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
    except openai.APIStatusError as erro:
        print(f"❌ {capacidade}: HTTP {erro.status_code}: {erro.message}\n")
        continue

    resposta = bruta.parse()
    print(f"capacidade pedida : {capacidade}")
    print(f"modelo físico     : {bruta.headers.get('x-litellm-model-name')}")
    print(f"resposta          : {(resposta.choices[0].message.content or '').strip()[:200]}\n")
