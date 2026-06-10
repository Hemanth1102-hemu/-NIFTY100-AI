// ============================================================
//  NIFTY100-AI  |  dashboard.js  —  REAL DATA VERSION
// ============================================================

const PAGES = {
    overview:        document.getElementById('overviewPage'),
    companies:       document.getElementById('companiesPage'),
    sectors:         document.getElementById('sectorsPage'),
    'ai-predictions':document.getElementById('aiPredictionsPage'),
    screeners:       document.getElementById('screenersPage'),
};

let allCompanies = [];
let allSectors   = [];
let dashboardData = null;  // from /api/dashboard-summary/
let modalChartInstance = null;
let revenueChartInstance = null;
let healthChartInstance  = null;
let sectorPieInstance    = null;
let sectorHealthBarInstance = null;
let mlHistInstance       = null;
let mlDonutInstance      = null;

// ── Helpers ─────────────────────────────────────────────────
const fmt = (n, dec = 0) => n == null ? 'N/A' : Number(n).toLocaleString('en-IN', { minimumFractionDigits: dec, maximumFractionDigits: dec });
const fmtCr = n => n == null ? 'N/A' : '₹ ' + fmt(n);
const healthLabel = s => s >= 85 ? 'Excellent' : s >= 70 ? 'Good' : s >= 50 ? 'Average' : s >= 35 ? 'Weak' : 'Poor';
const healthClass = s => s >= 85 ? 'health-excellent' : s >= 70 ? 'health-good' : s >= 50 ? 'health-fair' : 'health-poor';

// ── Page Navigation ─────────────────────────────────────────
function showPage(page) {
    Object.keys(PAGES).forEach(key => {
        if (PAGES[key]) PAGES[key].style.display = (key === page) ? 'block' : 'none';
    });
    document.querySelectorAll('.nav-link[data-page]').forEach(l => {
        l.classList.toggle('active', l.getAttribute('data-page') === page);
    });

    const titles = {
        overview:         ['Market Intelligence Dashboard', 'Real-time financial analysis & AI health scoring for Nifty 100 firms.'],
        companies:        ['Company Explorer', 'Browse and analyse every Nifty 100 company with live financial data.'],
        sectors:          ['Sector Comparison Analyzer', 'Compare sectors by revenue, health, and company distribution.'],
        'ai-predictions': ['Financial Health Scorecard', 'ML-powered health scores, anomaly detection, and cluster analysis.'],
        screeners:        ['Stock Screener', 'Filter Nifty 100 companies using institutional-grade financial criteria.'],
    };
    document.getElementById('pageTitle').innerText    = (titles[page] || ['--', ''])[0];
    document.getElementById('pageSubtitle').innerText = (titles[page] || ['', '--'])[1];
}

// ── API Fetch ────────────────────────────────────────────────
async function fetchAll(url) {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return data.results || data;
}

// ============================================================
//  OVERVIEW PAGE  —  uses REAL data from dashboard-summary
// ============================================================
function renderOverview() {
    document.getElementById('kpiCompanies').innerText = allCompanies.length;

    // Real KPIs
    if (dashboardData) {
        const totalRev = dashboardData.total_revenue || 0;
        // Format in Cr or Lakh Cr
        if (totalRev >= 100000) {
            document.getElementById('kpiRevenue').innerText = '₹ ' + fmt(Math.round(totalRev / 100), 0) + ' LCr';
        } else {
            document.getElementById('kpiRevenue').innerText = '₹ ' + fmt(Math.round(totalRev), 0) + ' Cr';
        }
        document.getElementById('kpiOPM').innerText = dashboardData.avg_opm + '%';
        document.getElementById('kpiMLCoverage').innerText = allCompanies.length + '/' + allCompanies.length;
    }

    populateOverviewTable(allCompanies);
    renderRevenueChart();
    renderHealthChart();
}

