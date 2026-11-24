import math
from typing import Dict, List, Any, Optional
from digital_twin.models import (
    AcademicEvent,
    TrafficIntensity,
    SimulationConfig,
    ServiceCapacitySpec,
    PredictedMetricPoint,
    BottleneckAlert,
    CapacityForecastResult,
    ScenarioComparisonResult,
)
from digital_twin.simulator import CampusActivitySimulator


# Default baseline microservice infrastructure specs
DEFAULT_SPECS: Dict[str, ServiceCapacitySpec] = {
    "student_portal": ServiceCapacitySpec(
        service_name="student_portal",
        replicas=2,
        max_rps_per_replica=600.0,
        base_cpu_percent=18.0,
        base_memory_percent=32.0,
        db_connections_per_100_rps=3.5,
        max_db_connections=50,
        avg_query_latency_ms=65.0,
    ),
    "lms": ServiceCapacitySpec(
        service_name="lms",
        replicas=2,
        max_rps_per_replica=750.0,
        base_cpu_percent=22.0,
        base_memory_percent=38.0,
        db_connections_per_100_rps=4.0,
        max_db_connections=50,
        avg_query_latency_ms=90.0,
    ),
    "exam_service": ServiceCapacitySpec(
        service_name="exam_service",
        replicas=2,
        max_rps_per_replica=400.0,
        base_cpu_percent=26.0,
        base_memory_percent=35.0,
        db_connections_per_100_rps=6.0,  # High transactional DB reads/writes
        max_db_connections=50,
        avg_query_latency_ms=120.0,
    ),
    "library_service": ServiceCapacitySpec(
        service_name="library_service",
        replicas=1,
        max_rps_per_replica=500.0,
        base_cpu_percent=15.0,
        base_memory_percent=25.0,
        db_connections_per_100_rps=2.5,
        max_db_connections=30,
        avg_query_latency_ms=50.0,
    ),
}


