# 03 — Compatibilidade com LiteLLM (modo SDK)

**Seção da nota:** "Compatibilidade — a primeira capacidade de uma AI Gateway" e "LiteLLM como primeira implementação da compatibilidade"

```
Aplicação (LiteLLM como SDK) → Tradução (normaliza, adapta) → Provider real (OpenAI, Anthropic, Google)
```

A chamada `completion(...)` é **a mesma** para ChatGPT e Gemini; só muda o prefixo do modelo (`openai/`, `gemini/`). Para qualquer outro provedor seria igual (ex.: `anthropic/`). A resposta volta sempre no formato da OpenAI (`choices[0].message.content`), e os erros saem padronizados.

```bash
python litellm_sdk.py
```

**Chamadas reais.** Precisa da chave e do modelo de pelo menos um provedor no `.env`; o que estiver sem chave é pulado.

**Repare no limite (nota):** no modo SDK o LiteLLM roda *dentro* da aplicação. A configuração fica distribuída (cada aplicação com suas chaves) e a lógica se repete. A pasta 04 tira isso da aplicação.

> Compatibilidade **não** significa igual: a interface é comum, mas cada modelo continua com sua qualidade, estilo e comportamento.
