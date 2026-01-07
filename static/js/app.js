/**
 * Web API Performance Analyzer - Frontend Application v2
 * URL analizi için interaktif dashboard + grafikler
 */

// API Base URL
const API_BASE = '';

// Global chart instances
let timingChart = null;
let securityChart = null;
let historyChart = null;

// DOM Elements
const navItems = document.querySelectorAll('.nav-item');
const sections = document.querySelectorAll('.section');
const pageTitle = document.getElementById('page-title');

// Page Titles
const pageTitles = {
    analyzer: 'URL Analizi',
    history: 'Analiz Geçmişi',
    detail: 'URL Detayı',
    about: 'Hakkında'
};

// Initialize Application
document.addEventListener('DOMContentLoaded', () => {
    initNavigation();

    // Enter tuşu ile analiz
    document.getElementById('url-input').addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            analyzeURL();
        }
    });
});

// Navigation
function initNavigation() {
    navItems.forEach(item => {
        item.addEventListener('click', () => {
            const section = item.dataset.section;
            switchSection(section);
        });
    });
}

function switchSection(section) {
    // Update active states
    navItems.forEach(nav => nav.classList.remove('active'));
    document.querySelector(`[data-section="${section}"]`).classList.add('active');

    // Show selected section
    sections.forEach(sec => sec.classList.remove('active'));
    document.getElementById(`${section}-section`).classList.add('active');

    // Update page title
    pageTitle.textContent = pageTitles[section];

    // Load data for section
    if (section === 'history') {
        loadHistory();
    }
}

// Set URL from quick links
function setURL(url) {
    document.getElementById('url-input').value = url;
    document.getElementById('url-input').focus();
}