function populateOverviewTable(companies) {
    const tbody = document.getElementById('companyTableBody');
    if (!companies.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">No data found.</td></tr>';
        return;
    }
    const sorted = [...companies].sort((a,b) => b._rev - a._rev);
    tbody.innerHTML = sorted.slice(0, 15).map((c, i) => `
        <tr>
            <td>${i + 1}</td>
            <td>
                <div class="company-cell">
                    <span class="symbol-tag">${c.symbol}</span>
                    <span class="company-name-small">${c.name}</span>
                </div>
            </td>
            <td><span class="sector-pill">${c.sector_name || 'N/A'}</span></td>
            <td>₹ ${fmt(c._rev)}</td>
            <td class="${c._roe > 15 ? 'text-green' : 'text-muted'}">${Number(c._roe).toFixed(1)}%</td>
            <td><span class="health-badge ${healthClass(c._health)}">${c._health}</span></td>
            <td><button class="details-btn" onclick="openCompanyModal(${c.id})">View</button></td>
        </tr>
    `).join('');
}

function renderRevenueChart() {
    const ctx = document.getElementById('revenueChart').getContext('2d');
    if (revenueChartInstance) revenueChartInstance.destroy();

    // Use real sector summary data
    let sectorRevenue = {};
    if (dashboardData && dashboardData.sector_summary) {
        dashboardData.sector_summary.forEach(s => {
            sectorRevenue[s.name] = s.total_revenue;
        });
    } else {
        allCompanies.forEach(c => {
            const s = c.sector_name || 'Other';
            sectorRevenue[s] = (sectorRevenue[s] || 0) + (c._rev || 0);
        });
    }
    const sorted = Object.entries(sectorRevenue).sort((a,b)=>b[1]-a[1]).slice(0,7);
    const colors = ['#6366f1','#ec4899','#10b981','#f59e0b','#3b82f6','#8b5cf6','#ef4444'];
    revenueChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: sorted.map(([k])=>k),
            datasets: [{ label: 'Total Revenue (Cr)', data: sorted.map(([,v])=>v), backgroundColor: colors, borderRadius: 6 }]
        },
        options: {
            responsive: true, maintainAspectRatio: false, indexAxis: 'y',
            plugins: { legend: { display: false } },
            scales: {
                x: { grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94a3b8' } },
                y: { grid: { display: false }, ticks: { color: '#f8fafc' } }
            }
        }
    });
}

function renderHealthChart() {
    const ctx = document.getElementById('healthChart').getContext('2d');
    if (healthChartInstance) healthChartInstance.destroy();

    // Use real sector summary
    let labels = [];
    let data = [];
    if (dashboardData && dashboardData.sector_summary) {
        const sorted = [...dashboardData.sector_summary].sort((a,b) => b.avg_health - a.avg_health);
        labels = sorted.map(s => s.name);
        data = sorted.map(s => Math.round(s.avg_health));
    } else {
        const sectorScores = {};
        const sectorCounts = {};
        allCompanies.forEach(c => {
            const s = c.sector_name || 'Other';
            sectorScores[s] = (sectorScores[s] || 0) + (c._health || 0);
            sectorCounts[s] = (sectorCounts[s] || 0) + 1;
        });
        labels = Object.keys(sectorScores);
        data = labels.map(l => Math.round(sectorScores[l] / sectorCounts[l]));
    }

    const colors = data.map(v => v >= 80 ? '#10b981' : v >= 60 ? '#6366f1' : '#ef4444');
    healthChartInstance = new Chart(ctx, {
        type: 'bar',
        data: { labels, datasets: [{ label: 'Avg Health Score', data, backgroundColor: colors, borderRadius: 6 }] },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: { legend: { display: false } },
            scales: {
                y: { min:0, max:100, grid: { color: 'rgba(255,255,255,0.04)' }, ticks: { color: '#94a3b8' } },
                x: { grid: { display: false }, ticks: { color: '#f8fafc', maxRotation: 30, font:{size:10} } }
            }
        }
    });
}

// ── Overview search ─────────────────────────────────────────
document.getElementById('companySearch').addEventListener('input', e => {
    const q = e.target.value.toLowerCase();
    populateOverviewTable(q ? allCompanies.filter(c =>
        c.name.toLowerCase().includes(q) || c.symbol.toLowerCase().includes(q)
    ) : allCompanies);
});

// ============================================================
//  COMPANIES PAGE
// ============================================================
function renderCompaniesPage() {
    const sel = document.getElementById('sectorFilter');
    sel.innerHTML = '<option value="">All Sectors</option>';
    allSectors.forEach(s => {
        sel.innerHTML += `<option value="${s.id}">${s.name}</option>`;
    });
    populateCompaniesTable(allCompanies);
}

