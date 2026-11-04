# stackit Constitution

## Core Principles

### Modular Code

Every function, class, and module MUST have a single clear purpose. If you cannot describe what it does in one or two sentences, it MUST be split.

**The Split Rule:**
- A function does one thing. If describing it requires "and", split it.
- A module groups related functions around one concept (e.g., "auth validation", "storage operations", "user queries").
- A file that requires scrolling to understand should be broken into a module directory with an `__init__.py` re-exporting the public interface.

**Structure Pattern:**
```
# Simple module — single file is fine
gcp_secrets.py          # One concept: loading secrets

# Complex module — split into directory
gcp_services/
├── __init__.py         # Re-exports public interface
├── clients/            # Grouped by sub-concept
│   ├── gcp_services.py # Firebase client singletons
│   ├── fb_auth.py      # Auth decorator + helpers
│   └── fb_config.py    # Internal config (not re-exported)
├── gcp_logging.py      # Logging setup
└── gcp_secrets.py      # Secret management
```

**Reuse Before You Write:**
- Before adding a helper, check, or filter, search for one that
  already does the job — by behavior, not just by name.
- A check or filter written twice gets one shared helper, placed next
  to the data it's about, with every call site updated to use it
  instead of its own copy.
- This is the Split Rule's inverse: the Split Rule keeps one function
  from doing two things; this rule keeps two functions from doing the
  same thing. See Consistency below for the same principle applied
  across patterns, not just functions.

**Rationale**: Single-purpose modules are faster to read, easier to test, and give AI assistants enough context in a single file to make correct changes without needing the full codebase. Unreviewed duplication is the same defect from the other direction — a second implementation of the same check drifts from the first the moment one of them is fixed and the other isn't.

### Consistency

Every recurring problem MUST have exactly one solution in the
codebase. When two call sites solve the same problem differently, one
of them is wrong.

**Apply this to:**
- One pattern for refreshing data after a write (e.g. one
  query-invalidation helper), not ad hoc refetches invented per
  feature.
- One error-handling pattern and one shared error-display component —
  don't let each feature grow its own.
- One date/time formatter, reused everywhere a date is shown.
- One home for user-facing copy strings, so a wording change touches
  one file.
- One name per concept across code, copy, and docs. If a concept
  legitimately needs two names (an internal field vs. its public
  label, say), write down which name belongs to which — don't leave
  the mapping implicit.

**Rationale**: Divergent solutions to the same problem are themselves
a bug surface — fixing one path leaves the others broken, and a
newcomer (human or AI) can't tell which pattern is canonical. Solving
every recurring problem once, and naming every concept once, keeps the
codebase legible enough for an agent to extend correctly without
re-deriving the convention each time.

### Testing Discipline

All code MUST be written so it can be tested. Keep business logic pure (input in, output out) and isolate side effects to boundary functions that are testable via mocking singleton imports.

```python
# CORRECT - Pure logic, easy to test without mocks
def validate_email_domain(email: str, valid_domains: list[str]) -> bool:
    domain = email.split("@")[1]
    return domain in valid_domains


# CORRECT - Boundary function with side effects, test via mocking db
async def create_user(email: str, name: str) -> str:
    if not validate_email_domain(email, VALID_DOMAINS):
        raise ValueError("Invalid domain")
    doc_ref = db.collection("users").document()
    await doc_ref.set({"email": email, "name": name})
    return doc_ref.id
```

**Network Isolation:**
All tests MUST run with network access blocked by default. External calls cause test failures unless explicitly allowed.

```python
# Default - network blocked, no annotation needed
def test_unit_logic():
    result = process_data({"key": "value"})
    assert result is not None


# CORRECT - explicitly allow network for integration tests
@pytest.mark.enable_socket
def test_external_api_integration():
    response = requests.get("https://api.example.com")
    assert response.status_code == 200


# CORRECT - allow specific hosts only
@pytest.mark.allow_hosts(["127.0.0.1", "localhost"])
def test_local_service(): ...
```

**pytest-socket Configuration**: Network blocking is enabled via `pytest-socket` plugin configured in `pyproject.toml`.

**Rationale**: Pure logic is trivially testable. Boundary functions are testable via singleton mocking. Network isolation ensures tests are deterministic, fast, and don't depend on external service availability.

### Required Test Coverage

All new code MUST include tests. Tests are not optional and MUST NOT
be deferred to a later phase. The following categories define minimum
coverage:

| Category | What to test | Examples |
|----------|-------------|---------|
| **Pure logic** | Input -> output, edge cases, boundary conditions, error cases. No mocks needed — the easiest and most valuable tests. | Utility functions, formatters, validators, parsers, algorithms, state machines |
| **Components** | Renders correctly with typical props. Renders gracefully with missing/null/empty data. Key interactions (click, toggle) produce expected UI changes. | UI components, widgets, reusable building blocks |
| **Pages / Views** | Smoke render (catches import chain crashes). Loading states. Data display with mocked API/service layer. Key user flows (navigation, form submit). | Route-level components, screens, full page views |
| **API endpoints / Services** | Request/response shape matches contract. Validation rejects bad input. Error codes are correct. Side effects occur (DB writes, queue dispatch). | REST endpoints, GraphQL resolvers, service layer functions with I/O |
| **App entry (smoke)** | Import and render/initialize without runtime errors. Verifies entire dependency tree loads. | App root component, server entry point, CLI entry point |