// ============================================
// URL Analysis
// ============================================
async function analyzeURL() {
    const urlInput = document.getElementById('url-input');
    const url = urlInput.value.trim();

    if (!url) {
        showToast('Lütfen bir URL girin', 'error');
        urlInput.focus();
        return;
    }

    // UI state
    const analyzeBtn = document.getElementById('analyze-btn');
    const loadingState = document.getElementById('loading-state');
    const resultsContainer = document.getElementById('results-container');

    // Disable button and show loading
    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">Analiz Ediliyor...</span>';
    loadingState.classList.remove('hidden');
    resultsContainer.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE}/analyze`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || 'Analiz başarısız');
        }

        // Render results
        renderResults(data);

        showToast('Analiz tamamlandı!', 'success');

    } catch (error) {
        console.error('Analiz hatası:', error);
        showToast(error.message || 'Analiz sırasında hata oluştu', 'error');
    } finally {
        // Reset button
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = '<span class="btn-icon">🚀</span><span class="btn-text">Analiz Et</span>';
        loadingState.classList.add('hidden');
    }
}

function renderResults(data) {
    const resultsContainer = document.getElementById('results-container');

    // Show results container
    resultsContainer.classList.remove('hidden');

    const performance = data.performance || {};
    const security = data.security || {};
    const ssl = data.ssl || {};
    const suggestions = data.suggestions || [];

    // 1. Grade Cards
    renderGradeCards(performance, security);

    // 2. Stats Grid
    renderStatsGrid(performance);

    // 3. Timing Chart
    renderTimingChart(performance.timing_breakdown || {});

    // 4. Security Chart
    renderSecurityChart(security.headers || {});

    // 5. Security Details
    renderSecurityDetails(security);

    // 6. SSL Info
    renderSSLInfo(ssl);

    // 7. Suggestions
    renderSuggestions(suggestions);

    // Scroll to results
    resultsContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderGradeCards(performance, security) {
    // Performance Grade
    const perfGrade = performance.performance_grade || '-';
    const perfColor = performance.performance_color || 'gray';
    const perfTime = performance.avg_response_time_ms || 0;

    document.getElementById('performance-grade').textContent = perfGrade;
    document.getElementById('performance-detail').textContent = `${perfTime.toFixed(0)}ms`;
    document.getElementById('performance-grade-card').className = `grade-card grade-${perfColor}`;

    // Security Grade
    const secHeaders = security.headers || {};
    const secGrade = secHeaders.grade || '-';
    const secColor = secHeaders.grade_color || 'gray';
    const secScore = secHeaders.score || 0;

    document.getElementById('security-grade').textContent = secGrade;
    document.getElementById('security-detail').textContent = `${secScore}/100`;
    document.getElementById('security-grade-card').className = `grade-card grade-${secColor}`;
}

function renderStatsGrid(performance) {
    const statsGrid = document.getElementById('stats-grid');
    const avgTime = performance.avg_response_time_ms || 0;
    const statusCode = performance.status_code || 0;
    const successRate = performance.success_rate || 0;
    const contentSize = formatBytes(performance.content_length || 0);
    const httpVersion = performance.http_version || 'N/A';

    statsGrid.innerHTML = `
        <div class="stat-card gradient-purple">
            <div class="stat-icon">⏱️</div>
            <div class="stat-info">
                <span class="stat-value">${avgTime.toFixed(0)}ms</span>
                <span class="stat-label">Ortalama Response</span>
            </div>
        </div>
        <div class="stat-card ${statusCode >= 200 && statusCode < 300 ? 'gradient-green' : 'gradient-orange'}">
            <div class="stat-icon">${statusCode >= 200 && statusCode < 300 ? '✅' : '⚠️'}</div>
            <div class="stat-info">
                <span class="stat-value">${statusCode}</span>
                <span class="stat-label">HTTP Status</span>
            </div>
        </div>
        <div class="stat-card gradient-blue">
            <div class="stat-icon">📦</div>
            <div class="stat-info">
                <span class="stat-value">${contentSize}</span>
                <span class="stat-label">Sayfa Boyutu</span>
            </div>
        </div>
        <div class="stat-card gradient-pink">
            <div class="stat-icon">🌐</div>
            <div class="stat-info">
                <span class="stat-value">${httpVersion}</span>
                <span class="stat-label">HTTP Versiyon</span>
            </div>
        </div>
    `;
}

function renderTimingChart(timing) {
    const ctx = document.getElementById('timing-chart').getContext('2d');

    // Destroy existing chart
    if (timingChart) {
        timingChart.destroy();
    }

    const labels = ['DNS Lookup', 'TCP Bağlantı', 'TLS Handshake', 'TTFB', 'İndirme'];
    const values = [
        timing.dns_lookup_ms || 0,
        timing.tcp_connection_ms || 0,
        timing.tls_handshake_ms || 0,
        timing.ttfb_ms || 0,
        timing.content_download_ms || 0
    ];

    timingChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: 'Süre (ms)',
                data: values,
                backgroundColor: [
                    'rgba(99, 102, 241, 0.8)',
                    'rgba(59, 130, 246, 0.8)',
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(245, 158, 11, 0.8)',
                    'rgba(236, 72, 153, 0.8)'
                ],
                borderRadius: 8
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });
}

function renderSecurityChart(headers) {
    const ctx = document.getElementById('security-chart').getContext('2d');

    // Destroy existing chart
    if (securityChart) {
        securityChart.destroy();
    }

    const headerList = headers.headers || [];
    const present = headerList.filter(h => h.present).length;
    const missing = headerList.filter(h => !h.present).length;

    securityChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Mevcut', 'Eksik'],
            datasets: [{
                data: [present, missing],
                backgroundColor: [
                    'rgba(16, 185, 129, 0.8)',
                    'rgba(239, 68, 68, 0.8)'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        color: '#94a3b8',
                        padding: 20
                    }
                }
            },
            cutout: '60%'
        }
    });
}

function renderSecurityDetails(security) {
    const container = document.getElementById('security-details');
    const headers = security.headers?.headers || [];

    if (headers.length === 0) {
        container.innerHTML = '<p class="text-muted">Güvenlik başlığı bilgisi yok</p>';
        return;
    }

    container.innerHTML = `
        <div class="security-header-grid">
            ${headers.map(h => `
                <div class="security-header-item ${h.present ? 'present' : 'missing'}">
                    <div class="header-status">
                        ${h.present ? '✅' : '❌'}
                    </div>
                    <div class="header-info">
                        <div class="header-name">${h.name}</div>
                        <div class="header-desc">${h.description}</div>
                        ${h.value ? `<div class="header-value">${h.value.substring(0, 50)}${h.value.length > 50 ? '...' : ''}</div>` : ''}
                        ${!h.present && h.recommendation ? `<div class="header-rec">💡 Önerilen: ${h.recommendation}</div>` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderSSLInfo(ssl) {
    const container = document.getElementById('ssl-info');
    const sslCard = document.getElementById('ssl-card');

    if (!ssl || !ssl.valid) {
        sslCard.classList.add('hidden');
        return;
    }

    sslCard.classList.remove('hidden');

    const daysClass = ssl.is_expired ? 'danger' : (ssl.expiring_soon ? 'warning' : 'success');

    container.innerHTML = `
        <div class="ssl-grid">
            <div class="ssl-item">
                <span class="ssl-label">🏢 Verilen</span>
                <span class="ssl-value">${ssl.subject || 'N/A'}</span>
            </div>
            <div class="ssl-item">
                <span class="ssl-label">🔏 Veren</span>
                <span class="ssl-value">${ssl.issuer || 'N/A'}</span>
            </div>
            <div class="ssl-item">
                <span class="ssl-label">📅 Son Geçerlilik</span>
                <span class="ssl-value">${ssl.not_after ? new Date(ssl.not_after).toLocaleDateString('tr-TR') : 'N/A'}</span>
            </div>
            <div class="ssl-item">
                <span class="ssl-label">⏳ Kalan Gün</span>
                <span class="ssl-value badge ${daysClass}">${ssl.days_remaining || 0} gün</span>
            </div>
            <div class="ssl-item">
                <span class="ssl-label">🔐 Protokol</span>
                <span class="ssl-value">${ssl.protocol || 'N/A'}</span>
            </div>
        </div>
    `;
}

function renderSuggestions(suggestions) {
    const container = document.getElementById('suggestions-container');

    if (suggestions.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">✨</div>
                <div class="empty-state-text">Herhangi bir öneri yok</div>
            </div>
        `;
        return;
    }

    // Kategorilere göre grupla
    const grouped = suggestions.reduce((acc, s) => {
        const cat = s.category || 'other';
        if (!acc[cat]) acc[cat] = [];
        acc[cat].push(s);
        return acc;
    }, {});

    container.innerHTML = Object.entries(grouped).map(([category, items]) => `
        <div class="suggestion-category">
            <h3 class="category-title">${getCategoryTitle(category)}</h3>
            ${items.map(s => `
                <div class="suggestion-item severity-${s.severity}">
                    <div class="suggestion-header-inline">
                        <span class="suggestion-title">${s.title}</span>
                        <span class="severity-badge severity-${s.severity}">${getSeverityText(s.severity)}</span>
                    </div>
                    <p class="suggestion-message">${s.message}</p>
                    ${s.recommendations && s.recommendations.length > 0 ? `
                        <ul class="recommendations-list">
                            ${s.recommendations.map(r => `<li>${r}</li>`).join('')}
                        </ul>
                    ` : ''}
                </div>
            `).join('')}
        </div>
    `).join('');
}

