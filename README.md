# UniMind AI with AegisOps Platform

> **Autonomous University Operations, Grounded Student Support RAG AI & Predictive AIOps Self-Healing Engine**

---

## 📌 Table of Contents
1. [Executive Summary & Platform Architecture](#-executive-summary--platform-architecture)
2. [Quick Start & How to Run](#-quick-start--how-to-run)
3. [Global Navigation & Header Controls](#-global-navigation--header-controls)
4. [Sidebar Navigation: Complete Button & Feature Guide](#-sidebar-navigation-complete-button--feature-guide)
   - [Special Action Button: Run AegisOps Demo](#-special-action-button-run-aegisops-demo)
   - [Section 1: UNIMIND AI Suite](#section-1-unimind-ai-suite)
     - [1. Dashboard](#1-dashboard)
     - [2. Student Assistant](#2-student-assistant)
     - [3. Knowledge Base](#3-knowledge-base)
     - [4. Documents](#4-documents)
     - [5. RAG Management](#5-rag-management)
     - [6. Tickets & Incidents](#6-tickets--incidents)
   - [Section 2: AEGISOPS Autonomous Fleet Suite](#section-2-aegisops-autonomous-fleet-suite)
     - [7. AegisOps Overview](#7-aegisops-overview)
     - [8. Services](#8-services)
     - [9. Monitoring](#9-monitoring)
     - [10. Metrics](#10-metrics)
     - [11. Logs (Loki)](#11-logs-loki)
     - [12. ML Anomaly Detection](#12-ml-anomaly-detection)
     - [13. Incidents](#13-incidents)
     - [14. AI Diagnosis](#14-ai-diagnosis)
     - [15. Remediation](#15-remediation)
     - [16. Kubernetes](#16-kubernetes)
5. [End-to-End Self-Healing Incident Walkthrough](#-end-to-end-self-healing-incident-walkthrough)
6. [Backend API Endpoint Mapping](#-backend-api-endpoint-mapping)
7. [Technology Stack & System Requirements](#-technology-stack--system-requirements)

---

## 🏛️ Executive Summary & Platform Architecture

**UniMind AI with AegisOps** is a dual-engine enterprise platform engineered for university campuses:

1. **UniMind AI**: A grounded, hallucination-resistant Retrieval-Augmented Generation (RAG) assistant for university students, staff, and faculty. It indexes official university policies (hostel curfew, academic attendance, grading schemes, IT access) into a persistent ChromaDB vector store using 384-dimensional dense semantic embeddings (`all-MiniLM-L6-v2`) to provide cited answers and automate student helpdesk ticketing.
2. **AegisOps**: An autonomous Site Reliability Engineering (AIOps) observability and self-healing platform. It monitors campus microservices (Exam Service, LMS, Student Portal, Library Service) using an unsupervised Machine Learning **Isolation Forest** model to detect multivariate anomalies before system failure, correlates live telemetry against codified SRE runbooks, and executes human-in-the-loop remediation (pod restarts, replica scaling).

```
 ┌────────────────────────────────────────────────────────────────────────┐
 │                      React 18 + Tailwind CSS Dashboard                 │
 │            (UniMind AI Student Assistant + AegisOps SRE Console)       │
 └──────────────────────────────────┬─────────────────────────────────────┘
                                    │ HTTP / REST
 ┌──────────────────────────────────▼─────────────────────────────────────┐
 │                         FastAPI Backend Engine                         │
 │                           (Port 8000 / Uvicorn)                        │
 ├────────────────────────────────────┬───────────────────────────────────┤
 │        UniMind AI Services         │          AegisOps Services        │
 │  • RAG Retrieval & Ingestion       │  • Prometheus Telemetry Collector │
 │  • ChromaDB Vector Pipeline        │  • Isolation Forest ML Anomaly    │
 │  • Policy Search & Chunking        │  • Loki Centralized Log Stream    │
 │  • Student Helpdesk Ticketing      │  • AI Runbook Diagnostic Engine   │
 │  • RBAC & JWT Authentication       │  • Kubernetes Pod / Scale Healing │
 └──────────────────┬─────────────────┴───────────────────┬───────────────┘
                    │                                     │
 ┌──────────────────▼───────────┐         ┌───────────────▼───────────────┐
 │       ChromaDB Vector DB     │         │      Relational Database      │
 │ (384-dim all-MiniLM-L6-v2)   │         │ (Users, Policies, Incidents)  │
 └──────────────────────────────┘         └───────────────────────────────┘
```

---

## 🚀 Quick Start & How to Run

### 1. Prerequisites
- **Python 3.10+** (with virtual environment)
- **Node.js 18+** & npm

### 2. Single-Command Launch
Run the automated supervisor script from the project root directory:

```bash
python run_app.py
```

This single command automatically:
1. Detects or initializes the Python environment (`.venv`).
2. Seeds initial demo data (users, sample documents, ChromaDB vector chunks, active incident).
3. Spawns the **FastAPI Backend** on **`http://localhost:8000`** (Swagger docs: `http://localhost:8000/docs`).
4. Spawns the **React + Vite Frontend** on **`http://localhost:5173`**.
5. Automatically opens your default web browser to the dashboard.

### 3. Default Login Credentials
- **Username:** `admin` | **Password:** `admin123` (Admin / SRE Lab Manager)
- **Username:** `student` | **Password:** `student123` (Undergraduate Student)

---

## 🧭 Global Navigation & Header Controls

The top sticky header is present on every view:

| UI Element | Type | What It Does / Where It Works |
| :--- | :--- | :--- |
| **Search Input Box** | Text Filter | Global search across documents, active services, and open tickets. |
| **Incident Status Pill** | Dynamic Badge | Displays the live health of the campus infrastructure (e.g. `Degraded • 1 incident` in amber with a pulsing dot when chaos/incident is active). |
| **Notification Bell** | Badge Icon | Displays unread system alert count (`1` when critical alerts exist). |
| **User Profile Capsule** | Avatar & Role | Shows active user badge (`KL`), Full Name (`Kartik Lakhera`), and role (`Lab Manager`). |

---

## 🗂️ Sidebar Navigation: Complete Button & Feature Guide

The left sidebar is permanently docked on the left (dark navy `#0b132b`). It organizes the entire platform into two functional suites and one primary action button:

```
┌─────────────────────────────────┐
│ 🎓 UniMind AI WITH AEGISOPS     │
├─────────────────────────────────┤
│ UNIMIND AI                      │
│   ⊞ Dashboard                   │
│   💬 Student Assistant          │
│   📖 Knowledge Base             │
│   📄 Documents                  │
│   🗄️ RAG Management             │
│   🎫 Tickets & Incidents        │
├─────────────────────────────────┤
│ AEGISOPS                        │
│   📈 AegisOps Overview          │
│   🖥️ Services                   │
│   📉 Monitoring                 │
│   📊 Metrics                    │
│   📑 Logs                       │
│   🧠 ML Anomaly Detection       │
│   ⚠️ Incidents                  │
│   ✨ AI Diagnosis               │
│   🔧 Remediation                │
│   ☸️ Kubernetes                 │
├─────────────────────────────────┤
│ [ ▶ Run AegisOps Demo ]         │
└─────────────────────────────────┘
```

---

### 🔘 Special Action Button: Run AegisOps Demo

* **Location:** Bottom of the left sidebar (Blue full-width button).
* **Button Label:** `▶ Run AegisOps Demo`
* **What Happens When Clicked:**
  1. Instantly navigates the user directly to the **ML Anomaly Detection** tab (`ml_anomaly`).
  2. Simultaneously triggers parallel backend API calls to `/api/v1/ml/anomaly-scores`, `/api/v1/aegisops/services`, `/api/v1/aegisops/metrics`, and `/api/v1/aegisops/logs`.
  3. Displays live multivariate Isolation Forest anomaly scores (e.g. 0.91 anomaly score on Exam Service) with actionable diagnostic recommendations.

---

### SECTION 1: UNIMIND AI SUITE

#### 1. Dashboard
* **Sidebar Item:** `Dashboard` (Icon: Layout Grid)
* **Purpose:** The high-level executive bird's-eye view of both student AI health and campus microservices infrastructure.
* **Buttons & Interactive Elements:**
  * **`Resolve Degraded Service` Button (Red, Top Banner):** Immediately jumps straight to the **Remediation** tab to resolve active incidents.
  * **`View Details` Links (Bottom of KPI Cards):**
    * *Active Infrastructure (3/4 Healthy)*: Opens Services Fleet view.
    * *ML Anomaly Engine (Isolation Forest)*: Opens ML Anomaly Detection view.
    * *RAG Knowledge Base (4 Policies)*: Opens Knowledge Base view.
    * *Student AI Assistant (98% Grounded)*: Opens Student Assistant chat.
  * **Quick Workflows Action Cards:**
    * **`Ask Student Assistant`:** Launches AI policy chat.
    * **`Inspect ML Anomaly Scan`:** Jumps to Isolation Forest telemetry.
    * **`AI Root Cause Diagnosis`:** Evaluates telemetry against SRE runbooks.
    * **`Trigger Self-Healing`:** Opens the human-in-the-loop remediation terminal.
  * **`All Services` Link:** Jumps to the full services telemetry grid.
  * **Microservice Row Action Buttons:**
    * **`Diagnose` (Blue button on Exam Service row):** Navigates to AI Diagnosis for that specific service.
    * **`Monitor` (Grey buttons on healthy service rows):** Navigates to real-time SVG monitoring charts.
  * **`Execute Remediation Action` Button (Active SRE Alert card):** Direct shortcut to execute pod restarts or replica scaling.
  * **`View AI Root Cause Analysis` Button:** Direct shortcut to inspect AI runbook matching.

---

#### 2. Student Assistant
* **Sidebar Item:** `Student Assistant` (Icon: Message Bubble)
* **Purpose:** Grounded RAG conversational AI assistant answering student queries on attendance, exams, hostel curfews, and grading.
* **Buttons & Interactive Elements:**
  * **Question Input Field:** Textbox to enter questions (e.g., *"What is the curfew time for undergraduate hostel students?"*).
  * **`Send` Button (Blue with Send Icon):**
    * Submits the prompt to backend `/api/v1/assistant/chat`.
    * Performs vector search against ChromaDB (`university_knowledge_base`).
    * Returns the answer alongside verified source documents, policy categories, and cosine similarity match percentages (e.g., `94% match`).
  * **Citation Pills (Under bot replies):** Highlights the exact document and similarity score retrieved.

---

#### 3. Knowledge Base
* **Sidebar Item:** `Knowledge Base` (Icon: Open Book)
* **Purpose:** Document and policy explorer containing official campus regulations and SRE incident runbooks.
* **Buttons & Interactive Elements:**
  * **`Search knowledge...` Input Field:** Real-time search filter matching keywords across document titles and text excerpts.
  * **Category Filter Pills:**
    * `All`: Displays all indexed records.
    * `Hostel`: Filters residence and curfew rules.
    * `Attendance`: Filters lecture and lab attendance regulations.
    * `Academic`: Filters grading and GPA calculation standards.
    * `IT Support`: Filters 24/7 compute cluster access rules.
    * `SRE Runbooks`: Filters operational runbooks (e.g., `runbook-001` for Database Pool Exhaustion).
  * **`Read Full` Button (On each card):** Opens a full-screen modal showing the un-truncated text of the policy or runbook.
  * **`Ask Assistant` Button (On each card):** Pre-populates the Student Assistant chat with this document's subject and switches to the chat screen.
  * **Modal Buttons:**
    * **`Ask AI Assistant About This`:** Sends the modal document's topic directly to the AI Assistant.
    * **`Close` / `✕`:** Closes the reading modal.

---

#### 4. Documents
* **Sidebar Item:** `Documents` (Icon: File Text)
* **Purpose:** Document management and automatic ChromaDB vector ingestion pipeline.
* **Buttons & Interactive Elements:**
  * **`Refresh` Button (Top Right):** Refetches the list of indexed documents from `/api/v1/documents`.
  * **`Document Title` Input & `Category` Dropdown:** Metadata fields for new institutional documents.
  * **`Select File` Input:** File chooser accepting `.txt`, `.pdf`, `.md`, or `.docx` policy files.
  * **`Upload & Ingest to RAG` Button (Blue):**
    1. Uploads file to `/api/v1/documents/upload`.
    2. Automatically triggers `/api/v1/rag/ingest/{doc_id}` to chunk text (300-char chunks, 40-char overlap) and generate 384-dimensional dense vectors in ChromaDB.
    3. Displays live success toast with chunk count.
  * **`Re-Ingest` Button (Table row):** Re-runs text chunking and vector storage on an existing document.
  * **`Delete` (Trash Icon, Table row):** Deletes document metadata, disk file, and associated ChromaDB vector entries after user confirmation.

---

#### 5. RAG Management
* **Sidebar Item:** `RAG Management` (Icon: Database)
* **Purpose:** Semantic vector retrieval testing playground and ChromaDB index observability.
* **Buttons & Interactive Elements:**
  * **Metadata KPI Counters:** Shows Vector Store (`ChromaDB`), Embedding Model (`all-MiniLM-L6-v2`), Dimensions (`384`), Total Indexed Chunks, and Relevance Threshold (`0.45`).
  * **Retrieval Query Input:** Textbox to input custom test queries.
  * **Category Filter Dropdown:** Limits semantic search scope to specific departments (`Hostel`, `Attendance`, `Academic`, `IT Support`).
  * **`Vector Search` Button (Blue):**
    * Calls `/api/v1/rag/query`.
    * Computes cosine similarity scores against all chunks in the ChromaDB collection.
    * Renders the top-ranked vector chunks with match percentages and metadata.
  * **Sample Query Chips (4 buttons):** Quick pre-set queries (e.g. *"What is the mandatory hostel curfew time?"*). Clicking any chip auto-populates the query box and immediately executes the vector search.

---

#### 6. Tickets & Incidents
* **Sidebar Item:** `Tickets & Incidents` (Icon: Ticket)
* **Purpose:** Automated student inquiries, grievance management, priority triaging, and AI-assisted ticket resolution.
* **Buttons & Interactive Elements:**
  * **`+ New Support Ticket` Button (Blue, Top Right):** Opens the ticket creation modal.
  * **Status Filter Tabs:**
    * `all`: Shows all student tickets.
    * `open`: Shows unassigned or new tickets.
    * `in progress`: Shows actively worked tickets.
    * `resolved`: Shows closed tickets.
  * **`Start` Button (Row action):** Updates ticket status to `IN_PROGRESS` via `PATCH /api/v1/tickets/{id}`.
  * **`Resolve` Button (Row action):** Updates ticket status to `RESOLVED`.
  * **`AI Solve` Button (Purple, Sparkles Icon):** Automatically packages the ticket subject and description into a prompt, switches to the Student Assistant view, and queries the knowledge base for an authoritative solution.
  * **Create Ticket Modal Buttons:**
    * **`Submit Ticket` (Blue):** Persists the new ticket to `/api/v1/tickets`.
    * **`Cancel` / `✕`:** Discards form and closes modal.

---

### SECTION 2: AEGISOPS AUTONOMOUS FLEET SUITE

#### 7. AegisOps Overview
* **Sidebar Item:** `AegisOps Overview` (Icon: Activity Pulse)
* **Purpose:** Primary SRE control center with interactive Chaos Engineering injection and microservices topology.
* **Buttons & Interactive Elements:**
  * **`Refresh Telemetry` Button:** Refetches cluster health status from `/api/v1/aegisops/overview`.
  * **`Inject Chaos Anomaly` / `Disable Chaos (Restore Normal)` Button (Gradient Banner):**
    * Calls `/api/v1/aegisops/chaos/toggle`.
    * **When Chaos Injected:** Artificially induces 92% CPU load and 1,800ms latency on Exam Service, triggers an anomaly score of 0.91, degrades cluster health to 75%, and surfaces critical alerts.
    * **When Chaos Disabled:** Restores nominal traffic (CPU <25%, Latency <110ms, Anomaly score <0.15) and sets cluster health to 100%.
  * **`Remediate Now` Button:** Appears when chaos is active; immediately routes to the Remediation console.
  * **Cluster KPI Gauges:** Displays Cluster Health (`75%` or `100%`), Active Incidents count, MTTD (`1.2m`), and MTTR (`3.4m`).
  * **Architecture & Traffic Topology Map:** Visual diagram illustrating ingress routing from Cloud Gateway into Exam Service (Port 8003), LMS (Port 8001), Student Portal (Port 8002), Library Service (Port 8004), and underlying PostgreSQL / Redis / Prometheus / ChromaDB persistence.

---

#### 8. Services
* **Sidebar Item:** `Services` (Icon: Server)
* **Purpose:** Microservices fleet health cards displaying key operational metrics and mini trend sparklines.
* **Buttons & Interactive Elements:**
  * **Interactive Service Cards (4 Cards: LMS, Student Portal, Exam Service, Library Service):**
    * Clicking anywhere on any service card navigates directly to the **Monitoring** view for detailed inspection.
    * Displays CPU progress bar, Memory progress bar, Latency (ms), Uptime, Request Rate (req/s), Error Rate (%), Replicas, and Last Incident status.
    * Critical cards (Exam Service under chaos) feature a red flashing border, pulsing alert beacon, and spiked red sparkline chart.

---

#### 9. Monitoring
* **Sidebar Item:** `Monitoring` (Icon: Trending Up)
* **Purpose:** Real-time multi-variate SVG time-series charts with Isolation Forest anomaly detection markers.
* **Buttons & Interactive Elements:**
  * **Time Range Selector Buttons:**
    * `Last 15 min`
    * `Last 1 hour` (Default)
    * `Last 6 hours`
    * `Last 24 hours`
  * **5 Real-Time Telemetry Charts:**
    1. **CPU Usage (93%):** Line chart showing historical CPU values with red circular anomaly markers at timestamps where values breached normal distributions.
    2. **Memory Usage (82.3%):** Purple trendline with anomaly detection markers.
    3. **Request Rate (2945.1/s):** Green throughput curve with load spike flags.
    4. **Latency (1695 ms):** Amber response latency curve with critical latency flags.
    5. **Error Rate (13.8%):** Red HTTP 5xx error rate spike curve.

---

#### 10. Metrics
* **Sidebar Item:** `Metrics` (Icon: Bar Chart)
* **Purpose:** Prometheus tabular telemetry view displaying the raw multivariate feature vector that feeds the ML Anomaly Detection model.
* **Features Displayed per Service:**
  * `SERVICE`: Service name (`Exam Service`, `LMS`, `Student Portal`, `Library Service`).
  * `CPU`: Processor utilization percentage.
  * `MEMORY`: RAM utilization percentage.
  * `REQUESTS`: Incoming throughput (requests/sec).
  * `LATENCY`: Round-trip response time (milliseconds).
  * `ERRORS`: Failed request percentage (5xx).
  * `REPLICAS`: Active pod replica count.
  * *Alert Styling:* Degraded rows are styled in bold red with critical warnings.

---

#### 11. Logs (Loki)
* **Sidebar Item:** `Logs` (Icon: File Code)
* **Purpose:** High-throughput centralized log explorer modeled after Grafana Loki.
* **Buttons & Interactive Elements:**
  * **`All services` Dropdown Filter:** Filter log entries by service (`exam-service`, `lms`, `student-portal`, `library`).
  * **`All levels` Dropdown Filter:** Filter by severity (`ERROR`, `WARN`, `INFO`, `DEBUG`).
  * **Time Range Dropdown:** `Last 15 min`, `Last 1 hour`, `Last 24 hours`.
  * **`Search messages...` Text Input:** Real-time search across log message strings (e.g., *"pool exhausted"*, *"timeout"*, *"503"*).
  * **Dark Mode Log Table:** Displays exact timestamps, emitting service, color-coded level badges (Red `ERROR`, Amber `WARN`, Cyan `INFO`), message contents, and distributed Trace IDs (`a91f3c2e`).

---

#### 12. ML Anomaly Detection
* **Sidebar Item:** `ML Anomaly Detection` (Icon: CPU Chip)
* **Purpose:** Unsupervised Machine Learning observability using Scikit-Learn **Isolation Forest**.
* **Display & Interactive Elements:**
  * **Model Metadata Card:**
    * Algorithm: `Isolation Forest`
    * Status: `Active` (Green beacon)
    * Features Evaluated: `CPU`, `Memory`, `Requests`, `Latency`, `Errors` (5-dimensional vector)
    * Decision Threshold: `0.70`
    * Baseline: `Trained on 14 days of normal campus traffic`
  * **Anomaly Score Bars (Per Service):**
    * Visual progress bars from 0.00 to 1.00.
    * Exam Service under contention scores **`0.91`** with a red **`• HIGH ANOMALY`** badge.
    * Healthy services score **`0.07 – 0.12`** with green normal bars.
  * **Active Alert Message Box:** Contextual explanation highlighting why current service behavior significantly diverges from learned distributions.
  * **Educational Architecture Card:** Explains the engineering difference between Unsupervised Anomaly Detection (implemented) vs Probabilistic Failure Risk Estimation.

---

#### 13. Incidents
* **Sidebar Item:** `Incidents` (Icon: Alert Triangle)
* **Purpose:** SRE IT infrastructure incident management, triage, and resolution tracking.
* **Buttons & Interactive Elements:**
  * **`Refresh` Button:** Refetches incidents from `/api/v1/incidents`.
  * **Incident Card Headers:** Shows Incident Code (e.g. `INC-2026-0842`), Severity (`CRITICAL`), Status (`OPEN` / `RESOLVED`), and affected Service.
  * **Root Cause & Recommendation Details:** Lists root-cause diagnosis and recommended operational runbook action.
  * **`Remediate` Button (Blue):** Jumps directly to the controlled remediation view with this incident pre-selected.
  * **`AI Diagnosis` Button (Grey):** Jumps to AI diagnosis to view runbook and confidence metrics.
  * **`Incident Resolved` Badge (Green):** Appears when remediation has closed the incident.

---

#### 14. AI Diagnosis
* **Sidebar Item:** `AI Diagnosis` (Icon: Sparkles)
* **Purpose:** AI Root Cause Analysis correlating live multi-variate telemetry against codified SRE incident runbooks.
* **Buttons & Interactive Elements:**
  * **`Diagnose Service` Dropdown:** Choose target service (`Exam Service`, `LMS`, `Student Portal`, `Library Service`).
  * **Root Cause Assessment Card:**
    * Displays Suspected Root Cause (e.g., *Database Connection Pool Exhaustion*).
    * AI Confidence Score: `88% Confidence`.
    * Telemetry Evidence Box: Exact telemetry data proving the root cause (CPU 92%, Latency 1,800ms, Error rate 14%).
    * Matched SRE Runbook Section: Automatically matches `runbook-001` (Exam Service High Latency & Pool Exhaustion) from the knowledge base.
  * **`Proceed to Controlled Remediation` Button (Blue, with Arrow):** Transitions operator directly into the human-approved remediation workflow.

---

#### 15. Remediation
* **Sidebar Item:** `Remediation` (Icon: Wrench)
* **Purpose:** Human-in-the-loop autonomous self-healing execution console with real-time audit logging.
* **Buttons & Interactive Elements:**
  * **Controlled Action Radio Buttons:**
    1. **`Restart Pod Deployment`:** Gracefully terminates degraded containers and flushes exhausted database connection pool handles.
    2. **`Scale Out Replicas (2 → 4)`:** Scales deployment from 2 to 4 pods to distribute incoming traffic.
  * **`Approve & Execute Remediation` Button (Blue):**
    * Triggers human approval and calls `POST /api/v1/aegisops/remediate`.
    * Initiates live streaming terminal logs.
  * **Live Execution Terminal (`aegisops-remediation-engine // stdout`):**
    * Streams real-time diagnostic output:
      1. Verifies operator RBAC authorization (`Kartik Lakhera - ADMIN`).
      2. Queries Kubernetes API for deployment `exam-service`.
      3. Sends `SIGTERM` to degraded pod `exam-service-7d9f-x2k`.
      4. Flushes connection pool and resets handles.
      5. Spins up fresh pod `exam-service-7d9f-y4n` (RUNNING in 1.4s).
      6. Polls Prometheus probes: Latency drops to 112ms, CPU drops to 24%.
      7. Isolation Forest score recovers to nominal 0.12 (< 0.70 threshold).
      8. Writes security audit log (`AUDIT-2026-7782`).
      9. Closes incident `INC-2026-0842` as `RESOLVED`.
  * **`View Restored Service Fleet` Button:** Appears after successful remediation to return operator to the healthy services overview.

---

#### 16. Kubernetes
* **Sidebar Item:** `Kubernetes` (Icon: Layers)
* **Purpose:** Cluster deployment and pod-level operational management console for namespace `unimind-aegisops`.
* **Buttons & Interactive Elements:**
  * **`Refresh Cluster` Button:** Calls `/api/v1/aegisops/kubernetes/status` to get live pod statuses.
  * **Deployments Table:** Displays deployment names, health badges, replica ratios, container images, and resource limits.
  * **Deployment Row Action Buttons:**
    * **`▲` (Scale Out Button):** Increments replica count by +1 (calls `/api/v1/aegisops/services/{name}/scale`).
    * **`▼` (Scale In Button):** Decrements replica count by -1.
    * **`Restart` Button:** Sends rollout restart to all deployment pods.
  * **Pods Fleet Status Table:** Lists each running pod, its parent deployment, restart count, node allocation (`gke-node-pool-1`, `gke-node-pool-2`), CPU, and memory.
  * **`Logs` Button (On each pod row):** Opens a dark terminal modal showing live `kubectl logs` for that specific pod.
  * **Pod Log Modal Buttons:**
    * **`Close` / `✕`:** Dismisses pod log inspection modal.

---

## 🔄 End-to-End Self-Healing Incident Walkthrough

To experience the full closed-loop autonomous AIOps workflow:

```
[ Step 1: Inject Chaos ] 
       │ 
       ▼
[ Step 2: Anomaly Flagged by Isolation Forest (Score 0.91) ]
       │ 
       ▼
[ Step 3: Inspect Logs in Loki & Metrics in Monitoring ]
       │ 
       ▼
[ Step 4: AI Root Cause Diagnosis (Matched runbook-001) ]
       │ 
       ▼
[ Step 5: Operator Approves Remediation in Terminal ]
       │ 
       ▼
[ Step 6: Pod Restarted, DB Pool Flushed, Incident Resolved ]
```

1. Go to **AegisOps Overview** and ensure Chaos is active (or click **`Inject Chaos Anomaly`**).
2. Click **`Run AegisOps Demo`** in the bottom sidebar: observe **Exam Service** flagged with **`0.91 HIGH ANOMALY`**.
3. Open **Monitoring**: view red anomaly markers on CPU (93%) and Latency (1695ms).
4. Open **Logs**: filter by `ERROR` to see `Database connection timeout after 5000ms (pool exhausted)`.
5. Open **AI Diagnosis**: review the 88% confidence diagnosis and matched `runbook-001`.
6. Click **`Proceed to Controlled Remediation`**, select **`Restart Pod Deployment`**, and click **`Approve & Execute Remediation`**.
7. Watch the terminal execute live. Once complete, notice the incident resolves and cluster returns to 100% healthy.

---

## 📡 Backend API Endpoint Mapping

All UI buttons connect to authenticated FastAPI endpoints:

| UI Button / Action | Frontend Tab | HTTP Method & Route | Backend Action |
| :--- | :--- | :--- | :--- |
| `Run AegisOps Demo` | Sidebar Footer | `GET /api/v1/ml/anomaly-scores` | Calculates Isolation Forest scores across all services |
| `Send` Chat Prompt | Student Assistant | `POST /api/v1/assistant/chat` | RAG semantic retrieval & answer generation |
| `Upload & Ingest to RAG` | Documents | `POST /api/v1/documents/upload` | Stores policy document on disk |
| `Re-Ingest` | Documents | `POST /api/v1/rag/ingest/{id}` | Chunks text & embeds into ChromaDB |
| `Delete` Document | Documents | `DELETE /api/v1/documents/{id}` | Removes document and vector embeddings |
| `Vector Search` | RAG Management | `POST /api/v1/rag/query` | Cosine similarity vector query in ChromaDB |
| `Submit Ticket` | Tickets & Incidents | `POST /api/v1/tickets` | Creates student inquiry ticket |
| `Start` / `Resolve` Ticket | Tickets & Incidents | `PATCH /api/v1/tickets/{id}` | Updates ticket workflow state |
| `Inject / Disable Chaos` | AegisOps Overview | `POST /api/v1/aegisops/chaos/toggle` | Toggles CPU/latency failure injection |
| `Diagnose Service` | AI Diagnosis | `POST /api/v1/aegisops/diagnose/{name}` | Correlates telemetry with SRE runbooks |
| `Approve & Execute` | Remediation | `POST /api/v1/aegisops/remediate` | Executes pod restart / scaling self-healing |
| `Scale Out` (`▲` / `▼`) | Kubernetes | `POST /api/v1/aegisops/services/{name}/scale` | Scales Kubernetes deployment replicas |
| `Restart Pod` | Kubernetes | `POST /api/v1/aegisops/services/{name}/restart` | Triggers rollout restart of service pod |
| `Refresh Cluster` | Kubernetes | `GET /api/v1/aegisops/kubernetes/status` | Queries pod fleet and deployment status |
| `Filter Logs` | Logs | `GET /api/v1/aegisops/logs` | Queries centralized Loki log stream |
| `Fetch Telemetry` | Metrics | `GET /api/v1/aegisops/metrics` | Returns 5-feature Prometheus telemetry vector |

---

## 💻 Technology Stack & System Requirements

| Layer | Component | Technologies Used |
| :--- | :--- | :--- |
| **Frontend** | Single Page App | React 18, Vite, Tailwind CSS, Lucide Icons |
| **Backend API** | High Performance REST | Python 3.10+, FastAPI, Uvicorn, Pydantic v2 |
| **Vector Database** | RAG Embeddings | ChromaDB, `sentence-transformers` (`all-MiniLM-L6-v2`) |
| **Relational Database** | Data Persistence | SQLAlchemy ORM, SQLite / PostgreSQL |
| **Machine Learning** | Anomaly Detection | Scikit-Learn (Unsupervised `IsolationForest`, NumPy) |
| **Telemetry & Observability** | Monitoring & Logs | Simulated Prometheus Metrics, Grafana Loki Logs |
| **Orchestration** | Microservices & Healing | Kubernetes Deployment API Simulator, Chaos Engine |

---

*Authored for the UniMind AI & AegisOps University Platform.*
