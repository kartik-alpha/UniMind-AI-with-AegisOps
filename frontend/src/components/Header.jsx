import React from 'react';
import { Search, Bell, GraduationCap } from 'lucide-react';

export default function Header({ activeTab, activeIncidentCount = 1 }) {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-6 flex items-center justify-between sticky top-0 z-20">
      {/* Left Search Bar */}
      <div className="flex items-center gap-3 w-96">
        <div className="relative w-full">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-400" />
          <input
            type="text"
            placeholder="Search documents, services, incidents..."
            className="w-full bg-slate-100 hover:bg-slate-200/70 focus:bg-white text-sm text-slate-800 pl-9 pr-4 py-2 rounded-lg border border-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
          />
        </div>
      </div>

      {/* Right User & System Status */}
      <div className="flex items-center gap-4">
        {/* Degraded Incident Badge */}
        <div className="flex items-center gap-2 bg-amber-50 text-amber-700 text-xs font-semibold px-3 py-1.5 rounded-full border border-amber-200">
          <span className="h-2 w-2 rounded-full bg-amber-500 animate-pulse"></span>
          <span>Degraded • {activeIncidentCount} incident</span>
        </div>

        {/* Bell Notification Icon */}
        <div className="relative p-2 text-slate-500 hover:text-slate-700 cursor-pointer">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 h-4 w-4 bg-red-500 text-white text-[10px] font-bold rounded-full flex items-center justify-center">
            1
          </span>
        </div>

        {/* User Profile Capsule */}
        <div className="flex items-center gap-3 pl-3 border-l border-slate-200">
          <div className="h-9 w-9 rounded-full bg-slate-900 text-white font-semibold flex items-center justify-center text-sm shadow-sm">
            KL
          </div>
          <div className="flex flex-col text-left">
            <span className="text-sm font-semibold text-slate-800 leading-tight">Kartik Lakhera</span>
            <span className="text-xs text-blue-600 font-medium">Lab Manager</span>
          </div>
        </div>
      </div>
    </header>
  );
}
