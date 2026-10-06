"""Command line: `copilot triage` runs one email through triage with a real model.

    uv run copilot triage --list            # show the sample emails
    uv run copilot triage --sample 2        # triage sample 2
    uv run copilot triage --to press@aigothenburg.com --from a@b.se \\
        --subject "Intervju" --body "Hej! ..."   # your own email

Traces go to LangSmith when LANGSMITH_TRACING=true in .env.
"""

from __future__ import annotations

import argparse
import sys
import time

from dotenv import load_dotenv

from copilot.triage import Email, triage

# Fictional senders, real AI Gothenburg context (see CONTEXT.md and docs/design.md).
SAMPLES = [
    Email(
        mailbox="hello@aigothenburg.com",
        sender="partner@kustvind.example",
        subject="Investor Night + podcast",
        body=(
            "Hi! I'm a partner at Kustvind Ventures. Could I get a seat at Investor Night on Oct 14? "
            "Fjordsight looks like a great fit for us, would love an intro. "
            "Also happy to be a guest on the podcast."
        ),
    ),
    Email(
        mailbox="press@aigothenburg.com",
        sender="anna.berg@gp.example",
        subject="Intervju om AI-hubben",
        body=(
            "Hej! Jag skriver en artikel för Göteborgs-Posten om AI-scenen i Göteborg. "
            "Kan vi ses på fredag för en kort intervju? Skicka gärna ert pressmaterial också."
        ),
    ),
    Email(
        mailbox="members@aigothenburg.com",
        sender="elin@fjordsight.example",
        subject="Room for a customer demo",
        body="Hi! Could we book the big room on Tuesday 10-12 for a demo with a shipping customer?",
    ),
    Email(
        mailbox="info@aigothenburg.com",
        sender="news@saas-weekly.example",
        subject="10 AI tools you need this week",
        body="Our top picks for founders...",
        headers={"List-Unsubscribe": "<https://saas-weekly.example/unsubscribe>"},
    ),
]


def _print_samples() -> None:
    for number, email in enumerate(SAMPLES, start=1):
        print(f"{number}. {email.mailbox:<28} {email.subject}")


def _run_triage(args: argparse.Namespace) -> int:
    if args.list:
        _print_samples()
        return 0
    if args.body:
        email = Email(mailbox=args.to, sender=args.sender, subject=args.subject, body=args.body)
    elif 1 <= args.sample <= len(SAMPLES):
        email = SAMPLES[args.sample - 1]
    else:
        print(f"No sample {args.sample}. Run `copilot triage --list` to see them.", file=sys.stderr)
        return 2

    from copilot.models import chat_model  # needs the Command Code key, so only load it now

    started = time.monotonic()
    result = triage(email, model=chat_model("triage", profile=args.profile))
    seconds = time.monotonic() - started

    print(f"Email     {email.subject}  ({email.mailbox})")
    print(f"Category  {result.category}")
    print(f"Brief     {'yes, automatic' if result.wants_brief else 'no'}")
    print("Asks      " + ("\n          ".join(result.asks) if result.asks else "(none)"))
    print(f"Took      {seconds:.1f}s")
    return 0


def main() -> int:
    load_dotenv(".env")
    parser = argparse.ArgumentParser(prog="copilot", description="AI Gothenburg Ops Copilot")
    commands = parser.add_subparsers(dest="command", required=True)

    t = commands.add_parser("triage", help="sort one email into a Category and its Asks")
    t.add_argument("--sample", type=int, default=1, help="which sample email to use (default 1)")
    t.add_argument("--list", action="store_true", help="list the sample emails and exit")
    t.add_argument("--to", default="hello@aigothenburg.com", help="Mailbox the email arrived at")
    t.add_argument("--from", dest="sender", default="someone@example.com", help="sender address")
    t.add_argument("--subject", default="(no subject)")
    t.add_argument("--body", help="email text; when given, it is used instead of a sample")
    t.add_argument("--profile", choices=["dev", "release"], help="dev = free Ling (default), release = Claude")
    t.set_defaults(handler=_run_triage)

    args = parser.parse_args()
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
