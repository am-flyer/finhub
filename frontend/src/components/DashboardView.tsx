import React, { useEffect, useMemo, useState } from 'react';
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

interface Position {
  symbol: string;
  name?: string | null;
}

interface ReportContext {
  positions?: Position[];
  impacts?: ImpactAssessment[];
  market_snapshots?: MarketSnapshot[];
  news?: NewsItem[];
  filings?: FilingItem[];
  business_quality?: BusinessQualityAssessment[];
  fundamental_snapshots?: FundamentalSnapshot[];
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

interface HoldingSummary {
  symbol: string;
  name?: string | null;
  impact?: ImpactAssessment;
  quality?: BusinessQualityAssessment;
  market?: MarketSnapshot;
  fundamentals?: FundamentalSnapshot;
  news: NewsItem[];
  filings: FilingItem[];
  impactScore10: number;
  qualityScore10: number;
  newsScore10: number;
  priceScore10: number;
  avgSentiment10: number;
  combinedScore10: number;
  priceChangePercent: number | null;
  averageSentiment: number;
}

type DetailTab = 'impact' | 'business';

const clamp = (value: number, min: number, max: number) => Math.min(max, Math.max(min, value));

export const DashboardView: React.FC<DashboardViewProps> = ({ report }) => {
  const [activeTab, setActiveTab] = useState<'summary' | 'full'>('summary');
  const [detailTab, setDetailTab] = useState<DetailTab>('impact');
  const [parsedContext, setParsedContext] = useState<ReportContext | null>(null);
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
    setSelectedSymbol(null);
    setDetailTab('impact');
  }, [report]);

  const holdings = useMemo(() => buildHoldingSummaries(parsedContext), [parsedContext]);
  const selectedHolding = selectedSymbol
    ? holdings.find((holding) => holding.symbol === selectedSymbol) || null
    : null;

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

  const openDetail = (symbol: string) => {
    setSelectedSymbol(symbol);
    setDetailTab('impact');
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
        selectedHolding ? (
          <HoldingDetailView
            holding={selectedHolding}
            activeTab={detailTab}
            onTabChange={setDetailTab}
            onBack={() => setSelectedSymbol(null)}
          />
        ) : (
          <HoldingSummaryView holdings={holdings} onOpenDetail={openDetail} />
        )
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

const HoldingSummaryView: React.FC<{
  holdings: HoldingSummary[];
  onOpenDetail: (symbol: string) => void;
}> = ({ holdings, onOpenDetail }) => (
  <div className="holding-summary-view">
    <div className="summary-page-header">
      <div>
        <h3>Holding Summary</h3>
        <p>Combined score blends impact, business quality, news sentiment, and price movement on a 10-point scale.</p>
      </div>
      <div className="score-legend">
        <span className="legend-green">Green 7-10</span>
        <span className="legend-amber">Amber 4-6.9</span>
        <span className="legend-red">Red below 4</span>
      </div>
    </div>
    <div className="score-explainer-grid">
      <div><strong>Combined</strong><span>35% impact, 35% quality, 20% news, 10% price.</span></div>
      <div><strong>Impact</strong><span>Short-term -100 to +100 score mapped to 0-10.</span></div>
      <div><strong>Quality</strong><span>Business quality score, converted from 0-8 to 0-10.</span></div>
      <div><strong>News</strong><span>Average article sentiment, scaled from -1..1 to 0-10.</span></div>
      <div><strong>Price</strong><span>Daily move vs previous close, centered around 5/10.</span></div>
      <div><strong>Articles</strong><span>Number of stock-specific news items analyzed.</span></div>
      <div><strong>Avg Sent</strong><span>Average news tone shown as a 10-point score.</span></div>
    </div>

    {holdings.length > 0 ? (
      <div className="holding-score-list">
        {holdings.map((holding) => (
          <button className="holding-score-card" key={holding.symbol} onClick={() => onOpenDetail(holding.symbol)}>
            <div className="holding-identity">
              <div>
                <strong>{holding.symbol}</strong>
                <span className="summary-status status-details">
                  More Details
                  <i className="fa-solid fa-arrow-right"></i>
                </span>
              </div>
              {holding.name && <span>{holding.name}</span>}
            </div>
            <div className="holding-score-card-grid">
              <ScoreCell label="Combined" value={holding.combinedScore10} display={`${holding.combinedScore10.toFixed(1)}/10`} />
              <ScoreCell label="Impact" value={holding.impactScore10} display={holding.impact ? signed(holding.impact.score) : 'N/A'} />
              <ScoreCell label="Quality" value={holding.qualityScore10} display={holding.quality ? `${holding.quality.score}/${holding.quality.max_score}` : 'N/A'} />
              <ScoreCell label="News" value={holding.newsScore10} display={`${holding.newsScore10.toFixed(1)}/10`} />
              <ScoreCell label="Price" value={holding.priceScore10} display={`${holding.priceScore10.toFixed(1)}/10`} />
              <div className="holding-mini-stat">
                <span>Articles</span>
                <strong>{holding.news.length}</strong>
              </div>
              <ScoreCell label="Avg Sent" value={holding.avgSentiment10} display={`${holding.avgSentiment10.toFixed(1)}/10`} />
            </div>
          </button>
        ))}
      </div>
    ) : (
      <p className="text-muted">No holding scores computed for this report.</p>
    )}
  </div>
);

const ScoreCell: React.FC<{ label: string; value: number; display: string }> = ({ label, value, display }) => {
  const tone = scoreTone(value);
  return (
    <div className="score-cell">
      <div className="score-cell-top">
        <span>{label}</span>
        <strong className={`score-text-${tone}`}>{display}</strong>
      </div>
      <div className="mini-score-meter">
        <div className={`mini-score-fill fill-${tone}`} style={{ width: `${clamp(value, 0, 10) * 10}%` }}></div>
      </div>
    </div>
  );
};

const HoldingDetailView: React.FC<{
  holding: HoldingSummary;
  activeTab: DetailTab;
  onTabChange: (tab: DetailTab) => void;
  onBack: () => void;
}> = ({ holding, activeTab, onTabChange, onBack }) => {
  const positiveNewsCount = holding.news.filter((item) => (item.sentiment_score || 0) > 0.1).length;
  const negativeNewsCount = holding.news.filter((item) => (item.sentiment_score || 0) < -0.1).length;
  const neutralNewsCount = Math.max(0, holding.news.length - positiveNewsCount - negativeNewsCount);
  const fundamentalRows = buildFundamentalRows(holding.fundamentals);

  return (
    <div className="holding-detail-view">
      <div className="detail-page-header">
        <button className="btn btn-secondary" onClick={onBack}>
          <i className="fa-solid fa-arrow-left"></i>
          <span>Back</span>
        </button>
        <div className="detail-title-block">
          <h3>{holding.symbol}</h3>
          {holding.name && <p>{holding.name}</p>}
        </div>
        <div className={`detail-combined-pill status-${scoreTone(holding.combinedScore10)}`}>
          Combined {holding.combinedScore10.toFixed(1)}/10
        </div>
      </div>

      <div className="detail-kpi-row">
        <ScoreKpi title="Impact" value={holding.impactScore10} detail={holding.impact ? signed(holding.impact.score) : 'N/A'} />
        <ScoreKpi title="Business Quality" value={holding.qualityScore10} detail={holding.quality ? `${holding.quality.score}/${holding.quality.max_score}` : 'N/A'} />
        <ScoreKpi title="News Sentiment" value={holding.newsScore10} detail={`${holding.newsScore10.toFixed(1)}/10`} />
        <ScoreKpi title="Price Movement" value={holding.priceScore10} detail={`${holding.priceScore10.toFixed(1)}/10`} />
      </div>

      <div className="detail-tabs">
        <button className={`detail-tab-btn ${activeTab === 'impact' ? 'active' : ''}`} onClick={() => onTabChange('impact')}>
          Impact & Market
        </button>
        <button className={`detail-tab-btn ${activeTab === 'business' ? 'active' : ''}`} onClick={() => onTabChange('business')}>
          Business & Fundamentals
        </button>
      </div>

      {activeTab === 'impact' ? (
        <div className="detail-section-grid">
          <div className="detail-panel score-detail-panel">
            <div className="detail-panel-header">
              <div>
                <span className="detail-eyebrow">Impact score</span>
                <h4>{holding.impact ? signed(holding.impact.score) : 'N/A'}</h4>
              </div>
              <span className={`summary-status status-${scoreTone(holding.impactScore10)}`}>
                {scoreLabel(holding.impactScore10)}
              </span>
            </div>
            <p className="detail-copy">{holding.impact?.reason || 'No impact explanation is available for this holding.'}</p>
            <div className="breakdown-grid">
              <StatBox label="News sentiment" value={`${holding.newsScore10.toFixed(1)}/10`} tone={scoreTone(holding.newsScore10)} />
              <StatBox label="Price movement" value={`${holding.priceScore10.toFixed(1)}/10`} tone={scoreTone(holding.priceScore10)} />
              <StatBox label="Articles analyzed" value={String(holding.news.length)} />
              <StatBox label="Avg sentiment" value={`${holding.avgSentiment10.toFixed(1)}/10`} tone={scoreTone(holding.avgSentiment10)} />
            </div>
          </div>

          <div className="detail-panel">
            <h4><i className="fa-solid fa-chart-line text-primary"></i> Market Signals</h4>
            <div className="stat-grid">
              <StatBox label="Latest price" value={formatCurrency(holding.market?.latest_price)} />
              <StatBox label="Previous close" value={formatCurrency(holding.market?.previous_close)} />
              <StatBox label="Daily change" value={holding.priceChangePercent === null ? 'Not available' : formatPercent(holding.priceChangePercent)} tone={scoreTone(holding.priceScore10)} />
              <StatBox label="Direction" value={holding.priceChangePercent === null ? 'Unknown' : holding.priceChangePercent > 0 ? 'Up' : holding.priceChangePercent < 0 ? 'Down' : 'Flat'} />
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
              {holding.news.length > 0 ? (
                holding.news.slice(0, 10).map((item, idx) => (
                  <div className="signal-item" key={`${item.title}-${idx}`}>
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
            <h4><i className="fa-solid fa-file-signature text-secondary"></i> SEC EDGAR Filings</h4>
            <div className="signals-list compact">
              {holding.filings.length > 0 ? (
                holding.filings.map((item, idx) => (
                  <div className="signal-item" key={`${item.title}-${idx}`}>
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
        </div>
      ) : (
        <div className="detail-section-grid">
          <div className="detail-panel">
            <h4><i className="fa-solid fa-medal text-secondary"></i> Business Breakdown</h4>
            {holding.quality ? (
              <>
                <div className="quality-score-row">
                  <span className={`summary-status status-${scoreTone(holding.qualityScore10)}`}>
                    {holding.quality.rating}
                  </span>
                  <strong>{holding.quality.score}/{holding.quality.max_score}</strong>
                </div>
                <div className="metric-list">
                  {holding.quality.metrics.map((metric) => (
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
            {holding.fundamentals ? (
              <>
                <div className="fundamentals-grid">
                  {fundamentalRows.map((row) => (
                    <div className="fundamental-row" key={row.label}>
                      <span>{row.label}</span>
                      <strong>{row.value}</strong>
                    </div>
                  ))}
                </div>
                {holding.fundamentals.notes && holding.fundamentals.notes.length > 0 && (
                  <div className="fundamental-notes">
                    {holding.fundamentals.notes.slice(0, 3).map((note) => (
                      <p key={note}>{note}</p>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="text-muted">No fundamental snapshot found for this holding.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const ScoreKpi: React.FC<{ title: string; value: number; detail: string }> = ({ title, value, detail }) => {
  const tone = scoreTone(value);
  return (
    <div className={`score-kpi score-kpi-${tone}`}>
      <span>{title}</span>
      <strong>{detail}</strong>
      <div className="mini-score-meter">
        <div className={`mini-score-fill fill-${tone}`} style={{ width: `${clamp(value, 0, 10) * 10}%` }}></div>
      </div>
    </div>
  );
};

const StatBox: React.FC<{ label: string; value: string; tone?: 'green' | 'amber' | 'red' }> = ({ label, value, tone }) => (
  <div className="stat-row">
    <span>{label}</span>
    <strong className={tone ? `score-text-${tone}` : undefined}>{value}</strong>
  </div>
);

function buildHoldingSummaries(context: ReportContext | null): HoldingSummary[] {
  if (!context) return [];

  const impacts = context.impacts || [];
  const news = context.news || [];
  const filings = context.filings || [];
  const marketSnapshots = context.market_snapshots || [];
  const businessQuality = context.business_quality || [];
  const fundamentalSnapshots = context.fundamental_snapshots || [];
  const positions = context.positions || [];
  const symbols = Array.from(new Set([
    ...impacts.map((item) => item.symbol),
    ...businessQuality.map((item) => item.symbol),
    ...marketSnapshots.map((item) => item.symbol),
    ...fundamentalSnapshots.map((item) => item.symbol),
  ]));

  return symbols.map((symbol) => {
    const impact = impacts.find((item) => item.symbol === symbol);
    const quality = businessQuality.find((item) => item.symbol === symbol);
    const market = marketSnapshots.find((item) => item.symbol === symbol);
    const fundamentals = fundamentalSnapshots.find((item) => item.symbol === symbol);
    const holdingNews = news.filter((item) => item.symbol === symbol);
    const holdingFilings = filings.filter((item) => item.symbol === symbol);
    const position = positions.find((item) => item.symbol === symbol);
    const sentimentValues = holdingNews
      .map((item) => item.sentiment_score)
      .filter((value): value is number => typeof value === 'number');
    const averageSentiment = sentimentValues.length
      ? sentimentValues.reduce((sum, value) => sum + value, 0) / sentimentValues.length
      : 0;
    const priceChangePercent = market?.latest_price && market?.previous_close
      ? (market.latest_price - market.previous_close) / market.previous_close
      : null;
    const impactScore10 = impact ? clamp((impact.score + 100) / 20, 0, 10) : 5;
    const qualityScore10 = quality ? clamp((quality.score / quality.max_score) * 10, 0, 10) : 5;
    const newsScore10 = clamp((averageSentiment + 1) * 5, 0, 10);
    const priceScore10 = priceChangePercent === null
      ? 5
      : clamp(5 + (priceChangePercent * 100), 0, 10);
    const avgSentiment10 = newsScore10;
    const combinedScore10 = clamp(
      (impactScore10 * 0.35) +
      (qualityScore10 * 0.35) +
      (newsScore10 * 0.2) +
      (priceScore10 * 0.1),
      0,
      10
    );

    return {
      symbol,
      name: position?.name,
      impact,
      quality,
      market,
      fundamentals,
      news: holdingNews,
      filings: holdingFilings,
      impactScore10,
      qualityScore10,
      newsScore10,
      priceScore10,
      avgSentiment10,
      combinedScore10,
      priceChangePercent,
      averageSentiment,
    };
  }).sort((a, b) => b.combinedScore10 - a.combinedScore10);
}

function buildFundamentalRows(fundamentals?: FundamentalSnapshot) {
  if (!fundamentals) return [];
  return [
    { label: 'Revenue growth', value: formatPercent(fundamentals.revenue_growth) },
    { label: 'EPS growth', value: formatPercent(fundamentals.eps_growth) },
    { label: 'Free cash flow', value: formatLargeCurrency(fundamentals.free_cash_flow) },
    { label: 'Free cash flow growth', value: formatPercent(fundamentals.free_cash_flow_growth) },
    { label: 'Debt to equity', value: fundamentals.debt_to_equity === null || fundamentals.debt_to_equity === undefined ? 'Not available' : `${(fundamentals.debt_to_equity / 100).toFixed(2)}` },
    { label: 'Return on equity', value: formatPercent(fundamentals.return_on_equity) },
    { label: 'Dividend yield', value: formatPercent(fundamentals.dividend_yield) },
    { label: 'Payout ratio', value: formatPercent(fundamentals.payout_ratio) },
    { label: 'Trailing P/E', value: formatRatio(fundamentals.trailing_pe) },
    { label: 'Forward P/E', value: formatRatio(fundamentals.forward_pe) },
    { label: 'PEG ratio', value: formatRatio(fundamentals.peg_ratio) },
    { label: 'Profit margin', value: formatPercent(fundamentals.profit_margin) },
    { label: 'Gross margin', value: formatPercent(fundamentals.gross_margin) },
    { label: 'Market cap', value: formatLargeCurrency(fundamentals.market_cap) },
  ];
}

function scoreTone(score: number): 'green' | 'amber' | 'red' {
  if (score >= 7) return 'green';
  if (score >= 4) return 'amber';
  return 'red';
}

function scoreLabel(score: number) {
  if (score >= 7) return 'Strong';
  if (score >= 4) return 'Watch';
  return 'Risk';
}

function signed(value: number) {
  return `${value > 0 ? '+' : ''}${value}`;
}

function formatDate(dateStr: string) {
  try {
    const date = new Date(dateStr);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    });
  } catch (e) {
    return dateStr;
  }
}

function formatCurrency(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'Not available';
  }
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: value >= 1000 ? 0 : 2 })}`;
}

function formatPercent(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'Not available';
  }
  return `${(value * 100).toFixed(1)}%`;
}

function formatRatio(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'Not available';
  }
  return value.toFixed(2);
}

function formatLargeCurrency(value?: number | null) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return 'Not available';
  }
  const absValue = Math.abs(value);
  if (absValue >= 1_000_000_000_000) return `$${(value / 1_000_000_000_000).toFixed(2)}T`;
  if (absValue >= 1_000_000_000) return `$${(value / 1_000_000_000).toFixed(2)}B`;
  if (absValue >= 1_000_000) return `$${(value / 1_000_000).toFixed(2)}M`;
  return `$${value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}
