# A graph runs every email; agents only do open-ended work

Every email goes through a fixed LangGraph StateGraph (triage → recall Person → Brief if high value → Decision Request → record Decision). Deep Agents with subagents are used only where the steps can't be drawn in advance: researching a Brief, and the Operator Copilot chat. We rejected a single Deep Agent orchestrator for the email flow because it can skip triage or forget the Decision Request — a procedure the model *may* follow — whereas the graph is one it *cannot not* follow, and a fixed path is what makes the evals meaningful.
