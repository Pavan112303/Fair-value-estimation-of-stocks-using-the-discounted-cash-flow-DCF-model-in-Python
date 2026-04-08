from flask import Flask, render_template, request, jsonify, session, send_file
import json
import pandas as pd
import numpy as np
from datetime import datetime
import os
import base64
import io
from functools import lru_cache
import requests
import sqlite3
import yfinance as yf
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from openai import OpenAI
import matplotlib
matplotlib.use('Agg')  
import matplotlib.pyplot as plt
import seaborn as sns
from dcf_calculator import DCFCalculator
from data_interface import StockDataInterface

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  


dcf_calc = DCFCalculator()
data_interface = StockDataInterface()


plt.style.use('seaborn-v0_8')
sns.set_palette("husl")

# Initialize database for valuation history
def init_db():
    """Initialize SQLite database for valuation history"""
    conn = sqlite3.connect('valuation_history.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS valuations (
            id INTEGER PRIMARY KEY,
            ticker TEXT,
            fair_value REAL,
            current_price REAL,
            upside REAL,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()

# Initialize database on app startup
init_db()

# FX Rate Caching
FX_FALLBACK_RATES = {
    'USD': 1.0,
    'INR': 83.0,
    'EUR': 0.92,
    'GBP': 0.79,
    'CAD': 1.36,
    'HKD': 7.8,
}


def normalize_currency_code(currency_code):
    return str(currency_code or '').strip().upper()


@lru_cache(maxsize=128)
def get_fx_rate(from_currency, to_currency):
    """Get exchange rate between two currencies (cached)"""
    try:
        from_currency = normalize_currency_code(from_currency)
        to_currency = normalize_currency_code(to_currency)

        if from_currency == to_currency:
            return 1.0

        fallback_from = FX_FALLBACK_RATES.get(from_currency)
        fallback_to = FX_FALLBACK_RATES.get(to_currency)
        if fallback_from and fallback_to:
            return fallback_to / fallback_from

        ticker_symbol = f'{from_currency}{to_currency}=X'
        url = f'https://query1.finance.yahoo.com/v7/finance/quote?symbols={ticker_symbol}&fields=regularMarketPrice'
        response = requests.get(url, timeout=5)
        data = response.json()
        if data['quoteResponse']['result']:
            rate = data['quoteResponse']['result'][0]['regularMarketPrice']
            return rate
    except Exception as e:
        print(f"FX conversion error: {str(e)}")
    fallback_from = FX_FALLBACK_RATES.get(normalize_currency_code(from_currency))
    fallback_to = FX_FALLBACK_RATES.get(normalize_currency_code(to_currency))
    if fallback_from and fallback_to:
        return fallback_to / fallback_from
    return 1.0  # Fallback to 1:1 if error

def save_valuation_snapshot(ticker, fair_value, current_price, upside, recommendation):
    """Save valuation to history database"""
    try:
        conn = sqlite3.connect('valuation_history.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO valuations (ticker, fair_value, current_price, upside, recommendation)
            VALUES (?, ?, ?, ?, ?)
        ''', (ticker, fair_value, current_price, upside, recommendation))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Failed to save valuation snapshot: {str(e)}")

@app.route('/')
def landing():
    """Landing page with DCF explanation"""
    return render_template('landing.html')

@app.route('/convert_currency', methods=['POST'])
def convert_currency():
    """Convert valuation to target currency"""
    try:
        data = request.get_json()
        amount = float(data.get('amount', 0))
        from_curr = normalize_currency_code(data.get('from_currency', 'USD'))
        to_curr = normalize_currency_code(data.get('to_currency', 'INR'))
        
        if from_curr == to_curr:
            return jsonify({
                'original_amount': amount,
                'converted_amount': amount,
                'from_currency': from_curr,
                'to_currency': to_curr,
                'exchange_rate': 1.0
            })
        
        rate = get_fx_rate(from_curr, to_curr)
        converted = amount * rate
        
        return jsonify({
            'original_amount': amount,
            'converted_amount': converted,
            'from_currency': from_curr,
            'to_currency': to_curr,
            'exchange_rate': rate
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze')
def index():
    """Analysis page with DCF analysis form"""
    return render_template('index.html')

@app.route('/valuation_history/<ticker>')
def get_valuation_history(ticker):
    """Get historical valuations for a stock"""
    try:
        conn = sqlite3.connect('valuation_history.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fair_value, current_price, upside, recommendation, created_at
            FROM valuations
            WHERE ticker = ?
            ORDER BY created_at DESC
            LIMIT 50
        ''', (ticker,))
        
        history = [
            {
                'fair_value': row[0],
                'current_price': row[1],
                'upside': row[2],
                'recommendation': row[3],
                'created_at': row[4]
            }
            for row in cursor.fetchall()
        ]
        conn.close()
        
        return jsonify({'history': history})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/analyze', methods=['POST'])
def analyze_stock():
    """Analyze a stock using DCF model"""
    try:
        data = request.get_json()
        
        raw_ticker = data.get('ticker', '')
        market = data.get('market', 'US')
        growth_rates = [float(x) for x in data.get('growth_rates', [])]
        tax_rate = float(data.get('tax_rate', 0.25))
        years = int(data.get('years', 5))

        resolution = data_interface.resolve_ticker(raw_ticker, market)
        if resolution.get('status') == 'suggestion':
            return jsonify({
                'error': resolution.get('message', 'Ticker not found.'),
                'suggestions': resolution.get('suggestions', [])
            }), 400
        if resolution.get('status') != 'match':
            return jsonify({'error': resolution.get('message', 'Ticker not found.')}), 400

        ticker = resolution.get('ticker', '').upper()

        # Detect currency based on ticker suffix
        currency = 'USD'  # Default
        market_region = 'US'  # Default for terminal growth calculation
        if ticker.endswith('.NS') or ticker.endswith('.BO'):
            currency = 'INR'
            market_region = 'IN'
        elif ticker.endswith('.L'):
            currency = 'GBP'
            market_region = 'EU'
        elif ticker.endswith('.HK'):
            currency = 'HKD'
            market_region = 'CN'
        elif ticker.endswith('.TO'):
            currency = 'CAD'
            market_region = 'US'

        stock_info = data_interface.get_stock_info(ticker)
        if not stock_info or not stock_info.get('name'):
            return jsonify({'error': f'Stock not found: {ticker}. Please check the ticker symbol and try again.'}), 400
        
        
        financials = data_interface.get_financial_statements(ticker)
        
        
        fcf_history = data_interface.calculate_free_cash_flow(ticker, years)
        
        if fcf_history.empty:
           
            try:
                cash_flow = financials.get('cash_flow', pd.DataFrame())
                if not cash_flow.empty:
                    
                    latest_fcf = None
                    for i, (date, row) in enumerate(cash_flow.iterrows()):
                        if i >= 1:  
                            break
                        fcf = row.get('Free Cash Flow', 0)
                        if pd.notna(fcf) and fcf != 0:
                            latest_fcf = fcf
                            break
                    
                    if latest_fcf is not None:
                        current_fcf = latest_fcf
                    else:
                        # Estimate from net income using improved formula
                        current_fcf = estimate_fcf_from_net_income(stock_info, ticker)
                        if current_fcf is None:
                            return jsonify({'error': f'No FCF data available for {ticker}. Please try a different ticker or check if the company has sufficient financial data.'}), 400
                else:
                    # Estimate from net income using improved formula
                    current_fcf = estimate_fcf_from_net_income(stock_info, ticker)
                    if current_fcf is None:
                        return jsonify({'error': f'No FCF data available for {ticker}. Please try a different ticker or check if the company has sufficient financial data.'}), 400
            except Exception as e:
                # Estimate from net income using improved formula
                current_fcf = estimate_fcf_from_net_income(stock_info, ticker)
                if current_fcf is None:
                    return jsonify({'error': f'No FCF data available for {ticker}. Please try a different ticker or check if the company has sufficient financial data.'}), 400
        else:
            
            current_fcf = fcf_history.iloc[-1]['Free_Cash_Flow']
        
        
        if current_fcf <= 0:
            return jsonify({'error': f'No valid FCF data available for {ticker}. Please try a different stock with sufficient financial data.'}), 400
        
        
        net_debt = stock_info.get('total_debt', 0) - stock_info.get('cash', 0)
        
        
        shares_outstanding = stock_info.get('shares_outstanding', 1)
        if shares_outstanding <= 0:
            shares_outstanding = 1 
        
        print(f"Calculating DCF for {ticker} with FCF: {current_fcf}")
        print(f"Shares outstanding: {shares_outstanding}, Net debt: {net_debt}")
        
        try:
            valuation = dcf_calc.calculate_fair_value(
                current_fcf=current_fcf,
                growth_rates=growth_rates,
                beta=stock_info.get('beta', 1.0),
                debt_to_equity=stock_info.get('debt_to_equity', 0),
                tax_rate=tax_rate,
                shares_outstanding=shares_outstanding,
                net_debt=net_debt,
                years=len(growth_rates),
                market=market_region,
                current_price=stock_info.get('current_price', 0)
            )
            
            
            fair_value = valuation.get('fair_value_per_share', 0)
            if fair_value <= 0:
                return jsonify({'error': f'Invalid DCF calculation result for {ticker}. The stock may have negative cash flows or invalid financial data.'}), 400
            
            print(f"DCF calculation completed. Fair value: {fair_value}")
        except Exception as e:
            print(f"DCF calculation error: {str(e)}")
            return jsonify({'error': f'DCF calculation failed for {ticker}: {str(e)}'}), 400
        
        # Add valuation details to response
        valuation.update({
            'ticker': ticker,
            'stock_name': stock_info.get('name', ticker),
            'current_price': stock_info.get('current_price', 0),
            'market_cap': stock_info.get('market_cap', 0),
            'fcf_history': fcf_history.to_dict('records'),
            'stock_info': stock_info,
            'currency': currency,  # Add currency to response
            'market_region': market_region,  # Add market region
            # Add input parameters for premium features (Monte Carlo, etc.)
            'current_fcf': current_fcf,
            'growth_rates': growth_rates,
            'beta': stock_info.get('beta', 1.0),
            'debt_to_equity': stock_info.get('debt_to_equity', 0),
            'tax_rate': tax_rate,
            'shares_outstanding': shares_outstanding,
            'net_debt': net_debt
        })
        
        
        current_price = stock_info.get('current_price', 0)
        if current_price > 0:
            upside = ((valuation['fair_value_per_share'] - current_price) / current_price) * 100
            valuation['upside_percentage'] = upside
            
            if upside > 20:
                recommendation = "STRONG BUY"
                recommendation_color = "success"
            elif upside > 10:
                recommendation = "BUY"
                recommendation_color = "success"
            elif upside > -10:
                recommendation = "HOLD"
                recommendation_color = "warning"
            elif upside > -20:
                recommendation = "SELL"
                recommendation_color = "danger"
            else:
                recommendation = "STRONG SELL"
                recommendation_color = "danger"
            
            valuation['recommendation'] = recommendation
            valuation['recommendation_color'] = recommendation_color
        
    
        if 'projected_fcf' in valuation:
            valuation['projected_fcf'] = valuation['projected_fcf'].to_dict('records')
        
        # Save valuation snapshot to history
        current_price = stock_info.get('current_price', 0)
        fair_value = valuation.get('fair_value_per_share', 0)
        upside = valuation.get('upside_percentage', 0)
        recommendation = valuation.get('recommendation', 'HOLD')
        save_valuation_snapshot(ticker, fair_value, current_price, upside, recommendation)
        
        return jsonify(valuation)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/sensitivity', methods=['POST'])
def sensitivity_analysis():
    """Perform sensitivity analysis"""
    try:
        data = request.get_json()
        
        base_params = {
            'current_fcf': float(data.get('current_fcf', 0)),
            'growth_rates': [float(x) for x in data.get('growth_rates', [])],
            'beta': float(data.get('beta', 1.0)),
            'debt_to_equity': float(data.get('debt_to_equity', 0)),
            'tax_rate': float(data.get('tax_rate', 0.25)),
            'shares_outstanding': float(data.get('shares_outstanding', 1)),
            'net_debt': float(data.get('net_debt', 0)),
            'market': data.get('market_region', 'US'),
            'current_price': float(data.get('current_price', 0))
        }
        
        sensitivity_results = dcf_calc.sensitivity_analysis(base_params)
        
        return jsonify({
            'sensitivity_data': sensitivity_results.to_dict('records')
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/monte_carlo', methods=['POST'])
def monte_carlo_analysis():
    """Perform Monte Carlo simulation for valuation uncertainty"""
    try:
        data = request.get_json()
        
        base_params = {
            'current_fcf': float(data.get('current_fcf', 0)),
            'growth_rates': [float(x) for x in data.get('growth_rates', [])],
            'beta': float(data.get('beta', 1.0)),
            'debt_to_equity': float(data.get('debt_to_equity', 0)),
            'tax_rate': float(data.get('tax_rate', 0.25)),
            'shares_outstanding': float(data.get('shares_outstanding', 1)),
            'net_debt': float(data.get('net_debt', 0)),
            'market': data.get('market_region', 'US'),
            'current_price': float(data.get('current_price', 0))
        }
        
        iterations = int(data.get('iterations', 10000))
        mc_results = dcf_calc.monte_carlo_simulation(base_params, iterations=iterations)
        
        return jsonify(mc_results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ddm', methods=['POST'])
def calculate_ddm():
    """Calculate fair value using Dividend Discount Model"""
    try:
        data = request.get_json()
        
        current_dividend = float(data.get('current_dividend', 0))
        dividend_growth_rate = float(data.get('dividend_growth_rate', 0.05))
        required_return = float(data.get('required_return', 0.10))
        years = int(data.get('years', 10))
        
        if current_dividend <= 0:
            return jsonify({'error': 'Current dividend must be greater than 0'}), 400
        
        ddm_results = dcf_calc.calculate_ddm(
            current_dividend=current_dividend,
            dividend_growth_rate=dividend_growth_rate,
            required_return=required_return,
            years=years
        )
        
        return jsonify(ddm_results)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/risk_metrics', methods=['POST'])
def calculate_risk_metrics():
    """Calculate risk metrics and risk score for a stock"""
    try:
        data = request.get_json()
        
        base_params = {
            'current_fcf': float(data.get('current_fcf', 0)),
            'growth_rates': [float(x) for x in data.get('growth_rates', [])],
            'beta': float(data.get('beta', 1.0)),
            'debt_to_equity': float(data.get('debt_to_equity', 0)),
            'tax_rate': float(data.get('tax_rate', 0.25)),
            'shares_outstanding': float(data.get('shares_outstanding', 1)),
            'net_debt': float(data.get('net_debt', 0))
        }
        
        valuation = {
            'fair_value_per_share': float(data.get('fair_value_per_share', 0)),
            'wacc': float(data.get('wacc', 0.1)),
            'fcf_yield': float(data.get('fcf_yield', 0))
        }
        
        risk_metrics = dcf_calc.calculate_risk_metrics(base_params, valuation)
        
        return jsonify(risk_metrics)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/peer_comparison/<ticker>')
def peer_comparison(ticker):
    """Compare stock metrics with industry peers"""
    try:
        stock_info = data_interface.get_stock_info(ticker)
        
        if not stock_info:
            return jsonify({'error': f'Stock {ticker} not found'}), 400
        
        sector = stock_info.get('sector', 'Technology')
        peer_tickers = get_peers_by_sector(sector)
        
        # Get current stock metrics
        current_metrics = {
            'ticker': ticker,
            'pe_ratio': stock_info.get('pe_ratio', 0),
            'pb_ratio': stock_info.get('pb_ratio', 0),
            'dividend_yield': stock_info.get('dividend_yield', 0),
            'return_on_equity': stock_info.get('return_on_equity', 0),
            'profit_margin': stock_info.get('profit_margin', 0)
        }
        
        # Get peer metrics
        peers_data = []
        for peer_ticker in peer_tickers:
            if peer_ticker == ticker:
                continue
            try:
                peer_info = data_interface.get_stock_info(peer_ticker)
                if peer_info:
                    peers_data.append({
                        'ticker': peer_ticker,
                        'name': peer_info.get('name', peer_ticker),
                        'pe_ratio': peer_info.get('pe_ratio', 0),
                        'pb_ratio': peer_info.get('pb_ratio', 0),
                        'dividend_yield': peer_info.get('dividend_yield', 0),
                        'return_on_equity': peer_info.get('return_on_equity', 0),
                        'profit_margin': peer_info.get('profit_margin', 0)
                    })
            except:
                continue
        
        sector_avg = calculate_sector_averages(peers_data)
        
        return jsonify({
            'ticker': ticker,
            'sector': sector,
            'stock_metrics': current_metrics,
            'peers': peers_data,
            'sector_average': sector_avg
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/export_report/<ticker>')
def export_report(ticker):
    """Generate PDF valuation report"""
    try:
        # Fetch valuation data from session or database
        stock_info = data_interface.get_stock_info(ticker)
        
        if not stock_info:
            return jsonify({'error': f'Stock {ticker} not found'}), 400
        
        # Create PDF buffer
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.75*inch,
            leftMargin=0.75*inch,
            topMargin=0.75*inch,
            bottomMargin=0.75*inch
        )
        
        # Container for PDF elements
        elements = []
        styles = getSampleStyleSheet()
        
        # Add title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f77b4'),
            spaceAfter=30,
            alignment=1  # Center
        )
        elements.append(Paragraph(f'DCF Valuation Report: {ticker}', title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        # Add timestamp
        timestamp_style = ParagraphStyle(
            'Timestamp',
            parent=styles['Normal'],
            fontSize=10,
            textColor=colors.grey,
            alignment=1
        )
        elements.append(Paragraph(f'Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}', timestamp_style))
        elements.append(Spacer(1, 0.3*inch))
        
        # Add stock overview
        elements.append(Paragraph('Stock Overview', styles['Heading2']))
        overview_data = [
            ['Company', stock_info.get('name', 'N/A')],
            ['Ticker', ticker],
            ['Sector', stock_info.get('sector', 'N/A')],
            ['Industry', stock_info.get('industry', 'N/A')],
            ['Market Cap', f"${stock_info.get('market_cap', 0):,.0f}"]
        ]
        overview_table = Table(overview_data, colWidths=[2*inch, 3.5*inch])
        overview_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(overview_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Add key metrics
        elements.append(Paragraph('Key Metrics', styles['Heading2']))
        metrics_data = [
            ['Metric', 'Value'],
            ['P/E Ratio', f"{stock_info.get('pe_ratio', 0):.2f}"],
            ['P/B Ratio', f"{stock_info.get('pb_ratio', 0):.2f}"],
            ['Dividend Yield', f"{stock_info.get('dividend_yield', 0)*100:.2f}%"],
            ['ROE', f"{stock_info.get('return_on_equity', 0)*100:.2f}%"],
            ['Profit Margin', f"{stock_info.get('profit_margin', 0)*100:.2f}%"]
        ]
        metrics_table = Table(metrics_data, colWidths=[2.5*inch, 3*inch])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        elements.append(metrics_table)
        elements.append(Spacer(1, 0.3*inch))
        
        # Add footer
        elements.append(Spacer(1, 0.5*inch))
        footer_text = 'This report is for informational purposes only and should not be considered as investment advice.'
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=8,
            textColor=colors.grey,
            alignment=0
        )
        elements.append(Paragraph(footer_text, footer_style))
        
        # Build PDF
        doc.build(elements)
        buffer.seek(0)
        
        return send_file(
            buffer,
            mimetype='application/pdf',
            as_attachment=True,
            download_name=f'{ticker}_valuation_report.pdf'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/chart/<chart_type>')
def generate_chart(chart_type):
    """Generate charts for visualization"""
    try:
        
        ticker = request.args.get('ticker', '')
        
        if chart_type == 'fcf_projection':
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            
            years = [1, 2, 3, 4, 5]
            fcf_values = [100, 110, 120, 130, 140]  
            
            ax.bar(years, fcf_values, color='skyblue', alpha=0.7)
            ax.set_title(f'Projected Free Cash Flows - {ticker}')
            ax.set_xlabel('Year')
            ax.set_ylabel('Free Cash Flow ($M)')
            ax.grid(True, alpha=0.3)
            
        elif chart_type == 'sensitivity':
           
            fig, ax = plt.subplots(figsize=(10, 8))
            
           
            wacc_values = np.linspace(0.08, 0.15, 5)
            growth_values = np.linspace(0.02, 0.08, 5)
            
            
            sensitivity_data = np.random.rand(5, 5) * 100 + 50
            
            im = ax.imshow(sensitivity_data, cmap='RdYlGn', aspect='auto')
            ax.set_xticks(range(5))
            ax.set_yticks(range(5))
            ax.set_xticklabels([f'{w:.1%}' for w in wacc_values])
            ax.set_yticklabels([f'{g:.1%}' for g in growth_values])
            ax.set_xlabel('WACC')
            ax.set_ylabel('Growth Rate')
            ax.set_title(f'Sensitivity Analysis - {ticker}')
            
            
            plt.colorbar(im, ax=ax, label='Fair Value ($)')
        
        
        img_buffer = io.BytesIO()
        plt.savefig(img_buffer, format='png', dpi=150, bbox_inches='tight')
        img_buffer.seek(0)
        img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        plt.close()
        
        return jsonify({'chart': img_base64})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/stock_info/<ticker>')
def get_stock_info(ticker):
    """Get basic stock information"""
    try:
        stock_info = data_interface.get_stock_info(ticker)
        recommendations = data_interface.get_analyst_recommendations(ticker)
        earnings = data_interface.get_earnings_calendar(ticker)
        
        return jsonify({
            'stock_info': stock_info,
            'recommendations': recommendations,
            'earnings': earnings
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/popular_stocks')
def get_popular_stocks():
    """Get list of popular stocks for quick selection"""
    market = request.args.get('market', 'US')
    
    if market == 'IN':
       
        popular_stocks = [
            {'ticker': 'RELIANCE.NS', 'name': 'Reliance Industries Ltd.', 'sector': 'Energy'},
            {'ticker': 'TCS.NS', 'name': 'Tata Consultancy Services', 'sector': 'Technology'},
            {'ticker': 'HDFCBANK.NS', 'name': 'HDFC Bank Ltd.', 'sector': 'Banking'},
            {'ticker': 'INFY.NS', 'name': 'Infosys Ltd.', 'sector': 'Technology'},
            {'ticker': 'HINDUNILVR.NS', 'name': 'Hindustan Unilever Ltd.', 'sector': 'Consumer Goods'},
            {'ticker': 'ICICIBANK.NS', 'name': 'ICICI Bank Ltd.', 'sector': 'Banking'},
            {'ticker': 'BHARTIARTL.NS', 'name': 'Bharti Airtel Ltd.', 'sector': 'Telecom'},
            {'ticker': 'SBIN.NS', 'name': 'State Bank of India', 'sector': 'Banking'},
            {'ticker': 'WIPRO.NS', 'name': 'Wipro Ltd.', 'sector': 'Technology'},
            {'ticker': 'ITC.NS', 'name': 'ITC Ltd.', 'sector': 'Consumer Goods'}
        ]
    else:
        
        popular_stocks = [
            {'ticker': 'AAPL', 'name': 'Apple Inc.', 'sector': 'Technology'},
            {'ticker': 'MSFT', 'name': 'Microsoft Corporation', 'sector': 'Technology'},
            {'ticker': 'GOOGL', 'name': 'Alphabet Inc.', 'sector': 'Technology'},
            {'ticker': 'AMZN', 'name': 'Amazon.com Inc.', 'sector': 'Consumer Discretionary'},
            {'ticker': 'TSLA', 'name': 'Tesla Inc.', 'sector': 'Consumer Discretionary'},
            {'ticker': 'META', 'name': 'Meta Platforms Inc.', 'sector': 'Technology'},
            {'ticker': 'NVDA', 'name': 'NVIDIA Corporation', 'sector': 'Technology'},
            {'ticker': 'JPM', 'name': 'JPMorgan Chase & Co.', 'sector': 'Financial Services'},
            {'ticker': 'JNJ', 'name': 'Johnson & Johnson', 'sector': 'Healthcare'},
            {'ticker': 'V', 'name': 'Visa Inc.', 'sector': 'Financial Services'}
        ]
    
    return jsonify(popular_stocks)

@app.route('/watchlist', methods=['GET', 'POST', 'DELETE'])
def manage_watchlist():
    """Manage user watchlist"""
    try:
        if request.method == 'POST':
            data = request.get_json()
            ticker = data.get('ticker')
            # Save to user session
            if 'watchlist' not in session:
                session['watchlist'] = []
            if ticker not in session['watchlist']:
                session['watchlist'].append(ticker)
            session.modified = True
            return jsonify({'watchlist': session['watchlist'], 'message': f'{ticker} added to watchlist'})
        
        elif request.method == 'DELETE':
            data = request.get_json()
            ticker = data.get('ticker')
            if 'watchlist' in session and ticker in session['watchlist']:
                session['watchlist'].remove(ticker)
                session.modified = True
            return jsonify({'watchlist': session.get('watchlist', []), 'message': f'{ticker} removed from watchlist'})
        
        else:  # GET
            return jsonify({'watchlist': session.get('watchlist', [])})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def get_peers_by_sector(sector):
    """Return peer tickers by sector"""
    sector_peers = {
        'Technology': ['MSFT', 'GOOGL', 'META', 'NVDA', 'AAPL'],
        'Banking': ['JPM', 'BAC', 'WFC', 'GS', 'MS'],
        'Healthcare': ['JNJ', 'PFE', 'UNH', 'ABBV', 'MRNA'],
        'Consumer': ['AMZN', 'WMT', 'TM', 'COST', 'MCD'],
        'Financial Services': ['V', 'MA', 'AXP', 'CB', 'BLK'],
        'Energy': ['XOM', 'CVX', 'COP', 'SLB', 'EOG'],
        'Industrials': ['BA', 'CAT', 'GE', 'MMM', 'HON'],
        'Telecom': ['VZ', 'T', 'TMUS', 'CCI', 'LUMN'],
        'Utilities': ['NEE', 'DUK', 'SO', 'D', 'EXC'],
        'Real Estate': ['SPY', 'PLD', 'AMT', 'EQIX', 'AVB']
    }
    
    # Handle Indian stocks
    if sector and ('NSE' in sector or 'India' in sector):
        india_sector_peers = {
            'Technology': ['TCS.NS', 'INFY.NS', 'WIPRO.NS', 'LTIM.NS'],
            'Banking': ['HDFCBANK.NS', 'ICICIBANK.NS', 'SBIN.NS', 'AXISBANK.NS'],
            'Energy': ['RELIANCE.NS', 'NTPC.NS', 'POWERGRID.NS'],
            'Telecom': ['BHARTIARTL.NS', 'VI.NS', 'JIOTOWER.NS'],
            'FMCG': ['HINDUNILVR.NS', 'ITC.NS', 'BRITANNIA.NS', 'NESTLEIND.NS']
        }
        return india_sector_peers.get(sector, [])
    
    return sector_peers.get(sector, [])

def calculate_sector_averages(peers_data):
    """Calculate average metrics for peers"""
    if not peers_data:
        return {}
    
    metrics = ['pe_ratio', 'pb_ratio', 'dividend_yield', 'return_on_equity', 'profit_margin']
    averages = {}
    
    for metric in metrics:
        values = [p.get(metric, 0) for p in peers_data if p.get(metric, 0) > 0]
        if values:
            averages[metric] = sum(values) / len(values)
        else:
            averages[metric] = 0
    
    return averages

def get_ai_insights(ticker, fair_value, current_price, upside, recommendation, pe_ratio, roe, sector, stock_name):
    """Generate AI-powered investment insights"""
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            # Fallback to rule-based insights
            return generate_rule_based_insights(ticker, fair_value, current_price, upside, recommendation, pe_ratio, roe)
        
        client = OpenAI(api_key=api_key)
        
        prompt = f"""
        Provide a concise investment analysis for {stock_name} ({ticker}):
        
        Valuation Metrics:
        - Fair Value: ${fair_value:.2f}
        - Current Price: ${current_price:.2f}
        - Upside Potential: {upside:.1f}%
        - DCF Recommendation: {recommendation}
        
        Fundamental Metrics:
        - P/E Ratio: {pe_ratio:.2f}
        - ROE: {roe*100:.2f}%
        - Sector: {sector}
        
        Please provide:
        1. Investment thesis (2-3 sentences)
        2. Key risks
        3. Growth catalysts
        4. Conclusion
        
        Keep it concise and professional.
        """
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an expert financial analyst."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        return response.choices[0].message.content
    except:
        return generate_rule_based_insights(ticker, fair_value, current_price, upside, recommendation, pe_ratio, roe)

def generate_rule_based_insights(ticker, fair_value, current_price, upside, recommendation, pe_ratio, roe):
    """Generate rule-based insights when AI API unavailable"""
    
    thesis = f"{ticker} DCF fair value: ${fair_value:.2f} vs current price ${current_price:.2f}."
    
    risks = []
    if pe_ratio > 25:
        risks.append("High valuation multiples")
    if roe < 0.1:
        risks.append("Below-average profitability")
    if not risks:
        risks = ["Market volatility", "Sector headwinds"]
    
    catalysts = ["Strong balance sheet", "Market expansion", "Operational improvements"][:2]
    
    return f"""
INVESTMENT ANALYSIS: {ticker}

THESIS:
{thesis} Upside potential: {upside:.1f}%

RISKS:
• {risks[0]}
• {risks[1] if len(risks) > 1 else 'Economic downturn'}

CATALYSTS:
• {catalysts[0]}
• {catalysts[1] if len(catalysts) > 1 else 'Cost efficiency'}

CONCLUSION:
Rating: {recommendation}. Current risk-reward {'favorable' if upside > 10 else 'unfavorable'}.
"""

@app.route('/ai_insights', methods=['POST'])
def generate_ai_insights():
    """Generate AI-powered investment insights and summary"""
    try:
        data = request.get_json()
        
        ticker = data.get('ticker', 'Unknown')
        stock_name = data.get('stock_name', ticker)
        fair_value = float(data.get('fair_value_per_share', 0))
        current_price = float(data.get('current_price', 0))
        upside = float(data.get('upside_percentage', 0))
        recommendation = data.get('recommendation', 'HOLD')
        pe_ratio = float(data.get('pe_ratio', 0))
        roe = float(data.get('return_on_equity', 0))
        sector = data.get('sector', 'Unknown')
        
        insight = get_ai_insights(ticker, fair_value, current_price, upside, recommendation, pe_ratio, roe, sector, stock_name)
        
        return jsonify({
            'ticker': ticker,
            'insight': insight,
            'source': 'OpenAI GPT' if os.getenv('OPENAI_API_KEY') else 'Rule-Based'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def estimate_fcf_from_net_income(stock_info, ticker=None):
    """
    Estimate FCF from financial data using proper formula:
    FCF = Net Income + D&A - CapEx - Change in Working Capital
    Falls back to simpler methods if detailed data unavailable
    """
    try:
        # Try to get detailed FCF components from financials
        if ticker:
            try:
                stock = yf.Ticker(ticker)
                cash_flow = stock.cashflow
                
                if not cash_flow.empty and len(cash_flow.columns) > 0:
                    latest = cash_flow.iloc[:, 0]  # Most recent period
                    
                    # Get components
                    net_income = stock_info.get('net_income', 0)
                    depreciation = latest.get('Depreciation And Amortization', 0)
                    capex = abs(latest.get('Capital Expenditure', 0))  # Usually negative, so take abs
                    change_in_wc = latest.get('Change In Working Capital', 0)
                    
                    # Calculate FCF properly
                    if pd.notna(net_income) and net_income > 0:
                        fcf = net_income
                        
                        if pd.notna(depreciation):
                            fcf += depreciation
                        
                        if pd.notna(capex):
                            fcf -= capex
                        
                        if pd.notna(change_in_wc):
                            fcf -= change_in_wc
                        
                        if fcf > 0:
                            print(f"Estimated FCF from components: NI={net_income:,.0f}, D&A={depreciation:,.0f}, CapEx={capex:,.0f}, ΔWC={change_in_wc:,.0f}, FCF={fcf:,.0f}")
                            return fcf
            except Exception as e:
                print(f"Error calculating FCF from components: {e}")
        
        # Fallback: simple estimation from net income
        net_income = stock_info.get('net_income', 0)
        if net_income and net_income > 0:
            # Conservative estimate: 60-70% of net income
            estimated_fcf = net_income * 0.65
            print(f"Estimated FCF from net income (65%): {estimated_fcf:,.0f}")
            return estimated_fcf
        return None
    except Exception as e:
        print(f"Error in FCF estimation: {e}")
        return None

if __name__ == '__main__':
    
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static/css', exist_ok=True)
    os.makedirs('static/js', exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)
