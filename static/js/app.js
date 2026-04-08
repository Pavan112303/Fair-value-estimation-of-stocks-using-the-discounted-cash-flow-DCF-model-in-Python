// DCF Valuation Tool - Main JavaScript Application

class DCFApp {
    constructor() {
        this.currentAnalysis = null;
        this.charts = {};
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadPopularStocks();
        this.setupFormValidation();
        this.setupRealTimeSearch();
        this.initializeCharts();
        this.setupWhatIfDashboard();
    }

    setupEventListeners() {
        // Form submission
        document.getElementById('analysisForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.analyzeStock();
        });

        // Market selection change
        document.getElementById('market').addEventListener('change', (e) => {
            this.onMarketChange(e.target.value);
        });

        // Popular stocks selection
        document.getElementById('popularStocks').addEventListener('change', (e) => {
            if (e.target.value) {
                document.getElementById('ticker').value = e.target.value;
                // Auto-fill ticker field but don't search automatically
                // Let user click Analyze button
            }
        });

        // Clear form
        document.getElementById('clearForm').addEventListener('click', () => {
            this.clearForm();
        });

        // Reset growth rates
        document.getElementById('resetGrowthRates').addEventListener('click', () => {
            this.resetGrowthRates();
        });

        // Sensitivity analysis
        document.getElementById('runSensitivity').addEventListener('click', () => {
            this.runSensitivityAnalysis();
        });

        // Premium Feature Event Listeners
        document.getElementById('runMonteCarloBtn')?.addEventListener('click', () => this.runMonteCarlo());
        document.getElementById('runRiskMetricsBtn')?.addEventListener('click', () => this.runRiskMetrics());
        document.getElementById('runDDMBtn')?.addEventListener('click', () => this.runDDM());
        document.getElementById('runPeerComparisonBtn')?.addEventListener('click', () => this.runPeerComparison());
        document.getElementById('loadHistoryBtn')?.addEventListener('click', () => this.loadValuationHistory());
        document.getElementById('getAIInsightsBtn')?.addEventListener('click', () => this.getAIInsights());
        document.getElementById('convertCurrencyBtn')?.addEventListener('click', () => this.convertCurrency());
        document.getElementById('addWatchlistBtn')?.addEventListener('click', () => this.addToWatchlist());
        document.getElementById('viewWatchlistBtn')?.addEventListener('click', () => this.loadWatchlist());
        document.getElementById('exportPDFBtn')?.addEventListener('click', () => this.exportPDF());