**Rules:**

1. **Smoke tests are mandatory**: Every app entry point MUST have a
   test that imports and initializes it. This catches dependency
   crashes (missing packages, circular imports, bad re-exports)
   before they reach production.

2. **Pure logic tests first**: If a function has no side effects,
   test it directly. Don't skip tests because "it's simple" — simple
   functions with untested edge cases cause production bugs.

3. **Mock at boundaries, not everywhere**: Mock external I/O
   (database, APIs, file system). Don't mock internal code — if you
   need to mock internal code to test something, refactor for
   testability instead.

4. **Tests accompany code**: Tests for new code ship in the same
   PR/commit. "I'll add tests later" means "tests won't be added."

5. **Missing tests are a review blocker**: Code without tests for
   the applicable categories above MUST NOT be approved.

**Rationale**: Untested code is unverified code. Mandatory coverage
categories prevent the common failure mode where "we'll add tests
later" becomes "tests were never added." Smoke tests alone have
prevented countless production incidents caused by broken import
chains and missing dependencies.

### Test Economy

Tests MUST cover each behavior in exactly one place, at the cheapest
layer that can observe it. More tests are not more coverage — a
bloated suite slows every change and buries the signal from the
failures that actually matter.

**Rules:**

1. **One place per behavior.** Pure logic is tested where it lives —
   in a unit test for that function, not re-verified from every
   caller. A service or GCP-service wrapper is tested at the service
   layer. An API endpoint test checks wiring only: the right status
   code, the right service call, the right response shape — not the
   business rules already covered by the service's own unit tests.
   Same split on the frontend: hooks are tested in hook tests,
   components in component tests, pages/routes check that the right
   components receive the right props, not what's already proven
   inside them.

2. **Test rules, not literals.** Do not write a test whose only job
   is to restate a constant, a count, a list, or a copy string — see
   Change-Tolerant Tests and Copy-Resilient Tests below. Assert
   the invariant behind the data, e.g. "every domain in
   `VALID_DOMAINS` passes `validate_email_domain`", not "`VALID_DOMAINS`
   has these 3 entries".

3. **Repeat a case across variants only when the behavior differs.**
   If two configurations (two agent models, two environments, two
   component sizes) run the identical code path, one test covers
   both. Duplicate a test per variant only when that variant changes
   the outcome.

4. **Recorded AI output is data, not a contract.** A test over a saved
   fixture — a recorded ADK eval transcript, a cached Vertex AI
   response, a golden API payload — MUST derive its expected values
   from the fixture itself, not from a second, hand-maintained copy of
   what the fixture "should" contain; an assertion may only claim what
   the source recording actually supports. When the fixture is wrong
   or stale, re-record it — don't hand-edit the assertion to match.
   The exception is a test about the model's own judgment (quality,
   tone, correctness of reasoning): that belongs in an eval scored by
   a rubric or LLM-judge, not pinned to one exact recorded output.

5. **The test double holds no business rules.** A mock for `db`,
   `bucket`, `auth_client`, or `vertex.client` stores, replies, and
   fails on request — nothing more. It MUST expose only the methods
   exercised by the tests that use it, and an operation nothing
   exercises MUST fail loudly (raise `NotImplementedError` or similar)
   rather than silently returning a default. The rules that decide
   what a real service does — validation, authorization, business
   logic — are tested against the service that owns them, never
   reimplemented inside the double; tests script what the server does
   and verify the caller handles it.

6. **Decision logic lives in pure functions.** Anything with a
   branch — an `if`, a `match`, a threshold — belongs in a pure
   function that can be called directly in a test, not buried inside
   a FastAPI route handler or a React component body where testing it
   means standing up the client or rendering the tree. This is
   Testing Discipline's pure-logic split, applied to branching as
   well as I/O.

7. **Trimming a test must not lose covered lines.** When removing or
   consolidating tests, run coverage before and after; the diff MUST
   NOT drop any previously covered line in any file. A test earns its
   keep by covering a line nothing else covers — losing that line
   without replacement is a regression, even if every remaining test
   still passes.

8. **Find the owner before writing.** Before adding a test, search for
   the test that already owns the behavior and extend or change it
   instead of adding one beside it. A new test file or case is only
   for a behavior that has no owner yet. When a change moves a
   behavior from one place to another, its test moves with it — the
   old test is deleted, not kept alongside the new one. This applies
   at planning time, not just in review: a task that adds tests MUST
   name the existing test file it extends, or state plainly that the
   behavior has no owner yet — "add tests for X" is not a task.

