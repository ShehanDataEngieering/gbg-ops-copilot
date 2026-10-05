# Deep Agents vs our own harness, for the Brief researcher and the Operator Copilot

Researched 2026-10-05 against `deepagents==0.7.20` (installed), `langchain==1.4.3`, `langgraph==1.2.12`.
Path shorthand: `SP/` = `.venv/lib/python3.12/site-packages/`. "Probe" = a throwaway script run in the project
venv with a scripted fake chat model (method in [Probe method](#probe-method)). Token counts are **cl100k
approximations**, not Claude or Ling tokens.

## TL;DR

1. **Brief researcher: keep Deep Agents**, but configure it explicitly: pass model *instances*, add `TodoListMiddleware` yourself (0.7.0 removed it), restrict file tools, and cap model calls. It gives us isolated subagents, a virtual filesystem that subagents write back into, and summarization, which would take a few hundred lines to rebuild.
2. **Operator Copilot: use `create_agent`, not `create_deep_agent`**. It needs neither subagents nor a filesystem. Decision tools should call our own `decisions.ask()` (`interrupt()` with the neutral Decision Request payload), not `interrupt_on`.
3. **Biggest risk:** the design's "`interrupt_on` → Agent Inbox" path. Agent Inbox is archived. From reading its source, it looks incompatible with the HITL middleware's payload and resume format. The payload is also tool-shaped and does not record which Hub Operator decided (ADR 0001, CONTEXT "Decision").
4. **Quota:** measured, 5 model calls for 1 subagent doing 1 search. Estimated 15–25 calls for a real 3-subagent Brief, so roughly 4–6 Briefs/day on Ling's 100 req/day. The default `recursion_limit` is 9,999 with no call cap.
5. **Churn:** 96 `deepagents` releases. 0.7.0 (2026-07-29) had about 12 breaking changes, and 0.7.21 is already out. Pin exactly and wrap it behind `briefs.write_brief()`.

## Context

- **ADR 0005**: a fixed StateGraph runs every email. Agents are used only where steps can't be drawn in advance: the Brief researcher and the Operator Copilot.
- **Brief researcher** (`docs/design.md` "Harness shape"): it plans, then delegates to `company-researcher`, `founder-researcher` and `criteria-checker`. It writes `brief.md` and `sources.json` to a virtual FS, gets `previous_brief.md` for returning Persons, and uses Tavily search. It must never output a score (ADR 0003), and every claim needs a source.
- **Operator Copilot**: a chat agent whose tools are our modules (triage, people, briefs). Decision-making tools must only produce a Decision Request (ADR 0001), surfaced in Agent Inbox for the demo and Slack later.
- **Runtime**: `langgraph dev` / LangGraph Server, Postgres checkpointer, LangSmith tracing.
- **Models** (`docs/design.md` "Models"): everything goes through Command Code.
  - Dev: `inclusionai/ling-3.0-flash-sante:free` over OpenAI-compatible *chat completions*. 100 req/day; tool calling and structured output are undocumented.
  - Release/demo: `claude-sonnet-5-5` and `claude-haiku-4-5-20251001` via `ChatAnthropic(base_url=...)`.

## What Deep Agents provides (0.7.20)

| Feature | What it actually does | Source |
|---|---|---|
| Entry point | `create_deep_agent(...)` assembles middleware and then calls LangChain `create_agent`. It is not a separate runtime. | `SP/deepagents/graph.py:272`, `:961-973` |
| Default main stack | `FilesystemMiddleware` → `SubAgentMiddleware` (if any subagents) → summarization → `PatchToolCallsMiddleware` → `AnthropicPromptCachingMiddleware` (always) → HITL (only if `interrupt_on`) → `UnsupportedContentMiddleware` | `graph.py:864-924` |
| Auto `general-purpose` subagent | Added unless you define one with that name or a profile disables it | `graph.py:797-861`, `middleware/subagents.py:493-497` |
| Planning (`write_todos`) | **No longer default.** Since 0.7.0 you pass `middleware=[TodoListMiddleware()]` | [0.7.0 release](https://github.com/langchain-ai/deepagents/releases/tag/deepagents%3D%3D0.7.0); `SP/langchain/agents/middleware/todo.py:174` |
| Default system prompt | **Empty.** The authored base prompt was removed in 0.7.0 (`BASE_AGENT_PROMPT` deprecated). A profile suffix is added only for matched models. | `graph.py:80-141`, `:641-650`; 0.7.0 release |
| Virtual filesystem | Tools `ls, read_file, write_file, edit_file, delete, glob, grep` (+ `execute` on sandbox backends). Default backend is `StateBackend` (files live in graph state, so they are checkpointed). | `graph.py:296-302`, `:639`; probe |
| Tool allowlist | `FilesystemMiddleware(tools=[...])`; the list must include `read_file` | `middleware/filesystem.py:1721`; 0.7.0 release |
| Backends | State, Store, Filesystem, LocalShell, Sandbox, Composite, LangSmith, ContextHub | `SP/deepagents/backends/` |
| Subagents (`task` tool) | Isolated by default: the subagent sees only the `description` string and returns its final text. The `files` state *does* flow back to the parent; `messages`/`todos` do not. `mode="fork"` is experimental. | `subagents.py:70-81`, `:396-402`, `:727-760`, `:463-475` |
| Subagent defaults | Each declarative subagent gets FS + summarization + patch + prompt caching, and inherits the parent's `tools` and `interrupt_on` unless it overrides them | `graph.py:691-790` |
| Summarization | Triggers at 85% of `model.profile["max_input_tokens"]`. **With no profile, it triggers at a fixed 170k tokens and keeps 6 messages.** Evicted history is offloaded to the backend, and it falls back on `ContextOverflowError`. | `middleware/summarization.py:262-299`, `:1772-1813` |
| HITL | `interrupt_on={tool: True \| InterruptOnConfig}` → LangChain `HumanInTheLoopMiddleware`. Needs a checkpointer. | `graph.py:918-923`; [docs](https://docs.langchain.com/oss/python/deepagents/human-in-the-loop) |
| Skills / memory | `SkillsMiddleware` / `MemoryMiddleware`, only when `skills=` / `memory=` are passed | `graph.py:865-917`; `middleware/skills.py:770`, `memory.py:180` |
| Permissions | `FilesystemPermission` rules; can generate interrupts | `filesystem.py:354`; `graph.py:918-921` |
| Async subagents | Background runs on remote Agent Protocol / LangGraph servers | `middleware/async_subagents.py:1-9` |
| Harness profiles | Per-model prompt suffix and middleware. Built-in profiles cover `claude-sonnet-4-6`, `claude-haiku-4-5`, `claude-opus-4-7`, Codex and Nemotron. | `profiles/_builtin_profiles.py:149-156` |
| Run config | `recursion_limit: 9_999`, LangSmith metadata `ls_integration: deepagents` | `graph.py:974-982` |

**Measured default footprint (probe, `create_deep_agent(model=fake, tools=[])`):**

| Configuration | System prompt | Tool schemas per call |
|---|---|---|
| No custom tools | 0 tokens | about 2,500 tokens (8 tools) |
| `+ TodoListMiddleware` | about 290 tokens | about 3,540 tokens |
| `create_agent` + `FilesystemMiddleware(tools=["ls","read_file","write_file"])` + `SubAgentMiddleware` | (our prompt only) | about 1,120 tokens |

This overhead is resent on every call.

## Strengths for our uses

**Brief researcher (good fit)**
- **Context isolation for free.** Each researcher subagent sees only its task string and returns one report, so raw Tavily output never reaches the main context (`subagents.py:463-475`, `:727-760`). This is the main reason to use it.
- **The filesystem matches our artifact model.** We seed `previous_brief.md` through the input `files` key. Subagents can write to the shared `StateBackend`, and the files come back to the parent. The probe ended with `['/brief.md', '/previous_brief.md']` in state. Because files live in graph state, they are checkpointed in Postgres and visible in LangSmith and Studio.
- **Parallel fan-out.** The `task` description tells the model to launch independent subagents in one message (`subagents.py:469`), so the three researchers can run concurrently.
- **Summarization with history offload** comes free, which matters if a founder has a long web footprint.
- **The default prompt is now small** (0 tokens authored), so our ADR 0003 "no score, cite everything" instructions are not fighting a long generic prompt.
- **Testable with fakes.** `create_deep_agent` accepted a `BaseChatModel` subclass whose `bind_tools` returns a copy. A full task→search→write_file→answer run worked offline (probe).
- It is plain LangGraph, so it is a `CompiledStateGraph` (probe), runs on LangGraph Server, and traces to LangSmith with no extra glue.

**Operator Copilot (weak fit)**
- `interrupt_on` gives approve/edit/reject/respond per tool in one line. It is just LangChain's `HumanInTheLoopMiddleware`, though (`graph.py:13`, `:923`), so `create_agent` gives the same thing.
- Nothing else in the Deep Agents bundle (FS, subagents, offload) is needed for a chat over our module tools.

## Weaknesses and risks

### 1. HITL → Agent Inbox looks broken, and it conflicts with ADR 0001 (highest risk)

**Evidence (source reading, not run end-to-end):**
- Agent Inbox is **archived** (`gh repo view langchain-ai/agent-inbox` → `isArchived: true`; last push 2026-09-18). I found no successor named in a primary source (**unverified**).
- **Payload mismatch.** Inbox normalizes HITL payloads by reading `action_requests[0].arguments` (`agent-inbox/src/components/agent-inbox/contexts/utils.ts:24-37`). The middleware emits `args` (`SP/langchain/agents/middleware/human_in_the_loop.py:52-58`; probe payload `{'action_requests': [{'name':..., 'args': {...}, 'description':...}], 'review_configs': [...]}`). The result is empty args in the UI. The `description` string still embeds the args, so the display degrades rather than going blank. Only the first action request is shown (`utils.ts:24`).
- **Resume mismatch.** Inbox resumes with a list `[{type: "accept"|"edit"|"response"|"ignore", args}]` (`types.ts:39-42`, `hooks/use-interrupted-actions.tsx:207`, `contexts/ThreadContext.tsx:444-456`). The middleware does `interrupt(hitl_request)["decisions"]` and expects `{"decisions": [{"type": "approve"|...}]}` (`human_in_the_loop.py:144-147`, `:481`). I found no reverse mapping in the Inbox `src`, so Accept/Edit would most likely raise on resume.
- **Shape mismatch with ADR 0001.** The payload is a tool call ("Tool execution requires approval\n\nTool: decide_application\nArgs: ..."), not our neutral Decision Request (what it proposes, supporting material, allowed choices). The resume `Decision` has no "who" field (`human_in_the_loop.py:144-147`), but CONTEXT says every Decision records its Hub Operator.

**Opinion:** this is a design conflict with `docs/design.md` ("wrapped with `interrupt_on`"), not just an integration bug. Moving the Copilot to `create_agent` (see Recommendation) also means amending **ADR 0005**, which names the Operator Copilot as a Deep Agent use, and the "Harness shape" section of `docs/design.md`. Fix: decision-making Copilot tools should call `decisions.ask(DecisionRequest)`, which calls `interrupt()` with the same neutral payload the email graph uses. Then there is one Decision Request format, one adapter per surface, and the operator identity comes from the resume value or server auth.

### 2. Call count vs 100 req/day (Ling free tier)

- **Measured** (probe): 1 main agent → 1 subagent → 1 search → write `brief.md` → answer = **5 model calls**. The main agent made 3 calls (dispatch, write, final) and the subagent made 2 (search, report).
- **Estimate** for a real Brief: main = plan (`write_todos`) 1 + dispatch 3 subagents in parallel 1 + read `previous_brief.md` 1 + write `brief.md`/`sources.json` 1–2 + update todos about 2 + final 1, so **about 7–8**. Each subagent = about 3 searches + 1 report, **about 4**, so 3 subagents ≈ 12. **Total ≈ 19–20**, call it 15–25. Weak models re-plan and retry more, so expect the high end. That allows **about 4–6 Briefs/day in dev** before evals or triage spend anything.
- **No guard by default:** `recursion_limit` is 9,999 (`graph.py:976`) and there is no call limit. A looping weak model can burn the day's quota in one run. LangChain exports `ModelCallLimitMiddleware` (`SP/langchain/agents/middleware/model_call_limit.py:94`) and `ToolCallLimitMiddleware`; add them. **The counters are per graph.** They are `PrivateStateAttr` fields (`model_call_limit.py:33-34`), kept out of subagent inputs and outputs (`subagents.py:396-402`, 0.7.0 fix). Main-agent `middleware=` also does not propagate to declarative subagents, which get only `spec["middleware"]` unless forked (`graph.py:728-737`). So a limit on the main agent counts only its own ~7–8 calls, not the ~12 subagent calls. **Put a limit in every subagent spec as well.**
- **Trade-off of the alternative in 1.** `HumanInTheLoopMiddleware` interrupts after the model call and before any tool runs. An `interrupt()` *inside* a tool (`decisions.ask()`) re-runs the tools node on resume, so sibling tool calls from the same model turn may run twice (**unverified for the 1.2.12 ToolNode**). Make decision tools idempotent, or turn off parallel tool calls for the Copilot.
- Summarization calls also count, but with Ling it effectively never triggers (see 4).

### 3. Model coupling (mild, but there are traps)

- **Anthropic is a hard import**, not a hard requirement. `graph.py:22` imports `ChatAnthropic`. `model=None` falls back to `claude-sonnet-4-6` (`graph.py:144-152`), which is deprecated and will be removed in 1.0 (`:155-167`). `AnthropicPromptCachingMiddleware` is appended unconditionally with `unsupported_model_behavior="ignore"` (`middleware/_prompt_caching.py:41-43`), so it is a no-op on non-Anthropic models.
- **Trap: model strings get the Responses API.** String specs go through `resolve_model` → `init_chat_model(model, **apply_provider_profile(model))` (`_models.py:35-57`). The built-in `openai` provider profile sets `use_responses_api=True` (`profiles/provider/_openai.py`). Command Code is chat-completions only, so a string `openai:...` model, including a subagent's `model:` string, would hit the wrong API. **Always pass `ChatOpenAI(..., use_responses_api=False)` instances.** The docstring says the same (`graph.py:322-330`).
- **No harness profile matches our models** (probe). Ling → none. `claude-sonnet-5-5` → none. `claude-haiku-4-5-20251001` does not match the key `anthropic:claude-haiku-4-5` (`profiles/harness/_anthropic_haiku_4_5.py:50`). So no Claude prompt suffix is added; we fully own the prompt (good).
- **Unverified:** whether Command Code's Anthropic-compatible endpoint accepts the `cache_control` blocks that the caching middleware adds to `ChatAnthropic` requests. If it rejects them, the release model fails. This is a first-slice check.
- **Weak-model behavior:** the docs say only "any LangChain chat model that supports tool calling" and list Gemini/GPT/Claude/GLM/Kimi as performing well ([models docs](https://docs.langchain.com/oss/python/deepagents/models)). There is no statement on small models. Ling's tool calling is undocumented (**unverified**). Note that the `task` schema rejects invented keys (`subagents.py:438-459`), which helps weak models recover.

### 4. Summarization does not fit Ling

`ChatOpenAI` for Ling has `profile=None` (probe), so the trigger falls back to **170,000 tokens** (`summarization.py:292-299`). If Ling's context window is smaller (**unverified**), the provider errors first. Recovery then depends on Command Code's error being mapped to `ContextOverflowError` (**unverified**). Fix: pass `ChatOpenAI(..., profile={"max_input_tokens": N})` or override the summarization middleware by name (0.7.0 feature).

### 5. API churn (0.x)

- **Cadence:** 96 `deepagents==` releases on GitHub. 0.3.0 (2025-12-08), 0.4.0 (2026-02-10), 0.5.0 (2026-04-07), 0.6.0 (2026-05-12), 0.7.0 (2026-07-29), then 0.7.1→0.7.21 in 9 weeks (a patch every 2–4 days) (`gh release list -R langchain-ai/deepagents`).
- **0.7.0 broke about 12 things** that touch us directly: todos removed by default, base prompt emptied, prompt constants removed, `write_file` now overwrites (no file-exists guard), new recursive `delete` tool on by default, and backend API shims removed ([release notes](https://github.com/langchain-ai/deepagents/releases/tag/deepagents%3D%3D0.7.0)). Further deprecations are scheduled for 0.9.0 and 1.0.0 (`graph.py:128-135`, `:155-165`).
- The docs lag the code: the overview still advertises `write_todos` as a built-in feature ([overview](https://docs.langchain.com/oss/python/deepagents/overview)).
- `pyproject.toml` pins `deepagents>=0.7.20`, a floor not a pin. 0.7.21 is already out (2026-09-30).

### 6. Defaults that work against ADR 0003

- `write_file` overwrites and `delete` is recursive (0.7.0 release). A model can clobber or delete `previous_brief.md`, which we need for "what changed". Use `FilesystemMiddleware(tools=["ls","read_file","write_file"])` **in the main `middleware=` and in each subagent spec's `middleware`**, because main-agent middleware does not reach declarative subagents (`graph.py:728-737`; `SubAgent` docstring `subagents.py:105-108`). Alternatively, add a deny rule on `/previous_brief.md` via `permissions=`, which subagents do inherit (`graph.py:685`).
- The auto `general-purpose` subagent inherits all tools (`graph.py:837-842`). It is a 4th, unscoped researcher that bypasses our three. Disable it via a profile (`GeneralPurposeSubagentProfile(enabled=False)`, `graph.py:409-411`) or define our own.
- Subagents inherit the parent's `tools`, `interrupt_on` and `permissions` (`graph.py:685`, `:754`, `:762`), but **not** its custom `middleware` (`:728-737`). This asymmetry is easy to get wrong.

### 7. Opacity and debugging

- The real stack is assembled at runtime from profiles, exclusions and name-based replacement (`graph.py:205-239`, `:617-959`). The compiled graph shows only `model`, `tools` and `PatchToolCallsMiddleware.before_agent` nodes (probe), so middleware behavior is invisible in Studio's graph view and appears only in traces.
- `messages` uses `DeltaChannel`, which is marked **beta** (`SP/langgraph/channels/delta.py:25-36`; `graph.py:74-77`). The base saver has a fallback (`SP/langgraph/checkpoint/base/__init__.py:582`), but Postgres saver / `langgraph_api` behavior is **unverified** (only the sqlite saver is installed). In LangGraph Server, the server supplies the checkpointer.
- **Known open issues** (relevant only to the experimental QuickJS/PTC path, which we don't use): [#4832](https://github.com/langchain-ai/deepagents/issues/4832) (a HITL gate inside a subagent can be silently skipped) and [#4833](https://github.com/langchain-ai/deepagents/issues/4833).

### 8. Testing with fake models

- **Works**, verified by the probe. `BaseChatModel.bind_tools` raises by default, so the fake must override it.
- Main and subagents can share one model instance. A single shared script is order-fragile once the main agent dispatches parallel `task` calls, so give each subagent its own scripted model via the spec's `model` (done in the middle-option probe).

## Own-harness option

**waku baseline.** The clone is at `/home/shehanp12/Projects/test/waku-agent`, not the scratchpad path in the brief. `waku/loop/agent.py` is 138 lines including docstrings: a `for` loop over `client.messages.create`, executing `tool_use` blocks, with a `max_iterations=10` guard (`agent.py:59-138`).
- It is **bound to the Anthropic SDK** (`agent.py:24`, `:104-110`), so it can't run Ling as-is.
- It has no persistence, interrupts, subagents or summarization.
- `docs/loop-vs-graph.md` makes the same argument as our ADR 0005: "a graph can't forget" and "a model that is never given tools cannot use them".

**What we would write** to match the Brief researcher (estimates, opinion):

| Piece | Approach | Rough size |
|---|---|---|
| Loop + tool calling | LangGraph `StateGraph` (model node ↔ ToolNode) or `create_agent`. Provider-neutral via `bind_tools`. | 40–80 lines |
| Subagent dispatch | One tool per researcher that invokes a compiled sub-graph with a fresh message list and returns the final text | 60–100 |
| File scratchpad | A `files: dict[str, str]` state key with a merge reducer, plus `read_file`/`write_file` tools returning `Command(update=...)` | 60–100 |
| HITL | `interrupt()` inside a tool or node; we need this anyway for `decisions.ask()` | 20–40 |
| Summarization | LangChain `SummarizationMiddleware`, or trim and skip it in v1 | 0–150 |
| Call cap, retries | `ModelCallLimitMiddleware` or a counter in state | 10–30 |

**Total:** about 250–500 lines plus tests. **Gain:** a far smaller prompt and schema per call, every call visible, no 0.x churn, and the learning. **Lose:** context offload, `ContextOverflowError` recovery, tested parallel subagent state merging, and the "Deep Agents" piece of the stated project goal (`pyproject.toml` description: "LangChain, LangGraph, Deep Agents and LangSmith, one piece each").

## Middle options

| Option | Verdict |
|---|---|
| **A. `create_agent` + selected middleware** (`TodoListMiddleware`, `deepagents.middleware.FilesystemMiddleware(tools=[...])`, `SubAgentMiddleware`, `ModelCallLimitMiddleware`) | **Works** (probe: 5 calls, `/brief.md` written, about 1,120 schema tokens/call vs about 2,570). Caveat: declarative subagents get *no* default middleware this way (the subagent saw only `web_search`), and you must supply `model` per spec. You still import deepagents internals, so you still face churn. Best ratio of control to effort. |
| **B. `create_deep_agent`, configured** (instances, todos added, FS allowlist via `middleware=` name replacement, call cap, GP subagent off) | Keeps the "Deep Agents" learning goal and the subagent defaults (FS + summarization in each researcher). More hidden behavior, but documented. **Recommended for Briefs.** |
| **C. Custom LangGraph subgraph** (fixed fan-out: 3 researcher nodes in parallel → writer → `criteria-checker`) | Strong candidate *once the Brief shape settles* ("write the skill first, harden into a graph later", waku `docs/loop-vs-graph.md`). Fewest calls and deterministic evals, but it contradicts ADR 0005's "steps can't be drawn in advance" for v1. |
| **D. Deep Agents for Briefs, `create_agent` for the Copilot** | **Recommended overall.** |

## Recommendation per use (opinion)

**Brief researcher → `create_deep_agent` (option B), behind `briefs.write_brief()`.**
- `deepagents==0.7.21` (or 0.7.20) **exact pin**. Upgrade deliberately, reading release notes.
- Models as instances: `ChatOpenAI(model=..., base_url=..., use_responses_api=False, profile={"max_input_tokens": N})` and `ChatAnthropic(model=..., base_url=...)`. Pass them to the main agent *and* each subagent spec.
- Main agent: `middleware=[TodoListMiddleware(), FilesystemMiddleware(backend=..., tools=["ls","read_file","write_file"]), ModelCallLimitMiddleware(run_limit=~10)]`. The FS instance replaces the default by name (0.7.0 feature).
- **Each researcher spec repeats** the FS allowlist and its own `ModelCallLimitMiddleware(run_limit=~6)` in `middleware`, because the main list does not propagate (`graph.py:728-737`). The effective cap per Brief is about 10 + 3×6 = 28 calls.
- Disable or replace the `general-purpose` subagent. Give `criteria-checker` no search tool.
- Enforce "no score" and "every claim has a source" in **code after the agent returns** (parse `brief.md` + `sources.json`), not just in the prompt. The deterministic eval in `docs/design.md` already expects this.
- Rationale: context isolation and the file artifact model are exactly what this task needs, and this is where the project's "one piece each" Deep Agents learning lives.

**Operator Copilot → `create_agent` + our tools, no `interrupt_on` for Decisions.**
- Decision-shaped tools (approve/decline/send/archive) call `decisions.ask(DecisionRequest)` → `interrupt(neutral_payload)` → the surface adapter. This is the same path as the email graph (ADR 0001), and it records the Hub Operator from the resume value.
- `HumanInTheLoopMiddleware` is fine as a *backstop* on any write tool, but not as the Decision Request mechanism.
- No FS or subagents: the Copilot calls `briefs.write_brief()` as a tool when it needs research, which reuses the Deep Agent.
- Add `ModelCallLimitMiddleware`.

## What to verify first (TDD slice checklist)

- [ ] Ling via Command Code: `ChatOpenAI(use_responses_api=False).bind_tools([...])` returns `tool_calls` (1–2 real requests).
- [ ] Ling's context window. Set `profile={"max_input_tokens": ...}` and check that summarization triggers below it.
- [ ] `ChatAnthropic(base_url=Command Code)` through `create_deep_agent`: does the endpoint accept `cache_control` blocks? (1 real request)
- [ ] Fake-model test: Brief researcher with a scripted model per subagent writes `/brief.md` + `/sources.json`, keeps `/previous_brief.md` unchanged, and never calls `delete`.
- [ ] Count model calls per scripted Brief. Assert that a looping **subagent** fake is stopped by its own `ModelCallLimitMiddleware`, and that a looping main fake is stopped too.
- [ ] Each researcher's bound tools exclude `edit_file`/`delete`/`glob`/`grep` (assert via the fake model's recorded tool names).
- [ ] Copilot: a model turn with a decision tool call plus a sibling read tool call. After the `decisions.ask()` resume, the sibling ran exactly once.
- [ ] Graph exported in `langgraph.json` loads under `langgraph dev` with Postgres. Check thread state / time-travel with `DeltaChannel` messages in Studio.
- [ ] Decision Request round-trip: `interrupt(neutral_payload)` → resume from the surface (Agent Inbox or a test adapter) → Decision recorded with the Hub Operator. Decide whether the demo still uses Agent Inbox, given that it is archived and appears to be schema-incompatible.
- [ ] LangSmith trace shows subagent runs nested under the `task` tool call.

## Probe method

Throwaway scripts in the session scratchpad, run with the project venv (`.venv/bin/python`), with nothing installed. The fake model is a `BaseChatModel` subclass with `bind_tools` returning `model_copy(update={"bound_tools": tools})`. `_generate` pops a scripted `AIMessage` and records the system text, the bound tool names and the tool-schema size (`convert_to_openai_tool` + tiktoken `cl100k_base`). The scripts covered four runs:
1. Minimal `create_deep_agent`.
2. A Brief run with one `company-researcher` subagent and a fake `web_search`.
3. `interrupt_on` with `InMemorySaver` and a `reject` resume.
4. `create_agent` + `FilesystemMiddleware`/`SubAgentMiddleware`/`ModelCallLimitMiddleware`.

Agent Inbox was shallow-cloned at HEAD (2026-09-18) for source reading only.

## Sources

**Installed source** (`SP/` = `/home/shehanp12/Projects/test/langchain/.venv/lib/python3.12/site-packages/`)
- `SP/deepagents/graph.py`
- `SP/deepagents/middleware/{subagents,summarization,filesystem,_prompt_caching,memory,skills,async_subagents}.py`
- `SP/deepagents/_models.py`
- `SP/deepagents/profiles/{_builtin_profiles.py,harness/*.py,provider/_openai.py}`
- `SP/langchain/agents/middleware/{human_in_the_loop,todo,model_call_limit}.py`
- `SP/langgraph/channels/delta.py`

**GitHub**
- deepagents releases: https://github.com/langchain-ai/deepagents/releases (esp. `deepagents==0.7.0`, `==0.7.21`)
- deepagents issues #4832, #4833: https://github.com/langchain-ai/deepagents/issues
- Agent Inbox (archived): https://github.com/langchain-ai/agent-inbox. Files read: `src/components/agent-inbox/contexts/utils.ts`, `contexts/ThreadContext.tsx`, `hooks/use-interrupted-actions.tsx`, `types.ts`.

**Docs**
- https://docs.langchain.com/oss/python/deepagents/overview
- https://docs.langchain.com/oss/python/deepagents/models
- https://docs.langchain.com/oss/python/deepagents/human-in-the-loop

**Project and baseline**
- waku-agent: `/home/shehanp12/Projects/test/waku-agent/waku/loop/agent.py`, `docs/loop-vs-graph.md`
- Project: `docs/design.md`, `CONTEXT.md`, `docs/adr/0001`, `0003`, `0005`, `pyproject.toml`