function populateCompaniesTable(companies) {
    document.getElementById('companyCount').innerText = `${companies.length} companies`;
    const tbody = document.getElementById('allCompaniesBody');
    if (!companies.length) {
        tbody.innerHTML = '<tr><td colspan="7" class="loading-cell">No companies match your filter.</td></tr>';
        return;
    }
    tbody.innerHTML = companies.map((c, i) => `
        <tr>
            <td>${i+1}</td>
            <td><span class="symbol-tag">${c.symbol}</span></td>
            <td>${c.name}</td>
            <td><span class="sector-pill">${c.sector_name || 'N/A'}</span></td>
            <td>${c.industry || '—'}</td>
            <td style="font-size:0.75rem;color:var(--text-muted);">${c.isin_code || '—'}</td>
            <td><button class="details-btn" onclick="openCompanyModal(${c.id})"><i class="fa-solid fa-chart-area"></i> Analyse</button></td>
        </tr>
    `).join('');
}

// Sector & Search filters
document.getElementById('sectorFilter').addEventListener('change', applyCompanyFilters);
document.getElementById('companyFilterSearch').addEventListener('input', applyCompanyFilters);
function applyCompanyFilters() {
    const sectorId = document.getElementById('sectorFilter').value;
    const q = document.getElementById('companyFilterSearch').value.toLowerCase();
    let filtered = allCompanies;
    if (sectorId) filtered = filtered.filter(c => String(c.sector) === sectorId);
    if (q)        filtered = filtered.filter(c => c.name.toLowerCase().includes(q) || c.symbol.toLowerCase().includes(q));
    populateCompaniesTable(filtered);
}

