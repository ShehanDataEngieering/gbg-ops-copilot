"""Seam: triage(email) -> Triage. One Category from the editable list, plus its Asks."""

from copilot.triage import Email, triage


class ModelMustNotBeCalled:
    """Stands in for the model when a rule should decide on its own."""

    def with_structured_output(self, schema, **_):
        raise AssertionError("triage called the model for an email a rule should handle")


def test_automatic_reply_is_noise_without_asking_the_model():
    email = Email(
        mailbox="hello@aigothenburg.com",
        sender="erik.lund@example.se",
        subject="Automatiskt svar: Investor Night",
        body="Jag är på semester till och med 14 oktober.",
        headers={"Auto-Submitted": "auto-replied"},
    )

    result = triage(email, model=ModelMustNotBeCalled())

    assert (result.category, result.asks) == ("Noise", [])


class ScriptedModel:
    """A model at the system boundary that gives scripted structured answers, in order."""

    def __init__(self, *answers):
        self.answers = list(answers)

    def with_structured_output(self, schema, **_):
        answers = self.answers

        class _Runnable:
            def invoke(self, _messages):
                return schema(**answers.pop(0))

        return _Runnable()


def test_one_email_keeps_one_category_and_every_ask():
    email = Email(
        mailbox="hello@aigothenburg.com",
        sender="partner@kustvind.example",
        subject="Investor Night + podcast",
        body=(
            "Hi! I'm a partner at Kustvind Ventures. Could I get a seat at Investor Night "
            "on Oct 14? Fjordsight looks like a great fit for us, would love an intro. "
            "Also happy to be a guest on the podcast."
        ),
    )
    model = ScriptedModel(
        {
            "category": "Investor",
            "asks": ["Seat at Investor Night", "Intro to Fjordsight", "Podcast guest slot"],
        }
    )

    result = triage(email, model=model)

    assert result.category == "Investor"
    assert result.asks == ["Seat at Investor Night", "Intro to Fjordsight", "Podcast guest slot"]


SPONSOR_EMAIL = Email(
    mailbox="hello@aigothenburg.com",
    sender="events@gpucloud.example",
    subject="Sponsoring your Wednesday Afterwork",
    body="We'd like to sponsor the drinks at the next Wednesday Afterwork in exchange for a short talk.",
)


def test_category_off_the_list_twice_leaves_the_email_unsorted():
    model = ScriptedModel(
        {"category": "Sponsorship", "asks": ["Sponsor Wednesday Afterwork"]},
        {"category": "Sponsorship", "asks": ["Sponsor Wednesday Afterwork"]},
    )

    result = triage(SPONSOR_EMAIL, model=model)

    assert result.category == "Unsorted"


def test_category_off_the_list_gets_one_retry():
    model = ScriptedModel(
        {"category": "Sponsorship", "asks": ["Sponsor Wednesday Afterwork"]},
        {"category": "Event proposal", "asks": ["Sponsor Wednesday Afterwork"]},
    )

    result = triage(SPONSOR_EMAIL, model=model)

    assert result.category == "Event proposal"


def test_investor_email_gets_an_automatic_brief():
    model = ScriptedModel({"category": "Investor", "asks": ["Intro to Fjordsight"]})

    result = triage(SPONSOR_EMAIL, model=model)

    assert result.wants_brief is True


def test_event_proposal_gets_no_automatic_brief():
    model = ScriptedModel({"category": "Event proposal", "asks": ["Sponsor Wednesday Afterwork"]})

    result = triage(SPONSOR_EMAIL, model=model)

    assert result.wants_brief is False


def test_bulk_mail_is_noise_without_asking_the_model():
    email = Email(
        mailbox="info@aigothenburg.com",
        sender="news@saas-weekly.example",
        subject="10 AI tools you need this week",
        body="Our top picks for founders...",
        headers={"List-Unsubscribe": "<https://saas-weekly.example/unsubscribe>"},
    )

    result = triage(email, model=ModelMustNotBeCalled())

    assert (result.category, result.asks) == ("Noise", [])


def test_noise_rules_ignore_header_name_case():
    email = Email(
        mailbox="info@aigothenburg.com",
        sender="news@saas-weekly.example",
        subject="10 AI tools you need this week",
        body="Our top picks for founders...",
        headers={"list-unsubscribe": "<https://saas-weekly.example/unsubscribe>"},
    )

    result = triage(email, model=ModelMustNotBeCalled())

    assert result.category == "Noise"
