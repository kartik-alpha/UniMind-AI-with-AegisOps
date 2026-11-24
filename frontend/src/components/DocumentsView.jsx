import React, { useState, useEffect } from 'react';
import { FileText, Upload, Trash2, Database, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';
import { apiFetch, getTenantId, parseApiError } from '../apiClient';

export default function DocumentsView() {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [title, setTitle] = useState('');
  const [category, setCategory] = useState('academic');
  const [file, setFile] = useState(null);
  const [statusMsg, setStatusMsg] = useState(null);

  const fetchDocs = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/documents');
      if (res.ok) {
        setDocuments(await res.json());
      } else {
        const prob = await parseApiError(res);
        setStatusMsg({ type: 'error', text: prob.detail });
      }
    } catch (e) {
      console.error(e);
      setStatusMsg({ type: 'error', text: 'Network connection failed.' });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
    const handleTenantChange = () => fetchDocs();
    window.addEventListener('unimind:tenant_change', handleTenantChange);
    return () => window.removeEventListener('unimind:tenant_change', handleTenantChange);
  }, []);

  const handleUpload = async (e) => {
    e.preventDefault();
    if (!file || !title) return;

    const formData = new FormData();
    formData.append('title', title);
    formData.append('category', category);
    formData.append('file', file);

    try {
      setStatusMsg({ type: 'info', text: 'Uploading document...' });
      const res = await apiFetch('/api/v1/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const doc = await res.json();
        setStatusMsg({
          type: 'success',
          text: `Document '${doc.title}' uploaded successfully! Auto-ingesting into ChromaDB...`,
        });
        setTitle('');
        setFile(null);
        await handleIngest(doc.id);
        fetchDocs();
      } else {
        const prob = await parseApiError(res);
        setStatusMsg({ type: 'error', text: `Upload failed: ${prob.detail}` });
      }
    } catch (err) {
      setStatusMsg({ type: 'error', text: `Network error during upload: ${err.message}` });
    }
  };

  const handleIngest = async (docId) => {
    try {
      const res = await apiFetch(`/api/v1/rag/ingest/${docId}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setStatusMsg({
          type: 'success',
          text: `Ingested ${data.chunks_indexed} chunks into ChromaDB vector store!`,
        });
        fetchDocs();
      } else {
        const prob = await parseApiError(res);
        setStatusMsg({ type: 'error', text: `Ingest failed: ${prob.detail}` });
      }
    } catch (err) {
      setStatusMsg({ type: 'error', text: 'Ingest error.' });
    }
  };

  const handleDelete = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      const res = await apiFetch(`/api/v1/documents/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        setStatusMsg({ type: 'info', text: 'Document deleted.' });
        fetchDocs();
      } else {
        const prob = await parseApiError(res);
        setStatusMsg({ type: 'error', text: `Delete failed: ${prob.detail}` });
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">UNIMIND AI</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Documents & Vector Ingestion</h2>
          <p className="text-xs text-slate-400 mt-1">
            Upload institutional handbooks, syllabus guidelines, and policies to index into ChromaDB.
          </p>
        </div>

        <button
          onClick={fetchDocs}
          className="px-3 py-2 bg-slate-800 border border-slate-700 hover:bg-slate-700/80 text-slate-300 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-all"
        >
          <RefreshCw className={`h-4 w-4 text-cyan-400 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {statusMsg && (
        <div
          className={`p-3 rounded-lg text-xs font-semibold flex items-center gap-2 border ${
            statusMsg.type === 'success'
              ? 'bg-emerald-950/20 text-emerald-300 border-emerald-500/30'
              : statusMsg.type === 'error'
              ? 'bg-rose-950/20 text-rose-300 border-rose-500/30'
              : 'bg-cyan-950/20 text-cyan-300 border-cyan-500/30'
          }`}
        >
          {statusMsg.type === 'success' ? (
            <CheckCircle className="h-4 w-4 text-emerald-400 shrink-0" />
          ) : (
            <AlertCircle className="h-4 w-4 text-rose-400 shrink-0" />
          )}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Upload Box */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 shadow-sm">
        <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Upload className="h-4 w-4 text-cyan-400" /> Upload New University Document
        </h3>

        <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2 space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase">Document Title</label>
            <input
              type="text"
              placeholder="e.g. Hostel Guidelines 2026"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full bg-slate-800 border border-slate-700 text-xs px-3 py-2 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-xs px-3 py-2 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="academic">Academic</option>
              <option value="attendance">Attendance</option>
              <option value="hostel">Hostel</option>
              <option value="it">IT Support</option>
              <option value="general">General</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase">Select File</label>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files[0])}
              required
              className="w-full text-xs text-slate-400 file:mr-2 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-slate-700 file:text-cyan-300 hover:file:bg-slate-600 cursor-pointer"
            />
          </div>

          <div className="md:col-span-4 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs px-5 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <Upload className="h-4 w-4" />
              <span>Upload & Ingest to RAG</span>
            </button>
          </div>
        </form>
      </div>

      {/* Documents Table */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-700/60 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-100">Indexed Knowledge Files ({documents.length})</h3>
          <span className="text-xs text-slate-400">ChromaDB Store: university_knowledge_base</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-900/80 text-slate-400 font-bold uppercase tracking-wider border-b border-slate-700/60">
              <tr>
                <th className="py-2.5 px-4">Title</th>
                <th className="py-2.5 px-4">Category</th>
                <th className="py-2.5 px-4">Filename</th>
                <th className="py-2.5 px-4">Chunks</th>
                <th className="py-2.5 px-4">RAG Status</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-700/50">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    No documents found. Upload a policy above to begin.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-700/30 transition-colors">
                    <td className="py-3 px-4 font-semibold text-slate-200 flex items-center gap-2">
                      <FileText className="h-4 w-4 text-cyan-400 shrink-0" />
                      <span>{doc.title}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-800 text-slate-300 border border-slate-700 uppercase">
                        {doc.category}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">{doc.filename}</td>
                    <td className="py-3 px-4 font-mono font-bold text-cyan-400">
                      {doc.chunk_count || 0}
                    </td>
                    <td className="py-3 px-4">
                      {doc.chunk_count > 0 ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-400">
                          <CheckCircle className="h-3.5 w-3.5" /> Indexed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-400">
                          <AlertCircle className="h-3.5 w-3.5" /> Ready to Ingest
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleIngest(doc.id)}
                        className="px-2.5 py-1 rounded bg-cyan-500/10 text-cyan-300 hover:bg-cyan-600 hover:text-white font-semibold text-[11px] transition-colors border border-cyan-500/20"
                      >
                        Re-Ingest
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="px-2.5 py-1 rounded bg-rose-500/10 text-rose-400 hover:bg-rose-600 hover:text-white font-semibold text-[11px] transition-colors border border-rose-500/20"
                      >
                        <Trash2 className="h-3.5 w-3.5 inline" />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
