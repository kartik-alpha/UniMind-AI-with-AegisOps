import sys
import time
import argparse
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from services.common_metrics import ServiceMetrics, auth_m
from services.lms.main import metrics as lms_m
from services.student_portal.main import metrics as portal_m
from services.exam_service.main import metrics as exam_m
from services.library_service.main import metrics as lib_m


SERVICES_MAP: Dict[str, ServiceMetrics] = {
    "exam_service": exam_m,
    "exam-service": exam_m,
    "lms": lms_m,
    "student_portal": portal_m,
    "student-portal": portal_m,
    "library_service": lib_m,
    "library-service": lib_m,
    "auth_service": auth_m,
    "auth-service": auth_m,
}

SCENARIOS = {
    "cpu": ServiceMetrics.SCENARIO_CPU,
    "memory": ServiceMetrics.SCENARIO_MEMORY,
    "database": ServiceMetrics.SCENARIO_DB_POOL,
    "network": ServiceMetrics.SCENARIO_NETWORK,
    "http_errors": ServiceMetrics.SCENARIO_HTTP_ERRORS,
    "combined": ServiceMetrics.SCENARIO_COMBINED,
}


class ChaosSimulator:
    """
    Automated Chaos Engineering and Failure Injection Engine for AegisOps.
    Strictly isolated to development environment microservices.
    """

    def __init__(self):
        self.services = SERVICES_MAP

    def inject_failure(
        self,
        service_name: str,
        scenario: str,
        severity: str = "HIGH",
        duration_seconds: int = 60,
    ) -> Dict[str, Any]:
        """
        Injects a failure scenario into the specified microservice.
        """
        clean_svc = service_name.lower().strip()
        if clean_svc not in self.services:
            raise ValueError(f"Unknown service '{service_name}'. Valid: {list(self.services.keys())}")

        clean_scen = scenario.lower().strip()
        scenario_constant = SCENARIOS.get(clean_scen, clean_scen.upper())

        svc = self.services[clean_svc]
        svc.set_chaos(
            active=True,
            scenario=scenario_constant,
            severity=severity.upper(),
            duration_seconds=duration_seconds,
        )

        metrics = svc.get_current_metrics()
        return {
            "service": svc.service_name,
            "scenario": scenario_constant,
            "severity": severity.upper(),
            "duration_seconds": duration_seconds,
            "is_synthetic": True,
            "status": metrics["status"],
            "cpu_usage_percent": metrics["cpu_usage_percent"],
            "memory_usage_percent": metrics["memory_usage_percent"],
            "latency_ms": metrics["latency_ms"],
            "error_rate_percent": metrics["error_rate_percent"],
            "request_rate_per_sec": metrics["request_rate_per_sec"],
        }

    def restore_service(self, service_name: str) -> Dict[str, Any]:
        """
        Restores a target service to normal operating baseline.
        """
        clean_svc = service_name.lower().strip()
        if clean_svc not in self.services:
            raise ValueError(f"Unknown service '{service_name}'.")

        svc = self.services[clean_svc]
        svc.set_chaos(False)
        metrics = svc.get_current_metrics()
        return {
            "service": svc.service_name,
            "status": "HEALTHY",
            "chaos_active": False,
            "metrics": metrics,
        }

    def restore_all(self) -> Dict[str, Any]:
        """
        Restores all 4 demo university services to healthy baseline.
        """
        restored = []
        for name, svc in self.services.items():
            svc.set_chaos(False)
            restored.append(svc.service_name)
        return {"status": "SUCCESS", "restored_services": list(set(restored))}

    def get_fleet_status(self) -> Dict[str, Any]:
        """
        Gathers real-time telemetry from all monitored services.
        """
        status_list = []
        for name in ["exam_service", "lms", "student_portal", "library_service"]:
            svc = self.services[name]
            status_list.append(svc.get_current_metrics())
        return {"fleet": status_list, "timestamp": time.time()}


_simulator_instance = None


def get_chaos_simulator() -> ChaosSimulator:
    global _simulator_instance
    if _simulator_instance is None:
        _simulator_instance = ChaosSimulator()
    return _simulator_instance


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AegisOps Chaos Simulator CLI")
    parser.add_argument("--service", type=str, default="exam_service", help="Target service name")
    parser.add_argument("--scenario", type=str, default="database", choices=list(SCENARIOS.keys()) + ["all"], help="Failure scenario")
    parser.add_argument("--severity", type=str, default="HIGH", choices=["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds (0 = indefinite)")
    parser.add_argument("--restore-all", action="store_true", help="Restore all services to baseline")

    args = parser.parse_args()
    sim = get_chaos_simulator()

    if args.restore_all:
        res = sim.restore_all()
        print("\n[+] All services restored to healthy baseline operation.")
        sys.exit(0)

    print("=" * 70)
    print(" AEGISPOS AUTOMATED CHAOS ENGINEERING INJECTOR")
    print(f" Target Service : {args.service.upper()}")
    print(f" Scenario       : {args.scenario.upper()}")
    print(f" Severity       : {args.severity.upper()}")
    print(f" Duration       : {args.duration}s")
    print("=" * 70)

    result = sim.inject_failure(
        service_name=args.service,
        scenario=args.scenario,
        severity=args.severity,
        duration_seconds=args.duration,
    )

    print(f"\n[+] Injected Telemetry State:")
    for k, v in result.items():
        print(f"    - {k:<22}: {v}")

    print("\n[!] Chaos active. Monitoring telemetry reflection...")
    time.sleep(2)
    current = sim.services[args.service.lower()].get_current_metrics()
    print(f"[+] Verified Live Status: {current['status']} | CPU: {current['cpu_usage_percent']}% | Latency: {current['latency_ms']}ms | Errors: {current['error_rate_percent']}%")
    print("=" * 70)

