# Exemplos — AI Gateways

Exemplos práticos da nota **AI Gateways**.

Cada pasta é um degrau da **"Evolução do módulo de integração com IA"**, do simples ao robusto:

```
01 sem SDK ─► 02 SDK direto ─► 03 LiteLLM (SDK) ─► 04 LiteLLM Proxy ─► 05 capacidades ─► 06 resiliência ─► 07 governança
   HTTP puro     acoplado         compatibilidade      gateway             router            timeout/retry       virtual keys,
                 ao provedor      (1 API, N modelos)   (serviço separado)  nomes lógicos     fallback            limites, custo, logs
```

| Pasta | Seção da nota | O que você vê | Provedor |
|---|---|---|---|
| `01-sem-sdk` | Na prática: chamar um LLM sem SDK | URL, headers e JSON montados à mão | ChatGPT |
| `02-sdk-direto` | SDK DIRETO vs GATEWAY | O SDK facilita, mas prende ao provedor | ChatGPT |
| `03-compatibilidade-litellm` | LiteLLM como primeira implementação da compatibilidade | A mesma chamada para ChatGPT e Gemini | ChatGPT e/ou Gemini |
| `04-litellm-proxy` | LiteLLM como Proxy / Gatekeeping / Fluxo de Requisição | A aplicação fala com o gateway, não com o provedor | ChatGPT e/ou Gemini |
| `05-capacidades` | Router / Expondo capacidades, não modelos físicos | A aplicação pede `resposta-suporte`, o gateway escolhe o modelo | ChatGPT e/ou Gemini |
| `06-resiliencia` | Resiliência: timeout, retry e fallback | Provedor lento e provedor fora do ar, e o gateway contornando | ChatGPT e/ou Gemini |
| `07-governanca` | Virtual Key / Rate limiting & cost control / Governança mínima | App A, B e C com acessos, limites e gastos diferentes | ChatGPT e/ou Gemini |

## O que é um AI Gateway

Um **AI Gateway** é a camada de arquitetura entre as aplicações e os provedores de modelos de linguagem (OpenAI, Google, Anthropic etc.). Este laboratório nasceu dos estudos do módulo **"Arquitetura na era da IA"** de um MBA em Arquitetura de Software com IA. A proposta é ver cada conceito funcionando em código executável, em vez de apenas ler sobre ele.

Integrar IA parece simples: instalar o SDK, chamar a API e pronto. Isso funciona bem com **um serviço e um modelo**, mas surgem problemas quando a empresa cresce:

- **Acoplamento:** cada serviço fala com o provedor do seu jeito. Trocar de modelo ou provedor pode virar um projeto de reescrita.
- **Custo invisível:** IA cobra por token, não por requisição. Sem um ponto central, fica difícil saber quanto cada aplicação gasta, e um loop mal desenhado pode consumir o orçamento rapidamente.
- **Segurança:** a chave real do provedor acaba espalhada por vários serviços e ambientes.
- **Fragilidade:** provedores ficam lentos e caem. Se cada time implementa retry e fallback por conta própria, cada um falha de um jeito diferente.
- **Governança:** regulação e clientes corporativos exigem saber quem usou IA, para quê, com qual modelo e a que custo.

O gateway cria uma **fronteira arquitetural controlada**: padroniza o acesso, esconde as chaves reais, aplica limites, registra o uso e concentra a resiliência. As aplicações ficam simples, e as decisões sobre modelos, custos e riscos passam a ser tomadas em um lugar só.

Mais do que a ferramenta, os exemplos demonstram decisões de arquitetura:

- **Comece simples e evolua por maturidade:** SDK direto não é errado; vira problema quando a escala muda.
- **Peça capacidades, não modelos:** nomes estáveis (`analise-profunda`) protegem a aplicação quando o modelo por trás muda.
- **Compatibilidade não é igualdade:** a mesma API não garante a mesma qualidade; trocar o modelo exige reavaliar os resultados.
- **Retry tem custo:** cada tentativa acrescenta latência e gasto, além de pressionar um provedor que já está com problemas.
- **O gateway não decide os limites sozinho:** os números vêm de produto, finanças e risco.

**Todas as chamadas são reais.** As pastas 01 e 02 precisam da chave do ChatGPT. As pastas 03 a 07 funcionam com a chave do **ChatGPT, do Gemini ou das duas**.

