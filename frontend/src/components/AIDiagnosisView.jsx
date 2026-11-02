import React, { useState, useEffect } from 'react';
import { Cpu, Zap, BookOpen, CheckCircle, AlertTriangle, ArrowRight, Activity, Sparkles } from 'lucide-react';

export default function AIDiagnosisView({ onNavigate }) {
  const [service, setService] = useState('Exam Service');
  const [diagnosis, setDiagnosis] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchDiagnosis = async (svc) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/v1/aegisops/diagnose/${encodeURIComponent(svc)}`, { method: 'POST' });
      if (res.ok) {
        setDiagnosis(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDiagnosis(service);
  }, [service]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">AEGISOPS</span>
          <h2 className="text-2xl font-bold text-slate-900 mt-0.5">AI Root Cause Diagnosis</h2>
          <p className="text-xs text-slate-500 mt-1">
            Automated correlation of multi-variate telemetry, Prometheus metrics, and SRE incident runbooks.
          </p>
        </div>

        {/* Service Selector */}
        <div className="flex items-center gap-2">
          <label className="text-xs font-bold text-slate-600">Diagnose Service:</label>
          <select
            value={service}
            onChange={(e) => setService(e.target.value)}
            className="bg-white border border-slate-200 text-xs px-3 py-2 rounded-lg font-bold text-slate-800 shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="Exam Service">Exam Service (Active Degraded)</option>
            <option value="LMS">LMS Service</option>
            <option value="Student Portal">Student Portal</option>
            <option value="Library Service">Library Service</option>
          </select>
        </div>
      </div>

      {loading ? (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center space-y-3">
          <Cpu className="h-8 w-8 text-blue-600 animate-spin mx-auto" />
          <h4 className="text-sm font-bold text-slate-700">Evaluating multi-variate telemetry...</h4>
          <p className="text-xs text-slate-400">Matching incident symptoms with knowledge runbooks</p>
        </div>
      ) : diagnosis ? (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main 2-Col Root Cause Analysis */}
          <div className="lg:col-span-2 space-y-5">
            <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
              <div className="flex items-center justify-between pb-3 border-b border-slate-200">
                <span className="text-xs font-bold uppercase tracking-wider text-blue-600 flex items-center gap-1.5">
                  <Sparkles className="h-4 w-4" /> Root Cause Assessment
                </span>
                <span className="text-xs font-mono font-bold bg-blue-50 text-blue-700 px-2.5 py-1 rounded-full border border-blue-200">
                  Confidence: {Math.round((diagnosis.confidence_score || 0.88) * 100)}%
                </span>
              </div>

              <div>
                <h3 className="text-base font-bold text-slate-900 leading-snug">
                  {diagnosis.suspected_root_cause}
                </h3>
              </div>

              <div className="p-4 bg-slate-50 border border-slate-200 rounded-xl space-y-2">
                <span className="text-xs font-bold text-slate-700 block">Telemetry Evidence:</span>
                <p className="text-xs font-mono text-slate-600 leading-relaxed bg-white p-3 rounded border border-slate-200">
                  {diagnosis.evidence}
                </p>
              </div>

              {/* Matched Runbook */}
              <div className="p-4 bg-amber-50/50 border border-amber-200 rounded-xl space-y-2">
                <span className="text-xs font-bold text-amber-900 flex items-center gap-1.5">
                  <BookOpen className="h-4 w-4 text-amber-700" /> Matched SRE Runbook: {diagnosis.matched_runbook_title}
                </span>
                <p className="text-xs text-slate-700 font-mono whitespace-pre-wrap leading-relaxed">
                  {diagnosis.runbook_summary}
                </p>
              </div>
            </div>
          </div>

          {/* Right Action Column */}
          <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col justify-between space-y-6">
            <div className="space-y-4">
              <span className="text-xs font-bold text-slate-500 uppercase tracking-wider block">
                Prescribed Remediation
              </span>

              <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-xl space-y-1">
                <span className="text-[11px] font-bold text-emerald-800 uppercase block">Action Plan</span>
                <p className="text-xs font-bold text-slate-900">
                  {diagnosis.recommended_remediation}
                </p>
              </div>

              <div className="space-y-2 text-xs text-slate-600 leading-relaxed">
                <div className="flex items-start gap-2">
                  <span className="font-bold text-blue-600">1.</span>
                  <span>Initiate graceful pod termination on degraded node.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-blue-600">2.</span>
                  <span>Scale deployment replicas from 2 to 4 pods.</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="font-bold text-blue-600">3.</span>
                  <span>Verify connection pool handles drop below threshold.</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => onNavigate('remediation')}
              className="w-full bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs py-3 px-4 rounded-xl shadow-lg transition-all flex items-center justify-center gap-2"
            >
              <Zap className="h-4 w-4" />
              <span>Proceed to Controlled Remediation</span>
              <ArrowRight className="h-4 w-4 ml-1" />
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
