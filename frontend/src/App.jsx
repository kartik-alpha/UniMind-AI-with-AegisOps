import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Sidebar from './components/Sidebar';
import DashboardView from './components/DashboardView';
import StudentAssistantView from './components/StudentAssistantView';
import KnowledgeBaseView from './components/KnowledgeBaseView';
import DocumentsView from './components/DocumentsView';
import RAGManagementView from './components/RAGManagementView';
import TicketsView from './components/TicketsView';
import AegisOverviewView from './components/AegisOverviewView';
import ServicesView from './components/ServicesView';
import MonitoringView from './components/MonitoringView';
import MetricsView from './components/MetricsView';
import LogsView from './components/LogsView';
import MLAnomalyDetectionView from './components/MLAnomalyDetectionView';
import IncidentsView from './components/IncidentsView';
import AIDiagnosisView from './components/AIDiagnosisView';
import RemediationView from './components/RemediationView';
import KubernetesView from './components/KubernetesView';
import ChaosSimulationView from './components/ChaosSimulationView';
import DigitalTwinView from './components/DigitalTwinView';
import TenantGovernanceView from './components/TenantGovernanceView';
import ObservabilityView from './components/ObservabilityView';
import { apiFetch } from './apiClient';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [assistantPrompt, setAssistantPrompt] = useState('');
  const [anomalyData, setAnomalyData] = useState(null);
  const [servicesData, setServicesData] = useState(null);
  const [metricsData, setMetricsData] = useState(null);
  const [logsData, setLogsData] = useState(null);
  const [error, setError] = useState(null);

  // Fetch backend API state
  const fetchData = async () => {
    try {
      const [anomRes, svcRes, metRes, logRes] = await Promise.all([
        apiFetch('/api/v1/ml/anomaly-scores'),
        apiFetch('/api/v1/aegisops/services'),
        apiFetch('/api/v1/aegisops/metrics'),
        apiFetch('/api/v1/aegisops/logs'),
      ]);

      if (anomRes.ok) setAnomalyData(await anomRes.json());
      if (svcRes.ok) setServicesData(await svcRes.json());
      if (metRes.ok) setMetricsData(await metRes.json());
      if (logRes.ok) setLogsData(await logRes.json());
      setError(null);
    } catch (e) {
      setError('Unable to reach backend services. Displaying cached data.');
    }
  };

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 15000);
    const handleTenantChange = () => fetchData();
    window.addEventListener('unimind:tenant_change', handleTenantChange);
    return () => {
      clearInterval(interval);
      window.removeEventListener('unimind:tenant_change', handleTenantChange);
    };
  }, []);

  const handleRunDemo = () => {
    setActiveTab('ml_anomaly');
    fetchData();
  };

  const handleAskAssistant = (prompt) => {
    setAssistantPrompt(prompt);
    setActiveTab('assistant');
  };

  return (
    <div className="flex h-screen overflow-hidden bg-[#0B0F19] font-sans text-slate-200">
      {/* Left Sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} onRunDemo={handleRunDemo} />

      {/* Main Right Body */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Header activeTab={activeTab} activeIncidentCount={1} />

        <main className="flex-1 p-6 max-w-7xl w-full mx-auto">
          {/* Error Banner */}
          {error && (
            <div className="mb-4 px-4 py-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-rose-400 text-sm">
              {error}
            </div>
          )}

          {/* UniMind AI Suite */}
          {activeTab === 'dashboard' && (
            <DashboardView
              onNavigate={(tab) => setActiveTab(tab)}
              servicesData={servicesData}
              anomalyData={anomalyData}
            />
          )}
          {activeTab === 'assistant' && (
            <StudentAssistantView initialPrompt={assistantPrompt} />
          )}
          {activeTab === 'knowledge' && (
            <KnowledgeBaseView onAskAssistant={handleAskAssistant} />
          )}
          {activeTab === 'documents' && <DocumentsView />}
          {activeTab === 'rag' && <RAGManagementView />}
          {activeTab === 'tickets' && (
            <TicketsView onAskAssistant={handleAskAssistant} />
          )}

          {/* AegisOps Fleet Suite */}
          {activeTab === 'aegis_overview' && (
            <AegisOverviewView onNavigate={(tab) => setActiveTab(tab)} />
          )}
          {activeTab === 'digital_twin' && (
            <DigitalTwinView onNavigate={(tab) => setActiveTab(tab)} />
          )}
          {activeTab === 'chaos' && (
            <ChaosSimulationView onNavigate={(tab) => setActiveTab(tab)} />
          )}
          {activeTab === 'services' && (
            <ServicesView
              services={servicesData}
              onSelectService={() => setActiveTab('monitoring')}
            />
          )}
          {activeTab === 'monitoring' && <MonitoringView />}
          {activeTab === 'metrics' && <MetricsView metrics={metricsData} />}
          {activeTab === 'logs' && <LogsView logs={logsData} />}
          {activeTab === 'ml_anomaly' && <MLAnomalyDetectionView data={anomalyData} />}
          {activeTab === 'incidents' && (
            <IncidentsView onNavigate={(tab) => setActiveTab(tab)} />
          )}
          {activeTab === 'ai_diagnosis' && (
            <AIDiagnosisView onNavigate={(tab) => setActiveTab(tab)} />
          )}
          {activeTab === 'remediation' && (
            <RemediationView onNavigate={(tab) => setActiveTab(tab)} />
          )}
          {activeTab === 'kubernetes' && <KubernetesView />}
          {activeTab === 'governance' && <TenantGovernanceView />}
          {activeTab === 'observability' && <ObservabilityView />}
        </main>
      </div>
    </div>
  );
}
