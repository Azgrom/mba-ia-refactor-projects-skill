# SPDD Analysis: Refactor-Arch Macro Objectives

## Original Business Requirement

# Macro-objective compilation for `refactor-arch`

## Purpose

Deliver a reusable Custom Skill named `refactor-arch` that audits and safely refactors legacy backend applications toward MVC while preserving externally observable behavior. The workflow must be technology-agnostic at its core and must prove that portability on the repository's two Python/Flask APIs and one Node.js/Express API.

## Macro Objectives

1. **Understand each project before judging it.** Detect the language, framework, dependencies, database, application domain, source scope, entry point, current architecture, and existing responsibility boundaries. Treat the E-commerce API, LMS checkout API, and Task Manager API as different domain and architecture shapes rather than assuming a fixed project layout.
2. **Produce an evidence-based Architecture Audit.** Evaluate the discovered code against MVC and SOLID responsibility boundaries plus security, performance, maintainability, validation, and deprecated-API concerns. Every finding must be traceable to an exact file and line range, explain impact, recommend a direction, and use the shared CRITICAL, HIGH, MEDIUM, or LOW severity vocabulary. Findings must be ordered by severity and assembled into a structured audit report.
3. **Govern all mutation through an explicit human gate.** Execute Project Analysis and Architecture Audit before changing files, stop after the audit report, and require explicit confirmation before Refactoring begins. A report is a review artifact, not implicit permission to mutate the target application.
4. **Refactor toward contextual MVC responsibility boundaries.** Use Models for domain and data concerns, Views/Routes for transport or presentation concerns, Controllers for application flow, configuration for environment-specific values, centralized error handling, and a clear composition entry point. Adapt the transformation to the current project: decompose a monolith where needed and improve an already partially layered system without destroying useful structure.
5. **Preserve domain behavior while eliminating confirmed findings.** Keep the original API capabilities and business flows working, including Produto–Usuário–Pedido ordering, Course–Enrollment–Payment checkout, and Task–User–Category management. Architecture improvement is incomplete if it silently changes endpoint behavior, corrupts state, or leaves confirmed in-scope problems unresolved without an explicit disposition.
6. **Validate outcomes with observable evidence.** After refactoring, prove that each application boots without errors and that its original endpoints continue responding. Validation must cover the application surface, not merely syntax or import success, and failed checks must prevent a successful completion claim.
7. **Encode reusable knowledge rather than project-specific instructions.** Keep the `SKILL.md` focused on the three-phase workflow and back it with Markdown references for project-analysis heuristics, an anti-pattern catalog, the audit-report contract, target MVC guidelines, and a refactoring playbook. The catalog must contain at least eight distributed-severity anti-patterns including deprecated APIs; the playbook must contain at least eight concrete before/after transformation patterns.
8. **Calibrate the skill against human-reviewed evidence.** Document at least five manually identified problems per target project, including at least one CRITICAL or HIGH, two MEDIUM, and two LOW findings, then use those baselines to verify that the automated audit detects meaningful issues rather than merely producing volume.
9. **Prove portability and leave traceable deliverables.** Run the complete three-phase workflow successfully on all three projects, retain an equivalent copy of the skill for each target project using the chosen tool's convention, save one audit report per project, preserve validation evidence, and update the repository README with manual analysis, skill design decisions, results, and execution guidance.

## Constraints

- The implementation must use Custom Skills or the equivalent in Claude Code, Gemini CLI, or OpenAI Codex; the skill name `refactor-arch` and `SKILL.md` are fixed.
- The phase order is strict: Project Analysis → Architecture Audit → human confirmation → Refactoring and Validation.
- No target-project file may be modified before explicit confirmation after the Architecture Audit.
- Technology-agnostic behavior must be demonstrated on `code-smells-project`, `ecommerce-api-legacy`, and `task-manager-api`, including the partially organized Task Manager codebase.
- Reference knowledge must be stored as Markdown and must cover all five required knowledge areas.
- Reports must be saved as `reports/audit-project-1.md`, `reports/audit-project-2.md`, and `reports/audit-project-3.md`.

