import re
from typing import List, Dict, Set, Any


# Multi-domain enterprise synonym and term expansion dictionary
ENTERPRISE_SYNONYM_MAP: Dict[str, List[str]] = {
    # Academic & University
    "attendance": ["minimum attendance", "75% attendance", "eligibility", "condonation", "medical certificate", "shortage"],
    "curfew": ["hostel timing", "in-time", "10:00 PM", "gate close", "entry rule", "resident curfew"],
    "hostel": ["hostel warden", "resident", "curfew", "mess", "room allotment", "hostel guidelines"],
    "exam": ["examination", "end-semester", "mid-semester", "grading", "evaluation", "hall ticket", "re-evaluation"],
    "examination": ["end-semester", "grade", "re-evaluation", "answer script", "weightage", "marks"],
    "re-evaluation": ["re-checking", "re-evaluation", "rechecking", "scrutiny", "7 days", "marks review"],
    "library": ["book renewal", "issue return", "library card", "catalogue", "borrowing", "fine"],
    "grading": ["credits", "grade point", "cgpa", "sgpa", "passing marks", "evaluation scheme"],
    "cgpa": ["cumulative grade point average", "sgpa", "grading scale", "10-point scale", "credits"],
    
    # Technology, Cloud & Infrastructure
    "kubernetes": ["k8s", "cluster", "istio", "pods", "service mesh", "deployment", "namespaces"],
    "k8s": ["kubernetes", "cluster", "pods", "container", "service mesh"],
    "istio": ["service mesh", "mtls", "envoy proxy", "traffic routing", "ingress gateway"],
    "terraform": ["iac", "state file", "infrastructure as code", "hcl", "vault", "provisioning"],
    "zerotrust": ["mtls 1.3", "least privilege", "microsegmentation", "identity verification"],
    "vault": ["secret management", "encryption keys", "iac vault", "credentials storage"],
    "aws": ["cloud", "s3", "ec2", "vpc", "iam", "cloudwatch"],
    
    # Healthcare & Clinical Protocols
    "triage": ["icu triage", "emergency severity index", "clinical protocols", "critical care", "vital signs"],
    "icu": ["intensive care unit", "triage", "telemetry", "attending physician", "level 1 critical"],
    "morphine": ["pediatric dosage", "controlled substance", "dual RN sign-off", "analgesic", "opioid protocol"],
    "hipaa": ["protected health information", "phi", "epic ehr", "data privacy", "sandbox isolation"],
    "ehr": ["epic ehr", "electronic health records", "patient records", "clinical sandbox"],
    
    # IT Operations & SRE
    "it": ["wifi", "network", "portal", "lms", "credentials", "server"],
    "wifi": ["internet", "network", "hostel connectivity", "portal", "login"],
    "outage": ["downtime", "incident", "service down", "high latency", "error spike", "unavailability"],
    "latency": ["response time", "p95 latency", "p99 latency", "slow performance", "sla breach"],
    "incident": ["alert", "severity", "root cause analysis", "rca", "remediation", "outage"],
    "sla": ["service level agreement", "availability target", "99.9% uptime", "error budget"],
    
    # Security, Governance & Compliance
    "audit": ["audit log", "provenance", "compliance", "activity trace", "tamper evidence"],
    "rbac": ["role based access control", "permissions", "user roles", "tenant isolation", "authorization"],
    "tenant": ["multi-tenant", "organization", "isolation boundary", "partitioning", "data residency"],
}

# Backward compatibility alias
UNIVERSITY_SYNONYM_MAP = ENTERPRISE_SYNONYM_MAP


def expand_query(query: str) -> Dict[str, Any]:
    """
    Expands student and enterprise queries with cross-domain synonyms, abbreviations, and key entity terms.
    Returns:
      - normalized_query: cleaned and normalized string
      - expanded_terms: list of high-priority additional keywords
      - expanded_query: augmented query string combining original + expanded concepts
    """
    if not query:
        return {"normalized_query": "", "expanded_terms": [], "expanded_query": ""}

    cleaned = query.strip()
    words = re.findall(r"\b[\w%]+(?:-[\w%]+)*\b", cleaned.lower())

    expanded_terms: Set[str] = set()

    for word in words:
        if word in ENTERPRISE_SYNONYM_MAP:
            for syn in ENTERPRISE_SYNONYM_MAP[word]:
                expanded_terms.add(syn)
        # Check partial subwords (e.g. "attend" in "attendance")
        for key, syns in ENTERPRISE_SYNONYM_MAP.items():
            if (len(key) >= 4 and key in word) or (len(word) >= 4 and word in key):
                for s in syns[:3]:
                    expanded_terms.add(s)

    # Exclude terms already in query to avoid redundancy
    query_lower = cleaned.lower()
    novel_terms = [t for t in expanded_terms if t.lower() not in query_lower]

    # Combine into enriched search query
    augmented_parts = [cleaned]
    if novel_terms:
        augmented_parts.append(" ".join(novel_terms[:5]))

    augmented_query = " ".join(augmented_parts)

    return {
        "normalized_query": cleaned,
        "expanded_terms": novel_terms[:8],
        "expanded_query": augmented_query,
    }
