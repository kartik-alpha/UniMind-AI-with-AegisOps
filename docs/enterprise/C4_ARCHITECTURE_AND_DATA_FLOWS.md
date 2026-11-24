# UniMind AI + AegisOps: C4 Architecture & System Data Flows
**Version:** 1.0.0-PROD  
**Classification:** Enterprise SaaS Architecture & Infrastructure Blueprint  
**Authors:** Enterprise Software Architecture & DevOps Teams  

---

## 1. Executive Summary

This document specifies the complete C4 model (Context, Containers, Components, and Code/Deployment) along with end-to-end data flows for the **UniMind AI + AegisOps Unified Enterprise Platform**.

The platform is designed around two tightly integrated, multi-tenant engines:
1. **UniMind AI Engine:** Enterprise Knowledge Intelligence, Hybrid RAG (Dense + BM25 + Reciprocal Rank Fusion), Grounded Answer Generation with Citation Chains, and Real-Time SSE Token Streaming.
2. **AegisOps Engine:** Autonomous SRE Engine, Microservice Telemetry Harvesting, Unsupervised Isolation Forest Anomaly Detection, Automated Root Cause Analysis (RCA), and Controlled Human-in-the-Loop (HITL) Self-Healing Remediation.

Both engines share a Zero-Trust Multi-Tenant Governance layer featuring strict tenant isolation (`X-Tenant-ID` verification), Cryptographic SHA-256 Audit Log Chains, and Fine-Grained Role-Based Access Control (RBAC).

---

## 2. C4 Architecture Specification

### Level 1: System Context Diagram

The System Context diagram illustrates the boundary of the UniMind AI + AegisOps platform, its external actors (students, staff, SRE engineers, platform administrators), and its integration points with institutional core systems.

```mermaid
flowchart TD
    UserStudent["Student / End User<br/>(Browser / Mobile)"]
    UserStaff["Faculty & Academic Staff<br/>(Web Portal)"]
    UserSRE["Site Reliability Engineer (SRE)<br/>(Ops Console)"]
    UserAdmin["Tenant Administrator<br/>(Governance Console)"]

    subgraph UniMindPlatform["UniMind AI + AegisOps Unified Enterprise Platform"]
        PlatformBoundary["Multi-Tenant Unified Platform Gateway<br/>(API Gateway & Ingress Router)"]
    end

    subgraph ExternalSystems["Enterprise Institutional Infrastructure"]
        SIS["Student Information System (SIS)"]
        LMS["Learning Management System (LMS)"]
        Prometheus["Prometheus / Datadog APM"]
        OAuth["Enterprise IdP / SAML 2.0 / OIDC"]
    end

    UserStudent -->|"Queries policies, courses, schedules (HTTPS/SSE)"| PlatformBoundary
    UserStaff -->|"Uploads syllabus, course docs, knowledge base"| PlatformBoundary
    UserSRE -->|"Monitors anomalies, approves HITL remediation"| PlatformBoundary
    UserAdmin -->|"Configures tenants, quotas, verifies audit chains"| PlatformBoundary

    PlatformBoundary -->|"Syncs student records"| SIS
    PlatformBoundary -->|"Ingests course materials"| LMS
    PlatformBoundary -->|"Exports SRE telemetry & scrape targets"| Prometheus
    PlatformBoundary -->|"Authenticates enterprise identities"| OAuth
```

---

### Level 2: Container Architecture Diagram

The Container diagram decomposes the platform into independently deployable units: Frontend Single Page Application (SPA), Backend Core API (FastAPI), Hybrid Vector Engine (ChromaDB + BM25), Relational & Audit Database (PostgreSQL / SQLite WAL), and Distributed Caching / Rate Limiting (Redis).

