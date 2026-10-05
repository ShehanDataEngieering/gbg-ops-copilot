"""Seam: the demo seed and reset graphs that prepare the pitch (ADR 0006)."""

from langgraph.store.memory import InMemoryStore

from copilot.demo import build_reset_graph, build_seed_graph
from datetime import datetime

from copilot.people import EmailReceived, People


def test_the_seed_gives_elin_a_revisited_march_application_by_a_fictional_operator():
    store = InMemoryStore()

    build_seed_graph(store=store).invoke({})

    elin = People(store=store).recall("elin@fjordsight.example")
    application = elin.applications[0]
    assert (application.company, application.decision.choice, application.decision.reason) == (
        "Fjordsight AB",
        "Revisit",
        "Too early",
    )
    assert application.decision.hub_operator.endswith("@demo.example")


def test_seeding_twice_does_not_duplicate_anything():
    store = InMemoryStore()
    seed = build_seed_graph(store=store)

    seed.invoke({})
    seed.invoke({})

    assert len(People(store=store).recall("elin@fjordsight.example").applications) == 1


def test_reset_forgets_everyone_including_people_from_live_emails():
    store = InMemoryStore()
    build_seed_graph(store=store).invoke({})
    People(store=store).record(
        EmailReceived(
            address="partner@kustvind.example",
            conversation_id="conv-kustvind",
            mailbox="hello@aigothenburg.com",
            subject="Investor Night + podcast",
            category="Investor",
            asks=["Seat at Investor Night"],
            received_at=datetime(2026, 9, 9, 8, 40),
        )
    )

    build_reset_graph(store=store).invoke({})

    people = People(store=store)
    assert people.recall("elin@fjordsight.example").name is None
    assert people.recall("partner@kustvind.example").emails == []


def test_the_cast_has_a_member_and_an_applicant_still_waiting():
    store = InMemoryStore()
    build_seed_graph(store=store).invoke({})

    people = People(store=store)
    assert people.recall("omar@triagely.example").roles == {"Member"}
    assert people.recall("linnea@evalkit.example").roles == {"Applicant"}
