import React, { useState } from 'react';

export default function MonitoringView() {
  const [timeRange, setTimeRange] = useState('Last 1 hour');

  const timeOptions = ['Last 15 min', 'Last 1 hour', 'Last 6 hours', 'Last 24 hours'];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header + Subtitle */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Monitoring</h2>
          <p className="text-xs text-slate-400 mt-1">Red markers show points flagged by the anomaly model.</p>
        </div>

        {/* Time Filters */}
        <div className="flex bg-slate-800/80 border border-slate-700/60 rounded-lg p-1 shadow-sm text-xs font-medium">
          {timeOptions.map((option) => (
            <button
              key={option}
              onClick={() => setTimeRange(option)}
              className={`px-3 py-1.5 rounded-md transition-all ${
                timeRange === option
                  ? 'bg-cyan-600 text-white font-semibold shadow-sm'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-700/50'
              }`}
            >
              {option}
            </button>
          ))}
        </div>
      </div>

      {/* 5 Charts Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* 1. CPU Usage */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-200 text-sm">CPU Usage</h3>
            <span className="font-bold text-slate-100 text-sm font-mono">93%</span>
          </div>
          <div className="relative h-40 w-full pt-4">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 300 100">
              <path
                d="M 0,60 L 40,55 L 80,62 L 120,58 L 160,65 L 200,60 L 240,30 L 280,15 L 300,5"
                fill="none"
                stroke="#06b6d4"
                strokeWidth="2.5"
              />
              {/* Anomaly markers */}
              <circle cx="240" cy="30" r="4" fill="#f43f5e" />
              <circle cx="260" cy="22" r="4" fill="#f43f5e" />
              <circle cx="280" cy="15" r="4" fill="#f43f5e" />
              <circle cx="300" cy="5" r="5" fill="#f43f5e" />
            </svg>
            <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono">
              <span>12:12</span>
              <span>12:19</span>
              <span>12:26</span>
              <span>12:33</span>
              <span>12:40</span>
            </div>
          </div>
        </div>

        {/* 2. Memory Usage */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-200 text-sm">Memory Usage</h3>
            <span className="font-bold text-slate-100 text-sm font-mono">82.3%</span>
          </div>
          <div className="relative h-40 w-full pt-4">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 300 100">
              <path
                d="M 0,55 L 40,50 L 80,52 L 120,58 L 160,50 L 200,48 L 240,32 L 280,25 L 300,18"
                fill="none"
                stroke="#a855f7"
                strokeWidth="2.5"
              />
              <circle cx="240" cy="32" r="4" fill="#f43f5e" />
              <circle cx="260" cy="28" r="4" fill="#f43f5e" />
              <circle cx="280" cy="25" r="4" fill="#f43f5e" />
              <circle cx="300" cy="18" r="5" fill="#f43f5e" />
            </svg>
            <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono">
              <span>12:12</span>
              <span>12:19</span>
              <span>12:26</span>
              <span>12:33</span>
              <span>12:40</span>
            </div>
          </div>
        </div>

        {/* 3. Request Rate */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-200 text-sm">Request Rate</h3>
            <span className="font-bold text-slate-100 text-sm font-mono">2945.1/s</span>
          </div>
          <div className="relative h-40 w-full pt-4">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 300 100">
              <path
                d="M 0,70 L 40,68 L 80,72 L 120,65 L 160,70 L 200,66 L 240,40 L 280,20 L 300,5"
                fill="none"
                stroke="#10b981"
                strokeWidth="2.5"
              />
              <circle cx="240" cy="40" r="4" fill="#f43f5e" />
              <circle cx="260" cy="30" r="4" fill="#f43f5e" />
              <circle cx="280" cy="20" r="4" fill="#f43f5e" />
              <circle cx="300" cy="5" r="5" fill="#f43f5e" />
            </svg>
            <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono">
              <span>12:12</span>
              <span>12:19</span>
              <span>12:26</span>
              <span>12:33</span>
              <span>12:40</span>
            </div>
          </div>
        </div>

        {/* 4. Latency */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-200 text-sm">Latency</h3>
            <span className="font-bold text-slate-100 text-sm font-mono">1695 ms</span>
          </div>
          <div className="relative h-40 w-full pt-4">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 300 100">
              <path
                d="M 0,90 L 40,88 L 80,90 L 120,89 L 160,88 L 200,85 L 240,50 L 280,25 L 300,10"
                fill="none"
                stroke="#f59e0b"
                strokeWidth="2.5"
              />
              <circle cx="240" cy="50" r="4" fill="#f43f5e" />
              <circle cx="260" cy="35" r="4" fill="#f43f5e" />
              <circle cx="280" cy="25" r="4" fill="#f43f5e" />
              <circle cx="300" cy="10" r="5" fill="#f43f5e" />
            </svg>
            <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono">
              <span>12:12</span>
              <span>12:19</span>
              <span>12:26</span>
              <span>12:33</span>
              <span>12:40</span>
            </div>
          </div>
        </div>

        {/* 5. Error Rate */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="font-bold text-slate-200 text-sm">Error Rate</h3>
            <span className="font-bold text-rose-400 text-sm font-mono">13.8%</span>
          </div>
          <div className="relative h-40 w-full pt-4">
            <svg className="w-full h-full overflow-visible" viewBox="0 0 300 100">
              <path
                d="M 0,98 L 40,97 L 80,98 L 120,96 L 160,98 L 200,95 L 240,60 L 280,30 L 300,15"
                fill="none"
                stroke="#f43f5e"
                strokeWidth="2.5"
              />
              <circle cx="240" cy="60" r="4" fill="#f43f5e" />
              <circle cx="260" cy="45" r="4" fill="#f43f5e" />
              <circle cx="280" cy="30" r="4" fill="#f43f5e" />
              <circle cx="300" cy="15" r="5" fill="#f43f5e" />
            </svg>
            <div className="flex justify-between text-[10px] text-slate-500 mt-2 font-mono">
              <span>12:12</span>
              <span>12:19</span>
              <span>12:26</span>
              <span>12:33</span>
              <span>12:40</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
