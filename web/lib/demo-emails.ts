// Fictional people in AI Gothenburg's real public context (CONTEXT.md, Q20).
export type DemoEmail = {
  mailbox: string;
  sender: string;
  subject: string;
  body: string;
  headers?: Record<string, string>;
};

export const demoEmails: DemoEmail[] = [
  {
    mailbox: "hello@aigothenburg.com",
    sender: "partner@kustvind.example",
    subject: "Investor Night + podcast",
    body:
      "Hi! I'm a partner at Kustvind Ventures. Could I get a seat at Investor Night on Oct 14? " +
      "Fjordsight looks like a great fit for us, would love an intro. Also happy to be a guest on the podcast.",
  },
  {
    mailbox: "info@aigothenburg.com",
    sender: "news@saas-weekly.example",
    subject: "10 AI tools you need this week",
    body: "Our top picks for founders this week...",
    headers: { "List-Unsubscribe": "<https://saas-weekly.example/unsubscribe>" },
  },
  {
    mailbox: "members@aigothenburg.com",
    sender: "omar@triagely.example",
    subject: "Room for a customer demo",
    body: "Hi! Could we book the big room on Tuesday 10–12 for a demo with a clinic?",
  },
  {
    mailbox: "press@aigothenburg.com",
    sender: "Elin@Fjordsight.example",
    subject: "GP skrev om Fjordsight",
    body:
      "Hej! Göteborgs-Posten skrev igår om Fjordsight. Vi har nu två betalande kunder. " +
      "Jag skulle gärna vilja söka till hubben igen, och kan ni skicka ert pressmaterial till vår uppföljningsartikel?",
  },
];
