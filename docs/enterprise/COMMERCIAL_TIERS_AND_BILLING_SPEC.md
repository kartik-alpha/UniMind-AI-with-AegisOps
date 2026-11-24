# UniMind AI + AegisOps: Commercial Tiers & Billing Specification
**Version:** 1.0.0-PROD  
**Classification:** Commercial SaaS Product & Billing Engineering Specification  
**Effective Date:** 2026-11-20  

---

## 1. Commercial SaaS Subscription Tiers & Entitlements

The UniMind AI + AegisOps platform enforces strict multi-tenant entitlement gating across three commercial tiers: **Starter**, **Professional**, and **Enterprise**.

### 1.1 Entitlement Gating Matrix

| Entitlement Metric | Starter Tier | Professional Tier | Enterprise Tier |
| :--- | :--- | :--- | :--- |
| **Target Market** | Departments, Pilot Labs, Small Schools | Mid-Market Colleges, Divisions, Growing Enterprises | Global Universities, Healthcare Networks, Fortune 500 |
| **Monthly Subscription Base** | **$299 / month** | **$999 / month** | **$3,999 / month** |
| **Monthly LLM Token Allowance** | **500,000 Tokens (500K)** | **5,000,000 Tokens (5M)** | **Unlimited (Soft-Cap: 50M)** |
| **Token Overage Rate** | $0.003 / 1,000 tokens | $0.002 / 1,000 tokens | Custom Volume Discount |
| **Vector Storage Capacity** | **1 GB** (`1,073,741,824` Bytes) | **10 GB** (`10,737,418,240` Bytes) | **100 GB** (`107,374,182,400` Bytes) |
| **Vector Collection Isolation** | Logical Collection Partitioning (`knowledge_{tenant_id}`) | Dedicated Inverted Index & Vector Namespaces | Dedicated Encrypted Vector Node / Cluster |
| **Telemetry Retention Window** | **7 Days** Rolling Buffer | **30 Days** Historical Storage | **365 Days** Immutable Compliance Archive |
| **API Request Rate Limit** | 60 requests / minute | 300 requests / minute | 2,000 requests / minute |
| **User Seat Limit** | Up to 10 active seats | Up to 50 active seats | Up to 1,000 active seats |
| **AegisOps Incident Remediation** | Read-only telemetry alerting | Manual Human-in-the-Loop (HITL) Approval | Automated Closed-Loop & Controlled HITL |
| **Audit Log Provenance** | Standard Hash Chaining | Tamper-Evident SHA-256 Chain + HMAC | Real-Time WORM Export & Forensic Verification |
| **SLA Commitment** | 99.5% Monthly Uptime | 99.9% Monthly Uptime | 99.99% Enterprise Uptime with Financial Penalties |

---

## 2. Stripe-Compatible Billing Event & Webhook Data Models

The platform provides standard REST endpoints and webhook receivers for billing automation compatible with payment gateways (Stripe, Chargebee).

### 2.1 Webhook Ingestion Contract: `POST /api/v1/governance/billing/webhooks`

All inbound webhook events require cryptographic header signature verification:
- Header: `Stripe-Signature: t=1795368000,v1=5257a869e7ecebeda32affa62cdca3fa51cad7e77a0e56ff536d0ce8e108d8bd`

#### 2.1.1 Event: `customer.subscription.created`
Fires immediately when a new customer completes self-service checkout:
```json
{
  "id": "evt_sub_created_98234",
  "object": "event",
  "type": "customer.subscription.created",
  "created": 1795368000,
  "data": {
    "object": {
      "id": "sub_1Q2w3E4r5T",
      "customer": "cus_982341",
      "status": "active",
      "metadata": {
        "tenant_id": "14",
        "tenant_slug": "apex-institute",
        "subscription_tier": "PROFESSIONAL"
      },
      "items": {
        "data": [
          {
            "id": "si_12345",
            "price": {
              "id": "price_prof_monthly_999",
              "unit_amount": 99900,
              "currency": "usd"
            }
          }
        ]
      },
      "current_period_start": 1795368000,
      "current_period_end": 1797960000
    }
  }
}
```
**Platform Action:** Automatically executes `GovernanceService.onboard_tenant` or sets `status=ACTIVE` on the tenant organization with `PROFESSIONAL` quotas.

---

#### 2.1.2 Event: `invoice.payment_succeeded`
```json
{
  "id": "evt_inv_paid_87123",
  "object": "event",
  "type": "invoice.payment_succeeded",
  "created": 1797960000,
  "data": {
    "object": {
      "id": "in_123456789",
      "customer": "cus_982341",
      "amount_paid": 104500,
      "currency": "usd",
      "lines": {
        "data": [
          {
            "description": "UniMind Professional Tier (Monthly)",
            "amount": 99900
          },
          {
            "description": "LLM Token Overage (23,000 tokens @ $0.002/1k)",
            "amount": 4600
          }
        ]
      },
      "metadata": {
        "tenant_id": "14"
      }
    }
  }
}
```
**Platform Action:** Records `INVOICE_PAYMENT_SUCCEEDED` in the cryptographic audit chain and resets the tenant's monthly token consumption counter in the Redis cache adapter.

---

#### 2.1.3 Event: `invoice.payment_failed`
```json
{
  "id": "evt_inv_failed_34120",
  "object": "event",
  "type": "invoice.payment_failed",
  "created": 1797960000,
  "data": {
    "object": {
      "id": "in_987654321",
      "customer": "cus_982341",
      "amount_due": 99900,
      "attempt_count": 3,
      "metadata": {
        "tenant_id": "14"
      }
    }
  }
}
```
**Platform Action:** Executes `GovernanceService.transition_tenant_lifecycle(tenant_id=14, new_status="SUSPENDED")`, enforcing immediate API lockout and firing an alert to institutional administrators.

---

## 3. Usage Metering Contracts & Aggregation

### 3.1 Metering Endpoint: `GET /api/v1/governance/billing/usage`
Computes real-time tenant invoice projections:
```json
{
  "tenant_id": 14,
  "organization_name": "Apex Institute of Technology",
  "subscription_tier": "PROFESSIONAL",
  "currency": "USD",
  "billing_cycle": "2026-11",
  "base_monthly_price_usd": 999.0,
  "token_overage_charge_usd": 46.0,
  "estimated_total_due_usd": 1045.0,
  "sla_tier": "99.9% Standard SLA",
  "usage_breakdown": {
    "storage": {
      "used_bytes": 2147483648,
      "quota_bytes": 10737418240,
      "used_percentage": 20.0
    },
    "tokens": {
      "consumed_monthly": 5023000,
      "monthly_budget": 5000000,
      "overage_tokens": 23000
    },
    "seats": {
      "active_users": 18,
      "seat_limit": 50
    }
  }
}
```

---
*Maintained by:* **Commercial SaaS Architecture & Billing Engineering Council**
