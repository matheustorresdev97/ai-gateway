"""
Nota AI Gateways → "Na prática: chamar um LLM com e sem SDK" (sem SDK)

Chamada à API do ChatGPT (OpenAI) montando a requisição HTTP sozinho:
URL, headers, formato do JSON e tratamento de erros. Só biblioteca padrão.
"""

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

comum.exigir("OPENAI_API_KEY", "MODELO_OPENAI")

# 1. A URL: você precisa saber qual é (endpoint de Chat Completions).
URL = "https://api.openai.com/v1/chat/completions"

# 2. Os headers exigidos pela API (a OpenAI usa Bearer Token).
headers = {
    "Authorization": f"Bearer {comum.valor('OPENAI_API_KEY')}",
    "content-type": "application/json",
}

# 3. O corpo no formato exato da API.
corpo = {
    "model": comum.valor("MODELO_OPENAI"),
    # max_completion_tokens (e não max_tokens): funciona também nos modelos
    # de raciocínio, que gastam parte dos tokens "pensando" antes de responder.
    "max_completion_tokens": 2000,
    "messages": [{"role": "user", "content": comum.PERGUNTA}],
}

requisicao = urllib.request.Request(
    URL, data=json.dumps(corpo).encode("utf-8"), headers=headers, method="POST"
)

# 4. Enviar e tratar erros: sem retry, sem classes de erro. Tudo é código seu.
try:
    with urllib.request.urlopen(requisicao, timeout=120) as resposta_http:
        resposta = json.loads(resposta_http.read().decode("utf-8"))
except urllib.error.HTTPError as erro:
    raise SystemExit(f"❌ Erro HTTP {erro.code}:\n{erro.read().decode('utf-8')}")
except urllib.error.URLError as erro:
    raise SystemExit(f"❌ Falha de conexão: {erro.reason}")

# 5. A resposta é um dicionário: você precisa conhecer a estrutura.
escolha = resposta["choices"][0]
texto = escolha["message"]["content"]
if not texto and escolha.get("finish_reason") == "length":
    raise SystemExit("⚠️ Acabaram os tokens antes da resposta. Aumente max_completion_tokens.")

print(f"modelo: {resposta['model']}")
print(f"tokens: entrada={resposta['usage']['prompt_tokens']} saída={resposta['usage']['completion_tokens']}")
print("-" * 60)
print(texto)
