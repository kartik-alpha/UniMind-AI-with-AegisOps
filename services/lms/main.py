from fastapi import FastAPI, Response
from fastapi.responses import PlainTextResponse
from services.common_metrics import ServiceMetrics

app = FastAPI(title="UniMind LMS Demo Service", version="1.0.0")
metrics = ServiceMetrics(service_name="LMS", base_cpu=34.0, base_mem=48.0, base_latency=142.0, replicas=3)


@app.get("/health")
def health():
    m = metrics.get_current_metrics()
    return {"service": "lms", "status": m["status"], "replicas": m["replicas"]}


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return metrics.to_prometheus_format()


@app.get("/api/courses")
def get_courses():
    return [
        {"code": "CS401", "name": "Artificial Intelligence & Multi-Agent Systems", "credits": 4},
        {"code": "CS402", "name": "Cloud Operations & AIOps", "credits": 3},
        {"code": "CS403", "name": "Database Architecture & Distributed Systems", "credits": 4},
    ]


@app.post("/chaos/enable")
def enable_chaos():
    metrics.set_chaos(True)
    return {"message": "Chaos injected into LMS service."}


@app.post("/chaos/disable")
def disable_chaos():
    metrics.set_chaos(False)
    return {"message": "Chaos disabled for LMS service."}