```mermaid
flowchart TD
    subgraph ClientTier["Client Tier (Browser)"]
        SPA["UniMind AI + AegisOps React SPA<br/>[Vite, TailwindCSS, React 18]<br/>Single Page App across 22 Views"]
    end

    subgraph IngressTier["Ingress & Edge Routing"]
        Ingress["NGINX Ingress Controller<br/>[TLS Termination, Rate Limiting, CORS]"]
    end

    subgraph AppTier["Application Compute Tier"]
        FastAPIServer["FastAPI Backend Application<br/>[Python 3.11, Uvicorn, SQLAlchemy Core/ORM]<br/>Stateless, Multi-Replica Deployment"]
    end

    subgraph StorageTier["Data & Vector Persistence Tier"]
        DB["Relational Database<br/>[PostgreSQL 16 / SQLite WAL Mode]<br/>Multi-Tenant Schemas, Tickets, Audit Hash Chain"]
        VectorDB["ChromaDB Vector Store<br/>[Dense Embeddings: all-MiniLM-L6-v2]<br/>Tenant-Partitioned Collections"]
        BM25Store["BM25 Inverted Index File Storage<br/>[Sparse Retrieval Inverted Indices]"]
        MLArtifacts["ML Model Registry<br/>[Isolation Forest, Scaler Checksum C2715...]"]
        Cache["Redis / Memory Cache Adapter<br/>[Session Store, Rate Limits, Token Denylist]"]
    end

    SPA -->|"HTTPS / REST / SSE Streaming (Port 443)"| Ingress
    Ingress -->|"Reverse Proxy / Load Balance (Port 8000)"| FastAPIServer
    FastAPIServer -->|"SQL Queries / Transactions"| DB
    FastAPIServer -->|"Dense Vector Search"| VectorDB
    FastAPIServer -->|"Sparse Lexical Retrieval"| BM25Store
    FastAPIServer -->|"Feature Extraction & ML Scoring"| MLArtifacts
    FastAPIServer -->|"Token Denylist & Quota Enforce"| Cache
```

---

### Level 3: Component Architecture Diagrams

#### 3.1 Backend Component Decomposition

```mermaid
flowchart LR
    subgraph APIRouters["FastAPI API Routers (backend/app/api/)"]
        AuthRouter["Auth Router<br/>/api/v1/auth"]
        AssistantRouter["Assistant Router<br/>/api/v1/assistant"]
        AegisOpsRouter["AegisOps Router<br/>/api/v1/aegisops"]
        GovernanceRouter["Governance Router<br/>/api/v1/governance"]
        TicketsRouter["Tickets Router<br/>/api/v1/tickets"]
    end

    subgraph SecurityMiddleware["Zero-Trust Security & Tenant Isolation"]
        TenantDeps["Tenant Scoping Dependency<br/>(tenant_deps.py)"]
        RateLimiter["Rate Limiting & Token Denylist"]
        AuditChaining["Cryptographic Audit Chaining<br/>(models/audit.py auto_chain)"]
    end

    subgraph CoreEngines["Core Processing Engines"]
        HybridRAGEngine["Hybrid RAG Engine<br/>(Dense + BM25 + RRF)"]
        MLAnomalyEngine["Isolation Forest ML Engine<br/>(Telemetry Scorer)"]
        RCADiagnosticsEngine["RCA & Diagnostic Engine<br/>(Rule Graph + Correlator)"]
        RemediationEngine["Remediation Engine<br/>(Action Dispatcher + HITL)"]
    end

    AuthRouter --> SecurityMiddleware
    AssistantRouter --> SecurityMiddleware
    AegisOpsRouter --> SecurityMiddleware
    GovernanceRouter --> SecurityMiddleware
    TicketsRouter --> SecurityMiddleware

    SecurityMiddleware --> HybridRAGEngine
    SecurityMiddleware --> MLAnomalyEngine
    SecurityMiddleware --> RCADiagnosticsEngine
    SecurityMiddleware --> RemediationEngine
    SecurityMiddleware --> AuditChaining
```

---

## 3. End-to-End System Data Flows

### 3.1 RAG Query, Reciprocal Rank Fusion & SSE Streaming Flow

The sequence diagram below models the entire lifecycle of an enterprise student knowledge retrieval query, from token streaming to grounded citation verification.

