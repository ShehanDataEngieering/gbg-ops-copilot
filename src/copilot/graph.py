"""The email graph: the fixed path every email takes (ADR 0005).

    triage -> recall -> record

State is plain JSON so the LangGraph server can stream it to the frontend.
The store comes from the runtime: InMemoryStore in tests, the server's own
store under `langgraph dev`. The model comes from the run's context, so tests
pass a fake and real runs fall back to models.chat_model("triage").
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypedDict

from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore

from copilot.people import EmailReceived, People
from copilot.triage import Email, triage


@dataclass
class Context:
    model: Any = None


class EmailState(TypedDict, total=False):
    email: dict  # mailbox, sender, subject, body, headers
    conversation_id: str
    received_at: str  # ISO 8601
    triage: dict  # category, asks, wants_brief
    person: dict  # name, roles, applications, emails — who the sender is, before this email


def _progress(step: str, message: str) -> None:
    """A line for the live progress feed (stream_mode="custom")."""
    get_stream_writer()({"step": step, "message": message})


def _model(runtime: Runtime[Context]):
    if runtime.context and runtime.context.model is not None:
        return runtime.context.model
    from copilot.models import chat_model

    return chat_model("triage")


def triage_email(state: EmailState, runtime: Runtime[Context]) -> EmailState:
    _progress("triage", "Sorting the email…")
    email = state["email"]
    result = triage(
        Email(
            mailbox=email["mailbox"],
            sender=email["sender"],
            subject=email["subject"],
            body=email["body"],
            headers=email.get("headers", {}),
        ),
        model=_model(runtime),
    )
    _progress("triage", f"{result.category} · {len(result.asks)} Ask(s)")
    return {"triage": {"category": result.category, "asks": result.asks, "wants_brief": result.wants_brief}}


def recall_person(state: EmailState, runtime: Runtime[Context]) -> EmailState:
    sender = state["email"]["sender"]
    _progress("recall", f"Looking up {sender}…")
    history = People(store=runtime.store).recall(sender)
    person = {
        "address": history.address,
        "name": history.name,
        "roles": sorted(history.roles),
        "applications": [
            {
                "application_id": a.application_id,
                "company": a.company,
                "received_at": a.received_at.isoformat(),
                "decision": None
                if a.decision is None
                else {
                    "choice": a.decision.choice,
                    "reason": a.decision.reason,
                    "hub_operator": a.decision.hub_operator,
                    "made_at": a.decision.made_at.isoformat(),
                },
            }
            for a in history.applications
        ],
        "emails": [
            {"subject": e.subject, "category": e.category, "received_at": e.received_at.isoformat()}
            for e in history.emails
        ],
    }
    if history.name or history.emails:
        _progress("recall", f"Known: {history.name or sender} · {len(history.applications)} Application(s), {len(history.emails)} earlier email(s)")
    else:
        _progress("recall", "New Person")
    return {"person": person}


def record_email(state: EmailState, runtime: Runtime[Context]) -> EmailState:
    email, result = state["email"], state["triage"]
    People(store=runtime.store).record(
        EmailReceived(
            address=email["sender"],
            conversation_id=state["conversation_id"],
            mailbox=email["mailbox"],
            subject=email["subject"],
            category=result["category"],
            asks=result["asks"],
            received_at=datetime.fromisoformat(state["received_at"]),
        )
    )
    _progress("record", "Saved to the Person's history")
    return {}


def build_email_graph(*, store: BaseStore | None = None):
    builder = StateGraph(EmailState, context_schema=Context)
    builder.add_node("triage", triage_email)
    builder.add_node("recall", recall_person)
    builder.add_node("record", record_email)
    builder.add_edge(START, "triage")
    builder.add_edge("triage", "recall")
    builder.add_edge("recall", "record")
    builder.add_edge("record", END)
    return builder.compile(store=store)


# What `langgraph dev` serves; the server supplies the store and checkpointer.
graph = build_email_graph()
