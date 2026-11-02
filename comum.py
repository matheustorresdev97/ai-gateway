"""
Utilitários compartilhados pelos exemplos em Python.

Lê o arquivo .env da raiz (sem depender de bibliotecas externas) e oferece
helpers para validar configuração e falar com o LiteLLM Proxy.
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
URL_PROXY = "http://localhost:4000"


def _carregar_env() -> None:
    arquivo = RAIZ / ".env"
    if not arquivo.exists():
        raise SystemExit(f"❌ Arquivo não encontrado: {arquivo}")
    for linha in arquivo.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        nome, valor = linha.split("=", 1)
        os.environ.setdefault(nome.strip(), valor.strip().strip('"').strip("'"))


_carregar_env()


def valor(nome: str) -> str:
    return os.environ.get(nome, "")


def preenchido(nome: str) -> bool:
    return bool(valor(nome)) and not valor(nome).startswith("COLE_")


def exigir(*nomes: str) -> None:
    """Para o programa se algum valor do .env ainda estiver com COLE_..."""
    faltando = [n for n in nomes if not preenchido(n)]
    if faltando:
        raise SystemExit(f"❌ Preencha no arquivo .env: {', '.join(faltando)}")


PERGUNTA = "Explique em duas frases o que é um AI gateway."
