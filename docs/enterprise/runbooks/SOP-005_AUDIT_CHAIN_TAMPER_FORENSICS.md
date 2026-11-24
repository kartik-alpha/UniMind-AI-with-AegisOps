# Production Standard Operating Procedure (Runbook)
# SOP-005: Cryptographic Audit Hash Chain Tamper Forensics

**Document ID:** SOP-005-SEC-AUDIT-FORENSICS  
**Severity Tier:** P1 - CRITICAL (Security Incident)  
**Service Impacted:** `governance_service`, Audit Logging & Compliance  
**Classification:** Information Security & Digital Forensics  
**Effective Date:** 2026-11-20  

---

## 1. Incident Overview & Symptoms

### 1.1 Symptoms
- Periodic automated compliance check `/api/v1/governance/audit/verify-chain` returns `is_valid: False`.
- Security alert fired: `AUDIT_LOG_TAMPER_DETECTED: Tampered record ID X, Reason: Content tampering / Broken hash chain`.
- AegisOps marks security health badge as `COMPROMISED`.

### 1.2 Threat Models & Attack Vectors
1. Rogue database administrator or attacker with direct `UPDATE` / `DELETE` access to the `audit_logs` SQL table.
2. SQL injection exploit attempting to erase evidence of unauthorized privilege escalation or data export.
3. Storage medium corruption causing flipped bits in audit log records.

---

## 2. Automated Forensic Analysis via API

Run the forensic verification probe to pinpoint the exact record where the cryptographic chain was broken:
```bash
curl -X GET "https://api.unimind.internal/api/v1/governance/audit/verify-chain" \
  -H "Authorization: Bearer $SECURITY_OFFICER_JWT" \
  -H "X-Tenant-ID: $TENANT_ID"
```

Expected Response upon Tampering:
```json
{
  "status": "TAMPER_DETECTED",
  "is_valid": false,
  "tenant_id": "unimind-university",
  "tampered_record_id": 145,
  "reason": "Content tampering detected at record 145: hash mismatch",
  "expected_hash": "a4f8...b12",
  "stored_hash": "9c12...f88",
  "total_records_checked": 210,
  "tampered_at_utc": "2026-11-20T14:32:10.123456"
}
```

---

## 3. Forensic Triage & Evidence Collection Procedure

### Step 1: Freeze Current Database State
Immediately create a point-in-time forensic dump of the affected database without terminating running pods:
```bash
# On primary database pod
pg_dump -U unimind_user -d unimind_db -t audit_logs > /evidence/audit_logs_forensic_dump_$(date +%s).sql
```

### Step 2: Query WAL / Replication Logs
Examine PostgreSQL Write-Ahead Logs (WAL) for direct `UPDATE` or `DELETE` statements on `audit_logs`:
```sql
SELECT query, calls, total_exec_time 
FROM pg_stat_statements 
WHERE query ILIKE '%audit_logs%' AND (query ILIKE '%update%' OR query ILIKE '%delete%');
```
*Note: Under standard platform operation, `audit_logs` is strictly APPEND-ONLY. Any UPDATE or DELETE indicates unauthorized tampering.*

### Step 3: Compare with Cold Immutable Backup
Compare the compromised record with the last verified offsite S3 backup snapshot:
```bash
python scripts/forensic_compare_audit_snapshot.py \
  --live-record-id 145 \
  --backup-s3-uri s3://unimind-cold-audit-archive/2026-11-20/audit_logs.parquet
```

### Step 4: Isolate Compromised Database Credentials
1. Revoke the database role active during the tampering incident.
2. Rotate all database connection secrets immediately (Follow SOP-006).

---

## 4. Remediation & Chain Reconstruction

1. Confirm whether the discrepancy was caused by unauthorized tampering or disk corruption.
2. If malicious tampering is confirmed:
   - Quarantine affected database nodes.
   - Restore `audit_logs` from the verified write-once-read-many (WORM) storage archive.
   - Re-verify chain integrity from ID 1 to N.
3. Submit full forensic report to the Chief Information Security Officer (CISO).

---

## 5. Post-Remediation Verification Checklist

- [ ] `/api/v1/governance/audit/verify-chain` returns `is_valid: True` across 100% of tenants.
- [ ] Database credentials rotated and old tokens revoked.
- [ ] Forensic evidence sealed in WORM compliance vault.
- [ ] Compliance incident report compiled with timestamps and hash proofs.

---
*Approved by:* **Chief Information Security Officer (CISO)**
