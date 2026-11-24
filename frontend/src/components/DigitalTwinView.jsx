import React, { useState, useEffect } from 'react';
import {
  Users,
  Calendar,
  Zap,
  Cpu,
  Database,
  AlertTriangle,
  ShieldCheck,
  CheckCircle2,
  RefreshCw,
  BarChart2,
  Clock,
  Layers,
  ArrowRight,
  TrendingUp,
  Server,
  XCircle,
} from 'lucide-react';

export default function DigitalTwinView({ onNavigate }) {
  // Config state
  const [totalStudents, setTotalStudents] = useState(15000);
  const [concurrencyRatio, setConcurrencyRatio] = useState(0.20);
  const [event, setEvent] = useState('EXAM_PERIOD');
  const [intensity, setIntensity] = useState('PEAK');
  const [durationHours, setDurationHours] = useState(24);

  // Data state
  const [forecast, setForecast] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [predictiveAlerts, setPredictiveAlerts] = useState([]);
  const [loading, setLoading] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('forecast'); // 'forecast', 'compare', 'alerts'
  const [actionResult, setActionResult] = useState(null);

  // Fetch forecast and predictive incidents
  const runCapacityPlan = async () => {
    setLoading(true);
    setActionResult(null);
    try {
      const res = await fetch('/api/v1/digital-twin/capacity-plan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          total_students: parseInt(totalStudents),
          concurrency_ratio: parseFloat(concurrencyRatio),
          duration_hours: parseInt(durationHours),
          event: event,
          intensity: intensity,
          sync_to_aegisops: true,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setForecast(data);
      }
      await fetchPredictiveAlerts();
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const runScenarioComparison = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/digital-twin/scenario-compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          total_students: parseInt(totalStudents),
          duration_hours: 24,
          event: event,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setComparison(data);
        setActiveTab('compare');
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchPredictiveAlerts = async () => {
    try {
      const res = await fetch('/api/v1/digital-twin/predictive-alerts');
      if (res.ok) {
        setPredictiveAlerts(await res.json());
      }
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    runCapacityPlan();
  }, []);

  const handleApproveProactive = async (incidentId, targetReplicas = 4) => {
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token') || '';
      const res = await fetch('/api/v1/digital-twin/proactive-remediation/approve', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          incident_id: incidentId,
          target_replicas: targetReplicas,
        }),
      });
      if (res.ok) {
        const result = await res.json();
        setActionResult({ type: 'success', text: `Approved proactive pre-scale! Action: ${result.action_executed}. Headroom verified.` });
        await runCapacityPlan();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  const handleRejectProactive = async (incidentId) => {
    setActionLoading(true);
    try {
      const token = localStorage.getItem('token') || '';
      const res = await fetch('/api/v1/digital-twin/proactive-remediation/reject', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({
          incident_id: incidentId,
          reason: 'Administrator deferred pre-scaling based on manual assessment',
        }),
      });
      if (res.ok) {
        setActionResult({ type: 'info', text: 'Proactive recommendation deferred. Incident updated to OPEN.' });
        await fetchPredictiveAlerts();
      }
    } catch (e) {
      console.error(e);
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-xs font-bold tracking-wider text-cyan-400 uppercase">Stage E Engine</span>
            <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
              Deterministic Simulation
            </span>
          </div>
          <h2 className="text-2xl font-bold text-slate-100 mt-1">Digital Twin Campus Simulation</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Model diurnal student curves, academic calendar traffic shocks, and predictive capacity saturation.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={() => { setActiveTab('forecast'); runCapacityPlan(); }}
            disabled={loading}
            className="px-3 py-2 bg-cyan-600 hover:bg-cyan-500 text-white text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-sm transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-3.5 w-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Simulate & Plan</span>
          </button>
          <button
            onClick={runScenarioComparison}
            disabled={loading}
            className="px-3 py-2 bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg flex items-center gap-1.5 shadow-sm transition-all"
          >
            <BarChart2 className="h-3.5 w-3.5 text-cyan-400" />
            <span>Compare Scenarios</span>
          </button>
        </div>
      </div>

      {actionResult && (
        <div className={`p-4 rounded-xl border text-xs flex items-center justify-between ${
          actionResult.type === 'success'
            ? 'bg-emerald-950/20 border-emerald-500/30 text-emerald-300'
            : 'bg-slate-800 border-slate-700 text-slate-300'
        }`}>
          <div className="flex items-center gap-2">
            <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            <span>{actionResult.text}</span>
          </div>
          <button onClick={() => setActionResult(null)} className="text-slate-400 hover:text-slate-200 font-bold">✕</button>
        </div>
      )}

      {/* Simulation Parameter Controls */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm">
        <h3 className="text-xs font-bold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Calendar className="h-4 w-4 text-cyan-400" />
          <span>Campus Simulation Parameters</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">Total Students</label>
            <select
              value={totalStudents}
              onChange={(e) => setTotalStudents(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs font-medium text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="5000">5,000 Students</option>
              <option value="10000">10,000 Students</option>
              <option value="15000">15,000 Students (Standard)</option>
              <option value="25000">25,000 Students (Large Campus)</option>
              <option value="40000">40,000 Students (State Univ)</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">Academic Event</label>
            <select
              value={event}
              onChange={(e) => setEvent(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs font-medium text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="NORMAL_DAY">Normal Academic Day</option>
              <option value="EXAM_PERIOD">Exam Period (Exam Spike)</option>
              <option value="ASSIGNMENT_DEADLINE">Assignment Deadline (LMS Spike)</option>
              <option value="ADMISSION_PERIOD">Admissions (Portal Influx)</option>
              <option value="RESULT_ANNOUNCEMENT">Result Announcement (Shock Spike)</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">Traffic Intensity</label>
            <select
              value={intensity}
              onChange={(e) => setIntensity(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs font-medium text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="LOW">Low (0.7x)</option>
              <option value="NORMAL">Normal (1.0x)</option>
              <option value="PEAK">Peak (1.4x)</option>
              <option value="EXTREME">Extreme Stress (2.1x)</option>
            </select>
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">
              Active Concurrency: {Math.round(concurrencyRatio * 100)}%
            </label>
            <input
              type="range"
              min="0.05"
              max="0.40"
              step="0.05"
              value={concurrencyRatio}
              onChange={(e) => setConcurrencyRatio(parseFloat(e.target.value))}
              className="w-full mt-2 accent-cyan-500 cursor-pointer"
            />
          </div>

          <div>
            <label className="text-[11px] font-semibold text-slate-400 block mb-1">Duration</label>
            <select
              value={durationHours}
              onChange={(e) => setDurationHours(Number(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-xs font-medium text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="24">24-Hour Cycle</option>
              <option value="48">48-Hour Window</option>
              <option value="168">7-Day Academic Week</option>
            </select>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex border-b border-slate-700/60 gap-6 text-xs font-semibold">
        <button
          onClick={() => setActiveTab('forecast')}
          className={`pb-3 transition-colors flex items-center gap-1.5 ${
            activeTab === 'forecast' ? 'border-b-2 border-cyan-400 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <TrendingUp className="h-4 w-4" />
          <span>Capacity Forecast & Saturation</span>
        </button>

        <button
          onClick={() => setActiveTab('alerts')}
          className={`pb-3 transition-colors flex items-center gap-1.5 relative ${
            activeTab === 'alerts' ? 'border-b-2 border-cyan-400 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <AlertTriangle className="h-4 w-4" />
          <span>AegisOps Early Warnings</span>
          {forecast?.alerts?.length > 0 && (
            <span className="ml-1 px-1.5 py-0.5 rounded-full bg-rose-500 text-white text-[10px] font-bold">
              {forecast.alerts.length}
            </span>
          )}
        </button>

        <button
          onClick={() => setActiveTab('compare')}
          className={`pb-3 transition-colors flex items-center gap-1.5 ${
            activeTab === 'compare' ? 'border-b-2 border-cyan-400 text-cyan-300' : 'text-slate-400 hover:text-slate-200'
          }`}
        >
          <BarChart2 className="h-4 w-4" />
          <span>Multi-Scenario Matrix</span>
        </button>
      </div>

      {/* Tab 1: Forecast & Saturation */}
      {activeTab === 'forecast' && forecast && (
        <div className="space-y-6">
          {/* Executive KPI Cards */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 shadow-sm">
              <span className="text-[11px] font-bold text-slate-400 uppercase">Headroom Status</span>
              <div className="mt-2 flex items-center justify-between">
                <span className={`text-xl font-bold ${
                  forecast.overall_status === 'HEALTHY' ? 'text-emerald-400' :
                  forecast.overall_status === 'WARNING' ? 'text-amber-400' : 'text-rose-400'
                }`}>
                  {forecast.overall_status}
                </span>
                <span className={`px-2 py-1 rounded text-xs font-semibold border ${
                  forecast.overall_status === 'HEALTHY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                  forecast.overall_status === 'WARNING' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                }`}>
                  {forecast.alerts.length} alerts
                </span>
              </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 shadow-sm">
              <span className="text-[11px] font-bold text-slate-400 uppercase">Peak Concurrent Users</span>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-2xl font-bold text-slate-100">{forecast.peak_concurrent_users.toLocaleString()}</span>
                <span className="text-xs text-slate-400 font-medium">@ {String(forecast.peak_hour).padStart(2, '0')}:00</span>
              </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 shadow-sm">
              <span className="text-[11px] font-bold text-slate-400 uppercase">Peak Throughput</span>
              <div className="mt-2 flex items-baseline justify-between">
                <span className="text-2xl font-bold text-cyan-400">{forecast.peak_rps.toFixed(1)}</span>
                <span className="text-xs text-slate-400 font-medium">req / sec</span>
              </div>
            </div>

            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 shadow-sm">
              <span className="text-[11px] font-bold text-slate-400 uppercase">Simulated Event</span>
              <div className="mt-2 flex items-center justify-between">
                <span className="text-sm font-bold text-slate-200 truncate">{forecast.event}</span>
                <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-700 text-slate-300">
                  {forecast.intensity}
                </span>
              </div>
            </div>
          </div>

          {/* AI Executive Summary */}
          <div className="bg-cyan-950/20 border border-cyan-500/30 rounded-xl p-4 text-xs text-cyan-200 flex items-start gap-3">
            <Zap className="h-4 w-4 text-cyan-400 flex-shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block mb-0.5 text-cyan-300">Predictive SRE Headroom Analysis:</span>
              <p className="text-slate-300 leading-relaxed">{forecast.executive_summary}</p>
            </div>
          </div>

          {/* Service Capacity Saturation Cards */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center justify-between">
              <span>Predictive Fleet Resource Utilization (Peak Hour)</span>
              <span className="text-[10px] text-slate-500 font-normal">Derived from calibrated non-linear M/M/c queuing models</span>
            </h3>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {Object.entries(forecast.metrics_by_service).map(([sName, points]) => {
                const peakPoint = points.reduce((prev, curr) => (curr.predicted_rps > prev.predicted_rps ? curr : prev), points[0]);
                const isCrit = peakPoint.predicted_cpu_percent >= 85 || peakPoint.db_pool_saturation_percent >= 85;

                return (
                  <div
                    key={sName}
                    className={`p-4 rounded-xl border transition-all ${
                      isCrit ? 'border-rose-500/40 bg-rose-950/20' : 'border-slate-700/50 bg-slate-800/80'
                    }`}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-xs font-bold text-slate-200 capitalize">{sName.replace('_', ' ')}</span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded border ${
                        isCrit ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                      }`}>
                        {isCrit ? 'Bottleneck' : 'Headroom OK'}
                      </span>
                    </div>

                    <div className="space-y-3 text-xs">
                      {/* RPS */}
                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-400 font-medium">Throughput</span>
                          <span className="font-bold text-slate-200">{peakPoint.predicted_rps.toFixed(0)} / {peakPoint.capacity_rps.toFixed(0)} RPS</span>
                        </div>
                        <div className="w-full bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${peakPoint.utilization_percent >= 90 ? 'bg-rose-500' : 'bg-cyan-500'}`}
                            style={{ width: `${Math.min(100, peakPoint.utilization_percent)}%` }}
                          />
                        </div>
                      </div>

                      {/* CPU */}
                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-400 font-medium flex items-center gap-1">
                            <Cpu className="h-3 w-3" /> CPU Load
                          </span>
                          <span className="font-bold text-slate-200">{peakPoint.predicted_cpu_percent}%</span>
                        </div>
                        <div className="w-full bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${peakPoint.predicted_cpu_percent >= 85 ? 'bg-rose-500' : 'bg-blue-500'}`}
                            style={{ width: `${Math.min(100, peakPoint.predicted_cpu_percent)}%` }}
                          />
                        </div>
                      </div>

                      {/* DB Pool */}
                      <div>
                        <div className="flex justify-between text-[11px] mb-1">
                          <span className="text-slate-400 font-medium flex items-center gap-1">
                            <Database className="h-3 w-3" /> DB Pool Saturation
                          </span>
                          <span className="font-bold text-slate-200">{peakPoint.db_pool_saturation_percent}%</span>
                        </div>
                        <div className="w-full bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                          <div
                            className={`h-full ${peakPoint.db_pool_saturation_percent >= 85 ? 'bg-rose-500' : 'bg-emerald-500'}`}
                            style={{ width: `${Math.min(100, peakPoint.db_pool_saturation_percent)}%` }}
                          />
                        </div>
                      </div>

                      {/* Latency */}
                      <div className="pt-2 border-t border-slate-700/50 flex justify-between text-[11px] text-slate-400">
                        <span>Est. Latency:</span>
                        <span className="font-bold text-slate-200">{peakPoint.predicted_latency_ms.toFixed(0)} ms</span>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Diurnal Timeline Table / Trend */}
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <Clock className="h-4 w-4 text-cyan-400" />
              <span>24-Hour Diurnal Student Concurrency & RPS Distribution</span>
            </h3>

            <div className="overflow-x-auto max-h-80 overflow-y-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 font-semibold border-b border-slate-700/60 sticky top-0">
                  <tr>
                    <th className="py-2.5 px-3">Hour</th>
                    <th className="py-2.5 px-3">Active Students</th>
                    <th className="py-2.5 px-3">% Campus</th>
                    <th className="py-2.5 px-3">Total Incoming RPS</th>
                    <th className="py-2.5 px-3">Student Portal</th>
                    <th className="py-2.5 px-3">LMS Service</th>
                    <th className="py-2.5 px-3">Exam Service</th>
                    <th className="py-2.5 px-3">Library</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50">
                  {forecast.timeline.map((pt) => (
                    <tr key={pt.hour} className="hover:bg-slate-700/30 transition-colors">
                      <td className="py-2 px-3 font-semibold text-slate-200">{pt.time_label}</td>
                      <td className="py-2 px-3 text-slate-300 font-medium">{pt.concurrent_students.toLocaleString()}</td>
                      <td className="py-2 px-3 text-slate-400">{pt.active_percentage}%</td>
                      <td className="py-2 px-3 font-bold text-cyan-400">{pt.total_incoming_rps.toFixed(1)}/s</td>
                      <td className="py-2 px-3 text-slate-300">{(pt.service_rps.student_portal || 0).toFixed(1)}/s</td>
                      <td className="py-2 px-3 text-slate-300">{(pt.service_rps.lms || 0).toFixed(1)}/s</td>
                      <td className="py-2 px-3 text-slate-300">{(pt.service_rps.exam_service || 0).toFixed(1)}/s</td>
                      <td className="py-2 px-3 text-slate-300">{(pt.service_rps.library_service || 0).toFixed(1)}/s</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab 2: AegisOps Early Warning Alerts */}
      {activeTab === 'alerts' && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-100">
              Proactive SRE Early-Warning Alerts ({predictiveAlerts.length})
            </h3>
            <span className="text-xs text-slate-400">
              Generated by Digital Twin prior to actual operational degradation
            </span>
          </div>

          {predictiveAlerts.length === 0 ? (
            <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-8 text-center text-xs text-slate-400 space-y-2">
              <ShieldCheck className="h-8 w-8 text-emerald-400 mx-auto" />
              <p className="font-semibold text-slate-200">No active predictive alerts</p>
              <p className="text-slate-400">All services are forecasted to have sufficient headroom.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {predictiveAlerts.map((alt) => {
                const isPending = alt.status === 'PENDING_APPROVAL';
                const isResolved = alt.status === 'RESOLVED';

                return (
                  <div
                    key={alt.id}
                    className={`border rounded-xl p-5 shadow-sm transition-all flex flex-col md:flex-row justify-between gap-6 ${
                      isPending ? 'border-amber-500/40 bg-amber-950/20' : 'bg-slate-800/50 border-slate-700/50'
                    }`}
                  >
                    <div className="space-y-2 max-w-3xl">
                      <div className="flex items-center gap-2">
                        <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">
                          {alt.incident_code}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          alt.severity === 'CRITICAL' ? 'bg-rose-500/10 text-rose-400 border-rose-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}>
                          {alt.severity}
                        </span>
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          isResolved ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        }`}>
                          {alt.status}
                        </span>
                        <span className="text-[10px] text-slate-500">Source: Digital Twin Simulation</span>
                      </div>

                      <h4 className="text-sm font-bold text-slate-100">{alt.title}</h4>
                      <p className="text-xs text-slate-300">{alt.root_cause}</p>

                      <div className="bg-slate-900/60 border border-slate-700/60 rounded-lg p-3 text-xs text-slate-300 space-y-1">
                        <span className="font-bold text-slate-200 block">SRE Proactive Recommendation:</span>
                        <p className="text-slate-400">{alt.recommendation}</p>
                        {alt.action_taken && (
                          <p className="text-emerald-400 font-semibold pt-1">Result: {alt.action_taken}</p>
                        )}
                      </div>
                    </div>

                    {isPending && (
                      <div className="flex flex-col justify-center gap-2 min-w-[180px]">
                        <button
                          onClick={() => handleApproveProactive(alt.id, alt.metrics_summary?.target_replicas || 4)}
                          disabled={actionLoading}
                          className="w-full px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold rounded-lg shadow-sm flex items-center justify-center gap-1.5 transition-all disabled:opacity-50"
                        >
                          <CheckCircle2 className="h-4 w-4" />
                          <span>Approve Pre-Scale</span>
                        </button>
                        <button
                          onClick={() => handleRejectProactive(alt.id)}
                          disabled={actionLoading}
                          className="w-full px-4 py-2 bg-slate-800 border border-slate-700 hover:bg-slate-700 text-slate-300 text-xs font-semibold rounded-lg flex items-center justify-center gap-1.5 transition-all"
                        >
                          <XCircle className="h-4 w-4 text-slate-400" />
                          <span>Defer / Acknowledge</span>
                        </button>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Multi-Scenario Comparison */}
      {activeTab === 'compare' && comparison && (
        <div className="space-y-6">
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 shadow-sm">
            <h3 className="text-xs font-bold text-slate-300 uppercase tracking-wider mb-4 flex items-center gap-2">
              <BarChart2 className="h-4 w-4 text-cyan-400" />
              <span>Multi-Scenario Comparative Matrix</span>
            </h3>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-900/80 text-slate-400 font-semibold border-b border-slate-700/60">
                  <tr>
                    <th className="py-3 px-4">Scenario</th>
                    <th className="py-3 px-4">Academic Event</th>
                    <th className="py-3 px-4">Peak Concurrency</th>
                    <th className="py-3 px-4">Peak Throughput</th>
                    <th className="py-3 px-4">Max CPU Load</th>
                    <th className="py-3 px-4">Max DB Pool Saturation</th>
                    <th className="py-3 px-4">Capacity Alerts</th>
                    <th className="py-3 px-4">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-700/50 font-medium text-slate-300">
                  {comparison.comparison_table.map((row) => (
                    <tr key={row.scenario_name} className="hover:bg-slate-700/30 transition-colors">
                      <td className="py-3 px-4 font-bold text-slate-100">{row.scenario_name}</td>
                      <td className="py-3 px-4">{row.event}</td>
                      <td className="py-3 px-4">{row.peak_concurrent_users.toLocaleString()} users</td>
                      <td className="py-3 px-4 font-bold text-cyan-400">{row.peak_rps} RPS</td>
                      <td className="py-3 px-4">
                        <span className={row.peak_cpu_percent >= 85 ? 'text-rose-400 font-bold' : ''}>
                          {row.peak_cpu_percent}%
                        </span>
                      </td>
                      <td className="py-3 px-4">
                        <span className={row.peak_db_pool_percent >= 85 ? 'text-rose-400 font-bold' : ''}>
                          {row.peak_db_pool_percent}%
                        </span>
                      </td>
                      <td className="py-3 px-4 font-bold">{row.alert_count}</td>
                      <td className="py-3 px-4">
                        <span className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                          row.overall_status === 'HEALTHY' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                          row.overall_status === 'WARNING' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        }`}>
                          {row.overall_status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="mt-5 p-4 rounded-xl bg-slate-900/60 border border-slate-700/60 text-xs text-slate-300 space-y-2">
              <span className="font-bold text-slate-200 block">Digital Twin Comparative Findings:</span>
              <ul className="list-disc pl-5 space-y-1 text-slate-400">
                {comparison.key_findings.map((f, i) => (
                  <li key={i}>{f}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