9. **A test must be able to fail on its own.** A test MUST NOT
   recompute the code under test to build its own expected value (e.g.
   rebuilding an expected column order with the same steps the
   implementation uses) — that only proves the function agrees with
   itself. A test MUST NOT assert only that a removed field, key, or
   id is absent; deleting it is the proof, and a type checker plus the
   generic unknown-field test (rule 2) already hold that line. A test
   earns its place by being able to fail for a reason the code under
   test doesn't already guarantee.

**Rationale**: Each rule maps to a failure mode seen in practice:
duplicate assertions at every layer, tests that re-type a constant
instead of a rule, fixture tests that drift from their own
recordings, mocks permissive enough to hide a missing code path,
decision logic that can only be exercised by rendering a page, test
trims that quietly remove the one case that caught a regression,
duplicate tests added because no one checked for an owner first, and
tautological or absence-only tests that can't fail for a real reason.
The fix in every case is the same — test the behavior once, at the
layer that owns it, make sure it can actually fail, and keep the
suite's coverage honest as it changes.

### Change-Tolerant Tests

A test MUST fail only when behavior a caller depends on breaks. A test
that fails on a change a user or caller would accept — new records in
a data file, edited copy, reordered keys, an internal refactor — is
brittle and MUST be rewritten. Once written, a test changes only when
the requirement it covers changes.

**Rules:**

1. **App data is not test data.** JSON, YAML, seed data, prompt files,
   and config that the app loads at runtime change as content, not
   code. Tests MUST NOT pin their record count, record order, or any
   single record's content. Every such file MUST have one validation
   test that checks per-record invariants across *all* records:
   required fields present, types valid, IDs unique, cross-references
   resolve, enum values known. That test grows with the data instead
   of breaking on it.

2. **Tests own their data.** A test that needs exact output builds its
   own input — a builder or factory with valid defaults where the test
   overrides only the fields it is about, or a small fixture under
   `tests/` that exists only for tests. An exact-output test MUST NOT
   read a file the app loads.

3. **Count only what you created.** A count assertion is allowed only
   when the test created the inputs (`len(result) == len(items)`,
   "added 3, got 3 rows"). Against data the test doesn't own, assert
   existence, a lower bound (`>= 1`), or the invariant per item.

4. **Assert the fields you care about.** Compare the keys under test,
   not entire dicts, JSON payloads, or response bodies; an extra field
   or new optional key MUST NOT fail a test. Do not assert order
   unless order is the contract (sorted output, pagination) — otherwise
   compare as sets or sort first.

5. **Check outcomes, not call sequences.** Assert returned values and
   resulting state. Assert a mock call only when that call is itself
   the side effect under test (the DB write, the message sent), and
   then assert the payload that matters — not call count or call
   order. A test that only verifies mocks were called in the order the
   code calls them is a change detector and MUST be rewritten or
   deleted.

6. **No large snapshots.** Full-render, full-page, and full-response
   snapshots are forbidden: they break on any child change and their
   diffs get approved without review. Inline snapshots are allowed for
   small, deliberate output (roughly 20 lines or fewer) with dynamic
   values (timestamps, generated IDs) masked.

7. **Invariants for wide-input functions.** Parsers, validators,
   formatters, and normalizers SHOULD get property-based tests
   (Hypothesis for Python, fast-check for TypeScript) that state the
   rule — round-trips, idempotence, never raising on valid input —
   alongside a few named example cases that document intent.

8. **The review question.** For every test, ask: "Would this fail on a
   change a user or caller would accept?" If yes, it is brittle — fix
   it before merge.

```python
# WRONG - breaks the day someone adds a model to the catalog
def test_model_catalog():
    models = load_model_catalog()
    assert len(models) == 4
    assert models[0]["id"] == "gemini-2.5-pro"


# CORRECT - per-record invariants over the whole app-loaded file
def test_model_catalog_records_are_valid():
    models = load_model_catalog()
    assert models
    ids = [m["id"] for m in models]
    assert len(ids) == len(set(ids))
    for m in models:
        assert m["provider"] in Provider
        assert m["max_tokens"] > 0


# CORRECT - exact output from data the test owns
def test_filter_enabled_models():
    models = [make_model(enabled=True), make_model(enabled=False)]
    assert [m["id"] for m in filter_enabled(models)] == [models[0]["id"]]


# WRONG - whole-body equality fails when a field is added
assert response.json() == {"id": "u1", "name": "Ada", "role": "admin"}

# CORRECT - assert only the fields under test
body = response.json()
assert body["role"] == Role.ADMIN
```

**Rationale**: A brittle test fails without a bug, so every failure
costs a diagnosis and teaches the team to distrust red builds. The
recurring causes are tests pinned to content the app treats as data,
counts of things the test didn't create, whole-object equality,
order assumptions, mock call-sequence checks, and large snapshots.
Each rule above swaps the incidental detail for the invariant the
caller actually relies on, so the suite stays green through content
growth and refactors and goes red only for real regressions.

