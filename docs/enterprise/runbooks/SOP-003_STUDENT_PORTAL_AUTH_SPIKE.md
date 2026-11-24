# Production Standard Operating Procedure (Runbook)
# SOP-003: Student Portal Authentication Spike & Rate Limiting

**Document ID:** SOP-003-OPS-PORTAL-AUTH  
**Severity Tier:** P1 - CRITICAL  
**Service Impacted:** `student_portal`, `auth_gateway`, Token Verification  
**Classification:** AegisOps SRE Automated & Manual Incident Remediation  
**Effective Date:** 2026-11-20  

---

## 1. Incident Overview & Symptoms

### 1.1 Symptoms
- Incoming login requests surge by 500% to 1000% within a 60-second window (e.g., during course registration or grade release).
- `auth_gateway` CPU utilization reaches > 92%.
- Influx of HTTP 429 (`Too Many Requests`) and HTTP 503 (`Service Unavailable`) errors.
- AegisOps anomaly score exceeds `0.78`.

### 1.2 Potential Root Causes
1. Legitimate high-concurrency student login stampede (flash crowd).
2. Distributed credential stuffing or brute-force authentication attack against `/api/v1/auth/login`.
3. Client-side retry storm caused by aggressive frontend refresh loops without exponential backoff.
4. Downstream LDAP / Identity Provider (IdP) connection saturation.

---

## 2. Automated AegisOps Detection & Mitigation

When AegisOps detects an authentication surge:
1. Incident registered: `INC-AUTH-SPIKE-XXXX`, Severity: `CRITICAL`.
2. Root Cause Analysis flags:
   - Primary: High CPU / Ingress saturation on `student_portal` / `auth_gateway`.
   - Secondary: Elevated rate limit rejections.
3. Recommended Action: `SCALE_DEPLOYMENT` (Autoscale replicas from 3 to 8).
4. If attack pattern is detected (e.g. repeated failed logins from specific IP CIDR blocks):
   - Action: `APPLY_RATE_LIMIT_RULE` via Redis token bucket.

---

## 3. Human-in-the-Loop (HITL) Execution via AegisOps Console

### 3.1 Via AegisOps Frontend UI:
1. Open **AegisOps Console** -> **Incidents**.
2. Select `INC-AUTH-SPIKE-XXXX`.
3. Verify recommended action is `SCALE_DEPLOYMENT`.
4. Click **"Approve & Execute Remediation"**.
5. Observe HPA / Deployment replica expansion in real time.

### 3.2 Via API Endpoint:
```bash
curl -X POST "https://api.unimind.internal/api/v1/aegisops/remediate/approve" \
  -H "Authorization: Bearer $SRE_JWT_TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{
    "incident_code": "INC-AUTH-SPIKE-XXXX",
    "action": "SCALE_DEPLOYMENT",
    "target_service": "student_portal",
    "approved_by": "sre-engineer@enterprise.org"
  }'
```

---

## 4. Manual Fallback & Triage Procedures

### Step 1: Immediate Scale-Out via Kubectl
```bash
kubectl scale deployment/unimind-backend --replicas=8 -n unimind-production
kubectl get hpa backend-hpa -n unimind-production
```

### Step 2: Inspect NGINX Ingress Rate-Limiting Metrics
```bash
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=500 | grep "limiting requests"
```

### Step 3: Temporary WAF / IP Rate Limit Throttling
If a DDoS or credential stuffing attack is in progress, tighten Redis rate limit thresholds dynamically:
```bash
# Set temporary IP rate limit to 10 requests/minute per client IP
curl -X POST "https://api.unimind.internal/api/v1/governance/quota/override" \
  -H "Authorization: Bearer $ADMIN_JWT_TOKEN" \
  -H "X-Tenant-ID: $TENANT_ID" \
  -H "Content-Type: application/json" \
  -d '{"endpoint": "/api/v1/auth/login", "max_requests_per_minute": 10}'
```

---

## 5. Post-Remediation Verification Checklist

- [ ] CPU utilization on backend pods drops below 60%.
- [ ] P95 response latency on `/api/v1/auth/login` normalizes to < 80 ms.
- [ ] Error rate on student portal returns to < 0.1%.
- [ ] Incident transitioned to `RESOLVED` in AegisOps.
- [ ] Cryptographic audit log confirms scaling operation with actor ID.

---
*Approved by:* **Enterprise SRE Operations Team**