// ============================================
// History
// ============================================
async function loadHistory() {
    const tbody = document.getElementById('history-table');
    tbody.innerHTML = '<tr><td colspan="5" class="loading">Yükleniyor...</td></tr>';

    try {
        const response = await fetch(`${API_BASE}/analyze/history`);
        const data = await response.json();

        const items = data.items || [];

        if (items.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="empty-state">
                        <div class="empty-state-icon">📜</div>
                        <div class="empty-state-text">Henüz analiz geçmişi yok</div>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = items.map(item => `
            <tr>
                <td><code class="url-code">${truncateURL(item.url)}</code></td>
                <td><span class="badge info">${item.analysis_count}x</span></td>
                <td><span class="response-time ${getResponseTimeClass(item.avg_response_time_ms)}">${item.avg_response_time_ms.toFixed(0)} ms</span></td>
                <td>${formatDate(item.last_analyzed)}</td>
                <td>
                    <button class="detail-btn" onclick="loadURLDetail(${item.id})">
                        📊 Detay
                    </button>
                </td>
            </tr>
        `).join('');

    } catch (error) {
        console.error('Geçmiş yükleme hatası:', error);
        tbody.innerHTML = `
            <tr>
                <td colspan="5" class="empty-state">
                    <div class="empty-state-icon">❌</div>
                    <div class="empty-state-text">Geçmiş yüklenemedi</div>
                </td>
            </tr>
        `;
    }
}

// ============================================
// URL Detail
// ============================================
async function loadURLDetail(endpointId) {
    // Switch to detail section
    switchSection('detail');

    const container = document.getElementById('detail-content');
    container.innerHTML = '<div class="loading-state"><div class="loader"></div><p>Yükleniyor...</p></div>';

    try {
        const response = await fetch(`${API_BASE}/analyze/history/${endpointId}`);

        if (!response.ok) {
            throw new Error('URL detayı yüklenemedi');
        }

        const data = await response.json();
        renderURLDetail(data);

    } catch (error) {
        console.error('Detay yükleme hatası:', error);
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">❌</div>
                <div class="empty-state-text">${error.message}</div>
            </div>
        `;
    }
}

function renderURLDetail(data) {
    const container = document.getElementById('detail-content');
    const endpoint = data.endpoint || {};
    const stats = data.stats || {};
    const chartData = data.chart_data || [];
    const history = data.history || [];

    container.innerHTML = `
        <div class="detail-header">
            <h2>📊 ${endpoint.url || 'URL Detayı'}</h2>
            <p class="text-muted">İlk analiz: ${formatDate(endpoint.created_at)}</p>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card gradient-purple">
                <div class="stat-icon">📈</div>
                <div class="stat-info">
                    <span class="stat-value">${stats.total_analyses || 0}</span>
                    <span class="stat-label">Toplam Analiz</span>
                </div>
            </div>
            <div class="stat-card gradient-blue">
                <div class="stat-icon">⏱️</div>
                <div class="stat-info">
                    <span class="stat-value">${stats.avg_response_time_ms?.toFixed(0) || 0}ms</span>
                    <span class="stat-label">Ortalama Süre</span>
                </div>
            </div>
            <div class="stat-card gradient-green">
                <div class="stat-icon">✅</div>
                <div class="stat-info">
                    <span class="stat-value">${stats.success_count || 0}</span>
                    <span class="stat-label">Başarılı</span>
                </div>
            </div>
            <div class="stat-card gradient-orange">
                <div class="stat-icon">⚠️</div>
                <div class="stat-info">
                    <span class="stat-value">${stats.error_count || 0}</span>
                    <span class="stat-label">Hatalı</span>
                </div>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2>📈 Response Süresi Trendi</h2>
            </div>
            <div class="card-body chart-body">
                <canvas id="history-chart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <div class="card-header">
                <h2>📜 Analiz Geçmişi</h2>
            </div>
            <div class="card-body">
                <div class="table-container">
                    <table class="data-table">
                        <thead>
                            <tr>
                                <th>Tarih</th>
                                <th>Response Süresi</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                            ${history.slice(0, 20).map(h => `
                                <tr>
                                    <td>${formatDate(h.analyzed_at)}</td>
                                    <td><span class="response-time ${getResponseTimeClass(h.response_time_ms)}">${h.response_time_ms.toFixed(0)} ms</span></td>
                                    <td><span class="status-badge-code status-${getStatusClass(h.status_code)}">${h.status_code}</span></td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        
        <button class="primary-btn" onclick="reanalyzeURL('${endpoint.url}')">
            🔄 Yeniden Analiz Et
        </button>
    `;

    // Render history chart
    renderHistoryChart(chartData);
}

function renderHistoryChart(chartData) {
    const ctx = document.getElementById('history-chart');
    if (!ctx) return;

    // Destroy existing chart
    if (historyChart) {
        historyChart.destroy();
    }

    const labels = chartData.map(d => {
        const date = new Date(d.timestamp);
        return date.toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' });
    });
    const values = chartData.map(d => d.response_time_ms);

    historyChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: labels,
            datasets: [{
                label: 'Response Süresi (ms)',
                data: values,
                borderColor: 'rgba(99, 102, 241, 1)',
                backgroundColor: 'rgba(99, 102, 241, 0.1)',
                fill: true,
                tension: 0.4,
                pointRadius: 4,
                pointBackgroundColor: 'rgba(99, 102, 241, 1)'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(255, 255, 255, 0.1)'
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                },
                x: {
                    grid: {
                        display: false
                    },
                    ticks: {
                        color: '#94a3b8'
                    }
                }
            }
        }
    });
}

function reanalyzeURL(url) {
    document.getElementById('url-input').value = url;
    switchSection('analyzer');
    analyzeURL();
}

// ============================================
// Utility Functions
// ============================================
function getResponseTimeClass(ms) {
    if (ms < 300) return 'fast';
    if (ms < 1000) return 'medium';
    return 'slow';
}

function getStatusClass(code) {
    if (code >= 200 && code < 300) return '2xx';
    if (code >= 300 && code < 400) return '3xx';
    if (code >= 400 && code < 500) return '4xx';
    return '5xx';
}

function getSeverityText(severity) {
    const texts = {
        low: 'Düşük',
        medium: 'Orta',
        high: 'Yüksek',
        critical: 'Kritik'
    };
    return texts[severity] || severity;
}

function getCategoryTitle(category) {
    const titles = {
        performance: '🚀 Performans',
        security: '🔒 Güvenlik',
        other: '💡 Diğer'
    };
    return titles[category] || category;
}

function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
}

