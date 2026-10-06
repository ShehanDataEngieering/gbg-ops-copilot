# The first frontend is a live pitch demo, built on LangGraph's own frontend tooling

Agent Inbox, the planned surface for Decision Requests (ADR 0001), is archived and does not match the current interrupt format, so we build our own screens. The first frontend exists to win the pitch, not for daily use: three screens (Inbox with live step-by-step progress, Decision, People), React/Next.js with LangChain's `useStream` against the real LangGraph server, run on the presenter's laptop with no login and no public URL. It is fully live — new emails are processed in front of the audience from a presenter button or an email someone in the room writes — on top of a seeded fictional history.

## Considered Options

A scripted or pre-processed demo was rejected in favour of a fully live one; Streamlit and FastAPI + HTMX were rejected for React/Next.js because `useStream` gives streaming and interrupt/resume as LangChain's own product. Hosting it publicly was rejected: without login, an exposed LangGraph proxy lets anyone read every thread.

## Consequences

- Login, hosting and GDPR controls are deliberately absent and must be added before any real data (pilot).
- Seeded past Decisions belong to a fictional Hub Operator; live Decisions are recorded under the name the person in the room types — never invent records attributed to a real person.
- Brand is neutral ("Ops Copilot, built for AI Gothenburg") with the theme in one config file.
- Build order changes to vertical slices: the email graph comes forward so each step ends in a clickable screen.
