# STAGE H — MASTER HYBRID DISTRIBUTED INFRASTRUCTURE ARCHITECTURE

**Platform:** UniMind AI + AegisOps Unified Enterprise Platform  
**Target Milestone:** Stage H (H0 through H5)  
**Execution Mode:** Local-First Low-Resource Development & Cloud-Ready Distributed Architecture  
**Hardware Baseline:** Windows 11 / Intel i5-12450H / 8 GB RAM / 54+ GB Free Disk  
**Status:** **LOCAL DEVELOPMENT VERIFIED & CLOUD DEPLOYMENT PREPARED**  

---

## 1. Executive Architectural Blueprint

Stage H evolves the formally accepted Stage G monolithic baseline into a **Hardware-Optimized Hybrid Distributed Architecture**. The architecture explicitly decouples the core domain and API layer from concrete infrastructure implementations using Hexagonal Architecture (Ports and Adapters).

```
                      ┌──────────────────────────────────────────────┐
                      │    FastAPI Application Core / API Routers    │
                      │ (UniMind RAG, AegisOps, Governance, Twin)    │
                      └──────────────────────┬───────────────────────┘
                                             │
                       ┌─────────────────────┴─────────────────────┐
                       │               AdapterFactory              │
                       └─┬─────────────┬─────────────┬───────────┬─┘
                         │             │             │           │
         ┌───────────────┘             │             │           └───────────────┐
         ▼                             ▼             ▼                           ▼
┌──────────────────┐          ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
│ DatabaseAdapter  │          │  VectorAdapter   │  │CacheBrokerAdapter│  │  StorageAdapter  │
└────────┬─────────┘          └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
         │                             │                     │                     │
    ┌────┴────┐                   ┌────┴────┐           ┌────┴────┐           ┌────┴────┐
    ▼         ▼                   ▼         ▼           ▼         ▼           ▼         ▼
┌───────┐ ┌────────┐         ┌────────┐ ┌──────┐    ┌────────┐ ┌─────┐    ┌───────┐ ┌───────┐
│SQLite │ │Postgres│         │ChromaDB│ │Qdrant│    │In-Mem  │ │Redis│    │LocalFS│ │S3/MinIO│
└───────┘ └────────┘         └────────┘ └──────┘    └────────┘ └─────┘    └───────┘ └───────┘
  (Local)   (Cloud)            (Local)   (Cloud)      (Local)   (Cloud)     (Local)   (Cloud)
```

---

## 2. Environment Dual-Topology

### 2.1 Environment A — Local Development (Low-Resource Mode)
- **Host Target:** Windows 11 with 8 GB physical RAM and limited SSD headroom ($> 54$ GB free).
- **Core Engine:** Single FastAPI process with Uvicorn, local React/Vite server.
- **Persistence & Adapters:**
  - Relational: `SQLiteDatabaseAdapter` running `backend/unimind.db` with WAL mode.
  - Vector: `LocalChromaAdapter` managing embedded ChromaDB collections (`data/chroma_db`).
  - Cache & Rate Limiting: `LocalInMemoryCacheBroker` with 10,000-key LRU cap ($< 25$ MB).
  - Storage: `LocalStorageAdapter` with tenant folder jail (`data/tenants/{id}/`).
- **Compose Profile Isolation:** When testing distributed services, containers are started individually via Docker Compose profiles (`postgres`, `qdrant`, `redis`, `minio`).

### 2.2 Environment B — Cloud / Production (Enterprise High Availability)
- **Host Target:** Multi-node Kubernetes cluster (AWS EKS, GCP GKE, or Bare-Metal).
- **Orchestration:** Helm chart ([helm/unimind-ai/](file:///c:/Users/kartik/Documents/unimind-ai/helm/unimind-ai)) managing Deployments, Ingress, HPA, NetworkPolicies, and PDBs.
- **Persistence & Adapters:**
  - Relational: Patroni 3-node PostgreSQL HA cluster with automated streaming failover.
  - Vector: Distributed Qdrant cluster with cosine distance and payload metadata filtering.
  - Cache: Redis Sentinel HA (1 Master, 2 Replicas, 3 Sentinels) or Redis Cluster.
  - Storage: Multi-Region S3 bucket with client-side SHA-256 integrity checks and SSE-S3 encryption.

---

## 3. Centralized Configuration & Dynamic Routing

All backend adapters are dynamically configured via environment variables with safe monolithic defaults:

```bash
# Centralized Backend Selection
DATABASE_BACKEND=sqlite      # [sqlite | postgres]
VECTOR_BACKEND=chroma        # [chroma | qdrant]
CACHE_BACKEND=memory         # [memory | redis]
STORAGE_BACKEND=local        # [local | s3 | minio]
APP_ENV=development          # [development | staging | production]
```

If an external service is offline or unreachable, the system automatically falls back to its local adapter without crashing the user application.
