from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from services.common_metrics import ServiceMetrics

app = FastAPI(title="UniMind Exam Service Demo", version="1.0.0")
metrics = ServiceMetrics(service_name="Exam Service", base_cpu=92.0, base_mem=81.0, base_latency=1800.0, replicas=2)
# Default Exam Service into active degraded mode to match AegisOps screenshot scenario
metrics.set_chaos(True)


@app.get("/health")
def health():
    m = metrics.get_current_metrics()
    return {"service": "exam_service", "status": m["status"], "replicas": m["replicas"]}


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return metrics.to_prometheus_format()


@app.get("/api/results")
def get_results():
    return {
        "term": "Spring 2026",
        "results": [
            {"subject": "CS401 AI", "grade": "A+"},
            {"subject": "CS402 Cloud & AIOps", "grade": "A"},
        ],
        "system_notice": "High load on results database connection pool.",
    }


@app.post("/chaos/enable")
def enable_chaos():
    metrics.set_chaos(True)
    return {"message": "Chaos enabled: High CPU & Latency injected into Exam Service."}


@app.post("/chaos/disable")
def disable_chaos():
    metrics.set_chaos(False)
    return {"message": "Chaos disabled: Exam Service metrics restored to normal."}