## Acceptance Criteria

1. On all three target projects, Project Analysis correctly identifies the language, framework, domain, architecture shape, and realistic source scope.
2. On all three target projects, Architecture Audit emits a report that follows the reference template, orders findings from CRITICAL to LOW, and gives exact file and line evidence for every finding.
3. On every target project, Architecture Audit identifies at least five genuine findings.
4. On every target project, the findings include at least one CRITICAL or HIGH issue.
5. Deprecated-API detection is included and reports version-relevant replacements when applicable.
6. The workflow pauses after Architecture Audit and performs no file mutation until the user explicitly approves Refactoring.
7. Refactoring establishes or improves MVC responsibility boundaries, externalized configuration, centralized error handling, and a clear entry point without forcing one identical directory tree onto all stacks.
8. Each refactored application boots without errors.
9. Every original endpoint and documented business flow continues responding correctly after refactoring.
10. The knowledge pack contains all five required Markdown reference areas, at least eight distributed-severity anti-patterns, and at least eight before/after transformation patterns.
11. The complete workflow succeeds on all three projects, and each project has the required skill copy, saved audit report, and validation evidence.
12. The root README contains the manual analysis for all projects, skill-construction decisions, before/after results, completed validation checklists, runtime evidence, and execution instructions.

## Domain Concept Identification

### Existing Concepts (from codebase)

- **Target Project Suite**: Three small backend systems serve as acceptance fixtures for the skill: two Flask applications and one Express application. Together they provide monolithic, manager-centric, and partially layered architecture shapes against which portability must be judged.
- **E-commerce Ordering**: Produto, Usuário, Pedido, and Item de Pedido form the Flask/SQLite store domain. HTTP routes call controller functions; controllers mix request validation, orchestration, and response concerns; model functions combine business rules with persistence; the database module owns schema bootstrap and seed data.
- **LMS Checkout**: User, Course, Enrollment, Payment, and Audit Log form the Express/SQLite learning-commerce domain. The application delegates initialization and routes to a single AppManager, which owns checkout, enrollment, financial reporting, deletion, and data access while shared utilities own configuration and process-wide state.
- **Task Management**: Task, User, and Category form the Flask-SQLAlchemy domain. The application registers Task, User, and Report route blueprints that call ORM Models directly; NotificationService and helpers provide partial separation, but significant orchestration, validation, reporting, and persistence work remains in routes.
- **HTTP Application Contract**: Each project has a documented boot command and port. The Flask store exposes health and commerce routes, the Express LMS includes checkout, financial-report, and user-deletion request examples, and the Task Manager exposes task, user, category, report, login, health, and root surfaces.
- **Persistence Lifecycle**: The store bootstraps a persistent SQLite database, the LMS recreates an in-memory SQLite database on startup, and the Task Manager uses SQLAlchemy with a separate seed step. These different lifecycles constrain how refactoring and regression validation can preserve state.
- **Severity Vocabulary**: The README already defines CRITICAL, HIGH, MEDIUM, and LOW in terms of architecture, security, maintainability, performance, and readability impact. This vocabulary is the shared policy for manual findings and automated reports, but it is not yet encoded in a repository-local skill or report contract.

### New Concepts Required

