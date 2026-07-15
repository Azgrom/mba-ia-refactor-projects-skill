"""Application services: use-case orchestration and transaction boundaries.

Services coordinate repositories and domain rules, own the unit of work for
multi-write use cases (finding F-008), and keep domain policy out of transport
(findings F-006, F-007). They return transport-neutral data.
"""
from __future__ import annotations

from werkzeug.security import check_password_hash, generate_password_hash

from . import domain
from .config import APP_VERSION
from .db import Database
from .errors import ConflictError, NotFoundError, ValidationError
from .repositories import (
    PedidoRepository,
    ProdutoRepository,
    UsuarioRepository,
)


class Notifier:
    """Post-commit side effects (email/SMS/push). Isolated from transport and domain."""

    def __init__(self, logger):
        self.logger = logger

    def pedido_criado(self, pedido_id, usuario_id):
        self.logger.info("ENVIANDO EMAIL: Pedido %s criado para usuario %s", pedido_id, usuario_id)
        self.logger.info("ENVIANDO SMS: Seu pedido foi recebido!")
        self.logger.info("ENVIANDO PUSH: Novo pedido recebido pelo sistema")

    def status_alterado(self, pedido_id, status):
        if status == domain.STATUS_APROVADO:
            self.logger.info("NOTIFICAÇÃO: Pedido %s foi aprovado! Preparar envio.", pedido_id)
        if status == domain.STATUS_CANCELADO:
            self.logger.info("NOTIFICAÇÃO: Pedido %s cancelado. Devolver estoque.", pedido_id)


class ProdutoService:
    def __init__(self, db: Database, produtos: ProdutoRepository):
        self.db = db
        self.produtos = produtos

    def listar(self):
        return self.produtos.listar()

    def buscar(self, termo, categoria, preco_min, preco_max):
        return self.produtos.buscar(termo, categoria, preco_min, preco_max)

    def obter(self, produto_id):
        return self.produtos.obter(produto_id)

    def criar(self, dados) -> int:
        campos = domain.validar_produto(dados)
        with self.db.transaction():
            return self.produtos.criar(
                campos["nome"], campos["descricao"], campos["preco"],
                campos["estoque"], campos["categoria"],
            )

    def atualizar(self, produto_id, dados) -> None:
        if self.produtos.obter(produto_id) is None:
            raise NotFoundError("Produto não encontrado")
        campos = domain.validar_produto(dados)
        with self.db.transaction():
            self.produtos.atualizar(
                produto_id, campos["nome"], campos["descricao"], campos["preco"],
                campos["estoque"], campos["categoria"],
            )

    def deletar(self, produto_id) -> None:
        if self.produtos.obter(produto_id) is None:
            raise NotFoundError("Produto não encontrado")
        with self.db.transaction():
            self.produtos.deletar(produto_id)


class UsuarioService:
    def __init__(self, db: Database, usuarios: UsuarioRepository):
        self.db = db
        self.usuarios = usuarios

    def listar(self):
        return self.usuarios.listar()

    def obter(self, usuario_id):
        usuario = self.usuarios.obter(usuario_id)
        if usuario is None:
            raise NotFoundError("Usuário não encontrado")
        return usuario

    def criar(self, dados) -> int:
        if not dados:
            raise ValidationError("Dados inválidos")
        nome = dados.get("nome", "")
        email = dados.get("email", "")
        senha = dados.get("senha", "")
        if not nome or not email or not senha:
            raise ValidationError("Nome, email e senha são obrigatórios")
        with self.db.transaction():
            return self.usuarios.criar(nome, email, generate_password_hash(senha))

    def login(self, dados):
        email = (dados or {}).get("email", "")
        senha = (dados or {}).get("senha", "")
        if not email or not senha:
            raise ValidationError("Email e senha são obrigatórios")
        row = self.usuarios.obter_por_email(email)
        if row is None or not check_password_hash(row["senha"], senha):
            raise ValidationError("Email ou senha inválidos", status=401, flag=True)
        return {
            "id": row["id"],
            "nome": row["nome"],
            "email": row["email"],
            "tipo": row["tipo"],
        }


