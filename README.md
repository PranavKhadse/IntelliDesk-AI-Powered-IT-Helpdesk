# IntelliDesk — AI-Powered Enterprise IT Service Desk

> A modern, full-stack IT service management platform featuring intelligent ticket triage, verified Knowledge Base grounding, multi-tier SLA policy engines, advisory escalation intelligence, and real-time operations analytics.

---

## 📑 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
  - [Prerequisites](#prerequisites)
  - [Backend Setup](#backend-setup)
  - [Database Setup & Seeding](#database-setup--seeding)
  - [Frontend Setup](#frontend-setup)
- [Demo Credentials & Role Matrix](#-demo-credentials--role-matrix)
- [REST API Reference](#-rest-api-reference)
- [AI Safety, Privacy & Advisory Controls](#-ai-safety-privacy--advisory-controls)
- [Testing & Quality Assurance](#-testing--quality-assurance)

---

## 🌟 Overview

**IntelliDesk** is an enterprise-grade IT Helpdesk & Service Desk application designed to streamline IT support operations. It combines deterministic business logic with transparent, advisory AI workflows:

1. **Deterministic Core**: Rock-solid RBAC authorization, full audit event logging, hierarchical SLA calculation matrices, and database-backed workload aggregations.
2. **Advisory AI Intelligence**: Zero unapproved mutations. All AI capabilities (triage suggestions, response drafts, ticket summaries, KB grounding, and SLA breach risks) operate in a read-only advisory mode and require explicit staff approval before applying changes.
3. **Security & Privacy First**: Automated secret and credential sanitization, complete exclusion of internal staff notes from AI context, and strict isolation between end-user and staff capabilities.

---

## 🚀 Key Features

### 1. IT Ticket & Lifecycle Management
- **Full Ticket Lifecycle**: `open` ➔ `in_progress` ➔ `pending_customer` ➔ `resolved` ➔ `closed`.
- **Threaded Communication**: Public comments for customer communication and private `INTERNAL_NOTE` entries visible only to staff.
- **Audit Trails**: Immutable log records (`audit_logs`) tracking ticket creation, status changes, priority shifts, assignments, and AI decisions.

### 2. Role-Based Access Control (RBAC)
- **`ADMIN`**: Full platform oversight, SLA policy management, staff management, executive analytics, and ticket triaging.
- **`AGENT`**: Ticket investigation, triage acceptance, customer response generation, KB article authoring, and team analytics.
- **`USER`**: Scoped self-service portal (viewing/creating own tickets, viewing public comments, reading published KB articles).

### 3. AI Ticket Triage & Routing
- Analyzes ticket title and description to recommend optimal **Category**, **Priority**, and **Assigned Team** with calibrated confidence scores and reasoning.
- Generates cryptographic state fingerprints to prevent duplicate, stale, or conflicting approvals.

### 4. AI Customer Response Assistant & Summaries
- **Response Drafter**: Crafts empathetic, professional responses tailored to the issue, adhering to IT service standards.
- **Ticket Summarization**: Extracts executive summaries, key technical findings, and concrete pending action items for long ticket threads.

### 5. Knowledge Base & Grounded AI Recommendations
- Article authoring, tag management, view tracking, and helpfulness voting.
- **AI Grounding**: Retrieves verified, published KB articles and synthesizes step-by-step troubleshooting recommendations citing exact source articles.

### 6. SLA Policy Engine & Escalation Intelligence
- **Hierarchical Policy Resolution**: `(Category, Priority)` ➔ `Priority` ➔ `Category` ➔ Default SLA Matrix.
- **Real-Time SLA Tracking**: Tracks elapsed time, remaining targets, warning thresholds, first-response compliance, and SLA states (`ON_TRACK`, `AT_RISK`, `BREACHED`, `PAUSED`, `RESOLVED_MET`, `RESOLVED_BREACHED`).
- **AI SLA Risk Analysis**: Detects breach probability, calculates predicted time-to-breach, highlights risk factors, and proposes human-in-the-loop escalation decisions.

### 7. Operations & Management Analytics
- **Executive KPI Ribbon**: Total volume, active backlog, SLA compliance rate, avg first-response hours, avg resolution hours, and AI acceptance rate.
- **Visual Trends & Breakdowns**: Daily throughput timeline (created vs. resolved), multi-segment SLA health meters, category/priority distributions, and Agent Workload Leaderboards.
- **Time Filtering**: Quick-select presets (`7d`, `30d`, `90d`, `all`) with deterministic, timezone-aware database aggregations.

---

## 🏗 System Architecture

                         ┌─────────────────────────────┐
                         │            USERS            │
                         │                             │
                         │  Customer   Agent   Admin   │
                         └──────────────┬──────────────┘
                                        │
                                        ▼
              ┌──────────────────────────────────────────┐
              │              PRESENTATION LAYER          │
              │                                          │
              │        React + TypeScript + Vite         │
              │                                          │
              │  Login │ Dashboard │ Tickets │ KB       │
              │  AI Assistant │ SLA │ Analytics          │
              └────────────────────┬─────────────────────┘
                                   │
                                   │ HTTPS / REST API
                                   ▼
              ┌──────────────────────────────────────────┐
              │                 API LAYER                │
              │                                          │
              │                  FastAPI                 │
              │                                          │
              │  Authentication │ Users │ Tickets       │
              │  Comments │ Knowledge Base │ SLA        │
              │  AI │ Analytics                             │
              └────────────────────┬─────────────────────┘
                                   │
                                   ▼
              ┌──────────────────────────────────────────┐
              │            SECURITY & ACCESS             │
              │                                          │
              │       JWT Authentication                 │
              │       Role-Based Access Control           │
              │                                          │
              │     USER │ AGENT │ ADMIN                 │
              └────────────────────┬─────────────────────┘
                                   │
                                   ▼
        ┌────────────────────────────────────────────────────────┐
        │                  APPLICATION LAYER                      │
        │                                                        │
        │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
        │  │ Ticket       │  │ Knowledge    │  │ SLA &       │ │
        │  │ Management   │  │ Base        │  │ Escalation  │ │
        │  └──────────────┘  └──────────────┘  └─────────────┘ │
        │                                                        │
        │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐ │
        │  │ AI           │  │ Audit        │  │ Operations  │ │
        │  │ Intelligence │  │ Logging      │  │ Analytics   │ │
        │  └──────────────┘  └──────────────┘  └─────────────┘ │
        └────────────────────────┬───────────────────────────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  │                             │
                  ▼                             ▼
      ┌────────────────────────┐    ┌────────────────────────┐
      │     AI INTELLIGENCE    │    │    KNOWLEDGE / SLA     │
      │                        │    │                        │
      │ • AI Triage            │    │ • KB Search             │
      │ • AI Summary           │    │ • AI Grounding          │
      │ • Response Draft       │    │ • SLA Policy Engine     │
      │ • SLA Risk Analysis    │    │ • Escalation Engine     │
      │                        │    │ • Human Approval        │
      └────────────┬───────────┘    └────────────┬───────────┘
                   │                             │
                   ▼                             │
          ┌───────────────────┐                  │
          │   EXTERNAL LLM    │                  │
          │   AI PROVIDER      │                  │
          └───────────────────┘                  │
                                                 │
                         ┌───────────────────────┘
                         │
                         ▼
              ┌──────────────────────────────────┐
              │             DATA LAYER            │
              │                                  │
              │        SQLAlchemy ORM            │
              │              │                   │
              │              ▼                   │
              │      Relational Database         │
              │                                  │
              │  Users │ Tickets │ Comments      │
              │  KB │ SLA Policies │ Audit Logs  │
              └────────────────┬─────────────────┘
                               │
                 ┌─────────────┴─────────────┐
                 ▼                           ▼
        ┌──────────────────┐       ┌──────────────────┐
        │ Alembic          │       │ Seed Data        │
        │ Migrations       │       │ Development Data │
        └──────────────────┘       └──────────────────┘

## 🛠 Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11+)
- **ORM & Database**: SQLAlchemy 2.0, PostgreSQL, psycopg2-binary
- **Schema & Validation**: Pydantic v2, Pydantic Settings
- **Authentication**: JWT (python-jose), Passlib (bcrypt)
- **Database Migrations**: Alembic
- **Testing**: Pytest, Pytest-Asyncio, HTTPX

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite v8
- **Routing**: React Router v6
- **HTTP Client**: Axios with interceptors
- **Icons**: Lucide React
- **Styling**: Vanilla CSS Design Tokens (Dark Glassmorphism UI)

---

## 📁 Project Structure

```
IntelliDesk/
├── backend/
│   ├── alembic/                    # Database migration scripts & env.py
│   ├── app/
│   │   ├── api/v1/                 # REST API Routers (auth, tickets, kb, sla, analytics, users)
│   │   ├── core/                   # Config, DB connection, JWT security, exceptions, dependencies
│   │   ├── models/                 # SQLAlchemy ORM Models (User, Ticket, Comment, Audit, KB, SLA)
│   │   ├── schemas/                # Typed Pydantic Request/Response DTOs
│   │   ├── services/               # Core Business Logic & AI Engines
│   │   └── main.py                 # FastAPI Application Factory & Exception Handlers
│   ├── scripts/
│   │   └── seed_data.py            # Complete Idempotent Database Seeding Script
│   ├── tests/                      # 13 Test Suites (113 automated unit & integration tests)
│   ├── .env.example                # Backend environment variable template
│   └── requirements.txt            # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/             # AppLayout, ProtectedRoute, PublicOnlyRoute
│   │   ├── context/                # AuthContext & Session Management
│   │   ├── pages/                  # Dashboard, TicketDetail, CreateTicket, KB, Analytics, Auth
│   │   ├── services/               # API clients (apiClient, ticketService, kbService, slaService, analyticsService)
│   │   ├── styles/                 # Global Design System & Component CSS (index.css)
│   │   ├── types/                  # Shared TypeScript Interfaces
│   │   └── App.tsx                 # Client Routing & Shell
│   ├── .env.example                # Frontend environment variable template
│   ├── package.json                # NPM dependencies & scripts
│   └── vite.config.ts              # Vite configuration & proxy settings
└── README.md                       # Project Documentation
```

---

## ⚡ Getting Started

### Prerequisites
- **Python**: `3.11+`
- **Node.js**: `18.0+` & `npm`
- **PostgreSQL**: Running instance with a database named `intellidesk_db`

---

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Windows
   python -m venv .venv
   .venv\Scripts\activate

   # Linux / macOS
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. Install required Python packages:
   ```bash
   pip install -r requirements.txt
   ```

4. Create your local environment configuration:
   ```bash
   # Copy the template
   cp .env.example .env
   ```
   *Verify your `DATABASE_URL` in `backend/.env` (e.g., `postgresql+psycopg2://postgres:password@localhost:5432/intellidesk_db`).*

---

### Database Setup & Seeding

1. Run Alembic migrations to create all database tables:
   ```bash
   alembic upgrade head
   ```

2. Seed the database with sample IT categories, users, tickets, comments, audit logs, KB articles, and SLA policies:
   ```bash
   python scripts/seed_data.py
   ```

3. Start the FastAPI development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```
   *The API documentation is accessible at `http://localhost:8000/docs`.*

---

### Frontend Setup

1. Open a new terminal and navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install Node dependencies:
   ```bash
   npm install
   ```

3. Start the Vite development server:
   ```bash
   npm run dev
   ```
   *Open `http://localhost:5173` in your browser.*

---

## 👥 Demo Credentials & Role Matrix

The `seed_data.py` script provisions the following accounts:

| Role | Name | Email | Password | Department | Permissions |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **ADMIN** | Alex Vance | `admin@intellidesk.com` | `AdminPass123!` | IT Operations | Full system management, SLA policy CRUD, Operations Analytics, AI triage approval |
| **AGENT** | Sarah Chen | `sarah.chen@intellidesk.com` | `AgentPass123!` | Tier 2 Support | Ticket resolution, AI triage/risk review, KB authoring, Team Analytics |
| **AGENT** | Marcus Brooks | `marcus.brooks@intellidesk.com` | `AgentPass123!` | Network Operations | Ticket resolution, AI response drafting, internal notes, Team Analytics |
| **USER** | John Doe | `john.doe@company.com` | `UserPass123!` | Finance | Create tickets, view own tickets, add public comments, browse published KB |
| **USER** | Emily Smith | `emily.smith@company.com` | `UserPass123!` | Engineering | Create tickets, view own tickets, add public comments, browse published KB |

---

## 📡 REST API Reference

### Authentication (`/api/v1/auth`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `POST` | `/api/v1/auth/register` | Public | Register a new user account |
| `POST` | `/api/v1/auth/login` | Public | Authenticate user & receive Access and Refresh tokens |
| `POST` | `/api/v1/auth/refresh` | Public | Exchange valid Refresh token for new Access token |
| `GET` | `/api/v1/auth/me` | Authenticated | Retrieve authenticated user profile |

### Tickets & AI Features (`/api/v1/tickets`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/tickets` | Authenticated | List tickets (filtered by role scope, status, priority, category) |
| `POST` | `/api/v1/tickets` | Authenticated | Create a new support ticket |
| `GET` | `/api/v1/tickets/{id}` | Authenticated | Get ticket details with comments and audit logs |
| `PATCH` | `/api/v1/tickets/{id}` | Staff / Owner | Update ticket status, priority, category, or assignee |
| `POST` | `/api/v1/tickets/{id}/comments` | Authenticated | Add public comment or internal staff note |
| `GET` | `/api/v1/tickets/{id}/sla` | Authenticated | Get real-time SLA metrics, state, and remaining target time |
| `POST` | `/api/v1/tickets/{id}/ai-triage` | Staff / Owner | Generate AI triage recommendation (Category, Priority, Team) |
| `POST` | `/api/v1/tickets/{id}/ai-triage/approve`| Staff Only | Human approval applying AI recommendation |
| `POST` | `/api/v1/tickets/{id}/ai-triage/reject` | Staff Only | Human rejection of AI recommendation |
| `POST` | `/api/v1/tickets/{id}/ai-response-draft`| Staff Only | Generate customer response draft |
| `POST` | `/api/v1/tickets/{id}/ai-summary` | Staff Only | Extract structured summary and action items |
| `POST` | `/api/v1/tickets/{id}/ai-grounding` | Staff Only | Generate KB-grounded recommendation with source citations |
| `POST` | `/api/v1/tickets/{id}/ai-sla-risk` | Staff Only | Assess SLA breach probability and escalation urgency |
| `POST` | `/api/v1/tickets/{id}/ai-sla-risk/approve`| Staff Only | Human approval of AI escalation (updates ticket priority) |
| `POST` | `/api/v1/tickets/{id}/ai-sla-risk/reject` | Staff Only | Human rejection of AI escalation proposal |

### Knowledge Base (`/api/v1/kb`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/kb/articles` | Authenticated | List articles (published only for users; drafts included for staff) |
| `POST` | `/api/v1/kb/articles` | Staff Only | Author a new Knowledge Base article |
| `GET` | `/api/v1/kb/articles/{id_or_slug}`| Authenticated | Retrieve article details |
| `PUT` | `/api/v1/kb/articles/{id}` | Staff Only | Update article content, tags, category, or publish state |
| `DELETE`| `/api/v1/kb/articles/{id}` | Admin Only | Delete a knowledge base article |
| `POST` | `/api/v1/kb/articles/{id}/helpful`| Authenticated | Cast a helpfulness vote |
| `GET` | `/api/v1/kb/search` | Authenticated | Relevance-scored keyword search across published articles |

### SLA Policy Engine (`/api/v1/sla`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/sla/policies` | Staff Only | List active and configured SLA policies |
| `POST` | `/api/v1/sla/policies` | Admin Only | Create custom SLA policy |
| `GET` | `/api/v1/sla/policies/{id}` | Staff Only | Get SLA policy details |
| `PUT` | `/api/v1/sla/policies/{id}` | Admin Only | Update SLA target hours or thresholds |
| `DELETE`| `/api/v1/sla/policies/{id}` | Admin Only | Delete SLA policy |

### Operations Analytics (`/api/v1/analytics`)
| Method | Endpoint | Access | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/v1/analytics/dashboard` | Staff Only | Consolidated operations analytics dashboard |
| `GET` | `/api/v1/analytics/sla` | Staff Only | Dedicated SLA compliance and breach rate report |
| `GET` | `/api/v1/analytics/workload` | Staff Only | Support team & agent workload leaderboard |

---

## 🔒 AI Safety, Privacy & Advisory Controls

IntelliDesk enforces strict safeguards across all AI interactions:

1. **Secret & Credential Masking**:
   - Automated regex scrubbing sanitizes bearer tokens, API keys, passwords, private keys, and authorization headers from all ticket content before forwarding to language models.
2. **Internal Note Exclusion**:
   - Private `INTERNAL_NOTE` comments are strictly stripped from all AI prompts (`grounding`, `summary`, `response_draft`, `sla_risk`).
3. **Verified Knowledge Grounding**:
   - AI suggestions are strictly grounded in published (`is_published == True`) articles. No procedural hallucinations.
4. **Human-in-the-Loop & Immutability**:
   - AI services never mutate database records directly.
   - All AI triage and escalation proposals require an explicit human decision (`approve`/`reject`), logged immutably in `audit_logs`.
   - Cryptographic fingerprints ensure stale or duplicate decisions cannot overwrite concurrent human edits.

---

## 🧪 Testing & Quality Assurance

IntelliDesk maintains a comprehensive test suite across the backend and frontend:

### Running Backend Pytest Suites
```bash
cd backend
.venv\Scripts\pytest.exe -v
```
**Test Coverage (113/113 Passed - 100%)**:
- `test_auth.py`: Registration, login, token decode, refresh rotation, RBAC dependencies.
- `test_tickets.py`: CRUD, role scoping, status transitions, threaded comments, internal notes.
- `test_ticket_triage.py`: AI triage generation, approval, rejection, state fingerprints, duplicate prevention.
- `test_response_draft.py`: Customer response generation, secret sanitization, internal note exclusion.
- `test_ticket_summary.py`: Summary extraction, key findings, action items, ticket immutability.
- `test_kb.py`: Article CRUD, draft visibility, slug collision resolution, helpful voting, search scoring.
- `test_ai_grounding.py`: KB grounding, source attribution, zero-mutation guarantee, fallback handling.
- `test_sla.py`: Policy matching hierarchy, target calculations, first-response metrics, SLA state transitions.
- `test_ai_sla_risk.py`: SLA breach risk prediction, escalation urgency, staff review approval/rejection.
- `test_analytics.py`: Date parsing, volume counts, SLA distributions, agent workloads, AI adoption metrics.
- `test_ai_service.py`: Provider health, timeouts, safe fallbacks, error handling.

### Running Frontend Production Build
```bash
cd frontend
cmd.exe /c "npm run build"
```
*Validates zero TypeScript errors, clean bundle compilation, and minification in <1 second.*

---

## 📄 License
This project is developed for educational and enterprise IT service management demonstration purposes. All rights reserved.
