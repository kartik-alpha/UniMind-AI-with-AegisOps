import React, { useState, useEffect } from 'react';
import { AlertTriangle, ShieldAlert, CheckCircle, ArrowRight, Zap, RefreshCw, Cpu } from 'lucide-react';

export default function IncidentsView({ onNavigate }) {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(false);

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/incidents');
      if (res.ok) {
        setIncidents(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-900 mt-0.5">IT Infrastructure Incidents</h2>
          <p className="text-xs text-slate-500 mt-1">
            Predictive anomaly alerts, multi-variate telemetry correlation, and incident triage logs.
          </p>
        </div>

        <button
          onClick={fetchIncidents}
          className="px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-all"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Incident Cards */}
      <div className="space-y-4">
        {incidents.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-400">
            No incidents found. All services are healthy.
          </div>
        ) : (
          incidents.map((inc) => {
            const isResolved = inc.status === 'RESOLVED';
            return (
              <div
                key={inc.id}
                className={`bg-white border rounded-xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col md:flex-row justify-between gap-6 ${
                  isResolved ? 'border-slate-200' : 'border-rose-300 bg-rose-50/10'
                }`}
              >
                <div className="space-y-3 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
                      {inc.incident_code}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        inc.severity === 'CRITICAL'
                          ? 'bg-rose-100 text-rose-700'
                          : inc.severity === 'HIGH'
                          ? 'bg-amber-100 text-amber-700'
                          : 'bg-slate-100 text-slate-700'
                      }`}
                    >
                      {inc.severity}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        isResolved
                          ? 'bg-emerald-100 text-emerald-700'
                          : 'bg-rose-100 text-rose-700 animate-pulse'
                      }`}
                    >
                      {inc.status}
                    </span>
                    <span className="text-xs font-semibold text-slate-600">
                      Service: <span className="text-blue-600 font-bold">{inc.service_name}</span>
                    </span>
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-slate-900">{inc.title}</h3>
                    {inc.root_cause && (
                      <p className="text-xs text-slate-600 mt-1 leading-relaxed">
                        <span className="font-semibold text-slate-700">Root Cause:</span> {inc.root_cause}
                      </p>
                    )}
                  </div>

                  {inc.recommendation && (
                    <div className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1">
                      <span className="font-bold text-slate-700 flex items-center gap-1.5">
                        <Zap className="h-3.5 w-3.5 text-amber-600" /> Recommended Action:
                      </span>
                      <p className="text-slate-600 font-mono">{inc.recommendation}</p>
                    </div>
                  )}
                </div>

                {/* Right Action Buttons */}
                <div className="flex md:flex-col justify-end gap-2 shrink-0 md:w-48">
                  {!isResolved ? (
                    <>
                      <button
                        onClick={() => onNavigate('remediation')}
                        className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-2 px-3 rounded-lg shadow-sm transition-all flex items-center justify-center gap-1.5"
                      >
                        <Zap className="h-3.5 w-3.5" />
                        <span>Remediate</span>
                      </button>
                      <button
                        onClick={() => onNavigate('ai_diagnosis')}
                        className="w-full bg-slate-100 hover:bg-slate-200 text-slate-800 font-bold text-xs py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-1.5"
                      >
                        <Cpu className="h-3.5 w-3.5" />
                        <span>AI Diagnosis</span>
                      </button>
                    </>
                  ) : (
                    <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-bold justify-end md:justify-center">
                      <CheckCircle className="h-4 w-4" />
                      <span>Incident Resolved</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