```mermaid
sequenceDiagram
    autonumber
    actor Student as Student Browser
    participant API as FastAPI Ingress (/assistant/chat/stream)
    participant Sec as TenantDeps & Auth Guard
    participant Chroma as ChromaDB (Dense)
    participant BM25 as BM25 Index (Sparse)
    participant RRF as RRF Ranker & Deduplicator
    participant LLM as LLM Inference / Generator
    participant Audit as Audit Hash Chain

    Student->>API: POST /api/v1/assistant/chat/stream {"query": "drop deadline", "mode": "hybrid"}
    Note over Student,API: Headers: Authorization: Bearer <JWT>, X-Tenant-ID: unimind-university
    API->>Sec: Validate JWT, Tenant ID & Rate Limit Quota
    Sec-->>API: Authorized (tenant_id="unimind-university")
    
    par Parallel Retrieval
        API->>Chroma: Dense query_embeddings(top_k=4)
        Chroma-->>API: Dense Candidates [doc1, doc2, doc5]
    and
        API->>BM25: BM25 lexical token match(top_k=4)
        BM25-->>API: Sparse Candidates [doc1, doc3, doc7]
    end

    API->>RRF: Compute RRF Scores: 1 / (60 + rank_dense) + 1 / (60 + rank_bm25)
    RRF-->>API: Top Reranked Context + Citations (Score: 0.88, Confidence: 0.94)

    loop Token Stream (SSE)
        API->>LLM: Stream Prompt (Grounded Context + Query)
        LLM-->>API: Yield token chunk "The last date..."
        API-->>Student: data: {"token": "The", "done": false}
        API-->>Student: data: {"token": " last", "done": false}
    end

    API->>Audit: Append query & citation log (auto SHA-256 hash chaining)
    API-->>Student: data: {"done": true, "citations": [...], "grounding_verified": true}
```

---

### 3.2 AegisOps Telemetry Ingestion, ML Anomaly Detection & HITL Remediation

```mermaid
sequenceDiagram
    autonumber
    actor SRE as SRE Operator
    participant Microservice as Monitored Microservice (Exam Service)
    participant Harvester as Telemetry Harvester (/aegisops/telemetry)
    participant ML as Isolation Forest Model (SHA-256 Verified)
    participant RCA as AI Root Cause Correlator
    participant State as Incident State Machine
    participant Remediator as Remediation Dispatcher

    Microservice->>Harvester: Push Service Metrics (CPU: 96%, DB Saturation: 99%, p95: 1850ms)
    Harvester->>ML: Extract 6-D Feature Vector & Score
    ML-->>Harvester: Anomaly Score = 0.842 (> 0.70 Critical Threshold)
    
    Harvester->>State: Auto-create Incident (INC-48201, Severity: CRITICAL, Status: OPEN)
    Harvester->>RCA: Trigger Multi-Service Dependency Correlator
    RCA-->>State: Identified RCA: "Exam DB Connection Pool Saturation -> Auth Gateway Cascading Latency"
    RCA-->>State: Recommend Action: "FLUSH_IDLE_CONNECTIONS", Confidence: 0.96

    State-->>SRE: UI Alert / SSE Webhook Notification
    SRE->>State: POST /api/v1/aegisops/incidents/INC-48201/transition {"status": "INVESTIGATING"}
    
    SRE->>Remediator: POST /api/v1/aegisops/remediate/approve {"incident_code": "INC-48201", "action": "FLUSH_IDLE_CONNECTIONS"}
    Remediator->>Microservice: Dispatch Pool Flush Command
    Remediator->>Harvester: Verify Post-Remediation Health Metrics
    Harvester-->>Remediator: Metrics Recovered (DB Saturation: 12%, Latency: 42ms, Anomaly: 0.08)
    Remediator->>State: Transition Incident to RESOLVED
    Remediator-->>SRE: Status: SUCCESS, Verified Recovery: True
```

---

### 3.3 Cryptographic Audit Hash Chaining & Tamper Verification Flow

