"""
Nota AI Gateways → "SDK DIRETO vs GATEWAY" (degrau 1: SDK direto)

A mesma chamada do 01-sem-sdk, agora com o SDK oficial da OpenAI.
Por baixo é a mesma requisição HTTP: o SDK esconde URL e headers, e traz
retry, timeout e classes de erro prontos.

Vantagens (nota): rápido de implementar, menor abstração.
Problema (nota): ACOPLADO AO PROVEDOR. Este código só fala com a OpenAI.
"""

import sys
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

comum.exigir("OPENAI_API_KEY", "MODELO_OPENAI")

# Sem api_key=..., o SDK lê OPENAI_API_KEY do ambiente (carregado do .env).
client = OpenAI()

try:
    resposta = client.chat.completions.create(
        model=comum.valor("MODELO_OPENAI"),
        max_completion_tokens=2000,
        messages=[{"role": "user", "content": comum.PERGUNTA}],
    )
except openai.AuthenticationError:
    raise SystemExit("❌ Chave inválida (OPENAI_API_KEY no .env).")
except openai.NotFoundError:
    raise SystemExit("❌ Modelo não encontrado (MODELO_OPENAI no .env).")
except openai.RateLimitError:
    raise SystemExit("❌ Limite de requisições ou de créditos atingido (o SDK já tentou de novo).")
except openai.APIStatusError as erro:
    raise SystemExit(f"❌ Erro HTTP {erro.status_code}: {erro.message}")
except openai.APIConnectionError:
    raise SystemExit("❌ Falha de conexão.")

# A resposta é um objeto, não um dicionário.
escolha = resposta.choices[0]
if not escolha.message.content and escolha.finish_reason == "length":
    raise SystemExit("⚠️ Acabaram os tokens antes da resposta. Aumente max_completion_tokens.")

print(f"modelo: {resposta.model}")
print(f"tokens: entrada={resposta.usage.prompt_tokens} saída={resposta.usage.completion_tokens}")
print("-" * 60)
print(escolha.message.content)
