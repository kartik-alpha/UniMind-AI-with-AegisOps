import React, { useState, useEffect } from 'react';
import {
  Flame,
  Zap,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Server,
  Activity,
  Sparkles,
  Wrench,
  Clock,
  Layers,
  ArrowRight,
  XCircle,
} from 'lucide-react';
import { apiFetch, getTenantId, parseApiError } from '../apiClient';

export default function ChaosSimulationView({ onNavigate }) {
  const [service, setService] = useState('exam_service');
  const [scenario, setScenario] = useState('database');
  const [severity, setSeverity] = useState('HIGH');
  const [duration, setDuration] = useState(60);

  const [loading, setLoading] = useState(false);
  const [chaosResult, setChaosResult] = useState(null);
  const [liveAnomaly, setLiveAnomaly] = useState(null);
  const [activeIncident, setActiveIncident] = useState(null);
  const [diagnosis, setDiagnosis] = useState(null);
  const [remediationResult, setRemediationResult] = useState(null);
  const [remediationLoading, setRemediationLoading] = useState(false);

  const fetchStatus = async () => {
    try {
      const [overviewRes, anomRes] = await Promise.all([
        apiFetch('/api/v1/aegisops/overview'),
        apiFetch('/api/v1/ml/anomaly-scores'),
      ]);
      if (overviewRes.ok) {
        const data = await overviewRes.json();
        if (data.active_incident_details && data.active_incident_details.length > 0) {
          setActiveIncident(data.active_incident_details[0]);
        } else {
          setActiveIncident(null);
        }
      }
      if (anomRes.ok) {
        setLiveAnomaly(await anomRes.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchStatus();
    const interval = setInterval(fetchStatus, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleInjectChaos = async () => {
    setLoading(true);
    setRemediationResult(null);
    try {
      const res = await apiFetch('/api/v1/aegisops/chaos/inject', {
        method: 'POST',
        body: JSON.stringify({
          service_name: service,
          scenario: scenario,
          severity: severity,
          duration_seconds: parseInt(duration),
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setChaosResult(data);
        if (data.incident) {
          setActiveIncident(data.incident);
        }
        handleFetchDiagnosis(service);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      fetchStatus();
    }
  };

  const handleRestoreBaseline = async () => {
    setLoading(true);
    try {
      await apiFetch('/api/v1/aegisops/chaos/restore', {
        method: 'POST',
        body: JSON.stringify({ service_name: service }),
      });
      setChaosResult(null);
      setDiagnosis(null);
      setRemediationResult({ status: 'RESOLVED', message: 'All services restored to healthy baseline.' });
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
      fetchStatus();
    }
  };

  const handleFetchDiagnosis = async (targetService) => {
    try {
      const res = await apiFetch(`/api/v1/aegisops/diagnose/${encodeURIComponent(targetService || service)}`, {
        method: 'POST',
      });
      if (res.ok) {
        setDiagnosis(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleApproveRemediation = async () => {
    if (!activeIncident && !chaosResult?.incident) return;
    const incId = activeIncident?.id || chaosResult?.incident?.id || 1;

    setRemediationLoading(true);
    try {
      const res = await apiFetch('/api/v1/aegisops/remediate/approve', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: incId,
          action: 'RESTART_POD',
          target_replicas: 4,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setRemediationResult(data);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setRemediationLoading(false);
      fetchStatus();
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Chaos Engineering Simulator</h2>
          <p className="text-xs text-slate-400 mt-1">
            Simulate real-world production outages and evaluate ML anomaly detection, AI diagnosis, and autonomous self-healing.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleRestoreBaseline}
            disabled={loading}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-xs font-bold rounded-lg transition-all flex items-center gap-1.5 shadow-sm"
          >
            <RotateCcw className="h-3.5 w-3.5 text-cyan-400" />
            <span>Restore Nominal Baseline</span>
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Controls Column */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 shadow-sm space-y-4">
          <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider flex items-center gap-2">
            <Flame className="h-4 w-4 text-rose-500" /> Inject Chaos Failure
          </h3>

          <div>
            <label className="text-[11px] font-bold text-slate-400 block mb-1">Target Service</label>
            <select
              value={service}
              onChange={(e) => setService(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="exam_service">Exam Service (Port 8003)</option>
              <option value="lms">LMS Service (Port 8001)</option>
              <option value="student_portal">Student Portal (Port 8002)</option>
              <option value="library_service">Library Service (Port 8004)</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-bold text-slate-400 block mb-1">Failure Scenario</label>
            <select
              value={scenario}
              onChange={(e) => setScenario(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="database">Database Pool Exhaustion (High Latency + 503)</option>
              <option value="cpu">CPU Saturation Spike (95%+ Usage)</option>
              <option value="memory">Memory Leak & OOM Pressure (90%+ RAM)</option>
              <option value="network">Network Packet Latency / Jitter (2,500ms)</option>
              <option value="http_errors">HTTP 500 / 503 Burst Spike</option>
              <option value="combined">Cascading Outage (Combined Stress)</option>
            </select>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="text-[11px] font-bold text-slate-400 block mb-1">Severity</label>
              <select
                value={severity}
                onChange={(e) => setSeverity(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              >
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
                <option value="CRITICAL">Critical</option>
              </select>
            </div>

            <div>
              <label className="text-[11px] font-bold text-slate-400 block mb-1">Duration (Sec)</label>
              <input
                type="number"
                min="10"
                max="600"
                value={duration}
                onChange={(e) => setDuration(e.target.value)}
                className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
            </div>
          </div>

          <button
            onClick={handleInjectChaos}
            disabled={loading}
            className="w-full py-3 bg-rose-600 hover:bg-rose-500 text-white font-bold text-xs rounded-xl shadow-lg transition-all flex items-center justify-center gap-2 disabled:opacity-50"
          >
            <Flame className="h-4 w-4" />
            <span>{loading ? 'Injecting Chaos Outage...' : 'Inject Chaos Outage'}</span>
          </button>
        </div>

        {/* Live Observability / Diagnosis Column */}
        <div className="lg:col-span-2 space-y-4">
          {chaosResult && (
            <div className="bg-rose-950/20 border border-rose-500/40 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-rose-400 flex items-center gap-1.5 uppercase tracking-wider">
                  <AlertTriangle className="h-4 w-4" /> Live Chaos Active
                </span>
                <span className="font-mono text-xs font-bold text-rose-300">
                  Anomaly Score: {(chaosResult.anomaly_score * 100).toFixed(1)}%
                </span>
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">CPU</span>
                  <span className="font-mono font-bold text-rose-400">
                    {chaosResult.telemetry.cpu_usage_percent}%
                  </span>
                </div>
                <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Memory</span>
                  <span className="font-mono font-bold text-rose-400">
                    {chaosResult.telemetry.memory_usage_percent}%
                  </span>
                </div>
                <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Latency</span>
                  <span className="font-mono font-bold text-rose-400">
                    {chaosResult.telemetry.latency_ms} ms
                  </span>
                </div>
                <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-800">
                  <span className="text-slate-400 block text-[10px]">Error Rate</span>
                  <span className="font-mono font-bold text-rose-400">
                    {chaosResult.telemetry.error_rate_percent}%
                  </span>
                </div>
              </div>
            </div>
          )}

          {diagnosis && (
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 space-y-3">
              <div className="flex items-center justify-between pb-2 border-b border-slate-700/60">
                <span className="text-xs font-bold text-cyan-400 flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4" /> Automated AI Diagnosis
                </span>
                <span className="text-[10px] bg-cyan-500/10 text-cyan-300 font-bold px-2 py-0.5 rounded border border-cyan-500/20">
                  Confidence: {Math.round((diagnosis.confidence_score || 0.88) * 100)}%
                </span>
              </div>

              <div>
                <h4 className="text-sm font-bold text-slate-100">{diagnosis.suspected_root_cause}</h4>
                <p className="text-xs text-slate-400 mt-1">{diagnosis.evidence}</p>
              </div>

              <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/60 text-xs flex items-center justify-between gap-3">
                <div>
                  <span className="font-bold text-slate-300 block">Recommended Self-Healing:</span>
                  <span className="text-cyan-400 font-mono text-[11px]">{diagnosis.recommended_remediation}</span>
                </div>
                <button
                  onClick={handleApproveRemediation}
                  disabled={remediationLoading}
                  className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs rounded-lg transition-all flex items-center gap-1.5 shadow-sm disabled:opacity-50 shrink-0"
                >
                  <Wrench className={`h-3.5 w-3.5 ${remediationLoading ? 'animate-spin' : ''}`} />
                  <span>Approve & Remediate</span>
                </button>
              </div>
            </div>
          )}

          {remediationResult && (
            <div className="bg-emerald-950/20 border border-emerald-500/40 rounded-xl p-4 text-xs text-emerald-300 flex items-center gap-2">
              <CheckCircle2 className="h-5 w-5 text-emerald-400 shrink-0" />
              <span>{remediationResult.message || 'Remediation completed successfully. Cluster restored.'}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
