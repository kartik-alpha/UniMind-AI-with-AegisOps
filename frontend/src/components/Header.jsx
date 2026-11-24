import React, { useState, useEffect } from 'react';
import { Search, Bell, GraduationCap, Building2, ChevronDown } from 'lucide-react';
import { getTenantId, setTenantId } from '../apiClient';

const TENANTS = [
  { id: '1', name: 'UniMind University', type: 'EDU', role: 'Primary Campus' },
  { id: '2', name: 'Apex Institute of Tech', type: 'POLYTECH', role: 'Affiliate Tenant' },
  { id: '3', name: 'St. Jude Health Sciences', type: 'HEALTH', role: 'Medical System' },
];

export default function Header({ activeTab, activeIncidentCount = 1 }) {
  const [currentTenantId, setCurrentTenantId] = useState(getTenantId());
  const [tenantDropdownOpen, setTenantDropdownOpen] = useState(false);

  useEffect(() => {
    const handleTenantChange = (e) => {
      setCurrentTenantId(e.detail?.tenantId || getTenantId());
    };
    window.addEventListener('unimind:tenant_change', handleTenantChange);
    return () => window.removeEventListener('unimind:tenant_change', handleTenantChange);
  }, []);

  const handleSelectTenant = (tid) => {
    setTenantId(tid);
    setCurrentTenantId(tid);
    setTenantDropdownOpen(false);
  };

  const activeTenant = TENANTS.find((t) => t.id === currentTenantId) || TENANTS[0];

  return (
    <header className="h-16 bg-[#111827]/80 backdrop-blur-xl border-b border-slate-700/50 px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Left Search Bar */}
      <div className="flex items-center gap-3 w-96">
        <div className="relative w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search documents, services, incidents..."
            className="w-full bg-slate-800 hover:bg-slate-700/70 focus:bg-slate-800 text-sm text-slate-200 pl-9 pr-4 py-2 rounded-lg border border-slate-700 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Right User & System Status */}
      <div className="flex items-center gap-4">
        {/* Active Tenant / Organization Dropdown Switcher */}
        <div className="relative">
          <div
            onClick={() => setTenantDropdownOpen(!tenantDropdownOpen)}
            className="flex items-center gap-2 bg-slate-800 hover:bg-slate-700/80 transition-colors border border-slate-700 rounded-lg px-3 py-1.5 cursor-pointer shadow-sm"
          >
            <Building2 className="h-4 w-4 text-cyan-400" />
            <div className="flex flex-col text-left">
              <div className="flex items-center gap-1.5">
                <span className="text-xs font-bold text-slate-200">{activeTenant.name}</span>
                <span className="text-[10px] bg-cyan-500/10 text-cyan-400 font-bold px-1.5 py-0.2 rounded uppercase tracking-wider border border-cyan-500/20">
                  {activeTenant.type}
                </span>
              </div>
              <span className="text-[10px] text-slate-400 font-medium">Tenant #{activeTenant.id} • Active</span>
            </div>
            <ChevronDown className="h-3.5 w-3.5 text-slate-400 ml-1" />
          </div>

          {tenantDropdownOpen && (
            <div className="absolute right-0 mt-2 w-64 bg-slate-900 border border-slate-700 rounded-xl shadow-xl py-2 z-50 animate-fadeIn">
              <div className="px-3 py-1.5 text-[10px] font-bold uppercase tracking-wider text-slate-400 border-b border-slate-800">
                Switch Multi-Tenant Context
              </div>
              {TENANTS.map((t) => (
                <button
                  key={t.id}
                  onClick={() => handleSelectTenant(t.id)}
                  className={`w-full text-left px-3 py-2 text-xs hover:bg-slate-800 flex items-center justify-between transition-colors ${t.id === currentTenantId ? 'bg-cyan-500/10 text-cyan-300 font-bold' : 'text-slate-300'
                    }`}
                >
                  <div>
                    <div className="font-semibold">{t.name}</div>
                    <div className="text-[10px] text-slate-500">Tenant #{t.id} • {t.role}</div>
                  </div>
                  {t.id === currentTenantId && (
                    <span className="h-2 w-2 rounded-full bg-cyan-400" />
                  )}
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Degraded Incident Badge */}
        <div className="flex items-center gap-2 bg-rose-500/10 text-rose-400 text-xs font-semibold px-3 py-1.5 rounded-full border border-rose-500/20">
          <span className="h-2 w-2 rounded-full bg-rose-500 animate-pulse"></span>
          <span>Degraded • {activeIncidentCount} incident</span>
        </div>

        {/* Bell Notification Icon */}
        <div className="relative p-2 text-slate-400 hover:text-slate-200 cursor-pointer transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 h-4 w-4 bg-rose-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            1
          </span>
        </div>

        {/* User Profile Capsule */}
        <div className="flex items-center gap-3 pl-3 border-l border-slate-700">
          <div className="h-9 w-9 rounded-full bg-slate-700 text-white font-semibold flex items-center justify-center text-sm shadow-sm">
            KL
          </div>
          <div className="flex flex-col text-left">
            <span className="text-sm font-semibold text-slate-200 leading-tight">Kartik Lakhera</span>
            <span className="text-xs text-cyan-400 font-medium">Lab Manager</span>
          </div>
        </div>
      </div>
    </header>
  );
}
