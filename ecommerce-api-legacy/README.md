# ecommerce-api-legacy

LMS API (com fluxo de checkout) em Node.js/Express usada como entrada do desafio `refactor-arch`.

## Como rodar

```bash
npm install
npm start
```

A aplicação sobe em `http://localhost:3000`. O banco SQLite é em memória e já carrega seeds automaticamente no boot.

Os endpoints administrativos (`GET /api/admin/financial-report` e `DELETE /api/users/:id`) exigem autenticação via cabeçalho `Authorization: Bearer <token>`. Defina o token com a variável de ambiente `ADMIN_TOKEN`; se ela não estiver definida, um token aleatório é gerado e exibido no log de boot. A porta pode ser configurada com `PORT`.

Exemplos de requisições estão em `api.http`.
