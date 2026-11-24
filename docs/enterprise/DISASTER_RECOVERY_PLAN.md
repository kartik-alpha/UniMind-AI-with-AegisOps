# UniMind AI + AegisOps: Enterprise Disaster Recovery (DR) Plan
**Classification:** Business Continuity & Infrastructure Disaster Recovery  
**Target RTO:** < 15 Minutes (Recovery Time Objective)  
**Target RPO:** < 1 Minute (Recovery Point Objective)  
**Effective Date:** 2026-11-20  
**Version:** 1.0.0-PROD  

---

## 1. Executive Summary & DR Objectives

This Disaster Recovery (DR) Plan defines the strategies, architectures, failover mechanisms, and recovery runbooks required to maintain business continuity for the **UniMind AI + AegisOps Unified Enterprise Platform**.

### Key Disaster Recovery Metrics
- **Recovery Time Objective (RTO):** Maximum acceptable duration between declaration of a disaster and the restoration of full production service availability.  
  **Standard RTO:** `< 15 Minutes`.
- **Recovery Point Objective (RPO):** Maximum acceptable age of data that must be recovered from backup storage when normal computer operations are restored.  
  **Standard RPO:** `< 1 Minute` (via continuous PostgreSQL WAL streaming and replicated vector snapshots).

---

## 2. Disaster Classification & Tiers

| Tier | Disaster Scenario | Impact Radius | Primary Recovery Mechanism | Target RTO | Target RPO |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Tier 1** | Single Pod / Process Crash | Node / Container | Kubernetes Automated Self-Healing (ReplicaSet / Liveness) | < 30 seconds | 0 seconds |
| **Tier 2** | Availability Zone (AZ) Outage | 1 Cloud Data Center | Multi-AZ Kubernetes failover via Pod Anti-Affinity & Persistent Volumes | < 3 minutes | 0 seconds |
| **Tier 3** | Database Storage Corruption | Primary Database | Point-In-Time Recovery (PITR) from WAL stream + hourly base backup | < 12 minutes | < 1 minute |
| **Tier 4** | Complete Primary Cloud Region Failure | Full Cloud Region | Cross-Region Traffic Redirection via Route53 / Cloudflare DNS to Standby | < 15 minutes | < 1 minute |

---

## 3. High Availability & Data Replication Architecture

```mermaid
flowchart TD
    subgraph PrimaryRegion["Primary Cloud Region (e.g. us-east-1)"]
        Ingress1["Primary Ingress / API Gateway"]
        K8sPrimary["Kubernetes Compute Cluster (3 Backend Replicas)"]
        PGPrimary["PostgreSQL Primary (Read/Write)"]
        ChromaPrimary["ChromaDB Vector Volume (Read/Write)"]
        WALStreamer["WAL-G / Continuous WAL Archiver"]
    end

    subgraph CrossRegionStorage["Durable Object Storage (AWS S3 / GCS Multi-Region)"]
        S3Base["Hourly DB Base Backups (Encrypted KMS)"]
        S3WAL["Real-Time WAL Archive (< 1 min flush)"]
        S3Vector["Daily ChromaDB Vector Snapshots"]
        S3Audit["Immutable WORM Audit Hash Chain Archive"]
    end

    subgraph StandbyRegion["Secondary Standby Region (e.g. us-west-2)"]
        Ingress2["Standby Ingress / Warm Gateway"]
        K8sStandby["Kubernetes Standby Cluster (1 Minimal Replica)"]
        PGStandby["PostgreSQL Standby Replica (Continuous Streaming)"]
        ChromaStandby["ChromaDB Standby Volume (Warm Replicas)"]
    end

    PGPrimary -->|"Continuous Streaming WAL"| PGStandby
    PGPrimary -->|"WAL Archive Ship"| WALStreamer
    WALStreamer -->|"Push WAL Segment"| S3WAL
    PGPrimary -->|"Hourly Snapshot"| S3Base
    ChromaPrimary -->|"Hourly Sync"| S3Vector
    PGPrimary -->|"Audit Chain Export"| S3Audit

    S3Base -.->|"On-Demand Restore"| PGStandby
    S3WAL -.->|"Continuous Replay"| PGStandby
    S3Vector -.->|"Warm Sync"| ChromaStandby
```

---

## 4. Disaster Recovery Procedures & Failover Runbooks

### 4.1 Procedure A: Primary Database Failover (RTO < 3 min, RPO 0 sec)

