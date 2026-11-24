import React from 'react';
import {
  GraduationCap,
  LayoutDashboard,
  MessageSquare,
  BookOpen,
  FileText,
  Database,
  Ticket,
  Activity,
  Server,
  TrendingUp,
  BarChart3,
  FileCode,
  Cpu,
  AlertTriangle,
  Sparkles,
  Wrench,
  Layers,
  Play,
  Flame,
  Building2,
  ShieldCheck,
} from 'lucide-react';

export default function Sidebar({ activeTab, setActiveTab, onRunDemo }) {
  const unimindNav = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'assistant', label: 'Student Assistant', icon: MessageSquare },
    { id: 'knowledge', label: 'Knowledge Base', icon: BookOpen },
    { id: 'documents', label: 'Documents', icon: FileText },
    { id: 'rag', label: 'RAG Management', icon: Database },
    { id: 'tickets', label: 'Tickets & Incidents', icon: Ticket },
  ];

  const aegisNav = [
    { id: 'aegis_overview', label: 'AegisOps Overview', icon: Activity },
    { id: 'digital_twin', label: 'Digital Twin Campus', icon: TrendingUp },
    { id: 'chaos', label: 'Chaos Simulator', icon: Flame },
    { id: 'services', label: 'Services', icon: Server },
    { id: 'monitoring', label: 'Monitoring', icon: TrendingUp },
    { id: 'metrics', label: 'Metrics', icon: BarChart3 },
    { id: 'logs', label: 'Logs', icon: FileCode },
    { id: 'ml_anomaly', label: 'ML Anomaly Detection', icon: Cpu },
    { id: 'incidents', label: 'Incidents', icon: AlertTriangle },
    { id: 'ai_diagnosis', label: 'AI Diagnosis', icon: Sparkles },
    { id: 'remediation', label: 'Remediation', icon: Wrench },
    { id: 'kubernetes', label: 'Kubernetes', icon: Layers },
  ];

  const governanceNav = [
    { id: 'governance', label: 'Tenant Governance', icon: ShieldCheck },
    { id: 'observability', label: 'Observability & Metrics', icon: Activity },
  ];

  return (
    <aside className="w-64 bg-[#0b132b] text-slate-300 flex flex-col justify-between shrink-0 min-h-screen border-r border-slate-800 select-none">
      <div>
        {/* Top Brand Logo */}
        <div className="h-16 px-5 flex items-center gap-3 border-b border-slate-800">
          <div className="h-9 w-9 rounded-lg bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-white shadow-md">
            <GraduationCap className="h-5 w-5" />
          </div>
          <div>
            <h1 className="font-bold text-white text-base leading-tight tracking-wide">UniMind AI</h1>
            <span className="text-[10px] font-bold text-slate-400 tracking-wider uppercase block">
              WITH AEGISOPS
            </span>
          </div>
        </div>

        {/* Active Tenant / Organization Context Pill */}
        <div className="mx-3 mt-3 px-3 py-2 bg-slate-800/60 rounded-lg border border-slate-700/60 flex items-center justify-between">
          <div className="flex items-center gap-2.5 min-w-0">
            <Building2 className="h-4 w-4 text-cyan-400 shrink-0" />
            <div className="truncate">
              <div className="text-xs font-semibold text-slate-200 truncate">UniMind University</div>
              <div className="text-[10px] text-slate-400 flex items-center gap-1">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400"></span>
                <span>Education Enterprise</span>
              </div>
            </div>
          </div>
          <span className="text-[9px] bg-cyan-900/40 text-cyan-300 font-mono px-1.5 py-0.5 rounded border border-cyan-700/50">T1</span>
        </div>

        {/* Navigation Sections */}
        <div className="p-3 space-y-6 overflow-y-auto max-h-[calc(100vh-140px)]">
          {/* Section: UNIMIND AI */}
          <div>
            <span className="px-3 text-[10px] font-extrabold text-slate-500 uppercase tracking-wider block mb-2">
              UNIMIND AI
            </span>
            <nav className="space-y-0.5">
              {unimindNav.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-all ${
                      isActive
                        ? 'bg-cyan-500/10 text-cyan-300 border-l-2 border-cyan-400 font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/30'
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Section: AEGISOPS */}
          <div>
            <span className="px-3 text-[10px] font-extrabold text-slate-500 uppercase tracking-wider block mb-2">
              AEGISOPS
            </span>
            <nav className="space-y-0.5">
              {aegisNav.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-all ${
                      isActive
                        ? 'bg-cyan-500/10 text-cyan-300 border-l-2 border-cyan-400 font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/30'
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Section: ENTERPRISE GOVERNANCE */}
          <div>
            <span className="px-3 text-[10px] font-extrabold text-slate-500 uppercase tracking-wider block mb-2">
              GOVERNANCE & OPS
            </span>
            <nav className="space-y-0.5">
              {governanceNav.map((item) => {
                const Icon = item.icon;
                const isActive = activeTab === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setActiveTab(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2 text-sm font-medium rounded-md transition-all ${
                      isActive
                        ? 'bg-cyan-500/10 text-cyan-300 border-l-2 border-cyan-400 font-semibold'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/30'
                    }`}
                  >
                    <Icon className={`h-4 w-4 ${isActive ? 'text-cyan-400' : 'text-slate-400'}`} />
                    <span>{item.label}</span>
                  </button>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* Bottom Action Button: Run AegisOps Demo */}
      <div className="p-3 border-t border-slate-800 bg-[#080d1e]">
        <button
          onClick={onRunDemo}
          className="w-full bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-semibold text-sm py-2.5 px-4 rounded-lg flex items-center justify-center gap-2 shadow-lg transition-all active:scale-[0.98]"
        >
          <Play className="h-4 w-4 fill-current" />
          <span>Run AegisOps Demo</span>
        </button>
      </div>
    </aside>
  );
}
