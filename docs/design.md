# Ops Copilot — v1 design

Vocabulary comes from [CONTEXT.md](../CONTEXT.md); decisions with trade-offs are in [adr/](adr/).

## v1 scope

Triage · Briefs · Decision Requests · Person memory · LangSmith · simple Daily Report.
Later: reply drafts, Urgent Alerts, full Daily Report, Slack adapter (also mobile), Hub Admin connection, personal Mailboxes.

## Harness shape (ADR 0005)

- **Email graph** (LangGraph StateGraph), one thread per Conversation:
  `triage → recall Person → Brief if high value → Decision Request (interrupt) → record Decision`
- **Brief researcher** (Deep Agent, configured explicitly: exact `deepagents` pin, model instances, call caps in
  every subagent, file tools limited to ls/read_file/write_file, general-purpose subagent off). Subagents: `company-researcher`, `founder-researcher`, `criteria-checker`.
  Writes `brief.md` + `sources.json` to its virtual filesystem. A returning Person's previous Brief is
  seeded as `previous_brief.md` and the new Brief states what changed.
- **Operator Copilot** (`create_agent` chat, ADR 0005 amendment). Tools are the modules below. Tools that would
  make a Decision call `decisions.ask()`, so they only ever produce a Decision Request; research goes through
  `write_brief()`.
- **Daily Report graph** (LangGraph): gather → group by Category → render HTML → deliver.

## Modules

| Module | Interface | Hides |
|---|---|---|
| `triage` | `triage(email) -> Triage` (one Category, Asks, language, high_value) | prompt from LangSmith Prompt Hub (local copy for tests), Mailbox hint, structured output |
| `people` | `recall(address)`, `record(event)`, `similar(text, kind)` | Postgres (truth) + Pinecone (similarity) — ADR 0004. Writes Postgres first; failed indexing is flagged and fixed by `reindex`. `similar()` returns current records from Postgres. |
| `briefs` | `write_brief(subject) -> Brief` | the Brief researcher Deep Agent, Tavily, previous-Brief handling |
| `decisions` | `ask(DecisionRequest) -> Decision` | LangGraph `interrupt()`; surfaces: our pitch frontend via `useStream` (now, ADR 0006), Slack (later), test — ADR 0001 |
| `report` | `build_report(since) -> Report`, `deliver(report)` | HTML rendering; delivery adapters: dry-run (default), SMTP |

Dependencies: models and Tavily are passed in and faked in tests.

## Models (current decision)

All models go through Command Code with one key (`COMMANDCODE_API_KEY`), using plain LangChain packages.

| Role | Development | Release gate + pitch demo |
|---|---|---|
| Main (Briefs, Operator Copilot) | `inclusionai/ling-3.0-flash-sante:free` | `claude-sonnet-5-5` |
| Triage | `inclusionai/ling-3.0-flash-sante:free` | `claude-haiku-4-5-20251001` |
| Eval judge | `gpt-6-sol` | `gpt-6-sol` |

- Ling and GPT-6 Sol: `langchain-openai`, base URL `https://api.commandcode.ai/provider/v1` (chat completions only).
- Claude: `langchain-anthropic`, base URL `https://api.commandcode.ai/provider` (the SDK appends `/v1/messages`).
- The judge is never the model being judged.
- Ling's free tier allows 100 requests/day and its tool calling, structured output and Swedish support are
  undocumented: verify them in the first triage test before relying on them.

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

## Frontend (ADR 0006)

Pitch-only, fully live, on the presenter's laptop. React/Next.js + `useStream` (`@langchain/langgraph-sdk/react`)
against `langgraph dev`. Three screens:

1. **Inbox**: new emails and live step-by-step progress (LangGraph streaming). Emails arrive from a presenter
   button ("deliver next email") or a free-text box anyone in the room can fill in.
2. **Decision**: the Decision Request with its Brief and the Person's history; the clicker types their name, and the
   Decision is recorded under it.
3. **People**: a Person's timeline; Applicant/Member derived, other Roles shown as suggested until confirmed.

Before the meeting a seed loads fictional history (a small cast incl. Elin's March Application and its Revisit by a
fictional Hub Operator) through `people.record()`. Pitch runs use the release profile (Claude). Neutral brand,
theme in one config file. Operator Copilot chat is not in the pitch frontend.

## Build order (vertical slices)

1. Finish `people` → thin email graph (triage → recall → record) on `langgraph dev` → Inbox screen with live progress.
2. `decisions` (interrupt + resume with the Hub Operator's name) → Decision screen.
3. Briefs (Deep Agent) → on the Decision screen; subagents visible in live progress.
4. People screen (incl. suggested Roles), then the Daily Report.

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
- Command Code sits between the Copilot and the model providers, so it processes applicant text too: check its
  data-retention terms (it offers a zero-data-retention option) or switch to Anthropic directly for the pilot.
