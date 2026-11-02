import React, { useState, useEffect } from 'react';
import { Database, Search, Cpu, CheckCircle, ArrowRight, Layers, Sliders, Zap, Tag, Bookmark } from 'lucide-react';

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
      const res = await fetch('/api/v1/rag/stats');
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
      const res = await fetch('/api/v1/rag/query', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
    <div className="space-y-6">
      {/* Header */}
      <div>
        <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">UNIMIND AI</span>
        <h2 className="text-2xl font-bold text-slate-900 mt-0.5">Production Hybrid RAG Engine</h2>
        <p className="text-xs text-slate-500 mt-1">
          State-of-the-art multi-stage retrieval: Dense vector embeddings (ChromaDB) + Sparse lexical matching (Okapi BM25) + Reciprocal Rank Fusion (RRF) + Re-ranking.
        </p>
      </div>

      {/* Vector & Lexical Store Metadata Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Vector Store (Dense)</span>
          <div className="text-lg font-bold text-slate-900 mt-1 flex items-center gap-1.5">
            <Database className="h-4 w-4 text-blue-600" /> ChromaDB
          </div>
          <span className="text-xs text-emerald-600 font-semibold mt-1 block">all-MiniLM-L6-v2 (384-dim)</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Lexical Engine (Sparse)</span>
          <div className="text-lg font-bold text-slate-900 mt-1 flex items-center gap-1.5 font-mono text-sm">
            <Zap className="h-4 w-4 text-amber-500" /> Okapi BM25
          </div>
          <span className="text-xs text-slate-500 mt-1 block">k1=1.5, b=0.75 (Exact Codes & %)</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Total Chunks Synced</span>
          <div className="text-lg font-bold text-blue-600 mt-1 font-mono">
            {stats ? stats.total_chunks : '12+'}
          </div>
          <span className="text-xs text-slate-500 mt-1 block">Sentence-Aware Recursive Split</span>
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
          <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider block">Fusion Algorithm</span>
          <div className="text-lg font-bold text-slate-900 mt-1 font-mono">RRF (k=60)</div>
          <span className="text-xs text-slate-500 mt-1 block">Multi-Factor Re-ranking</span>
        </div>
      </div>

      {/* Retrieval Mode Selector & Search Tester */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-blue-600" />
            <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider">
              Retrieval Playground & Diagnostic Console
            </h3>
          </div>

          {/* Mode Switcher */}
          <div className="inline-flex rounded-lg border border-slate-200 bg-slate-50 p-1">
            <button
              onClick={() => setMode('hybrid')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-all flex items-center gap-1.5 ${
                mode === 'hybrid'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Zap className="h-3 w-3" /> Hybrid (RRF)
            </button>
            <button
              onClick={() => setMode('dense')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-all flex items-center gap-1.5 ${
                mode === 'dense'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Database className="h-3 w-3" /> Dense Vector
            </button>
            <button
              onClick={() => setMode('bm25')}
              className={`px-3 py-1 text-xs font-bold rounded-md transition-all flex items-center gap-1.5 ${
                mode === 'bm25'
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-slate-600 hover:text-slate-900'
              }`}
            >
              <Search className="h-3 w-3" /> BM25 Lexical
            </button>
          </div>
        </div>

        <div className="flex flex-col md:flex-row gap-3">
          <div className="flex-1 relative">
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter student query, course code, percentage, or policy rule..."
              className="w-full bg-slate-50 border border-slate-200 text-xs px-4 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 font-medium"
            />
          </div>

          <div className="flex items-center gap-2">
            <select
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              className="bg-slate-50 border border-slate-200 text-xs px-3 py-2.5 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-slate-700"
            >
              <option value="">All Categories</option>
              <option value="hostel">Hostel</option>
              <option value="attendance">Attendance</option>
              <option value="academic">Academic</option>
              <option value="examination">Examination</option>
              <option value="it">IT Support</option>
            </select>

            <button
              onClick={() => handleSearch()}
              disabled={loading}
              className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-5 py-2.5 rounded-lg shadow-sm transition-all flex items-center gap-2 disabled:opacity-50"
            >
              <Search className="h-4 w-4" />
              <span>{loading ? 'Searching...' : 'Run Search'}</span>
            </button>
          </div>
        </div>

        {/* Query Expansion Bar */}
        {expandedTerms.length > 0 && (
          <div className="p-2.5 bg-blue-50/50 border border-blue-100 rounded-lg flex items-center gap-2 text-xs text-blue-900 flex-wrap">
            <span className="font-bold text-[11px] uppercase tracking-wider text-blue-700 flex items-center gap-1">
              <Tag className="h-3 w-3" /> Institutional Synonym Expansion:
            </span>
            {expandedTerms.map((term, tIdx) => (
              <span key={tIdx} className="bg-white border border-blue-200 text-blue-700 font-mono text-[10px] px-2 py-0.5 rounded-full font-semibold">
                +{term}
              </span>
            ))}
          </div>
        )}

        {/* Quick Sample Queries */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[11px] font-bold text-slate-400">Sample Queries:</span>
          {sampleQueries.map((sq, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(sq);
                handleSearch(sq);
              }}
              className="bg-slate-100 hover:bg-blue-50 hover:text-blue-600 text-slate-600 text-[11px] px-2.5 py-1 rounded-md transition-colors font-medium border border-slate-200"
            >
              {sq}
            </button>
          ))}
        </div>
      </div>

      {/* Query Results */}
      <div className="space-y-3">
        <h3 className="text-sm font-bold text-slate-900 uppercase tracking-wider flex items-center justify-between">
          <span className="flex items-center gap-2">
            Retrieved Chunks ({results.length})
            <span className="text-xs font-mono font-normal text-blue-600 bg-blue-50 px-2 py-0.5 rounded border border-blue-100">
              Mode: {mode.toUpperCase()}
            </span>
          </span>
          <span className="text-xs text-slate-500 font-normal">Ranked by Reciprocal Rank Fusion & Re-ranking</span>
        </h3>

        {results.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-400">
            No chunks retrieved. Click 'Run Search' to query the knowledge base.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {results.map((res, idx) => {
              const scorePct = Math.round((res.similarity_score || 0) * 100);
              const meta = res.metadata || {};
              const matchedKw = res.matched_keywords || [];
              const sectionHeading = meta.section_heading || '';

              return (
                <div
                  key={idx}
                  className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm hover:border-blue-300 transition-all space-y-2.5 flex flex-col justify-between"
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-blue-50 text-blue-700 uppercase">
                        {meta.category || 'General'}
                      </span>
                      <div className="flex items-center gap-1.5">
                        {res.rrf_score !== undefined && res.rrf_score !== null && (
                          <span className="text-[10px] font-mono text-slate-500 bg-slate-100 px-1.5 py-0.5 rounded">
                            RRF: {res.rrf_score}
                          </span>
                        )}
                        <span
                          className={`text-xs font-mono font-bold px-2 py-0.5 rounded-full ${
                            scorePct >= 70
                              ? 'bg-emerald-100 text-emerald-800'
                              : scorePct >= 45
                              ? 'bg-blue-100 text-blue-800'
                              : 'bg-amber-100 text-amber-800'
                          }`}
                        >
                          {scorePct}% Match
                        </span>
                      </div>
                    </div>

                    <h4 className="text-xs font-bold text-slate-900 mt-2">
                      {meta.title || 'Official University Document'}
                    </h4>

                    {sectionHeading && (
                      <div className="text-[11px] font-semibold text-blue-800 flex items-center gap-1 mt-0.5">
                        <Bookmark className="h-3 w-3 text-blue-600" />
                        {sectionHeading}
                      </div>
                    )}

                    <p className="text-[11px] text-slate-500 font-mono mt-0.5">
                      File: {meta.filename || 'source'} • Chunk ID: {res.chunk_id}
                    </p>

                    {/* Matched Keywords Pills */}
                    {matchedKw.length > 0 && (
                      <div className="flex items-center gap-1 flex-wrap mt-1.5">
                        <span className="text-[10px] font-bold text-slate-400">Lexical Hits:</span>
                        {matchedKw.map((kw, kIdx) => (
                          <span key={kIdx} className="bg-amber-50 text-amber-800 border border-amber-200 text-[10px] px-1.5 py-0.2 rounded font-mono font-semibold">
                            {kw}
                          </span>
                        ))}
                      </div>
                    )}

                    <div className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-700 leading-relaxed font-mono whitespace-pre-wrap">
                      {res.text}
                    </div>
                  </div>

                  <div className="pt-2 text-[10px] text-slate-400 flex items-center justify-between border-t border-slate-100">
                    <span>
                      {res.bm25_score ? `BM25 Score: ${res.bm25_score}` : `Raw Score: ${res.similarity_score}`}
                    </span>
                    <span className="text-emerald-600 font-semibold flex items-center gap-1">
                      <CheckCircle className="h-3 w-3" /> Grounded in Knowledge Base
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
