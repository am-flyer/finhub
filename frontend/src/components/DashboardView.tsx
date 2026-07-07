import React, { useState, useEffect } from 'react';
import { marked } from 'marked';

interface ImpactAssessment {
  symbol: string;
  score: number;
  reason: string;
  risks?: string[];
  source_titles?: string[];
}

interface MarketSnapshot {
  symbol: string;
  latest_price?: number | null;
  previous_close?: number | null;
  technical_summary?: string | null;
}

interface MetricEvaluation {
  metric: string;
  rating: string;
  value?: string;
  reason: string;
}

interface FundamentalSnapshot {
  symbol: string;
  revenue_growth?: number | null;
  eps_growth?: number | null;
  free_cash_flow?: number | null;
  free_cash_flow_growth?: number | null;
  debt_to_equity?: number | null;
  return_on_equity?: number | null;
  dividend_yield?: number | null;
  payout_ratio?: number | null;
  trailing_pe?: number | null;
  forward_pe?: number | null;
  peg_ratio?: number | null;
  profit_margin?: number | null;
  gross_margin?: number | null;
  market_cap?: number | null;
  notes?: string[];
}

interface BusinessQualityAssessment {
  symbol: string;
  score: number;
  max_score: number;
  rating: string;
  metrics: MetricEvaluation[];
  reason: string;
}

interface NewsItem {
  symbol: string;
  title: string;
  source: string;
  published_at?: string;
  url?: string;
  sentiment_score?: number | null;
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
  const [selectedSymbol, setSelectedSymbol] = useState<string | null>(null);

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

  useEffect(() => {
    const impacts = parsedContext?.impacts || [];
    if (!impacts.length) {
      setSelectedSymbol(null);
      return;
    }

    const currentStillExists = impacts.some((impact: ImpactAssessment) => impact.symbol === selectedSymbol);
    if (!selectedSymbol || !currentStillExists) {
      setSelectedSymbol(impacts[0].symbol);
    }
  }, [parsedContext, selectedSymbol]);

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

  const getQualityDetails = (rating: string) => {
    if (rating === 'strong') {
      return { badge: 'badge-positive', fill: 'fill-positive', label: 'Strong' };
    } else if (rating === 'weak') {
      return { badge: 'badge-negative', fill: 'fill-negative', label: 'Weak' };
    }
    return { badge: 'badge-neutral', fill: 'fill-neutral', label: 'Average' };
  };

  const formatSigned = (value: number) => `${value > 0 ? '+' : ''}${value}`;

