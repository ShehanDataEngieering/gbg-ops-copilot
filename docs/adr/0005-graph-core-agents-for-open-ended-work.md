# A graph runs every email; agents only do open-ended work

Every email goes through a fixed LangGraph StateGraph (triage → recall Person → Brief if high value → Decision Request → record Decision). Deep Agents with subagents are used only where the steps can't be drawn in advance: researching a Brief, and the Operator Copilot chat. We rejected a single Deep Agent orchestrator for the email flow because it can skip triage or forget the Decision Request — a procedure the model *may* follow — whereas the graph is one it *cannot not* follow, and a fixed path is what makes the evals meaningful.

## Amendment (Oct 2026): only the Brief researcher is a Deep Agent

Research (docs/research/deep-agents-vs-own-harness.md) showed the Operator Copilot needs neither subagents nor a filesystem, and that Deep Agents' `interrupt_on` produces a tool-shaped approval that records no Hub Operator. The Operator Copilot is therefore a plain LangChain `create_agent`: its decision tools call `decisions.ask()` — the same Decision Request path as the email graph (ADR 0001) — and it calls `write_brief()` when it needs research. The Brief researcher stays a Deep Agent, configured explicitly (exact version pin, model instances, call caps per subagent, restricted file tools).
