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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-900 mt-0.5">Kubernetes Cluster & Deployments</h2>
          <p className="text-xs text-slate-500 mt-1">
            Namespace: <span className="font-mono font-bold text-blue-600">unimind-aegisops</span> • Cluster: v1.28.4-gke
          </p>
        </div>

        <button
          onClick={fetchK8s}
          className="px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-all"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh Cluster</span>
        </button>
      </div>

      {/* Deployments Section */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Layers className="h-4 w-4 text-blue-600" /> Active Deployments (4)
          </h3>
          <span className="text-xs text-slate-500">Autonomous Replica Autoscaling Enabled</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Deployment</th>
                <th className="py-2.5 px-4">Status</th>
                <th className="py-2.5 px-4">Replicas</th>
                <th className="py-2.5 px-4">Container Image</th>
                <th className="py-2.5 px-4">Resource Limits</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data?.deployments?.map((dep) => {
                const isDegraded = dep.status.includes('Degraded');
                return (
                  <tr key={dep.name} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-semibold text-slate-900">{dep.name}</td>
                    <td className="py-3 px-4">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          isDegraded
                            ? 'bg-rose-100 text-rose-700 animate-pulse'
                            : 'bg-emerald-100 text-emerald-700'
                        }`}
                      >
                        {isDegraded ? 'Degraded' : 'Healthy'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono font-bold text-slate-800">
                      {dep.ready_replicas} / {dep.total_replicas}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-500">{dep.image}</td>
                    <td className="py-3 px-4 font-mono text-slate-600">
                      {dep.cpu_limit} / {dep.mem_limit}
                    </td>
                    <td className="py-3 px-4 text-right space-x-1">
                      <button
                        onClick={() => handleScale(dep.name, dep.total_replicas + 1)}
                        title="Scale Out"
                        className="p-1 rounded bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-600 font-bold text-xs"
                      >
                        <ArrowUp className="h-3.5 w-3.5 inline" />
                      </button>
                      <button
                        onClick={() => handleScale(dep.name, Math.max(1, dep.total_replicas - 1))}
                        title="Scale In"
                        className="p-1 rounded bg-slate-100 hover:bg-blue-50 text-slate-700 hover:text-blue-600 font-bold text-xs"
                      >
                        <ArrowDown className="h-3.5 w-3.5 inline" />
                      </button>
                      <button
                        onClick={() => handleRestart(dep.name)}
                        className="px-2 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 text-[11px] font-semibold"
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
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900 flex items-center gap-2">
            <Server className="h-4 w-4 text-blue-600" /> Pod Fleet Status ({data?.pods?.length || 0})
          </h3>
          <span className="text-xs text-slate-500">Node Pools: gke-node-pool-1, gke-node-pool-2</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
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
            <tbody className="divide-y divide-slate-100 font-mono">
              {data?.pods?.map((pod) => {
                const isCrash = pod.status === 'CrashLoopBackOff';
                return (
                  <tr key={pod.name} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-semibold text-slate-900 font-sans">{pod.name}</td>
                    <td className="py-3 px-4 text-slate-600 font-sans">{pod.deployment}</td>
                    <td className="py-3 px-4 font-sans">
                      <span
                        className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[10px] font-bold ${
                          isCrash
                            ? 'bg-rose-100 text-rose-700 animate-pulse'
                            : 'bg-emerald-100 text-emerald-700'
                        }`}
                      >
                        {pod.status}
                      </span>
                    </td>
                    <td className="py-3 px-4">{pod.restarts}</td>
                    <td className="py-3 px-4 text-slate-500">{pod.age}</td>
                    <td className="py-3 px-4 text-slate-500">{pod.node}</td>
                    <td className="py-3 px-4 font-bold text-slate-800">{pod.cpu}</td>
                    <td className="py-3 px-4 font-bold text-slate-800">{pod.memory}</td>
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
                        className="px-2 py-1 rounded bg-blue-50 text-blue-600 hover:bg-blue-600 hover:text-white text-[11px] font-semibold transition-colors"
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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0b132b] text-slate-200 rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-800 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <span className="text-[10px] font-mono uppercase text-blue-400 block">kubectl logs</span>
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
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-white rounded-lg text-xs font-bold transition-all"
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
