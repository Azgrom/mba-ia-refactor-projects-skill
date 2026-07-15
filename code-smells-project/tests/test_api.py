"""Endpoint contract tests — the behavior the refactor must preserve."""


def test_index(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.get_json()["mensagem"] == "Bem-vindo à API da Loja"


def test_listar_produtos(client):
    r = client.get("/produtos")
    body = r.get_json()
    assert r.status_code == 200
    assert body["sucesso"] is True
    assert len(body["dados"]) == 10
    assert body["dados"][0]["nome"] == "Notebook Gamer"


def test_produto_por_id_ok_e_404(client):
    assert client.get("/produtos/1").status_code == 200
    r = client.get("/produtos/9999")
    assert r.status_code == 404
    assert r.get_json() == {"erro": "Produto não encontrado", "sucesso": False}


def test_busca_produtos(client):
    r = client.get("/produtos/busca?q=Mouse")
    body = r.get_json()
    assert body["total"] == 1
    assert body["dados"][0]["nome"] == "Mouse Wireless"


def test_busca_por_faixa_de_preco(client):
    r = client.get("/produtos/busca?preco_min=100&preco_max=300")
    assert {d["nome"] for d in r.get_json()["dados"]} == {
        "Teclado Mecânico", "Headset Gamer", "Webcam HD",
    }


def test_criar_produto_ok(client):
    r = client.post("/produtos", json={
        "nome": "Item Teste", "preco": 10.5, "estoque": 5, "categoria": "geral",
    })
    assert r.status_code == 201
    assert r.get_json()["mensagem"] == "Produto criado"


def test_criar_produto_validacoes(client):
    assert client.post("/produtos", json={"preco": 1, "estoque": 1}).get_json() == {
        "erro": "Nome é obrigatório"}
    assert client.post("/produtos", json={
        "nome": "Item", "preco": -1, "estoque": 1}).get_json() == {
        "erro": "Preço não pode ser negativo"}
    assert client.post("/produtos", json={
        "nome": "A", "preco": 1, "estoque": 1}).get_json() == {"erro": "Nome muito curto"}
    assert client.post("/produtos", json={
        "nome": "Item", "preco": 1, "estoque": 1, "categoria": "xyz"}
    ).status_code == 400


def test_atualizar_produto_agora_valida_categoria(client):
    # F-013: the update path now enforces the same rules as create (was silently skipped).
    r = client.put("/produtos/1", json={
        "nome": "X", "preco": 1, "estoque": 1, "categoria": "invalida"})
    assert r.status_code == 400


def test_atualizar_e_deletar_404(client):
    assert client.put("/produtos/9999", json={
        "nome": "Nome valido", "preco": 1, "estoque": 1}).get_json() == {
        "erro": "Produto não encontrado"}
    assert client.delete("/produtos/9999").get_json() == {"erro": "Produto não encontrado"}


def test_usuarios_nao_expoem_senha(client):
    lista = client.get("/usuarios").get_json()["dados"]
    assert lista, "esperava usuarios semeados"
    for u in lista:
        assert "senha" not in u
    assert "senha" not in client.get("/usuarios/1").get_json()["dados"]


def test_login_ok_com_credencial_semeada(client):
    r = client.post("/login", json={"email": "joao@email.com", "senha": "123456"})
    assert r.status_code == 200
    assert r.get_json()["dados"]["email"] == "joao@email.com"
    assert "senha" not in r.get_json()["dados"]


def test_login_invalido(client):
    r = client.post("/login", json={"email": "joao@email.com", "senha": "errada"})
    assert r.status_code == 401
    assert r.get_json() == {"erro": "Email ou senha inválidos", "sucesso": False}


def test_fluxo_pedido_completo(client):
    r = client.post("/pedidos", json={
        "usuario_id": 2, "itens": [{"produto_id": 2, "quantidade": 2}]})
    assert r.status_code == 201
    assert r.get_json()["dados"]["total"] == 179.8
    pedido_id = r.get_json()["dados"]["pedido_id"]

    # stock decremented from 50 to 48
    assert client.get("/produtos/2").get_json()["dados"]["estoque"] == 48

    todos = client.get("/pedidos").get_json()["dados"]
    assert len(todos) == 1
    assert todos[0]["itens"][0]["produto_nome"] == "Mouse Wireless"

    assert client.put(f"/pedidos/{pedido_id}/status", json={
        "status": "aprovado"}).status_code == 200

    rel = client.get("/relatorios/vendas").get_json()["dados"]
    assert rel["faturamento_bruto"] == 179.8
    assert rel["pedidos_aprovados"] == 1


def test_pedido_validacoes(client):
    assert client.post("/pedidos", json={
        "itens": [{"produto_id": 2, "quantidade": 1}]}).get_json() == {
        "erro": "Usuario ID é obrigatório"}
    assert client.post("/pedidos", json={"usuario_id": 2, "itens": []}).get_json() == {
        "erro": "Pedido deve ter pelo menos 1 item"}
    assert client.post("/pedidos", json={
        "usuario_id": 2, "itens": [{"produto_id": 9999, "quantidade": 1}]}).get_json() == {
        "erro": "Produto 9999 não encontrado", "sucesso": False}
    assert client.post("/pedidos", json={
        "usuario_id": 2, "itens": [{"produto_id": 6, "quantidade": 99999}]}).get_json() == {
        "erro": "Estoque insuficiente para Cadeira Gamer", "sucesso": False}


def test_status_pedido_inexistente_404(client):
    # F-012: updating a nonexistent order used to return 200; now it is a 404.
    r = client.put("/pedidos/4242/status", json={"status": "aprovado"})
    assert r.status_code == 404


def test_status_invalido(client):
    r = client.put("/pedidos/1/status", json={"status": "xyz"})
    assert r.status_code == 400
    assert r.get_json() == {"erro": "Status inválido"}
