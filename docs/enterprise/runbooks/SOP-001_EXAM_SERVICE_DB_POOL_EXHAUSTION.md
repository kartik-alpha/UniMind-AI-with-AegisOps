# Production Standard Operating Procedure (Runbook)
# SOP-001: Exam Service Database Connection Pool Exhaustion

**Document ID:** SOP-001-OPS-EXAM-POOL  
**Severity Tier:** P1 - CRITICAL  
**Service Impacted:** `exam_service`, Student Exam Scheduling & Online Assessment  
**Classification:** AegisOps SRE Automated & Manual Incident Remediation  
**Effective Date:** 2026-11-20  

---

## 1. Incident Overview & Symptoms

### 1.1 Symptoms
- AegisOps telemetry alerts indicate `db_pool_saturation` > 90% (often spiking to 99-100%).
- `latency_p95` on `exam_service` escalates from normal baseline (45 ms) to > 1,800 ms.
- Downstream services (`student_portal`, `auth_gateway`) report cascading connection timeouts (`HTTP 504 Gateway Timeout` or `500 Internal Server Error`).
- AegisOps Isolation Forest anomaly score exceeds `0.75` (Critical Anomaly).

### 1.2 Potential Root Causes
1. Spike in concurrent student examination submissions holding active transactions open.
2. Unindexed slow SQL queries executing in long-running transactions.
3. Database connection leaks in connection pool clients without proper `finally` pool releases.
4. Transient PostgreSQL network partition leaving orphan TCP sockets open.

---

## 2. Automated AegisOps Detection & Self-Healing Trigger

When AegisOps detects `exam_service` pool saturation:
1. An incident is automatically registered:
   - Incident Code: `INC-EXAM-POOL-XXXX`
   - Severity: `CRITICAL`
   - Detected Anomaly Score: `> 0.70`
2. Root Cause Analysis (RCA) engine correlates error spikes and recommends:
   - Action: `FLUSH_IDLE_CONNECTIONS`
   - Target Service: `exam_service`
   - Confidence: `0.95+`
3. If HITL (Human-in-the-Loop) policy is set to `MANUAL_APPROVAL`:
   - Incident moves to `PENDING_APPROVAL`.
   - On-call SRE receives immediate alert on AegisOps Incident Dashboard.

---

## 3. Human-in-the-Loop (HITL) Execution via AegisOps Console

### 3.1 Via AegisOps Frontend UI:
1. Navigate to **AegisOps Console** -> **Incidents & Remediation**.
2. Select incident `INC-EXAM-POOL-XXXX`.
3. Verify recommended action is `FLUSH_IDLE_CONNECTIONS`.
4. Click **"Approve & Execute Remediation"**.
5. Observe live execution logs and wait for automated health verification check.

### 3.2 Via API Endpoint (CLI / Automation):
```bash
curl -X POST "https://api.unimind.internal/api/v1/aegisops/remediate/approve" \
  -H "Authorization: Bearer $SRE_JWT_TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "incident_code": "INC-EXAM-POOL-XXXX",
    "action": "FLUSH_IDLE_CONNECTIONS",
    "target_service": "exam_service",
    "approved_by": "sre-engineer@enterprise.org"
  }'
```

---

## 4. Manual Fallback & Triage Procedures

If automated remediation fails or cannot connect to the service mesh:

### Step 1: Inspect Monitored Pods
```bash
kubectl get pods -n unimind-production -l app=exam-service
kubectl logs -n unimind-production -l app=exam-service --tail=200 | grep -E "pool|timeout|psycopg2"
```

### Step 2: Query Active Connections in PostgreSQL
Connect to the primary PostgreSQL replica:
```sql
SELECT pid, usename, client_addr, state, query_start, now() - query_start AS duration, query
FROM pg_stat_activity
WHERE datname = 'unimind_exam' AND state != 'idle'
ORDER BY duration DESC;
```

### Step 3: Terminate Idle In-Transaction Sessions
```sql
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = 'unimind_exam'
  AND state = 'idle in transaction'
  AND (now() - state_change) > interval '2 minutes';
```

### Step 4: Gracefully Scale or Restart Pods
If connections remain locked:
```bash
kubectl rollout restart deployment/exam-service -n unimind-production
kubectl rollout status deployment/exam-service -n unimind-production
```

---

## 5. Post-Remediation Verification Checklist

- [ ] `exam_service` database connection pool saturation dropped below 30%.
- [ ] Telemetry harvest latency p95 returns to < 100 ms.
- [ ] AegisOps anomaly score drops below 0.20.
- [ ] Transition incident state to `RESOLVED` in AegisOps.
- [ ] Verify SHA-256 audit log entry is recorded with actor ID and action `FLUSH_IDLE_CONNECTIONS`.
- [ ] File Jira/Linear postmortem ticket if downtime exceeded 60 seconds.

---
*Approved by:* **Enterprise SRE Operations Team**
