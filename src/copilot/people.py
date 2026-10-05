"""People: the Person memory. One deep module hiding the stores.

A Person is identified by exact email address, never by similarity
(ADR 0004). Records live in a LangGraph store: PostgresStore in real use,
InMemoryStore in tests — same interface, so the tests exercise real behavior.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from langgraph.store.base import BaseStore

_PERSONS = ("persons",)


# ── Events: what happened, as recorded with people.record() ──────────────────


@dataclass(frozen=True)
class ApplicationReceived:
    """One submission of the hub's founder form (the real /apply fields)."""

    application_id: str
    address: str
    name: str
    company: str
    based_in: str
    gothenburg_plan: str
    situation: str
    received_at: datetime


@dataclass(frozen=True)
class DecisionMade:
    """A Hub Operator's Decision on one Application."""

    address: str
    application_id: str
    choice: str  # Approve, Decline, Ask for more info, Revisit
    hub_operator: str
    made_at: datetime
    reason: str | None = None  # the Decline Reason, or why it is Revisited


@dataclass(frozen=True)
class EmailReceived:
    """One triaged email from this Person, in one Conversation."""

    address: str
    conversation_id: str
    mailbox: str
    subject: str
    category: str
    asks: list[str]
    received_at: datetime


# ── What people.recall() returns ──────────────────────────────────────────────


@dataclass(frozen=True)
class Decision:
    choice: str
    hub_operator: str
    made_at: datetime
    reason: str | None = None


@dataclass(frozen=True)
class Application:
    application_id: str
    company: str
    based_in: str
    gothenburg_plan: str
    situation: str
    received_at: datetime
    decision: Decision | None = None


@dataclass(frozen=True)
class Email:
    conversation_id: str
    mailbox: str
    subject: str
    category: str
    asks: list[str]
    received_at: datetime


# Choices that still leave an Application waiting for a final Decision.
_STILL_WAITING = {None, "Ask for more info", "Revisit"}


@dataclass(frozen=True)
class History:
    address: str
    name: str | None = None
    applications: list[Application] = field(default_factory=list)
    emails: list[Email] = field(default_factory=list)

    @property
    def roles(self) -> set[str]:
        """Only the Roles that follow from facts. Other Roles are suggested, never derived."""
        choices = {a.decision.choice if a.decision else None for a in self.applications}
        roles = set()
        if choices & _STILL_WAITING:
            roles.add("Applicant")
        if "Approve" in choices:
            roles.add("Member")
        return roles


class UnknownApplication(LookupError):
    """A Decision named an Application this Person never submitted."""


def _key(address: str) -> str:
    # Exact match, but email addresses are case-insensitive in practice.
    return address.strip().lower()


class People:
    def __init__(self, *, store: BaseStore):
        self._store = store

    def record(self, event: ApplicationReceived | DecisionMade | EmailReceived) -> None:
        item = self._store.get(_PERSONS, _key(event.address))
        person = item.value if item else {"name": None, "applications": [], "emails": []}
        if isinstance(event, ApplicationReceived):
            person["name"] = event.name
            person["applications"].append(
                {
                    "application_id": event.application_id,
                    "company": event.company,
                    "based_in": event.based_in,
                    "gothenburg_plan": event.gothenburg_plan,
                    "situation": event.situation,
                    "received_at": event.received_at.isoformat(),
                    "decision": None,
                }
            )
        elif isinstance(event, DecisionMade):
            application = next(
                (a for a in person["applications"] if a["application_id"] == event.application_id), None
            )
            if application is None:
                raise UnknownApplication(f"{event.address} has no Application {event.application_id}")
            application["decision"] = {
                "choice": event.choice,
                "hub_operator": event.hub_operator,
                "made_at": event.made_at.isoformat(),
                "reason": event.reason,
            }
        elif isinstance(event, EmailReceived):
            person["emails"].append(
                {
                    "conversation_id": event.conversation_id,
                    "mailbox": event.mailbox,
                    "subject": event.subject,
                    "category": event.category,
                    "asks": list(event.asks),
                    "received_at": event.received_at.isoformat(),
                }
            )
        self._store.put(_PERSONS, _key(event.address), person)

    def recall(self, address: str) -> History:
        item = self._store.get(_PERSONS, _key(address))
        if item is None:
            return History(address=address)
        person = item.value
        return History(
            address=address,
            name=person["name"],
            applications=[_application(a) for a in person["applications"]],
            emails=[
                Email(**(e | {"received_at": datetime.fromisoformat(e["received_at"])}))
                for e in person["emails"]
            ],
        )


def _application(stored: dict) -> Application:
    decision = stored["decision"]
    return Application(
        application_id=stored["application_id"],
        company=stored["company"],
        based_in=stored["based_in"],
        gothenburg_plan=stored["gothenburg_plan"],
        situation=stored["situation"],
        received_at=datetime.fromisoformat(stored["received_at"]),
        decision=None
        if decision is None
        else Decision(
            choice=decision["choice"],
            hub_operator=decision["hub_operator"],
            made_at=datetime.fromisoformat(decision["made_at"]),
            reason=decision["reason"],
        ),
    )
