import React, { useState, useEffect } from 'react';
import { Ticket, Plus, CheckCircle, Clock, AlertTriangle, Filter, Sparkles, RefreshCw } from 'lucide-react';
import { apiFetch, getTenantId, parseApiError } from '../apiClient';

export default function TicketsView({ onAskAssistant }) {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('ALL');
  const [showCreateModal, setShowCreateModal] = useState(false);

  // New ticket state
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [category, setCategory] = useState('IT Support');
  const [priority, setPriority] = useState('MEDIUM');

  const fetchTickets = async () => {
    setLoading(true);
    try {
      const res = await apiFetch('/api/v1/tickets');
      if (res.ok) {
        setTickets(await res.json());
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
    const handleTenantChange = () => fetchTickets();
    window.addEventListener('unimind:tenant_change', handleTenantChange);
    return () => window.removeEventListener('unimind:tenant_change', handleTenantChange);
  }, []);

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!title || !description) return;

    try {
      const res = await apiFetch('/api/v1/tickets', {
        method: 'POST',
        body: JSON.stringify({
          title,
          description,
          category,
          priority,
        }),
      });

      if (res.ok) {
        setShowCreateModal(false);
        setTitle('');
        setDescription('');
        fetchTickets();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUpdateStatus = async (ticketId, newStatus) => {
    try {
      const res = await apiFetch(`/api/v1/tickets/${ticketId}`, {
        method: 'PATCH',
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        fetchTickets();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const filteredTickets = tickets.filter((t) => {
    if (filter === 'ALL') return true;
    return t.status === filter;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">UNIMIND AI</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Tickets & Student Inquiries</h2>
          <p className="text-xs text-slate-400 mt-1">
            Automated student support ticket routing, priority triaging, and AI-assisted resolution.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-cyan-600 hover:bg-cyan-500 text-white font-bold text-xs px-4 py-2.5 rounded-lg shadow-sm flex items-center gap-2 transition-all self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          <span>New Support Ticket</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-700/60 pb-3">
        <Filter className="h-4 w-4 text-slate-400" />
        <span className="text-xs font-bold text-slate-400 mr-2">Filter:</span>
        {['ALL', 'OPEN', 'IN_PROGRESS', 'RESOLVED'].map((status) => (
          <button
            key={status}
            onClick={() => setFilter(status)}
            className={`px-3 py-1 rounded-lg text-xs font-bold transition-all ${
              filter === status
                ? 'bg-cyan-600 text-white shadow-sm'
                : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800'
            }`}
          >
            {status}
          </button>
        ))}
      </div>

      {/* Tickets List */}
      <div className="space-y-3">
        {loading && tickets.length === 0 ? (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center text-xs text-slate-400">
            <RefreshCw className="h-6 w-6 text-cyan-400 animate-spin mx-auto mb-2" />
            <span>Loading support tickets...</span>
          </div>
        ) : filteredTickets.length === 0 ? (
          <div className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-8 text-center text-xs text-slate-400">
            No tickets found in this view.
          </div>
        ) : (
          filteredTickets.map((t) => (
            <div
              key={t.id}
              className="bg-slate-800/50 border border-slate-700/50 rounded-xl p-5 hover:border-slate-600 transition-all shadow-sm space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-xs font-bold text-cyan-400 bg-cyan-500/10 px-2 py-0.5 rounded border border-cyan-500/20">
                    TICK-{t.id}
                  </span>
                  <h4 className="text-sm font-bold text-slate-100">{t.title}</h4>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                      t.priority === 'CRITICAL'
                        ? 'bg-rose-500/10 text-rose-400 border-rose-500/20'
                        : t.priority === 'HIGH'
                        ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                        : 'bg-slate-700 text-slate-300 border-slate-600'
                    }`}
                  >
                    {t.priority}
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full uppercase border ${
                      t.status === 'RESOLVED'
                        ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                        : t.status === 'IN_PROGRESS'
                        ? 'bg-cyan-500/10 text-cyan-400 border-cyan-500/20'
                        : 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                    }`}
                  >
                    {t.status}
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-300 leading-relaxed">{t.description}</p>

              <div className="pt-2 flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs border-t border-slate-700/60">
                <div className="text-slate-400 flex items-center gap-4 text-[11px]">
                  <span>Category: <strong className="text-slate-300">{t.category}</strong></span>
                  <span>Created: {new Date(t.created_at).toLocaleDateString()}</span>
                </div>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() =>
                      onAskAssistant(
                        `Regarding ticket "${t.title}": ${t.description} What are the university guidelines?`
                      )
                    }
                    className="px-2.5 py-1 bg-cyan-500/10 hover:bg-cyan-600 hover:text-white text-cyan-300 border border-cyan-500/20 rounded font-semibold text-[11px] flex items-center gap-1.5 transition-colors"
                  >
                    <Sparkles className="h-3 w-3" />
                    <span>Ask AI Assistant</span>
                  </button>

                  {t.status !== 'RESOLVED' && (
                    <button
                      onClick={() => handleUpdateStatus(t.id, 'RESOLVED')}
                      className="px-2.5 py-1 bg-emerald-500/10 hover:bg-emerald-600 hover:text-white text-emerald-300 border border-emerald-500/20 rounded font-semibold text-[11px] flex items-center gap-1 transition-colors"
                    >
                      <CheckCircle className="h-3 w-3" />
                      <span>Resolve</span>
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4 z-50">
          <div className="bg-slate-900 border border-slate-700 rounded-xl p-6 max-w-lg w-full space-y-4 shadow-2xl">
            <h3 className="text-base font-bold text-slate-100">Create New Support Ticket</h3>
            <form onSubmit={handleCreateTicket} className="space-y-4 text-xs">
              <div>
                <label className="block text-slate-300 font-bold mb-1">Subject</label>
                <input
                  type="text"
                  placeholder="e.g. Wi-Fi Access in Library 3rd Floor"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  required
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Category</label>
                <select
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="IT Support">IT Support</option>
                  <option value="Academic">Academic</option>
                  <option value="Hostel">Hostel</option>
                  <option value="Examination">Examination</option>
                  <option value="Fees">Fees & Billing</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Priority</label>
                <select
                  value={priority}
                  onChange={(e) => setPriority(e.target.value)}
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                >
                  <option value="LOW">Low</option>
                  <option value="MEDIUM">Medium</option>
                  <option value="HIGH">High</option>
                  <option value="CRITICAL">Critical</option>
                </select>
              </div>

              <div>
                <label className="block text-slate-300 font-bold mb-1">Description</label>
                <textarea
                  rows="4"
                  placeholder="Provide detailed inquiry or issue description..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  required
                  className="w-full bg-slate-800 border border-slate-700 rounded-lg p-2.5 text-slate-200 focus:outline-none focus:ring-2 focus:ring-cyan-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg font-bold"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg font-bold shadow-sm"
                >
                  Create Ticket
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
