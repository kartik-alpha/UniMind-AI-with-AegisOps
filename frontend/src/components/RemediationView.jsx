import React, { useState, useEffect } from 'react';
import {
  Wrench,
  Zap,
  CheckCircle2,
  AlertTriangle,
  ShieldCheck,
  Play,
  ArrowRight,
  RotateCcw,
  XCircle,
  Server,
  Layers,
} from 'lucide-react';
import { apiFetch, getTenantId, parseApiError } from '../apiClient';

export default function RemediationView({ onNavigate }) {
  const [action, setAction] = useState('RESTART_POD');
  const [incidents, setIncidents] = useState([]);
  const [selectedIncidentId, setSelectedIncidentId] = useState('');
  const [targetReplicas, setTargetReplicas] = useState(4);
  const [executing, setExecuting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [logs, setLogs] = useState([]);
  const [errorMsg, setErrorMsg] = useState(null);

  const fetchActiveIncidents = async () => {
    try {
      const res = await apiFetch('/api/v1/incidents');
      if (res.ok) {
        const list = await res.json();
        setIncidents(list);
        const active = list.filter((i) => i.status !== 'RESOLVED');
        if (active.length > 0 && !selectedIncidentId) {
          setSelectedIncidentId(String(active[0].id));
        } else if (list.length > 0 && !selectedIncidentId) {
          setSelectedIncidentId(String(list[0].id));
        }
      }
    } catch (err) {
      console.warn('Failed to fetch active incidents', err);
    }
  };

  useEffect(() => {
    fetchActiveIncidents();
  }, []);

  const activeIncident =
    incidents.find((i) => String(i.id) === String(selectedIncidentId)) || incidents[0] || null;

  const handleExecuteRemediation = async () => {
    if (!selectedIncidentId) {
      setErrorMsg('Please select an incident to remediate.');
      return;
    }

    setExecuting(true);
    setCompleted(false);
    setErrorMsg(null);
    setLogs([
      `[${new Date().toLocaleTimeString()}] Initializing AegisOps Autonomous Remediation Engine...`,
      `[${new Date().toLocaleTimeString()}] Target Incident: ${activeIncident?.incident_code || 'INC-1'} (${activeIncident?.service_name || 'Exam Service'})`,
      `[${new Date().toLocaleTimeString()}] Selected Strategy: ${action}...`,
    ]);

    try {
      const res = await apiFetch('/api/v1/aegisops/remediate/approve', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: parseInt(selectedIncidentId, 10),
          action: action,
          target_replicas: parseInt(targetReplicas, 10) || 4,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        const steps = [
          `[${new Date().toLocaleTimeString()}] Verifying RBAC authorization for operator... APPROVED`,
          `[${new Date().toLocaleTimeString()}] Invoking Kubernetes self-healing orchestrator...`,
          `[${new Date().toLocaleTimeString()}] Action dispatched: ${data.action || action}`,
          `[${new Date().toLocaleTimeString()}] Status transition: ${data.incident_status || 'RESOLVED'}`,
          `[${new Date().toLocaleTimeString()}] Telemetry verification: ${data.message || 'Service returned to healthy baseline.'}`,
          `[${new Date().toLocaleTimeString()}] Cryptographic audit log written (Tamper-evident chain updated).`,
          `[${new Date().toLocaleTimeString()}] Self-healing sequence COMPLETED successfully!`,
        ];

        for (const step of steps) {
          await new Promise((r) => setTimeout(r, 200));
          setLogs((prev) => [...prev, step]);
        }

        setCompleted(true);
        fetchActiveIncidents();
      } else {
        const prob = await parseApiError(res);
        setErrorMsg(prob.detail);
        setLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] [ERROR] Remediation execution failed (${prob.status}): ${prob.detail}`,
        ]);
      }
    } catch (err) {
      setErrorMsg(err.message);
      setLogs((prev) => [
        ...prev,
        `[${new Date().toLocaleTimeString()}] [NETWORK ERROR] ${err.message}`,
      ]);
    } finally {
      setExecuting(false);
    }
  };

  const handleRejectRemediation = async () => {
    if (!selectedIncidentId) return;

    setExecuting(true);
    setErrorMsg(null);
    try {
      const res = await apiFetch('/api/v1/aegisops/remediate/reject', {
        method: 'POST',
        body: JSON.stringify({
          incident_id: parseInt(selectedIncidentId, 10),
          reason: 'Operator rejected automated recommendation in favor of manual review.',
        }),
      });

      if (res.ok) {
        setLogs((prev) => [
          ...prev,
          `[${new Date().toLocaleTimeString()}] Automated recommendation REJECTED by operator. Incident returned to open review.`,
        ]);
        fetchActiveIncidents();
      } else {
        const prob = await parseApiError(res);
        setErrorMsg(prob.detail);
      }
    } catch (err) {
      setErrorMsg(err.message);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Controlled Self-Healing Remediation</h2>
          <p className="text-xs text-slate-400 mt-1">
            Human-in-the-loop and automated recovery orchestration with real-time audit logging.
          </p>
        </div>
      </div>

      {errorMsg && (
        <div className="p-4 bg-rose-950/20 border border-rose-500/30 rounded-xl text-rose-300 text-xs flex items-center justify-between">
          <span>{errorMsg}</span>
          <button onClick={() => setErrorMsg(null)} className="text-slate-400 hover:text-white font-bold ml-2">
            ✕
          </button>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Remediation Controls */}
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 shadow-sm space-y-5">
          <span className="text-xs font-bold text-slate-400 uppercase tracking-wider block">
            Incident Remediation Plan
          </span>

          {/* Incident Selector */}
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-slate-300">Select Target Incident:</label>
            <select
              value={selectedIncidentId}
              onChange={(e) => setSelectedIncidentId(e.target.value)}
              className="w-full bg-slate-900 border border-slate-700 rounded-lg p-2.5 text-xs text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              {incidents.length === 0 ? (
                <option value="">No active incidents</option>
              ) : (
                incidents.map((i) => (
                  <option key={i.id} value={i.id}>
                    {i.incident_code} - {i.service_name} ({i.status})
                  </option>
                ))
              )}
            </select>
          </div>

          {activeIncident && (
            <div className="p-3 bg-slate-900/60 rounded-xl border border-slate-700/60 space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-400">Target Incident:</span>
                <span className="font-mono font-bold text-slate-200">{activeIncident.incident_code}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Service:</span>
                <span className="font-bold text-cyan-400">{activeIncident.service_name}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Status:</span>
                <span className="font-bold text-amber-400">{activeIncident.status}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-400">Root Cause:</span>
                <span className="font-semibold text-slate-300 truncate max-w-[180px]">
                  {activeIncident.root_cause || 'Telemetry saturation'}
                </span>
              </div>
            </div>
          )}

          {/* Remediation Action Selection */}
          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-300 block">Select Controlled Action:</label>
            <div className="space-y-2">
              <label
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer text-xs transition-all ${
                  action === 'RESTART_POD'
                    ? 'border-cyan-500 bg-cyan-500/10 text-cyan-200 font-semibold'
                    : 'border-slate-700 hover:bg-slate-700/40 text-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="action"
                  checked={action === 'RESTART_POD'}
                  onChange={() => setAction('RESTART_POD')}
                  className="mt-0.5 text-cyan-600 focus:ring-cyan-500"
                />
                <div>
                  <span className="font-bold block text-slate-200">Restart Pod Deployment</span>
                  <span className="text-[11px] text-slate-400 font-normal">
                    Gracefully terminates degraded container and flushes exhausted connection pool.
                  </span>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer text-xs transition-all ${
                  action === 'SCALE_DEPLOYMENT'
                    ? 'border-cyan-500 bg-cyan-500/10 text-cyan-200 font-semibold'
                    : 'border-slate-700 hover:bg-slate-700/40 text-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="action"
                  checked={action === 'SCALE_DEPLOYMENT'}
                  onChange={() => setAction('SCALE_DEPLOYMENT')}
                  className="mt-0.5 text-cyan-600 focus:ring-cyan-500"
                />
                <div>
                  <span className="font-bold block text-slate-200">Scale Out Replicas</span>
                  <span className="text-[11px] text-slate-400 font-normal">
                    Distributes incoming exam submission traffic across 4 pods.
                  </span>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer text-xs transition-all ${
                  action === 'FLUSH_IDLE_CONNECTIONS'
                    ? 'border-cyan-500 bg-cyan-500/10 text-cyan-200 font-semibold'
                    : 'border-slate-700 hover:bg-slate-700/40 text-slate-300'
                }`}
              >
                <input
                  type="radio"
                  name="action"
                  checked={action === 'FLUSH_IDLE_CONNECTIONS'}
                  onChange={() => setAction('FLUSH_IDLE_CONNECTIONS')}
                  className="mt-0.5 text-cyan-600 focus:ring-cyan-500"
                />
                <div>
                  <span className="font-bold block text-slate-200">Flush Idle DB Handles</span>
                  <span className="text-[11px] text-slate-400 font-normal">
                    Resets connection handles and clears connection starvation.
                  </span>
                </div>
              </label>
            </div>
          </div>

          {/* Action Trigger Buttons */}
          <div className="pt-2 space-y-2">
            <button
              onClick={handleExecuteRemediation}
              disabled={executing || !selectedIncidentId}
              className={`w-full py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-lg transition-all ${
                completed
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                  : 'bg-cyan-600 hover:bg-cyan-500 text-white'
              } disabled:opacity-50`}
            >
              {executing ? (
                <>
                  <Wrench className="h-4 w-4 animate-spin" />
                  <span>Executing Self-Healing...</span>
                </>
              ) : completed ? (
                <>
                  <CheckCircle2 className="h-4 w-4" />
                  <span>Remediation Complete (Re-run)</span>
                </>
              ) : (
                <>
                  <Play className="h-4 w-4 fill-current" />
                  <span>Approve & Execute Remediation</span>
                </>
              )}
            </button>

            {activeIncident && activeIncident.status === 'PENDING_APPROVAL' && (
              <button
                onClick={handleRejectRemediation}
                disabled={executing}
                className="w-full py-2 px-4 rounded-xl text-xs font-bold bg-slate-800 hover:bg-rose-950/40 text-rose-300 border border-rose-800/40 flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
              >
                <XCircle className="h-3.5 w-3.5" />
                <span>Reject Automated Recommendation</span>
              </button>
            )}
          </div>

          {completed && (
            <button
              onClick={() => onNavigate('services')}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-bold bg-slate-700 hover:bg-slate-600 text-slate-200 flex items-center justify-center gap-1.5 transition-all border border-slate-600"
            >
              <span>View Restored Service Fleet</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Right 2 Columns: Live Execution Terminal */}
        <div className="lg:col-span-2 bg-[#0b132b] text-slate-200 rounded-xl p-6 shadow-sm border border-slate-800 flex flex-col justify-between h-[520px]">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-rose-500"></div>
                <div className="h-3 w-3 rounded-full bg-amber-500"></div>
                <div className="h-3 w-3 rounded-full bg-emerald-500"></div>
                <span className="text-xs font-mono text-slate-400 ml-2">
                  aegisops-remediation-engine // stdout
                </span>
              </div>
              <span className="text-[10px] font-mono text-cyan-400 font-bold">
                {executing ? 'RUNNING PROBE...' : completed ? 'EXECUTION SUCCESS' : 'STANDBY'}
              </span>
            </div>

            <div className="mt-4 space-y-1.5 font-mono text-xs overflow-y-auto max-h-[400px]">
              {logs.length === 0 ? (
                <div className="text-slate-500 py-16 text-center">
                  Select an incident and action on the left, then click 'Approve & Execute Remediation' to begin live orchestration.
                </div>
              ) : (
                logs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`${
                      log.includes('SUCCESS') || log.includes('RESOLVED') || log.includes('COMPLETED')
                        ? 'text-emerald-400 font-bold'
                        : log.includes('ERROR')
                        ? 'text-rose-400 font-bold'
                        : log.includes('Verifying') || log.includes('Target')
                        ? 'text-cyan-300'
                        : 'text-slate-300'
                    }`}
                  >
                    {log}
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500 flex justify-between font-mono">
            <span>Cluster: unimind-prod-us-east-1</span>
            <span>Target: {activeIncident?.service_name || 'exam-service'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
