RUNBOOKS_KNOWLEDGE = [
    {
        "id": "runbook-001",
        "service": "exam-service",
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
        "title": "LMS Cache Thrashing & High Memory Runbook",
        "content": """
        SYMPTOMS: Memory usage (>85%), slow page load times.
        ROOT CAUSE: Redis cache eviction queue stall during assignment submission deadlines.
        RECOMMENDED REMEDIATION: Restart LMS pod deployment.
        """,
    },
]
