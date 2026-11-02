"""
Nota Fluxos de Chamada → "Quando transformar IA em processamento assíncrono"
                         "Ciclo de vida do Job" e "O que muda com processamento assíncrono"

Uma mini arquitetura de jobs, num só processo para caber num exemplo:

  criar_job()  = a "request": registra o pedido e responde NA HORA (como um HTTP 202)
  fila         = queue.Queue (em produção: Redis, SQS, RabbitMQ, Kafka)
  worker       = thread separada que consome a fila e chama o gateway
  jobs         = estado explícito do job (em produção: banco)
  laço final   = o cliente acompanhando por polling

Pedidos da demonstração:
  pedido-1  análise normal                          → concluido
  pedido-1  REPETIDO (clique duplo / retry)         → mesmo job, não processa de novo
  pedido-2  falha transiente simulada na 1ª vez     → retry com backoff → concluido
  pedido-3  capacidade inexistente (erro permanente)→ falhou → DLQ, sem retry
  pedido-1  REENTREGUE pela fila (at-least-once)    → worker vê que já concluiu e ignora

A idempotência aparece nos DOIS lados:
  - na criação (criar_job): a chave de idempotência barra o pedido repetido do cliente;
  - no worker (reivindicar): o estado do job barra a mensagem repetida da fila.

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import queue
import sys
import threading
import time
from pathlib import Path

import openai
from openai import OpenAI

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import comum  # noqa: E402

client = OpenAI(base_url=f"{comum.URL_PROXY}/v1", api_key=comum.valor("LITELLM_MASTER_KEY"), max_retries=0)

MAX_TENTATIVAS = 3
FINAIS = {"concluido", "falhou"}

jobs: dict[str, dict] = {}   # estado explícito: id → status, tentativas, resultado
dlq: list[str] = []          # dead letter queue: jobs que falharam de vez
ignoradas: list[str] = []    # mensagens repetidas da fila que o worker não reprocessou
fila: queue.Queue = queue.Queue()
trava = threading.Lock()


class FalhaTransiente(Exception):
    """Simula um 503/timeout do provedor, que vale a pena tentar de novo."""


# Erros que podem passar sozinhos: tentar de novo com backoff.
TRANSIENTES = (FalhaTransiente, openai.APIConnectionError, openai.RateLimitError, openai.InternalServerError)


def atualizar(job_id: str, **campos) -> None:
    with trava:
        jobs[job_id].update(campos)


# ---------------------------------------------------------------- a "request"
def criar_job(chave_idempotencia: str, capacidade: str, documento: str, instavel: bool = False) -> dict:
    """Registra o pedido e devolve na hora. Não chama a IA aqui."""
    with trava:
        if chave_idempotencia in jobs:                      # pedido repetido
            return {"job_id": chave_idempotencia, "repetido": True, **jobs[chave_idempotencia]}
        jobs[chave_idempotencia] = {"status": "pendente", "tentativas": 0}
    fila.put((chave_idempotencia, capacidade, documento, instavel))
    return {"job_id": chave_idempotencia, "repetido": False, "status": "pendente"}


def simular_reentrega(job_id: str, capacidade: str, documento: str) -> None:
    """A fila entrega a mesma mensagem de novo (ex.: o worker caiu antes de confirmar).

    Kafka, SQS e RabbitMQ garantem entrega "pelo menos uma vez" (at-least-once):
    duplicata não é bug, é algo que o worker PRECISA saber tratar.
    """
    fila.put((job_id, capacidade, documento, False))


# ---------------------------------------------------------------- o worker
def reivindicar(job_id: str) -> bool:
    """Idempotência do worker: só processa o job se ninguém já processou.

    Verificar e marcar acontecem juntos, sob a trava. Assim, nem uma mensagem
    repetida nem dois workers ao mesmo tempo processam o mesmo job duas vezes.
    Em produção, o mesmo papel é de um UPDATE condicional no banco
    (UPDATE jobs SET status='processando' WHERE id=? AND status='pendente').
    """
    with trava:
        job = jobs[job_id]
        if job["status"] != "pendente" or job.get("reservado"):   # já feito ou em andamento
            return False
        job["reservado"] = True        # continua reservado durante o backoff entre tentativas
        return True


def worker() -> None:
    while True:
        job_id, capacidade, documento, instavel = fila.get()
        if not reivindicar(job_id):                        # mensagem repetida
            ignoradas.append(job_id)
            fila.task_done()                               # confirma e segue, sem chamar a IA
            continue
        for tentativa in range(1, MAX_TENTATIVAS + 1):
            atualizar(job_id, status="processando", tentativas=tentativa, erro=None)
            try:
                if instavel and tentativa == 1:
                    raise FalhaTransiente("503 simulado: provedor sobrecarregado")
                with trava:
                    jobs[job_id]["chamadas_ia"] = jobs[job_id].get("chamadas_ia", 0) + 1
                resposta = client.chat.completions.create(
                    model=capacidade,
                    messages=[{"role": "user", "content": "Liste em 3 tópicos curtos os principais riscos "
                                                          "deste contrato:\n\n" + documento}],
                    max_tokens=4000,
                )
                atualizar(job_id, status="concluido", resultado=resposta.choices[0].message.content)
                break
            except TRANSIENTES as erro:
                if tentativa == MAX_TENTATIVAS:
                    atualizar(job_id, status="falhou", erro=f"esgotou tentativas: {erro}")
                    dlq.append(job_id)
                    break
                espera = 2 ** tentativa                     # backoff exponencial: 2s, 4s...
                atualizar(job_id, status="pendente", erro=f"transiente ({erro}); nova tentativa em {espera}s")
                time.sleep(espera)
            except openai.APIStatusError as erro:           # 4xx: tentar de novo não resolve
                atualizar(job_id, status="falhou", erro=f"permanente: HTTP {erro.status_code}")
                dlq.append(job_id)
                break
        fila.task_done()


threading.Thread(target=worker, daemon=True).start()   # um worker só: os jobs esperam na fila

# ---------------------------------------------------------------- o cliente
CONTRATO = ("Contrato de prestação de serviços. O fornecedor pode reajustar o preço a qualquer "
            "momento sem aviso. Multa de 50% em caso de cancelamento. Foro exclusivo no exterior.")

PEDIDOS = [
    ("pedido-1", "analise", CONTRATO, False),
    ("pedido-1", "analise", CONTRATO, False),               # clique duplo
    ("pedido-2", "analise", CONTRATO, True),                # falha transiente na 1ª tentativa
    ("pedido-3", "capacidade-que-nao-existe", CONTRATO, False),
]

print("=" * 60 + "\nREQUESTS: cada uma só registra o job e responde\n" + "=" * 60)
for chave, capacidade, doc, instavel in PEDIDOS:
    inicio = time.perf_counter()
    r = criar_job(chave, capacidade, doc, instavel)
    ms = (time.perf_counter() - inicio) * 1000
    aviso = "  ← repetido: mesmo job, não processa de novo" if r["repetido"] else ""
    print(f"202 Accepted em {ms:.2f} ms  job_id={r['job_id']}  status={r['status']}{aviso}")

simular_reentrega("pedido-1", "analise", CONTRATO)
print("📨 a fila reentregou a mensagem do pedido-1 (at-least-once): vai chegar ao worker de novo")

print("\n" + "=" * 60 + "\nPOLLING: o cliente acompanha o estado (a cada 1s)\n" + "=" * 60)
inicio = time.perf_counter()
visto: dict[str, tuple] = {}
try:
    while True:
        with trava:
            retrato = {k: dict(v) for k, v in jobs.items()}
        for job_id, job in retrato.items():
            chave = (job["status"], job["tentativas"])
            if visto.get(job_id) != chave:                  # só imprime quando muda
                visto[job_id] = chave
                extra = f"  ({job['erro']})" if job.get("erro") and job["status"] != "concluido" else ""
                print(f"[{time.perf_counter() - inicio:5.1f}s] {job_id}: {job['status']}"
                      f" (tentativa {job['tentativas']}){extra}")
        if all(j["status"] in FINAIS for j in retrato.values()):
            break
        time.sleep(1)
    fila.join()                                         # espera a fila esvaziar (inclui a reentrega)
except KeyboardInterrupt:
    raise SystemExit("\ninterrompido")

print("\n" + "=" * 60 + "\nRESULTADO\n" + "=" * 60)
for job_id, job in jobs.items():
    if job["status"] == "concluido":
        print(f"✅ {job_id}:\n{job['resultado']}\n")
erro_conexao = any("Connection" in jobs[j].get("erro", "") for j in dlq)
print("🔁 Idempotência")
print(f"   mensagens repetidas ignoradas pelo worker: {ignoradas}")
for job_id, job in jobs.items():
    print(f"   {job_id}: {job.get('chamadas_ia', 0)} chamada(s) à IA")
print(f"\n📮 DLQ (para análise humana): {dlq}")
for job_id in dlq:
    print(f"   {job_id}: {jobs[job_id]['erro']}")
if erro_conexao:
    print("\n❌ Parece que o proxy está fora do ar. Rode ./iniciar_proxy.sh em outro terminal.")
