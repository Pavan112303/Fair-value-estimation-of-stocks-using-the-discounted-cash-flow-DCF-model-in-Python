import yfinance as yf
import pandas as pd
from typing import Dict, Optional, List
import requests
from datetime import datetime, timedelta
import json
from rapidfuzz import fuzz


class TickerResolver:
    """Resolve user-provided ticker or company name to a valid Yahoo Finance ticker."""

    def __init__(self, session: Optional[requests.Session] = None, timeout: int = 6):
        self.session = session or requests.Session()
        self.timeout = timeout
        if not self.session.headers.get('User-Agent'):
            self.session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })

    def resolve(self, user_input: str, market: Optional[str] = None) -> Dict:
        query = (user_input or '').strip()
        if not query:
            return self._error('Ticker or company name is required.')

        normalized = query.upper().replace(' ', '')
        variations = self._build_variations(normalized, market)

        for symbol in variations:
            if self._validate_with_yfinance(symbol):
                return self._match(symbol, 100, 'yfinance', self._detect_market(symbol, ''))

        search_results = self._search_yahoo(query)
        if not search_results:
            return self._error(f"No match found for '{query}'.")

        scored = self._score_candidates(query, search_results)
        if not scored:
            return self._error(f"No match found for '{query}'.")

        best = scored[0]
        if best['score'] >= 80:
            return self._match(best['symbol'], best['score'], 'search', best['market'], best.get('name', ''))
        if best['score'] >= 60:
            return self._suggest(query, scored[:5])

        return self._error(f"No confident match found for '{query}'.")

    def _build_variations(self, normalized: str, market: Optional[str]) -> List[str]:
        if not normalized:
            return []

        if '.' in normalized:
            return [normalized]

        if market and market.upper() == 'IN':
            return [f'{normalized}.NS', f'{normalized}.BO', normalized]

        return [normalized, f'{normalized}.NS', f'{normalized}.BO']

    def _validate_with_yfinance(self, symbol: str) -> bool:
        try:
            stock = yf.Ticker(symbol)
            info = stock.info
            if info and (info.get('shortName') or info.get('longName') or info.get('regularMarketPrice') or info.get('currentPrice')):
                return True
            history = stock.history(period='1d')
            return history is not None and not history.empty
        except Exception:
            return False

    def _search_yahoo(self, query: str) -> List[Dict]:
        try:
            url = 'https://query2.finance.yahoo.com/v1/finance/search'
            params = {
                'q': query,
                'quotesCount': 10,
                'newsCount': 0
            }
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            return data.get('quotes', [])
        except Exception:
            return []

    def _score_candidates(self, query: str, quotes: List[Dict]) -> List[Dict]:
        results = []
        query_upper = query.upper()

        for quote in quotes:
            symbol = quote.get('symbol', '')
            if not symbol:
                continue

            quote_type = quote.get('quoteType')
            if quote_type and quote_type.upper() not in {'EQUITY', 'ETF'}:
                continue

            name = quote.get('shortname') or quote.get('longname') or ''
            exchange = quote.get('exchDisp') or quote.get('exchange') or ''

            symbol_score = fuzz.WRatio(query_upper, symbol.upper())
            name_score = fuzz.WRatio(query, name) if name else 0
            score = int(max(symbol_score, name_score))

            results.append({
                'symbol': symbol.upper(),
                'name': name,
                'exchange': exchange,
                'score': score,
                'market': self._detect_market(symbol, exchange)
            })

        results.sort(key=lambda item: item['score'], reverse=True)
        return results

    def _detect_market(self, symbol: str, exchange: str) -> str:
        symbol_upper = (symbol or '').upper()
        exchange_upper = (exchange or '').upper()

        if symbol_upper.endswith('.NS') or 'NSE' in exchange_upper:
            return 'IN'
        if symbol_upper.endswith('.BO') or 'BSE' in exchange_upper:
            return 'IN'
        return 'US'

    def _match(self, symbol: str, score: int, source: str, market: str, name: str = '') -> Dict:
        return {
            'status': 'match',
            'ticker': symbol.upper(),
            'confidence': score,
            'source': source,
            'market': market,
            'name': name
        }

    def _suggest(self, query: str, candidates: List[Dict]) -> Dict:
        return {
            'status': 'suggestion',
            'message': f"Did you mean one of these for '{query}'?",
            'suggestions': candidates
        }

    def _error(self, message: str) -> Dict:
        return {
            'status': 'error',
            'message': message
        }

