"""
Nota AI Gateways → "Observabilidade e Impacto Arquitetural"

1) Chamada observável: um LOG COMPACTO por chamada (quem, modelo, tokens,
   custo) para entender uso, custo e comportamento.
2) Visão por aplicação: quanto cada virtual key já gastou do orçamento.

PRINCÍPIO (nota): observabilidade por chamada + controle de gateway +
governança de limites = sistema saudável, previsível e sustentável.

Se o custo aparecer 0, o LiteLLM pode não conhecer o preço do modelo escolhido.

Antes de rodar: execute o testar_acessos.py para gerar algum uso.
"""

import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

ARQUIVO_CHAVES = Path(__file__).parent / "chaves_geradas.json"
ADMIN = {"Authorization": f"Bearer {comum.valor('LITELLM_MASTER_KEY')}"}


def get(caminho: str):
    requisicao = urllib.request.Request(f"{comum.URL_PROXY}{caminho}", headers=ADMIN)
    try:
        with urllib.request.urlopen(requisicao, timeout=30) as resposta:
            return json.loads(resposta.read())
    except urllib.error.URLError as erro:
        raise SystemExit(f"❌ Gateway inacessível ({erro}). Rode ./iniciar_gateway.sh")


if not ARQUIVO_CHAVES.exists():
    raise SystemExit("❌ Rode antes: python criar_virtual_keys.py")
chaves = json.loads(ARQUIVO_CHAVES.read_text(encoding="utf-8"))

print("GASTO POR APLICAÇÃO (virtual key)\n")
print(f"  {'aplicação':<24}{'gasto (US$)':>12}{'orçamento':>12}{'rpm':>6}")
for app, chave in chaves.items():
    info = get(f"/key/info?key={urllib.parse.quote(chave)}")["info"]
    print(f"  {info.get('key_alias') or app:<24}{info.get('spend') or 0:>12.6f}"
          f"{info.get('max_budget') or 0:>12.2f}{info.get('rpm_limit') or '-':>6}")

print("\nLOG COMPACTO POR CHAMADA (últimas 10)")
print("(o gateway grava os logs em lote: chamadas recentes podem levar ~1 min para aparecer)\n")
logs = get("/spend/logs")
logs = logs if isinstance(logs, list) else logs.get("data", [])
print(f"  {'quando':<10}{'aplicação':<24}{'capacidade':<23}{'modelo físico':<36}{'status':<9}{'tokens':>7}{'custo US$':>11}")
for log in sorted(logs, key=lambda l: l.get("startTime", ""))[-10:]:
    meta = log.get("metadata") or {}
    print(f"  {str(log.get('startTime', ''))[11:19]:<10}"
          f"{meta.get('user_api_key_alias') or '-':<24}"
          f"{log.get('model_group') or '-':<23}"
          f"{(log.get('model') or '-')[:34]:<36}"
          f"{meta.get('status') or log.get('status') or '-':<9}"
          f"{log.get('total_tokens') or 0:>7}"
          f"{log.get('spend') or 0:>11.6f}")
