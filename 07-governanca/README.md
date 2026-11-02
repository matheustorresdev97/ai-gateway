# 07 — Governança: virtual keys, limites, custo e observabilidade

**Seção da nota:** "Virtual Key", "Rate limiting & cost-control", "Governança mínima — acesso, custo e limites", "Observabilidade e impacto arquitetural" e "Camada de IA compartilhada com governança"

Este gateway tem **banco de dados** (Postgres), onde guarda as virtual keys, os gastos e um log por chamada. Por isso roda com **Docker**.

| Aplicação | Acesso (nota) | Capacidades | Orçamento | rpm |
|---|---|---|---|---|
| App A | completo | `classificacao-simples` + `analise-critica` | US$ 10 | 60 |
| App B | limitado | só `classificacao-simples` | US$ 2 | 30 |
| App C | restrito | só `classificacao-simples` | US$ 0,50 | **2** |

- `classificacao-simples` → modelo secundário (o barato; Gemini se houver chave), limite alto
- `analise-critica` → modelo principal (o caro; ChatGPT se houver chave), controle mais rigoroso
- Com só um provedor no `.env`, as duas capacidades usam o mesmo, e as **regras de acesso continuam valendo** (403, 429).

| Arquivo | O que faz |
|---|---|
| `docker-compose.yml` + `config.yaml` | Gateway + banco |
| `iniciar_gateway.sh` | Carrega o `.env` e sobe tudo |
| `criar_virtual_keys.py` | O admin (master key) emite uma virtual key por aplicação |
| `testar_acessos.py` | Cada app usa a sua key: permitido, 403 (sem acesso ao modelo) ou 429 (limite) |
| `ver_uso.py` | Gasto por aplicação + **log compacto por chamada** |

```bash
# Terminal 1 (a primeira vez baixa as imagens, ~1,7 GB)
./iniciar_gateway.sh

# Terminal 2 (com o .venv ativado)
python criar_virtual_keys.py
python testar_acessos.py
python ver_uso.py          # os logs podem levar ~1 min para aparecer
```

**O que você deve ver:**
- **App B e App C recebem 403** ao pedir `analise-critica`: acesso negado pela key.
- **App C recebe 429** a partir da 2ª requisição seguida: passou do rpm=2. A 1ª chamada do teste 1 já contou dentro do mesmo minuto.
- No `ver_uso.py`, cada chamada aparece com aplicação, capacidade, modelo físico, status, tokens e custo.
- As chamadas são **reais**: o gasto de cada key sobe e o orçamento passa a valer. Se algum custo aparecer 0, o LiteLLM pode não conhecer o preço daquele modelo.

**Lembrete da nota:** o gateway **registra, bloqueia e controla**, mas não define os limites sozinho. Os números das keys vêm de políticas da organização, de produto, de finanças e de risco.

**Parar:** Ctrl+C e depois `docker compose down` (use `docker compose down -v` para apagar o banco e as keys).
