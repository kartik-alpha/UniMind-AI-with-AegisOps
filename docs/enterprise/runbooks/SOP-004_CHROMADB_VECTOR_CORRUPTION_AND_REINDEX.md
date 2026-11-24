# Production Standard Operating Procedure (Runbook)
# SOP-004: ChromaDB Vector Store Corruption & Full Re-indexing

**Document ID:** SOP-004-OPS-CHROMA-REINDEX  
**Severity Tier:** P2 - HIGH  
**Service Impacted:** `unimind_ai_engine`, Hybrid RAG Dense Retrieval  
**Classification:** UniMind AI Engine Maintenance & Recovery  
**Effective Date:** 2026-11-20  

---

## 1. Incident Overview & Symptoms

### 1.1 Symptoms
- Assistant queries fail with `ChromaError: Index corrupted` or `SQLite header malformed` in `vector_store/chroma.sqlite3`.
- RAG retrieval falls back to sparse BM25-only retrieval, causing retrieval recall drop from 100% to ~70%.
- Log messages: `Failed to query dense vector index for tenant <TENANT_ID>`.
- Latency spikes on document search endpoints as vector queries hang until timeout.

### 1.2 Potential Root Causes
1. Unclean container termination during vector embedding batch insertion.
2. Underlying persistent volume storage corruption or IO bottleneck.
3. Schema or embedding dimension mismatch following embedding model version update.
4. Tenant collection metadata partition collision.

---

## 2. Automated Fallback Behavior

When ChromaDB dense retrieval fails:
1. The **Hybrid RAG Adapter** automatically catches the vector store exception.
2. Logs warning: `DENSE_SEARCH_UNAVAILABLE: falling back to pure BM25 lexical mode`.
3. Returns response to student with citation grounding, but appends `retrieval_mode: bm25_fallback` in metadata.
4. Fires AegisOps alert: `CHROMADB_INDEX_DEGRADATION` (Severity: HIGH).

---

## 3. Standard Remediation: Full Vector Re-indexing

### Step 1: Put Vector Ingestion in Maintenance Mode
```bash
curl -X POST "https://api.unimind.internal/api/v1/governance/maintenance" \
  -H "Authorization: Bearer $ADMIN_JWT_TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -d '{"service": "rag_ingestion", "status": "MAINTENANCE"}'
```

### Step 2: Backup Existing Chroma Directory
```bash
kubectl exec -it deployment/unimind-backend -n unimind-production -- /bin/bash -c "
  cp -r /app/data/vector_store /app/data/vector_store_corrupted_backup_\$(date +%Y%m%d%H%M%S)
"
```

### Step 3: Execute Automated Re-indexing Script
Run the platform re-indexing utility which iterates over all canonical source documents in the relational store and re-generates embeddings with `all-MiniLM-L6-v2`:
```bash
kubectl exec -it deployment/unimind-backend -n unimind-production -- python -m scripts.rebuild_vector_indices --tenant-id all --batch-size 64
```

### Step 4: Verify Collection Integrity & Embedding Dimension
```python
# Verification snippet executed inside container
from app.rag.hybrid_retriever import hybrid_retriever
stats = hybrid_retriever.get_tenant_collection_stats(tenant_id="unimind-university")
print(f"Collection count: {stats['document_count']}, Dimensions: {stats['dimension']}")
assert stats['document_count'] > 0
assert stats['dimension'] == 384
```

---

## 4. Post-Remediation Verification Checklist

- [ ] All tenant vector collections in ChromaDB are populated and healthy.
- [ ] Embedding dimension verified at 384 (`all-MiniLM-L6-v2`).
- [ ] Hybrid RAG retrieval latency p50 returns to < 800 ms.
- [ ] Groundedness score on benchmark test suite verified at > 0.90.
- [ ] Disable maintenance mode and notify tenant administrators.
- [ ] Chained audit log records `REBUILD_VECTOR_INDICES` action.

---
*Approved by:* **Enterprise AI/ML & SRE Teams**
