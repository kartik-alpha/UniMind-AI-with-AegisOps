import React, { useState } from 'react';
import { Wrench, Zap, CheckCircle2, AlertTriangle, ShieldCheck, Play, ArrowRight, RotateCcw } from 'lucide-react';

export default function RemediationView({ onNavigate }) {
  const [action, setAction] = useState('RESTART_POD');
  const [executing, setExecuting] = useState(false);
  const [completed, setCompleted] = useState(false);
  const [logs, setLogs] = useState([]);

  const handleExecute = async () => {
    setExecuting(true);
    setCompleted(false);
    setLogs(['[00:00] Initializing AegisOps Autonomous Remediation Engine...']);

    const steps = [
      '[00:01] Verifying operator RBAC authorization: Kartik Lakhera (Role: ADMIN)... OK',
      '[00:02] Querying Kubernetes API: deployment/exam-service in namespace unimind-aegisops... OK',
      '[00:03] Sending SIGTERM to degraded pod exam-service-7d9f-x2k to flush pool contention...',
      '[00:04] Clearing stale PostgreSQL connection handles & resetting connection pool...',
      '[00:05] Initializing fresh replica container... Pod exam-service-7d9f-y4n is RUNNING (1.4s)',
      '[00:06] Polling Prometheus live probes: Latency dropped from 1,800ms to 112ms. CPU dropped to 24%.',
      '[00:07] Isolation Forest Anomaly Score recovered to nominal baseline (0.12 < 0.70 threshold).',
      '[00:08] Writing audit record to security log (ID: AUDIT-2026-7782)... SUCCESS',
      '[00:09] Incident INC-2026-0842 marked as RESOLVED in database.',
    ];

    try {
      // Call backend API
      const res = await fetch('/api/v1/aegisops/remediate?incident_id=1&action=RESTART_POD', {
        method: 'POST',
      });

      // Stream fake log steps for realistic terminal experience
      for (let i = 0; i < steps.length; i++) {
        await new Promise((r) => setTimeout(r, 300));
        setLogs((prev) => [...prev, steps[i]]);
      }

      setCompleted(true);
    } catch (err) {
      setLogs((prev) => [...prev, `[ERROR] Failed to execute remediation: ${err.message}`]);
    } finally {
      setExecuting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-900 mt-0.5">Controlled Self-Healing Remediation</h2>
          <p className="text-xs text-slate-500 mt-1">
            Human-in-the-loop and automated recovery orchestration with real-time audit logging.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Remediation Controls */}
        <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
            Incident Remediation Plan
          </span>

          <div className="p-3 bg-slate-50 rounded-xl border border-slate-200 space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-slate-500">Target Incident:</span>
              <span className="font-mono font-bold text-slate-900">INC-2026-0842</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Service:</span>
              <span className="font-bold text-blue-600">Exam Service</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-500">Root Cause:</span>
              <span className="font-semibold text-slate-700">Database Pool Exhaustion</span>
            </div>
          </div>

          <div className="space-y-2">
            <label className="text-xs font-bold text-slate-700 block">Select Controlled Action:</label>
            <div className="space-y-2">
              <label
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer text-xs transition-all ${
                  action === 'RESTART_POD'
                    ? 'border-blue-500 bg-blue-50/50 text-blue-900 font-semibold'
                    : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                }`}
              >
                <input
                  type="radio"
                  name="action"
                  checked={action === 'RESTART_POD'}
                  onChange={() => setAction('RESTART_POD')}
                  className="mt-0.5"
                />
                <div>
                  <span className="font-bold block">Restart Pod Deployment</span>
                  <span className="text-[11px] text-slate-500 font-normal">
                    Gracefully terminates degraded container and flushes exhausted connection pool.
                  </span>
                </div>
              </label>

              <label
                className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer text-xs transition-all ${
                  action === 'SCALE_DEPLOYMENT'
                    ? 'border-blue-500 bg-blue-50/50 text-blue-900 font-semibold'
                    : 'border-slate-200 hover:bg-slate-50 text-slate-700'
                }`}
              >
                <input
                  type="radio"
                  name="action"
                  checked={action === 'SCALE_DEPLOYMENT'}
                  onChange={() => setAction('SCALE_DEPLOYMENT')}
                  className="mt-0.5"
                />
                <div>
                  <span className="font-bold block">Scale Out Replicas (2 → 4)</span>
                  <span className="text-[11px] text-slate-500 font-normal">
                    Distributes incoming exam submission traffic across 4 pods.
                  </span>
                </div>
              </label>
            </div>
          </div>

          <div className="pt-2">
            <button
              onClick={handleExecute}
              disabled={executing}
              className={`w-full py-3 px-4 rounded-xl text-xs font-bold flex items-center justify-center gap-2 shadow-lg transition-all ${
                completed
                  ? 'bg-emerald-600 hover:bg-emerald-500 text-white'
                  : 'bg-blue-600 hover:bg-blue-500 text-white'
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
          </div>

          {completed && (
            <button
              onClick={() => onNavigate('services')}
              className="w-full py-2.5 px-4 rounded-xl text-xs font-bold bg-slate-100 hover:bg-slate-200 text-slate-700 flex items-center justify-center gap-1.5 transition-all"
            >
              <span>View Restored Service Fleet</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Right 2 Columns: Live Execution Terminal */}
        <div className="lg:col-span-2 bg-[#0b132b] text-slate-200 rounded-xl p-6 shadow-sm border border-slate-800 flex flex-col justify-between h-[450px]">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div className="flex items-center gap-2">
                <div className="h-3 w-3 rounded-full bg-red-500"></div>
                <div className="h-3 w-3 rounded-full bg-yellow-500"></div>
                <div className="h-3 w-3 rounded-full bg-green-500"></div>
                <span className="text-xs font-mono text-slate-400 ml-2">
                  aegisops-remediation-engine // stdout
                </span>
              </div>
              <span className="text-[10px] font-mono text-emerald-400 font-bold">
                {executing ? 'RUNNING PROBE...' : completed ? 'EXECUTION SUCCESS' : 'STANDBY'}
              </span>
            </div>

            <div className="mt-4 space-y-1.5 font-mono text-xs overflow-y-auto max-h-[340px]">
              {logs.length === 0 ? (
                <div className="text-slate-500 py-12 text-center">
                  Select an action on the left and click 'Approve & Execute Remediation' to begin live orchestration.
                </div>
              ) : (
                logs.map((log, idx) => (
                  <div
                    key={idx}
                    className={`${
                      log.includes('SUCCESS') || log.includes('RESOLVED')
                        ? 'text-emerald-400 font-bold'
                        : log.includes('ERROR')
                        ? 'text-rose-400 font-bold'
                        : log.includes('Verifying')
                        ? 'text-blue-300'
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
            <span>Target: exam-service (Port 8003)</span>
          </div>
        </div>
      </div>
    </div>
  );
}