// ── Company Modal  —  fetches REAL financials ────────────────
async function openCompanyModal(id) {
    const c = allCompanies.find(x => x.id === id);
    if (!c) return;
    document.getElementById('modalCompanyName').innerText   = `${c.symbol} — ${c.name}`;
    document.getElementById('modalCompanySector').innerText = c.sector_name || '';

    // Show cached values first
    document.getElementById('mRevenue').innerText  = fmtCr(c._rev);
    document.getElementById('mProfit').innerText   = fmtCr(c._profit);
    document.getElementById('mROE').innerText      = Number(c._roe).toFixed(1) + '%';
    document.getElementById('mDE').innerText       = Number(c._de).toFixed(2);
    document.getElementById('mOPM').innerText      = Number(c._opm).toFixed(1) + '%';
    document.getElementById('mHealth').innerText   = c._health || '--';

    document.getElementById('companyModal').style.display = 'flex';

    // Fetch REAL historical financials for this company
    try {
        const financials = await fetchAll(`/api/companies/${id}/financials/`);
        // Filter non-TTM years and sort ascending
        const yearly = financials
            .filter(f => !f.is_ttm && f.year < 9999)
            .sort((a,b) => a.year - b.year);

        if (yearly.length > 0) {
            const latest = yearly[yearly.length - 1];
            document.getElementById('mRevenue').innerText = fmtCr(latest.sales);
            document.getElementById('mProfit').innerText  = fmtCr(latest.net_profit);
            document.getElementById('mOPM').innerText     = Number(latest.opm_percentage || 0).toFixed(1) + '%';
            document.getElementById('mDE').innerText      = Number(latest.debt_to_equity || 0).toFixed(2);
        }

        // Chart with real data
        const ctx = document.getElementById('modalChart').getContext('2d');
        if (modalChartInstance) modalChartInstance.destroy();

        const last6 = yearly.slice(-6);
        const years = last6.map(f => String(f.year));
        const revData = last6.map(f => Number(f.sales || 0));
        const profData = last6.map(f => Number(f.net_profit || 0));

        modalChartInstance = new Chart(ctx, {
            data: {
                labels: years,
                datasets: [
                    { type:'bar',  label:'Revenue (Cr)',  data: revData,  backgroundColor:'rgba(99,102,241,0.5)', borderRadius:4, yAxisID:'y' },
                    { type:'line', label:'Profit (Cr)',   data: profData, borderColor:'#10b981', tension:0.4, pointRadius:3, yAxisID:'y1' }
                ]
            },
            options: {
                responsive:true, maintainAspectRatio:true,
                plugins:{ legend:{ labels:{ color:'#f8fafc', font:{size:11} } } },
                scales:{
                    y:  { grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#94a3b8'} },
                    y1: { position:'right', grid:{display:false}, ticks:{color:'#10b981'} }
                }
            }
        });
    } catch (err) {
        console.error('Error fetching financials:', err);
        // Show chart with whatever we have
        const ctx = document.getElementById('modalChart').getContext('2d');
        if (modalChartInstance) modalChartInstance.destroy();
        modalChartInstance = new Chart(ctx, {
            type: 'bar',
            data: { labels: ['N/A'], datasets: [{ label: 'No data', data: [0], backgroundColor: '#6366f1' }] },
            options: { responsive: true, maintainAspectRatio: true }
        });
    }
}

document.getElementById('closeModal').addEventListener('click', () => {
    document.getElementById('companyModal').style.display = 'none';
});
document.getElementById('modalBackdrop').addEventListener('click', () => {
    document.getElementById('companyModal').style.display = 'none';
});

// ============================================================
//  SECTORS PAGE  —  REAL data
// ============================================================
function renderSectorsPage() {
    const sectorMap = {};
    allCompanies.forEach(c => {
        const s = c.sector_name || 'Other';
        if (!sectorMap[s]) sectorMap[s] = { count: 0, health: 0, revenue: 0, opm: 0 };
        sectorMap[s].count++;
        sectorMap[s].health += c._health || 0;
        sectorMap[s].revenue += c._rev || 0;
        sectorMap[s].opm += c._opm || 0;
    });
    const entries = Object.entries(sectorMap).sort((a,b) => b[1].count - a[1].count);
    const largest = entries[0] ? entries[0][0] : '--';
    document.getElementById('kpiSectorCount').innerText    = entries.length;
    document.getElementById('kpiLargestSector').innerText  = largest;

    // Sector table
    const tbody = document.getElementById('sectorTableBody');
    tbody.innerHTML = entries.map(([name, data], i) => {
        const avg = Math.round(data.health / data.count);
        return `<tr>
            <td>${i+1}</td>
            <td><strong>${name}</strong></td>
            <td>${data.count}</td>
            <td><span class="health-badge ${healthClass(avg)}">${avg}</span></td>
            <td style="color:var(--text-muted);font-size:0.8rem;">₹ ${fmt(Math.round(data.revenue))} Cr</td>
        </tr>`;
    }).join('');

    // Pie chart
    const pieCtx = document.getElementById('sectorPieChart').getContext('2d');
    if (sectorPieInstance) sectorPieInstance.destroy();
    const pieColors = ['#6366f1','#ec4899','#10b981','#f59e0b','#3b82f6','#8b5cf6','#ef4444','#14b8a6','#f97316','#84cc16','#a855f7','#06b6d4','#d946ef','#64748b','#fb923c','#22d3ee','#fbbf24','#34d399'];
    sectorPieInstance = new Chart(pieCtx, {
        type: 'doughnut',
        data: {
            labels: entries.map(([k])=>k),
            datasets:[{ data: entries.map(([,v])=>v.count), backgroundColor: pieColors, borderWidth:2, borderColor:'#1e293b' }]
        },
        options:{
            responsive:true, maintainAspectRatio:false,
            plugins:{ legend:{ position:'right', labels:{ color:'#f8fafc', font:{size:11} } } }
        }
    });

    // Bar chart — avg health
    const barCtx = document.getElementById('sectorHealthBar').getContext('2d');
    if (sectorHealthBarInstance) sectorHealthBarInstance.destroy();
    const avgHealthData = entries.map(([,v]) => Math.round(v.health / v.count));
    sectorHealthBarInstance = new Chart(barCtx, {
        type:'bar',
        data:{
            labels: entries.map(([k])=>k),
            datasets:[{ label:'Avg Health Score', data: avgHealthData,
                backgroundColor: avgHealthData.map(v=> v>=80?'#10b981': v>=60?'#6366f1':'#ef4444'),
                borderRadius:6 }]
        },
        options:{
            responsive:true, maintainAspectRatio:false,
            plugins:{ legend:{display:false} },
            scales:{
                y:{ min:0, max:100, grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#94a3b8'} },
                x:{ grid:{display:false}, ticks:{color:'#f8fafc', maxRotation:35, font:{size:10}} }
            }
        }
    });
}

// ============================================================
//  AI PREDICTIONS PAGE  —  REAL ML scores
// ============================================================
function renderAIPredictionsPage() {
    const excellent = allCompanies.filter(c => c._health >= 85).length;
    const good      = allCompanies.filter(c => c._health >= 70 && c._health < 85).length;
    const poor      = allCompanies.filter(c => c._health < 50).length;
    document.getElementById('kpiExcellent').innerText = excellent;
    document.getElementById('kpiGood').innerText      = good;
    document.getElementById('kpiPoor').innerText      = poor;

    // Histogram (buckets: <35, 35-49, 50-69, 70-84, 85-100)
    const buckets = [0,0,0,0,0];
    allCompanies.forEach(c => {
        const s = c._health;
        if      (s < 35)  buckets[0]++;
        else if (s < 50)  buckets[1]++;
        else if (s < 70)  buckets[2]++;
        else if (s < 85)  buckets[3]++;
        else              buckets[4]++;
    });
    const histCtx = document.getElementById('mlHistogram').getContext('2d');
    if (mlHistInstance) mlHistInstance.destroy();
    mlHistInstance = new Chart(histCtx, {
        type:'bar',
        data:{
            labels:['Poor (<35)','Weak (35-49)','Average (50-69)','Good (70-84)','Excellent (85+)'],
            datasets:[{ label:'Companies', data:buckets,
                backgroundColor:['#ef4444','#f97316','#f59e0b','#6366f1','#10b981'],
                borderRadius:6 }]
        },
        options:{
            responsive:true, maintainAspectRatio:false,
            plugins:{ legend:{display:false} },
            scales:{ y:{grid:{color:'rgba(255,255,255,0.04)'}, ticks:{color:'#94a3b8'}}, x:{grid:{display:false}, ticks:{color:'#f8fafc'}} }
        }
    });

    // Donut
    const donutCtx = document.getElementById('mlDonut').getContext('2d');
    if (mlDonutInstance) mlDonutInstance.destroy();
    const attention = allCompanies.filter(c => c._health < 70).length;
    mlDonutInstance = new Chart(donutCtx, {
        type:'doughnut',
        data:{
            labels:['Excellent (≥85)','Good (70–84)','Needs Attention (<70)'],
            datasets:[{ data:[excellent,good,attention], backgroundColor:['#10b981','#6366f1','#ef4444'], borderWidth:2, borderColor:'#1e293b' }]
        },
        options:{ responsive:true, maintainAspectRatio:false, plugins:{ legend:{ position:'bottom', labels:{color:'#f8fafc'} } } }
    });

    populateMLScorecard('all');

    // Filter pills
    document.querySelectorAll('.filter-pill').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.filter-pill').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            populateMLScorecard(btn.getAttribute('data-filter'));
        });
    });
}

