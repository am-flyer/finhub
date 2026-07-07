import React, { useState, useEffect } from 'react';

interface PortfolioPoint {
  date: string;
  value: number;
  cost: number;
}

interface PricePoint {
  date: string;
  price: number;
}

interface NewsMarker {
  date: string;
  title: string;
  sentiment: number | null;
  url: string | null;
  source: string;
}

interface NewsItem {
  id: number;
  symbol: string;
  published_at: string;
  title: string;
  summary: string | null;
  source: string;
  url: string | null;
  sentiment_score: number | null;
}

interface Position {
  symbol: string;
  name: string | null;
  quantity: number;
  average_cost: number | null;
  scope: 'holding' | 'watchlist';
}

interface AnalyticsViewProps {
  positions: Position[];
}

type TimeframeOption = 'max' | '5y' | '2y' | '1y' | '6m' | '3m' | '1m' | 'weekly' | 'day';

export const AnalyticsView: React.FC<AnalyticsViewProps> = ({ positions }) => {
  const holdings = positions.filter(p => p.scope === 'holding');
  
  const [selectedSymbol, setSelectedSymbol] = useState<string>('PORTFOLIO'); // 'PORTFOLIO' or ticker
  const [portfolioData, setPortfolioData] = useState<PortfolioPoint[]>([]);
  const [stockPrices, setStockPrices] = useState<PricePoint[]>([]);
  const [stockAvgCost, setStockAvgCost] = useState<number | null>(null);
  const [newsMarkers, setNewsMarkers] = useState<NewsMarker[]>([]);
  
  const [newsList, setNewsList] = useState<NewsItem[]>([]);
  const [newsOffset, setNewsOffset] = useState(0);
  const [hasMoreNews, setHasMoreNews] = useState(true);
  const [newsLoading, setNewsLoading] = useState(false);
  const [loading, setLoading] = useState(false);

  // Timeframe and selection states
  const [timeframe, setTimeframe] = useState<TimeframeOption>('max');
  const [selectedDate, setSelectedDate] = useState<string | null>(null);

  // Crosshair coordinate lines (hover & active)
  const [hoveredDataPoint, setHoveredDataPoint] = useState<{ x: number; y: number; date: string; value: string } | null>(null);

  // Tooltip persistent state and hide delay
  const [hoveredMarker, setHoveredMarker] = useState<NewsMarker[] | null>(null);
  const [activeTooltipIndex, setActiveTooltipIndex] = useState<number>(0);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [hideTimeout, setHideTimeout] = useState<number | null>(null);

  useEffect(() => {
    setSelectedDate(null); // Clear selected date when selected symbol switches
    setHoveredDataPoint(null);
    if (selectedSymbol === 'PORTFOLIO') {
      fetchPortfolioData();
      // Fetch combined portfolio/market-wide news articles
      setNewsOffset(0);
      setHasMoreNews(true);
      fetchNews('PORTFOLIO', 0, false, selectedDate);
    } else {
      fetchStockData(selectedSymbol);
    }
  }, [selectedSymbol]);

  // Refetch news list from backend whenever selectedDate changes
  useEffect(() => {
    setNewsOffset(0);
    setHasMoreNews(true);
    fetchNews(selectedSymbol, 0, false, selectedDate);
  }, [selectedDate]);

  const fetchPortfolioData = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/analytics/portfolio');
      if (!res.ok) throw new Error('Failed to fetch portfolio analytics');
      const data = await res.json();
      setPortfolioData(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchStockData = async (symbol: string) => {
    setLoading(true);
    try {
      const res = await fetch(`/api/analytics/stock?symbol=${symbol}`);
      if (!res.ok) throw new Error(`Failed to fetch stock analytics for ${symbol}`);
      const data = await res.json();
      setStockPrices(data.prices || []);
      setStockAvgCost(data.avg_cost);
      setNewsMarkers(data.news_markers || []);
      
      // Load initial 10 news articles
      setNewsOffset(0);
      setHasMoreNews(true);
      fetchNews(symbol, 0, false, selectedDate);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const fetchNews = async (symbol: string, offset: number, append: boolean, dateFilterVal: string | null = null) => {
    setNewsLoading(true);
    try {
      let url = `/api/news?symbol=${symbol}&limit=10&offset=${offset}`;
      if (dateFilterVal) {
        url += `&date=${dateFilterVal}`;
      }
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch news');
      const data: NewsItem[] = await res.json();
      
      if (append) {
        setNewsList(prev => [...prev, ...data]);
      } else {
        setNewsList(data);
      }
      
      if (data.length < 10) {
        setHasMoreNews(false);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setNewsLoading(false);
    }
  };

  const handleLoadMoreNews = () => {
    const nextOffset = newsOffset + 10;
    setNewsOffset(nextOffset);
    fetchNews(selectedSymbol, nextOffset, true, selectedDate);
  };

  // Helper function to escape HTML entity codes (like &nbsp; and &amp;) when displaying
  const cleanText = (text: string | null): string => {
    if (!text) return '';
    return text
      .replace(/&nbsp;/gi, ' ')
      .replace(/&amp;/gi, '&')
      .replace(/&quot;/gi, '"')
      .replace(/&#39;/gi, "'")
      .replace(/&lt;/gi, '<')
      .replace(/&gt;/gi, '>')
      .replace(/\xa0/g, ' ') // Strip non-breaking spaces
      .trim();
  };

  // Trailing window data filtering helper
  const filterByTimeframe = <T extends { date: string }>(data: T[]): T[] => {
    if (data.length === 0) return data;
    const now = new Date();
    
    let threshold = new Date(0); // 'max' default
    if (timeframe === 'day') {
      threshold = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    } else if (timeframe === 'weekly') {
      threshold = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    } else if (timeframe === '1m') {
      threshold = new Date(now.getFullYear(), now.getMonth() - 1, now.getDate());
    } else if (timeframe === '3m') {
      threshold = new Date(now.getFullYear(), now.getMonth() - 3, now.getDate());
    } else if (timeframe === '6m') {
      threshold = new Date(now.getFullYear(), now.getMonth() - 6, now.getDate());
    } else if (timeframe === '1y') {
      threshold = new Date(now.getFullYear() - 1, now.getMonth(), now.getDate());
    } else if (timeframe === '2y') {
      threshold = new Date(now.getFullYear() - 2, now.getMonth(), now.getDate());
    } else if (timeframe === '5y') {
      threshold = new Date(now.getFullYear() - 5, now.getMonth(), now.getDate());
    }

    const filtered = data.filter(d => new Date(d.date) >= threshold);
    if (filtered.length < 2 && data.length >= 2) {
      return data.slice(-2); // Fallback: ensure at least two points to draw a path
    }
    return filtered;
  };

  // Tooltip mouse interactions for persistent hover clickability
  const handleMouseEnterMarker = (markers: NewsMarker[], x: number, y: number) => {
    if (hideTimeout) {
      clearTimeout(hideTimeout);
      setHideTimeout(null);
    }
    setHoveredMarker(markers);
    setActiveTooltipIndex(0);
    setTooltipPos({ x, y });
  };

  const handleMouseLeaveMarker = () => {
    const timeout = window.setTimeout(() => {
      setHoveredMarker(null);
    }, 400); // 400ms delay to let user hover over the tooltip link
    setHideTimeout(timeout);
  };

  const handleMouseEnterTooltip = () => {
    if (hideTimeout) {
      clearTimeout(hideTimeout);
      setHideTimeout(null);
    }
  };

  const handleMouseLeaveTooltip = () => {
    setHoveredMarker(null);
  };

  // SVG dimensions
  const width = 800;
  const height = 350;
  const padding = { top: 20, right: 30, bottom: 40, left: 65 };
  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  // Chart rendering coordinator
  const renderChart = () => {
    if (selectedSymbol === 'PORTFOLIO') {
      const filteredPortfolio = filterByTimeframe(portfolioData);
      
      if (filteredPortfolio.length < 2) {
        return (
          <div className="no-data-notice">
            <i className="fa-solid fa-chart-line"></i>
            <p>Not enough historical price points available for this timeframe.</p>
          </div>
        );
      }

      const valMin = Math.min(...filteredPortfolio.map(d => d.value), ...filteredPortfolio.map(d => d.cost)) * 0.95;
      const valMax = Math.max(...filteredPortfolio.map(d => d.value), ...filteredPortfolio.map(d => d.cost)) * 1.05;
      const range = valMax - valMin || 1;

      const getX = (index: number) => padding.left + (index / (filteredPortfolio.length - 1)) * chartWidth;
      const getY = (val: number) => padding.top + chartHeight - ((val - valMin) / range) * chartHeight;

      const valuePoints = filteredPortfolio.map((d, i) => `${getX(i)},${getY(d.value)}`).join(' L ');
      const costPoints = filteredPortfolio.map((d, i) => `${getX(i)},${getY(d.cost)}`).join(' L ');

      const gridVals = [valMin, valMin + range * 0.33, valMin + range * 0.66, valMax];

      // Calculate clicked date point coordinates for crosshair highlight
      let selectedPoint = null;
      if (selectedDate) {
        const matchIdx = filteredPortfolio.findIndex(d => d.date === selectedDate);
        if (matchIdx !== -1) {
          selectedPoint = {
            x: getX(matchIdx),
            y: getY(filteredPortfolio[matchIdx].value),
            date: selectedDate,
            value: `$${filteredPortfolio[matchIdx].value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
          };
        }
      }

      const activePoint = hoveredDataPoint || selectedPoint;

      return (
        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="analytics-svg">
          <defs>
            <linearGradient id="valueGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#8b5cf6" stopOpacity="0.4" />
              <stop offset="100%" stopColor="#8b5cf6" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {gridVals.map((val, idx) => (
            <g key={idx}>
              <line 
                x1={padding.left} 
                y1={getY(val)} 
                x2={width - padding.right} 
                y2={getY(val)} 
                stroke="rgba(255, 255, 255, 0.05)" 
                strokeDasharray="4 4"
              />
              <text 
                x={padding.left - 10} 
                y={getY(val) + 4} 
                textAnchor="end" 
                fill="var(--text-muted)" 
                fontSize="10"
              >
                ${val.toLocaleString(undefined, { maximumFractionDigits: 0 })}
              </text>
            </g>
          ))}

          {/* Date Axis tags */}
          <text x={padding.left} y={height - 15} fill="var(--text-muted)" fontSize="10">
            {filteredPortfolio[0].date}
          </text>
          <text x={padding.left + chartWidth / 2} y={height - 15} textAnchor="middle" fill="var(--text-muted)" fontSize="10">
            {filteredPortfolio[Math.floor(filteredPortfolio.length / 2)].date}
          </text>
          <text x={width - padding.right} y={height - 15} textAnchor="end" fill="var(--text-muted)" fontSize="10">
            {filteredPortfolio[filteredPortfolio.length - 1].date}
          </text>

          {/* Area gradient */}
          <path
            d={`M ${getX(0)},${getY(valMin)} L ${valuePoints} L ${getX(filteredPortfolio.length - 1)},${getY(valMin)} Z`}
            fill="url(#valueGrad)"
          />

          {/* Portfolio Value line */}
          <path
            d={`M ${valuePoints}`}
            fill="none"
            stroke="#8b5cf6"
            strokeWidth="3.5"
            strokeLinecap="round"
          />

          {/* Cost Basis line */}
          <path
            d={`M ${costPoints}`}
            fill="none"
            stroke="rgba(255, 255, 255, 0.4)"
            strokeWidth="2"
            strokeDasharray="6 4"
          />

          {/* Coordinate Perforated crosshair lines */}
          {activePoint && (
            <g>
              {/* Vertical line pointing to date axis */}
              <line
                x1={activePoint.x}
                y1={activePoint.y}
                x2={activePoint.x}
                y2={height - padding.bottom}
                stroke="#8b5cf6"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                opacity="0.75"
              />
              {/* Horizontal line pointing to money axis */}
              <line
                x1={padding.left}
                y1={activePoint.y}
                x2={activePoint.x}
                y2={activePoint.y}
                stroke="#8b5cf6"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                opacity="0.75"
              />
              {/* Capsule label over money coordinate axis */}
              <rect
                x={padding.left - 62}
                y={activePoint.y - 8}
                width="56"
                height="16"
                rx="4"
                fill="#8b5cf6"
                opacity="0.9"
              />
              <text
                x={padding.left - 34}
                y={activePoint.y + 4}
                fill="#070b13"
                fontSize="9"
                fontWeight="700"
                textAnchor="middle"
              >
                {activePoint.value}
              </text>
              {/* Capsule label over date coordinate axis */}
              <rect
                x={activePoint.x - 38}
                y={height - padding.bottom + 2}
                width="76"
                height="16"
                rx="4"
                fill="#8b5cf6"
                opacity="0.9"
              />
              <text
                x={activePoint.x}
                y={height - padding.bottom + 13}
                fill="#070b13"
                fontSize="8"
                fontWeight="700"
                textAnchor="middle"
              >
                {activePoint.date}
              </text>
            </g>
          )}

          {/* Interactive coordinates points */}
          {filteredPortfolio.map((d, i) => {
            const isSelected = selectedDate === d.date;
            return (
              <circle
                key={i}
                cx={getX(i)}
                cy={getY(d.value)}
                r={isSelected ? "6" : "4"}
                fill={isSelected ? '#8b5cf6' : 'rgba(139, 92, 246, 0.2)'}
                stroke="#8b5cf6"
                strokeWidth={isSelected ? "2" : "1"}
                style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                onClick={() => setSelectedDate(isSelected ? null : d.date)}
                onMouseEnter={() => setHoveredDataPoint({
                  x: getX(i),
                  y: getY(d.value),
                  date: d.date,
                  value: `$${d.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`
                })}
                onMouseLeave={() => setHoveredDataPoint(null)}
              />
            );
          })}
        </svg>
      );
    } else {
      // Individual stock price chart
      const filteredPrices = filterByTimeframe(stockPrices);
      
      if (filteredPrices.length < 2) {
        return (
          <div className="no-data-notice">
            <i className="fa-solid fa-chart-line"></i>
            <p>No historical prices found for {selectedSymbol} in this timeframe.</p>
          </div>
        );
      }

      const pricesList = filteredPrices.map(p => p.price);
      const allVals = stockAvgCost !== null ? [...pricesList, stockAvgCost] : pricesList;
      const valMin = Math.min(...allVals) * 0.97;
      const valMax = Math.max(...allVals) * 1.03;
      const range = valMax - valMin || 1;

      const getX = (index: number) => padding.left + (index / (filteredPrices.length - 1)) * chartWidth;
      const getY = (val: number) => padding.top + chartHeight - ((val - valMin) / range) * chartHeight;

      const pricePoints = filteredPrices.map((d, i) => `${getX(i)},${getY(d.price)}`).join(' L ');
      const gridVals = [valMin, valMin + range * 0.33, valMin + range * 0.66, valMax];

      // Overlay markers only if date matches filtered range
      const activeMarkers = newsMarkers
        .map(marker => {
          const matchIndex = filteredPrices.findIndex(p => p.date === marker.date);
          if (matchIndex === -1) return null;
          return {
            ...marker,
            x: getX(matchIndex),
            y: getY(filteredPrices[matchIndex].price)
          };
        })
        .filter((m): m is (NewsMarker & { x: number; y: number }) => m !== null);

      // Calculate clicked stock date point coordinates for crosshairs
      let selectedPoint = null;
      if (selectedDate) {
        const matchIdx = filteredPrices.findIndex(d => d.date === selectedDate);
        if (matchIdx !== -1) {
          selectedPoint = {
            x: getX(matchIdx),
            y: getY(filteredPrices[matchIdx].price),
            date: selectedDate,
            value: `$${filteredPrices[matchIdx].price.toFixed(2)}`
          };
        }
      }

      const activePoint = hoveredDataPoint || selectedPoint;

      // Group markers by identical dates to prevent overlaps of multiple news items on same day
      const groupedMarkersMap: { [date: string]: (NewsMarker & { x: number; y: number })[] } = {};
      activeMarkers.forEach(m => {
        if (!groupedMarkersMap[m.date]) {
          groupedMarkersMap[m.date] = [];
        }
        groupedMarkersMap[m.date].push(m);
      });

      return (
        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height}`} className="analytics-svg" style={{ position: 'relative' }}>
          <defs>
            <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#10b981" stopOpacity="0.3" />
              <stop offset="100%" stopColor="#10b981" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          {gridVals.map((val, idx) => (
            <g key={idx}>
              <line 
                x1={padding.left} 
                y1={getY(val)} 
                x2={width - padding.right} 
                y2={getY(val)} 
                stroke="rgba(255, 255, 255, 0.05)" 
                strokeDasharray="4 4"
              />
              <text 
                x={padding.left - 10} 
                y={getY(val) + 4} 
                textAnchor="end" 
                fill="var(--text-muted)" 
                fontSize="10"
              >
                ${val.toFixed(2)}
              </text>
            </g>
          ))}

          {/* Date Axis tags */}
          <text x={padding.left} y={height - 15} fill="var(--text-muted)" fontSize="10">
            {filteredPrices[0].date}
          </text>
          <text x={padding.left + chartWidth / 2} y={height - 15} textAnchor="middle" fill="var(--text-muted)" fontSize="10">
            {filteredPrices[Math.floor(filteredPrices.length / 2)].date}
          </text>
          <text x={width - padding.right} y={height - 15} textAnchor="end" fill="var(--text-muted)" fontSize="10">
            {filteredPrices[filteredPrices.length - 1].date}
          </text>

          {/* Area gradient fill */}
          <path
            d={`M ${getX(0)},${getY(valMin)} L ${pricePoints} L ${getX(filteredPrices.length - 1)},${getY(valMin)} Z`}
            fill="url(#priceGrad)"
          />

          {/* Price Line */}
          <path
            d={`M ${pricePoints}`}
            fill="none"
            stroke="var(--primary)"
            strokeWidth="3"
            strokeLinecap="round"
          />

          {/* Average Cost Line */}
          {stockAvgCost !== null && (
            <g>
              <line
                x1={padding.left}
                y1={getY(stockAvgCost)}
                x2={width - padding.right}
                y2={getY(stockAvgCost)}
                stroke="var(--warning)"
                strokeWidth="1.5"
                strokeDasharray="6 3"
              />
              <text
                x={width - padding.right - 10}
                y={getY(stockAvgCost) - 6}
                textAnchor="end"
                fill="var(--warning)"
                fontSize="9"
                fontWeight="600"
              >
                Avg Cost: ${stockAvgCost.toFixed(2)}
              </text>
            </g>
          )}

          {/* Coordinate Perforated crosshair lines */}
          {activePoint && (
            <g>
              {/* Vertical line pointing to date axis */}
              <line
                x1={activePoint.x}
                y1={activePoint.y}
                x2={activePoint.x}
                y2={height - padding.bottom}
                stroke="var(--primary)"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                opacity="0.75"
              />
              {/* Horizontal line pointing to price axis */}
              <line
                x1={padding.left}
                y1={activePoint.y}
                x2={activePoint.x}
                y2={activePoint.y}
                stroke="var(--primary)"
                strokeWidth="1.2"
                strokeDasharray="4 4"
                opacity="0.75"
              />
              {/* Capsule label over price coordinate axis */}
              <rect
                x={padding.left - 54}
                y={activePoint.y - 8}
                width="48"
                height="16"
                rx="4"
                fill="var(--primary)"
                opacity="0.9"
              />
              <text
                x={padding.left - 30}
                y={activePoint.y + 4}
                fill="#070b13"
                fontSize="9"
                fontWeight="700"
                textAnchor="middle"
              >
                {activePoint.value}
              </text>
              {/* Capsule label over date coordinate axis */}
              <rect
                x={activePoint.x - 38}
                y={height - padding.bottom + 2}
                width="76"
                height="16"
                rx="4"
                fill="var(--primary)"
                opacity="0.9"
              />
              <text
                x={activePoint.x}
                y={height - padding.bottom + 13}
                fill="#070b13"
                fontSize="8"
                fontWeight="700"
                textAnchor="middle"
              >
                {activePoint.date}
              </text>
            </g>
          )}

          {/* Interactive coordinates points */}
          {filteredPrices.map((d, i) => {
            const isSelected = selectedDate === d.date;
            return (
              <circle
                key={i}
                cx={getX(i)}
                cy={getY(d.price)}
                r={isSelected ? "6" : "4"}
                fill={isSelected ? 'var(--primary)' : 'rgba(16, 185, 129, 0.1)'}
                stroke="var(--primary)"
                strokeWidth={isSelected ? "2" : "1"}
                style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                onClick={() => setSelectedDate(isSelected ? null : d.date)}
                onMouseEnter={() => setHoveredDataPoint({
                  x: getX(i),
                  y: getY(d.price),
                  date: d.date,
                  value: `$${d.price.toFixed(2)}`
                })}
                onMouseLeave={() => setHoveredDataPoint(null)}
              />
            );
          })}

          {/* Sentiment markers dots (grouped by date) */}
          {Object.keys(groupedMarkersMap).map((dateKey, gIdx) => {
            const markers = groupedMarkersMap[dateKey];
            const primaryMarker = markers[0];
            const isPos = (primaryMarker.sentiment || 0) > 0.1;
            const isNeg = (primaryMarker.sentiment || 0) < -0.1;
            const color = isPos ? '#10b981' : isNeg ? '#ef4444' : '#eab308';
            const isSelected = selectedDate === dateKey;
            
            return (
              <circle
                key={gIdx}
                cx={primaryMarker.x}
                cy={primaryMarker.y}
                r={isSelected ? 9 : 6.5}
                fill={color}
                stroke={isSelected ? "#8b5cf6" : "#070b13"}
                strokeWidth="1.8"
                style={{ cursor: 'pointer', transition: 'r 0.1s' }}
                onClick={(e) => {
                  e.stopPropagation();
                  setSelectedDate(selectedDate === dateKey ? null : dateKey);
                }}
                onMouseEnter={(e) => {
                  handleMouseEnterMarker(markers, primaryMarker.x, primaryMarker.y - 12);
                }}
                onMouseLeave={handleMouseLeaveMarker}
              />
            );
          })}
        </svg>
      );
    }
  };

  // Adjust translation to shift tooltip left when hovering near the right edge
  const isNearRightEdge = tooltipPos.x > width - 180;
  const isNearLeftEdge = tooltipPos.x < 180;
  const tooltipTransform = isNearRightEdge 
    ? 'translate(-85%, -100%)' 
    : isNearLeftEdge 
      ? 'translate(-15%, -100%)' 
      : 'translate(-50%, -100%)';

  // Extract currently active tooltip news metadata item
  const activeMarker = hoveredMarker ? hoveredMarker[activeTooltipIndex] : null;

  return (
    <div className="workspace">
      <style>{`
        .analytics-container {
          display: grid;
          grid-template-columns: 1fr;
          gap: 28px;
          width: 100%;
        }
        @media (min-width: 1024px) {
          .analytics-container {
            grid-template-columns: 1fr 1fr; /* Balanced 50/50 split on desktop for wide news panels */
          }
        }
        .selector-bar {
          display: flex;
          gap: 8px;
          overflow-x: auto;
          padding-bottom: 8px;
          border-bottom: 1px solid var(--border-color);
          margin-bottom: 16px;
          flex-shrink: 0;
        }
        .selector-item {
          background-color: var(--bg-card);
          border: 1px solid var(--border-color);
          padding: 8px 16px;
          border-radius: 12px;
          cursor: pointer;
          font-family: var(--font-heading);
          font-weight: 600;
          font-size: 0.85rem;
          color: var(--text-muted);
          transition: var(--transition-fast);
          white-space: nowrap;
        }
        .selector-item:hover {
          color: var(--text-main);
          background-color: var(--bg-sidebar-hover);
        }
        .selector-item.active {
          color: var(--primary);
          background-color: var(--primary-glow);
          border-color: var(--primary);
        }
        .chart-card {
          background-color: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 20px;
          padding: 24px;
          backdrop-filter: blur(10px);
          display: flex;
          flex-direction: column;
          gap: 16px;
          position: relative;
          z-index: 10; /* Ensures tooltips hover above other panels */
        }
        .chart-header {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        @media (min-width: 768px) {
          .chart-header {
            flex-direction: row;
            justify-content: space-between;
            align-items: center;
          }
        }
        .chart-header h3 {
          font-family: var(--font-heading);
          font-size: 1.15rem;
          margin: 0;
        }
        .timeframe-bar {
          display: flex;
          gap: 4px;
          background: rgba(0, 0, 0, 0.2);
          padding: 4px;
          border-radius: 8px;
          border: 1px solid var(--border-color);
          width: fit-content;
        }
        .timeframe-btn {
          background: transparent;
          border: none;
          padding: 4px 10px;
          border-radius: 6px;
          color: var(--text-muted);
          font-size: 0.75rem;
          font-weight: 600;
          cursor: pointer;
          transition: var(--transition-fast);
        }
        .timeframe-btn:hover {
          color: var(--text-main);
        }
        .timeframe-btn.active {
          background-color: var(--primary);
          color: #070b13;
        }
        .legend {
          display: flex;
          gap: 16px;
          font-size: 0.8rem;
          margin-top: 4px;
        }
        .legend-item {
          display: flex;
          align-items: center;
          gap: 6px;
          color: var(--text-muted);
        }
        .legend-dot {
          width: 12px;
          height: 3px;
          border-radius: 2px;
        }
        .svg-container {
          width: 100%;
          height: 300px;
          position: relative;
          overflow: visible; /* Prevents desktop scrollbar shifting/jitter */
        }
        .analytics-svg {
          overflow: visible;
          height: 100%;
        }
        @media (max-width: 768px) {
          .svg-container {
            overflow-x: auto; /* Enable scroll only on mobile */
            overflow-y: hidden;
            -webkit-overflow-scrolling: touch;
          }
          .analytics-svg {
            min-width: 650px; /* Keep coordinates legible on mobile viewports */
          }
        }
        .no-data-notice {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          color: var(--text-muted);
          gap: 12px;
          text-align: center;
          padding: 40px;
        }
        .no-data-notice i {
          font-size: 2.5rem;
        }
        .sentiment-tooltip {
          position: absolute;
          background: rgba(13, 19, 32, 0.95);
          border: 1px solid var(--border-color);
          border-radius: 8px;
          padding: 12px;
          width: max-content; /* Dynamic sizing */
          min-width: 200px;   /* Safe readable width bounds */
          max-width: 290px;
          white-space: normal; /* Allow titles to wrap naturally */
          pointer-events: auto;
          z-index: 9999;
          box-shadow: 0 4px 12px rgba(0,0,0,0.5);
          word-break: break-word;
          overflow-wrap: break-word;
        }
        .tooltip-title {
          font-size: 0.78rem;
          font-weight: 600;
          color: var(--text-main);
          margin-bottom: 6px;
          line-height: 1.4;
          word-break: break-word;
          overflow-wrap: break-word;
        }
        .tooltip-meta {
          font-size: 0.65rem;
          color: var(--text-muted);
          display: flex;
          justify-content: space-between;
          margin-top: 4px;
        }
        .tooltip-paginator {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-top: 8px;
          border-top: 1px solid var(--border-color);
          padding-top: 6px;
          font-size: 0.68rem;
          color: var(--primary);
        }
        .tooltip-nav-btn {
          background: transparent;
          border: none;
          color: var(--primary);
          cursor: pointer;
          font-weight: bold;
          font-size: 0.7rem;
        }
        .tooltip-nav-btn:disabled {
          color: var(--text-muted);
          cursor: not-allowed;
        }
        .news-panel {
          background-color: var(--bg-card);
          border: 1px solid var(--border-color);
          border-radius: 20px;
          padding: 24px;
          backdrop-filter: blur(10px);
          display: flex;
          flex-direction: column;
          gap: 16px;
          max-height: 480px;
          overflow-y: auto;
          z-index: 5;
        }
        .news-panel h3 {
          font-family: var(--font-heading);
          font-size: 1.15rem;
          margin: 0;
          border-bottom: 1px solid var(--border-color);
          padding-bottom: 10px;
        }
        .date-filter-status {
          display: flex;
          align-items: center;
          justify-content: space-between;
          background: var(--primary-glow);
          border: 1px solid var(--primary);
          padding: 8px 12px;
          border-radius: 10px;
          font-size: 0.78rem;
          color: #a78bfa;
        }
        .news-card-list {
          display: flex;
          flex-direction: column;
          gap: 12px;
        }
        .news-card {
          background: rgba(255, 255, 255, 0.02);
          border: 1px solid var(--border-color);
          border-radius: 12px;
          padding: 14px;
          display: flex;
          flex-direction: column;
          gap: 8px;
          transition: var(--transition-fast);
        }
        .news-card:hover {
          background: rgba(255, 255, 255, 0.04);
          border-color: rgba(255, 255, 255, 0.15);
        }
        .news-card-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          flex-wrap: wrap; /* Prevent overlap/overflow in narrow viewports */
          font-size: 0.7rem;
          color: var(--text-muted);
        }
        .news-card-title {
          font-size: 0.85rem;
          font-weight: 600;
          color: var(--text-main);
          text-decoration: none;
          line-height: 1.4;
          word-break: break-word;
          overflow-wrap: break-word;
        }
        .news-card-title:hover {
          color: var(--primary);
        }
        .news-card-summary {
          font-size: 0.78rem;
          color: var(--text-muted);
          line-height: 1.4;
          word-break: break-word;
          overflow-wrap: break-word;
        }
      `}</style>

      {/* Asset Selector bar */}
      <div className="selector-bar">
        <div 
          className={`selector-item ${selectedSymbol === 'PORTFOLIO' ? 'active' : ''}`}
          onClick={() => setSelectedSymbol('PORTFOLIO')}
        >
          Total Portfolio
        </div>
        {holdings.map(h => (
          <div
            key={h.symbol}
            className={`selector-item ${selectedSymbol === h.symbol ? 'active' : ''}`}
            onClick={() => setSelectedSymbol(h.symbol)}
          >
            {h.symbol}
          </div>
        ))}
      </div>

      <div className="analytics-container">
        {/* Left Side: Historical Line Chart */}
        <div className="chart-card">
          <div className="chart-header">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <h3>
                {selectedSymbol === 'PORTFOLIO' 
                  ? 'Portfolio Value Timeline (vs. Cost Basis)' 
                  : `${selectedSymbol} Price History vs. Avg Cost`}
              </h3>
              
              <div className="legend">
                {selectedSymbol === 'PORTFOLIO' ? (
                  <>
                    <div className="legend-item">
                      <div className="legend-dot" style={{ backgroundColor: '#8b5cf6' }}></div>
                      <span>Total Value</span>
                    </div>
                    <div className="legend-item">
                      <div className="legend-dot" style={{ borderTop: '2px dashed rgba(255,255,255,0.4)' }}></div>
                      <span>Total Cost</span>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="legend-item">
                      <div className="legend-dot" style={{ backgroundColor: 'var(--primary)' }}></div>
                      <span>Price</span>
                    </div>
                    {stockAvgCost !== null && (
                      <div className="legend-item">
                        <div className="legend-dot" style={{ borderTop: '2px dashed var(--warning)' }}></div>
                        <span>Average Cost</span>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>

            {/* Timeframe Buttons Bar */}
            <div className="timeframe-bar">
              {(['max', '5y', '2y', '1y', '6m', '3m', '1m', 'weekly', 'day'] as TimeframeOption[]).map(opt => (
                <button
                  key={opt}
                  className={`timeframe-btn ${timeframe === opt ? 'active' : ''}`}
                  onClick={() => {
                    setTimeframe(opt);
                    setSelectedDate(null);
                  }}
                >
                  {opt.toUpperCase()}
                </button>
              ))}
            </div>
          </div>

          <div className="svg-container">
            {loading ? (
              <div className="loading-state" style={{ height: '100%' }}>
                <i className="fa-solid fa-circle-notch fa-spin" style={{ fontSize: '2rem' }}></i>
                <span>Loading analytics...</span>
              </div>
            ) : (
              renderChart()
            )}

            {/* Hover Tooltip for Sentiment Markers */}
            {hoveredMarker && activeMarker && (
              <div 
                className="sentiment-tooltip"
                style={{ 
                  left: `${tooltipPos.x}px`, 
                  top: `${tooltipPos.y}px`,
                  transform: tooltipTransform
                }}
                onMouseEnter={handleMouseEnterTooltip}
                onMouseLeave={handleMouseLeaveTooltip}
              >
                {activeMarker.url ? (
                  <a
                    href={activeMarker.url}
                    target="_blank"
                    rel="noreferrer"
                    className="tooltip-title"
                    style={{ textDecoration: 'underline', color: '#a78bfa', cursor: 'pointer' }}
                  >
                    {cleanText(activeMarker.title)}
                  </a>
                ) : (
                  <div className="tooltip-title">{cleanText(activeMarker.title)}</div>
                )}
                <div className="tooltip-meta">
                  <span>{activeMarker.source}</span>
                  <span style={{ 
                    color: (activeMarker.sentiment || 0) > 0.1 ? '#10b981' : (activeMarker.sentiment || 0) < -0.1 ? '#ef4444' : '#eab308',
                    fontWeight: 'bold'
                  }}>
                    {(activeMarker.sentiment || 0) > 0.1 ? 'Positive' : (activeMarker.sentiment || 0) < -0.1 ? 'Negative' : 'Neutral'}
                  </span>
                </div>

                {/* Render navigation buttons inside tooltip if multiple news items exist on same date */}
                {hoveredMarker.length > 1 && (
                  <div className="tooltip-paginator">
                    <button 
                      className="tooltip-nav-btn"
                      disabled={activeTooltipIndex === 0}
                      onClick={() => setActiveTooltipIndex(prev => prev - 1)}
                    >
                      <i className="fa-solid fa-chevron-left"></i> Prev
                    </button>
                    <span>{activeTooltipIndex + 1} of {hoveredMarker.length}</span>
                    <button 
                      className="tooltip-nav-btn"
                      disabled={activeTooltipIndex === hoveredMarker.length - 1}
                      onClick={() => setActiveTooltipIndex(prev => prev + 1)}
                    >
                      Next <i className="fa-solid fa-chevron-right"></i>
                    </button>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* Right Side: News Panel */}
        <div className="news-panel">
          <h3>
            {selectedSymbol === 'PORTFOLIO' 
              ? 'Market-Wide News' 
              : `${selectedSymbol} Recent News & Sentiments`}
          </h3>

          {/* Selected Date Filter Banner */}
          {selectedDate && (
            <div className="date-filter-status">
              <span>Showing news for <strong>{selectedDate}</strong></span>
              <button 
                className="btn btn-secondary" 
                style={{ padding: '2px 8px', fontSize: '0.7rem' }}
                onClick={() => setSelectedDate(null)}
              >
                Show All
              </button>
            </div>
          )}

          <div className="news-card-list">
            {newsList.length > 0 ? (
              <>
                {newsList.map((news) => {
                  const isPos = (news.sentiment_score || 0) > 0.1;
                  const isNeg = (news.sentiment_score || 0) < -0.1;
                  const sentimentLabel = isPos ? 'Positive' : isNeg ? 'Negative' : 'Neutral';
                  const sentimentColor = isPos ? 'var(--success)' : isNeg ? 'var(--danger)' : 'var(--warning)';
                  
                  return (
                    <div className="news-card" key={news.id}>
                      <div className="news-card-header">
                        <span>{news.symbol} • {news.source} • {new Date(news.published_at).toLocaleDateString()}</span>
                        <span style={{ color: sentimentColor, fontWeight: '700' }}>{sentimentLabel}</span>
                      </div>
                      
                      <a 
                        href={news.url || '#'} 
                        target="_blank" 
                        rel="noreferrer" 
                        className="news-card-title"
                      >
                        {cleanText(news.title)}
                      </a>
                      
                      {news.summary && (
                        <p className="news-card-summary">
                          {cleanText(news.summary.length > 140 ? `${news.summary.slice(0, 140)}...` : news.summary)}
                        </p>
                      )}
                    </div>
                  );
                })}

                {!selectedDate && hasMoreNews && (
                  <button 
                    className="btn btn-secondary" 
                    onClick={handleLoadMoreNews}
                    disabled={newsLoading}
                    style={{ marginTop: '8px' }}
                  >
                    {newsLoading ? (
                      <i className="fa-solid fa-circle-notch fa-spin"></i>
                    ) : (
                      'Load More News'
                    )}
                  </button>
                )}
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem', textAlign: 'center', padding: '20px' }}>
                {newsLoading ? 'Fetching news feed...' : 'No news found.'}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
