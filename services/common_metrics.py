import time
import random
from typing import Dict, Any


class ServiceMetrics:
    def __init__(self, service_name: str, base_cpu: float, base_mem: float, base_latency: float, replicas: int = 2):
        self.service_name = service_name
        self.base_cpu = base_cpu
        self.base_mem = base_mem
        self.base_latency = base_latency
        self.replicas = replicas
        self.chaos_active = False
        self.request_count = random.randint(100, 500)
        self.error_count = 0
        self.last_incident = "None"

    def set_chaos(self, active: bool):
        self.chaos_active = active

    def get_current_metrics(self) -> Dict[str, Any]:
        if self.chaos_active:
            cpu = round(min(99.0, self.base_cpu + random.uniform(50.0, 65.0)), 1)
            mem = round(min(95.0, self.base_mem + random.uniform(30.0, 45.0)), 1)
            latency = round(self.base_latency + random.uniform(1400.0, 1900.0), 1)
            error_rate = round(random.uniform(12.0, 18.0), 1)
            req_rate = round(random.uniform(850.0, 1100.0), 1)
        else:
            cpu = round(max(10.0, self.base_cpu + random.uniform(-4.0, 4.0)), 1)
            mem = round(max(20.0, self.base_mem + random.uniform(-3.0, 3.0)), 1)
            latency = round(max(50.0, self.base_latency + random.uniform(-15.0, 15.0)), 1)
            error_rate = round(random.uniform(0.0, 0.2), 1)
            req_rate = round(self.request_count + random.uniform(-20.0, 20.0), 1)

        return {
            "service": self.service_name,
            "status": "CRITICAL" if (self.chaos_active or cpu > 85.0) else "HEALTHY",
            "cpu_usage_percent": cpu,
            "memory_usage_percent": mem,
            "latency_ms": latency,
            "error_rate_percent": error_rate,
            "request_rate_per_sec": req_rate,
            "replicas": self.replicas,
            "chaos_mode": self.chaos_active,
        }

    def to_prometheus_format(self) -> str:
        m = self.get_current_metrics()
        lines = [
            f'university_service_cpu_percent{{service="{m["service"]}"}} {m["cpu_usage_percent"]}',
            f'university_service_memory_percent{{service="{m["service"]}"}} {m["memory_usage_percent"]}',
            f'university_service_latency_ms{{service="{m["service"]}"}} {m["latency_ms"]}',
            f'university_service_error_rate_percent{{service="{m["service"]}"}} {m["error_rate_percent"]}',
            f'university_service_request_rate{{service="{m["service"]}"}} {m["request_rate_per_sec"]}',
            f'university_service_replicas{{service="{m["service"]}"}} {m["replicas"]}',
        ]
        return "\n".join(lines)
