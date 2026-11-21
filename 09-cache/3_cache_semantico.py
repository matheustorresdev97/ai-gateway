"""
Nota Cache → "O que é um modelo de embedding", "Cache semântico não é RAG"
             e "Entendendo a integração do cache semântico no fluxo principal"

Cadeia de prioridade da aula:  cache exato → cache semântico (pgvector) → IA

  1. cache exato em memória (fingerprint)          → HIT exato
  2. embedding da pergunta + top-1 no pgvector,
     FILTRADO por tenant, versão do prompt e modelo de embedding
  3. similaridade ≥ THRESHOLD?  sim → HIT semântico (e promove para o cache exato)
                                não → chama a IA, valida e grava nas DUAS camadas

O banco guarda PERGUNTAS + RESPOSTAS já dadas (não documentos: isso seria RAG).

Antes de rodar:
  docker compose up -d       (banco pgvector na porta 5433)
  ./iniciar_proxy.sh         (em outro terminal)

Threshold: rode o 4_calibrar_threshold.py para ver de onde veio o número.
Para testar outro valor:  THRESHOLD=0.70 python 3_cache_semantico.py
"""

import json
import os
import time

import psycopg

from cache_app import (PROMPTS, CacheTTL, classificar_com_ia, fingerprint, gerar_embeddings,
                       modelo_embedding_fisico, resposta_valida)

THRESHOLD = float(os.environ.get("THRESHOLD", "0.80"))
PROMPT_VERSAO = "triagem-v1"
MODELO_EMB = modelo_embedding_fisico()
URL_BANCO = "postgresql://cache:cache@localhost:5433/cache"

try:
    banco = psycopg.connect(URL_BANCO, autocommit=True)
except psycopg.OperationalError:
    raise SystemExit("❌ Banco fora do ar. Rode: docker compose up -d")

banco.execute("CREATE EXTENSION IF NOT EXISTS vector")
banco.execute("""
    CREATE TABLE IF NOT EXISTS cache_semantico (
        id               bigserial   PRIMARY KEY,
        tenant_id        text        NOT NULL,
        prompt_versao    text        NOT NULL,
        modelo_embedding text        NOT NULL,   -- vetores de modelos diferentes não se comparam
        pergunta         text        NOT NULL,
        resposta         jsonb       NOT NULL,
        embedding        vector      NOT NULL,
        acessos          int         NOT NULL DEFAULT 0,
        criado_em        timestamptz NOT NULL DEFAULT now()
    )""")
banco.execute("TRUNCATE cache_semantico")      # demonstração sempre do zero

cache_exato = CacheTTL(ttl_segundos=600)
chamadas_ia = 0


def vetor_sql(v: list[float]) -> str:
    return "[" + ",".join(f"{x:.6f}" for x in v) + "]"