class StockDataInterface:
    """
    Interface for fetching stock data and financial metrics
    """
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.ticker_resolver = TickerResolver(self.session)

    def resolve_ticker(self, user_input: str, market: Optional[str] = None) -> Dict:
        """Resolve user input to a valid ticker symbol."""
        return self.ticker_resolver.resolve(user_input, market)
    
    def get_stock_info(self, ticker: str) -> Dict:
        """
        Fetch basic stock information
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with stock information
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            # Check if we got valid data
            if not info or len(info) < 5:
                print(f"No data returned for {ticker}")
                return {}
            
            # Check if the stock exists (has basic info)
            if not info.get('longName') and not info.get('shortName'):
                print(f"Stock {ticker} not found or no data available")
                return {}
            
            return {
                'ticker': ticker,
                'name': info.get('longName', info.get('shortName', ticker)),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'shares_outstanding': info.get('sharesOutstanding', 0),
                'current_price': info.get('currentPrice', info.get('regularMarketPrice', 0)),
                'beta': info.get('beta', 1.0),
                'debt_to_equity': info.get('debtToEquity', 0),
                'total_debt': info.get('totalDebt', 0),
                'cash': info.get('totalCash', 0),
                'revenue': info.get('totalRevenue', 0),
                'net_income': info.get('netIncomeToCommon', 0),
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'dividend_yield': info.get('dividendYield', 0),
                'return_on_equity': info.get('returnOnEquity', 0),
                'profit_margin': info.get('profitMargins', 0)
            }
        except Exception as e:
            print(f"Error fetching data for {ticker}: {str(e)}")
            return {}
    
    def get_financial_statements(self, ticker: str) -> Dict:
        """
        Fetch financial statements
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with financial statements
        """
        try:
            stock = yf.Ticker(ticker)
            
            # Get financial statements
            income_stmt = stock.financials
            balance_sheet = stock.balance_sheet
            cash_flow = stock.cashflow
            
            return {
                'income_statement': income_stmt,
                'balance_sheet': balance_sheet,
                'cash_flow': cash_flow
            }
        except Exception as e:
            print(f"Error fetching financial statements for {ticker}: {str(e)}")
            return {}
    
    def calculate_free_cash_flow(self, ticker: str, years: int = 5) -> pd.DataFrame:
        """
        Calculate historical free cash flow
        
        Args:
            ticker: Stock ticker symbol
            years: Number of years to look back
            
        Returns:
            DataFrame with FCF data
        """
        try:
            stock = yf.Ticker(ticker)
            cash_flow = stock.cashflow
            
            # Check if cash_flow is empty or None
            if cash_flow is None or cash_flow.empty:
                print(f"No cash flow data available for {ticker}")
                return self._calculate_fcf_alternative(ticker, years)
            
            # Extract FCF data
            fcf_data = []
            for i, (date, row) in enumerate(cash_flow.iterrows()):
                if i >= years:
                    break
                    
                # Try different FCF column names
                fcf = None
                for col_name in ['Free Cash Flow', 'FreeCashFlow', 'Free cash flow']:
                    if col_name in row.index:
                        fcf = row.get(col_name, 0)
                        break
                
                if fcf is None:
                    fcf = 0
                
                # Check if fcf is a valid number
                if pd.notna(fcf) and isinstance(fcf, (int, float)) and fcf != 0:
                    # Handle different date formats
                    if hasattr(date, 'year'):
                        year = date.year
                    elif isinstance(date, str):
                        try:
                            year = int(date.split('-')[0])  # Extract year from string
                        except:
                            year = 2024  # Default year
                    else:
                        year = 2024  # Default year
                    
                    fcf_data.append({
                        'Year': year,
                        'Free_Cash_Flow': fcf
                    })
            
            # If no FCF data found, try alternative calculation
            if not fcf_data:
                return self._calculate_fcf_alternative(ticker, years)
            
            return pd.DataFrame(fcf_data)
        except Exception as e:
            print(f"Error calculating FCF for {ticker}: {str(e)}")
            return self._calculate_fcf_alternative(ticker, years)
    
    def _calculate_fcf_alternative(self, ticker: str, years: int = 5) -> pd.DataFrame:
        """
        Alternative method to calculate FCF using operating cash flow and capex
        
        Args:
            ticker: Stock ticker symbol
            years: Number of years to look back
            
        Returns:
            DataFrame with FCF data
        """
        try:
            stock = yf.Ticker(ticker)
            cash_flow = stock.cashflow
            
            if cash_flow is None or cash_flow.empty:
                print(f"No cash flow data available for {ticker}")
                return pd.DataFrame()
            
            fcf_data = []
            for i, (date, row) in enumerate(cash_flow.iterrows()):
                if i >= years:
                    break
                
                # Try different column names for operating cash flow
                operating_cf = None
                for col_name in ['Total Cash From Operating Activities', 'Operating Cash Flow', 'Cash from Operations', 'Cash From Operations']:
                    if col_name in row.index:
                        operating_cf = row.get(col_name, 0)
                        break
                
                # Try different column names for capital expenditures
                capex = None
                for col_name in ['Capital Expenditures', 'Capital Expenditure', 'Capex', 'Capital Expenditure']:
                    if col_name in row.index:
                        capex = row.get(col_name, 0)
                        break
                
                if operating_cf is None:
                    operating_cf = 0
                if capex is None:
                    capex = 0
                
                # Check if both are valid numbers
                if (pd.notna(operating_cf) and pd.notna(capex) and 
                    isinstance(operating_cf, (int, float)) and isinstance(capex, (int, float))):
                    
                    fcf = operating_cf - abs(capex)  # Capex is usually negative
                    
                    # Only include positive FCF values
                    if fcf > 0:
                        # Handle different date formats
                        if hasattr(date, 'year'):
                            year = date.year
                        elif isinstance(date, str):
                            try:
                                year = int(date.split('-')[0])
                            except:
                                year = 2024
                        else:
                            year = 2024
                        
                        fcf_data.append({
                            'Year': year,
                            'Free_Cash_Flow': fcf
                        })
            
            return pd.DataFrame(fcf_data)
        except Exception as e:
            print(f"Error in alternative FCF calculation for {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def get_market_data(self, ticker: str, period: str = "5y") -> pd.DataFrame:
        """
        Get historical price data
        
        Args:
            ticker: Stock ticker symbol
            period: Time period for data
            
        Returns:
            DataFrame with price data
        """
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            return hist
        except Exception as e:
            print(f"Error fetching market data for {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def get_analyst_recommendations(self, ticker: str) -> Dict:
        """
        Get analyst recommendations and price targets
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with analyst data
        """
        try:
            stock = yf.Ticker(ticker)
            recommendations = stock.recommendations
            
            if recommendations is not None and not recommendations.empty:
                latest = recommendations.iloc[-1]
                return {
                    'firm': latest.get('Firm', 'Unknown'),
                    'to_grade': latest.get('To Grade', 'Unknown'),
                    'action': latest.get('Action', 'Unknown'),
                    'date': latest.name.strftime('%Y-%m-%d') if hasattr(latest.name, 'strftime') else str(latest.name)
                }
            else:
                return {'firm': 'No data', 'to_grade': 'No data', 'action': 'No data', 'date': 'No data'}
        except Exception as e:
            print(f"Error fetching recommendations for {ticker}: {str(e)}")
            return {'firm': 'Error', 'to_grade': 'Error', 'action': 'Error', 'date': 'Error'}
    
    def get_earnings_calendar(self, ticker: str) -> Dict:
        """
        Get earnings calendar information
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dictionary with earnings data
        """
        try:
            stock = yf.Ticker(ticker)
            calendar = stock.calendar
            
            if calendar is not None and hasattr(calendar, 'empty') and not calendar.empty:
                return {
                    'earnings_date': calendar.index[0].strftime('%Y-%m-%d') if hasattr(calendar.index[0], 'strftime') else str(calendar.index[0]),
                    'earnings_estimate': calendar.iloc[0].get('Earnings Estimate', 0),
                    'revenue_estimate': calendar.iloc[0].get('Revenue Estimate', 0)
                }
            else:
                return {'earnings_date': 'No data', 'earnings_estimate': 0, 'revenue_estimate': 0}
        except Exception as e:
            print(f"Error fetching earnings calendar for {ticker}: {str(e)}")
            return {'earnings_date': 'Error', 'earnings_estimate': 0, 'revenue_estimate': 0}