### Copy-Resilient Tests

Tests MUST NOT match on copy: any human-readable string owned by
product, design, or content rather than by code. This covers UI
labels, headings, placeholders, button text, error and exception
messages, log lines, and prompt text. Copy changes independently of
logic, and a test that matches on it fails for no real reason.

**Frontend — locate elements, in this order:**
1. `getByRole` by role alone (scoped with `within()` when needed), or
   with `name` only when the name comes from mock data or a code
   constant — this keeps queries close to how users and assistive
   technology find elements.
2. `data-testid` — when a role alone isn't unique and the only
   distinguishing name is static copy.
3. DOM structure (tag type, nesting) as a last resort.

**Backend — assert on:**
- HTTP status codes, exception types, and error codes or enum values.
- Structured fields in the response or log record, not the message
  string. `pytest.raises(...)` MUST NOT use `match=` against copy;
  `match=` is allowed only for an identifier or value taken from the
  test's own input.

**Assert values by:**
- Comparing rendered text or response fields against the mock data
  the test passed in, not against hardcoded display strings.
- Matching enum or constant values — these are code-level
  identifiers, not copy.

**Rules:**
1. New components and page sections MUST use semantic elements and
   ARIA roles, and MUST add `data-testid` where a role alone can't
   identify an element.
2. Tests MUST NOT use `getByText`, `getByLabelText`,
   `getByPlaceholderText`, or `getByRole(..., { name })` with a
   hardcoded display string.
3. Enum values and typed constants (status codes, category keys) are
   safe to assert against — they change via code, not content edits.
4. To verify that specific data appears, assert the rendered text
   matches the mock data input, not a hardcoded expected string.

```tsx
// WRONG - breaks when copy changes
expect(screen.getByText("Welcome back, friend!")).toBeInTheDocument();
expect(screen.getByRole("button", { name: /submit/i })).toBeEnabled();

// CORRECT - role alone, scoped to the form
expect(within(screen.getByRole("form")).getByRole("button")).toBeEnabled();

// CORRECT - accessible name taken from mock data
expect(screen.getByRole("link", { name: mockProject.title })).toHaveAttribute(
  "href",
  `/projects/${mockProject.id}`,
);

// CORRECT - testid where the role isn't unique, assert against mock data
expect(screen.getByTestId("greeting").textContent).toContain(mockUser.name);

// CORRECT - enum value is a code constant, not copy
expect(screen.getByTestId("status-badge").textContent).toBe(Status.ACTIVE);
```

```python
# WRONG - breaks when the message is reworded
with pytest.raises(ValueError, match="Email domain is not allowed"):
    validate_user(email="a@other.com")

# CORRECT - exception type, plus a value from the test's input
with pytest.raises(InvalidDomainError, match="other.com"):
    validate_user(email="a@other.com")

# CORRECT - status and error code, not the detail string
assert response.status_code == 403
assert response.json()["code"] == ErrorCode.INVALID_DOMAIN
```

**Rationale**: Copy is owned by designers, product, and content
editors and changes on its own schedule. Tests coupled to it produce
false failures that erode trust in the suite. Role queries keep
frontend tests aligned with how users and assistive technology find
elements; test IDs, error codes, and mock-data assertions cover the
rest, so tests verify behavior without depending on wording.

### Import-Time Safety

Code that runs at module level — top-level function calls in settings
files, client initialization, secret loading — MUST be safe to execute
with no network access. Network-dependent operations MUST be deferred
to first use or explicit initialization calls, never triggered by
`import`.

**Why this matters:**
Network-blocking test tools (e.g., `pytest-socket --disable-socket`)
and sandboxed environments disable sockets before any test code runs.
gRPC clients and HTTP libraries initialized at import time will hang
silently under these conditions instead of raising a catchable
exception — `except Exception` will not save you because the call
never returns.

**Rules:**
- Module-level code MUST NOT open network connections, resolve DNS,
  or call remote services.
- Client singletons, secret loaders, and configuration fetchers that
  require network MUST use lazy initialization (initialize on first
  access, not on import).
- If a module needs a "ready" state that depends on network, expose an
  explicit `init()` or `setup()` function that callers invoke after
  the environment is known to be available.

```python
# WRONG - hangs silently when network is blocked
secrets = SecretManagerClient().get("my-secret")  # runs at import

# WRONG - still runs at import even inside a function default
client = SomeGrpcClient()  # module-level instantiation

# CORRECT - lazy initialization on first use
_client = None


def get_client():
    global _client
    if _client is None:
        _client = SomeGrpcClient()
    return _client


# CORRECT - explicit init called by application startup
def init():
    global secrets
    secrets = SecretManagerClient().get("my-secret")
```

**Rationale**: Import-time network calls create invisible coupling
between module loading and network availability. This breaks test
isolation, slows startup, and produces failures that are
impossible to catch or debug with standard exception handling.

### Boundary Logging

