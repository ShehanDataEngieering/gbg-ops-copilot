# AI Gothenburg Ops Copilot

An assistant for the people who run the AI Gothenburg founder hub: it helps them review founder applications and keep up with the hub's inbox, while a human makes every decision.

## Language

### People

**Hub Operator**:
A person who runs the hub day to day: reads the inbox, reviews applications, and makes the decisions. There is at least one, possibly two or three.
_Avoid_: admin, organizer, user, reviewer

**Person**:
One human the hub deals with, identified by email address. A Person holds Roles over time and carries the full history of their emails, Applications and Decisions.
_Avoid_: contact, user, lead, founder (as an identity)

**Role**:
What a Person is to the hub at a given time: Applicant, Member, Supporter, Partner, Investor, Press. A Person can hold several at once and change them over time. Applicant and Member follow from Applications and their Decisions; every other Role is only suggested by the assistant and becomes real when a Hub Operator confirms it. An email's Category never sets a Role.
_Avoid_: type, status, label

**Applicant**:
A Person with at least one Application still awaiting a Decision.
_Avoid_: candidate, lead

**Member**:
A Person whose Application was approved and who builds from the hub, as part of a Member Company.
_Avoid_: resident, tenant

**Member Company**:
A company building from the hub. Members belong to it; the relationship with the hub is always held by its Persons.
_Avoid_: startup, portfolio company, team

**Application**:
One submission of the hub's founder form by a Person. A Person may submit several over time; each gets its own Decision.
_Avoid_: submission, request

**Decline Reason**:
The short, fixed reason recorded with a declined Application (too early, not AI-first, not building from Gothenburg, other). Internal only; never sent to the Applicant automatically.
_Avoid_: rejection note, feedback

**Revisit**:
A Decision to look at an Application again later instead of deciding now. When that Person writes again, the assistant flags the earlier Application.
_Avoid_: waitlist, maybe, snooze

### Systems

**Operator Copilot**:
The chat a Hub Operator talks to for open questions and ad-hoc research. It can look things up and prepare Decision Requests, but never makes a Decision itself.
_Avoid_: chatbot, assistant (for this specific surface)

**Hub Admin**:
AI Gothenburg's own existing admin system (applications, email queue, tasks, members, audit log). The assistant feeds it; it never replaces it.
_Avoid_: backend, CMS, dashboard

### Work

**Decision**:
A choice made by a named Hub Operator (approve, decline, send, archive). Every Decision records who made it; the assistant never makes one on its own.
_Avoid_: action, verdict

**Decision Request**:
A question the assistant puts to a Hub Operator when it needs a Decision: what it proposes, the supporting material, and the allowed choices. It is the same no matter where the Hub Operator sees it.
_Avoid_: interrupt, approval, task

### Inbox

**Category**:
A named topic an incoming email is sorted into (e.g. Podcast, Partnership, Press). Hub Operators own the list and can change it; each Category has a description and examples.
_Avoid_: label, tag, folder, type

**Unsorted**:
The state of an email the assistant could not place in any Category after one retry. It waits in the Daily Report for a Hub Operator's Correction; it is never treated as Noise.
_Avoid_: unknown, other, misc, uncategorized

**Correction**:
A Hub Operator's fix of the Category the assistant chose for an email. Every Correction becomes a test case the next version of the sorting must pass.
_Avoid_: feedback, relabel, override

**Ask**:
One distinct request inside an email (e.g. "a seat at Investor Night", "a podcast slot"). An email has exactly one Category but may carry several Asks; all Asks from one email are answered in a single reply.
_Avoid_: request, intent, action item

**Mailbox**:
An email address the assistant reads. Shared Mailboxes (hello@, info@, members@, press@, admin@) are read by default; a Hub Operator's personal Mailbox only if that Hub Operator connects it.
_Avoid_: inbox, account

**Brief**:
A sourced research summary about a Person (and their company) prepared for a Hub Operator before a Decision. It lists evidence per Criterion, what is still unknown, and suggested follow-up questions — never a score or recommendation. Every Brief is kept with its date; when a Person returns, a new Brief builds on the previous one and states what changed since. Written automatically for Applications and for Partnership, Investor and Press emails; on request otherwise.
_Avoid_: profile, report, dossier, assessment

**Criterion**:
One of the hub's own published selection criteria (e.g. "building a real company", "able to work from the hub"). Briefs organise evidence by Criterion.
_Avoid_: requirement, score, rubric

**Conversation**:
One email reply chain. It is the unit of work: each Conversation is handled on its own and shows up as its own item for a Hub Operator, while the Person's history from other Conversations is always shown alongside.
_Avoid_: thread (reserved for the technical run), ticket, case

### Reporting

**Daily Report**:
A calm once-a-day email to the Hub Operators summarising what arrived since the last one and what needs a Decision.
_Avoid_: digest, newsletter, summary

**Urgent Alert**:
An immediate notice about one item that cannot wait for the next Daily Report, delivered where Decisions are made. Capped at a few per day.
_Avoid_: notification, ping
