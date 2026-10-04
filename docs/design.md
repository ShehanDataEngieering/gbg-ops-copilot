# Ops Copilot — v1 design

Vocabulary comes from [CONTEXT.md](../CONTEXT.md); decisions with trade-offs are in [adr/](adr/).

## v1 scope

Triage · Briefs · Decision Requests · Person memory · LangSmith · simple Daily Report.
Later: reply drafts, Urgent Alerts, full Daily Report, Slack adapter (also mobile), Hub Admin connection, personal Mailboxes.

## Harness shape (ADR 0005)

- **Email graph** (LangGraph StateGraph), one thread per Conversation:
  `triage → recall Person → Brief if high value → Decision Request (interrupt) → record Decision`
- **Brief researcher** (Deep Agent). Subagents: `company-researcher`, `founder-researcher`, `criteria-checker`.
  Writes `brief.md` + `sources.json` to its virtual filesystem. A returning Person's previous Brief is
  seeded as `previous_brief.md` and the new Brief states what changed.
- **Operator Copilot** (Deep Agent chat). Tools are the modules below. Tools that would make a Decision
  are wrapped with `interrupt_on`, so they only ever produce a Decision Request.
- **Daily Report graph** (LangGraph): gather → group by Category → render HTML → deliver.

## Modules

| Module | Interface | Hides |
|---|---|---|
| `triage` | `triage(email) -> Triage` (one Category, Asks, language, high_value) | prompt from LangSmith Prompt Hub (local copy for tests), Mailbox hint, structured output |
| `people` | `recall(address)`, `record(event)`, `similar(text, kind)` | Postgres (truth) + Pinecone (similarity) — ADR 0004. Writes Postgres first; failed indexing is flagged and fixed by `reindex`. `similar()` returns current records from Postgres. |
| `briefs` | `write_brief(subject) -> Brief` | the Brief researcher Deep Agent, Tavily, previous-Brief handling |
| `decisions` | `ask(DecisionRequest) -> Decision` | LangGraph `interrupt()`; surface adapters: Agent Inbox (now), Slack (later), test — ADR 0001 |
| `report` | `build_report(since) -> Report`, `deliver(report)` | HTML rendering; delivery adapters: dry-run (default), SMTP |

Dependencies: Claude models and Tavily are passed in and faked in tests. Postgres/Pinecone sit behind
`people` only; tests use an in-memory `people`.

## Storage (ADR 0004)

- **Postgres**: `PostgresStore` (Persons, Roles, Applications, Briefs, Decisions, Corrections) and
  `PostgresSaver` (paused runs). Identity is always an exact lookup by email address.
- **Pinecone**: embeddings only, via Pinecone's hosted multilingual model (exact model confirmed at index setup).
  Every vector carries its Postgres id; the index can be rebuilt from Postgres.

## Triggers

LangGraph Server crons: check Mailboxes every 5 min (one run per new Conversation); Daily Report at 08:00 on
weekdays. A `demo replay` command feeds the fictional dataset with realistic timestamps.
To verify: crons on the local `langgraph dev` server; fallback is a small local scheduler calling the same API.

## Learning loop

Triage prompt + Category list are versioned in LangSmith Prompt Hub. Every Correction is stored in Postgres and
added to a LangSmith dataset; a new prompt version is promoted only after it passes the evals on that dataset.

## Evals and release gate

- Yes/no (pytest, offline): Elin's later email links to her earlier Application; no Brief contains a score;
  every Decision has a Hub Operator; every Brief claim has a source; "Not sure yet" about Gothenburg is shown as unknown.
- Scored (LangSmith): Category accuracy ≥ 90%, Ask recall ≥ 85%, Brief groundedness ≥ 95%.

## Where it runs

Develop with `langgraph dev` + Postgres in Docker. A `docker compose` (LangGraph server + Postgres) is kept
working from week one. LangSmith Deployment vs a self-hosted EU server is decided with AI Gothenburg at pilot time.

## CI/CD (GitHub Actions)

CI/CD delivers the Copilot; a server runs it (Decision Requests wait hours; CI jobs are short-lived).

| When | Stage |
|---|---|
| Every PR | yes/no checks, offline |
| Merge to main | LangSmith evals + release gate (blocks on any threshold) |
| Gate passed | `langgraph build` → image → GitHub container registry |
| Gate passed | deploy (off until a server exists) |
| Nightly | Category accuracy on the growing Correction dataset |
| New prompt version | same evals before promotion |

## Open for the pilot

- Where applicant data may live (LangSmith Deployment vs EU server).
- How long Briefs about declined Applicants are kept (GDPR retention).