- **Refactor-Arch Skill**: The reusable workflow owner that coordinates Project Analysis, Architecture Audit, the human confirmation gate, Refactoring, and Validation across a discovered target project.
- **Project Fingerprint**: A technology-neutral description of stack, dependencies, persistence, domain, entry points, source scope, and current responsibility boundaries that establishes the context for later judgments.
- **Architecture Finding**: A traceable audit unit that connects a detected signal to severity, exact evidence, impact, and a transformation direction without changing the code.
- **Architecture Audit Report**: The ordered, reviewable aggregate of findings and severity totals that becomes both the Phase 2 deliverable and the decision input for the human gate.
- **Anti-Pattern Catalog**: The reusable policy that defines detection signals and severity rationale across MVC, SOLID, security, performance, quality, validation, and deprecated-API concerns.
- **MVC Target Model**: A responsibility-based destination for Models, Views/Routes, Controllers, configuration, error handling, and the composition entry point that can be expressed appropriately in Flask and Express.
- **Refactoring Transformation**: A catalog-linked, context-sensitive change pattern that removes a confirmed finding while preserving the relevant domain and HTTP contracts.
- **Human Confirmation Gate**: The lifecycle boundary that owns the transition from read-only audit to repository mutation and prevents Architecture Audit from being treated as implicit authorization.
- **Behavioral Baseline**: The pre-change description of bootability, endpoints, representative domain flows, and persistence expectations against which the refactored system is evaluated.
- **Validation Evidence**: Observable proof of boot and endpoint behavior after refactoring, including failure visibility; it supports completion claims and README results.
- **Portability Contract**: The invariant workflow and output semantics shared across stacks, separated conceptually from stack- and framework-aware discovery, transformation, and validation knowledge.
- **Manual Audit Baseline**: Human-reviewed findings for each fixture that calibrate severity, establish meaningful expected detections, and reveal false negatives or superficial audit behavior.

### Key Business Rules

- **Analysis precedes judgment**: No finding is valid until the target's stack, domain, source boundary, persistence, and current architecture have been discovered.
- **Audit precedes mutation**: Project Analysis and Architecture Audit are read-only; only explicit user approval can open the Refactoring phase.
- **Evidence is mandatory**: Every finding must point to exact source evidence and state impact and recommendation; unsupported labels do not count toward acceptance thresholds.
- **Severity is impact-based**: CRITICAL through LOW must retain the README's shared meaning across the manual baseline, catalog, reports, and all three stacks.
- **Finding counts measure genuine coverage**: Each fixture needs at least five defensible findings and at least one CRITICAL or HIGH issue; duplicates or invented issues cannot satisfy the threshold.
- **Architecture is responsibility-based**: MVC success depends on separation and dependency direction, not on mechanically producing identical folder names in every framework.
- **Existing useful structure must be preserved**: The Task Manager's current Models, Route Blueprints, Service, and helpers are inputs to improvement, not evidence that the whole project should be rebuilt.
- **Externally observable behavior is invariant**: Original endpoints, domain flows, status semantics, and relevant persistence effects must remain valid unless the reviewed audit explicitly identifies unsafe behavior that requires an agreed contract change.
- **Validation gates completion**: A project cannot be reported as successfully refactored if it does not boot or if its original endpoint suite has not been exercised successfully.
- **Security findings cannot be cosmetically moved**: Hardcoded secrets, unsafe data access, weak credential handling, sensitive output, and destructive privileged behavior must be removed or controlled, not merely relocated into new MVC folders.
- **Deprecation judgments are version-aware**: A deprecated-API finding must be grounded in the detected dependency version and identify a valid modern direction; generic staleness guesses are insufficient.
- **Copies must remain equivalent**: The skill distributed to all three target projects must express the same workflow and knowledge contract so portability results are comparable.

## Strategic Approach

### Solution Direction

- Treat the three applications as an executable acceptance suite for a single responsibility-driven skill. The overall flow is: discover the project and its domain → build a Project Fingerprint → evaluate scoped source against the Anti-Pattern Catalog → emit an Architecture Audit Report → stop at the Human Confirmation Gate → apply context-sensitive transformations toward the MVC Target Model → validate boot, endpoints, domain flows, and persistence expectations → retain reports and Validation Evidence.
- Keep workflow invariants in the skill orchestration while allowing detected stack and architecture shape to select appropriate knowledge and validation strategies. The E-commerce API needs decomposition of a controller/model/database chain, the LMS needs decomposition of AppManager and shared utilities, and the Task Manager needs boundary correction within an existing blueprint/model structure.
- Use the required manual findings as a calibration baseline, not as a hardcoded answer key. They should test whether the audit's signals and severities are meaningful while still allowing the skill to discover additional genuine findings.
- Establish a behavioral baseline before Refactoring because the repository currently has no automated tests. Existing run instructions and LMS HTTP examples are initial anchors, but the complete endpoint surfaces and state expectations must become explicit before change begins.

