Completed the architecture audit and conservative refactor of `fixture/`.

The API now keeps Flask routes focused on HTTP concerns, moves workflows and transactions into focused task/user/category/report services, separates category CRUD from reporting, reuses model domain rules, supports configured app construction, and removes embedded SMTP credentials. Public routes, status semantics, response meaning, and tested persistence effects remain intact.

Verification: `7 passed` with the characterization suite, and the full fixture compiles successfully. The remaining warnings concern the existing naive UTC timestamp model.

The detailed audit is in `outputs/audit.md`. It also documents intentionally deferred compatibility-sensitive risks, especially MD5 password storage, password-hash exposure, fake login tokens, malformed search handling, and naive timestamps.
