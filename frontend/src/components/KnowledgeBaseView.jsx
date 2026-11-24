import React, { useState } from 'react';
import { BookOpen, Search, FileText, ArrowRight, CheckCircle, ExternalLink, ShieldAlert } from 'lucide-react';

export default function KnowledgeBaseView({ onAskAssistant }) {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [activeModalDoc, setActiveModalDoc] = useState(null);

  const articles = [
    {
      id: 'doc-001',
      title: 'Hostel Policy & Curfew Guidelines 2026',
      category: 'Hostel',
      updated: 'Spring 2026',
      chunks: 3,
      excerpt: 'Mandatory hostel curfew is 10:00 PM for all undergraduate resident students. Late entries require prior digital approval from the hostel warden...',
      content: `HOSTEL POLICY 2026 - CAMPUS RESIDENCE REGULATIONS
1. Curfew & Timing: Mandatory hostel curfew is 10:00 PM for all undergraduate resident students. Late entries require prior digital approval from the hostel warden submitted at least 2 hours in advance via the student portal.
2. Quiet Hours: Quiet hours begin strictly at 11:00 PM on weekdays and 12:00 AM on weekends.
3. Visitors: External visitors are permitted in designated ground-floor visitor lounges between 4:00 PM and 8:00 PM daily.
4. Prohibited Items: Possession of prohibited electrical heating appliances, cooking induction plates, or hazardous materials is strictly forbidden.`,
    },
    {
      id: 'doc-002',
      title: 'Academic Attendance & Examination Regulations 2026',
      category: 'Attendance',
      updated: 'Spring 2026',
      chunks: 3,
      excerpt: 'A minimum of 75% aggregate attendance across lectures, practical laboratory sessions, and tutorial hours is mandatory to be eligible for semester final examinations...',
      content: `ACADEMIC REGULATIONS 2026 - ATTENDANCE REQUIREMENTS
1. Minimum Requirement: A minimum of 75% aggregate attendance across lectures, practical laboratory sessions, and tutorial hours is mandatory to be eligible for semester final examinations.
2. Medical Condonation: Students with attendance between 65% and 74% due to verified medical emergencies must file an appeal with medical documentation to the Dean of Academic Affairs within 7 working days.
3. Barred Candidates: Students falling below 65% attendance are automatically barred from end-term examinations and must repeat the course in the upcoming summer semester.`,
    },
    {
      id: 'doc-003',
      title: 'Grading System & GPA Calculation Guidelines 2026',
      category: 'Academic',
      updated: 'Spring 2026',
      chunks: 4,
      excerpt: 'The university utilizes a 10-point cumulative grade point average (CGPA) system based on relative grading: A+ (10), A (9), B+ (8), B (7), C (6), D (5), F (0)...',
      content: `EXAMINATION GRADING SYSTEM 2026
1. Grading Scale: The university utilizes a 10-point cumulative grade point average (CGPA) system based on relative grading:
   • A+ = 10.0 (Outstanding)
   • A = 9.0 (Excellent)
   • B+ = 8.0 (Very Good)
   • B = 7.0 (Good)
   • C = 6.0 (Average)
   • D = 5.0 (Pass)
   • F = 0.0 (Fail)
2. Degree Eligibility: A minimum cumulative CGPA of 5.0 is required for undergraduate degree conferral.
3. Re-evaluation: Grade dispute appeals must be formally lodged through the Examination Portal within 10 days of results publication.`,
    },
    {
      id: 'doc-004',
      title: 'IT Lab Access & Cloud Computing Regulations 2026',
      category: 'IT Support',
      updated: 'Spring 2026',
      chunks: 2,
      excerpt: 'Computing laboratories and AI research clusters are open 24/7 for authenticated engineering students. VPN and cloud sandbox credentials are provisioned through university SSO...',
      content: `IT INFRASTRUCTURE & LAB POLICIES 2026
1. Laboratory Hours: Computing laboratories and AI research clusters are open 24/7 for authenticated engineering students.
2. Authentication: VPN and cloud sandbox credentials are provisioned through university SSO and reset automatically every 90 days.
3. Security Compliance: Unauthorized network sniffing, port scanning, or cryptocurrency mining on university compute nodes is strictly prohibited and results in immediate account suspension.`,
    },
    {
      id: 'runbook-001',
      title: 'Exam Service High Latency & Pool Exhaustion Runbook',
      category: 'SRE Runbooks',
      updated: 'Updated Today',
      chunks: 2,
      isRunbook: true,
      excerpt: 'SYMPTOMS: High CPU (>90%), Latency (>1500ms), 503 error spikes, Database connection pool timeout log errors. ROOT CAUSE: Heavy concurrent exam submissions...',
      content: `SRE RUNBOOK-001: EXAM SERVICE HIGH LATENCY & POOL EXHAUSTION
SYMPTOMS: High CPU (>90%), Latency (>1500ms), 503 error spikes, Database connection pool timeout log errors.
ROOT CAUSE: Heavy concurrent exam submissions leading to database connection pool exhaustion.
RECOMMENDED REMEDIATION:
1. Restart exam-service pod to clear stale database pool handles.
2. Scale deployment replicas from 2 to 4 to distribute incoming traffic load.
VERIFICATION: Monitor latency drops below 200ms and CPU returns to <35%.`,
    },
    {
      id: 'runbook-002',
      title: 'LMS Cache Thrashing & High Memory Runbook',
      category: 'SRE Runbooks',
      updated: 'Updated 2d ago',
      chunks: 2,
      isRunbook: true,
      excerpt: 'SYMPTOMS: Memory usage (>85%), slow page load times. ROOT CAUSE: Redis cache eviction queue stall during assignment submission deadlines...',
      content: `SRE RUNBOOK-002: LMS CACHE THRASHING & HIGH MEMORY
SYMPTOMS: Memory usage (>85%), slow page load times.
ROOT CAUSE: Redis cache eviction queue stall during assignment submission deadlines.
RECOMMENDED REMEDIATION:
1. Restart LMS pod deployment.
2. Flush expired Redis key namespaces.
VERIFICATION: Memory returns to normal bounds (<50%).`,
    },
  ];

  const categories = ['All', 'Hostel', 'Attendance', 'Academic', 'IT Support', 'SRE Runbooks'];

  const filtered = articles.filter((a) => {
    const matchCat = selectedCategory === 'All' || a.category === selectedCategory;
    const matchQuery =
      a.title.toLowerCase().includes(search.toLowerCase()) ||
      a.excerpt.toLowerCase().includes(search.toLowerCase());
    return matchCat && matchQuery;
  });

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* View Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <span className="text-xs font-bold tracking-wider text-slate-400 uppercase block">UNIMIND AI</span>
          <h2 className="text-2xl font-bold text-slate-100 mt-0.5">Knowledge Base & Policy Explorer</h2>
          <p className="text-xs text-slate-400 mt-1">
            Official university policies, student guidelines, and SRE incident runbooks indexed in ChromaDB.
          </p>
        </div>

        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-2.5 h-4 w-4 text-slate-500" />
          <input
            type="text"
            placeholder="Search knowledge..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 text-xs text-slate-200 placeholder-slate-500 pl-9 pr-3 py-2 rounded-lg focus:outline-none focus:ring-2 focus:ring-cyan-500 shadow-sm"
          />
        </div>
      </div>

      {/* Category Filter Pills */}
      <div className="flex items-center gap-2 overflow-x-auto pb-1">
        {categories.map((c) => (
          <button
            key={c}
            onClick={() => setSelectedCategory(c)}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap transition-all border ${
              selectedCategory === c
                ? 'bg-cyan-600 text-white border-cyan-500 shadow-sm'
                : 'bg-slate-800 border-slate-700 text-slate-300 hover:bg-slate-700 hover:text-white'
            }`}
          >
            {c}
          </button>
        ))}
      </div>

      {/* Articles Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {filtered.map((item) => (
          <div
            key={item.id}
            className={`border rounded-xl p-5 shadow-sm hover:shadow-md transition-all flex flex-col justify-between ${
              item.isRunbook
                ? 'border-amber-500/30 bg-amber-950/20'
                : 'bg-slate-800/50 border-slate-700/50 hover:border-slate-600'
            }`}
          >
            <div>
              <div className="flex items-center justify-between mb-2">
                <span
                  className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${
                    item.isRunbook
                      ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
                      : 'bg-cyan-500/10 text-cyan-300 border-cyan-500/20'
                  }`}
                >
                  {item.category}
                </span>
                <span className="text-[11px] text-slate-400">{item.chunks} vector chunks</span>
              </div>

              <h4 className="text-sm font-bold text-slate-100 mt-2 flex items-start gap-1.5">
                {item.isRunbook ? (
                  <ShieldAlert className="h-4 w-4 text-amber-400 shrink-0 mt-0.5" />
                ) : (
                  <BookOpen className="h-4 w-4 text-cyan-400 shrink-0 mt-0.5" />
                )}
                <span>{item.title}</span>
              </h4>

              <p className="text-xs text-slate-400 mt-2 line-clamp-3 leading-relaxed">
                {item.excerpt}
              </p>
            </div>

            <div className="mt-5 pt-3 border-t border-slate-700/50 flex items-center justify-between">
              <button
                onClick={() => setActiveModalDoc(item)}
                className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1"
              >
                <span>Read Full</span>
                <ExternalLink className="h-3 w-3" />
              </button>

              <button
                onClick={() => onAskAssistant(item.title)}
                className="px-2.5 py-1 rounded bg-slate-700 hover:bg-cyan-500/20 hover:text-cyan-300 text-slate-300 text-[11px] font-semibold transition-colors border border-slate-600"
              >
                Ask Assistant
              </button>
            </div>
          </div>
        ))}
      </div>

      {/* Modal for full document reading */}
      {activeModalDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
          <div className="bg-[#0b132b] rounded-2xl max-w-2xl w-full p-6 shadow-2xl border border-slate-800 max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <div>
                <span className="text-[10px] font-bold uppercase tracking-wider text-cyan-400">
                  {activeModalDoc.category}
                </span>
                <h3 className="text-lg font-bold text-white mt-0.5">
                  {activeModalDoc.title}
                </h3>
              </div>
              <button
                onClick={() => setActiveModalDoc(null)}
                className="h-8 w-8 rounded-lg bg-slate-800 hover:bg-slate-700 flex items-center justify-center text-slate-400 hover:text-white font-bold"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto py-4 text-xs text-slate-300 leading-relaxed font-mono whitespace-pre-wrap bg-[#080d1e] p-4 rounded-xl mt-3 border border-slate-800">
              {activeModalDoc.content}
            </div>

            <div className="pt-4 border-t border-slate-800 flex justify-end gap-2">
              <button
                onClick={() => {
                  const title = activeModalDoc.title;
                  setActiveModalDoc(null);
                  onAskAssistant(title);
                }}
                className="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg text-xs font-bold transition-all"
              >
                Ask AI Assistant About This
              </button>
              <button
                onClick={() => setActiveModalDoc(null)}
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-xs font-bold transition-all border border-slate-700"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