Logging MUST happen at system boundaries — not inside every function. Log where data enters or leaves the system, not where it's transformed.

**Boundary points:**
- API endpoint entry (request received)
- External service calls (GCP, third-party APIs)
- Errors and exceptions
- Startup/shutdown events

```python
# CORRECT - Log at the boundary
async def get_user(user_id: str) -> dict:
    logging.info(f"Fetching user: {user_id}")
    doc = await db.collection("users").document(user_id).get()
    if not doc.exists:
        logging.warning(f"User not found: {user_id}")
        raise HTTPException(status_code=404)
    return doc.to_dict()


# WRONG - Logging inside pure logic
def calculate_score(items: list[int]) -> int:
    logging.info("Starting calculation")  # Noise
    total = sum(items)
    logging.info(f"Sum: {total}")  # Noise
    return total * 2
```

**Rationale**: Boundary logging provides observability without noise. Pure functions don't need logging — their behavior is verified by tests. Logging at edges makes it easy to trace requests through the system.

### Quality Gates

All commits MUST pass pre-commit hooks. Never use `--no-verify` to bypass checks.

```bash
# Run hooks manually on all files
make hooks

# Hooks run automatically on commit
git commit -m "[TASK] :: Description"
```

**Quality Gates (in order):**

| Hook         | Purpose            | Fix Command      |
|--------------|--------------------|------------------|
| ruff check   | Linting violations | `make lint`      |
| ruff format  | Code formatting    | `make format`    |
| ty           | Type checking      | `make typecheck` |
| pytest       | Test failures      | `make test`      |
| yaml-check   | YAML syntax        | Manual fix       |
| large-files  | Prevent bloat      | Remove/gitignore |

**Hook Configuration**: Located at `.config/.pre-commit-config.yaml` (non-default path).

**Rationale**: Pre-commit gates catch issues before they enter the codebase, maintaining consistent quality and preventing CI failures.

### No Backwards Compatibility Before First Release

Until a project reaches its first production release, breaking changes
MUST be made outright. Replace code, schemas, and data shapes
directly — do not add shims, aliases, dual-write paths, or migrations
for data that doesn't matter yet.

```python
# WRONG - compatibility shim for a pre-release schema
def get_user_email(user: dict) -> str:
    return user.get("email") or user.get(
        "email_address"
    )  # old field kept "just in case"


# CORRECT - rename outright, fix the (few) callers
def get_user_email(user: dict) -> str:
    return user["email"]
```

**Rationale**: Shims exist to protect data or callers that must keep
working. Before a first release there are no production callers and no
data worth preserving — a shim only adds a second code path to
maintain and a historical artifact nobody will read. Once a project
ships, standard migration discipline applies.

### Boilerplate Is the Baseline

The team boilerplate is a working system, not a starting point to
improve. Its conventions are decided; epics build on them.

- **Do not change what works.** Configuration loading (`app_settings.py`),
  Firestore wiring (the `NAMESPACE` database in the cloud, `(default)`
  on the emulator, blank `NAMESPACE` allowed), the emulator setup, and
  the Makefile shape MUST stay as they are unless an epic's spec says
  otherwise in so many words.
- **Fewest moving parts wins.** Prefer a documented command over a
  script, a script over a Make target, and a Make target over a
  workflow. No CI/CD, no generated config files, no custom service
  accounts, and no per-environment identity plumbing unless the owner
  asks for it by name.
- **Platform defaults over explicit flags.** Deploy commands MUST pass
  only what the app needs to run. Do not add flags, labels, env vars,
  or settings that restate a default.
- **One knob per fact.** `PROJECT_ID` and `NAMESPACE` in `.env` define
  the environment. Nothing else names a database, bucket, or service.
  If a value can be derived (from the platform, from metadata, from
  another setting), derive it; do not add a variable for it.
- **No new settings without a consumer.** Every new key in `Settings`
  MUST be read by code that ships in the same epic, and that code MUST
  be tested.
- **Ask before inventing infrastructure.** If a plan needs a resource,
  role, secret, or environment the boilerplate does not already have,
  the plan MUST list it as an open question for the owner. Assumed
  infrastructure is a defect.
- **Confirm the reading before editing.** When an instruction admits
  two readings (for example, "we want one" as one config entry versus
  one database name), confirm the intended reading before touching a
  file the owner wrote.

**Rationale**: The boilerplate encodes decisions already paid for.
Rebuilding them inside an epic costs review time and hides accidental
changes among the intentional ones.

## Service Patterns

### I. Use Pre-Configured Clients

All GCP services (Firestore, Auth, Storage, Vertex AI) MUST be accessed via pre-configured clients. Never instantiate Firebase/GCP/genai clients directly.

```python
# CORRECT - Always import from gcp_services
from gcp_services.clients.gcp_services import db, bucket, auth_client
from gcp_services.clients.gcp_vertex import vertex

# WRONG - Never instantiate your own
from firebase_admin import firestore_async

db = firestore_async.client()  # Prohibited
```

