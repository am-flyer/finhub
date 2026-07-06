document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const reportsList = document.getElementById('reports-list');
    const workspace = document.getElementById('workspace');
    const welcomeView = document.getElementById('welcome-view');
    const reportView = document.getElementById('report-view');
    const activeReportTitle = document.getElementById('active-report-title');
    const activeReportMeta = document.getElementById('active-report-meta');
    const metaDate = document.getElementById('meta-date');
    const metaHoldings = document.getElementById('meta-holdings');
    const metaWatchlist = document.getElementById('meta-watchlist');
    const portfolioQuickStats = document.getElementById('portfolio-quick-stats');
    
    const markdownRenderer = document.getElementById('markdown-renderer');
    const impactCardsContainer = document.getElementById('impact-cards-container');
    const signalsNewsList = document.getElementById('signals-news-list');
    const signalsFilingsList = document.getElementById('signals-filings-list');
    
    const btnGenerateReport = document.getElementById('btn-generate-report');
    const loadingOverlay = document.getElementById('loading-overlay');
    const loadingStatus = document.getElementById('loading-status');
    const stepCollect = document.getElementById('step-collect');
    const stepProcess = document.getElementById('step-process');
    const stepGenerate = document.getElementById('step-generate');
    
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    
    let activeReportId = null;

    // Initialize marked configuration
    marked.setOptions({
        gfm: true,
        breaks: true,
        headerIds: false
    });

    // Load Initial Data
    loadReports();
    loadPortfolioSummary();

    // Tab Switching
    tabButtons.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            
            tabButtons.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.remove('active'));
            
            btn.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // Fetch reports list from API
    async function loadReports() {
        try {
            const res = await fetch('/api/reports');
            if (!res.ok) throw new Error('Failed to fetch reports list');
            const data = await res.json();
            renderReportsSidebar(data);
        } catch (err) {
            console.error(err);
            reportsList.innerHTML = `
                <div class="loading-state">
                    <i class="fa-solid fa-triangle-exclamation text-danger"></i>
                    <span>Failed to load reports history</span>
                </div>
            `;
        }
    }

    // Fetch current portfolio positions to display in welcome screen
    async function loadPortfolioSummary() {
        try {
            const res = await fetch('/api/positions');
            if (!res.ok) throw new Error('Failed to fetch positions');
            const positions = await res.json();
            
            const holdings = positions.filter(p => p.scope === 'holding');
            const watchlist = positions.filter(p => p.scope === 'watchlist');
            
            portfolioQuickStats.innerHTML = `
                <div class="quick-stat-box">
                    <h4>Holdings</h4>
                    <p>${holdings.length} Assets</p>
                </div>
                <div class="quick-stat-box">
                    <h4>Watchlist</h4>
                    <p>${watchlist.length} Symbols</p>
                </div>
                <div class="quick-stat-box">
                    <h4>Profile</h4>
                    <p>Beginner</p>
                </div>
            `;
        } catch (err) {
            console.error(err);
        }
    }

    // Render reports list sidebar
    function renderReportsSidebar(reports) {
        if (reports.length === 0) {
            reportsList.innerHTML = `
                <div class="loading-state">
                    <i class="fa-solid fa-folder-open"></i>
                    <span>No reports generated yet.</span>
                </div>
            `;
            return;
        }

        reportsList.innerHTML = '';
        reports.forEach(report => {
            const item = document.createElement('div');
            item.className = `report-item ${activeReportId === report.id ? 'active' : ''}`;
            item.setAttribute('data-id', report.id);
            
            const dateStr = report.created_at ? formatDate(report.created_at) : 'Unknown date';
            const shortSummary = report.summary || 'Pre-market review and analysis.';

            item.innerHTML = `
                <div class="report-item-title">${report.title}</div>
                <div class="report-item-summary">${shortSummary}</div>
                <div class="report-item-footer">
                    <span>${dateStr}</span>
                    <div class="report-item-badge">
                        <span>H: ${report.holding_count}</span>
                        <span>W: ${report.watchlist_count}</span>
                    </div>
                </div>
            `;
            
            item.addEventListener('click', () => selectReport(report.id));
            reportsList.appendChild(item);
        });
    }

    // Select a report and fetch full details
    async function selectReport(reportId) {
        activeReportId = reportId;
        
        // Highlight active item in list
        document.querySelectorAll('.report-item').forEach(item => {
            if (parseInt(item.getAttribute('data-id')) === reportId) {
                item.classList.add('active');
            } else {
                item.classList.remove('active');
            }
        });

        // Show loading state in view
        activeReportTitle.innerText = "Loading Report...";
        activeReportMeta.style.display = 'none';
        welcomeView.style.display = 'none';
        reportView.style.display = 'none';

        try {
            const res = await fetch(`/api/reports/${reportId}`);
            if (!res.ok) throw new Error('Failed to load report details');
            const report = await res.json();
            
            // Show report panel
            reportView.style.display = 'block';
            
            // Set header meta
            activeReportTitle.innerText = report.title;
            metaDate.innerText = report.created_at ? formatDate(report.created_at) : 'N/A';
            metaHoldings.innerText = `${report.holding_count} Holdings`;
            metaWatchlist.innerText = `${report.watchlist_count} Watchlist`;
            activeReportMeta.style.display = 'flex';
            
            // Render markdown content
            markdownRenderer.innerHTML = marked.parse(report.content);

            // Parse json data and populate summary panels
            let context = null;
            if (report.json_data) {
                try {
                    context = JSON.parse(report.json_data);
                } catch (e) {
                    console.error('Failed to parse json_data', e);
                }
            }

            renderSummaryDashboard(context);

        } catch (err) {
            console.error(err);
            activeReportTitle.innerText = "Error Loading Report";
        }
    }

    // Render interactive widgets using parsed context JSON
    function renderSummaryDashboard(context) {
        impactCardsContainer.innerHTML = '';
        signalsNewsList.innerHTML = '';
        signalsFilingsList.innerHTML = '';

        if (!context) {
            impactCardsContainer.innerHTML = '<p class="text-muted">No visual impact scores stored for this report.</p>';
            signalsNewsList.innerHTML = '<p class="text-muted">No news data analyzed.</p>';
            signalsFilingsList.innerHTML = '<p class="text-muted">No filings analyzed.</p>';
            return;
        }

        // Render Impact Assessments
        if (context.impacts && context.impacts.length > 0) {
            context.impacts.forEach(imp => {
                const card = document.createElement('div');
                card.className = 'impact-card';
                
                let badgeClass = 'badge-neutral';
                let fillClass = 'fill-neutral';
                let badgeLabel = 'Neutral';
                
                if (imp.score > 20) {
                    badgeClass = 'badge-positive';
                    fillClass = 'fill-positive';
                    badgeLabel = 'Positive';
                } else if (imp.score < -20) {
                    badgeClass = 'badge-negative';
                    fillClass = 'fill-negative';
                    badgeLabel = 'Negative';
                } else {
                    badgeClass = 'badge-neutral';
                    fillClass = 'fill-neutral';
                    badgeLabel = 'Mixed/Neutral';
                }

                // Map -100 to 100 into a 0 to 100 percentage bar
                // Let's make the progress bar fill out from 0% to Math.abs(score)%
                const scorePercent = Math.min(100, Math.max(0, Math.abs(imp.score)));

                card.innerHTML = `
                    <div class="impact-card-header">
                        <span class="impact-symbol">${imp.symbol}</span>
                        <span class="impact-badge ${badgeClass}">${badgeLabel}</span>
                    </div>
                    <div class="score-meter-container">
                        <span>Score: ${imp.score > 0 ? '+' : ''}${imp.score}</span>
                        <div class="score-meter">
                            <div class="score-fill ${fillClass}" style="width: ${scorePercent}%"></div>
                        </div>
                    </div>
                    <div class="impact-card-body">
                        <p>${imp.reason}</p>
                    </div>
                `;
                impactCardsContainer.appendChild(card);
            });
        } else {
            impactCardsContainer.innerHTML = '<p class="text-muted">No holding impact scores computed.</p>';
        }

        // Render News analyzed
        if (context.news && context.news.length > 0) {
            context.news.forEach(item => {
                const el = document.createElement('div');
                el.className = 'signal-item';
                
                const urlAttr = item.url ? `href="${item.url}" target="_blank"` : 'href="#"';
                const dateStr = item.published_at ? formatDate(item.published_at) : 'Recent';
                const source = item.source || 'News Source';

                el.innerHTML = `
                    <div class="signal-item-header">
                        <span>${source}</span>
                        <span>${dateStr}</span>
                    </div>
                    <a ${urlAttr} class="signal-item-title">${item.title}</a>
                    <span class="badge-tag">${item.symbol}</span>
                `;
                signalsNewsList.appendChild(el);
            });
        } else {
            signalsNewsList.innerHTML = '<div class="loading-state">No relevant news items found for this report.</div>';
        }

        // Render SEC filings analyzed
        if (context.filings && context.filings.length > 0) {
            context.filings.forEach(item => {
                const el = document.createElement('div');
                el.className = 'signal-item';

                const urlAttr = item.url ? `href="${item.url}" target="_blank"` : 'href="#"';
                const dateStr = item.filed_at ? formatDate(item.filed_at) : 'Recent';

                el.innerHTML = `
                    <div class="signal-item-header">
                        <span>Form ${item.form_type}</span>
                        <span>${dateStr}</span>
                    </div>
                    <a ${urlAttr} class="signal-item-title">${item.title}</a>
                    <span class="badge-tag">${item.symbol}</span>
                `;
                signalsFilingsList.appendChild(el);
            });
        } else {
            signalsFilingsList.innerHTML = '<div class="loading-state">No SEC filings processed.</div>';
        }
    }

    // Trigger report generation
    btnGenerateReport.addEventListener('click', async () => {
        // Show loading screen
        showLoadingState();

        try {
            // POST request to generate endpoint
            const res = await fetch('/api/reports/generate', { method: 'POST' });
            if (!res.ok) throw new Error('Report generation endpoint failed');
            const data = await res.json();
            
            if (data.error) {
                alert('Generation failed: ' + data.error);
                hideLoadingState();
                return;
            }

            // Close loading screen and reload reports
            completeStep('step-generate');
            setTimeout(async () => {
                hideLoadingState();
                await loadReports();
                if (data.id) {
                    await selectReport(data.id);
                }
            }, 600);

        } catch (err) {
            console.error(err);
            alert('Failed to generate report: ' + err.message);
            hideLoadingState();
        }
    });

    // Helper functions for loading overlay
    function showLoadingState() {
        loadingOverlay.style.display = 'flex';
        
        // Reset states
        resetStep('step-collect');
        resetStep('step-process');
        resetStep('step-generate');
        
        loadingStatus.innerText = "Gathering signals from yfinance & SEC EDGAR...";
        activateStep('step-collect');

        // Simulate steps updates to feel nice
        setTimeout(() => {
            completeStep('step-collect');
            activateStep('step-process');
            loadingStatus.innerText = "Computing holding sentiment and impact scores...";
        }, 6000);

        setTimeout(() => {
            completeStep('step-process');
            activateStep('step-generate');
            loadingStatus.innerText = "Asking Gemini AI to draft pre-market review...";
        }, 12000);
    }

    function hideLoadingState() {
        loadingOverlay.style.display = 'none';
    }

    function activateStep(id) {
        const step = document.getElementById(id);
        step.className = 'step active';
        step.querySelector('i').className = 'fa-solid fa-circle-dot';
    }

    function completeStep(id) {
        const step = document.getElementById(id);
        step.className = 'step done';
        step.querySelector('i').className = 'fa-solid fa-circle-check';
    }

    function resetStep(id) {
        const step = document.getElementById(id);
        step.className = 'step';
        step.querySelector('i').className = 'fa-solid fa-circle-dot';
    }

    // Helper date formatting
    function formatDate(dateStr) {
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
    }
});
