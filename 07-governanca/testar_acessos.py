"""
Nota AI Gateways → "Gateway (aplica regras): permite / bloqueia, limites / cotas"

Cada aplicação usa a SUA virtual key. O gateway valida a key antes de chamar
o provider: existe? está ativa? dentro do orçamento e dos limites? o acesso
a este modelo é permitido?

Teste 1: cada app tenta usar as duas capacidades → App B e C são bloqueados
         na análise crítica (modelo caro).
Teste 2: App C faz 4 requisições seguidas → passa do rpm=2 e recebe HTTP 429.

Antes de rodar: ./iniciar_gateway.sh e python criar_virtual_keys.py
"""

import json
import sys
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

ARQUIVO_CHAVES = Path(__file__).parent / "chaves_geradas.json"
if not ARQUIVO_CHAVES.exists():
    raise SystemExit("❌ Rode antes: python criar_virtual_keys.py")
chaves = json.loads(ARQUIVO_CHAVES.read_text(encoding="utf-8"))


def chamar(app: str, capacidade: str) -> str:
    client = OpenAI(base_url=f"{comum.URL_PROXY}/v1", api_key=chaves[app], max_retries=0)
    try:
        resposta = client.chat.completions.create(
            model=capacidade,
            messages=[{"role": "user", "content": "Classifique: 'meu boleto não chegou'."}],
            max_tokens=500,
        )
        return f"✅ permitido → {resposta.choices[0].message.content.strip()[:60]}"
    except openai.RateLimitError:
        return "⛔ 429 bloqueado: limite de requisições/tokens/orçamento"
    except openai.APIConnectionError:
        raise SystemExit("❌ Gateway fora do ar. Rode ./iniciar_gateway.sh")
    except openai.APIStatusError as erro:
        return f"⛔ {erro.status_code} bloqueado: sem acesso a este modelo"


print("TESTE 1: diferentes aplicações, diferentes acessos\n")
for app in ["app-a", "app-b", "app-c"]:
    for capacidade in ["classificacao-simples", "analise-critica"]:
        print(f"  {app} → {capacidade:<22} {chamar(app, capacidade)}")
    print()

print("TESTE 2: App C (rpm=2) faz 4 requisições seguidas\n")
for i in range(1, 5):
    print(f"  requisição {i}: {chamar('app-c', 'classificacao-simples')}")
