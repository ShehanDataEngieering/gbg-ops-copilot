"""Demo seed and reset for the pitch (ADR 0006).

The seed loads the hub's *past* — a small fictional cast — through
people.record(), the same path live events use. Every Person and the Hub
Operator behind past Decisions are invented; live Decisions in the meeting
are recorded under the name the person in the room types.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.runtime import Runtime
from langgraph.store.base import BaseStore

from copilot.people import ApplicationReceived, DecisionMade, People

DEMO_OPERATOR = "sara@demo.example"  # fictional Hub Operator for seeded history

CAST = [
    ApplicationReceived(
        application_id="app-2026-0312-elin",
        address="elin@fjordsight.example",
        name="Elin Sund",
        company="Fjordsight AB",
        based_in="Gothenburg",
        gothenburg_plan="Already based in Gothenburg",
        situation="Working toward product-market fit",
        received_at=datetime(2026, 3, 12, 9, 30),
    ),
    DecisionMade(
        address="elin@fjordsight.example",
        application_id="app-2026-0312-elin",
        choice="Revisit",
        reason="Too early",
        hub_operator=DEMO_OPERATOR,
        made_at=datetime(2026, 3, 20, 14, 0),
    ),
    # A Member: approved in April, now books rooms at the hub.
    ApplicationReceived(
        application_id="app-2026-0402-omar",
        address="omar@triagely.example",
        name="Omar Nilsson",
        company="Triagely",
        based_in="Gothenburg (Lindholmen)",
        gothenburg_plan="Already based in Gothenburg",
        situation="Working toward product-market fit",
        received_at=datetime(2026, 4, 2, 11, 0),
    ),
    DecisionMade(
        address="omar@triagely.example",
        application_id="app-2026-0402-omar",
        choice="Approve",
        hub_operator=DEMO_OPERATOR,
        made_at=datetime(2026, 4, 9, 10, 0),
    ),
    # An Applicant still waiting for a Decision.
    ApplicationReceived(
        application_id="app-2026-0928-linnea",
        address="linnea@evalkit.example",
        name="Linnea Ek",
        company="EvalKit",
        based_in="Stockholm",
        gothenburg_plan="Willing to relocate or spend significant time in Gothenburg",
        situation="I have a company that is already working",
        received_at=datetime(2026, 9, 28, 16, 45),
    ),
]


class DemoState(TypedDict, total=False):
    recorded: int


def seed(state: DemoState, runtime: Runtime) -> DemoState:
    people = People(store=runtime.store)
    for event in CAST:
        people.record(event)
    return {"recorded": len(CAST)}


def build_seed_graph(*, store: BaseStore | None = None):
    builder = StateGraph(DemoState)
    builder.add_node("seed", seed)
    builder.add_edge(START, "seed")
    builder.add_edge("seed", END)
    return builder.compile(store=store)


def reset(state: DemoState, runtime: Runtime) -> DemoState:
    forgotten = People(store=runtime.store).forget_everyone()
    return {"recorded": -forgotten}


def build_reset_graph(*, store: BaseStore | None = None):
    builder = StateGraph(DemoState)
    builder.add_node("reset", reset)
    builder.add_edge(START, "reset")
    builder.add_edge("reset", END)
    return builder.compile(store=store)


seed_graph = build_seed_graph()
reset_graph = build_reset_graph()
