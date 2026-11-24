import React, { useState, useEffect } from 'react';
import { Layers, Server, RefreshCw, CheckCircle, AlertTriangle, ArrowUp, ArrowDown, RotateCcw } from 'lucide-react';

export default function KubernetesView() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [selectedPodLog, setSelectedPodLog] = useState(null);

  const fetchK8s = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/aegisops/kubernetes/status');
      if (res.ok) {
        setData(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchK8s();
  }, []);

  const handleScale = async (serviceName, newReplicas) => {
    try {
      await fetch(`/api/v1/aegisops/services/${serviceName}/scale?replicas=${newReplicas}`, {
        method: 'POST',
      });
      fetchK8s();
    } catch (err) {
      console.error(err);
    }
  };

  const handleRestart = async (serviceName) => {
    try {
      await fetch(`/api/v1/aegisops/services/${serviceName}/restart`, {
        method: 'POST',
      });
      fetchK8s();
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Kubernetes Cluster & Deployments</h2>
          <p className="text-xs text-slate-400 mt-1">
            Namespace: <span className="font-mono font-bold text-cyan-400">unimind-aegisops</span> • Cluster: v1.28.4-gke
          </p>
        </div>

        <button
          onClick={fetchK8s}
          className="px-3 py-2 bg-slate-800 border border-slate-700 hover:bg-slate-700/80 text-slate-300 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-all"
        >
          <RefreshCw className={`h-4 w-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Cluster</span>
        </button>
      </div>

      {/* Deployments Section */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-700/60 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Layers className="h-4 w-4 text-cyan-400" /> Active Deployments (4)
          </h3>
          <span className="text-xs text-slate-400">Autonomous Replica Autoscaling Enabled</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-700/60">
              <tr>
                <th className="py-2.5 px-4">Deployment</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Replicas</th>
                <th className="py-2.5 px-4">Container Image</th>
                <th className="py-2.5 px-4">Resource Limits</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {data?.deployments?.map((dep) => {
                const isDegraded = dep.status.includes('Degraded');
                return (
                  <tr key={dep.name} className="hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-200">{dep.name}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          isDegraded
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/20 animate-pulse'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        }`}
                      >
                        {isDegraded ? 'Degraded' : 'Healthy'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-200">
                      {dep.ready_replicas} / {dep.total_replicas}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">{dep.image}</td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      {dep.cpu_limit} / {dep.mem_limit}
                    </td>
                    <td className="py-3 px-4 text-right space-x-1">
                      <button
                        onClick={() => handleScale(dep.name, dep.total_replicas + 1)}
                        title="Scale Out"
                        className="p-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-cyan-300 font-bold text-xs transition-colors"
                      >
                        <ArrowUp className="h-3.5 w-3.5 inline" />
                      </button>
                      <button
                        onClick={() => handleScale(dep.name, Math.max(1, dep.total_replicas - 1))}
                        title="Scale In"
                        className="p-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-300 hover:text-cyan-300 font-bold text-xs transition-colors"
                      >
                        <ArrowDown className="h-3.5 w-3.5 inline" />
                      </button>
                      <button
                        onClick={() => handleRestart(dep.name)}
                        className="px-2 py-1 rounded bg-slate-700 hover:bg-slate-600 text-slate-300 text-[11px] font-semibold transition-colors"
                      >
                        Restart
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pods Table */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-700/60 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-100 flex items-center gap-2">
            <Server className="h-4 w-4 text-cyan-400" /> Pod Fleet Status ({data?.pods?.length || 0})
          </h3>
          <span className="text-xs text-slate-400">Node Pools: gke-node-pool-1, gke-node-pool-2</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-700/60">
              <tr>
                <th className="py-2.5 px-4">Pod Name</th>
                <th className="py-2.5 px-4">Deployment</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Restarts</th>
                <th className="py-2.5 px-4">Age</th>
                <th className="py-2.5 px-4">Node</th>
                <th className="py-2.5 px-4">CPU</th>
                <th className="py-2.5 px-4">Memory</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50 font-mono">
              {data?.pods?.map((pod) => {
                const isCrash = pod.status === 'CrashLoopBackOff';
                return (
                  <tr key={pod.name} className="hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-200 font-sans">{pod.name}</td>
                    <td className="py-3 px-4 text-slate-400 font-sans">{pod.deployment}</td>
                    <td className="py-3 px-4 font-sans">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                          isCrash
                            ? 'bg-rose-500/10 text-rose-400 border-rose-500/20 animate-pulse'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        }`}
                      >
                        {pod.status}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-slate-300">{pod.restarts}</td>
                    <td className="py-3 px-4 text-slate-400">{pod.age}</td>
                    <td className="py-3 px-4 text-slate-400">{pod.node}</td>
                    <td className="py-3 px-4 font-bold text-slate-200">{pod.cpu}</td>
                    <td className="py-3 px-4 font-bold text-slate-200">{pod.memory}</td>
                    <td className="py-3 px-4 text-right font-sans">
                      <button
                        onClick={() =>
                          setSelectedPodLog({
                            pod: pod.name,
                            logs: `[INFO] Pod ${pod.name} container started on ${pod.node}
[DEBUG] Initializing health check liveness probe on port 8003
${isCrash ? '[ERROR] Database connection timeout: Connection pool handles maxed out (50/50)' : '[INFO] Normal telemetry heartbeat recorded. 0 memory leaks.'}
[INFO] Container status: ${pod.status}`,
                          })
                        }
                        className="px-2 py-1 rounded bg-cyan-500/10 text-cyan-300 hover:bg-cyan-600 hover:text-white text-[11px] font-semibold transition-colors border border-cyan-500/20"
                      >
                        Logs
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Pod Log Drawer / Modal */}
      {selectedPodLog && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0b132b] text-slate-200 rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <span className="text-[10px] font-mono uppercase text-cyan-400 block">kubectl logs</span>
                <h3 className="text-sm font-bold font-mono text-white mt-0.5">
                  {selectedPodLog.pod}
                </h3>
              </div>
              <button
                onClick={() => setSelectedPodLog(null)}
                className="text-slate-400 hover:text-white font-bold"
              >
                ✕
              </button>
            </div>

            <div className="bg-black/60 rounded-xl p-4 font-mono text-xs text-emerald-400 whitespace-pre-wrap leading-relaxed max-h-80 overflow-y-auto border border-slate-800">
              {selectedPodLog.logs}
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedPodLog(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-bold transition-all border border-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