        // Smooth scrolling
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                e.preventDefault();
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    }

    async loadPopularStocks(market = 'US') {
        try {
            const response = await fetch(`/popular_stocks?market=${market}`);
            const stocks = await response.json();
            
            const select = document.getElementById('popularStocks');
            // Clear existing options except the first one
            select.innerHTML = '<option value="">Choose a popular stock...</option>';
            
            stocks.forEach(stock => {
                const option = document.createElement('option');
                option.value = stock.ticker;
                option.textContent = `${stock.ticker} - ${stock.name}`;
                select.appendChild(option);
            });
        } catch (error) {
            console.error('Error loading popular stocks:', error);
        }
    }

    onMarketChange(market) {
        // Update placeholder and help text based on market
        const tickerInput = document.getElementById('ticker');
        const tickerHelp = document.getElementById('tickerHelp');
        const popularStocksHelp = document.getElementById('popularStocksHelp');
        
        if (market === 'IN') {
            tickerInput.placeholder = 'Enter ticker with .NS suffix (e.g., RELIANCE.NS, TCS.NS, INFY.NS...)';
            tickerHelp.innerHTML = '<i class="fas fa-flag-india me-1"></i>Enter Indian stock ticker with .NS (NSE) or .BO (BSE) suffix';
            popularStocksHelp.innerHTML = '<i class="fas fa-info-circle me-1"></i>Indian stocks: Tech (TCS, INFY, WIPRO), Banking (HDFCBANK, ICICIBANK, SBIN), Energy (RELIANCE), FMCG (HINDUNILVR, ITC)';
        } else {
            tickerInput.placeholder = 'Enter ticker (e.g., AAPL, MSFT, GOOGL, TSLA...)';
            tickerHelp.innerHTML = '<i class="fas fa-flag-usa me-1"></i>Enter any valid US stock ticker symbol and click Analyze';
            popularStocksHelp.innerHTML = '<i class="fas fa-info-circle me-1"></i>Works with US stocks: Tech (AAPL, MSFT, GOOGL), Auto (TSLA, F), Retail (AMZN, WMT), Finance (JPM, BAC), Healthcare (JNJ, PFE)';
        }
        
        // Clear current ticker
        tickerInput.value = '';
        
        // Load popular stocks for the selected market
        this.loadPopularStocks(market);
    }

    setupFormValidation() {
        const form = document.getElementById('analysisForm');
        const inputs = form.querySelectorAll('input[required], select[required]');
        
        inputs.forEach(input => {
            input.addEventListener('blur', () => {
                this.validateInput(input);
            });
        });
    }

    validateInput(input) {
        const value = input.value.trim();
        const isValid = value !== '';
        
        if (isValid) {
            input.classList.remove('is-invalid');
            input.classList.add('is-valid');
        } else {
            input.classList.remove('is-valid');
            input.classList.add('is-invalid');
        }
        
        return isValid;
    }


    // Setup ticker input behavior
    setupRealTimeSearch() {
        const tickerInput = document.getElementById('ticker');
        
        // Convert to uppercase as user types (except for the dot and suffix)
        tickerInput.addEventListener('input', (e) => {
            const cursorPos = e.target.selectionStart;
            const oldValue = e.target.value;
            e.target.value = e.target.value.toUpperCase();
            // Restore cursor position
            e.target.setSelectionRange(cursorPos, cursorPos);
        });
        
        // Submit form on Enter key
        tickerInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.analyzeStock();
            }
        });
    }


    async analyzeStock() {
        const formData = this.getFormData();
        if (!this.validateForm(formData)) return;

        try {
            this.showLoading(true);
            
            // Clear any previous error messages
            const errorAlert = document.getElementById('errorAlert');
            if (errorAlert) {
                errorAlert.style.display = 'none';
            }
            
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(formData)
            });

            // read text first to handle non-JSON responses gracefully
            const text = await response.text();
            let result = null;
            try {
                result = text ? JSON.parse(text) : {};
            } catch (e) {
                this.showError('Server error: ' + (text || response.statusText));
                return;
            }

            if (result.error) {
                if (Array.isArray(result.suggestions) && result.suggestions.length > 0) {
                    const suggestionItems = result.suggestions
                        .map(item => {
                            const name = item.name ? ` - ${item.name}` : '';
                            const exchange = item.exchange ? ` (${item.exchange})` : '';
                            return `<li><strong>${item.symbol}</strong>${name}${exchange}</li>`;
                        })
                        .join('');
                    this.showError(`${result.error}<ul class="mb-0 mt-2">${suggestionItems}</ul>`);
                } else {
                    this.showError(result.error);
                }
                return;
            }

            console.log('Analysis result:', result); // Debug log
            this.currentAnalysis = result;
            this.displayResults(result);
            this.scrollToResults();
        } catch (error) {
            this.showError('Error analyzing stock. Please check the ticker symbol and try again.');
            console.error('Error:', error);
        } finally {
            this.showLoading(false);
        }
    }

    getFormData() {
        const ticker = document.getElementById('ticker').value.trim().toUpperCase();
        const growthRates = Array.from(document.querySelectorAll('#growthRatesContainer input'))
            .map(input => parseFloat(input.value) || 0);
        const taxRate = parseFloat(document.getElementById('taxRate').value) || 0.25;
        const years = parseInt(document.getElementById('years').value) || 5;
        const riskFreeRate = parseFloat(document.getElementById('riskFreeRate').value) || 0.04;
        const market = document.getElementById('market')?.value || 'US';

        return {
            ticker,
            growth_rates: growthRates,
            tax_rate: taxRate,
            years,
            risk_free_rate: riskFreeRate
            ,market
        };
    }

    validateForm(data) {
        const market = document.getElementById('market').value;
        
        if (!data.ticker) {
            if (market === 'IN') {
                this.showError('Please enter an Indian stock ticker with .NS or .BO suffix (e.g., RELIANCE.NS, TCS.NS, INFY.NS)');
            } else {
                this.showError('Please enter a stock ticker symbol (e.g., AAPL, MSFT, GOOGL, TSLA)');
            }
            return false;
        }

        // Validate ticker format
        if (data.ticker.length < 1 || data.ticker.length > 20) {
            this.showError('Invalid ticker symbol. Please check the format and try again.');
            return false;
        }

        // Check for invalid characters (allow company names)
        if (!/^[A-Z0-9 .&-]+$/.test(data.ticker)) {
            this.showError('Invalid input. Use letters, numbers, spaces, dots, and hyphens (e.g., AAPL, RELIANCE.NS, APPLE INC)');
            return false;
        }

        if (data.growth_rates.some(rate => isNaN(rate) || rate < 0 || rate > 1)) {
            this.showError('Please enter valid growth rates between 0 and 1 (e.g., 0.08 for 8%)');
            return false;
        }

        return true;
    }

    displayResults(result) {
        console.log('Displaying results:', result); // Debug log
        
        // Show the results section
        const resultsSection = document.getElementById('resultsSection');
        if (resultsSection) {
            resultsSection.style.display = 'block';
        }
        
        // Update the results header with stock name
        const resultsHeader = resultsSection.querySelector('h2');
        if (resultsHeader && result.stock_name) {
            resultsHeader.innerHTML = `
                <i class="fas fa-chart-bar me-2"></i>
                Analysis Results: ${result.ticker} - ${result.stock_name}
            `;
        }
        
        this.displayKeyMetrics(result);
        this.displayValuationDetails(result);
        this.displayRecommendation(result);
        this.createCharts(result);
        this.scrollToResults();
    }

    getCurrencySymbol() {
        // Use currency from backend if available, otherwise determine from ticker
        if (this.currentAnalysis && this.currentAnalysis.currency) {
            const currencyMap = {
                'INR': '₹',
                'USD': '$',
                'GBP': '£',
                'EUR': '€',
                'CAD': 'C$',
                'HKD': 'HK$'
            };
            return currencyMap[this.currentAnalysis.currency] || '$';
        }
        
        // Fallback: determine from ticker/market
        try {
            const market = document.getElementById('market')?.value || '';
            const ticker = document.getElementById('ticker')?.value || '';
            if (market === 'IN' || ticker.endsWith('.NS') || ticker.endsWith('.BO')) {
                return '₹';
            }
        } catch (e) {
            // fallback
        }
        return '$';
    }

    displayKeyMetrics(result) {
        const container = document.getElementById('keyMetricsCards');
        const currentPrice = Number(result.current_price) || 0;
        const fairValue = Number(result.fair_value_per_share) || 0;
        const upside = Number(result.upside_percentage) || 0;
        const wacc = Number(result.wacc);
        const enterprise = Number(result.enterprise_value) || 0;
        const currency = this.getCurrencySymbol();

        const currentPriceText = isFinite(currentPrice) ? `${currency}${currentPrice.toFixed(2)}` : 'N/A';
        const fairValueText = isFinite(fairValue) ? `${currency}${fairValue.toFixed(2)}` : 'N/A';
        const waccText = isFinite(wacc) ? `${(wacc * 100).toFixed(1)}%` : 'N/A';
        const enterpriseText = isFinite(enterprise) ? `${currency}${this.formatNumber(enterprise)}` : 'N/A';

        container.innerHTML = `
            <div class="col-lg-3 col-md-6 mb-4">
                <div class="card metric-card">
                    <div class="metric-value">${currentPriceText}</div>
                    <div class="metric-label">Current Price</div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-4">
                <div class="card metric-card">
                    <div class="metric-value">${fairValueText}</div>
                    <div class="metric-label">Fair Value</div>
                    <div class="metric-change ${upside >= 0 ? 'positive' : 'negative'}">
                        ${upside >= 0 ? '+' : ''}${isFinite(upside) ? upside.toFixed(1) : 'N/A'}%
                    </div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-4">
                <div class="card metric-card">
                    <div class="metric-value">${waccText}</div>
                    <div class="metric-label">WACC</div>
                </div>
            </div>
            <div class="col-lg-3 col-md-6 mb-4">
                <div class="card metric-card">
                    <div class="metric-value">${enterpriseText}</div>
                    <div class="metric-label">Enterprise Value</div>
                </div>
            </div>
        `;
    }

    displayValuationDetails(result) {
        const container = document.getElementById('valuationDetails');
        const currency = this.getCurrencySymbol();
        const pv_projected = Number(result.pv_projected_fcf) || 0;
        const pv_terminal = Number(result.pv_terminal_value) || 0;
        const enterprise = Number(result.enterprise_value) || 0;
        const net_debt = Number(result.net_debt) || 0;
        const equity = Number(result.equity_value) || 0;
        const shares = Number(result.shares_outstanding) || 0;
        const fcf_yield = Number(result.fcf_yield) || 0;
        const final_year_fcf = Number(result.final_year_fcf) || 0;

        container.innerHTML = `
            <div class="row">
                <div class="col-md-6">
                    <h6>Valuation Breakdown</h6>
                    <table class="table table-striped">
                        <tbody>
                            <tr>
                                <td>Projected FCF PV</td>
                                <td>${currency}${this.formatNumber(pv_projected)}</td>
                            </tr>
                            <tr>
                                <td>Terminal Value PV</td>
                                <td>${currency}${this.formatNumber(pv_terminal)}</td>
                            </tr>
                            <tr>
                                <td>Enterprise Value</td>
                                <td>${currency}${this.formatNumber(enterprise)}</td>
                            </tr>
                            <tr>
                                <td>Net Debt</td>
                                <td>${currency}${this.formatNumber(net_debt)}</td>
                            </tr>
                            <tr>
                                <td>Equity Value</td>
                                <td>${currency}${this.formatNumber(equity)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="col-md-6">
                    <h6>Key Metrics</h6>
                    <table class="table table-striped">
                        <tbody>
                            <tr>
                                <td>Shares Outstanding</td>
                                <td>${this.formatNumber(shares)}</td>
                            </tr>
                            <tr>
                                <td>FCF Yield</td>
                                <td>${(fcf_yield * 100).toFixed(2)}%</td>
                            </tr>
                            <tr>
                                <td>Terminal Growth</td>
                                <td>2.5%</td>
                            </tr>
                            <tr>
                                <td>Final Year FCF</td>
                                <td>${currency}${this.formatNumber(final_year_fcf)}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
    }

    displayRecommendation(result) {
        const container = document.getElementById('recommendationCard');
        const recommendation = result.recommendation || 'HOLD';
        const upside = result.upside_percentage || 0;
        const colorClass = result.recommendation_color || 'warning';

        container.innerHTML = `
            <div class="recommendation-card">
                <div class="recommendation-badge ${colorClass.toLowerCase().replace(' ', '-')}">
                    ${recommendation}
                </div>
                <h5>${upside >= 0 ? 'Upside' : 'Downside'}: ${Math.abs(upside).toFixed(1)}%</h5>
                <p class="mb-0">
                    ${this.getRecommendationText(recommendation, upside)}
                </p>
            </div>
        `;
    }

    getRecommendationText(recommendation, upside) {
        const recommendations = {
            'STRONG BUY': 'Significant upside potential. Strong buy opportunity.',
            'BUY': 'Good upside potential. Consider buying.',
            'HOLD': 'Fairly valued. Hold current position.',
            'SELL': 'Overvalued. Consider selling.',
            'STRONG SELL': 'Significantly overvalued. Strong sell recommendation.'
        };
        return recommendations[recommendation] || 'No recommendation available.';
    }

    createCharts(result) {
        this.createFCFChart(result);
        this.createValueChart(result);
    }

    createFCFChart(result) {
        const canvas = document.getElementById('fcfChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (this.charts.fcf) {
            this.charts.fcf.destroy();
        }

        const projectedFCF = result.projected_fcf || [];
        if (projectedFCF.length === 0) return;
        
        const years = projectedFCF.map(item => `Year ${item.Year}`);
        const values = projectedFCF.map(item => item.Free_Cash_Flow / 1000000); // Convert to millions

        this.charts.fcf = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: years,
                datasets: [{
                    label: 'Free Cash Flow (Millions)',
                    data: values,
                    backgroundColor: 'rgba(52, 152, 219, 0.8)',
                    borderColor: 'rgba(52, 152, 219, 1)',
                    borderWidth: 2,
                    borderRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        display: false
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                const symbol = (window.dcfApp && window.dcfApp.getCurrencySymbol()) || '$';
                                return symbol + value.toFixed(1) + 'M';
                            }
                        }
                    }
                }
            }
        });
    }

    createValueChart(result) {
        const canvas = document.getElementById('valueChart');
        if (!canvas) return;
        
        const ctx = canvas.getContext('2d');
        
        if (this.charts.value) {
            this.charts.value.destroy();
        }

        const pvProjected = result.pv_projected_fcf / 1000000; // Convert to millions
        const pvTerminal = result.pv_terminal_value / 1000000;

        this.charts.value = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Projected FCF', 'Terminal Value'],
                datasets: [{
                    data: [pvProjected, pvTerminal],
                    backgroundColor: [
                        'rgba(52, 152, 219, 0.8)',
                        'rgba(46, 204, 113, 0.8)'
                    ],
                    borderColor: [
                        'rgba(52, 152, 219, 1)',
                        'rgba(46, 204, 113, 1)'
                    ],
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    title: {
                        display: false
                    },
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const symbol = (window.dcfApp && window.dcfApp.getCurrencySymbol()) || '$';
                                return context.label + ': ' + symbol + context.parsed.toFixed(1) + 'M';
                            }
                        }
                    }
                }
            }
        });
    }

    async runSensitivityAnalysis() {
        if (!this.currentAnalysis) {
            this.showError('Please run an analysis first');
            return;
        }

        try {
            this.showLoading(true);
            const response = await fetch('/sensitivity', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    current_fcf: this.currentAnalysis.final_year_fcf,
                    growth_rates: this.currentAnalysis.projected_fcf.map(item => item.Growth_Rate),
                    beta: this.currentAnalysis.stock_info?.beta || 1.0,
                    debt_to_equity: this.currentAnalysis.stock_info?.debt_to_equity || 0,
                    tax_rate: 0.25,
                    shares_outstanding: this.currentAnalysis.shares_outstanding,
                    net_debt: this.currentAnalysis.net_debt,
                    market: document.getElementById('market')?.value || 'US'
                })
            });

            const result = await response.json();
            
            if (result.error) {
                this.showError(result.error);
                return;
            }

            this.displaySensitivityResults(result.sensitivity_data);
        } catch (error) {
            this.showError('Error running sensitivity analysis');
            console.error('Error:', error);
        } finally {
            this.showLoading(false);
        }
    }

    displaySensitivityResults(data) {
        const container = document.getElementById('sensitivityResults');
        
        // Create heatmap table
        const waccValues = [...new Set(data.map(item => item.WACC))].sort();
        const growthValues = [...new Set(data.map(item => item.Growth_Rate))].sort();
        const currency = this.getCurrencySymbol();
        
        let html = '<h6>Sensitivity Analysis Results</h6>';
        html += '<div class="table-responsive"><table class="table table-bordered">';
        
        // Header row
        html += '<thead><tr><th>Growth Rate / WACC</th>';
        waccValues.forEach(wacc => {
            html += `<th>${(wacc * 100).toFixed(1)}%</th>`;
        });
        html += '</tr></thead><tbody>';
        
        // Data rows
        growthValues.forEach(growth => {
            html += `<tr><th>${(growth * 100).toFixed(1)}%</th>`;
            waccValues.forEach(wacc => {
                const item = data.find(d => d.WACC === wacc && d.Growth_Rate === growth);
                const value = item ? item.Fair_Value.toFixed(2) : 'N/A';
                html += `<td>${currency}${value}</td>`;
            });
            html += '</tr>';
        });
        
        html += '</tbody></table></div>';
        container.innerHTML = html;
    }

    async runWhatIfAnalysis(paramName, paramValue) {
        /**
         * Run what-if analysis with modified parameters
         * Updates valuation in real-time as user adjusts sliders
         */
        if (!this.currentAnalysis) {
            return;
        }

        try {
            // Clone current analysis and modify parameter
            const modifiedData = this.getFormData();
            
            // Update the specific parameter
            switch(paramName) {
                case 'fcf':
                    // FCF adjustment - scale all FCF values
                    this.currentAnalysis.final_year_fcf *= (paramValue / 100);
                    break;
                case 'growth':
                    // Adjust growth rates
                    modifiedData.growth_rates = modifiedData.growth_rates.map(g => g * (paramValue / 100));
                    break;
                case 'wacc':
                    // WACC adjustment via beta or cost of equity
                    this.currentAnalysis.stock_info.beta *= (paramValue / 100);
                    break;
                case 'tax_rate':
                    modifiedData.tax_rate = paramValue / 100;
                    break;
            }

            // Re-run analysis with modified parameters
            const response = await fetch('/analyze', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(modifiedData)
            });

            const text = await response.text();
            let result = null;
            try {
                result = text ? JSON.parse(text) : {};
            } catch (e) {
                console.error('Parse error:', e);
                return;
            }

            if (result.error) {
                console.error('What-if analysis error:', result.error);
                return;
            }

            // Update metrics in real-time without full page refresh
            this.updateWhatIfMetrics(result);
        } catch (error) {
            console.error('What-if analysis error:', error);
        }
    }

    updateWhatIfMetrics(result) {
        /**
         * Update metrics display without full re-render
         * Used for real-time what-if dashboard
         */
        const currency = this.getCurrencySymbol();
        const fairValue = Number(result.fair_value_per_share) || 0;
        const currentPrice = Number(result.current_price) || 0;
        const upside = Number(result.upside_percentage) || 0;

        // Update fair value display
        const fairValueEl = document.getElementById('whatIfFairValue');
        if (fairValueEl) {
            fairValueEl.textContent = isFinite(fairValue) ? 
                `${currency}${fairValue.toFixed(2)}` : 'N/A';
        }

        // Update upside percentage
        const upsideEl = document.getElementById('whatIfUpside');
        if (upsideEl) {
            upsideEl.textContent = isFinite(upside) ? 
                `${upside >= 0 ? '+' : ''}${upside.toFixed(1)}%` : 'N/A';
            upsideEl.className = upside >= 0 ? 'text-success fw-bold' : 'text-danger fw-bold';
        }

        // Update recommendation
        const recommendationEl = document.getElementById('whatIfRecommendation');
        if (recommendationEl) {
            const recommendation = result.recommendation || 'HOLD';
            recommendationEl.textContent = recommendation;
            recommendationEl.className = `badge bg-${result.recommendation_color || 'secondary'}`;
        }

        // Update WACC display
        const waccEl = document.getElementById('whatIfWacc');
        if (waccEl) {
            const wacc = Number(result.wacc);
            waccEl.textContent = isFinite(wacc) ? `${(wacc * 100).toFixed(1)}%` : 'N/A';
        }
    }

    setupWhatIfDashboard() {
        /**
         * Initialize what-if analysis sliders and real-time updates
         */
        const sliders = document.querySelectorAll('.what-if-slider');
        
        sliders.forEach(slider => {
            slider.addEventListener('input', (e) => {
                const param = e.target.dataset.param;
                const value = parseFloat(e.target.value);
                
                // Update slider value display
                const displayEl = document.getElementById(`${param}Display`);
                if (displayEl) {
                    displayEl.textContent = value.toFixed(1);
                }
                
                // Run what-if analysis
                this.runWhatIfAnalysis(param, value);
            });
        });
    }

    showResultsSection() {
        const resultsSection = document.getElementById('resultsSection');
        if (resultsSection) {
            resultsSection.style.display = 'block';
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        }
    }

    showLoading(show) {
        const spinner = document.getElementById('loadingSpinner');
        const analyzeBtn = document.getElementById('analyzeBtn');
        
        if (show) {
            spinner.style.display = 'block';
            analyzeBtn.disabled = true;
            analyzeBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Analyzing...';
        } else {
            spinner.style.display = 'none';
            analyzeBtn.disabled = false;
            analyzeBtn.innerHTML = '<i class="fas fa-calculator me-2"></i>Analyze Stock';
        }
    }

    showError(message) {
        // Scroll to top so user sees the error
        window.scrollTo({ top: 0, behavior: 'smooth' });
        
        // Create or update error alert
        let alertDiv = document.getElementById('errorAlert');
        if (!alertDiv) {
            alertDiv = document.createElement('div');
            alertDiv.id = 'errorAlert';
            alertDiv.className = 'alert alert-danger alert-dismissible fade show';
            alertDiv.innerHTML = `
                <i class="fas fa-exclamation-triangle me-2"></i>
                <span id="errorMessage"></span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            `;
            // Insert before the row containing the form
            const analysisSection = document.getElementById('analysis-section');
            const firstRow = analysisSection.querySelector('.row');
            if (firstRow) {
                analysisSection.insertBefore(alertDiv, firstRow);
            }
        }
        
        // Make error message more user-friendly
        const market = document.getElementById('market')?.value || 'US';
        let friendlyMessage = message;
        
        if (message.includes('No FCF data available')) {
            if (market === 'IN') {
                friendlyMessage = `<strong>Unable to get financial data for this stock.</strong> This might be because:
                <ul class="mb-0 mt-2">
                    <li>The company doesn't have sufficient financial data available</li>
                    <li>The ticker symbol might be incorrect - verify the .NS or .BO suffix</li>
                    <li>Try well-known Indian stocks: RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS</li>
                    <li>Some smaller companies may not have complete financial data</li>
                </ul>`;
            } else {
                friendlyMessage = `<strong>Unable to get financial data for this stock.</strong> This might be because:
                <ul class="mb-0 mt-2">
                    <li>The company doesn't have sufficient financial data available</li>
                    <li>The ticker symbol might be incorrect</li>
                    <li>Try well-known stocks like: AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA</li>
                </ul>`;
            }
        } else if (message.includes('Stock not found')) {
            if (market === 'IN') {
                friendlyMessage = `<strong>Stock not found.</strong> Please check:
                <ul class="mb-0 mt-2">
                    <li>Indian stocks must include .NS (NSE) or .BO (BSE) suffix</li>
                    <li>Example: RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS</li>
                    <li>Verify the company is listed on NSE or BSE</li>
                    <li>Try popular stocks from the dropdown menu</li>
                </ul>`;
            } else {
                friendlyMessage = `<strong>Stock not found.</strong> Please check:
                <ul class="mb-0 mt-2">
                    <li>Verify the ticker symbol is correct (e.g., AAPL for Apple)</li>
                    <li>Try popular stocks: AAPL, MSFT, GOOGL, AMZN, TSLA, META, NVDA, JPM</li>
                    <li>Note: Some international stocks may not be available</li>
                </ul>`;
            }
        } else if (message.includes('Invalid DCF calculation')) {
            friendlyMessage = `<strong>DCF calculation failed.</strong> This might be because:
            <ul class="mb-0 mt-2">
                <li>The company has negative or inconsistent cash flows</li>
                <li>Insufficient financial data for proper analysis</li>
                <li>Try a different stock with more stable financials</li>
            </ul>`;
        } else if (message.includes('Invalid ticker symbol')) {
            if (market === 'IN') {
                friendlyMessage = `<strong>Invalid ticker format.</strong> Please note:
                <ul class="mb-0 mt-2">
                    <li>Indian stocks require .NS (NSE) or .BO (BSE) suffix</li>
                    <li>Correct format: RELIANCE.NS, TCS.NS, HDFCBANK.NS</li>
                    <li>Incorrect: RELIANCE, TCS, HDFCBANK (missing suffix)</li>
                </ul>`;
            } else {
                friendlyMessage = message;
            }
        }
        
        document.getElementById('errorMessage').innerHTML = friendlyMessage;
        alertDiv.style.display = 'block';
        
        // Auto-hide after 10 seconds
        setTimeout(() => {
            if (alertDiv) {
                const bsAlert = new bootstrap.Alert(alertDiv);
                bsAlert.close();
            }
        }, 10000);
    }

    clearForm() {
        document.getElementById('analysisForm').reset();
        document.getElementById('resultsSection').style.display = 'none';
        this.currentAnalysis = null;
        
        // Clear any error messages
        const errorAlert = document.getElementById('errorAlert');
        if (errorAlert) {
            errorAlert.style.display = 'none';
        }
        
        // Clear any existing charts
        Object.values(this.charts).forEach(chart => {
            if (chart) chart.destroy();
        });
        this.charts = {};
        
        // Reset growth rates to default
        this.resetGrowthRates();
        
        // Scroll to top
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    resetGrowthRates() {
        const inputs = document.querySelectorAll('#growthRatesContainer input');
        const defaultRates = [0.08, 0.07, 0.06, 0.05, 0.04];
        
        inputs.forEach((input, index) => {
            if (defaultRates[index] !== undefined) {
                input.value = defaultRates[index];
            }
        });
    }

    scrollToResults() {
        document.getElementById('resultsSection').scrollIntoView({ behavior: 'smooth' });
    }

    scrollToAnalysis() {
        document.getElementById('analysis-section').scrollIntoView({ behavior: 'smooth' });
    }

    formatNumber(num) {
        if (num >= 1e12) return (num / 1e12).toFixed(1) + 'T';
        if (num >= 1e9) return (num / 1e9).toFixed(1) + 'B';
        if (num >= 1e6) return (num / 1e6).toFixed(1) + 'M';
        if (num >= 1e3) return (num / 1e3).toFixed(1) + 'K';
        return num.toFixed(0);
    }

    initializeCharts() {
        // Charts will be created when analysis results are available
        // No need to initialize empty charts
    }

    // ===== PREMIUM FEATURES =====

    // Feature 1: What-If Analysis
    setupWhatIfDashboard() {
        const sliders = document.querySelectorAll('.what-if-slider');
        sliders.forEach(slider => {
            slider.addEventListener('input', (e) => {
                const param = e.target.getAttribute('data-param');
                const value = e.target.value;
                
                // Update display
                const displayId = param === 'fcf' ? 'fcfDisplay' :
                                  param === 'growth' ? 'growthDisplay' :
                                  param === 'wacc' ? 'waccDisplay' :
                                  param === 'tax' ? 'taxDisplay' : '';
                
                if (displayId) {
                    const display = document.getElementById(displayId);
                    if (param === 'wacc') {
                        display.textContent = `${parseInt(value)} bps`;
                    } else {
                        display.textContent = `${value}%`;
                    }
                }
                
                this.runWhatIfAnalysis(param, parseFloat(value));
            });
        });
    }

    runWhatIfAnalysis(paramName, paramValue) {
        if (!this.currentAnalysis) {
            document.getElementById('whatIfFairValue').textContent = 'Run analysis first';
            return;
        }

        const modifiers = {
            fcf: paramValue / 100,
            growth: paramValue / 100,
            wacc: (paramValue / 10000),
            tax: paramValue / 100
        };

        const symbol = this.getCurrencySymbol();
        const fairValue = parseFloat(this.currentAnalysis.fair_value_per_share);
        const currentPrice = parseFloat(this.currentAnalysis.current_price);
        
        let adjustedFair = fairValue;
        if (paramName === 'fcf') {
            adjustedFair = fairValue * modifiers.fcf;
        } else if (paramName === 'growth') {
            adjustedFair = fairValue * (0.5 + modifiers.growth);
        }

        const upside = ((adjustedFair - currentPrice) / currentPrice * 100).toFixed(2);
        const recommendation = upside > 15 ? 'BUY' : upside < -15 ? 'SELL' : 'HOLD';

        document.getElementById('whatIfFairValue').textContent = `${symbol}${adjustedFair.toFixed(2)}`;
        document.getElementById('whatIfUpside').textContent = `${upside}%`;
        document.getElementById('whatIfRecommendation').textContent = recommendation;
        document.getElementById('whatIfWacc').textContent = `${((this.currentAnalysis.wacc || 0.10) * 100 + paramValue / 100).toFixed(2)}%`;
    }

    // Feature 2: Monte Carlo Simulation
    async runMonteCarlo() {
        if (!this.currentAnalysis) {
            alert('Please run analysis first');
            return;
        }

        const btn = document.getElementById('runMonteCarloBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Running Simulation...';

        try {
            const response = await fetch('/monte_carlo', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_fcf: this.currentAnalysis.current_fcf || 1000000,
                    growth_rates: this.currentAnalysis.growth_rates || [0.08, 0.07, 0.06, 0.05, 0.04],
                    beta: this.currentAnalysis.beta || 1.0,
                    debt_to_equity: this.currentAnalysis.debt_to_equity || 0.5,
                    tax_rate: this.currentAnalysis.tax_rate || 0.25,
                    shares_outstanding: this.currentAnalysis.shares_outstanding || 1000000,
                    net_debt: this.currentAnalysis.net_debt || 0,
                    iterations: 10000
                })
            });

            const data = await response.json();
            this.displayMonteCarloResults(data);
        } catch (error) {
            alert('Error running Monte Carlo: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play me-2"></i>Run Simulation';
        }
    }

    displayMonteCarloResults(data) {
        const symbol = this.getCurrencySymbol();
        const html = `
            <div class="mc-distribution">
                <h6>Valuation Distribution</h6>
                <div class="mc-stat">
                    <span class="mc-stat-label">Mean Fair Value</span>
                    <span class="mc-stat-value">${symbol}${data.mean?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="mc-stat">
                    <span class="mc-stat-label">Median Fair Value</span>
                    <span class="mc-stat-value">${symbol}${data.median?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="mc-stat">
                    <span class="mc-stat-label">Standard Deviation</span>
                    <span class="mc-stat-value">${symbol}${data.std_dev?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="mc-stat">
                    <span class="mc-stat-label">10th Percentile</span>
                    <span class="mc-stat-value">${symbol}${data.percentile_10?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="mc-stat">
                    <span class="mc-stat-label">25th Percentile</span>
                    <span class="mc-stat-value">${symbol}${data.percentile_25?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="mc-stat">
                    <span class="mc-stat-label">75th Percentile</span>
                    <span class="mc-stat-value">${symbol}${data.percentile_75?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="mc-stat">
                    <span class="mc-stat-label">90th Percentile</span>
                    <span class="mc-stat-value">${symbol}${data.percentile_90?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="mc-stat">
                    <span class="mc-stat-label">Minimum Value</span>
                    <span class="mc-stat-value">${symbol}${data.min?.toFixed(2) || 'N/A'}</span>
                </div>
                <div class="mc-stat">
                    <span class="mc-stat-label">Maximum Value</span>
                    <span class="mc-stat-value">${symbol}${data.max?.toFixed(2) || 'N/A'}</span>
                </div>
            </div>
            <div class="alert alert-info">
                <i class="fas fa-info-circle me-2"></i>
                <strong>Interpretation:</strong> The simulation shows that fair value is likely between ${symbol}${data.percentile_10?.toFixed(2)} and ${symbol}${data.percentile_90?.toFixed(2)} with 80% confidence.
            </div>
        `;
        document.getElementById('monteCarloResults').innerHTML = html;
    }

    // Feature 3: Risk Metrics
    async runRiskMetrics() {
        if (!this.currentAnalysis) {
            alert('Please run analysis first');
            return;
        }

        const btn = document.getElementById('runRiskMetricsBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Calculating...';

        try {
            const response = await fetch('/risk_metrics', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_fcf: this.currentAnalysis.current_fcf || 1000000,
                    growth_rates: this.currentAnalysis.growth_rates || [0.08, 0.07],
                    beta: this.currentAnalysis.beta || 1.0,
                    debt_to_equity: this.currentAnalysis.debt_to_equity || 0.5,
                    fair_value_per_share: this.currentAnalysis.fair_value_per_share || 50,
                    wacc: this.currentAnalysis.wacc || 0.10,
                    fcf_yield: (this.currentAnalysis.current_fcf / (this.currentAnalysis.shares_outstanding * this.currentAnalysis.fair_value_per_share)) || 0.05
                })
            });

            const data = await response.json();
            this.displayRiskMetrics(data);
        } catch (error) {
            alert('Error calculating risk metrics: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play me-2"></i>Calculate Risk Score';
        }
    }

    displayRiskMetrics(data) {
        const getRiskColor = (score) => {
            if (score < 30) return '#28a745';
            if (score < 50) return '#ffc107';
            if (score < 70) return '#fd7e14';
            return '#dc3545';
        };

        const getRiskLevel = (score) => {
            if (score < 30) return 'Low Risk';
            if (score < 50) return 'Medium Risk';
            if (score < 70) return 'High Risk';
            return 'Very High Risk';
        };

        const score = data.overall_risk_score || 50;
        const color = getRiskColor(score);

        const html = `
            <div class="risk-score" style="background: linear-gradient(135deg, ${color} 0%, ${color}CC 100%);">
                <div class="score-number">${score.toFixed(1)}</div>
                <div class="score-label">${getRiskLevel(score)}</div>
            </div>

            <div class="risk-component">
                <div class="risk-component-name">Beta Risk (Volatility)</div>
                <div class="risk-component-bar">
                    <div class="risk-component-fill" style="width: ${data.beta_risk || 50}%">
                        ${data.beta_risk || 50}
                    </div>
                </div>
            </div>

            <div class="risk-component">
                <div class="risk-component-name">Leverage Risk (Debt)</div>
                <div class="risk-component-bar">
                    <div class="risk-component-fill" style="width: ${data.leverage_risk || 50}%">
                        ${data.leverage_risk || 50}
                    </div>
                </div>
            </div>

            <div class="risk-component">
                <div class="risk-component-name">WACC Risk (Cost of Capital)</div>
                <div class="risk-component-bar">
                    <div class="risk-component-fill" style="width: ${data.wacc_risk || 50}%">
                        ${data.wacc_risk || 50}
                    </div>
                </div>
            </div>

            <div class="risk-component">
                <div class="risk-component-name">FCF Risk (Cash Flow Yield)</div>
                <div class="risk-component-bar">
                    <div class="risk-component-fill" style="width: ${data.fcf_risk || 50}%">
                        ${data.fcf_risk || 50}
                    </div>
                </div>
            </div>

            <div class="alert alert-info mt-3">
                <i class="fas fa-lightbulb me-2"></i>
                <strong>Risk Assessment:</strong> This score combines multiple risk factors. Lower scores indicate safer investments, higher scores suggest more volatile or risky investments.
            </div>
        `;
        document.getElementById('riskMetricsResults').innerHTML = html;
    }

    // Feature 4: Dividend Discount Model
    async runDDM() {
        const currentDiv = parseFloat(document.getElementById('ddmCurrentDiv').value);
        const growthRate = parseFloat(document.getElementById('ddmGrowthRate').value) / 100;
        const requiredReturn = parseFloat(document.getElementById('ddmRequiredReturn').value) / 100;

        if (!currentDiv || !growthRate || !requiredReturn) {
            alert('Please fill all DDM parameters');
            return;
        }

        const btn = document.getElementById('runDDMBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Calculating...';

        try {
            const response = await fetch('/ddm', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    current_dividend: currentDiv,
                    dividend_growth_rate: growthRate,
                    required_return: requiredReturn,
                    years: 10
                })
            });

            const data = await response.json();
            this.displayDDMResults(data);
        } catch (error) {
            alert('Error calculating DDM: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-calculator me-2"></i>Calculate';
        }
    }

    displayDDMResults(data) {
        const symbol = this.getCurrencySymbol();
        const html = `
            <div class="card mt-3">
                <div class="card-body">
                    <h6 class="mb-3">DDM Valuation Results</h6>
                    <div class="stat-box mb-3">
                        <strong>Fair Value Per Share (DDM)</strong>
                        <p class="h5">${symbol}${data.fair_value_per_share?.toFixed(2) || 'N/A'}</p>
                    </div>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="stat-box">
                                <strong>PV of Dividends</strong>
                                <p class="h5">${symbol}${data.pv_dividends?.toFixed(2) || 'N/A'}</p>
                            </div>
                        </div>
                        <div class="col-md-6">
                            <div class="stat-box">
                                <strong>PV of Terminal Value</strong>
                                <p class="h5">${symbol}${data.pv_terminal_value?.toFixed(2) || 'N/A'}</p>
                            </div>
                        </div>
                    </div>
                    <div class="alert alert-info mt-3">
                        <i class="fas fa-info-circle me-2"></i>
                        <strong>Note:</strong> DDM is best for stable, dividend-paying companies. Compare with DCF for validation.
                    </div>
                </div>
            </div>
        `;
        document.getElementById('ddmResults').innerHTML = html;
    }

    // Feature 5: Peer Comparison
    async runPeerComparison() {
        const ticker = document.getElementById('ticker').value;
        if (!ticker) {
            alert('Please enter a ticker');
            return;
        }

        const btn = document.getElementById('runPeerComparisonBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading peers...';

        try {
            const response = await fetch(`/peer_comparison/${ticker}`, {
                method: 'GET'
            });

            const data = await response.json();
            this.displayPeerComparison(data);
        } catch (error) {
            alert('Error loading peer comparison: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-play me-2"></i>Analyze Peers';
        }
    }

    displayPeerComparison(data) {
        let html = '<div class="peer-table"><table class="table mb-0"><thead><tr><th>Company</th><th>P/E Ratio</th><th>P/B Ratio</th><th>Div Yield</th><th>ROE</th><th>Margin</th></tr></thead><tbody>';

        if (data.peers && data.peers.length > 0) {
            data.peers.forEach(peer => {
                const peRatio = peer.pe_ratio || peer.pe || 0;
                const pbRatio = peer.pb_ratio || peer.pb || 0;
                const divYield = (peer.dividend_yield || 0) * 100;
                const roe = (peer.return_on_equity || peer.roe || 0) * 100;
                const margin = (peer.profit_margin || peer.margin || 0) * 100;
                
                html += `<tr>
                    <td><strong>${peer.ticker}</strong><br><small class="text-muted">${peer.name || ''}</small></td>
                    <td>${peRatio > 0 ? peRatio.toFixed(2) : 'N/A'}</td>
                    <td>${pbRatio > 0 ? pbRatio.toFixed(2) : 'N/A'}</td>
                    <td>${divYield > 0 ? divYield.toFixed(2) + '%' : 'N/A'}</td>
                    <td>${roe > 0 ? roe.toFixed(2) + '%' : 'N/A'}</td>
                    <td>${margin > 0 ? margin.toFixed(2) + '%' : 'N/A'}</td>
                </tr>`;
            });
        } else {
            html += '<tr><td colspan="6" class="text-center text-muted">No peer data available</td></tr>';
        }

        html += '</tbody></table></div>';

        if (data.sector_average) {
            const avgPe = data.sector_average.pe_ratio || data.sector_average.pe || 0;
            const avgPb = data.sector_average.pb_ratio || data.sector_average.pb || 0;
            const avgRoe = (data.sector_average.return_on_equity || data.sector_average.roe || 0) * 100;
            
            html += `<div class="alert alert-info mt-3">
                <h6>Sector Averages (${data.sector || 'Unknown'})</h6>
                <p class="mb-0"><strong>Avg P/E:</strong> ${avgPe > 0 ? avgPe.toFixed(2) : 'N/A'} | 
                           <strong>Avg P/B:</strong> ${avgPb > 0 ? avgPb.toFixed(2) : 'N/A'} | 
                           <strong>Avg ROE:</strong> ${avgRoe > 0 ? avgRoe.toFixed(2) + '%' : 'N/A'}</p>
            </div>`;
        }

        document.getElementById('peerComparisonResults').innerHTML = html;
    }

    // Feature 6: Valuation History
    async loadValuationHistory() {
        const ticker = document.getElementById('ticker').value;
        if (!ticker) {
            alert('Please enter a ticker');
            return;
        }

        const btn = document.getElementById('loadHistoryBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Loading...';

        try {
            const response = await fetch(`/valuation_history/${ticker}`);
            const data = await response.json();
            this.displayValuationHistory(data);
        } catch (error) {
            alert('Error loading history: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-history me-2"></i>Load History';
        }
    }

    displayValuationHistory(data) {
        if (!data.history || data.history.length === 0) {
            document.getElementById('valuationHistoryResults').innerHTML = '<div class="alert alert-info">No history yet. Run more analyses to see trends.</div>';
            return;
        }

        const symbol = this.getCurrencySymbol();
        let html = '<div class="history-timeline">';

        data.history.forEach(item => {
            const date = new Date(item.created_at).toLocaleDateString();
            html += `
                <div class="history-item">
                    <div class="history-date">${date}</div>
                    <div class="history-value">${symbol}${item.fair_value?.toFixed(2)}</div>
                    <div><small class="text-muted">Price: ${symbol}${item.current_price?.toFixed(2)} | Upside: ${item.upside?.toFixed(2)}% | ${item.recommendation}</small></div>
                </div>
            `;
        });

        html += '</div>';
        document.getElementById('valuationHistoryResults').innerHTML = html;
    }

    // Feature 7: AI Insights
    async getAIInsights() {
        if (!this.currentAnalysis) {
            alert('Please run analysis first');
            return;
        }

        const btn = document.getElementById('getAIInsightsBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';

        try {
            const response = await fetch('/ai_insights', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ticker: document.getElementById('ticker').value,
                    stock_name: this.currentAnalysis.stock_name || 'Unknown',
                    fair_value_per_share: this.currentAnalysis.fair_value_per_share,
                    current_price: this.currentAnalysis.current_price,
                    upside_percentage: this.currentAnalysis.upside_percentage,
                    recommendation: this.currentAnalysis.recommendation,
                    pe_ratio: this.currentAnalysis.pe_ratio || 0,
                    return_on_equity: this.currentAnalysis.roe || 0,
                    sector: this.currentAnalysis.sector || 'Unknown'
                })
            });

            const data = await response.json();
            this.displayAIInsights(data);
        } catch (error) {
            alert('Error generating insights: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-wand-magic-sparkles me-2"></i>Generate AI Insights';
        }
    }

    displayAIInsights(data) {
        const html = `
            <div class="ai-insight-box">
                <div class="ai-source-badge">
                    <i class="fas fa-${data.source === 'OpenAI GPT' ? 'brain' : 'cogs'} me-1"></i>
                    ${data.source || 'Rule-Based Analysis'}
                </div>
                <div class="ai-insight-text">
                    ${data.insight || 'Unable to generate insights'}
                </div>
            </div>
        `;
        document.getElementById('aiInsightsResults').innerHTML = html;
    }

    // Feature 8: Currency Converter
    async convertCurrency() {
        const amount = parseFloat(document.getElementById('convertAmount').value);
        const fromCurrency = document.getElementById('fromCurrency').value;
        const toCurrency = document.getElementById('toCurrency').value;

        if (!amount || isNaN(amount)) {
            alert('Please enter a valid amount');
            return;
        }

        const btn = document.getElementById('convertCurrencyBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';

        try {
            const response = await fetch('/convert_currency', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    amount: amount,
                    from_currency: fromCurrency,
                    to_currency: toCurrency
                })
            });

            const data = await response.json();
            const resultDiv = document.getElementById('currencyConversionResult');
            resultDiv.innerHTML = `
                <strong>${amount} ${fromCurrency}</strong> = <strong>${data.converted_amount?.toFixed(2)} ${toCurrency}</strong>
                <br><small class="text-muted">Exchange Rate: 1 ${fromCurrency} = ${data.exchange_rate?.toFixed(4)} ${toCurrency}</small>
            `;
            resultDiv.style.display = 'block';
        } catch (error) {
            alert('Conversion error: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-exchange-alt me-2"></i>Convert';
        }
    }

    // Feature 9: Watchlist
    addToWatchlist() {
        const ticker = document.getElementById('watchlistTicker').value.trim();
        if (!ticker) {
            alert('Please enter a ticker');
            return;
        }

        fetch('/watchlist', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: ticker })
        }).then(() => {
            document.getElementById('watchlistTicker').value = '';
            this.loadWatchlist();
        }).catch(error => alert('Error adding to watchlist: ' + error.message));
    }

    removeFromWatchlist(ticker) {
        fetch('/watchlist', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ticker: ticker })
        }).then(() => {
            this.loadWatchlist();
        }).catch(error => alert('Error removing from watchlist: ' + error.message));
    }

    loadWatchlist() {
        fetch('/watchlist')
            .then(res => res.json())
            .then(data => {
                let html = '<h6>Your Watchlist</h6>';
                if (data.watchlist && data.watchlist.length > 0) {
                    html += '<div>';
                    data.watchlist.forEach(ticker => {
                        html += `<div class="watchlist-item">
                            <span class="watchlist-ticker">${ticker}</span>
                            <span class="watchlist-remove" onclick="window.dcfApp.removeFromWatchlist('${ticker}')">Remove</span>
                        </div>`;
                    });
                    html += '</div>';
                } else {
                    html += '<p class="text-muted">No stocks in watchlist</p>';
                }
                document.getElementById('watchlistResult').innerHTML = html;
            })
            .catch(error => alert('Error loading watchlist: ' + error.message));
    }

    // Feature 10: PDF Export
    exportPDF() {
        const ticker = document.getElementById('ticker').value;
        if (!ticker) {
            alert('Please enter a ticker');
            return;
        }

        const btn = document.getElementById('exportPDFBtn');
        btn.disabled = true;
        btn.innerHTML = '<i class="fas fa-spinner fa-spin me-2"></i>Generating...';

        setTimeout(() => {
            window.location.href = `/export_report/${ticker}`;
            btn.disabled = false;
            btn.innerHTML = '<i class="fas fa-file-pdf me-2"></i>Download PDF Report';
        }, 500);
    }

    getCurrencySymbol() {
        const market = document.getElementById('market')?.value || 'US';
        const ticker = document.getElementById('ticker')?.value || '';
        if (market === 'IN' || ticker.includes('.NS') || ticker.includes('.BO')) {
            return '₹';
        }
        return '$';
    }
}

// Initialize the application when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dcfApp = new DCFApp();
});

// Utility functions
function scrollToAnalysis() {
    if (window.dcfApp) {
        window.dcfApp.scrollToAnalysis();
    }
}