**Available Clients:**
- `db` - Firestore async client (auto-configured for emulator or cloud)
- `auth_client` - Firebase Auth client
- `bucket` - Cloud Storage bucket
- `vertex.client` - Gemini `genai.Client` bound to Vertex AI (lazy, created on first access)

**Rationale**: Centralized clients handle emulator detection, project configuration, and credential management automatically. Direct instantiation bypasses environment-aware setup.

### II. Settings-Driven Configuration

All environment configuration MUST flow through the `Settings` class in `app_settings.py`. Never read environment variables directly for application config.

```python
# CORRECT - Use settings object
from app_settings import settings

project = settings.project_id
is_local = settings.is_local
use_emulator = settings.use_emulator

# WRONG - Don't read env vars directly for config
import os

project = os.getenv("PROJECT_ID")  # Prohibited for app config
```

**Settings Cascade**: `.env` file → OS environment variables → GCP defaults

**Key Settings:**
- `settings.project_id` - GCP project identifier
- `settings.is_local` / `settings.is_gcp` - Environment detection
- `settings.use_emulator` - Firebase emulator mode
- `settings.static_dir` - Frontend asset path
- `settings.namespace` - Resource naming prefix (from `NAMESPACE` env var)
- `settings.firestore_db_name` - Firestore database name (defaults to `namespace`)
- `settings.firestore_bucket_name` - Storage bucket name (defaults to `{project_id}-{namespace}`)

**Rationale**: Pydantic Settings provides validation, type coercion, and a single source of truth for configuration across all modules.

### III. Authentication Decorator Pattern

Protected endpoints MUST use the `@firebase_auth_required()` decorator. Never implement custom auth logic.

```python
from gcp_services.clients.fb_auth import firebase_auth_required


@api_router.get("/protected/")
@firebase_auth_required()
async def protected_endpoint(request: Request) -> dict:
    user = request.state.user  # User attached by decorator
    return {"email": user["email"]}


# Admin-only endpoint
@api_router.post("/admin/")
@firebase_auth_required(is_admin=True)
async def admin_only(request: Request) -> dict:
    return {"admin": True}
```

**User Object** (`request.state.user`):
- `uid` - Firebase user ID
- `email` - User email address
- `display_name` - User display name
- `admin` - Boolean admin flag from claims
- `claims` - Full token claims dict

**Domain Whitelist**: Edit `VALID_DOMAINS` in `fb_auth.py` to control allowed email domains.

**Rationale**: Centralized auth handles token verification, user enrichment, and domain validation consistently across all endpoints.

### IV. ADK Agent Structure

All Google ADK agents MUST follow the standard directory structure and export `root_agent`.

```
api_service/agents/
└── my_agent/
    ├── __init__.py    # Exports root_agent
    ├── agent.py       # Agent definition
    └── prompt.py      # Prompt templates
```

**agent.py Pattern:**
```python
from google.adk import Agent

my_agent = Agent(
    name="MyAgent",
    model="gemini-2.5-flash-lite",
    description="What this agent does",
    instruction="Detailed instructions...",
)

root_agent = my_agent
```

**prompt.py Pattern:**
```python
my_prompt = """
Context: {context}
Task: {task}
"""
```

**Rationale**: Consistent structure enables ADK framework discovery, deployment tooling, and maintainable prompt management.

### V. Async-First Database Access

All Firestore operations MUST use async/await. The `db` client is `firestore_async` - synchronous calls are prohibited.

```python
from gcp_services.clients.gcp_services import db


# CORRECT - Async iteration
async def list_collections():
    collections = db.collections()
    return [col.id async for col in collections]


# CORRECT - Await document operations
async def get_user(user_id: str):
    doc = await db.collection("users").document(user_id).get()
    return doc.to_dict()


# WRONG - Synchronous access
def bad_example():
    doc = db.collection("users").document("x").get()  # Missing await
```

**Rationale**: Async database access prevents blocking the FastAPI event loop, enabling concurrent request handling.

### VI. LLM Access Uses Vertex AI Credentials, Never API Keys

All Gemini / LLM calls MUST go through Vertex AI using Google Cloud credentials. API keys (`GOOGLE_API_KEY`, `GEMINI_API_KEY`, Gemini Developer API, Vertex "express mode") are prohibited. No spec, plan, or task may introduce a key, a secret for a key, or a settings field for a key.

**How authentication works:**
- **Local**: Application Default Credentials from `gcloud auth application-default login`. No `.env` entry is needed for model access.
- **Cloud** (App Engine, Cloud Run, Agent Engine): the runtime service account. Nothing to configure in code.
- `GOOGLE_GENAI_USE_VERTEXAI=true` is set by `app_settings.py` (both deploy units) so every `genai.Client`, including the ones ADK creates for `Agent(model=...)`, resolves to Vertex AI. `GOOGLE_CLOUD_PROJECT` and `GOOGLE_CLOUD_LOCATION` are also set there from `PROJECT_ID`.
- If a stray `GOOGLE_API_KEY` is present in the environment, the genai client ignores it once the Vertex flag and project are set. Remove it anyway.

