"""Seam: the email graph. Every email goes triage -> recall -> record; no step is skipped."""

from datetime import datetime

from langgraph.store.memory import InMemoryStore

from copilot.graph import Context, build_email_graph
from copilot.people import ApplicationReceived, People


class ScriptedModel:
    def __init__(self, *answers):
        self.answers = list(answers)

    def with_structured_output(self, schema, **_):
        answers = self.answers

        class _Runnable:
            def invoke(self, _messages):
                return schema(**answers.pop(0))

        return _Runnable()


ELIN_SEPTEMBER = {
    "email": {
        "mailbox": "press@aigothenburg.com",
        "sender": "Elin@Fjordsight.example",
        "subject": "GP skrev om Fjordsight",
        "body": "Hej! GP skrev om oss. Jag vill söka igen, och kan ni skicka pressmaterial?",
    },
    "conversation_id": "conv-gp-article",
    "received_at": "2026-09-08T10:15:00",
}


def store_with_elins_march_application():
    store = InMemoryStore()
    People(store=store).record(
        ApplicationReceived(
            application_id="app-2026-0312-elin",
            address="elin@fjordsight.example",
            name="Elin Sund",
            company="Fjordsight AB",
            based_in="Gothenburg",
            gothenburg_plan="Already based in Gothenburg",
            situation="Working toward product-market fit",
            received_at=datetime(2026, 3, 12, 9, 30),
        )
    )
    return store


def test_an_email_run_is_recorded_in_the_persons_history():
    store = store_with_elins_march_application()
    graph = build_email_graph(store=store)
    model = ScriptedModel({"category": "Application", "asks": ["Apply again", "Send press kit"]})

    graph.invoke(ELIN_SEPTEMBER, context=Context(model=model))

    emails = People(store=store).recall("elin@fjordsight.example").emails
    assert [(e.subject, e.category) for e in emails] == [("GP skrev om Fjordsight", "Application")]


def test_the_run_returns_who_the_sender_is_from_memory():
    graph = build_email_graph(store=store_with_elins_march_application())
    model = ScriptedModel({"category": "Application", "asks": ["Apply again"]})

    result = graph.invoke(ELIN_SEPTEMBER, context=Context(model=model))

    person = result["person"]
    assert person["name"] == "Elin Sund"
    assert person["roles"] == ["Applicant"]
    assert [a["company"] for a in person["applications"]] == ["Fjordsight AB"]