function populateMLScorecard(filter) {
    let data = [...allCompanies].sort((a,b) => b._health - a._health);
    if (filter === 'excellent') data = data.filter(c => c._health >= 85);
    else if (filter === 'good') data = data.filter(c => c._health >= 70 && c._health < 85);
    else if (filter === 'poor') data = data.filter(c => c._health < 70);

    const tbody = document.getElementById('mlScorecardBody');
    tbody.innerHTML = data.map((c, i) => `
        <tr>
            <td>${i+1}</td>
            <td><span class="symbol-tag">${c.symbol}</span></td>
            <td>${c.sector_name || 'N/A'}</td>
            <td>
                <div class="score-bar-wrapper">
                    <div class="score-bar" style="width:${c._health}%;background:${c._health>=85?'#10b981':c._health>=70?'#6366f1':c._health>=50?'#f59e0b':'#ef4444'};"></div>
                    <span>${c._health}</span>
                </div>
            </td>
            <td><span class="health-badge ${healthClass(c._health)}">${healthLabel(c._health)}</span></td>
            <td>${c._anomaly ? '<span class="anomaly-tag"><i class="fa-solid fa-triangle-exclamation"></i> Flagged</span>' : '<span style="color:#10b981;">Normal</span>'}</td>
            <td>Cluster ${c._cluster || '—'}</td>
        </tr>
    `).join('');
}

