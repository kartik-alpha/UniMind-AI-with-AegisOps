# Production Standard Operating Procedure (Runbook)
# SOP-002: LMS High Memory Saturation & Cache Stall

**Document ID:** SOP-002-OPS-LMS-MEM  
**Severity Tier:** P2 - HIGH  
**Service Impacted:** `lms_service`, Course Management & Content Delivery  
**Classification:** AegisOps SRE Automated & Manual Incident Remediation  
**Effective Date:** 2026-11-20  

---

## 1. Incident Overview & Symptoms

### 1.1 Symptoms
- AegisOps telemetry alerts indicate `memory_utilization` > 88% (climbing towards 95-98%).
- `lms_service` container memory limits triggered; risk of Linux Kernel Out-Of-Memory (OOM) killer terminations (`ExitCode: 137`).
- Redis cache hit ratio drops below 60%; cache latency spikes from 1.2 ms to > 45 ms.
- AegisOps Isolation Forest anomaly score exceeds `0.72`.

### 1.2 Potential Root Causes
1. Unbounded in-memory caching of high-resolution PDF lecture notes and course assets.
2. Inefficient serialization of course roster objects containing nested grading records.
3. Redis memory eviction policy set to `noeviction` instead of `volatile-lru`.
4. PyTorch / sentence-transformer embedding tensors failing to deallocate memory after document parsing.

---

## 2. Automated AegisOps Detection & Self-Healing Trigger

When AegisOps detects `lms_service` memory saturation:
1. Incident registered: `INC-LMS-MEM-XXXX`, Severity: `HIGH`.
2. AI Root Cause Analysis diagnoses memory leak / cache stall and recommends:
   - Action: `RESTART_POD` (Graceful Rolling Restart) or `PURGE_SERVICE_CACHE`.
   - Confidence: `0.92+`.
3. HITL workflow prompts SRE for approval or automatically executes if automated remediation policy is enabled for P2 events.

---

## 3. Human-in-the-Loop (HITL) Execution via AegisOps Console

### 3.1 Via AegisOps Frontend UI:
1. Open **AegisOps Console** -> **Remediation Management**.
2. Locate incident `INC-LMS-MEM-XXXX`.
3. Review target pods and memory trajectory graph.
4. Click **"Approve & Execute Remediation"** (`RESTART_POD`).
5. Monitor zero-downtime rolling restart progress.

### 3.2 Via API Endpoint:
```bash
curl -X POST "https://api.unimind.internal/api/v1/aegisops/remediate/approve" \
  -H "Authorization: Bearer $SRE_JWT_TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "incident_code": "INC-LMS-MEM-XXXX",
    "action": "RESTART_POD",
    "target_service": "lms_service",
    "approved_by": "sre-engineer@enterprise.org"
  }'
```

---

## 4. Manual Fallback & Triage Procedures

### Step 1: Check Pod Memory Usage and OOM Events
```bash
kubectl top pods -n unimind-production -l app=lms-service
kubectl describe pods -n unimind-production -l app=lms-service | grep -E "OOMKilled|Last State"
```

### Step 2: Trigger Kubernetes Rolling Restart
```bash
kubectl rollout restart deployment/lms-service -n unimind-production
kubectl rollout status deployment/lms-service -n unimind-production --timeout=180s
```

### Step 3: Flush Stale Cache Keys in Redis
```bash
redis-cli -h redis.unimind-production.svc.cluster.local -p 6379 -a "$REDIS_PASSWORD" EVAL "
local keys = redis.call('keys', 'lms:cache:*')
for i,k in ipairs(keys) do
    redis.call('del', k)
end
return #keys
" 0
```

---

## 5. Post-Remediation Verification Checklist

- [ ] `lms_service` memory drops below 45% post-restart.
- [ ] No pods in `CrashLoopBackOff` or `OOMKilled` state.
- [ ] AegisOps anomaly score returns to baseline (< 0.15).
- [ ] Response latency p95 < 120 ms.
- [ ] Incident transitioned to `RESOLVED` in AegisOps.
- [ ] Audit log hash chained entry verified.

---
*Approved by:* **Enterprise SRE Operations Team**
