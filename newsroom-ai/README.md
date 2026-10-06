# Newsroom AI

AI-assisted institutional monitoring for legislative and public-affairs workflows.

Newsroom AI is an MVP built to explore how structured AI decisions, semantic retrieval, event linking and generative summaries can work together in a real monitoring pipeline.

The project currently ingests official Brazilian institutional sources, classifies new items, groups related developments into threads, analyzes what changed between events, and exposes monitoring views through a web application.

> Portfolio project focused on applied AI, data engineering, backend integration and decision-oriented AI workflows.

---

## Preview

![Newsroom AI dashboard](docs/screenshots/dashboard.png)

## Why I built it

Traditional alerts are good at detecting keywords, but much weaker at answering questions such as:

- Is this development actually relevant?
- Is it part of an existing issue?
- What changed compared with previous events?
- Does this deserve immediate attention?
- Can the result be returned in a structured form that software can use directly?

I built Newsroom AI to experiment with those questions in an end-to-end system instead of an isolated notebook or API demo.

A central part of the project was testing **Jev by TypeSafe** as a structured decision component inside a production-style pipeline.

---

## What the MVP does

### Institutional source ingestion

The backend currently ingests data from:

- Câmara dos Deputados
- Senado Federal

Incoming stories are normalized, deduplicated and stored in PostgreSQL.

### Structured AI classification with Jev

Jev is used for decision-oriented tasks such as:

- story classification
- priority scoring
- category scoring
- candidate evaluation for thread assignment
- structured analysis of changes between related stories

The goal was to test a model designed around typed decisions and scores rather than free-form generated text.

### Semantic retrieval

Stories are embedded locally and stored with **pgvector**.

Embeddings are used to retrieve similar historical stories and help generate candidate relationships.

This project also exposed an important engineering lesson:

> semantic similarity is useful for retrieval, but it should not automatically be treated as business relevance.

That distinction became one of the main design learnings of the project.

### Thread detection

When a new story arrives, the pipeline attempts to determine whether it belongs to an existing topic or sequence of events.

The current strategy combines:

1. deterministic matching using source entity identifiers when available
2. vector similarity for candidate retrieval
3. Jev-based structured evaluation of candidate relationships

This allows the application to build timelines instead of presenting every institutional update as an isolated item.

### What Changed analysis

For stories linked to previous developments, the system evaluates signals such as:

- new information
- new actors
- new measures
- status changes
- date changes
- quantitative changes
- contradictions

Jev provides the structured decision layer, while a generative model can produce a human-readable change summary.

### Client Monitor

The project also contains an experimental client-specific monitoring layer.

A monitoring profile can:

- define topics of interest
- evaluate historical and incoming stories
- calculate relevance and urgency
- separate immediate-attention items from general follow-up
- generate digest and briefing data

Historical backfills are intentionally separated from live alert creation so old stories do not generate retroactive notifications.

The relevance layer is still experimental. One of the next architectural iterations is to use local retrieval only for candidate generation and let an AI judge perform the final client-specific relevance decision.

---

## Architecture

```mermaid
flowchart TD
    A[Câmara dos Deputados] --> I[Ingestion Pipeline]
    B[Senado Federal] --> I

    I --> D[Deduplication / Normalization]
    D --> J[Jev Classification]
    J --> P[(PostgreSQL)]

    D --> E[Local Embeddings]
    E --> V[(pgvector)]

    V --> C[Candidate Retrieval]
    C --> T[Jev Thread Decision]
    T --> TH[Story Threads]

    TH --> WC[Jev What Changed Analysis]
    WC --> G[Generative Change Summary]

    P --> M[Client Monitoring]
    TH --> M
    WC --> M

    M --> UI[Next.js Dashboard]
```

---

## Tech stack

**Backend**

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- pgvector
- APScheduler
- httpx

**AI / Data**

- Jev / TypeSafe
- sentence-transformers
- multilingual-e5-base
- OpenAI API
- vector similarity
- structured AI scoring

**Frontend**

- Next.js
- React
- TypeScript
- Tailwind CSS

**Infrastructure / Development**

- Linux / WSL
- REST APIs
- scheduled ingestion jobs
- health monitoring
- retryable delivery workflow

---

## Pipeline

A simplified ingestion cycle looks like this:

