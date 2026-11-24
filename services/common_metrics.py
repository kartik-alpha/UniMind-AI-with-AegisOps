import time
import random
from typing import Dict, Any, List, Optional


class ServiceMetrics:
    """
    Standardized Telemetry and Chaos Instrumentation for Demo University Services.
    Supports granular failure injection scenarios while maintaining clear distinction
    between genuine baseline telemetry and synthetic failure injections.
    """

    SCENARIO_CPU = "CPU_SATURATION"
    SCENARIO_MEMORY = "MEMORY_PRESSURE"
    SCENARIO_DB_POOL = "DB_CONNECTION_EXHAUSTION"
    SCENARIO_NETWORK = "NETWORK_LATENCY"
    SCENARIO_HTTP_ERRORS = "HTTP_ERROR_SPIKE"
    SCENARIO_COMBINED = "COMBINED_FAILURE"

    def __init__(
        self,
        service_name: str,
        base_cpu: float = 25.0,
        base_mem: float = 40.0,
        base_latency: float = 120.0,
        replicas: int = 2,
    ):
        self.service_name = service_name
        self.base_cpu = base_cpu
        self.base_mem = base_mem
        self.base_latency = base_latency
        self.replicas = replicas

        # Chaos State
        self.chaos_active = False
        self.active_scenario: Optional[str] = None
        self.severity: str = "MEDIUM"
        self.duration_seconds: int = 0
        self.started_at: Optional[float] = None
        self.is_synthetic: bool = False

        self.request_count = random.randint(250, 450)
        self.recent_logs: List[Dict[str, Any]] = []
        self.history: List[Dict[str, Any]] = []
        self._init_baseline_history()

    def _init_baseline_history(self):
        """Pre-populates a rolling 10-point baseline telemetry history."""
        now = time.time()
        for i in range(10, 0, -1):
            t_str = time.strftime("%H:%M", time.localtime(now - i * 60))
            lat = round(max(50.0, self.base_latency + random.uniform(-8.0, 8.0)), 1)
            req = round(self.request_count + random.uniform(-10.0, 10.0), 1)
            p95 = round(lat * 1.25, 1)
            p99 = round(lat * 1.55, 1)
            db_pool = round(min(100.0, max(5.0, (req / 30.0) + random.uniform(-2.0, 2.0))), 1)
            self.history.append({
                "timestamp": t_str,
                "cpu_usage_percent": round(max(10.0, self.base_cpu + random.uniform(-2.0, 2.0)), 1),
                "memory_usage_percent": round(max(20.0, self.base_mem + random.uniform(-2.0, 2.0)), 1),
                "latency_ms": lat,
                "latency_p95_ms": p95,
                "latency_p99_ms": p99,
                "db_pool_saturation_percent": db_pool,
                "error_rate_percent": round(random.uniform(0.0, 0.1), 1),
                "request_rate_per_sec": req,
                "is_synthetic": False,
            })

    def get_history(self, points: int = 10) -> List[Dict[str, Any]]:
        """Returns the most recent N points from the rolling telemetry ring buffer."""
        return self.history[-points:] if self.history else []

    def set_chaos(
        self,
        active: bool,
        scenario: Optional[str] = None,
        severity: str = "HIGH",
        duration_seconds: int = 0,
    ):
        """
        Activates or deactivates a specific chaos scenario.
        """
        self.chaos_active = active
        self.is_synthetic = active

        if active:
            self.active_scenario = scenario or self.SCENARIO_DB_POOL
            self.severity = severity.upper()
            self.duration_seconds = duration_seconds
            self.started_at = time.time()
            self._generate_scenario_logs(self.active_scenario, self.severity)
        else:
            self.active_scenario = None
            self.severity = "LOW"
            self.duration_seconds = 0
            self.started_at = None
            self._append_log("INFO", f"Service {self.service_name} returned to healthy baseline operation.")

    @property
    def _chaos_active(self) -> bool:
        """Backward-compatibility property for existing route handlers."""
        self._check_duration_expiry()
        return self.chaos_active

    def _check_duration_expiry(self):
        """Automatically recovers baseline if scenario duration has elapsed."""
        if self.chaos_active and self.duration_seconds > 0 and self.started_at:
            if time.time() - self.started_at >= self.duration_seconds:
                self.set_chaos(False)

    def _append_log(self, level: str, message: str, trace_id: str = "-"):
        timestamp = time.strftime("%H:%M:%S")
        self.recent_logs.append({
            "timestamp": timestamp,
            "service": self.service_name.lower().replace(" ", "-"),
            "level": level,
            "message": message,
            "trace_id": trace_id if trace_id != "-" else f"{random.randint(1000, 9999):x}",
            "is_synthetic": self.is_synthetic,
        })
        if len(self.recent_logs) > 50:
            self.recent_logs.pop(0)

    def _generate_scenario_logs(self, scenario: str, severity: str):
        svc = self.service_name.lower().replace(" ", "-")
        if scenario == self.SCENARIO_CPU:
            self._append_log("WARN", f"[{svc}] CPU usage exceeding threshold: >90% sustained on pod {svc}-7d9f")
            self._append_log("ERROR", f"[{svc}] CFS quota throttling active: request processing queue depth 840")
        elif scenario == self.SCENARIO_MEMORY:
            self._append_log("WARN", f"[{svc}] Memory cgroup warning: 88% allocated of limit")
            self._append_log("ERROR", f"[{svc}] Potential Out-Of-Memory (OOM) condition detected; GC pause >1200ms")
        elif scenario == self.SCENARIO_DB_POOL:
            self._append_log("ERROR", f"[{svc}] Database connection timeout after 5000ms (connection pool exhausted)")
            self._append_log("ERROR", f"[{svc}] HTTP 503 Service Unavailable: upstream results_db pool saturated")
        elif scenario == self.SCENARIO_NETWORK:
            self._append_log("WARN", f"[{svc}] Inter-service latency degradation: packet round-trip >2500ms")
            self._append_log("ERROR", f"[{svc}] Socket read timeout on internal microservice RPC bridge")
        elif scenario == self.SCENARIO_HTTP_ERRORS:
            self._append_log("ERROR", f"[{svc}] HTTP 500 Internal Server Error rate spiked to >25%")
            self._append_log("ERROR", f"[{svc}] Unhandled exception in endpoint handler: downstream failure cascade")
        elif scenario == self.SCENARIO_COMBINED:
            self._append_log("CRITICAL", f"[{svc}] MULTIVARIATE INFRASTRUCTURE DEGRADATION: CPU >90%, DB Pool exhausted, 503 errors")
            self._append_log("ERROR", f"[{svc}] Pod health check liveness probe failing")

    def get_current_metrics(self) -> Dict[str, Any]:
        self._check_duration_expiry()

        sev_multiplier = 1.0
        if self.severity == "CRITICAL":
            sev_multiplier = 1.2
        elif self.severity == "LOW":
            sev_multiplier = 0.7

        if self.chaos_active:
            scen = self.active_scenario or self.SCENARIO_DB_POOL

            if scen == self.SCENARIO_CPU:
                cpu = round(min(99.0, (self.base_cpu + 70.0) * sev_multiplier), 1)
                mem = round(self.base_mem + random.uniform(5.0, 10.0), 1)
                latency = round(min(3000.0, (self.base_latency + 700.0) * sev_multiplier), 1)
                error_rate = round(min(25.0, 4.5 * sev_multiplier), 1)
                req_rate = round(self.request_count * 2.2, 1)
            elif scen == self.SCENARIO_MEMORY:
                cpu = round(self.base_cpu + random.uniform(10.0, 20.0), 1)
                mem = round(min(98.0, (self.base_mem + 50.0) * sev_multiplier), 1)
                latency = round(min(3000.0, (self.base_latency + 600.0) * sev_multiplier), 1)
                error_rate = round(min(20.0, 3.0 * sev_multiplier), 1)
                req_rate = round(self.request_count * 1.1, 1)
            elif scen == self.SCENARIO_DB_POOL:
                cpu = round(min(98.0, (self.base_cpu + 65.0) * sev_multiplier), 1)
                mem = round(min(95.0, (self.base_mem + 40.0) * sev_multiplier), 1)
                latency = round(min(5000.0, (self.base_latency + 1600.0) * sev_multiplier), 1)
                error_rate = round(min(35.0, 14.0 * sev_multiplier), 1)
                req_rate = round(self.request_count * 2.5, 1)
            elif scen == self.SCENARIO_NETWORK:
                cpu = round(self.base_cpu + random.uniform(5.0, 10.0), 1)
                mem = round(self.base_mem + random.uniform(2.0, 5.0), 1)
                latency = round(min(6000.0, 2400.0 * sev_multiplier), 1)
                error_rate = round(min(30.0, 9.5 * sev_multiplier), 1)
                req_rate = round(max(50.0, self.request_count * 0.4), 1)
            elif scen == self.SCENARIO_HTTP_ERRORS:
                cpu = round(self.base_cpu + random.uniform(15.0, 25.0), 1)
                mem = round(self.base_mem + random.uniform(10.0, 15.0), 1)
                latency = round(self.base_latency + 350.0, 1)
                error_rate = round(min(50.0, 28.0 * sev_multiplier), 1)
                req_rate = round(self.request_count * 1.8, 1)
            else:  # Combined
                cpu = round(min(99.0, 93.0 * sev_multiplier), 1)
                mem = round(min(96.0, 85.0 * sev_multiplier), 1)
                latency = round(min(5000.0, 1950.0 * sev_multiplier), 1)
                error_rate = round(min(40.0, 16.5 * sev_multiplier), 1)
                req_rate = round(self.request_count * 2.8, 1)

            status_val = "CRITICAL" if (self.severity in ("HIGH", "CRITICAL") or error_rate > 10.0 or cpu > 85.0) else "DEGRADED"
        else:
            cpu = round(max(10.0, self.base_cpu + random.uniform(-3.0, 3.0)), 1)
            mem = round(max(20.0, self.base_mem + random.uniform(-2.0, 2.0)), 1)
            latency = round(max(50.0, self.base_latency + random.uniform(-10.0, 10.0)), 1)
            error_rate = round(random.uniform(0.0, 0.2), 1)
            req_rate = round(self.request_count + random.uniform(-15.0, 15.0), 1)
            status_val = "HEALTHY"

        time_left = 0
        if self.chaos_active and self.duration_seconds > 0 and self.started_at:
            elapsed = time.time() - self.started_at
            time_left = max(0, int(self.duration_seconds - elapsed))

        # Standardized latency percentiles and DB connection pool saturation
        if self.chaos_active and scen == self.SCENARIO_DB_POOL:
            db_pool_sat = round(min(100.0, 94.0 * sev_multiplier), 1)
            p95_lat = round(latency * 1.35, 1)
            p99_lat = round(latency * 1.75, 1)
        elif self.chaos_active:
            db_pool_sat = round(min(95.0, 50.0 + random.uniform(15.0, 30.0) * sev_multiplier), 1)
            p95_lat = round(latency * 1.30, 1)
            p99_lat = round(latency * 1.65, 1)
        else:
            db_pool_sat = round(min(100.0, max(5.0, (req_rate / 30.0) + random.uniform(-2.0, 2.0))), 1)
            p95_lat = round(latency * 1.25, 1)
            p99_lat = round(latency * 1.55, 1)

        record = {
            "service": self.service_name,
            "status": status_val,
            "cpu_usage_percent": cpu,
            "memory_usage_percent": mem,
            "latency_ms": latency,
            "latency_p95_ms": p95_lat,
            "latency_p99_ms": p99_lat,
            "db_pool_saturation_percent": db_pool_sat,
            "error_rate_percent": error_rate,
            "request_rate_per_sec": req_rate,
            "replicas": self.replicas,
            "chaos_mode": self.chaos_active,
            "active_scenario": self.active_scenario,
            "severity": self.severity if self.chaos_active else "NORMAL",
            "is_synthetic": self.is_synthetic,
            "time_remaining_seconds": time_left,
            "timestamp": time.strftime("%H:%M"),
        }
        self.history.append(record)
        if len(self.history) > 60:
            self.history.pop(0)
        return record

    def to_prometheus_format(self) -> str:
        m = self.get_current_metrics()
        lines = [
            f'# HELP university_service_cpu_percent Current CPU utilization percentage',
            f'# TYPE university_service_cpu_percent gauge',
            f'university_service_cpu_percent{{service="{m["service"]}",synthetic="{str(m["is_synthetic"]).lower()}"}} {m["cpu_usage_percent"]}',
            f'# HELP university_service_memory_percent Current RAM utilization percentage',
            f'# TYPE university_service_memory_percent gauge',
            f'university_service_memory_percent{{service="{m["service"]}",synthetic="{str(m["is_synthetic"]).lower()}"}} {m["memory_usage_percent"]}',
            f'# HELP university_service_latency_ms Current request latency in milliseconds',
            f'# TYPE university_service_latency_ms gauge',
            f'university_service_latency_ms{{service="{m["service"]}",synthetic="{str(m["is_synthetic"]).lower()}"}} {m["latency_ms"]}',
            f'# HELP university_service_latency_p95_ms Current p95 request latency in milliseconds',
            f'# TYPE university_service_latency_p95_ms gauge',
            f'university_service_latency_p95_ms{{service="{m["service"]}",synthetic="{str(m["is_synthetic"]).lower()}"}} {m["latency_p95_ms"]}',
            f'# HELP university_service_latency_p99_ms Current p99 request latency in milliseconds',
            f'# TYPE university_service_latency_p99_ms gauge',
            f'university_service_latency_p99_ms{{service="{m["service"]}",synthetic="{str(m["is_synthetic"]).lower()}"}} {m["latency_p99_ms"]}',
            f'# HELP university_service_db_pool_saturation_percent Current database connection pool saturation percentage',
            f'# TYPE university_service_db_pool_saturation_percent gauge',
            f'university_service_db_pool_saturation_percent{{service="{m["service"]}",synthetic="{str(m["is_synthetic"]).lower()}"}} {m["db_pool_saturation_percent"]}',
            f'# HELP university_service_error_rate_percent Percentage of HTTP 5xx responses',
            f'# TYPE university_service_error_rate_percent gauge',
            f'university_service_error_rate_percent{{service="{m["service"]}",synthetic="{str(m["is_synthetic"]).lower()}"}} {m["error_rate_percent"]}',
            f'# HELP university_service_request_rate Requests per second',
            f'# TYPE university_service_request_rate gauge',
            f'university_service_request_rate{{service="{m["service"]}",synthetic="{str(m["is_synthetic"]).lower()}"}} {m["request_rate_per_sec"]}',
            f'# HELP university_service_replicas Configured Kubernetes replica count',
            f'# TYPE university_service_replicas gauge',
            f'university_service_replicas{{service="{m["service"]}"}} {m["replicas"]}',
        ]
        return "\n".join(lines)


