"""Transport layer: thin HTTP handlers.

Each handler parses input, calls exactly one use case, and serializes the result.
Business rules, SQL, and side effects live behind the services. Response envelopes
and status codes match the legacy contract; the two unauthenticated ``/admin/*``
endpoints are intentionally not registered (findings F-001, F-003).
"""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from .config import APP_VERSION
from .errors import NotFoundError


def _num(value):
    return float(value) if value not in (None, "") else None


def build_blueprints(services) -> list[Blueprint]:
    produto_service = services["produto"]
    usuario_service = services["usuario"]
    pedido_service = services["pedido"]
    relatorio_service = services["relatorio"]
    health_service = services["health"]

    produtos = Blueprint("produtos", __name__)
    usuarios = Blueprint("usuarios", __name__)
    pedidos = Blueprint("pedidos", __name__)
    ops = Blueprint("ops", __name__)

    # --- produtos ---
    @produtos.get("/produtos")
    def listar_produtos():
        return jsonify({"dados": produto_service.listar(), "sucesso": True}), 200

    @produtos.get("/produtos/busca")
    def buscar_produtos():
        termo = request.args.get("q", "")
        categoria = request.args.get("categoria", None)
        preco_min = _num(request.args.get("preco_min", None))
        preco_max = _num(request.args.get("preco_max", None))
        resultados = produto_service.buscar(termo, categoria, preco_min, preco_max)
        return jsonify({"dados": resultados, "total": len(resultados), "sucesso": True}), 200

    @produtos.get("/produtos/<int:id>")
    def buscar_produto(id):
        produto = produto_service.obter(id)
        if not produto:
            raise NotFoundError("Produto não encontrado", flag=True)
        return jsonify({"dados": produto, "sucesso": True}), 200

    @produtos.post("/produtos")
    def criar_produto():
        novo_id = produto_service.criar(request.get_json(silent=True))
        return jsonify({"dados": {"id": novo_id}, "sucesso": True, "mensagem": "Produto criado"}), 201

    @produtos.put("/produtos/<int:id>")
    def atualizar_produto(id):
        produto_service.atualizar(id, request.get_json(silent=True))
        return jsonify({"sucesso": True, "mensagem": "Produto atualizado"}), 200

    @produtos.delete("/produtos/<int:id>")
    def deletar_produto(id):
        produto_service.deletar(id)
        return jsonify({"sucesso": True, "mensagem": "Produto deletado"}), 200

    # --- usuarios / auth ---
    @usuarios.get("/usuarios")
    def listar_usuarios():
        return jsonify({"dados": usuario_service.listar(), "sucesso": True}), 200

    @usuarios.get("/usuarios/<int:id>")
    def buscar_usuario(id):
        return jsonify({"dados": usuario_service.obter(id), "sucesso": True}), 200

    @usuarios.post("/usuarios")
    def criar_usuario():
        novo_id = usuario_service.criar(request.get_json(silent=True))
        return jsonify({"dados": {"id": novo_id}, "sucesso": True}), 201

    @usuarios.post("/login")
    def login():
        usuario = usuario_service.login(request.get_json(silent=True))
        return jsonify({"dados": usuario, "sucesso": True, "mensagem": "Login OK"}), 200

    # --- pedidos ---
    @pedidos.post("/pedidos")
    def criar_pedido():
        resultado = pedido_service.criar(request.get_json(silent=True))
        return jsonify({
            "dados": resultado, "sucesso": True, "mensagem": "Pedido criado com sucesso",
        }), 201

    @pedidos.get("/pedidos")
    def listar_todos_pedidos():
        return jsonify({"dados": pedido_service.listar_todos(), "sucesso": True}), 200

    @pedidos.get("/pedidos/usuario/<int:usuario_id>")
    def listar_pedidos_usuario(usuario_id):
        return jsonify({"dados": pedido_service.listar_por_usuario(usuario_id), "sucesso": True}), 200

    @pedidos.put("/pedidos/<int:pedido_id>/status")
    def atualizar_status_pedido(pedido_id):
        pedido_service.atualizar_status(pedido_id, request.get_json(silent=True))
        return jsonify({"sucesso": True, "mensagem": "Status atualizado"}), 200

    # --- ops / report ---
    @ops.get("/relatorios/vendas")
    def relatorio_vendas():
        return jsonify({"dados": relatorio_service.vendas(), "sucesso": True}), 200

    @ops.get("/health")
    def health_check():
        return jsonify(health_service.check()), 200

    @ops.get("/")
    def index():
        return jsonify({
            "mensagem": "Bem-vindo à API da Loja",
            "versao": APP_VERSION,
            "endpoints": {
                "produtos": "/produtos",
                "usuarios": "/usuarios",
                "pedidos": "/pedidos",
                "login": "/login",
                "relatorios": "/relatorios/vendas",
                "health": "/health",
            },
        })

    return [produtos, usuarios, pedidos, ops]
