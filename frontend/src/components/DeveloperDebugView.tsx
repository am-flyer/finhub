import React, { useEffect, useState } from 'react';

interface IngestionStatusRow {
  count: number;
  latest_timestamp: string | null;
}

interface FeatureRecord {
  market: string;
  symbol: string;
  as_of_date: string | null;
  feature_name: string;
  numeric_value: number | null;
  text_value: string | null;
  source_name: string;
  source_type: string;
  raw_payload: Record<string, unknown> | null;
  computed_at: string | null;
}

export const DeveloperDebugView: React.FC = () => {
  const [ingestionStatus, setIngestionStatus] = useState<Record<string, IngestionStatusRow> | null>(null);
  const [rawCounts, setRawCounts] = useState<Record<string, number> | null>(null);
  const [backtestSummary, setBacktestSummary] = useState<Record<string, unknown> | null>(null);
  const [symbol, setSymbol] = useState('AAPL');
  const [market, setMarket] = useState('US');
  const [featureSample, setFeatureSample] = useState<FeatureRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchDebugStatus();
    fetchBacktestSummary();
  }, []);

  const fetchDebugStatus = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const [statusRes, countsRes] = await Promise.all([
        fetch('/api/debug/ingestion-status'),
        fetch('/api/debug/raw-counts'),
      ]);
      if (!statusRes.ok || !countsRes.ok) {
        throw new Error('Failed to load debug data.');
      }
      const statusData = await statusRes.json();
      const countsData = await countsRes.json();
      setIngestionStatus(statusData);
      setRawCounts(countsData.raw_counts_by_market || null);
    } catch (error) {
      console.error(error);
      setErrorMessage('Unable to load developer debug status.');
    } finally {
      setLoading(false);
    }
  };

  const fetchBacktestSummary = async () => {
    try {
      const res = await fetch('/api/debug/backtest-summary');
      if (!res.ok) {
        throw new Error('Failed to load backtest summary');
      }
      const data = await res.json();
      setBacktestSummary(data);
    } catch (error) {
      console.error(error);
      setBacktestSummary({ status: 'error', message: 'Unable to load backtest summary.' });
    }
  };

  const fetchFeatureSample = async () => {
    if (!symbol.trim()) {
      setErrorMessage('Symbol is required for feature samples.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase(), market });
      const res = await fetch(`/api/debug/feature-sample?${params.toString()}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Failed to fetch feature sample');
      }
      const data = await res.json();
      setFeatureSample(data.feature_sample || []);
    } catch (error) {
      console.error(error);
      setErrorMessage('Unable to load feature sample.');
      setFeatureSample([]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="developer-debug-view">
      <div className="prediction-header">
        <div>
          <h2>Developer Debug Console</h2>
          <p>Inspect ingestion status, raw data coverage, feature samples, and model readiness diagnostics.</p>
        </div>
      </div>

      {errorMessage && <p className="text-error">{errorMessage}</p>}

      <section className="debug-grid">
        <div className="prediction-card">
          <h3>Ingestion Status</h3>
          {loading && !ingestionStatus ? (
            <p>Loading ingestion status...</p>
          ) : (
            <div className="debug-table-wrap">
              <table className="debug-table">
                <thead>
                  <tr>
                    <th>Table</th>
                    <th>Row Count</th>
                    <th>Latest Timestamp</th>
                  </tr>
                </thead>
                <tbody>
                  {ingestionStatus ? (
                    Object.entries(ingestionStatus).map(([table, row]) => (
                      <tr key={table}>
                        <td>{table}</td>
                        <td>{row.count}</td>
                        <td>{row.latest_timestamp || 'N/A'}</td>
                      </tr>
                    ))
                  ) : (
                    <tr><td colSpan={3}>No ingestion data available.</td></tr>
                  )}
                </tbody>
              </table>
            </div>
          )}
        </div>

        <div className="prediction-card">
          <h3>Raw Counts by Market</h3>
          {rawCounts ? (
            <ul className="debug-list">
              {Object.entries(rawCounts).map(([marketKey, count]) => (
                <li key={marketKey}><strong>{marketKey}:</strong> {count}</li>
              ))}
            </ul>
          ) : (
            <p>No raw count data available.</p>
          )}
        </div>

        <div className="prediction-card">
          <h3>Backtest Status</h3>
          {backtestSummary ? (
            <div className="debug-list">
              <p><strong>Status:</strong> {String(backtestSummary.status)}</p>
              <p><strong>Message:</strong> {String(backtestSummary.message)}</p>
            </div>
          ) : (
            <p>Backtest diagnostics not yet available.</p>
          )}
        </div>
      </section>

      <section className="debug-grid">
        <div className="prediction-card prediction-card-full">
          <h3>Feature Sample Explorer</h3>
          <div className="prediction-form">
            <label>
              Symbol
              <input
                type="text"
                value={symbol}
                onChange={(event) => setSymbol(event.target.value.toUpperCase())}
                placeholder="AAPL"
              />
            </label>
            <label>
              Market
              <select value={market} onChange={(event) => setMarket(event.target.value)}>
                <option value="US">US</option>
                <option value="IN">India</option>
                <option value="JP">Japan</option>
              </select>
            </label>
            <button className="btn btn-primary" type="button" onClick={fetchFeatureSample} disabled={loading}>
              {loading ? 'Loading...' : 'Fetch Feature Sample'}
            </button>
          </div>

          {featureSample.length ? (
            <div className="debug-table-wrap">
              <table className="debug-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Feature</th>
                    <th>Value</th>
                    <th>Source</th>
                  </tr>
                </thead>
                <tbody>
                  {featureSample.map((feature, index) => (
                    <tr key={`${feature.feature_name}-${index}`}>
                      <td>{feature.as_of_date || 'N/A'}</td>
                      <td>{feature.feature_name}</td>
                      <td>{feature.numeric_value ?? feature.text_value ?? 'N/A'}</td>
                      <td>{feature.source_name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>No feature rows loaded yet. Fetch a sample to inspect feature vectors.</p>
          )}
        </div>
      </section>
    </div>
  );
};
