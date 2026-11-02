"""
Nota AI Gateways → "LiteLLM como primeira implementação da compatibilidade"
                   (degrau 2: LiteLLM como SDK, dentro da aplicação)

Aplicação (LiteLLM como SDK) → Tradução (normaliza, adapta) → Provider real

A chamada completion(...) é IDÊNTICA para os provedores; só muda o prefixo
do modelo. A resposta volta sempre no mesmo formato (o da OpenAI).

Limite (nota): no modo SDK a configuração fica distribuída e a lógica se
repete em cada aplicação. Isso é o que o proxy (pasta 04) resolve.
"""

import sys
from pathlib import Path

import litellm
from litellm import completion

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

# Descarta parâmetros que um provedor não aceita, em vez de dar erro.
litellm.drop_params = True

PROVEDORES = [
    ("ChatGPT (OpenAI)", "openai", "MODELO_OPENAI", "OPENAI_API_KEY"),
    ("Gemini (Google)", "gemini", "MODELO_GEMINI", "GEMINI_API_KEY"),
]

usados = 0
for nome, prefixo, var_modelo, var_chave in PROVEDORES:
    print("=" * 60 + f"\n{nome}\n" + "=" * 60)
    if not (comum.preenchido(var_modelo) and comum.preenchido(var_chave)):
        print(f"⏭️  Pulado: preencha {var_modelo} e {var_chave} no .env.\n")
        continue
    usados += 1

    try:
        # ↓ A MESMA chamada para qualquer provedor.
        resposta = completion(
            model=f"{prefixo}/{comum.valor(var_modelo)}",
            api_key=comum.valor(var_chave),
            messages=[{"role": "user", "content": comum.PERGUNTA}],
            max_tokens=2000,
        )
        # ↓ A MESMA forma de ler a resposta (normalizada para o padrão OpenAI).
        print(f"modelo: {resposta.model}")
        print(resposta.choices[0].message.content or "(resposta vazia: aumente max_tokens)")
    # ↓ Os MESMOS erros, qualquer que seja o provedor.
    except litellm.AuthenticationError:
        print("❌ Chave inválida.")
    except litellm.NotFoundError:
        print("❌ Modelo não encontrado.")
    except litellm.RateLimitError:
        print("❌ Limite de requisições ou de créditos atingido.")
    except litellm.APIConnectionError:
        print("❌ Falha de conexão com o provedor.")
    except litellm.APIError as erro:
        print(f"❌ Erro da API: {erro}")
    print()

if usados == 0:
    raise SystemExit("❌ Preencha no .env a chave e o modelo do ChatGPT e/ou do Gemini.")