def responder(pergunta: str, tenant: str = "loja-a") -> dict:
    global chamadas_ia
    inicio = time.perf_counter()

    # 1) cache exato
    chave = fingerprint(pergunta, PROMPT_VERSAO, tenant)
    if (r := cache_exato.get(chave)) is not None:
        return {"camada": "HIT exato", "resposta": r, "score": None, "candidato": None,
                "ms": (time.perf_counter() - inicio) * 1000}

    # 2) cache semântico: top-1 no pgvector, já filtrado (isolamento + versão + modelo)
    vetor = vetor_sql(gerar_embeddings([pergunta])[0])
    linha = banco.execute("""
        SELECT id, pergunta, resposta, 1 - (embedding <=> %s::vector) AS similaridade
        FROM   cache_semantico
        WHERE  tenant_id = %s AND prompt_versao = %s AND modelo_embedding = %s
        ORDER  BY embedding <=> %s::vector          -- <=> é DISTÂNCIA de cosseno: menor = mais perto
        LIMIT  1""", (vetor, tenant, PROMPT_VERSAO, MODELO_EMB, vetor)).fetchone()

    # 3) threshold: a decisão é da aplicação, não do banco
    if linha and linha[3] >= THRESHOLD:
        banco.execute("UPDATE cache_semantico SET acessos = acessos + 1 WHERE id = %s", (linha[0],))
        cache_exato.set(chave, linha[2])            # promove: na próxima, nem gera embedding
        return {"camada": "HIT semântico", "resposta": linha[2], "score": linha[3], "candidato": linha[1],
                "ms": (time.perf_counter() - inicio) * 1000}

    # 4) miss nas duas camadas: IA, validação e gravação nas duas
    resposta, _ = classificar_com_ia(pergunta, PROMPT_VERSAO)
    chamadas_ia += 1
    if resposta_valida(resposta):
        banco.execute("""
            INSERT INTO cache_semantico (tenant_id, prompt_versao, modelo_embedding, pergunta, resposta, embedding)
            VALUES (%s, %s, %s, %s, %s, %s::vector)""",
                      (tenant, PROMPT_VERSAO, MODELO_EMB, pergunta, json.dumps(resposta), vetor))
        cache_exato.set(chave, resposta)
    return {"camada": "MISS → IA", "resposta": resposta or {}, "score": linha[3] if linha else None,
            "candidato": linha[1] if linha else None, "ms": (time.perf_counter() - inicio) * 1000}


def mostrar(pergunta: str, r: dict, tenant: str = "loja-a") -> None:
    score = f"{r['score']:.3f}" if r["score"] is not None else "  -  "
    print(f"[{tenant}] {pergunta}")
    print(f"         {r['camada']:<14} score {score}  {r['ms']:>7.1f} ms  → {r['resposta'].get('categoria', '?')}")
    if r["candidato"] and r["camada"] != "HIT exato":
        print(f"         candidato mais próximo: \"{r['candidato']}\"")


print(f"capacidade 'embedding' → {MODELO_EMB} | threshold = {THRESHOLD:.2f} | prompt = {PROMPT_VERSAO}")
print(f"(regra do prompt: {PROMPTS[PROMPT_VERSAO][:60]}...)\n")

print("=" * 72 + "\nAQUECENDO: três perguntas novas (cache vazio)\n" + "=" * 72)
for p in ["Como cancelo minha assinatura?", "Meu boleto veio duplicado", "O aplicativo não abre na TV"]:
    mostrar(p, responder(p))

print("\n" + "=" * 72 + "\nPERGUNTAS NOVAS\n" + "=" * 72)
testes = [
    "Como faço para cancelar a minha assinatura?",   # paráfrase próxima
    "Como ativo minha assinatura?",                  # intenção OPOSTA, palavras parecidas
    "Quero encerrar meu plano",                      # mesma intenção, palavras diferentes
    "Como faço para cancelar a minha assinatura?",   # repetida: agora no cache exato
]
riscos = []
for p in testes:
    r = responder(p)
    mostrar(p, r)
    if r["score"] is not None and r["camada"] == "MISS → IA" and r["score"] >= 0.70:
        riscos.append((p, r["score"], r["candidato"]))

print("\n" + "=" * 72 + "\nISOLAMENTO POR TENANT\n" + "=" * 72)
mostrar("Como cancelo minha assinatura?", responder("Como cancelo minha assinatura?", "loja-b"), "loja-b")

print("\n" + "=" * 72 + "\nRESUMO\n" + "=" * 72)
print(f"chamadas à IA: {chamadas_ia} de {3 + len(testes) + 1} perguntas")
for pergunta, acessos in banco.execute(
        "SELECT pergunta, acessos FROM cache_semantico WHERE acessos > 0 ORDER BY id"):
    print(f"reaproveitada {acessos}x pelo cache semântico: \"{pergunta}\"")
for p, score, candidato in riscos:
    print(f"⚠️  \"{p}\" teve score {score:.3f} com \"{candidato}\": com threshold 0.70 "
          "seria um HIT e devolveria a resposta ERRADA (falso positivo).")
