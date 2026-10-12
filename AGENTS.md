# AI Gothenburg Ops Copilot

## Agent skills

### Issue tracker

Issues live in GitHub Issues for ShehanDataEngieering/gbg-ops-copilot, managed with the `gh` CLI. See `docs/agents/issue-tracker.md`.

### Triage labels

Default triage roles, with `needs-info` → `question` and `ready-for-human` → `help wanted`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context: `CONTEXT.md` and `docs/adr/` at the repo root. See `docs/agents/domain.md`.

## How we build

- `docs/design.md`, `CONTEXT.md` and `docs/adr/` are the background docs. Each feature gets a spec issue (`to-spec`), is broken into tickets (`to-tickets`) and built one ticket at a time with `implement`.
- All code is built test-first with the `tdd` skill: agree the seams first, then one red → green slice at a time. The failing test is committed before the code that makes it pass.
- Offline tests live in `evals/deterministic/`; run them with `uv run pytest`. Models and Tavily are passed in and faked in tests.
