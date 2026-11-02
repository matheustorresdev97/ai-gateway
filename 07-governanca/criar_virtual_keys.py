"""
Nota AI Gateways → "Virtual Key" + "Diferentes aplicações, diferentes acessos"

O GATEWAY emite e gerencia as virtual keys. Cada aplicação recebe a sua,
e nenhuma conhece a chave real do provedor.

  App A → acesso completo  (as duas capacidades, orçamento maior)
  App B → acesso limitado  (só a capacidade barata)
  App C → acesso restrito  (só a capacidade barata, poucas requisições por minuto)

Só a master key (admin) pode criar keys. As keys criadas são salvas em
chaves_geradas.json para os outros scripts usarem.

Antes de rodar: ./iniciar_gateway.sh (em outro terminal)
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

ARQUIVO_CHAVES = Path(__file__).parent / "chaves_geradas.json"

# Políticas de cada aplicação. Na vida real, estes números vêm da
# organização (produto, finanças, risco), não do time técnico sozinho.
APLICACOES = {
    "app-a": {
        "key_alias": "app-a-acesso-completo",
        "models": ["classificacao-simples", "analise-critica"],
        "max_budget": 10.0,        # US$ no período
        "budget_duration": "30d",  # o orçamento renova a cada 30 dias
        "rpm_limit": 60,           # requisições por minuto
        "tpm_limit": 100_000,      # tokens por minuto (a métrica que importa em IA)
    },
    "app-b": {
        "key_alias": "app-b-acesso-limitado",
        "models": ["classificacao-simples"],
        "max_budget": 2.0,
        "budget_duration": "30d",
        "rpm_limit": 30,
        "tpm_limit": 20_000,
    },
    "app-c": {
        "key_alias": "app-c-acesso-restrito",
        "models": ["classificacao-simples"],
        "max_budget": 0.5,
        "budget_duration": "30d",
        "rpm_limit": 2,            # bem baixo, para você ver o bloqueio (HTTP 429)
        "tpm_limit": 5_000,
    },
}


def criar_key(politica: dict) -> str:
    requisicao = urllib.request.Request(
        f"{comum.URL_PROXY}/key/generate",
        data=json.dumps(politica).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {comum.valor('LITELLM_MASTER_KEY')}",
            "content-type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(requisicao, timeout=30) as resposta:
        return json.loads(resposta.read())["key"]


chaves = {}
for app, politica in APLICACOES.items():
    try:
        chaves[app] = criar_key(politica)
    except urllib.error.URLError as erro:
        raise SystemExit(f"❌ Gateway inacessível ({erro}). Rode ./iniciar_gateway.sh antes.")
    print(f"🔑 {politica['key_alias']:<24} modelos={politica['models']} "
          f"orçamento=US${politica['max_budget']} rpm={politica['rpm_limit']}")

ARQUIVO_CHAVES.write_text(json.dumps(chaves, indent=2), encoding="utf-8")
print(f"\n✅ Keys salvas em {ARQUIVO_CHAVES.name}")