### Key Design Decisions

- **One invariant workflow with stack-aware knowledge**: A single monolithic prompt is simpler but tends to confuse universal policy with framework conventions. → Keep phase semantics, evidence, severity, consent, and output contracts invariant while making discovery, deprecation checks, transformations, and validation responsive to the detected stack.
- **Responsibility-based MVC rather than tree normalization**: An identical tree is easy to verify visually but can erase useful framework conventions and over-refactor the Task Manager. → Define the target through ownership and dependency boundaries; allow Flask blueprints and Express routers/controllers to express those boundaries idiomatically.
- **Immutable audit snapshot at the approval boundary**: Recomputing or mutating findings during refactoring weakens traceability between what the human approved and what changed. → Treat the reviewed Architecture Audit Report as the scope baseline, with any newly discovered issue surfaced rather than silently added to the mutation scope.
- **Behavioral baseline as a first-class concept**: Boot-only checks are cheap but miss broken responses, workflows, and state. Full exhaustive testing is costly and absent from the repository. → Capture every original endpoint plus representative success, failure, and persistence-sensitive flows, then require post-change equivalence appropriate to each project.
- **Version-aware deprecated-API policy**: A static list is portable offline but becomes stale and produces false positives across dependency versions. → Ground deprecation findings in detected versions and current authoritative documentation, while treating unavailable or unverified documentation as an explicit audit limitation.
- **Security and data integrity outrank cosmetic layering**: Moving code can make a tree look like MVC while SQL injection, credentials, weak hashes, sensitive responses, or orphaned data remain. → Prioritize elimination of CRITICAL/HIGH behavioral risks within the same responsibility-based transformation program.
- **Canonical skill source with controlled distribution**: Independent copies satisfy project-local discovery but can drift. A central-only skill avoids drift but does not satisfy the required per-project deliverable. → Maintain one canonical definition and propagate equivalent project-local copies through a reproducible verification step.
- **Explicit disposition for every approved finding**: Requiring every issue to vanish may encourage unsafe broad rewrites; allowing arbitrary deferral undermines the objective. → Each approved finding must be resolved or explicitly deferred with rationale and residual risk, and unresolved acceptance-blocking findings prevent completion.

### Alternatives Considered

- **Separate Flask and Express skills**: Rejected because it would prove stack-specific automation rather than the required portability of `refactor-arch`.
- **One fixed target directory template**: Rejected because file layout is not equivalent to separation of responsibilities and would mishandle the already partially organized Task Manager.
- **Immediate automatic refactoring after audit**: Rejected because it violates the mandatory human approval boundary and expands the risk of destructive changes.
- **Boot-only validation**: Rejected because all three systems can start while core endpoint behavior, database effects, checkout, ordering, reporting, authentication, or task workflows are broken.
- **Hardcoded detection of only the manually listed findings**: Rejected because it would overfit the fixtures and fail the intended general architecture-audit capability.
- **Static deprecated-API blacklist**: Rejected because deprecation is dependency- and version-specific and a frozen list would quickly lose authority.

## Risk & Gap Analysis

### Requirement Ambiguities

