# Postgres for records, Pinecone for similarity

Postgres holds everything that must be exact and durable — Persons, Applications, Decisions (with their Hub Operator), and LangGraph's checkpoints for paused Decision Requests — and matches Hub Admin, which runs on Supabase. Pinecone holds only embeddings for "find similar" (similar applicants, Members that fit a partner's offer, emails by meaning). Pinecone is a derived index: Postgres is the source of truth, every vector carries the Postgres id, and the whole index can be rebuilt from Postgres. Identity (linking an email to a Person) is always an exact lookup in Postgres, never a similarity match.

## Considered Options

A vector database alone was rejected: no LangGraph checkpointer exists for Pinecone, Qdrant, Weaviate or Chroma, and exact questions (who decided what, what is awaiting a Decision) need filters, joins and transactions. Postgres + pgvector would have been one database; Pinecone was chosen to learn a dedicated vector database, accepting the cost of keeping two stores in sync.
