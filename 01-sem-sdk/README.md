# 01 — Sem SDK (ChatGPT / OpenAI)

**Seção da nota:** "Na prática: chamar um LLM com e sem SDK" (parte sem SDK)

Você monta a requisição HTTP sozinho: precisa saber a **URL**, os **headers**, o **formato do JSON** e como **tratar erros e retries**.

| Arquivo | O que faz |
|---|---|
| `chamada_http.py` | Chamada em Python só com a biblioteca padrão, em 5 passos comentados |
| `chamada_curl.sh` | A mesma chamada com `curl` |

**Precisa de:** `OPENAI_API_KEY` e `MODELO_OPENAI` no `.env` (chamada real).

```bash
python chamada_http.py
./chamada_curl.sh
```

**Repare:**
- Tudo está preso à OpenAI: a URL, o header `Authorization: Bearer` e o formato `choices[0].message.content`. Trocar de provedor = reescrever tudo. A Anthropic, por exemplo, usa outra URL, o header `x-api-key` e devolve `content[]`.
- Usamos `max_completion_tokens` (e não `max_tokens`), porque modelos de raciocínio gastam parte dos tokens pensando. Se a resposta vier vazia, aumente esse valor.

**Teste:** coloque uma chave errada e veja o **HTTP 401** com o JSON cru do erro.
