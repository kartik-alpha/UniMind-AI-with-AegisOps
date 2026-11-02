from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from services.common_metrics import ServiceMetrics

app = FastAPI(title="UniMind Student Portal Demo Service", version="1.0.0")
metrics = ServiceMetrics(service_name="Student Portal", base_cpu=27.0, base_mem=41.0, base_latency=118.0, replicas=2)


@app.get("/health")
def health():
    m = metrics.get_current_metrics()
    return {"service": "student_portal", "status": m["status"], "replicas": m["replicas"]}


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return metrics.to_prometheus_format()


@app.get("/api/profile")
def get_profile():
    return {
        "student_id": "STU-2026-904",
        "name": "Kartik Lakhera",
        "program": "B.Tech Computer Science & Engineering",
        "semester": 8,
        "cgpa": 3.85,
    }


@app.post("/chaos/enable")
def enable_chaos():
    metrics.set_chaos(True)
    return {"message": "Chaos injected into Student Portal."}


@app.post("/chaos/disable")
def disable_chaos():
    metrics.set_chaos(False)
    return {"message": "Chaos disabled for Student Portal."}
