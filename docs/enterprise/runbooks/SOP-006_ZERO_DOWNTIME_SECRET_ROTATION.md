# Production Standard Operating Procedure (Runbook)
# SOP-006: Zero-Downtime Secret Rotation

**Document ID:** SOP-006-SEC-SECRET-ROTATION  
**Severity Tier:** P2 - HIGH (Scheduled or Emergency Security Task)  
**Service Impacted:** All Services (`auth_service`, `db`, `jwt_secret`, `redis`)  
**Classification:** Enterprise Security & Infrastructure Operations  
**Effective Date:** 2026-11-20  

---

## 1. Scope & Rotation Targets

This runbook covers the scheduled quarterly and emergency rotation of:
1. **JWT Signature Keys (`JWT_SECRET_KEY`)**: Supports Dual-Key Verification during rotation window.
2. **Database Master Credentials (`DATABASE_URL`)**: Multi-user zero-downtime PostgreSQL role rotation.
3. **Redis Auth Tokens (`REDIS_PASSWORD`)**: Dual-auth password support.
4. **Third-Party API Keys (Gemini, HuggingFace)**: In-memory dynamic hot-reload.

---

## 2. Zero-Downtime JWT Secret Key Rotation (Dual-Key Pattern)

To avoid logging out thousands of active students during key rotation, the platform implements dual-key verification:
- `JWT_SECRET_KEY_PRIMARY`: Used to sign new tokens.
- `JWT_SECRET_KEY_FALLBACK`: Used to verify existing active tokens generated within the last 24 hours.

### Step 1: Generate Cryptographically Secure New Key
```bash
NEW_JWT_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(64))")
echo "New Key Generated: Length ${#NEW_JWT_SECRET} characters"
```

### Step 2: Update Kubernetes Secret
```bash
CURRENT_SECRET=$(kubectl get secret backend-secrets -n unimind-production -o jsonpath='{.data.JWT_SECRET_KEY}' | base64 -d)

kubectl create secret generic backend-secrets-next \
  --from-literal=JWT_SECRET_KEY="$NEW_JWT_SECRET" \
  --from-literal=JWT_SECRET_KEY_FALLBACK="$CURRENT_SECRET" \
  --dry-run=client -o yaml | kubectl apply -n unimind-production -f -
```

### Step 3: Trigger Rolling Deployment
```bash
kubectl rollout restart deployment/unimind-backend -n unimind-production
kubectl rollout status deployment/unimind-backend -n unimind-production --timeout=180s
```

### Step 4: Verify Token Acceptance
- Existing active tokens signed with `CURRENT_SECRET` must verify cleanly via fallback.
- Newly minted tokens signed with `NEW_JWT_SECRET` must verify cleanly.

### Step 5: Deprecate Fallback Key after 24 Hours (Token Expiry Window)
After all old tokens have naturally expired, remove `JWT_SECRET_KEY_FALLBACK` from Kubernetes secrets and restart.

---

## 3. Database Credential Rotation (PostgreSQL Dual-User Pattern)

### Step 1: Create New Database User Role
```sql
CREATE USER unimind_user_v2 WITH PASSWORD 'SuperSecretNewPassword2026!';
GRANT unimind_app_role TO unimind_user_v2;
```

### Step 2: Update Application Connection String
Update Kubernetes secret `DATABASE_URL` to point to `unimind_user_v2`:
```bash
kubectl set env deployment/unimind-backend -n unimind-production \
  DATABASE_URL="postgresql://unimind_user_v2:SuperSecretNewPassword2026!@postgres-primary:5432/unimind_db"
```

### Step 3: Verify Connections & Drop Deprecated User Role
Once all pods have transitioned to `unimind_user_v2`:
```sql
-- Ensure 0 connections remain on v1 user
SELECT count(*) FROM pg_stat_activity WHERE usename = 'unimind_user_v1';

-- Drop deprecated role
DROP USER unimind_user_v1;
```

---

## 4. Post-Rotation Verification Checklist

- [ ] All backend pods healthy (`kubectl get pods -n unimind-production`).
- [ ] Active sessions continue without forced re-logins.
- [ ] Database transactions executing normally without authentication errors.
- [ ] SHA-256 audit log records `SECRET_ROTATION_COMPLETED` with timestamp and operator ID.
- [ ] Old credentials revoked and confirmed defunct.

---
*Approved by:* **Chief Information Security Officer (CISO) & DevOps Lead**
