import React from 'react';
import { AlertTriangle, CheckCircle2, Info } from 'lucide-react';

export default function MLAnomalyDetectionView({ data }) {
  const modelInfo = data?.model_info || {
    name: 'Isolation Forest',
    status: 'Active',
    features: ['CPU', 'Memory', 'Requests', 'Latency', 'Errors'],
    threshold: 0.70,
    trained_on: '14 days of normal traffic',
  };

  const services = data?.services || [
    { service: 'Exam Service', anomaly_score: 0.91, is_anomaly: true, status_label: 'HIGH ANOMALY' },
    { service: 'LMS', anomaly_score: 0.12, is_anomaly: false, status_label: 'NORMAL' },
    { service: 'Student Portal', anomaly_score: 0.09, is_anomaly: false, status_label: 'NORMAL' },
    { service: 'Library Service', anomaly_score: 0.07, is_anomaly: false, status_label: 'NORMAL' },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">AEGISOPS</span>
        <h2 className="text-2xl font-bold text-slate-900 mt-0.5">Anomaly Detection</h2>
      </div>

      {/* Top Grid: Model Card + Anomaly Scores Card */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Model Card (Left - 5 Cols) */}
        <div className="lg:col-span-5 bg-white border border-slate-200 rounded-xl p-6 shadow-sm flex flex-col justify-between">
          <h3 className="font-semibold text-slate-800 text-sm mb-4">Model</h3>
          
          <div className="space-y-4 text-sm">
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500">Model</span>
              <span className="font-semibold text-slate-800">{modelInfo.name}</span>
            </div>
            
            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500">Status</span>
              <span className="inline-flex items-center gap-1.5 bg-emerald-50 text-emerald-700 text-xs font-semibold px-2.5 py-1 rounded-full border border-emerald-200">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-500"></span>
                {modelInfo.status}
              </span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500">Features</span>
              <span className="font-medium text-slate-700 text-xs">{modelInfo.features.join(', ')}</span>
            </div>

            <div className="flex justify-between items-center py-1 border-b border-slate-100">
              <span className="text-slate-500">Threshold</span>
              <span className="font-semibold text-slate-800">{modelInfo.threshold.toFixed(2)}</span>
            </div>

            <div className="flex justify-between items-center py-1">
              <span className="text-slate-500">Trained on</span>
              <span className="font-medium text-slate-700">{modelInfo.trained_on}</span>
            </div>
          </div>
        </div>

        {/* Anomaly Scores Card (Right - 7 Cols) */}
        <div className="lg:col-span-7 bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-5">
          <h3 className="font-semibold text-slate-800 text-sm">Anomaly scores</h3>

          <div className="space-y-4">
            {services.map((item) => (
              <div key={item.service} className="space-y-1.5">
                <div className="flex justify-between items-center text-xs font-semibold">
                  <span className="text-slate-800 font-bold">{item.service}</span>
                  <div className="flex items-center gap-2">
                    <span className="text-slate-600 font-mono font-bold">{item.anomaly_score.toFixed(2)}</span>
                    {item.is_anomaly && (
                      <span className="bg-red-50 text-red-600 text-[10px] font-extrabold px-2 py-0.5 rounded uppercase tracking-wider border border-red-200">
                        • HIGH ANOMALY
                      </span>
                    )}
                  </div>
                </div>
                {/* Score Progress Bar */}
                <div className="w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full transition-all duration-500 rounded-full ${
                      item.is_anomaly ? 'bg-red-500' : 'bg-emerald-500'
                    }`}
                    style={{ width: `${Math.min(100, item.anomaly_score * 100)}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>

          {/* Alert Message Box */}
          <div className="bg-red-50/80 border border-red-200 rounded-lg p-3.5 text-xs text-red-700 flex items-start gap-2.5 mt-4">
            <AlertTriangle className="h-4 w-4 text-red-600 shrink-0 mt-0.5" />
            <span>
              <strong>Exam Service:</strong> current service behavior significantly differs from the learned normal operating pattern.
            </span>
          </div>
        </div>
      </div>

      {/* Bottom Explanation Card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="font-semibold text-slate-800 text-sm">Anomaly Detection vs Failure Risk Prediction</h3>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs leading-relaxed text-slate-600">
          <div>
            <h4 className="font-bold text-slate-800 text-xs mb-1">Anomaly Detection (implemented)</h4>
            <p>
              Answers "is this behaviour unusual right now?" by comparing live metrics to learned normal patterns. Unsupervised — no labelled failures needed.
            </p>
          </div>
          <div>
            <h4 className="font-bold text-slate-800 text-xs mb-1">Failure Risk Prediction (estimate)</h4>
            <p>
              Estimates the likelihood of degradation soon. It is probabilistic and can be wrong — AegisOps never claims perfect prediction, and always shows evidence.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