- **Technology-agnostic scope**: The phrase can mean any language/framework, while acceptance demonstrates only Flask and Express. The supported universe and expected behavior for unknown stacks need an explicit boundary.
- **Chosen tool and project-local skill path**: The README allows Claude Code, Gemini CLI, or Codex and shows Claude paths, while this workspace is using Codex-style skills. The canonical and copied paths need to be fixed before the REASONS Canvas defines deliverables.
- **Meaning of View in backend MVC**: The README permits Views/Routes, but the boundary among routes, serializers/presenters, and controllers is not fully defined for API-only systems.
- **Refactoring completion threshold**: The objective says to eliminate found problems, examples mention zero remaining anti-patterns, and acceptance only requires minimum finding counts plus functional applications. The policy for LOW findings and accepted deferrals needs clarification.
- **Behavioral equivalence**: “Endpoints continue responding” does not specify whether equivalence includes status codes, response semantics, side effects, authentication behavior, performance, or only non-error responses.
- **Security-driven contract changes**: Some existing endpoints expose secrets or unsafe administrative capabilities. Preserving them exactly conflicts with eliminating CRITICAL security findings, so approved secure replacement behavior must be defined.
- **Data preservation**: The persistent SQLite fixtures contain seed or runtime state, but the requirement does not say whether refactoring may recreate databases or must migrate existing data losslessly.
- **Deprecation authority and offline behavior**: The requirement asks for modern replacements without defining authoritative documentation sources or behavior when current documentation is unavailable.
- **Skill responsibility versus repository-delivery responsibility**: It is unclear whether the skill itself must copy its files, create commits, update README evidence, and prepare the public repository, or whether those are operator responsibilities around the skill runs.

### Edge Cases

- **Unknown or mixed stack**: A target may have multiple manifests, generated code, nested applications, or no recognizable dependency file, making source scope and framework detection uncertain.
- **Already compliant project**: A well-structured target may not contain five genuine findings; the threshold must not incentivize fabrication merely to satisfy a fixture-oriented count.
- **Non-MVC-native architecture**: A project may deliberately use hexagonal, clean, event-driven, serverless, or framework-native patterns whose responsibility boundaries are sound but whose directory names differ from MVC.
- **Incomplete validation surface**: The Flask projects have no request collection and none of the three projects has an automated test suite, so endpoint discovery and expected outcomes can be incomplete before refactoring.
- **External integration unavailability**: Notification email, payment behavior, ports, or other environmental dependencies may be unavailable during validation even when local architecture changes are correct.
- **Persistent versus ephemeral databases**: Repeated validation can retain state in the Flask databases but recreate all LMS state at boot, producing inconsistent or order-dependent endpoint outcomes.
- **Partial transformation failure**: Multi-file moves can leave imports, routes, schema initialization, or runtime wiring in an intermediate broken state unless the transformation lifecycle is recoverable.
- **Overlapping findings**: One source region may trigger God Class, business logic in routes, weak validation, secret exposure, and data-access issues; independent transformations can conflict or double-count the same root cause.
- **Dynamic or indirect routing**: Runtime registration, decorators, blueprints, and manager-owned route setup can make endpoint inventory and exact caller attribution incomplete if discovery relies only on filenames.
- **Version ambiguity**: Loose or ranged dependency declarations can make a deprecated API valid for one installed version and obsolete for another.

### Technical Risks

