import React, { useEffect, useState } from 'react';

interface Position {
  symbol: string;
  name: string | null;
  quantity: number;
  average_cost: number | null;
  scope: 'holding' | 'watchlist';
}

interface PredictionResult {
  symbol: string;
  market: string;
  predicted_up_probability: number;
  expected_move_percent: number;
  expected_price: number | null;
  confidence: string;
  top_drivers: string[];
  risks: string[];
  source: string;
  model_version: string;
  generated_at: string;
}

interface ModelInfo {
  model_type: string;
  status: string;
  version: string;
  explanation: string;
  accuracy?: number;
  roc_auc?: number;
  sample_count?: number;
}

interface PredictionViewProps {
  positions: Position[];
}

export const PredictionView: React.FC<PredictionViewProps> = ({ positions }) => {
  const [activeTab, setActiveTab] = useState<'estimate' | 'holdings'>('estimate');
  const [holdingsPredictions, setHoldingsPredictions] = useState<PredictionResult[]>([]);
  const [symbolInput, setSymbolInput] = useState('');
  const [marketInput, setMarketInput] = useState('US');
  const [estimate, setEstimate] = useState<PredictionResult | null>(null);
  const [modelInfo, setModelInfo] = useState<ModelInfo | null>(null);
  const [loadingHoldings, setLoadingHoldings] = useState(false);
  const [loadingEstimate, setLoadingEstimate] = useState(false);
  const [loadingModel, setLoadingModel] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchHoldingsPredictions();
    fetchModelInfo();
  }, [positions]);

  const fetchModelInfo = async () => {
    setLoadingModel(true);
    try {
      const res = await fetch('/api/debug/model-info');
      if (res.ok) {
        const data = await res.json();
        setModelInfo(data);
      }
    } catch (error) {
      console.error('Error fetching model info:', error);
    } finally {
      setLoadingModel(false);
    }
  };

  const fetchHoldingsPredictions = async () => {
    setLoadingHoldings(true);
    setErrorMessage(null);
    try {
      const res = await fetch('/api/predictions/holdings');
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`);
      }
      const data = await res.json();
      setHoldingsPredictions(data);
    } catch (error) {
      console.error(error);
      setErrorMessage('Unable to load holdings predictions at this time.');
    } finally {
      setLoadingHoldings(false);
    }
  };

  const handleEstimateSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLoadingEstimate(true);
    setErrorMessage(null);
    setEstimate(null);

    try {
      const res = await fetch('/api/predictions/estimate', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ symbol: symbolInput.trim(), market: marketInput }),
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.error || `HTTP ${res.status}`);
      }

      const data = await res.json();
      setEstimate(data);
    } catch (error) {
      console.error(error);
      setErrorMessage('Unable to estimate prediction for this symbol.');
    } finally {
      setLoadingEstimate(false);
    }
  };

  const getConfidenceSummary = () => {
    const counts = { high: 0, medium: 0, low: 0 };
    holdingsPredictions.forEach((pred) => {
      if (pred.confidence === 'High') counts.high++;
      else if (pred.confidence === 'Medium') counts.medium++;
      else if (pred.confidence === 'Low') counts.low++;
    });
    return counts;
  };

  const confidenceSummary = getConfidenceSummary();

  return (
    <div className="prediction-view">
      <div className="prediction-header">
        <div>
          <h2>Prediction Center</h2>
          <p>Run next-day predictions for your holdings or try a quick symbol estimate.</p>
        </div>
      </div>

      {/* Model Info Display */}
      {modelInfo && (
        <div className="prediction-model-info">
          <div className="model-header">
            <div>
              <h4>{modelInfo.model_type}</h4>
              <p className="model-status">Status: <strong>{modelInfo.status}</strong> | Version: {modelInfo.version}</p>
            </div>
            {modelInfo.accuracy !== undefined && (
              <div className="model-metrics">
                <span>Accuracy: {(modelInfo.accuracy * 100).toFixed(1)}%</span>
                {modelInfo.roc_auc && <span>ROC-AUC: {(modelInfo.roc_auc * 100).toFixed(1)}%</span>}
                {modelInfo.sample_count && <span>Samples: {modelInfo.sample_count}</span>}
              </div>
            )}
          </div>
          <p className="model-explanation">{modelInfo.explanation}</p>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="prediction-tabs">
        <button
          className={`prediction-tab ${activeTab === 'estimate' ? 'active' : ''}`}
          onClick={() => setActiveTab('estimate')}
        >
          Quick Symbol Estimate
        </button>
        <button
          className={`prediction-tab ${activeTab === 'holdings' ? 'active' : ''}`}
          onClick={() => setActiveTab('holdings')}
        >
          Holdings Predictions
        </button>
      </div>

      {/* Tab Content */}
      <div className="prediction-content">
        {/* Tab 1: Quick Symbol Estimate */}
        {activeTab === 'estimate' && (
          <div className="prediction-card full-width">
            <h3>Quick Symbol Estimate</h3>
            <p className="section-description">
              Enter a symbol to quickly estimate next-day price direction without saving it to your portfolio.
            </p>
            <form onSubmit={handleEstimateSubmit} className="prediction-form">
              <label>
                Symbol
                <input
                  type="text"
                  value={symbolInput}
                  onChange={(event) => setSymbolInput(event.target.value.toUpperCase())}
                  placeholder="AAPL"
                  required
                />
              </label>
              <label>
                Market
                <select value={marketInput} onChange={(event) => setMarketInput(event.target.value)}>
                  <option value="US">US</option>
                  <option value="IN">India</option>
                  <option value="JP">Japan</option>
                </select>
              </label>
              <button type="submit" className="btn btn-primary" disabled={loadingEstimate}>
                {loadingEstimate ? 'Estimating...' : 'Estimate Price'}
              </button>
            </form>

            {errorMessage && <p className="text-error">{errorMessage}</p>}

            {estimate && (
              <div className="prediction-result-card">
                <h4>{estimate.symbol} ({estimate.market})</h4>
                <div className="result-metrics">
                  <div className={`metric high-metric confidence-${estimate.confidence.toLowerCase()}`}>
                    <span className="metric-label">Up Probability</span>
                    <span className="metric-value">{(estimate.predicted_up_probability * 100).toFixed(0)}%</span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">Expected Move</span>
                    <span className="metric-value">{estimate.expected_move_percent.toFixed(2)}%</span>
                  </div>
                  <div className={`metric confidence-${estimate.confidence.toLowerCase()}`}>
                    <span className="metric-label">Confidence</span>
                    <span className="metric-value">{estimate.confidence}</span>
                  </div>
                  <div className="metric">
                    <span className="metric-label">Expected Price</span>
                    <span className="metric-value">{estimate.expected_price !== null ? `$${estimate.expected_price.toFixed(2)}` : 'N/A'}</span>
                  </div>
                </div>
                <div className="result-details">
                  <div className="detail-section">
                    <strong>Model & Source</strong>
                    <ul>
                      <li><strong>Model:</strong> {estimate.model_version}</li>
                      <li><strong>Source:</strong> {estimate.source}</li>
                      <li><strong>Generated:</strong> {new Date(estimate.generated_at).toLocaleString()}</li>
                    </ul>
                  </div>
                  <div className="detail-section">
                    <strong>Top Drivers</strong>
                    <ul>{estimate.top_drivers.map((item) => <li key={item}>• {item}</li>)}</ul>
                  </div>
                  <div className="detail-section">
                    <strong>Risks</strong>
                    <ul>{estimate.risks.map((item) => <li key={item}>• {item}</li>)}</ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Tab 2: Holdings Predictions */}
        {activeTab === 'holdings' && (
          <div className="prediction-card full-width">
            <div className="holdings-header">
              <div>
                <h3>Holdings Predictions</h3>
                <p className="section-description">
                  Next-day predictions for all holdings in your portfolio. Green indicates high confidence, yellow medium, and gray low.
                </p>
              </div>
              <button className="btn btn-secondary" type="button" onClick={fetchHoldingsPredictions} disabled={loadingHoldings}>
                {loadingHoldings ? 'Refreshing...' : 'Refresh'}
              </button>
            </div>

            {/* Confidence Summary */}
            {holdingsPredictions.length > 0 && (
              <div className="confidence-summary">
                <div className="summary-stat high">
                  <span className="stat-label">HIGH</span>
                  <span className="stat-value">{confidenceSummary.high}</span>
                </div>
                <div className="summary-stat medium">
                  <span className="stat-label">MEDIUM</span>
                  <span className="stat-value">{confidenceSummary.medium}</span>
                </div>
                <div className="summary-stat low">
                  <span className="stat-label">LOW</span>
                  <span className="stat-value">{confidenceSummary.low}</span>
                </div>
              </div>
            )}

            {errorMessage && <p className="text-error">{errorMessage}</p>}

            {loadingHoldings ? (
              <p>Loading holdings predictions...</p>
            ) : holdingsPredictions.length === 0 ? (
              <p>No holdings predictions available yet. Add holdings to your portfolio to see predictions.</p>
            ) : (
              <div className="prediction-holdings-list">
                {holdingsPredictions.map((prediction) => (
                  <div className={`prediction-holdings-item confidence-${prediction.confidence.toLowerCase()}`} key={prediction.symbol}>
                    <div className="prediction-holdings-title">
                      <strong>{prediction.symbol}</strong>
                      <span className={`confidence-badge confidence-${prediction.confidence.toLowerCase()}`}>
                        {prediction.confidence}
                      </span>
                    </div>
                    <div className="prediction-holdings-grid">
                      <div><strong>Up</strong><span>{(prediction.predicted_up_probability * 100).toFixed(0)}%</span></div>
                      <div><strong>Move</strong><span>{prediction.expected_move_percent.toFixed(2)}%</span></div>
                      <div><strong>Price</strong><span>{prediction.expected_price !== null ? `$${prediction.expected_price.toFixed(2)}` : 'N/A'}</span></div>
                      <div><strong>Source</strong><span>{prediction.source}</span></div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};

