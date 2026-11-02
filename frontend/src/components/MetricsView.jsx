import React from 'react';

export default function MetricsView({ metrics }) {
  const defaultMetrics = [
    { service: 'LMS', cpu: '34%', memory: '48%', requests: '412/s', latency: '142 ms', errors: '0.2%', replicas: 3 },
    { service: 'Student Portal', cpu: '27%', memory: '41%', requests: '288/s', latency: '118 ms', errors: '0.1%', replicas: 2 },
    { service: 'Exam Service', cpu: '92%', memory: '81%', requests: '964/s', latency: '1800 ms', errors: '14%', replicas: 2, is_alert: true },
    { service: 'Library Service', cpu: '21%', memory: '38%', requests: '96/s', latency: '105 ms', errors: '0%', replicas: 2 },
  ];

  const rows = metrics || defaultMetrics;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">PROMETHEUS</span>
        <h2 className="text-2xl font-bold text-slate-900 mt-0.5">Metrics</h2>
        <p className="text-xs text-slate-500 mt-1">Five features per service feed the anomaly model.</p>
      </div>

      {/* Metrics Table Card */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-50 border-b border-slate-200 text-slate-500 font-extrabold uppercase tracking-wider">
            <tr>
              <th className="py-3.5 px-6">SERVICE</th>
              <th className="py-3.5 px-6">CPU</th>
              <th className="py-3.5 px-6">MEMORY</th>
              <th className="py-3.5 px-6">REQUESTS</th>
              <th className="py-3.5 px-6">LATENCY</th>
              <th className="py-3.5 px-6">ERRORS</th>
              <th className="py-3.5 px-6">REPLICAS</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 font-medium text-slate-700">
            {rows.map((row) => (
              <tr key={row.service} className="hover:bg-slate-50/80 transition-colors">
                <td className="py-4 px-6 font-bold text-slate-900">{row.service}</td>
                <td className={`py-4 px-6 ${row.is_alert ? 'text-red-600 font-bold' : ''}`}>{row.cpu}</td>
                <td className="py-4 px-6">{row.memory}</td>
                <td className="py-4 px-6">{row.requests}</td>
                <td className={`py-4 px-6 ${row.is_alert ? 'text-red-600 font-bold' : ''}`}>{row.latency}</td>
                <td className={`py-4 px-6 ${row.is_alert ? 'text-red-600 font-bold' : ''}`}>{row.errors}</td>
                <td className="py-4 px-6">{row.replicas}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
