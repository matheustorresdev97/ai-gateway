# 09 — Cache: aplicação, gateway e provedor

**Nota:** "Cache" (seções "Hit, miss e cache-aside", "TTL, resposta stale e invalidação", "Fingerprint de prompt e contexto", "Similaridade, distância e threshold", "Cache semântico no fluxo principal", "Camadas de cache" e "Como OpenAI, Anthropic e Gemini tratam prompt caching")

A pasta 08 decide **como** executar a chamada. Esta decide **se ela precisa acontecer** e, quando precisa, como deixá-la mais barata. Exemplo: um **analisador de tickets** de um serviço de streaming que devolve `{categoria, confianca, motivo}`.

```
                     ┌──────────── APLICAÇÃO ────────────┐   ┌─ GATEWAY ─┐   ┌──── PROVEDOR ────┐
requisição ──► cache exato ──► cache semântico (pgvector) ──► cache LiteLLM ──► prompt caching ──► modelo
               (1, 2)          (3, 4)                         (5)               (6)
               "preciso chamar a IA?"                         "chamada igual?"  "que parte do prompt é repetida?"
```

| Arquivo | O que mostra |
|---|---|
| `config.yaml` | Capacidades `classificacao-tickets`, `embedding`, `explicacao` e `politicas`; cache do gateway em modo **opt-in** |
| `docker-compose.yml` | PostgreSQL + **pgvector** na porta 5433 (exemplos 3 e 4) |
| `cache_app.py` | As peças do cache da aplicação: normalização, **fingerprint**, cache com **TTL**, validação antes de gravar |
| `1_cache_exato.py` | Cache-aside: hit, miss, normalização, **troca de versão do prompt** muda a chave, **TTL** vencendo, limite do cache exato |
| `2_stampede.py` | 8 usuários com a mesma pergunta nova ao mesmo tempo: **8 chamadas** sem proteção, **1** com _request coalescing_ |
| `3_cache_semantico.py` | Cadeia **exato → semântico → IA** com pgvector, threshold, promoção para o cache exato e **isolamento por tenant** |
| `4_calibrar_threshold.py` | Similaridade real de pares rotulados: de onde vem (e por que é difícil) o número do threshold |
| `5_cache_no_gateway.py` | Cache do **LiteLLM**: hit em milissegundos, chave exata e o gateway guardando um **JSON quebrado** |
| `6_prompt_caching.py` | Cache do **provedor**: `cached_tokens` subindo com prefixo fixo e zerando com a **hora no topo** do prompt |

```bash
# Terminal 1
./iniciar_proxy.sh

# Terminal 2 (com o .venv ativado)
docker compose up -d          # só para o 3 (o 4 não usa banco)
python 1_cache_exato.py
python 2_stampede.py
python 3_cache_semantico.py
python 4_calibrar_threshold.py
python 5_cache_no_gateway.py
python 6_prompt_caching.py
docker compose down           # ao terminar
```

O modelo de embedding sai do `.env` automaticamente (`_comum/provedores.sh`): `text-embedding-3-small` com chave do ChatGPT, `gemini-embedding-001` só com a do Gemini.

**Repare:**
- **Cache exato (1):** o hit volta em **décimos de milissegundo** e o miss em ~1 s. O passo 4 (prompt `v2`, regra nova de retenção) dá **miss sozinho** e classifica como `retencao`: a versão está no fingerprint, então a resposta antiga **não** é servida. A entrada `v1` continua lá até o TTL vencer (passo 5). O passo 7 mostra o limite: mesma intenção com outras palavras é miss.
- **Stampede (2):** na rodada 1 as 8 threads chamam a IA. Na 2, uma chama e as outras 7 esperam a trava e leem do cache. O `if` repetido **dentro** da trava é o que faz funcionar.
- **Semântico (3):** a paráfrase próxima é reaproveitada (score ~0,96). "Como **ativo** minha assinatura?" tem score **~0,71** com "Como **cancelo**...": o threshold 0,80 barra, mas com 0,70 seria um **falso positivo**. "Quero encerrar meu plano" (mesma intenção) tem só ~0,51: falso negativo, custa uma chamada. O hit semântico leva ~0,7 s, quase tudo para **gerar o embedding**: é mais rápido que a IA, mas não é de graça. Teste outro corte com `THRESHOLD=0.70 python 3_cache_semantico.py`.
- **Calibração (4):** com frases curtas em português, os grupos **se sobrepõem** (um par "diferente" tem similaridade maior que um par "mesma intenção"). Nenhum número acerta tudo: escolha qual erro é mais caro. Trocou o modelo de embedding, recalibre.
- **Gateway (5):** a chave do LiteLLM é a requisição inteira (inclusive o `user`). Ele não normaliza, não entende intenção e **não valida**: guarda e devolve o JSON truncado. O header `x-litellm-cache-key` indica que a resposta saiu do cache do gateway.
- **Provedor (6):** do 2º pedido em diante, ~98% da entrada vem do cache (o valor de `cached_tokens` cresce em blocos de 128 tokens). Com a hora no **topo** do system prompt cai para 0; com a hora no **fim**, volta. O cache do provedor **não evita** a chamada: a resposta é gerada do mesmo jeito.
- No exemplo, o cache da aplicação fica em memória (um por processo). Em produção seria Redis, compartilhado entre réplicas; o cache do gateway também (`cache_params.type: redis`).
