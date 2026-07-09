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

interface RawRecord {
  market: string;
  symbol: string;
  as_of_date: string | null;
  data_type: string;
  field_name: string;
  numeric_value: number | null;
  text_value: string | null;
  source_name: string;
  source_type: string;
  raw_payload: Record<string, unknown> | null;
  retrieved_at: string | null;
}

export const DeveloperDebugView: React.FC = () => {
  const [ingestionStatus, setIngestionStatus] = useState<Record<string, IngestionStatusRow> | null>(null);
  const [readinessSummary, setReadinessSummary] = useState<any | null>(null);
  const [rawCounts, setRawCounts] = useState<Record<string, number> | null>(null);
  const [backtestSummary, setBacktestSummary] = useState<Record<string, unknown> | null>(null);
  const [symbol, setSymbol] = useState('AAPL');
  const [market, setMarket] = useState('US');
  const [featureSample, setFeatureSample] = useState<FeatureRecord[]>([]);
  const [rawSample, setRawSample] = useState<RawRecord[]>([]);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchDebugStatus();
    fetchBacktestSummary();
  }, []);

  const fetchDebugStatus = async () => {
    setLoading(true);
    setErrorMessage(null);
    try {
      const res = await fetch('/api/debug/readiness');
      if (!res.ok) {
        throw new Error('Failed to load debug status.');
      }
      const data = await res.json();
      setReadinessSummary(data.readiness || null);
      setIngestionStatus(data.ingestion_status || null);
      setRawCounts(data.raw_counts_by_market || null);
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

  const fetchRawSample = async () => {
    if (!symbol.trim()) {
      setErrorMessage('Symbol is required for raw sample.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    try {
      const params = new URLSearchParams({ symbol: symbol.trim().toUpperCase(), market });
      const res = await fetch(`/api/debug/raw-sample?${params.toString()}`);
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || 'Failed to fetch raw sample');
      }
      const data = await res.json();
      setRawSample(data.raw_sample || []);
    } catch (error) {
      console.error(error);
      setErrorMessage('Unable to load raw sample.');
      setRawSample([]);
    } finally {
      setLoading(false);
    }
  };

  const performDebugAction = async (action: 'ingest' | 'build' | 'sync') => {
    if (!symbol.trim()) {
      setErrorMessage('Symbol is required for debug actions.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    setActionMessage(null);
    try {
      const body = JSON.stringify({ symbol: symbol.trim().toUpperCase(), market });
      const path = action === 'ingest'
        ? '/api/debug/ingest-symbol'
        : action === 'build'
        ? '/api/debug/build-features'
        : '/api/debug/sync-symbol';

      const res = await fetch(path, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
      });
      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `Failed to ${action} data`);
      }
      const data = await res.json();
      const completedStatus = data.feature_count !== undefined ? `generated ${data.feature_count} features` : data.success ? 'completed' : 'done';
      setActionMessage(`Action completed: ${action} (${completedStatus})`);
      await fetchDebugStatus();
    } catch (error: any) {
      console.error(error);
      setErrorMessage(error.message || 'Unable to complete debug action.');
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
      {actionMessage && <p className="text-success">{actionMessage}</p>}

      <section className="debug-grid">
        <div className="prediction-card">
          <h3>Readiness Summary</h3>
          {loading && !readinessSummary ? (
            <p>Loading readiness data...</p>
          ) : readinessSummary ? (
            <div className="debug-table-wrap">
              <table className="debug-table">
                <thead>
                  <tr><th colSpan={2}>Feature Readiness</th></tr>
                </thead>
                <tbody>
                  <tr><td>Total feature rows</td><td>{readinessSummary.feature_readiness?.count ?? 'N/A'}</td></tr>
                  <tr><td>Distinct symbols</td><td>{readinessSummary.feature_readiness?.distinct_symbols ?? 'N/A'}</td></tr>
                  <tr><td>Latest feature date</td><td>{readinessSummary.feature_readiness?.latest_as_of_date ?? 'N/A'}</td></tr>
                  <tr><td>Latest feature computed</td><td>{readinessSummary.feature_readiness?.latest_computed_at ?? 'N/A'}</td></tr>
                </tbody>
              </table>
              <div className="debug-table-wrap" style={{ marginTop: '1rem' }}>
                <table className="debug-table">
                  <thead>
                    <tr><th colSpan={2}>Raw Data Summary</th></tr>
                  </thead>
                  <tbody>
                    <tr><td>Raw data rows</td><td>{readinessSummary.raw_status?.raw_data_records?.count ?? 'N/A'}</td></tr>
                    <tr><td>Raw news rows</td><td>{readinessSummary.raw_status?.raw_news_records?.count ?? 'N/A'}</td></tr>
                    <tr><td>Raw options rows</td><td>{readinessSummary.raw_status?.raw_options_records?.count ?? 'N/A'}</td></tr>
                    <tr><td>Raw macro rows</td><td>{readinessSummary.raw_status?.raw_macro_records?.count ?? 'N/A'}</td></tr>
                    <tr><td>Raw event rows</td><td>{readinessSummary.raw_status?.raw_event_records?.count ?? 'N/A'}</td></tr>
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <p>No readiness data available.</p>
          )}
        </div>

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
      </section>

      <section className="debug-grid">
        <div className="prediction-card prediction-card-full">
          <h3>Developer Actions</h3>
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
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" type="button" onClick={() => performDebugAction('ingest')} disabled={loading}>
                {loading ? 'Working...' : 'Ingest Raw Data'}
              </button>
              <button className="btn btn-secondary" type="button" onClick={() => performDebugAction('build')} disabled={loading}>
                {loading ? 'Working...' : 'Build Features'}
              </button>
              <button className="btn btn-secondary" type="button" onClick={() => performDebugAction('sync')} disabled={loading}>
                {loading ? 'Working...' : 'Sync Raw + Features'}
              </button>
            </div>
          </div>
          <p style={{ marginTop: '0.75rem', fontSize: '0.95rem', color: '#7a7a7a' }}>
            Use these actions to fetch raw data for a symbol and generate feature vectors for inspection.
          </p>
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
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" type="button" onClick={fetchFeatureSample} disabled={loading}>
                {loading ? 'Loading...' : 'Fetch Feature Sample'}
              </button>
            </div>
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

        <div className="prediction-card prediction-card-full">
          <h3>Raw Data Sample Explorer</h3>
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
            <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
              <button className="btn btn-primary" type="button" onClick={fetchRawSample} disabled={loading}>
                {loading ? 'Loading...' : 'Fetch Raw Sample'}
              </button>
            </div>
          </div>

          {rawSample.length ? (
            <div className="debug-table-wrap">
              <table className="debug-table">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Type</th>
                    <th>Field</th>
                    <th>Value</th>
                  </tr>
                </thead>
                <tbody>
                  {rawSample.map((record, index) => (
                    <tr key={`${record.data_type}-${record.field_name}-${index}`}>
                      <td>{record.as_of_date || 'N/A'}</td>
                      <td>{record.data_type}</td>
                      <td>{record.field_name}</td>
                      <td>{record.numeric_value ?? record.text_value ?? 'N/A'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p>No raw rows loaded yet. Fetch a sample to inspect raw ingestion data.</p>
          )}
        </div>
      </section>
    </div>
  );
};
