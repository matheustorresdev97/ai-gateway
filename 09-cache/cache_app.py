"""
Peças do CACHE DA APLICAÇÃO, usadas pelos exemplos 1 a 4.

Nota Cache → "Hit, miss e cache-aside", "TTL, resposta stale e invalidação"
             e "Fingerprint de prompt e contexto"

  normalizar()          → "Quero CANCELAR " e "quero cancelar" viram a mesma coisa
  fingerprint()         → hash de TUDO o que muda a resposta (não só a mensagem)
  CacheTTL              → cache em memória com prazo de validade (thread-safe)
  classificar_com_ia()  → a chamada real ao modelo, via gateway
  resposta_valida()     → nunca gravar no cache uma saída quebrada (cache poisoning)
  gerar_embeddings()    → texto → vetor, via capacidade "embedding" do gateway
  analisar()            → o fluxo cache-aside completo
"""

import hashlib
import json
import re
import sys
import threading
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

client = OpenAI(base_url=f"{comum.URL_PROXY}/v1", api_key=comum.valor("LITELLM_MASTER_KEY"), max_retries=0)

CAPACIDADE = "classificacao-tickets"
REGRAS_VERSAO = "regras-2026-11"
CATEGORIAS = {"cancelamento", "retencao", "cobranca", "suporte_tecnico", "outros"}

_FORMATO = ('Responda SOMENTE um JSON: {"categoria": "<categoria>", "confianca": <0.0 a 1.0>, '
            '"motivo": "<frase curta>"}')

# Duas versões do system prompt. A v2 muda a REGRA DE NEGÓCIO: quem quer cancelar
# por causa do preço passa a ir para o time de retenção.
PROMPTS = {
    "triagem-v1": (
        "Você classifica mensagens de clientes de um serviço de streaming por assinatura. "
        "Categorias: cancelamento, cobranca, suporte_tecnico, outros. " + _FORMATO
    ),
    "triagem-v2": (
        "Você classifica mensagens de clientes de um serviço de streaming por assinatura. "
        "Categorias: cancelamento, retencao, cobranca, suporte_tecnico, outros. "
        "Use 'retencao' quando o cliente quer cancelar POR CAUSA DO PREÇO. " + _FORMATO
    ),
}


# ------------------------------------------------------------------ chave
def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFC", texto).strip().lower()
    return re.sub(r"\s+", " ", texto)


def fingerprint(mensagem: str, prompt_versao: str, tenant: str = "loja-a") -> str:
    """Chave = tenant + versão do prompt (e hash do texto) + regras + capacidade + mensagem."""
    payload = {
        "prompt_versao": prompt_versao,
        # o hash do texto pega a edição de prompt feita sem trocar o número da versão
        "prompt_hash": hashlib.sha256(PROMPTS[prompt_versao].encode()).hexdigest()[:8],
        "regras": REGRAS_VERSAO,
        "capacidade": CAPACIDADE,
        "mensagem": normalizar(mensagem),
    }
    canonico = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    # o tenant fica FORA do hash: dá para auditar e limpar por cliente
    return f"{tenant}:{hashlib.sha256(canonico.encode()).hexdigest()[:12]}"


# ------------------------------------------------------------------ cache
class CacheTTL:
    """Cache em memória com TTL. Em produção: Redis (compartilhado entre réplicas)."""

    def __init__(self, ttl_segundos: float):
        self.ttl = ttl_segundos
        self._dados: dict[str, tuple[dict, float]] = {}
        self._trava = threading.Lock()

    def get(self, chave: str):
        with self._trava:
            item = self._dados.get(chave)
            if item is None:
                return None
            valor, expira_em = item
            if time.monotonic() >= expira_em:      # vencido: vale como ausência
                del self._dados[chave]
                return None
            return valor

    def set(self, chave: str, valor: dict) -> None:
        with self._trava:
            self._dados[chave] = (valor, time.monotonic() + self.ttl)


# ------------------------------------------------------------------ IA
@dataclass
class Estatisticas:
    hits: int = 0
    misses: int = 0
    chamadas_ia: int = 0
    tokens_gastos: int = 0
    tokens_poupados: int = 0
    tempos_hit: list = field(default_factory=list)
    tempos_miss: list = field(default_factory=list)
    _trava: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def hit_ratio(self) -> float:
        total = self.hits + self.misses
        return self.hits / total if total else 0.0


def classificar_com_ia(mensagem: str, prompt_versao: str) -> tuple[dict | None, int]:
    """Chamada REAL ao modelo via gateway. Devolve (resposta ou None, tokens gastos)."""
    try:
        resposta = client.chat.completions.create(
            model=CAPACIDADE,
            messages=[
                {"role": "system", "content": PROMPTS[prompt_versao]},
                {"role": "user", "content": mensagem},
            ],
            response_format={"type": "json_object"},
            temperature=0,
            max_tokens=300,
        )
    except openai.APIConnectionError:
        raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
    except openai.APIStatusError as erro:
        raise SystemExit(f"❌ HTTP {erro.status_code}: {erro.message}")

    tokens = resposta.usage.total_tokens if resposta.usage else 0
    try:
        return json.loads(resposta.choices[0].message.content or ""), tokens
    except json.JSONDecodeError:
        return None, tokens


def resposta_valida(r) -> bool:
    return (
        isinstance(r, dict)
        and r.get("categoria") in CATEGORIAS
        and isinstance(r.get("confianca"), (int, float))
        and 0 <= r["confianca"] <= 1
    )


# ------------------------------------------------------------------ embeddings
def modelo_embedding_fisico() -> str:
    """O modelo REAL por trás da capacidade "embedding" (mesma regra do _comum/provedores.sh).

    A aplicação pede a capacidade, mas o banco vetorial precisa saber o modelo físico:
    vetores de modelos diferentes não se comparam (lock-in de espaço vetorial).
    """
    if comum.preenchido("OPENAI_API_KEY") and comum.preenchido("MODELO_OPENAI"):
        return "openai/text-embedding-3-small"
    return "gemini/gemini-embedding-001"


def gerar_embeddings(textos: list[str]) -> list[list[float]]:
    try:
        resposta = client.embeddings.create(model="embedding", input=textos)
    except openai.APIConnectionError:
        raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
    except openai.APIStatusError as erro:
        raise SystemExit(f"❌ HTTP {erro.status_code}: {erro.message}")
    return [d.embedding for d in resposta.data]


# ------------------------------------------------------------------ cache-aside
def analisar(mensagem: str, cache: CacheTTL, est: Estatisticas,
             prompt_versao: str = "triagem-v1", tenant: str = "loja-a") -> dict:
    """Cache-aside: consulta → (hit) devolve | (miss) chama a IA, valida e grava."""
    inicio = time.perf_counter()
    chave = fingerprint(mensagem, prompt_versao, tenant)

    guardado = cache.get(chave)
    if guardado is not None:
        segundos = time.perf_counter() - inicio
        with est._trava:
            est.hits += 1
            est.tokens_poupados += guardado["_tokens"]
            est.tempos_hit.append(segundos)
        return {"status": "HIT", "chave": chave, "resposta": guardado, "segundos": segundos}

    resposta, tokens = classificar_com_ia(mensagem, prompt_versao)
    if resposta_valida(resposta):
        cache.set(chave, {**resposta, "_tokens": tokens})
    segundos = time.perf_counter() - inicio
    with est._trava:
        est.misses += 1
        est.chamadas_ia += 1
        est.tokens_gastos += tokens
        est.tempos_miss.append(segundos)
    return {"status": "MISS", "chave": chave, "resposta": resposta or {}, "segundos": segundos}
