# Entregável

Repositório público no GitHub (fork do repositório base) contendo:

- Skill completa em `refactor-arch/` (dentro dos 3 projetos)
  - Link simbólico ou cópia dentro de cada projeto, apontando para a skill
- Código refatorado dos 3 projetos (resultado da execução da Fase 3, commitado no repositório)
- Relatórios em `reports/` (auditoria e validação dos 3 projetos)
  - Os relatórios de auditoria seguem o prefixo `audit-project`
  - Os relatórios de validação dos débitos encontrados seguem o prefixo `validation`
- `README.md` atualizado

## Estrutura do repositório

- `refactor-arch/` — A skill completa (SKILL.md + arquivos de referência)
- Código refatorado dos 3 projetos — resultado da execução da Fase 3, commitado no repositório
- `reports/audit-project-*.md` — Relatório de auditoria de cada projeto
- `README.md` — Documentação do seu processo
- `docs/refactor-arch-effectiveness-benchmark/` com a validação da eficácia da skill, utilizada como critério de 'feito'
- `docs/spdd` e `docs/superpowers` com documentação gerada por análises das skills superpowers e workflow structured prompt driven development, utilizando as instruções da `skill-creator` como checklist de levantamento
- `code-smells-project/` — API de E-commerce Python/Flask com code smells intencionais
- `ecommerce-api-legacy/` — LMS API Node.js/Express (com fluxo de checkout) e problemas de implementação
- `task-manager-api/` — API de Task Manager Python/Flask com organização parcial e problemas de segurança/qualidade

# Análise Manual

A análise manual foi feita antes das refatorações, com foco em evidência de código executável, contratos HTTP, ciclo de vida de persistência e riscos de mudança. Os relatórios completos estão em `reports/`

## `code-smell-project`
- Código plano na raiz
- Acúmulo de responsabilidades no entrypoint
- Sem testes

## `ecommerce-api-lagacy`
- Recursos não implementados
- Acúmulo de responsabilidades no entrypoint

## `task-manager-api`
- segregação fraca de responsabilidades
- Sem testes
- Falta de organização

# Construção da Skill

A skill `refactor-arch` foi construída como um processo de auditoria e refatoração por fases, não como um conjunto de receitas por framework. O workflow usado foi:

1. Solicitei que `/superpowers` carregasse as instruções de `/skill-creator` e transformasse o objetivo em um plano.
2. Usei `/spdd-analysis` para decompor objetivos, riscos e critérios de feito.
3. Em novo contexto, pedi ao `/spdd-generate` o prompt de criação da skill.
4. Em novo contexto, usei `/skill-creator` para implementar a skill e seus arquivos auxiliares.
5. Validei a skill com uma suíte de benchmark em `docs/refactor-arch-effectiveness-benchmark/`.

