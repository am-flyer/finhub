import React, { useState, useEffect } from 'react';

interface Position {
  symbol: string;
  name: string | null;
  quantity: number;
  average_cost: number | null;
  scope: 'holding' | 'watchlist';
}

interface AssetFormViewProps {
  editingPosition: Position | null;
  onRefresh: () => void;
  onCancel: () => void;
}

export const AssetFormView: React.FC<AssetFormViewProps> = ({ 
  editingPosition, 
  onRefresh, 
  onCancel 
}) => {
  const [symbol, setSymbol] = useState('');
  const [name, setName] = useState('');
  const [quantity, setQuantity] = useState('0');
  const [averageCost, setAverageCost] = useState('');
  const [scope, setScope] = useState<'holding' | 'watchlist'>('holding');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Populate form if in edit mode
  useEffect(() => {
    if (editingPosition) {
      setSymbol(editingPosition.symbol);
      setName(editingPosition.name || '');
      setQuantity(editingPosition.quantity.toString());
      setAverageCost(editingPosition.average_cost !== null ? editingPosition.average_cost.toString() : '');
      setScope(editingPosition.scope);
    } else {
      setSymbol('');
      setName('');
      setQuantity('0');
      setAverageCost('');
      setScope('holding');
    }
    setError(null);
  }, [editingPosition]);

  // When scope changes, toggle watchlist defaults
  useEffect(() => {
    if (scope === 'watchlist') {
      setQuantity('0');
      setAverageCost('');
    }
  }, [scope]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbol.trim()) {
      setError('Ticker symbol is required');
      return;
    }

    setLoading(true);
    setError(null);

    const payload = {
      symbol: symbol.trim().toUpperCase(),
      name: name.trim() || null,
      quantity: parseFloat(quantity) || 0,
      average_cost: averageCost.trim() !== '' ? parseFloat(averageCost) : null,
      scope: scope,
    };

    try {
      const res = await fetch('/api/positions', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to save position');
      }

      onRefresh();
      onCancel(); // Go back to list view on success
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="workspace" style={{ maxWidth: '600px', margin: '0 auto', width: '100%' }}>
      <div className="form-card" style={{ width: '100%' }}>
        <h3>{editingPosition ? `Edit Asset: ${editingPosition.symbol}` : 'Add New Asset'}</h3>
        {error && (
          <div style={{ color: 'var(--danger)', marginBottom: '15px', fontSize: '0.85rem' }}>
            <i className="fa-solid fa-triangle-exclamation"></i> {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Asset Type</label>
            <select
              className="form-control"
              value={scope}
              onChange={(e) => setScope(e.target.value as 'holding' | 'watchlist')}
              disabled={!!editingPosition}
            >
              <option value="holding">Holding (Owned Stock/ETF)</option>
              <option value="watchlist">Watchlist (Monitored Asset)</option>
            </select>
          </div>

          <div className="form-group">
            <label>Ticker Symbol (e.g. MSFT)</label>
            <input
              type="text"
              className="form-control"
              placeholder="AAPL"
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              disabled={!!editingPosition}
              required
            />
          </div>

          <div className="form-group">
            <label>Asset Name (Optional)</label>
            <input
              type="text"
              className="form-control"
              placeholder="Apple Inc."
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {scope === 'holding' && (
            <>
              <div className="form-group">
                <label>Quantity Owned</label>
                <input
                  type="number"
                  step="any"
                  className="form-control"
                  placeholder="10.5"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  required
                />
              </div>

              <div className="form-group">
                <label>Average Cost Per Share ($)</label>
                <input
                  type="number"
                  step="any"
                  className="form-control"
                  placeholder="175.50"
                  value={averageCost}
                  onChange={(e) => setAverageCost(e.target.value)}
                  required
                />
              </div>
            </>
          )}

          <div className="form-actions" style={{ marginTop: '24px' }}>
            <button type="submit" className="btn btn-primary" style={{ flex: 1 }} disabled={loading}>
              {loading ? (
                <i className="fa-solid fa-circle-notch fa-spin"></i>
              ) : (
                <i className="fa-solid fa-floppy-disk"></i>
              )}
              <span>{editingPosition ? 'Update Asset' : 'Save Asset'}</span>
            </button>

            <button type="button" className="btn btn-secondary" onClick={onCancel} disabled={loading}>
              Cancel
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
