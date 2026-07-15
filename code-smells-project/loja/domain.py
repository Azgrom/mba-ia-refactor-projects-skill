"""Pure domain rules: no Flask, no database, no HTTP.

Owns product validation, order-status vocabulary, order totals, and the sales
discount policy. These functions are unit-testable without a web server or DB.
"""
from __future__ import annotations

from numbers import Number

from .errors import ValidationError

CATEGORIAS_VALIDAS = ["informatica", "moveis", "vestuario", "geral", "eletronicos", "livros"]
STATUS_VALIDOS = ["pendente", "aprovado", "enviado", "entregue", "cancelado"]
STATUS_INICIAL = "pendente"
STATUS_APROVADO = "aprovado"
STATUS_CANCELADO = "cancelado"

NOME_MIN = 2
NOME_MAX = 200
CATEGORIA_PADRAO = "geral"

# (limiar, taxa): a primeira faixa cujo limiar for excedido define o desconto.
FAIXAS_DESCONTO = [(10000, 0.10), (5000, 0.05), (1000, 0.02)]


def validar_produto(dados: dict) -> dict:
    """Validate a product payload and return normalized fields, or raise ValidationError.

    Enforces the same rules for creation and update (the legacy update path silently
    skipped the name-length and category checks — finding F-013).
    """
    if not dados:
        raise ValidationError("Dados inválidos")
    if "nome" not in dados:
        raise ValidationError("Nome é obrigatório")
    if "preco" not in dados:
        raise ValidationError("Preço é obrigatório")
    if "estoque" not in dados:
        raise ValidationError("Estoque é obrigatório")

    nome = dados["nome"]
    descricao = dados.get("descricao", "")
    preco = dados["preco"]
    estoque = dados["estoque"]
    categoria = dados.get("categoria", CATEGORIA_PADRAO)

    if not isinstance(preco, Number) or isinstance(preco, bool):
        raise ValidationError("Preço inválido")
    if not isinstance(estoque, Number) or isinstance(estoque, bool):
        raise ValidationError("Estoque inválido")
    if preco < 0:
        raise ValidationError("Preço não pode ser negativo")
    if estoque < 0:
        raise ValidationError("Estoque não pode ser negativo")
    if not isinstance(nome, str) or len(nome) < NOME_MIN:
        raise ValidationError("Nome muito curto")
    if len(nome) > NOME_MAX:
        raise ValidationError("Nome muito longo")
    if categoria not in CATEGORIAS_VALIDAS:
        raise ValidationError("Categoria inválida. Válidas: " + str(CATEGORIAS_VALIDAS))

    return {
        "nome": nome,
        "descricao": descricao,
        "preco": preco,
        "estoque": estoque,
        "categoria": categoria,
    }


def validar_status(status: str) -> str:
    if status not in STATUS_VALIDOS:
        raise ValidationError("Status inválido")
    return status


def calcular_desconto(faturamento: float) -> float:
    for limiar, taxa in FAIXAS_DESCONTO:
        if faturamento > limiar:
            return faturamento * taxa
    return 0
