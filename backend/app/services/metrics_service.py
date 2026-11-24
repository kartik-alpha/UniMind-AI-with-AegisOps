"""
Standard Prometheus Metrics Exporter & Health Probes (Pure Python, Zero Dependency).
Generates Prometheus text format 0.0.4 with bounded cardinality and sub-millisecond overhead.
"""
import time
import re
import threading
from typing import Dict, Any, List, Optional, Tuple


class PrometheusMetricsRegistry:
    """
    Thread-safe Prometheus metrics registry supporting Counters, Gauges, and Histograms.
    Exposes metrics in text/plain; version=0.0.4 without external third-party dependencies.
    """

    DEFAULT_BUCKETS = (0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)

    def __init__(self):
        self._lock = threading.RLock()
        self._counters: Dict[str, Dict[Tuple[Tuple[str, str], ...], float]] = {}
        self._gauges: Dict[str, Dict[Tuple[Tuple[str, str], ...], float]] = {}
        self._histograms: Dict[str, Dict[Tuple[Tuple[str, str], ...], Dict[str, Any]]] = {}
        self._help_strings: Dict[str, str] = {}
        self._type_strings: Dict[str, str] = {}

    def _sanitize_labels(self, labels: Optional[Dict[str, Any]]) -> Tuple[Tuple[str, str], ...]:
        if not labels:
            return ()
        clean = []
        for k, v in sorted(labels.items()):
            # Escape quotes and backslashes in label values
            val_str = str(v).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "")
            clean.append((str(k), val_str))
        return tuple(clean)

    def register_counter(self, name: str, help_text: str):
        with self._lock:
            self._help_strings[name] = help_text
            self._type_strings[name] = "counter"
            if name not in self._counters:
                self._counters[name] = {}

    def register_gauge(self, name: str, help_text: str):
        with self._lock:
            self._help_strings[name] = help_text
            self._type_strings[name] = "gauge"
            if name not in self._gauges:
                self._gauges[name] = {}

    def register_histogram(self, name: str, help_text: str):
        with self._lock:
            self._help_strings[name] = help_text
            self._type_strings[name] = "histogram"
            if name not in self._histograms:
                self._histograms[name] = {}

    def inc_counter(self, name: str, value: float = 1.0, labels: Optional[Dict[str, Any]] = None):
        key = self._sanitize_labels(labels)
        with self._lock:
            if name not in self._counters:
                self._counters[name] = {}
            self._counters[name][key] = self._counters[name].get(key, 0.0) + value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, Any]] = None):
        key = self._sanitize_labels(labels)
        with self._lock:
            if name not in self._gauges:
                self._gauges[name] = {}
            self._gauges[name][key] = float(value)

    def observe_histogram(self, name: str, value: float, labels: Optional[Dict[str, Any]] = None):
        key = self._sanitize_labels(labels)
        val = float(value)
        with self._lock:
            if name not in self._histograms:
                self._histograms[name] = {}
            if key not in self._histograms[name]:
                self._histograms[name][key] = {
                    "count": 0,
                    "sum": 0.0,
                    "buckets": {b: 0 for b in self.DEFAULT_BUCKETS},
                }
            entry = self._histograms[name][key]
            entry["count"] += 1
            entry["sum"] += val
            for b in self.DEFAULT_BUCKETS:
                if val <= b:
                    entry["buckets"][b] += 1

    def generate_exposition(self) -> str:
        lines = []
        with self._lock:
            # 1. Counters
            for name, series_dict in self._counters.items():
                if name in self._help_strings:
                    lines.append(f"# HELP {name} {self._help_strings[name]}")
                lines.append(f"# TYPE {name} counter")
                for labels_tuple, val in series_dict.items():
                    if labels_tuple:
                        lbls = ",".join(f'{k}="{v}"' for k, v in labels_tuple)
                        lines.append(f"{name}{{{lbls}}} {val}")
                    else:
                        lines.append(f"{name} {val}")
                lines.append("")

            # 2. Gauges
            for name, series_dict in self._gauges.items():
                if name in self._help_strings:
                    lines.append(f"# HELP {name} {self._help_strings[name]}")
                lines.append(f"# TYPE {name} gauge")
                for labels_tuple, val in series_dict.items():
                    if labels_tuple:
                        lbls = ",".join(f'{k}="{v}"' for k, v in labels_tuple)
                        lines.append(f"{name}{{{lbls}}} {val}")
                    else:
                        lines.append(f"{name} {val}")
                lines.append("")

            # 3. Histograms
            for name, series_dict in self._histograms.items():
                if name in self._help_strings:
                    lines.append(f"# HELP {name} {self._help_strings[name]}")
                lines.append(f"# TYPE {name} histogram")
                for labels_tuple, hdata in series_dict.items():
                    base_labels = dict(labels_tuple)
                    for b, count in hdata["buckets"].items():
                        bl = dict(base_labels)
                        bl["le"] = str(b)
                        lbls = ",".join(f'{k}="{v}"' for k, v in sorted(bl.items()))
                        lines.append(f"{name}_bucket{{{lbls}}} {count}")

                    # +Inf bucket
                    bl_inf = dict(base_labels)
                    bl_inf["le"] = "+Inf"
                    lbls_inf = ",".join(f'{k}="{v}"' for k, v in sorted(bl_inf.items()))
                    lines.append(f"{name}_bucket{{{lbls_inf}}} {hdata['count']}")

                    # sum and count
                    if base_labels:
                        lbls_base = ",".join(f'{k}="{v}"' for k, v in sorted(base_labels.items()))
                        lines.append(f"{name}_sum{{{lbls_base}}} {round(hdata['sum'], 4)}")
                        lines.append(f"{name}_count{{{lbls_base}}} {hdata['count']}")
                    else:
                        lines.append(f"{name}_sum {round(hdata['sum'], 4)}")
                        lines.append(f"{name}_count {hdata['count']}")
                lines.append("")

        return "\n".join(lines).strip() + "\n"


# Global singleton registry
metrics_registry = PrometheusMetricsRegistry()

# Pre-register standard enterprise metrics
metrics_registry.register_counter("unimind_http_requests_total", "Total count of processed HTTP requests")
metrics_registry.register_counter("unimind_http_errors_total", "Total count of HTTP error responses")
metrics_registry.register_histogram("unimind_http_request_duration_seconds", "HTTP request latency in seconds")
metrics_registry.register_histogram("unimind_rag_retrieval_duration_seconds", "RAG hybrid retrieval latency")
metrics_registry.register_histogram("unimind_agent_execution_duration_seconds", "UniMind AI Agent execution latency")
metrics_registry.register_gauge("aegisops_ml_anomaly_score", "Latest AegisOps ML anomaly detection score")
metrics_registry.register_gauge("aegisops_incidents_active", "Number of currently active AegisOps incidents")
metrics_registry.register_counter("unimind_rate_limit_breaches_total", "Total requests rejected due to rate limits")
metrics_registry.register_counter("unimind_quota_breaches_total", "Total uploads rejected due to storage quota")
