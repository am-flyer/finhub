import React, { useState, useEffect } from 'react';
import { DashboardView } from './components/DashboardView';
import { HoldingsListView } from './components/HoldingsListView';
import { AssetFormView } from './components/AssetFormView';
import { AnalyticsView } from './components/AnalyticsView';
import { ReportHistoryView } from './components/ReportHistoryView';

interface Position {
  symbol: string;
  name: string | null;
  quantity: number;
  average_cost: number | null;
  scope: 'holding' | 'watchlist';
}

interface ReportMeta {
  id: number;
  created_at: string;
  title: string;
  summary: string;
  holding_count: number;
  watchlist_count: number;
}

interface Report {
  id: number;
  created_at: string;
  title: string;
  content: string;
  summary: string;
  holding_count: number;
  watchlist_count: number;
  json_data?: string;
}

export default function App() {
  const [view, setView] = useState<'dashboard' | 'holdings' | 'add-asset' | 'analytics' | 'history'>('dashboard');
  const [reportsList, setReportsList] = useState<ReportMeta[]>([]);
  const [positionsList, setPositionsList] = useState<Position[]>([]);
  const [activeReportId, setActiveReportId] = useState<number | null>(null);
  const [activeReport, setActiveReport] = useState<Report | null>(null);
  const [editingPosition, setEditingPosition] = useState<Position | null>(null);
  
  // Loading Overlay states
  const [loadingOverlay, setLoadingOverlay] = useState(false);
  const [loadingStatus, setLoadingStatus] = useState('');
  const [stepState, setStepState] = useState({
    collect: 'todo' as 'todo' | 'active' | 'done',
    process: 'todo' as 'todo' | 'active' | 'done',
    generate: 'todo' as 'todo' | 'active' | 'done'
  });

  const [sidebarLoading, setSidebarLoading] = useState(false);
  const [reportDetailsLoading, setReportDetailsLoading] = useState(false);

  // Fetch initial data
  useEffect(() => {
    fetchReports();
    fetchPositions();
  }, []);

  // Fetch detailed report when active ID changes
  useEffect(() => {
    if (activeReportId !== null) {
      fetchReportDetails(activeReportId);
    } else {
      setActiveReport(null);
    }
  }, [activeReportId]);

  const fetchReports = async () => {
    setSidebarLoading(true);
    try {
      const res = await fetch('/api/reports');
      if (!res.ok) throw new Error('Failed to fetch reports');
      const data = await res.json();
      setReportsList(data);
      if (data.length > 0 && activeReportId === null) {
        setActiveReportId(data[0].id);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setSidebarLoading(false);
    }
  };

  const fetchPositions = async () => {
    try {
      const res = await fetch('/api/positions');
      if (!res.ok) throw new Error('Failed to fetch positions');
      const data = await res.json();
      setPositionsList(data);
    } catch (e) {
      console.error(e);
    }
  };

  const fetchReportDetails = async (id: number) => {
    setReportDetailsLoading(true);
    try {
      const res = await fetch(`/api/reports/${id}`);
      if (!res.ok) throw new Error('Failed to fetch report details');
      const data = await res.json();
      setActiveReport(data);
    } catch (e) {
      console.error(e);
    } finally {
      setReportDetailsLoading(false);
    }
  };

  const handleGenerateReport = async () => {
    setLoadingOverlay(true);
    setStepState({ collect: 'active', process: 'todo', generate: 'todo' });
    setLoadingStatus('Gathering signals from yfinance & SEC EDGAR...');

    const timer1 = setTimeout(() => {
      setStepState(s => ({ ...s, collect: 'done', process: 'active' }));
      setLoadingStatus('Computing holding sentiment and impact scores...');
    }, 6000);

    const timer2 = setTimeout(() => {
      setStepState(s => ({ ...s, process: 'done', generate: 'active' }));
      setLoadingStatus('Asking Gemini AI to draft pre-market review...');
    }, 12000);

    try {
      const res = await fetch('/api/reports/generate', { method: 'POST' });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `HTTP ${res.status}`);
      }
      const data = await res.json();
      
      clearTimeout(timer1);
      clearTimeout(timer2);
      
      setStepState({ collect: 'done', process: 'done', generate: 'done' });
      
      setTimeout(async () => {
        setLoadingOverlay(false);
        await fetchReports();
        if (data.id) {
          setActiveReportId(data.id);
          setView('dashboard');
        }
      }, 600);
    } catch (err: any) {
      clearTimeout(timer1);
      clearTimeout(timer2);
      console.error("Report generation failed:", err);
      alert(`Report generation failed: ${err.message}`);
      setLoadingOverlay(false);
    }
  };

  const navigateToAddAsset = () => {
    setEditingPosition(null);
    setView('add-asset');
  };

  const navigateToEditAsset = (pos: Position) => {
    setEditingPosition(pos);
    setView('add-asset');
  };

  const handleRefresh = () => {
    fetchPositions();
    fetchReports();
  };

  const handleDeleteReport = async (id: number) => {
    if (!window.confirm("Are you sure you want to delete this report from your history?")) {
      return;
    }
    try {
      const res = await fetch(`/api/reports/${id}`, {
        method: 'DELETE'
      });
      if (!res.ok) throw new Error('Failed to delete report');
      
      if (activeReportId === id) {
        const remaining = reportsList.filter(r => r.id !== id);
        if (remaining.length > 0) {
          setActiveReportId(remaining[0].id);
        } else {
          setActiveReportId(null);
          setActiveReport(null);
        }
      }
      
      await fetchReports();
    } catch (e) {
      console.error(e);
      alert("Failed to delete report.");
    }
  };

  return (
    <div className="app-container">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-header">
          <div className="logo" onClick={() => setView('dashboard')}>
            <i className="fa-solid fa-chart-line-up font-gradient"></i>
            <span className="font-gradient">FinHub</span>
          </div>
          <div className="budget-badge">
            <span className="label">Budget</span>
            <span className="value">$100/mo</span>
          </div>
        </div>

        {/* Sidebar Nav */}
        <div className="nav-links">
          <div 
            className={`nav-item ${view === 'dashboard' ? 'active' : ''}`}
            onClick={() => setView('dashboard')}
          >
            <i className="fa-solid fa-gauge-high"></i>
            <span>Dashboard</span>
          </div>
          <div 
            className={`nav-item ${view === 'holdings' ? 'active' : ''}`}
            onClick={() => setView('holdings')}
          >
            <i className="fa-solid fa-briefcase"></i>
            <span>My Assets</span>
          </div>
          
          {/* Show Add New Asset only when viewing holdings (My Assets) or adding/editing an asset */}
          {(view === 'holdings' || view === 'add-asset') && (
            <div 
              className={`nav-item ${view === 'add-asset' && !editingPosition ? 'active' : ''}`}
              onClick={navigateToAddAsset}
              style={{ paddingLeft: '28px', fontSize: '0.9rem' }}
            >
              <i className="fa-solid fa-plus-circle"></i>
              <span>Add New Asset</span>
            </div>
          )}

          <div 
            className={`nav-item ${view === 'analytics' ? 'active' : ''}`}
            onClick={() => setView('analytics')}
          >
            <i className="fa-solid fa-chart-line"></i>
            <span>Analytics</span>
          </div>

          <div 
            className={`nav-item ${view === 'history' ? 'active' : ''}`}
            onClick={() => setView('history')}
          >
            <i className="fa-solid fa-clock-rotate-left"></i>
            <span>Report History</span>
          </div>
        </div>

        {/* Generate Button */}
        <button 
          className="btn btn-primary btn-generate" 
          onClick={handleGenerateReport}
          disabled={loadingOverlay}
        >
          <i className="fa-solid fa-wand-magic-sparkles"></i>
          <span>Generate Report</span>
        </button>
      </aside>

      {/* Main Content Pane */}
      <main className="main-content">
        {/* Header Navigation */}
        <header className="navbar">
          <h1>
            {view === 'dashboard' && (reportDetailsLoading ? 'Loading report...' : (activeReport ? activeReport.title : 'Select a Report'))}
            {view === 'holdings' && 'My Assets'}
            {view === 'add-asset' && (editingPosition ? `Edit Asset: ${editingPosition.symbol}` : 'Add Asset to Portfolio')}
            {view === 'analytics' && 'Portfolio Performance & Market Events'}
            {view === 'history' && 'Daily Pre-Market Report History'}
          </h1>
          {view === 'dashboard' && activeReport && !reportDetailsLoading && (
            <div className="report-meta">
              <span className="meta-item">
                <i className="fa-regular fa-calendar"></i>
                <span>
                  {new Date(activeReport.created_at).toLocaleString(undefined, {
                    month: 'short',
                    day: 'numeric',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit',
                  })}
                </span>
              </span>
              <span 
                className="meta-item" 
                onClick={() => setView('holdings')} 
                style={{ cursor: 'pointer', transition: 'color 0.2s' }}
                title="View My Assets"
              >
                <i className="fa-solid fa-briefcase"></i>
                <span>{activeReport.holding_count} Holdings</span>
              </span>
              <span 
                className="meta-item" 
                onClick={() => setView('holdings')} 
                style={{ cursor: 'pointer', transition: 'color 0.2s' }}
                title="View My Assets"
              >
                <i className="fa-solid fa-eye"></i>
                <span>{activeReport.watchlist_count} Watchlist</span>
              </span>
            </div>
          )}
        </header>

        {/* View Router */}
        {view === 'dashboard' && (
          <div className="workspace">
            {reportDetailsLoading ? (
              <div className="loading-state" style={{ margin: 'auto' }}>
                <i className="fa-solid fa-circle-notch fa-spin" style={{ fontSize: '2rem' }}></i>
                <span>Loading report details...</span>
              </div>
            ) : (
              <DashboardView report={activeReport} />
            )}
          </div>
        )}

        {view === 'holdings' && (
          <HoldingsListView 
            positions={positionsList}
            onRefresh={handleRefresh}
            onEdit={navigateToEditAsset}
            onNavigateToAdd={navigateToAddAsset}
          />
        )}

        {view === 'add-asset' && (
          <AssetFormView 
            editingPosition={editingPosition}
            onRefresh={handleRefresh}
            onCancel={() => { setEditingPosition(null); setView('holdings'); }}
          />
        )}

        {view === 'analytics' && (
          <AnalyticsView positions={positionsList} />
        )}

        {view === 'history' && (
          <ReportHistoryView 
            reports={reportsList}
            onViewReport={(id) => {
              setActiveReportId(id);
              setView('dashboard');
            }}
            onDeleteReport={handleDeleteReport}
            loading={sidebarLoading}
          />
        )}
      </main>

      {/* Fullscreen Loading Overlay */}
      {loadingOverlay && (
        <div className="loading-overlay">
          <div className="loading-box">
            <div className="loading-spinner-container">
              <i className="fa-solid fa-circle-notch fa-spin spinner"></i>
              <i className="fa-solid fa-chart-line-up inner-icon"></i>
            </div>
            <h2>Generating Pre-Market Report</h2>
            <p>{loadingStatus}</p>
            <div className="progress-steps">
              <div className={`step ${stepState.collect === 'active' ? 'active' : (stepState.collect === 'done' ? 'done' : '')}`}>
                <i className={stepState.collect === 'done' ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-dot'}></i>
                <span>Collect quotes & filings</span>
              </div>
              <div className={`step ${stepState.process === 'active' ? 'active' : (stepState.process === 'done' ? 'done' : '')}`}>
                <i className={stepState.process === 'done' ? 'fa-solid fa-circle-check' : (stepState.process === 'active' ? 'fa-solid fa-circle-dot' : 'fa-regular fa-circle')}></i>
                <span>Analyze holding impacts</span>
              </div>
              <div className={`step ${stepState.generate === 'active' ? 'active' : (stepState.generate === 'done' ? 'done' : '')}`}>
                <i className={stepState.generate === 'done' ? 'fa-solid fa-circle-check' : (stepState.generate === 'active' ? 'fa-solid fa-circle-dot' : 'fa-regular fa-circle')}></i>
                <span>Generate education report</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
