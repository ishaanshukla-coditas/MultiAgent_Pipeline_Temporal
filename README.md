# Multi-Agent Content Pipeline

A production-grade multi-agent pipeline that autonomously researches a topic, analyses competitors, and writes a full SEO-optimised article — orchestrated with [Temporal](https://temporal.io/) for durable execution and [RabbitMQ](https://www.rabbitmq.com/) for decoupled event broadcasting. Includes a React dashboard and a live demo of Temporal's activity-level fault tolerance.

## Architecture

```
Topic Input
    │
    ├──► fetch_industry_trends ──┐
    ├──► fetch_key_facts        ─┼──► aggregate_research ──► Writer Agent ──► Human Approval
    ├──► fetch_recent_news      ─┘         (1 LLM call)       (1 LLM call)    (Temporal Signal)
    │                                                               │
    └──► Competitor Agent ──────────────────────────────────────────┘
         (Tavily + Groq)                        │
                                                │ on article ready / approved / rejected
                                                ▼
                                          RabbitMQ Exchange
                                                │
                                    ┌───────────┴───────────┐
                                    ▼                       ▼
                             Email Consumer          Slack Consumer
                          (article.ready)      (article.approved/rejected)
```

### Why Temporal + RabbitMQ — not one or the other

| Concern | Tool | Why |
|---|---|---|
| Run steps in order | Temporal | Tracks dependencies, retries failures |
| Wait 48 hrs for human approval | Temporal | Only Temporal can pause a workflow |
| Retry a failed activity | Temporal | Built-in retry policies with backoff |
| Notify editor when article is ready | RabbitMQ | Fire-and-forget, decoupled from pipeline |
| Add a new Slack/CMS consumer tomorrow | RabbitMQ | New consumer file — workflow never changes |
| Isolate notification failures from pipeline | RabbitMQ | Consumer crash doesn't affect orchestration |

## Agents

| Agent | Role |
|---|---|
| **fetch_industry_trends** | Tavily search — market trends and industry direction |
| **fetch_key_facts** | Tavily search — statistics, data, hard facts |
| **fetch_recent_news** | Tavily search — latest news and developments |
| **aggregate_research** | Merges 3 search result sets into a `ResearchBrief` via one Groq call |
| **Competitor Agent** | Finds competing content, identifies gaps and opportunities via Groq |
| **Writer Agent** | Generates SEO keyword strategy + full article in a single Groq call |
| **publish_pipeline_event** | Temporal activity that fires events into RabbitMQ |

The 3 research fetches and the Competitor Agent all run **in parallel** (4 concurrent activities). Once complete, `aggregate_research` runs, then the Writer. The workflow then publishes an `article.ready` event to RabbitMQ before pausing for human approval.

## Task Queue Architecture

Each worker type runs on its own dedicated Temporal task queue, enabling independent scaling:

```
orchestrator-queue   →  worker-orchestrator    (ContentPipelineWorkflow)
research-queue       →  worker-research        (fetch_industry_trends, fetch_key_facts,
                                                fetch_recent_news, aggregate_research)
competitor-queue     →  worker-competitor      (run_competitor_agent)
writer-queue         →  worker-writer          (run_writer_agent)
notification-queue   →  worker-notification    (publish_pipeline_event → RabbitMQ)
```

Scale any bottleneck independently:
```bash
docker compose up --scale worker-research=3 --scale worker-writer=2
```

## Tech Stack

| Layer | Technology |
|---|---|
| Workflow orchestration | [Temporal](https://temporal.io/) |
| Event broadcasting | [RabbitMQ](https://www.rabbitmq.com/) via [aio-pika](https://aio-pika.readthedocs.io/) |
| LLM inference | [Groq API](https://console.groq.com/) — `llama-3.3-70b-versatile` |
| Web search | [Tavily](https://tavily.com/) |
| Backend API | [FastAPI](https://fastapi.tiangolo.com/) + SQLAlchemy + PostgreSQL |
| Frontend | React + Vite + Tailwind CSS |
| Containerisation | Docker Compose |
| Python package manager | [uv](https://docs.astral.sh/uv/) |

## Prerequisites

- [Docker Desktop](https://www.docker.com/products/docker-desktop/)
- A free [Groq API key](https://console.groq.com/)
- A free [Tavily API key](https://app.tavily.com/)

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

Edit `.env` and fill in your keys:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=llama-3.3-70b-versatile
TAVILY_API_KEY=your_tavily_api_key_here
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
| RabbitMQ UI | http://localhost:15672 (guest / guest) |
| PostgreSQL | localhost:5433 |

## Running a Pipeline

1. Open **http://localhost:5173**
2. Enter a topic (e.g. `"AI Agents in production 2026"`)
3. Click **Start Pipeline**
4. Watch agents progress in real time on the pipeline detail view
5. Once writing completes, the article appears for review
6. Click **Approve & Publish** or **Reject & Request Revision**

After each key event, the `notification-consumer` logs what it received from RabbitMQ:
```
📧  EMAIL  → 'Your Title' is ready for review
✅  SLACK  → 'Your Title' approved and published!
❌  SLACK  → 'Your Title' was rejected. Feedback: ...
```

Watch it live:
```bash
docker compose logs -f notification-consumer
```

## RabbitMQ Event Flow

The workflow publishes three events over its lifetime:

| Event | When | Routing Key |
|---|---|---|
| `article.ready` | After Writer Agent completes | `article.ready` |
| `article.approved` | After human approves | `article.approved` |
| `article.rejected` | After human rejects | `article.rejected` |

All events go through the `pipeline_events` topic exchange. The `notification-consumer` subscribes to `article.*` and handles all three. To add a new consumer (e.g. a CMS publisher), create a new script that binds to the same exchange — no changes to the workflow needed.

## Simulate Writer Failure (Temporal Durability Demo)

Toggle **"Simulate writer failure"** in the new pipeline form before submitting.

**What happens:**
- Research fetches ✅ complete → results cached in Temporal event history
- Competitor Agent ✅ completes → result cached in Temporal event history
- aggregate_research ✅ completes → ResearchBrief cached in event history
- Writer Agent ❌ fails on attempt 1 (artificial error)
- Temporal automatically retries **only the Writer Agent** — all prior activities are **not re-run**
- Writer Agent ✅ succeeds on attempt 2

**What you see in Temporal UI (`http://localhost:8233`):**
- Activities `fetch_industry_trends`, `fetch_key_facts`, `fetch_recent_news` — Completed
- Activity `run_competitor_agent` — Completed
- Activity `run_writer_agent` — Failed (attempt 1), Completed (attempt 2)

## Rate Limit Handling

| Retry-After | Behaviour |
|---|---|
| ≤ 60s (per-minute limit) | Activity sleeps inside Temporal with heartbeats, retries the HTTP call silently |
| > 60s (quota exhaustion) | Activity fails fast; Temporal retries with exponential backoff (30s → 60s → 120s → 240s) |

## Project Structure

```
├── agents/
│   ├── llm_client.py           # Groq API wrapper with 429 handling + in-memory cache
│   ├── research_agent.py       # 3 parallel Tavily fetches + LLM aggregation
│   ├── competitor_agent.py     # Competitor content gap analysis (Tavily + Groq)
│   ├── writer_agent.py         # SEO strategy + article writing (1 LLM call)
│   └── event_publisher.py      # Temporal activity: publishes events to RabbitMQ
├── workflows/
│   └── content_pipeline.py     # Temporal workflow — orchestrates all agents + RabbitMQ handoff
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
│       │   ├── Dashboard.jsx       # Pipeline list + new pipeline form
│       │   └── PipelineDetail.jsx  # Agent progress + article + approval
│       ├── components/
│       │   ├── AgentProgress.jsx   # Step-by-step agent status
│       │   ├── PipelineCard.jsx    # Dashboard pipeline card
│       │   └── StatusBadge.jsx     # Status pill component
│       └── api/
│           └── pipelines.js        # Axios API client
├── docker/
│   ├── Dockerfile.backend      # Python backend + worker image
│   ├── Dockerfile.frontend     # Node/Vite frontend image
│   └── init-db.sql             # Creates the content_pipeline database
├── notification_consumer.py    # Standalone RabbitMQ consumer (email/Slack simulation)
├── queues.py                   # Task queue name constants
├── worker.py                   # Temporal worker — role selected via WORKER_ROLE env var
├── docker-compose.yml          # Full stack: db, temporal, rabbitmq, backend, workers, frontend
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
| `running_research_and_competitor` | 4 activities running in parallel |
| `writing_article` | Writer Agent generating article |
| `waiting_for_approval` | Article ready, `article.ready` event fired to RabbitMQ |
| `completed` | Article approved, `article.approved` event fired to RabbitMQ |
| `rejected` | Article rejected, `article.rejected` event fired to RabbitMQ |
| `failed` | Workflow failed (retries exhausted) — see Temporal UI for trace |

## Stopping the App

```bash
docker compose down
```

To also remove the PostgreSQL data volume (full reset):
```bash
docker compose down -v
```
