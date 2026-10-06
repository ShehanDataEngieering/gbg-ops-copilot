"""Triage: sort one email into exactly one Category and pull out its Asks.

Obvious Noise is decided by rules first, so the model is only asked about
emails a rule can't settle — the same idea as waku's retrieval gate.
A Category off the list gets one retry; after that the email is Unsorted,
never silently Noise.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from importlib import resources

from langsmith import traceable
from pydantic import BaseModel
from pydantic import Field as PydanticField

UNSORTED = "Unsorted"


@dataclass(frozen=True)
class Email:
    mailbox: str
    sender: str
    subject: str
    body: str
    headers: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Triage:
    category: str
    asks: list[str]
    wants_brief: bool = False


@dataclass(frozen=True)
class Category:
    name: str
    description: str
    example: str
    brief: bool = False


def load_categories() -> list[Category]:
    text = resources.files("copilot").joinpath("categories.toml").read_text(encoding="utf-8")
    return [Category(**entry) for entry in tomllib.loads(text)["category"]]


class _ModelAnswer(BaseModel):
    category: str = PydanticField(description="Exactly one Category name, copied from the list.")
    asks: list[str] = PydanticField(description="Every distinct request in the email, one per item.")


def _is_noise_by_rule(email: Email) -> bool:
    headers = {name.lower(): value for name, value in email.headers.items()}  # names are case-insensitive
    # RFC 3834: any Auto-Submitted value other than "no" means a machine sent it.
    automatic = headers.get("auto-submitted", "no").lower() != "no"
    # RFC 2369: List-Unsubscribe marks bulk mail. All of it is Noise by decision,
    # including newsletters from partners.
    bulk = "list-unsubscribe" in headers
    return automatic or bulk


def _messages(email: Email, categories: list[Category]) -> list[tuple[str, str]]:
    listing = "\n".join(f"- {c.name}: {c.description} (e.g. \"{c.example}\")" for c in categories)
    return [
        (
            "system",
            "Sort this email for the AI Gothenburg founder hub. Pick exactly one Category "
            "from the list, using its name exactly as written, and list every Ask "
            "(each distinct request) in the email.\n\nCategories:\n" + listing,
        ),
        ("human", f"To: {email.mailbox}\nFrom: {email.sender}\nSubject: {email.subject}\n\n{email.body}"),
    ]


@traceable(name="triage", run_type="chain")
def triage(email: Email, *, model, categories: list[Category] | None = None) -> Triage:
    if _is_noise_by_rule(email):
        return Triage(category="Noise", asks=[])

    categories = categories or load_categories()
    allowed = {c.name for c in categories}
    messages = _messages(email, categories)
    # Tool calling is the structured-output method every model we use supports
    # (Ling rejects JSON-schema and JSON mode).
    sorter = model.with_structured_output(_ModelAnswer, method="function_calling")

    answer = sorter.invoke(messages)
    if answer.category not in allowed:
        retry = messages + [
            ("ai", f"Category: {answer.category}"),
            ("human", f'"{answer.category}" is not on the list. Use one of: {", ".join(sorted(allowed))}.'),
        ]
        answer = sorter.invoke(retry)
    if answer.category not in allowed:
        return Triage(category=UNSORTED, asks=list(answer.asks))
    chosen = next(c for c in categories if c.name == answer.category)
    return Triage(category=chosen.name, asks=list(answer.asks), wants_brief=chosen.brief)