class PedidoService:
    def __init__(self, db, produtos, pedidos, notifier):
        self.db = db
        self.produtos = produtos
        self.pedidos = pedidos
        self.notifier = notifier

    def criar(self, dados) -> dict:
        if not dados:
            raise ValidationError("Dados inválidos")
        usuario_id = dados.get("usuario_id")
        itens = dados.get("itens", [])
        if not usuario_id:
            raise ValidationError("Usuario ID é obrigatório")
        if not itens or len(itens) == 0:
            raise ValidationError("Pedido deve ter pelo menos 1 item")

        # Validate availability up front (produces the exact legacy messages)...
        total = 0
        preparados = []
        for item in itens:
            produto = self.produtos.obter(item["produto_id"])
            if produto is None:
                raise ValidationError(
                    "Produto " + str(item["produto_id"]) + " não encontrado", flag=True
                )
            if produto["estoque"] < item["quantidade"]:
                raise ValidationError(
                    "Estoque insuficiente para " + produto["nome"], flag=True
                )
            total += produto["preco"] * item["quantidade"]
            preparados.append((produto, item["quantidade"]))

        # ...then write everything atomically with an atomic stock guard (F-008).
        with self.db.transaction():
            pedido_id = self.pedidos.criar(usuario_id, domain.STATUS_INICIAL, total)
            for produto, quantidade in preparados:
                self.pedidos.adicionar_item(
                    pedido_id, produto["id"], quantidade, produto["preco"]
                )
                afetadas = self.produtos.decrementar_estoque(produto["id"], quantidade)
                if afetadas == 0:
                    raise ConflictError(
                        "Estoque insuficiente para " + produto["nome"], status=400, flag=True
                    )

        self.notifier.pedido_criado(pedido_id, usuario_id)
        return {"pedido_id": pedido_id, "total": total}

    def listar_todos(self):
        return self.pedidos.listar_todos()

    def listar_por_usuario(self, usuario_id):
        return self.pedidos.listar_por_usuario(usuario_id)

    def atualizar_status(self, pedido_id, dados):
        novo_status = domain.validar_status((dados or {}).get("status", ""))
        if self.pedidos.obter(pedido_id) is None:
            raise NotFoundError("Pedido não encontrado")
        with self.db.transaction():
            self.pedidos.atualizar_status(pedido_id, novo_status)
        self.notifier.status_alterado(pedido_id, novo_status)


class RelatorioService:
    def __init__(self, pedidos: PedidoRepository):
        self.pedidos = pedidos

    def vendas(self) -> dict:
        a = self.pedidos.agregados()
        faturamento = a["faturamento"]
        desconto = domain.calcular_desconto(faturamento)
        total = a["total_pedidos"]
        return {
            "total_pedidos": total,
            "faturamento_bruto": round(faturamento, 2),
            "desconto_aplicavel": round(desconto, 2),
            "faturamento_liquido": round(faturamento - desconto, 2),
            "pedidos_pendentes": a["pendentes"],
            "pedidos_aprovados": a["aprovados"],
            "pedidos_cancelados": a["cancelados"],
            "ticket_medio": round(faturamento / total, 2) if total > 0 else 0,
        }


class HealthService:
    def __init__(self, produtos, usuarios, pedidos, ambiente):
        self.produtos = produtos
        self.usuarios = usuarios
        self.pedidos = pedidos
        self.ambiente = ambiente

    def check(self) -> dict:
        counts = {
            "produtos": self.produtos.contar(),
            "usuarios": self.usuarios.contar(),
            "pedidos": self.pedidos.contar(),
        }
        return {
            "status": "ok",
            "database": "connected",
            "counts": counts,
            "versao": APP_VERSION,
            "ambiente": self.ambiente,
        }