```text
Fetch official source
        ↓
Normalize story
        ↓
Deduplicate
        ↓
Jev classification
        ↓
Persist story
        ↓
Create embedding
        ↓
Find thread candidates
        ↓
Jev relationship decision
        ↓
Assign / create thread
        ↓
Analyze what changed
        ↓
Generate readable summary
        ↓
Evaluate alerts / client monitors
```

---

## Where Jev is used

The main reason for building this project was to test Jev beyond a toy example.

I used it where the application benefits from **structured decisions** rather than generated prose.

Examples include:

```text
Story
→ What category does it belong to?
→ How relevant / important is it?

New story + previous candidates
→ Do these represent the same ongoing issue?
→ Is this a continuation?
→ Do they share a specific reference?

New event + thread history
→ Is there meaningful new information?
→ Did the status change?
→ Is there a contradiction?
```

The outputs can then be consumed directly by application logic.

---

## What I learned

### 1. Retrieval and decision are different problems

High vector similarity does not necessarily mean two items are relevant to the same business question.

Embeddings work well for narrowing the search space, while a decision layer can evaluate the actual relationship.

### 2. Structured AI fits software pipelines differently from generative AI

Generative models are excellent for summaries and natural-language explanations.

Structured decision models are useful when the next step in the application depends on predictable scores or categories.

The project therefore uses different models for different responsibilities instead of trying to make one model do everything.

### 3. Real AI applications need orchestration, not just prompts

Most of the work in this project was not the API call itself.

It involved:

- ingestion
- deduplication
- database design
- vector storage
- decision thresholds
- fallbacks
- event linking
- API design
- frontend presentation
- operational monitoring

That was one of the main reasons I wanted to build an end-to-end project.

---

## Current status

This is an MVP / portfolio project, not a production SaaS.

Implemented:

- Câmara ingestion
- Senado ingestion
- PostgreSQL persistence
- pgvector embeddings
- Jev classification
- Jev thread candidate decisions
- deterministic source-entity linking
- thread timelines
- What Changed analysis
- generative change summaries
- alert engine
- monitoring profiles
- historical monitoring backfill
- dashboard and monitoring UI
- operations / health endpoints

Still experimental:

- client-specific relevance ranking
- relevance calibration across different monitoring domains
- final alert-routing strategy
- production authentication / multi-tenancy

---

## Suggested next iteration

The most important next architectural step is to separate **candidate retrieval** from **final relevance judgment**:

```text
Keyword / pgvector retrieval
          ↓
Possible candidates
          ↓
AI relevance judge
          ↓
relevance_score + explanation
          ↓
Dashboard / briefing / alert
```

This would allow a user to describe an interest in natural language, for example:

```text
Topic:
Eleições 2026

Interest:
News about Bolsonaro
```

and have the AI evaluate whether each retrieved story is actually pertinent to that specific monitoring request.

---

## Repository structure

```text
newsroom-ai/
├── backend/
│   ├── main.py
│   ├── services/
│   │   ├── ingestion.py
│   │   ├── jev.py
│   │   ├── embeddings.py
│   │   ├── generator.py
│   │   └── monitoring.py
│   └── sources/
│       ├── camara.py
│       └── senado.py
│
├── frontend/
│   └── src/
│       ├── app/
│       └── components/
│
└── README.md
```

---

## Running locally

The project currently expects a local PostgreSQL database with pgvector enabled, plus API credentials for the external AI services used by the backend. The database schema in this portfolio snapshot has not yet been consolidated into a single migration chain; see `database/README.md`.

Example environment variables:

```bash
DATABASE_URL=postgresql+psycopg://USER:PASSWORD@localhost/newsroom_ai
OPENAI_API_KEY=...
TYPESAFE_API_KEY=...
TELEGRAM_BOT_TOKEN=...
```

Before publishing or deploying, database credentials and every secret should be moved to environment variables and excluded from version control.

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

---

## Security note

No API keys, tokens, passwords or production credentials should be committed to this repository.

The public repository should contain only sample configuration such as `.env.example`.

---

## About this project

I built Newsroom AI as part of my portfolio to explore the intersection of:

- Data Engineering
- Applied AI
- Analytics
- API integration
- backend systems
- structured decision models
- LLM-based generation

My main interest is building end-to-end solutions around data: ingesting it, modeling it, automating workflows and turning it into usable products.

