"""
Nota Cache → "Camadas de cache em aplicações com IA" e
             "Cache da aplicação não é cache do provider"

O cache NO GATEWAY (LiteLLM, cache em memória, ttl 600s). No config.yaml ele
está em modo "default_off": só cacheia quando a requisição pede com
{"cache": {"use-cache": true}}.

  1. mesma requisição duas vezes          → a 2ª vem do gateway, sem chamar o modelo
  2. mesma pergunta, outro `user`         → MISS: o LiteLLM põe o `user` na chave
  3. mesma pergunta, outra pontuação      → MISS: o gateway é cache EXATO, sem normalizar
  4. resposta truncada (max_tokens=8)     → o gateway guarda o JSON quebrado e o serve de novo:
                                            ele não sabe o que é uma resposta válida
  5. "no-cache": true                     → pula o cache e vai ao modelo

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import sys
import time
import uuid
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

client = OpenAI(base_url=f"{comum.URL_PROXY}/v1", api_key=comum.valor("LITELLM_MASTER_KEY"), max_retries=0)

# Um sufixo novo a cada execução: assim rodar o script de novo não acerta o cache da rodada anterior.
RODADA = uuid.uuid4().hex[:6]
PERGUNTA = f"Em uma frase: o que é cache? (rodada {RODADA})"
USA_CACHE = {"cache": {"use-cache": True}}


def chamar(rotulo: str, mensagens: list, extra: dict = USA_CACHE, max_tokens: int = 80, **kwargs) -> None:
    inicio = time.perf_counter()
    try:
        bruto = client.chat.completions.with_raw_response.create(
            model="explicacao", messages=mensagens, max_tokens=max_tokens, temperature=0,
            extra_body=extra, **kwargs,
        )
    except openai.APIConnectionError:
        raise SystemExit("❌ Proxy fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
    ms = (time.perf_counter() - inicio) * 1000
    resposta = bruto.parse()
    # o LiteLLM devolve este header quando a resposta saiu do cache dele
    chave = bruto.headers.get("x-litellm-cache-key")
    origem = f"CACHE DO GATEWAY (chave {chave[:10]}…)" if chave else "modelo"
    texto = (resposta.choices[0].message.content or "").replace("\n", " ")
    print(f"{rotulo:<34} {ms:>7.0f} ms  {origem:<36} {texto[:45]!r}")


def usuario(texto: str) -> list:
    return [{"role": "user", "content": texto}]


print(f"{'passo':<34} {'tempo':>10}  {'origem':<36} resposta")
print("-" * 120)
chamar("1a. primeira vez", usuario(PERGUNTA), user="loja-a")
chamar("1b. mesma requisição", usuario(PERGUNTA), user="loja-a")
chamar("2.  outro user (loja-b)", usuario(PERGUNTA), user="loja-b")
chamar("3.  outra pontuação", usuario(PERGUNTA.replace(":", ",")), user="loja-a")

json_curto = [
    {"role": "system", "content": 'Responda SOMENTE um JSON {"categoria": "...", "motivo": "..."}'},
    {"role": "user", "content": f"Meu boleto veio duplicado ({RODADA})"},
]
chamar("4a. JSON truncado (max_tokens=8)", json_curto, max_tokens=8)
chamar("4b. de novo", json_curto, max_tokens=8)
chamar("5.  no-cache: true", json_curto, extra={"cache": {"use-cache": True, "no-cache": True}}, max_tokens=8)

print("""
Repare:
- 1b volta em milissegundos: o modelo nem foi chamado (o gateway respondeu).
- 2 e 3 são MISS: a chave do gateway é a requisição inteira (modelo, mensagens, parâmetros, user).
  Ele não normaliza o texto nem entende intenção: isso é papel da aplicação.
- 4b serve o JSON QUEBRADO do cache. O gateway não sabe o que é uma resposta válida para o seu domínio;
  a aplicação valida antes de gravar (veja cache_app.resposta_valida).
- O gateway também não conhece a versão das suas regras: se elas não estiverem no prompt, a chave não muda.""")
