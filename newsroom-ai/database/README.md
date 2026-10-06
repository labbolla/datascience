# Database note

This repository is a portfolio snapshot of an MVP that evolved iteratively.
The current application expects PostgreSQL with the `pgvector` extension and the tables referenced by the backend (`stories`, `story_embeddings`, `story_threads`, `story_thread_items`, monitoring tables, alert tables, and related audit/change tables).

The schema has not yet been consolidated into a single production migration chain. For portfolio review, the backend code documents the current data model and queries. A future hardening step is to move the schema to Alembic migrations and provide a reproducible bootstrap command.
