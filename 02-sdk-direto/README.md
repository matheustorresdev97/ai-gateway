# 02 — SDK direto (ChatGPT / OpenAI)

**Seção da nota:** "SDK DIRETO vs GATEWAY" (degrau 1: SDK direto)

A mesma chamada do `01-sem-sdk`, agora com o **SDK oficial da OpenAI**. Por baixo continua sendo a mesma requisição HTTP, mas o SDK esconde a **URL** e os **headers** e já traz **retry**, **timeout** e **classes de erro** prontos.

| Arquivo | O que faz |
|---|---|
| `openai_sdk.py` | Chamada com o SDK `openai`, tratando cada tipo de erro com uma classe própria |

**Precisa de:** `OPENAI_API_KEY` e `MODELO_OPENAI` no `.env` (chamada real) e o pacote `openai` instalado (`pip install -r requirements.txt`).

```bash
python openai_sdk.py
```

**Repare:**
- Compare com o `chamada_http.py`: sumiram a URL, o header `Authorization` e o `json.dumps`. O SDK lê a `OPENAI_API_KEY` do ambiente sozinho.
- A resposta é um **objeto** (`resposta.choices[0].message.content`), não um dicionário. O editor autocompleta os campos.
- Os erros viram exceções com nome (`AuthenticationError`, `NotFoundError`, `RateLimitError`...). Em `RateLimitError` o SDK já tentou de novo antes de desistir.
- **Vantagens:** rápido de implementar, menor abstração.
- **Problema:** continua **acoplado ao provedor**. Este código só fala com a OpenAI; trocar para Gemini ou Anthropic = outro SDK, outro formato, outro tratamento de erro. É esse problema que o gateway resolve nos próximos exemplos.

**Teste:** coloque uma chave errada e veja a mensagem **"Chave inválida"** vinda do `AuthenticationError`, em vez do JSON cru do HTTP 401 do `01-sem-sdk`. Depois troque o `MODELO_OPENAI` por um nome inexistente e veja o `NotFoundError`.
