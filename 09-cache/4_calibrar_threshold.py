"""
Nota Cache → "Similaridade, distância e threshold"

Não existe threshold universal: ele depende do MODELO DE EMBEDDING. Este
script mede a similaridade de cosseno de pares REAIS, rotulados à mão como
"mesma intenção" (deveria reaproveitar) ou "intenção diferente" (NÃO deveria),
e mostra onde fica o corte que separa os dois grupos.

Antes de rodar, suba o proxy em outro terminal:  ./iniciar_proxy.sh
"""

import math

from cache_app import gerar_embeddings, modelo_embedding_fisico

PARES = [
    # (frase A, frase B, mesma intenção?)
    ("Como cancelo minha assinatura?", "Quero encerrar meu plano", True),
    ("Como cancelo minha assinatura?", "Onde eu paro a minha cobrança mensal?", True),
    ("Meu boleto veio duplicado", "Fui cobrado duas vezes este mês", True),
    ("O aplicativo não abre na TV", "O app trava na smart TV e fecha sozinho", True),
    ("Como cancelo minha assinatura?", "Como ativo minha assinatura?", False),
    ("Como cancelo minha assinatura?", "Como mudo meu plano para o anual?", False),
    ("Meu boleto veio duplicado", "Como emito a segunda via do boleto?", False),
    ("O aplicativo não abre na TV", "Como instalo o aplicativo na TV?", False),
]


def cosseno(a: list[float], b: list[float]) -> float:
    produto = sum(x * y for x, y in zip(a, b))
    return produto / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b)))


frases = sorted({f for a, b, _ in PARES for f in (a, b)})
vetores = gerar_embeddings(frases)
vetor = dict(zip(frases, vetores))
print(f"capacidade 'embedding' → {modelo_embedding_fisico()} | dimensões: {len(vetores[0])}\n")

linhas = sorted(((cosseno(vetor[a], vetor[b]), a, b, igual) for a, b, igual in PARES), reverse=True)
print(f"{'similaridade':>12}  {'rótulo':<10}  par")
print("-" * 90)
for sim, a, b, igual in linhas:
    print(f"{sim:>12.3f}  {'MESMA' if igual else 'diferente':<10}  {a}  ↔  {b}")

menor_mesma = min(s for s, *_, igual in linhas if igual)
maior_diferente = max(s for s, *_, igual in linhas if not igual)
print()
print(f"menor similaridade entre pares de MESMA intenção:     {menor_mesma:.3f}")
print(f"maior similaridade entre pares de intenção DIFERENTE: {maior_diferente:.3f}")
if maior_diferente < menor_mesma:
    print(f"→ qualquer threshold entre {maior_diferente:.3f} e {menor_mesma:.3f} separa os dois grupos NESTA amostra.")
else:
    print("→ os grupos se SOBREPÕEM: nenhum threshold acerta tudo. Escolha qual erro é mais caro:")
    print("  falso positivo (resposta errada servida) ou falso negativo (chamada à IA a mais).")
print("\nCom outro modelo de embedding os números mudam: recalibre ao trocar de modelo.")