  const formatCurrency = (value?: number | null) => {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return 'Not available';
    }
    return `$${value.toLocaleString(undefined, { maximumFractionDigits: value >= 1000 ? 0 : 2 })}`;
  };

  const formatPercentValue = (value?: number | null) => {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return 'Not available';
    }
    return `${(value * 100).toFixed(1)}%`;
  };

  const formatRatio = (value?: number | null) => {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return 'Not available';
    }
    return value.toFixed(2);
  };

  const formatLargeCurrency = (value?: number | null) => {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return 'Not available';
    }
    const absValue = Math.abs(value);
    if (absValue >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(2)}T`;
    if (absValue >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`;
    if (absValue >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
    return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
  };

  const impacts: ImpactAssessment[] = parsedContext?.impacts || [];
  const news: NewsItem[] = parsedContext?.news || [];
  const filings: FilingItem[] = parsedContext?.filings || [];
  const marketSnapshots: MarketSnapshot[] = parsedContext?.market_snapshots || [];
  const businessQuality: BusinessQualityAssessment[] = parsedContext?.business_quality || [];
  const fundamentalSnapshots: FundamentalSnapshot[] = parsedContext?.fundamental_snapshots || [];

  const selectedImpact = impacts.find((item) => item.symbol === selectedSymbol) || impacts[0];
  const selectedNews = selectedImpact
    ? news.filter((item) => item.symbol === selectedImpact.symbol)
    : [];
  const selectedFilings = selectedImpact
    ? filings.filter((item) => item.symbol === selectedImpact.symbol)
    : [];
  const selectedMarket = selectedImpact
    ? marketSnapshots.find((item) => item.symbol === selectedImpact.symbol)
    : undefined;
  const selectedQuality = selectedImpact
    ? businessQuality.find((item) => item.symbol === selectedImpact.symbol)
    : undefined;
  const selectedFundamentals = selectedImpact
    ? fundamentalSnapshots.find((item) => item.symbol === selectedImpact.symbol)
    : undefined;

  const sentimentValues = selectedNews
    .map((item) => item.sentiment_score)
    .filter((value): value is number => typeof value === 'number');
  const averageSentiment = sentimentValues.length
    ? sentimentValues.reduce((sum, value) => sum + value, 0) / sentimentValues.length
    : 0;
  const positiveNewsCount = sentimentValues.filter((value) => value > 0.1).length;
  const negativeNewsCount = sentimentValues.filter((value) => value < -0.1).length;
  const neutralNewsCount = Math.max(0, selectedNews.length - positiveNewsCount - negativeNewsCount);
  const priceChangePercent = selectedMarket?.latest_price && selectedMarket?.previous_close
    ? (selectedMarket.latest_price - selectedMarket.previous_close) / selectedMarket.previous_close
    : null;
  const sentimentContribution = Math.round(averageSentiment * 70);
  const priceContribution = priceChangePercent === null
    ? 0
    : Math.round(Math.max(Math.min(priceChangePercent * 5, 1), -1) * 30);

  const fundamentalRows = selectedFundamentals ? [
    { label: 'Revenue growth', value: formatPercentValue(selectedFundamentals.revenue_growth) },
    { label: 'EPS growth', value: formatPercentValue(selectedFundamentals.eps_growth) },
    { label: 'Free cash flow', value: formatLargeCurrency(selectedFundamentals.free_cash_flow) },
    { label: 'Free cash flow growth', value: formatPercentValue(selectedFundamentals.free_cash_flow_growth) },
    { label: 'Debt to equity', value: selectedFundamentals.debt_to_equity === null || selectedFundamentals.debt_to_equity === undefined ? 'Not available' : `${(selectedFundamentals.debt_to_equity / 100).toFixed(2)}` },
    { label: 'Return on equity', value: formatPercentValue(selectedFundamentals.return_on_equity) },
    { label: 'Dividend yield', value: formatPercentValue(selectedFundamentals.dividend_yield) },
    { label: 'Payout ratio', value: formatPercentValue(selectedFundamentals.payout_ratio) },
    { label: 'Trailing P/E', value: formatRatio(selectedFundamentals.trailing_pe) },
    { label: 'Forward P/E', value: formatRatio(selectedFundamentals.forward_pe) },
    { label: 'PEG ratio', value: formatRatio(selectedFundamentals.peg_ratio) },
    { label: 'Profit margin', value: formatPercentValue(selectedFundamentals.profit_margin) },
    { label: 'Gross margin', value: formatPercentValue(selectedFundamentals.gross_margin) },
    { label: 'Market cap', value: formatLargeCurrency(selectedFundamentals.market_cap) },
  ] : [];

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
              {impacts.length > 0 ? (
                impacts.map((imp: ImpactAssessment, idx: number) => {
                  const details = getScoreDetails(imp.score);
                  const scorePercent = Math.min(100, Math.max(0, Math.abs(imp.score)));
                  return (
                    <button
                      className={`impact-card impact-card-selectable ${selectedImpact?.symbol === imp.symbol ? 'active' : ''}`}
                      key={idx}
                      onClick={() => setSelectedSymbol(imp.symbol)}
                    >
                      <div className="impact-card-header">
                        <span className="impact-symbol">{imp.symbol}</span>
                        <span className={`impact-badge ${details.badge}`}>{details.label}</span>
                      </div>
                      <div className="score-meter-container">
                        <span>Score: {formatSigned(imp.score)}</span>
                        <div className="score-meter">
                          <div className={`score-fill ${details.fill}`} style={{ width: `${scorePercent}%` }}></div>
                        </div>
                      </div>
                      <div className="impact-card-body">
                        <p>{imp.reason}</p>
                      </div>
                    </button>
                  );
                })
              ) : (
                <p className="text-muted">No holding impact assessments computed for this report.</p>
              )}
            </div>

            <h3>Business Quality Scores</h3>
            <div className="impact-cards-list">
              {businessQuality.length > 0 ? (
                businessQuality.map((quality: BusinessQualityAssessment, idx: number) => {
                  const details = getQualityDetails(quality.rating);
                  const scorePercent = Math.min(100, Math.max(0, (quality.score / quality.max_score) * 100));
                  const goodMetrics = quality.metrics
                    .filter((metric) => metric.rating === 'good')
                    .map((metric) => metric.metric)
                    .slice(0, 3)
                    .join(', ');

                  return (
                    <button
                      className={`impact-card impact-card-selectable ${selectedImpact?.symbol === quality.symbol ? 'active' : ''}`}
                      key={idx}
                      onClick={() => setSelectedSymbol(quality.symbol)}
                    >
                      <div className="impact-card-header">
                        <span className="impact-symbol">{quality.symbol}</span>
                        <span className={`impact-badge ${details.badge}`}>{details.label}</span>
                      </div>
                      <div className="score-meter-container">
                        <span>Score: {quality.score}/{quality.max_score}</span>
                        <div className="score-meter">
                          <div className={`score-fill ${details.fill}`} style={{ width: `${scorePercent}%` }}></div>
                        </div>
                      </div>
                      <div className="impact-card-body">
                        <p>{quality.reason}</p>
                        {goodMetrics && <p>Strong areas: {goodMetrics}</p>}
                      </div>
                    </button>
                  );
                })
              ) : (
                <p className="text-muted">No business quality scores computed for this report.</p>
              )}
            </div>
          </div>

          {/* Right Column: Selected Holding Details */}
          <div className="summary-column">
            <h3>{selectedImpact ? `${selectedImpact.symbol} Detail View` : 'Holding Details'}</h3>

            {selectedImpact ? (
              <>
                <div className="detail-panel score-detail-panel">
                  <div className="detail-panel-header">
                    <div>
                      <span className="detail-eyebrow">Impact score</span>
                      <h4>{selectedImpact.symbol} {formatSigned(selectedImpact.score)}</h4>
                    </div>
                    <span className={`impact-badge ${getScoreDetails(selectedImpact.score).badge}`}>
                      {getScoreDetails(selectedImpact.score).label}
                    </span>
                  </div>
                  <p className="detail-copy">{selectedImpact.reason}</p>
                  <div className="breakdown-grid">
                    <div className="breakdown-item">
                      <span>News sentiment</span>
                      <strong>{formatSigned(sentimentContribution)}</strong>
                    </div>
                    <div className="breakdown-item">
                      <span>Price movement</span>
                      <strong>{formatSigned(priceContribution)}</strong>
                    </div>
                    <div className="breakdown-item">
                      <span>Articles analyzed</span>
                      <strong>{selectedNews.length}</strong>
                    </div>
                    <div className="breakdown-item">
                      <span>Avg sentiment</span>
                      <strong>{averageSentiment.toFixed(2)}</strong>
                    </div>
                  </div>
                  <p className="detail-note">
                    Breakdown values are estimated from the saved report signals. The final score is the stored report score.
                  </p>
                </div>

                <div className="detail-panel">
                  <h4><i className="fa-solid fa-chart-line text-primary"></i> Market Signal</h4>
                  <div className="stat-grid">
                    <div className="stat-row"><span>Latest price</span><strong>{formatCurrency(selectedMarket?.latest_price)}</strong></div>
                    <div className="stat-row"><span>Previous close</span><strong>{formatCurrency(selectedMarket?.previous_close)}</strong></div>
                    <div className="stat-row">
                      <span>Daily change</span>
                      <strong>{priceChangePercent === null ? 'Not available' : formatPercentValue(priceChangePercent)}</strong>
                    </div>
                    <div className="stat-row">
                      <span>Direction</span>
                      <strong>{priceChangePercent === null ? 'Unknown' : priceChangePercent > 0 ? 'Up' : priceChangePercent < 0 ? 'Down' : 'Flat'}</strong>
                    </div>
                  </div>
                </div>

                <div className="detail-panel">
                  <h4><i className="fa-solid fa-newspaper text-primary"></i> News Sentiment</h4>
                  <div className="sentiment-split">
                    <span className="badge-positive">{positiveNewsCount} Positive</span>
                    <span className="badge-neutral">{neutralNewsCount} Neutral</span>
                    <span className="badge-negative">{negativeNewsCount} Negative</span>
                  </div>
                  <div className="signals-list compact">
                    {selectedNews.length > 0 ? (
                      selectedNews.slice(0, 8).map((item: NewsItem, idx: number) => (
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
                        </div>
                      ))
                    ) : (
                      <p className="text-muted" style={{ padding: '10px 0' }}>No news signals found for this holding.</p>
                    )}
                  </div>
                </div>

                <div className="detail-panel">
                  <h4><i className="fa-solid fa-medal text-secondary"></i> Business Quality Breakdown</h4>
                  {selectedQuality ? (
                    <>
                      <div className="quality-score-row">
                        <span className={`impact-badge ${getQualityDetails(selectedQuality.rating).badge}`}>
                          {getQualityDetails(selectedQuality.rating).label}
                        </span>
                        <strong>{selectedQuality.score}/{selectedQuality.max_score}</strong>
                      </div>
                      <div className="metric-list">
                        {selectedQuality.metrics.map((metric) => (
                          <div className="metric-row" key={metric.metric}>
                            <div className="metric-row-top">
                              <strong>{metric.metric}</strong>
                              <span className={`metric-rating rating-${metric.rating}`}>{metric.rating}</span>
                            </div>
                            {metric.value && <span className="metric-value">{metric.value}</span>}
                            <p>{metric.reason}</p>
                          </div>
                        ))}
                      </div>
                    </>
                  ) : (
                    <p className="text-muted">No business quality score found for this holding.</p>
                  )}
                </div>

                <div className="detail-panel">
                  <h4><i className="fa-solid fa-table-list text-secondary"></i> Fundamental Snapshot</h4>
                  {selectedFundamentals ? (
                    <>
                      <div className="fundamentals-grid">
                        {fundamentalRows.map((row) => (
                          <div className="fundamental-row" key={row.label}>
                            <span>{row.label}</span>
                            <strong>{row.value}</strong>
                          </div>
                        ))}
                      </div>
                      {selectedFundamentals.notes && selectedFundamentals.notes.length > 0 && (
                        <div className="fundamental-notes">
                          {selectedFundamentals.notes.slice(0, 3).map((note) => (
                            <p key={note}>{note}</p>
                          ))}
                        </div>
                      )}
                    </>
                  ) : (
                    <p className="text-muted">No fundamental snapshot found for this holding.</p>
                  )}
                </div>

                <div className="detail-panel">
                  <h4><i className="fa-solid fa-file-signature text-secondary"></i> SEC EDGAR Filings</h4>
                  <div className="signals-list compact">
                    {selectedFilings.length > 0 ? (
                      selectedFilings.map((item: FilingItem, idx: number) => (
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
                        </div>
                      ))
                    ) : (
                      <p className="text-muted" style={{ padding: '10px 0' }}>No corporate filings found for this holding.</p>
                    )}
                  </div>
                </div>
              </>
            ) : (
              <div className="detail-panel">
                <p className="text-muted">Select a holding to inspect its report signals.</p>
              </div>
            )}
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
