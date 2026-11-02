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
      color: 'bg-blue-600 hover:bg-blue-700 text-white',
    },
    {
      label: 'Inspect ML Anomaly Scan',
      desc: 'View Isolation Forest multi-variate score',
      tab: 'ml_anomaly',
      icon: Cpu,
      color: 'bg-purple-600 hover:bg-purple-700 text-white',
    },
    {
      label: 'AI Root Cause Diagnosis',
      desc: 'Correlate telemetry against SRE runbooks',
      tab: 'ai_diagnosis',
      icon: Zap,
      color: 'bg-amber-600 hover:bg-amber-700 text-white',
    },
    {
      label: 'Trigger Self-Healing',
      desc: 'Automated pod restart & replica scale-out',
      tab: 'remediation',
      icon: Activity,
      color: 'bg-emerald-600 hover:bg-emerald-700 text-white',
    },
  ];

  return (
    <div className="space-y-8 animate-fadeIn">
      {/* Top Banner */}
      <div className="bg-gradient-to-r from-[#0b132b] via-[#1c2541] to-[#3a506b] rounded-2xl p-6 text-white shadow-md flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border border-slate-700">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/20 text-blue-300 text-xs font-semibold mb-2 border border-blue-400/30">
            <span className="h-2 w-2 rounded-full bg-blue-400 animate-pulse"></span>
            Operational Dashboard • University Enterprise
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">
            UniMind AI & AegisOps Platform
          </h1>
          <p className="text-xs text-slate-300 mt-1 max-w-xl">
            Unified student support AI with automated predictive observability, intelligent RAG document retrieval, and autonomous self-healing microservices.
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => onNavigate('remediation')}
            className="px-4 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white text-xs font-bold flex items-center gap-2 shadow-lg transition-all"
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
              className="bg-white rounded-xl border border-slate-200 p-5 shadow-sm hover:shadow-md transition-shadow relative overflow-hidden"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  {s.title}
                </span>
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                    s.status === 'critical'
                      ? 'bg-rose-100 text-rose-700'
                      : s.status === 'warning'
                      ? 'bg-amber-100 text-amber-700'
                      : 'bg-emerald-100 text-emerald-700'
                  }`}
                >
                  {s.badge}
                </span>
              </div>
              <div className="mt-3 flex items-baseline gap-2">
                <span className="text-xl font-bold text-slate-900">{s.value}</span>
              </div>
              <p className="text-xs text-slate-500 mt-1">{s.subtitle}</p>
              <div className="mt-4 pt-3 border-t border-slate-100 flex items-center text-xs text-blue-600 font-semibold cursor-pointer">
                <span>View Details</span>
                <ArrowRight className="h-3 w-3 ml-1" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Action Cards */}
      <div>
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-3">
          Quick Workflows
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickActions.map((qa, idx) => {
            const Icon = qa.icon;
            return (
              <button
                key={idx}
                onClick={() => onNavigate(qa.tab)}
                className="bg-white border border-slate-200 rounded-xl p-4 text-left shadow-sm hover:border-blue-400 hover:shadow-md transition-all group flex flex-col justify-between"
              >
                <div>
                  <div className="h-9 w-9 rounded-lg bg-blue-50 text-blue-600 flex items-center justify-center mb-3 group-hover:bg-blue-600 group-hover:text-white transition-colors">
                    <Icon className="h-5 w-5" />
                  </div>
                  <h4 className="text-sm font-bold text-slate-800 group-hover:text-blue-600 transition-colors">
                    {qa.label}
                  </h4>
                  <p className="text-xs text-slate-500 mt-1">{qa.desc}</p>
                </div>
                <span className="mt-4 text-xs font-semibold text-blue-600 flex items-center gap-1 group-hover:translate-x-1 transition-transform">
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
        <div className="lg:col-span-2 bg-white rounded-xl border border-slate-200 p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-base font-bold text-slate-900">Campus Microservices Fleet</h3>
              <p className="text-xs text-slate-500">Live operational telemetry & health</p>
            </div>
            <button
              onClick={() => onNavigate('services')}
              className="text-xs font-bold text-blue-600 hover:text-blue-700 flex items-center gap-1"
            >
              All Services <ArrowRight className="h-3 w-3" />
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-y border-slate-200">
                <tr>
                  <th className="py-2.5 px-3">Service</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">CPU</th>
                  <th className="py-2.5 px-3">Latency</th>
                  <th className="py-2.5 px-3">Replicas</th>
                  <th className="py-2.5 px-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                <tr className="hover:bg-slate-50/50">
                  <td className="py-3 px-3 font-semibold text-slate-900">Exam Service</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-amber-100 text-amber-800">
                      <span className="h-1.5 w-1.5 rounded-full bg-amber-500 animate-pulse"></span>
                      Degraded
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono text-rose-600 font-bold">92%</td>
                  <td className="py-3 px-3 font-mono text-rose-600 font-bold">1,800 ms</td>
                  <td className="py-3 px-3 font-mono">2 / 2</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onNavigate('ai_diagnosis')}
                      className="px-2.5 py-1 bg-blue-50 text-blue-600 hover:bg-blue-600 hover:text-white rounded text-[11px] font-bold transition-all"
                    >
                      Diagnose
                    </button>
                  </td>
                </tr>

                <tr className="hover:bg-slate-50/50">
                  <td className="py-3 px-3 font-semibold text-slate-900">LMS Service</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                      Healthy
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono">24%</td>
                  <td className="py-3 px-3 font-mono">110 ms</td>
                  <td className="py-3 px-3 font-mono">3 / 3</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onNavigate('monitoring')}
                      className="px-2.5 py-1 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded text-[11px] font-bold transition-all"
                    >
                      Monitor
                    </button>
                  </td>
                </tr>

                <tr className="hover:bg-slate-50/50">
                  <td className="py-3 px-3 font-semibold text-slate-900">Student Portal</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                      Healthy
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono">18%</td>
                  <td className="py-3 px-3 font-mono">85 ms</td>
                  <td className="py-3 px-3 font-mono">2 / 2</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onNavigate('monitoring')}
                      className="px-2.5 py-1 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded text-[11px] font-bold transition-all"
                    >
                      Monitor
                    </button>
                  </td>
                </tr>

                <tr className="hover:bg-slate-50/50">
                  <td className="py-3 px-3 font-semibold text-slate-900">Library Service</td>
                  <td className="py-3 px-3">
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold bg-emerald-100 text-emerald-800">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                      Healthy
                    </span>
                  </td>
                  <td className="py-3 px-3 font-mono">12%</td>
                  <td className="py-3 px-3 font-mono">45 ms</td>
                  <td className="py-3 px-3 font-mono">1 / 1</td>
                  <td className="py-3 px-3 text-right">
                    <button
                      onClick={() => onNavigate('monitoring')}
                      className="px-2.5 py-1 bg-slate-100 text-slate-600 hover:bg-slate-200 rounded text-[11px] font-bold transition-all"
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
        <div className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-bold text-rose-600 uppercase tracking-wider flex items-center gap-1">
                <AlertCircle className="h-3.5 w-3.5" /> Active SRE Alert
              </span>
              <span className="text-[10px] font-mono bg-rose-50 text-rose-700 px-2 py-0.5 rounded font-bold border border-rose-200">
                CRITICAL
              </span>
            </div>

            <h4 className="text-sm font-bold text-slate-900">
              Exam Service DB Pool Exhaustion
            </h4>
            <p className="text-xs text-slate-500 mt-1">
              High concurrent submission volume leading to database connection pool timeout (&gt;5000ms).
            </p>

            <div className="mt-4 p-3 bg-slate-50 rounded-lg border border-slate-200 space-y-1.5 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Incident Code:</span>
                <span className="font-mono font-bold text-slate-800">INC-2026-0842</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Anomaly Score:</span>
                <span className="font-mono font-bold text-rose-600">0.91 (Isolation Forest)</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Matched Runbook:</span>
                <span className="font-semibold text-slate-800">runbook-001</span>
              </div>
            </div>
          </div>

          <div className="mt-5 space-y-2">
            <button
              onClick={() => onNavigate('remediation')}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2 px-3 rounded-lg shadow-sm transition-all"
            >
              Execute Remediation Action
            </button>
            <button
              onClick={() => onNavigate('ai_diagnosis')}
              className="w-full bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-xs py-2 px-3 rounded-lg transition-all"
            >
              View AI Root Cause Analysis
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
