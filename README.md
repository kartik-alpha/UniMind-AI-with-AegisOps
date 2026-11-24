# UniMind AI + AegisOps
### Unified Enterprise Intelligence & Autonomous SRE Platform

[![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen.svg?style=flat&logo=githubactions)](https://github.com)
[![Pytest Regression](https://img.shields.io/badge/Pytest-130%2F130%20Passing%20(100%25)-success.svg?style=flat&logo=pytest)](https://pytest.org)
[![Security Probes](https://img.shields.io/badge/Security-18%2F18%20Probes%20Passed-blue.svg?style=flat&logo=shield)](https://owasp.org)
[![Database Migrations](https://img.shields.io/badge/Migrations-3%2F3%20Verified-purple.svg?style=flat&logo=postgresql)](https://alembic.sqlalchemy.org)
[![Frontend Production Build](https://img.shields.io/badge/Vite%20Build-0%20Errors%20(1493%20Modules)-teal.svg?style=flat&logo=vite)](https://vitejs.dev)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-Production%20Ready-326CE5.svg?style=flat&logo=kubernetes)](https://kubernetes.io)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React 18](https://img.shields.io/badge/React-18.3-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![License](https://img.shields.io/badge/License-Proprietary%20Enterprise%20SaaS-0B0F19.svg?style=flat)](#)

---

## 🏛️ 1. Executive Summary & Product Vision

**UniMind AI + AegisOps** is a commercially deployable, multi-tenant enterprise Software-as-a-Service (SaaS) platform that bridges institutional intelligence with autonomous site reliability engineering in a unified single-pane-of-glass architecture.

The platform unites two enterprise-grade engines:

1. **UniMind AI Engine**: Enterprise Knowledge Intelligence powered by Hybrid Retrieval-Augmented Generation (Dense Embeddings `all-MiniLM-L6-v2` + Sparse BM25 Okapi + Reciprocal Rank Fusion), Grounded Answer Generation with Citation Chains, Low-Latency Server-Sent Events (SSE) Token Streaming, and Hallucination Refusal Defense.
2. **AegisOps Engine**: Autonomous SRE Operations powered by Telemetry Harvesting across core microservices, Unsupervised ML Anomaly Detection (Isolation Forest with verified SHA-256 model checksum), Automated Root Cause Analysis (RCA), SRE Runbook Automation, and Controlled Human-in-the-Loop (HITL) Self-Healing Remediation.

Both engines operate over a **Zero-Trust Multi-Tenant Governance Layer** featuring strict tenant scoping (`X-Tenant-ID`), Cryptographic SHA-256 Audit Log Chains with HMAC-SHA256 signatures, and Role-Based Access Control (RBAC).

---

## 🏗️ 2. Platform Architecture

The platform follows a **Pluggable Hybrid Architecture**: running with zero external dependencies in developer mode (SQLite WAL + In-Process ChromaDB) while scaling horizontally to high-availability Kubernetes clusters (PostgreSQL 16 StatefulSet + Redis Sentinel + Chroma/Qdrant + NGINX Ingress).

```
+---------------------------------------------------------------------------------------+
|                                    CLIENT LAYER                                       |
|      React 18 + Vite SPA | Tailwind CSS | Lucide Icons | Obsidian Navy UI System       |
|  (22 Production Views: Assistant, Knowledge Base, Incidents, Remediation, Governance) |
+-------------------------------------------+-------------------------------------------+
                                            | HTTPS / SSE Streaming / JWT / X-Tenant-ID
+-------------------------------------------v-------------------------------------------+
|                           FASTAPI ZERO-TRUST API GATEWAY                              |
|       Tenant Scoping Middleware | Rate Limiting | Cryptographic Audit Chaining        |
|       RFC 7807 Problem Details: {"type", "title", "status", "detail", "error_code"}   |
+---------------------+-------------------------------+---------------------------------+
                      |                               |
       +--------------v--------------+ +--------------v--------------+
       |      UNIMIND AI ENGINE      | |        AEGISOPS ENGINE      |
       |  - Hybrid RAG (Dense+BM25)  | |  - Telemetry Harvester      |
       |  - Reciprocal Rank Fusion   | |  - Isolation Forest (5D ML) |
       |  - Grounded Citation Chains | |  - AI Root Cause Analysis   |
       |  - SSE Token Streaming      | |  - Controlled Remediation   |
       |  - Hallucination Refusal    | |  - Digital Twin Simulation  |
       +--------------+--------------+ +--------------+--------------+
                      |                               |
+---------------------v-------------------------------v---------------------------------+
|                       DISTRIBUTED ADAPTER SUBSYSTEM                                   |
|  +--------------------+  +--------------------+  +--------------------+  +----------+ |
|  |  Database Adapter  |  |   Vector Adapter   |  |   Cache & Broker   |  | Storage  | |
|  |  SQLite WAL <-> PG |  |  Chroma <-> Qdrant |  | Memory <-> Redis   |  | Local<->S3|
|  +--------------------+  +--------------------+  +--------------------+  +----------+ |
+---------------------------------------------------------------------------------------+
```

---

## 🚀 3. Quick Start & Developer Execution

### Prerequisites
- **Python 3.11+**
- **Node.js 18+** & npm

### Zero-Dependency Local Developer Launch
Run the automated supervisor script:
```bash
python run_app.py
```
This single command:
1. Validates the virtual environment and checks database migrations.
2. Starts the **FastAPI Backend** on `http://localhost:8000` (API Docs: `http://localhost:8000/docs`).
3. Starts the **React + Vite Frontend** on `http://localhost:5173`.
4. Automatically opens the browser to the Obsidian Navy dashboard.

### Default Demonstration Credentials
| Username | Password | Role | Organization Context |
| :--- | :--- | :--- | :--- |
| `admin` | `password` | Platform / Institutional Admin | UniMind University (`1`) |
| `student` | `password` | Student / End-User | UniMind University (`1`) |

---

## 🐳 4. Containerized & Kubernetes Production Deployment

### 4.1 Docker Compose Deployment
```bash
docker compose up -d --build
```

### 4.2 Production Kubernetes Deployment (`deploy/k8s/`)
Deploy the production-grade manifests with High Availability:
```bash
kubectl apply -f deploy/k8s/00-namespace-and-network-policy.yaml
kubectl apply -f deploy/k8s/01-configmaps-secrets.yaml
kubectl apply -f deploy/k8s/02-database-statefulset.yaml
kubectl apply -f deploy/k8s/03-backend-deployment.yaml
kubectl apply -f deploy/k8s/04-frontend-ingress.yaml
```

---

## 🧪 5. Testing & Verification Suites

The repository contains automated regression, security, and benchmark suites:

```bash
# 1. Full Pytest Regression Suite (130 tests across unit, integration, benchmarks)
pytest -q

# 2. Independent Cross-Tenant Security Suite (18 Penetration Probes)
python scripts/verify_cross_tenant_security.py

# 3. Database Schema & Migration Idempotency Check
python scripts/validate_database_migrations.py

# 4. Frontend Production Build Check
npm --prefix frontend run build
```

---

## 📋 6. Commercial Subscription Tiers

| Tier Feature | Starter Tier ($299/mo) | Professional Tier ($999/mo) | Enterprise Tier ($3,999/mo) |
| :--- | :--- | :--- | :--- |
| **Token Allowance** | 500,000 Tokens/mo | 5,000,000 Tokens/mo | Unlimited (50M Soft-Cap) |
| **Vector Storage** | 1 GB Storage | 10 GB Storage | 100 GB Storage |
| **Telemetry Retention** | 7 Days | 30 Days | 365 Days |
| **Vector Isolation** | Shared Partition | Dedicated Collection | Dedicated Node/Cluster |
| **Rate Limit** | 60 req / min | 300 req / min | 2,000 req / min |
| **User Seats** | Up to 10 Seats | Up to 50 Seats | Up to 1,000 Seats |
| **SRE Remediation** | Read-Only Alerts | Manual HITL Approval | Automated Closed-Loop + HITL |
| **Uptime SLA** | 99.5% Uptime | 99.9% Uptime | 99.99% Enterprise Uptime |

---

## 📚 7. Enterprise Documentation Directory

Comprehensive engineering documentation is available under `docs/enterprise/`:
- **C4 Architecture & System Data Flows:** [`docs/enterprise/C4_ARCHITECTURE_AND_DATA_FLOWS.md`](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/C4_ARCHITECTURE_AND_DATA_FLOWS.md)
- **API Reference Guide:** [`docs/enterprise/API_REFERENCE_GUIDE.md`](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/API_REFERENCE_GUIDE.md)
- **Disaster Recovery Plan (RTO < 15m, RPO < 1m):** [`docs/enterprise/DISASTER_RECOVERY_PLAN.md`](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/DISASTER_RECOVERY_PLAN.md)
- **Commercial Tiers & Billing Specification:** [`docs/enterprise/COMMERCIAL_TIERS_AND_BILLING_SPEC.md`](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/COMMERCIAL_TIERS_AND_BILLING_SPEC.md)
- **Higher Education Industry Blueprint:** [`docs/enterprise/blueprints/HIGHER_EDUCATION_BLUEPRINT.md`](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/blueprints/HIGHER_EDUCATION_BLUEPRINT.md)
- **Enterprise IT Operations Blueprint:** [`docs/enterprise/blueprints/ENTERPRISE_ITOPS_BLUEPRINT.md`](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/blueprints/ENTERPRISE_ITOPS_BLUEPRINT.md)
- **SRE Standard Operating Procedures (Runbooks):**
  - `SOP-001`: [Exam Service DB Pool Exhaustion](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/runbooks/SOP-001_EXAM_SERVICE_DB_POOL_EXHAUSTION.md)
  - `SOP-002`: [LMS High Memory & Cache Stall](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/runbooks/SOP-002_LMS_HIGH_MEMORY_AND_CACHE_STALL.md)
  - `SOP-003`: [Student Portal Auth Surge & Throttling](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/runbooks/SOP-003_STUDENT_PORTAL_AUTH_SPIKE.md)
  - `SOP-004`: [ChromaDB Vector Store Corruption & Re-index](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/runbooks/SOP-004_CHROMADB_VECTOR_CORRUPTION_AND_REINDEX.md)
  - `SOP-005`: [Audit Hash Chain Tamper Forensics](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/runbooks/SOP-005_AUDIT_CHAIN_TAMPER_FORENSICS.md)
  - `SOP-006`: [Zero-Downtime Secret Rotation](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/runbooks/SOP-006_ZERO_DOWNTIME_SECRET_ROTATION.md)
- **Master Final Project Report:** [`docs/enterprise/UNIMIND_AI_AEGISOPS_FINAL_MASTER_REPORT.md`](file:///c:/Users/kartik/Documents/unimind-ai/docs/enterprise/UNIMIND_AI_AEGISOPS_FINAL_MASTER_REPORT.md)

---
*Maintained by:* **UniMind AI + AegisOps Engineering Council**  
*Copyright © 2026. All Rights Reserved.*
