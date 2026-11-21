"""
Nota Cache → "Armadilhas do cache-aside com IA" (cache stampede)

Uma promoção acabou de sair e 8 usuários fazem a MESMA pergunta inédita ao
mesmo tempo. O cache está vazio para essa chave.

  Rodada 1, cache-aside ingênuo: todos dão MISS juntos → 8 chamadas iguais à IA.
  Rodada 2, com request coalescing (single flight): uma trava por chave; só a
           primeira requisição chama a IA, as outras esperam e leem do cache.

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import threading
import time

from cache_app import CacheTTL, Estatisticas, analisar, classificar_com_ia, fingerprint, resposta_valida

USUARIOS = 8
PERGUNTA = "A promoção de 3 meses por R$ 9,90 vale para quem já é assinante?"


class SingleFlight:
    """Uma trava por chave: só um 'voo' por chave de cada vez."""

    def __init__(self):
        self._travas: dict[str, threading.Lock] = {}
        self._guarda = threading.Lock()

    def trava(self, chave: str) -> threading.Lock:
        with self._guarda:
            return self._travas.setdefault(chave, threading.Lock())


def analisar_coalescido(mensagem: str, cache: CacheTTL, est: Estatisticas, sf: SingleFlight) -> dict:
    inicio = time.perf_counter()
    chave = fingerprint(mensagem, "triagem-v1")
    if (r := cache.get(chave)) is not None:
        return {"status": "HIT", "segundos": time.perf_counter() - inicio}

    with sf.trava(chave):
        # verifica DE NOVO: enquanto esperava a trava, outro pode ter preenchido o cache
        if (r := cache.get(chave)) is not None:
            return {"status": "HIT (esperou)", "segundos": time.perf_counter() - inicio}
        resposta, tokens = classificar_com_ia(mensagem, "triagem-v1")
        with est._trava:
            est.chamadas_ia += 1
        if resposta_valida(resposta):
            cache.set(chave, {**resposta, "_tokens": tokens})
        return {"status": "MISS (chamou a IA)", "segundos": time.perf_counter() - inicio}


def rodada(titulo: str, funcao) -> int:
    resultados: list = [None] * USUARIOS
    largada = threading.Barrier(USUARIOS)      # todos disparam no mesmo instante

    def usuario(i: int) -> None:
        largada.wait()
        resultados[i] = funcao()

    threads = [threading.Thread(target=usuario, args=(i,)) for i in range(USUARIOS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    print("=" * 60 + f"\n{titulo}\n" + "=" * 60)
    for i, r in enumerate(resultados, 1):
        print(f"  usuário {i}: {r['status']:<20} {r['segundos']:.2f}s")
    return sum(1 for r in resultados if r["status"].startswith("MISS"))


est1 = Estatisticas()
cache1 = CacheTTL(ttl_segundos=300)
rodada("RODADA 1: cache-aside ingênuo", lambda: analisar(PERGUNTA, cache1, est1))
print(f"→ chamadas à IA: {est1.chamadas_ia} (todas para a MESMA pergunta)\n")

est2 = Estatisticas()
cache2 = CacheTTL(ttl_segundos=300)
sf = SingleFlight()
rodada("RODADA 2: com request coalescing (single flight)", lambda: analisar_coalescido(PERGUNTA, cache2, est2, sf))
print(f"→ chamadas à IA: {est2.chamadas_ia}")

print(f"\nO stampede custou {est1.chamadas_ia - est2.chamadas_ia} chamadas a mais, "
      "e num pico de verdade ainda poderia estourar o rate limit (429).")
