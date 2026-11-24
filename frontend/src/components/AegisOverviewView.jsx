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
    <div className="space-y-6 animate-fadeIn">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">AegisOps Cluster Overview</h2>
          <p className="text-xs text-slate-400 mt-1">
            Predictive SRE Observability, Isolation Forest Telemetry, and Autonomous Incident Healing.
          </p>
        </div>

        <button
          onClick={fetchOverview}
          className="px-3 py-2 bg-slate-800 border border-slate-700 hover:bg-slate-700/80 text-slate-300 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-all self-start sm:self-auto"
        >
          <RefreshCw className="h-4 w-4 text-cyan-400" />
          <span>Refresh Telemetry</span>
        </button>
      </div>

      {/* Chaos Engineering Interactive Banner */}
      <div
        className={`rounded-2xl p-6 border shadow-lg transition-all flex flex-col md:flex-row items-start md:items-center justify-between gap-5 ${
          isChaos
            ? 'bg-gradient-to-r from-amber-950/80 via-slate-900 to-rose-950/80 text-white border-amber-600/40'
            : 'bg-gradient-to-r from-slate-900 via-slate-800 to-blue-950/80 text-white border-slate-700/60'
        }`}
      >
        <div className="space-y-1.5 max-w-xl">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-bold border backdrop-blur-md bg-white/10 text-white">
            <Flame className={`h-3.5 w-3.5 ${isChaos ? 'text-amber-400 animate-bounce' : 'text-slate-400'}`} />
            <span>Chaos Simulation: {isChaos ? 'ACTIVE INJECTION' : 'STANDBY'}</span>
          </div>

          <h3 className="text-lg font-bold text-slate-100">
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
            <span>{isChaos ? 'Disable Chaos (Restore Normal)' : 'Quick Chaos Toggle'}</span>
          </button>

          <button
            onClick={() => onNavigate('digital_twin')}
            className="px-4 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg transition-all"
          >
            <Activity className="h-4 w-4" />
            <span>Digital Twin Planning</span>
          </button>

          <button
            onClick={() => onNavigate('chaos')}
            className="px-4 py-2.5 rounded-lg bg-amber-600 hover:bg-amber-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg transition-all"
          >
            <Flame className="h-4 w-4" />
            <span>Chaos Simulator Console</span>
          </button>

          {isChaos && (
            <button
              onClick={() => onNavigate('remediation')}
              className="px-4 py-2.5 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg transition-all"
            >
              <Activity className="h-4 w-4" />
              <span>Remediate Now</span>
            </button>
          )}
        </div>
      </div>

      {/* Cluster Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Cluster Health</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${isChaos ? 'text-amber-400' : 'text-emerald-400'}`}>
              {isChaos ? '75%' : '100%'}
            </span>
            <span className="text-xs text-slate-400">Operational</span>
          </div>
          <div className="w-full bg-slate-700/60 rounded-full h-1.5 mt-3 overflow-hidden">
            <div
              className={`h-full rounded-full ${isChaos ? 'bg-amber-500 w-3/4' : 'bg-emerald-500 w-full'}`}
            ></div>
          </div>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Active Incidents</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className={`text-2xl font-bold font-mono ${isChaos ? 'text-rose-400' : 'text-slate-100'}`}>
              {isChaos ? '1 Active' : '0 Active'}
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            {isChaos ? 'INC-2026-0842 (Exam Service)' : 'No active alerts'}
          </p>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Mean Time to Detect (MTTD)</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-cyan-400">1.2 min</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Isolation Forest threshold: 0.70</p>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Mean Time to Recover (MTTR)</span>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-2xl font-bold font-mono text-emerald-400">3.4 min</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">Automated pod restart & scaling</p>
        </div>
      </div>

      {/* Microservices Topology Architecture Diagram */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 shadow-sm space-y-6">
        <div>
          <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider">
            Campus Microservices Architecture & Traffic Topology
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Real-time inter-service routing, telemetry probes, and data persistence layers.
          </p>
        </div>

        <div className="bg-slate-900/60 border border-slate-700/60 rounded-xl p-6 relative overflow-hidden">
          {/* Top: Ingress / Client Gateway */}
          <div className="flex justify-center mb-8">
            <div className="bg-[#0b132b] text-white px-6 py-2.5 rounded-xl shadow-md text-center border border-slate-700">
              <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400 block">Ingress Controller</span>
              <span className="text-xs font-bold text-slate-200">UniMind Cloud Gateway (:80 / :443)</span>
            </div>
          </div>

          {/* Middle: 4 Microservices Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 relative z-10">
            {/* Exam Service */}
            <div
              className={`p-4 rounded-xl border transition-all ${
                isChaos
                  ? 'bg-rose-950/30 border-rose-500/40 shadow-sm'
                  : 'bg-slate-800/80 border-slate-700/60 shadow-sm'
              }`}
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-slate-400">Port 8003</span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    isChaos
                      ? 'bg-rose-500/10 text-rose-400 border-rose-500/20 animate-pulse'
                      : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  }`}
                >
                  {isChaos ? 'Degraded' : 'Healthy'}
                </span>
              </div>
              <h4 className="font-bold text-slate-100 text-sm">Exam Service</h4>
              <p className="text-[11px] text-slate-400 mt-1">Results & Submissions</p>
              <div className="mt-3 pt-2 border-t border-slate-700/60 font-mono text-[11px] flex justify-between text-slate-300">
                <span>CPU: {isChaos ? '92%' : '25%'}</span>
                <span>Lat: {isChaos ? '1,800ms' : '110ms'}</span>
              </div>
            </div>

            {/* LMS */}
            <div className="p-4 rounded-xl border border-slate-700/60 bg-slate-800/80 shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-slate-400">Port 8001</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Healthy
                </span>
              </div>
              <h4 className="font-bold text-slate-100 text-sm">LMS Service</h4>
              <p className="text-[11px] text-slate-400 mt-1">Courses & Assignments</p>
              <div className="mt-3 pt-2 border-t border-slate-700/60 font-mono text-[11px] flex justify-between text-slate-300">
                <span>CPU: 24%</span>
                <span>Lat: 110ms</span>
              </div>
            </div>

            {/* Student Portal */}
            <div className="p-4 rounded-xl border border-slate-700/60 bg-slate-800/80 shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-slate-400">Port 8002</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Healthy
                </span>
              </div>
              <h4 className="font-bold text-slate-100 text-sm">Student Portal</h4>
              <p className="text-[11px] text-slate-400 mt-1">Profile & Enrolment</p>
              <div className="mt-3 pt-2 border-t border-slate-700/60 font-mono text-[11px] flex justify-between text-slate-300">
                <span>CPU: 18%</span>
                <span>Lat: 85ms</span>
              </div>
            </div>

            {/* Library Service */}
            <div className="p-4 rounded-xl border border-slate-700/60 bg-slate-800/80 shadow-sm">
              <div className="flex items-center justify-between mb-1">
                <span className="text-[10px] font-bold uppercase text-slate-400">Port 8004</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  Healthy
                </span>
              </div>
              <h4 className="font-bold text-slate-100 text-sm">Library Service</h4>
              <p className="text-[11px] text-slate-400 mt-1">Catalog & RFID Borrows</p>
              <div className="mt-3 pt-2 border-t border-slate-700/60 font-mono text-[11px] flex justify-between text-slate-300">
                <span>CPU: 12%</span>
                <span>Lat: 45ms</span>
              </div>
            </div>
          </div>

          {/* Bottom: Persistence & Monitoring Layer */}
          <div className="mt-8 pt-6 border-t border-slate-700/60 grid grid-cols-2 sm:grid-cols-4 gap-3 text-center text-xs">
            <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/60 font-semibold text-slate-300">
              PostgreSQL 15 (unimind_db)
            </div>
            <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/60 font-semibold text-slate-300">
              Redis 7.2 (Cache & Queues)
            </div>
            <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/60 font-semibold text-slate-300">
              Prometheus + Loki Engine
            </div>
            <div className="bg-slate-800/80 p-2.5 rounded-lg border border-slate-700/60 font-semibold text-slate-300">
              ChromaDB Vector Store
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
