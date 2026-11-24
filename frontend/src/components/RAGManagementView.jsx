import React, { useState, useEffect } from 'react';
import { Database, Search, Cpu, CheckCircle, ArrowRight, Layers, Sliders, Zap, Tag, Bookmark } from 'lucide-react';
import { apiFetch, getTenantId, parseApiError } from '../apiClient';

export default function RAGManagementView() {
  const [query, setQuery] = useState('What is the mandatory curfew time for undergraduate resident students?');
  const [topK, setTopK] = useState(4);
  const [category, setCategory] = useState('');
  const [mode, setMode] = useState('hybrid');
  const [useExpansion, setUseExpansion] = useState(true);
  const [results, setResults] = useState([]);
  const [expandedTerms, setExpandedTerms] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(false);

  const fetchStats = async () => {
    try {
      const res = await apiFetch('/api/v1/rag/stats');
      if (res.ok) setStats(await res.json());
    } catch (e) {
      console.error(e);
    }
  };

  useEffect(() => {
    fetchStats();
    handleSearch();
  }, [mode]);

  const handleSearch = async (overrideQuery) => {
    const q = overrideQuery || query;
    if (!q.trim()) return;

    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/rag/query', {
        method: 'POST',
        body: JSON.stringify({
          query: q,
          top_k: topK,
          category: category || null,
          mode: mode,
          use_expansion: useExpansion,
        }),
      });

      if (res.ok) {
        const data = await res.json();
        setResults(data.results || []);
        setExpandedTerms(data.expanded_terms || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const sampleQueries = [
    'What is the mandatory hostel curfew time?',
    'What is the minimum attendance required for final exams?',
    'How is CGPA calculated on a 10-point scale?',
    'What are the re-evaluation rules and application deadlines?',
    'What are the rules for IT Lab and campus Wi-Fi access?',
  ];

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div>
        <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">UNIMIND AI</span>
        <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Production Hybrid RAG Engine</h2>
        <p className="text-xs text-slate-400 mt-1">
          State-of-the-art multi-stage retrieval: Dense vector embeddings (ChromaDB) + Sparse lexical matching (Okapi BM25) + Reciprocal Rank Fusion (RRF) + Re-ranking.
        </p>
      </div>

      {/* Vector & Lexical Store Metadata Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Vector Store (Dense)</span>
          <div className="text-lg font-bold text-slate-100 mt-1 flex items-center gap-1.5">
            <Database className="h-4 w-4 text-cyan-400" /> ChromaDB
          </div>
          <span className="text-xs text-emerald-400 font-semibold mt-1 block">all-MiniLM-L6-v2 (384-dim)</span>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Lexical Engine (Sparse)</span>
          <div className="text-lg font-bold text-slate-100 mt-1 flex items-center gap-1.5 font-mono text-sm">
            <Zap className="h-4 w-4 text-amber-400" /> Okapi BM25
          </div>
          <span className="text-xs text-slate-400 mt-1 block">k1=1.5, b=0.75 (Exact Codes & %)</span>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Total Chunks Synced</span>
          <div className="text-lg font-bold text-cyan-400 mt-1 font-mono">
            {stats ? stats.total_chunks : '12+'}
          </div>
          <span className="text-xs text-slate-400 mt-1 block">Indexed across all policies</span>
        </div>

        <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block">Fusion Strategy</span>
          <div className="text-lg font-bold text-purple-400 mt-1 flex items-center gap-1.5 font-mono text-sm">
            <Layers className="h-4 w-4" /> RRF Fusion
          </div>
          <span className="text-xs text-slate-400 mt-1 block">k=60 rank reciprocal score</span>
        </div>
      </div>

      {/* Query Testing Console */}
      <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-6 shadow-sm space-y-4">
        <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider flex items-center gap-2">
          <Sliders className="h-4 w-4 text-cyan-400" /> RAG Retrieval Query Sandbox
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2 space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase">Search Query</label>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-xs px-3 py-2.5 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase">Retrieval Mode</label>
            <select
              value={mode}
              onChange={(e) => setMode(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 text-xs px-3 py-2.5 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            >
              <option value="hybrid">Hybrid (Dense + BM25 + RRF)</option>
              <option value="dense">Dense Vector Only</option>
              <option value="bm25">BM25 Sparse Lexical Only</option>
            </select>
          </div>

          <div className="space-y-1">
            <label className="text-[11px] font-bold text-slate-300 uppercase">Top K Results</label>
            <input
              type="number"
              min="1"
              max="10"
              value={topK}
              onChange={(e) => setTopK(parseInt(e.target.value))}
              className="w-full bg-slate-800 border border-slate-700 text-xs px-3 py-2.5 rounded-lg text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
            />
          </div>
        </div>

        {/* Sample queries chips */}
        <div className="flex flex-wrap gap-2 items-center pt-2">
          <span className="text-[10px] font-bold text-slate-400 uppercase">Test Prompts:</span>
          {sampleQueries.map((sq, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(sq);
                handleSearch(sq);
              }}
              className="text-[11px] bg-slate-800 hover:bg-slate-700 text-slate-300 px-2.5 py-1 rounded-md border border-slate-700 transition-colors"
            >
              {sq}
            </button>
          ))}
        </div>

        <div className="flex justify-end pt-2">
          <button
            onClick={() => handleSearch()}
            disabled={loading}
            className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs px-6 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2 disabled:opacity-50"
          >
            <Search className="h-4 w-4" />
            <span>{loading ? 'Executing Retrieval...' : 'Execute Multi-Stage Retrieval'}</span>
          </button>
        </div>
      </div>

      {/* Query Expansion Terms */}
      {expandedTerms.length > 0 && (
        <div className="bg-slate-800/40 border border-slate-700/50 rounded-xl p-4 flex items-center gap-2 text-xs">
          <span className="font-bold text-cyan-400 flex items-center gap-1">
            <Tag className="h-3.5 w-3.5" /> Synonym Expansion:
          </span>
          <div className="flex flex-wrap gap-1.5">
            {expandedTerms.map((term, idx) => (
              <span key={idx} className="bg-cyan-500/10 text-cyan-300 px-2 py-0.5 rounded border border-cyan-500/20 font-mono text-[11px]">
                {term}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* Results Display */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-slate-100 flex items-center justify-between">
          <span>Ranked Retrieved Document Chunks ({results.length})</span>
          <span className="text-xs text-slate-400 font-normal">Ranked by Reciprocal Rank Fusion</span>
        </h3>

        {results.length === 0 ? (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-8 text-center text-xs text-slate-400">
            No results returned. Try clicking one of the test prompts above.
          </div>
        ) : (
          results.map((r, idx) => (
            <div
              key={idx}
              className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 hover:border-slate-600 transition-all shadow-sm space-y-2"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span className="h-5 w-5 rounded-full bg-cyan-600 text-white font-mono font-bold text-xs flex items-center justify-center">
                    {idx + 1}
                  </span>
                  <h4 className="text-xs font-bold text-slate-100">{r.title}</h4>
                  {r.section_heading && (
                    <span className="text-[11px] text-cyan-400 font-medium flex items-center gap-1">
                      <Bookmark className="h-3 w-3" /> {r.section_heading}
                    </span>
                  )}
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 uppercase font-mono">
                    {r.retrieval_mode || mode}
                  </span>
                  <span className="text-xs font-mono font-bold text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    Score: {(r.similarity_score * 100).toFixed(1)}%
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed font-sans bg-slate-900/60 p-3 rounded-lg border border-slate-800">
                {r.content}
              </p>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
