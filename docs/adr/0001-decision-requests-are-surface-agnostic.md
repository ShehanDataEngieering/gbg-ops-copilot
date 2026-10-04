# Decision Requests are surface-agnostic

The graph never knows where a Hub Operator sees a Decision Request. It pauses with a neutral payload (what it proposes, the supporting material, the allowed choices), and a thin adapter renders it: Agent Inbox for the pitch demo, Slack (including its mobile app) for production. We chose this over building straight against one UI so that moving from Agent Inbox to Slack is a new adapter, not a rewrite — don't "simplify" by putting Slack or Agent Inbox specifics into graph nodes.