```python
# CORRECT - service code: use the pre-configured client
from gcp_services.clients.gcp_vertex import vertex

response = vertex.client.models.generate_content(
    model="gemini-2.5-flash-lite", contents=prompt
)

# CORRECT - ADK agents: name the model, auth is inherited from the environment
from google.adk import Agent

root_agent = Agent(name="MyAgent", model="gemini-2.5-flash-lite", instruction="...")

# WRONG - API key, Developer API, or a hand-built client
from google import genai

client = genai.Client(api_key=settings.google_api_key)  # Prohibited
client = genai.Client()  # Prohibited - bypasses the shared client
```

**Rationale**: Service-account auth is auditable, revocable through IAM, needs no secret rotation, and is the only mode that works identically for the FastAPI service, `adk web` locally, and Agent Engine. An API key is a second credential system with none of those properties.

## Deployment

### VIII. Deployment-Aware Web Service Changes

This project runs differently in local development vs production. All changes to routing, static assets, middleware, or server configuration MUST account for both environments.

**Local Development:**
- Server: `uvicorn app:app --reload` (single async process)
- Static files: Served by FastAPI via `StaticFiles` mount (`config_app.py`)
- SPA routing: Handled by FastAPI catch-all fallback route
- CORS: Disabled (same-origin on localhost)

**Production (App Engine):**
- Server: `gunicorn -w 1 -k uvicorn.workers.UvicornWorker app:app`
- Static files: Served by App Engine's static handler (`app.yaml` `handlers`)
- SPA routing: App Engine `static_files` directive catches `/(.*)`
- CORS: Enabled via FastAPI middleware (`config_app.py`)
- Warmup: `/_ah/warmup` endpoint handled by both App Engine and FastAPI
- Scaling: `app.yaml` controls instance class and scaling mode
- Secrets: App Engine default service account does NOT have
  Secret Manager access by default — MUST be granted explicitly
  (see Cloud Setup Checklist below)

**Hosting Model:**

There is one environment, selected by `PROJECT_ID` and `NAMESPACE` in
`.env`. Two deploy targets exist, and both run from a maintainer's
machine; there is no hosted CI/CD:

- `make deploy-app` deploys to App Engine using `app.yaml`.
- `make deploy-cr` deploys to Cloud Run, which serves the API and the
  SPA same-origin behind IAP.

**Firestore Database Naming:**

In the cloud, Firestore uses the `NAMESPACE` database
(`settings.firestore_db_name`); the emulator uses `(default)`. Do not
change this to make the names match.

**Cloud Setup Checklist:**

The App Engine default service account
(`<project-id>@appspot.gserviceaccount.com`) does NOT have
Secret Manager or token-signing access by default. Run the
setup script to grant all required roles:

```bash
bash gcp/bin/setup_iam.sh
```

The script reads `PROJECT_ID` from the root `.env` file and grants:

| Role | Purpose | Scope |
|------|---------|-------|
| `roles/secretmanager.secretAccessor` | Read secrets at startup (`load_secrets()`) | Per-secret (each secret in the `SECRETS` array) |
| `roles/iam.serviceAccountTokenCreator` | Sign GCS URLs for Storage operations | On the SA itself |

Vertex AI (Gemini) calls need `roles/aiplatform.user` on the runtime service account; `setup_iam.sh` grants it, along with Firestore and Storage access, because newer projects no longer give default service accounts the Editor role. On Cloud Run it also grants `roles/run.builder` to the Compute Engine default account, which builds source deploys. No API key is involved (see Service Pattern VI).

When adding a new secret: add it to both `SECRET_KEY_NAMES` in
`gcp_secrets.py` **and** the `SECRETS` array in
`gcp/bin/setup_iam.sh`, then re-run the script before deploying.

**Storage Bucket CORS:**

The GCS bucket requires a CORS policy for browser-based access
(e.g., signed URL downloads, image loads). The policy is defined
in `gcp/cors.json` and MUST be applied to the bucket:

```bash
gcloud storage buckets update gs://<BUCKET_NAME> \
  --cors-file=gcp/cors.json
```

Current policy allows `GET` from any origin with a 1-hour cache.
To restrict origins for production, replace `["*"]` with specific
domains in `gcp/cors.json` and re-apply.

**Dual-Environment Checklist** — apply when changing web service behavior:

