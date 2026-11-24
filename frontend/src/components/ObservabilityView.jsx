import React, { useState, useEffect } from 'react';
import {
  Activity,
  CheckCircle,
  AlertCircle,
  Database,
  Server,
  Layers,
  Cpu,
  RefreshCw,
  Terminal,
  Clock,
  Zap,
} from 'lucide-react';

export default function ObservabilityView() {
  const [healthData, setHealthData] = useState(null);
  const [metricsText, setMetricsText] = useState('');
  const [loading, setLoading] = useState(true);

  const fetchObservabilityData = async () => {
    setLoading(true);
    try {
      const [hRes, mRes] = await Promise.all([
        fetch('/health/ready'),
        fetch('/metrics'),
      ]);
      if (hRes.ok) {
        setHealthData(await hRes.json());
      }
      if (mRes.ok) {
        setMetricsText(await mRes.text());
      }
    } catch (e) {
      console.error('Failed to load observability data', e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchObservabilityData();
    const timer = setInterval(fetchObservabilityData, 15000); // 15s refresh
    return () => clearInterval(timer);
  }, []);

  // Parse key metrics from Prometheus exposition
  const parseMetric = (text, metricName) => {
    const lines = text.split('\n');
    for (const l of lines) {
      if (l.startsWith(metricName) && !l.startsWith('#')) {
        const parts = l.trim().split(' ');
        return parts[parts.length - 1];
      }
    }
    return '0';
  };

  const httpTotal = parseMetric(metricsText, 'unimind_http_requests_total');
  const httpErrors = parseMetric(metricsText, 'unimind_http_errors_total');
  const anomalyScore = parseMetric(metricsText, 'aegisops_ml_anomaly_score');

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
            <Activity className="h-6 w-6" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-slate-100">Platform Observability & Prometheus</h2>
            <p className="text-sm text-slate-400">
              Live service readiness, RED instrumentation (Rate, Errors, Duration), and Prometheus exposition.
            </p>
          </div>
        </div>
        <button
          onClick={fetchObservabilityData}
          className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700/80 rounded-lg border border-slate-700 transition-colors"
        >
          <RefreshCw className={`h-4 w-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} /> Refresh
        </button>
      </div>

      {/* Health Probes Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 p-5 rounded-xl border border-slate-700/50 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase text-slate-400">Overall Readiness</span>
            <CheckCircle className="h-5 w-5 text-emerald-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 capitalize">
            {healthData?.status || 'Ready'}
          </div>
          <span className="text-xs text-slate-400">Kubernetes /health/ready</span>
        </div>

        <div className="bg-slate-800/50 p-5 rounded-xl border border-slate-700/50 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase text-slate-400">Database Engine</span>
            <Database className="h-5 w-5 text-cyan-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 capitalize">
            {healthData?.checks?.database || 'Ready'}
          </div>
          <span className="text-xs text-slate-400">SQLite WAL Pool</span>
        </div>

        <div className="bg-slate-800/50 p-5 rounded-xl border border-slate-700/50 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase text-slate-400">Vector Store</span>
            <Layers className="h-5 w-5 text-purple-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 capitalize">
            {healthData?.checks?.vector_store || 'Healthy'}
          </div>
          <span className="text-xs text-slate-400">ChromaDB HNSWlib</span>
        </div>

        <div className="bg-slate-800/50 p-5 rounded-xl border border-slate-700/50 shadow-sm">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-bold uppercase text-slate-400">Adapters & Broker</span>
            <Server className="h-5 w-5 text-indigo-400" />
          </div>
          <div className="text-xl font-bold text-slate-100 capitalize">
            {healthData?.checks?.cache_broker || 'Ready'}
          </div>
          <span className="text-xs text-slate-400">In-Memory Token Bucket</span>
        </div>
      </div>

      {/* Live RED Metrics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-slate-400">
            <Zap className="h-5 w-5 text-amber-400" />
            <span className="text-xs font-bold uppercase tracking-wider">Processed Requests</span>
          </div>
          <div className="text-3xl font-extrabold text-slate-100">{httpTotal}</div>
          <p className="text-xs text-slate-400 mt-1 font-mono">unimind_http_requests_total</p>
        </div>

        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-slate-400">
            <AlertCircle className="h-5 w-5 text-rose-400" />
            <span className="text-xs font-bold uppercase tracking-wider">HTTP Errors</span>
          </div>
          <div className="text-3xl font-extrabold text-rose-400">{httpErrors}</div>
          <p className="text-xs text-slate-400 mt-1 font-mono">unimind_http_errors_total</p>
        </div>

        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm">
          <div className="flex items-center gap-2 mb-2 text-slate-400">
            <Cpu className="h-5 w-5 text-cyan-400" />
            <span className="text-xs font-bold uppercase tracking-wider">ML Anomaly Score</span>
          </div>
          <div className="text-3xl font-extrabold text-slate-100">{anomalyScore}</div>
          <p className="text-xs text-slate-400 mt-1 font-mono">aegisops_ml_anomaly_score</p>
        </div>
      </div>

      {/* Raw Prometheus Text Feed */}
      <div className="bg-[#0b132b] rounded-xl p-5 border border-slate-800 shadow-md">
        <div className="flex items-center justify-between mb-3 border-b border-slate-800 pb-2">
          <div className="flex items-center gap-2 text-slate-200 font-mono text-sm">
            <Terminal className="h-4 w-4 text-emerald-400" />
            <span>Prometheus Exposition Feed (/metrics)</span>
          </div>
          <span className="text-[11px] font-mono text-slate-400">text/plain; version=0.0.4</span>
        </div>
        <pre className="text-xs font-mono text-slate-300 overflow-x-auto max-h-96 p-3 bg-[#080d1e] rounded-lg border border-slate-800/60">
          {metricsText || '# No metrics scraped yet'}
        </pre>
      </div>
    </div>
  );
}
