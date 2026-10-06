# GitHub publication checklist — Newsroom AI

Use this before making the repository public.

## Secrets and credentials

- Remove hard-coded database usernames/passwords from source code.
- Move database connection data to `DATABASE_URL`.
- Confirm `OPENAI_API_KEY` is never committed.
- Confirm `JEV_API_KEY` is never committed.
- Confirm `TELEGRAM_BOT_TOKEN` is never committed.
- Search the entire Git history for old credentials, not only the latest files.
- If a real credential was ever committed, rotate it before publishing.

## Files that should not be committed

Add or verify these patterns in `.gitignore`:

```gitignore
.env
.env.*
!.env.example

.venv/
venv/
__pycache__/
*.pyc

node_modules/
.next/
dist/
build/

*.log
.DS_Store
.vscode/
.idea/
```

## Repository cleanup

- Keep one current version of each source file.
- Remove temporary files such as `main(1).py`, `main(2).py`, experimental copies and generated patch files.
- Remove test dumps, raw API responses and temporary JSON files.
- Remove local database exports unless deliberately sanitized.
- Remove personal paths and machine-specific configuration.
- Keep migrations in a dedicated folder if they are required to reproduce the database.

## README evidence

Before publishing screenshots or claims, make sure the repository visibly supports them.

Useful screenshots:

1. Client dashboard.
2. Acompanhamento / thread timeline.
3. Story detail with “What Changed”.
4. Monitoring profile.
5. Optional FastAPI `/docs` screenshot showing the API surface.

Do not include screenshots containing API keys, Telegram IDs, personal identifiers or private data.

## Suggested repository name

`newsroom-ai`

Suggested GitHub description:

> AI-assisted institutional monitoring MVP using FastAPI, PostgreSQL/pgvector, Jev structured decisions and Next.js.

## Suggested repository topics

`python`, `fastapi`, `postgresql`, `pgvector`, `nextjs`, `typescript`, `applied-ai`, `data-engineering`, `llm`, `semantic-search`

## Final quality check

A recruiter should be able to understand these points within 30–60 seconds:

- what problem the project explores;
- what you personally built;
- where Jev is used;
- why pgvector is used;
- why generative AI and structured decision AI have different responsibilities;
- what is implemented versus experimental;
- how the architecture fits together.
