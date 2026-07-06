import React, { useState, useEffect } from 'react';
import { marked } from 'marked';

interface ImpactAssessment {
  symbol: string;
  score: number;
  reason: string;
  risks?: string[];
  source_titles?: string[];
}

interface NewsItem {
  symbol: string;
  title: string;
  source: string;
  published_at?: string;
  url?: string;
}

interface FilingItem {
  symbol: string;
  form_type: string;
  filed_at?: string;
  title: string;
  url?: string;
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

interface DashboardViewProps {
  report: Report | null;
}

export const DashboardView: React.FC<DashboardViewProps> = ({ report }) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'full'>('summary');
  const [parsedContext, setParsedContext] = useState<any>(null);

  useEffect(() => {
    if (report && report.json_data) {
      try {
        setParsedContext(JSON.parse(report.json_data));
      } catch (e) {
        console.error('Failed to parse report json_data', e);
        setParsedContext(null);
      }
    } else {
      setParsedContext(null);
    }
  }, [report]);

  if (!report) {
    return (
      <div className="welcome-view">
        <div className="welcome-card">
          <i className="fa-solid fa-chart-pie welcome-icon"></i>
          <h2>Select a Report</h2>
          <p>Please choose an existing pre-market report from the sidebar or click the "Generate Report" button to create a fresh one.</p>
        </div>
      </div>
    );
  }

  // Format date helper
  const formatDate = (dateStr: string) => {
    try {
      const date = new Date(dateStr);
      return date.toLocaleString('en-US', {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
      });
    } catch (e) {
      return dateStr;
    }
  };

  const getScoreDetails = (score: number) => {
    if (score > 20) {
      return { badge: 'badge-positive', fill: 'fill-positive', label: 'Positive' };
    } else if (score < -20) {
      return { badge: 'badge-negative', fill: 'fill-negative', label: 'Negative' };
    }
    return { badge: 'badge-neutral', fill: 'fill-neutral', label: 'Mixed/Neutral' };
  };

  return (
    <div className="report-view">
      <div className="tabs-container">
        <button 
          className={`tab-btn ${activeTab === 'summary' ? 'active' : ''}`}
          onClick={() => setActiveTab('summary')}
        >
          <i className="fa-solid fa-chart-bar"></i> Impact Summary
        </button>
        <button 
          className={`tab-btn ${activeTab === 'full' ? 'active' : ''}`}
          onClick={() => setActiveTab('full')}
        >
          <i className="fa-solid fa-file-lines"></i> Full AI Report
        </button>
      </div>

      {activeTab === 'summary' ? (
        <div className="summary-grid">
          {/* Left Column: Impact Cards */}
          <div className="summary-column">
            <h3>Holdings Impact Assessments</h3>
            <div className="impact-cards-list">
              {parsedContext && parsedContext.impacts && parsedContext.impacts.length > 0 ? (
                parsedContext.impacts.map((imp: ImpactAssessment, idx: number) => {
                  const details = getScoreDetails(imp.score);
                  const scorePercent = Math.min(100, Math.max(0, Math.abs(imp.score)));
                  return (
                    <div className="impact-card" key={idx}>
                      <div className="impact-card-header">
                        <span className="impact-symbol">{imp.symbol}</span>
                        <span className={`impact-badge ${details.badge}`}>{details.label}</span>
                      </div>
                      <div className="score-meter-container">
                        <span>Score: {imp.score > 0 ? '+' : ''}{imp.score}</span>
                        <div className="score-meter">
                          <div className={`score-fill ${details.fill}`} style={{ width: `${scorePercent}%` }}></div>
                        </div>
                      </div>
                      <div className="impact-card-body">
                        <p>{imp.reason}</p>
                      </div>
                    </div>
                  );
                })
              ) : (
                <p className="text-muted">No holding impact assessments computed for this report.</p>
              )}
            </div>
          </div>

          {/* Right Column: Signals */}
          <div className="summary-column">
            <h3>Data Signals Analyzed</h3>
            
            <div className="signal-section">
              <h4><i className="fa-solid fa-newspaper text-primary"></i> Market & News Sentiment</h4>
              <div className="signals-list">
                {parsedContext && parsedContext.news && parsedContext.news.length > 0 ? (
                  parsedContext.news.map((item: NewsItem, idx: number) => (
                    <div className="signal-item" key={idx}>
                      <div className="signal-item-header">
                        <span>{item.source || 'News Source'}</span>
                        {item.published_at && <span>{formatDate(item.published_at)}</span>}
                      </div>
                      {item.url ? (
                        <a href={item.url} target="_blank" rel="noopener noreferrer" className="signal-item-title">
                          {item.title}
                        </a>
                      ) : (
                        <span className="signal-item-title">{item.title}</span>
                      )}
                      <span className="badge-tag">{item.symbol}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-muted" style={{ padding: '10px 0' }}>No news signals found for this period.</p>
                )}
              </div>
            </div>

            <div className="signal-section">
              <h4><i className="fa-solid fa-file-signature text-secondary"></i> SEC EDGAR Filings</h4>
              <div className="signals-list">
                {parsedContext && parsedContext.filings && parsedContext.filings.length > 0 ? (
                  parsedContext.filings.map((item: FilingItem, idx: number) => (
                    <div className="signal-item" key={idx}>
                      <div className="signal-item-header">
                        <span>Form {item.form_type}</span>
                        {item.filed_at && <span>{formatDate(item.filed_at)}</span>}
                      </div>
                      {item.url ? (
                        <a href={item.url} target="_blank" rel="noopener noreferrer" className="signal-item-title">
                          {item.title}
                        </a>
                      ) : (
                        <span className="signal-item-title">{item.title}</span>
                      )}
                      <span className="badge-tag">{item.symbol}</span>
                    </div>
                  ))
                ) : (
                  <p className="text-muted" style={{ padding: '10px 0' }}>No corporate filings found for this period.</p>
                )}
              </div>
            </div>
          </div>
        </div>
      ) : (
        <div className="tab-content active">
          <article 
            className="markdown-body"
            dangerouslySetInnerHTML={{ __html: marked.parse(report.content) }}
          />
        </div>
      )}
    </div>
  );
};