## 1. Preparar (uma vez)

```bash
cd ~/"Área de trabalho/exemplos-ai-gateway"
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 2. Preencher o `.env` (único lugar com chaves e modelos)

Crie o seu `.env` a partir do modelo (o `.env` está no `.gitignore`: suas chaves não vão para o GitHub):

```bash
cp .env.example .env
```

```bash
OPENAI_API_KEY=...      MODELO_OPENAI=...
GEMINI_API_KEY=...      MODELO_GEMINI=...
LITELLM_MASTER_KEY=sk-mestre-troque-isto   # você inventa; é a chave de admin do gateway
```

Deixe `COLE_...` no provedor que não for usar.

**Como os gateways (04 a 07) usam as chaves:** o script de início define um modelo **principal** e um **secundário** e mostra o mapeamento ao subir.

| Chaves no `.env` | Principal | Secundário |
|---|---|---|
| ChatGPT e Gemini | ChatGPT | Gemini |
| Só ChatGPT | ChatGPT | ChatGPT |
| Só Gemini | Gemini | Gemini |

Assim os exemplos rodam com qualquer uma das chaves, sem editar os `config.yaml`.

## Sobre as chaves (teste, não produção)

- **ChatGPT:** chave em [platform.openai.com/api-keys](https://platform.openai.com/api-keys). Para gastar pouco, escolha um modelo pequeno/barato da lista da OpenAI e defina um **limite de gasto** no painel deles.
- **Gemini:** chave no [Google AI Studio](https://aistudio.google.com/apikey). Costuma ter **nível gratuito** com limites de uso, ótimo para testar.
- **Claude:** a assinatura do Claude (Pro/Max) **não inclui a API**: são produtos separados, com cobranças separadas. Por isso estes exemplos usam ChatGPT e Gemini. A API do Claude exige conta no Claude Console ([platform.claude.com](https://platform.claude.com)) com créditos pré-pagos. Pelo LiteLLM, seria só usar o prefixo `anthropic/`.

Cada chamada destes exemplos usa poucas centenas de tokens, então o custo por execução é de frações de centavo num modelo pequeno.

⚠️ Na pasta 07, os orçamentos das virtual keys (US$ 10 / 2 / 0,50) são limites **do gateway**, não da sua conta. Mantenha também o limite de gasto no painel do provedor.

## 3. Rodar

Cada pasta tem um `README.md` com os comandos. Os proxies usam a porta **4000**: rode **um por vez** (Ctrl+C para parar antes de ir para a próxima pasta).

A pasta 07 precisa de **Docker** (gateway + banco Postgres para guardar keys, gastos e logs).

⚠️ Não compartilhe o `.env` com chaves preenchidas.

## O que observar

- A **mesma chamada** respondida por ChatGPT e Gemini, com resposta e erros no mesmo formato.
- Uma aplicação que **não conhece nenhuma chave real** de provedor.
- O **router** distribuindo pedidos da mesma capacidade entre modelos diferentes.
- O **fallback** entrando em ação quando o provedor principal estoura o timeout ou fica fora do ar, e o tempo que o **retry** acrescenta.
- **Virtual keys** bloqueando acesso a modelos caros (HTTP 403) e estourando limite de requisições (HTTP 429).
- Um **log por chamada** com aplicação, capacidade, modelo físico, status, tokens e custo.

## Tecnologias

- **Python 3.10+**: exemplos e clientes.
- **[LiteLLM](https://docs.litellm.ai/)**: biblioteca de compatibilidade e proxy (o gateway).
- **SDK da OpenAI**: usado para falar diretamente com a OpenAI e, apontado para o gateway, com qualquer provedor.
- **Docker e PostgreSQL**: banco do gateway para virtual keys, gastos e logs (exemplo 07).
- **Provedores:** OpenAI (ChatGPT) e Google (Gemini). Funciona com a chave de qualquer um dos dois.

## Escopo

Este é um projeto **de estudo**, focado em mostrar conceitos de arquitetura com clareza. Não é uma configuração pronta para produção: por exemplo, o gateway roda sem TLS, a chave mestra fica num arquivo local e o banco não tem backup. Esses seriam próximos passos em um ambiente real.
