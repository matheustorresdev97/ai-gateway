# 06 — Resiliência: timeout, retry e fallback

**Seção da nota:** "Resiliência — timeout, retry e fallback", "Retry: comportamento e riscos", "Árvore de fallback" e "Decisões arquiteturais"

Decisão da nota: **centralizar a resiliência no gateway.** O cliente só pede a capacidade; quem tenta de novo e troca de caminho é o gateway.

| Capacidade | Política de timeout | Problema simulado no principal | Fallback |
|---|---|---|---|
| `atendimento` | rápido (5s) | provedor **lento** (`provedor_simulado.py`, demora 15s) | modelo principal (real) |
| `analise-longa` | mais tempo (120s) | provedor **fora do ar** (porta sem ninguém) | modelo secundário (real) |

O **problema** é simulado de propósito (provedor lento e provedor caído), porque não dá para derrubar a OpenAI ou o Google de verdade. O **fallback** é uma chamada **real** ao ChatGPT ou ao Gemini do seu `.env` (com os dois: principal = ChatGPT, secundário = Gemini).

```bash
# Terminal 1: o provedor com problema
python provedor_simulado.py

# Terminal 2: o gateway
./iniciar_proxy.sh

# Terminal 3: o cliente
python testar_resiliencia.py
```

**Repare:**
- **Atendimento leva cerca de 13s**: 5s da tentativa principal + 5s do **retry** + o fallback. É o risco da nota: *retry custa latência, dinheiro e pressão no provider*. Mude `num_retries` para `0` no `config.yaml` e compare.
- **Análise longa é rápida** apesar do timeout de 120s: conexão recusada falha na hora, e o fallback entra.
- O header `x-litellm-attempted-fallbacks: 1` mostra que o caminho alternativo foi usado. O cliente nem percebe.
- **A resposta pode mudar** (qualidade, formato, estilo): no fallback é outro modelo respondendo.
