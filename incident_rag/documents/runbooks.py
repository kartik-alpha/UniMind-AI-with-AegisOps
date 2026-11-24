RUNBOOKS_KNOWLEDGE = [
    {
        "id": "runbook-001",
        "service": "exam-service",
        "scenario": "DB_CONNECTION_EXHAUSTION",
        "title": "Exam Service High Latency & Pool Exhaustion Runbook",
        "content": """
        SYMPTOMS: High CPU (>90%), Latency (>1500ms), 503 error spikes, Database connection pool timeout log errors.
        ROOT CAUSE: Heavy concurrent exam submissions leading to database connection pool exhaustion.
        RECOMMENDED REMEDIATION:
        1. Restart exam-service pod to clear stale database pool handles.
        2. Scale deployment replicas from 2 to 4 to distribute incoming traffic load.
        VERIFICATION: Monitor latency drops below 200ms and CPU returns to <35%.
        """,
    },
    {
        "id": "runbook-002",
        "service": "lms",
        "scenario": "MEMORY_PRESSURE",
        "title": "LMS Memory Pressure & Cgroup OOM Runbook",
        "content": """
        SYMPTOMS: Memory usage (>85%), GC pauses (>1000ms), elevated latency.
        ROOT CAUSE: Redis cache eviction queue stall during assignment submission deadlines.
        RECOMMENDED REMEDIATION:
        1. Restart LMS pod deployment to flush bloated in-memory application buffers.
        2. Verify memory consumption stabilizes below 50%.
        """,
    },
    {
        "id": "runbook-003",
        "service": "any",
        "scenario": "CPU_SATURATION",
        "title": "Service CPU Saturation & CFS Quota Throttling Runbook",
        "content": """
        SYMPTOMS: Sustained CPU utilization (>90%), request queue depth growth, increased p99 latency.
        ROOT CAUSE: Computational bottleneck or unoptimized loop execution causing container CPU throttling.
        RECOMMENDED REMEDIATION:
        1. Scale deployment replicas to horizontal auto-scaling ceiling.
        2. Trigger controlled rolling restart of hot pods.
        VERIFICATION: Confirm CPU drops below 40% and latency normalizes.
        """,
    },
    {
        "id": "runbook-004",
        "service": "any",
        "scenario": "NETWORK_LATENCY",
        "title": "Microservice Inter-Service Network Latency Runbook",
        "content": """
        SYMPTOMS: p95 latency spikes (>2000ms), socket read timeouts, HTTP 504 Gateway Timeouts.
        ROOT CAUSE: Cross-zone routing latency or connection keep-alive exhaustion on internal service mesh.
        RECOMMENDED REMEDIATION:
        1. Restart affected service pods to refresh connection keep-alive pools.
        2. Verify inter-service latency drops below 150ms.
        """,
    },
    {
        "id": "runbook-005",
        "service": "any",
        "scenario": "HTTP_ERROR_SPIKE",
        "title": "HTTP 5xx Error Spike & Downstream Cascade Runbook",
        "content": """
        SYMPTOMS: HTTP 500/503 error rate exceeding 15%, unhandled exceptions in logs.
        ROOT CAUSE: Upstream microservice communication failure triggering unhandled exception cascades.
        RECOMMENDED REMEDIATION:
        1. Restart failing deployment pod.
        2. Verify HTTP error rate drops to <0.5%.
        """,
    },
    {
        "id": "runbook-006",
        "service": "any",
        "scenario": "COMBINED_FAILURE",
        "title": "Multivariate Critical Infrastructure Cascade Runbook",
        "content": """
        SYMPTOMS: Concurrent CPU (>90%), Memory (>85%), Latency (>1800ms), and Error Rate (>15%).
        ROOT CAUSE: Systemic cascading failure across compute, memory, and database layers.
        RECOMMENDED REMEDIATION:
        1. Execute emergency rolling restart of deployment pods.
        2. Scale replica count immediately to 4 to alleviate traffic pressure.
        VERIFICATION: Verify all telemetry metrics return to baseline within 60 seconds.
        """,
    },
]
