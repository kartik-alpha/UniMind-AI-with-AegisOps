import React from 'react';

export default function ServicesView({ services, onSelectService }) {
  const defaultServices = [
    {
      name: 'LMS',
      status: 'Healthy',
      cpu: '34%',
      memory: '48%',
      latency: '142 ms',
      uptime: '99.98%',
      request_rate: '412/s',
      error_rate: '0.2%',
      replicas: 3,
      last_incident: '12 days ago',
      is_critical: false,
    },
    {
      name: 'Student Portal',
      status: 'Healthy',
      cpu: '27%',
      memory: '41%',
      latency: '118 ms',
      uptime: '99.95%',
      request_rate: '288/s',
      error_rate: '0.1%',
      replicas: 2,
      last_incident: '21 days ago',
      is_critical: false,
    },
    {
      name: 'Exam Service',
      status: 'Critical',
      cpu: '92%',
      memory: '81%',
      latency: '1800 ms',
      uptime: '99.41%',
      request_rate: '964/s',
      error_rate: '14%',
      replicas: 2,
      last_incident: 'Active',
      is_critical: true,
    },
    {
      name: 'Library Service',
      status: 'Healthy',
      cpu: '21%',
      memory: '38%',
      latency: '105 ms',
      uptime: '99.99%',
      request_rate: '96/s',
      error_rate: '0%',
      replicas: 2,
      last_incident: '6 days ago',
      is_critical: false,
    },
  ];

  const serviceList = services || defaultServices;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Page Header */}
      <div>
        <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">AEGISOPS</span>
        <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Services</h2>
        <p className="text-xs text-slate-400 mt-1">Click a service to open detailed monitoring.</p>
      </div>

      {/* Services Grid (4 Cards) */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
        {serviceList.map((service) => {
          const isCritical = service.status.toLowerCase() === 'critical' || service.is_critical;
          return (
            <div
              key={service.name}
              onClick={() => onSelectService && onSelectService(service.name)}
              className={`rounded-xl p-5 border transition-all cursor-pointer shadow-sm hover:shadow-md ${
                isCritical
                  ? 'bg-rose-950/20 border-rose-500/40 ring-1 ring-rose-500/20 hover:border-rose-500/60'
                  : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
              }`}
            >
              {/* Card Header: Service Name + Status Badge */}
              <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-slate-100 text-base">{service.name}</h3>
                <span
                  className={`inline-flex items-center gap-1.5 text-xs font-bold px-2.5 py-0.5 rounded-full border ${
                    isCritical
                      ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                      : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  }`}
                >
                  <span
                    className={`h-1.5 w-1.5 rounded-full ${isCritical ? 'bg-rose-400 animate-ping' : 'bg-emerald-400'}`}
                  ></span>
                  {service.status}
                </span>
              </div>

              {/* Metrics Grid */}
              <div className="space-y-2.5 text-xs">
                <div className="flex justify-between items-center">
                  <span className="text-slate-400">CPU</span>
                  <span className={`font-semibold ${isCritical ? 'text-rose-400 font-bold' : 'text-slate-200'}`}>
                    {service.cpu}
                  </span>
                </div>
                <div className="w-full bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${isCritical ? 'bg-rose-500' : 'bg-emerald-500'}`}
                    style={{ width: service.cpu }}
                  ></div>
                </div>

                <div className="flex justify-between items-center pt-1">
                  <span className="text-slate-400">Memory</span>
                  <span className="font-semibold text-slate-200">{service.memory}</span>
                </div>
                <div className="w-full bg-slate-700/60 h-1.5 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full ${isCritical ? 'bg-amber-500' : 'bg-emerald-500'}`}
                    style={{ width: service.memory }}
                  ></div>
                </div>

                <div className="flex justify-between items-center pt-1">
                  <span className="text-slate-400">Latency</span>
                  <span className={`font-semibold ${isCritical ? 'text-rose-400 font-bold' : 'text-slate-200'}`}>
                    {service.latency}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Uptime</span>
                  <span className="font-semibold text-slate-200">{service.uptime}</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Request rate</span>
                  <span className="font-semibold text-slate-200">{service.request_rate}</span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Error rate</span>
                  <span className={`font-semibold ${isCritical ? 'text-rose-400 font-bold' : 'text-slate-200'}`}>
                    {service.error_rate}
                  </span>
                </div>

                <div className="flex justify-between items-center">
                  <span className="text-slate-400">Replicas</span>
                  <span className="font-semibold text-slate-200">{service.replicas}</span>
                </div>

                <div className="flex justify-between items-center pt-1 border-t border-slate-700/50">
                  <span className="text-slate-400">Last incident</span>
                  <span className={`font-medium ${isCritical ? 'text-rose-400 font-bold' : 'text-slate-300'}`}>
                    {service.last_incident}
                  </span>
                </div>
              </div>

              {/* Mini Sparkline Chart SVG at bottom */}
              <div className="mt-4 pt-2 border-t border-slate-700/50">
                <svg className="w-full h-8 overflow-visible" viewBox="0 0 100 20">
                  <path
                    d={
                      isCritical
                        ? 'M 0,15 Q 25,12 50,14 T 75,5 T 100,2'
                        : 'M 0,12 Q 25,10 50,11 T 75,10 T 100,11'
                    }
                    fill="none"
                    stroke={isCritical ? '#f43f5e' : '#10b981'}
                    strokeWidth="2"
                  />
                </svg>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
