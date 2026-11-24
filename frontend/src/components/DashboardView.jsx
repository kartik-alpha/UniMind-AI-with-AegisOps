import React from 'react';
import {
  GraduationCap,
  Activity,
  AlertTriangle,
  BookOpen,
  Database,
  Ticket,
  Cpu,
  ArrowRight,
  CheckCircle2,
  AlertCircle,
  TrendingUp,
  Server,
  Zap,
} from 'lucide-react';

export default function DashboardView({ onNavigate, servicesData, anomalyData }) {
  const stats = [
    {
      title: 'Active Infrastructure',
      value: '3 / 4 Healthy',
      subtitle: 'Exam Service degraded',
      status: 'warning',
      icon: Server,
      badge: 'Degraded',
    },
    {
      title: 'ML Anomaly Engine',
      value: 'Isolation Forest',
      subtitle: 'Anomaly score: 0.91 (Exam)',
      status: 'critical',
      icon: Cpu,
      badge: 'Active Alert',
    },
    {
      title: 'RAG Knowledge Base',
      value: '4 Official Policies',
      subtitle: 'ChromaDB Vector Store indexed',
      status: 'healthy',
      icon: BookOpen,
      badge: 'Ready',
    },
    {
      title: 'Student AI Assistant',
      value: '98% Grounded',
      subtitle: '0 Hallucination rate',
      status: 'healthy',
      icon: GraduationCap,
      badge: 'Active',
    },
  ];

  const quickActions = [
    {
      label: 'Ask Student Assistant',
      desc: 'Query attendance, hostel curfew & exam rules',
      tab: 'assistant',
      icon: GraduationCap,
      color: 'bg-cyan-600 hover:bg-cyan-500 text-white',
    },
    {
      label: 'Inspect ML Anomaly Scan',
      desc: 'View Isolation Forest multi-variate score',
      tab: 'ml_anomaly',
      icon: Cpu,
      color: 'bg-purple-600 hover:bg-purple-500 text-white',
    },
    {
      label: 'AI Root Cause Diagnosis',
      desc: 'Correlate telemetry against SRE runbooks',
      tab: 'ai_diagnosis',
      icon: Zap,
      color: 'bg-amber-600 hover:bg-amber-500 text-white',
    },
    {
      label: 'Trigger Self-Healing',
      desc: 'Automated pod restart & replica scale-out',
      tab: 'remediation',
      icon: Activity,
      color: 'bg-emerald-600 hover:bg-emerald-500 text-white',
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-[#0b132b] via-[#111827] to-[#1e293b] rounded-2xl p-6 text-white shadow-lg flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border border-slate-700/60">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 text-cyan-300 text-xs font-semibold mb-2 border border-cyan-500/20">
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-pulse"></span>
            Operational Dashboard • University Enterprise
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            UniMind AI & AegisOps Platform
          </h1>
          <p className="text-xs text-slate-400 mt-1 max-w-xl">
            Unified student support AI with automated predictive observability, intelligent RAG document retrieval, and autonomous self-healing microservices.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => onNavigate('remediation')}
            className="px-4 py-2.5 rounded-lg bg-rose-600 hover:bg-rose-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg transition-all"
          >
            <AlertTriangle className="h-4 w-4" />
            <span>Resolve Degraded Service</span>
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s, idx) => {
          const Icon = s.icon;
          return (
            <div
              key={idx}
              className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-5 shadow-sm hover:shadow-md hover:border-slate-600 transition-all relative overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                  {s.title}
                </span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    s.status === 'critical'
                      ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                      : s.status === 'warning'
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  }`}
                >
                  {s.badge}
                </span>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-xl font-bold text-slate-100">{s.value}</span>
              </div>
              <p className="text-xs text-slate-400 mt-1">{s.subtitle}</p>
              <div
                onClick={() => onNavigate(idx === 1 ? 'ml_anomaly' : idx === 2 ? 'rag' : idx === 3 ? 'assistant' : 'services')}
                className="mt-4 pt-3 border-t border-slate-700/50 flex items-center text-xs text-cyan-400 hover:text-cyan-300 font-semibold cursor-pointer"
              >
                <span>View Details</span>
                <ArrowRight className="h-3 w-3 ml-1" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Action Cards */}
      <div>
        <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3">
          Quick Workflows
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((qa, idx) => {
            const Icon = qa.icon;
            return (
              <button
                key={idx}
                onClick={() => onNavigate(qa.tab)}
                className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 text-left shadow-sm hover:border-cyan-500/50 hover:bg-slate-800/80 transition-all group flex flex-col justify-between"
              >
                <div>
                  <div className="h-9 w-9 rounded-lg bg-slate-700/50 text-cyan-400 flex items-center justify-center mb-3 group-hover:bg-cyan-600 group-hover:text-white transition-colors">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h4 className="text-sm font-bold text-slate-200 group-hover:text-cyan-300 transition-colors">
                    {qa.label}
                  </h4>
                  <p className="text-xs text-slate-400 mt-1">{qa.desc}</p>
                </div>
                <span className="mt-4 text-xs font-semibold text-cyan-400 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
                  Launch <ArrowRight className="h-3 w-3" />
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Active Incident Preview & Microservice Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Services Health Table */}
        <div className="lg:col-span-2 bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-100">Campus Microservices Fleet</h3>
              <p className="text-xs text-slate-400">Live operational telemetry & health</p>
            </div>
            <button
              onClick={() => onNavigate('services')}
              className="text-xs font-bold text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
            >
              All Services <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-900/80 text-slate-400 font-bold uppercase tracking-wider border-y border-slate-700/60">
                <tr>
                  <th className="py-2.5 px-3">Service</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">CPU</th>
                  <th className="py-2.5 px-3">Latency</th>
                  <th className="py-2.5 px-3">Replicas</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-700/50">
                <tr className="hover:bg-slate-750 hover:bg-slate-700/30 transition-colors">
                  <td className="py-3 px-3 font-semibold text-slate-200">Exam Service</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-400 animate-pulse"></span>
                      Degraded
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono text-rose-400 font-bold">92%</td>
                  <td className="py-3 px-3 font-mono text-rose-400 font-bold">1,800 ms</td>
                  <td className="py-3 px-3 font-mono text-slate-300">2 / 2</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onNavigate('ai_diagnosis')}
                      className="px-2.5 py-1 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-600 hover:text-white rounded text-[11px] font-bold transition-all border border-cyan-500/20"
                    >
                      Diagnose
                    </button>
                  </td>
                </tr>

                <tr className="hover:bg-slate-700/30 transition-colors">
                  <td className="py-3 px-3 font-semibold text-slate-200">LMS Service</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                      Healthy
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">24%</td>
                  <td className="py-3 px-3 font-mono text-slate-300">110 ms</td>
                  <td className="py-3 px-3 font-mono text-slate-300">3 / 3</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onNavigate('monitoring')}
                      className="px-2.5 py-1 bg-slate-700/60 text-slate-300 hover:bg-slate-700 hover:text-white rounded text-[11px] font-bold transition-all border border-slate-600/50"
                    >
                      Monitor
                    </button>
                  </td>
                </tr>

                <tr className="hover:bg-slate-700/30 transition-colors">
                  <td className="py-3 px-3 font-semibold text-slate-200">Student Portal</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                      Healthy
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">18%</td>
                  <td className="py-3 px-3 font-mono text-slate-300">85 ms</td>
                  <td className="py-3 px-3 font-mono text-slate-300">2 / 2</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onNavigate('monitoring')}
                      className="px-2.5 py-1 bg-slate-700/60 text-slate-300 hover:bg-slate-700 hover:text-white rounded text-[11px] font-bold transition-all border border-slate-600/50"
                    >
                      Monitor
                    </button>
                  </td>
                </tr>

                <tr className="hover:bg-slate-700/30 transition-colors">
                  <td className="py-3 px-3 font-semibold text-slate-200">Library Service</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                      Healthy
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono text-slate-300">12%</td>
                  <td className="py-3 px-3 font-mono text-slate-300">45 ms</td>
                  <td className="py-3 px-3 font-mono text-slate-300">1 / 1</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onNavigate('monitoring')}
                      className="px-2.5 py-1 bg-slate-700/60 text-slate-300 hover:bg-slate-700 hover:text-white rounded text-[11px] font-bold transition-all border border-slate-600/50"
                    >
                      Monitor
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Right 1 Col: Active Incident Banner */}
        <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-rose-400 uppercase tracking-wider flex items-center gap-1">
                <AlertCircle className="h-3.5 w-3.5" /> Active SRE Alert
              </span>
              <span className="text-[10px] font-mono bg-rose-500/10 text-rose-400 px-2 py-0.5 rounded font-bold border border-rose-500/20">
                CRITICAL
              </span>
            </div>

            <h4 className="text-sm font-bold text-slate-100">
              Exam Service DB Pool Exhaustion
            </h4>
            <p className="text-xs text-slate-400 mt-1">
              High concurrent submission volume leading to database connection pool timeout (&gt;5000ms).
            </p>

            <div className="mt-4 p-3 bg-slate-900/60 rounded-lg border border-slate-700/50 space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Incident Code:</span>
                <span className="font-mono font-bold text-slate-200">INC-2026-0842</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Anomaly Score:</span>
                <span className="font-mono font-bold text-rose-400">0.91 (Isolation Forest)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Matched Runbook:</span>
                <span className="font-semibold text-cyan-300">runbook-001</span>
              </div>
            </div>
          </div>

          <div className="mt-5 space-y-2">
            <button
              onClick={() => onNavigate('remediation')}
              className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs py-2 px-3 rounded-lg shadow-sm transition-all"
            >
              Execute Remediation Action
            </button>
            <button
              onClick={() => onNavigate('ai_diagnosis')}
              className="w-full bg-slate-700/60 hover:bg-slate-700 text-slate-200 font-semibold text-xs py-2 px-3 rounded-lg transition-all border border-slate-600/50"
            >
              View AI Root Cause Analysis
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
