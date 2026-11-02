# 05 — Capacidades e Router

**Seção da nota:** "LiteLLM Proxy e Router", "Tradução de Requisições e Normalização de Respostas" e "Expondo capacidades, não modelos físicos" (Gateway técnico)

A aplicação pede uma **capacidade** (nome lógico), não um provider:

```
CAPACIDADE INTERNA        MAPEAMENTO (config.yaml)          PROVIDER FÍSICO
classificador-simples  ─►  modelo secundário             ─►  Gemini
resposta-suporte       ─►  2 deployments (principal e    ─►  ChatGPT ou Gemini (o router escolhe)
                           secundário)
extracao-documento     ─►  modelo principal              ─►  ChatGPT
analise-profunda       ─►  modelo principal              ─►  ChatGPT
```

- **Model group:** o nome lógico que a aplicação enxerga.
- **Deployment:** configuração concreta que aponta para um modelo real.
- **Router:** decide qual deployment do grupo atende cada requisição.

```bash
# Terminal 1
./iniciar_proxy.sh

# Terminal 2
python cliente_capacidades.py
```

**Repare:**
- As três perguntas de `resposta-suporte` podem cair em modelos diferentes: o router está distribuindo.
- **Exercício da nota ("se o provedor mudar, seus nomes permanecem"):** no `config.yaml`, troque `MODELO_PRINCIPAL`/`CHAVE_PRINCIPAL` de `analise-profunda` por `MODELO_SECUNDARIO`/`CHAVE_SECUNDARIO` (outro provider) e reinicie o proxy. Rode o cliente de novo **sem mudar nenhuma linha dele**.
- A abstração protege a aplicação, mas **não elimina o modelo físico**: o header `x-litellm-model-name` mostra quem respondeu de verdade.

**Principal e secundário:** o `iniciar_proxy.sh` define sozinho a partir do `.env`. Com ChatGPT e Gemini, principal = ChatGPT e secundário = Gemini. Com só um, os dois apontam para ele (o router continua funcionando, mas sempre cai no mesmo provedor). O script mostra o mapeamento ao subir.
