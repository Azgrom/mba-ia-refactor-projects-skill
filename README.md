# Entregável

Repositório público no GitHub (fork do repositório base) contendo:

- Skill completa em `refactor-arch/` (dentro dos 3 projetos)
  - Link sombólico dentro de cada project, apontando para a skill
- Código refatorado dos 3 projetos (resultado da execução da Fase 3, commitado no repositório)
- Relatórios de auditoria em `reports/` (3 arquivos)
  - Os relatórios de autoria dos resultados seguem o prefixo `audit-project`
  - Os relatórios de validação dos débitos encontrados seguem o prefixo `validation`
- `README.md` atualizado

## Estrutura do repositório

- `refactor-arch/` — A skill completa (SKILL.md + arquivos de referência)
- Código refatorado dos 3 projetos — resultado da execução da Fase 3, commitado no repositório
- `reports/audit-project-{1,2,3}.md` — Relatório de auditoria de cada projeto
- `README.md` — Documentação do seu processo
- `docs/refactor-arch-effectiveness-benchmark/` com a validação da eficácia da skill, utilizada como critério de 'feito'
- `docs/spdd` e `docs/superpowers` com documentação gerada por análises das skills superpowers e workdlow structured prompt driven development, utilizando as instruções da `skill-creator` como checklist de levantamento
- `code-smells-project/` — API de E-commerce Python/Flask com code smells intencionais
- `ecommerce-api-legacy/` — LMS API Node.js/Express (com fluxo de checkout) e problemas de implementação
- `task-manager-api/` — API de Task Manager Python/Flask com organização parcial e problemas de segurança/qualidade

## README.md deve conter

**A) Seção "Análise Manual":**

- Lista dos problemas identificados manualmente em cada projeto
- Classificação por severidade
- Justificativa de por que cada problema é relevante

**B) Seção "Construção da Skill":**

- Decisões de design: como estruturou o SKILL.md e os arquivos de referência
- Quais anti-patterns incluiu no catálogo e por quê
- Como garantiu que a skill é agnóstica de tecnologia
- Desafios encontrados e como resolveu

**C) Seção "Resultados":**

- Resumo dos relatórios de auditoria dos 3 projetos (quantos findings por severidade em cada)
- Comparação antes/depois da estrutura de cada projeto
- Checklist de validação preenchido para cada projeto
- Screenshots ou logs mostrando as aplicações rodando após refatoração
- Observações sobre como a skill se comportou em stacks diferentes

**D) Seção "Como Executar":**

- Pré-requisitos (a ferramenta escolhida — Claude Code, Gemini CLI ou Codex — instalada e configurada)
- Comandos para executar a skill em cada projeto
- Como validar que a refatoração funcionou

# Análise Manual

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

Solicitei que `/superpowers` carregasse as instruções de `/skill-creator` e passasse o plano resultante para `/spdd-analysis`

Em um novo contexto, solicitei para `/spdd-generate` criar o prompt de criação da skill

Em um novo contexto, solicitei `/skill-creator` para executar a criação da skill com o prompt gerado

Workdlow SPDD pode ser encontrado [aqui](https://martinfowler.com/articles/structured-prompt-driven/)

# Resultados

Só se mexe com performance, medindo. O critério de aceite é definido pelo quão bom pode-se considerar feito. O quão bom deve ser medido pela eficácia da skill, através de benchmark. O resultado do benchmark pode ser encontrado em `docs/refactor-arch-effectiveness-benchmark`

A skill utilizada para rodar o benchmark pode ser encontrada em `refactor-arch/`

Todos projetos contém um link simbólico dentro de `.claude/skills/` que aponta para `refactor-arch/`

# Como Executar

Abre Claude Code. Solicita que as instruções de `refactor-arch/` analisem o codebase.

O Claude Code pode ser executado a partir da raiz deste repositório, ou a partir de dentro de cada um dos projetos
