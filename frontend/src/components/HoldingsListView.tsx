import React from 'react';

interface Position {
  symbol: string;
  name: string | null;
  quantity: number;
  average_cost: number | null;
  scope: 'holding' | 'watchlist';
}

interface HoldingsListViewProps {
  positions: Position[];
  onRefresh: () => void;
  onEdit: (pos: Position) => void;
  onNavigateToAdd: () => void;
}

export const HoldingsListView: React.FC<HoldingsListViewProps> = ({ 
  positions, 
  onRefresh, 
  onEdit, 
  onNavigateToAdd 
}) => {
  const handleDeleteClick = async (symbolToDelete: string) => {
    if (!window.confirm(`Are you sure you want to remove ${symbolToDelete}?`)) {
      return;
    }
    try {
      const res = await fetch(`/api/positions/${symbolToDelete}`, {
        method: 'DELETE',
      });
      if (!res.ok) {
        const data = await res.json();
        throw new Error(data.error || 'Failed to delete position');
      }
      onRefresh();
    } catch (err: any) {
      alert(err.message);
    }
  };

  return (
    <div className="workspace">
      <div className="summary-column" style={{ width: '100%' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <h3>My Assets</h3>
          <button className="btn btn-primary" onClick={onNavigateToAdd}>
            <i className="fa-solid fa-plus"></i> Add New Asset
          </button>
        </div>
        
        <div className="positions-table-container">
          <table className="positions-table">
            <thead>
              <tr>
                <th>Ticker</th>
                <th>Name</th>
                <th>Type</th>
                <th>Quantity</th>
                <th>Avg Cost</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {positions.length > 0 ? (
                positions.map((pos) => (
                  <tr key={pos.symbol}>
                    <td style={{ fontWeight: '700' }}>{pos.symbol}</td>
                    <td>{pos.name || '-'}</td>
                    <td>
                      <span className={`scope-indicator scope-${pos.scope}`}>
                        {pos.scope}
                      </span>
                    </td>
                    <td>{pos.scope === 'holding' ? pos.quantity : '-'}</td>
                    <td>
                      {pos.scope === 'holding' && pos.average_cost !== null
                        ? `$${pos.average_cost.toFixed(2)}`
                        : '-'}
                    </td>
                    <td className="actions-cell">
                      <button
                        className="action-icon-btn edit-btn"
                        onClick={() => onEdit(pos)}
                        title="Edit Position"
                      >
                        <i className="fa-solid fa-pen-to-square"></i>
                      </button>
                      <button
                        className="action-icon-btn delete-btn"
                        onClick={() => handleDeleteClick(pos.symbol)}
                        title="Delete Position"
                      >
                        <i className="fa-solid fa-trash-can"></i>
                      </button>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', color: 'var(--text-muted)' }}>
                    No positions saved. Click "Add New Asset" to save your first asset!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
