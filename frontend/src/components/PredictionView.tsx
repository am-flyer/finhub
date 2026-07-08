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

interface PredictionViewProps {
  positions: Position[];
}

export const PredictionView: React.FC<PredictionViewProps> = ({ positions }) => {
  const [holdingsPredictions, setHoldingsPredictions] = useState<PredictionResult[]>([]);
  const [symbolInput, setSymbolInput] = useState('');
  const [marketInput, setMarketInput] = useState('US');
  const [estimate, setEstimate] = useState<PredictionResult | null>(null);
  const [loadingHoldings, setLoadingHoldings] = useState(false);
  const [loadingEstimate, setLoadingEstimate] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchHoldingsPredictions();
  }, [positions]);

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

  return (
    <div className="prediction-view">
      <div className="prediction-header">
        <div>
          <h2>Prediction Center</h2>
          <p>Run next-day predictions for your holdings or try a quick symbol estimate without saving it.</p>
        </div>
      </div>

      <section className="prediction-grid">
        <div className="prediction-card">
          <h3>Quick Symbol Estimate</h3>
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
                <option value="India">India</option>
                <option value="Japan">Japan</option>
              </select>
            </label>
            <button type="submit" className="btn btn-primary" disabled={loadingEstimate}>
              {loadingEstimate ? 'Estimating...' : 'Estimate Price'}
            </button>
          </form>

          {estimate && (
            <div className="prediction-result-card">
              <h4>{estimate.symbol} ({estimate.market})</h4>
              <ul>
                <li><strong>Up probability:</strong> {(estimate.predicted_up_probability * 100).toFixed(0)}%</li>
                <li><strong>Expected move:</strong> {estimate.expected_move_percent.toFixed(2)}%</li>
                <li><strong>Expected price:</strong> {estimate.expected_price !== null ? `$${estimate.expected_price.toFixed(2)}` : 'N/A'}</li>
                <li><strong>Confidence:</strong> {estimate.confidence}</li>
                <li><strong>Model:</strong> {estimate.model_version}</li>
                <li><strong>Source:</strong> {estimate.source}</li>
              </ul>
              <div className="prediction-small-section">
                <strong>Top drivers</strong>
                <ul>{estimate.top_drivers.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
              <div className="prediction-small-section">
                <strong>Risks</strong>
                <ul>{estimate.risks.map((item) => <li key={item}>{item}</li>)}</ul>
              </div>
            </div>
          )}
        </div>

        <div className="prediction-card prediction-holdings-card">
          <div className="prediction-card-header">
            <h3>Holdings Predictions</h3>
            <button className="btn btn-secondary" type="button" onClick={fetchHoldingsPredictions} disabled={loadingHoldings}>
              Refresh
            </button>
          </div>
          {errorMessage && <p className="text-error">{errorMessage}</p>}
          {loadingHoldings ? (
            <p>Loading holdings predictions...</p>
          ) : holdingsPredictions.length === 0 ? (
            <p>No holdings predictions available yet.</p>
          ) : (
            <div className="prediction-holdings-list">
              {holdingsPredictions.map((prediction) => (
                <div className="prediction-holdings-item" key={prediction.symbol}>
                  <div className="prediction-holdings-title">
                    <strong>{prediction.symbol}</strong>
                    <span>{prediction.market}</span>
                  </div>
                  <div className="prediction-holdings-grid">
                    <div><strong>Up</strong><span>{(prediction.predicted_up_probability * 100).toFixed(0)}%</span></div>
                    <div><strong>Move</strong><span>{prediction.expected_move_percent.toFixed(2)}%</span></div>
                    <div><strong>Conf.</strong><span>{prediction.confidence}</span></div>
                    <div><strong>Price</strong><span>{prediction.expected_price !== null ? `$${prediction.expected_price.toFixed(2)}` : 'N/A'}</span></div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
};
