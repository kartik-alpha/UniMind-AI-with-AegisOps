import React, { useState, useEffect } from 'react';
import {
  AlertTriangle,
  ShieldAlert,
  CheckCircle,
  ArrowRight,
  Zap,
  RefreshCw,
  Cpu,
  Filter,
  CheckCircle2,
  Clock,
  Search,
} from 'lucide-react';
import { apiFetch, getTenantId, parseApiError } from '../apiClient';

export default function IncidentsView({ onNavigate }) {
  const [incidents, setIncidents] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusFilter, setStatusFilter] = useState('ALL');
  const [severityFilter, setSeverityFilter] = useState('ALL');
  const [actionInProgress, setActionInProgress] = useState(null);
  const [notification, setNotification] = useState(null);

  const fetchIncidents = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/incidents');
      if (res.ok) {
        setIncidents(await res.json());
      } else {
        const prob = await parseApiError(res);
        setNotification({ type: 'error', text: prob.detail });
      }
    } catch (e) {
      setNotification({ type: 'error', text: `Failed to connect to incidents API: ${e.message}` });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchIncidents();
    const handleTenantChange = () => fetchIncidents();
    window.addEventListener('unimind:tenant_change', handleTenantChange);
    return () => window.removeEventListener('unimind:tenant_change', handleTenantChange);
  }, []);

  const handleTransition = async (incidentId, targetStatus) => {
    setActionInProgress(incidentId);
    setNotification(null);
    try {
      const res = await apiFetch(`/api/v1/aegisops/incidents/${incidentId}/transition`, {
        method: 'POST',
        body: JSON.stringify({
          status: targetStatus,
          notes: `Operator transitioned incident to ${targetStatus} from AegisOps Console.`,
        }),
      });

      if (res.ok) {
        setNotification({
          type: 'success',
          text: `Incident successfully transitioned to ${targetStatus}.`,
        });
        await fetchIncidents();
      } else {
        const prob = await parseApiError(res);
        setNotification({ type: 'error', text: `Transition failed: ${prob.detail}` });
      }
    } catch (err) {
      setNotification({ type: 'error', text: `Network error: ${err.message}` });
    } finally {
      setActionInProgress(null);
    }
  };

  const filteredIncidents = incidents.filter((inc) => {
    if (statusFilter === 'ACTIVE' && inc.status === 'RESOLVED') return false;
    if (statusFilter === 'RESOLVED' && inc.status !== 'RESOLVED') return false;
    if (statusFilter === 'PENDING' && inc.status !== 'PENDING_APPROVAL') return false;
    if (severityFilter !== 'ALL' && inc.severity !== severityFilter) return false;
    return true;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">IT Infrastructure Incidents</h2>
          <p className="text-xs text-slate-400 mt-1">
            Predictive anomaly alerts, multi-variate telemetry correlation, and incident triage logs.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={fetchIncidents}
            disabled={loading}
            className="px-3 py-2 bg-slate-800 border border-slate-700 hover:bg-slate-700/80 text-slate-300 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>
      </div>

      {/* Notifications */}
      {notification && (
        <div
          className={`p-3.5 rounded-xl border text-xs flex items-center justify-between ${
            notification.type === 'success'
              ? 'bg-emerald-950/30 text-emerald-300 border-emerald-500/30'
              : 'bg-rose-950/30 text-rose-300 border-rose-500/30'
          }`}
        >
          <span>{notification.text}</span>
          <button onClick={() => setNotification(null)} className="text-slate-400 hover:text-white font-bold ml-2">
            ✕
          </button>
        </div>
      )}

      {/* Filter Tabs */}
      <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-3 rounded-xl border border-slate-800">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-400 flex items-center gap-1 mr-1">
            <Filter className="h-3.5 w-3.5" /> Status:
          </span>
          {['ALL', 'ACTIVE', 'PENDING', 'RESOLVED'].map((st) => (
            <button
              key={st}
              onClick={() => setStatusFilter(st)}
              className={`px-2.5 py-1 text-xs rounded-md font-bold transition-all ${
                statusFilter === st
                  ? 'bg-cyan-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700/60'
              }`}
            >
              {st}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-400 mr-1">Severity:</span>
          {['ALL', 'CRITICAL', 'HIGH', 'MEDIUM'].map((sev) => (
            <button
              key={sev}
              onClick={() => setSeverityFilter(sev)}
              className={`px-2.5 py-1 text-xs rounded-md font-bold transition-all ${
                severityFilter === sev
                  ? 'bg-purple-600 text-white shadow-sm'
                  : 'bg-slate-800 text-slate-400 hover:text-slate-200 border border-slate-700/60'
              }`}
            >
              {sev}
            </button>
          ))}
        </div>
      </div>

      {/* Incident Cards */}
      <div className="space-y-4">
        {loading && incidents.length === 0 ? (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center text-xs text-slate-400 flex flex-col items-center gap-3">
            <RefreshCw className="h-6 w-6 text-cyan-400 animate-spin" />
            <span>Loading telemetry incidents from fleet cluster...</span>
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center text-xs text-slate-400">
            <CheckCircle2 className="h-8 w-8 text-emerald-400 mx-auto mb-2" />
            <span className="font-bold text-slate-200 text-sm block">Zero Incidents Match Filters</span>
            <span>All monitored cluster services are operating within nominal baseline bounds.</span>
          </div>
        ) : (
          filteredIncidents.map((inc) => {
            const isResolved = inc.status === 'RESOLVED';
            const isPending = inc.status === 'PENDING_APPROVAL';
            const isBusy = actionInProgress === inc.id;

            return (
              <div
                key={inc.id}
                className={`border rounded-xl p-6 shadow-sm hover:shadow-md transition-all flex flex-col lg:flex-row justify-between gap-6 ${
                  isResolved
                    ? 'bg-slate-800/40 border-slate-700/50'
                    : inc.severity === 'CRITICAL'
                    ? 'border-rose-500/40 bg-rose-950/15'
                    : 'border-amber-500/40 bg-amber-950/15'
                }`}
              >
                <div className="space-y-3 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-xs font-bold text-slate-200 bg-slate-900 px-2 py-0.5 rounded border border-slate-700/60">
                      {inc.incident_code}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        inc.severity === 'CRITICAL'
                          ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                          : inc.severity === 'HIGH'
                          ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                          : 'bg-slate-800 text-slate-300 border-slate-700'
                      }`}
                    >
                      {inc.severity}
                    </span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                        isResolved
                          ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          : isPending
                          ? 'bg-amber-500/10 text-amber-300 border-amber-500/20 animate-pulse'
                          : 'bg-rose-500/10 text-rose-400 border-rose-500/20 animate-pulse'
                      }`}
                    >
                      {inc.status}
                    </span>
                    <span className="text-xs font-semibold text-slate-400">
                      Service: <span className="text-cyan-400 font-bold">{inc.service_name}</span>
                    </span>
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-slate-100">{inc.title}</h3>
                    {inc.root_cause && (
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">
                        <span className="font-semibold text-slate-300">Root Cause:</span> {inc.root_cause}
                      </p>
                    )}
                  </div>

                  {inc.recommendation && (
                    <div className="p-3 bg-slate-900/60 border border-slate-700/60 rounded-lg text-xs space-y-1">
                      <span className="font-bold text-slate-300 flex items-center gap-1.5">
                        <Zap className="h-3.5 w-3.5 text-amber-400" /> Prescribed SRE Action:
                      </span>
                      <p className="text-slate-400 font-mono">{inc.recommendation}</p>
                    </div>
                  )}
                </div>

                {/* Right Action Controls */}
                <div className="flex flex-col justify-center gap-2 shrink-0 lg:w-56 border-t lg:border-t-0 lg:border-l border-slate-700/60 pt-4 lg:pt-0 lg:pl-6">
                  {!isResolved ? (
                    <>
                      <button
                        onClick={() => onNavigate('remediation')}
                        disabled={isBusy}
                        className="w-full bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs py-2 px-3 rounded-lg shadow-sm transition-all flex items-center justify-center gap-1.5 disabled:opacity-50"
                      >
                        <Zap className="h-3.5 w-3.5" />
                        <span>Remediate Now</span>
                      </button>

                      <button
                        onClick={() => onNavigate('ai_diagnosis')}
                        className="w-full bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold text-xs py-2 px-3 rounded-lg transition-all flex items-center justify-center gap-1.5 border border-slate-600/50"
                      >
                        <Cpu className="h-3.5 w-3.5 text-cyan-400" />
                        <span>AI Diagnosis</span>
                      </button>

                      {inc.status === 'OPEN' && (
                        <button
                          onClick={() => handleTransition(inc.id, 'INVESTIGATING')}
                          disabled={isBusy}
                          className="w-full bg-slate-800 hover:bg-slate-700 text-amber-300 font-bold text-xs py-1.5 px-3 rounded-lg transition-all border border-amber-500/30"
                        >
                          Mark Investigating
                        </button>
                      )}

                      <button
                        onClick={() => handleTransition(inc.id, 'RESOLVED')}
                        disabled={isBusy}
                        className="w-full bg-slate-800 hover:bg-emerald-950/40 text-emerald-400 hover:text-emerald-300 font-bold text-xs py-1.5 px-3 rounded-lg transition-all border border-emerald-500/30 flex items-center justify-center gap-1"
                      >
                        <CheckCircle className="h-3 w-3" />
                        <span>Resolve Manually</span>
                      </button>
                    </>
                  ) : (
                    <div className="flex flex-col items-center justify-center gap-1 text-xs text-emerald-400 font-bold py-4">
                      <CheckCircle className="h-5 w-5" />
                      <span>Incident Resolved</span>
                      <button
                        onClick={() => handleTransition(inc.id, 'OPEN')}
                        disabled={isBusy}
                        className="text-[10px] text-slate-400 hover:text-slate-200 mt-2 underline"
                      >
                        Re-open Incident
                      </button>
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