If the primary PostgreSQL instance suffers hardware failure or crashes unrecoverably:
1. **Detect Failure:** AegisOps alerts `POSTGRESQL_CONNECTION_FAILURE` across all backend pods.
2. **Promote Standby Database:**
   ```bash
   # On secondary PostgreSQL replica pod:
   kubectl exec -it statefulset/postgres-replica -n unimind-production -- pg_ctl promote
   ```
3. **Re-point Application Services:**
   Update Kubernetes Service selector or backend `DATABASE_URL` secret:
   ```bash
   kubectl set env deployment/unimind-backend -n unimind-production DATABASE_URL="postgresql://unimind_user:$DB_PASS@postgres-standby.unimind-production.svc:5432/unimind_db"
   kubectl rollout restart deployment/unimind-backend -n unimind-production
   ```
4. **Verify Health:** Execute `GET /health` and verify HTTP 200 within 45 seconds.

---

### 4.2 Procedure B: Point-In-Time Database Recovery (PITR) from WAL (RTO < 12 min, RPO < 1 min)

If database tables suffer data corruption or malicious deletion:
1. **Isolate Database:** Stop backend ingestion immediately by scaling backend deployment to 0.
   ```bash
   kubectl scale deployment/unimind-backend --replicas=0 -n unimind-production
   ```
2. **Restore Base Backup:** Download the most recent hourly base backup from S3:
   ```bash
   wal-g backup-fetch /var/lib/postgresql/data LATEST
   ```
3. **Configure Recovery Target Time:**
   Create `/var/lib/postgresql/data/recovery.signal` and configure `postgresql.conf`:
   ```ini
   restore_command = 'wal-g wal-fetch "%f" "%p"'
   recovery_target_time = '2026-11-20 14:15:00 UTC'
   recovery_target_action = 'promote'
   ```
4. **Start PostgreSQL Instance:** Start PostgreSQL and monitor replay of WAL logs up to the recovery target time:
   ```bash
   kubectl logs -f statefulset/postgres-0 -n unimind-production
   ```
5. **Verify Audit Chain Integrity:**
   Run `scripts/verify_cross_tenant_security.py` and verify all 18 probes and audit hash chains are intact.
6. **Resume Compute:** Scale backend replicas back to 3:
   ```bash
   kubectl scale deployment/unimind-backend --replicas=3 -n unimind-production
   ```

---

### 4.3 Procedure C: ChromaDB Vector Volume Snapshot Recovery (RTO < 8 min)

If the persistent volume hosting vector embeddings is corrupted:
1. **Fetch Latest Vector Snapshot:**
   ```bash
   aws s3 sync s3://unimind-vector-backups/latest/ /data/vector_store/
   ```
2. **Validate Collection Dimensions:**
   ```bash
   python -c "
   import chromadb
   client = chromadb.PersistentClient(path='/data/vector_store')
   for col in client.list_collections():
       print(col.name, col.count())
   "
   ```
3. **Catch Up Incremental Documents:**
   Run incremental sync to embed any documents created between the snapshot timestamp and the present:
   ```bash
   python -m scripts.rebuild_vector_indices --since-snapshot
   ```

---

## 5. Multi-Tenant Data Export & Tenant Evacuation

In the event that an individual enterprise customer requests an emergency tenant-isolated data export or evacuation:
1. **Export Tenant Relational Records:**
   ```bash
   python scripts/export_tenant_data.py --tenant-id unimind-university --output /secure/exports/unimind_university_dr_export.json.gz
   ```
2. **Export Tenant Vector Embeddings:**
   ```bash
   python scripts/export_tenant_vectors.py --tenant-id unimind-university --output /secure/exports/unimind_university_vectors.tar.gz
   ```
3. **Verify Cryptographic Proofs:**
   Export tenant audit hash chain verification certificate confirming mathematical proof of zero tampering prior to disaster.

---

## 6. Disaster Recovery Drill Schedule & Governance

| Drill Type | Frequency | Target Metric | Procedure Executed | Sign-Off Authority |
| :--- | :--- | :--- | :--- | :--- |
| **Pod / Node Failure** | Bi-Weekly | RTO < 30s | ChaosMesh Pod Kill | SRE On-Call |
| **DB Standby Failover** | Monthly | RTO < 3 min, RPO 0 | Simulated Primary Crash & Promote | Lead Database Engineer |
| **PITR Cold Restore** | Quarterly | RTO < 15 min, RPO < 1 min | Full WAL Replay to Isolated Staging DB | Chief Architect |
| **Regional Evacuation** | Semi-Annually | RTO < 15 min | DNS Traffic Redirection to Standby Region | CISO & VP Engineering |

---
*Approved and Verified by:*  
**Chief Enterprise Architect, Head of SRE & CISO**
