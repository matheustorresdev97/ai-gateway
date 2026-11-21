"""
Nota Cache → "Hit, miss e cache-aside", "TTL, resposta stale e invalidação"
             e "Fingerprint de prompt e contexto"

O analisador de tickets com CACHE EXATO na aplicação (em memória, TTL de 6s
para caber na demonstração). Sequência:

  1. mensagem nova                                → MISS (chama a IA)
  2. a mesma mensagem com outra grafia            → HIT  (normalização)
  3. outra mensagem                               → MISS
  4. mensagem 1 com o prompt v2 (regra nova)      → MISS (o fingerprint mudou sozinho)
  5. mensagem 1 com o prompt v1 de novo           → HIT  (a entrada v1 continua lá até o TTL)
  6. mensagem 1 depois de vencer o TTL            → MISS (stale vale como ausência)
  7. mesma INTENÇÃO com outras palavras           → MISS (o cache exato não entende intenção)

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import time
from statistics import mean

from cache_app import CacheTTL, Estatisticas, analisar

TTL = 6
cache = CacheTTL(ttl_segundos=TTL)
est = Estatisticas()

MSG = "Quero cancelar meu plano, está caro demais"

passos = [
    ("1. mensagem nova", MSG, "triagem-v1"),
    ("2. mesma, outra grafia", "  quero CANCELAR meu plano,   está caro demais ", "triagem-v1"),
    ("3. outra mensagem", "Meu boleto veio duplicado este mês", "triagem-v1"),
    ("4. prompt v2 (regra nova)", MSG, "triagem-v2"),
    ("5. de volta ao prompt v1", MSG, "triagem-v1"),
]


def mostrar(rotulo: str, r: dict) -> None:
    categoria = r["resposta"].get("categoria", "?")
    print(f"{rotulo:<36} {r['status']:<4}  {r['chave']}  {r['segundos'] * 1000:>7.1f} ms  → {categoria}")


print(f"{'passo':<36} {'':<4}  {'chave (tenant:fingerprint)':<24} {'tempo':>10}    categoria")
print("-" * 92)
for rotulo, msg, versao in passos:
    mostrar(rotulo, analisar(msg, cache, est, prompt_versao=versao))

print(f"   ... esperando {TTL + 1}s para o TTL vencer ...")
time.sleep(TTL + 1)
mostrar("6. depois do TTL", analisar(MSG, cache, est))
mostrar("7. mesma intenção, outras palavras",
        analisar("Como encerro minha assinatura? O preço subiu muito", cache, est))

print("\n" + "=" * 60 + "\nRESUMO\n" + "=" * 60)
total = est.hits + est.misses
print(f"requisições: {total} | hits: {est.hits} | misses: {est.misses} | hit ratio: {est.hit_ratio():.0%}")
print(f"chamadas à IA: {est.chamadas_ia} | tokens gastos: {est.tokens_gastos} | tokens poupados pelos hits: {est.tokens_poupados}")
print(f"tempo médio: hit {mean(est.tempos_hit) * 1000:.2f} ms | miss {mean(est.tempos_miss) * 1000:.0f} ms")
