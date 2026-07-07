import React, { useState } from 'react';

interface ReportMeta {
  id: number;
  created_at: string;
  title: string;
  summary: string;
  holding_count: number;
  watchlist_count: number;
}

interface ReportHistoryViewProps {
  reports: ReportMeta[];
  onViewReport: (id: number) => void;
  onDeleteReport: (id: number) => void;
  loading: boolean;
  holdingCount?: number;
  watchlistCount?: number;
}

export const ReportHistoryView: React.FC<ReportHistoryViewProps> = ({
  reports,
  onViewReport,
  onDeleteReport,
  loading,
  holdingCount = 0,
  watchlistCount = 0,
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'newest' | 'oldest'>('newest');
  const [dateFilter, setDateFilter] = useState('');

  // Filter and sort reports
  const filteredReports = reports
    .filter((rep) => {
      const term = searchTerm.toLowerCase();
      const matchesSearch = 
        rep.title.toLowerCase().includes(term) ||
        (rep.summary && rep.summary.toLowerCase().includes(term)) ||
        rep.created_at.includes(term);

      const matchesDate = !dateFilter || rep.created_at.startsWith(dateFilter);

      return matchesSearch && matchesDate;
    })
    .sort((a, b) => {
      const dateA = new Date(a.created_at).getTime();
      const dateB = new Date(b.created_at).getTime();
      return sortBy === 'newest' ? dateB - dateA : dateA - dateB;
    });

  return (
    <div className="workspace" style={{ width: '100%' }}>
      <style>{`
        .history-layout {
          display: flex;
          flex-direction: column;
          gap: 24px;
          width: 100%;
        }
        .stats-summary-row {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
          gap: 16px;
        }
        .stat-history-card {
          background-color: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 16px;
          padding: 20px;
          display: flex;
          flex-direction: column;
          gap: 6px;
          backdrop-filter: blur(8px);
        }
        .stat-history-card .label {
          font-size: 0.78rem;
          color: var(--text-muted);
          text-transform: uppercase;
          font-weight: 600;
        }
        .stat-history-card .value {
          font-size: 1.8rem;
          font-weight: 700;
          font-family: var(--font-heading);
          color: var(--text-main);
        }
        .history-controls {
          display: flex;
          flex-direction: column;
          gap: 16px;
          background-color: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 16px;
          padding: 16px 20px;
          backdrop-filter: blur(8px);
        }
        @media (min-width: 768px) {
          .history-controls {
            flex-direction: row;
            align-items: center;
            justify-content: space-between;
          }
        }
        .search-input-wrapper {
          position: relative;
          flex-grow: 1;
          max-width: 480px;
        }
        .search-input-wrapper i {
          position: absolute;
          left: 14px;
          top: 50%;
          transform: translateY(-50%);
          color: var(--text-muted);
          font-size: 0.9rem;
        }
        .search-input-wrapper input {
          width: 100%;
          background: rgba(0, 0, 0, 0.2);
          border: 1px solid var(--border-color);
          border-radius: 10px;
          padding: 10px 16px 10px 40px;
          color: var(--text-main);
          font-size: 0.9rem;
          font-family: var(--font-body);
        }
        .search-input-wrapper input:focus {
          outline: none;
          border-color: var(--primary);
        }
        .sort-select-wrapper {
          display: flex;
          align-items: center;
          gap: 10px;
          font-size: 0.9rem;
          color: var(--text-muted);
        }
        .sort-select {
          background: rgba(0, 0, 0, 0.2);
          border: 1px solid var(--border-color);
          border-radius: 10px;
          padding: 8px 12px;
          color: var(--text-main);
          font-size: 0.85rem;
          font-family: var(--font-body);
          outline: none;
          cursor: pointer;
        }
        .reports-grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 16px;
        }
        @media (min-width: 768px) {
          .reports-grid {
            grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
          }
        }
        .report-history-card {
          background-color: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 16px;
          padding: 20px;
          display: flex;
          flex-direction: column;
          justify-content: space-between;
          gap: 16px;
          backdrop-filter: blur(8px);
          transition: var(--transition-fast);
        }
        .report-history-card:hover {
          border-color: rgba(255, 255, 255, 0.12);
          background-color: rgba(255, 255, 255, 0.02);
        }
        .card-header-meta {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
        }
        .card-date {
          font-size: 0.75rem;
          color: var(--text-muted);
          font-weight: 500;
        }
        .card-badges {
          display: flex;
          gap: 6px;
        }
        .card-badge {
          font-size: 0.7rem;
          font-weight: 700;
          padding: 2px 6px;
          border-radius: 4px;
        }
        .card-badge-holdings {
          background-color: var(--primary-glow);
          color: #a78bfa;
        }
        .card-badge-watchlist {
          background-color: var(--warning-glow);
          color: var(--warning);
        }
        .card-title {
          font-family: var(--font-heading);
          font-size: 0.95rem;
          font-weight: 700;
          color: var(--text-main);
          line-height: 1.3;
        }
        .card-summary {
          font-size: 0.8rem;
          color: var(--text-muted);
          line-height: 1.4;
          display: -webkit-box;
          -webkit-line-clamp: 3;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
        .card-actions {
          display: flex;
          gap: 10px;
          border-top: 1px solid var(--border-color);
          padding-top: 12px;
          margin-top: 8px;
        }
        .card-btn {
          flex-grow: 1;
          display: flex;
          align-items: center;
          justify-content: center;
          gap: 6px;
          padding: 8px 12px;
          border-radius: 8px;
          font-size: 0.8rem;
          font-weight: 600;
          cursor: pointer;
          transition: var(--transition-fast);
          border: 1px solid var(--border-color);
          background: rgba(255, 255, 255, 0.01);
          color: var(--text-main);
        }
        .card-btn:hover {
          background: rgba(255, 255, 255, 0.05);
        }
        .card-btn-view {
          border-color: var(--primary);
          color: var(--primary);
        }
        .card-btn-view:hover {
          background-color: var(--primary-glow);
        }
        .card-btn-delete {
          max-width: 44px;
          color: var(--danger);
        }
        .card-btn-delete:hover {
          background-color: var(--danger-glow);
          border-color: var(--danger);
        }
      `}</style>

      <div className="history-layout">
        {/* Statistics row */}
        <div className="stats-summary-row">
          <div className="stat-history-card">
            <span className="label">Total Reports</span>
            <span className="value">{loading ? '...' : reports.length}</span>
          </div>
          <div className="stat-history-card">
            <span className="label">Timeframe</span>
            <span className="value">{reports.length > 0 ? '30 Days' : '0 Days'}</span>
          </div>
          <div className="stat-history-card">
            <span className="label">Latest Output</span>
            <span className="value" style={{ fontSize: '1rem', paddingTop: '10px' }}>
              {reports.length > 0
                ? new Date(reports[0].created_at).toLocaleDateString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                  })
                : 'None'}
            </span>
          </div>
        </div>

        {/* Filter Toolbar */}
        <div className="history-controls">
          <div className="search-input-wrapper">
            <i className="fa-solid fa-magnifying-glass"></i>
            <input
              type="text"
              placeholder="Search reports by date or summary content..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>

          <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
            <div className="sort-select-wrapper">
              <span>Date:</span>
              <input
                type="date"
                className="sort-select"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value)}
              />
              {dateFilter && (
                <button
                  className="btn btn-secondary"
                  style={{ padding: '6px 12px', fontSize: '0.8rem' }}
                  onClick={() => setDateFilter('')}
                >
                  Clear
                </button>
              )}
            </div>

            <div className="sort-select-wrapper">
              <span>Sort by:</span>
              <select
                className="sort-select"
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value as 'newest' | 'oldest')}
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
              </select>
            </div>
          </div>
        </div>

        {/* Reports Grid */}
        {loading ? (
          <div className="loading-state" style={{ padding: '60px 0' }}>
            <i className="fa-solid fa-circle-notch fa-spin" style={{ fontSize: '2rem' }}></i>
            <span>Loading historical archives...</span>
          </div>
        ) : filteredReports.length > 0 ? (
          <div className="reports-grid">
            {filteredReports.map((rep) => (
              <div className="report-history-card" key={rep.id}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div className="card-header-meta">
                    <span className="card-date">
                      {new Date(rep.created_at).toLocaleString(undefined, {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </span>
                    <div className="card-badges">
                      <span className="card-badge card-badge-holdings">H: {holdingCount}</span>
                      <span className="card-badge card-badge-watchlist">W: {watchlistCount}</span>
                    </div>
                  </div>

                  <div className="card-title">{rep.title}</div>
                  <div className="card-summary">{rep.summary || 'No summary text available.'}</div>
                </div>

                <div className="card-actions">
                  <button className="card-btn card-btn-view" onClick={() => onViewReport(rep.id)}>
                    <i className="fa-solid fa-eye"></i> View Report
                  </button>
                  <button
                    className="card-btn card-btn-delete"
                    onClick={() => onDeleteReport(rep.id)}
                    title="Delete Record"
                  >
                    <i className="fa-solid fa-trash-can"></i>
                  </button>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="loading-state" style={{ padding: '60px 0' }}>
            <i className="fa-solid fa-folder-open" style={{ fontSize: '2rem' }}></i>
            <span>No matching report logs found.</span>
          </div>
        )}
      </div>
    </div>
  );
};
