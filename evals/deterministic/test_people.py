"""Seam: people.recall / record / similar. A Person is identified by exact email address."""

from datetime import datetime

import pytest

from langgraph.store.memory import InMemoryStore

from copilot.people import ApplicationReceived, DecisionMade, EmailReceived, People, UnknownApplication


def march_application(**overrides):
    fields = dict(
        application_id="app-2026-0312-elin",
        address="elin@fjordsight.example",
        name="Elin Sund",
        company="Fjordsight AB",
        based_in="Gothenburg",
        gothenburg_plan="Already based in Gothenburg",
        situation="Working toward product-market fit",
        received_at=datetime(2026, 3, 12, 9, 30),
    )
    return ApplicationReceived(**(fields | overrides))


def test_later_email_from_the_same_address_finds_the_earlier_application():
    people = People(store=InMemoryStore())
    people.record(march_application())

    history = people.recall("elin@fjordsight.example")

    assert [a.company for a in history.applications] == ["Fjordsight AB"]


def test_address_case_does_not_split_one_person_in_two():
    people = People(store=InMemoryStore())
    people.record(march_application())

    history = people.recall("Elin@Fjordsight.EXAMPLE")

    assert [a.company for a in history.applications] == ["Fjordsight AB"]


def test_a_decision_on_an_application_is_remembered_with_who_made_it():
    people = People(store=InMemoryStore())
    people.record(march_application())
    people.record(
        DecisionMade(
            address="elin@fjordsight.example",
            application_id="app-2026-0312-elin",
            choice="Revisit",
            reason="Too early",
            hub_operator="viktor.gold@aigothenburg.com",
            made_at=datetime(2026, 3, 20, 14, 0),
        )
    )

    decision = people.recall("elin@fjordsight.example").applications[0].decision

    assert (decision.choice, decision.reason, decision.hub_operator) == (
        "Revisit",
        "Too early",
        "viktor.gold@aigothenburg.com",
    )


def test_a_decision_on_an_unknown_application_is_refused():
    people = People(store=InMemoryStore())
    people.record(march_application())

    with pytest.raises(UnknownApplication):
        people.record(
            DecisionMade(
                address="elin@fjordsight.example",
                application_id="app-does-not-exist",
                choice="Approve",
                hub_operator="viktor.gold@aigothenburg.com",
                made_at=datetime(2026, 3, 20, 14, 0),
            )
        )


def test_emails_join_the_persons_history_next_to_their_application():
    people = People(store=InMemoryStore())
    people.record(march_application())
    people.record(
        EmailReceived(
            address="elin@fjordsight.example",
            conversation_id="conv-gp-article",
            mailbox="press@aigothenburg.com",
            subject="GP wrote about Fjordsight",
            category="Press",
            asks=["Reapply to the hub", "Send the press kit"],
            received_at=datetime(2026, 9, 8, 10, 15),
        )
    )

    history = people.recall("elin@fjordsight.example")

    assert [e.subject for e in history.emails] == ["GP wrote about Fjordsight"]
    assert [a.company for a in history.applications] == ["Fjordsight AB"]


def decision(choice, reason=None):
    return DecisionMade(
        address="elin@fjordsight.example",
        application_id="app-2026-0312-elin",
        choice=choice,
        reason=reason,
        hub_operator="sara@demo.example",
        made_at=datetime(2026, 3, 20, 14, 0),
    )


def test_a_revisited_application_keeps_the_person_an_applicant():
    people = People(store=InMemoryStore())
    people.record(march_application())
    people.record(decision("Revisit", "Too early"))

    assert people.recall("elin@fjordsight.example").roles == {"Applicant"}


def test_an_approved_application_makes_the_person_a_member():
    people = People(store=InMemoryStore())
    people.record(march_application())
    people.record(decision("Approve"))

    assert people.recall("elin@fjordsight.example").roles == {"Member"}


def test_a_declined_application_leaves_no_role():
    people = People(store=InMemoryStore())
    people.record(march_application())
    people.record(decision("Decline", "Too early"))

    assert people.recall("elin@fjordsight.example").roles == set()


def test_the_same_application_recorded_twice_stays_one_and_keeps_its_decision():
    people = People(store=InMemoryStore())
    people.record(march_application())
    people.record(decision("Revisit", "Too early"))
    people.record(march_application())

    applications = people.recall("elin@fjordsight.example").applications
    assert [(a.application_id, a.decision.choice) for a in applications] == [("app-2026-0312-elin", "Revisit")]