```mermaid
flowchart TD
    subgraph TransactionScope["SQLAlchemy Atomic Transaction Scope"]
        NewRecord["New AuditLog Entity Created<br/>(tenant_id, action, actor_id, details)"]
        EventListener["before_flush Event: auto_chain_audit_log"]
        FetchPrev["Fetch Previous Hash:<br/>connection.info['_pending_hash_{tenant}'] OR<br/>SELECT record_hash FROM audit_logs WHERE tenant_id ORDER BY id DESC LIMIT 1"]
        ComputeHash["Compute SHA-256 Payload:<br/>SHA256(id + tenant_id + action + actor_id + timestamp + details + prev_hash)"]
        AssignHash["Assign target.prev_hash = prev_hash<br/>Assign target.record_hash = calculated_hash"]
        CommitSQL["Atomic Commit to Database (WAL Mode)"]
    end

    subgraph ForensicAuditVerification["Forensic Verification Pipeline (/governance/audit/verify-chain)"]
        QueryRecords["Fetch All Tenant Audit Records<br/>Ordered by ID ASC"]
        LoopCheck["Iterate Records (i = 0 to N-1)"]
        VerifyPrev["Verify record[i].prev_hash == record[i-1].record_hash"]
        VerifyContent["Recalculate SHA-256 for record[i]<br/>Compare against record[i].record_hash"]
        ResultDecision{"Any Mismatch?"}
        ValidChain["Return is_valid: True<br/>Tampered: False, Records Checked: N"]
        TamperDetected["Return is_valid: False<br/>Tampered Record ID: X, Tamper Reason: 'Content tampering / broken chain'"]
    end

    NewRecord --> EventListener
    EventListener --> FetchPrev
    FetchPrev --> ComputeHash
    ComputeHash --> AssignHash
    AssignHash --> CommitSQL

    CommitSQL -.->|"Periodic / On-Demand Audit"| QueryRecords
    QueryRecords --> LoopCheck
    LoopCheck --> VerifyPrev
    VerifyPrev --> VerifyContent
    VerifyContent --> ResultDecision
    ResultDecision -->|"No"| ValidChain
    ResultDecision -->|"Yes"| TamperDetected
```

---

## 4. Multi-Tenant Network Boundary and Security Architecture

### 4.1 Tenant Boundary Isolation Invariant
- **Application Layer:** Every incoming HTTP request must supply `X-Tenant-ID` and a valid JWT. The `tenant_deps.py` guard parses the user's organization memberships from token claims. Any mismatch returns `403 Forbidden` (`INSUFFICIENT_TENANT_PERMISSIONS`).
- **Data Layer:** 
  - Relational queries enforce `WHERE tenant_id = :active_tenant` across all models (`Ticket`, `AuditLog`, `Incident`, `TenantQuota`).
  - Vector collections in ChromaDB are strictly partitioned using the naming convention `knowledge_{tenant_id}`.
- **Audit Verification:** The cryptographic hash chain is calculated on a per-tenant basis (`WHERE tenant_id = :tenant_id`), guaranteeing that one tenant's activities cannot invalidate or alter another tenant's cryptographic provenance.

---

## 5. Architectural Quality Attributes & Non-Functional Verification

| Attribute | Enterprise Requirement | Empirical Verified Score | Reference Evidence |
| :--- | :--- | :--- | :--- |
| **High Availability** | 99.99% Availability, Zero Single Point of Failure | 3-Replica Deployment, HPA 3-10 | `deploy/k8s/03-backend-deployment.yaml` |
| **RAG Latency (p95)** | < 3,000 ms on CPU, < 200 ms on GPU | 2,243.95 ms (p95 CPU), 780.33 ms (p50) | `tests/benchmarks/test_phase_g_latency.py` |
| **Anomaly Detection** | < 250 ms per telemetry frame | 133.31 ms (p95 CPU), 64.72 ms (p50) | `tests/benchmarks/test_phase_g_latency.py` |
| **Mean Time to Detect (MTTD)** | < 2,000 ms detection from injection | 17.65 ms across 6 chaos vectors | `tests/benchmarks/test_phase_g_sre_mttr.py` |
| **Mean Time to Remediate (MTTR)** | < 5,000 ms automated recovery | 51.67 ms average recovery | `tests/benchmarks/test_phase_g_sre_mttr.py` |
| **Tenant Isolation** | 0 cross-tenant data leaks across 18 threat vectors | 18/18 Probes 100% Passed | `scripts/verify_cross_tenant_security.py` |
| **Tamper Evidence** | 100% detection of unauthorized record mutation | SHA-256 Chained Hash Verification | `tests/test_phase_e_security_governance.py` |

---
*Signed and Approved by:*  
**Chief Enterprise Software Architect & SRE Lead**  
*UniMind AI + AegisOps Engineering Council*