- **False-positive audit evidence**: Text-only heuristics can misclassify examples, dead code, generated files, or framework conventions. Mitigation direction: combine structural signals with caller and dependency context before assigning severity.
- **Behavioral regression under broad refactoring**: The three fixtures concentrate business rules, persistence, and transport concerns, so decomposing them can change ordering totals, checkout atomicity, reports, authentication, task status rules, or serialization. Mitigation direction: establish domain-flow baselines before mutation and verify them afterward.
- **Weak regression evidence**: Boot and superficial HTTP success can miss incorrect data, side effects, authorization, or error contracts. Mitigation direction: make endpoint and representative business-flow evidence explicit and failure-sensitive.
- **Data integrity during separation**: Checkout/enrollment/payment and order/inventory flows span multiple writes, while user deletion can create orphans. Mitigation direction: make transactional and ownership boundaries part of the reviewed architectural target.
- **Security persistence through relocation**: Credentials, weak hashes, unsafe data access, sensitive health output, and raw administrative operations appear across all fixtures. Mitigation direction: audit post-refactor behavior, not only new file placement.
- **Skill-copy drift**: Three project-local copies can diverge after iteration, invalidating portability comparisons. Mitigation direction: verify equivalence from a canonical source before every acceptance run.
- **Context-scale failure on real projects**: A workflow proven on tiny fixtures may exhaust context or miss modules in larger repositories. Mitigation direction: require bounded discovery, explicit source-scope reporting, caller tracing, and coverage limitations.
- **Documentation freshness dependency**: Reliable deprecated-API findings require current, version-matched sources and can fail under network or quota constraints. Mitigation direction: surface evidence provenance and treat unverified deprecation checks as incomplete rather than guessing.
- **Destructive normalization of partial architecture**: Treating the Task Manager as a monolith would replace existing useful Models, blueprints, and Service abstractions and increase change risk. Mitigation direction: judge responsibility and coupling before deciding whether to move, split, or retain a module.

### Acceptance Criteria Coverage

| AC# | Description | Addressable? | Gaps/Notes |
|-----|-------------|--------------|------------|
| 1 | On all three target projects, Project Analysis correctly identifies the language, framework, domain, architecture shape, and realistic source scope. | Yes | The fixtures expose manifests, entry points, domain models, and distinct architecture shapes; “realistic source scope” still needs measurable discovery rules in the REASONS Canvas. |
| 2 | On all three target projects, Architecture Audit emits a report that follows the reference template, orders findings from CRITICAL to LOW, and gives exact file and line evidence for every finding. | Yes | The report contract and severity vocabulary are explicit, but neither artifact exists yet. |
| 3 | On every target project, Architecture Audit identifies at least five genuine findings. | Yes | Current code contains sufficient cross-cutting architecture, security, performance, and quality signals; the design must prevent duplicate root causes from inflating counts. |
| 4 | On every target project, the findings include at least one CRITICAL or HIGH issue. | Yes | Actual code contains high-impact security and responsibility-boundary risks in every fixture. |
| 5 | Deprecated-API detection is included and reports version-relevant replacements when applicable. | Partial | Dependency versions are discoverable, but the authoritative documentation source, installed-versus-declared version policy, and unavailable-doc behavior are unspecified. |
| 6 | The workflow pauses after Architecture Audit and performs no file mutation until the user explicitly approves Refactoring. | Yes | The lifecycle gate is explicit and can be made a hard phase invariant. |
| 7 | Refactoring establishes or improves MVC responsibility boundaries, externalized configuration, centralized error handling, and a clear entry point without forcing one identical directory tree onto all stacks. | Partial | The responsibility target is clear at a macro level; View/Route/Controller boundaries and acceptable framework-native variants need tactical definition. |
| 8 | Each refactored application boots without errors. | Yes | Every project has a documented run command; deterministic startup, seed handling, and port isolation must be included in validation design. |
| 9 | Every original endpoint and documented business flow continues responding correctly after refactoring. | Partial | Endpoint surfaces are discoverable, but complete expected response, side-effect, and security-adjusted contracts are not documented for all projects. |
| 10 | The knowledge pack contains all five required Markdown reference areas, at least eight distributed-severity anti-patterns, and at least eight before/after transformation patterns. | Yes | These are deterministic artifact requirements; no repository-local knowledge pack exists yet. |
| 11 | The complete workflow succeeds on all three projects, and each project has the required skill copy, saved audit report, and validation evidence. | Partial | All artifacts are addressable, but the selected tool path, canonical-copy mechanism, and operator-versus-skill ownership must be decided. |
| 12 | The root README contains the manual analysis for all projects, skill-construction decisions, before/after results, completed validation checklists, runtime evidence, and execution instructions. | Yes | The current README is the assignment specification and does not yet contain these result sections; they can be produced after the three acceptance runs. |
