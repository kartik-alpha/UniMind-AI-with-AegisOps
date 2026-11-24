# STAGE H0 — BACKUP, PRESERVATION & ROLLBACK PLAN

**Milestone:** Stage H  
**Date:** 2026-11-18  
**Scope:** Reversible Migrations, Disaster Recovery, and Low-Storage Preservation  

---

## 1. Principles of Preservation & Reversibility

1. **Zero-Destruction Guarantee:** Original Stage A–G databases (`unimind.db`), ChromaDB collections (`data/chroma_db`), and model artifacts (`ml/models/isolation_forest.joblib`) are never overwritten, dropped, or migrated in-place.
2. **Read-Only Migration Testing:** Any schema or vector migration testing to PostgreSQL or Qdrant must be performed on isolated test copies or test containers.
3. **Graceful Fallback:** If any distributed service (PostgreSQL, Qdrant, Redis, MinIO) is unconfigured, unreachable, or stopped, the platform automatically falls back to its corresponding local in-process adapter (`LocalStorageAdapter`, `LocalChromaAdapter`, `LocalInMemoryCacheBroker`, SQLite).

---

## 2. Snapshot Verification

The Stage G baseline snapshot has been recorded under `backups/stage_g_baseline/`:

```
backups/stage_g_baseline/
├── unimind.db                 (Primary Relational Store - 9 tables)
├── isolation_forest.joblib    (ML Anomaly Detection Model - SHA-256 c271522...)
└── chroma_db/                 (Persistent Vector Collections - 8 university chunks)
```
- **Total Backup Size:** 5.31 MB
- **Verification Command:**
  ```powershell
  .venv\Scripts\python.exe -c "import hashlib; assert hashlib.sha256(open('backups/stage_g_baseline/isolation_forest.joblib', 'rb').read()).hexdigest() == 'c2715221415485b2c3956f71625d244d554281a44911f1d49fe8b0c170ff5b20'"
  ```

---

## 3. Explicit Step-by-Step Rollback Procedures

### 3.1 Relational Database Rollback (PostgreSQL -> SQLite)
If a PostgreSQL migration introduces schema discrepancies or operational instability:
1. Revert environment variable in `.env`:
   ```bash
   DATABASE_BACKEND=sqlite
   DATABASE_URL=sqlite:///./unimind.db
   ```
2. If `backend/unimind.db` was touched, restore from baseline snapshot:
   ```powershell
   Copy-Item -Force backups\stage_g_baseline\unimind.db backend\unimind.db
   ```
3. Restart application. All user accounts, tickets, organizations, and incidents immediately revert to the verified Stage G state.

### 3.2 Vector Database Rollback (Qdrant -> ChromaDB)
If Qdrant indexing fails or causes search latency regressions:
1. Revert environment variable in `.env`:
   ```bash
   VECTOR_BACKEND=chroma
   ```
2. Restore ChromaDB persistent store if needed:
   ```powershell
   Copy-Item -Recurse -Force backups\stage_g_baseline\chroma_db\* data\chroma_db\
   ```
3. Run RAG verification tests (`pytest tests/unit/test_improved_rag.py`) to confirm 100% chunk accessibility.

### 3.3 Cache & Object Storage Rollback
1. Revert cache broker: `CACHE_BACKEND=memory`
2. Revert object storage: `STORAGE_BACKEND=local`
3. Application instantly runs with zero external network socket requirements.

### 3.4 Git Working-Tree Rollback
To roll back Stage H branch changes without affecting Stage G:
```powershell
git checkout main
```
The `main` branch remains permanently anchored at the formally approved Stage G baseline.
