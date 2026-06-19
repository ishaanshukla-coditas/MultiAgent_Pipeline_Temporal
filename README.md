# Multi-Agent Content Pipeline

A production-grade multi-agent pipeline that autonomously researches a topic, analyses competitors, and writes a full SEO-optimised article — orchestrated with [Temporal](https://temporal.io/) for durable execution and human-in-the-loop approval. Includes a React dashboard and a live demo of Temporal's activity-level fault tolerance.

## Architecture

```
Topic Input
    │
    ├──► Research Agent  ──┐
    │    (DuckDuckGo +     │  parallel
    │     Groq LLM)        │
    │                      ▼
    └──► Competitor Agent ──► Writer Agent ──► Human Approval
         (DuckDuckGo +        (SEO strategy       (Temporal Signal
          Groq LLM)            + full article,      via React UI)
                               1 LLM call)
```

| Agent | Role |
|---|---|
| **Research Agent** | Searches DuckDuckGo, summarises key facts and trends via Groq |
| **Competitor Agent** | Finds competing content, identifies gaps and opportunities via Groq |
| **Writer Agent** | Generates SEO keyword strategy + full article in a single Groq call |

Research and Competitor agents run **in parallel**. Writer runs after both complete. The workflow pauses for human approval (approve or reject with feedback) before completing.

## Tech Stack

| Layer | Technology |
|---|---|
| Workflow orchestration | [Temporal](https://temporal.io/) |
| LLM inference | [Groq API](https://console.groq.com/) — `llama-3.3-70b-versatile` |
| Web search | [DuckDuckGo Search](https://pypi.org/project/duckduckgo-search/) |
| Backend API | [FastAPI](https://fastapi.tiangolo.com/) + SQLAlchemy + PostgreSQL |
| Frontend | React + Vite + Tailwind CSS |
| Containerisation | Docker Compose |
| Python package manager | [uv](https://docs.astral.sh/uv/) |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (includes Docker Compose)
- A free [Groq API key](https://console.groq.com/) — sign up at console.groq.com

That's it. Everything else runs inside Docker.

## Quick Start

**1. Clone the repo**
```bash
git clone https://github.com/ishaanshukla-coditas/MultiAgent_Pipeline_Temporal.git
cd MultiAgent_Pipeline_Temporal
```

**2. Create your `.env` file**
```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
```

**3. Start everything**
```bash
docker compose up --build
```

First run takes ~2 minutes to pull images and build. Subsequent starts are fast.

**4. Open the app**

| Service | URL |
|---|---|
| React Dashboard | http://localhost:5173 |
| FastAPI Backend | http://localhost:8080/docs |
| Temporal UI | http://localhost:8233 |
| PostgreSQL | localhost:5433 |

## Running a Pipeline

1. Open **http://localhost:5173**
2. Enter a topic in the sidebar (e.g. `"AI Agents in production 2026"`)
3. Click **Start Pipeline**
4. Click the pipeline card to open the detail view and watch agents progress in real time
5. Once the Writer Agent completes, the article appears for review
6. Click **Approve & Publish** or **Reject & Request Revision** (with feedback)

## Simulate Writer Failure (Temporal Durability Demo)

Toggle **"Simulate writer failure"** in the new pipeline form before submitting.

**What happens:**
- Research Agent ✅ completes → result cached in Temporal event history
- Competitor Agent ✅ completes → result cached in Temporal event history
- Writer Agent ❌ fails on attempt 1 (artificial error)
- Temporal automatically retries **only the Writer Agent** — Research and Competitor are **not re-run**; their results are served from the event history
- Writer Agent ✅ succeeds on attempt 2

**What you see in the UI:**
- Research and Competitor steps show green **"done"** + a **"cached"** pill
- Writer step shows amber spinner with **"retrying"** badge
- An info banner explains what Temporal is doing and why

**What you see in Temporal UI (`http://localhost:8233`):**
- Activity 1 (`run_research_agent`) — Completed
- Activity 2 (`run_competitor_agent`) — Completed
- Activity 3 (`run_writer_agent`) — Failed (attempt 1), Completed (attempt 2)

This demonstrates Temporal's core durability guarantee: completed work is never repeated, even across failures and worker restarts.

## Rate Limit Handling

Groq enforces per-minute and daily token quotas.

| Retry-After | Behaviour |
|---|---|
| ≤ 60s (per-minute limit) | Activity sleeps inside Temporal with heartbeats, retries the HTTP call silently |
| > 60s (quota exhaustion) | Activity fails fast with a clear error; Temporal retries with exponential backoff (30s → 60s → 120s → 240s) |

If you see `Groq quota exhausted: Retry-After=Xs` in the Temporal UI, your daily quota is exhausted. Check [console.groq.com](https://console.groq.com) and wait for the quota to reset (usually top of the hour or midnight UTC).

## Project Structure

```
├── agents/
│   ├── llm_client.py           # Groq API wrapper with 429 handling + in-memory cache
│   ├── research_agent.py       # DuckDuckGo search + Groq summarisation
│   ├── competitor_agent.py     # Competitor content gap analysis
│   └── writer_agent.py         # SEO strategy + article writing (1 LLM call)
├── workflows/
│   └── content_pipeline.py     # Temporal workflow — orchestrates all agents
├── backend/
│   ├── main.py                 # FastAPI app entrypoint
│   ├── models.py               # SQLAlchemy models
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── routers/
│   │   ├── pipelines.py        # Pipeline CRUD + signal endpoints
│   │   └── health.py           # Health check
│   └── services/
│       ├── pipeline_service.py # Business logic + Temporal status sync
│       └── temporal_service.py # Temporal client wrapper
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx   # Pipeline list + new pipeline form
│       │   └── PipelineDetail.jsx  # Agent progress + article + approval
│       ├── components/
│       │   ├── AgentProgress.jsx   # Step-by-step agent status (incl. retrying/failed)
│       │   ├── PipelineCard.jsx    # Dashboard pipeline card
│       │   └── StatusBadge.jsx     # Status pill component
│       └── api/
│           └── pipelines.js    # Axios API client
├── docker/
│   ├── Dockerfile.backend      # Python backend + worker image
│   ├── Dockerfile.frontend     # Node/Vite frontend image
│   └── init-db.sql             # Creates the content_pipeline database
├── worker.py                   # Temporal worker entrypoint
├── docker-compose.yml          # Full stack: db, temporal, backend, worker, frontend
└── pyproject.toml
```

## Workflow Signals & Queries

| Signal | Description |
|---|---|
| `approve_article` | Marks the article as approved and completes the workflow |
| `reject_article(feedback: str)` | Sends the article back with revision feedback |

| Query | Description |
|---|---|
| `get_status` | Returns the current pipeline stage |
| `get_article` | Returns the generated article (title, content, meta description, word count) |

## Pipeline Statuses

| Status | Meaning |
|---|---|
| `started` | Workflow created, about to begin |
| `running_research_and_competitor` | Research + Competitor agents running in parallel |
| `writing_article` | Writer Agent generating SEO strategy + article |
| `waiting_for_approval` | Article ready, awaiting human decision |
| `completed` | Article approved |
| `rejected` | Article rejected with feedback |
| `failed` | Workflow failed (retries exhausted) — see Temporal UI for trace |

## Stopping the App

```bash
docker compose down
```

To also remove the PostgreSQL data volume (full reset):
```bash
docker compose down -v
```
