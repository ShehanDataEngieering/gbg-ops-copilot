# Feed Hub Admin, never replace it

AI Gothenburg already runs its own admin system (applications, email queue, tasks, members, audit log). The assistant is a standalone core with explicit connection points into that system — Decisions, drafts and tasks are handed to Hub Admin rather than kept in a parallel queue. We rejected building a competing admin, and rejected replacing parts of theirs, because "now you have two systems" kills adoption with a team that built its own tools.
