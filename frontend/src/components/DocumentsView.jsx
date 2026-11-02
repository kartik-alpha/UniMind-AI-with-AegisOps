import React, { useState, useEffect } from 'react';
import { FileText, Upload, Trash2, Database, CheckCircle, AlertCircle, RefreshCw } from 'lucide-react';

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
      const res = await fetch('/api/v1/documents');
      if (res.ok) {
        setDocuments(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocs();
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
      const res = await fetch('/api/v1/documents/upload', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        const doc = await res.json();
        setStatusMsg({ type: 'success', text: `Document '${doc.title}' uploaded successfully! Auto-ingesting into ChromaDB...` });
        setTitle('');
        setFile(null);
        // Trigger auto ingest
        await handleIngest(doc.id);
        fetchDocs();
      } else {
        setStatusMsg({ type: 'error', text: 'Upload failed. Please check file format.' });
      }
    } catch (err) {
      setStatusMsg({ type: 'error', text: 'Network error during upload.' });
    }
  };

  const handleIngest = async (docId) => {
    try {
      const res = await fetch(`/api/v1/rag/ingest/${docId}`, { method: 'POST' });
      if (res.ok) {
        const data = await res.json();
        setStatusMsg({
          type: 'success',
          text: `Ingested ${data.chunks_indexed} chunks into ChromaDB vector store!`,
        });
        fetchDocs();
      }
    } catch (err) {
      setStatusMsg({ type: 'error', text: 'Ingest error.' });
    }
  };

  const handleDelete = async (docId) => {
    if (!confirm('Are you sure you want to delete this document?')) return;
    try {
      const res = await fetch(`/api/v1/documents/${docId}`, { method: 'DELETE' });
      if (res.ok) {
        setStatusMsg({ type: 'info', text: 'Document deleted.' });
        fetchDocs();
      }
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">UNIMIND AI</span>
          <h2 className="text-2xl font-bold text-slate-900 mt-0.5">Documents & Vector Ingestion</h2>
          <p className="text-xs text-slate-500 mt-1">
            Upload institutional handbooks, syllabus guidelines, and policies to index into ChromaDB.
          </p>
        </div>

        <button
          onClick={fetchDocs}
          className="px-3 py-2 bg-white border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-semibold rounded-lg flex items-center gap-2 shadow-sm transition-all"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {statusMsg && (
        <div
          className={`p-3 rounded-lg text-xs font-semibold flex items-center gap-2 ${
            statusMsg.type === 'success'
              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
              : statusMsg.type === 'error'
              ? 'bg-rose-50 text-rose-700 border border-rose-200'
              : 'bg-blue-50 text-blue-700 border border-blue-200'
          }`}
        >
          {statusMsg.type === 'success' ? (
            <CheckCircle className="h-4 w-4" />
          ) : (
            <AlertCircle className="h-4 w-4" />
          )}
          <span>{statusMsg.text}</span>
        </div>
      )}

      {/* Upload Box */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider mb-4 flex items-center gap-2">
          <Upload className="h-4 w-4 text-blue-600" /> Upload New University Document
        </h3>

        <form onSubmit={handleUpload} className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2 space-y-1">
            <label className="text-[11px] font-bold text-slate-600 uppercase">Document Title</label>
            <input
              type="text"
              placeholder="e.g. Hostel Guidelines 2026"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              className="w-full bg-slate-50 border border-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-600 uppercase">Category</label>
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="w-full bg-slate-50 border border-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="academic">Academic</option>
              <option value="attendance">Attendance</option>
              <option value="hostel">Hostel</option>
              <option value="it">IT Support</option>
              <option value="general">General</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-600 uppercase">Select File</label>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files[0])}
              required
              className="w-full text-xs text-slate-500 file:mr-2 file:py-1.5 file:px-3 file:rounded file:border-0 file:text-xs file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
            />
          </div>

          <div className="md:col-span-4 flex justify-end">
            <button
              type="submit"
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-5 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2"
            >
              <Upload className="h-4 w-4" />
              <span>Upload & Ingest to RAG</span>
            </button>
          </div>
        </form>
      </div>

      {/* Documents Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-slate-200 flex items-center justify-between">
          <h3 className="text-sm font-bold text-slate-900">Indexed Knowledge Files ({documents.length})</h3>
          <span className="text-xs text-slate-500">ChromaDB Store: university_knowledge_base</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 text-slate-500 font-bold uppercase tracking-wider border-b border-slate-200">
              <tr>
                <th className="py-2.5 px-4">Title</th>
                <th className="py-2.5 px-4">Category</th>
                <th className="py-2.5 px-4">Filename</th>
                <th className="py-2.5 px-4">Chunks</th>
                <th className="py-2.5 px-4">RAG Status</th>
                <th className="py-2.5 px-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {documents.length === 0 ? (
                <tr>
                  <td colSpan="6" className="py-8 text-center text-slate-400">
                    No documents found. Upload a policy above to begin.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.id} className="hover:bg-slate-50/50">
                    <td className="py-3 px-4 font-semibold text-slate-900 flex items-center gap-2">
                      <FileText className="h-4 w-4 text-blue-600" />
                      <span>{doc.title}</span>
                    </td>
                    <td className="py-3 px-4">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-slate-100 text-slate-700 uppercase">
                        {doc.category}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-600">{doc.filename}</td>
                    <td className="py-3 px-4 font-mono font-bold text-blue-600">
                      {doc.chunk_count || 0}
                    </td>
                    <td className="py-3 px-4">
                      {doc.chunk_count > 0 ? (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-emerald-600">
                          <CheckCircle className="h-3.5 w-3.5" /> Indexed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1 text-[11px] font-bold text-amber-600">
                          <AlertCircle className="h-3.5 w-3.5" /> Ready to Ingest
                        </span>
                      )}
                    </td>
                    <td className="py-3 px-4 text-right space-x-2">
                      <button
                        onClick={() => handleIngest(doc.id)}
                        className="px-2.5 py-1 rounded bg-blue-50 text-blue-600 hover:bg-blue-600 hover:text-white font-semibold text-[11px] transition-colors"
                      >
                        Re-Ingest
                      </button>
                      <button
                        onClick={() => handleDelete(doc.id)}
                        className="px-2.5 py-1 rounded bg-rose-50 text-rose-600 hover:bg-rose-600 hover:text-white font-semibold text-[11px] transition-colors"
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
