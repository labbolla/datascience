# Data Science & Applied AI Portfolio

Portfolio of projects across data science, statistics, optimization, machine learning and applied AI.

I use this repository to document practical work built with Python, SQL, statistical analysis, machine learning, APIs and AI systems.

---

## Featured project

### Newsroom AI — AI-assisted institutional monitoring

`newsroom-ai/`

An end-to-end MVP for monitoring Brazilian institutional sources and turning incoming public information into structured, actionable intelligence.

The project combines:

- FastAPI backend
- PostgreSQL + pgvector
- local multilingual embeddings
- Jev / TypeSafe for structured AI decisions
- OpenAI for generative summaries
- Next.js + TypeScript frontend
- automated ingestion from Câmara dos Deputados and Senado Federal

Main capabilities include:

- ingestion and deduplication of institutional stories
- structured classification and scoring
- semantic candidate retrieval
- automatic linking of related developments into threads
- “What Changed” analysis across related events
- client monitoring profiles
- historical backfill
- operational dashboard and health endpoints

One of the main engineering lessons from this project was the distinction between **semantic similarity** and **business relevance**: embeddings are useful for retrieval, but a decision layer is better suited to judging whether a result is actually relevant to a specific monitoring objective.

➡️ See the full project: [`newsroom-ai/`](./newsroom-ai/)

---

## Machine Learning

### Hotel Booking — Logistic Regression

Files:

- [`Hotel Booking Machine Learning Log Reg.ipynb`](./Hotel%20Booking%20Machine%20Learning%20Log%20Reg.ipynb)
- [`Hotel Booking Machine Learning Log Reg.html`](./Hotel%20Booking%20Machine%20Learning%20Log%20Reg.html)

Classification project using logistic regression to model hotel booking outcomes and evaluate predictive performance.

---

### Real Estate — Linear Regression

Files:

- [`Real Estate forecast Linear Regression.ipynb`](./Real%20Estate%20forecast%20Linear%20Regression.ipynb)
- [`Real Estate Analysis Data Science Linear Reg.html`](./Real%20Estate%20Analysis%20Data%20Science%20Linear%20Reg.html)

Regression-based analysis focused on understanding and forecasting real-estate values.

---

## Statistics

### Retail Sales — ANOVA

Files:

- [`Retail sales analysis ANOVA.ipynb`](./Retail%20sales%20analysis%20ANOVA.ipynb)
- [`Retail sales categoires ANOVA Data science.html`](./Retail%20sales%20categoires%20ANOVA%20Data%20science.html)

Statistical analysis of retail-sales categories using Analysis of Variance.

---

## Optimization

### Linear Optimization

File:

- [`Plot Linear Problems Optimal solutions.ipynb`](./Plot%20Linear%20Problems%20Optimal%20solutions.ipynb)

Exploration and visualization of linear optimization problems and optimal solutions.

---

## Technologies used across the portfolio

Python · Jupyter · pandas · scikit-learn · statistical analysis · regression · classification · optimization · FastAPI · PostgreSQL · pgvector · SQL · REST APIs · Next.js · TypeScript · applied AI · LLM integration

---

## About me

I am interested in roles at the intersection of:

- Data & Analytics
- Data Engineering
- Applied AI
- Solution Engineering
- Backend / API development
- AI automation

I particularly enjoy turning data pipelines and analytical models into complete, usable products rather than stopping at isolated experiments.