| Change Type              | Local Impact                           | Production Impact                                             |
|--------------------------|----------------------------------------|---------------------------------------------------------------|
| New API route            | Add to `api/router.py`                 | Also verify `app.yaml` `/api.*` handler catches it            |
| New static asset path    | `StaticFiles` mount in `config_app.py` | Add `app.yaml` `handlers` entry for the path                  |
| SPA route changes        | Update fallback in `config_app.py`     | Update `app.yaml` catch-all `static_files` rule               |
| Middleware addition      | Add in `app.py` or `config_app.py`     | Verify it works under gunicorn (no uvicorn-specific features)  |
| Startup/lifespan events  | Test with `uvicorn`                    | Verify gunicorn UvicornWorker triggers them correctly          |
| Worker concurrency       | Single process locally                 | `gunicorn -w N` — ensure no in-process shared state           |
| Environment variables    | `.env` file                            | `app.yaml` `env_variables` section                            |
| New secret added         | Add to `.env` for local use            | Add to `gcp/bin/setup_iam.sh` SECRETS array, re-run script    |

**Key Files:**

| File                        | Role                                              |
|-----------------------------|---------------------------------------------------|
| `api_service/app.py`            | FastAPI app definition + local uvicorn entry       |
| `api_service/app.yaml`          | App Engine config: entrypoint, handlers, scaling   |
| `api_service/api/config_app.py` | CORS middleware + static file / SPA routing setup  |
| `api_service/api/router.py`     | API route definitions (prefix: `/api`)             |
| `gcp/bin/setup_iam.sh`      | Grants IAM roles to the server's service accounts  |
| `gcp/cors.json`             | GCS bucket CORS policy (apply via `gcloud`)        |

**Rationale**: App Engine's static file handling and gunicorn worker model behave differently from uvicorn's development server. Routing and asset changes that work locally can silently break in production if `app.yaml` handlers are not updated in tandem. This principle ensures both environments stay in sync.

## Quick Reference

### GCP Service Clients

| Import                                                             | Purpose                |
|--------------------------------------------------------------------|------------------------|
| `from gcp_services.clients.gcp_services import db`                | Firestore async client |
| `from gcp_services.clients.gcp_services import auth_client`       | Firebase Auth          |
| `from gcp_services.clients.gcp_services import bucket`            | Cloud Storage          |
| `from gcp_services.clients.fb_auth import firebase_auth_required` | Auth decorator         |

### Configuration & Environment

| Import                                                    | Purpose               |
|-----------------------------------------------------------|-----------------------|
| `from app_settings import settings`                       | All app configuration |
| `from gcp_services import IS_GCP, IS_GAE, IS_CLOUD_RUN` | Environment flags     |
| `from gcp_services.gcp_secrets import load_secrets`      | Secret Manager loader |
| `from gcp_services.gcp_logging import setup_logging`     | Cloud Logging setup   |

### API Routing

| Import                              | Purpose                          |
|-------------------------------------|----------------------------------|
| `from api.router import api_router` | Main API router (prefix: `/api`) |
| `from fastapi import APIRouter`     | Create sub-routers               |

### Vertex AI / Agents

| Import                                                      | Purpose                  |
|-------------------------------------------------------------|--------------------------|
| `from gcp_services.clients.gcp_vertex import vertex`       | Gemini client on Vertex AI (`vertex.client`), ADC auth |
| `from google.adk import Agent`                              | ADK agent definition     |

### Key Abstractions

| Location                               | Abstraction        | Use When                                     |
|----------------------------------------|--------------------|----------------------------------------------|
| `gcp_services/clients/gcp_services.py` | Firebase clients   | Any Firestore, Auth, or Storage operation    |
| `gcp_services/clients/fb_auth.py`      | Auth decorator     | Protecting any endpoint                      |
| `gcp_services/clients/fb_config.py`    | Firebase app setup | Never directly - used internally             |
| `gcp_services/gcp_secrets.py`          | Secret loading     | Loader only; `SECRET_KEY_NAMES` lives in `app_settings.py` |
| `gcp_services/clients/gcp_vertex.py`   | Gemini/Vertex client | Any LLM call from service code (never an API key) |
| `gcp_services/gcp_logging.py`          | Structured logging | Already auto-configured at startup           |
| `app_settings.py`                      | Settings class     | Adding new config fields                     |
| `api/router.py`                        | API routes         | Adding new endpoints                         |
| `api/config_app.py`                    | Middleware setup   | Frontend routing changes                     |

## Governance

This constitution documents patterns that MUST be followed to maintain codebase consistency.

**Precedence**: Spec before plan, plan before code. If a spec conflicts
with this constitution, the spec is wrong — fix the spec, not the
code, unless the amendment process below is used to change the
constitution itself.

**Spec Freshness**: Every spec records the commit it was checked
against. If the code has moved since, re-check the spec against
current state before building from it.

**Living Docs vs. Specs**: Guides and architecture docs describe the
current code and change in the same commit as the code they describe.
A spec is a record of a decision: once shipped, only its status and
checkboxes change — its body is history, not a living doc.

**Amendment Process:**
1. Propose changes via PR modifying this file
2. Document rationale for pattern changes
3. Increment version per semantic versioning

**Versioning:**
- MAJOR: Pattern removal or incompatible change
- MINOR: New pattern or utility added
- PATCH: Clarifications or examples

**Version**: 3.11.0 | **Ratified**: 2026-03-12 | **Last Amended**: 2026-10-14
