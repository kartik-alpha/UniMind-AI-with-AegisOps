from fastapi import FastAPI
from fastapi.responses import PlainTextResponse
from services.common_metrics import ServiceMetrics

app = FastAPI(title="UniMind Library Service Demo", version="1.0.0")
metrics = ServiceMetrics(service_name="Library Service", base_cpu=21.0, base_mem=38.0, base_latency=105.0, replicas=2)


@app.get("/health")
def health():
    m = metrics.get_current_metrics()
    return {"service": "library_service", "status": m["status"], "replicas": m["replicas"]}


@app.get("/metrics", response_class=PlainTextResponse)
def prometheus_metrics():
    return metrics.to_prometheus_format()


@app.get("/api/books")
def search_books():
    return [
        {"id": 1, "title": "Pattern Recognition and Machine Learning", "author": "Christopher Bishop", "available": True},
        {"id": 2, "title": "Site Reliability Engineering", "author": "Betsy Beyer et al.", "available": True},
    ]


@app.post("/chaos/enable")
def enable_chaos():
    metrics.set_chaos(True)
    return {"message": "Chaos enabled for Library Service."}


@app.post("/chaos/disable")
def disable_chaos():
    metrics.set_chaos(False)
    return {"message": "Chaos disabled for Library Service."}
