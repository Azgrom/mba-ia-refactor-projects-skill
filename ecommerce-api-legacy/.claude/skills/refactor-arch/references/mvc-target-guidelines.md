# Responsibility-Based MVC Target

Treat MVC as responsibility and dependency boundaries for an API backend, not as a mandatory directory tree.

## Contents

- Target responsibilities
- Dependency direction
- Transport and application contracts
- Domain and persistence boundaries
- Configuration and composition
- Centralized errors
- Dependency injection and transactions
- Framework mapping
- Conservative design checks

## Target responsibilities

| Boundary | Owns | Does not own |
|---|---|---|
| Routes / views | HTTP method/path, parsing, auth context, boundary validation, controller call, response serialization. | Business workflow, transaction coordination, query construction. |
| Controllers / application services | Use-case orchestration, authorization decision, transaction boundary, domain/repository coordination. | Framework request/response objects, SQL/ORM query details. |
| Domain models / domain services | Invariants, calculations, state transitions, domain terminology. | Flask/Express imports, HTTP status selection, connection/session lifecycle. |
| Repositories / data access | Query construction, persistence mapping, storage-specific constraints and batching. | HTTP concerns and business policy. |
| Configuration | Environment reads, typed normalization, safe defaults, required-secret failure. | Use-case behavior and request state. |
| Error handling | Typed failure vocabulary, logging/redaction, framework-wide HTTP mapping. | Scattered route-specific exception shape. |
| Composition root | Dependency creation, lifecycle, route/error registration, application/server startup. | Business rules or query implementation. |

A small application may combine controller and application-service roles or model and repository roles when the combined responsibility remains coherent and testable. Add a boundary only when it removes demonstrated coupling, protects an invariant, or enables required validation.

## Dependency direction

Prefer this direction:

```text
HTTP route → application/controller → domain policy
                              └──────→ repository contract
infrastructure repository ───────────→ repository contract
composition root ────────────────────→ all concrete wiring
```

Domain code does not import transport objects. Application code does not construct framework globals or storage connections. Infrastructure depends inward on the contracts it implements. For simple stacks without formal interfaces, constructor/factory injection and duck-typed contracts are enough.

Avoid service locators and module-global mutable dependencies. An interface with one implementation is justified only when it creates a meaningful test/ownership boundary, not because a diagram expects one.

## Transport and application contracts

Routes should be readable as a short mapping:

1. parse and normalize transport input;
2. identify authentication/authorization context;
3. call one use-case entry point;
4. serialize the result or allow typed errors to reach the global handler.

Application services own use-case ordering and return transport-neutral results. They coordinate repositories and domain behavior, and they define where a multi-write transaction begins and ends.

Keep HTTP status and header selection in the transport/error mapping boundary. Keep domain outcomes explicit enough that the mapper can distinguish validation, authorization, not-found, conflict, and infrastructure failures.

## Domain and persistence boundaries

Domain rules remain valid without a web server or database. Examples include allowed state transitions, totals, ownership, capacity, uniqueness intent, and deletion policy.

Repositories expose operations named for application needs rather than leaking query-builder/session objects. They own batching, eager loading, projections, and storage-specific translation. Database constraints remain the final integrity layer; application validation does not replace them.

Do not turn every record into a rich entity wrapper when the framework model already expresses one coherent responsibility. Preserve useful ORM models and move only misplaced transport/orchestration/query ownership.

## Configuration and composition

Read environment values once at startup or through a coherent configuration object. Normalize types, distinguish safe local defaults from required secrets, and fail clearly when required production values are missing.

The composition root should:

- build configuration;
- create connection/session factories and infrastructure adapters;
- create repositories and application services;
- register routes/blueprints/routers and global errors;
- start the app/server only from the executable entry point.

Importing the application for tests or tooling should not unexpectedly start a server, seed valuable data, or make network calls.

## Centralized errors

Use a shared application-error concept with:

- stable `errorCode`;
- safe client `message`;
- semantic category or HTTP mapping;
- optional internal cause that never crosses the HTTP boundary.

Define domain/application errors such as validation, authorization, not-found, conflict, and infrastructure failures. A framework-native global handler maps known errors to one sanitized JSON schema and maps unexpected failures to a generic response.

Log internal diagnostics with correlation context. Never log or return passwords, password hashes, tokens, full payment-card values, connection strings, raw sensitive payloads, or stack traces.

## Dependency injection and transactions

Prefer constructor or factory parameters for repositories, integrations, time/ID providers, and configuration. Defaults may be assembled at the composition root, not hidden inside use cases.

Own transactions at the application-service boundary when one business action spans dependent writes. Repositories may participate in a supplied unit of work/session but should not independently commit partial steps. Validation must inject a mid-flow failure and prove rollback.

For external side effects, decide explicitly among transactional outbox, post-commit notification, idempotent retry, or compensating action. Do not imply atomicity across systems that cannot share a transaction.

## Framework mapping

| Responsibility | Flask-style expression | Express-style expression |
|---|---|---|
| Transport | Blueprint/route functions and request/response serialization | Router handlers and middleware |
| Application | Plain controller/service objects or functions | Plain controller/service modules or objects |
| Domain | Plain Python models/services or coherent ORM model behavior | Plain JavaScript domain modules/services |
| Persistence | Repository/query module or coherent ORM access boundary | Repository/adapter around database driver/ORM |
| Errors | Registered app/blueprint error handlers | Terminal four-argument error middleware |
| Composition | Application factory and executable entry point | App builder plus separate server/listen entry point |

These are mappings, not filenames. Detect the project's conventions and use idiomatic equivalents verified for its installed framework version.

## Conservative design checks

Before moving or creating a module, answer:

- Which confirmed finding does this change resolve?
- What single responsibility will the target module own?
- Can callers use it without reading its internals?
- Does it improve dependency direction or only move code?
- Which public import, endpoint, status, response meaning, or state effect might change?
- Can an adapter/facade preserve compatibility during the move?
- Is a new interface necessary for coupling/testing, or merely speculative?
- What is the smallest rollback boundary?

Retain a module when it already has coherent ownership. A successful target may remain partially layered, use framework-native models, or follow hexagonal/clean conventions while satisfying the same responsibility contract.
