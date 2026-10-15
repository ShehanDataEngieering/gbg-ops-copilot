# AI Gothenburg Ops Copilot

An assistant for the Hub Operators who run the AI Gothenburg founder hub. It sorts the hub's inbox, remembers every Person the hub deals with, and prepares Decisions — while a named Hub Operator makes every Decision.

Built on LangChain, LangGraph, Deep Agents and LangSmith. Vocabulary (Person, Application, Category, Ask, Decision Request…) is defined in [`CONTEXT.md`](CONTEXT.md); please use those words.

## Status

| Built | Planned (see [`docs/design.md`](docs/design.md)) |
|---|---|
| Triage, Person memory, the email graph (triage → recall → record), demo seed/reset, live Inbox screen, CLI | Decision Requests (interrupt/resume), Briefs (Deep Agent), Operator Copilot chat, Daily Report, Postgres + Pinecone, CI |

## Architecture

```
        Mailbox email                          Pitch frontend (Next.js, web/)
              │                                  useStream ◄── live progress
              ▼                                      │
┌──────────────────── LangGraph server (langgraph dev) ───────────────────┐
│  email graph   START → triage → recall → record → END                    │
│                         │         │        │                             │
│                         ▼         ▼        ▼                             │
│                     triage.py   people.py (Person memory)                │
│                         │              │                                 │
│                    chat model      LangGraph store                       │
│                   (models.py)   (InMemory now → Postgres)                │
│                                                                          │
│  demo_seed / demo_reset graphs  — load or clear the fictional cast       │
└──────────────────────────────────────────────────────────────────────────┘
```

### The main ideas

1. **A fixed graph runs every email; agents only do open-ended work** ([ADR 0005](docs/adr/0005-graph-core-agents-for-open-ended-work.md)). Each email goes through a LangGraph `StateGraph` that cannot skip a step. That fixed path is what makes the evals meaningful. A Deep Agent is used only where the steps can't be drawn in advance: researching a Brief. The planned Operator Copilot chat is a plain `create_agent`.
2. **Deep modules at clean seams.** The code follows Matt Pocock's codebase-design approach; see [Code architecture](#code-architecture-deep-modules-matt-pococks-codebase-design) below.
3. **A human makes every Decision.** Decision Requests pause the graph with a neutral payload, so the screen that shows them is only an adapter ([ADR 0001](docs/adr/0001-decision-requests-are-surface-agnostic.md)). Every Decision records the Hub Operator who made it.
4. **Briefs show evidence, never scores** ([ADR 0003](docs/adr/0003-briefs-show-evidence-never-scores.md)).
5. **Postgres is the source of truth; Pinecone only finds similar records** ([ADR 0004](docs/adr/0004-postgres-for-records-pinecone-for-similarity.md)). A Person is always found by exact email address.
6. **The Copilot feeds Hub Admin and never replaces it** ([ADR 0002](docs/adr/0002-feed-hub-admin-never-replace-it.md)).

## Code architecture: deep modules (Matt Pocock's codebase-design)

The code is designed with the vocabulary of Matt Pocock's `codebase-design` skill, which builds on John Ousterhout's *A Philosophy of Software Design* and Michael Feathers' seams. We use these words exactly:

| Term | Meaning |
|---|---|
| **Module** | anything with an interface and an implementation: a function, a class, a package |
| **Interface** | everything a caller must know: the signature, plus invariants, error modes and required configuration |
| **Depth** | how much behaviour a caller or test gets per unit of interface it has to learn. **Deep** = small interface, a lot behind it; **shallow** = the interface is about as complex as the code |
| **Seam** | the place where behaviour can be changed without editing that place; the module's interface sits at a seam |
| **Adapter** | a concrete thing that fills a seam (a real model, a fake model, `InMemoryStore`, `PostgresStore`) |
| **Leverage / Locality** | what depth buys: callers get more per call, and changes and bugs stay in one place |

### Our modules

| Module | Interface (small) | Implementation (hidden behind it) |
|---|---|---|
| `triage` | `triage(email, model=…) -> Triage` | Noise rules (RFC 3834/2369 headers), the prompt and Category list, structured output via tool calling, one retry, the Unsorted fallback, LangSmith tracing |
| `people` | `People(store).record(event)`, `.recall(address) -> History` | storage layout, case-insensitive exact identity, Roles derived from facts, a resubmitted Application kept once, Decisions on unknown Applications rejected |
| `models` | `chat_model(role)` | which model each role uses, dev/release profiles, Command Code base URLs, the judge never being the judged model |
| `graph` | `build_email_graph(store=…)` | node wiring, JSON state for streaming, progress events |
| `demo` | `seed_graph`, `reset_graph` | the fictional cast, recorded through the same `people.record()` path as live events |

`people` is the clearest example. Callers record **events** (`ApplicationReceived`, `DecisionMade`, `EmailReceived`) and ask for a **History**. They never see how a Person is stored, so moving from the LangGraph store to Postgres + Pinecone (ADR 0004) changes only `people`.

### Seams and adapters

A seam counts only when something actually varies across it: *one adapter is a hypothetical seam, two adapters make a real one.* We have two real seams:

| Seam | Test adapter | Production adapter | Dependency category |
|---|---|---|---|
| chat model (passed into `triage()` and through the graph's `Context`) | a fake model returning fixed answers | `models.chat_model(...)` via Command Code | true external, so it is injected and faked |
| LangGraph store (from the runtime) | `InMemoryStore` | the server's store, later `PostgresStore` | local-substitutable, so tests run against a real in-memory stand-in |

Tavily (web search for Briefs) will be the third seam, injected the same way.

### Rules we follow

- **Accept dependencies, don't create them.** No module builds its own model or store. `graph._model()` falls back to `chat_model("triage")` only when no model is passed in.
- **Return results.** `triage()` returns a `Triage` value; `recall()` returns a `History` value.
- **The interface is the test surface.** Tests call `triage()`, `People.record/recall` and the compiled graph, never private helpers. If a test needs to reach past the interface, the module is the wrong shape.
- **The deletion test.** If deleting a module would push its complexity back into every caller, it is earning its keep; if the complexity would just disappear, it was a pass-through and should go.
- **Vertical slices.** Features are built end to end in thin slices (graph → server → screen), not layer by layer. Tests work the same way: one test, then just enough code to pass it.
- **One language.** Module, test and variable names use the `CONTEXT.md` terms (Person, Application, Ask, Hub Operator), and design decisions with trade-offs go into an ADR.

### Email graph state

`EmailState` (in `src/copilot/graph.py`) is plain JSON so the server can stream it: `email`, `conversation_id`, `received_at`, `triage` (category, asks, wants_brief) and `person` (who the sender was before this email). Each node also sends `{step, message}` lines on `stream_mode="custom"`; the Inbox screen shows them as live progress.

### Models

Every model goes through Command Code with one key (`COMMANDCODE_API_KEY`). `COPILOT_PROFILE=dev` (the default) uses the free Ling model; `release` uses Claude (Sonnet for main work, Haiku for triage). The eval judge is always a different model (GPT-6 Sol), so it never grades its own work. Categories live in `src/copilot/categories.toml`.

## Repository layout

```
src/copilot/        Python package: triage, people, graph, demo, models, cli
evals/deterministic Offline tests (pytest): no network, fake models
web/                Next.js pitch frontend (Inbox screen, useStream)
docs/design.md      v1 design — what is planned and why
docs/adr/           Architecture Decision Records
docs/agents/        How the coding-agent skills use this repo
CONTEXT.md          Domain glossary
langgraph.json      Graphs the server serves: email, demo_seed, demo_reset
scripts/setup-wizard.sh  Walks you through API keys and GitHub secrets
```

## Running it

```bash
uv sync
bash scripts/setup-wizard.sh          # writes .env (Command Code, LangSmith, Pinecone, Tavily)

uv run pytest                         # offline tests
uv run copilot triage --list          # sample emails
uv run copilot triage --sample 2      # triage one with a real model

uv run langgraph dev                  # LangGraph server on :2024
uv run copilot demo prepare           # reset + seed the fictional cast
cd web && npm install && npm run dev  # Inbox screen on :3000
```

The frontend is for the pitch only. It has no login and must not be exposed publicly ([ADR 0006](docs/adr/0006-pitch-frontend-live-on-laptop.md)).

## How we build: coding skills

The code is written together with coding agents (Claude Code) using [Matt Pocock's skills](https://github.com/mattpocock/skills). Agent rules are in [`AGENTS.md`](AGENTS.md); `CLAUDE.md` only imports it.

**Workflow per feature**

1. **Spec**: write a spec issue in GitHub Issues (`to-spec`), grounded in `docs/design.md`, `CONTEXT.md` and the ADRs.
2. **Tickets**: break it into thin vertical-slice tickets (`to-tickets`).
3. **Implement**: build one ticket at a time (`implement`).
4. **Test-first** (`tdd`): agree on the seams first, then work one red → green slice at a time. The failing test is committed before the code that makes it pass.

**Other skills we use**

| Skill | Used for |
|---|---|
| `grilling` | stress-testing a plan or design, one question at a time |
| `domain-modeling` | keeping `CONTEXT.md` and the ADRs current |
| `codebase-design` | designing deep modules and where the seams go |
| `diagnosing-bugs` | a diagnose loop for hard bugs |
| `code-review` | reviewing a branch against the repo's standards and the ticket |
| `prototype` / `research` | throwaway prototypes; research written to `docs/research/` |
| `wizard` | generated `scripts/setup-wizard.sh` |

Issues use the default triage labels, except that `needs-info` maps to `question` and `ready-for-human` to `help wanted` ([`docs/agents/triage-labels.md`](docs/agents/triage-labels.md)).

**Testing rules**

- Offline tests live in `evals/deterministic/`. They never call a model or LangSmith: models and Tavily are passed in and faked.
- The tests use real LangGraph stores (`InMemoryStore`), not mocks, so they exercise real behavior.
- Scored evals (Category accuracy ≥ 90%, Ask recall ≥ 85%, Brief groundedness ≥ 95%) are planned to run in LangSmith as the release gate. Every Correction a Hub Operator makes becomes a test case.

**Before code lands: no-mistakes**

We are adopting Kun Chen's [no-mistakes](https://github.com/kunchenguid/no-mistakes) as the gate every change goes through before it reaches GitHub. It is a local Git proxy: instead of pushing straight to `origin`, you push to the `no-mistakes` remote. That push starts a pipeline that runs on the committed branch:

```
intent → rebase → review → test → document → lint → push → PR → CI
```

- **review**: a coding agent (`agent: claude`) reviews the diff against the stated intent.
- **test**: runs `uv run pytest` (configured in [`.no-mistakes.yaml`](.no-mistakes.yaml)).
- **push → PR**: only a branch that passes is pushed to `origin` and opened as a pull request.
- **CI**: switched off for now (`no_ci: true`) until GitHub Actions runs the offline checks. `no-mistakes ci-workflow` can generate that workflow from the same config.

From an agent session, run `/no-mistakes` (validate committed work) or `/no-mistakes <task>` (do the task, then validate it). Its test-quality rule matches ours: tests run the real interface and assert behaviour, never grep the source.

Commits are small and use [Conventional Commits](https://www.conventionalcommits.org/) (`feat(graph): …`, `fix(people): …`).
