import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  HardDrive,
  Cpu,
  Gauge,
  Download,
  Save,
  AlertTriangle,
  CheckCircle,
  RefreshCw,
  FileText,
  Sliders,
  Building,
  Key,
  Lock,
  Link2,
} from 'lucide-react';
import { apiFetch, getTenantId, parseApiError } from '../apiClient';

export default function TenantGovernanceView() {
  const [governanceData, setGovernanceData] = useState(null);
  const [chainVerification, setChainVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [verifyingChain, setVerifyingChain] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [actionMessage, setActionMessage] = useState(null);

  // Form states for governance controls
  const [storageQuotaMB, setStorageQuotaMB] = useState(50);
  const [rateLimitPerMin, setRateLimitPerMin] = useState(120);
  const [monthlyTokenBudget, setMonthlyTokenBudget] = useState(500000);
  const [exportFormat, setExportFormat] = useState('jsonl');

  const fetchGovernanceStatus = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/governance/status');
      if (res.ok) {
        const data = await res.json();
        setGovernanceData(data);
        if (data.storage?.quota_bytes) {
          setStorageQuotaMB(Math.round(data.storage.quota_bytes / (1024 * 1024)));
        }
        if (data.rate_limit?.requests_per_minute) {
          setRateLimitPerMin(data.rate_limit.requests_per_minute);
        }
        if (data.tokens?.budget) {
          setMonthlyTokenBudget(data.tokens.budget);
        }
      }
    } catch (e) {
      console.error('Failed to load governance status', e);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyAuditChain = async () => {
    setVerifyingChain(true);
    setActionMessage(null);
    try {
      const res = await apiFetch('/api/v1/governance/audit/verify-chain');
      if (res.ok) {
        const result = await res.json();
        setChainVerification(result);
        if (result.is_valid) {
          setActionMessage({
            type: 'success',
            text: `Cryptographic Audit Chain 100% Intact. Verified ${result.total_records} chained records with SHA-256 + HMAC signatures.`,
          });
        } else {
          setActionMessage({
            type: 'error',
            text: `Tamper Warning: Audit chain violation detected at record #${result.tampered_record_id}. (${result.reason})`,
          });
        }
      } else {
        const prob = await parseApiError(res);
        setActionMessage({ type: 'error', text: `Audit verification failed: ${prob.detail}` });
      }
    } catch (e) {
      setActionMessage({ type: 'error', text: `Network error verifying audit chain: ${e.message}` });
    } finally {
      setVerifyingChain(false);
    }
  };

  const handleBackfillChain = async () => {
    try {
      const res = await apiFetch('/api/v1/governance/audit/backfill-chain', { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setActionMessage({
          type: 'success',
          text: `Backfilled cryptographic hash chain for ${data.records_backfilled} audit records.`,
        });
        await handleVerifyAuditChain();
      } else {
        const prob = await parseApiError(res);
        setActionMessage({ type: 'error', text: `Backfill failed: ${prob.detail}` });
      }
    } catch (e) {
      setActionMessage({ type: 'error', text: `Network error: ${e.message}` });
    }
  };

  useEffect(() => {
    fetchGovernanceStatus();
    handleVerifyAuditChain();
    const handleTenantChange = () => {
      fetchGovernanceStatus();
      handleVerifyAuditChain();
    };
    window.addEventListener('unimind:tenant_change', handleTenantChange);
    return () => window.removeEventListener('unimind:tenant_change', handleTenantChange);
  }, []);

  const handleSaveControls = async (e) => {
    e.preventDefault();
    setUpdating(true);
    setActionMessage(null);
    try {
      const payload = {
        storage_quota_bytes: storageQuotaMB * 1024 * 1024,
        rate_limit_per_min: parseInt(rateLimitPerMin, 10),
        monthly_token_budget: parseInt(monthlyTokenBudget, 10),
      };
      const res = await apiFetch('/api/v1/governance/controls', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      if (res.ok) {
        const updated = await res.json();
        setGovernanceData(updated);
        setActionMessage({ type: 'success', text: 'Tenant governance controls successfully updated!' });
      } else {
        const prob = await parseApiError(res);
        setActionMessage({ type: 'error', text: `Failed to update governance controls: ${prob.detail}` });
      }
    } catch (e) {
      setActionMessage({ type: 'error', text: 'Network error updating controls.' });
    } finally {
      setUpdating(false);
    }
  };

  const handleExportAuditLogs = async () => {
    setExporting(true);
    try {
      const res = await apiFetch(`/api/v1/governance/audit/export?format=${exportFormat}`);
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `tenant_audit_export.${exportFormat}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        window.URL.revokeObjectURL(url);
      }
    } catch (e) {
      console.error('Audit export failed', e);
    } finally {
      setExporting(false);
    }
  };

  if (loading && !governanceData) {
    return (
      <div className="flex items-center justify-center h-64">
        <RefreshCw className="h-8 w-8 animate-spin text-cyan-400" />
      </div>
    );
  }

  const storageUsedMB = (governanceData?.storage?.used_bytes / (1024 * 1024)).toFixed(2);
  const storageTotalMB = (governanceData?.storage?.quota_bytes / (1024 * 1024)).toFixed(0);
  const storagePct = governanceData?.storage?.used_percent || 0;

  const tokensUsed = governanceData?.tokens?.total_tokens || 0;
  const tokenBudget = governanceData?.tokens?.budget || 500000;
  const tokenPct = governanceData?.tokens?.budget_used_percent || 0;

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Top Banner */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm">
        <div>
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-lg bg-cyan-500/10 border border-cyan-500/20 flex items-center justify-center text-cyan-400">
              <ShieldCheck className="h-6 w-6" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-slate-100">Tenant Governance & Quotas</h2>
              <p className="text-sm text-slate-400">
                Enterprise multi-tenant resource boundaries, rate limits, token accounting, and audit integrity.
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchGovernanceStatus}
            className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-slate-300 bg-slate-800 hover:bg-slate-700/80 rounded-lg border border-slate-700 transition-colors"
          >
            <RefreshCw className="h-4 w-4 text-cyan-400" /> Refresh
          </button>
        </div>
      </div>

      {actionMessage && (
        <div
          className={`p-4 rounded-xl border text-sm flex items-center gap-3 ${
            actionMessage.type === 'success'
              ? 'bg-emerald-950/20 text-emerald-300 border-emerald-500/30'
              : 'bg-rose-950/20 text-rose-300 border-rose-500/30'
          }`}
        >
          {actionMessage.type === 'success' ? (
            <CheckCircle className="h-5 w-5 text-emerald-400 shrink-0" />
          ) : (
            <AlertTriangle className="h-5 w-5 text-rose-400 shrink-0" />
          )}
          <span>{actionMessage.text}</span>
        </div>
      )}

      {/* Overview Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Storage Quota Card */}
        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider">Document Storage</span>
              <HardDrive className="h-5 w-5 text-cyan-400" />
            </div>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-2xl font-bold text-slate-100">{storageUsedMB} MB</span>
              <span className="text-sm text-slate-400">of {storageTotalMB} MB</span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              {governanceData?.storage?.total_files || 0} documents indexed in tenant repository
            </p>
          </div>
          <div>
            <div className="w-full bg-slate-700/60 rounded-full h-2 mb-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  storagePct > 80 ? 'bg-amber-500' : 'bg-cyan-500'
                }`}
                style={{ width: `${Math.min(100, storagePct)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              <span>{storagePct}% Consumed</span>
              <span>HTTP 413 on Overflow</span>
            </div>
          </div>
        </div>

        {/* Token Accounting Card */}
        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider">Monthly LLM Tokens</span>
              <Cpu className="h-5 w-5 text-purple-400" />
            </div>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-2xl font-bold text-slate-100">{tokensUsed.toLocaleString()}</span>
              <span className="text-sm text-slate-400">/ {tokenBudget.toLocaleString()}</span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Prompt: {governanceData?.tokens?.prompt_tokens?.toLocaleString() || 0} | Completion:{' '}
              {governanceData?.tokens?.completion_tokens?.toLocaleString() || 0}
            </p>
          </div>
          <div>
            <div className="w-full bg-slate-700/60 rounded-full h-2 mb-2 overflow-hidden">
              <div
                className={`h-full transition-all duration-500 ${
                  tokenPct > 80 ? 'bg-rose-500' : 'bg-purple-500'
                }`}
                style={{ width: `${Math.min(100, tokenPct)}%` }}
              />
            </div>
            <div className="flex justify-between text-xs text-slate-400">
              <span>{tokenPct}% Budget Used</span>
              <span>{governanceData?.tokens?.is_warning ? 'Warning (>=80%)' : 'Nominal'}</span>
            </div>
          </div>
        </div>

        {/* Rate Limiting Card */}
        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between text-slate-400 mb-2">
              <span className="text-xs font-bold uppercase tracking-wider">API Rate Limit</span>
              <Gauge className="h-5 w-5 text-emerald-400" />
            </div>
            <div className="flex items-baseline gap-2 mb-1">
              <span className="text-2xl font-bold text-slate-100">
                {governanceData?.rate_limit?.requests_per_minute || 120}
              </span>
              <span className="text-sm text-slate-400">req / min</span>
            </div>
            <p className="text-xs text-slate-400 mb-4">
              Sliding-window token bucket (Window: 60 seconds)
            </p>
          </div>
          <div className="p-2.5 bg-slate-900/60 rounded-lg border border-slate-700/60 text-xs text-slate-400">
            <span className="font-semibold text-slate-300">Throttling:</span> Returns HTTP 429 with Retry-After header upon threshold breach.
          </div>
        </div>
      </div>

      {/* Cryptographic Audit Chain Verification Card */}
      <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-3 border-b border-slate-700/60">
          <div className="flex items-center gap-2.5">
            <Link2 className="h-5 w-5 text-cyan-400" />
            <h3 className="text-base font-bold text-slate-100">
              Cryptographic Tamper-Evident Audit Chain
            </h3>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={handleVerifyAuditChain}
              disabled={verifyingChain}
              className="px-3 py-1.5 bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs rounded-lg shadow-sm transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${verifyingChain ? 'animate-spin' : ''}`} />
              <span>Verify Chain Integrity</span>
            </button>
            <button
              onClick={handleBackfillChain}
              className="px-3 py-1.5 bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold text-xs rounded-lg transition-all"
            >
              Backfill Signatures
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-xs">
          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/60">
            <span className="text-slate-400 block mb-1">Chain Status</span>
            {chainVerification?.is_valid ? (
              <span className="text-emerald-400 font-bold flex items-center gap-1">
                <CheckCircle className="h-4 w-4" /> 100% Intact & Verified
              </span>
            ) : chainVerification?.is_valid === false ? (
              <span className="text-rose-400 font-bold flex items-center gap-1">
                <AlertTriangle className="h-4 w-4" /> Tamper Violation
              </span>
            ) : (
              <span className="text-slate-400">Pending Verification</span>
            )}
          </div>

          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/60">
            <span className="text-slate-400 block mb-1">Chained Records</span>
            <span className="font-mono font-bold text-slate-200 text-sm">
              {chainVerification?.total_records ?? '--'} logs
            </span>
          </div>

          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/60">
            <span className="text-slate-400 block mb-1">Hashing Standard</span>
            <span className="font-mono font-bold text-cyan-400">SHA-256 + HMAC-SHA256</span>
          </div>

          <div className="p-3 bg-slate-900/60 rounded-lg border border-slate-700/60">
            <span className="text-slate-400 block mb-1">Last Cryptographic Proof</span>
            <span className="text-slate-300 font-mono text-[11px]">
              {chainVerification?.verified_at ? new Date(chainVerification.verified_at).toLocaleTimeString() : 'Just now'}
            </span>
          </div>
        </div>
      </div>

      {/* Governance Controls & Audit Export */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Controls Form */}
        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm">
          <div className="flex items-center gap-2 mb-4 text-slate-100 font-bold text-base">
            <Sliders className="h-5 w-5 text-cyan-400" />
            <h3>Configure Tenant Boundaries (Admin)</h3>
          </div>
          <form onSubmit={handleSaveControls} className="space-y-4">
            <div>
              <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                Storage Quota (MB)
              </label>
              <input
                type="number"
                min="10"
                max="5000"
                value={storageQuotaMB}
                onChange={(e) => setStorageQuotaMB(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <span className="text-[11px] text-slate-500">Enforces hard ceiling on document uploads</span>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                Rate Limit (Requests / Minute)
              </label>
              <input
                type="number"
                min="10"
                max="2000"
                value={rateLimitPerMin}
                onChange={(e) => setRateLimitPerMin(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <span className="text-[11px] text-slate-500">Per-tenant IP rate throttling limit</span>
            </div>

            <div>
              <label className="block text-xs font-bold uppercase text-slate-300 mb-1">
                Monthly LLM Token Budget
              </label>
              <input
                type="number"
                min="50000"
                max="50000000"
                step="50000"
                value={monthlyTokenBudget}
                onChange={(e) => setMonthlyTokenBudget(e.target.value)}
                className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
              />
              <span className="text-[11px] text-slate-500">
                Warning threshold triggers automatically at 80% consumption
              </span>
            </div>

            <button
              type="submit"
              disabled={updating}
              className="w-full py-2.5 bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs rounded-lg transition-colors flex items-center justify-center gap-2 shadow-sm disabled:opacity-50"
            >
              <Save className="h-4 w-4" />
              <span>{updating ? 'Saving Changes...' : 'Save Tenant Boundaries'}</span>
            </button>
          </form>
        </div>

        {/* Audit Export & Compliance */}
        <div className="bg-slate-800/50 p-6 rounded-xl border border-slate-700/50 shadow-sm flex flex-col justify-between">
          <div className="space-y-4">
            <div className="flex items-center gap-2 text-slate-100 font-bold text-base">
              <FileText className="h-5 w-5 text-purple-400" />
              <h3>Audit Log & Compliance Export</h3>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed">
              Export tenant-isolated compliance logs for external security auditors. All exported records
              contain cryptographic previous_hash linkages and HMAC signatures.
            </p>

            <div className="space-y-2">
              <label className="block text-xs font-bold uppercase text-slate-300">Export Format</label>
              <div className="flex gap-4">
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="radio"
                    name="exportFormat"
                    value="jsonl"
                    checked={exportFormat === 'jsonl'}
                    onChange={() => setExportFormat('jsonl')}
                    className="text-cyan-500 focus:ring-cyan-500"
                  />
                  <span>JSONL (SIEM Compatible)</span>
                </label>
                <label className="flex items-center gap-2 text-xs text-slate-300 cursor-pointer">
                  <input
                    type="radio"
                    name="exportFormat"
                    value="csv"
                    checked={exportFormat === 'csv'}
                    onChange={() => setExportFormat('csv')}
                    className="text-cyan-500 focus:ring-cyan-500"
                  />
                  <span>CSV Spreadsheet</span>
                </label>
              </div>
            </div>
          </div>

          <div className="pt-6">
            <button
              onClick={handleExportAuditLogs}
              disabled={exporting}
              className="w-full py-2.5 bg-slate-700 hover:bg-slate-600 text-slate-200 font-bold text-xs rounded-lg transition-colors flex items-center justify-center gap-2 border border-slate-600 shadow-sm disabled:opacity-50"
            >
              <Download className="h-4 w-4" />
              <span>{exporting ? 'Generating Compliant Export...' : 'Download Tamper-Evident Audit Archive'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