class PredictiveCapacityPlanner:
    """
    Predictive capacity planning engine.
    Forecasts microservice resource utilization, detects infrastructure bottlenecks,
    and formulates proactive SRE recommendations before degradation occurs.
    """

    def __init__(self, specs: Optional[Dict[str, ServiceCapacitySpec]] = None):
        self.specs = specs or {k: v.model_copy() for k, v in DEFAULT_SPECS.items()}
        self.simulator = CampusActivitySimulator()

    def apply_capacity_overrides(self, overrides: Dict[str, Dict[str, Any]]):
        """Allows testing custom infrastructure capacities (e.g., scaled replicas)."""
        for s_name, override_dict in overrides.items():
            if s_name in self.specs:
                curr = self.specs[s_name].model_dump()
                curr.update(override_dict)
                self.specs[s_name] = ServiceCapacitySpec(**curr)

    def forecast_service_metric(
        self,
        service_name: str,
        predicted_rps: float,
        hour: int,
        time_label: str,
    ) -> PredictedMetricPoint:
        """
        Calculates predicted CPU, Memory, Latency, and DB Pool utilization for a service.
        """
        spec = self.specs.get(service_name, DEFAULT_SPECS["student_portal"])
        total_capacity_rps = spec.replicas * spec.max_rps_per_replica
        utilization_ratio = predicted_rps / max(total_capacity_rps, 1.0)
        util_pct = round(min(100.0, utilization_ratio * 100.0), 2)

        # 1. Non-linear CPU utilization (exponential increase under heavy load)
        cpu_load = math.pow(min(utilization_ratio, 2.0), 1.35) * 65.0
        predicted_cpu = round(min(100.0, spec.base_cpu_percent + cpu_load), 1)

        # 2. Memory utilization (stateful sessions and memory buffers)
        mem_load = min(utilization_ratio, 1.8) * 45.0
        predicted_mem = round(min(100.0, spec.base_memory_percent + mem_load), 1)

        # 3. Latency estimation (M/M/c queuing curve)
        if utilization_ratio < 0.70:
            predicted_lat = spec.avg_query_latency_ms * (1.0 + 0.3 * utilization_ratio)
        elif utilization_ratio < 0.95:
            predicted_lat = spec.avg_query_latency_ms * (1.5 + 2.5 * (utilization_ratio - 0.70))
        else:
            # Saturation queue buildup
            predicted_lat = spec.avg_query_latency_ms * (3.5 + 8.0 * (utilization_ratio - 0.95))
        predicted_lat = round(min(3000.0, predicted_lat), 1)

        # 4. Database Connection Pool Usage
        active_db_conns = int((predicted_rps / 100.0) * spec.db_connections_per_100_rps + 4)
        active_db_conns = min(active_db_conns, spec.max_db_connections + 20)
        pool_sat_pct = round(min(100.0, (active_db_conns / spec.max_db_connections) * 100.0), 1)

        # 5. Bottleneck Determination
        reasons = []
        if predicted_cpu >= 85.0:
            reasons.append(f"CPU Saturation predicted ({predicted_cpu}% >= 85%)")
        if predicted_mem >= 90.0:
            reasons.append(f"Memory Pressure / OOM Risk predicted ({predicted_mem}% >= 90%)")
        if pool_sat_pct >= 85.0:
            reasons.append(f"Database Connection Pool Saturation ({pool_sat_pct}% of {spec.max_db_connections} conns)")
        if util_pct >= 95.0:
            reasons.append(f"Throughput limit exceeded ({predicted_rps:.0f} RPS >= {total_capacity_rps:.0f} RPS cap)")

        is_bottleneck = len(reasons) > 0

        return PredictedMetricPoint(
            hour=hour,
            time_label=time_label,
            service_name=service_name,
            predicted_rps=predicted_rps,
            capacity_rps=total_capacity_rps,
            utilization_percent=util_pct,
            predicted_cpu_percent=predicted_cpu,
            predicted_memory_percent=predicted_mem,
            predicted_latency_ms=predicted_lat,
            predicted_db_connections=active_db_conns,
            db_pool_saturation_percent=pool_sat_pct,
            is_bottleneck=is_bottleneck,
            bottleneck_reasons=reasons,
            is_simulation=True,
        )

    def generate_capacity_forecast(self, config: SimulationConfig) -> CapacityForecastResult:
        """
        Runs full simulation and predictive capacity planning over the configured time range.
        """
        # Apply capacity overrides if provided
        if config.capacity_overrides:
            self.apply_capacity_overrides(config.capacity_overrides)

        activity_timeline = self.simulator.simulate_timeline(config)
        
        metrics_by_svc: Dict[str, List[PredictedMetricPoint]] = {
            s: [] for s in self.specs.keys()
        }
        alerts: List[BottleneckAlert] = []
        alert_counter = 1

        peak_concurrent = 0
        peak_hour = 0
        peak_total_rps = 0.0

        for pt in activity_timeline:
            if pt.concurrent_students > peak_concurrent:
                peak_concurrent = pt.concurrent_students
                peak_hour = pt.hour
            if pt.total_incoming_rps > peak_total_rps:
                peak_total_rps = pt.total_incoming_rps

            for s_name in self.specs.keys():
                s_rps = pt.service_rps.get(s_name, 0.0)
                m_point = self.forecast_service_metric(s_name, s_rps, pt.hour, pt.time_label)
                metrics_by_svc[s_name].append(m_point)

                # Generate alert if bottleneck predicted
                if m_point.is_bottleneck:
                    # Choose primary bottleneck
                    if m_point.db_pool_saturation_percent >= 85.0:
                        primary = "DB_POOL"
                        val = m_point.db_pool_saturation_percent
                        thresh = 85.0
                        rec = f"Pre-scale {s_name} replicas and increase DB pool max_connections to {int(self.specs[s_name].max_db_connections * 1.5)}"
                    elif m_point.predicted_cpu_percent >= 85.0:
                        primary = "CPU"
                        val = m_point.predicted_cpu_percent
                        thresh = 85.0
                        rec = f"Pre-scale {s_name} from {self.specs[s_name].replicas} to {self.specs[s_name].replicas + 2} replicas prior to peak"
                    elif m_point.predicted_memory_percent >= 90.0:
                        primary = "MEMORY"
                        val = m_point.predicted_memory_percent
                        thresh = 90.0
                        rec = f"Increase container memory limit or scale {s_name} to {self.specs[s_name].replicas + 2} replicas"
                    else:
                        primary = "RPS_CAPACITY"
                        val = m_point.utilization_percent
                        thresh = 95.0
                        rec = f"Autoscale {s_name} replicas from {self.specs[s_name].replicas} to {self.specs[s_name].replicas + 2}"

                    sev = "CRITICAL" if (m_point.predicted_cpu_percent >= 92.0 or m_point.db_pool_saturation_percent >= 95.0) else "WARNING"
                    
                    # Target replicas recommended to restore headroom (<70% utilization)
                    needed_reps = max(
                        self.specs[s_name].replicas + 1,
                        int(math.ceil(m_point.predicted_rps / (self.specs[s_name].max_rps_per_replica * 0.65)))
                    )

                    alert = BottleneckAlert(
                        alert_id=f"PRED-ALT-{alert_counter:04d}",
                        service_name=s_name,
                        hour=pt.hour,
                        time_label=pt.time_label,
                        severity=sev,
                        primary_bottleneck=primary,
                        predicted_value=val,
                        threshold_value=thresh,
                        lead_time_hours=max(1, pt.hour),
                        explanation="; ".join(m_point.bottleneck_reasons),
                        recommendation=rec,
                        target_replicas=needed_reps,
                        is_simulation=True,
                    )
                    alerts.append(alert)
                    alert_counter += 1

        # Summary assessment
        has_critical = any(a.severity == "CRITICAL" for a in alerts)
        has_warning = len(alerts) > 0
        overall = "CRITICAL" if has_critical else ("WARNING" if has_warning else "HEALTHY")

        if overall == "HEALTHY":
            exec_summary = f"Infrastructure headroom is sufficient. Peak concurrency of {peak_concurrent:,} users generates {peak_total_rps:.1f} RPS with all services below 75% capacity."
        elif overall == "WARNING":
            exec_summary = f"Moderate capacity pressure predicted during {config.event.value}. {len(alerts)} warning alerts identified across {len(set(a.service_name for a in alerts))} services. Pre-emptive scaling recommended."
        else:
            exec_summary = f"High saturation bottleneck detected during {config.event.value}. Peak load of {peak_total_rps:.1f} RPS will exhaust resources. Proactive intervention required."

        return CapacityForecastResult(
            config=config,
            total_students=config.total_students,
            event=config.event,
            intensity=config.intensity,
            peak_concurrent_users=peak_concurrent,
            peak_hour=peak_hour,
            peak_rps=peak_total_rps,
            timeline=activity_timeline,
            metrics_by_service=metrics_by_svc,
            alerts=alerts,
            overall_status=overall,
            executive_summary=exec_summary,
            is_simulation=True,
        )

    def compare_scenarios(self, base_config: SimulationConfig) -> ScenarioComparisonResult:
        """
        Runs comparative simulation comparing:
        1. Normal baseline day (Intensity: NORMAL, Event: NORMAL_DAY)
        2. Peak day (Intensity: PEAK, Event: configured or EXAM_PERIOD)
        3. Extreme day (Intensity: EXTREME, Event: RESULT_ANNOUNCEMENT)
        """
        configs = {
            "Baseline Normal": base_config.model_copy(update={"intensity": TrafficIntensity.NORMAL, "event": AcademicEvent.NORMAL_DAY}),
            "Peak Academic": base_config.model_copy(update={"intensity": TrafficIntensity.PEAK, "event": base_config.event if base_config.event != AcademicEvent.NORMAL_DAY else AcademicEvent.EXAM_PERIOD}),
            "Extreme Shock": base_config.model_copy(update={"intensity": TrafficIntensity.EXTREME, "event": AcademicEvent.RESULT_ANNOUNCEMENT}),
        }

        results = {}
        table = []

        for name, cfg in configs.items():
            planner = PredictiveCapacityPlanner()
            res = planner.generate_capacity_forecast(cfg)
            results[name] = res
            
            # Extract key metrics
            max_cpu = max(
                max(p.predicted_cpu_percent for p in pts)
                for pts in res.metrics_by_service.values()
            )
            max_pool = max(
                max(p.db_pool_saturation_percent for p in pts)
                for pts in res.metrics_by_service.values()
            )

            table.append({
                "scenario_name": name,
                "event": cfg.event.value,
                "intensity": cfg.intensity.value,
                "peak_concurrent_users": res.peak_concurrent_users,
                "peak_rps": round(res.peak_rps, 1),
                "peak_cpu_percent": round(max_cpu, 1),
                "peak_db_pool_percent": round(max_pool, 1),
                "alert_count": len(res.alerts),
                "overall_status": res.overall_status,
            })

        findings = [
            f"Under 'Baseline Normal', campus infrastructure operates safely with peak CPU at {table[0]['peak_cpu_percent']}% and {table[0]['alert_count']} alerts.",
            f"Under '{table[1]['scenario_name']}', concurrency jumps to {table[1]['peak_concurrent_users']:,} users, triggering {table[1]['alert_count']} capacity warnings.",
            f"Under '{table[2]['scenario_name']}', peak request rate reaches {table[2]['peak_rps']} RPS; database pool saturation reaches {table[2]['peak_db_pool_percent']}%. Proactive pre-scaling is strongly advised.",
        ]

        return ScenarioComparisonResult(
            scenarios=results,
            comparison_table=table,
            key_findings=findings,
            is_simulation=True,
        )

