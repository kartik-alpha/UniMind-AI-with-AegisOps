import React, { useState, useEffect } from 'react';
import { Ticket, Plus, CheckCircle, Clock, AlertTriangle, Filter, Sparkles } from 'lucide-react';

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
      const res = await fetch('/api/v1/tickets');
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
  }, []);

  const handleCreateTicket = async (e) => {
    e.preventDefault();
    if (!title || !description) return;

    try {
      const res = await fetch('/api/v1/tickets', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
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
      const res = await fetch(`/api/v1/tickets/${ticketId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-500 uppercase block">UNIMIND AI</span>
          <h2 className="text-2xl font-bold text-slate-900 mt-0.5">Tickets & Student Inquiries</h2>
          <p className="text-xs text-slate-500 mt-1">
            Automated student support ticket routing, priority triaging, and AI-assisted resolution.
          </p>
        </div>

        <button
          onClick={() => setShowCreateModal(true)}
          className="bg-blue-600 hover:bg-blue-500 text-white font-bold text-xs px-4 py-2.5 rounded-lg shadow-sm flex items-center gap-2 transition-all self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          <span>New Support Ticket</span>
        </button>
      </div>

      {/* Filter Tabs */}
      <div className="flex items-center gap-2 border-b border-slate-200 pb-3">
        {['ALL', 'OPEN', 'IN_PROGRESS', 'RESOLVED'].map((f) => (
          <button
            key={f}
            onClick={() => setFilter(f)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold capitalize transition-all ${
              filter === f
                ? 'bg-[#1c2541] text-white shadow-sm'
                : 'text-slate-600 hover:bg-slate-100'
            }`}
          >
            {f.replace('_', ' ').toLowerCase()} ({tickets.filter((t) => f === 'ALL' || t.status === f).length})
          </button>
        ))}
      </div>

      {/* Tickets List */}
      <div className="space-y-3">
        {filteredTickets.length === 0 ? (
          <div className="bg-white border border-slate-200 rounded-xl p-8 text-center text-xs text-slate-400">
            No tickets found in this view.
          </div>
        ) : (
          filteredTickets.map((t) => (
            <div
              key={t.id}
              className="bg-white border border-slate-200 rounded-xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col md:flex-row md:items-center justify-between gap-4"
            >
              <div className="space-y-1.5 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-bold text-blue-600 bg-blue-50 px-2 py-0.5 rounded">
                    {t.ticket_code}
                  </span>
                  <span
                    className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                      t.priority === 'CRITICAL'
                        ? 'bg-rose-100 text-rose-700'
                        : t.priority === 'HIGH'
                        ? 'bg-amber-100 text-amber-700'
                        : 'bg-slate-100 text-slate-700'
                    }`}
                  >
                    {t.priority}
                  </span>
                  <span className="text-[11px] text-slate-500 font-medium">
                    Category: <span className="font-semibold text-slate-700">{t.category}</span>
                  </span>
                </div>

                <h4 className="text-sm font-bold text-slate-900">{t.title}</h4>
                <p className="text-xs text-slate-600 line-clamp-2 leading-relaxed">
                  {t.description}
                </p>
              </div>

              {/* Status & Actions */}
              <div className="flex items-center gap-3 self-end md:self-center shrink-0">
                <span
                  className={`text-xs font-bold px-2.5 py-1 rounded-full ${
                    t.status === 'RESOLVED'
                      ? 'bg-emerald-100 text-emerald-700'
                      : t.status === 'IN_PROGRESS'
                      ? 'bg-blue-100 text-blue-700'
                      : 'bg-amber-100 text-amber-700'
                  }`}
                >
                  {t.status.replace('_', ' ')}
                </span>

                <div className="flex gap-1.5">
                  {t.status !== 'RESOLVED' && (
                    <button
                      onClick={() => handleUpdateStatus(t.id, 'RESOLVED')}
                      className="px-2.5 py-1 bg-emerald-50 text-emerald-700 hover:bg-emerald-600 hover:text-white rounded text-xs font-semibold transition-colors"
                    >
                      Resolve
                    </button>
                  )}

                  {t.status === 'OPEN' && (
                    <button
                      onClick={() => handleUpdateStatus(t.id, 'IN_PROGRESS')}
                      className="px-2.5 py-1 bg-slate-100 text-slate-700 hover:bg-slate-200 rounded text-xs font-semibold transition-colors"
                    >
                      Start
                    </button>
                  )}

                  <button
                    onClick={() => onAskAssistant(`How do I resolve ticket: ${t.title}? ${t.description}`)}
                    className="px-2.5 py-1 bg-purple-50 text-purple-700 hover:bg-purple-600 hover:text-white rounded text-xs font-semibold flex items-center gap-1 transition-colors"
                  >
                    <Sparkles className="h-3 w-3" />
                    <span>AI Solve</span>
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Create Ticket Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm animate-fadeIn">
          <div className="bg-white rounded-2xl max-w-lg w-full p-6 shadow-2xl border border-slate-200 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-200">
              <h3 className="text-base font-bold text-slate-900">Create New Support Ticket</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-slate-600 font-bold"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateTicket} className="space-y-4">
              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-700">Subject / Title</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Hostel Wi-Fi issue in Room 204"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700">Category</label>
                  <select
                    value={category}
                    onChange={(e) => setCategory(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="IT Support">IT Support</option>
                    <option value="Academic">Academic</option>
                    <option value="Hostel">Hostel</option>
                    <option value="Library">Library</option>
                  </select>
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-bold text-slate-700">Priority</label>
                  <select
                    value={priority}
                    onChange={(e) => setPriority(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="LOW">Low</option>
                    <option value="MEDIUM">Medium</option>
                    <option value="HIGH">High</option>
                    <option value="CRITICAL">Critical</option>
                  </select>
                </div>
              </div>

              <div className="space-y-1">
                <label className="text-xs font-bold text-slate-700">Description</label>
                <textarea
                  rows="3"
                  required
                  placeholder="Provide detailed description of the inquiry..."
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-200 text-xs px-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div className="flex justify-end gap-2 pt-2 border-t border-slate-200">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-4 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-lg text-xs font-bold transition-all"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-bold transition-all"
                >
                  Submit Ticket
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
