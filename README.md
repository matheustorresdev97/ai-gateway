# Exemplos — AI Gateways

Exemplos práticos **AI Gateways** (MBA Arquitetura de Software com IA).


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