# 08 — Fluxos de chamada: síncrono, streaming e job assíncrono

**Nota:** "Fluxos de Chamada" (seções "Quando síncrono faz sentido", "Streaming e latência percebida" e "Quando transformar IA em processamento assíncrono")

As pastas 01 a 07 decidem **por onde** a chamada passa (o gateway). Esta decide **como** ela é executada:

```
Precisa terminar na request? ──não──► JOB ASSÍNCRONO   (3_job_assincrono.py)
        │ sim
Resposta curta e estruturada? ──sim──► SÍNCRONO        (1_sincrono.py)
        │ não
O parcial tem valor? ──sim──► STREAMING                (2_streaming.py)
        └─────────────não──► JOB ASSÍNCRONO
```

| Arquivo | O que mostra |
|---|---|
| `config.yaml` | Uma capacidade por fluxo (`classificacao`, `explicacao`, `analise`), cada uma com sua política de timeout |
| `iniciar_proxy.sh` | Sobe o gateway em `http://localhost:4000` |
| `1_sincrono.py` | Mesmo fluxo síncrono para duas tarefas: a classificação volta rápido; o relatório longo **estoura o timeout** de 8s do cliente |
| `2_streaming.py` | A mesma explicação síncrona e em streaming: compara **TTFT** (primeiro texto visível) e tempo total |
| `3_job_assincrono.py` | Request que responde na hora (202), **fila + worker**, estado explícito, polling, **retry com backoff**, **DLQ** e **idempotência** na criação e no worker |

```bash
# Terminal 1
./iniciar_proxy.sh

# Terminal 2 (com o .venv ativado)
python 1_sincrono.py
python 2_streaming.py
python 3_job_assincrono.py
```

**Repare:**
- **Síncrono:** o problema não é só o erro, é a conexão presa e o usuário sem nada por 8s. Se o modelo for rápido e o relatório voltar a tempo, rode de novo ou reduza `TIMEOUT_CLIENTE`: o tempo varia a cada chamada, e essa imprevisibilidade é o ponto da nota.
- **Streaming:** o tempo **total** é parecido nos dois modos; o que cai é o tempo até o primeiro texto. Streaming melhora a latência **percebida**. Modelos de raciocínio aumentam o TTFT, porque "pensam" antes de escrever.
- **Job:** as quatro requests respondem em milissegundos. O `pedido-1` repetido (clique duplo) **não** vira um segundo processamento. O `pedido-2` falha de propósito na 1ª tentativa (falha transiente) e passa no retry. O `pedido-3` pede uma capacidade que não existe (erro permanente, HTTP 400): vai **direto** para a DLQ, porque tentar de novo não resolve.
- **Idempotência dos dois lados:**
  - **Na criação** (`criar_job`): a chave de idempotência barra o pedido repetido do **cliente** (clique duplo, retry após timeout).
  - **No worker** (`reivindicar`): a fila reentrega a mensagem do `pedido-1`, como Kafka, SQS e RabbitMQ podem fazer (entrega *at-least-once*). O worker vê que o job já foi concluído e só confirma a mensagem. No final, cada pedido mostra **1 chamada à IA**.
  - Verificar e marcar acontecem juntos, sob a trava, para dois workers nunca pegarem o mesmo job. Em banco, o equivalente é um `UPDATE ... WHERE status = 'pendente'` condicional.
- No job, fila, worker e estado ficam no mesmo processo para caber num exemplo. Em produção seriam uma fila de verdade (Redis, SQS, Kafka), workers separados e um banco.
