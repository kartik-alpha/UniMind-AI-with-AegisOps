import React, { useState, useEffect } from 'react';
import {
  Activity,
  Server,
  AlertTriangle,
  Zap,
  Cpu,
  Layers,
  ArrowRight,
  ShieldCheck,
  Flame,
  CheckCircle2,
  RefreshCw,
} from 'lucide-react';

export default function AegisOverviewView({ onNavigate }) {
  const [overview, setOverview] = useState(null);
  const [chaosLoading, setChaosLoading] = useState(false);

  const fetchOverview = async () => {
    try {
      const res = await fetch('/api/v1/aegisops/overview');
      if (res.ok) setOverview(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const handleToggleChaos = async () => {
    setChaosLoading(true);
    try {
      const res = await fetch('/api/v1/aegisops/chaos/toggle', { method: 'POST' });
      if (res.ok) {
        await fetchOverview();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setChaosLoading(false);
    }
  };

  const isChaos = overview?.chaos_active ?? true;

  return (
    <div className="space-y-6">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-900 mt-0.5">AegisOps Cluster Overview</h2>
          <p className="text-xs text-slate-500 mt-1">
            Predictive SRE Observability, Isolation Forest Telemetry, and Autonomous Incident Healing.
          </p>
        </div>

        <button
          onClick={fetchOverview}
          className="px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-all self-start sm:self-auto"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* Chaos Engineering Interactive Banner */}
      <div
        className={`rounded-2xl p-6 border shadow-sm transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-5 ${
          isChaos
            ? 'bg-gradient-to-r from-amber-900/90 via-slate-900 to-rose-950 text-white border-amber-600/50'
            : 'bg-gradient-to-r from-slate-900 via-slate-800 to-blue-950 text-white border-slate-800'
        }`}
      >
        <div className="space-y-1.5 max-w-xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold border backdrop-blur-md bg-white/10 text-white">
            <Flame className={`h-3.5 w-3.5 ${isChaos ? 'text-amber-400 animate-bounce' : 'text-slate-400'}`} />
            <span>Chaos Simulation: {isChaos ? 'ACTIVE INJECTION' : 'STANDBY'}</span>
          </div>

          <h3 className="text-lg font-bold">
            {isChaos
              ? 'Chaos Scenario: Exam Service Under Peak DB Contention'
              : 'All Microservices Running Within Healthy Baseline Bounds'}
          </h3>
          <p className="text-xs text-slate-300 leading-relaxed">
            {isChaos
              ? 'Injected high latency (>1800ms) and CPU spikes (>90%) into Exam Service to test AegisOps predictive Isolation Forest anomaly detection and automated runbook self-healing.'
              : 'Normal traffic mode active across all 4 microservices. Anomaly scores are well within nominal safety thresholds (<0.20).'}
          </p>
        </div>

        <div className="flex flex-col sm:flex-row gap-3">
          <button
            onClick={handleToggleChaos}
            disabled={chaosLoading}
            className={`px-4 py-2.5 rounded-lg text-xs font-bold flex items-center gap-2 shadow-lg transition-all ${
              isChaos
                ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                : 'bg-rose-600 hover:bg-rose-500 text-white'
            }`}
          >
            <Zap className="h-4 w-4" />
            <span>{isChaos ? 'Disable Chaos (Restore Normal)' : 'Inject Chaos Anomaly'}</span>
          </button>

          {isChaos && (
            <button
              onClick={() => onNavigate('remediation')}
              className="px-4 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg transition-all"
            >
              <Activity className="h-4 w-4" />
              <span>Remediate Now</span>
            </button>
          )}
        </div>
      </div>

      {/* Cluster Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Cluster Health</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${isChaos ? 'text-amber-600' : 'text-emerald-600'}`}>
              {isChaos ? '75%' : '100%'}
            </span>
            <span className="text-xs text-slate-500">Operational</span>
          </div>
          <div className="w-full bg-slate-100 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className={`h-full rounded-full ${isChaos ? 'bg-amber-500 w-3/4' : 'bg-emerald-500 w-full'}`}
            ></div>
          </div>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Active Incidents</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${isChaos ? 'text-rose-600' : 'text-slate-800'}`}>
              {isChaos ? '1 Active' : '0 Active'}
            </span>
          </div>
          <p className="text-xs text-slate-500 mt-2">
            {isChaos ? 'INC-2026-0842 (Exam Service)' : 'No active alerts'}
          </p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Mean Time to Detect (MTTD)</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-blue-600">1.2 min</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Isolation Forest threshold: 0.70</p>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Mean Time to Recover (MTTR)</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-600">3.4 min</span>
          </div>
          <p className="text-xs text-slate-500 mt-2">Automated pod restart & scaling</p>
        </div>
      </div>

      {/* Microservices Topology Architecture Diagram */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-6">
        <div>
          <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
            Campus Microservices Architecture & Traffic Topology
          </h3>
          <p className="text-xs text-slate-500 mt-0.5">
            Real-time inter-service routing, telemetry probes, and data persistence layers.
          </p>
        </div>

        <div className="bg-slate-50 border border-slate-200 rounded-xl p-6 relative overflow-hidden">
          {/* Top: Ingress / Client Gateway */}
          <div className="flex justify-center mb-8">
            <div className="bg-[#0b132b] text-white px-6 py-2.5 rounded-xl shadow-md text-center border border-slate-700">
              <span className="text-[10px] font-bold uppercase tracking-wider text-blue-400 block">Ingress Controller</span>
              <span className="text-xs font-bold">UniMind Cloud Gateway (:80 / :443)</span>
            </div>
          </div>

          {/* Middle: 4 Microservices Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative z-10">
            {/* Exam Service */}
            <div
              className={`p-4 rounded-xl border transition-all ${
                isChaos
                  ? 'bg-rose-50 border-rose-300 shadow-sm'
                  : 'bg-white border-slate-200 shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-slate-500">Port 8003</span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    isChaos ? 'bg-rose-100 text-rose-700 animate-pulse' : 'bg-emerald-100 text-emerald-700'
                  }`}
                >
                  {isChaos ? 'Degraded' : 'Healthy'}
                </span>
              </div>
              <h4 className="font-bold text-slate-900 text-sm">Exam Service</h4>
              <p className="text-[11px] text-slate-500 mt-1">Results & Submissions</p>
              <div className="mt-3 pt-2 border-t border-slate-200/60 font-mono text-[11px] flex justify-between">
                <span>CPU: {isChaos ? '92%' : '25%'}</span>
                <span>Lat: {isChaos ? '1,800ms' : '110ms'}</span>
              </div>
            </div>

            {/* LMS */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-slate-500">Port 8001</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                  Healthy
                </span>
              </div>
              <h4 className="font-bold text-slate-900 text-sm">LMS Service</h4>
              <p className="text-[11px] text-slate-500 mt-1">Courses & Assignments</p>
              <div className="mt-3 pt-2 border-t border-slate-200/60 font-mono text-[11px] flex justify-between">
                <span>CPU: 24%</span>
                <span>Lat: 110ms</span>
              </div>
            </div>

            {/* Student Portal */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-slate-500">Port 8002</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                  Healthy
                </span>
              </div>
              <h4 className="font-bold text-slate-900 text-sm">Student Portal</h4>
              <p className="text-[11px] text-slate-500 mt-1">Profile & Enrolment</p>
              <div className="mt-3 pt-2 border-t border-slate-200/60 font-mono text-[11px] flex justify-between">
                <span>CPU: 18%</span>
                <span>Lat: 85ms</span>
              </div>
            </div>

            {/* Library Service */}
            <div className="p-4 rounded-xl border border-slate-200 bg-white shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-slate-500">Port 8004</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-700">
                  Healthy
                </span>
              </div>
              <h4 className="font-bold text-slate-900 text-sm">Library Service</h4>
              <p className="text-[11px] text-slate-500 mt-1">Catalog & RFID Borrows</p>
              <div className="mt-3 pt-2 border-t border-slate-200/60 font-mono text-[11px] flex justify-between">
                <span>CPU: 12%</span>
                <span>Lat: 45ms</span>
              </div>
            </div>
          </div>

          {/* Bottom: Persistence & Monitoring Layer */}
          <div className="mt-8 pt-6 border-t border-slate-200 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs">
            <div className="bg-white p-2.5 rounded-lg border border-slate-200 font-semibold text-slate-700">
              PostgreSQL 15 (unimind_db)
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-slate-200 font-semibold text-slate-700">
              Redis 7.2 (Cache & Queues)
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-slate-200 font-semibold text-slate-700">
              Prometheus + Loki Engine
            </div>
            <div className="bg-white p-2.5 rounded-lg border border-slate-200 font-semibold text-slate-700">
              ChromaDB Vector Store
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
