# code-smells-project

API de E-commerce em Python/Flask. Originalmente a entrada do desafio `refactor-arch`;
esta branch (`refactor/arch-audit-findings`) contém a versão refatorada por responsabilidades,
preservando os contratos dos endpoints exceto pelas mudanças de segurança aprovadas (ver abaixo).

## Como rodar

```bash
pip install -r requirements.txt
python app.py
```

A aplicação sobe em `http://127.0.0.1:5000`. O banco SQLite (`loja.db`) é criado
automaticamente no primeiro boot, já com produtos e usuários de exemplo (senhas com hash).

## Configuração (variáveis de ambiente)

| Variável | Padrão | Descrição |
|---|---|---|
| `SECRET_KEY` | *(gerada em dev)* | **Obrigatória** quando `APP_ENV=production`; nunca embutida no código. |
| `APP_ENV` | `development` | `production` desativa debug e exige `SECRET_KEY`. |
| `DB_PATH` | `loja.db` | Caminho do arquivo SQLite. |
| `HOST` / `PORT` | `127.0.0.1` / `5000` | Bind do servidor de desenvolvimento. |
| `CORS_ORIGINS` | *(vazio)* | Lista separada por vírgula; vazio = sem CORS liberado (sem wildcard). |
| `SEED` | `true` | Semeia dados de exemplo se o banco estiver vazio. |

## Arquitetura

Camadas por responsabilidade (pacote `loja/`):

- `routes.py` — transporte HTTP (thin): parse, delega a um caso de uso, serializa.
- `services.py` — orquestração de casos de uso e fronteira de transação.
- `domain.py` — regras puras (validação de produto, política de desconto, status).
- `repositories.py` — acesso a dados com SQL **parametrizado** e projeções explícitas.
- `db.py` — conexão por requisição (`flask.g`) e unidade de trabalho; schema/seed explícitos.
- `errors.py` — erros tipados e mapeamento HTTP sanitizado único.
- `config.py` — configuração via ambiente; `app_factory.py` — composição.

## Mudanças de contrato (segurança)

Estas quebram intencionalmente o contrato inseguro original e foram aprovadas na auditoria:

1. Endpoints `POST /admin/query` e `POST /admin/reset-db` **removidos**.
2. `GET /usuarios` e `GET /usuarios/<id>` **não retornam mais `senha`**; senhas são
   armazenadas com hash (`werkzeug.security`).
3. `GET /health` **não expõe mais** `secret_key`, `debug` nem `db_path`.
4. Erros inesperados retornam `{"erro": "Erro interno do servidor"}` (500) sem vazar detalhes.

Além disso, `PUT /produtos/<id>` agora valida categoria/nome como o create (antes ignorava),
e `PUT /pedidos/<id>/status` retorna 404 para pedido inexistente (antes retornava 200).

## Testes

```bash
pip install pytest
python -m pytest
```

Cobrem contratos de endpoint, segurança (injeção/segredos/hash), e atomicidade de pedido.
