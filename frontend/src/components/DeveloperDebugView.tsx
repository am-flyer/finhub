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

interface SchedulerJobStatus {
  id: string;
  name: string;
  next_run_time: string | null;
  trigger: string;
  func_ref: string;
  args: unknown[];
  kwargs: Record<string, unknown>;
}

interface SchedulerStatus {
  scheduler_running: boolean;
  message?: string;
  jobs?: SchedulerJobStatus[];
}

export const DeveloperDebugView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'readiness' | 'ingestion' | 'markets' | 'operations'>('readiness');
  const [ingestionStatus, setIngestionStatus] = useState<Record<string, IngestionStatusRow> | null>(null);
  const [readinessSummary, setReadinessSummary] = useState<any | null>(null);
  const [rawCounts, setRawCounts] = useState<Record<string, number> | null>(null);
  const [backtestSummary, setBacktestSummary] = useState<Record<string, unknown> | null>(null);
  const [symbol, setSymbol] = useState('AAPL');
  const [market, setMarket] = useState('US');
  const [featureSample, setFeatureSample] = useState<FeatureRecord[]>([]);
  const [rawSample, setRawSample] = useState<RawRecord[]>([]);
  const [pipelineJobs, setPipelineJobs] = useState<Array<Record<string, unknown>> | null>(null);
  const [schedulerStatus, setSchedulerStatus] = useState<SchedulerStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchDebugStatus();
    fetchBacktestSummary();
    fetchPipelineJobs();
    fetchSchedulerStatus();
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

  const fetchPipelineJobs = async () => {
    try {
      const res = await fetch('/api/debug/pipeline-jobs');
      if (!res.ok) {
        throw new Error('Failed to load pipeline jobs');
      }
      const data = await res.json();
      setPipelineJobs(data.pipeline_jobs || []);
    } catch (error) {
      console.error(error);
      setPipelineJobs([]);
    }
  };

  const fetchSchedulerStatus = async () => {
    try {
      const res = await fetch('/api/debug/scheduler-status');
      if (!res.ok) {
        throw new Error('Failed to load scheduler status');
      }
      const data = await res.json();
      setSchedulerStatus(data || null);
    } catch (error) {
      console.error(error);
      setSchedulerStatus({ scheduler_running: false, message: 'Unable to load scheduler status.' });
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

  const performDebugAction = async (action: 'ingest' | 'build' | 'sync' | 'orchestrate') => {
    if (!symbol.trim() && action !== 'orchestrate') {
      setErrorMessage('Symbol is required for debug actions.');
      return;
    }

    setLoading(true);
    setErrorMessage(null);
    setActionMessage(null);
    try {
      const body = action === 'orchestrate'
        ? JSON.stringify({ market, include_watchlist: true })
        : JSON.stringify({ symbol: symbol.trim().toUpperCase(), market });
      const path = action === 'ingest'
        ? '/api/debug/ingest-symbol'
        : action === 'build'
        ? '/api/debug/build-features'
        : action === 'sync'
        ? '/api/debug/sync-symbol'
        : '/api/debug/orchestrate-portfolio';

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
      let completedStatus = 'completed';
      if (action === 'orchestrate') {
        const completed = Array.isArray(data.completed_symbols) ? data.completed_symbols.length : 0;
        const failed = Array.isArray(data.failed_symbols) ? data.failed_symbols.length : 0;
        completedStatus = `completed ${completed} symbols${failed ? `, ${failed} failed` : ''}`;
      } else if (data.feature_count !== undefined) {
        completedStatus = `generated ${data.feature_count} features`;
      } else if (data.success !== undefined) {
        completedStatus = 'completed successfully';
      }
      setActionMessage(`Action completed: ${action} (${completedStatus})`);
      await fetchDebugStatus();
      await fetchPipelineJobs();
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
          <h2>Developer Console</h2>
          <p>Monitor data ingestion, feature engineering, and model training pipeline.</p>
        </div>
      </div>

      {errorMessage && <p className="text-error">{errorMessage}</p>}
      {actionMessage && <p className="text-success">{actionMessage}</p>}

      {/* Tab Navigation */}
      <div className="prediction-tabs">
        <button
          className={`prediction-tab ${activeTab === 'readiness' ? 'active' : ''}`}
          onClick={() => setActiveTab('readiness')}
        >
          Readiness Summary
        </button>
        <button
          className={`prediction-tab ${activeTab === 'ingestion' ? 'active' : ''}`}
          onClick={() => setActiveTab('ingestion')}
        >
          Ingestion Status
        </button>
        <button
          className={`prediction-tab ${activeTab === 'markets' ? 'active' : ''}`}
          onClick={() => setActiveTab('markets')}
        >
          Raw Count by Markets
        </button>
        <button
          className={`prediction-tab ${activeTab === 'operations' ? 'active' : ''}`}
          onClick={() => setActiveTab('operations')}
        >
          Operations & Explorers
        </button>
      </div>

      {/* Tab Content */}
      <div className="prediction-content">
        {/* Tab 1: Readiness Summary */}
        {activeTab === 'readiness' && (
          <div className="prediction-card full-width">
            <h3>Readiness Summary</h3>
            <p className="section-description">
              Feature readiness shows your feature engineering pipeline status. Raw data summary displays all ingested data types. Both are essential for model training readiness.
            </p>

            {loading && !readinessSummary ? (
              <p>Loading readiness data...</p>
            ) : readinessSummary ? (
              <div className="readiness-grids">
                <div className="readiness-grid-item">
                  <h4>Feature Readiness</h4>
                  <p className="grid-description">Extracted features from raw data, ready for model training.</p>
                  <div className="debug-table-wrap">
                    <table className="debug-table">
                      <tbody>
                        <tr><td>Total Feature Rows</td><td><strong>{readinessSummary.feature_readiness?.count ?? 'N/A'}</strong></td></tr>
                        <tr><td>Distinct Symbols</td><td><strong>{readinessSummary.feature_readiness?.distinct_symbols ?? 'N/A'}</strong></td></tr>
                        <tr><td>Latest Feature Date</td><td>{readinessSummary.feature_readiness?.latest_as_of_date ?? 'N/A'}</td></tr>
                        <tr><td>Latest Computed</td><td>{readinessSummary.feature_readiness?.latest_computed_at ?? 'N/A'}</td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>

                <div className="readiness-grid-item">
                  <h4>Raw Data Summary</h4>
                  <p className="grid-description">All ingested raw data organized by type. Use for debugging data completeness.</p>
                  <div className="debug-table-wrap">
                    <table className="debug-table">
                      <tbody>
                        <tr><td>Raw Data Rows</td><td><strong>{readinessSummary.raw_status?.raw_data_records?.count ?? 'N/A'}</strong></td></tr>
                        <tr><td>Raw News Rows</td><td><strong>{readinessSummary.raw_status?.raw_news_records?.count ?? 'N/A'}</strong></td></tr>
                        <tr><td>Raw Options Rows</td><td><strong>{readinessSummary.raw_status?.raw_options_records?.count ?? 'N/A'}</strong></td></tr>
                        <tr><td>Raw Macro Rows</td><td><strong>{readinessSummary.raw_status?.raw_macro_records?.count ?? 'N/A'}</strong></td></tr>
                        <tr><td>Raw Event Rows</td><td><strong>{readinessSummary.raw_status?.raw_event_records?.count ?? 'N/A'}</strong></td></tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            ) : (
              <p>No readiness data available.</p>
            )}
          </div>
        )}

        {/* Tab 2: Ingestion Status */}
        {activeTab === 'ingestion' && (
          <div className="prediction-card full-width">
            <h3>Ingestion Status</h3>
            <p className="section-description">
              Status of all ingested tables showing record counts and last update timestamp. Use to verify data is flowing through the pipeline.
            </p>

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
                          <td><strong>{table}</strong></td>
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
        )}

        {/* Tab 3: Raw Count by Markets */}
        {activeTab === 'markets' && (
          <div className="prediction-card full-width">
            <h3>Raw Data Distribution</h3>
            <p className="section-description">
              Raw record count by market. Higher counts indicate more data available for feature engineering and model training.
            </p>

            {rawCounts ? (
              <div className="markets-grid">
                {Object.entries(rawCounts).map(([marketKey, count]) => (
                  <div key={marketKey} className="market-card">
                    <div className="market-name">{marketKey}</div>
                    <div className="market-count">{count.toLocaleString()}</div>
                    <div className="market-label">records</div>
                  </div>
                ))}
              </div>
            ) : (
              <p>No raw count data available.</p>
            )}
          </div>
        )}

        {/* Tab 4: Operations & Explorers */}
        {activeTab === 'operations' && (
          <div className="prediction-card full-width">
            <h3>Developer Operations</h3>
            <p className="section-description">
              Execute pipeline actions and explore feature/raw data samples. Actions: ingest symbols, build features, sync data, orchestrate portfolio.
            </p>

            {/* Developer Actions */}
            <div className="debug-section">
              <h4>Quick Actions</h4>
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
                  <button className="btn btn-secondary" type="button" onClick={() => performDebugAction('orchestrate')} disabled={loading}>
                    {loading ? 'Working...' : 'Orchestrate Portfolio'}
                  </button>
                </div>
              </div>
            </div>

            {/* Scheduler Status */}
            <div className="debug-section">
              <h4>Scheduler Status</h4>
              {schedulerStatus ? (
                <div className="debug-table-wrap">
                  <table className="debug-table">
                    <tbody>
                      <tr><td>Scheduler Running</td><td><strong>{schedulerStatus.scheduler_running ? '✓ Active' : '✗ Inactive'}</strong></td></tr>
                      {schedulerStatus.message && (
                        <tr><td>Message</td><td>{schedulerStatus.message}</td></tr>
                      )}
                      {schedulerStatus.jobs && schedulerStatus.jobs.length > 0 && (
                        <tr>
                          <td>Scheduled Jobs ({schedulerStatus.jobs.length})</td>
                          <td>
                            <ul className="debug-list">
                              {schedulerStatus.jobs.map((job) => (
                                <li key={job.id}>
                                  <strong>{job.id}</strong>: {job.next_run_time || 'No next run'}
                                </li>
                              ))}
                            </ul>
                          </td>
                        </tr>
                      )}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>Loading scheduler details...</p>
              )}
            </div>

            {/* Pipeline Job History */}
            <div className="debug-section">
              <h4>Pipeline Job History</h4>
              {pipelineJobs ? (
                <div className="debug-table-wrap" style={{ maxHeight: '300px', overflowY: 'auto' }}>
                  <table className="debug-table">
                    <thead>
                      <tr>
                        <th>ID</th>
                        <th>Type</th>
                        <th>Status</th>
                        <th>Started At</th>
                        <th>Completed At</th>
                      </tr>
                    </thead>
                    <tbody>
                      {pipelineJobs.length ? (
                        pipelineJobs.map((job: any) => (
                          <tr key={job.id}>
                            <td>{job.id}</td>
                            <td>{job.job_type || 'N/A'}</td>
                            <td>{job.status || 'N/A'}</td>
                            <td>{job.started_at || 'N/A'}</td>
                            <td>{job.completed_at || 'N/A'}</td>
                          </tr>
                        ))
                      ) : (
                        <tr><td colSpan={5}>No pipeline job records available.</td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              ) : (
                <p>No pipeline job data available.</p>
              )}
            </div>

            {/* Feature Sample Explorer */}
            <div className="debug-section">
              <h4>Feature Sample Explorer</h4>
              <p className="grid-description">Inspect feature vectors extracted for a specific symbol.</p>
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
                <div className="debug-table-wrap" style={{ maxHeight: '300px', overflowY: 'auto', marginTop: '1rem' }}>
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
                <p>No feature rows loaded yet.</p>
              )}
            </div>

            {/* Raw Data Sample Explorer */}
            <div className="debug-section">
              <h4>Raw Data Sample Explorer</h4>
              <p className="grid-description">Inspect raw data collected for a specific symbol before feature engineering.</p>
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
                <button className="btn btn-primary" type="button" onClick={fetchRawSample} disabled={loading}>
                  {loading ? 'Loading...' : 'Fetch Raw Sample'}
                </button>
              </div>

              {rawSample.length ? (
                <div className="debug-table-wrap" style={{ maxHeight: '300px', overflowY: 'auto', marginTop: '1rem' }}>
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
                <p>No raw rows loaded yet.</p>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
