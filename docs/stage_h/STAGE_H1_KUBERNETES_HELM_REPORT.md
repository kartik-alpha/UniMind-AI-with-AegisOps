# STAGE H1 — KUBERNETES AND HELM CLOUD-READY DEPLOYMENT REPORT

**Milestone:** Stage H1 (Kubernetes & Helm Deployment Assets)  
**Date:** 2026-11-18  
**Author:** Principal Cloud Architect & Kubernetes Engineer  
**Status:** **CLOUD DEPLOYMENT PREPARED — LOCAL WORKSTATION PROTECTED**  

---

## 1. Executive Summary

Stage H1 delivers a complete, production-grade Kubernetes manifest suite and parameterized Helm chart for the UniMind AI + AegisOps platform. 

In strict adherence to the hardware resource policy (Windows 11 with 7.71 GB usable RAM), a local Kubernetes cluster (Minikube/Kind/k3s) was **not** spawned. Local development remains natively anchored in the FastAPI/React runtime with Docker Compose named profiles. The Kubernetes deployment assets are fully parameterized across multi-environment value overlays.

---

## 2. Helm Chart Architecture (`helm/unimind-ai/`)

The chart structure conforms to Helm v2/v3 specifications:

```
helm/unimind-ai/
├── Chart.yaml                  (Chart metadata, version 1.0.0)
├── values.yaml                 (Default base configuration)
├── values.local.yaml           (Single-node local development overrides)
├── values.staging.yaml         (Single-host staging with distributed services)
├── values.production.yaml      (Multi-node HA cluster with TLS & HPA)
└── templates/
    ├── _helpers.tpl            (Template macro definitions)
    ├── configmap.yaml          (Backend & infrastructure environment parameters)
    ├── secrets.yaml            (Kubernetes opaque secrets for credentials)
    ├── backend-deployment.yaml (FastAPI deployment with non-root security context)
    ├── backend-service.yaml    (ClusterIP service for API routing)
    ├── frontend-deployment.yaml(Nginx static React SPA deployment)
    ├── frontend-service.yaml   (ClusterIP service for Web UI)
    ├── ingress.yaml            (Ingress with path routing & cert-manager TLS)
    ├── hpa.yaml                (HorizontalPodAutoscaler for CPU & Memory triggers)
    ├── networkpolicy.yaml      (Network isolation denying unauthorized egress)
    ├── pdb.yaml                (PodDisruptionBudget preventing eviction outages)
    └── pvc.yaml                (PersistentVolumeClaim for local state retention)
```

---

## 3. Security, High-Availability & Resource Controls

### 3.1 Security Hardening
- **Non-Root Execution:** Backend runs under UID/GID `10001:10001` with `runAsNonRoot: true`. Frontend runs under UID/GID `101:101`.
- **Network Policies:** Ingress restricted to the cluster namespace; egress restricted strictly to DNS (port 53), PostgreSQL (port 5432), Qdrant (port 6333), Redis (port 6379), and MinIO (port 9000).
- **Probes:** Configured `/health/live` and deep-check `/health/ready` probes with configurable failure thresholds.

### 3.2 Autoscaling & Reliability
- **HPA Policy:** Production autoscaling from 4 to 16 replicas triggered at 70% average CPU or 75% average memory utilization.
- **PDB:** Minimum 2 available replicas in production during node drains or rolling upgrades.
- **Zero-Downtime Rollouts:** Configured `RollingUpdate` with `maxSurge: 1` and `maxUnavailable: 0`.

---

## 4. Environment Matrix Comparison

| Parameter | Local (`values.local.yaml`) | Staging (`values.staging.yaml`) | Production (`values.production.yaml`) |
| :--- | :--- | :--- | :--- |
| **Backend Replicas** | 1 | 2 | 4 (autoscale to 16) |
| **Frontend Replicas** | 1 | 2 | 3 |
| **Database Backend** | SQLite (embedded) | PostgreSQL (single) | Patroni Clustered PostgreSQL HA |
| **Vector Backend** | ChromaDB (local) | Qdrant (standalone) | Distributed Qdrant Cluster |
| **Cache Backend** | In-Memory (LRU) | Redis (standalone) | Redis Sentinel / Cluster |
| **Storage Backend** | Local Filesystem | MinIO (standalone) | S3 / Multi-Region Object Store |
| **TLS** | Disabled | Staging CA | Let's Encrypt Production / Vault |
| **Memory Limit/Pod** | 450 Mi | 650 Mi | 750 Mi |

---

## 5. Deployment & Rollback Commands

### Deployment:
```bash
# Staging deployment
helm upgrade --install unimind-staging ./helm/unimind-ai \
  --namespace unimind-staging --create-namespace \
  -f ./helm/unimind-ai/values.staging.yaml

# Production deployment
helm upgrade --install unimind-prod ./helm/unimind-ai \
  --namespace unimind-prod --create-namespace \
  -f ./helm/unimind-ai/values.production.yaml
```

### Rollback:
```bash
# View release history
helm history unimind-prod -n unimind-prod

# Roll back to previous revision
helm rollback unimind-prod 1 -n unimind-prod
```
