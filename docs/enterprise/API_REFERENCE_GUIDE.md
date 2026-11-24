# UniMind AI + AegisOps: Enterprise API Reference Guide
**Version:** 1.0.0-PROD  
**Classification:** Enterprise SaaS Technical Documentation  
**Base URL:** `https://api.unimind.internal/api/v1` (Production) / `http://localhost:8000/api/v1` (Development)  

---

## 1. Authentication & Tenant Context Specification

All requests to the UniMind AI + AegisOps platform require two standard headers:
1. `Authorization: Bearer <JWT_TOKEN>`: Cryptographically signed token verifying identity, organization memberships, and role (`student`, `faculty`, `sre_admin`, `tenant_admin`).
2. `X-Tenant-ID: <TENANT_ID>`: Mandatory multi-tenant identifier (e.g. `unimind-university`, `apex-institute`, `st-jude-health`).

### Error Format: RFC 7807 Problem Details
All non-2xx responses return standard RFC 7807 problem details:
```json
{
  "type": "https://errors.unimind.ai/INSUFFICIENT_TENANT_PERMISSIONS",
  "title": "Insufficient Tenant Permissions",
  "status": 403,
  "detail": "User token does not permit access to tenant 'apex-institute'.",
  "instance": "/api/v1/assistant/chat",
  "error_code": "INSUFFICIENT_TENANT_PERMISSIONS",
  "timestamp": "2026-11-20T14:22:01.123456Z"
}
```

---

## 2. API Endpoint Directory

### 2.1 Authentication Endpoints

#### `POST /auth/login`
Authenticates user credentials and issues a multi-tenant scoped JWT.
- **Request Body:**
  ```json
  {
    "username": "student@unimind.edu",
    "password": "SecurePassword123!"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "access_token": "eyJhbGciOi...",
    "token_type": "bearer",
    "expires_in": 86400,
    "user": {
      "id": 12,
      "username": "student@unimind.edu",
      "role": "student",
      "tenant_ids": ["unimind-university"]
    }
  }
  ```

#### `GET /auth/me`
Retrieves identity profile and accessible tenant organizations for the currently authenticated caller.

---

### 2.2 UniMind AI Engine Endpoints

#### `POST /assistant/chat` (Unary Grounded Completion)
Performs Hybrid RAG retrieval (Dense + BM25 + RRF) and returns a grounded answer with citations.
- **Headers:** `Authorization`, `X-Tenant-ID`
- **Request Body:**
  ```json
  {
    "query": "What is the policy for dropping a course before the midterm?",
    "mode": "hybrid",
    "top_k": 4
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "query": "What is the policy for dropping a course before the midterm?",
    "answer": "Courses may be dropped without academic penalty up to the 4th week of instruction...",
    "confidence": 0.94,
    "grounding_verified": true,
    "retrieval_mode": "hybrid_dense_bm25_rrf",
    "citations": [
      {
        "document_id": "doc-acad-policy-2026",
        "title": "Academic Policies Handbook 2026",
        "section": "Course Withdrawal & Deadlines",
        "match_score": 0.92,
        "text_snippet": "Section 4.2: Course withdrawal deadline is Friday of Week 4."
      }
    ],
    "timing_ms": {
      "retrieval": 42.1,
      "synthesis": 650.4,
      "total": 692.5
    }
  }
  ```

#### `POST /assistant/chat/stream` (Server-Sent Events Streaming)
Streams tokens in real time via Server-Sent Events (SSE).
- **Format:** `text/event-stream`
- **Event Chunks:**
  ```
  data: {"token": "Courses", "done": false}
  data: {"token": " may", "done": false}
  data: {"token": " be", "done": false}
  ...
  data: {"done": true, "citations": [...], "grounding_verified": true, "confidence": 0.94}
  ```

---

### 2.3 AegisOps Autonomous SRE Engine Endpoints