O workflow SPDD usado como referência está descrito em [martinfowler.com](https://martinfowler.com/articles/structured-prompt-driven/).

## Decisões de design

- `refactor-arch/SKILL.md` ficou pequeno o suficiente para orientar a execução, mas rígido nos invariantes importantes: analisar antes de julgar, auditar antes de alterar, exigir aprovação explícita por caminho + digest antes de refatorar e validar contra baseline.
- As instruções detalhadas foram separadas em `refactor-arch/references/` para reduzir carga cognitiva e permitir leitura por fase:
  - `project-analysis.md`: fingerprint, escopo, rotas, persistência, baseline e snapshot de mutação.
  - `anti-pattern-catalog.md`: regras de detecção, severidade, falsos positivos e direção de remediação.
  - `audit-report-contract.md`: formato exato do relatório, digest e semântica de aprovação.
  - `mvc-target-guidelines.md` e `refactoring-playbook.md`: extração por responsabilidade sem impor template universal.
  - `validation-playbook.md`: validação de boot, endpoints, fluxos, persistência, rollback, segurança e limpeza.
- Os scripts `validate_audit_report.py` e `verify_skill_distribution.py` foram incluídos para transformar qualidade do relatório e empacotamento da skill em checks executáveis.
- O formato do relatório exige `Project Fingerprint`, `Behavioral Baseline`, `Severity Summary`, findings com evidência/impacto/recomendação e `Audit Snapshot Digest`. Isso evita refatoração baseada em impressão geral.

## Anti-patterns incluídos

O catálogo foi desenhado por consequência e causa-raiz, não por nome de arquivo. Inclui:

- CRITICAL: execução arbitrária de dados/comandos, segredo exposto em runtime, exposição de credenciais/pagamento e operação privilegiada sem controle. Esses itens cobrem riscos que justificam mudança de contrato.
- HIGH: God Component, credenciais fracas, ausência de transação, transporte dono de domínio/persistência e estado global mutável. Esses itens capturam as violações arquiteturais que impedem mudança segura.
- MEDIUM: query em loop, validação de fronteira ausente, política duplicada, acesso sem paginação/projeção e API depreciada com evidência de versão. Esses itens cobrem escalabilidade, manutenção e compatibilidade.
- LOW: nome enganoso, valor mágico, código morto e serialização duplicada. Esses itens evitam ruído, mas registram sintomas que explicam drift e manutenção difícil.

Cada anti-pattern tem sinais de detecção, checagens contra falso positivo, impacto, direção de remediação e autoridade de evidência. Isso foi necessário para impedir que a skill contasse sintomas duplicados como findings diferentes.

## Agnosticismo tecnológico

A skill não assume Flask, Express, MVC ou Clean Architecture como destino obrigatório. Ela manda identificar entrypoints, rotas, persistência, lifecycle, contratos e responsabilidades reais primeiro. A mesma regra "transporte não deve coordenar domínio e persistência" foi aplicada em Flask puro, Express e Flask-SQLAlchemy sem exigir a mesma árvore de diretórios.

Quando há uma stack parcialmente organizada, como `task-manager-api`, a skill preserva módulos úteis e corrige ownership. Quando há um componente centralizador, como `AppManager`, ela propõe decomposição contextual. Quando há código plano, como `code-smells-project`, ela introduz camadas mínimas por responsabilidade.

## Desafios e resoluções

- Aprovação de mudança: o maior risco era a ferramenta refatorar antes de autorização. Resolvi com uma máquina de estados (`PROJECT_ANALYSIS`, `ARCHITECTURE_AUDIT`, `WAITING_FOR_APPROVAL`, `REFACTORING`, `VALIDATION`) e digest obrigatório do relatório.
- Segurança versus compatibilidade: alguns contratos eram inseguros por definição, como retornar senha ou aceitar endpoint de SQL arbitrário. Resolvi separando "contratos preservados" de "mudanças de contrato orientadas por segurança" no relatório.
- Evidência de depreciação: a skill proíbe findings de API depreciada por memória. Ela exige versão detectada e documentação atual, ou registra limitação.
- Evitar template fixo: o benchmark mostrou stacks diferentes; por isso as referências falam de responsabilidades, transações, serialização e fronteiras, não de nomes obrigatórios de pastas.
- Validação real: a skill exige baseline e checks pós-refatoração. Isso evitou declarar sucesso só com sintaxe ou boot.

# Resultados

Só se mexe com performance medindo. O critério de aceite foi definido pela eficácia da skill e pela validação das refatorações contra o baseline de cada projeto. O benchmark está em `docs/refactor-arch-effectiveness-benchmark/`.

## Resumo das auditorias

| Projeto | CRITICAL | HIGH | MEDIUM | LOW | Total | Relatório |
|---|---:|---:|---:|---:|---:|---|
| `code-smells-project` | 5 | 4 | 4 | 3 | 16 | `reports/audit-project-code-smells-project.md` |
| `ecommerce-api-legacy` | 3 | 4 | 3 | 1 | 11 | `reports/audit-project-ecommerce-api-legacy.md` |
| `task-manager-api` | 3 | 4 | 6 | 3 | 16 | `reports/audit-project-task-manager-api.md` |

### `code-smells-project`

| Severidade | Problema identificado | Por que é relevante |
|---|---|---|
| CRITICAL | Endpoints administrativos sem autenticação: `POST /admin/query` executava SQL arbitrário e `POST /admin/reset-db` apagava todas as tabelas. | Qualquer cliente poderia ler, alterar ou destruir os dados da aplicação. Isso é comprometimento total de confidencialidade, integridade e disponibilidade. |
| CRITICAL | SQL montado por concatenação em praticamente toda a persistência, inclusive login. | Permitiria bypass de autenticação e injeção em fluxos de leitura, escrita e busca. A correção exigia mover queries para uma fronteira parametrizada. |
| CRITICAL | Segredos, `debug=True`, CORS aberto e dados internos expostos em `/health`. | O segredo Flask era literal no código e também retornado ao cliente; debug em `0.0.0.0` poderia expor o console interativo em falhas. |
| CRITICAL | Senhas em texto puro armazenadas, comparadas e serializadas. | A API entregava credenciais por endpoints sem autenticação. Mesmo uma refatoração arquitetural não seria aceitável preservando esse contrato inseguro. |
| HIGH | `models.py` concentrava persistência, regras de domínio, cálculo de totais/descontos e orquestração de pedido. | Mudanças de regra de negócio exigiam editar a camada de dados; testes unitários ficavam acoplados ao banco. |
| HIGH | Controllers continham validação de negócio, efeitos colaterais e SQL bruto no health check. | O transporte HTTP decidia política de domínio e persistência, dificultando reuso e consistência entre entradas. |
| HIGH | Criação de pedidos sem transação explícita e com checagem de estoque separada da baixa. | Uma falha no meio do pedido poderia deixar estoque e itens inconsistentes; concorrência poderia causar oversell. |
| HIGH | Conexão SQLite global com `check_same_thread=False` e schema/seed como efeito colateral do primeiro acesso. | O comportamento ficava dependente da ordem das requisições e inseguro sob concorrência/testes. |
| MEDIUM | N+1 em listagens de pedidos. | A latência crescia com pedidos e itens, tornando endpoints de leitura progressivamente caros. |
| MEDIUM | Leituras sem paginação/autorização e validação fraca de usuários, pedidos e status. | A aplicação aceitava estados inválidos, retornava sucesso falso e lia dados sensíveis em massa. |
| MEDIUM | Política de validação e erro duplicada e divergente. | O create e update de produto já tinham regras diferentes; exceções vazavam `str(e)` ao cliente. |
| LOW | Serialização manual duplicada, valores mágicos e código morto. | Essas duplicações explicavam vazamento de campos e aumentavam o custo de mudanças pequenas. |

### `ecommerce-api-legacy`

| Severidade | Problema identificado | Por que é relevante |
|---|---|---|
| CRITICAL | Segredos de produção hardcoded em `src/utils.js`. | Chaves de banco, gateway de pagamento e SMTP ficavam expostas a qualquer pessoa com acesso ao repositório. |
| CRITICAL | PAN completo do cartão e chave do gateway enviados para log; senhas em texto puro ou hash caseiro. | Isso viola práticas básicas de segurança/PCI e torna credenciais e dados de pagamento recuperáveis. |
| CRITICAL | Relatório financeiro e deleção de usuários sem autenticação. | Um cliente anônimo podia ler PII/receita e destruir usuários. |
| HIGH | `AppManager` era um God Component. | O mesmo componente criava schema, seed, rotas, validação, pagamento, SQL, auditoria e resposta HTTP. |
| HIGH | Checkout com múltiplas escritas sem transação. | Uma falha após criar usuário deixava dados parciais sem matrícula/pagamento, corrompendo o fluxo financeiro. |
| HIGH | Estado global mutável e conexão compartilhada. | Cache e conexão viviam no processo inteiro, gerando vazamento entre requisições e comportamento dependente de ordem. |
| HIGH | Hash de senha customizado e não criptográfico. | Senhas eram fáceis de quebrar e não havia primitiva mantida para verificação. |
| MEDIUM | Validação de input insuficiente derrubava o processo. | Um `card` numérico causava `TypeError` em `startsWith`, gerando DoS e estado parcial. |
| MEDIUM | N+1 no relatório com agregação assíncrona não determinística. | O mesmo relatório podia retornar cursos em ordens diferentes e escalava mal com volume. |
| MEDIUM | Relatório sem limite/projeção adequada. | Dados financeiros e PII eram materializados e expostos sem paginação nem autorização. |
| LOW | Valores mágicos para status, regra de pagamento e porta. | A política de pagamento ficava escondida em literais como prefixo `"4"` e status `"PAID"`. |

### `task-manager-api`

| Severidade | Problema identificado | Por que é relevante |
|---|---|---|
| CRITICAL | Hash de senha serializado nas respostas de usuário e login. | A API expunha diretamente o segredo de autenticação armazenado; com MD5, isso equivale a facilitar quebra offline. |
| CRITICAL | Não havia fronteira real de autenticação/autorização; login retornava token fake não verificado. | Qualquer cliente podia alterar papéis, excluir dados e acessar recursos protegidos sem credenciais. |
| CRITICAL | `SECRET_KEY` hardcoded. | Artefatos assinados por Flask poderiam ser forjados e a rotação dependia de alteração de código. |
| HIGH | Senhas com MD5 sem salt. | Hash rápido e sem salt é inadequado para credenciais; senhas curtas do seed eram triviais de quebrar. |
| HIGH | Rotas concentravam validação, regras, queries, transações e serialização. | Apesar das pastas `models/`, `routes/`, `services/` e `utils/`, a aplicação real era quase toda rota + ORM. |
| HIGH | Debug ligado em `0.0.0.0`. | Falhas não tratadas podiam expor o debugger Werkzeug remotamente no caminho documentado de boot. |
| HIGH | App global com `db.create_all()` em import e config hardcoded. | Importar o módulo alterava banco; isso bloqueava testes isolados e ambientes configuráveis. |
| MEDIUM | N+1 em listagens e relatórios. | `GET /tasks` fazia 17 queries para 10 linhas e `/reports/summary` fazia 19, crescendo com o volume. |
| MEDIUM | Inputs inválidos viravam 500; `except:` mascarava falhas. | Sete entradas malformadas causavam erro interno, confundindo cliente e escondendo causa operacional. |
| MEDIUM | Listagens e relatórios sem paginação. | Um usuário anônimo podia forçar leituras completas de tasks, users, categories e reports. |
| MEDIUM | Regras duplicadas enquanto helpers/model methods existentes não eram usados. | A regra de overdue apareceu em seis lugares e divergiu entre endpoints. |
| MEDIUM | APIs depreciadas: `Query.get()` do SQLAlchemy 2.x e `datetime.utcnow()` no Python 3.14. | A aplicação já emitia warnings/legado e acumulava risco de upgrade e timestamps sem timezone. |
| LOW | Código morto, serializadores inconsistentes e categoria dentro do blueprint de reports. | A estrutura indicava camadas que não existiam de fato e dificultava localizar ownership de domínio. |

## Antes e depois da estrutura

| Projeto | Antes | Depois |
|---|---|---|
| `code-smells-project` | Aplicação Flask plana com `app.py`, controllers, models e database misturando transporte, SQL, regra de domínio, seed e conexão global. | `app.py` como entrada fina e pacote `loja/` com `app_factory.py`, `config.py`, `db.py`, `domain.py`, `errors.py`, `repositories.py`, `routes.py` e `services.py`; testes em `tests/`. |
| `ecommerce-api-legacy` | `src/AppManager.js` centralizava schema, seed, rotas, checkout, relatórios, SQL e resposta HTTP; `utils.js` concentrava config, segredo, cache global e crypto ruim. | `src/appFactory.js`, `config.js`, `db/`, `domain/`, `http/`, `repositories/` e `services/`; `AppManager` e `utils` legados removidos; teste de regressão em `tests/regression.test.js`. |
| `task-manager-api` | Havia pastas `models/`, `routes/`, `services/`, `utils/`, mas as rotas ainda faziam validação, regra de negócio, ORM, transação e serialização; app global criava schema no import. | `create_app`, `config.py`, `errors.py`, `security.py`, `serializers.py`, `validators.py`, `timeutil.py`, services reais, repositories, category routes próprias, testes em `tests/` e `.env.example`. |

## Checklist de validação

| Check | `code-smells-project` | `ecommerce-api-legacy` | `task-manager-api` |
|---|---|---|---|
| Boot real | PASS: `DB_PATH=... APP_ENV=development SECRET_KEY=... PORT=5055 python app.py`, `/health` pronto. | PASS: `ADMIN_TOKEN=validation-admin-token PORT=5318 npm start`, log `LMS API rodando na porta 5318...`. | PASS: boot em porta isolada 5099, `/health` 200 após 3 polls. |
| Endpoints exercitados | PASS: 34/34 golden replay. | PASS: 12/12 endpoints/checks. | PASS: 22/22 rotas exercitadas. |
| Testes automatizados | PASS: 26/26 pytest. | PASS: 3/3 `node --test tests/regression.test.js`. | PASS: 61/61 pytest. |
| Fluxos de domínio | PASS: ciclo de pedido, estoque, listagem, status e relatório. | PASS: checkout, relatório autorizado, deleção legada autorizada e erro de pagamento sem escrita parcial. | PASS: lifecycle de task, cascade de user delete e login. |
| Transações/rollback | PASS: falha injetada não deixou pedidos/itens nem alterou estoque. | PASS: pagamento negado não criou usuário parcial; sucesso fica dentro de transação. | PASS: mutações protegidas e persistência validada em SQLite in-memory. |
| Segurança/erros | PASS: admin SQL/reset removidos, SQL parametrizado, senha hash, health sanitizado, erro 500 sanitizado. | PASS: admin exige token, segredos/logs/PAN/cache legado ausentes, hash via `crypto.scrypt`. | PASS: 18 endpoints protegidos rejeitam anônimo, JWT real, senha fora das respostas, fake token recusado. |
| Performance | PASS: listagem de pedidos com até 3 SQL statements para 5 pedidos. | PASS: relatório com query bounded/determinística e `limit`/`offset`. | PASS: `GET /tasks` 17 -> 5 queries; `/reports/summary` 19 -> 9, estável em 200 rows. |
| Limpeza | PASS: bancos descartáveis, caches e venv/db ignorados. | PASS: runtime/install em `/tmp`, sem estado alvo extra. | PASS: sem estado gerado no root alvo. |

## Logs de execução pós-refatoração

```text
code-smells-project
Command: DB_PATH=... APP_ENV=development SECRET_KEY=... PORT=5055 python app.py
Actual: ready after readiness poll; banner printed; /health reachable; port released after shutdown.
Tests: 34/34 golden PASS; 26/26 pytest PASS.
```

```text
ecommerce-api-legacy
Command: ADMIN_TOKEN=validation-admin-token PORT=5318 npm start
Actual: LMS API rodando na porta 5318...
Tests: node --test tests/regression.test.js -> pass 3, fail 0.
```

```text
task-manager-api
Command: python app.py em porta isolada 5099
Actual: /health 200, readiness after 3 polls, clean shutdown.
Tests: 61/61 PASS.
```

## Comportamento da skill em stacks diferentes

- Em Flask simples (`code-smells-project`), a skill identificou que MVC por nome de arquivo não bastava: controllers e models ainda misturavam HTTP, regra e SQL. A refatoração criou fronteiras explícitas.
- Em Express (`ecommerce-api-legacy`), a skill evitou impor convenções Flask/Python e atacou o ponto real: `AppManager` concentrando rotas, persistência, checkout e relatório.
- Em Flask-SQLAlchemy (`task-manager-api`), a skill foi conservadora: preservou modelos, blueprints e helpers úteis, mas moveu use cases para services/repositories, adicionou factory, autenticação e serializers consistentes.
- No benchmark, a configuração com skill atingiu **96% +/- 7%** de pass rate contra **16% +/- 8%** sem skill. O custo foi maior em tokens (`15207 +/- 4953` contra `10022 +/- 1646`), mas com melhoria clara de qualidade e rastreabilidade.

A skill utilizada para rodar o benchmark pode ser encontrada em `refactor-arch/`

Todos os projetos contêm uma entrada dentro de `.claude/skills/` para disponibilizar `refactor-arch/`

# Como Executar

## Pré-requisitos

- Codex ou Claude Code instalado e configurado.
- Python 3.14+ para os projetos Flask.
- Node.js e npm para o projeto Express.
- Dependências instaladas por projeto antes da validação (`pip install -r requirements.txt`, `npm install` ou `npm ci`).
- A skill `refactor-arch` disponível no projeto. Neste repositório, ela está em `refactor-arch/` e também exposta pelos links em `.claude/skills/refactor-arch`.

## Executar a skill

O agente pode ser aberto na raiz deste repositório ou dentro de cada projeto. A forma mais segura é pedir primeiro a auditoria e só depois aprovar a refatoração usando o caminho e digest emitidos.

### `code-smells-project`

```text
Use a skill refactor-arch para auditar o projeto code-smells-project.
Gere o relatório em reports/audit-project-code-smells-project.md.
Não altere arquivos da aplicação antes da minha aprovação explícita.
```

Depois da auditoria:

```text
Approve reports/audit-project-code-smells-project.md sha256:<digest> all findings
```

### `ecommerce-api-legacy`

```text
Use a skill refactor-arch para auditar o projeto ecommerce-api-legacy.
Gere o relatório em reports/audit-project-ecommerce-api-legacy.md.
Não altere arquivos da aplicação antes da minha aprovação explícita.
```

Depois da auditoria, aprovar todos os findings ou um subconjunto:

```text
Approve reports/audit-project-ecommerce-api-legacy.md sha256:<digest> F-006,F-010
```

### `task-manager-api`

```text
Use a skill refactor-arch para auditar o projeto task-manager-api.
Gere o relatório em reports/audit-project-task-manager-api.md.
Não altere arquivos da aplicação antes da minha aprovação explícita.
```

Depois da auditoria:

```text
Approve reports/audit-project-task-manager-api.md sha256:<digest> all findings
```

## Validar as refatorações

### `code-smells-project`

```bash
cd code-smells-project
pip install -r requirements.txt
python -m pytest

# terminal 1
APP_ENV=development SECRET_KEY=dev-secret PORT=5055 python app.py

# terminal 2
curl http://127.0.0.1:5055/health
```

### `ecommerce-api-legacy`

```bash
cd ecommerce-api-legacy
npm ci
node --test tests/regression.test.js

# terminal 1
ADMIN_TOKEN=validation-admin-token npm start

# terminal 2
curl -H "Authorization: Bearer validation-admin-token" \
  "http://127.0.0.1:3000/api/admin/financial-report?limit=1"
```

### `task-manager-api`

```bash
cd task-manager-api
pip install -r requirements.txt
SECRET_KEY=dev-secret python seed.py
SECRET_KEY=dev-secret python -m pytest

# terminal 1
SECRET_KEY=dev-secret python app.py

# terminal 2
curl http://127.0.0.1:5000/health
```

Também é possível validar os relatórios e o empacotamento da skill:

```bash
python refactor-arch/scripts/validate_audit_report.py \
  reports/audit-project-code-smells-project.md code-smells-project --minimum-findings 5

python refactor-arch/scripts/validate_audit_report.py \
  reports/audit-project-ecommerce-api-legacy.md ecommerce-api-legacy --minimum-findings 5

python refactor-arch/scripts/validate_audit_report.py \
  reports/audit-project-task-manager-api.md task-manager-api --minimum-findings 5

python refactor-arch/scripts/verify_skill_distribution.py refactor-arch
```
