"""
UniMind AI + AegisOps Enterprise Industry Templates & Company Configurations.

Provides declarative configuration presets for multi-tenant enterprise provisioning across:
- Higher Education
- Healthcare
- Financial Services / Banking
- IT & Technology
- Manufacturing & Logistics
"""

from typing import Dict, Any, List


INDUSTRY_TEMPLATES: Dict[str, Dict[str, Any]] = {
    "education": {
        "industry": "education",
        "name": "UniMind University",
        "slug": "unimind-edu",
        "description": "Comprehensive academic operations and student support system.",
        "config": {
            "display_name": "UniMind University",
            "tagline": "AI-Powered Academic Operations & Institutional Intelligence",
            "primary_color": "#2563eb",
            "categories": [
                "attendance",
                "examinations",
                "hostel",
                "library",
                "academics",
                "policies",
                "student_guidelines",
            ],
            "welcome_message": "Welcome to UniMind University AI Assistant. How can I assist you with academic rules, exams, or campus operations?",
            "ai_instructions": "You are UniMind AI, the official academic assistant for students, faculty, and administrators. Answer questions strictly using verified university policies and cite your sources.",
            "services": [
                {"name": "LMS", "port": 8001, "baseline_qps": 300},
                {"name": "Student Portal", "port": 8002, "baseline_qps": 150},
                {"name": "Exam Service", "port": 8003, "baseline_qps": 450},
                {"name": "Library Service", "port": 8004, "baseline_qps": 80},
            ],
        },
        "sample_documents": [
            {
                "title": "Institutional Examination & Attendance Regulations 2026",
                "category": "examinations",
                "filename": "academic_regulations_2026.txt",
                "content": (
                    "UniMind University Examination Regulations 2026.\n"
                    "1. Attendance Requirement: A minimum of 75% attendance in both lectures and practical sessions is strictly required to appear for end-semester examinations. Medical leave may condone up to 10% attendance upon submission of a certified medical certificate within 5 working days.\n"
                    "2. Re-evaluation Policy: Applications for paper re-evaluation must be submitted within 14 calendar days of result publication with a non-refundable fee of $25 per course.\n"
                    "3. Passing Criteria: A minimum of 40% in internal assessments and 40% in end-semester exams, with an aggregate score of 45%, is required to pass any academic course."
                ),
            }
        ],
    },
    "healthcare": {
        "industry": "healthcare",
        "name": "Apollo Metro Health System",
        "slug": "apollo-health",
        "description": "Hospital clinical operations, patient protocols, and health infrastructure.",
        "config": {
            "display_name": "Apollo Metro Health",
            "tagline": "Clinical Intelligence & Healthcare Infrastructure Operations",
            "primary_color": "#0d9488",
            "categories": [
                "clinical_protocols",
                "patient_care",
                "pharmacy",
                "billing",
                "compliance",
                "emergency",
            ],
            "welcome_message": "Welcome to Apollo Metro Health AI Clinical Navigator. Access protocols, pharmacy guidelines, and patient triage policies.",
            "ai_instructions": "You are AegisHealth AI, clinical intelligence assistant. You provide grounded clinical protocols and patient safety guidelines based strictly on hospital operating procedures.",
            "services": [
                {"name": "EHR Gateway", "port": 9001, "baseline_qps": 500},
                {"name": "Patient Portal", "port": 9002, "baseline_qps": 220},
                {"name": "Lab Diagnostics Service", "port": 9003, "baseline_qps": 380},
                {"name": "Pharmacy Dispatch", "port": 9004, "baseline_qps": 160},
            ],
        },
        "sample_documents": [
            {
                "title": "Hospital Emergency Triage and HIPAA Protocol 2026",
                "category": "clinical_protocols",
                "filename": "emergency_triage_hipaa_2026.txt",
                "content": (
                    "Apollo Metro Health Clinical Operating Procedures.\n"
                    "1. Emergency Triage Standard: Emergency Severity Index (ESI) Level 1 (immediate life-saving intervention) mandates physician bedside presence within 60 seconds. Level 2 (high risk) mandates nursing intervention within 10 minutes.\n"
                    "2. HIPAA Data Protection: All protected health information (PHI) must be encrypted in transit using TLS 1.3 and at rest with AES-256. Clinical records access is audited every 24 hours.\n"
                    "3. Controlled Substance Dispensing: Dual authentication by two certified nurse practitioners is required before dispensing Schedule II medications."
                ),
            }
        ],
    },
    "finance": {
        "industry": "finance",
        "name": "Apex Fintech & Banking Corp",
        "slug": "apex-fintech",
        "description": "Core banking infrastructure, loan underwriting, and transaction monitoring.",
        "config": {
            "display_name": "Apex Banking Corp",
            "tagline": "Mission-Critical Financial Operations & Compliance Intelligence",
            "primary_color": "#1e40af",
            "categories": [
                "compliance",
                "security",
                "fraud_policies",
                "loans",
                "accounts",
                "regulatory",
            ],
            "welcome_message": "Welcome to Apex Banking Intelligence. Query KYC/AML regulations, loan policies, and transaction thresholds.",
            "ai_instructions": "You are Apex Financial AI. You assist compliance officers and analysts with regulatory guidelines, fraud prevention procedures, and transactional rules.",
            "services": [
                {"name": "Core Banking Ledger", "port": 9101, "baseline_qps": 850},
                {"name": "Payment Gateway", "port": 9102, "baseline_qps": 1200},
                {"name": "Fraud Detection Engine", "port": 9103, "baseline_qps": 900},
                {"name": "Customer Account API", "port": 9104, "baseline_qps": 400},
            ],
        },
        "sample_documents": [
            {
                "title": "Anti-Money Laundering (AML) and Wire Transfer Compliance 2026",
                "category": "compliance",
                "filename": "aml_wire_compliance_2026.txt",
                "content": (
                    "Apex Fintech Global Compliance Policy.\n"
                    "1. AML Transaction Flagging: Any single wire transfer exceeding $10,000 USD or cumulative transactions exceeding $25,000 within 48 hours automatically triggers a Suspicious Activity Report (SAR) review.\n"
                    "2. KYC Verification: High-risk customer accounts require enhanced due diligence (EDD) renewed every 12 months with certified beneficial ownership verification.\n"
                    "3. Account Freeze Authorization: Level 3 Compliance Officers are authorized to temporarily freeze suspicious transaction accounts for up to 72 hours pending federal regulatory disclosure."
                ),
            }
        ],
    },
    "technology": {
        "industry": "technology",
        "name": "CloudScale Systems Inc",
        "slug": "cloudscale-tech",
        "description": "Multi-region cloud infrastructure, API gateways, and developer platform.",
        "config": {
            "display_name": "CloudScale Systems",
            "tagline": "Autonomous Cloud Platform & Observability Intelligence",
            "primary_color": "#7c3aed",
            "categories": [
                "devops",
                "api_docs",
                "security_policies",
                "incident_response",
                "architecture",
            ],
            "welcome_message": "Welcome to CloudScale Systems Platform AI. Query developer docs, SLO policies, and deployment runbooks.",
            "ai_instructions": "You are CloudScale Ops AI. You assist Site Reliability Engineers and DevOps teams with runbooks, SLO thresholds, and deployment policies.",
            "services": [
                {"name": "API Gateway", "port": 9201, "baseline_qps": 2000},
                {"name": "Auth Service", "port": 9202, "baseline_qps": 800},
                {"name": "Build & CI Pipeline", "port": 9203, "baseline_qps": 150},
                {"name": "Telemetry Ingestion", "port": 9204, "baseline_qps": 5000},
            ],
        },
        "sample_documents": [
            {
                "title": "Service Level Objectives (SLO) & Production Incident Runbook",
                "category": "incident_response",
                "filename": "slo_incident_runbook.txt",
                "content": (
                    "CloudScale Systems Production SRE Handbook.\n"
                    "1. Service Availability Target: Tier-1 APIs maintain an availability target of 99.95% measured over a rolling 30-day window. Error budget burn rate exceeding 14.4x requires immediate P1 incident declaration.\n"
                    "2. Deployment Rollback: Automated canary analysis rolls back deployments within 90 seconds if latency p99 exceeds 150ms or HTTP 5xx error rate exceeds 0.5%.\n"
                    "3. Blast Radius Mitigation: All production database connection pools must be configured with a maximum lifetime of 1800 seconds and a connection timeout of 3000ms."
                ),
            }
        ],
    },
    "manufacturing": {
        "industry": "manufacturing",
        "name": "Vertex Logistics & Supply Chain",
        "slug": "vertex-logistics",
        "description": "Automated warehouse, fleet telemetry, and inventory management.",
        "config": {
            "display_name": "Vertex Logistics",
            "tagline": "Industrial IoT & Supply Chain Logistics Intelligence",
            "primary_color": "#ea580c",
            "categories": [
                "supply_chain",
                "safety_protocols",
                "inventory",
                "equipment",
                "dispatch",
            ],
            "welcome_message": "Welcome to Vertex Logistics AI. Inquire about dispatch schedules, warehouse safety, and fleet tracking.",
            "ai_instructions": "You are Vertex Industrial AI. You provide operational guidance on warehouse safety, OSHA compliance, and inventory dispatch.",
            "services": [
                {"name": "Warehouse Management (WMS)", "port": 9301, "baseline_qps": 350},
                {"name": "Fleet Tracking Telemetry", "port": 9302, "baseline_qps": 1100},
                {"name": "ERP Inventory Connector", "port": 9303, "baseline_qps": 250},
                {"name": "Order Dispatch Engine", "port": 9304, "baseline_qps": 400},
            ],
        },
        "sample_documents": [
            {
                "title": "Warehouse OSHA Safety and Automated Fleet Dispatch Protocol",
                "category": "safety_protocols",
                "filename": "safety_dispatch_protocols.txt",
                "content": (
                    "Vertex Industrial Supply Chain Operating Rules.\n"
                    "1. Forklift & AGV Safety: Automated Guided Vehicles (AGVs) must operate at a maximum speed of 4.5 km/h in shared pedestrian zones. Emergency stop laser buffers are calibrated to 1.8 meters.\n"
                    "2. Hazardous Material Handling: Class 3 flammable liquids must be stored in UL-listed safety cabinets equipped with self-closing doors and grounded to earth ground (< 5 ohms).\n"
                    "3. Fleet Dispatch Deadlines: Express priority orders must be staged at bay doors within 45 minutes of pick allocation."
                ),
            }
        ],
    },
}


def get_template_by_industry(industry: str) -> Dict[str, Any]:
    """Returns the template dictionary for the specified industry."""
    key = industry.lower().strip()
    return INDUSTRY_TEMPLATES.get(key, INDUSTRY_TEMPLATES["education"])


def list_available_templates() -> List[Dict[str, Any]]:
    """Returns a summary list of all available industry templates."""
    results = []
    for key, tmpl in INDUSTRY_TEMPLATES.items():
        results.append({
            "key": key,
            "industry": tmpl["industry"],
            "name": tmpl["name"],
            "slug": tmpl["slug"],
            "description": tmpl["description"],
            "categories": tmpl["config"]["categories"],
            "service_count": len(tmpl["config"]["services"]),
        })
    return results