function truncateURL(url) {
    if (!url) return 'N/A';
    if (url.length <= 50) return url;
    return url.substring(0, 47) + '...';
}

function formatDate(dateStr) {
    if (!dateStr) return 'N/A';
    const date = new Date(dateStr);
    return date.toLocaleDateString('tr-TR', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ============================================
// Toast Notifications
// ============================================
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;

    const icons = {
        success: '✅',
        error: '❌',
        info: 'ℹ️'
    };

    toast.innerHTML = `
        <span>${icons[type]}</span>
        <span class="toast-message">${message}</span>
    `;

    container.appendChild(toast);

    // Remove after 3 seconds
    setTimeout(() => {
        toast.style.animation = 'slideIn 0.3s ease reverse';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// ============================================
// PDF Download
// ============================================
async function downloadPDF() {
    const urlInput = document.getElementById('url-input');
    const url = urlInput.value.trim();

    if (!url) {
        showToast('Lütfen önce bir URL analiz edin', 'error');
        return;
    }

    const downloadBtn = document.getElementById('download-pdf-btn');
    downloadBtn.disabled = true;
    downloadBtn.innerHTML = '<span class="btn-icon">⏳</span><span class="btn-text">PDF Oluşturuluyor...</span>';

    try {
        const response = await fetch(`${API_BASE}/analyze/pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ url: url })
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'PDF oluşturulamadı');
        }

        // PDF blob'u al
        const blob = await response.blob();

        // İndirme linki oluştur
        const downloadUrl = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = downloadUrl;
        a.download = `api_report_${url.replace(/[^a-zA-Z0-9]/g, '_')}.pdf`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(downloadUrl);

        showToast('PDF rapor indirildi!', 'success');

    } catch (error) {
        console.error('PDF indirme hatası:', error);
        showToast(error.message || 'PDF oluşturulurken hata oluştu', 'error');
    } finally {
        downloadBtn.disabled = false;
        downloadBtn.innerHTML = '<span class="btn-icon">📄</span><span class="btn-text">PDF Rapor İndir</span>';
    }
}
