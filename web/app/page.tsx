"use client";

import { useEffect, useRef, useState } from "react";
import { useStream } from "@langchain/langgraph-sdk/react";
import { brand } from "@/lib/brand";
import { demoEmails, type DemoEmail } from "@/lib/demo-emails";

const API_URL = process.env.NEXT_PUBLIC_LANGGRAPH_URL ?? "http://localhost:2024";
const MAILBOXES = ["hello@aigothenburg.com", "press@aigothenburg.com", "members@aigothenburg.com", "info@aigothenburg.com"];

// Mirrors EmailState in src/copilot/graph.py.
type Person = {
  address: string;
  name: string | null;
  roles: string[];
  applications: { company: string; decision: { choice: string; reason: string | null } | null }[];
  emails: { subject: string; category: string }[];
};
type EmailState = {
  email: DemoEmail;
  conversation_id: string;
  received_at: string;
  triage?: { category: string; asks: string[]; wants_brief: boolean };
  person?: Person;
};
type Step = { step: string; message: string; at: number };
type Done = { email: DemoEmail; triage: NonNullable<EmailState["triage"]>; person?: Person; seconds: number };

export default function InboxPage() {
  const [steps, setSteps] = useState<Step[]>([]);
  const [current, setCurrent] = useState<DemoEmail | null>(null);
  const [done, setDone] = useState<Done[]>([]);
  const [next, setNext] = useState(0);
  const startedAt = useRef(0);

  const stream = useStream<EmailState>({
    apiUrl: API_URL,
    assistantId: "email",
    onCustomEvent: (data) => {
      const { step, message } = data as { step: string; message: string };
      setSteps((s) => [...s, { step, message, at: (performance.now() - startedAt.current) / 1000 }]);
    },
  });

  // When a run finishes, move it from "live" into the inbox.
  const wasLoading = useRef(false);
  useEffect(() => {
    if (wasLoading.current && !stream.isLoading && current && stream.values?.triage) {
      setDone((d) => [
        {
          email: current,
          triage: stream.values.triage!,
          person: stream.values.person,
          seconds: (performance.now() - startedAt.current) / 1000,
        },
        ...d,
      ]);
    }
    wasLoading.current = stream.isLoading;
  }, [stream.isLoading, stream.values, current]);

  async function deliver(email: DemoEmail) {
    setCurrent(email);
    setSteps([]);
    startedAt.current = performance.now();
    stream.switchThread(null); // one thread per Conversation
    await stream.submit(
      { email, conversation_id: `conv-${Date.now()}`, received_at: new Date().toISOString() },
      { streamMode: ["custom", "updates", "values"] },
    );
  }

  return (
    <main className="shell">
      <header className="top">
        <div className="brand">
          <h1>{brand.product}</h1>
          <span>{brand.subtitle}</span>
        </div>
        <nav className="tabs" aria-label="Screens">
          <span className="tab on">Inbox</span>
          <span className="tab soon" title="Coming in the next slice">Decisions</span>
          <span className="tab soon" title="Coming later">People</span>
        </nav>
      </header>

      <div className="grid">
        <section className="panel" aria-labelledby="arriving">
          <h2 id="arriving">Arriving</h2>
          <button
            className="primary"
            disabled={stream.isLoading || next >= demoEmails.length}
            onClick={() => {
              deliver(demoEmails[next]);
              setNext((n) => n + 1);
            }}
          >
            Deliver next email
            <small>
              {next < demoEmails.length
                ? `${next + 1}/${demoEmails.length}: ${demoEmails[next].subject}`
                : "All demo emails delivered"}
            </small>
          </button>
          <WriteYourOwn disabled={stream.isLoading} onSend={deliver} />
        </section>

        <section className="panel" aria-labelledby="live" aria-live="polite">
          <div className="live-head">
            <h2 id="live">Live</h2>
            {stream.isLoading && (
              <span className="mono">
                <span className="pulse" aria-hidden="true" />
                working
              </span>
            )}
          </div>
          {current ? (
            <div className="live-email">
              <div>{current.subject}</div>
              <div className="meta">
                from {current.sender} · to {current.mailbox}
              </div>
            </div>
          ) : (
            <p className="empty">Deliver an email to watch the Copilot work, step by step.</p>
          )}
          <ol className="steps">
            {steps.map((s, i) => (
              <li key={i}>
                <span className="t">{s.at.toFixed(1)}s</span>
                <span className="s">{s.step}</span>
                <span>{s.message}</span>
              </li>
            ))}
          </ol>
          {stream.error ? <p className="error">The run failed: {String((stream.error as Error).message ?? stream.error)}</p> : null}
        </section>

        <section className="panel" aria-labelledby="inbox">
          <h2 id="inbox">Inbox · {done.length} sorted</h2>
          {done.length === 0 ? (
            <p className="empty">Sorted emails appear here with their Category, Asks and who sent them.</p>
          ) : (
            <ul className="inbox">
              {done.map((d, i) => (
                <li key={i} className="card">
                  <div className="row">
                    <span className="subject">{d.email.subject}</span>
                    <span className="meta">{d.seconds.toFixed(1)}s</span>
                  </div>
                  <div className="meta">
                    {d.email.sender} → {d.email.mailbox}
                  </div>
                  <div className="chips">
                    <span className={`chip ${categoryClass(d.triage.category)}`}>{d.triage.category}</span>
                    {d.triage.wants_brief && <span className="chip brief">Brief next</span>}
                    {d.person?.roles.map((r) => (
                      <span key={r} className="chip role">
                        {r}
                      </span>
                    ))}
                  </div>
                  {d.triage.asks.length > 0 && (
                    <ul className="asks">
                      {d.triage.asks.map((a, j) => (
                        <li key={j}>{a}</li>
                      ))}
                    </ul>
                  )}
                  <Who person={d.person} />
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </main>
  );
}

function categoryClass(category: string) {
  if (category === "Noise") return "noise";
  if (category === "Unsorted") return "unsorted";
  return "cat";
}

function Who({ person }: { person?: Person }) {
  if (!person) return null;
  const known = person.name || person.emails.length > 0;
  if (!known) return <div className="who">New Person</div>;
  const app = person.applications[0];
  return (
    <div className="who">
      <strong>{person.name ?? person.address}</strong>
      {app && (
        <>
          {" "}
          · applied with {app.company}
          {app.decision && ` · ${app.decision.choice}${app.decision.reason ? ` ("${app.decision.reason}")` : ""}`}
        </>
      )}
      {person.emails.length > 0 && ` · ${person.emails.length} earlier email(s)`}
    </div>
  );
}

function WriteYourOwn({ disabled, onSend }: { disabled: boolean; onSend: (e: DemoEmail) => void }) {
  const [sender, setSender] = useState("");
  const [mailbox, setMailbox] = useState(MAILBOXES[0]);
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  return (
    <form
      className="own"
      onSubmit={(e) => {
        e.preventDefault();
        if (!body.trim()) return;
        onSend({ sender: sender || "guest@example.com", mailbox, subject: subject || "(no subject)", body });
        setBody("");
        setSubject("");
      }}
    >
      <h2>Write your own</h2>
      <label>
        From
        <input id="own-from" value={sender} onChange={(e) => setSender(e.target.value)} placeholder="you@example.com" />
      </label>
      <label>
        To
        <select id="own-to" value={mailbox} onChange={(e) => setMailbox(e.target.value)}>
          {MAILBOXES.map((m) => (
            <option key={m}>{m}</option>
          ))}
        </select>
      </label>
      <label>
        Subject
        <input id="own-subject" value={subject} onChange={(e) => setSubject(e.target.value)} />
      </label>
      <label>
        Email (any language)
        <textarea id="own-body" value={body} onChange={(e) => setBody(e.target.value)} />
      </label>
      <button className="ghost" type="submit" disabled={disabled || !body.trim()}>
        Send to the Copilot
      </button>
    </form>
  );
}
