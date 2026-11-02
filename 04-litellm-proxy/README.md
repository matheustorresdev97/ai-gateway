# 04 — LiteLLM Proxy (o gateway)

**Seção da nota:** "LiteLLM como Proxy", "Fluxo de Requisição e Mudança de Responsabilidade", "Gatekeeping Interno do Proxy" e "LiteLLM Proxy — Fluxo de Requisição"

```
APLICAÇÃO ──Bearer Token (HTTP)──► PROXY ──HTTP──► PROVIDER
          ◄────── resposta JSON ──       ◄──────
```

O LiteLLM sai de dentro da aplicação e vira um **serviço separado**: a nova fronteira arquitetural. Ele esconde as chaves reais, padroniza o acesso, registra o uso e centraliza a configuração.

| Arquivo | O que faz |
|---|---|
| `config.yaml` | Os modelos que o gateway oferece (`chatgpt`, `gemini`) e as chaves reais |
| `iniciar_proxy.sh` | Sobe o gateway em `http://localhost:4000` |
| `cliente_openai_sdk.py` | Aplicação usando o **SDK da OpenAI apontado para o proxy** e falando com ChatGPT e Gemini |
| `cliente_curl.sh` | A mesma chamada com `curl` |

```bash
# Terminal 1
./iniciar_proxy.sh

# Terminal 2 (com o .venv ativado)
python cliente_openai_sdk.py
./cliente_curl.sh gemini
```

**Repare:**
- A aplicação só conhece a URL do gateway e a `LITELLM_MASTER_KEY`. **Nenhuma chave real de provedor.**
- Se só um provedor tiver chave no `.env`, o outro responde **401**: o erro vem do provedor, através do gateway.
- O header `x-litellm-model-name` mostra qual modelo real o gateway chamou.
- Compare `cliente_curl.sh` com `01-sem-sdk/chamada_curl.sh`: mesma ideia, mas o formato agora é um só para qualquer provedor.