// ============================================================
//  SCREENERS PAGE  —  uses REAL data
// ============================================================
const SCREENER_DEFS = {
    topROE:          { title: 'Top ROE Companies (ROE ≥ 20%)',       fn: c => c._roe >= 20 },
    debtFree:        { title: 'Debt-Free Companies (D/E < 0.1)',     fn: c => Number(c._de) < 0.1 },
    highOPM:         { title: 'High Margin Companies (OPM ≥ 25%)',   fn: c => c._opm >= 25 },
    excellentHealth: { title: 'Excellent Health Score (≥ 85)',        fn: c => c._health >= 85 },
    consistentProfit:{ title: 'Consistent Profitability',            fn: c => c._profit > 0 },
    anomaly:         { title: 'ML Anomaly Detected Companies',       fn: c => c._anomaly === true },
};

function renderScreenersPage() {
    document.querySelectorAll('.screener-run-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.getAttribute('data-screener');
            runScreener(key);
        });
    });
}

function runScreener(key) {
    const def = SCREENER_DEFS[key];
    if (!def) return;
    const results = allCompanies.filter(def.fn);
    document.getElementById('screenerResults').style.display = 'block';
    document.getElementById('screenerResultTitle').innerHTML = `<i class="fa-solid fa-filter"></i> ${def.title}`;
    document.getElementById('screenerResultCount').innerText = `${results.length} companies`;
    document.getElementById('screenerResultBody').innerHTML = results.map((c,i) => `
        <tr>
            <td>${i+1}</td>
            <td><span class="symbol-tag">${c.symbol}</span></td>
            <td>${c.name}</td>
            <td><span class="sector-pill">${c.sector_name || 'N/A'}</span></td>
            <td>₹ ${fmt(c._rev)}</td>
            <td class="${c._roe>=15?'text-green':'text-muted'}">${Number(c._roe).toFixed(1)}%</td>
            <td><span class="health-badge ${healthClass(c._health)}">${c._health}</span></td>
        </tr>
    `).join('') || '<tr><td colspan="7" class="loading-cell">No companies match this screen.</td></tr>';
    document.getElementById('screenerResults').scrollIntoView({ behavior:'smooth' });
}

// ============================================================
//  INIT  —  fetch REAL data from dashboard-summary
// ============================================================
document.addEventListener('DOMContentLoaded', async () => {
    // Nav
    document.querySelectorAll('.nav-link[data-page]').forEach(link => {
        link.addEventListener('click', e => {
            e.preventDefault();
            const page = link.getAttribute('data-page');
            showPage(page);
            if (page === 'companies'        && allCompanies.length) renderCompaniesPage();
            if (page === 'sectors'          && allCompanies.length) renderSectorsPage();
            if (page === 'ai-predictions'   && allCompanies.length) renderAIPredictionsPage();
            if (page === 'screeners'        && allCompanies.length) renderScreenersPage();
        });
    });

    // Refresh btn
    document.getElementById('refreshBtn').addEventListener('click', () => location.reload());

    try {
        // Load sectors first
        allSectors = await fetchAll('/api/sectors/');

        const sectorIdx = {};
        allSectors.forEach(s => { sectorIdx[s.id] = s.name; });

        // Load dashboard summary with REAL pre-computed data
        dashboardData = await fetchAll('/api/dashboard-summary/');

        // Use the companies_list from dashboard summary (has all real financials)
        if (dashboardData && dashboardData.companies_list) {
            allCompanies = dashboardData.companies_list.map(c => ({
                ...c,
                // Map real financial data to the properties the UI expects
                _rev:     c.revenue || 0,
                _profit:  c.net_profit || 0,
                _roe:     c.roe || 0,
                _opm:     c.opm || 0,
                _de:      c.debt_to_equity || 0,
                _health:  c.health_score || 0,
                _anomaly: c.anomaly || false,
                _cluster: c.cluster || 0,
            }));
        } else {
            // Fallback: load from /api/companies/
            allCompanies = await fetchAll('/api/companies/');
            allCompanies.forEach(c => {
                c.sector_name = sectorIdx[c.sector] || 'Other';
                c._rev = 0; c._profit = 0; c._roe = 0;
                c._opm = 0; c._de = 0; c._health = 0;
                c._anomaly = false; c._cluster = 0;
            });
        }

        renderOverview();
        showPage('overview');

    } catch (err) {
        console.error('Init error:', err);
        document.getElementById('companyTableBody').innerHTML =
            `<tr><td colspan="7" class="loading-cell" style="color:#ef4444;"><i class="fa-solid fa-circle-exclamation"></i> Failed to load data. Check API & DB connection.</td></tr>`;
    }
});