def parse_structured_log(raw_log: str) -> Dict[str, Any]:
    """
    Parses unstructured or structured log lines into a normalized telemetry log record.
    Supports JSON log envelopes and syslog/Kubernetes bracketed format.
    """
    import json
    import re

    stripped = raw_log.strip()
    # Try parsing JSON log format
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            parsed = json.loads(stripped)
            return {
                "timestamp": parsed.get("timestamp") or parsed.get("time") or time.strftime("%H:%M:%S"),
                "level": (parsed.get("level") or parsed.get("severity") or "INFO").upper(),
                "service": parsed.get("service") or parsed.get("app") or "unknown-service",
                "message": parsed.get("message") or parsed.get("msg") or "",
                "trace_id": parsed.get("trace_id") or parsed.get("traceId") or "-",
                "is_synthetic": parsed.get("is_synthetic", False),
            }
        except Exception:
            pass

    # Standard bracketed format: [TIMESTAMP] [LEVEL] [SERVICE] MESSAGE
    match = re.match(r"^\[?([^\]]+)\]?\s+\[?(DEBUG|INFO|WARN|WARNING|ERROR|CRITICAL)\]?\s+\[?([^\]]+)\]?\s+(.*)$", stripped, re.IGNORECASE)
    if match:
        t_stamp, lvl, svc, msg = match.groups()
        return {
            "timestamp": t_stamp.strip(),
            "level": lvl.upper().replace("WARNING", "WARN"),
            "service": svc.strip().lower().replace(" ", "-"),
            "message": msg.strip(),
            "trace_id": f"{hash(msg) & 0xffff:04x}",
            "is_synthetic": "synthetic" in msg.lower() or "chaos" in msg.lower(),
        }

    # Fallback generic parsing
    lvl = "INFO"
    for l_cand in ["CRITICAL", "ERROR", "WARN", "WARNING", "DEBUG"]:
        if l_cand in stripped.upper():
            lvl = l_cand.replace("WARNING", "WARN")
            break

    return {
        "timestamp": time.strftime("%H:%M:%S"),
        "level": lvl,
        "service": "application",
        "message": stripped,
        "trace_id": "-",
        "is_synthetic": False,
    }


# Enterprise Microservices Telemetry Instances
auth_m = ServiceMetrics(service_name="Auth Service", base_cpu=15.0, base_mem=30.0, base_latency=85.0, replicas=2)
