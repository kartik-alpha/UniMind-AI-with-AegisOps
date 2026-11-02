import React, { useState } from 'react';
import { Search } from 'lucide-react';

export default function LogsView({ logs }) {
  const [serviceFilter, setServiceFilter] = useState('All services');
  const [levelFilter, setLevelFilter] = useState('All levels');
  const [searchQuery, setSearchQuery] = useState('');

  const defaultLogs = [
    { timestamp: '12:42:00', service: 'exam-service', level: 'ERROR', message: 'Database connection timeout after 5000ms (pool exhausted)', trace_id: 'a91f3c2e' },
    { timestamp: '12:42:11', service: 'exam-service', level: 'WARN', message: 'Request latency exceeded threshold: 1834ms > 800ms', trace_id: 'a91f3c40' },
    { timestamp: '12:42:15', service: 'exam-service', level: 'ERROR', message: 'Request failed with status 503 GET /api/results', trace_id: 'b20d7714' },
    { timestamp: '12:42:16', service: 'exam-service', level: 'WARN', message: 'CPU throttling detected on pod exam-7d9f-x2k', trace_id: '-' },
    { timestamp: '12:42:19', service: 'lms', level: 'INFO', message: 'GET /courses/CS401 200 130ms', trace_id: 'c80e1s02' },
    { timestamp: '12:42:21', service: 'student-portal', level: 'INFO', message: 'User session refreshed', trace_id: 'd01b4f9a' },
    { timestamp: '12:42:24', service: 'exam-service', level: 'ERROR', message: 'Upstream timeout from results db', trace_id: 'b20d7790' },
    { timestamp: '12:42:27', service: 'library', level: 'INFO', message: 'Catalogue search completed 92ms', trace_id: 'e47c2b11' },
    { timestamp: '12:42:30', service: 'lms', level: 'DEBUG', message: 'Cache hit ratio 0.94', trace_id: '-' },
    { timestamp: '12:42:33', service: 'exam-service', level: 'WARN', message: 'Queue depth 1,240 requests', trace_id: '-' },
  ];

  const logList = logs || defaultLogs;

  const filteredLogs = logList.filter((item) => {
    const matchesService = serviceFilter === 'All services' || item.service.toLowerCase().includes(serviceFilter.toLowerCase());
    const matchesLevel = levelFilter === 'All levels' || item.level.toUpperCase() === levelFilter.toUpperCase();
    const matchesSearch = !searchQuery || item.message.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesService && matchesLevel && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">AEGISOPS</span>
        <h2 className="text-2xl font-bold text-slate-900 mt-0.5">Loki — Centralized Logs</h2>
      </div>

      {/* Filter Bar */}
      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm flex flex-wrap gap-4 items-center">
        <select
          value={serviceFilter}
          onChange={(e) => setServiceFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option>All services</option>
          <option>exam-service</option>
          <option>lms</option>
          <option>student-portal</option>
          <option>library</option>
        </select>

        <select
          value={levelFilter}
          onChange={(e) => setLevelFilter(e.target.value)}
          className="bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option>All levels</option>
          <option>ERROR</option>
          <option>WARN</option>
          <option>INFO</option>
          <option>DEBUG</option>
        </select>

        <select className="bg-slate-50 border border-slate-200 text-slate-700 text-xs font-medium rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500">
          <option>Last 15 min</option>
          <option>Last 1 hour</option>
          <option>Last 24 hours</option>
        </select>

        <div className="relative flex-1 min-w-[200px]">
          <Search className="absolute left-3 top-2.5 h-3.5 w-3.5 text-slate-400" />
          <input
            type="text"
            placeholder="Search messages..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-slate-50 border border-slate-200 text-slate-800 text-xs pl-8 pr-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Dark Theme Loki Log Table (Matching Screenshot 5) */}
      <div className="bg-[#0b132b] rounded-xl overflow-hidden shadow-lg border border-slate-800">
        <table className="w-full text-left font-mono text-xs text-slate-300">
          <thead className="bg-[#080d1e] text-slate-400 font-bold border-b border-slate-800 uppercase tracking-wider">
            <tr>
              <th className="py-3 px-4">Timestamp</th>
              <th className="py-3 px-4">Service</th>
              <th className="py-3 px-4">Level</th>
              <th className="py-3 px-4">Message</th>
              <th className="py-3 px-4">Trace ID</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {filteredLogs.map((log, idx) => {
              const isError = log.level === 'ERROR';
              const isWarn = log.level === 'WARN';
              const isInfo = log.level === 'INFO';
              return (
                <tr
                  key={idx}
                  className={`hover:bg-slate-800/40 transition-colors ${
                    isError ? 'bg-red-950/20' : ''
                  }`}
                >
                  <td className="py-2.5 px-4 text-slate-400 whitespace-nowrap">{log.timestamp}</td>
                  <td className="py-2.5 px-4 text-slate-200 font-semibold">{log.service}</td>
                  <td className="py-2.5 px-4">
                    {isError && <span className="text-red-500 font-extrabold">ERROR</span>}
                    {isWarn && <span className="text-amber-400 font-extrabold">WARN</span>}
                    {isInfo && <span className="text-cyan-400 font-extrabold">INFO</span>}
                    {!isError && !isWarn && !isInfo && <span className="text-slate-400 font-bold">{log.level}</span>}
                  </td>
                  <td className={`py-2.5 px-4 ${isError ? 'text-red-300' : 'text-slate-200'}`}>
                    {log.message}
                  </td>
                  <td className="py-2.5 px-4 text-slate-500 font-mono">{log.trace_id}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
