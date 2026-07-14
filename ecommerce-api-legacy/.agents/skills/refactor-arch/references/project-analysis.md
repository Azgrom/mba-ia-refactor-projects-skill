# Project Analysis

Build a bounded, reproducible understanding of the original application before assigning findings.

## Contents

- Discovery order
- Source scope
- Stack and dependency versions
- Entry points, routes, and persistence
- Responsibility map
- Behavioral baseline
- Mutation snapshot
- Output contract
- Stop conditions

## Discovery order

1. Read repository instructions and run documentation first. They define allowed tools, documentation sources, generated-code rules, and safe commands.
2. Inventory top-level files and manifests without installing or upgrading dependencies.
3. Identify candidate application roots, entry points, route registration, and composition code.
4. Traverse imports from entry points and route registration to bound executable source.
5. Inspect models, schema, migrations, seed data, use-case verbs, and request examples to infer the domain.
6. Map persistence lifecycle, external integrations, environment inputs, boot commands, ports, and generated state.
7. Inventory every endpoint and representative multi-step domain flow.
8. Map who owns transport, orchestration, domain rules, persistence, configuration, errors, and composition.
9. Capture a behavioral baseline and all discovery limitations.

Use the least invasive command that answers the question. Do not install dependencies merely to identify declared versions. Do not run migrations, seeds, boot commands, or requests against valuable state.

## Source scope

Build scope from entry-point and route-registration reachability, then reconcile it with manifests and documented layout.

Include:

- application entry points and composition roots;
- registered routes, routers, blueprints, middleware, and error handlers;
- controllers, services, models, domain logic, repositories, data access, configuration, serializers, and relevant helpers;
- migrations or schema definitions when they execute or constrain application behavior.

Exclude by default:

- `.git/`, dependency directories, virtual environments, caches, coverage, build output, logs, databases, and editor state;
- generated, vendored, minified, or copied third-party code;
- examples and tests that do not execute in the application path.

List every exclusion category. If a suspicious file is excluded, explain why. In monorepos or mixed-stack repositories, identify the target application boundary or ask for one; do not silently audit adjacent services.

## Stack and dependency versions

Report language and framework evidence from multiple signals:

- manifests and lockfiles;
- imports/requires and framework construction;
- entry-point commands and documentation;
- installed package metadata when already available.

Separate declared constraints from resolved/installed versions. A loose declaration is not proof of the runtime version. Record unresolved versions explicitly because deprecated-API evaluation depends on them.

Use repository-prescribed documentation tools for version-sensitive claims. Documentation availability is evidence provenance, not a reason to guess.

## Entry points, routes, and persistence

Trace registration rather than assuming filenames.

For Flask-like stacks, inspect application factories, `Flask(...)`, decorators, blueprints, `register_blueprint`, `add_url_rule`, CLI commands, and registered error handlers.

For Express-like stacks, inspect application construction, `app.METHOD`, `router.METHOD`, `app.use`, exported routers, manager/setup functions, terminal middleware, and listen/server entry points.

For unknown stacks, search framework imports, route verbs, server startup calls, manifest scripts, and request collections. State the heuristic and confidence.

For every endpoint record:

| Field | Meaning |
|---|---|
| Method and path | Include prefixes introduced by nested registration. |
| Handler chain | Authentication, validation, controller/service, and error path. |
| Success contract | Representative request, status class, response meaning, and side effects. |
| Failure contract | Invalid, not-found, conflict, authorization, and infrastructure cases that apply. |
| State effect | Tables/collections touched, transaction expectation, and observable follow-up. |
| Evidence | Route declaration and indirect registration locations. |

Map persistence type, connection/session lifetime, schema ownership, initialization, seed behavior, transaction ownership, cleanup, and whether state is persistent, ephemeral, or externally managed.

## Responsibility map

Describe present ownership without judging folder names:

| Responsibility | Questions |
|---|---|
| Transport | Who reads HTTP input, auth context, headers, and maps responses? |
| Application flow | Who sequences a use case and coordinates a transaction? |
| Domain | Where are invariants, calculations, and state transitions? |
| Persistence | Who builds queries, uses sessions/connections, and maps stored records? |
| Configuration | Where are environment values read and defaults decided? |
| Errors | Where are internal failures classified, logged, sanitized, and mapped to HTTP? |
| Composition | Where are dependencies created, routes registered, and the server started? |

Name concrete modules and their callers. A long file is not automatically a God Component; unrelated reasons to change and dependency concentration are the evidence.

## Behavioral baseline

Capture original behavior before mutation:

1. Boot commands, prerequisites, environment variables, port/defaults, readiness signal, and bounded timeout.
2. Every discovered endpoint with at least one representative successful case.
3. Applicable invalid, not-found, authorization, conflict, and infrastructure cases.
4. Multi-step domain flows that cross endpoints or writes.
5. Persistence expectations: created/updated/deleted records, totals, ownership, ordering, rollback, and orphan behavior.
6. Security exceptions where preserving an unsafe contract would conflict with remediation. Mark these as proposed, not authorized.

Prefer observable integration behavior over syntax. Run dynamic checks only in disposable state. If dependencies, integrations, or expected outputs are unavailable, preserve the static inventory and record precisely what could not be established.

## Mutation snapshot

Before audit, prove what “unchanged” means:

- In Git: record `git status --short`, current diff, and relevant untracked files. Pre-existing changes belong to the user.
- Outside Git: hash the scoped source, manifests, lockfiles, configuration, schemas, databases, and tests.
- Keep the report path outside the compared application scope when practical.

Recheck after audit. Cache, bytecode, database, lockfile, or log creation counts as mutation if the audit run caused it.

## Output contract

```markdown
## Project Fingerprint
- Language: [language and version evidence]
- Framework: [framework and declared/resolved versions]
- Domain: [entities, use cases, and evidence]
- Entry points: [repository-relative paths]
- Routes: [count and registration mechanisms]
- Persistence: [technology, lifecycle, and state class]
- Architecture shape: [current responsibility ownership]
- Source scope: [included file count and rule]
- Exclusions: [categories and rationale]
- Environment/integrations: [requirements]
- Discovery limitations: [none or explicit list]

## Behavioral Baseline
- Boot: [commands, readiness, state]
- Endpoints: [inventory artifact or concise list]
- Domain flows: [representative flows]
- Persistence expectations: [observable effects]
- Proposed security exceptions: [none or explicit list]
```

## Stop conditions

Stop before refactoring when any of these remains materially uncertain:

- target application or source boundary;
- entry point or route surface;
- persistence lifecycle or valuable-state safety;
- representative domain behavior;
- required dependency version for a proposed deprecation finding;
- report path or permission to create it.

Return the partial fingerprint and actionable limitations. Uncertainty is safer and more useful than a confident destructive guess.
