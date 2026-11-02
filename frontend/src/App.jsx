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

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [assistantPrompt, setAssistantPrompt] = useState('');
  const [anomalyData, setAnomalyData] = useState(null);
  const [servicesData, setServicesData] = useState(null);
  const [metricsData, setMetricsData] = useState(null);
  const [logsData, setLogsData] = useState(null);

  // Fetch backend API state
  const fetchData = async () => {
    try {
      const [anomRes, svcRes, metRes, logRes] = await Promise.all([
        fetch('/api/v1/ml/anomaly-scores'),
        fetch('/api/v1/aegisops/services'),
        fetch('/api/v1/aegisops/metrics'),
        fetch('/api/v1/aegisops/logs'),
      ]);

      if (anomRes.ok) setAnomalyData(await anomRes.json());
      if (svcRes.ok) setServicesData(await svcRes.json());
      if (metRes.ok) setMetricsData(await metRes.json());
      if (logRes.ok) setLogsData(await logRes.json());
    } catch (e) {
      // Offline fallback state matching screenshots
    }
  };

  useEffect(() => {
    fetchData();
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
    <div className="flex h-screen overflow-hidden bg-slate-50 font-sans text-slate-800">
      {/* Left Sidebar */}
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} onRunDemo={handleRunDemo} />

      {/* Main Right Body */}
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Header activeTab={activeTab} activeIncidentCount={1} />

        <main className="flex-1 p-8 max-w-7xl w-full mx-auto">
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
        </main>
      </div>
    </div>
  );
}