#### `POST /aegisops/telemetry`
Ingests metric time-series frames and executes real-time ML anomaly scoring.
- **Request Body:**
  ```json
  {
    "service_name": "exam_service",
    "cpu_percent": 96.5,
    "memory_percent": 82.1,
    "latency_p95_ms": 1850.0,
    "error_rate_percent": 14.2,
    "db_pool_saturation": 99.1
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "service_name": "exam_service",
    "is_anomaly": true,
    "anomaly_score": 0.842,
    "incident_triggered": true,
    "incident_code": "INC-82910"
  }
  ```

#### `GET /aegisops/incidents`
Lists all SRE incidents with optional filtering by `status`, `severity`, or `service`.

#### `POST /aegisops/incidents/{incident_id}/transition`
Transitions incident state machine (`OPEN` -> `INVESTIGATING` -> `PENDING_APPROVAL` -> `RESOLVED` -> `CLOSED`).
- **Request Body:** `{"status": "INVESTIGATING", "notes": "Triaging connection pool leak."}`

#### `POST /aegisops/remediate/approve` (HITL Remediation)
Authorizes and dispatches an autonomous remediation action.
- **Request Body:**
  ```json
  {
    "incident_code": "INC-82910",
    "action": "FLUSH_IDLE_CONNECTIONS",
    "target_service": "exam_service",
    "approved_by": "sre-engineer@enterprise.org"
  }
  ```
- **Response (200 OK):**
  ```json
  {
    "status": "RESOLVED",
    "verified_recovery": true,
    "post_health_anomaly_score": 0.08,
    "execution_log": "Connection pool successfully flushed. 42 idle connections pruned. Service latency normal."
  }
  ```

---

### 2.4 Multi-Tenant Governance & Cryptographic Audit Endpoints

#### `GET /governance/audit/verify-chain`
Performs cryptographic verification of the SHA-256 audit hash chain for the active tenant context.
- **Response (200 OK):**
  ```json
  {
    "is_valid": true,
    "tenant_id": "unimind-university",
    "tampered": false,
    "tampered_record_id": null,
    "total_records_checked": 265,
    "head_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    "verified_at": "2026-11-20T14:45:00.000000Z"
  }
  ```

#### `GET /governance/quota`
Returns active API quotas, usage counters, and remaining requests for the tenant.

---

## 3. Client SDK Code Examples

### 3.1 Python SDK Example (Using `httpx`)
```python
import httpx
import json

BASE_URL = "https://api.unimind.internal/api/v1"
HEADERS = {
    "Authorization": "Bearer eyJhbGciOi...",
    "X-Tenant-ID": "unimind-university",
    "Content-Type": "application/json"
}

def stream_assistant_response(query: str):
    with httpx.Client(timeout=30.0) as client:
        with client.stream(
            "POST",
            f"{BASE_URL}/assistant/chat/stream",
            headers=HEADERS,
            json={"query": query, "mode": "hybrid"}
        ) as response:
            for line in response.iter_lines():
                if line.startswith("data: "):
                    payload = json.loads(line[6:])
                    if not payload.get("done"):
                        print(payload.get("token", ""), end="", flush=True)
                    else:
                        print(f"\n[Completed with Confidence: {payload.get('confidence')}]")

if __name__ == "__main__":
    stream_assistant_response("How do I register for fall semester courses?")
```

### 3.2 TypeScript / React Example (Fetch API Stream)
```typescript
interface StreamChunk {
  token?: string;
  done: boolean;
  confidence?: number;
  citations?: Array<{ document_id: string; title: string; match_score: number }>;
}

export async function queryAssistantStream(
  query: string,
  onToken: (token: string) => void,
  onComplete: (metadata: StreamChunk) => void
): Promise<void> {
  const response = await fetch("https://api.unimind.internal/api/v1/assistant/chat/stream", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${localStorage.getItem("token")}`,
      "X-Tenant-ID": localStorage.getItem("tenantId") || "unimind-university",
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ query, mode: "hybrid" })
  });

  const reader = response.body?.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (reader) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const chunk: StreamChunk = JSON.parse(line.slice(6));
        if (chunk.done) {
          onComplete(chunk);
        } else if (chunk.token) {
          onToken(chunk.token);
        }
      }
    }
  }
}
```

---
*Maintained by:* **Enterprise API & Integration Architecture Council**
